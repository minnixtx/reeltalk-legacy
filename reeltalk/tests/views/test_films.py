"""test for film page and film edit views"""

from unittest.mock import patch

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from reeltalk import models, views
from reeltalk.tests.validate_html import validate_html


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
class FilmViews(TestCase):
    """film page and film editing"""

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
        cls.group = Group.objects.create(name="editor")
        cls.group.permissions.add(
            Permission.objects.create(
                name="edit_film",
                codename="edit_film",
                content_type=ContentType.objects.get_for_model(models.User),
            ).id
        )
        cls.local_user.groups.add(cls.group)

        cls.tmdb_film = models.Film.objects.create(
            title="Blade Runner", tmdb_id="78", year=1982
        )
        cls.manual_film = models.Film.objects.create(
            title="Manual Film", remote_id="https://example.com/film/1"
        )

    def setUp(self):
        """individual test setup"""
        self.factory = RequestFactory()

    # --- EditFilm: TMDB films are locked, manual films stay editable ---

    def test_edit_tmdb_film_redirects_get(self, *_):
        """the edit page of a TMDB film bounces back to the film page"""
        view = views.EditFilm.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request, self.tmdb_film.id)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, self.tmdb_film.local_path)

    def test_edit_tmdb_film_redirects_post(self, *_):
        """a POST to the edit page of a TMDB film changes nothing"""
        view = views.EditFilm.as_view()
        request = self.factory.post("", {"title": "Hacked"})
        request.user = self.local_user
        result = view(request, self.tmdb_film.id)
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, self.tmdb_film.local_path)
        self.tmdb_film.refresh_from_db()
        self.assertEqual(self.tmdb_film.title, "Blade Runner")

    def test_edit_manual_film_renders(self, *_):
        """manually created films stay fully editable"""
        view = views.EditFilm.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request, self.manual_film.id)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_edit_manual_film_saves(self, *_):
        """editing a manual film saves the changes"""
        view = views.EditFilm.as_view()
        request = self.factory.post(
            "",
            {
                "title": "Renamed Film",
                "sort_title": "",
                "subtitle": "",
                "description": "",
                "year": "",
                "runtime": "",
                "genres": "",
                "directors": "",
                "cast": "",
            },
        )
        request.user = self.local_user
        result = view(request, self.manual_film.id)
        self.assertEqual(result.status_code, 302)
        self.manual_film.refresh_from_db()
        self.assertEqual(self.manual_film.title, "Renamed Film")

    # --- poster and description endpoints: locked for TMDB films ---

    def test_upload_poster_locked_for_tmdb_film(self, *_):
        """uploading a poster to a TMDB film is ignored"""
        request = self.factory.post(
            "", {"poster-url": "https://example.com/poster.jpg"}
        )
        request.user = self.local_user
        result = views.upload_poster(request, self.tmdb_film.id)
        self.assertEqual(result.status_code, 302)
        self.tmdb_film.refresh_from_db()
        self.assertFalse(self.tmdb_film.poster)

    def test_add_description_locked_for_tmdb_film(self, *_):
        """adding a description to a TMDB film is ignored"""
        request = self.factory.post("", {"description": "A new description"})
        request.user = self.local_user
        result = views.add_description(request, self.tmdb_film.id)
        self.assertEqual(result.status_code, 302)
        self.tmdb_film.refresh_from_db()
        self.assertFalse(self.tmdb_film.description)

    def test_add_description_manual_film(self, *_):
        """adding a description to a manual film saves it"""
        request = self.factory.post("", {"description": "A new description"})
        request.user = self.local_user
        result = views.add_description(request, self.manual_film.id)
        self.assertEqual(result.status_code, 302)
        self.manual_film.refresh_from_db()
        self.assertEqual(self.manual_film.description, "A new description")

    # --- film page: edit controls hidden for TMDB films ---

    def test_film_page_tmdb_film_has_no_edit_controls(self, *_):
        """a TMDB film's page offers no metadata editing"""
        self.client.force_login(self.local_user)
        response = self.client.get(self.tmdb_film.local_path)
        validate_html(response)
        content = response.content.decode()
        self.assertNotIn(
            reverse("edit-film", args=[self.tmdb_film.id]), content
        )
        self.assertNotIn("Add Description", content)
        self.assertNotIn(f"add_poster_{self.tmdb_film.id}", content)

    def test_film_page_manual_film_has_edit_controls(self, *_):
        """a manual film's page keeps its editing affordances"""
        self.client.force_login(self.local_user)
        response = self.client.get(self.manual_film.local_path)
        validate_html(response)
        content = response.content.decode()
        self.assertIn(reverse("edit-film", args=[self.manual_film.id]), content)
        self.assertIn("Add Description", content)
        self.assertIn(f"add_poster_{self.manual_film.id}", content)

    # --- one review per film: the review tab becomes an edit link ---

    def test_film_page_review_tab_edit_only(self, *_):
        """a user who reviewed a film gets an edit link, not a new review form"""
        models.Review.objects.create(
            user=self.local_user, film=self.manual_film, content="Good movie"
        )
        self.client.force_login(self.local_user)
        response = self.client.get(self.manual_film.local_path)
        validate_html(response)
        content = response.content.decode()
        self.assertIn("Edit your review", content)
        self.assertNotIn(f'form_review_{self.manual_film.id}', content)

    def test_film_page_review_tab_for_new_reviewer(self, *_):
        """a user without a review still gets the review form"""
        self.client.force_login(self.local_user)
        response = self.client.get(self.manual_film.local_path)
        validate_html(response)
        content = response.content.decode()
        self.assertIn(f'form_review_{self.manual_film.id}', content)
