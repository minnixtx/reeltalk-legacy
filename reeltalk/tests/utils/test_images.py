"""test image utilities"""

from unittest.mock import patch

from django.test import TestCase

from reeltalk.utils.images import set_cover_from_url


class ImageUtils(TestCase):
    """image helper functions"""

    @patch("reeltalk.utils.images.get_image")
    def test_set_cover_from_url(self, mock_get_image):
        """fetch an image from a url and name it for storage"""
        mock_get_image.return_value = (b"imagedata", "jpg")
        result = set_cover_from_url("https://example.com/poster.jpg")
        self.assertEqual(len(result), 2)
        self.assertTrue(result[0].endswith(".jpg"))
        self.assertEqual(result[1], b"imagedata")

    @patch("reeltalk.utils.images.get_image")
    def test_set_cover_from_url_error(self, mock_get_image):
        """a failed fetch returns None"""
        mock_get_image.side_effect = Exception("nope")
        self.assertIsNone(set_cover_from_url("https://example.com/poster.jpg"))

    @patch("reeltalk.utils.images.get_image")
    def test_set_cover_from_url_empty(self, mock_get_image):
        """empty content returns None"""
        mock_get_image.return_value = (None, None)
        self.assertIsNone(set_cover_from_url("https://example.com/poster.jpg"))
