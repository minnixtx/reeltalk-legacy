"""style fixes and lookups for templates"""

import datetime
from unittest.mock import patch

from django.template.loader import render_to_string
from django.test import TestCase
from django.test.client import RequestFactory
from django.utils import timezone

from reeltalk import models
from reeltalk.templatetags import status_display


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.remove_status_task.delay")
class StatusDisplayTags(TestCase):
    """lotta different things here"""

    @classmethod
    def setUpTestData(cls):
        """create some filler objects"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.user = models.User.objects.create_user(
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

    def test_get_mentions(self, *_):
        """list of people mentioned"""
        status = models.Status.objects.create(content="hi", user=self.remote_user)
        result = status_display.get_mentions(status, self.user)
        self.assertEqual(result, "@rat@example.com ")

    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    def test_get_replies(self, *_):
        """direct replies to a status"""
        parent = models.Review.objects.create(
            user=self.user, film=self.film, content="hi"
        )
        first_child = models.Status.objects.create(
            reply_parent=parent, user=self.user, content="hi"
        )
        second_child = models.Status.objects.create(
            reply_parent=parent, user=self.user, content="hi"
        )
        third_child = models.Status.objects.create(
            reply_parent=parent,
            user=self.user,
            deleted=True,
            deleted_date=timezone.now(),
        )

        replies = status_display.get_replies(parent)
        self.assertEqual(len(replies), 2)
        self.assertTrue(first_child in replies)
        self.assertTrue(second_child in replies)
        self.assertFalse(third_child in replies)

    def test_get_parent(self, *_):
        """get the reply parent of a status"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            parent = models.Review.objects.create(
                user=self.user, film=self.film, content="hi"
            )
            child = models.Status.objects.create(
                reply_parent=parent, user=self.user, content="hi"
            )

        result = status_display.get_parent(child)
        self.assertEqual(result, parent)
        self.assertIsInstance(result, models.Review)

    def test_get_boosted(self, *_):
        """load a boosted status"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            status = models.Review.objects.create(
                user=self.remote_user, film=self.film
            )
            boost = models.Boost.objects.create(user=self.user, boosted_status=status)
        boosted = status_display.get_boosted(boost)
        self.assertIsInstance(boosted, models.Review)
        self.assertEqual(boosted, status)

    def test_get_published_date(self, *_):
        """date formatting"""
        date = datetime.datetime(2020, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
        with patch("django.utils.timezone.now") as timezone_mock:
            timezone_mock.return_value = datetime.datetime(
                2022, 1, 1, 0, 0, tzinfo=datetime.timezone.utc
            )
            result = status_display.get_published_date(date)
        self.assertEqual(result, "Jan. 1, 2020")

        date = datetime.datetime(2022, 1, 1, 0, 0, tzinfo=datetime.timezone.utc)
        with patch("django.utils.timezone.now") as timezone_mock:
            timezone_mock.return_value = datetime.datetime(
                2022, 1, 8, 0, 0, tzinfo=datetime.timezone.utc
            )
            result = status_display.get_published_date(date)
        self.assertEqual(result, "January 1")

        with patch("django.utils.timezone.now") as timezone_mock:
            timezone_mock.return_value = datetime.datetime(
                # reeltalk-social#3365: bug with exact month deltas
                2022,
                3,
                1,
                0,
                0,
                tzinfo=datetime.timezone.utc,
            )
            result = status_display.get_published_date(date)
        self.assertEqual(result, "January 1")

    def test_get_header_template_rating_forwards_request(self, *_):
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            rating = models.ReviewRating.objects.create(
                user=self.user, film=self.film, rating=3
            )
        request = RequestFactory().get("")
        request.user = self.user

        self.user.show_ratings = True
        shown = render_to_string(
            "snippets/status/header_content.html", {"status": rating}, request=request
        )
        self.assertNotIn("Show rating", shown)

        self.user.show_ratings = False
        hidden = render_to_string(
            "snippets/status/header_content.html", {"status": rating}, request=request
        )
        self.assertIn("Show rating", hidden)
