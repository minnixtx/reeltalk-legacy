"""What you need in the database to make it work"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

from reeltalk import models


def init_groups():
    """permission levels"""
    groups = ["admin", "owner", "moderator", "editor"]
    for group in groups:
        Group.objects.get_or_create(name=group)


def init_permissions():
    """permission types"""
    permissions = [
        {
            "codename": "manage_registration",
            "name": "allow or prevent user registration",
            "groups": ["admin"],
        },
        {
            "codename": "system_administration",
            "name": "technical controls",
            "groups": ["admin"],
        },
        {
            "codename": "edit_instance_settings",
            "name": "change the instance info",
            "groups": ["admin", "owner"],
        },
        {
            "codename": "set_user_group",
            "name": "change what group a user is in",
            "groups": ["admin", "owner", "moderator"],
        },
        {
            "codename": "control_federation",
            "name": "control who to federate with",
            "groups": ["admin", "owner", "moderator"],
        },
        {
            "codename": "create_invites",
            "name": "issue invitations to join",
            "groups": ["admin", "owner", "moderator"],
        },
        {
            "codename": "moderate_user",
            "name": "deactivate or silence a user",
            "groups": ["admin", "owner", "moderator"],
        },
        {
            "codename": "moderate_post",
            "name": "delete other users' posts",
            "groups": ["admin", "owner", "moderator"],
        },
        {
            "codename": "edit_film",
            "name": "edit film info",
            "groups": ["admin", "owner", "moderator", "editor"],
        },
    ]

    content_type = ContentType.objects.get_for_model(models.User)
    for permission in permissions:
        permission_obj, _ = Permission.objects.get_or_create(
            codename=permission["codename"],
            name=permission["name"],
            content_type=content_type,
        )
        # add the permission to the appropriate groups
        for group_name in permission["groups"]:
            Group.objects.get(name=group_name).permissions.add(permission_obj)


def init_settings():
    """info about the instance"""
    group_editor = Group.objects.filter(name="editor").first()
    if not models.SiteSettings.objects.all().first():
        models.SiteSettings.objects.create(
            install_mode=True,
            default_user_auth_group=group_editor,
        )


def init_link_domains():
    """safe book links"""
    domains = [
        ("standardebooks.org", "Standard EBooks"),
        ("www.gutenberg.org", "Project Gutenberg"),
        ("archive.org", "Internet Archive"),
        ("openlibrary.org", "Open Library"),
        ("theanarchistlibrary.org", "The Anarchist Library"),
    ]
    for domain, name in domains:
        models.LinkDomain.objects.get_or_create(
            domain=domain,
            defaults={
                "name": name,
                "status": "approved",
            },
        )


class Command(BaseCommand):
    """command-line options"""

    help = "Initializes the database with starter data"

    def add_arguments(self, parser):
        """specify which function to run"""
        parser.add_argument(
            "--limit",
            default=None,
            help="Limit init to specific table",
        )

    def handle(self, *args, **options):
        """execute init"""
        limit = options.get("limit")
        tables = [
            "group",
            "permission",
            "settings",
            "linkdomain",
        ]
        if limit and limit not in tables:
            raise Exception("Invalid table limit:", limit)

        if not limit or limit == "group":
            init_groups()
        if not limit or limit == "permission":
            init_permissions()
        if not limit or limit == "settings":
            init_settings()
        if not limit or limit == "linkdomain":
            init_link_domains()
