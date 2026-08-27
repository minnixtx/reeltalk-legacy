from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator

from django.views import View
from django.views.decorators.http import require_POST

from reeltalk import activitystreams, models


@method_decorator(login_required, name="dispatch")
class BlockedFilms(View):
    """show film blocks page"""

    def get(self, request):
        """list of blocked films"""
        return TemplateResponse(request, "preferences/films.html")

    def post(self, request, film_id):
        """block a film"""
        film = get_object_or_404(models.Film, id=film_id)
        # first, add film to blocked_films
        request.user.blocked_films.add(film)
        # now remove from streams
        activitystreams.remove_blocked_film_statuses_task.delay(
            request.user.id, film.id
        )

        return redirect("prefs-block-films")


@login_required
@require_POST
def unblock_film(request, film_id):
    """unblock a film"""
    film = get_object_or_404(models.Film, id=film_id)
    # first, remove film from blocked_films
    request.user.blocked_films.remove(film)
    # now add to streams
    activitystreams.add_blocked_film_statuses_task.delay(request.user.id, film.id)

    return redirect("prefs-block-films")
