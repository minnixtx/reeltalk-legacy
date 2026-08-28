"""test for app action functionality"""

from unittest.mock import patch

from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views


class ListItemViews(TestCase):
    """list view"""

    @classmethod
    def setUpTestData(cls):
        """we need basic test data and mocks"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse@local.com",
                "mouse@mouse.com",
                "mouseword",
                local=True,
                localname="mouse",
                remote_id="https://example.com/users/mouse",
            )
        cls.film = models.Film.objects.create(
            title="Example Film",
            remote_id="https://example.com/film/1",
        )
        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.lists_stream.remove_list_task.delay"),
        ):
            cls.list = models.List.objects.create(name="Test List", user=cls.local_user)

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    def test_add_list_item_notes(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.ListItem.as_view()
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            item = models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=True,
                order=1,
            )
        request = self.factory.post(
            "",
            {
                "film_list": self.list.id,
                "film": self.film.id,
                "user": self.local_user.id,
                "notes": "beep boop",
            },
        )
        request.user = self.local_user
        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            view(request, self.list.id, item.id)
        self.assertEqual(mock.call_count, 1)

        item.refresh_from_db()
        self.assertEqual(item.notes, "<p>beep boop</p>")
        self.assertEqual(item.raw_notes, "beep boop")
