"""testing activitystreams"""

from datetime import datetime, timezone
from unittest.mock import patch
from django.test import TestCase

from reeltalk import activitystreams, models


@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
class Activitystreams(TestCase):
    """using redis to build activity streams"""

    @classmethod
    def setUpTestData(cls):
        """use a test csv"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse", "mouse@mouse.mouse", "password", local=True, localname="mouse"
            )
            cls.another_user = models.User.objects.create_user(
                "nutria",
                "nutria@nutria.nutria",
                "password",
                local=True,
                localname="nutria",
            )
        with patch("reeltalk.models.user.set_remote_server.delay"):
            cls.remote_user = models.User.objects.create_user(
                "rat",
                "rat@rat.com",
                "ratword",
                local=False,
                remote_id="https://example.com/users/rat",
                inbox="https://example.com/users/rat/inbox",
                outbox="https://example.com/users/rat/outbox",
            )
        cls.film = models.Film.objects.create(title="Test Film")

    def setUp(self):
        """per-test setUp"""

        class TestStream(activitystreams.ActivityStream):
            """test stream, don't have to do anything here"""

            key = "test"

        self.test_stream = TestStream()

    def test_activitystream_class_ids(self, *_):
        """the abstract base class for stream objects"""
        self.assertEqual(
            self.test_stream.stream_id(self.local_user.id),
            f"{self.local_user.id}-test",
        )
        self.assertEqual(
            self.test_stream.unread_id(self.local_user.id),
            f"{self.local_user.id}-test-unread",
        )

    def test_unread_by_status_type_id(self, *_):
        """stream for status type"""
        self.assertEqual(
            self.test_stream.unread_by_status_type_id(self.local_user.id),
            f"{self.local_user.id}-test-unread-by-type",
        )

    def test_get_rank(self, *_):
        """sort order"""
        date = datetime(2022, 1, 28, 0, 0, tzinfo=timezone.utc)
        status = models.Status.objects.create(
            user=self.remote_user,
            content="hi",
            privacy="direct",
            published_date=date,
        )
        self.assertEqual(
            str(self.test_stream.get_rank(status)),
            "1643328000.0",
        )

    def test_get_activity_stream(self, *_):
        """load statuses"""
        status = models.Status.objects.create(
            user=self.remote_user,
            content="hi",
            privacy="direct",
        )
        status2 = models.Comment.objects.create(
            user=self.remote_user,
            content="hi",
            privacy="direct",
            film=self.film,
        )
        models.Comment.objects.create(
            user=self.remote_user,
            content="hi",
            privacy="direct",
            film=self.film,
        )
        with (
            patch("reeltalk.activitystreams.r.set"),
            patch("reeltalk.activitystreams.r.delete"),
            patch("reeltalk.activitystreams.ActivityStream.get_store") as redis_mock,
        ):
            redis_mock.return_value = [status.id, status2.id]
            result = self.test_stream.get_activity_stream(self.local_user)
        self.assertEqual(result.count(), 2)
        self.assertEqual(result.first(), status2)
        self.assertEqual(result.last(), status)
        self.assertIsInstance(result.first(), models.Comment)

    def test_abstractstream_get_audience(self, *_):
        """get a list of users that should see a status"""
        status = models.Status.objects.create(
            user=self.remote_user, content="hi", privacy="public"
        )
        users = self.test_stream.get_audience(status)
        # remote users don't have feeds
        self.assertFalse(self.remote_user.id in users)
        self.assertTrue(self.local_user.id in users)
        self.assertTrue(self.another_user.id in users)

    def test_abstractstream_get_audience_direct(self, *_):
        """get a list of users that should see a status"""
        status = models.Status.objects.create(
            user=self.remote_user,
            content="hi",
            privacy="direct",
        )
        status.mention_users.add(self.local_user)
        users = self.test_stream.get_audience(status)
        self.assertEqual(users, [])

        status = models.Comment.objects.create(
            user=self.remote_user,
            content="hi",
            privacy="direct",
            film=self.film,
        )
        status.mention_users.add(self.local_user)
        users = self.test_stream.get_audience(status)
        self.assertTrue(self.local_user.id in users)
        self.assertFalse(self.another_user.id in users)
        self.assertFalse(self.remote_user.id in users)

    def test_abstractstream_get_audience_followers_remote_user(self, *_):
        """get a list of users that should see a status"""
        status = models.Status.objects.create(
            user=self.remote_user,
            content="hi",
            privacy="followers",
        )
        users = self.test_stream.get_audience(status)
        self.assertEqual(users, [])

    def test_abstractstream_get_audience_followers_self(self, *_):
        """get a list of users that should see a status"""
        status = models.Comment.objects.create(
            user=self.local_user,
            content="hi",
            privacy="direct",
            film=self.film,
        )
        users = self.test_stream.get_audience(status)
        self.assertTrue(self.local_user.id in users)
        self.assertFalse(self.another_user.id in users)
        self.assertFalse(self.remote_user.id in users)

    def test_abstractstream_get_audience_followers_with_mention(self, *_):
        """get a list of users that should see a status"""
        status = models.Comment.objects.create(
            user=self.remote_user,
            content="hi",
            privacy="direct",
            film=self.film,
        )
        status.mention_users.add(self.local_user)

        users = self.test_stream.get_audience(status)
        self.assertTrue(self.local_user.id in users)
        self.assertFalse(self.another_user.id in users)
        self.assertFalse(self.remote_user.id in users)

    def test_abstractstream_get_audience_followers_with_relationship(self, *_):
        """get a list of users that should see a status"""
        self.remote_user.followers.add(self.local_user)
        status = models.Comment.objects.create(
            user=self.remote_user,
            content="hi",
            privacy="direct",
            film=self.film,
        )
        users = self.test_stream.get_audience(status)
        self.assertFalse(self.local_user.id in users)
        self.assertFalse(self.another_user.id in users)
        self.assertFalse(self.remote_user.id in users)

    def test_abstractstream_exclude_films(self, *_):
        """exlude users who have blocked a film"""

        self.local_user.blocked_films.add(self.film)

        status = models.Comment.objects.create(
            user=self.remote_user,
            content="This book is awful",
            privacy="public",
            film=self.film,
        )

        users = self.test_stream.get_audience(status)
        self.assertTrue(self.another_user.id in users)
        self.assertFalse(self.local_user.id in users)

    def test_abstractstream_exclude_films_in_thread(self, *_):
        """exlude users who have blocked a film mentioned earlier in the thread"""

        self.local_user.blocked_films.add(self.film)

        parent_status = models.Comment.objects.create(
            user=self.remote_user,
            content="This book is awful",
            privacy="public",
            film=self.film,
        )
        status = models.Status.objects.create(
            user=self.remote_user,
            content="a bad reply to an awful book",
            privacy="public",
            reply_parent=parent_status,
        )

        users = self.test_stream.get_audience(status)
        self.assertTrue(self.another_user.id in users)
        self.assertFalse(self.local_user.id in users)
