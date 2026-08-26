"""database schema for films"""

import re
from functools import reduce
import operator
from typing import Any, Dict, Optional, Iterable
from typing_extensions import Self
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex, BloomIndex
from django.db import models
from django.db.models import ManyToManyField, Q
from imagekit.models import ImageSpecField
import pgtrigger

from reeltalk import activitypub
from reeltalk.settings import ENABLE_THUMBNAIL_GENERATION
from reeltalk.utils.db import add_update_fields

from .activitypub_mixin import ObjectMixin
from .base_model import ReelTalkModel
from . import fields


class MergedFilm(models.Model):
    """a Film instance that has been merged into another instance. kept
    to be able to redirect old URLs"""

    deleted_id = models.IntegerField(primary_key=True)
    merged_into = fields.ForeignKey(
        "Film", on_delete=models.PROTECT, related_name="absorbed"
    )


class Film(ObjectMixin, ReelTalkModel):
    """a film — one object per title"""

    merged_model = MergedFilm

    # film metadata
    title = fields.TextField(max_length=255)
    sort_title = fields.CharField(max_length=255, blank=True, null=True)
    subtitle = fields.TextField(max_length=255, blank=True, null=True)
    description = fields.HtmlField(blank=True, null=True)
    year = fields.IntegerField(blank=True, null=True)
    runtime = fields.IntegerField(blank=True, null=True)  # in minutes

    genres = fields.ArrayField(
        models.CharField(max_length=255), blank=True, default=list
    )
    directors = fields.ArrayField(
        models.CharField(max_length=255), blank=True, default=list
    )
    cast = fields.ArrayField(
        models.CharField(max_length=255), blank=True, default=list
    )

    poster = fields.ImageField(
        upload_to="posters/", blank=True, null=True, alt_field="alt_text"
    )

    # identifiers
    origin_id = models.CharField(max_length=255, null=True, blank=True)
    tmdb_id = fields.CharField(
        max_length=255, blank=True, null=True, deduplication_field=True
    )
    imdb_id = fields.CharField(
        max_length=255, blank=True, null=True, deduplication_field=True
    )

    search_vector = SearchVectorField(null=True)

    last_edited_by = fields.ForeignKey(
        "User",
        on_delete=models.PROTECT,
        null=True,
    )

    name_field = "title"
    activity_serializer = activitypub.Film

    if ENABLE_THUMBNAIL_GENERATION:
        poster_bw_film_xsmall_webp = ImageSpecField(
            source="poster", id="film:xsmall:webp"
        )
        poster_bw_film_xsmall_jpg = ImageSpecField(
            source="poster", id="film:xsmall:jpg"
        )
        poster_bw_film_small_webp = ImageSpecField(
            source="poster", id="film:small:webp"
        )
        poster_bw_film_small_jpg = ImageSpecField(source="poster", id="film:small:jpg")
        poster_bw_film_medium_webp = ImageSpecField(
            source="poster", id="film:medium:webp"
        )
        poster_bw_film_medium_jpg = ImageSpecField(source="poster", id="film:medium:jpg")
        poster_bw_film_large_webp = ImageSpecField(
            source="poster", id="film:large:webp"
        )
        poster_bw_film_large_jpg = ImageSpecField(source="poster", id="film:large:jpg")
        poster_bw_film_xlarge_webp = ImageSpecField(
            source="poster", id="film:xlarge:webp"
        )
        poster_bw_film_xlarge_jpg = ImageSpecField(source="poster", id="film:xlarge:jpg")
        poster_bw_film_xxlarge_webp = ImageSpecField(
            source="poster", id="film:xxlarge:webp"
        )
        poster_bw_film_xxlarge_jpg = ImageSpecField(source="poster", id="film:xxlarge:jpg")

    @property
    def director_text(self):
        """format a list of directors"""
        return ", ".join(self.directors)

    @property
    def alt_text(self):
        """image alt text"""
        director = f"{name}: " if (name := self.director_text) else ""
        year = f" ({self.year})" if self.year else ""
        return f"{director}{self.title}{year}"

    def save(
        self, *args: Any, update_fields: Optional[Iterable[str]] = None, **kwargs: Any
    ) -> None:
        """ensure that the remote_id is within this instance"""
        if self.id:
            self.remote_id = self.get_remote_id()
            update_fields = add_update_fields(update_fields, "remote_id")
        else:
            self.origin_id = self.remote_id
            self.remote_id = None
            update_fields = add_update_fields(update_fields, "origin_id", "remote_id")

        # Create sort title by removing leading articles from the title
        if self.sort_title in [None, ""]:
            self.sort_title = self.guess_sort_title()
            update_fields = add_update_fields(update_fields, "sort_title")

        super().save(*args, update_fields=update_fields, **kwargs)

    def broadcast(self, activity, sender, software="reeltalk", **kwargs):
        """only send film data updates to other reeltalk instances"""
        super().broadcast(activity, sender, software=software, **kwargs)

    def guess_sort_title(self):
        """Get a best-guess sort title for the current film"""
        return re.sub(r"^(the|a|an) ", "", str(self.title).lower())

    @classmethod
    def find_existing(cls, data):
        """compare data to fields that can be used for deduplication.
        This always includes remote_id, but can also be unique identifiers
        like a tmdb id or imdb id"""
        filters = []
        # grabs all the data from the model to create django queryset filters
        for field in cls._meta.get_fields():
            if (
                not hasattr(field, "deduplication_field")
                or not field.deduplication_field
            ):
                continue

            value = data.get(field.get_activitypub_field())
            if not value:
                continue
            filters.append({field.name: value})

        if "id" in data:
            # kinda janky, but this handles the special case where the
            # incoming object's id is one of our own remote ids
            filters.append({"origin_id": data["id"]})

        if not filters:
            # if there are no deduplication fields, it will match the first
            # item no matter what. this shouldn't happen but just in case.
            return None

        # an OR operation on all the match fields, sorry for the dense syntax
        match = cls.objects.filter(reduce(operator.or_, (Q(**f) for f in filters)))
        # there OUGHT to be only one match
        return match.first()

    def merge_into(self, canonical: Self, dry_run=False) -> Dict[str, Any]:
        """merge this entity into another entity"""
        if canonical.id == self.id:
            raise ValueError(f"Cannot merge {self} into itself")

        absorbed_fields = canonical.absorb_data_from(self, dry_run=dry_run)

        if dry_run:
            return absorbed_fields

        canonical.save()

        self.merged_model.objects.create(deleted_id=self.id, merged_into=canonical)

        # move related models to canonical
        related_models = [
            (r.remote_field.name, r.related_model) for r in self._meta.related_objects
        ]
        for related_field, related_model in related_models:
            # Skip the ManyToMany fields that aren’t auto-created. These
            # should have a corresponding OneToMany field in the model for
            # the linking table anyway. If we update it through that model
            # instead then we won’t lose the extra fields in the linking
            # table.

            related_field_obj = related_model._meta.get_field(related_field)
            if isinstance(related_field_obj, ManyToManyField):
                through = related_field_obj.remote_field.through
                if not through._meta.auto_created:
                    continue
            related_objs = related_model.objects.filter(**{related_field: self})
            for related_obj in related_objs:
                try:
                    setattr(related_obj, related_field, canonical)
                    related_obj.save()
                except TypeError:
                    getattr(related_obj, related_field).add(canonical)
                    getattr(related_obj, related_field).remove(self)

        self.delete()
        return absorbed_fields

    def absorb_data_from(self, other: Self, dry_run=False) -> Dict[str, Any]:
        """fill empty fields with values from another entity"""
        absorbed_fields = {}
        for data_field in self._meta.get_fields():
            if not hasattr(data_field, "activitypub_field"):
                continue
            canonical_value = getattr(self, data_field.name)
            other_value = getattr(other, data_field.name)
            if not other_value:
                continue
            if isinstance(data_field, fields.ArrayField):
                if new_values := list(set(other_value) - set(canonical_value)):
                    # append at the end (in no particular order)
                    if not dry_run:
                        setattr(self, data_field.name, canonical_value + new_values)
                    absorbed_fields[data_field.name] = new_values
            else:
                if not canonical_value:
                    if not dry_run:
                        setattr(self, data_field.name, other_value)
                    absorbed_fields[data_field.name] = other_value
        return absorbed_fields

    def __repr__(self):
        return "<{} key={!r} title={!r}>".format(
            self.__class__,
            self.tmdb_id or self.imdb_id,
            self.title,
        )

    class Meta:
        """set up indexes and triggers"""

        indexes = [
            GinIndex(fields=["search_vector"]),
            # Add bloom index for all deduplication_fields
            BloomIndex(
                fields=[
                    "origin_id",
                    "remote_id",
                    "tmdb_id",
                    "imdb_id",
                ]
            ),
        ]
        triggers = [
            pgtrigger.Trigger(
                name="update_search_vector_on_film_edit",
                when=pgtrigger.Before,
                operation=pgtrigger.Insert
                | pgtrigger.UpdateOf(
                    "title", "subtitle", "directors", "cast", "genres", "search_vector"
                ),
                func="""
                    SELECT
                        -- title, with priority A (parse in English, default to simple if empty)
                        setweight(COALESCE(nullif(
                            to_tsvector('english', new.title), ''),
                            to_tsvector('simple', new.title)), 'A') ||

                        -- subtitle, with priority B
                        setweight(to_tsvector('english', COALESCE(new.subtitle, '')), 'B') ||

                        -- directors and cast names, with priority C
                        setweight(to_tsvector('simple', COALESCE(
                            array_to_string(COALESCE(new.directors, '{}'), ' ') || ' ' ||
                            array_to_string(COALESCE(new."cast", '{}'), ' '), '')), 'C') ||

                        -- genres, with lowest priority D
                        setweight(to_tsvector('english', COALESCE(
                            array_to_string(COALESCE(new.genres, '{}'), ' '), '')), 'D')

                        INTO new.search_vector;
                    RETURN new;
                """,
            )
        ]
