"""search views"""

import re

from django.contrib.postgres.search import TrigramSimilarity
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models.functions import Greatest
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.views import View
from django.views.decorators.vary import vary_on_headers

from csp.decorators import csp_update

from reeltalk import models
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
    """search the local film database"""
    query = request.GET.get("q").strip()
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
