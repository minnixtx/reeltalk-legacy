"""style fixes and lookups for templates"""

from unittest.mock import patch

from django.test import TestCase

from reeltalk import models
from reeltalk.templatetags import feed_page_tags


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.remove_status_task.delay")
class FeedPageTags(TestCase):
    """lotta different things here"""

    @classmethod
    def setUpTestData(cls):
        """create some filler objects"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.user = models.User.objects.create_user(
                "mouse@example.com",
                "mouse@mouse.mouse",
                "mouseword",
                local=True,
                localname="mouse",
            )
        cls.film = models.Film.objects.create(title="Test Film")

    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    def test_load_subclass(self, *_):
        """get a status' real type"""
        review = models.Review.objects.create(user=self.user, film=self.film, rating=3)
        status = models.Status.objects.get(id=review.id)
        self.assertIsInstance(status, models.Status)
        self.assertIsInstance(feed_page_tags.load_subclass(status), models.Review)

        comment = models.Comment.objects.create(
            user=self.user, film=self.film, content="hi"
        )
        status = models.Status.objects.get(id=comment.id)
        self.assertIsInstance(status, models.Status)
        self.assertIsInstance(feed_page_tags.load_subclass(status), models.Comment)
