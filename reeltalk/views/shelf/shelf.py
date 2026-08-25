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
            books = shelf.books
        else:
            # this is a constructed "all books" view, with a fake "shelf" obj
            FakeShelf = namedtuple(
                "Shelf", ("identifier", "name", "user", "books", "privacy")
            )

            books = (
                models.Edition.viewer_aware_objects(request.user)
                .filter(
                    # privacy is ensured because the shelves are already filtered above
                    shelfbook__shelf__in=shelves
                )
                .distinct()
            )

            shelf = FakeShelf("all", _("All films"), user, books, "public")

        if is_api_request(request) and shelf_identifier:
            return ActivitypubResponse(shelf.to_activity(**request.GET))

        reviews = models.Review.objects
        if not is_self:
            reviews = models.Review.privacy_filter(request.user)

        reviews = reviews.filter(
            user=user,
            rating__isnull=False,
            book__id=OuterRef("id"),
            deleted=False,
        ).order_by("-published_date")

        reading = models.ReadThrough.objects

        reading = reading.filter(user=user, book__id=OuterRef("id")).order_by(
            "start_date"
        )

        # don't annotate on every possible sort field
        sort = request.GET.get("sort") or "-shelved_date"
        if re.match(r"^-?rating$", sort):
            books = books.annotate(rating=Subquery(reviews.values("rating")[:1]))
        elif re.match(r"^-?start_date$", sort):
            books = books.annotate(
                start_date=Subquery(reading.values("start_date")[:1])
            )
        elif re.match(r"^-?finish_date$", sort):
            books = books.annotate(
                finish_date=Subquery(reading.values("finish_date")[:1])
            )
        elif re.match(r"^-?author$", sort):
            books = books.annotate(
                author=models.Book.objects.filter(id=OuterRef("id")).values(
                    "authors__name"
                )[:1]
            )
        elif not re.match(r"^-?sort_title$", sort):
            books = books.annotate(shelved_date=Max("shelfbook__shelved_date"))

        books = books.prefetch_related("authors")

        books = sort_books(books, sort)

        if shelves_filter_query:
            books = search(shelves_filter_query, books=books)

        paginated = Paginator(
            books,
            PAGE_LENGTH,
        )
        page = paginated.get_page(request.GET.get("page"))
        data = {
            "user": user,
            "is_self": is_self,
            "shelves": shelves,
            "shelf_tabs": shelves.filter(identifier__in=["to-read", "read"]),
            "shelf": shelf,
            "books": page,
            "sort": sort,
            "page_range": paginated.get_elided_page_range(
                page.number, on_each_side=2, on_ends=1
            ),
            "shelves_filter_query": shelves_filter_query,
            "size": "small",
        }

        return TemplateResponse(request, "shelf/shelf.html", data)


def sort_books(books, sort):
    """Books in shelf sorting"""
    sort_fields = [
        "sort_title",
        "author",
        "shelved_date",
        "start_date",
        "finish_date",
        "rating",
    ]

    if sort in sort_fields:
        books = books.order_by(sort)
    elif sort and sort[1:] in sort_fields:
        books = books.order_by(F(sort[1:]).desc(nulls_last=True))
    else:
        books = books.order_by("-shelved_date")
    return books
