"""test for app action functionality"""

from unittest.mock import patch
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.tests.validate_html import validate_html


class DiscoverViews(TestCase):
    """pages you land on without really trying"""

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
                "mouse@mouse.mouse",
                "password",
                local=True,
                localname="mouse",
            )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()
        self.anonymous_user = AnonymousUser
        self.anonymous_user.is_authenticated = False

    def test_discover_page_empty(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Discover.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch(
            "reeltalk.activitystreams.ActivityStream.get_activity_stream"
        ) as mock:
            result = view(request)
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(result.status_code, 200)
        validate_html(result.render())

    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    @patch("reeltalk.activitystreams.add_status_task.delay")
    def test_discover_page_with_posts(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Discover.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        # a distinct film per status: the discover page renders one finish
        # modal per film tile and reusing a film would duplicate its ids
        films = [models.Film.objects.create(title=f"hi {i}") for i in range(3)]

        models.ReviewRating.objects.create(
            film=films[0],
            user=self.local_user,
            rating=4,
        )
        models.Review.objects.create(
            film=films[1],
            user=self.local_user,
            content="hello",
            rating=4,
        )
        models.Comment.objects.create(
            film=films[2],
            user=self.local_user,
            content="hello",
        )
        models.Status.objects.create(user=self.local_user, content="beep")

        with patch(
            "reeltalk.activitystreams.ActivityStream.get_activity_stream"
        ) as mock:
            mock.return_value = models.Status.objects.select_subclasses().all()
            result = view(request)
        self.assertEqual(mock.call_count, 1)
        self.assertEqual(result.status_code, 200)
        validate_html(result.render())

    def test_discover_page_logged_out(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Discover.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user
        result = view(request)
        self.assertEqual(result.status_code, 302)
