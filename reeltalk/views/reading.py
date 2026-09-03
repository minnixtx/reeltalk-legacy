"""watch status for films"""

import logging
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from reeltalk import models
from reeltalk.views.helpers import handle_reading_status, is_api_request
from reeltalk.views.helpers import redirect_to_referer
from reeltalk.views.shelf.shelf_actions import unshelve
from .status import CreateStatus

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class ReadingStatus(View):
    """consider watching a film"""

    def get(self, request, status, film_id):
        """modal page"""
        film = get_object_or_404(models.Film, id=film_id)
        template = {
            "want": "want.html",
            "finish": "finish.html",
        }.get(status)
        if not template:
            return HttpResponseNotFound()
        # redirect if we're already on this shelf
        return TemplateResponse(request, f"reading_progress/{template}", {"film": film})

    @transaction.atomic
    def post(self, request, status, film_id):
        """Change the state of a film by shelving it"""
        # the film model has no watching state: only "want" and "finish"
        identifier = {
            "want": models.Shelf.TO_READ,
            "finish": models.Shelf.READ_FINISHED,
        }.get(status)
        if not identifier:
            logger.exception("Invalid reading status type: %s", status)
            return HttpResponseBadRequest()

        desired_shelf = get_object_or_404(
            models.Shelf, identifier=identifier, user=request.user
        )

        film = get_object_or_404(models.Film, id=film_id)

        # marking a film as watched requires a star rating (0.5-5)
        if status == "finish":
            rating = request.POST.get("rating")
            try:
                rating_value = float(rating)
            except (TypeError, ValueError):
                rating_value = None
            if rating_value is None or not 0.5 <= rating_value <= 5:
                if is_api_request(request):
                    return HttpResponseBadRequest()
                return TemplateResponse(
                    request,
                    "reading_progress/finish.html",
                    {"film": film, "error": True},
                )

        # invalidate related caches
        cache.delete(f"active_shelf-{request.user.id}-{film_id}")

        # gets the first shelf that indicates a reading status, or None
        # film.shelffilm_set spans all users: an unscoped lookup would delete
        # another user's read-status entry for the same film
        shelves = [
            s
            for s in film.shelffilm_set.select_related("shelf")
            if s.user_id == request.user.id
            and s.shelf.identifier in models.Shelf.READ_STATUS_IDENTIFIERS
        ]
        current_status_shelffilm = shelves[0] if shelves else None

        # checking the referer prevents redirecting back to the modal page
        if current_status_shelffilm is not None:
            if current_status_shelffilm.shelf.identifier != desired_shelf.identifier:
                current_status_shelffilm.delete()
            else:  # It already was on the shelf
                return redirect_to_referer(request)

        models.ShelfFilm.objects.create(
            film=film, shelf=desired_shelf, user=request.user
        )

        # marking a film as watched posts the review (rating is required,
        # written review optional); adding to want-to-watch posts optionally
        if status == "finish":
            # one review per film: an existing review is updated instead of
            # creating a second entry
            existing_review = film.review_set.filter(
                user=request.user, deleted=False
            ).first()
            if existing_review:
                if not request.POST.get("content"):
                    # an empty modal text keeps the review's current content
                    post = request.POST.copy()
                    post["content"] = (
                        existing_review.raw_content or existing_review.content or ""
                    )
                    request.POST = post
                return CreateStatus.as_view()(request, "review", existing_review.id)
            status_type = "review" if request.POST.get("content") else "rating"
            return CreateStatus.as_view()(request, status_type)

        if request.POST.get("post-status"):
            # is it a comment?
            if request.POST.get("content"):
                return CreateStatus.as_view()(request, "comment")
            privacy = request.POST.get("privacy")
            handle_reading_status(request.user, desired_shelf, film, privacy)

        # if the request includes a "shelf" value we are using the 'move' button
        if bool(request.POST.get("shelf")):
            # unshelve the existing shelf
            this_shelf = request.POST.get("shelf")
            if (
                bool(current_status_shelffilm)
                and int(this_shelf) != int(current_status_shelffilm.shelf.id)
                and current_status_shelffilm.shelf.identifier
                != desired_shelf.identifier
            ):
                return unshelve(request, film_id=film_id)

        if is_api_request(request):
            return HttpResponse()

        return redirect_to_referer(request)
