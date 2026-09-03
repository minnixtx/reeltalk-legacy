"""file-based film import from a TMDB-style CSV export"""

import csv
import io
import logging

from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.db import transaction
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from reeltalk import models, tmdb
from reeltalk.models.film import normalize_sort_title

logger = logging.getLogger(__name__)

# columns a file must carry to be recognized as a TMDB export; the full
# canonical header (what ReelTalk's own export emits) is ten columns wide,
# but only these are load-bearing for the import
REQUIRED_COLUMNS = ["TMDb ID", "Name", "Release Date"]

# the import runs in one transaction and renders every row into the results
# table, so bound the file size well past any realistic watchlist
MAX_IMPORT_ROWS = 20_000


def parse_release_year(release_date):
    """a TMDB release date ("1976-05-20T00:00:00Z") down to its year"""
    if not release_date or len(release_date) < 4:
        return None
    try:
        return int(release_date[:4])
    except ValueError:
        return None


def parse_tmdb_rating(raw):
    """a TMDB "Your Rating" (1-10 scale) onto our 0.5-5 star scale"""
    if raw is None or not str(raw).strip():
        return None
    try:
        value = float(str(raw).strip())
    except ValueError:
        return None
    if not 1 <= value <= 10:
        return None
    return min(max(round(value) / 2, 0.5), 5)


def find_or_create_film(row):
    """the local Film for a CSV row, created from the row's data only

    No TMDB API calls: matching is by TMDB/IMDb ID first, then normalized
    title + year (decision #23). Returns (film, was_created).
    """
    name = (row.get("Name") or "").strip()
    tmdb_id = (row.get("TMDb ID") or "").strip()
    imdb_id = (row.get("IMDb ID") or "").strip()
    year = parse_release_year(row.get("Release Date"))

    film = None
    lookup = {}
    if tmdb_id:
        lookup["tmdbId"] = tmdb_id
    if imdb_id:
        lookup["imdbId"] = imdb_id
    if lookup:
        film = models.Film.find_existing(lookup)
    if film is None and year is not None:
        film = models.Film.objects.filter(
            sort_title=normalize_sort_title(name), year=year
        ).first()

    if film is None:
        film = models.Film.objects.create(
            title=name,
            year=year,
            tmdb_id=tmdb_id or None,
            imdb_id=imdb_id or None,
        )
        return film, True

    # matched an existing film: backfill empty identifier fields from the row
    updated = False
    if tmdb_id and not film.tmdb_id:
        film.tmdb_id = tmdb_id
        updated = True
    if imdb_id and not film.imdb_id:
        film.imdb_id = imdb_id
        updated = True
    if year is not None and not film.year:
        film.year = year
        updated = True
    if updated:
        film.save()
    return film, False


def shelve_film(user, shelf, film):
    """put a film on a shelf, invalidating the same caches the web shelve does"""
    cache.delete(f"active_shelf-{user.id}-{film.id}")
    cache.delete(f"film-on-shelf-{film.id}-{shelf.id}")
    models.ShelfFilm.objects.create(film=film, shelf=shelf, user=user)


def import_row(user, watchlist_shelf, watched_shelf, row):
    """process one CSV row; returns (status, note, film) for the results table"""
    name = (row.get("Name") or "").strip()
    film_type = (row.get("Type") or "movie").strip().lower()

    if film_type and film_type != "movie":
        return "skipped", f"not a movie ({film_type})", None
    if not name:
        return "skipped", "missing name", None

    rating = parse_tmdb_rating(row.get("Your Rating"))
    film, created = find_or_create_film(row)
    status = "created" if created else "matched"

    if rating is None:
        if models.ShelfFilm.objects.filter(
            film=film, shelf=watchlist_shelf
        ).exists():
            return status, "already on your Watchlist", film
        shelve_film(user, watchlist_shelf, film)
        return status, "added to Watchlist", film

    # a rated row lands on Watched with a rating-only entry (decision #19);
    # one review per film (decision #27): an existing review is never touched
    if models.Review.objects.filter(
        user=user, film=film, deleted=False
    ).exists():
        return status, "you already have a review; rating not imported", film
    shelve_film(user, watched_shelf, film)
    entry = models.ReviewRating(user=user, film=film, rating=rating)
    # a bulk import is data migration, not sharing: don't federate the entries
    entry.save(broadcast=False)
    return status, f"Watched — {rating:g} stars", film


@method_decorator(login_required, name="dispatch")
class ImportFilms(View):
    """import films from a TMDB-style CSV export"""

    def get(self, request):
        """upload page"""
        return TemplateResponse(request, "preferences/import_films.html")

    @transaction.atomic
    def post(self, request):
        """parse the upload and import every row"""
        user = request.user
        if not user.local:
            data = {
                "error": "Film import is only available on your home instance."
            }
            return TemplateResponse(request, "preferences/import_films.html", data)

        upload = request.FILES.get("csv_file")
        if not upload:
            data = {"error": "Choose a CSV file to import."}
            return TemplateResponse(request, "preferences/import_films.html", data)

        try:
            text = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            data = {"error": "That file isn't readable UTF-8; expected a CSV export."}
            return TemplateResponse(request, "preferences/import_films.html", data)

        reader = csv.DictReader(io.StringIO(text))
        header = reader.fieldnames or []
        missing = [column for column in REQUIRED_COLUMNS if column not in header]
        if missing:
            data = {
                "error": (
                    "Not a recognized TMDB export — missing column(s): "
                    + ", ".join(missing)
                )
            }
            return TemplateResponse(request, "preferences/import_films.html", data)

        rows = list(reader)
        if len(rows) > MAX_IMPORT_ROWS:
            data = {
                "error": (
                    f"That file has {len(rows):,} rows; the import is limited to "
                    f"{MAX_IMPORT_ROWS:,}. Split it into smaller files."
                )
            }
            return TemplateResponse(request, "preferences/import_films.html", data)

        watchlist_shelf = models.Shelf.objects.filter(
            identifier=models.Shelf.TO_READ, user=user
        ).first()
        watched_shelf = models.Shelf.objects.filter(
            identifier=models.Shelf.READ_FINISHED, user=user
        ).first()

        results = []
        films = []
        for line_number, row in enumerate(rows, start=2):
            status, note, film = import_row(user, watchlist_shelf, watched_shelf, row)
            results.append(
                {
                    "line": line_number,
                    "name": (row.get("Name") or "").strip(),
                    "status": status,
                    "note": note,
                }
            )
            films.append(film)

        data = {
            "results": results,
            "summary": {
                "total": len(results),
                "created": sum(1 for r in results if r["status"] == "created"),
                "matched": sum(1 for r in results if r["status"] == "matched"),
                "skipped": sum(1 for r in results if r["status"] == "skipped"),
            },
        }

        # imported films are ID stubs (no API calls during import, decision
        # #30): fetch their posters and details in the background so the list
        # looks complete. Matched films are included too, so re-importing a
        # previously imported list backfills any stubs it left behind
        backfill_ids = [film.id for film in films if film is not None]
        if backfill_ids and tmdb.is_configured():
            data["backfill_queued"] = True
            transaction.on_commit(
                lambda: tmdb.backfill_imported_films_task.delay(backfill_ids)
            )

        return TemplateResponse(request, "preferences/import_films.html", data)
