"""tests for the file-based film import (TMDB-style CSV)"""

from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.tests.validate_html import validate_html
from reeltalk.views.preferences.import_films import MAX_IMPORT_ROWS

# a row in the canonical TMDB export format (the owner's watchlist export is
# the reference); line 2 of the file
TRACKDOWN_ROW = {
    "TMDb ID": "102938",
    "IMDb ID": "tt0075344",
    "Type": "movie",
    "Name": "Trackdown",
    "Release Date": "1976-05-20T00:00:00Z",
    "Season Number": "",
    "Episode Number": "",
    "Rating": "5.667",
    "Your Rating": "",
    "Date Rated": "",
}

CANONICAL_HEADER = ",".join(TRACKDOWN_ROW.keys())


def csv_upload(rows, header=CANONICAL_HEADER):
    """build a CSV upload from row dicts (keys must match the header)"""
    lines = [header]
    for row in rows:
        lines.append(",".join(str(row.get(key, "")) for key in header.split(",")))
    return SimpleUploadedFile("watchlist.csv", "\n".join(lines).encode(), "text/csv")


@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
class ImportFilmsViews(TestCase):
    """file-based film import"""

    @classmethod
    def setUpTestData(cls):
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse@local.com",
                "mouse@mouse.com",
                "mouseword",
                local=True,
                localname="mouse",
                remote_id="https://example.com/users/mouse",
            )
        cls.watchlist_shelf = models.Shelf.objects.get(
            identifier=models.Shelf.TO_READ, user=cls.local_user
        )
        cls.watched_shelf = models.Shelf.objects.get(
            identifier=models.Shelf.READ_FINISHED, user=cls.local_user
        )
        # an existing film for match tests: TMDB ID but no IMDb ID or year
        cls.film = models.Film.objects.create(
            title="Test Film",
            remote_id="https://example.com/film/1",
            tmdb_id="42",
        )

    def setUp(self):
        self.factory = RequestFactory()

    def post_import(self, rows, header=CANONICAL_HEADER):
        request = self.factory.post("", {"csv_file": csv_upload(rows, header)})
        request.user = self.local_user
        return views.ImportFilms.as_view()(request)

    def test_import_get(self, *_):
        """the upload page loads"""
        request = self.factory.get("")
        request.user = self.local_user
        result = views.ImportFilms.as_view()(request)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_import_requires_file(self, *_):
        """a POST with no file shows an error"""
        request = self.factory.post("")
        request.user = self.local_user
        result = views.ImportFilms.as_view()(request)
        self.assertIsInstance(result, TemplateResponse)
        self.assertIn("Choose a CSV file", result.context_data["error"])

    def test_import_rejects_non_tmdb_csv(self, *_):
        """a file without the TMDB columns is rejected"""
        result = self.post_import(
            [{"Title": "Trackdown", "Year": "1976"}], header="Title,Year"
        )
        self.assertIsInstance(result, TemplateResponse)
        self.assertIn("Not a recognized TMDB export", result.context_data["error"])
        self.assertEqual(models.Film.objects.count(), 1)

    def test_import_rejects_too_many_rows(self, *_):
        """files past the row cap are rejected before anything is imported"""
        rows = [dict(TRACKDOWN_ROW) for _ in range(MAX_IMPORT_ROWS + 1)]
        result = self.post_import(rows)
        self.assertIsInstance(result, TemplateResponse)
        self.assertIn("limited to", result.context_data["error"])
        self.assertEqual(models.Film.objects.count(), 1)

    def test_import_creates_film_on_watchlist(self, *_):
        """an unmatched row creates the film from CSV data and watchlists it"""
        result = self.post_import([TRACKDOWN_ROW])
        validate_html(result.render())

        film = models.Film.objects.get(title="Trackdown")
        self.assertEqual(film.tmdb_id, "102938")
        self.assertEqual(film.imdb_id, "tt0075344")
        self.assertEqual(film.year, 1976)
        self.assertTrue(
            models.ShelfFilm.objects.filter(
                film=film, shelf=self.watchlist_shelf, user=self.local_user
            ).exists()
        )
        self.assertFalse(models.ReviewRating.objects.exists())

        row = result.context_data["results"][0]
        self.assertEqual(row["status"], "created")
        self.assertEqual(row["note"], "added to Watchlist")
        self.assertEqual(result.context_data["summary"]["created"], 1)

    def test_import_rated_row_lands_on_watched(self, *_):
        """a row with Your Rating goes to Watched with a rating-only entry"""
        row = dict(TRACKDOWN_ROW, **{"Your Rating": "9"})
        result = self.post_import([row])

        film = models.Film.objects.get(title="Trackdown")
        entry = models.ReviewRating.objects.get(film=film, user=self.local_user)
        self.assertEqual(float(entry.rating), 4.5)
        self.assertTrue(
            models.ShelfFilm.objects.filter(
                film=film, shelf=self.watched_shelf, user=self.local_user
            ).exists()
        )
        self.assertFalse(
            models.ShelfFilm.objects.filter(
                film=film, shelf=self.watchlist_shelf, user=self.local_user
            ).exists()
        )
        self.assertEqual(result.context_data["results"][0]["note"], "Watched — 4.5 stars")

    def test_import_matches_existing_by_tmdb_id(self, *_):
        """a row whose TMDB ID is known matches instead of duplicating"""
        row = dict(
            TRACKDOWN_ROW,
            **{"TMDb ID": "42", "Name": "Test Film", "IMDb ID": "tt0111111"}
        )
        result = self.post_import([row])

        self.assertEqual(models.Film.objects.count(), 1)
        self.film.refresh_from_db()
        self.assertEqual(self.film.imdb_id, "tt0111111")  # backfilled
        self.assertTrue(
            models.ShelfFilm.objects.filter(
                film=self.film, shelf=self.watchlist_shelf, user=self.local_user
            ).exists()
        )
        self.assertEqual(result.context_data["results"][0]["status"], "matched")

    def test_import_matches_by_title_and_year(self, *_):
        """a row without a TMDB ID matches on normalized title + year"""
        godfather = models.Film.objects.create(title="The Godfather", year=1972)
        row = dict(
            TRACKDOWN_ROW,
            **{
                "TMDb ID": "",
                "IMDb ID": "",
                "Name": "The Godfather",
                "Release Date": "1972-03-30T00:00:00Z",
            },
        )
        result = self.post_import([row])

        self.assertEqual(models.Film.objects.count(), 2)
        godfather.refresh_from_db()
        self.assertIsNone(godfather.tmdb_id)  # nothing to backfill from an empty ID
        self.assertTrue(
            models.ShelfFilm.objects.filter(
                film=godfather, shelf=self.watchlist_shelf, user=self.local_user
            ).exists()
        )
        self.assertEqual(result.context_data["results"][0]["status"], "matched")

    def test_import_skips_non_movies(self, *_):
        """TV rows in a TMDB export are skipped, not created"""
        row = dict(TRACKDOWN_ROW, **{"Type": "series", "Name": "Some Show"})
        result = self.post_import([row])

        self.assertEqual(models.Film.objects.count(), 1)
        row_result = result.context_data["results"][0]
        self.assertEqual(row_result["status"], "skipped")
        self.assertIn("not a movie", row_result["note"])

    def test_import_skips_missing_name(self, *_):
        """a row without a name can't be created (no API calls to fetch one)"""
        row = dict(TRACKDOWN_ROW, **{"Name": ""})
        result = self.post_import([row])

        self.assertEqual(models.Film.objects.count(), 1)
        self.assertEqual(result.context_data["results"][0]["status"], "skipped")
        self.assertIn("missing name", result.context_data["results"][0]["note"])

    def test_import_already_on_watchlist(self, *_):
        """re-importing a watchlisted film is a no-op with a note"""
        models.ShelfFilm.objects.create(
            film=self.film, shelf=self.watchlist_shelf, user=self.local_user
        )
        row = dict(TRACKDOWN_ROW, **{"TMDb ID": "42", "Name": "Test Film"})
        result = self.post_import([row])

        self.assertEqual(
            models.ShelfFilm.objects.filter(
                film=self.film, shelf=self.watchlist_shelf
            ).count(),
            1,
        )
        row_result = result.context_data["results"][0]
        self.assertEqual(row_result["status"], "matched")
        self.assertEqual(row_result["note"], "already on your Watchlist")

    def test_import_rated_row_keeps_existing_review(self, *_):
        """one review per film: an existing review is never touched"""
        models.Review.objects.create(
            film=self.film, user=self.local_user, content="my review", rating=5
        )
        row = dict(
            TRACKDOWN_ROW, **{"TMDb ID": "42", "Name": "Test Film", "Your Rating": "9"}
        )
        result = self.post_import([row])

        self.assertEqual(models.ReviewRating.objects.count(), 0)
        review = models.Review.objects.get(film=self.film, user=self.local_user)
        self.assertEqual(float(review.rating), 5.0)  # untouched
        row_result = result.context_data["results"][0]
        self.assertIn("already have a review", row_result["note"])

    def test_import_summary_counts(self, *_):
        """the summary tallies created/matched/skipped rows"""
        rows = [
            TRACKDOWN_ROW,  # created + watchlisted
            dict(TRACKDOWN_ROW, **{"TMDb ID": "42", "Name": "Test Film"}),  # matched
            dict(TRACKDOWN_ROW, **{"Type": "series", "Name": "Some Show"}),  # skipped
        ]
        result = self.post_import(rows)

        summary = result.context_data["summary"]
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["created"], 1)
        self.assertEqual(summary["matched"], 1)
        self.assertEqual(summary["skipped"], 1)
        # line numbers point at the rows in the uploaded file (header is line 1)
        self.assertEqual(
            [r["line"] for r in result.context_data["results"]], [2, 3, 4]
        )
