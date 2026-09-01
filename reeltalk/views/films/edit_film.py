"""edit and create films"""

from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from reeltalk import book_search, forms, models
from reeltalk.utils.images import remove_uploaded_image_exif, set_cover_from_url
from reeltalk.views.helpers import get_mergeable_object_or_404


def apply_poster(request, film):
    """save a poster from a url or an uploaded file, if provided"""
    url = request.POST.get("poster-url")
    if url:
        image = set_cover_from_url(url)
        if image:
            film.poster.save(*image, save=False)
    elif "poster" in request.FILES:
        film.poster = remove_uploaded_image_exif(request.FILES["poster"])


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("reeltalk.edit_film", raise_exception=True), name="dispatch"
)
class EditFilm(View):
    """edit a film"""

    def get(self, request, film_id):
        """info about a film"""
        film = get_mergeable_object_or_404(models.Film, id=film_id)
        if film.tmdb_id:
            # TMDB is the source of truth for this film's details
            return redirect(film.local_path)
        data = {
            "film": film,
            "form": forms.FilmForm(instance=film),
        }
        return TemplateResponse(request, "film/edit/film.html", data)

    def post(self, request, film_id):
        """edit a film"""
        film = get_mergeable_object_or_404(models.Film, id=film_id)
        if film.tmdb_id:
            # TMDB is the source of truth for this film's details
            return redirect(film.local_path)

        form = forms.FilmForm(request.POST, request.FILES, instance=film)
        if not form.is_valid():
            data = {"film": film, "form": form}
            return TemplateResponse(request, "film/edit/film.html", data)

        film = form.save(request, commit=False)
        apply_poster(request, film)
        film.last_edited_by = request.user
        film.save()
        return redirect(film.local_path)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("reeltalk.edit_film", raise_exception=True), name="dispatch"
)
class CreateFilm(View):
    """brand new film"""

    def get(self, request):
        """info about a film"""
        data = {"form": forms.FilmForm()}
        return TemplateResponse(request, "film/edit/film.html", data)

    def post(self, request):
        """create a new film"""
        form = forms.FilmForm(request.POST, request.FILES)
        if not form.is_valid():
            data = {"form": form}
            return TemplateResponse(request, "film/edit/film.html", data)

        # check for existing films with the same title before creating
        matches = book_search.search(
            form.cleaned_data.get("title"),
            min_confidence=0.1,
        )[:5]

        if matches:
            data = {"form": form, "film_matches": matches, "confirm_mode": True}
            return TemplateResponse(request, "film/edit/film.html", data)

        film = form.save(request)
        apply_poster(request, film)
        film.last_edited_by = request.user
        film.save()
        return redirect(film.local_path)


@method_decorator(login_required, name="dispatch")
@method_decorator(
    permission_required("reeltalk.edit_film", raise_exception=True), name="dispatch"
)
class ConfirmEditFilm(View):
    """confirm creating a film that matches an existing one"""

    def post(self, request):
        form = forms.FilmForm(request.POST, request.FILES)
        if not form.is_valid():
            return HttpResponseBadRequest()

        match_id = request.POST.get("film_match")
        if match_id and match_id != "0":
            # merge the new data into the existing film
            canonical = get_object_or_404(models.Film, id=match_id)
            duplicate = form.save(request, commit=False)
            canonical.absorb_data_from(duplicate)
            apply_poster(request, canonical)
            canonical.last_edited_by = request.user
            canonical.save()
            return redirect(canonical.local_path)

        # no match selected, create the new film
        film = form.save(request)
        apply_poster(request, film)
        film.last_edited_by = request.user
        film.save()
        return redirect(film.local_path)
