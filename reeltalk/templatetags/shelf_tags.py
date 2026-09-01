"""Filters and tags related to shelving films"""

from django import template
from django.utils.translation import gettext_lazy as _

from reeltalk import models
from reeltalk.utils import cache


register = template.Library()


SHELF_NAMES = {
    "all": _("All films"),
    "to-read": _("Watchlist"),
    "read": _("Watched"),
}


@register.filter(name="is_film_on_shelf")
def get_is_film_on_shelf(film, shelf):
    """is a film on a shelf"""
    return cache.get_or_set(
        f"film-on-shelf-{film.id}-{shelf.id}",
        lambda f, s: s.films.filter(id=f.id).exists(),
        film,
        shelf,
        timeout=60 * 60,  # just cache this for an hour
    )


@register.filter(name="next_shelf")
def get_next_shelf(current_shelf):
    """shelf you'd use to update viewing status"""
    if current_shelf == "to-read":
        return "read"
    if current_shelf == "read":
        return "complete"
    return "to-read"


@register.filter(name="translate_shelf_name")
def get_translated_shelf_name(shelf):
    """produce translated shelf identifiername"""
    if not shelf:
        return ""
    # support obj or dict
    identifier = shelf["identifier"] if isinstance(shelf, dict) else shelf.identifier

    try:
        return SHELF_NAMES[identifier]
    except KeyError:
        return shelf["name"] if isinstance(shelf, dict) else shelf.name


@register.simple_tag(takes_context=True)
def active_shelf(context, film):
    """check what shelf a user has a film on, if any"""
    user = context["request"].user
    return cache.get_or_set(
        f"active_shelf-{user.id}-{film.id}",
        lambda u, f: (
            models.ShelfFilm.objects.filter(
                shelf__user=u,
                film=f,
            ).first()
            or False
        ),
        user,
        film,
        timeout=60 * 60,
    ) or {"film": film}
