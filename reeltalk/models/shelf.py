"""puttin' films on shelves"""

import re
from typing import Optional, Iterable
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import models
from django.utils import timezone

from reeltalk import activitypub
from reeltalk.tasks import BROADCAST
from reeltalk.utils.db import add_update_fields
from .activitypub_mixin import CollectionItemMixin, OrderedCollectionMixin
from .base_model import ReelTalkModel
from . import fields


class Shelf(OrderedCollectionMixin, ReelTalkModel):
    """a list of films owned by a user"""

    TO_READ = "to-read"
    # legacy identifiers kept for migration compatibility
    READING = "reading"
    STOPPED_READING = "stopped-reading"
    READ_FINISHED = "read"

    READ_STATUS_IDENTIFIERS = (TO_READ, READ_FINISHED)

    name = fields.CharField(max_length=100)
    identifier = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True, max_length=500)
    user = fields.ForeignKey(
        "User", on_delete=models.PROTECT, activitypub_field="owner"
    )
    editable = models.BooleanField(default=True)
    privacy = fields.PrivacyField()
    films = models.ManyToManyField(
        "Film",
        symmetrical=False,
        through="ShelfFilm",
        through_fields=("shelf", "film"),
    )

    activity_serializer = activitypub.Shelf

    def save(self, *args, priority=BROADCAST, **kwargs):
        """set the identifier"""
        super().save(*args, priority=priority, **kwargs)
        if not self.identifier:
            # this needs the auto increment ID from the save() above
            self.identifier = self.get_identifier()
            super().save(*args, **kwargs, broadcast=False, update_fields={"identifier"})

    def get_identifier(self):
        """custom-shelf-123 for the url"""
        slug = re.sub(r"[^\w]", "", self.name).lower()
        return f"{slug}-{self.id}"

    @property
    def collection_queryset(self):
        """list of films for this shelf, overrides OrderedCollectionMixin"""
        return self.films.order_by("shelffilm")

    @property
    def deletable(self):
        """can the shelf be safely deleted?"""
        return self.editable and not self.shelffilm_set.exists()

    def get_remote_id(self):
        """shelf identifier instead of id"""
        base_path = self.user.remote_id
        identifier = self.identifier or self.get_identifier()
        return f"{base_path}/films/{identifier}"

    @property
    def local_path(self):
        """No slugs"""
        identifier = self.identifier or self.get_identifier()
        return f"{self.user.local_path}/films/{identifier}"

    def raise_not_deletable(self, viewer):
        """don't let anyone delete a default shelf"""
        super().raise_not_deletable(viewer)
        if not self.deletable:
            raise PermissionDenied()

    class Meta:
        """user/shelf uniqueness"""

        unique_together = ("user", "identifier")


class ShelfFilm(CollectionItemMixin, ReelTalkModel):
    """many to many join table for films and shelves"""

    film = fields.ForeignKey(
        "Film", on_delete=models.PROTECT, activitypub_field="film"
    )
    shelf = models.ForeignKey("Shelf", on_delete=models.PROTECT)
    shelved_date = models.DateTimeField(default=timezone.now)
    user = fields.ForeignKey(
        "User", on_delete=models.PROTECT, activitypub_field="actor"
    )

    activity_serializer = activitypub.ShelfItem
    collection_field = "shelf"

    def save(
        self,
        *args,
        priority=BROADCAST,
        update_fields: Optional[Iterable[str]] = None,
        **kwargs,
    ):
        if not self.user:
            self.user = self.shelf.user
            update_fields = add_update_fields(update_fields, "user")

        is_update = self.id is not None
        super().save(*args, priority=priority, update_fields=update_fields, **kwargs)

        if is_update and self.user.local:
            cache.delete(f"film-on-shelf-{self.film.id}-{self.shelf_id}")

    def delete(self, *args, **kwargs):
        if self.id and self.user.local:
            cache.delete(f"film-on-shelf-{self.film.id}-{self.shelf_id}")
        super().delete(*args, **kwargs)

    class Meta:
        """an opinionated constraint!
        you can't put a film on shelf twice"""

        unique_together = ("film", "shelf")
        ordering = ("-shelved_date", "-created_date", "-updated_date")
