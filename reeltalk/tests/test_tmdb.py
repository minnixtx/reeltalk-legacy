"""tests for the TMDB client used by global film search"""

import pathlib
from unittest.mock import patch

import responses
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from reeltalk import models, tmdb


SEARCH_PAYLOAD = {
    "page": 1,
    "results": [
        {
            "id": 78,
            "title": "Blade Runner",
            "release_date": "1982-06-25",
            "poster_path": "/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg",
        },
        {
            "id": 335984,
            "title": "Blade Runner 2049",
            "release_date": None,
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
    "genres": [
        {"id": 878, "name": "Science Fiction"},
        {"id": 18, "name": "Drama"},
    ],
    "poster_path": "/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg",
    "credits": {
        "crew": [
            {"name": "Ridley Scott", "job": "Director"},
            {"name": "Hans Zimmer", "job": "Original Music Composer"},
        ],
        "cast": [{"name": "Harrison Ford"}] * 12,
    },
}


class TmdbClientTests(TestCase):
    """search/details/payload mapping for the TMDB client"""

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_search_films(self):
        """search results parse into SearchResult rows with page metadata"""
        responses.add(
            responses.GET,
            "https://api.themoviedb.org/3/search/movie",
            json={**SEARCH_PAYLOAD, "total_results": 42, "total_pages": 3},
            status=200,
        )
        results = tmdb.search_films("blade runner")
        self.assertEqual(len(results.rows), 2)
        self.assertEqual(results.total_results, 42)
        self.assertEqual(results.total_pages, 3)
        self.assertEqual(results.rows[0].tmdb_id, "78")
        self.assertEqual(results.rows[0].title, "Blade Runner")
        self.assertEqual(results.rows[0].year, 1982)
        self.assertTrue(results.rows[0].poster_url.startswith("https://image.tmdb.org/"))
        self.assertIsNone(results.rows[1].year)
        self.assertIsNone(results.rows[1].poster_url)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_search_sends_api_key_and_page(self):
        """the instance's API key and page number go out with the request"""
        responses.add(
            responses.GET,
            "https://api.themoviedb.org/3/search/movie",
            json=SEARCH_PAYLOAD,
            status=200,
        )
        tmdb.search_films("blade runner", page=2)
        self.assertIn("api_key=test-key", responses.calls[0].request.url)
        self.assertIn("page=2", responses.calls[0].request.url)

    @override_settings(TMDB_API_KEY="bad-key")
    @responses.activate
    def test_search_invalid_key(self):
        """a 401 from TMDB surfaces as a user-facing error"""
        responses.add(
            responses.GET,
            "https://api.themoviedb.org/3/search/movie",
            json={"status_message": "Invalid API key."},
            status=401,
        )
        with self.assertRaises(tmdb.TmdbError) as ctx:
            tmdb.search_films("blade runner")
        self.assertIn("invalid", str(ctx.exception))

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_search_rate_limited(self):
        """a 429 from TMDB surfaces as a user-facing error"""
        responses.add(
            responses.GET,
            "https://api.themoviedb.org/3/search/movie",
            json={},
            status=429,
        )
        with self.assertRaises(tmdb.TmdbError) as ctx:
            tmdb.search_films("blade runner")
        self.assertIn("rate limit", str(ctx.exception))

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_get_film_details(self):
        """details fetch appends credits and images"""
        responses.add(
            responses.GET,
            "https://api.themoviedb.org/3/movie/78",
            json=DETAILS_PAYLOAD,
            status=200,
        )
        details = tmdb.get_film_details("78")
        self.assertEqual(details["id"], 78)
        self.assertIn("append_to_response", responses.calls[0].request.url)

    def test_film_fields_from_tmdb(self):
        """a details payload maps onto Film model fields"""
        mapped = tmdb.film_fields_from_tmdb(DETAILS_PAYLOAD)
        self.assertEqual(mapped["title"], "Blade Runner")
        self.assertEqual(mapped["year"], 1982)
        self.assertEqual(mapped["runtime"], 117)
        self.assertIn("replicants", mapped["description"])
        self.assertEqual(mapped["genres"], ["Science Fiction", "Drama"])
        # only the director, not every crew member
        self.assertEqual(mapped["directors"], ["Ridley Scott"])
        # cast is capped
        self.assertEqual(len(mapped["cast"]), 10)

    @override_settings(TMDB_API_KEY="test-key")
    @responses.activate
    def test_download_poster(self):
        """the poster downloads from the TMDB image CDN"""
        responses.add(
            responses.GET,
            "https://image.tmdb.org/t/p/w500/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg",
            body=b"fake-jpeg-bytes",
            status=200,
        )
        self.assertEqual(tmdb.download_poster(DETAILS_PAYLOAD), b"fake-jpeg-bytes")

    @override_settings(TMDB_API_KEY="test-key")
    def test_download_poster_without_path(self):
        """no poster path means nothing to download"""
        self.assertIsNone(tmdb.download_poster({"poster_path": None}))

    @override_settings(TMDB_API_KEY="test-key")
    def test_is_configured(self):
        """a set key counts as configured"""
        self.assertTrue(tmdb.is_configured())

    @override_settings(TMDB_API_KEY="")
    def test_not_configured(self):
        """an empty key means the import page shows its notice"""
        self.assertFalse(tmdb.is_configured())


class BackfillTaskTests(TestCase):
    """async TMDB backfill for file-imported films (decision #32)"""

    @classmethod
    def setUpTestData(cls):
        with open(
            pathlib.Path(__file__).parent.joinpath("../static/images/default_avi.jpg"),
            "rb",
        ) as image_file:
            cls.image_data = image_file.read()
        cls.film = models.Film.objects.create(
            title="Trackdown", year=1976, tmdb_id="102938"
        )

    @override_settings(TMDB_API_KEY="")
    def test_backfill_noop_when_unconfigured(self):
        """without an API key the task does nothing"""
        with patch("reeltalk.tmdb.get_film_details") as details:
            tmdb.backfill_imported_films_task([self.film.id])
        details.assert_not_called()

    def test_backfill_skips_complete_films(self):
        """a film that already has a poster and description is untouched"""
        self.film.poster = "posters/existing.jpg"
        self.film.description = "A heist goes wrong."
        self.film.save()
        with patch("reeltalk.tmdb.get_film_details") as details:
            tmdb.backfill_imported_films_task([self.film.id])
        details.assert_not_called()

    def test_backfill_skips_films_without_tmdb_id(self):
        """a manually created film has no TMDB source to fetch from"""
        manual = models.Film.objects.create(title="Manual Film")
        with patch("reeltalk.tmdb.get_film_details") as details:
            tmdb.backfill_imported_films_task([manual.id])
        details.assert_not_called()

    @override_settings(TMDB_API_KEY="test-key")
    def test_backfill_fills_stub_film(self):
        """missing metadata and poster are filled from the TMDB details"""
        with (
            patch("reeltalk.tmdb.get_film_details", return_value=DETAILS_PAYLOAD),
            patch("reeltalk.tmdb.download_poster", return_value=self.image_data),
            patch("reeltalk.tmdb.time.sleep"),
        ):
            tmdb.backfill_imported_films_task([self.film.id])
        self.film.refresh_from_db()
        self.assertIn("replicants", self.film.description)
        self.assertEqual(self.film.directors, ["Ridley Scott"])
        self.assertTrue(self.film.poster.name.endswith("tmdb-102938.jpg"))

    @override_settings(TMDB_API_KEY="test-key")
    def test_backfill_continues_past_failures(self):
        """a TMDB error on one film never stops the rest of the batch"""
        good = models.Film.objects.create(
            title="Blade Runner", year=1982, tmdb_id="78"
        )
        bad = models.Film.objects.create(title="Ghost Film", tmdb_id="999999")

        def details_or_error(tmdb_id):
            if tmdb_id == "999999":
                raise tmdb.TmdbError("TMDB request failed (404)")
            return DETAILS_PAYLOAD

        with (
            patch("reeltalk.tmdb.get_film_details", side_effect=details_or_error),
            patch("reeltalk.tmdb.download_poster", return_value=self.image_data),
            patch("reeltalk.tmdb.time.sleep"),
        ):
            tmdb.backfill_imported_films_task([bad.id, good.id])
        good.refresh_from_db()
        self.assertIn("replicants", good.description)
