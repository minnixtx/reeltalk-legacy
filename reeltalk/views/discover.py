"""What's up locally"""

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.views import View

from reeltalk import activitystreams


@method_decorator(login_required, name="dispatch")
class Discover(View):
    """preview of recently reviewed films"""

    def get(self, request):
        """tiled film activity page"""
        # all activities in the "local" feed associated with a film
        activities = (
            activitystreams.streams["local"]
            .get_activity_stream(request.user)
            .filter(
                Q(comment__isnull=False)
                | Q(review__isnull=False)
                | Q(mention_films__isnull=False)
            )
        )

        large_activities = Paginator(
            activities.filter(mention_films__isnull=True)
            # exclude statuses with no user-provided content for large panels
            .exclude(Q(content="") | Q(content__isnull=True)),
            6,
        )
        small_activities = Paginator(
            activities.filter(
                Q(mention_films__isnull=False)
                | Q(Q(content="") | Q(content__isnull=True))
            ),
            4,
        )

        page = request.GET.get("page")
        data = {
            "large_activities": large_activities.get_page(page),
            "small_activities": small_activities.get_page(page),
        }
        return TemplateResponse(request, "discover/discover.html", data)
