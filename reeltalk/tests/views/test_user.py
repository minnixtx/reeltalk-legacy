"""test for app action functionality"""

import datetime
import json
import pathlib
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http.response import Http404
from django.template.response import TemplateResponse
from django.test import Client, TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.activitypub import ActivitypubResponse
from reeltalk.tests.validate_html import validate_html
from reeltalk.settings import BASE_URL


def make_date(*args):
    """helper function to easily generate a date obj"""
    return datetime.datetime(*args, tzinfo=datetime.timezone.utc)


class UserViews(TestCase):
    """view user and edit profile"""

    @classmethod
    def setUpTestData(cls):
        """we need basic test data and mocks"""
        cls.local_user = models.User.objects.create_user(
            "mouse@local.com",
            "mouse@mouse.mouse",
            "password",
            local=True,
            localname="mouse",
        )
        cls.rat = models.User.objects.create_user(
            "rat@local.com", "rat@rat.rat", "password", local=True, localname="rat"
        )
        cls.film = models.Film.objects.create(title="test")
        cls.another_film = models.Film.objects.create(title="test 2")
        cls.film_recently_shelved = models.Film.objects.create(title="recently shelved")
        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.add_film_statuses_task.delay"),
        ):
            models.ShelfFilm.objects.create(
                film=cls.film,
                user=cls.local_user,
                shelf=cls.local_user.shelf_set.get(identifier="to-read"),
                shelved_date=make_date(2020, 10, 21),
            )

            models.ShelfFilm.objects.create(
                film=cls.film_recently_shelved,
                user=cls.local_user,
                shelf=cls.local_user.shelf_set.get(identifier="to-read"),
                shelved_date=make_date(2024, 7, 1),
            )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()
        self.anonymous_user = AnonymousUser
        self.anonymous_user.is_authenticated = False

    def test_user_page(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.User.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="mouse")
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        request.user = self.anonymous_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="mouse")
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, username="mouse")
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

    def test_user_page_activitypub(self):
        """Make sure the avatar is rendered correctly in the activity"""
        avatar_path = pathlib.Path(__file__).parent.joinpath(
            "../../static/images/default_avi.jpg"
        )
        with open(avatar_path, "rb") as avatar_file:
            self.local_user.avatar.save("mouse-avatar.jpg", avatar_file)
        view = views.User.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, username="mouse")
        activity = json.loads(result.content)
        self.assertEqual(
            activity["icon"],
            {
                "type": "Image",
                "url": f"{BASE_URL}{self.local_user.avatar.url}",
                "name": "avatar for mouse",
                "@context": [
                    "https://www.w3.org/ns/activitystreams",
                    {"Hashtag": "as:Hashtag"},
                ],
            },
        )

    def test_user_page_domain(self):
        """when the user domain has dashes in it"""
        with patch("reeltalk.models.user.set_remote_server"):
            models.User.objects.create_user(
                "nutria",
                "",
                "nutriaword",
                local=False,
                remote_id="https://ex--ample.co----m/users/nutria",
                inbox="https://ex--ample.co----m/users/nutria/inbox",
                outbox="https://ex--ample.co----m/users/nutria/outbox",
            )

        view = views.User.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="nutria@ex--ample.co----m")
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_user_page_blocked(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.User.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        self.rat.blocks.add(self.local_user)
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            with self.assertRaises(Http404):
                view(request, username="rat")

    def test_user_page_private(self):
        models.User.objects.filter(id=self.rat.id).update(is_profile_private=True)
        view = views.User.as_view()
        request = self.factory.get("")

        request.user = self.anonymous_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="rat")
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)
        self.assertTrue(result.context_data["is_profile_locked"])

        request.user = self.local_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="rat")
        self.assertTrue(result.context_data["is_profile_locked"])

        self.rat.followers.add(self.local_user)
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="rat")
        self.assertFalse(result.context_data["is_profile_locked"])

    def test_reviews_comments_private(self):
        models.User.objects.filter(id=self.local_user.id).update(
            is_profile_private=True
        )
        view = views.UserReviewsComments.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user
        result = view(request, username=self.local_user.localname)
        self.assertTrue(result.context_data["is_profile_locked"])

    def test_followers_page_private(self):
        models.User.objects.filter(id=self.local_user.id).update(
            is_profile_private=True
        )
        view = views.Relationships.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user
        result = view(
            request, username=self.local_user.localname, direction="followers"
        )
        self.assertTrue(result.context_data["is_profile_locked"])

    def test_user_page_activity_sorted(self):
        """the most recently shelved film should be displayed first"""
        view = views.User.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="mouse")

        self.assertIsInstance(result, TemplateResponse)
        self.assertEqual(result.status_code, 200)

        first_shelf = result.context_data["shelves"][0]
        first_film = first_shelf["films"][0]

        self.assertEqual(first_film, self.film_recently_shelved)

    def test_followers_page(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Relationships.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="mouse", direction="followers")

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_followers_page_ap(self):
        """JSON response"""
        view = views.Relationships.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.relationships.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, username="mouse", direction="followers")

        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

    def test_followers_page_anonymous(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Relationships.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="mouse", direction="followers")

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_user_page_remote_anonymous(self):
        """when a anonymous user tries to get a remote user"""
        with patch("reeltalk.models.user.set_remote_server"):
            models.User.objects.create_user(
                "nutria",
                "",
                "nutriaword",
                local=False,
                remote_id="https://example.com/users/nutria",
                inbox="https://example.com/users/nutria/inbox",
                outbox="https://example.com/users/nutria/outbox",
            )

        view = views.User.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="nutria@example.com")
        result.client = Client()
        self.assertRedirects(
            result, "https://example.com/users/nutria", fetch_redirect_response=False
        )

    @patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
    @patch("reeltalk.activitystreams.populate_stream_task.delay")
    def test_followers_page_blocked(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Relationships.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        self.rat.blocks.add(self.local_user)
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            with self.assertRaises(Http404):
                view(request, username="rat", direction="followers")

    def test_following_page(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Relationships.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="mouse", direction="following")

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_following_page_json(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Relationships.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.relationships.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, username="mouse", direction="following")

        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

    def test_following_page_anonymous(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Relationships.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username="mouse", direction="following")

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_following_page_blocked(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Relationships.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        self.rat.blocks.add(self.local_user)
        with patch("reeltalk.views.user.is_api_request") as is_api:
            is_api.return_value = False
            with self.assertRaises(Http404):
                view(request, username="rat", direction="following")

    def test_hide_suggestions(self):
        """update suggestions settings"""
        self.assertTrue(self.local_user.show_suggested_users)
        request = self.factory.post("")
        request.user = self.local_user

        result = views.hide_suggestions(request)
        self.assertEqual(result.status_code, 302)

        self.local_user.refresh_from_db()
        self.assertFalse(self.local_user.show_suggested_users)

    def test_user_redirect(self):
        """test the basic redirect"""
        request = self.factory.get("@mouse")
        request.user = self.anonymous_user
        result = views.user_redirect(request, "mouse")

        self.assertEqual(result.status_code, 302)

    def test_reviews_comments_page(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.UserReviewsComments.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request, username="mouse")
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        request.user = self.anonymous_user
        result = view(request, username="mouse")
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)
