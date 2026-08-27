"""using django model forms"""

from django import forms

from file_resubmit.widgets import ResubmitImageWidget

from reeltalk import models
from reeltalk.settings import DATA_UPLOAD_MAX_MEMORY_SIZE
from .custom_form import CustomForm
from .widgets import ArrayWidget


class CoverForm(CustomForm):
    class Meta:
        model = models.Film
        fields = ["poster"]
        help_texts = {f: None for f in fields}


class ResubmitImageWidgetWithWarning(ResubmitImageWidget):
    """Define template to use that shows warning on too big image"""

    template_name = "widgets/clearable_file_input_with_warning.html"

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["attrs"].update(
            {
                "data-max-upload": DATA_UPLOAD_MAX_MEMORY_SIZE,
                "max_mb": DATA_UPLOAD_MAX_MEMORY_SIZE >> 20,
            }
        )
        return context


class FilmForm(CustomForm):
    class Meta:
        model = models.Film
        fields = [
            "title",
            "sort_title",
            "subtitle",
            "description",
            "year",
            "runtime",
            "genres",
            "directors",
            "cast",
            "poster",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"aria-describedby": "desc_title"}),
            "sort_title": forms.TextInput(
                attrs={"aria-describedby": "desc_sort_title"}
            ),
            "subtitle": forms.TextInput(attrs={"aria-describedby": "desc_subtitle"}),
            "description": forms.Textarea(
                attrs={"aria-describedby": "desc_description"}
            ),
            "year": forms.NumberInput(attrs={"aria-describedby": "desc_year"}),
            "runtime": forms.NumberInput(attrs={"aria-describedby": "desc_runtime"}),
            "genres": ArrayWidget(),
            "directors": ArrayWidget(),
            "cast": ArrayWidget(),
            "poster": ResubmitImageWidgetWithWarning(
                attrs={"aria-describedby": "desc_poster"}
            ),
        }
