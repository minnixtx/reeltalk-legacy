"""tests incoming activities"""

from unittest.mock import patch

from django.test import TestCase, TransactionTestCase

from reeltalk import models, views
from reeltalk.activitypub import ActivitySerializerError

FILM_ID = "https://example.com/film/1"


class TransactionInboxCreate(TransactionTestCase):
    """readthrough tests"""

    def setUp(self):
        """basic user and film data"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            self.local_user = models.User.objects.create_user(
                "mouse@example.com",
                "mouse@mouse.com",
                "mouseword",
                local=True,
                localname="mouse",
            )
        self.local_user.remote_id = "https://example.com/user/mouse"
        self.local_user.save(broadcast=False, update_fields=["remote_id"])
        with patch("reeltalk.models.user.set_remote_server.delay"):
            self.remote_user = models.User.objects.create_user(
                "rat",
                "rat@rat.com",
                "ratword",
                local=False,
                remote_id="https://example.com/users/rat",
                inbox="https://example.com/users/rat/inbox",
                outbox="https://example.com/users/rat/outbox",
            )

        self.create_json = {
            "id": "hi",
            "type": "Create",
            "actor": "hi",
            "to": ["https://www.w3.org/ns/activitystreams#public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "object": {},
        }

    def test_create_status_transaction(self, *_):
        """the "it justs works" mode"""
        models.Film.objects.create(title="Test Film", remote_id=FILM_ID)
        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/user/mouse/quotation/13",
            "url": "https://example.com/user/mouse/quotation/13",
            "published": "2020-05-10T02:38:31.150343+00:00",
            "attributedTo": "https://example.com/user/mouse",
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "sensitive": False,
            "content": "commentary",
            "type": "Quotation",
            "inReplyToFilm": FILM_ID,
            "quote": "quote body",
        }

        with patch("reeltalk.activitystreams.add_status_task.apply_async") as mock:
            views.inbox.activity_task(activity)
        self.assertEqual(mock.call_count, 0)


@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
class InboxCreate(TestCase):
    """readthrough tests"""

    @classmethod
    def setUpTestData(cls):
        """basic user and film data"""
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

        models.SiteSettings.objects.create()

    def setUp(self):
        """individual test setup"""
        self.film = models.Film.objects.create(title="Test Film", remote_id=FILM_ID)
        self.create_json = {
            "id": "hi",
            "type": "Create",
            "actor": "hi",
            "to": ["https://www.w3.org/ns/activitystreams#public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "object": {},
        }

    def test_create_status(self, *_):
        """the "it justs works" mode"""
        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/user/mouse/quotation/13",
            "url": "https://example.com/user/mouse/quotation/13",
            "published": "2020-05-10T02:38:31.150343+00:00",
            "attributedTo": "https://example.com/user/mouse",
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "sensitive": False,
            "content": "commentary",
            "type": "Quotation",
            "inReplyToFilm": FILM_ID,
            "quote": "quote body",
        }

        views.inbox.activity_task(activity)

        status = models.Quotation.objects.get()
        self.assertEqual(
            status.remote_id, "https://example.com/user/mouse/quotation/13"
        )
        self.assertEqual(status.quote, "quote body")
        self.assertEqual(status.content, "commentary")
        self.assertEqual(status.user, self.local_user)
        self.assertEqual(status.thread_id, status.id)

        # while we're here, lets ensure we avoid dupes
        views.inbox.activity_task(activity)
        self.assertEqual(models.Status.objects.count(), 1)

    def test_create_comment_with_reading_status(self, *_):
        """a comment on a film with a reading status"""
        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/user/mouse/comment/6",
            "url": "https://example.com/user/mouse/comment/6",
            "published": "2020-05-08T23:45:44.768012+00:00",
            "attributedTo": "https://example.com/user/mouse",
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "sensitive": False,
            "content": "commentary",
            "type": "Comment",
            "inReplyToFilm": FILM_ID,
            "readingStatus": "to-read",
        }

        views.inbox.activity_task(activity)

        status = models.Comment.objects.get()
        self.assertEqual(status.remote_id, "https://example.com/user/mouse/comment/6")
        self.assertEqual(status.content, "commentary")
        self.assertEqual(status.reading_status, "to-read")
        self.assertEqual(status.user, self.local_user)

        # while we're here, lets ensure we avoid dupes
        views.inbox.activity_task(activity)
        self.assertEqual(models.Status.objects.count(), 1)

    def test_create_status_remote_note_with_mention(self, *_):
        """should only create it under the right circumstances"""
        self.assertFalse(
            models.Notification.objects.filter(user=self.local_user).exists()
        )

        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/users/rat/statuses/1234567",
            "type": "Note",
            "published": "2020-12-13T05:09:29Z",
            "url": "https://example.com/@rat/1234567",
            "attributedTo": self.remote_user.remote_id,
            "to": ["https://example.com/user/mouse"],
            "cc": [],
            "sensitive": False,
            "content": "test content in note",
            "tag": [
                {
                    "type": "Mention",
                    "href": self.local_user.remote_id,
                    "name": "@mouse@example.com",
                }
            ],
        }

        views.inbox.activity_task(activity)

        status = models.Status.objects.last()
        self.assertEqual(status.content, "test content in note")
        self.assertEqual(status.mention_users.first(), self.local_user)
        self.assertTrue(
            models.Notification.objects.filter(user=self.local_user).exists()
        )
        self.assertEqual(models.Notification.objects.get().notification_type, "MENTION")

    def test_create_status_remote_note_with_reply(self, *_):
        """should only create it under the right circumstances"""
        parent_status = models.Status.objects.create(
            user=self.local_user,
            content="Test status",
            remote_id="https://example.com/status/1",
        )

        self.assertEqual(models.Status.objects.count(), 1)
        self.assertFalse(models.Notification.objects.filter(user=self.local_user))

        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/users/rat/statuses/1234567",
            "type": "Note",
            "published": "2020-12-13T05:09:29Z",
            "url": "https://example.com/@rat/1234567",
            "attributedTo": self.remote_user.remote_id,
            "to": ["https://example.com/user/mouse"],
            "cc": [],
            "sensitive": False,
            "content": "test content in note",
            "inReplyTo": parent_status.remote_id,
        }

        views.inbox.activity_task(activity)
        status = models.Status.objects.last()
        self.assertEqual(status.content, "test content in note")
        self.assertEqual(status.reply_parent, parent_status)
        self.assertEqual(status.thread_id, parent_status.id)
        self.assertTrue(models.Notification.objects.filter(user=self.local_user))
        self.assertEqual(models.Notification.objects.get().notification_type, "REPLY")

    def test_create_rating(self, *_):
        """a remote rating activity"""
        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/user/mouse/reviewrating/12",
            "type": "Rating",
            "published": "2021-04-29T21:27:30.014235+00:00",
            "attributedTo": "https://example.com/user/mouse",
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "sensitive": False,
            "inReplyToFilm": FILM_ID,
            "rating": 3,
        }
        views.inbox.activity_task(activity)
        rating = models.ReviewRating.objects.first()
        self.assertEqual(rating.film, self.film)
        self.assertEqual(rating.rating, 3.0)

    def test_create_list(self, *_):
        """a new list"""
        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/list/22",
            "type": "FilmList",
            "totalItems": 1,
            "first": "https://example.com/list/22?page=1",
            "last": "https://example.com/list/22?page=1",
            "name": "Test List",
            "owner": "https://example.com/user/mouse",
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "summary": "summary text",
            "curation": "curated",
        }
        views.inbox.activity_task(activity)
        film_list = models.List.objects.get()
        self.assertEqual(film_list.name, "Test List")
        self.assertEqual(film_list.curation, "curated")
        self.assertEqual(film_list.description, "summary text")
        self.assertEqual(film_list.remote_id, "https://example.com/list/22")

    def test_create_unsupported_type_question(self, *_):
        """ignore activities we know we can't handle"""
        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/status/887",
            "type": "Question",
        }
        # just observe how it doesn't throw an error
        views.inbox.activity_task(activity)

    def test_create_unsupported_type_article(self, *_):
        """special case in unsupported type because we do know what it is"""
        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/status/887",
            "type": "Article",
            "name": "hello",
            "published": "2021-04-29T21:27:30.014235+00:00",
            "attributedTo": "https://example.com/user/mouse",
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "sensitive": False,
        }
        # just observe how it doesn't throw an error
        views.inbox.activity_task(activity)

    def test_create_unsupported_type_unknown(self, *_):
        """Something truly unexpected should throw an error"""
        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/status/887",
            "type": "Blaaaah",
        }
        # error this time
        with self.assertRaises(ActivitySerializerError):
            views.inbox.activity_task(activity)

    def test_create_unknown_type(self, *_):
        """ignore activities we know we've never heard of"""
        activity = self.create_json
        activity["object"] = {
            "id": "https://example.com/status/887",
            "type": "Threnody",
        }
        with self.assertRaises(ActivitySerializerError):
            views.inbox.activity_task(activity)
