"""Import data from Reeltalk export files"""

from django.http import QueryDict

from reeltalk.models import User
from reeltalk.models.reeltalk_import_job import ReeltalkImportJob
from . import Importer


class ReeltalkImporter:
    """Import a Reeltalk User export file.
    This is kind of a combination of an importer and a connector.
    """

    def process_import(
        self, user: User, archive_file: bytes, settings: QueryDict
    ) -> ReeltalkImportJob:
        """import user data from a Reeltalk export file"""

        required = [k for k in settings if settings.get(k) == "on"]

        job = ReeltalkImportJob.objects.create(
            user=user, archive_file=archive_file, required=required
        )

        return job

    def create_retry_job(
        self, user: User, original_job: ReeltalkImportJob
    ) -> ReeltalkImportJob:
        """retry items that didn't import"""

        job = ReeltalkImportJob.objects.create(
            user=user,
            archive_file=original_job.archive_file,
            required=original_job.required,
            retry=True,
        )

        return job


class ReeltalkBooksImporter(Importer):
    """
    Handle reading a csv from ReelTalk.
    Goodreads is the default importer, we basically just use the same structure
    But ReelTalk has additional attributes in the csv
    """

    service = "ReelTalk"
    row_mappings_guesses = Importer.row_mappings_guesses + [
        ("shelf_name", ["shelf_name"]),
        ("review_published", ["review_published"]),
    ]
