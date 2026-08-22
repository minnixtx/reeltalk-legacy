"""Get your admin code to allow install"""

from django.core.management.base import BaseCommand

from reeltalk import models


def get_admin_code():
    """get that code"""
    return models.SiteSettings.get().admin_code


class Command(BaseCommand):
    """command-line options"""

    help = "Gets admin code for configuring ReelTalk"

    def handle(self, *args, **options):
        """execute init"""
        self.stdout.write("*******************************************")
        self.stdout.write("Use this code to create your admin account:")
        self.stdout.write(get_admin_code())
        self.stdout.write("*******************************************")
