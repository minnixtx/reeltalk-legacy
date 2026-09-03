"""test for app action functionality"""

import json
from unittest.mock import patch
import pathlib
from django.http import Http404
from django.test import TestCase
from django.test.client import RequestFactory
import responses

from reeltalk import models, views
from reeltalk.settings import USER_AGENT, BASE_URL


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.suggested_users.rerank_user_task.delay")
class ViewsHelpers(TestCase):
    """viewing and creating statuses"""

    @classmethod
    def setUpTestData(cls):
        """we need basic test data and mocks"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
            patch("reeltalk.suggested_users.rerank_user_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse@local.com",
                "mouse@mouse.com",
                "mouseword",
                local=True,
                discoverable=True,
                localname="mouse",
                remote_id="https://example.com/users/mouse",
            )
        with (
            patch("reeltalk.models.user.set_remote_server.delay"),
            patch("reeltalk.suggested_users.rerank_user_task.delay"),
        ):
            cls.remote_user = models.User.objects.create_user(
                "rat",
                "rat@rat.com",
                "ratword",
                local=False,
                remote_id="https://example.com/users/rat",
                discoverable=True,
                inbox="https://example.com/users/rat/inbox",
                outbox="https://example.com/users/rat/outbox",
            )
        cls.film = models.Film.objects.create(
            title="Test Film",
            remote_id="https://example.com/film/1",
        )
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            cls.shelf = models.Shelf.objects.create(
                name="Test Shelf", identifier="test-shelf", user=cls.local_user
            )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()
        datafile = pathlib.Path(__file__).parent.joinpath("../data/ap_user.json")
        self.userdata = json.loads(datafile.read_bytes())
        del self.userdata["icon"]

    def test_get_film(self, *_):
        """given a film id, returns the film"""
        self.assertEqual(views.helpers.get_film(self.film.id), self.film)

    def test_get_mergeable_object_or_404_empty_id(self, *_):
        """an empty id 404s instead of matching every row in the absorbed lookup"""
        with self.assertRaises(Http404):
            views.helpers.get_mergeable_object_or_404(models.Film, None)
        with self.assertRaises(Http404):
            views.helpers.get_mergeable_object_or_404(models.Film, "")

    def test_get_user_from_username(self, *_):
        """works for either localname or username"""
        self.assertEqual(
            views.helpers.get_user_from_username(self.local_user, "mouse"),
            self.local_user,
        )
        self.assertEqual(
            views.helpers.get_user_from_username(self.local_user, "mouse@local.com"),
            self.local_user,
        )
        with self.assertRaises(Http404):
            views.helpers.get_user_from_username(self.local_user, "mojfse@example.com")

    def test_is_api_request(self, *_):
        """should it return html or json"""
        request = self.factory.get("/path")
        request.headers = {"Accept": "application/json"}
        self.assertTrue(views.helpers.is_api_request(request))

        request = self.factory.get("/path.json")
        request.headers = {"Accept": "Praise"}
        self.assertTrue(views.helpers.is_api_request(request))

        request = self.factory.get("/path")
        request.headers = {"Accept": "Praise"}
        self.assertFalse(views.helpers.is_api_request(request))

    def test_is_api_request_no_headers(self, *_):
        """should it return html or json"""
        request = self.factory.get("/path")
        self.assertFalse(views.helpers.is_api_request(request))

    def test_is_reeltalk_request(self, *_):
        """checks if a request came from a reeltalk instance"""
        request = self.factory.get("", {"q": "Test Film"})
        self.assertFalse(views.helpers.is_reeltalk_request(request))

        request = self.factory.get(
            "",
            {"q": "Test Film"},
            headers={
                "user-agent": "http.rb/4.4.1 (Mastodon/3.3.0; +https://mastodon.social/)",
            },
        )
        self.assertFalse(views.helpers.is_reeltalk_request(request))

        request = self.factory.get(
            "",
            {"q": "Test Film"},
            headers={
                "user-agent": USER_AGENT,
            },
        )
        self.assertTrue(views.helpers.is_reeltalk_request(request))

    def test_handle_remote_webfinger_invalid(self, *_):
        """Various ways you can send a bad query"""
        # if there's no query, there's no result
        result = views.helpers.handle_remote_webfinger(None)
        self.assertIsNone(result)

        # malformed user
        result = views.helpers.handle_remote_webfinger("noatsymbol")
        self.assertIsNone(result)

    def test_handle_remote_webfinger_existing_user(self, *_):
        """simple database lookup by username"""
        result = views.helpers.handle_remote_webfinger("@mouse@local.com")
        self.assertEqual(result, self.local_user)

        result = views.helpers.handle_remote_webfinger("mouse@local.com")
        self.assertEqual(result, self.local_user)

        result = views.helpers.handle_remote_webfinger("mOuSe@loCal.cOm")
        self.assertEqual(result, self.local_user)

    @responses.activate
    def test_handle_remote_webfinger_load_user_invalid_result(self, *_):
        """find a remote user using webfinger, but fail"""
        username = "mouse@example.com"
        responses.add(
            responses.GET,
            f"https://example.com/.well-known/webfinger?resource=acct:{username}",
            status=500,
        )
        result = views.helpers.handle_remote_webfinger("@mouse@example.com")
        self.assertIsNone(result)

    @responses.activate
    def test_handle_remote_webfinger_load_user(self, *_):
        """find a remote user using webfinger"""
        username = "mouse@example.com"
        wellknown = {
            "subject": "acct:mouse@example.com",
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": "https://example.com/user/mouse",
                }
            ],
        }
        responses.add(
            responses.GET,
            f"https://example.com/.well-known/webfinger?resource=acct:{username}",
            json=wellknown,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://example.com/user/mouse",
            json=self.userdata,
            status=200,
        )
        with patch("reeltalk.models.user.set_remote_server.delay"):
            result = views.helpers.handle_remote_webfinger("@mouse@example.com")
            self.assertIsInstance(result, models.User)
            self.assertEqual(result.username, "mouse@example.com")

    def test_handler_remote_webfinger_user_on_blocked_server(self, *_):
        """find a remote user using webfinger"""
        models.FederatedServer.objects.create(
            server_name="example.com", status="blocked"
        )

        result = views.helpers.handle_remote_webfinger("@mouse@example.com")
        self.assertIsNone(result)

    @responses.activate
    def test_subscribe_remote_webfinger(self, *_):
        """remote subscribe templates"""
        query = "mouse@example.com"
        response = {
            "subject": f"acct:{query}",
            "links": [
                {
                    "rel": "self",
                    "type": "application/activity+json",
                    "href": "https://example.com/user/mouse",
                    "template": "hi",
                },
                {
                    "rel": "http://ostatus.org/schema/1.0/subscribe",
                    "type": "application/activity+json",
                    "href": "https://example.com/user/mouse",
                    "template": "hello",
                },
            ],
        }
        responses.add(
            responses.GET,
            f"https://example.com/.well-known/webfinger?resource=acct:{query}",
            json=response,
            status=200,
        )
        template = views.helpers.subscribe_remote_webfinger(query)
        self.assertEqual(template, "hello")
        template = views.helpers.subscribe_remote_webfinger(f"@{query}")
        self.assertEqual(template, "hello")

    def test_handle_reading_status_to_read(self, *_):
        """posts shelve activities"""
        shelf = self.local_user.shelf_set.get(identifier="to-read")
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            views.helpers.handle_reading_status(
                self.local_user, shelf, self.film, "public"
            )
        status = models.GeneratedNote.objects.get()
        self.assertEqual(status.user, self.local_user)
        self.assertEqual(status.mention_films.first(), self.film)
        self.assertEqual(status.content, "wants to watch")

    def test_handle_reading_status_legacy_identifier(self, *_):
        """legacy shelf identifiers no longer generate notes"""
        # no local user has a "reading" shelf anymore, but remote instances
        # may still send them, so the helper ignores the identifier
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            shelf = models.Shelf.objects.create(
                name="Currently Reading",
                identifier="reading",
                user=self.local_user,
            )
        views.helpers.handle_reading_status(
            self.local_user, shelf, self.film, "public"
        )
        self.assertFalse(models.GeneratedNote.objects.exists())

    def test_handle_reading_status_read(self, *_):
        """finishing a film is silent: no generated note"""
        shelf = self.local_user.shelf_set.get(identifier="read")
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            views.helpers.handle_reading_status(
                self.local_user, shelf, self.film, "public"
            )
        self.assertFalse(models.GeneratedNote.objects.exists())

    def test_handle_reading_status_other(self, *_):
        """posts shelve activities"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            views.helpers.handle_reading_status(
                self.local_user, self.shelf, self.film, "public"
            )
        self.assertFalse(models.GeneratedNote.objects.exists())

    def test_redirect_to_referer_outside_domain(self, *_):
        """safely send people on their way"""
        request = self.factory.get(
            "/path",
            headers={
                "referer": "http://outside.domain/name",
            },
        )
        result = views.helpers.redirect_to_referer(
            request, "user-feed", self.local_user.localname
        )
        self.assertEqual(result.url, f"/user/{self.local_user.localname}")

    def test_redirect_to_referer_outside_domain_with_fallback(self, *_):
        """invalid domain with regular params for the redirect function"""
        request = self.factory.get(
            "/path",
            headers={
                "referer": "http://outside.domain/name",
            },
        )
        result = views.helpers.redirect_to_referer(request)
        self.assertEqual(result.url, "/")

    def test_redirect_to_referer_valid_domain(self, *_):
        """redirect to within the app"""
        request = self.factory.get(
            "/path",
            headers={
                "referer": f"{BASE_URL}/and/a/path",
            },
        )
        result = views.helpers.redirect_to_referer(request)
        self.assertEqual(result.url, f"{BASE_URL}/and/a/path")

    def test_redirect_to_referer_with_get_args(self, *_):
        """if the path has get params (like sort) they are preserved"""
        request = self.factory.get(
            "/path",
            headers={
                "referer": f"{BASE_URL}/and/a/path?sort=hello",
            },
        )
        result = views.helpers.redirect_to_referer(request)
        self.assertEqual(result.url, f"{BASE_URL}/and/a/path?sort=hello")
