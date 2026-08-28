"""test for app action functionality"""

import json
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.settings import BASE_URL, DOMAIN
from reeltalk.tests.validate_html import validate_html


class Views(TestCase):
    """search views"""

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
            title="Test Film",
            remote_id="https://example.com/film/1",
        )

        cls.site = models.SiteSettings.get()

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    def test_search_json_response(self):
        """searches local films and returns film data in json format"""
        view = views.Search.as_view()
        request = self.factory.get("", {"q": "Test Film"})
        with patch("reeltalk.views.search.is_api_request") as is_api:
            is_api.return_value = True
            response = view(request)
        self.assertIsInstance(response, JsonResponse)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["title"], "Test Film")
        self.assertEqual(data[0]["key"], f"{BASE_URL}/film/{self.film.id}")

    def test_search_no_query(self):
        """just the search page"""
        view = views.Search.as_view()
        request = self.factory.get("")
        with patch("reeltalk.views.search.is_api_request") as is_api:
            is_api.return_value = False
            response = view(request)
        self.assertIsInstance(response, TemplateResponse)
        validate_html(response.render())

    def test_search_films(self):
        """searches the local film database"""
        view = views.Search.as_view()
        request = self.factory.get("", {"q": "Test Film"})
        request.user = self.local_user
        with patch("reeltalk.views.search.is_api_request") as is_api:
            is_api.return_value = False
            response = view(request)

        self.assertIsInstance(response, TemplateResponse)
        validate_html(response.render())

        local_results = response.context_data["results"]
        self.assertEqual(local_results.object_list[0].title, "Test Film")

    def test_search_films_extra_whitespace(self):
        """just the search page"""
        view = views.Search.as_view()
        request = self.factory.get("", {"q": " Test Film "})
        request.user = self.local_user
        with patch("reeltalk.views.search.is_api_request") as is_api:
            is_api.return_value = False
            response = view(request)
        self.assertIsInstance(response, TemplateResponse)
        validate_html(response.render())

        local_results = response.context_data["results"]
        self.assertEqual(local_results.object_list[0].title, "Test Film")

    def test_search_films_anonymous(self):
        """logged out users can search local films"""
        view = views.Search.as_view()
        request = self.factory.get("", {"q": "Test Film"})

        anonymous_user = AnonymousUser
        anonymous_user.is_authenticated = False
        request.user = anonymous_user
        with patch("reeltalk.views.search.is_api_request") as is_api:
            is_api.return_value = False
            response = view(request)

        self.assertIsInstance(response, TemplateResponse)
        validate_html(response.render())

        local_results = response.context_data["results"]
        self.assertEqual(local_results.object_list[0].title, "Test Film")

    def test_search_users(self):
        """searches users"""
        view = views.Search.as_view()
        request = self.factory.get("", {"q": "mouse", "type": "user"})
        request.user = self.local_user
        response = view(request)

        self.assertIsInstance(response, TemplateResponse)
        validate_html(response.render())
        self.assertEqual(response.context_data["results"][0], self.local_user)

    def test_search_users_extra_whitespace(self):
        """searches users"""
        view = views.Search.as_view()
        request = self.factory.get("", {"q": " mouse ", "type": "user"})
        request.user = self.local_user
        response = view(request)

        self.assertIsInstance(response, TemplateResponse)
        validate_html(response.render())
        self.assertEqual(response.context_data["results"][0], self.local_user)

    def test_search_users_logged_out(self):
        """searches users"""
        view = views.Search.as_view()
        request = self.factory.get("", {"q": "mouse", "type": "user"})

        anonymous_user = AnonymousUser
        anonymous_user.is_authenticated = False
        request.user = anonymous_user

        response = view(request)

        validate_html(response.render())
        self.assertTrue("results" in response.context_data)

    def test_search_lists(self):
        """searches lists"""
        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.lists_stream.remove_list_task.delay"),
        ):
            filmlist = models.List.objects.create(
                user=self.local_user, name="test list"
            )
        view = views.Search.as_view()
        request = self.factory.get("", {"q": "test", "type": "list"})
        request.user = self.local_user
        response = view(request)

        self.assertIsInstance(response, TemplateResponse)
        validate_html(response.render())
        self.assertEqual(response.context_data["results"][0], filmlist)

    def test_search_lists_extra_whitespace(self):
        """searches lists"""
        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.lists_stream.remove_list_task.delay"),
        ):
            filmlist = models.List.objects.create(
                user=self.local_user, name="test list"
            )
        view = views.Search.as_view()
        request = self.factory.get("", {"q": " test ", "type": "list"})
        request.user = self.local_user
        response = view(request)

        self.assertIsInstance(response, TemplateResponse)
        validate_html(response.render())
        self.assertEqual(response.context_data["results"][0], filmlist)

    def test_block_incoming_search(self):
        """disallow search endpoint"""

        response = self.client.get(
            "/search/?q=beep",
            headers={
                "Host": DOMAIN,
                "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
        )
        self.assertEqual(response.status_code, 200)

        self.site.block_incoming_search = True
        self.site.save(update_fields=["block_incoming_search"])

        response = self.client.get(
            "/search/?q=boop",
            headers={
                "Host": DOMAIN,
                "Accept": 'application/ld+json; profile="https://www.w3.org/ns/activitystreams"',
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_search_films_blocked_film(self):
        """don't return blocked films on search"""

        self.local_user.blocked_films.add(self.film)

        view = views.Search.as_view()
        request = self.factory.get("", {"q": "Test Film"})
        request.user = self.local_user
        with patch("reeltalk.views.search.is_api_request") as is_api:
            is_api.return_value = False
            response = view(request)
        self.assertIsInstance(response, TemplateResponse)
        validate_html(response.render())

        self.assertEqual(response.context_data["blocked_films_excluded"], True)
        self.assertEqual(len(response.context_data["results"]), 0)
