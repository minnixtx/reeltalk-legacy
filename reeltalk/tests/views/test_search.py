"""test for app action functionality"""

import json
from unittest.mock import patch

import responses
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.test import TestCase, override_settings
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

    @override_settings(TMDB_API_KEY="")
    def test_search_films(self):
        """searches the local film database when TMDB is not configured"""
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

    @override_settings(TMDB_API_KEY="")
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

    @override_settings(TMDB_API_KEY="")
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

    @override_settings(TMDB_API_KEY="")
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


TMDB_SEARCH_PAYLOAD = {
    "results": [
        {
            "id": 78,
            "title": "Blade Runner",
            "release_date": "1982-06-25",
            "poster_path": "/br.jpg",
        },
        {
            "id": 335984,
            "title": "Blade Runner 2049",
            "release_date": "2017-09-20",
            "poster_path": None,
        },
    ],
    "total_results": 2,
    "total_pages": 1,
}

TMDB_DETAILS_PAYLOAD = {
    "id": 78,
    "title": "Blade Runner",
    "release_date": "1982-06-25",
    "runtime": 117,
    "overview": "A blade runner must track down and retire four replicants.",
    "genres": [{"id": 878, "name": "Science Fiction"}],
    "poster_path": "/br.jpg",
    "credits": {
        "crew": [{"name": "Ridley Scott", "job": "Director"}],
        "cast": [{"name": "Harrison Ford"}],
    },
}

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_DETAILS_URL = "https://api.themoviedb.org/3/movie/78"
TMDB_POSTER_URL = "https://image.tmdb.org/t/p/w500/br.jpg"


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
class TmdbSearchViews(TestCase):
    """global film search against TMDB, click-through, watchlist action"""

    @classmethod
    def setUpTestData(cls):
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
        cls.want_shelf = models.Shelf.objects.get(
            identifier=models.Shelf.TO_READ, user=cls.local_user
        )

    def search_get(self, extra=None):
        params = {"q": "blade runner", "type": "film"}
        if extra:
            params.update(extra)
        return self.client.get("/search/", params)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_tmdb_search_renders_results(self, *_):
        """a configured instance searches TMDB and renders the hits"""
        responses.add(responses.GET, TMDB_SEARCH_URL, json=TMDB_SEARCH_PAYLOAD, status=200)
        self.client.force_login(self.local_user)
        response = self.search_get()

        validate_html(response)
        content = response.content.decode()
        self.assertIn("Blade Runner", content)
        self.assertIn("Blade Runner 2049", content)
        self.assertIn("(1982)", content)
        self.assertIn(TMDB_POSTER_URL, content)
        # a hit without a local match links to the click-through route
        self.assertIn("/search/film/335984/", content)
        self.assertIn("Add to Watchlist", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_tmdb_search_local_match_links_film_page(self, *_):
        """a hit already in the library links straight to the film page"""
        responses.add(responses.GET, TMDB_SEARCH_URL, json=TMDB_SEARCH_PAYLOAD, status=200)
        film = models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        self.client.force_login(self.local_user)
        response = self.search_get()

        content = response.content.decode()
        self.assertIn(film.local_path, content)
        self.assertIn("In your library", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_tmdb_search_anonymous_sees_results_without_add(self, *_):
        """anonymous users get results but no watchlist action"""
        responses.add(responses.GET, TMDB_SEARCH_URL, json=TMDB_SEARCH_PAYLOAD, status=200)
        response = self.search_get()

        content = response.content.decode()
        self.assertIn("Blade Runner", content)
        self.assertNotIn("Add to Watchlist", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_tmdb_search_watchlist_state(self, *_):
        """a hit already on the user's watchlist shows its state"""
        responses.add(responses.GET, TMDB_SEARCH_URL, json=TMDB_SEARCH_PAYLOAD, status=200)
        film = models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        models.ShelfFilm.objects.create(
            film=film, shelf=self.want_shelf, user=self.local_user
        )
        self.client.force_login(self.local_user)
        response = self.search_get()

        content = response.content.decode()
        self.assertIn("On your watchlist", content)
        # only the unmatched row still offers the add button
        self.assertEqual(content.count("Add to Watchlist"), 1)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_tmdb_search_excludes_blocked_local_match(self, *_):
        """a locally blocked film is dropped from the TMDB results"""
        responses.add(responses.GET, TMDB_SEARCH_URL, json=TMDB_SEARCH_PAYLOAD, status=200)
        film = models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        self.local_user.blocked_films.add(film)
        self.client.force_login(self.local_user)
        response = self.search_get()

        content = response.content.decode()
        self.assertNotIn(film.local_path, content)
        self.assertIn("Blade Runner 2049", content)
        self.assertTrue(response.context["blocked_films_excluded"])

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_tmdb_search_error(self, *_):
        """a TMDB failure shows a user-facing error"""
        responses.add(responses.GET, TMDB_SEARCH_URL, json={}, status=429)
        self.client.force_login(self.local_user)
        response = self.search_get()

        content = response.content.decode()
        self.assertIn("rate limit", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_clickthrough_creates_film(self, *_):
        """clicking an unmatched hit creates the local film and opens it"""
        responses.add(responses.GET, TMDB_DETAILS_URL, json=TMDB_DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, TMDB_POSTER_URL, body=b"jpeg", status=200)
        response = self.client.get("/search/film/78/")

        self.assertEqual(response.status_code, 302)
        film = models.Film.objects.get(tmdb_id="78")
        self.assertURLEqual(response.url, film.local_path)
        self.assertEqual(film.year, 1982)
        self.assertEqual(film.directors, ["Ridley Scott"])
        self.assertTrue(film.poster)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_clickthrough_existing_film_no_duplicate(self, *_):
        """clicking a hit that is already in the library creates no duplicate"""
        film = models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        responses.add(responses.GET, TMDB_DETAILS_URL, json=TMDB_DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, TMDB_POSTER_URL, body=b"jpeg", status=200)
        response = self.client.get("/search/film/78/")

        self.assertEqual(models.Film.objects.count(), 1)
        self.assertURLEqual(response.url, film.local_path)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_clickthrough_backfills_manual_film(self, *_):
        """a manually created film matching title + year is backfilled, not duplicated"""
        manual = models.Film.objects.create(title="Blade Runner", year=1982)
        responses.add(responses.GET, TMDB_DETAILS_URL, json=TMDB_DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, TMDB_POSTER_URL, body=b"jpeg", status=200)
        response = self.client.get("/search/film/78/")

        self.assertEqual(models.Film.objects.count(), 1)
        manual.refresh_from_db()
        self.assertEqual(manual.tmdb_id, "78")
        self.assertEqual(manual.genres, ["Science Fiction"])
        self.assertURLEqual(response.url, manual.local_path)

    @override_settings(TMDB_API_KEY="test-key")
    def test_watchlist_add_requires_login(self, *_):
        """anonymous users are sent to the login page"""
        response = self.client.post("/search/film/78/watchlist/", {"return_to": "/"})
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_watchlist_add_creates_film_and_shelves(self, *_):
        """one click creates the film and shelves it on the Watchlist"""
        responses.add(responses.GET, TMDB_DETAILS_URL, json=TMDB_DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, TMDB_POSTER_URL, body=b"jpeg", status=200)
        self.client.force_login(self.local_user)
        response = self.client.post(
            "/search/film/78/watchlist/",
            {
                "return_to": "/search/?q=blade+runner&type=film",
                "title": "Blade Runner",
                "year": "1982",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, "/search/?q=blade+runner&type=film")
        film = models.Film.objects.get(tmdb_id="78")
        self.assertTrue(
            models.ShelfFilm.objects.filter(film=film, shelf=self.want_shelf).exists()
        )

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_watchlist_add_duplicate_is_a_noop(self, *_):
        """adding a film that is already on the watchlist creates no duplicate"""
        film = models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        models.ShelfFilm.objects.create(
            film=film, shelf=self.want_shelf, user=self.local_user
        )
        responses.add(responses.GET, TMDB_DETAILS_URL, json=TMDB_DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, TMDB_POSTER_URL, body=b"jpeg", status=200)
        self.client.force_login(self.local_user)
        response = self.client.post(
            "/search/film/78/watchlist/",
            {"return_to": "/", "title": "Blade Runner", "year": "1982"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertURLEqual(response.url, "/")
        self.assertEqual(
            models.ShelfFilm.objects.filter(film=film, shelf=self.want_shelf).count(),
            1,
        )

    @override_settings(TMDB_API_KEY="test-key")
    def test_watchlist_add_remote_user_denied(self, *_):
        """federated users can't use the local watchlist action"""
        with patch("reeltalk.models.user.set_remote_server"):
            remote = models.User.objects.create_user(
                "rat",
                "rat@email.com",
                "ratword",
                local=False,
                remote_id="https://example.com/users/rat",
                inbox="https://example.com/users/rat/inbox",
                outbox="https://example.com/users/rat/outbox",
            )
        self.client.force_login(remote)
        response = self.client.post("/search/film/78/watchlist/", {"return_to": "/"})
        self.assertEqual(response.status_code, 403)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_watchlist_add_tmdb_error_redirects_with_error(self, *_):
        """a TMDB failure bounces back to the grid with a user-facing error"""
        responses.add(responses.GET, TMDB_DETAILS_URL, json={}, status=429)
        responses.add(responses.GET, TMDB_SEARCH_URL, json={}, status=429)
        self.client.force_login(self.local_user)
        response = self.client.post(
            "/search/film/78/watchlist/",
            {
                "return_to": "/search/?q=blade+runner&type=film",
                "title": "Blade Runner",
                "year": "1982",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("error=", response.url)
        follow = self.client.get(response.url)
        self.assertIn("rate limit", follow.content.decode())


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
class FilmSuggestViews(TestCase):
    """search-as-you-type JSON suggestions (decision 28)"""

    @classmethod
    def setUpTestData(cls):
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

    def suggest_get(self, q, search_type="film"):
        return self.client.get("/search/suggest/", {"q": q, "type": search_type})

    @override_settings(TMDB_API_KEY="test-key")
    def test_suggest_anonymous_empty(self, *_):
        """anonymous users get no suggestions and no TMDB call"""
        with patch("reeltalk.views.search.tmdb.search_films") as search_films:
            response = self.suggest_get("blade")

        data = json.loads(response.content)
        self.assertEqual(data["results"], [])
        search_films.assert_not_called()

    @override_settings(TMDB_API_KEY="test-key")
    def test_suggest_short_query_empty(self, *_):
        """queries under two characters return nothing without calling TMDB"""
        self.client.force_login(self.local_user)
        with patch("reeltalk.views.search.tmdb.search_films") as search_films:
            response = self.suggest_get("b")

        data = json.loads(response.content)
        self.assertEqual(data["results"], [])
        search_films.assert_not_called()

    @override_settings(TMDB_API_KEY="test-key")
    def test_suggest_wrong_type_empty(self, *_):
        """only film suggestions are supported"""
        self.client.force_login(self.local_user)
        with patch("reeltalk.views.search.tmdb.search_films") as search_films:
            response = self.suggest_get("blade", search_type="user")

        data = json.loads(response.content)
        self.assertEqual(data["results"], [])
        search_films.assert_not_called()

    @override_settings(TMDB_API_KEY="test-key")
    def test_suggest_remote_user_empty(self, *_):
        """federated users get no suggestions and no TMDB call"""
        with patch("reeltalk.models.user.set_remote_server"):
            remote = models.User.objects.create_user(
                "rat",
                "rat@email.com",
                "ratword",
                local=False,
                remote_id="https://example.com/users/rat",
                inbox="https://example.com/users/rat/inbox",
                outbox="https://example.com/users/rat/outbox",
            )
        self.client.force_login(remote)
        with patch("reeltalk.views.search.tmdb.search_films") as search_films:
            response = self.suggest_get("blade")

        data = json.loads(response.content)
        self.assertEqual(data["results"], [])
        search_films.assert_not_called()

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_suggest_tmdb_rows(self, *_):
        """configured instances suggest TMDB hits with the right link targets"""
        responses.add(responses.GET, TMDB_SEARCH_URL, json=TMDB_SEARCH_PAYLOAD, status=200)
        film = models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        self.client.force_login(self.local_user)
        response = self.suggest_get("blade runner")

        data = json.loads(response.content)
        self.assertEqual(len(data["results"]), 2)
        first, second = data["results"]
        # a local match links straight to the film page
        self.assertEqual(first["title"], "Blade Runner")
        self.assertEqual(first["year"], 1982)
        self.assertEqual(first["poster"], TMDB_POSTER_URL)
        self.assertEqual(first["url"], film.local_path)
        # an unmatched hit links to the click-through route
        self.assertEqual(second["title"], "Blade Runner 2049")
        self.assertIsNone(second["poster"])
        self.assertEqual(second["url"], "/search/film/335984")

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_suggest_tmdb_caps_at_eight(self, *_):
        """only the top eight hits of page one are suggested"""
        payload = {
            "results": [
                {
                    "id": i,
                    "title": f"Film {i}",
                    "release_date": "2000-01-01",
                    "poster_path": None,
                }
                for i in range(10)
            ],
            "total_results": 10,
            "total_pages": 1,
        }
        responses.add(responses.GET, TMDB_SEARCH_URL, json=payload, status=200)
        self.client.force_login(self.local_user)
        response = self.suggest_get("film")

        data = json.loads(response.content)
        self.assertEqual(len(data["results"]), 8)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_suggest_tmdb_error_empty(self, *_):
        """a TMDB failure degrades to no suggestions"""
        responses.add(responses.GET, TMDB_SEARCH_URL, json={}, status=429)
        self.client.force_login(self.local_user)
        response = self.suggest_get("blade runner")

        data = json.loads(response.content)
        self.assertEqual(data["results"], [])

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_suggest_tmdb_blocked_local_match_excluded(self, *_):
        """a locally blocked film is dropped from the suggestions"""
        responses.add(responses.GET, TMDB_SEARCH_URL, json=TMDB_SEARCH_PAYLOAD, status=200)
        film = models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        self.local_user.blocked_films.add(film)
        self.client.force_login(self.local_user)
        response = self.suggest_get("blade runner")

        data = json.loads(response.content)
        titles = [row["title"] for row in data["results"]]
        self.assertNotIn("Blade Runner", titles)
        self.assertIn("Blade Runner 2049", titles)

    @override_settings(TMDB_API_KEY="")
    def test_suggest_local_fallback(self, *_):
        """without a key the suggestions list local trigram matches"""
        film = models.Film.objects.create(title="Test Film", year=1999)
        self.client.force_login(self.local_user)
        response = self.suggest_get("test film")

        data = json.loads(response.content)
        self.assertEqual(len(data["results"]), 1)
        row = data["results"][0]
        self.assertEqual(row["title"], "Test Film")
        self.assertEqual(row["year"], 1999)
        self.assertIsNone(row["poster"])
        self.assertEqual(row["url"], film.local_path)

    @override_settings(TMDB_API_KEY="")
    def test_suggest_local_fallback_zero_matches(self, *_):
        """zero local matches return nothing while typing"""
        self.client.force_login(self.local_user)
        response = self.suggest_get("zzz nothing here")

        data = json.loads(response.content)
        self.assertEqual(data["results"], [])

    @override_settings(TMDB_API_KEY="")
    def test_suggest_local_fallback_blocked_excluded(self, *_):
        """blocked films are dropped from the local fallback"""
        film = models.Film.objects.create(title="Test Film")
        self.local_user.blocked_films.add(film)
        self.client.force_login(self.local_user)
        response = self.suggest_get("test film")

        data = json.loads(response.content)
        self.assertEqual(data["results"], [])
