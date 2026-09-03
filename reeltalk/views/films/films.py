"""the good stuff! the films!"""

from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Avg, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views import View
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_headers

from reeltalk import forms, models
from reeltalk.activitypub import ActivitypubResponse
from reeltalk.settings import PAGE_LENGTH
from reeltalk.utils.images import remove_uploaded_image_exif, set_cover_from_url
from reeltalk.views.helpers import (
    is_api_request,
    maybe_redirect_local_path,
    get_mergeable_object_or_404,
)


class Film(View):
    """a film! this is the stuff"""

    @vary_on_headers("Accept")
    def get(self, request, film_id, **kwargs):
        """info about a film"""
        if is_api_request(request):
            film = get_object_or_404(models.Film, id=film_id)
            return ActivitypubResponse(film.to_activity())

        user_statuses = (
            kwargs.get("user_statuses", False)
            if request.user.is_authenticated
            else False
        )

        film = get_mergeable_object_or_404(models.Film, id=film_id)
        if not film:
            raise Http404()

        if redirect_local_path := not user_statuses and maybe_redirect_local_path(
            request, film
        ):
            return redirect_local_path

        # all reviews for this film
        reviews = models.Review.privacy_filter(request.user).filter(film=film)

        # the reviews to show
        if user_statuses:
            if user_statuses == "review":
                queryset = film.review_set.select_subclasses()
            else:
                queryset = film.comment_set
            queryset = queryset.filter(user=request.user, deleted=False)
        else:
            queryset = reviews.exclude(Q(content__isnull=True) | Q(content=""))
        queryset = queryset.select_related("user").order_by("-published_date")
        paginated = Paginator(queryset, PAGE_LENGTH)

        lists = models.List.privacy_filter(request.user).filter(
            listitem__approved=True,
            listitem__film=film,
        )
        data = {
            "film": film,
            "statuses": paginated.get_page(request.GET.get("page")),
            "review_count": reviews.count(),
            "ratings": (
                reviews.filter(Q(content__isnull=True) | Q(content="")).select_related(
                    "user"
                )
                if not user_statuses
                else None
            ),
            "rating": reviews.aggregate(Avg("rating"))["rating__avg"],
            "lists": lists,
        }

        if request.user.is_authenticated:
            data["list_options"] = request.user.list_set.exclude(id__in=data["lists"])
            data["list_form"] = forms.ListForm()

            data["user_shelffilms"] = models.ShelfFilm.objects.filter(
                user=request.user, film=film
            ).select_related("shelf")

            filters = {"user": request.user, "deleted": False}
            data["user_statuses"] = {
                "review_count": film.review_set.filter(**filters).count(),
                "comment_count": film.comment_set.filter(**filters).count(),
            }

        return TemplateResponse(request, "film/film.html", data)


@login_required
@require_POST
def upload_poster(request, film_id):
    """upload a new poster"""
    film = get_mergeable_object_or_404(models.Film, id=film_id)
    if film.tmdb_id:
        # TMDB is the source of truth for this film's details
        return redirect(film.local_path)
    film.last_edited_by = request.user

    url = request.POST.get("poster-url")
    if url:
        image = set_cover_from_url(url)
        if image:
            film.poster.save(*image)

        return redirect(f"{film.local_path}?poster_error=True")

    form = forms.CoverForm(request.POST, request.FILES, instance=film)
    if not form.is_valid() or not form.files.get("poster"):
        return redirect(film.local_path)

    film.poster = remove_uploaded_image_exif(form.files["poster"])
    film.save()

    return redirect(film.local_path)


@login_required
@require_POST
@permission_required("reeltalk.edit_film", raise_exception=True)
def add_description(request, film_id):
    """add a description to a film"""
    film = get_mergeable_object_or_404(models.Film, id=film_id)
    if film.tmdb_id:
        # TMDB is the source of truth for this film's details
        return redirect("film", film.id)

    description = request.POST.get("description")

    film.description = description
    film.last_edited_by = request.user
    film.save(update_fields=["description", "last_edited_by"])

    return redirect("film", film.id)
