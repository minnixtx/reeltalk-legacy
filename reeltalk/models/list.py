"""make a list of films!!"""

from typing import Optional, Iterable
import uuid

from django.contrib.postgres.indexes import Index
from django.core.exceptions import PermissionDenied
from django.db import models
from django.db.models import Q
from django.utils import timezone

from reeltalk import activitypub
from reeltalk.settings import BASE_URL
from reeltalk.utils.db import add_update_fields

from .activitypub_mixin import CollectionItemMixin, OrderedCollectionMixin
from .base_model import ReelTalkModel
from .group import GroupMember
from . import fields

CurationType = models.TextChoices(
    "Curation",
    ["closed", "open", "curated", "group"],
)


class AbstractList(OrderedCollectionMixin, ReelTalkModel):
    """Abstract model for lists of films"""

    embed_key = models.UUIDField(unique=True, null=True, editable=False)
    activity_serializer = activitypub.FilmList
    privacy = fields.PrivacyField()
    user = fields.ForeignKey(
        "User", on_delete=models.PROTECT, activitypub_field="owner"
    )

    def save(self, *args, update_fields: Optional[Iterable[str]] = None, **kwargs):
        """on save, update embed_key and avoid clash with existing code"""
        if not self.embed_key:
            self.embed_key = uuid.uuid4()
            update_fields = add_update_fields(update_fields, "embed_key")

        super().save(*args, update_fields=update_fields, **kwargs)

    @property
    def collection_queryset(self):
        raise NotImplementedError

    class Meta:
        """default sorting"""

        ordering = ("-updated_date",)
        abstract = True


class List(AbstractList):
    """a list of films"""

    films = models.ManyToManyField(
        "Film",
        symmetrical=False,
        through="ListItem",
        through_fields=("film_list", "film"),
    )
    name = fields.CharField(max_length=100)
    description = fields.TextField(blank=True, null=True, activitypub_field="summary")
    curation = fields.CharField(
        max_length=255, default="closed", choices=CurationType.choices
    )
    group = models.ForeignKey(
        "Group",
        on_delete=models.SET_NULL,
        default=None,
        blank=True,
        null=True,
    )

    class Meta:
        """default sorting"""

        indexes = [Index(fields=["privacy", "-updated_date"])]

    @property
    def collection_queryset(self):
        """list of films for this list, overrides OrderedCollectionMixin"""
        return self.films.filter(listitem__approved=True).order_by("listitem")

    def get_remote_id(self):
        """don't want the user to be in there in this case"""
        return f"{BASE_URL}/list/{self.id}"

    def raise_not_editable(self, viewer):
        """the associated user OR the list owner can edit"""
        if self.user == viewer:
            return
        # group members can edit items in group lists
        is_group_member = GroupMember.objects.filter(
            group=self.group, user=viewer
        ).exists()
        if is_group_member:
            return
        super().raise_not_editable(viewer)

    def raise_not_submittable(self, viewer):
        """can the user submit a book to the list?"""
        # if you can't view the list you can't submit to it
        self.raise_visible_to_user(viewer)

        # all good if you're the owner or the list is open
        if self.user == viewer or self.curation in ["open", "curated"]:
            return
        if self.curation == "group":
            is_group_member = GroupMember.objects.filter(
                group=self.group, user=viewer
            ).exists()
            if is_group_member:
                return
        raise PermissionDenied()

    @classmethod
    def followers_filter(cls, queryset, viewer):
        """Override filter for "followers" privacy level to allow non-following
        group members to see the existence of group lists"""

        return queryset.exclude(
            ~Q(  # user isn't following or group member
                Q(user__followers=viewer)
                | Q(user=viewer)
                | Q(group__memberships__user=viewer)
            ),
            privacy="followers",  # and the status (of the list) is followers only
        )

    @classmethod
    def direct_filter(cls, queryset, viewer):
        """Override filter for "direct" privacy level to allow
        group members to see the existence of group lists"""

        return queryset.exclude(
            ~Q(  # user not self and not in the group if this is a group list
                Q(user=viewer) | Q(group__memberships__user=viewer)
            ),
            privacy="direct",
        )

    @classmethod
    def remove_from_group(cls, owner, user):
        """remove a list from a group"""

        cls.objects.filter(group__user=owner, user=user).all().update(
            group=None, curation="closed"
        )


class AbstractListItem(CollectionItemMixin, ReelTalkModel):
    """Abstract class for list items for all types of lists"""

    user = fields.ForeignKey(
        "User", on_delete=models.PROTECT, activitypub_field="actor"
    )
    notes = fields.HtmlField(blank=True, null=True, max_length=300)
    raw_notes = models.TextField(blank=True, null=True, max_length=300)

    endorsement = models.ManyToManyField("User", related_name="endorsers")

    activity_serializer = activitypub.ListItem
    collection_field = "film_list"

    def endorse(self, user):
        """another user supports this suggestion"""
        # you can't endorse your own contribution, silly
        if user == self.user:
            return
        self.endorsement.add(user)

    def unendorse(self, user):
        """the user rescinds support this suggestion"""
        if user == self.user:
            return
        self.endorsement.remove(user)

    def raise_not_deletable(self, viewer):
        """the associated user OR the list owner can delete"""
        if self.film_list.user == viewer:
            return
        super().raise_not_deletable(viewer)

    class Meta:
        """A film may only be placed into a list once,
        and each order in the list may be used only once"""

        ordering = ("-created_date",)
        abstract = True


class ListItem(AbstractListItem):
    """ok"""

    film = fields.ForeignKey("Film", on_delete=models.PROTECT, activitypub_field="film")

    film_list = models.ForeignKey("List", on_delete=models.CASCADE)
    approved = models.BooleanField(default=True)
    order = fields.IntegerField()

    @property
    def edit_path_name(self):
        """the form submit link to edit this item"""
        return "list-item"

    @property
    def privacy(self):
        """inherit the privacy of the list, or direct if pending"""
        collection_field = getattr(self, self.collection_field)
        if self.approved:
            return collection_field.privacy
        return "direct"

    def raise_not_deletable(self, viewer):
        """the associated user OR the list owner can delete"""
        # group members can delete items in group lists
        is_group_member = GroupMember.objects.filter(
            group=self.film_list.group, user=viewer
        ).exists()
        if is_group_member:
            return
        super().raise_not_deletable(viewer)

    def save(self, *args, **kwargs):
        """Update the list's date"""
        super().save(*args, **kwargs)
        # tick the updated date on the parent list
        self.film_list.updated_date = timezone.now()
        self.film_list.save(broadcast=False, update_fields=["updated_date"])

    class Meta:
        """A film may only be placed into a list once,
        and each order in the list may be used only once"""

        unique_together = (("film", "film_list"), ("order", "film_list"))
