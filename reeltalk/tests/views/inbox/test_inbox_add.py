"""tests incoming activities"""

from unittest.mock import patch

from django.test import TestCase
import responses

from reeltalk import models, views


class InboxAdd(TestCase):
    """inbox tests"""

    @classmethod
    def setUpTestData(cls):
        """basic user and film data"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            local_user = models.User.objects.create_user(
                "mouse@example.com",
                "mouse@mouse.com",
                "mouseword",
                local=True,
                localname="mouse",
            )
        local_user.remote_id = "https://example.com/user/mouse"
        local_user.save(broadcast=False, update_fields=["remote_id"])
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

        cls.film = models.Film.objects.create(
            title="Test",
            remote_id="https://example.com/film/37292",
        )

    @responses.activate
    def test_handle_add_film_to_shelf(self):
        """shelving a film"""
        shelf = models.Shelf.objects.create(user=self.remote_user, name="Test Shelf")
        shelf.remote_id = "https://example.com/user/rat/shelf/to-read"
        shelf.save()

        responses.add(
            responses.GET,
            "https://example.com/user/rat/shelf/to-read",
            json={
                "id": shelf.remote_id,
                "type": "Shelf",
                "totalItems": 1,
                "first": "https://example.com/shelf/22?page=1",
                "last": "https://example.com/shelf/22?page=1",
                "name": "Test Shelf",
                "owner": self.remote_user.remote_id,
                "to": ["https://www.w3.org/ns/activitystreams#Public"],
                "cc": ["https://example.com/user/rat/followers"],
                "@context": "https://www.w3.org/ns/activitystreams",
            },
        )

        activity = {
            "id": "https://example.com/shelffilm/6189#add",
            "type": "Add",
            "actor": "https://example.com/users/rat",
            "object": {
                "actor": self.remote_user.remote_id,
                "type": "ShelfItem",
                "film": "https://example.com/film/37292",
                "id": "https://example.com/shelffilm/6189",
            },
            "target": "https://example.com/user/rat/shelf/to-read",
            "@context": "https://www.w3.org/ns/activitystreams",
        }
        views.inbox.activity_task(activity)
        self.assertEqual(shelf.films.first(), self.film)

    @responses.activate
    def test_handle_add_film_to_list(self):
        """listing a film"""
        responses.add(
            responses.GET,
            "https://example.com/user/mouse/list/to-read",
            json={
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
                "@context": "https://www.w3.org/ns/activitystreams",
            },
        )

        activity = {
            "id": "https://example.com/listfilm/6189#add",
            "type": "Add",
            "actor": "https://example.com/users/rat",
            "object": {
                "actor": self.remote_user.remote_id,
                "type": "ListItem",
                "film": "https://example.com/film/37292",
                "id": "https://example.com/listfilm/6189",
                "notes": "hi hello",
                "order": 1,
            },
            "target": "https://example.com/user/mouse/list/to-read",
            "@context": "https://www.w3.org/ns/activitystreams",
        }
        views.inbox.activity_task(activity)

        film_list = models.List.objects.get()
        listitem = models.ListItem.objects.get()
        self.assertEqual(film_list.name, "Test List")
        self.assertEqual(film_list.films.first(), self.film)
        self.assertEqual(listitem.remote_id, "https://example.com/listfilm/6189")
        self.assertEqual(listitem.notes, "hi hello")
