"""tests incoming activities"""

from unittest.mock import patch

from django.test import TestCase
import responses

from reeltalk import models, views


class InboxActivities(TestCase):
    """inbox tests"""

    @classmethod
    def setUpTestData(cls):
        """basic user and book data"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse@example.com",
                "mouse@mouse.com",
                "mouseword",
                local=True,
                localname="mouse",
            )
        cls.local_user.remote_id = "https://example.com/user/mouse"
        cls.local_user.save(broadcast=False, update_fields=["remote_id"])
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

        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.activitystreams.add_status_task.delay"),
        ):
            cls.status = models.Status.objects.create(
                user=cls.local_user,
                content="Test status",
                remote_id="https://example.com/status/1",
            )

    def setUp(self):
        """individual test setup"""
        self.create_json = {
            "id": "hi",
            "type": "Create",
            "actor": "hi",
            "to": ["https://www.w3.org/ns/activitystreams#public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "object": {},
        }

    @patch("reeltalk.activitystreams.handle_boost_task.delay")
    def test_boost(self, _):
        """boost a status"""
        self.assertEqual(models.Notification.objects.count(), 0)
        activity = {
            "type": "Announce",
            "id": f"{self.status.remote_id}/boost",
            "actor": self.remote_user.remote_id,
            "object": self.status.remote_id,
            "to": ["https://www.w3.org/ns/activitystreams#public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "published": "Mon, 25 May 2020 19:31:20 GMT",
        }
        with patch("reeltalk.models.status.Status.ignore_activity") as discarder:
            discarder.return_value = False
            views.inbox.activity_task(activity)

        # boost created of correct status
        boost = models.Boost.objects.get()
        self.assertEqual(boost.boosted_status, self.status)

        # notification sent to original poster
        notification = models.Notification.objects.get()
        self.assertEqual(notification.user, self.local_user)
        self.assertEqual(notification.related_status, self.status)

    @responses.activate
    @patch("reeltalk.activitystreams.handle_boost_task.delay")
    def test_boost_remote_status(self, _):
        """boost a status from a remote server"""
        film = models.Film.objects.create(
            title="Test",
            remote_id="https://bookwyrm.social/film/37292",
        )
        self.assertEqual(models.Notification.objects.count(), 0)
        activity = {
            "type": "Announce",
            "id": f"{self.status.remote_id}/boost",
            "actor": self.remote_user.remote_id,
            "object": "https://remote.com/status/1",
            "to": ["https://www.w3.org/ns/activitystreams#public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "published": "Mon, 25 May 2020 19:31:20 GMT",
        }
        responses.add(
            responses.GET,
            "https://remote.com/status/1",
            json={
                "id": "https://remote.com/status/1",
                "type": "Comment",
                "published": "2021-04-05T18:04:59.735190+00:00",
                "attributedTo": self.remote_user.remote_id,
                "content": "<p>a comment</p>",
                "to": ["https://www.w3.org/ns/activitystreams#Public"],
                "cc": ["https://b875df3d118b.ngrok.io/user/mouse/followers"],
                "inReplyTo": "",
                "inReplyToFilm": "https://bookwyrm.social/film/37292",
                "summary": "",
                "tag": [],
                "sensitive": False,
                "@context": "https://www.w3.org/ns/activitystreams",
            },
        )

        with patch("reeltalk.models.status.Status.ignore_activity") as discarder:
            discarder.return_value = False
            views.inbox.activity_task(activity)

        boost = models.Boost.objects.get()
        self.assertEqual(boost.boosted_status.remote_id, "https://remote.com/status/1")
        self.assertEqual(boost.boosted_status.comment.status_type, "Comment")
        self.assertEqual(boost.boosted_status.comment.film, film)

    @responses.activate
    def test_discarded_boost(self):
        """test a boost of a mastodon status that will be discarded"""
        status = models.Status(
            content="hi",
            user=self.remote_user,
        )
        with patch("reeltalk.activitystreams.add_status_task.delay"):
            status.save(broadcast=False)
        activity = {
            "type": "Announce",
            "id": "http://www.faraway.com/boost/12",
            "actor": self.remote_user.remote_id,
            "object": status.remote_id,
            "to": ["https://www.w3.org/ns/activitystreams#public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "published": "Mon, 25 May 2020 19:31:20 GMT",
        }
        responses.add(
            responses.GET, status.remote_id, json=status.to_activity(), status=200
        )
        views.inbox.activity_task(activity)
        self.assertEqual(models.Boost.objects.count(), 0)

    @patch("reeltalk.activitystreams.add_status_task.delay")
    @patch("reeltalk.activitystreams.handle_boost_task.delay")
    @patch("reeltalk.activitystreams.remove_status_task.delay")
    def test_unboost(self, *_):
        """undo a boost"""
        boost = models.Boost.objects.create(
            boosted_status=self.status, user=self.remote_user
        )
        activity = {
            "type": "Undo",
            "actor": "hi",
            "id": "bleh",
            "to": ["https://www.w3.org/ns/activitystreams#public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "object": {
                "type": "Announce",
                "id": boost.remote_id,
                "actor": self.remote_user.remote_id,
                "object": self.status.remote_id,
                "to": ["https://www.w3.org/ns/activitystreams#public"],
                "cc": ["https://example.com/user/mouse/followers"],
                "published": "Mon, 25 May 2020 19:31:20 GMT",
            },
        }
        views.inbox.activity_task(activity)
        self.assertFalse(models.Boost.objects.exists())

    def test_unboost_unknown_boost(self):
        """undo a boost"""
        activity = {
            "type": "Undo",
            "actor": "hi",
            "id": "bleh",
            "to": ["https://www.w3.org/ns/activitystreams#public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "object": {
                "type": "Announce",
                "id": "http://fake.com/unknown/boost",
                "actor": self.remote_user.remote_id,
                "object": self.status.remote_id,
                "published": "Mon, 25 May 2020 19:31:20 GMT",
            },
        }
        views.inbox.activity_task(activity)
