"""testing activitystreams"""

import itertools

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

    def test_get_statuses_for_user_films(self, *_):
        """create a stream for a user"""
        # generic (non-film) status must be filtered out of the stream
        models.Status.objects.create(
            user=self.local_user, content="hi", privacy="public"
        )
        comment = models.Comment.objects.create(
            user=self.remote_user, content="hi", privacy="public", film=self.film
        )
        models.ShelfFilm.objects.create(
            user=self.local_user,
            shelf=self.local_user.shelf_set.first(),
            film=self.film,
        )
        # yes film, yes audience
        result = activitystreams.FilmsStream().get_statuses_for_user(self.local_user)
        self.assertEqual(list(result), [comment])

    def test_film_statuses(self, *_):
        """statuses about a film"""
        # generic (non-film) status must be filtered out of the stream
        models.Status.objects.create(
            user=self.local_user, content="hi", privacy="public"
        )
        comment = models.Comment.objects.create(
            user=self.remote_user, content="hi", privacy="public", film=self.film
        )
        models.ShelfFilm.objects.create(
            user=self.local_user,
            shelf=self.local_user.shelf_set.first(),
            film=self.film,
        )

        class RedisMockCounter:
            """keep track of calls to mock redis store"""

            calls = []

            def bulk_add_objects_to_store(self, objs, store):
                """keep track of bulk_add_objects_to_store calls"""
                self.calls.append((objs, store))

        redis_mock_counter = RedisMockCounter()
        with patch(
            "reeltalk.activitystreams.FilmsStream.bulk_add_objects_to_store"
        ) as redis_mock:
            redis_mock.side_effect = redis_mock_counter.bulk_add_objects_to_store
            activitystreams.FilmsStream().add_film_statuses(self.local_user, self.film)

        self.assertEqual(sum(map(lambda x: x[0].count(), redis_mock_counter.calls)), 1)
        self.assertTrue(
            comment
            in itertools.chain.from_iterable(
                map(lambda x: x[0], redis_mock_counter.calls)
            )
        )
        for call in redis_mock_counter.calls:
            self.assertEqual(call[1], f"{self.local_user.id}-films")
