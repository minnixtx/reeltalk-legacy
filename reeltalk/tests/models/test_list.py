"""testing models"""

from uuid import UUID
from unittest.mock import patch
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from reeltalk import activitypub
from reeltalk import models, settings


@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
@patch("reeltalk.lists_stream.remove_list_task.delay")
class List(TestCase):
    """some activitypub oddness ahead"""

    @classmethod
    def setUpTestData(cls):
        """look, a list"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse", "mouse@mouse.mouse", "mouseword", local=True, localname="mouse"
            )
            cls.another_user = models.User.objects.create_user(
                "rat", "rat@rat.rat", "ratword", local=True, localname="rat"
            )
        cls.film = models.Film.objects.create(title="Test Film")

    def test_remote_id(self, *_):
        """lists use custom remote ids"""
        film_list = models.List.objects.create(name="Test List", user=self.local_user)
        expected_id = f"{settings.BASE_URL}/list/{film_list.id}"
        self.assertEqual(film_list.get_remote_id(), expected_id)

    def test_to_activity_list(self, *_):
        """jsonify it"""
        film_list = models.List.objects.create(name="Test List", user=self.local_user)
        activity_json = film_list.to_activity()
        self.assertIsInstance(activity_json, dict)
        self.assertEqual(activity_json["id"], film_list.remote_id)
        self.assertEqual(activity_json["totalItems"], 0)
        self.assertEqual(activity_json["type"], "FilmList")
        self.assertEqual(activity_json["name"], "Test List")
        self.assertEqual(activity_json["owner"], self.local_user.remote_id)

    def test_list_item(self, *_):
        """a list entry"""
        film_list = models.List.objects.create(
            name="Test List", user=self.local_user, privacy="unlisted"
        )

        item = models.ListItem.objects.create(
            film_list=film_list,
            film=self.film,
            user=self.local_user,
            order=1,
        )

        self.assertTrue(item.approved)
        self.assertEqual(item.privacy, "unlisted")
        self.assertEqual(item.recipients, [])
        self.assertEqual(item.film, self.film)
        self.assertEqual(item.order, 1)
        self.assertEqual(film_list.films.first(), self.film)

    def test_list_item_pending(self, *_):
        """a list entry"""
        film_list = models.List.objects.create(name="Test List", user=self.local_user)

        item = models.ListItem.objects.create(
            film_list=film_list,
            film=self.film,
            user=self.local_user,
            approved=False,
            order=1,
        )

        self.assertFalse(item.approved)
        self.assertEqual(film_list.privacy, "public")
        self.assertEqual(item.privacy, "direct")
        self.assertEqual(item.recipients, [])

    def test_raise_not_submittable(self, *_):
        """user trying to add to list they shouldn't access"""
        film_list = models.List.objects.create(
            name="Test List", user=self.local_user, privacy="public", curation="open"
        )
        result = film_list.raise_not_submittable(self.another_user)
        self.assertIsNone(result)

        film_list = models.List.objects.create(
            name="Test List", user=self.local_user, privacy="public", curation="curated"
        )
        result = film_list.raise_not_submittable(self.another_user)
        self.assertIsNone(result)

        film_list = models.List.objects.create(
            name="Test List", user=self.local_user, privacy="public", curation="closed"
        )
        with self.assertRaises(PermissionDenied):
            film_list.raise_not_submittable(self.another_user)

    def test_embed_key(self, *_):
        """embed_key should never be empty"""
        film_list = models.List.objects.create(name="Test List", user=self.local_user)

        self.assertIsInstance(film_list.embed_key, UUID)
