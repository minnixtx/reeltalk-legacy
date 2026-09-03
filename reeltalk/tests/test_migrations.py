"""testing data migration functions"""

import importlib
from unittest.mock import patch

from django.apps import apps as django_apps
from django.test import TestCase

from reeltalk import models


class QuotationFeedFilterMigration(TestCase):
    """0252 strips the removed 'quotation' key from saved feed filters (decision 33)"""

    def test_strip_quotation(self):
        """users with the removed key have it stripped; other keys and users untouched"""
        migration = importlib.import_module(
            "reeltalk.migrations.0252_strip_quotation_feed_filter"
        )
        user = models.User.objects.create_user(
            "mouse",
            "mouse@mouse.mouse",
            "password",
            local=True,
            localname="mouse",
            reeltalk_user=False,
        )
        other = models.User.objects.create_user(
            "rat",
            "rat@local.rat",
            "password",
            local=True,
            localname="rat",
            reeltalk_user=False,
        )
        with patch("reeltalk.models.activitypub_mixin.broadcast_task.apply_async"):
            user.feed_status_types = ["review", "quotation"]
            user.save()
            other.feed_status_types = ["review", "comment", "everything"]
            other.save()

        migration.strip_quotation(django_apps, None)

        user.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(user.feed_status_types, ["review"])
        self.assertEqual(other.feed_status_types, ["review", "comment", "everything"])

    def test_restore_quotation(self):
        """the reverse adds the key back for users missing it"""
        migration = importlib.import_module(
            "reeltalk.migrations.0252_strip_quotation_feed_filter"
        )
        user = models.User.objects.create_user(
            "mouse",
            "mouse@mouse.mouse",
            "password",
            local=True,
            localname="mouse",
            reeltalk_user=False,
        )

        migration.restore_quotation(django_apps, None)

        user.refresh_from_db()
        self.assertIn("quotation", user.feed_status_types)
