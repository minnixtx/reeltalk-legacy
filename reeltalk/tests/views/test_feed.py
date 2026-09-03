"""test for app action functionality"""

from unittest.mock import patch
import pathlib

from django.http import Http404
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import forms, models, views
from reeltalk.activitypub import ActivitypubResponse
from reeltalk.tests.validate_html import validate_html


@patch("reeltalk.activitystreams.ActivityStream.get_activity_stream")
@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.lists_stream.populate_lists_task.delay")
@patch("reeltalk.suggested_users.remove_user_task.delay")
class FeedViews(TestCase):
    """activity feed, statuses, dms"""

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
            cls.another_user = models.User.objects.create_user(
                "nutria@local.com",
                "nutria@nutria.nutria",
                "password",
                local=True,
                localname="nutria",
            )
        cls.film = models.Film.objects.create(
            title="Example Film",
            remote_id="https://example.com/film/1",
        )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    @patch("reeltalk.suggested_users.SuggestedUsers.get_suggestions")
    def test_feed(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Feed.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request, "home")
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    @patch("reeltalk.suggested_users.SuggestedUsers.get_suggestions")
    def test_save_feed_settings(self, *_):
        """update display preferences"""
        self.assertEqual(
            self.local_user.feed_status_types,
            ["review", "comment", "everything"],
        )
        view = views.Feed.as_view()
        form = forms.FeedStatusTypesForm(instance=self.local_user)
        form.data["feed_status_types"] = "review"
        request = self.factory.post("", form.data)
        request.user = self.local_user

        result = view(request, "home")

        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, "/home")
        self.local_user.refresh_from_db()
        self.assertEqual(self.local_user.feed_status_types, ["review"])

    @patch("reeltalk.suggested_users.SuggestedUsers.get_suggestions")
    def test_feed_shows_filters_applied_badge(self, *_):
        self.local_user.feed_status_types = ["review"]
        view = views.Feed.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        result = view(request, "home")

        self.assertContains(result, "Filters are applied")

    def test_status_page(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Status.as_view()
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            status = models.Status.objects.create(content="hi", user=self.local_user)
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.feed.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, "mouse", status.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        with patch("reeltalk.views.feed.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, "mouse", status.id)
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

    def test_status_page_not_found(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Status.as_view()

        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.feed.is_api_request") as is_api:
            is_api.return_value = False
            with self.assertRaises(Http404):
                view(request, "mouse", 12345)

    def test_status_page_not_found_wrong_user(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Status.as_view()
        another_user = models.User.objects.create_user(
            "rat@local.com",
            "rat@rat.rat",
            "password",
            local=True,
            localname="rat",
        )
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            status = models.Status.objects.create(content="hi", user=another_user)

        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.feed.is_api_request") as is_api:
            is_api.return_value = False
            with self.assertRaises(Http404):
                view(request, "mouse", status.id)

    def test_status_page_with_image(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Status.as_view()

        image_path = pathlib.Path(__file__).parent.joinpath(
            "../../static/images/default_avi.jpg"
        )
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            status = models.Review.objects.create(
                content="hi",
                user=self.local_user,
                film=self.film,
            )
            attachment = models.Image.objects.create(
                status=status, caption="alt text here"
            )
            with open(image_path, "rb") as image_file:
                attachment.image.save("test.jpg", image_file)

        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.feed.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, "mouse", status.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        with patch("reeltalk.views.feed.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, "mouse", status.id)
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

    def test_replies_page(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Replies.as_view()
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            status = models.Status.objects.create(content="hi", user=self.local_user)
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.feed.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, "mouse", status.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        with patch("reeltalk.views.feed.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, "mouse", status.id)
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

    def test_direct_messages_page(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.DirectMessage.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_direct_messages_page_user(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.DirectMessage.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request, "nutria")
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.context_data["partner"], self.another_user)

    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    @patch("reeltalk.activitystreams.add_film_statuses_task.delay")
    def test_get_suggested_film(self, *_):
        """gets films the ~*~ algorithm ~*~ thinks you want to post about"""
        models.ShelfFilm.objects.create(
            film=self.film,
            user=self.local_user,
            shelf=self.local_user.shelf_set.get(identifier="to-read"),
        )
        suggestions = views.feed.get_suggested_films(self.local_user)
        self.assertEqual(suggestions[0]["name"], "Watchlist")
        self.assertEqual(suggestions[0]["films"][0], self.film)

    def test_get_suggested_film_filters_blocked(self, *_):
        """gets films you're interested in minus films you definitely don't want to see"""

        models.ShelfFilm.objects.create(
            film=self.film,
            user=self.local_user,
            shelf=self.local_user.shelf_set.get(identifier="to-read"),
        )

        awful_film = models.Film.objects.create(
            title="This film is very bad",
            remote_id="https://example.com/film/99",
        )

        self.local_user.blocked_films.add(awful_film)

        models.ShelfFilm.objects.create(
            film=awful_film,
            user=self.local_user,
            shelf=self.local_user.shelf_set.get(identifier="to-read"),
        )

        suggestions = views.feed.get_suggested_films(self.local_user)
        self.assertEqual(suggestions[0]["name"], "Watchlist")
        self.assertEqual(suggestions[0]["films"][0], self.film)
        self.assertTrue(awful_film not in list(suggestions[0]["films"]))
