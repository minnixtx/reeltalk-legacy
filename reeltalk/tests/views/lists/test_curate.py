"""test for app action functionality"""

from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.tests.validate_html import validate_html


class ListViews(TestCase):
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
        self.anonymous_user = AnonymousUser
        self.anonymous_user.is_authenticated = False

    def test_curate_page(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Curate.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=False,
                order=1,
            )

        result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        request.user = self.anonymous_user
        result = view(request, self.list.id)
        self.assertEqual(result.status_code, 302)

    def test_curate_approve(self):
        """approve a pending item"""
        view = views.Curate.as_view()
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            pending = models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=False,
                order=1,
            )

        request = self.factory.post(
            "",
            {"item": pending.id, "approved": "true"},
        )
        request.user = self.local_user

        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            view(request, self.list.id)

        self.assertEqual(mock.call_count, 2)
        activity = mock.call_args[0][0]
        self.assertEqual(activity["type"], "Add")
        self.assertEqual(activity["actor"], self.local_user.remote_id)
        self.assertEqual(activity["target"], self.list.remote_id)

        pending.refresh_from_db()
        self.assertEqual(self.list.films.count(), 1)
        self.assertEqual(self.list.listitem_set.first(), pending)
        self.assertTrue(pending.approved)

    def test_curate_reject(self):
        """reject a pending item"""
        view = views.Curate.as_view()
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=False,
                order=1,
            )

        request = self.factory.post(
            "",
            {
                "item": models.ListItem.objects.get().id,
                "approved": "false",
            },
        )
        request.user = self.local_user

        view(request, self.list.id)

        self.assertFalse(self.list.films.exists())
        self.assertFalse(models.ListItem.objects.exists())
