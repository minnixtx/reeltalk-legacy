"""tests updating reading progress"""

from datetime import datetime, timezone
from unittest.mock import patch
from django.test import TestCase, Client

from reeltalk import models


@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
@patch("reeltalk.activitystreams.add_book_statuses_task.delay")
@patch("reeltalk.activitystreams.remove_book_statuses_task.delay")
class ReadThrough(TestCase):
    """readthrough tests"""

    @classmethod
    def setUpTestData(cls):
        """basic user and book data"""
        cls.work = models.Work.objects.create(title="Example Work")

        cls.edition = models.Edition.objects.create(
            title="Example Edition", parent_work=cls.work
        )

        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.user = models.User.objects.create_user(
                "cinco", "cinco@example.com", "seissiete", local=True, localname="cinco"
            )

    def setUp(self):
        """individual test setup"""
        self.client = Client()
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            self.client.force_login(self.user)

    @patch("reeltalk.activitystreams.remove_user_statuses_task.delay")
    def test_create_basic_readthrough(self, *_):
        """A basic readthrough doesn't create a progress update"""
        self.assertEqual(self.edition.readthrough_set.count(), 0)

        models.ReadThrough.objects.create(
            user=self.user,
            book=self.edition,
            start_date=datetime(2020, 11, 27, tzinfo=timezone.utc),
        )

        readthroughs = self.edition.readthrough_set.all()
        self.assertEqual(len(readthroughs), 1)
        self.assertEqual(readthroughs[0].progressupdate_set.count(), 0)
        self.assertEqual(
            readthroughs[0].start_date, datetime(2020, 11, 27, tzinfo=timezone.utc)
        )
        self.assertEqual(readthroughs[0].progress, None)
        self.assertEqual(readthroughs[0].finish_date, None)

    @patch("reeltalk.activitystreams.remove_user_statuses_task.delay")
    def test_create_progress_readthrough(self, *_):
        """a readthrough with progress"""
        self.assertEqual(self.edition.readthrough_set.count(), 0)

        models.ReadThrough.objects.create(
            user=self.user,
            book=self.edition,
            start_date=datetime(2020, 11, 27, tzinfo=timezone.utc),
        )

        readthroughs = self.edition.readthrough_set.all()
        self.assertEqual(len(readthroughs), 1)
        self.assertEqual(
            readthroughs[0].start_date, datetime(2020, 11, 27, tzinfo=timezone.utc)
        )
        self.assertEqual(readthroughs[0].finish_date, None)

        # Update progress
        self.client.post(
            "/edit-readthrough",
            {
                "id": readthroughs[0].id,
                "progress": 100,
            },
        )

        progress_updates = (
            readthroughs[0].progressupdate_set.order_by("updated_date").all()
        )
        self.assertEqual(len(progress_updates), 1)
        self.assertEqual(progress_updates[0].mode, models.ProgressMode.PAGE)
        self.assertEqual(progress_updates[0].progress, 100)

        # Edit doesn't publish anything
        self.client.post(
            "/delete-readthrough",
            {
                "id": readthroughs[0].id,
            },
        )

        readthroughs = self.edition.readthrough_set.all()
        updates = self.user.progressupdate_set.all()
        self.assertEqual(len(readthroughs), 0)
        self.assertEqual(len(updates), 0)
