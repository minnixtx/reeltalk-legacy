"""connections to external ActivityPub servers"""

from urllib.parse import urlparse

from django.db import models
from django.utils.translation import gettext_lazy as _

from .base_model import ReelTalkModel

FederationStatus = [
    ("federated", _("Federated")),
    ("blocked", _("Blocked")),
]


class FederatedServer(ReelTalkModel):
    """store which servers we federate with"""

    server_name = models.CharField(max_length=255, unique=True)  # domain
    status = models.CharField(
        max_length=255, default="federated", choices=FederationStatus
    )
    # is it mastodon, reeltalk, etc
    application_type = models.CharField(max_length=255, null=True, blank=True)
    application_version = models.CharField(max_length=255, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    def block(self):
        """block a server"""
        self.status = "blocked"
        self.save(update_fields=["status"])

        # deactivate all associated users
        self.user_set.filter(is_active=True).update(
            is_active=False, deactivation_reason="domain_block"
        )

    def unblock(self):
        """unblock a server"""
        self.status = "federated"
        self.save(update_fields=["status"])

        self.user_set.filter(deactivation_reason="domain_block").update(
            is_active=True, deactivation_reason=None
        )

    @classmethod
    def is_blocked(cls, url: str) -> bool:
        """look up if a domain is blocked"""
        url = urlparse(url)
        return cls.objects.filter(server_name=url.hostname, status="blocked").exists()
