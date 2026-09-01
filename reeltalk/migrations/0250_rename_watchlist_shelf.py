"""rename the Want to Watch shelf to Watchlist (display name only)"""

from django.db import migrations


def rename_watchlist(apps, schema_editor):
    Shelf = apps.get_model("reeltalk", "Shelf")
    # the identifier is wire format and stays "to-read"; only the display
    # name changes. default shelves are created with editable=False.
    Shelf.objects.filter(
        identifier="to-read", editable=False, name="Want to Watch"
    ).update(name="Watchlist")


def rename_back(apps, schema_editor):
    Shelf = apps.get_model("reeltalk", "Shelf")
    Shelf.objects.filter(
        identifier="to-read", editable=False, name="Watchlist"
    ).update(name="Want to Watch")


class Migration(migrations.Migration):

    dependencies = [
        ("reeltalk", "0249_alter_comment_reading_status_and_more"),
    ]

    operations = [
        migrations.RunPython(rename_watchlist, rename_back),
    ]
