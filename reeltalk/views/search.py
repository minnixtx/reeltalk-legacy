"""search views"""

import re
from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import TrigramSimilarity
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.core.paginator import Page, Paginator
from django.db.models.functions import Greatest
from django.http import JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.vary import vary_on_headers

from csp.decorators import csp_update

from reeltalk import models, tmdb
from reeltalk.book_search import search, format_search_result
from reeltalk.settings import PAGE_LENGTH, INSTANCE_ACTOR_USERNAME
from reeltalk.utils import regex
from .helpers import is_api_request
from .helpers import handle_remote_webfinger


class Search(View):
    """search users or films"""

    @csp_update(IMG_SRC="*")
    @vary_on_headers("Accept")
    def get(self, request):
        """that search bar up top"""
        if is_api_request(request):
            if models.SiteSettings.get().block_incoming_search:
                raise PermissionDenied
            return api_film_search(request)

        query = request.GET.get("q")
        if not query:
            return TemplateResponse(request, "search/film.html")

        search_type = request.GET.get("type")
        if query and not search_type:
            search_type = "user" if "@" in query else "film"

        endpoints = {
            "film": film_search,
            "user": user_search,
            "list": list_search,
        }
        if search_type not in endpoints:
            search_type = "film"

        return endpoints[search_type](request)


def api_film_search(request):
    """Return films via API response"""
    query = request.GET.get("q").strip()
    min_confidence = float(request.GET.get("min_confidence", 0.1))
    film_results = search(query, min_confidence=min_confidence)
    return JsonResponse(
        [format_search_result(r) for r in film_results[:10]], safe=False
    )


def film_search(request):
    """search films: TMDB when configured, the local database otherwise"""
    query = request.GET.get("q").strip()
    if tmdb.is_configured():
        return tmdb_film_search(request, query)
    return local_film_search(request, query)


def local_film_search(request, query):
    """search the local film database"""
    min_confidence = float(request.GET.get("min_confidence", 0.1))

    # try a local-only search
    local_results = search(query, min_confidence=min_confidence)

    cleaned_results = local_results
    if request.user.is_authenticated:
        blocked = request.user.blocked_films.values_list("id", flat=True)
        cleaned_results = list(filter(lambda f: f.id not in blocked, local_results))

    blocked_films_excluded = (
        True if len(cleaned_results) < len(local_results) else False
    )

    paginated = Paginator(cleaned_results, PAGE_LENGTH)
    page = paginated.get_page(request.GET.get("page"))
    data = {
        "query": query,
        "blocked_films_excluded": blocked_films_excluded,
        "results": page,
        "type": "film",
        "page_range": paginated.get_elided_page_range(
            page.number, on_each_side=2, on_ends=1
        ),
    }
    return TemplateResponse(request, "search/film.html", data)


class TmdbPaginator(Paginator):
    """a paginator whose count and page count come from the TMDB API"""

    def __init__(self, rows, total_results, total_pages):
        super().__init__(rows, per_page=20)
        self._tmdb_total_results = total_results
        self._tmdb_total_pages = total_pages

    @property
    def count(self):
        return self._tmdb_total_results

    @property
    def num_pages(self):
        return self._tmdb_total_pages


def tmdb_film_search(request, query):
    """search the TMDB catalog and annotate hits with their local match"""
    viewer = request.user
    try:
        page_number = int(request.GET.get("page", 1))
    except (TypeError, ValueError):
        page_number = 1

    data = {"query": query, "type": "film", "source": "tmdb"}
    if request.GET.get("error"):
        data["error"] = request.GET.get("error")

    try:
        results = tmdb.search_films(query, page=page_number)
    except tmdb.TmdbError as err:
        data["error"] = str(err)
        return TemplateResponse(request, "search/film.html", data)

    total_pages = max(results.total_pages, 1)
    page_number = min(max(page_number, 1), total_pages)

    watchlist_shelf = None
    blocked_ids = set()
    if viewer.is_authenticated:
        blocked_ids = set(viewer.blocked_films.values_list("id", flat=True))
        if viewer.local:
            watchlist_shelf = models.Shelf.objects.filter(
                identifier=models.Shelf.TO_READ, user=viewer
            ).first()

    rows = []
    blocked_excluded = False
    for row in results.rows:
        local_film = tmdb.find_local_film(row)
        if local_film and local_film.id in blocked_ids:
            blocked_excluded = True
            continue
        on_watchlist = bool(
            watchlist_shelf
            and local_film
            and models.ShelfFilm.objects.filter(
                film=local_film, shelf=watchlist_shelf
            ).exists()
        )
        rows.append(
            {"result": row, "local_film": local_film, "on_watchlist": on_watchlist}
        )

    paginator = TmdbPaginator(rows, results.total_results, total_pages)
    page = Page(rows, page_number, paginator)
    data.update(
        {
            "results": page,
            "page_range": paginator.get_elided_page_range(
                page.number, on_each_side=2, on_ends=1
            ),
            "blocked_films_excluded": blocked_excluded,
        }
    )
    return TemplateResponse(request, "search/film.html", data)


def film_search_clickthrough(request, tmdb_id):
    """open the local page for a TMDB search hit, creating it if needed"""
    try:
        film = tmdb.ensure_local_film(tmdb_id)
    except tmdb.TmdbError as err:
        return TemplateResponse(
            request,
            "search/film.html",
            {"query": "", "type": "film", "source": "tmdb", "error": str(err)},
        )
    return redirect(film.local_path)


@method_decorator(login_required, name="dispatch")
class FilmWatchlistAdd(View):
    """one-click add of a TMDB search hit to the user's Watchlist"""

    def post(self, request, tmdb_id):
        user = request.user
        if not user.local:
            raise PermissionDenied()
        shelf = models.Shelf.objects.filter(
            identifier=models.Shelf.TO_READ, user=user
        ).first()
        return_to = request.POST.get("return_to") or "/"
        if not url_has_allowed_host_and_scheme(
            return_to, allowed_hosts={request.get_host()}
        ):
            return_to = "/"

        title = request.POST.get("title") or None
        year_raw = request.POST.get("year", "").strip()
        try:
            year = int(year_raw) if year_raw else None
        except ValueError:
            year = None

        try:
            film = tmdb.ensure_local_film(tmdb_id, title, year)
            if not models.ShelfFilm.objects.filter(film=film, shelf=shelf).exists():
                cache.delete(f"active_shelf-{user.id}-{film.id}")
                cache.delete(f"film-on-shelf-{film.id}-{shelf.id}")
                models.ShelfFilm.objects.create(film=film, shelf=shelf, user=user)
        except tmdb.TmdbError as err:
            separator = "&" if "?" in return_to else "?"
            return redirect(f"{return_to}{separator}error={quote(str(err))}")

        return redirect(return_to)


def user_search(request):
    """user search: search for a user"""
    viewer = request.user
    query = request.GET.get("q").strip()
    data = {"type": "user", "query": query}

    # use webfinger for mastodon style account@domain.com username to load the user if
    # they don't exist locally (handle_remote_webfinger will check the db)
    if re.match(regex.FULL_USERNAME, query) and viewer.is_authenticated:
        try:
            handle_remote_webfinger(query)
        except PermissionDenied:
            return TemplateResponse(request, "search/user.html", data)

    results = (
        models.User.viewer_aware_objects(viewer)
        .annotate(
            similarity=Greatest(
                TrigramSimilarity("username", query),
                TrigramSimilarity("localname", query),
            )
        )
        .filter(
            similarity__gt=0.5,
        )
        .exclude(localname=INSTANCE_ACTOR_USERNAME)
        .order_by("-similarity")
    )

    # don't expose remote users
    if not viewer.is_authenticated:
        results = results.filter(local=True)

    paginated = Paginator(results, PAGE_LENGTH)
    page = paginated.get_page(request.GET.get("page"))
    data["results"] = page
    data["page_range"] = paginated.get_elided_page_range(
        page.number, on_each_side=2, on_ends=1
    )
    return TemplateResponse(request, "search/user.html", data)


def list_search(request):
    """any relevent lists?"""
    query = request.GET.get("q").strip()
    data = {"query": query, "type": "list"}
    results = (
        models.List.privacy_filter(
            request.user,
            privacy_levels=["public", "followers"],
        )
        .annotate(
            similarity=Greatest(
                TrigramSimilarity("name", query),
                TrigramSimilarity("description", query),
            )
        )
        .filter(
            similarity__gt=0.1,
        )
        .order_by("-similarity")
    )
    paginated = Paginator(results, PAGE_LENGTH)
    page = paginated.get_page(request.GET.get("page"))
    data["results"] = page
    data["page_range"] = paginated.get_elided_page_range(
        page.number, on_each_side=2, on_ends=1
    )
    return TemplateResponse(request, "search/list.html", data)
