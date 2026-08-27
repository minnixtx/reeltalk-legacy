"""template filters"""

from django import template
from django.db.models import Avg

from reeltalk import models
from reeltalk.utils import cache


register = template.Library()


@register.filter(name="rating")
def get_rating(film, user):
    """get the overall rating of a film"""
    return cache.get_or_set(
        f"film-rating-{film.id}",
        lambda u, f: models.Review.objects.filter(
            film=f, rating__gt=0
        ).aggregate(Avg("rating"))["rating__avg"]
        or 0,
        user,
        film,
        timeout=15552000,
    )


@register.filter(name="user_rating")
def get_user_rating(film, user):
    """get a user's rating of a film"""
    rating = (
        models.Review.objects.filter(
            user=user,
            film=film,
            rating__isnull=False,
            deleted=False,
        )
        .order_by("-published_date")
        .first()
    )
    if rating:
        return rating.rating
    return 0
