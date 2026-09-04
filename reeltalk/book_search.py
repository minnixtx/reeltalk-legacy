"""search films in the local database"""

from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any, Literal, Optional, Union, overload

from django.contrib.postgres.search import SearchRank, SearchQuery
from django.db.models import F, Q
from django.db.models.query import QuerySet

from reeltalk import models
from reeltalk.settings import MEDIA_FULL_URL


@overload
def search(
    query: str,
    *,
    min_confidence: float = 0,
    filters: Optional[list[Any]] = None,
    return_first: Literal[False],
) -> QuerySet[models.Film]: ...


@overload
def search(
    query: str,
    *,
    min_confidence: float = 0,
    filters: Optional[list[Any]] = None,
    return_first: Literal[True],
) -> Optional[models.Film]: ...


def search(
    query: str,
    *,
    min_confidence: float = 0,
    filters: Optional[list[Any]] = None,
    return_first: bool = False,
    films: Optional[QuerySet[models.Film]] = None,
) -> Union[Optional[models.Film], QuerySet[models.Film]]:
    """search your local database"""
    filters = filters or []
    if not query:
        return None if return_first else []
    query = query.strip()

    results = None
    # first, try searching unique identifiers
    # unique identifiers never have spaces, titles usually do
    if " " not in query:
        results = search_identifiers(
            query, *filters, return_first=return_first, films=films
        )

    # if there were no identifier results...
    if not results:
        # then try searching title/director/cast/genres
        results = search_title(
            query, min_confidence, *filters, return_first=return_first, films=films
        )
    return results


def search_identifiers(
    query,
    *filters,
    return_first=False,
    films=None,
) -> Union[Optional[models.Film], QuerySet[models.Film]]:
    """search Films by deduplication fields

    Best for cases when we can assume someone is searching for an exact match on
    commonly unique data identifiers like a tmdb or imdb id.
    """
    films = films or models.Film.objects
    film_deduplication_fields = [
        {f.name: query}
        for f in models.Film._meta.get_fields()
        if hasattr(f, "deduplication_field") and f.deduplication_field
    ]

    results = None
    # We assume that identifier hits only one field and we care only first hit
    #  searching each field separately makes overall search a little slower in
    #  case all fields need to be checked, but each query is really small for db load.
    for f in film_deduplication_fields[::-1]:
        field_results = films.filter(*filters, Q(**f))
        if field_results.exists() is False:
            continue
        if return_first:
            return field_results.first()
        if results is None:
            results = field_results
        else:
            results |= field_results

    return results


def search_title(
    query,
    min_confidence,
    *filters,
    return_first=False,
    films=None,
) -> QuerySet[models.Film]:
    """searches for title, subtitle, directors, cast and genres"""
    films = films or models.Film.objects
    query = SearchQuery(query, config="simple") | SearchQuery(query, config="english")
    results = (
        films.filter(*filters, search_vector=query)
        .annotate(rank=SearchRank(F("search_vector"), query, normalization=32))
        .filter(rank__gt=min_confidence)
        .order_by("-rank", "sort_title")
    )

    if return_first:
        return results.first()
    return results


def format_search_result(search_result):
    """convert a film object into a search result object"""
    cover = None
    if search_result.poster:
        cover = f"{MEDIA_FULL_URL}{search_result.poster}"

    return SearchResult(
        title=search_result.title,
        key=search_result.remote_id,
        director=search_result.director_text or None,
        year=str(search_result.year) if search_result.year else None,
        cover=cover,
        confidence=search_result.rank if hasattr(search_result, "rank") else 1,
    ).json()


@dataclass
class SearchResult:
    """standardized search result object"""

    title: str
    key: str
    view_link: Optional[str] = None
    director: Optional[str] = None
    year: Optional[str] = None
    cover: Optional[str] = None
    confidence: float = 1.0

    def __repr__(self):
        return (
            "<SearchResult key={!r} title={!r} director={!r} confidence={!r}>".format(
                self.key, self.title, self.director, self.confidence
            )
        )

    def json(self):
        """serialize a search result for a json response"""
        return asdict(self)
