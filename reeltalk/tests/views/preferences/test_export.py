"""test for app action functionality"""

from unittest.mock import patch

from django.http import HttpResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.tests.validate_html import validate_html


@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
class ExportViews(TestCase):
    """viewing and creating statuses"""

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
        )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    def test_export_get(self, *_):
        """request export"""
        request = self.factory.get("")
        request.user = self.local_user
        result = views.Export.as_view()(request)
        validate_html(result.render())

    def test_export_file(self, *_):
        """simple export"""
        shelf_film = models.ShelfFilm.objects.create(
            shelf=self.local_user.shelf_set.first(),
            user=self.local_user,
            film=self.film,
        )
        film_date = str.encode(f"{shelf_film.shelved_date.date()}")
        request = self.factory.post("")
        request.user = self.local_user
        export = views.Export.as_view()(request)
        self.assertIsInstance(export, HttpResponse)
        self.assertEqual(export.status_code, 200)

        self.assertEqual(
            export.content,
            b"title,director_text,remote_id,tmdb_id,imdb_id,year,runtime,rating,review_name,review_cw,review_content,review_published,shelf,shelf_name,shelf_date\r\n"
            + b"Test Film,,%b,42,,,,,,,,,to-read,Want to Watch,%b\r\n"
            % (self.film.remote_id.encode("utf-8"), film_date),
        )

    def test_export_file_with_review(self, *_):
        """simple export"""
        shelf_film = models.ShelfFilm.objects.create(
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
        review_date = str.encode(f"{review.published_date.date()}")
        film_date = str.encode(f"{shelf_film.shelved_date.date()}")
        request = self.factory.post("")
        request.user = self.local_user
        export = views.Export.as_view()(request)
        self.assertIsInstance(export, HttpResponse)
        self.assertEqual(export.status_code, 200)

        self.assertEqual(
            export.content,
            b"title,director_text,remote_id,tmdb_id,imdb_id,year,runtime,rating,review_name,review_cw,review_content,review_published,shelf,shelf_name,shelf_date\r\n"
            + b"Test Film,,%b,42,,,,3.00,review title,,content here,%b,to-read,Want to Watch,%b\r\n"
            % (self.film.remote_id.encode("utf-8"), review_date, film_date),
        )

    def test_export_file_with_rating_only(self, *_):
        """export a rating-only entry"""
        models.ReviewRating.objects.create(
            film=self.film,
            user=self.local_user,
            rating=4.5,
        )
        request = self.factory.post("")
        request.user = self.local_user
        export = views.Export.as_view()(request)
        self.assertIsInstance(export, HttpResponse)
        self.assertEqual(export.status_code, 200)

        lines = export.content.decode("utf-8").strip().split("\r\n")
        self.assertEqual(len(lines), 2)
        values = dict(zip(lines[0].split(","), lines[1].split(",")))
        self.assertEqual(values["title"], "Test Film")
        self.assertEqual(values["rating"], "4.50")
        self.assertEqual(values["shelf"], "")
