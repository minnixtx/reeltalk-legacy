"""film data"""

from dataclasses import dataclass, field
from typing import Optional

from .base_activity import ActivityObject
from .image import Document


@dataclass(init=False)
class Film(ActivityObject):
    """a film object on the wire"""

    title: str
    sortTitle: str = None
    subtitle: str = None
    description: str = ""
    year: Optional[int] = None
    runtime: Optional[int] = None

    genres: list[str] = field(default_factory=list)
    directors: list[str] = field(default_factory=list)
    cast: list[str] = field(default_factory=list)

    tmdbId: Optional[str] = None
    imdbId: Optional[str] = None
    lastEditedBy: Optional[str] = None

    poster: Optional[Document] = None
    type: str = "Film"
