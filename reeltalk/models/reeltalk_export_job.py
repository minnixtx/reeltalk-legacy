"""Export user account to tar.gz file for import into another Reeltalk instance"""

import logging
import os

from boto3.session import Session as BotoSession
from s3_tar import S3Tar

from django.db import transaction
from django.db.models import FileField, JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.core.files.base import ContentFile
from django.core.files.storage import storages

from reeltalk import settings

from reeltalk.models import Film, ShelfFilm, ListItem
from reeltalk.models import Review, Comment
from reeltalk.models import UserFollows, User, UserBlocks
from reeltalk.models.job import ParentJob, ParentTask
from reeltalk.tasks import app, IMPORTS
from reeltalk.utils.tar import ReeltalkTarFile

logger = logging.getLogger(__name__)


class ReeltalkAwsSession(BotoSession):
    """a boto session that always uses settings.AWS_S3_ENDPOINT_URL"""

    def client(self, *args, **kwargs):
        kwargs["endpoint_url"] = storages["exports"].endpoint_url
        return super().client("s3", *args, **kwargs)


def select_exports_storage():
    """callable to allow for dependency on runtime configuration"""
    return storages["exports"]


class ReeltalkExportJob(ParentJob):
    """entry for a specific request to export a reeltalk user"""

    export_data = FileField(null=True, storage=select_exports_storage)
    export_json = JSONField(null=True, encoder=DjangoJSONEncoder)

    def start_job(self):
        """schedule the first task"""

        self.set_status("active")
        create_export_json_task.delay(job_id=self.id)


@app.task(queue=IMPORTS, base=ParentTask)
def create_export_json_task(**kwargs):
    """create the JSON data for the export"""

    job = ReeltalkExportJob.objects.get(id=kwargs["job_id"])
    # don't start the job if it was stopped from the UI
    if job.status == "stopped":
        return

    with transaction.atomic():
        try:
            # generate JSON
            data = export_user(job.user)
            data["settings"] = export_settings(job.user)
            data["films"] = export_films(job.user)
            data["saved_lists"] = export_saved_lists(job.user)
            data["follows"] = export_follows(job.user)
            data["blocks"] = export_blocks(job.user)
            job.export_json = data
            job.save(update_fields=["export_json"])

            # trigger task to create tar file
            create_archive_task.delay(job_id=job.id)

        except Exception as err:
            logger.exception(
                "create_export_json_task for job %s failed with error: %s", job.id, err
            )
            job.set_status("failed")


def archive_file_location(file, directory="") -> str:
    """get the relative location of a file inside the archive"""
    return os.path.join(directory, file.name)


@app.task(queue=IMPORTS, base=ParentTask)
def create_archive_task(**kwargs):
    """create the archive containing the JSON file and additional files"""

    job = ReeltalkExportJob.objects.get(id=kwargs["job_id"])

    # don't start the job if it was stopped from the UI
    if job.status == "stopped":
        return

    try:
        export_task_id = str(job.task_id)
        archive_filename = f"{export_task_id}.tar.gz"
        export_json_bytes = DjangoJSONEncoder().encode(job.export_json).encode("utf-8")
        user = job.user
        exports_storage = storages["exports"]

        if settings.USE_S3_FOR_EXPORTS:
            # Handle creating the final archive
            s3_tar = S3Tar(
                exports_storage.bucket_name,
                os.path.join(exports_storage.location, archive_filename),
                session=ReeltalkAwsSession(),
            )

            # Save JSON file to a temporary location
            export_json_tmp_file = os.path.join(export_task_id, "archive.json")
            exports_storage.save(
                export_json_tmp_file,
                ContentFile(export_json_bytes),
            )
            s3_tar.add_file(
                os.path.join(exports_storage.location, export_json_tmp_file)
            )

            if user.avatar:
                exports_storage.save(user.avatar.name, user.avatar)
                s3_tar.add_file(
                    os.path.join(exports_storage.location, user.avatar.name),
                    folder="avatars",
                )

            # Create archive and store file name
            s3_tar.tar()
            job.export_data = archive_filename
            job.save(update_fields=["export_data"])

            # Delete temporary files
            exports_storage.delete(export_json_tmp_file)
            exports_storage.delete(user.avatar.name)

        else:
            # exports saved to local storage
            # this is the default even when using S3 for other files
            # Use the scheduled task to periodically delete these
            job.export_data = archive_filename
            with job.export_data.open("wb") as tar_file:
                with ReeltalkTarFile.open(mode="w:gz", fileobj=tar_file) as tar:
                    # save json file
                    tar.write_bytes(export_json_bytes)

                    # Add avatar image if present
                    if user.avatar:
                        tar.add_image(user.avatar)

            job.save(update_fields=["export_data"])

        job.complete_job()

    except Exception as err:
        logger.exception(
            "create_archive_task for job %s failed with error: %s", job.id, err
        )
        job.set_status("failed")


def export_user(user: User):
    """export user data"""
    data = user.to_activity()
    if user.avatar:
        data["icon"]["url"] = archive_file_location(user.avatar)
    else:
        data["icon"] = {}
    return data


def export_settings(user: User):
    """Additional settings - can't be serialized as AP"""
    vals = [
        "preferred_timezone",
        "default_post_privacy",
        "show_suggested_users",
    ]
    return {k: getattr(user, k) for k in vals}


def export_saved_lists(user: User):
    """add user saved lists to export JSON"""
    return [saved_list.remote_id for saved_list in user.saved_lists.all()]


def export_follows(user: User):
    """add user follows to export JSON"""
    follows = UserFollows.objects.filter(user_subject=user).distinct()
    following = User.objects.filter(userfollows_user_object__in=follows).distinct()
    return [f.remote_id for f in following]


def export_blocks(user: User):
    """add user blocks to export JSON"""
    blocks = UserBlocks.objects.filter(user_subject=user).distinct()
    blocking = User.objects.filter(userblocks_user_object__in=blocks).distinct()
    return [b.remote_id for b in blocking]


def export_films(user: User):
    """add films to export JSON"""
    films = get_films_for_user(user)
    return [export_film(user, film) for film in films]


def export_film(user: User, film: Film):
    """add film to export JSON"""
    data = {}
    data["film"] = film.to_activity()

    if film.poster:
        data["film"]["poster"]["url"] = archive_file_location(
            film.poster, directory="images"
        )

    # Shelves this film is on
    # Every ShelfItem is this film so we don't need to serialize the items
    shelf_films = (
        ShelfFilm.objects.select_related("shelf")
        .filter(user=user, film=film)
        .distinct()
    )
    data["shelves"] = [shelffilm.shelf.to_activity() for shelffilm in shelf_films]

    # Lists and ListItems
    # ListItems include "notes" and "approved" so we need them
    # even though we know it's this film
    list_items = ListItem.objects.filter(film=film, user=user).distinct()

    data["lists"] = []
    for item in list_items:
        list_info = item.film_list.to_activity()
        list_info["privacy"] = (
            item.film_list.privacy
        )  # this isn't serialized so we add it
        list_info["list_item"] = item.to_activity()
        data["lists"].append(list_info)

    # Statuses
    # Can't use select_subclasses here because
    # we need to filter on the "film" value,
    # which is not available on an ordinary Status
    for status in ["comments", "reviews"]:
        data[status] = []

    comments = Comment.objects.filter(user=user, film=film, deleted=False).all()
    data["comments"] = [status.to_activity() for status in comments]

    reviews = Review.objects.filter(user=user, film=film, deleted=False).all()
    data["reviews"] = [status.to_activity() for status in reviews]
    return data


def get_films_for_user(user):
    """
    Get all the films related to a user.
    We use selecting film_id instead of Q objects because it creates
    multiple simple queries instead of a complex DB query
    that can time out.
    """

    shelf_ids = ShelfFilm.objects.filter(user=user).values_list("film_id", flat=True)
    reviews = Review.objects.filter(user=user).values_list("film_id", flat=True)
    lists = ListItem.objects.filter(user=user).values_list("film_id", flat=True)
    comments = Comment.objects.filter(user=user, deleted=False).values_list(
        "film_id", flat=True
    )

    films = (
        Film.objects.filter(
            id__in=(set(shelf_ids) | set(reviews) | set(lists) | set(comments))
        )
        .distinct()
    )

    return films
