"""tags used on the feed pages"""

from django import template
from reeltalk.views.feed import get_suggested_films


register = template.Library()


@register.filter(name="load_subclass")
def load_subclass(status):
    """sometimes you didn't select_subclass"""
    if hasattr(status, "review"):
        return status.review
    if hasattr(status, "comment"):
        return status.comment
    if hasattr(status, "generatednote"):
        return status.generatednote
    return status


@register.simple_tag(takes_context=True)
def suggested_films(context):
    """get films for suggested films panel"""
    # this happens here instead of in the view so that the template snippet can
    # be cached in the template
    return get_suggested_films(context["request"].user)
