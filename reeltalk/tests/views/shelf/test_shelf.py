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
    """tag views"""

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
        cls.work = models.Work.objects.create(title="Test Work")
        cls.book = models.Edition.objects.create(
            title="Example Edition",
            remote_id="https://example.com/book/1",
            parent_work=cls.work,
        )
        cls.shelf = models.Shelf.objects.create(
            name="Test Shelf", identifier="test-shelf", user=cls.local_user
        )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()
        self.anonymous_user = AnonymousUser
        self.anonymous_user.is_authenticated = False

    def test_shelf_page_all_books(self):
        """there are so many views, this just makes sure it LOADS"""
        models.ShelfBook.objects.create(
            book=self.book,
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

    def test_shelf_page_all_books_empty(self):
        """No books shelved"""
        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username=self.local_user.username)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_all_books_avoid_duplicates(self):
        """Make sure books aren't showing up twice on the all shelves view"""
        models.ShelfBook.objects.create(
            book=self.book,
            shelf=self.shelf,
            user=self.local_user,
        )
        models.ShelfBook.objects.create(
            book=self.book,
            shelf=self.local_user.shelf_set.first(),
            user=self.local_user,
        )
        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username=self.local_user.username)
        self.assertEqual(result.context_data["books"].object_list.count(), 1)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_shelf_page_all_books_json(self):
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

    def test_shelf_page_all_books_anonymous(self):
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

    def test_shelf_page_sorted_start_date(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("", {"sort": "start_date"})
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

    def test_shelf_page_sorted_finish_date(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("", {"sort": "finish_date"})
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

    def test_shelf_page_sorted_author(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.Shelf.as_view()
        shelf = self.local_user.shelf_set.first()
        request = self.factory.get("", {"sort": "author"})
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
        """display books that match a filter keyword"""
        models.ShelfBook.objects.create(
            book=self.book,
            shelf=self.shelf,
            user=self.local_user,
        )
        shelf_book = models.ShelfBook.objects.create(
            book=self.book,
            shelf=self.local_user.shelf_set.first(),
            user=self.local_user,
        )
        view = views.Shelf.as_view()
        request = self.factory.get("", {"filter": shelf_book.book.title})
        request.user = self.local_user
        with patch("reeltalk.views.shelf.shelf.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, username=self.local_user.username)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.context_data["books"].object_list), 1)
        self.assertEqual(
            result.context_data["books"].object_list[0].title,
            shelf_book.book.title,
        )

    def test_filter_shelf_none(self):
        """display a message when no books match a filter keyword"""
        models.ShelfBook.objects.create(
            book=self.book,
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
        self.assertEqual(len(result.context_data["books"].object_list), 0)

    def test_shelf_excludes_blocked(self):
        """are blocked books actually blocked?"""
        shelf = models.Shelf.objects.get(user=self.local_user, identifier="read")
        work = models.Work.objects.create(title="Awful Book")
        awful_book = models.Edition.objects.create(
            title="Awful Edition",
            remote_id="https://example.com/book/99",
            parent_work=work,
        )

        models.ShelfBook.objects.create(
            shelf=shelf, user=self.local_user, book=awful_book
        )
        models.ShelfBook.objects.create(
            shelf=shelf, user=self.local_user, book=self.book
        )

        self.local_user.blocked_books.add(work)

        view = views.Shelf.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request, username=request.user.username)

        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.context_data["books"].object_list), 1)
        self.assertFalse(awful_book in result.context_data["books"].object_list)
        self.assertEqual(result.context_data["books"].object_list, [self.book])
