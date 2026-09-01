"""tests for the TMDB client used by global film search"""

import responses
from django.test import TestCase, override_settings

from reeltalk import tmdb


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
