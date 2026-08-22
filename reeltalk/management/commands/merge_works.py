"""PROCEED WITH CAUTION: uses deduplication fields to permanently
merge work data objects"""

from reeltalk import models
from reeltalk.management.merge_command import MergeCommand


class Command(MergeCommand):
    """merges two works by ID"""

    help = "merges specified works into one"

    MODEL = models.Work
