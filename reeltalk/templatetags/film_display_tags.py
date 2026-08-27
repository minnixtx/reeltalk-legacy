"""template filters"""

from django import template
from django.core.exceptions import FieldError
from reeltalk import models


register = template.Library()


@register.filter(name="review_count")
def get_review_count(film):
    """how many reviews?"""
    return models.Review.objects.filter(deleted=False, film=film).count()


@register.filter(name="film_description")
def get_film_description(film):
    """the film's description, if it has one"""
    if film.description:
        return film.description
    return None


@register.filter(name="blocked_film_filter")
def blocked_film_filter(queryset, viewer):
    """filter out blocked films from querysets"""

    if not viewer or not viewer.is_authenticated:
        return queryset

    blocked = viewer.blocked_films.all().values_list("id", flat=True)
    try:
        return queryset.exclude(film__in=blocked)
    except FieldError:
        return queryset
