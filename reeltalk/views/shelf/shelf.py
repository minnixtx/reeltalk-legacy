"""shelf views"""

from collections import namedtuple
import re

from django.db.models import OuterRef, Subquery, F, Max
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.decorators.vary import vary_on_headers

from reeltalk import models
from reeltalk.activitypub import ActivitypubResponse
from reeltalk.settings import PAGE_LENGTH
from reeltalk.views.helpers import is_api_request
from reeltalk.book_search import search
from reeltalk.views.mixins import PrivateProfileMixin


class Shelf(PrivateProfileMixin, View):
    """shelf page"""

    @vary_on_headers("Accept")
    def get(self, request, username, shelf_identifier=None):
        """display a shelf"""
        user = request.profile_user

        is_self = user == request.user

        if is_self:
            shelves = user.shelf_set.all()
        else:
            shelves = models.Shelf.privacy_filter(request.user).filter(user=user).all()

        shelves_filter_query = request.GET.get("filter")

        # get the shelf and make sure the logged in user should be able to see it
        if shelf_identifier:
            shelf = get_object_or_404(user.shelf_set, identifier=shelf_identifier)
            shelf.raise_visible_to_user(request.user)
            films = shelf.films
        else:
            # this is a constructed "all films" view, with a fake "shelf" obj
            FakeShelf = namedtuple(
                "Shelf", ("identifier", "name", "user", "films", "privacy")
            )

            films = (
                models.Film.viewer_aware_objects(request.user)
                .filter(
                    # privacy is ensured because the shelves are already filtered above
                    shelffilm__shelf__in=shelves
                )
                .distinct()
            )

            shelf = FakeShelf("all", _("All films"), user, films, "public")

        if is_api_request(request) and shelf_identifier:
            return ActivitypubResponse(shelf.to_activity(**request.GET))

        reviews = models.Review.objects
        if not is_self:
            reviews = models.Review.privacy_filter(request.user)

        reviews = reviews.filter(
            user=user,
            rating__isnull=False,
            film__id=OuterRef("id"),
            deleted=False,
        ).order_by("-published_date")

        # don't annotate on every possible sort field
        sort = request.GET.get("sort") or "-shelved_date"
        if re.match(r"^-?rating$", sort):
            films = films.annotate(rating=Subquery(reviews.values("rating")[:1]))
        elif re.match(r"^-?director$", sort):
            films = films.annotate(
                director=models.Film.objects.filter(id=OuterRef("id")).values(
                    "directors"
                )[:1]
            )
        elif not re.match(r"^-?sort_title$", sort):
            films = films.annotate(shelved_date=Max("shelffilm__shelved_date"))

        films = sort_films(films, sort)

        if shelves_filter_query:
            films = search(shelves_filter_query, films=films)

        paginated = Paginator(
            films,
            PAGE_LENGTH,
        )
        page = paginated.get_page(request.GET.get("page"))
        data = {
            "user": user,
            "is_self": is_self,
            "shelves": shelves,
            "shelf_tabs": shelves.filter(identifier__in=["to-read", "read"]),
            "shelf": shelf,
            "films": page,
            "sort": sort,
            "page_range": paginated.get_elided_page_range(
                page.number, on_each_side=2, on_ends=1
            ),
            "shelves_filter_query": shelves_filter_query,
            "size": "small",
        }

        return TemplateResponse(request, "shelf/shelf.html", data)


def sort_films(films, sort):
    """Films in shelf sorting"""
    sort_fields = [
        "sort_title",
        "director",
        "shelved_date",
        "rating",
    ]

    if sort in sort_fields:
        films = films.order_by(sort)
    elif sort and sort[1:] in sort_fields:
        films = films.order_by(F(sort[1:]).desc(nulls_last=True))
    else:
        films = films.order_by("-shelved_date")
    return films
