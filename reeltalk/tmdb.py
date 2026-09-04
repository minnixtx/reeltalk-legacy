"""client for the TMDB v3 API and the local-catalog logic built on it"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests
from django.conf import settings
from django.core.files.base import ContentFile

from reeltalk import models
from reeltalk.models.film import normalize_sort_title
from reeltalk.tasks import IMPORTS, app

logger = logging.getLogger(__name__)

API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
REQUEST_TIMEOUT = 10

# the canonical film-list CSV shape: TMDB's own export format, which ReelTalk's
# "Export Film List" emits and "Import Film List" accepts (decisions #29-31)
TMDB_EXPORT_HEADER = [
    "TMDb ID",
    "IMDb ID",
    "Type",
    "Name",
    "Release Date",
    "Season Number",
    "Episode Number",
    "Rating",
    "Your Rating",
    "Date Rated",
]


class TmdbError(Exception):
    """user-facing failure talking to TMDB (bad key, rate limit, etc.)"""


def is_configured() -> bool:
    """whether the instance has a TMDB API key set"""
    return bool(settings.TMDB_API_KEY)


@dataclass
class SearchResult:
    """one row from a TMDB movie search"""

    tmdb_id: str
    title: str
    year: Optional[int]
    poster_url: Optional[str]

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "SearchResult":
        year = None
        if data.get("release_date"):
            year = int(data["release_date"][:4])
        poster_path = data.get("poster_path")
        return cls(
            tmdb_id=str(data["id"]),
            title=data["title"],
            year=year,
            poster_url=f"{IMAGE_BASE}{poster_path}" if poster_path else None,
        )


@dataclass
class FilmSearch:
    """one page of TMDB movie search results"""

    rows: list[SearchResult]
    total_results: int
    total_pages: int


def _get(url: str, params: dict[str, Any]) -> dict[str, Any]:
    """GET a TMDB endpoint and return the parsed JSON payload"""
    try:
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as err:
        raise TmdbError("Could not reach TMDB; try again shortly") from err
    if resp.status_code == 401:
        raise TmdbError("The instance's TMDB API key is invalid")
    if resp.status_code == 429:
        raise TmdbError("TMDB rate limit reached; try again in a minute")
    if not resp.ok:
        raise TmdbError(f"TMDB request failed ({resp.status_code})")
    return resp.json()


def search_films(query: str, page: int = 1) -> FilmSearch:
    """search TMDB for films matching the query"""
    data = _get(
        f"{API_BASE}/search/movie",
        {
            "api_key": settings.TMDB_API_KEY,
            "query": query,
            "include_adult": "false",
            "page": page,
        },
    )
    return FilmSearch(
        rows=[SearchResult.from_api(row) for row in data.get("results", [])],
        total_results=data.get("total_results", 0),
        total_pages=data.get("total_pages", 0),
    )


def get_film_details(tmdb_id: str) -> dict[str, Any]:
    """fetch a film's full data including credits and images"""
    return _get(
        f"{API_BASE}/movie/{tmdb_id}",
        {
            "api_key": settings.TMDB_API_KEY,
            "append_to_response": "credits,images",
        },
    )


def download_poster(details: dict[str, Any]) -> Optional[bytes]:
    """download a film's poster from the TMDB image CDN"""
    path = details.get("poster_path")
    if not path:
        return None
    url = f"{IMAGE_BASE}{path}"
    try:
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as err:
        raise TmdbError("Could not download the film poster") from err
    if not resp.ok:
        raise TmdbError("Could not download the film poster")
    return resp.content


def film_fields_from_tmdb(details: dict[str, Any]) -> dict[str, Any]:
    """map a TMDB movie detail payload onto Film model fields"""
    crew = details.get("credits", {}).get("crew", [])
    cast = details.get("credits", {}).get("cast", [])
    year = None
    if details.get("release_date"):
        year = int(details["release_date"][:4])
    return {
        "title": details["title"],
        "year": year,
        "runtime": details.get("runtime") or None,
        "description": details.get("overview") or None,
        "genres": [g["name"] for g in details.get("genres", [])],
        "directors": [p["name"] for p in crew if p.get("job") == "Director"],
        # cap the cast list so we don't store every extra
        "cast": [p["name"] for p in cast[:10]],
    }


def find_local_film(row: SearchResult) -> Optional[models.Film]:
    """the local Film matching a TMDB search hit, if any"""
    existing = models.Film.find_existing({"tmdbId": row.tmdb_id})
    if existing:
        return existing
    if not row.year:
        return None
    sort_title = normalize_sort_title(row.title)
    return models.Film.objects.filter(sort_title=sort_title, year=row.year).first()


def ensure_local_film(
    tmdb_id: str,
    title: Optional[str] = None,
    year: Optional[int] = None,
) -> models.Film:
    """find or create the local Film for a TMDB film

    Matches on tmdb_id first, then falls back to normalized title + year
    (backfilling a manually created film), and creates a new film otherwise.
    """
    existing = models.Film.find_existing({"tmdbId": tmdb_id})
    if existing:
        add_poster(existing)
        return existing

    details = None
    if not (title and year):
        # without title + year the manual-film fallback is impossible, so pull
        # the TMDB data up front for matching/creation
        details = get_film_details(tmdb_id)
        title = title or details.get("title")
        if not year and details.get("release_date"):
            year = int(details["release_date"][:4])

    film = None
    if title and year:
        sort_title = normalize_sort_title(title)
        film = models.Film.objects.filter(sort_title=sort_title, year=year).first()
    if film is not None:
        # a manually created film matching title + year: backfill from TMDB
        if details is None:
            details = get_film_details(tmdb_id)
        backfill_film_from_tmdb(film, details)
        return film

    if details is None:
        details = get_film_details(tmdb_id)
    film = models.Film.objects.create(**film_fields_from_tmdb(details), tmdb_id=tmdb_id)
    add_poster(film, details)
    return film


def backfill_film_from_tmdb(film: models.Film, details: dict[str, Any]) -> None:
    """fill empty fields on a manually created film from TMDB data"""
    updated = False
    if not film.tmdb_id:
        film.tmdb_id = str(details["id"])
        updated = True
    for key, value in film_fields_from_tmdb(details).items():
        if key == "title" or not value:
            continue
        if not getattr(film, key):
            setattr(film, key, value)
            updated = True
    if updated:
        film.save()
    add_poster(film, details)


def add_poster(film: models.Film, details: Optional[dict[str, Any]] = None) -> None:
    """download the TMDB poster onto a film that doesn't have one yet"""
    if film.poster:
        return
    if details is None:
        details = get_film_details(film.tmdb_id)
    content = download_poster(details)
    if content:
        film.poster.save(
            f"tmdb-{film.tmdb_id or 'unknown'}.jpg", ContentFile(content), save=False
        )
        film.save()


# seconds to wait between TMDB detail fetches in the import backfill; keeps a
# large import well under TMDB's 50-requests-per-10-seconds rate limit
BACKFILL_REQUEST_INTERVAL = 0.25


@app.task(queue=IMPORTS)
def backfill_imported_films_task(film_ids):
    """fetch TMDB metadata + poster for films created by a file import

    The import itself makes no API calls (decision #30); this runs afterwards
    so imported films get their posters and details without any user action.
    Idempotent: films that already have a poster and description are skipped,
    and a failure on one film never stops the rest of the batch.
    """
    if not is_configured():
        return
    for film_id in film_ids:
        film = models.Film.objects.filter(id=film_id, tmdb_id__isnull=False).first()
        if film is None or not film.tmdb_id:
            continue
        if film.poster and film.description:
            continue
        try:
            details = get_film_details(film.tmdb_id)
            backfill_film_from_tmdb(film, details)
        except TmdbError:
            logger.warning("TMDB backfill failed for film %s", film.id)
            continue
        time.sleep(BACKFILL_REQUEST_INTERVAL)
