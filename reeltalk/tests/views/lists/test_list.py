"""test for app action functionality"""

from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import models, views
from reeltalk.activitypub import ActivitypubResponse
from reeltalk.tests.validate_html import validate_html


class ListViews(TestCase):
    """list view"""

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
            )
            cls.rat = models.User.objects.create_user(
                "rat@local.com",
                "rat@rat.com",
                "ratword",
                local=True,
                localname="rat",
                remote_id="https://example.com/users/rat",
            )
        cls.film = models.Film.objects.create(
            title="Example Film",
            remote_id="https://example.com/film/1",
        )
        cls.film_two = models.Film.objects.create(
            title="Example Film 2",
            remote_id="https://example.com/film/2",
        )
        cls.film_three = models.Film.objects.create(
            title="Example Film 3",
            remote_id="https://example.com/film/3",
        )
        cls.film_four = models.Film.objects.create(
            title="Example Film 4",
            remote_id="https://example.com/film/4",
        )

        with (
            patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"),
            patch("reeltalk.lists_stream.remove_list_task.delay"),
        ):
            cls.list = models.List.objects.create(name="Test List", user=cls.local_user)

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()
        self.anonymous_user = AnonymousUser
        self.anonymous_user.is_authenticated = False

    def test_list_page(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.List.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=True,
                notes="hello",
                order=1,
            )

        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_list_page_with_query(self):
        """searching for a film to add"""
        view = views.List.as_view()
        request = self.factory.get("", {"q": "Example Film"})
        request.user = self.local_user

        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_list_page_sorted(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.List.as_view()
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            for i, film in enumerate([self.film, self.film_two, self.film_three]):
                models.ListItem.objects.create(
                    film_list=self.list,
                    user=self.local_user,
                    film=film,
                    approved=True,
                    order=i + 1,
                )

        request = self.factory.get("/?sort_by=order")
        request.user = self.local_user
        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        request = self.factory.get("/?sort_by=sort_title")
        request.user = self.local_user
        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        request = self.factory.get("/?sort_by=rating")
        request.user = self.local_user
        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        request = self.factory.get("/?sort_by=sdkfh")
        request.user = self.local_user
        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_list_page_empty(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.List.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_list_page_logged_out(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.List.as_view()
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                notes="hi hello",
                approved=True,
                order=1,
            )

        request = self.factory.get("")
        request.user = self.anonymous_user
        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_list_page_json_view(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.List.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=True,
                order=1,
            )

        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, self.list.id)
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

    def test_list_page_json_view_page(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.List.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        request = self.factory.get("/?page=1")
        request.user = self.local_user
        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = True
            result = view(request, self.list.id)
        self.assertIsInstance(result, ActivitypubResponse)
        self.assertEqual(result.status_code, 200)

    def test_list_edit(self):
        """edit a list"""
        view = views.List.as_view()
        request = self.factory.post(
            "",
            {
                "name": "New Name",
                "description": "wow",
                "privacy": "direct",
                "curation": "curated",
                "user": self.local_user.id,
            },
        )
        request.user = self.local_user

        with (
            patch(
                "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
            ) as mock,
            patch("reeltalk.lists_stream.remove_list_task.delay"),
        ):
            result = view(request, self.list.id)

        self.assertEqual(mock.call_count, 1)
        activity = mock.call_args[0][0]
        self.assertEqual(activity["type"], "Update")
        self.assertEqual(activity["actor"], self.local_user.remote_id)
        self.assertEqual(activity["object"]["id"], self.list.remote_id)

        self.assertEqual(result.status_code, 302)

        self.list.refresh_from_db()
        self.assertEqual(self.list.name, "New Name")
        self.assertEqual(self.list.description, "wow")
        self.assertEqual(self.list.privacy, "direct")
        self.assertEqual(self.list.curation, "curated")

    def test_delete_list(self):
        """delete an entire list"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=True,
                order=1,
            )
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film_two,
                approved=False,
                order=2,
            )
        request = self.factory.post("")
        request.user = self.local_user
        with (
            patch(
                "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
            ) as mock,
            patch("reeltalk.lists_stream.remove_list_task.delay") as redis_mock,
        ):
            views.delete_list(request, self.list.id)
        self.assertTrue(redis_mock.called)
        activity = mock.call_args[0][0]
        self.assertEqual(activity["type"], "Delete")
        self.assertEqual(activity["actor"], self.local_user.remote_id)
        self.assertEqual(activity["object"]["id"], self.list.remote_id)
        self.assertEqual(activity["object"]["type"], "FilmList")

        self.assertEqual(mock.call_count, 1)
        self.assertFalse(models.List.objects.exists())
        self.assertFalse(models.ListItem.objects.exists())

    def test_delete_list_permission_denied(self):
        """delete an entire list"""
        request = self.factory.post("")
        request.user = self.rat
        with self.assertRaises(PermissionDenied):
            views.delete_list(request, self.list.id)

    def test_add_film(self):
        """put a film on a list"""
        request = self.factory.post(
            "",
            {
                "film": self.film.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request.user = self.local_user

        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            views.add_film(request)
            self.assertEqual(mock.call_count, 1)
            activity = mock.call_args[0][0]
            self.assertEqual(activity["type"], "Add")
            self.assertEqual(activity["actor"], self.local_user.remote_id)
            self.assertEqual(activity["target"], self.list.remote_id)

        item = self.list.listitem_set.get()
        self.assertEqual(item.film, self.film)
        self.assertEqual(item.user, self.local_user)
        self.assertTrue(item.approved)

    def test_add_two_films(self):
        """
        Putting two films on the list. The first should have an order value of
        1 and the second should have an order value of 2.
        """
        request_one = self.factory.post(
            "",
            {
                "film": self.film.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request_one.user = self.local_user

        request_two = self.factory.post(
            "",
            {
                "film": self.film_two.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request_two.user = self.local_user
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            views.add_film(request_one)
            views.add_film(request_two)

        items = self.list.listitem_set.order_by("order").all()
        self.assertEqual(items[0].film, self.film)
        self.assertEqual(items[1].film, self.film_two)
        self.assertEqual(items[0].order, 1)
        self.assertEqual(items[1].order, 2)

    def test_add_three_films_and_remove_second(self):
        """
        Put three films on a list and then remove the one in the middle. The
        ordering of the list should adjust to not have a gap.
        """
        request_one = self.factory.post(
            "",
            {
                "film": self.film.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request_one.user = self.local_user

        request_two = self.factory.post(
            "",
            {
                "film": self.film_two.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request_two.user = self.local_user

        request_three = self.factory.post(
            "",
            {
                "film": self.film_three.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request_three.user = self.local_user

        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            views.add_film(request_one)
            views.add_film(request_two)
            views.add_film(request_three)

        items = self.list.listitem_set.order_by("order").all()
        self.assertEqual(items[0].film, self.film)
        self.assertEqual(items[1].film, self.film_two)
        self.assertEqual(items[2].film, self.film_three)
        self.assertEqual(items[0].order, 1)
        self.assertEqual(items[1].order, 2)
        self.assertEqual(items[2].order, 3)

        remove_request = self.factory.post("", {"item": items[1].id})
        remove_request.user = self.local_user
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            views.remove_film(remove_request, self.list.id)
        items = self.list.listitem_set.order_by("order").all()
        self.assertEqual(items[0].film, self.film)
        self.assertEqual(items[1].film, self.film_three)
        self.assertEqual(items[0].order, 1)
        self.assertEqual(items[1].order, 2)

    def test_adding_film_with_a_pending_film(self):
        """
        When a list contains any pending films, the pending films should have
        be at the end of the list by order. If a film is added while a film is
        pending, its order should precede the pending films.
        """
        request = self.factory.post(
            "",
            {
                "film": self.film_three.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request.user = self.local_user
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=True,
                order=1,
            )
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.rat,
                film=self.film_two,
                approved=False,
                order=2,
            )
            views.add_film(request)

        items = self.list.listitem_set.order_by("order").all()
        self.assertEqual(items[0].film, self.film)
        self.assertEqual(items[0].order, 1)
        self.assertTrue(items[0].approved)

        self.assertEqual(items[1].film, self.film_three)
        self.assertEqual(items[1].order, 2)
        self.assertTrue(items[1].approved)

        self.assertEqual(items[2].film, self.film_two)
        self.assertEqual(items[2].order, 3)
        self.assertFalse(items[2].approved)

    def test_approving_one_pending_film_from_multiple(self):
        """
        When a list contains any pending films, the pending films should have
        be at the end of the list by order. If a pending film is approved, then
        its order should be at the end of the approved films and before the
        remaining pending films.
        """
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                approved=True,
                order=1,
            )
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film_two,
                approved=True,
                order=2,
            )
            models.ListItem.objects.create(
                film_list=self.list,
                user=self.rat,
                film=self.film_three,
                approved=False,
                order=3,
            )
            to_be_approved = models.ListItem.objects.create(
                film_list=self.list,
                user=self.rat,
                film=self.film_four,
                approved=False,
                order=4,
            )

        view = views.Curate.as_view()
        request = self.factory.post(
            "",
            {
                "item": to_be_approved.id,
                "approved": "true",
            },
        )
        request.user = self.local_user

        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            view(request, self.list.id)

        items = self.list.listitem_set.order_by("order").all()
        self.assertEqual(items[0].film, self.film)
        self.assertEqual(items[0].order, 1)
        self.assertTrue(items[0].approved)

        self.assertEqual(items[1].film, self.film_two)
        self.assertEqual(items[1].order, 2)
        self.assertTrue(items[1].approved)

        self.assertEqual(items[2].film, self.film_four)
        self.assertEqual(items[2].order, 3)
        self.assertTrue(items[2].approved)

        self.assertEqual(items[3].film, self.film_three)
        self.assertEqual(items[3].order, 4)
        self.assertFalse(items[3].approved)

    def test_add_three_films_and_move_last_to_first(self):
        """
        Put three films on the list and move the last film to the first
        position.
        """
        request_one = self.factory.post(
            "",
            {
                "film": self.film.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request_one.user = self.local_user

        request_two = self.factory.post(
            "",
            {
                "film": self.film_two.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request_two.user = self.local_user

        request_three = self.factory.post(
            "",
            {
                "film": self.film_three.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request_three.user = self.local_user

        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            views.add_film(request_one)
            views.add_film(request_two)
            views.add_film(request_three)

        items = self.list.listitem_set.order_by("order").all()
        self.assertEqual(items[0].film, self.film)
        self.assertEqual(items[1].film, self.film_two)
        self.assertEqual(items[2].film, self.film_three)
        self.assertEqual(items[0].order, 1)
        self.assertEqual(items[1].order, 2)
        self.assertEqual(items[2].order, 3)

        set_position_request = self.factory.post("", {"position": 1})
        set_position_request.user = self.local_user
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            views.set_film_position(set_position_request, items[2].id)
        items = self.list.listitem_set.order_by("order").all()
        self.assertEqual(items[0].film, self.film_three)
        self.assertEqual(items[1].film, self.film)
        self.assertEqual(items[2].film, self.film_two)
        self.assertEqual(items[0].order, 1)
        self.assertEqual(items[1].order, 2)
        self.assertEqual(items[2].order, 3)

    def test_add_film_outsider(self):
        """put a film on a list"""
        self.list.curation = "open"
        self.list.save(broadcast=False, update_fields=["curation"])
        request = self.factory.post(
            "",
            {
                "film": self.film.id,
                "film_list": self.list.id,
                "user": self.rat.id,
            },
        )
        request.user = self.rat

        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            views.add_film(request)
            self.assertEqual(mock.call_count, 1)
            activity = mock.call_args[0][0]
            self.assertEqual(activity["type"], "Add")
            self.assertEqual(activity["actor"], self.rat.remote_id)
            self.assertEqual(activity["target"], self.list.remote_id)

        item = self.list.listitem_set.get()
        self.assertEqual(item.film, self.film)
        self.assertEqual(item.user, self.rat)
        self.assertTrue(item.approved)

    def test_add_film_pending(self):
        """put a film on a list awaiting approval"""
        self.list.curation = "curated"
        self.list.save(broadcast=False, update_fields=["curation"])
        request = self.factory.post(
            "",
            {
                "film": self.film.id,
                "film_list": self.list.id,
                "user": self.rat.id,
            },
        )
        request.user = self.rat

        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            views.add_film(request)

        self.assertEqual(mock.call_count, 1)
        activity = mock.call_args[0][0]

        self.assertEqual(activity["type"], "Add")
        self.assertEqual(activity["actor"], self.rat.remote_id)
        self.assertEqual(activity["target"], self.list.remote_id)

        item = self.list.listitem_set.get()
        self.assertEqual(activity["object"]["id"], item.remote_id)

        self.assertEqual(item.film, self.film)
        self.assertEqual(item.user, self.rat)
        self.assertFalse(item.approved)

    def test_add_film_self_curated(self):
        """put a film on a list automatically approved"""
        self.list.curation = "curated"
        self.list.save(broadcast=False, update_fields=["curation"])
        request = self.factory.post(
            "",
            {
                "film": self.film.id,
                "film_list": self.list.id,
                "user": self.local_user.id,
            },
        )
        request.user = self.local_user

        with patch(
            "reeltalk.models.activitypub_mixin.ActivitypubMixin.broadcast"
        ) as mock:
            views.add_film(request)
            self.assertEqual(mock.call_count, 1)
            activity = mock.call_args[0][0]
            self.assertEqual(activity["type"], "Add")
            self.assertEqual(activity["actor"], self.local_user.remote_id)
            self.assertEqual(activity["target"], self.list.remote_id)

        item = self.list.listitem_set.get()
        self.assertEqual(item.film, self.film)
        self.assertEqual(item.user, self.local_user)
        self.assertTrue(item.approved)

    def test_add_film_permission_denied(self):
        """you can't add to that list"""
        self.list.curation = "closed"
        self.list.save(broadcast=False, update_fields=["curation"])
        request = self.factory.post(
            "",
            {
                "film": self.film.id,
                "film_list": self.list.id,
                "user": self.rat.id,
            },
        )
        request.user = self.rat

        with self.assertRaises(PermissionDenied):
            views.add_film(request)

    def test_remove_film(self):
        """take an item off a list"""

        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            item = models.ListItem.objects.create(
                film_list=self.list,
                user=self.local_user,
                film=self.film,
                order=1,
            )
        self.assertTrue(self.list.listitem_set.exists())

        request = self.factory.post("", {"item": item.id})
        request.user = self.local_user

        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            views.remove_film(request, self.list.id)
        self.assertFalse(self.list.listitem_set.exists())

    def test_remove_film_unauthorized(self):
        """take an item off a list"""
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            item = models.ListItem.objects.create(
                film_list=self.list, user=self.local_user, film=self.film, order=1
            )
        self.assertTrue(self.list.listitem_set.exists())
        request = self.factory.post("", {"item": item.id})
        request.user = self.rat

        with self.assertRaises(PermissionDenied):
            views.remove_film(request, self.list.id)
        self.assertTrue(self.list.listitem_set.exists())

    def test_save_unsave_list(self):
        """bookmark a list"""
        self.assertFalse(self.local_user.saved_lists.exists())
        request = self.factory.post("")
        request.user = self.local_user
        views.save_list(request, self.list.id)
        self.local_user.refresh_from_db()
        self.assertEqual(self.local_user.saved_lists.first(), self.list)

        views.unsave_list(request, self.list.id)
        self.local_user.refresh_from_db()
        self.assertFalse(self.local_user.saved_lists.exists())

    def test_list_page_excludes_blocked_items(self):
        """exclude blocked films from lists"""

        self.local_user.blocked_films.add(self.film_two)

        view = views.List.as_view()
        request = self.factory.get("")
        request.user = self.local_user

        list_item_one = models.ListItem.objects.create(
            film_list=self.list,
            user=self.local_user,
            film=self.film,
            approved=True,
            notes="hello",
            order=1,
        )

        list_item_two = models.ListItem.objects.create(
            film_list=self.list,
            user=self.local_user,
            film=self.film_two,
            approved=True,
            notes="goodbye",
            order=2,
        )

        with patch("reeltalk.views.list.list.is_api_request") as is_api:
            is_api.return_value = False
            result = view(request, self.list.id)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

        self.assertFalse(list_item_two in result.context_data["items"].object_list)
        self.assertEqual(result.context_data["items"].object_list, [list_item_one])
