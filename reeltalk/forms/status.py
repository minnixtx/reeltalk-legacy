"""using django model forms"""

from django.core.exceptions import ValidationError

from reeltalk import models
from .custom_form import CustomForm


class RatingForm(CustomForm):
    class Meta:
        model = models.ReviewRating
        fields = ["user", "film", "rating", "privacy"]


class ReviewForm(CustomForm):
    class Meta:
        model = models.Review
        fields = [
            "user",
            "film",
            "name",
            "content",
            "rating",
            "content_warning",
            "sensitive",
            "privacy",
        ]

    def clean(self):
        """a rating-only entry must keep its rating (it can't be saved without one)"""
        cleaned_data = super().clean()
        if isinstance(self.instance, models.ReviewRating) and not cleaned_data.get(
            "rating"
        ):
            self.add_error("rating", ValidationError("A star rating is required."))
        return cleaned_data


class CommentForm(CustomForm):
    class Meta:
        model = models.Comment
        fields = [
            "user",
            "film",
            "content",
            "content_warning",
            "sensitive",
            "privacy",
            "reading_status",
        ]


class ReplyForm(CustomForm):
    class Meta:
        model = models.Status
        fields = [
            "user",
            "content",
            "content_warning",
            "sensitive",
            "reply_parent",
            "privacy",
        ]


class StatusForm(CustomForm):
    class Meta:
        model = models.Status
        fields = ["user", "content", "content_warning", "sensitive", "privacy"]


class DirectForm(CustomForm):
    class Meta:
        model = models.Status
        fields = ["user", "content", "content_warning", "sensitive", "privacy"]
