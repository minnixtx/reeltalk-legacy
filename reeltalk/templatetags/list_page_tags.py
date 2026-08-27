"""template filters for list page"""

from django import template
from django.utils.translation import gettext_lazy as _, ngettext

from reeltalk import models


register = template.Library()


@register.filter(name="opengraph_title")
def get_opengraph_title(film_list: models.List) -> str:
    """Construct title for Open Graph"""
    return _("Film List: %(name)s") % {"name": film_list.name}


@register.filter(name="opengraph_description")
def get_opengraph_description(film_list: models.List) -> str:
    """Construct description for Open Graph"""
    num_films = film_list.films.all().count()
    num_films_str = ngettext(
        "%(num)d film - by %(user)s", "%(num)d films - by %(user)s", num_films
    ) % {"num": num_films, "user": film_list.user}

    return f"{film_list.description} {num_films_str}"
