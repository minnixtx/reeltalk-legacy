"""template filters"""

from dateutil.relativedelta import relativedelta
from django import template
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import naturaltime, naturalday
from django.template.loader import select_template
from django.utils import timezone
from reeltalk import models
from reeltalk.templatetags.utilities import get_user_identifier


register = template.Library()


@register.filter(name="mentions")
def get_mentions(status, user):
    """people to @ in a reply: the parent and all mentions"""
    mentions = set([status.user] + list(status.mention_users.all()))
    return (
        " ".join("@" + get_user_identifier(m) for m in mentions if not m == user) + " "
    )


@register.filter(name="replies")
def get_replies(status):
    """get all direct replies to a status"""
    # TODO: this limit could cause problems
    return models.Status.objects.filter(
        reply_parent=status,
        deleted=False,
    ).select_subclasses()[:10]


@register.filter(name="parent")
def get_parent(status):
    """get the reply parent for a status"""
    return (
        models.Status.objects.filter(id=status.reply_parent_id)
        .select_subclasses()
        .first()
    )


@register.filter(name="boosted_status")
def get_boosted(boost):
    """load a boosted status. have to do this or it won't get foreign keys"""
    return (
        models.Status.objects.select_subclasses()
        .select_related("user", "reply_parent")
        .prefetch_related("mention_films", "mention_users")
        .get(id=boost.boosted_status.id)
    )


@register.filter(name="published_date")
def get_published_date(date):
    """less verbose combo of humanize filters"""
    if not date:
        return ""
    now = timezone.now()
    delta = relativedelta(now, date)
    if delta.years:
        return naturalday(date)
    if delta.days or delta.months:
        return naturalday(date, settings.MONTH_DAY_FORMAT)
    return naturaltime(date)


@register.simple_tag()
def get_header_template(status):
    """get the path for the status template"""
    if isinstance(status, models.Boost):
        status = status.boosted_status
    try:
        header_type = status.reading_status.replace("-", "_")
        if not header_type:
            raise AttributeError()
    except AttributeError:
        header_type = status.status_type.lower()
    filename = f"snippets/status/headers/{header_type}.html"
    return select_template([filename, "snippets/status/headers/note.html"])


@register.simple_tag(takes_context=False)
def load_film(status):
    """load the film a status is about, or the first mentioned film"""
    return status.film if hasattr(status, "film") else status.mention_films.first()


@register.simple_tag(takes_context=False)
def get_user_review(film, user):
    """the current user's existing review of a film, if any (one review per film)"""
    if not user.is_authenticated:
        return None
    return film.review_set.filter(user=user, deleted=False).first()


@register.simple_tag(takes_context=False)
def show_review_header(status_type, content):
    """whether a status shows its name+stars header (template ifs can't group with parens)"""
    return status_type == "Review" or (status_type == "Rating" and bool(content))
