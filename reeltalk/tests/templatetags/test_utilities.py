"""style fixes and lookups for templates"""

from collections import namedtuple
import re
from unittest.mock import patch

from django.test import TestCase

from reeltalk import models
from reeltalk.templatetags import utilities


@patch("reeltalk.activitystreams.add_status_task.delay")
@patch("reeltalk.activitystreams.remove_status_task.delay")
class UtilitiesTags(TestCase):
    """lotta different things here"""

    @classmethod
    def setUpTestData(cls):
        """create some filler objects"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.user = models.User.objects.create_user(
                "mouse@example.com",
                "mouse@mouse.mouse",
                "mouseword",
                local=True,
                localname="mouse",
            )
        with patch("reeltalk.models.user.set_remote_server.delay"):
            cls.remote_user = models.User.objects.create_user(
                "rat",
                "rat@rat.rat",
                "ratword",
                remote_id="http://example.com/rat",
                local=False,
            )
        cls.film = models.Film.objects.create(title="Test Film")

    def test_get_uuid(self, *_):
        """uuid functionality"""
        uuid = utilities.get_uuid("hi")
        self.assertTrue(re.match(r"hi[A-Za-z0-9\-]", uuid))

    def test_join(self, *_):
        """concats things with underscores"""
        self.assertEqual(utilities.join("hi", 5, "blah", 0.75), "hi_5_blah_0.75")

    def test_get_user_identifer_local(self, *_):
        """fall back to the simplest uid available"""
        self.assertNotEqual(self.user.username, self.user.localname)
        self.assertEqual(utilities.get_user_identifier(self.user), "mouse")

    def test_get_user_identifer_remote(self, *_):
        """for a remote user, should be their full username"""
        self.assertEqual(
            utilities.get_user_identifier(self.remote_user), "rat@example.com"
        )

    def test_get_user_identifier_from_remote_id(self, *_):
        """load a user based on a remote id"""
        result = utilities.get_user_identifier_from_remote_id(self.user.remote_id)
        self.assertEqual(result, self.user)

        result = utilities.get_user_identifier_from_remote_id("http://nota.real/user")
        self.assertIsNone(result)

    def test_get_title(self, *_):
        """the title of a film"""
        self.assertEqual(utilities.get_title(None), "")
        self.assertEqual(utilities.get_title(self.film), "Test Film")
        film = models.Film.objects.create(title="Oh", subtitle="oh my")
        self.assertEqual(utilities.get_title(film), "Oh: oh my")

    def test_get_title_too_short(self, *_):
        """the too_short threshold can be overridden"""
        film = models.Film.objects.create(title="Test Film", subtitle="oh my")
        # default threshold (5) is below the title length: no subtitle shown
        self.assertEqual(utilities.get_title(film), "Test Film")
        # a higher threshold pulls in the subtitle
        self.assertEqual(utilities.get_title(film, 10), "Test Film: oh my")

    def test_comparison_bool(self, *_):
        """just a simple comparison"""
        self.assertTrue(utilities.comparison_bool("a", "a"))
        self.assertFalse(utilities.comparison_bool("a", "b"))

        self.assertFalse(utilities.comparison_bool("a", "a", reverse=True))
        self.assertTrue(utilities.comparison_bool("a", "b", reverse=True))

    def test_truncatepath(self, *_):
        """truncate a path"""
        ValueMock = namedtuple("Value", ("name"))
        value = ValueMock("home/one/two/three/four")
        self.assertEqual(utilities.truncatepath(value, 2), "home/…ur")
        self.assertEqual(utilities.truncatepath(value, "a"), "four")

    def test_id_to_username(self, *_):
        """given an arbitrary remote id, return the username"""
        self.assertEqual(
            utilities.id_to_username("http://example.com/rat"), "rat@example.com"
        )
        self.assertEqual(utilities.id_to_username(None), "a new user account")

    def test_get_file_size(self, *_):
        """display the size of a file in human readable terms"""
        self.assertEqual(utilities.get_file_size(5), "5.0 bytes")
        self.assertEqual(utilities.get_file_size(5120), "5.00 KB")
        self.assertEqual(utilities.get_file_size(5242880), "5.00 MB")
        self.assertEqual(utilities.get_file_size(5368709000), "5.00 GB")
