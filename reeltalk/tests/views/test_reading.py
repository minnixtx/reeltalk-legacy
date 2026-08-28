"""test for app action functionality"""

from unittest.mock import patch

from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.tests.validate_html import validate_html


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
class ReadingViews(TestCase):
    """watch status for films"""

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

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    def post_finish(self, extra=None, api=False):
        """POST a finish request with the required form fields"""
        data = {
            "user": self.local_user.id,
            "film": self.film.id,
            "privacy": "public",
        }
        if extra:
            data.update(extra)
        request = self.factory.post("", data)
        request.user = self.local_user
        with patch("reeltalk.views.reading.is_api_request") as is_api:
            is_api.return_value = api
            return views.ReadingStatus.as_view()(request, "finish", self.film.id)

    def test_reading_status_get(self, *_):
        """watch status modal"""
        view = views.ReadingStatus.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        result = view(request, "want", self.film.id)
        validate_html(result.render())

        result = view(request, "finish", self.film.id)
        validate_html(result.render())

    def test_reading_status_get_invalid(self, *_):
        """unknown status types 404"""
        view = views.ReadingStatus.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request, "start", self.film.id)
        self.assertIsInstance(result, HttpResponseNotFound)

    def test_finish_requires_rating(self, *_):
        """finishing without a rating is rejected before any DB writes"""
        result = self.post_finish()
        self.assertIsInstance(result, TemplateResponse)
        self.assertTrue(result.context_data["error"])
        validate_html(result.render())

        self.assertFalse(models.ShelfFilm.objects.exists())
        self.assertFalse(models.ReviewRating.objects.exists())
        self.assertFalse(models.Review.objects.exists())

    def test_finish_rejects_invalid_rating(self, *_):
        """ratings outside 0.5-5 are rejected before any DB writes"""
        for bad in ("abc", "0", "0.4", "5.5", "-1"):
            result = self.post_finish({"rating": bad})
            self.assertIsInstance(result, TemplateResponse)
            self.assertTrue(result.context_data["error"])

        self.assertFalse(models.ShelfFilm.objects.exists())
        self.assertFalse(models.ReviewRating.objects.exists())
        self.assertFalse(models.Review.objects.exists())

    def test_finish_rejects_invalid_rating_api(self, *_):
        """API requests get a 400 for missing ratings"""
        result = self.post_finish(api=True)
        self.assertIsInstance(result, HttpResponseBadRequest)
        self.assertFalse(models.ShelfFilm.objects.exists())
        self.assertFalse(models.ReviewRating.objects.exists())

    def test_finish_rating_only(self, *_):
        """finishing with just a rating creates a ReviewRating"""
        result = self.post_finish({"rating": "4"})
        self.assertEqual(result.status_code, 302)

        shelf = self.local_user.shelf_set.get(
            identifier=models.Shelf.READ_FINISHED
        )
        self.assertEqual(shelf.films.get(), self.film)

        status = models.ReviewRating.objects.get()
        self.assertEqual(status.user, self.local_user)
        self.assertEqual(status.film, self.film)
        self.assertEqual(status.rating, 4.0)
        self.assertEqual(status.privacy, "public")

    def test_finish_rating_boundaries(self, *_):
        """0.5 and 5 are both valid ratings"""
        result = self.post_finish({"rating": "0.5"})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(models.ReviewRating.objects.get().rating, 0.5)

    def test_finish_with_content(self, *_):
        """finishing with a written review creates a Review"""
        result = self.post_finish(
            {"rating": "4.5", "content": "a fine film"}
        )
        self.assertEqual(result.status_code, 302)

        shelf = self.local_user.shelf_set.get(
            identifier=models.Shelf.READ_FINISHED
        )
        self.assertEqual(shelf.films.get(), self.film)

        status = models.Status.objects.select_subclasses().get()
        self.assertIsInstance(status, models.Review)
        self.assertNotIsInstance(status, models.ReviewRating)
        self.assertEqual(status.user, self.local_user)
        self.assertEqual(status.film, self.film)
        self.assertEqual(status.rating, 4.5)
        self.assertEqual(status.content, "<p>a fine film</p>")

    def test_finish_moves_from_to_read(self, *_):
        """a want-to-watch film moves to the read shelf on finish"""
        to_read = self.local_user.shelf_set.get(
            identifier=models.Shelf.TO_READ
        )
        models.ShelfFilm.objects.create(
            film=self.film, shelf=to_read, user=self.local_user
        )

        result = self.post_finish({"rating": "3"})
        self.assertEqual(result.status_code, 302)

        read = self.local_user.shelf_set.get(identifier=models.Shelf.READ_FINISHED)
        self.assertEqual(read.films.get(), self.film)
        self.assertFalse(to_read.films.exists())
        self.assertEqual(models.ReviewRating.objects.count(), 1)

    def test_finish_already_read(self, *_):
        """finishing a film that is already read just redirects"""
        result = self.post_finish({"rating": "3"})
        self.assertEqual(result.status_code, 302)
        self.assertEqual(models.ReviewRating.objects.count(), 1)

        result = self.post_finish({"rating": "4"})
        self.assertEqual(result.status_code, 302)
        # no second rating or shelf entry
        self.assertEqual(models.ReviewRating.objects.count(), 1)
        self.assertEqual(models.ShelfFilm.objects.count(), 1)

    def test_want_shelves_only(self, *_):
        """wanting to watch without posting just shelves the film"""
        request = self.factory.post(
            "",
            {
                "user": self.local_user.id,
                "film": self.film.id,
                "privacy": "public",
            },
        )
        request.user = self.local_user
        result = views.ReadingStatus.as_view()(request, "want", self.film.id)
        self.assertEqual(result.status_code, 302)

        to_read = self.local_user.shelf_set.get(identifier=models.Shelf.TO_READ)
        self.assertEqual(to_read.films.get(), self.film)
        self.assertFalse(models.Status.objects.exists())

    def test_want_with_content(self, *_):
        """wanting to watch with a note posts a Comment"""
        request = self.factory.post(
            "",
            {
                "user": self.local_user.id,
                "film": self.film.id,
                "privacy": "followers",
                "post-status": "on",
                "content": "heard great things",
            },
        )
        request.user = self.local_user
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            result = views.ReadingStatus.as_view()(request, "want", self.film.id)
        self.assertEqual(result.status_code, 302)

        to_read = self.local_user.shelf_set.get(identifier=models.Shelf.TO_READ)
        self.assertEqual(to_read.films.get(), self.film)

        status = models.Comment.objects.get()
        self.assertEqual(status.user, self.local_user)
        self.assertEqual(status.film, self.film)
        self.assertEqual(status.content, "<p>heard great things</p>")
        self.assertEqual(status.privacy, "followers")

    def test_want_without_content(self, *_):
        """wanting to watch without a note posts a GeneratedNote"""
        request = self.factory.post(
            "",
            {
                "user": self.local_user.id,
                "film": self.film.id,
                "privacy": "followers",
                "post-status": "on",
            },
        )
        request.user = self.local_user
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            result = views.ReadingStatus.as_view()(request, "want", self.film.id)
        self.assertEqual(result.status_code, 302)

        to_read = self.local_user.shelf_set.get(identifier=models.Shelf.TO_READ)
        self.assertEqual(to_read.films.get(), self.film)

        status = models.GeneratedNote.objects.get()
        self.assertEqual(status.user, self.local_user)
        self.assertEqual(status.mention_films.get(), self.film)
        self.assertEqual(status.privacy, "followers")
