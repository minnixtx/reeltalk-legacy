"""Let users export their film data"""

from datetime import UTC, timedelta
import csv
import datetime
import io
import logging

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, ExpressionWrapper, F
from django.db.models.fields import DurationField
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse, HttpResponseServerError, Http404
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views import View
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.shortcuts import redirect

from reeltalk import models, settings, tmdb
from reeltalk.models.reeltalk_export_job import ReeltalkExportJob
from reeltalk.utils.cache import get_or_set

logger = logging.getLogger(__name__)


@method_decorator(login_required, name="dispatch")
class Export(View):
    """Let users export data"""

    def get(self, request):
        """Request csv file"""
        return TemplateResponse(request, "preferences/export.html")

    def post(self, request):
        """Download the user's film list as a TMDB-format CSV"""
        films = models.Film.viewer_aware_objects(request.user)
        films_shelves = films.filter(Q(shelffilm__user=request.user)).distinct()
        films_review = films.filter(Q(review__user=request.user)).distinct()
        films_comment = films.filter(Q(comment__user=request.user)).distinct()
        films_quotation = films.filter(Q(quotation__user=request.user)).distinct()

        films = set(
            list(films_shelves) + list(films_review) + list(films_comment) + list(films_quotation)
        )

        csv_string = io.StringIO()
        writer = csv.writer(csv_string)
        writer.writerow(tmdb.TMDB_EXPORT_HEADER)

        for film in films:
            # the user's most recent rated review provides Your Rating / Date Rated
            review = (
                models.Review.objects.filter(
                    user=request.user, film=film, rating__isnull=False
                )
                .order_by("-published_date")
                .first()
            )
            writer.writerow(
                [
                    film.tmdb_id or "",
                    film.imdb_id or "",
                    "movie",
                    film.title,
                    # only the year is stored: emit it as a Jan 1 date so a
                    # round-trip import can read it back
                    f"{film.year}-01-01T00:00:00Z" if film.year else "",
                    "",  # Season Number
                    "",  # Episode Number
                    "",  # Rating (TMDB community score — not stored)
                    int(review.rating * 2) if review else "",
                    review.published_date.astimezone(UTC).strftime(
                        "%Y-%m-%dT%H:%M:%SZ"
                    )
                    if review and review.published_date
                    else "",
                ]
            )

        return HttpResponse(
            csv_string.getvalue(),
            content_type="text/csv",
            headers={
                "Content-Disposition": 'attachment; filename="reeltalk-export.csv"'
            },
        )


@method_decorator(login_required, name="dispatch")
class ExportUser(View):
    """
    Let users request and download an archive of user data to import into
    another Reeltalk instance.
    """

    user_jobs = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        self.user_jobs = ReeltalkExportJob.objects.filter(user=request.user).order_by(
            "-created_date"
        )

    def new_export_blocked_until(self):
        """whether the user is allowed to request a new export"""
        last_job = self.user_jobs.first()
        if not last_job:
            return None
        site = models.SiteSettings.get()
        blocked_until = last_job.created_date + timedelta(
            hours=site.user_import_time_limit
        )
        return blocked_until if blocked_until > timezone.now() else None

    def get(self, request):
        """Request tar file"""

        exports = []
        for job in self.user_jobs:
            export = {"job": job}

            if job.export_data:
                try:
                    export["size"] = job.export_data.size
                    export["url"] = reverse("prefs-export-file", args=[job.task_id])
                except (
                    FileNotFoundError,
                    Exception,
                ):
                    # file no longer exists
                    export["url"] = None

            exports.append(export)

        next_available = self.new_export_blocked_until()
        paginated = Paginator(exports, settings.PAGE_LENGTH)
        site = models.SiteSettings.objects.get()
        page = paginated.get_page(request.GET.get("page"))
        data = {
            "jobs": page,
            "next_available": next_available,
            "page_range": paginated.get_elided_page_range(
                page.number, on_each_side=2, on_ends=1
            ),
            "expiry_hours": site.export_files_lifetime_hours,
        }

        seconds = get_or_set(
            "avg-user-export-time", get_average_export_time, timeout=86400
        )
        if seconds and seconds > 60**2:
            data["recent_avg_hours"] = seconds / (60**2)
        elif seconds:
            data["recent_avg_minutes"] = seconds / 60

        return TemplateResponse(request, "preferences/export-user.html", data)

    def post(self, request):
        """Trigger processing of a new user export file"""
        if self.new_export_blocked_until() is not None:
            return HttpResponse(status=429)  # Too Many Requests

        job = ReeltalkExportJob.objects.create(user=request.user)
        job.start_job()

        return redirect("prefs-user-export")


@method_decorator(login_required, name="dispatch")
class ExportArchive(View):
    """Serve the archive file"""

    def get(self, request, archive_id):
        """download user export file"""
        export = ReeltalkExportJob.objects.get(task_id=archive_id, user=request.user)

        if settings.USE_S3_FOR_EXPORTS:
            url = export.export_data.url  # this is a pre-signed url by default, nice
            return redirect(url)

        if settings.USE_AZURE:
            # not implemented
            return HttpResponseServerError()

        try:
            return HttpResponse(
                export.export_data,
                content_type="application/gzip",
                headers={
                    "Content-Disposition": 'attachment; filename="reeltalk-account-export.tar.gz"'
                },
            )
        except FileNotFoundError:
            raise Http404()


def get_average_export_time() -> float:
    """Helper to figure out how long exports are taking (returns seconds)"""
    last_week = timezone.now() - datetime.timedelta(days=7)
    recent_avg = (
        models.ReeltalkExportJob.objects.filter(
            created_date__gte=last_week, complete=True
        )
        .exclude(status="stopped")
        .annotate(
            runtime=ExpressionWrapper(
                F("updated_date") - F("created_date"),
                output_field=DurationField(),
            )
        )
        .aggregate(Avg("runtime"))
        .get("runtime__avg")
    )

    if recent_avg:
        return recent_avg.total_seconds()
    return None
