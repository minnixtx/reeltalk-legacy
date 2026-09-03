"""Gettings film ratings"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from reeltalk import models
from reeltalk.templatetags import rating_tags


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.remove_status_task.delay")
class RatingTags(TestCase):
    """lotta different things here"""

    @classmethod
    def setUpTestData(cls):
        """create some filler objects"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse@example.com",
                "mouse@mouse.mouse",
                "mouseword",
                local=True,
                localname="mouse",
            )
        with patch("reeltalk.models.user.set_remote_server.delay"):
            cls.remote_user = models.User.objects.create_user(
                "rat",
                "rat@rat.rat",
                "ratword",
                remote_id="http://example.com/rat",
                local=False,
            )
        cls.film = models.Film.objects.create(title="Test Film")

    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    def test_get_rating(self, *_):
        """average of all ratings above zero. privacy filtering is how it
        ought to work with subjective ratings, which are currently not used
        for performance reasons."""
        self.assertEqual(rating_tags.get_rating(self.film, self.local_user), 0)

        # rating-only entry: included
        models.ReviewRating.objects.create(
            user=self.remote_user,
            rating=4,
            film=self.film,
            privacy="public",
        )
        self.assertEqual(rating_tags.get_rating(self.film, self.local_user), 4)

        # followers-only: included
        models.ReviewRating.objects.create(
            user=self.remote_user,
            rating=5,
            film=self.film,
            privacy="followers",
        )
        self.assertEqual(rating_tags.get_rating(self.film, self.local_user), 4.5)

        # review without a rating: not included
        models.Review.objects.create(
            name="blah",
            user=self.local_user,
            film=self.film,
            privacy="public",
        )
        self.assertEqual(rating_tags.get_rating(self.film, self.local_user), 4.5)

    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    def test_get_rating_excludes_soft_deleted(self, *_):
        """deleted reviews don't count toward the film's average"""
        first = models.Review.objects.create(
            content="meh", user=self.local_user, film=self.film, rating=2
        )
        models.Review.objects.create(
            content="great", user=self.local_user, film=self.film, rating=4
        )
        self.assertEqual(rating_tags.get_rating(self.film, self.local_user), 3)

        first.delete()
        self.assertEqual(rating_tags.get_rating(self.film, self.local_user), 4)

    def test_get_user_rating(self, *_):
        """get a user's most recent rating of a film"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.Review.objects.create(
                user=self.local_user, film=self.film, rating=3
            )
        self.assertEqual(rating_tags.get_user_rating(self.film, self.local_user), 3)

    def test_get_user_rating_most_recent(self, *_):
        """the newest review wins"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.Review.objects.create(
                user=self.local_user,
                film=self.film,
                rating=2,
                published_date=timezone.now() - timedelta(days=1),
            )
            models.Review.objects.create(
                user=self.local_user, film=self.film, rating=5
            )
        self.assertEqual(rating_tags.get_user_rating(self.film, self.local_user), 5)

    def test_get_user_rating_deleted(self, *_):
        """deleted reviews don't count"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            review = models.Review.objects.create(
                user=self.local_user, film=self.film, rating=3
            )
        review.delete()
        self.assertEqual(rating_tags.get_user_rating(self.film, self.local_user), 0)

    def test_get_user_rating_doesnt_exist(self, *_):
        """there is no rating available"""
        self.assertEqual(rating_tags.get_user_rating(self.film, self.local_user), 0)
