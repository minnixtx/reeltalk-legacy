"""test reeltalk user export functions"""

import json
import pathlib

from unittest.mock import patch

from django.test import TestCase

from reeltalk import models
from reeltalk.utils.tar import ReeltalkTarFile


class ReeltalkExportJob(TestCase):
    """testing user export functions"""

    @classmethod
    def setUpTestData(self):
        """lots of stuff to set up for a user export"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
            patch("reeltalk.suggested_users.rerank_user_task.delay"),
            patch("reeltalk.lists_stream.remove_list_task.delay"),
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.activitystreams.add_film_statuses_task"),
            patch("reeltalk.activitystreams.remove_film_statuses_task"),
        ):
            self.local_user = models.User.objects.create_user(
                "mouse",
                "mouse@mouse.mouse",
                "password",
                local=True,
                localname="mouse",
                name="Mouse",
                summary="I'm a real film mouse",
                manually_approves_followers=False,
                hide_follows=False,
                show_suggested_users=False,
                discoverable=True,
                preferred_timezone="America/Los Angeles",
                default_post_privacy="followers",
            )
            avatar_path = pathlib.Path(__file__).parent.joinpath(
                "../../static/images/default_avi.jpg"
            )
            with open(avatar_path, "rb") as avatar_file:
                self.local_user.avatar.save("mouse-avatar.jpg", avatar_file)

            self.rat_user = models.User.objects.create_user(
                "rat", "rat@rat.rat", "ratword", local=True, localname="rat"
            )

            self.badger_user = models.User.objects.create_user(
                "badger",
                "badger@badger.badger",
                "badgerword",
                local=True,
                localname="badger",
            )

            self.list = models.List.objects.create(
                name="My excellent list",
                user=self.local_user,
                remote_id="https://local.lists/1111",
            )

            self.saved_list = models.List.objects.create(
                name="My cool list",
                user=self.rat_user,
                remote_id="https://local.lists/9999",
            )

            self.local_user.saved_lists.add(self.saved_list)
            self.local_user.blocks.add(self.badger_user)
            self.rat_user.followers.add(self.local_user)

            # films
            self.film = models.Film.objects.create(title="Example Film")
            self.another_film = models.Film.objects.create(title="Another Film")

            # film poster
            poster_path = pathlib.Path(__file__).parent.joinpath(
                "../../static/images/default_avi.jpg"
            )
            with open(poster_path, "rb") as poster_file:
                self.film.poster.save("tèst.jpg", poster_file)

            # shelve
            read_shelf = models.Shelf.objects.get(
                user=self.local_user, identifier="read"
            )
            models.ShelfFilm.objects.create(
                film=self.film, shelf=read_shelf, user=self.local_user
            )
            models.ShelfFilm.objects.create(
                film=self.another_film, shelf=read_shelf, user=self.local_user
            )

            # add to list
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=True,
                order=1,
            )

            # review
            models.Review.objects.create(
                content="awesome",
                name="my review",
                rating=5,
                user=self.local_user,
                film=self.film,
            )
            # comment
            models.Comment.objects.create(
                content="ok so far",
                user=self.local_user,
                film=self.film,
            )
            # deleted comment
            models.Comment.objects.create(
                content="so far",
                user=self.local_user,
                film=self.film,
                deleted=True,
            )

            self.job = models.ReeltalkExportJob.objects.create(user=self.local_user)

            # run the first stage of the export
            with patch("reeltalk.models.reeltalk_export_job.create_archive_task.delay"):
                models.reeltalk_export_job.create_export_json_task(job_id=self.job.id)
            self.job.refresh_from_db()

    def test_add_film_to_user_export_job(self):
        """does the export include the films and their related data?"""
        self.assertIsNotNone(self.job.export_json["films"])
        self.assertEqual(len(self.job.export_json["films"]), 2)

        entry = next(
            f
            for f in self.job.export_json["films"]
            if f["film"]["id"] == self.film.remote_id
        )

        self.assertEqual(entry["film"]["title"], "Example Film")
        self.assertEqual(len(entry["shelves"]), 1)
        self.assertEqual(len(entry["lists"]), 1)
        self.assertEqual(len(entry["comments"]), 1)
        self.assertEqual(len(entry["reviews"]), 1)

        self.assertEqual(
            entry["film"]["poster"]["url"], f"images/{self.film.poster.name}"
        )

    def test_start_export_task(self):
        """test saved list task saves initial json and data"""
        self.assertIsNotNone(self.job.export_data)
        self.assertIsNotNone(self.job.export_json)
        self.assertEqual(self.job.export_json["name"], self.local_user.name)

    def test_export_saved_lists_task(self):
        """test export_saved_lists_task adds the saved lists"""
        self.assertIsNotNone(self.job.export_json["saved_lists"])
        self.assertEqual(
            self.job.export_json["saved_lists"][0], self.saved_list.remote_id
        )

    def test_export_follows_task(self):
        """test export_follows_task adds the follows"""
        self.assertIsNotNone(self.job.export_json["follows"])
        self.assertEqual(self.job.export_json["follows"][0], self.rat_user.remote_id)

    def test_export_blocks_task(self):
        """test export_blocks_task adds the blocks"""
        self.assertIsNotNone(self.job.export_json["blocks"])
        self.assertEqual(self.job.export_json["blocks"][0], self.badger_user.remote_id)

    def test_json_export(self):
        """test json_export job adds settings"""
        self.assertIsNotNone(self.job.export_json["settings"])
        self.assertEqual(
            self.job.export_json["settings"]["preferred_timezone"],
            "America/Los Angeles",
        )
        self.assertEqual(
            self.job.export_json["settings"]["default_post_privacy"], "followers"
        )
        self.assertFalse(self.job.export_json["settings"]["show_suggested_users"])

    def test_get_films_for_user(self):
        """does get_films_for_user get all the films"""

        data = models.reeltalk_export_job.get_films_for_user(self.local_user)

        self.assertEqual(len(data), 2)
        self.assertCountEqual([f.title for f in data], ["Example Film", "Another Film"])

    def test_archive(self):
        """actually create the TAR file"""
        models.reeltalk_export_job.create_archive_task(job_id=self.job.id)
        self.job.refresh_from_db()

        with (
            self.job.export_data.open("rb") as tar_file,
            ReeltalkTarFile.open(mode="r", fileobj=tar_file) as tar,
        ):
            archive_json_file = tar.extractfile("archive.json")
            data = json.load(archive_json_file)

            # JSON from the archive should be what we want it to be
            self.assertEqual(data, self.job.export_json)

            # User avatar should be present in archive
            with self.local_user.avatar.open() as expected_avatar:
                archive_avatar = tar.extractfile(data["icon"]["url"])
                self.assertEqual(expected_avatar.read(), archive_avatar.read())
