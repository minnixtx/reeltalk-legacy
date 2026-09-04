"""testing activitystreams"""

from unittest.mock import patch
from django.test import TestCase
from reeltalk import activitystreams, models


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
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            cls.status = models.Status.objects.create(content="hi", user=cls.local_user)

    def test_add_film_statuses_task(self):
        """statuses related to a film"""
        with patch("reeltalk.activitystreams.FilmsStream.add_film_statuses") as mock:
            activitystreams.add_film_statuses_task(self.local_user.id, self.film.id)
        self.assertTrue(mock.called)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.local_user)
        self.assertEqual(args[1], self.film)

    def test_remove_film_statuses_task(self):
        """remove statuses related to a film"""
        with patch("reeltalk.activitystreams.FilmsStream.remove_film_statuses") as mock:
            activitystreams.remove_film_statuses_task(self.local_user.id, self.film.id)
        self.assertTrue(mock.called)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.local_user)
        self.assertEqual(args[1], self.film)

    def test_populate_stream_task(self):
        """populate a given stream"""
        with patch("reeltalk.activitystreams.FilmsStream.populate_streams") as mock:
            activitystreams.populate_stream_task("films", self.local_user.id)
        self.assertTrue(mock.called)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.local_user)

        with patch("reeltalk.activitystreams.HomeStream.populate_streams") as mock:
            activitystreams.populate_stream_task("home", self.local_user.id)
        self.assertTrue(mock.called)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.local_user)

    def test_remove_status_task(self):
        """remove a status from all streams"""
        with patch(
            "reeltalk.activitystreams.ActivityStream.remove_object_from_stores"
        ) as mock:
            activitystreams.remove_status_task(self.status.id)
        self.assertEqual(mock.call_count, 3)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.status)

    def test_add_status_task(self):
        """add a status to all streams"""
        with patch("reeltalk.activitystreams.ActivityStream.add_status") as mock:
            activitystreams.add_status_task(self.status.id)
        self.assertEqual(mock.call_count, 3)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.status)

    def test_remove_user_statuses_task(self):
        """remove all statuses by a user from another users' feeds"""
        with patch(
            "reeltalk.activitystreams.ActivityStream.remove_user_statuses"
        ) as mock:
            activitystreams.remove_user_statuses_task(
                self.local_user.id, self.another_user.id
            )
        self.assertEqual(mock.call_count, 3)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.local_user)
        self.assertEqual(args[1], self.another_user)

        with patch("reeltalk.activitystreams.HomeStream.remove_user_statuses") as mock:
            activitystreams.remove_user_statuses_task(
                self.local_user.id, self.another_user.id, stream_list=["home"]
            )
        self.assertEqual(mock.call_count, 1)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.local_user)
        self.assertEqual(args[1], self.another_user)

    def test_add_user_statuses_task(self):
        """add a user's statuses to another users feeds"""
        with patch("reeltalk.activitystreams.ActivityStream.add_user_statuses") as mock:
            activitystreams.add_user_statuses_task(
                self.local_user.id, self.another_user.id
            )
        self.assertEqual(mock.call_count, 3)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.local_user)
        self.assertEqual(args[1], self.another_user)

        with patch("reeltalk.activitystreams.HomeStream.add_user_statuses") as mock:
            activitystreams.add_user_statuses_task(
                self.local_user.id, self.another_user.id, stream_list=["home"]
            )
        self.assertEqual(mock.call_count, 1)
        args = mock.call_args[0]
        self.assertEqual(args[0], self.local_user)
        self.assertEqual(args[1], self.another_user)

    @patch("reeltalk.activitystreams.LocalStream.remove_object_from_stores")
    @patch("reeltalk.activitystreams.FilmsStream.remove_object_from_stores")
    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    def test_boost_to_another_timeline(self, *_):
        """boost from a non-follower doesn't remove original status from feed"""
        status = models.Status.objects.create(user=self.local_user, content="hi")
        with patch("reeltalk.activitystreams.handle_boost_task.delay"):
            boost = models.Boost.objects.create(
                boosted_status=status,
                user=self.another_user,
            )
        with patch(
            "reeltalk.activitystreams.HomeStream.remove_object_from_stores"
        ) as mock:
            activitystreams.handle_boost_task(boost.id)

        self.assertTrue(mock.called)
        self.assertEqual(mock.call_count, 1)
        call_args = mock.call_args
        self.assertEqual(call_args[0][0], status)
        self.assertEqual(call_args[0][1], [f"{self.another_user.id}-home"])

    @patch("reeltalk.activitystreams.LocalStream.remove_object_from_stores")
    @patch("reeltalk.activitystreams.FilmsStream.remove_object_from_stores")
    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    def test_boost_to_another_timeline_remote(self, *_):
        """boost from a remote non-follower doesn't remove original status from feed"""
        status = models.Status.objects.create(user=self.local_user, content="hi")
        with patch("reeltalk.activitystreams.handle_boost_task.delay"):
            boost = models.Boost.objects.create(
                boosted_status=status,
                user=self.remote_user,
            )
        with patch(
            "reeltalk.activitystreams.HomeStream.remove_object_from_stores"
        ) as mock:
            activitystreams.handle_boost_task(boost.id)

        self.assertTrue(mock.called)
        self.assertEqual(mock.call_count, 1)
        call_args = mock.call_args
        self.assertEqual(call_args[0][0], status)
        self.assertEqual(call_args[0][1], [])

    @patch("reeltalk.activitystreams.LocalStream.remove_object_from_stores")
    @patch("reeltalk.activitystreams.FilmsStream.remove_object_from_stores")
    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    def test_boost_to_following_timeline(self, *_):
        """add a boost and deduplicate the boosted status on the timeline"""
        self.local_user.following.add(self.another_user)
        status = models.Status.objects.create(user=self.local_user, content="hi")
        with patch("reeltalk.activitystreams.handle_boost_task.delay"):
            boost = models.Boost.objects.create(
                boosted_status=status,
                user=self.another_user,
            )
        with patch(
            "reeltalk.activitystreams.HomeStream.remove_object_from_stores"
        ) as mock:
            activitystreams.handle_boost_task(boost.id)
        self.assertTrue(mock.called)
        call_args = mock.call_args
        self.assertEqual(call_args[0][0], status)
        self.assertTrue(f"{self.another_user.id}-home" in call_args[0][1])
        self.assertTrue(f"{self.local_user.id}-home" in call_args[0][1])

    @patch("reeltalk.activitystreams.LocalStream.remove_object_from_stores")
    @patch("reeltalk.activitystreams.FilmsStream.remove_object_from_stores")
    @patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
    def test_boost_to_same_timeline(self, *_):
        """add a boost and deduplicate the boosted status on the timeline"""
        status = models.Status.objects.create(user=self.local_user, content="hi")
        with patch("reeltalk.activitystreams.handle_boost_task.delay"):
            boost = models.Boost.objects.create(
                boosted_status=status,
                user=self.local_user,
            )
        with patch(
            "reeltalk.activitystreams.HomeStream.remove_object_from_stores"
        ) as mock:
            activitystreams.handle_boost_task(boost.id)
        self.assertTrue(mock.called)
        call_args = mock.call_args
        self.assertEqual(call_args[0][0], status)
        self.assertEqual(call_args[0][1], [f"{self.local_user.id}-home"])
