"""tests incoming activities"""

import json
import pathlib
from unittest.mock import patch

from django.test import TestCase

from reeltalk import models, views


class InboxUpdate(TestCase):
    """inbox tests"""

    @classmethod
    def setUpTestData(cls):
        """basic user and film data"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse@example.com",
                "mouse@mouse.com",
                "mouseword",
                local=True,
                localname="mouse",
            )
        cls.local_user.remote_id = "https://example.com/user/mouse"
        cls.local_user.save(broadcast=False, update_fields=["remote_id"])
        with patch("reeltalk.models.user.set_remote_server.delay"):
            cls.remote_user = models.User.objects.create_user(
                "rat",
                "rat@rat.com",
                "ratword",
                local=False,
                remote_id="https://example.com/users/rat",
                inbox="https://example.com/users/rat/inbox",
                outbox="https://example.com/users/rat/outbox",
            )

    def setUp(self):
        """individual test setup"""
        self.update_json = {
            "id": "hi",
            "type": "Update",
            "actor": "hi",
            "to": ["https://www.w3.org/ns/activitystreams#public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "object": {},
        }

    def test_update_list(self):
        """update an existing list"""
        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.lists_stream.remove_list_task.delay"),
        ):
            film_list = models.List.objects.create(
                name="hi", remote_id="https://example.com/list/22", user=self.local_user
            )
        activity = self.update_json
        activity["object"] = {
            "id": "https://example.com/list/22",
            "type": "FilmList",
            "totalItems": 1,
            "first": "https://example.com/list/22?page=1",
            "last": "https://example.com/list/22?page=1",
            "name": "Test List",
            "owner": "https://example.com/user/mouse",
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "summary": "summary text",
            "curation": "curated",
        }
        with patch("reeltalk.lists_stream.remove_list_task.delay"):
            views.inbox.activity_task(activity)
        film_list.refresh_from_db()
        self.assertEqual(film_list.name, "Test List")
        self.assertEqual(film_list.curation, "curated")
        self.assertEqual(film_list.description, "summary text")
        self.assertEqual(film_list.remote_id, "https://example.com/list/22")

    @patch("reeltalk.suggested_users.rerank_user_task.delay")
    @patch("reeltalk.activitystreams.add_user_statuses_task.delay")
    @patch("reeltalk.lists_stream.add_user_lists_task.delay")
    def test_update_user(self, *_):
        """update an existing user"""
        models.UserFollows.objects.create(
            user_subject=self.local_user,
            user_object=self.remote_user,
        )
        models.UserFollows.objects.create(
            user_subject=self.remote_user,
            user_object=self.local_user,
        )
        self.assertTrue(self.remote_user in self.local_user.followers.all())
        self.assertTrue(self.local_user in self.remote_user.followers.all())

        datafile = pathlib.Path(__file__).parent.joinpath("../../data/ap_user_rat.json")
        userdata = json.loads(datafile.read_bytes())
        del userdata["icon"]
        self.assertIsNone(self.remote_user.name)
        self.assertFalse(self.remote_user.discoverable)

        views.inbox.activity_task(
            {
                "type": "Update",
                "to": [],
                "cc": [],
                "actor": "hi",
                "id": "sdkjf",
                "object": userdata,
            }
        )
        user = models.User.objects.get(id=self.remote_user.id)
        self.assertEqual(user.name, "RAT???")
        self.assertEqual(user.username, "rat@example.com")
        self.assertTrue(user.discoverable)

        # make sure relationships aren't disrupted
        self.assertTrue(self.remote_user in self.local_user.followers.all())
        self.assertTrue(self.local_user in self.remote_user.followers.all())

    def test_update_film(self):
        """update an existing film"""
        film = models.Film.objects.create(
            title="Test Film", remote_id="https://bookwyrm.social/film/5989"
        )

        self.assertEqual(film.title, "Test Film")

        views.inbox.activity_task(
            {
                "type": "Update",
                "to": [],
                "cc": [],
                "actor": "hi",
                "id": "sdkjf",
                "object": {
                    "id": "https://bookwyrm.social/film/5989",
                    "type": "Film",
                    "title": "Piranesi",
                    "description": "A mysterious house and its keeper.",
                    "year": 2020,
                    "runtime": 120,
                    "lastEditedBy": self.remote_user.remote_id,
                },
            }
        )
        film = models.Film.objects.get(id=film.id)
        self.assertEqual(film.title, "Piranesi")
        self.assertEqual(film.last_edited_by, self.remote_user)

    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    @patch("reeltalk.activitystreams.add_status_task.delay")
    def test_update_status(self, *_):
        """edit a status"""
        status = models.Status.objects.create(
            user=self.remote_user,
            content="hi",
            remote_id="https://example.com/status/1",
        )

        activity = self.update_json
        activity["object"] = {
            "id": status.remote_id,
            "type": "Note",
            "published": "2020-12-13T05:09:29Z",
            "url": "https://example.com/@rat/1234567",
            "attributedTo": self.remote_user.remote_id,
            "to": ["https://example.com/user/mouse"],
            "cc": [],
            "sensitive": False,
            "content": "test content in note",
            "updated": "2021-12-13T05:09:29Z",
        }

        views.inbox.activity_task(activity)

        status.refresh_from_db()
        self.assertEqual(status.content, "test content in note")
        self.assertEqual(status.edited_date.year, 2021)
        self.assertEqual(status.edited_date.month, 12)
        self.assertEqual(status.edited_date.day, 13)
