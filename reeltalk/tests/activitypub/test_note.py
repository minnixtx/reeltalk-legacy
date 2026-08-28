"""tests functionality specifically for the Note ActivityPub dataclass"""

from unittest.mock import patch

from django.test import TestCase

from reeltalk import activitypub
from reeltalk import models


class Note(TestCase):
    """the model-linked ActivityPub dataclass for Note-based types"""

    @classmethod
    def setUpTestData(cls):
        """create a shared user"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            cls.user = models.User.objects.create_user(
                "mouse", "mouse@mouse.mouse", "mouseword", local=True, localname="mouse"
            )
        cls.user.remote_id = "https://test-instance.org/user/critic"
        cls.user.save(broadcast=False, update_fields=["remote_id"])

        cls.film = models.Film.objects.create(title="Test Film")

    def test_to_model_hashtag_postprocess_content(self):
        """test that hashtag links are post-processed and link to local URLs"""
        update_data = activitypub.Comment(
            id="https://test-instance.org/user/critic/comment/42",
            attributedTo=self.user.remote_id,
            inReplyToFilm=self.film.remote_id,
            content="<p>This is interesting "
            + '<a href="https://test-instance.org/hashtag/2" data-mention="hashtag">'
            + "#filmclub</a></p>",
            published="2023-02-17T23:12:59.398030+00:00",
            to=[],
            cc=[],
            tag=[
                {
                    "type": "Film",
                    "name": "test film",
                    "href": self.film.remote_id,
                },
                {
                    "type": "Hashtag",
                    "name": "#FilmClub",
                    "href": "https://test-instance.org/hashtag/2",
                },
            ],
        )

        instance = update_data.to_model(model=models.Status)
        self.assertIsNotNone(instance)
        hashtag = models.Hashtag.objects.filter(name="#FilmClub").first()
        self.assertIsNotNone(hashtag)
        self.assertEqual(
            instance.content,
            "<p>This is interesting "
            + f'<a href="{hashtag.remote_id}" data-mention="hashtag">'
            + "#filmclub</a></p>",
        )
