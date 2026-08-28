"""testing the annual summary page"""

import datetime
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.tests.validate_html import validate_html


def make_date(*args):
    """helper function to easily generate a date obj"""
    return datetime.datetime(*args, tzinfo=datetime.timezone.utc)


class AnnualSummary(TestCase):
    """views"""

    @classmethod
    def setUpTestData(cls):
        """we need basic test data and mocks"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.local_user = models.User.objects.create_user(
                "mouse@local.com",
                "mouse@mouse.com",
                "mouseword",
                local=True,
                localname="mouse",
                remote_id="https://example.com/users/mouse",
                summary_keys={"2020": "0123456789"},
            )
        cls.film = models.Film.objects.create(
            title="Example Film",
            remote_id="https://example.com/film/1",
        )

    def setUp(self):
        """individual test setup"""
        self.year = "2020"
        self.factory = RequestFactory()
        self.anonymous_user = AnonymousUser
        self.anonymous_user.is_authenticated = False

    def shelve_film(self, film, year_date, shelf_identifier="read"):
        """add a film to one of the user's shelves on a given date"""
        shelf = self.local_user.shelf_set.get(identifier=shelf_identifier)
        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.activitystreams.add_film_statuses_task.delay"),
        ):
            models.ShelfFilm.objects.create(
                film=film,
                shelf=shelf,
                user=self.local_user,
                shelved_date=year_date,
            )

    def test_annual_summary_not_authenticated(self, *_):
        """there are so many views, this just makes sure it DOESN'T LOAD"""
        view = views.AnnualSummary.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user

        with self.assertRaises(Http404):
            view(request, self.local_user.localname, self.year)

    def test_annual_summary_not_authenticated_with_key(self, *_):
        """there are so many views, this just makes sure it DOES LOAD"""
        key = self.local_user.summary_keys[self.year]
        view = views.AnnualSummary.as_view()
        request_url = (
            f"user/{self.local_user.localname}/{self.year}-in-review?key={key}"
        )
        request = self.factory.get(request_url)
        request.user = self.anonymous_user

        result = view(request, self.local_user.localname, self.year)

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_annual_summary_wrong_year(self, *_):
        """there are so many views, this just makes sure it DOESN'T LOAD"""
        view = views.AnnualSummary.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user

        with self.assertRaises(Http404):
            view(request, self.local_user.localname, "2019")

    def test_annual_summary_empty_page(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        view = views.AnnualSummary.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        result = view(request, self.local_user.localname, self.year)

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_annual_summary_page(self, *_):
        """there are so many views, this just makes sure it LOADS"""
        self.shelve_film(self.film, make_date(2020, 1, 1))

        view = views.AnnualSummary.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        result = view(request, self.local_user.localname, self.year)

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_annual_summary_page_with_review(self, *_):
        """there are so many views, this just makes sure it LOADS"""

        models.Review.objects.create(
            name="Review name",
            content="test content",
            rating=3.0,
            user=self.local_user,
            film=self.film,
        )

        self.shelve_film(self.film, make_date(2020, 1, 1))

        view = views.AnnualSummary.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        result = view(request, self.local_user.localname, self.year)

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_personal_annual_summary(self, *_):
        """redirect to unique user url"""
        view = views.personal_annual_summary
        request = self.factory.get("")
        request.user = self.local_user

        result = view(request, 2020)

        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, "/user/mouse/2020-in-review")

    def test_summary_add_key(self, *_):
        """add shareable key"""
        self.assertFalse("2022" in self.local_user.summary_keys.keys())

        request = self.factory.post("", {"year": "2022"})
        request.user = self.local_user

        result = views.summary_add_key(request)

        self.assertEqual(result.status_code, 302)
        self.assertIsNotNone(self.local_user.summary_keys["2022"])

    def test_summary_revoke_key(self, *_):
        """add shareable key"""
        self.assertTrue("2020" in self.local_user.summary_keys.keys())

        request = self.factory.post("", {"year": "2020"})
        request.user = self.local_user

        result = views.summary_revoke_key(request)

        self.assertEqual(result.status_code, 302)
        self.assertFalse("2020" in self.local_user.summary_keys.keys())

    def test_annual_summary_with_blocked_film(self, *_):
        """don't show blocked films"""

        bad_film = models.Film.objects.create(
            title="Bad Film",
            remote_id="https://example.com/film/666",
        )

        self.shelve_film(self.film, make_date(2020, 1, 1))
        self.shelve_film(bad_film, make_date(2020, 1, 2))

        self.local_user.blocked_films.add(bad_film)

        view = views.AnnualSummary.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        result = view(request, self.local_user.localname, self.year)

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        self.assertFalse(result.context_data["films"].contains(bad_film))
        self.assertTrue(result.context_data["films"].contains(self.film))
