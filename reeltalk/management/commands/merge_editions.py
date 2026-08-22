"""PROCEED WITH CAUTION: uses deduplication fields to permanently
merge edition data objects"""

from reeltalk import models
from reeltalk.management.merge_command import MergeCommand


class Command(MergeCommand):
    """merges two editions by ID"""

    help = "merges specified editions into one"

    MODEL = models.Edition
