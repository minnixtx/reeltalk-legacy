"""Helping new users figure out the lay of the land"""

import re

from django.contrib.auth.decorators import login_required
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.functions import Greatest
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from reeltalk import book_search, forms, models
from reeltalk.settings import INSTANCE_ACTOR_USERNAME
from reeltalk.suggested_users import suggested_users
from reeltalk.views.helpers import get_mergeable_object_or_404
from .preferences.edit_user import save_user_form


@method_decorator(login_required, name="dispatch")
class GetStartedProfile(View):
    """tell us about yourself"""

    next_view = "get-started-films"

    def get(self, request):
        """basic profile info"""
        data = {
            "form": forms.LimitedEditUserForm(instance=request.user),
            "next": self.next_view,
        }
        return TemplateResponse(request, "get_started/profile.html", data)

    def post(self, request):
        """update your profile"""
        form = forms.LimitedEditUserForm(
            request.POST, request.FILES, instance=request.user
        )
        if not form.is_valid():
            data = {"form": form, "next": "get-started-films"}
            return TemplateResponse(request, "get_started/profile.html", data)
        save_user_form(request, form)
        return redirect(self.next_view)


@method_decorator(login_required, name="dispatch")
class GetStartedFilms(View):
    """name a film, any film, we gotta start somewhere"""

    next_view = "get-started-users"

    def get(self, request):
        """info about a film"""
        query = request.GET.get("query")
        film_results = popular_films = []
        if query:
            film_results = book_search.search(query)[:5]
        if len(film_results) < 5:
            popular_films = (
                models.Film.objects.exclude(
                    Q(  # exclude if it's already in search results
                        id__in=[f.id for f in film_results]
                    )
                )
                .annotate(Count("shelffilm"))
                .order_by("-shelffilm__count")[: 5 - len(film_results)]
            )

        data = {
            "film_results": film_results,
            "popular_films": popular_films,
            "next": self.next_view,
        }
        return TemplateResponse(request, "get_started/films.html", data)

    def post(self, request):
        """shelve some films"""
        shelve_actions = [
            (k, v)
            for k, v in request.POST.items()
            if re.match(r"\d+", k) and re.match(r"\d+", v)
        ]
        for film_id, shelf_id in shelve_actions:
            film = get_mergeable_object_or_404(models.Film, id=film_id)
            shelf = get_object_or_404(models.Shelf, id=shelf_id)

            models.ShelfFilm.objects.create(film=film, shelf=shelf, user=request.user)
        return redirect(self.next_view)


@method_decorator(login_required, name="dispatch")
class GetStartedUsers(View):
    """find friends"""

    def get(self, request):
        """basic profile info"""
        query = request.GET.get("query")
        user_results = (
            models.User.viewer_aware_objects(request.user)
            .annotate(
                similarity=Greatest(
                    TrigramSimilarity("username", query),
                    TrigramSimilarity("localname", query),
                )
            )
            .filter(
                similarity__gt=0.5,
            )
            .exclude(
                id=request.user.id,
            )
            .exclude(localname=INSTANCE_ACTOR_USERNAME)
            .order_by("-similarity")[:5]
        )
        data = {"no_results": not user_results}

        if user_results.count() < 5:
            user_results = list(user_results) + list(
                suggested_users.get_suggestions(request.user)
            )

        data["suggested_users"] = user_results
        return TemplateResponse(request, "get_started/users.html", data)
