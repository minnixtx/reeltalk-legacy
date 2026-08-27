"""Handle user activity"""

from django.db import transaction

from reeltalk import models
from reeltalk.utils import sanitizer


def create_generated_note(user, content, mention_films=None, privacy="public"):
    """a note created by the app about user activity"""
    # sanitize input html
    content = sanitizer.clean(content)

    with transaction.atomic():
        # create but don't save
        status = models.GeneratedNote(user=user, content=content, privacy=privacy)
        # we have to save it to set the related fields, but hold off on telling
        # folks about it because it is not ready
        status.save(broadcast=False)

        if mention_films:
            status.mention_films.set(mention_films)
        status.save(created=True)
    return status
