"""testing models"""

from unittest.mock import patch
from django.test import TestCase

from reeltalk import models, settings


@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.lists_stream.populate_lists_task.delay")
@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
@patch("reeltalk.activitystreams.remove_film_statuses_task.delay")
class Shelf(TestCase):
    """some activitypub oddness ahead"""

    @classmethod
    def setUpTestData(cls):
        """look, a shelf"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse", "mouse@mouse.mouse", "mouseword", local=True, localname="mouse"
            )
        cls.film = models.Film.objects.create(title="Test Film")

    def test_remote_id(self, *_):
        """shelves use custom remote ids"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            shelf = models.Shelf.objects.create(
                name="Test Shelf", identifier="test-shelf", user=self.local_user
            )
        expected_id = f"{settings.BASE_URL}/user/mouse/films/test-shelf"
        self.assertEqual(shelf.get_remote_id(), expected_id)

    def test_local_path_for_local_user_shelf(self, *_):
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            shelf = models.Shelf.objects.create(
                name="Test Shelf", identifier="test-shelf", user=self.local_user
            )
        self.assertEqual(shelf.local_path, "/user/mouse/films/test-shelf")

    def test_local_path_for_remote_user_shelf_stays_local(self, *_):
        remote_user = models.User.objects.create_user(
            "rat",
            "rat@rat.rat",
            "ratword",
            local=False,
            remote_id="https://example.com/user/rat",
            reeltalk_user=False,
        )
        shelf = models.Shelf.objects.create(
            name="Test Shelf", identifier="test-shelf", user=remote_user
        )
        self.assertEqual(shelf.local_path, "/user/rat@example.com/films/test-shelf")

    def test_to_activity(self, *_):
        """jsonify it"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            shelf = models.Shelf.objects.create(
                name="Test Shelf", identifier="test-shelf", user=self.local_user
            )
        activity_json = shelf.to_activity()
        self.assertIsInstance(activity_json, dict)
        self.assertEqual(activity_json["id"], shelf.remote_id)
        self.assertEqual(activity_json["totalItems"], 0)
        self.assertEqual(activity_json["type"], "Shelf")
        self.assertEqual(activity_json["name"], "Test Shelf")
        self.assertEqual(activity_json["owner"], self.local_user.remote_id)

    def test_create_update_shelf(self, *_):
        """create and broadcast shelf creation"""

        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            shelf = models.Shelf.objects.create(
                name="Test Shelf", identifier="test-shelf", user=self.local_user
            )
        activity = mock.call_args[0][0]
        self.assertEqual(activity["type"], "Create")
        self.assertEqual(activity["actor"], self.local_user.remote_id)
        self.assertEqual(activity["object"]["name"], "Test Shelf")

        shelf.name = "arthur russel"
        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            shelf.save()
        activity = mock.call_args[0][0]
        self.assertEqual(activity["type"], "Update")
        self.assertEqual(activity["actor"], self.local_user.remote_id)
        self.assertEqual(activity["object"]["name"], "arthur russel")
        self.assertEqual(shelf.name, "arthur russel")

    def test_shelve(self, *_):
        """create and broadcast shelf creation"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            shelf = models.Shelf.objects.create(
                name="Test Shelf", identifier="test-shelf", user=self.local_user
            )

        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            shelf_film = models.ShelfFilm.objects.create(
                shelf=shelf, user=self.local_user, film=self.film
            )
        self.assertEqual(mock.call_count, 1)
        activity = mock.call_args[0][0]
        self.assertEqual(activity["type"], "Add")
        self.assertEqual(activity["actor"], self.local_user.remote_id)
        self.assertEqual(activity["object"]["id"], shelf_film.remote_id)
        self.assertEqual(activity["target"], shelf.remote_id)
        self.assertEqual(shelf.films.first(), self.film)

        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            shelf_film.delete()
        self.assertEqual(mock.call_count, 1)
        activity = mock.call_args[0][0]
        self.assertEqual(activity["type"], "Remove")
        self.assertEqual(activity["actor"], self.local_user.remote_id)
        self.assertEqual(activity["object"]["id"], shelf_film.remote_id)
        self.assertEqual(activity["target"], shelf.remote_id)
        self.assertFalse(shelf.films.exists())

    def test_save_inherits_user_from_shelf(self, *_):
        """an instance without an explicit user gets the shelf's user"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            shelf = models.Shelf.objects.create(
                name="Test Shelf", identifier="test-shelf", user=self.local_user
            )

        shelf_film = models.ShelfFilm(shelf=shelf, film=self.film)
        shelf_film.save(broadcast=False)
        self.assertEqual(shelf_film.user, self.local_user)

    def test_save_without_user_or_shelf(self, *_):
        """a bare instance fails with a clear error, not an obscure one"""
        shelf_film = models.ShelfFilm(film=self.film)
        with self.assertRaises(ValueError):
            shelf_film.save(broadcast=False)
