"""template filters"""

from django import template
from django.db.models import Avg, StdDev, Count, F, Q

from reeltalk import models

register = template.Library()


@register.simple_tag(takes_context=False)
def get_film_superlatives():
    """get film stats for the about page"""
    total_ratings = models.Review.objects.filter(local=True, deleted=False).count()
    data = {}
    data["top_rated"] = (
        models.Film.objects.annotate(
            rating=Avg(
                "review__rating",
                filter=Q(review__user__local=True, review__deleted=False),
            ),
            rating_count=Count(
                "review", filter=Q(review__user__local=True, review__deleted=False)
            ),
        )
        .annotate(weighted=F("rating") * F("rating_count") / total_ratings)
        .filter(rating__gt=4, weighted__gt=0)
        .order_by("-weighted")
        .first()
    )

    data["controversial"] = (
        models.Film.objects.annotate(
            deviation=StdDev(
                "review__rating",
                filter=Q(review__user__local=True, review__deleted=False),
            ),
            rating_count=Count(
                "review", filter=Q(review__user__local=True, review__deleted=False)
            ),
        )
        .annotate(weighted=F("deviation") * F("rating_count") / total_ratings)
        .filter(weighted__gt=0)
        .order_by("-weighted")
        .first()
    )

    data["wanted"] = (
        models.Film.objects.annotate(
            shelf_count=Count(
                "shelffilm", filter=Q(shelffilm__shelf__identifier="to-read")
            )
        )
        .order_by("-shelf_count")
        .first()
    )
    return data


@register.simple_tag(takes_context=False)
def get_landing_films():
    """list of films for the landing page"""
    return models.Film.objects.distinct().order_by("-updated_date")[:20]
