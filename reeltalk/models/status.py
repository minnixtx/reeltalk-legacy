"""models for storing different kinds of Activities"""

from dataclasses import MISSING
from typing import Optional, Iterable
import re

from django.apps import apps
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.dispatch import receiver
from django.template.loader import get_template
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext_lazy
from model_utils import FieldTracker
from model_utils.managers import InheritanceManager

from reeltalk import activitypub
from reeltalk.utils.db import add_update_fields
from .activitypub_mixin import ActivitypubMixin, ActivityMixin
from .activitypub_mixin import OrderedCollectionPageMixin
from .base_model import ReelTalkModel
from . import fields


class Status(OrderedCollectionPageMixin, ReelTalkModel):
    """any post, like a reply to a review, etc"""

    user = fields.ForeignKey(
        "User", on_delete=models.PROTECT, activitypub_field="attributedTo"
    )
    content = fields.HtmlField(blank=True, null=True)
    raw_content = models.TextField(blank=True, null=True)
    mention_users = fields.TagField("User", related_name="mention_user")
    mention_films = fields.TagField("Film", related_name="mention_film")
    mention_hashtags = fields.TagField("Hashtag", related_name="mention_hashtag")
    local = models.BooleanField(default=True)
    content_warning = fields.CharField(
        max_length=500, blank=True, null=True, activitypub_field="summary"
    )
    privacy = fields.PrivacyField(max_length=255)
    sensitive = fields.BooleanField(default=False)
    # created date is different than publish date because of federated posts
    published_date = fields.DateTimeField(
        default=timezone.now, activitypub_field="published"
    )
    edited_date = fields.DateTimeField(
        blank=True, null=True, activitypub_field="updated"
    )
    deleted = models.BooleanField(default=False)
    deleted_date = models.DateTimeField(blank=True, null=True)
    favorites = models.ManyToManyField(
        "User",
        symmetrical=False,
        through="Favorite",
        through_fields=("status", "user"),
        related_name="user_favorites",
    )
    reply_parent = fields.ForeignKey(
        "self",
        null=True,
        on_delete=models.PROTECT,
        activitypub_field="inReplyTo",
    )
    thread_id = models.IntegerField(blank=True, null=True)
    # statuses get saved a few times, this indicates if they're set
    ready = models.BooleanField(default=True)

    objects = InheritanceManager()

    activity_serializer = activitypub.Note
    serialize_reverse_fields = [("attachments", "attachment", "id")]
    deserialize_reverse_fields = [("attachments", "attachment")]

    class Meta:
        """default sorting"""

        ordering = ("-published_date",)
        indexes = [
            models.Index(fields=["remote_id"]),
            models.Index(fields=["thread_id"]),
        ]

    def save(self, *args, update_fields: Optional[Iterable[str]] = None, **kwargs):
        """save and notify"""
        if self.thread_id is None and self.reply_parent:
            self.thread_id = self.reply_parent.thread_id or self.reply_parent_id
            update_fields = add_update_fields(update_fields, "thread_id")

        super().save(*args, update_fields=update_fields, **kwargs)

        if not self.reply_parent:
            self.thread_id = self.id
            super().save(broadcast=False, update_fields=["thread_id"])

    def delete(self, *args, **kwargs):
        """ "delete" a status"""
        if hasattr(self, "boosted_status"):
            # okay but if it's a boost really delete it
            super().delete(*args, **kwargs)
            return
        self.deleted = True
        # clear user content
        self.content = None
        if hasattr(self, "quotation"):
            self.quotation = None
        self.deleted_date = timezone.now()
        self.save(*args, **kwargs)

    @property
    def recipients(self):
        """tagged users who definitely need to get this status in broadcast"""
        mentions = {u for u in self.mention_users.all() if not u.local}
        if (
            hasattr(self, "reply_parent")
            and self.reply_parent
            and not self.reply_parent.user.local
        ):
            mentions.add(self.reply_parent.user)
        return list(mentions)

    @classmethod
    def ignore_activity(cls, activity, allow_external_connections=True):
        """keep notes if they are replies to existing statuses"""
        if activity.type == "Announce":
            boosted = activitypub.resolve_remote_id(
                activity.object,
                get_activity=True,
                allow_external_connections=allow_external_connections,
                model=apps.get_model("reeltalk.Status", require_ready=True),
            )
            if not boosted:
                # if we can't load the status, definitely ignore it
                return True
            # keep the boost if we would keep the status
            return cls.ignore_activity(boosted)

        # keep if it if it's a custom type
        if activity.type != "Note":
            return False
        # keep it if it's a reply to an existing status
        if cls.objects.filter(remote_id=activity.inReplyTo).exists():
            return False

        # keep notes if they mention local users
        if activity.tag == MISSING or activity.tag is None:
            return True
        # GoToSocial sends single tags as objects
        # not wrapped in a list
        tags = activity.tag if isinstance(activity.tag, list) else [activity.tag]
        user_model = apps.get_model("reeltalk.User", require_ready=True)
        for tag in tags:
            if (
                tag["type"] == "Mention"
                and user_model.objects.filter(
                    remote_id=tag["href"], local=True
                ).exists()
            ):
                # we found a mention of a known use boost
                return False
        return True

    @classmethod
    def replies(cls, status):
        """load all replies to a status. idk if there's a better way
        to write this so it's just a property"""
        return (
            cls.objects.filter(reply_parent=status)
            .select_subclasses()
            .order_by("published_date")
        )

    @property
    def status_type(self):
        """expose the type of status for the ui using activity type"""
        return self.activity_serializer.__name__

    @property
    def boostable(self):
        """you can't boost dms"""
        return self.privacy in ["unlisted", "public"]

    @property
    def page_title(self):
        """title of the page when only this status is shown"""
        return _("%(display_name)s's status") % {"display_name": self.user.display_name}

    @property
    def page_description(self):
        """description of the page in meta tags when only this status is shown"""
        return None

    @property
    def page_image(self):
        """image to use as preview in meta tags when only this status is shown"""
        if self.mention_films.exists():
            film = self.mention_films.first()
            return film.poster
        return self.user.preview_image

    def to_replies(self, **kwargs):
        """helper function for loading AP serialized replies to a status"""
        return self.to_ordered_collection(
            self.replies(self),
            remote_id=f"{self.remote_id}/replies",
            collection_only=True,
            **kwargs,
        ).serialize()

    def to_activity_dataclass(self, pure=False):
        """return tombstone if the status is deleted"""
        if self.deleted:
            return activitypub.Tombstone(
                id=self.remote_id,
                url=self.remote_id,
                deleted=self.deleted_date.isoformat(),
                published=self.deleted_date.isoformat(),
            )
        activity = ActivitypubMixin.to_activity_dataclass(self)
        activity.replies = self.to_replies()

        # "pure" serialization for non-reeltalk instances
        if pure and hasattr(self, "pure_content"):
            activity.content = self.pure_content
            if hasattr(activity, "name"):
                activity.name = self.pure_name
            activity.type = self.pure_type
            film = getattr(self, "film", None)
            films = [film] if film else []
            films += list(self.mention_films.all())
            posters = [
                activitypub.Document(
                    url=fields.get_absolute_url(f.poster),
                    name=f.alt_text,
                )
                for f in films
                if f and f.poster
            ]
            activity.attachment = posters
        return activity

    def to_activity(self, pure=False):
        """json serialized activitypub class"""
        return self.to_activity_dataclass(pure=pure).serialize()

    def raise_not_editable(self, viewer):
        """certain types of status aren't editable"""
        # first, the standard raise
        super().raise_not_editable(viewer)
        # if it's an edit (not a create) you can only edit content statuses
        if self.id and isinstance(self, (GeneratedNote, ReviewRating)):
            raise PermissionDenied()

    @classmethod
    def privacy_filter(cls, viewer, privacy_levels=None):
        queryset = super().privacy_filter(viewer, privacy_levels=privacy_levels)
        return queryset.filter(deleted=False, user__is_active=True)

    @classmethod
    def direct_filter(cls, queryset, viewer):
        """Overridden filter for "direct" privacy level"""
        return queryset.exclude(
            ~Q(Q(user=viewer) | Q(mention_users=viewer)), privacy="direct"
        )

    @classmethod
    def blocked_film_filter(cls, viewer, privacy_levels=None):
        """filter out all statuses related to a film this user has blocked"""

        queryset = super().privacy_filter(viewer, privacy_levels=privacy_levels)

        if not viewer or not viewer.is_authenticated:
            return queryset

        blocked = viewer.blocked_films.values_list("id", flat=True)

        film_comments = queryset.filter(comment__film__in=blocked)
        film_quotations = queryset.filter(quotation__film__in=blocked)
        film_reviews = queryset.filter(review__film__in=blocked)
        film_mentions = queryset.filter(mention_films__in=blocked)
        film_statuses = film_comments.union(film_quotations, film_reviews, film_mentions)

        threads = film_statuses.values_list("thread_id", flat=True)
        thread_statuses = queryset.exclude(
            id__in=film_statuses.values_list("id", flat=True)
        ).filter(thread_id__in=threads)

        exclude = film_statuses.union(thread_statuses).values_list("id", flat=True)

        return queryset.exclude(id__in=exclude).filter(
            deleted=False, user__is_active=True
        )

    @classmethod
    def followers_filter(cls, queryset, viewer):
        """Override-able filter for "followers" privacy level"""
        return queryset.exclude(
            ~Q(  # not yourself, a follower, or someone who is tagged
                Q(user__followers=viewer) | Q(user=viewer) | Q(mention_users=viewer)
            ),
            privacy="followers",  # and the status is followers only
        )


class GeneratedNote(Status):
    """these are app-generated messages about user activity"""

    @property
    def pure_content(self):
        """indicate the film in question for mastodon (or w/e) users"""
        message = self.content
        films = ", ".join(
            f'<a href="{film.remote_id}"><i>{film.title}</i></a>'
            for film in self.mention_films.all()
        )
        return f"{self.user.display_name} {message} {films}"

    activity_serializer = activitypub.GeneratedNote
    pure_type = "Note"


ReadingStatusChoices = models.TextChoices(
    "ReadingStatusChoices", ["to-read", "read"]
)


class FilmStatus(Status):
    """Shared fields for comments, quotes, reviews"""

    film = fields.ForeignKey(
        "Film", on_delete=models.PROTECT, activitypub_field="inReplyToFilm"
    )
    pure_type = "Note"

    reading_status = fields.CharField(
        max_length=255, choices=ReadingStatusChoices.choices, null=True, blank=True
    )

    class Meta:
        """not a real model, sorry"""

        abstract = True

    @property
    def page_image(self):
        return self.film.poster or super().page_image


class Comment(FilmStatus):
    """like a review but without a rating and transient"""

    @property
    def pure_content(self):
        """indicate the film in question for mastodon (or w/e) users"""
        citation = (
            f'comment on <a href="{self.film.remote_id}"><i>{self.film.title}</i></a>'
        )
        return f"{self.content}<p>({citation})</p>"

    activity_serializer = activitypub.Comment

    @property
    def page_title(self):
        return _("%(display_name)s's comment on %(film_title)s") % {
            "display_name": self.user.display_name,
            "film_title": self.film.title,
        }


class Quotation(FilmStatus):
    """like a review but without a rating and transient"""

    quote = fields.HtmlField()
    raw_quote = models.TextField(blank=True, null=True)

    @property
    def pure_content(self):
        """indicate the film in question for mastodon (or w/e) users"""
        quote = re.sub(r"^<p>", '<p>"', self.quote)
        quote = re.sub(r"</p>$", '"</p>', quote)
        title, href = self.film.title, self.film.remote_id
        director = f"{name}: " if (name := self.film.director_text) else ""
        citation = f'— {director}<a href="{href}"><i>{title}</i></a>'
        return f"{quote} <p>{citation}</p>{self.content}"

    activity_serializer = activitypub.Quotation

    @property
    def page_title(self):
        return _("%(display_name)s's quote from %(film_title)s") % {
            "display_name": self.user.display_name,
            "film_title": self.film.title,
        }


class Review(FilmStatus):
    """a film review"""

    name = fields.CharField(max_length=255, null=True, blank=True)
    rating = fields.DecimalField(
        default=None,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.5), MaxValueValidator(5)],
        decimal_places=2,
        max_digits=3,
    )

    field_tracker = FieldTracker(fields=["rating"])

    @property
    def pure_name(self):
        """clarify review names for mastodon serialization"""
        template = get_template("snippets/generated_status/review_pure_name.html")
        return template.render(
            {"film": self.film, "rating": self.rating, "name": self.name}
        ).strip()

    @property
    def pure_content(self):
        """indicate the film in question for mastodon (or w/e) users"""
        if self.content:
            return self.content
        else:
            template = get_template("snippets/generated_status/rating_pure_name.html")
            return template.render({"film": self.film, "rating": self.rating}).strip()

    @property
    def page_title(self):
        return _("%(display_name)s's review of %(film_title)s") % {
            "display_name": self.user.display_name,
            "film_title": self.film.title,
        }

    activity_serializer = activitypub.Review
    pure_type = "Article"

    def save(self, *args, **kwargs):
        """clear rating caches"""
        super().save(*args, **kwargs)

        cache.delete(f"film-rating-{self.film.id}")


class ReviewRating(Review):
    """a subtype of review that only contains a rating"""

    def save(self, *args, **kwargs):
        if not self.rating:
            raise ValueError("ReviewRating object must include a numerical rating")
        super().save(*args, **kwargs)

    @property
    def pure_content(self):
        template = get_template("snippets/generated_status/rating.html")
        return template.render({"film": self.film, "rating": self.rating}).strip()

    @property
    def page_description(self):
        return ngettext_lazy(
            "%(display_name)s rated %(film_title)s: %(display_rating).1f star",
            "%(display_name)s rated %(film_title)s: %(display_rating).1f stars",
            "display_rating",
        ) % {
            "display_name": self.user.display_name,
            "film_title": self.film.title,
            "display_rating": self.rating,
        }

    activity_serializer = activitypub.Rating
    pure_type = "Note"


class Boost(ActivityMixin, Status):
    """boost'ing a post"""

    boosted_status = fields.ForeignKey(
        "Status",
        on_delete=models.PROTECT,
        related_name="boosters",
        activitypub_field="object",
    )
    activity_serializer = activitypub.Announce

    def save(self, *args, **kwargs):
        """save and notify"""
        # This constraint can't work as it would cross tables.
        # class Meta:
        #     unique_together = ('user', 'boosted_status')
        if (
            Boost.objects.filter(boosted_status=self.boosted_status, user=self.user)
            .exclude(id=self.id)
            .exists()
        ):
            return

        super().save(*args, **kwargs)

    def __init__(self, *args, **kwargs):
        """the user field is "actor" here instead of "attributedTo" """
        super().__init__(*args, **kwargs)

        reserve_fields = ["user", "boosted_status", "published_date", "privacy"]
        self.simple_fields = [f for f in self.simple_fields if f.name in reserve_fields]
        self.activity_fields = self.simple_fields
        self.many_to_many_fields = []
        self.image_fields = []
        self.deserialize_reverse_fields = []
