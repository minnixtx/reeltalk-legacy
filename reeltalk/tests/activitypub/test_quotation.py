"""quotation activity object serializer class"""

from unittest.mock import patch

from django.test import TestCase
from reeltalk import activitypub, models


class Quotation(TestCase):
    """we have hecka ways to create statuses"""

    @classmethod
    def setUpTestData(cls):
        """model objects we'll need"""
        with patch("reeltalk.models.user.set_remote_server.delay"):
            cls.user = models.User.objects.create_user(
                "mouse",
                "mouse@mouse.mouse",
                "mouseword",
                local=False,
                inbox="https://example.com/user/mouse/inbox",
                outbox="https://example.com/user/mouse/outbox",
                remote_id="https://example.com/user/mouse",
            )
        cls.film = models.Film.objects.create(title="Example Film")

    def setUp(self):
        """other test data"""
        self.status_data = {
            "id": "https://example.com/user/mouse/quotation/13",
            "url": "https://example.com/user/mouse/quotation/13",
            "inReplyTo": None,
            "published": "2020-05-10T02:38:31.150343+00:00",
            "attributedTo": "https://example.com/user/mouse",
            "to": ["https://www.w3.org/ns/activitystreams#Public"],
            "cc": ["https://example.com/user/mouse/followers"],
            "sensitive": False,
            "content": "commentary",
            "type": "Quotation",
            "replies": {
                "id": "https://example.com/user/mouse/quotation/13/replies",
                "type": "Collection",
                "first": {
                    "type": "CollectionPage",
                    "next": "https://example.com/user/mouse/quotation/13"
                    "/replies?only_other_accounts=true&page=true",
                    "partOf": "https://example.com/user/mouse/quotation/13/replies",
                    "items": [],
                },
            },
            "inReplyToFilm": self.film.remote_id,
            "quote": "quote body",
        }

    def test_quotation_activity(self):
        """create a Quotation ap object from json"""
        quotation = activitypub.Quotation(**self.status_data)

        self.assertEqual(quotation.type, "Quotation")
        self.assertEqual(quotation.id, "https://example.com/user/mouse/quotation/13")
        self.assertEqual(quotation.content, "commentary")
        self.assertEqual(quotation.quote, "quote body")
        self.assertEqual(quotation.inReplyToFilm, self.film.remote_id)
        self.assertEqual(quotation.published, "2020-05-10T02:38:31.150343+00:00")

    def test_activity_to_model(self):
        """create a model instance from an activity object"""
        activity = activitypub.Quotation(**self.status_data)
        quotation = activity.to_model(model=models.Quotation)

        self.assertEqual(quotation.film, self.film)
        self.assertEqual(quotation.user, self.user)
