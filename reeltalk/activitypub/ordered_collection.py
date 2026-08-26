"""defines activitypub collections (lists)"""

from dataclasses import dataclass, field
from typing import List

from .base_activity import ActivityObject


@dataclass(init=False)
class OrderedCollection(ActivityObject):
    """structure of an ordered collection activity"""

    totalItems: int
    first: str
    last: str = None
    name: str = None
    owner: str = None
    type: str = "OrderedCollection"


@dataclass(init=False)
class OrderedCollectionPrivate(OrderedCollection):
    """an ordered collection with privacy settings"""

    to: List[str] = field(default_factory=lambda: [])
    cc: List[str] = field(default_factory=lambda: [])


@dataclass(init=False)
class Shelf(OrderedCollectionPrivate):
    """structure of an ordered collection activity"""

    type: str = "Shelf"


@dataclass(init=False)
class FilmList(OrderedCollectionPrivate):
    """structure of an ordered collection activity"""

    summary: str = None
    curation: str = "closed"
    type: str = "FilmList"


@dataclass(init=False)
class OrderedCollectionPage(ActivityObject):
    """structure of an ordered collection page activity"""

    partOf: str
    orderedItems: List
    next: str = None
    prev: str = None
    type: str = "OrderedCollectionPage"


@dataclass(init=False)
class CollectionItem(ActivityObject):
    """an item in a collection"""

    actor: str
    type: str = "CollectionItem"


@dataclass(init=False)
class ListItem(CollectionItem):
    """a film on a list"""

    film: str
    notes: str = None
    approved: bool = True
    order: int = None
    type: str = "ListItem"


@dataclass(init=False)
class ShelfItem(CollectionItem):
    """a film on a shelf"""

    film: str
    type: str = "ShelfItem"
