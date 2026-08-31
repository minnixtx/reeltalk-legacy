"""minimal client for the TMDB v3 API, used by the film importer"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests
from django.conf import settings

API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
REQUEST_TIMEOUT = 10


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


def search_films(query: str) -> list[SearchResult]:
    """search TMDB for films matching the query"""
    data = _get(
        f"{API_BASE}/search/movie",
        {"api_key": settings.TMDB_API_KEY, "query": query, "include_adult": "false"},
    )
    return [SearchResult.from_api(row) for row in data.get("results", [])]


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
