"""PROCEED WITH CAUTION: uses deduplication fields to permanently
merge author data objects"""

from reeltalk import models
from reeltalk.management.merge_command import MergeCommand


class Command(MergeCommand):
    """merges two authors by ID"""

    help = "merges specified authors into one"

    MODEL = models.Author
