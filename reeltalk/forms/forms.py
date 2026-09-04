"""using django model forms"""

from django.forms import widgets

from reeltalk import models
from reeltalk.models.user import FeedFilterChoices
from .custom_form import CustomForm


class FeedStatusTypesForm(CustomForm):
    class Meta:
        model = models.User
        fields = ["feed_status_types"]
        help_texts = {f: None for f in fields}
        widgets = {
            "feed_status_types": widgets.CheckboxSelectMultiple(
                choices=FeedFilterChoices,
            ),
        }


class ReportForm(CustomForm):
    class Meta:
        model = models.Report
        fields = [
            "reported_user",
            "user",
            "statuses",
            "links",
            "note",
            "allow_broadcast",
        ]
