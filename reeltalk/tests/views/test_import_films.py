"""tests for the TMDB film import page"""

from unittest.mock import patch

import responses
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, override_settings
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.tests.validate_html import validate_html


SEARCH_PAYLOAD = {
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
}

DETAILS_PAYLOAD = {
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

SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
DETAILS_URL = "https://api.themoviedb.org/3/movie/78"
POSTER_URL = "https://image.tmdb.org/t/p/w500/br.jpg"


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
class ImportFilmsViews(TestCase):
    """search, create-or-match, add to list or shelf"""

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
        # local users get their default shelves (incl. Watchlist) on create
        cls.want_shelf = models.Shelf.objects.get(
            identifier=models.Shelf.TO_READ, user=cls.local_user
        )
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            cls.film_list = models.List.objects.create(
                name="Cult Classics", user=cls.local_user, curation="closed"
            )

    def setUp(self):
        self.factory = RequestFactory()

    def call_view(self, data=None):
        """call the import view as the local user"""
        if data is not None:
            request = self.factory.post("/import/", data)
        else:
            request = self.factory.get("/import/")
        request.user = self.local_user
        return views.ImportFilms.as_view()(request)

    def add_post(self, target, extra=None):
        data = {
            "action": "add",
            "query": "blade runner",
            "target": target,
            "tmdb_id": "78",
            "title": "Blade Runner",
            "year": "1982",
        }
        if extra:
            data.update(extra)
        return self.call_view(data)

    def test_login_required(self, *_):
        """anonymous users are sent to the login page"""
        request = self.factory.get("/import/")
        request.user = AnonymousUser()
        result = views.ImportFilms.as_view()(request)
        self.assertEqual(result.status_code, 302)
        self.assertIn("login", result.url)

    @override_settings(TMDB_API_KEY="")
    def test_get_unconfigured(self, *_):
        """without an API key the page shows a not-configured notice"""
        result = self.call_view()
        content = result.render().content.decode()
        self.assertIn("isn't configured on this instance", content)

    @override_settings(TMDB_API_KEY="test-key")
    def test_get_configured(self, *_):
        """the form lists the watchlist shelf and the user's lists"""
        result = self.call_view()
        validate_html(result.render())
        content = result.render().content.decode()
        self.assertIn("Watchlist", content)
        self.assertIn("Cult Classics", content)

    @override_settings(TMDB_API_KEY="test-key")
    def test_get_preselected_target(self, *_):
        """a ?target= param preselects the destination dropdown"""
        request = self.factory.get(f"/import/?target=list:{self.film_list.id}")
        request.user = self.local_user
        result = views.ImportFilms.as_view()(request)
        self.assertEqual(result.context_data["target"], f"list:{self.film_list.id}")

    @override_settings(TMDB_API_KEY="test-key")
    def test_search_requires_query(self, *_):
        """an empty search term is rejected without calling TMDB"""
        result = self.call_view(
            {"action": "search", "query": "", "target": f"list:{self.film_list.id}"}
        )
        content = result.render().content.decode()
        self.assertIn("Please enter a film title", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_search_renders_results(self, *_):
        """search hits render with local matches badged"""
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_PAYLOAD, status=200)
        models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        result = self.call_view(
            {
                "action": "search",
                "query": "blade runner",
                "target": f"list:{self.film_list.id}",
            }
        )
        validate_html(result.render())
        content = result.render().content.decode()
        self.assertIn("Blade Runner 2049", content)
        self.assertIn("In your library", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_search_tmdb_error(self, *_):
        """a TMDB failure shows a user-facing error"""
        responses.add(responses.GET, SEARCH_URL, json={}, status=429)
        result = self.call_view(
            {
                "action": "search",
                "query": "blade runner",
                "target": f"list:{self.film_list.id}",
            }
        )
        content = result.render().content.decode()
        self.assertIn("rate limit", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_add_new_film_to_list(self, *_):
        """an unknown film is created from TMDB and added to the list"""
        responses.add(responses.GET, DETAILS_URL, json=DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, POSTER_URL, body=b"jpeg", status=200)
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_PAYLOAD, status=200)
        result = self.add_post(f"list:{self.film_list.id}")

        film = models.Film.objects.get(tmdb_id="78")
        self.assertEqual(film.year, 1982)
        self.assertEqual(film.runtime, 117)
        self.assertEqual(film.directors, ["Ridley Scott"])
        self.assertEqual(film.genres, ["Science Fiction"])
        self.assertTrue(film.poster)
        item = models.ListItem.objects.get(film=film, film_list=self.film_list)
        self.assertTrue(item.approved)

        content = result.render().content.decode()
        self.assertIn("Added “Blade Runner” to Cult Classics", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_add_existing_film_to_list(self, *_):
        """a film already in the library is added without a duplicate row"""
        models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        responses.add(responses.GET, DETAILS_URL, json=DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, POSTER_URL, body=b"jpeg", status=200)
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_PAYLOAD, status=200)
        result = self.add_post(f"list:{self.film_list.id}")

        self.assertEqual(models.Film.objects.count(), 1)
        film = models.Film.objects.get()
        self.assertTrue(models.ListItem.objects.filter(
            film=film, film_list=self.film_list
        ).exists())
        content = result.render().content.decode()
        self.assertIn("Added “Blade Runner” to Cult Classics", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_add_duplicate_to_list(self, *_):
        """adding a film that is already on the list is rejected"""
        film = models.Film.objects.create(title="Blade Runner", tmdb_id="78")
        models.ListItem.objects.create(
            user=self.local_user, film=film, film_list=self.film_list, order=1
        )
        responses.add(responses.GET, DETAILS_URL, json=DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, POSTER_URL, body=b"jpeg", status=200)
        result = self.add_post(f"list:{self.film_list.id}")

        self.assertEqual(
            models.ListItem.objects.filter(film_list=self.film_list).count(), 1
        )
        content = result.render().content.decode()
        self.assertIn("is already on Cult Classics", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_add_to_shelf(self, *_):
        """a film can be imported straight onto the Watchlist"""
        responses.add(responses.GET, DETAILS_URL, json=DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, POSTER_URL, body=b"jpeg", status=200)
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_PAYLOAD, status=200)
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            result = self.add_post("shelf:to-read")

        film = models.Film.objects.get(tmdb_id="78")
        self.assertTrue(
            models.ShelfFilm.objects.filter(film=film, shelf=self.want_shelf).exists()
        )
        content = result.render().content.decode()
        self.assertIn("Added “Blade Runner” to Watchlist", content)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_add_manual_film_backfills_tmdb_id(self, *_):
        """a manually created film matching title + year is backfilled, not duplicated"""
        manual = models.Film.objects.create(title="Blade Runner", year=1982)
        responses.add(responses.GET, DETAILS_URL, json=DETAILS_PAYLOAD, status=200)
        responses.add(responses.GET, POSTER_URL, body=b"jpeg", status=200)
        responses.add(responses.GET, SEARCH_URL, json=SEARCH_PAYLOAD, status=200)
        result = self.add_post(f"list:{self.film_list.id}")

        self.assertEqual(models.Film.objects.count(), 1)
        manual.refresh_from_db()
        self.assertEqual(manual.tmdb_id, "78")
        self.assertEqual(manual.genres, ["Science Fiction"])
        self.assertTrue(
            models.ListItem.objects.filter(
                film=manual, film_list=self.film_list
            ).exists()
        )

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_add_invalid_target(self, *_):
        """an unknown destination is rejected before any TMDB calls"""
        result = self.add_post("list:99999")
        content = result.render().content.decode()
        self.assertIn("Please choose a destination", content)
        self.assertEqual(models.Film.objects.count(), 0)
