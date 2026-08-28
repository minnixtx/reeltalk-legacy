"""style fixes and lookups for templates"""

from unittest.mock import patch

from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models
from reeltalk.templatetags import shelf_tags


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.remove_status_task.delay")
@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
class ShelfTags(TestCase):
    """lotta different things here"""

    @classmethod
    def setUpTestData(cls):
        """create some filler objects"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse@example.com",
                "mouse@mouse.mouse",
                "mouseword",
                local=True,
                localname="mouse",
            )
        with patch("reeltalk.models.user.set_remote_server.delay"):
            cls.remote_user = models.User.objects.create_user(
                "rat",
                "rat@rat.rat",
                "ratword",
                remote_id="http://example.com/rat",
                local=False,
            )
        cls.film = models.Film.objects.create(title="Test Film")

    def setUp(self):
        """test data"""
        self.factory = RequestFactory()

    def test_get_is_film_on_shelf(self, *_):
        """check if a film is on a shelf"""
        shelf = self.local_user.shelf_set.first()
        self.assertFalse(shelf_tags.get_is_film_on_shelf(self.film, shelf))
        models.ShelfFilm.objects.create(
            shelf=shelf, film=self.film, user=self.local_user
        )
        self.assertTrue(shelf_tags.get_is_film_on_shelf(self.film, shelf))

    def test_get_next_shelf(self, *_):
        """self progress helper"""
        self.assertEqual(shelf_tags.get_next_shelf("to-read"), "read")
        self.assertEqual(shelf_tags.get_next_shelf("read"), "complete")
        self.assertEqual(shelf_tags.get_next_shelf("blooooga"), "to-read")

    def test_active_shelf(self, *_):
        """get the shelf a film is on"""
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("")
        request.user = self.local_user
        context = {"request": request}
        self.assertIsInstance(shelf_tags.active_shelf(context, self.film), dict)
        models.ShelfFilm.objects.create(
            shelf=shelf, film=self.film, user=self.local_user
        )
        self.assertEqual(shelf_tags.active_shelf(context, self.film).shelf, shelf)
