"""using django model forms"""

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


class QuotationForm(CustomForm):
    class Meta:
        model = models.Quotation
        fields = [
            "user",
            "film",
            "quote",
            "content",
            "content_warning",
            "sensitive",
            "privacy",
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
