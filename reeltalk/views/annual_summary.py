"""end-of-year watched films stats"""

from datetime import date
from uuid import uuid4

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Sum, Min, Case, When
from django.http import Http404
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.views import View
from django.views.decorators.http import require_POST

from reeltalk import models
from .helpers import get_user_from_username


# December day of first availability
FIRST_DAY = 15
# January day of last availability, 0 for no availability in Jan.
LAST_DAY = 15


class AnnualSummary(View):
    """display a summary of the year for the current user"""

    def get(self, request, username, year):
        """get response"""

        user = get_user_from_username(request.user, username)

        year_key = None
        if user.summary_keys and year in user.summary_keys:
            year_key = user.summary_keys[year]

        privacy_verification(request, user, year, year_key)

        paginated_years = (
            int(year) - 1 if is_year_available(user, int(year) - 1) else None,
            int(year) + 1 if is_year_available(user, int(year) + 1) else None,
        )

        # get data
        watched_film_ids_in_year = (
            user.shelffilm_set.filter(
                shelf__identifier="read",
                shelved_date__year__gte=year,
                shelved_date__year__lt=int(year) + 1,
            )
            .order_by("shelved_date")
            .values_list("film_id", flat=True)
        )

        if len(watched_film_ids_in_year) == 0:
            data = {
                "summary_user": user,
                "year": year,
                "year_key": year_key,
                "films_total": 0,
                "films": [],
                "paginated_years": paginated_years,
            }
            return TemplateResponse(request, "annual_summary/layout.html", data)

        watched_films_in_year = get_films_from_shelffilms(
            watched_film_ids_in_year, request.user
        )

        # runtime stats queries (in minutes)
        runtime_stats = watched_films_in_year.aggregate(Sum("runtime"))
        total_runtime_minutes = runtime_stats["runtime__sum"] or 0

        # rating stats queries
        ratings = (
            models.Review.objects.filter(user=user)
            .exclude(deleted=True)
            .exclude(rating=None)
            .filter(film_id__in=watched_film_ids_in_year)
        )
        ratings_stats = ratings.aggregate(Avg("rating"))

        data = {
            "summary_user": user,
            "year": year,
            "year_key": year_key,
            "films_total": len(watched_films_in_year),
            "films": watched_films_in_year,
            "runtime_hours": round(total_runtime_minutes / 60, 1),
            "ratings_total": ratings.count(),
            "rating_average": round(
                ratings_stats["rating__avg"] if ratings_stats["rating__avg"] else 0, 2
            ),
            "film_rating_highest": ratings.order_by("-rating").first(),
            "best_ratings_films_ids": [
                review.film_id for review in ratings.filter(rating=5)
            ],
            "paginated_years": paginated_years,
        }

        return TemplateResponse(request, "annual_summary/layout.html", data)


@login_required
def personal_annual_summary(request, year):
    """redirect simple URL to URL with username"""

    return redirect("annual-summary", request.user.localname, year)


@login_required
@require_POST
def summary_add_key(request):
    """Create a shareable token for this annual review year"""

    year = request.POST["year"]
    user = request.user

    new_key = uuid4().hex

    if not user.summary_keys:
        user.summary_keys = {
            year: new_key,
        }
    else:
        user.summary_keys[year] = new_key

    user.save(update_fields=["summary_keys"], broadcast=False)

    response = redirect("annual-summary", user.localname, year)
    response["Location"] += f"?key={str(new_key)}"
    return response


@login_required
@require_POST
def summary_revoke_key(request):
    """No longer sharing the annual review"""

    year = request.POST["year"]
    user = request.user

    if user.summary_keys and year in user.summary_keys:
        user.summary_keys.pop(year)

    user.save(update_fields=["summary_keys"], broadcast=False)

    return redirect("annual-summary", user.localname, year)


def get_annual_summary_year():
    """return the latest available annual summary year or None"""

    today = date.today()
    if date(today.year, 12, FIRST_DAY) <= today <= date(today.year, 12, 31):
        return today.year

    if LAST_DAY > 0 and date(today.year, 1, 1) <= today <= date(
        today.year, 1, LAST_DAY
    ):
        return today.year - 1

    return None


def privacy_verification(request, user, year, year_key):
    """raises a 404 error if the user should not access the page"""
    if user != request.user:
        request_key = None
        if "key" in request.GET:
            request_key = request.GET["key"]

        if not request_key or request_key != year_key:
            raise Http404(f"The summary for {year} is unavailable")

    if not is_year_available(user, year):
        raise Http404(f"The summary for {year} is unavailable")


def is_year_available(user, year):
    """return boolean"""

    earliest_year = user.shelffilm_set.filter(shelf__identifier="read").aggregate(
        Min("shelved_date")
    )["shelved_date__min"]
    if not earliest_year:
        return True
    earliest_year = earliest_year.year
    today = date.today()
    year = int(year)
    if earliest_year <= year < today.year:
        return True
    if year == today.year and today >= date(today.year, 12, FIRST_DAY):
        return True

    return False


def get_films_from_shelffilms(films_ids, viewer):
    """return an ordered QuerySet of films from a list"""

    ordered = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(films_ids)])
    films = models.Film.objects.filter(id__in=films_ids).order_by(ordered)

    if hasattr(viewer, "blocked_films"):
        films = films.exclude(id__in=viewer.blocked_films.all())

    return films
