"""test film serializer"""

import pathlib
from unittest.mock import patch

import responses
from django.core.files.base import ContentFile
from django.test import TestCase
from reeltalk import activitypub, models


class Film(TestCase):
    """serialize/deserialize tests for the flat Film wire type"""

    @classmethod
    def setUpTestData(cls):
        """initial data"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.user = models.User.objects.create_user(
                "instance",
                "instance@example.example",
                "pass",
                local=True,
                localname="instance",
            )

        cls.film = models.Film.objects.create(
            title="Example Film",
            year=1999,
            runtime=120,
            genres=["Drama", "Mystery"],
            directors=["Jane Doe"],
            cast=["John Smith", "Jane Roe"],
            tmdb_id="12345",
            imdb_id="tt0112462",
        )

    def setUp(self):
        """per-test data"""
        image_path = pathlib.Path(__file__).parent.joinpath(
            "../../static/images/default_avi.jpg"
        )
        with open(image_path, "rb") as image_file:
            self.image_data = image_file.read()

    def test_serialize_model(self):
        """check presence of film fields"""
        activity = self.film.to_activity()

        self.assertEqual(activity["type"], "Film")
        self.assertTrue(activity["id"])
        self.assertEqual(activity["title"], "Example Film")
        self.assertEqual(activity["sortTitle"], "example film")
        self.assertEqual(activity["year"], 1999)
        self.assertEqual(activity["runtime"], 120)
        self.assertEqual(activity["genres"], ["Drama", "Mystery"])
        self.assertEqual(activity["directors"], ["Jane Doe"])
        self.assertEqual(activity["cast"], ["John Smith", "Jane Roe"])
        self.assertEqual(activity["tmdbId"], "12345")
        self.assertEqual(activity["imdbId"], "tt0112462")

    def test_serialize_model_with_poster(self):
        """check that a poster image is serialized as an Image"""
        self.film.poster.save(
            "test-poster.jpg", ContentFile(self.image_data), save=False
        )
        self.film.save(broadcast=False)

        activity = self.film.to_activity()

        self.assertEqual(activity["poster"]["type"], "Image")
        # the media directory persists between runs, so Django may suffix the
        # stored filename; build the expectation from the saved file (§7 quirk 6)
        self.assertTrue(activity["poster"]["url"].endswith(self.film.poster.name))
        self.assertEqual(
            activity["poster"]["name"], "Jane Doe: Example Film (1999)"
        )

    def test_serialize_model_last_edited_by(self):
        """the last editor is serialized as a remote id"""
        self.film.last_edited_by = self.user
        self.film.save(broadcast=False)

        activity = self.film.to_activity()
        self.assertEqual(activity["lastEditedBy"], self.user.remote_id)

    @responses.activate
    def test_from_activity(self):
        """create a Film model instance from a wire object"""
        responses.add(
            responses.GET,
            "http://example.com/poster.jpg",
            body=self.image_data,
            status=200,
        )

        film_data = {
            "id": "https://example.com/film/1",
            "type": "Film",
            "title": "Remote Film",
            "sortTitle": "remote film",
            "subtitle": "The Sequel",
            "description": "<p>A remote film</p>",
            "year": 2001,
            "runtime": 95,
            "genres": ["Sci-Fi"],
            "directors": ["Remote Director"],
            "cast": ["Remote Actor"],
            "tmdbId": "67890",
            "imdbId": "tt0241527",
            "poster": {
                "type": "Document",
                "url": "http://example.com/poster.jpg",
            },
        }

        film = activitypub.Film(**film_data).to_model(model=models.Film)

        self.assertIsNotNone(film.id)
        # the incoming id is kept as the origin of the local object
        self.assertEqual(film.origin_id, "https://example.com/film/1")
        self.assertEqual(film.title, "Remote Film")
        self.assertEqual(film.sort_title, "remote film")
        self.assertEqual(film.subtitle, "The Sequel")
        self.assertEqual(film.year, 2001)
        self.assertEqual(film.runtime, 95)
        self.assertEqual(film.genres, ["Sci-Fi"])
        self.assertEqual(film.directors, ["Remote Director"])
        self.assertEqual(film.cast, ["Remote Actor"])
        self.assertEqual(film.tmdb_id, "67890")
        self.assertEqual(film.imdb_id, "tt0241527")
        self.assertTrue(film.poster)

    def test_from_activity_dedupes_on_tmdb_id(self):
        """an incoming film with a known tmdb id updates the existing model"""
        film_data = {
            "id": "https://example.com/film/2",
            "type": "Film",
            "title": "Example Film (updated)",
            "sortTitle": "example film updated",
            "year": 2000,
            "runtime": 130,
            "genres": ["Drama"],
            "directors": ["Jane Doe", "Another Director"],
            "cast": ["John Smith"],
            "tmdbId": "12345",
        }

        count = models.Film.objects.count()
        film = activitypub.Film(**film_data).to_model(model=models.Film)

        self.assertEqual(film.id, self.film.id)
        self.assertEqual(models.Film.objects.count(), count)
        self.assertEqual(film.title, "Example Film (updated)")
        self.assertEqual(film.directors, ["Jane Doe", "Another Director"])

    def test_round_trip(self):
        """a serialized model can be parsed back into a wire object"""
        activity = self.film.to_activity()
        wire = activitypub.Film(**activity)

        self.assertEqual(wire.type, "Film")
        self.assertEqual(wire.title, self.film.title)
        self.assertEqual(wire.year, self.film.year)
        self.assertEqual(wire.runtime, self.film.runtime)
        self.assertEqual(wire.genres, self.film.genres)
        self.assertEqual(wire.directors, self.film.directors)
        self.assertEqual(wire.cast, self.film.cast)
        self.assertEqual(wire.tmdbId, self.film.tmdb_id)
        self.assertEqual(wire.imdbId, self.film.imdb_id)

    def test_parse(self):
        """activitypub.parse dispatches the Film type to the Film serializer"""
        parsed = activitypub.parse(self.film.to_activity())
        self.assertIsInstance(parsed, activitypub.Film)
        self.assertEqual(parsed.title, self.film.title)
