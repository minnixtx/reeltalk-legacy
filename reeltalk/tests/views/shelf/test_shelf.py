"""test for app action functionality"""

from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.activitypub import ActivitypubResponse
from reeltalk.tests.validate_html import validate_html


class ShelfViews(TestCase):
    """shelf page views"""

    @classmethod
    def setUpTestData(cls):
        """we need basic test data and mocks"""
        cls.local_user = models.User.objects.create_user(
            "mouse@local.com",
            "mouse@mouse.com",
            "mouseword",
            local=True,
            localname="mouse",
            remote_id="https://example.com/users/mouse",
        )
        cls.film = models.Film.objects.create(title="Example Film")
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            cls.shelf = models.Shelf.objects.create(
                name="Test Shelf", identifier="test-shelf", user=cls.local_user
            )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()
        self.anonymous_user = AnonymousUser
        self.anonymous_user.is_authenticated = False

    def test_shelf_page_all_films(self):
        """there are so many views, this just makes sure it LOADS"""
        models.ShelfFilm.objects.create(
            film=self.film,
            shelf=self.shelf,
            user=self.local_user,
        )
        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username=self.local_user.username)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_all_films_empty(self):
        """No films shelved"""
        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username=self.local_user.username)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_all_films_avoid_duplicates(self):
        """Make sure films aren't showing up twice on the all shelves view"""
        models.ShelfFilm.objects.create(
            film=self.film,
            shelf=self.shelf,
            user=self.local_user,
        )
        models.ShelfFilm.objects.create(
            film=self.film,
            shelf=self.local_user.shelf_set.first(),
            user=self.local_user,
        )
        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username=self.local_user.username)
        self.assertEqual(result.context_data["films"].object_list.count(), 1)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_all_films_json(self):
        """there is no json view here"""
        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, username=self.local_user.username)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_all_films_anonymous(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username=self.local_user.username)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_private(self):
        models.User.objects.filter(id=self.local_user.id).update(
            is_profile_private=True
        )
        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.anonymous_user
        result = view(request, username=self.local_user.localname)
        self.assertTrue(result.context_data["is_profile_locked"])

    def test_shelf_page_sorted_shelved(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("", {"sort": "shelved_date"})
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(
                request,
                username=self.local_user.username,
                shelf_identifier=shelf.identifier,
            )
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_sorted_rating(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("", {"sort": "rating"})
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(
                request,
                username=self.local_user.username,
                shelf_identifier=shelf.identifier,
            )
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_sorted_director(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("", {"sort": "director"})
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(
                request,
                username=self.local_user.username,
                shelf_identifier=shelf.identifier,
            )
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_sorted_title(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("", {"sort": "sort_title"})
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(
                request,
                username=self.local_user.username,
                shelf_identifier=shelf.identifier,
            )
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_sorted_garbled(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("", {"sort": "sort_titledfdfgfdg"})
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(
                request,
                username=self.local_user.username,
                shelf_identifier=shelf.identifier,
            )
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_implicit_sort(self):
        """ensure the shelf view always has a sort in its response"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(
                request,
                username=self.local_user.username,
                shelf_identifier=shelf.identifier,
            )
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertIsNotNone(result.context_data["sort"])
        self.assertNotEqual("", result.context_data["sort"])
        self.assertEqual(result.status_code, 200)

    def test_shelf_page(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(
                request,
                username=self.local_user.username,
                shelf_identifier=shelf.identifier,
            )
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = True
            result = view(
                request,
                username=self.local_user.username,
                shelf_identifier=shelf.identifier,
            )
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

        request = self.factory.get("/?page=1")
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = True
            result = view(
                request,
                username=self.local_user.username,
                shelf_identifier=shelf.identifier,
            )
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

    def test_filter_shelf_found(self):
        """display films that match a filter keyword"""
        models.ShelfFilm.objects.create(
            film=self.film,
            shelf=self.shelf,
            user=self.local_user,
        )
        shelf_film = models.ShelfFilm.objects.create(
            film=self.film,
            shelf=self.local_user.shelf_set.first(),
            user=self.local_user,
        )
        view = views.Shelf.as_view()
        request = self.factory.get("", {"filter": shelf_film.film.title})
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username=self.local_user.username)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.context_data["films"].object_list), 1)
        self.assertEqual(
            result.context_data["films"].object_list[0].title,
            shelf_film.film.title,
        )

    def test_filter_shelf_none(self):
        """display a message when no films match a filter keyword"""
        models.ShelfFilm.objects.create(
            film=self.film,
            shelf=self.shelf,
            user=self.local_user,
        )
        view = views.Shelf.as_view()
        request = self.factory.get("", {"filter": "NOPE"})
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username=self.local_user.username)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.context_data["films"].object_list), 0)

    def test_shelf_excludes_blocked(self):
        """are blocked films actually blocked?"""
        shelf = models.Shelf.objects.get(user=self.local_user, identifier="read")
        awful_film = models.Film.objects.create(
            title="Awful Film",
            remote_id="https://example.com/film/99",
        )

        models.ShelfFilm.objects.create(
            shelf=shelf, user=self.local_user, film=awful_film
        )
        models.ShelfFilm.objects.create(
            shelf=shelf, user=self.local_user, film=self.film
        )

        self.local_user.blocked_films.add(awful_film)

        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request, username=request.user.username)

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.context_data["films"].object_list), 1)
        self.assertFalse(awful_film in result.context_data["films"].object_list)
        self.assertEqual(result.context_data["films"].object_list, [self.film])
