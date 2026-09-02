"""test for app action functionality"""

from datetime import UTC
from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, tmdb, views
from reeltalk.tests.validate_html import validate_html


@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
class ExportViews(TestCase):
    """exporting a user's film list as a TMDB-format CSV"""

    @classmethod
    def setUpTestData(cls):
        """we need basic test data and mocks"""
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
        cls.film = models.Film.objects.create(
            title="Test Film",
            remote_id="https://example.com/film/1",
            tmdb_id="42",
            year=1976,
        )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    def parse_export(self, response):
        """the exported CSV as (header, list of row dicts)"""
        lines = response.content.decode("utf-8").strip().split("\r\n")
        header = lines[0].split(",")
        return header, [dict(zip(header, line.split(","))) for line in lines[1:]]

    def test_export_get(self, *_):
        """request export"""
        request = self.factory.get("")
        request.user = self.local_user
        result = views.Export.as_view()(request)
        validate_html(result.render())

    def test_export_file(self, *_):
        """a shelved film exports as one TMDB-format row"""
        models.ShelfFilm.objects.create(
            shelf=self.local_user.shelf_set.first(),
            user=self.local_user,
            film=self.film,
        )
        request = self.factory.post("")
        request.user = self.local_user
        export = views.Export.as_view()(request)
        self.assertIsInstance(export, HttpResponse)
        self.assertEqual(export.status_code, 200)

        header, rows = self.parse_export(export)
        self.assertEqual(header, tmdb.TMDB_EXPORT_HEADER)
        self.assertEqual(len(rows), 1)
        self.assertEqual(
            rows[0],
            {
                "TMDb ID": "42",
                "IMDb ID": "",
                "Type": "movie",
                "Name": "Test Film",
                "Release Date": "1976-01-01T00:00:00Z",
                "Season Number": "",
                "Episode Number": "",
                "Rating": "",
                "Your Rating": "",
                "Date Rated": "",
            },
        )

    def test_export_file_with_review(self, *_):
        """a rated review exports as Your Rating (TMDB's 1-10 scale) + Date Rated"""
        models.ShelfFilm.objects.create(
            shelf=self.local_user.shelf_set.first(),
            user=self.local_user,
            film=self.film,
        )
        review = models.Review.objects.create(
            film=self.film,
            user=self.local_user,
            name="review title",
            content="content here",
            rating=3,
        )
        request = self.factory.post("")
        request.user = self.local_user
        export = views.Export.as_view()(request)
        self.assertIsInstance(export, HttpResponse)
        self.assertEqual(export.status_code, 200)

        _, rows = self.parse_export(export)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Your Rating"], "6")
        self.assertEqual(
            rows[0]["Date Rated"],
            review.published_date.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    def test_export_file_with_rating_only(self, *_):
        """a rating-only entry exports like any other rating"""
        models.ReviewRating.objects.create(
            film=self.film,
            user=self.local_user,
            rating=4.5,
        )
        request = self.factory.post("")
        request.user = self.local_user
        export = views.Export.as_view()(request)
        self.assertIsInstance(export, HttpResponse)

        _, rows = self.parse_export(export)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["TMDb ID"], "42")
        self.assertEqual(rows[0]["Name"], "Test Film")
        self.assertEqual(rows[0]["Your Rating"], "9")
