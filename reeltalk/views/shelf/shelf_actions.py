"""shelf views"""

from django.db import IntegrityError, transaction
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST

from reeltalk import models
from reeltalk.views.helpers import redirect_to_referer, get_mergeable_object_or_404


@login_required
@require_POST
@transaction.atomic
def shelve(request):
    """put a film on a user's shelf"""
    film = get_mergeable_object_or_404(models.Film, id=request.POST.get("film"))
    desired_shelf = get_object_or_404(
        request.user.shelf_set, identifier=request.POST.get("shelf")
    )

    # first we need to remove from the specified shelf
    change_from_current_identifier = request.POST.get("change-shelf-from")
    if change_from_current_identifier:
        # find the shelffilm obj and delete it
        get_object_or_404(
            models.ShelfFilm,
            film=film,
            user=request.user,
            shelf__identifier=change_from_current_identifier,
        ).delete()

    # A film can be on multiple shelves, but only on one read status shelf at a time
    if desired_shelf.identifier in models.Shelf.READ_STATUS_IDENTIFIERS:
        # figure out where state shelf it's currently on (if any)
        current_read_status_shelffilm = (
            models.ShelfFilm.objects.select_related("shelf")
            .filter(
                shelf__identifier__in=models.Shelf.READ_STATUS_IDENTIFIERS,
                user=request.user,
                film=film,
            )
            .first()
        )
        if current_read_status_shelffilm is not None:
            # If it is not already on the shelf
            if (
                current_read_status_shelffilm.shelf.identifier
                != desired_shelf.identifier
            ):
                current_read_status_shelffilm.delete()
            else:
                return redirect_to_referer(request)

        # create the new shelf-film entry
        models.ShelfFilm.objects.create(
            film=film, shelf=desired_shelf, user=request.user
        )
    else:
        # we're putting it on a custom shelf
        try:
            models.ShelfFilm.objects.create(
                film=film, shelf=desired_shelf, user=request.user
            )
        # The film is already on this shelf.
        # Might be good to alert, or reject the action?
        except IntegrityError:
            pass

    return redirect_to_referer(request)


@login_required
@require_POST
def unshelve(request, film_id=False):
    """remove a film from a user's shelf"""
    identity = film_id if film_id else request.POST.get("film")
    film = get_mergeable_object_or_404(models.Film, id=identity)
    shelf_film = get_object_or_404(
        models.ShelfFilm, film=film, shelf__id=request.POST["shelf"]
    )
    shelf_film.raise_not_deletable(request.user)
    shelf_film.delete()
    return redirect_to_referer(request)
