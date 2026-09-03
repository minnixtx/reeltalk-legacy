"""testing import"""

from unittest.mock import patch
from django.test import RequestFactory, TestCase

from reeltalk import models
from reeltalk.views import rss_feed


@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
@patch("reeltalk.activitystreams.ActivityStream.get_activity_stream")
@patch("reeltalk.activitystreams.add_status_task.delay")
class RssFeedView(TestCase):
    """rss feed behaves as expected"""

    @classmethod
    def setUpTestData(cls):
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "rss_user", "rss@test.rss", "password", local=True
            )
        cls.film = models.Film.objects.create(
            title="Example Film",
            remote_id="https://example.com/film/1",
        )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    def test_rss_empty(self, *_):
        """load an rss feed"""
        view = rss_feed.RssFeed()
        request = self.factory.get("/user/rss_user/rss")
        request.user = self.local_user
        result = view(request, username=self.local_user.username)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Status updates from rss_user", result.content)

    def test_rss_comment(self, *_):
        """load an rss feed"""
        models.Comment.objects.create(
            content="comment test content",
            user=self.local_user,
            film=self.film,
        )
        view = rss_feed.RssFeed()
        request = self.factory.get("/user/rss_user/rss")
        request.user = self.local_user
        result = view(request, username=self.local_user.username)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Example Film", result.content)

    def test_rss_review(self, *_):
        """load an rss feed"""
        models.Review.objects.create(
            name="Review name",
            content="test content",
            rating=3,
            user=self.local_user,
            film=self.film,
        )
        view = rss_feed.RssFeed()
        request = self.factory.get("/user/rss_user/rss")
        request.user = self.local_user
        result = view(request, username=self.local_user.username)
        self.assertEqual(result.status_code, 200)

    def test_rss_comment_only(self, *_):
        """load an rss feed"""
        models.Comment.objects.create(
            content="comment test content",
            user=self.local_user,
            film=self.film,
        )
        view = rss_feed.RssCommentsOnlyFeed()
        request = self.factory.get("/user/rss_user/rss")
        request.user = self.local_user
        result = view(request, username=self.local_user.username)
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Example Film", result.content)

    def test_rss_review_only(self, *_):
        """load an rss feed"""
        models.Review.objects.create(
            name="Review name",
            content="test content",
            rating=3,
            user=self.local_user,
            film=self.film,
        )
        view = rss_feed.RssReviewsOnlyFeed()
        request = self.factory.get("/user/rss_user/rss")
        request.user = self.local_user
        result = view(request, username=self.local_user.username)
        self.assertEqual(result.status_code, 200)

    def test_rss_shelf(self, *_):
        """load the rss feed of a shelf"""
        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.activitystreams.add_film_statuses_task.delay"),
        ):
            # make the shelf
            shelf = models.Shelf.objects.create(
                name="Test Shelf", identifier="test-shelf", user=self.local_user
            )
            # put the film on the shelf
            models.ShelfFilm.objects.create(
                film=self.film,
                shelf=shelf,
                user=self.local_user,
            )
        view = rss_feed.RssShelfFeed()
        request = self.factory.get("/user/films/test-shelf/rss")
        request.user = self.local_user
        result = view(
            request, username=self.local_user.username, shelf_identifier="test-shelf"
        )
        self.assertEqual(result.status_code, 200)
        self.assertIn(b"Example Film", result.content)
