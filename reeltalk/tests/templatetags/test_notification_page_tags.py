"""style fixes and lookups for templates"""

from unittest.mock import patch

from django.test import TestCase

from reeltalk import models
from reeltalk.templatetags import notification_page_tags


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.remove_status_task.delay")
class NotificationPageTags(TestCase):
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

    def test_related_status(self, *_):
        """gets the subclass model for a notification status"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            status = models.Status.objects.create(content="hi", user=self.user)
        notification = models.Notification.objects.create(
            user=self.user, notification_type="MENTION", related_status=status
        )

        result = notification_page_tags.related_status(notification)
        self.assertIsInstance(result, models.Status)
