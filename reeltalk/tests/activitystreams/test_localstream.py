"""testing activitystreams"""

from django.test import TestCase
from reeltalk import activitystreams, models


class Activitystreams(TestCase):
    """using redis to build activity streams"""

    @classmethod
    def setUpTestData(cls):
        """use a test csv"""
        cls.local_user = models.User.objects.create_user(
            "mouse", "mouse@mouse.mouse", "password", local=True, localname="mouse"
        )
        cls.another_user = models.User.objects.create_user(
            "nutria",
            "nutria@nutria.nutria",
            "password",
            local=True,
            localname="nutria",
        )
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

    def test_localstream_get_audience_remote_status(self):
        """get a list of users that should see a status"""
        status = models.Status.objects.create(
            user=self.remote_user, content="hi", privacy="public"
        )
        users = activitystreams.LocalStream().get_audience(status)
        self.assertEqual(users, [])

    def test_localstream_get_audience_local_status(self):
        """get a list of users that should see a status"""
        status = models.Status.objects.create(
            user=self.local_user, content="hi", privacy="public"
        )
        users = activitystreams.LocalStream().get_audience(status)
        self.assertFalse(self.local_user.id in users)
        self.assertTrue(self.another_user.id in users)

    def test_localstream_get_audience_unlisted(self):
        """get a list of users that should see a status"""
        status = models.Status.objects.create(
            user=self.local_user, content="hi", privacy="unlisted"
        )
        users = activitystreams.LocalStream().get_audience(status)
        self.assertEqual(users, [])

    def test_filmsstream_get_audience_no_film(self):
        """get a list of users that should see a status"""
        status = models.Status.objects.create(
            user=self.local_user, content="hi", privacy="public"
        )
        models.ShelfFilm.objects.create(
            user=self.local_user,
            shelf=self.local_user.shelf_set.first(),
            film=self.film,
        )
        audience = activitystreams.FilmsStream().get_audience(status)
        # no film, no audience
        self.assertEqual(audience, [])

    def test_filmsstream_get_audience_mention_film(self):
        """get a list of users that should see a status"""
        status = models.Status.objects.create(
            user=self.local_user, content="hi", privacy="public"
        )
        status.mention_films.add(self.film)
        status.save(broadcast=False)
        models.ShelfFilm.objects.create(
            user=self.another_user,
            shelf=self.another_user.shelf_set.first(),
            film=self.film,
        )
        # yes film, yes audience
        audience = activitystreams.FilmsStream().get_audience(status)
        self.assertTrue(self.another_user.id in audience)

    def test_filmsstream_get_audience_film_field(self):
        """get a list of users that should see a status"""
        status = models.Comment.objects.create(
            user=self.local_user, content="hi", privacy="public", film=self.film
        )
        models.ShelfFilm.objects.create(
            user=self.another_user,
            shelf=self.another_user.shelf_set.first(),
            film=self.film,
        )
        # yes film, yes audience
        audience = activitystreams.FilmsStream().get_audience(status)
        self.assertTrue(self.another_user.id in audience)

    def test_filmsstream_get_audience_different_film(self):
        """a status about a different film doesn't reach this audience"""
        alt_film = models.Film.objects.create(title="hi")
        status = models.Comment.objects.create(
            user=self.remote_user, content="hi", privacy="public", film=alt_film
        )
        models.ShelfFilm.objects.create(
            user=self.another_user,
            shelf=self.another_user.shelf_set.first(),
            film=self.film,
        )
        # different film, no audience
        audience = activitystreams.FilmsStream().get_audience(status)
        self.assertFalse(self.another_user.id in audience)

    def test_filmsstream_get_audience_non_public(self):
        """non-public film statuses have no films-stream audience"""
        alt_film = models.Film.objects.create(title="hi")
        status = models.Comment.objects.create(
            user=self.remote_user, content="hi", privacy="unlisted", film=alt_film
        )
        models.ShelfFilm.objects.create(
            user=self.local_user,
            shelf=self.local_user.shelf_set.first(),
            film=self.film,
        )
        # not public, no audience
        audience = activitystreams.FilmsStream().get_audience(status)
        self.assertEqual(audience, [])
