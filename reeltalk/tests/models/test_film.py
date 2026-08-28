"""testing models"""

import pathlib
from unittest.mock import patch

import pytest

from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

from reeltalk import models, settings
from reeltalk.settings import ENABLE_THUMBNAIL_GENERATION


@patch("reeltalk.suggested_users.rerank_suggestions_task.delay")
@patch("reeltalk.activitystreams.populate_stream_task.delay")
@patch("reeltalk.lists_stream.populate_lists_task.delay")
@patch("reeltalk.activitystreams.add_film_statuses_task.delay")
@patch("reeltalk.activitystreams.remove_film_statuses_task.delay")
@patch("reeltalk.models.Status.broadcast")
@patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async")
class Film(TestCase):
    """not too much going on in the film model but here we are"""

    @classmethod
    def setUpTestData(cls):
        """we'll need some films"""
        cls.local_user = models.User.objects.create_user(
            "mouse", "mouse@mouse.mouse", "mouseword", local=True, localname="mouse"
        )
        cls.film = models.Film.objects.create(title="Example Film")

    def test_remote_id(self, *_):
        """fanciness with remote/origin ids"""
        expected_id = f"{settings.BASE_URL}/film/{self.film.id}"
        self.assertEqual(self.film.get_remote_id(), expected_id)
        self.assertEqual(self.film.remote_id, expected_id)

    def test_origin_id_from_remote(self, *_):
        """a film created from a remote object keeps its origin id"""
        film = models.Film.objects.create(
            title="Remote Film", remote_id="http://film.com/film"
        )
        self.assertEqual(film.origin_id, "http://film.com/film")
        self.assertNotEqual(film.remote_id, "http://film.com/film")

    def test_sort_title(self, *_):
        """the sort title should remove the initial article on save"""
        for title, expected in [
            ("The Matrix", "matrix"),
            ("A Star Is Born", "star is born"),
            ("An Example Film", "example film"),
            ("Inception", "inception"),
        ]:
            with self.subTest(title=title):
                film = models.Film.objects.create(title=title)
                self.assertEqual(film.sort_title, expected)

    def test_sort_title_not_overwritten(self, *_):
        """an explicitly set sort title is kept"""
        film = models.Film.objects.create(title="The Matrix", sort_title="custom")
        self.assertEqual(film.sort_title, "custom")

    def test_director_text(self, *_):
        """format a list of directors"""
        film = models.Film.objects.create(title="Test Film")
        self.assertEqual(film.director_text, "")

        film.directors = ["Christopher Nolan"]
        film.save(broadcast=False)
        self.assertEqual(film.director_text, "Christopher Nolan")

        film.directors = ["Sister A", "Brother B"]
        film.save(broadcast=False)
        self.assertEqual(film.director_text, "Sister A, Brother B")

    def test_alt_text(self, *_):
        """text slug used for poster images"""
        film = models.Film.objects.create(title="Test Film")
        self.assertEqual(film.alt_text, "Test Film")

        film.year = 2020
        film.save(broadcast=False)
        self.assertEqual(film.alt_text, "Test Film (2020)")

        film.directors = ["Director Name"]
        film.save(broadcast=False)
        self.assertEqual(film.alt_text, "Director Name: Test Film (2020)")

    def test_find_existing(self, *_):
        """match a blob of data to a model"""
        film = models.Film.objects.create(title="Test film", tmdb_id="1234")

        result = models.Film.find_existing({"tmdbId": "1234"})
        self.assertEqual(result, film)

    def test_find_existing_imdb(self, *_):
        """match on the imdb id too"""
        film = models.Film.objects.create(title="Test film", imdb_id="tt1234")

        result = models.Film.find_existing({"imdbId": "tt1234"})
        self.assertEqual(result, film)

    def test_find_existing_by_remote_id(self, *_):
        """match on the origin id of a remote object"""
        film = models.Film.objects.create(
            title="Test film", remote_id="http://film.com/film/1"
        )

        result = models.Film.find_existing({"id": "http://film.com/film/1"})
        self.assertEqual(result, film)

    def test_find_existing_no_match(self, *_):
        """no deduplication fields in the data means no match"""
        models.Film.objects.create(title="Test film", tmdb_id="1234")

        result = models.Film.find_existing({"title": "something else"})
        self.assertIsNone(result)

    def test_find_existing_with_id(self, *_):
        """make sure that a local "id" field won't produce a match"""
        film = models.Film.objects.create(title="Test film")

        result = models.Film.find_existing({"id": film.id})
        self.assertIsNone(result)

    def test_find_existing_with_id_and_match(self, *_):
        """the other deduplication fields still match when an id is present"""
        models.Film.objects.create(title="Test film")
        matching_film = models.Film.objects.create(
            title="Another test film", tmdb_id="1234"
        )

        result = models.Film.find_existing({"tmdbId": "1234"})
        self.assertEqual(result, matching_film)

    def test_merge_into(self, *_):
        """merging moves related objects and leaves a redirect"""
        canonical = models.Film.objects.create(title="Canonical Film")
        duplicate = models.Film.objects.create(
            title="Duplicate Film", description="<p>a duplicate</p>"
        )

        # related data on the duplicate
        shelf = models.Shelf.objects.create(
            name="Test Shelf", identifier="test-shelf", user=self.local_user
        )
        models.ShelfFilm.objects.create(
            shelf=shelf, film=duplicate, user=self.local_user
        )
        review = models.Review.objects.create(
            content="great", user=self.local_user, film=duplicate, rating=4
        )
        film_list = models.List.objects.create(name="Test List", user=self.local_user)
        list_item = models.ListItem.objects.create(
            film_list=film_list, film=duplicate, user=self.local_user, order=1
        )

        duplicate_id = duplicate.id
        absorbed = duplicate.merge_into(canonical)

        # the duplicate is gone and a redirect remains
        self.assertFalse(models.Film.objects.filter(id=duplicate_id).exists())
        merged = models.MergedFilm.objects.get(deleted_id=duplicate_id)
        self.assertEqual(merged.merged_into, canonical)

        # empty fields on the canonical film were filled in
        self.assertEqual(absorbed["description"], "<p>a duplicate</p>")

        # related objects moved to the canonical film
        shelf_film = models.ShelfFilm.objects.get(shelf=shelf)
        self.assertEqual(shelf_film.film, canonical)
        review.refresh_from_db()
        self.assertEqual(review.film, canonical)
        list_item.refresh_from_db()
        self.assertEqual(list_item.film, canonical)

    def test_merge_into_itself(self, *_):
        """can't merge a film into itself"""
        with self.assertRaises(ValueError):
            self.film.merge_into(self.film)

    def test_absorb_data_from(self, *_):
        """fill empty fields with values from another entity"""
        canonical = models.Film.objects.create(title="Canonical Film")
        other = models.Film.objects.create(
            title="Other Film",
            year=1999,
            runtime=120,
            genres=["Drama"],
            directors=["Jane Doe"],
        )

        absorbed = canonical.absorb_data_from(other)

        self.assertEqual(absorbed["year"], 1999)
        self.assertEqual(absorbed["runtime"], 120)
        self.assertEqual(absorbed["genres"], ["Drama"])
        self.assertEqual(absorbed["directors"], ["Jane Doe"])
        # the title is already set, so it's not absorbed
        self.assertNotIn("title", absorbed)

    def test_absorb_data_from_dry_run(self, *_):
        """dry run reports what would be absorbed without changing anything"""
        canonical = models.Film.objects.create(title="Canonical Film")
        other = models.Film.objects.create(title="Other Film", year=1999)

        absorbed = canonical.absorb_data_from(other, dry_run=True)

        self.assertEqual(absorbed["year"], 1999)
        canonical.refresh_from_db()
        self.assertIsNone(canonical.year)

    def test_absorb_data_from_arrays(self, *_):
        """array fields are merged without duplicates"""
        canonical = models.Film.objects.create(
            title="Canonical Film", genres=["Drama"], directors=["Jane Doe"]
        )
        other = models.Film.objects.create(
            title="Other Film",
            genres=["Drama", "Mystery"],
            directors=["John Roe"],
        )

        absorbed = canonical.absorb_data_from(other)

        self.assertEqual(absorbed["genres"], ["Mystery"])
        self.assertEqual(absorbed["directors"], ["John Roe"])
        # absorption only mutates the instance; merge_into is what saves
        canonical.save(broadcast=False)
        canonical.refresh_from_db()
        self.assertCountEqual(canonical.genres, ["Drama", "Mystery"])
        self.assertCountEqual(canonical.directors, ["Jane Doe", "John Roe"])

    def test_viewer_aware_objects(self, *_):
        """blocked films are hidden from the viewer"""
        blocked_film = models.Film.objects.create(title="Blocked Film")
        visible_film = models.Film.objects.create(title="Visible Film")

        self.local_user.blocked_films.add(blocked_film)

        queryset = models.Film.viewer_aware_objects(self.local_user)
        self.assertNotIn(blocked_film, queryset)
        self.assertIn(visible_film, queryset)
        # the prefetch of current shelves is attached
        self.assertTrue(hasattr(queryset.first(), "current_shelves"))

        # anonymous viewers see everything (the app returns the bare
        # manager in this branch; .all() normalizes it to a queryset)
        queryset = models.Film.viewer_aware_objects(AnonymousUser()).all()
        self.assertIn(blocked_film, queryset)

    @pytest.mark.skipif(
        not ENABLE_THUMBNAIL_GENERATION,
        reason="Thumbnail generation disabled in settings",
    )
    def test_thumbnail_fields(self, *_):
        """Just hit them"""
        image_path = pathlib.Path(__file__).parent.joinpath(
            "../../static/images/default_avi.jpg"
        )

        film = models.Film.objects.create(title="hello")
        with open(image_path, "rb") as image_file:
            film.poster.save("test.jpg", image_file)

        self.assertIsNotNone(film.poster_bw_film_xsmall_webp.url)
        self.assertIsNotNone(film.poster_bw_film_xsmall_jpg.url)
        self.assertIsNotNone(film.poster_bw_film_small_webp.url)
        self.assertIsNotNone(film.poster_bw_film_small_jpg.url)
        self.assertIsNotNone(film.poster_bw_film_medium_webp.url)
        self.assertIsNotNone(film.poster_bw_film_medium_jpg.url)
        self.assertIsNotNone(film.poster_bw_film_large_webp.url)
        self.assertIsNotNone(film.poster_bw_film_large_jpg.url)
        self.assertIsNotNone(film.poster_bw_film_xlarge_webp.url)
        self.assertIsNotNone(film.poster_bw_film_xlarge_jpg.url)
        self.assertIsNotNone(film.poster_bw_film_xxlarge_webp.url)
        self.assertIsNotNone(film.poster_bw_film_xxlarge_jpg.url)
