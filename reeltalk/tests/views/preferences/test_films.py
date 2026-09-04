"""test for app action functionality"""

from unittest.mock import patch

from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.tests.validate_html import validate_html


@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
class BlockedFilmsViews(TestCase):
    """block and unblock films"""

    @classmethod
    def setUpTestData(cls):
        """we need basic test data and mocks"""

        cls.local_user = models.User.objects.create_user(
            "mouse@local.com",
            "mouse@mouse.mouse",
            "password",
            local=True,
            localname="mouse",
        )

        cls.film = models.Film.objects.create(
            title="Example Film",
            remote_id="https://example.com/film/1",
        )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    def test_block_get(self, _):
        """there are so many views, this just makes sure it LOADS"""
        view = views.BlockedFilms.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_block_film(self, _):
        """block a film"""

        self.assertFalse(self.film in self.local_user.blocked_films.all())

        view = views.BlockedFilms.as_view()
        request = self.factory.post("")
        request.user = self.local_user

        with patch("reeltalk.activitystreams.remove_blocked_film_statuses_task.delay"):
            view(request, self.film.id)

        self.assertTrue(self.film in self.local_user.blocked_films.all())

    def test_unblock_film(self, _):
        """undo a block"""

        self.local_user.blocked_films.add(self.film)
        self.assertTrue(self.film in self.local_user.blocked_films.all())

        request = self.factory.post("")
        request.user = self.local_user
        with patch("reeltalk.activitystreams.add_blocked_film_statuses_task.delay"):
            views.unblock_film(request, self.film.id)

        self.assertFalse(self.film in self.local_user.blocked_films.all())
