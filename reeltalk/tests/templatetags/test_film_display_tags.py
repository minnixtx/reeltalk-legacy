"""style fixes and lookups for templates"""

from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from reeltalk import models
from reeltalk.templatetags import film_display_tags


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.remove_status_task.delay")
class FilmDisplayTags(TestCase):
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

    def test_get_film_description(self, *_):
        """grab it from the film"""
        self.assertIsNone(film_display_tags.get_film_description(self.film))

        self.film.description = "hello"
        self.film.save(broadcast=False)
        self.assertEqual(
            film_display_tags.get_film_description(self.film), "hello"
        )

    def test_get_review_count(self, *_):
        """count non-deleted reviews"""
        self.assertEqual(film_display_tags.get_review_count(self.film), 0)

        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.Review.objects.create(user=self.user, film=self.film, rating=3)
            deleted = models.Review.objects.create(
                user=self.user, film=self.film, rating=4
            )
        deleted.delete()
        self.assertEqual(film_display_tags.get_review_count(self.film), 1)

    def test_blocked_film_filter_anonymous(self, *_):
        """no viewer means nothing is filtered"""
        queryset = models.Review.objects
        self.assertEqual(
            film_display_tags.blocked_film_filter(queryset, None), queryset
        )
        self.assertEqual(
            film_display_tags.blocked_film_filter(queryset, AnonymousUser()),
            queryset,
        )

    def test_blocked_film_filter(self, *_):
        """statuses about blocked films are excluded"""
        other_film = models.Film.objects.create(title="Other Film")
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            kept = models.Review.objects.create(
                user=self.user, film=other_film, rating=3
            )
            dropped = models.Review.objects.create(
                user=self.user, film=self.film, rating=4
            )

        self.user.blocked_films.add(self.film)

        results = film_display_tags.blocked_film_filter(
            models.Review.objects, self.user
        )
        self.assertIn(kept, results)
        self.assertNotIn(dropped, results)

    def test_blocked_film_filter_no_film_field(self, *_):
        """querysets without a film field are returned untouched"""
        other_film = models.Film.objects.create(title="Other Film")
        self.user.blocked_films.add(self.film)

        results = film_display_tags.blocked_film_filter(
            models.Film.objects, self.user
        )
        self.assertEqual(results.count(), 2)
