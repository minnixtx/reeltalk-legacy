"""tests incoming activities"""

from unittest.mock import patch

from django.test import TestCase

from reeltalk import models, views


class InboxRemove(TestCase):
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

        cls.film = models.Film.objects.create(
            title="Test",
            remote_id="https://bookwyrm.social/film/37292",
        )

    def test_handle_unshelve_film(self):
        """remove a film from a shelf"""
        shelf = models.Shelf.objects.create(user=self.remote_user, name="Test Shelf")
        shelf.remote_id = "https://bookwyrm.social/user/mouse/shelf/to-read"
        shelf.save()

        shelffilm = models.ShelfFilm.objects.create(
            user=self.remote_user, shelf=shelf, film=self.film
        )
        shelffilm.remote_id = "https://example.com/shelffilm/6189"
        shelffilm.save(broadcast=False)

        self.assertEqual(shelf.films.first(), self.film)
        self.assertEqual(shelf.films.count(), 1)

        activity = {
            "id": shelffilm.remote_id,
            "type": "Remove",
            "actor": "https://example.com/users/rat",
            "object": {
                "actor": self.remote_user.remote_id,
                "type": "ShelfItem",
                "film": "https://bookwyrm.social/film/37292",
                "id": shelffilm.remote_id,
            },
            "target": "https://bookwyrm.social/user/mouse/shelf/to-read",
            "@context": "https://www.w3.org/ns/activitystreams",
        }
        views.inbox.activity_task(activity)
        self.assertFalse(shelf.films.exists())

    def test_handle_remove_film_from_list(self):
        """remove a film from a list"""
        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.lists_stream.remove_list_task.delay"),
        ):
            film_list = models.List.objects.create(
                name="test list",
                user=self.local_user,
            )
            listitem = models.ListItem.objects.create(
                user=self.local_user,
                film=self.film,
                film_list=film_list,
                order=1,
            )
        listitem.remote_id = "https://example.com/listfilm/6189"
        listitem.save(broadcast=False)
        self.assertEqual(film_list.films.count(), 1)

        activity = {
            "id": listitem.remote_id,
            "type": "Remove",
            "actor": "https://example.com/users/rat",
            "object": {
                "actor": self.remote_user.remote_id,
                "type": "ListItem",
                "film": "https://bookwyrm.social/film/37292",
                "id": listitem.remote_id,
            },
            "target": film_list.remote_id,
            "@context": "https://www.w3.org/ns/activitystreams",
        }
        views.inbox.activity_task(activity)

        self.assertEqual(film_list.films.count(), 0)
