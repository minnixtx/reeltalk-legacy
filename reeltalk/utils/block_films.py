"""
Function for filtering out blocked films on any relevant queryset
For statuses instead use self.blocked_film_filter(viewer)
"""

from typing import Any

from django.core.exceptions import FieldError
from django.db.models.query import QuerySet


def blocked_film_filter(queryset: QuerySet[Any], viewer: Any) -> QuerySet[Any]:
    """filter out rows whose related film the viewer has blocked"""

    if not viewer or not viewer.is_authenticated:
        return queryset

    blocked = viewer.blocked_films.all().values_list("id", flat=True)

    try:
        return queryset.exclude(film__in=blocked)
    except FieldError:
        return queryset
