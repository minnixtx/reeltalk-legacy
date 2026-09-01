"""import films from TMDB: search, create-or-match, add to a list or shelf"""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from reeltalk import models, tmdb
from reeltalk.views.list.list import set_list_item_order


def get_target_choices(user):
    """(value, label) pairs for the destination dropdown"""
    choices = []
    if user.local:
        shelf = models.Shelf.objects.filter(
            identifier=models.Shelf.TO_READ, user=user
        ).first()
        if shelf:
            choices.append(("shelf:to-read", shelf.name))
    lists = (
        models.List.objects.filter(
            Q(user=user) | Q(curation="group", group__memberships__user=user)
        )
        .distinct()
        .order_by("name")
    )
    for film_list in lists:
        choices.append((f"list:{film_list.id}", film_list.name))
    return choices


def resolve_target(user, target):
    """validate a "shelf:<identifier>" or "list:<id>" target; returns (kind, obj)"""
    kind, _, value = target.partition(":")
    if kind == "shelf":
        return "shelf", get_object_or_404(
            models.Shelf, identifier=value, user=user
        )
    if kind == "list":
        film_list = get_object_or_404(models.List, id=value)
        film_list.raise_not_submittable(user)
        return "list", film_list
    raise Http404()


def add_to_target(user, film, kind, target):
    """add a film to the resolved target; returns (ok, message)"""
    if kind == "shelf":
        shelf = target
        if film.shelffilm_set.filter(shelf=shelf).exists():
            return False, f"“{film.title}” is already on {shelf.name}."
        cache.delete(f"active_shelf-{user.id}-{film.id}")
        models.ShelfFilm.objects.create(film=film, shelf=shelf, user=user)
        return True, f"Added “{film.title}” to {shelf.name}."

    film_list = target
    if film_list.listitem_set.filter(film=film).exists():
        return False, f"“{film.title}” is already on {film_list.name}."
    item = models.ListItem(user=user, film=film, film_list=film_list)
    set_list_item_order(item)
    item.save()
    if not item.approved:
        return True, f"You suggested “{film.title}” for {film_list.name}."
    return True, f"Added “{film.title}” to {film_list.name}."


@method_decorator(login_required, name="dispatch")
class ImportFilms(View):
    """TMDB film import page"""

    template_name = "import/films.html"

    def get(self, request):
        return self.render(request)

    def post(self, request):
        if request.POST.get("action") == "add":
            return self.handle_add(request)
        return self.handle_search(request)

    def render(self, request, **context):
        choices = get_target_choices(request.user)
        target = (
            context.pop("target", None)
            or request.POST.get("target")
            or request.GET.get("target")
        )
        if not any(value == target for value, _ in choices):
            target = choices[0][0] if choices else ""
        context["target_choices"] = choices
        context["target"] = target
        context["target_label"] = dict(choices).get(target, "")
        context.setdefault("configured", tmdb.is_configured())
        context.setdefault("query", "")
        context.setdefault("rows", [])
        return TemplateResponse(request, self.template_name, context)

    def handle_search(self, request):
        query = request.POST.get("query", "").strip()
        if not tmdb.is_configured():
            return self.render(
                request, error="TMDB import isn't configured on this instance."
            )
        if not query:
            return self.render(
                request, error="Please enter a film title to search for."
            )
        try:
            results = tmdb.search_films(query)
        except tmdb.TmdbError as err:
            return self.render(request, query=query, error=str(err))
        rows = [
            {"result": row, "local_film": tmdb.find_local_film(row)}
            for row in results.rows
        ]
        return self.render(request, query=query, rows=rows)

    def handle_add(self, request):
        query = request.POST.get("query", "").strip()
        tmdb_id = request.POST.get("tmdb_id", "").strip()
        title = request.POST.get("title", "").strip()
        year_raw = request.POST.get("year", "").strip()
        try:
            year = int(year_raw) if year_raw else None
        except ValueError:
            year = None

        if not tmdb.is_configured():
            return self.render(
                request, error="TMDB import isn't configured on this instance."
            )
        if not tmdb_id or not title:
            return self.render(request, query=query, error="Please choose a film to add.")

        try:
            kind, target_obj = resolve_target(
                request.user, request.POST.get("target", "")
            )
        except Http404:
            return self.render(
                request, query=query, error="Please choose a destination for the film."
            )

        try:
            film = tmdb.ensure_local_film(tmdb_id, title, year)
            ok, message = add_to_target(request.user, film, kind, target_obj)
        except tmdb.TmdbError as err:
            return self.render(request, query=query, error=str(err))

        # re-run the search so the results grid stays visible after adding
        rows = []
        if ok and query:
            try:
                results = tmdb.search_films(query)
                rows = [
                    {"result": row, "local_film": tmdb.find_local_film(row)}
                    for row in results.rows
                ]
            except tmdb.TmdbError:
                pass

        return self.render(
            request,
            query=query,
            rows=rows,
            added_tmdb_id=film.tmdb_id if ok else None,
            success=message if ok else None,
            error=None if ok else message,
        )
