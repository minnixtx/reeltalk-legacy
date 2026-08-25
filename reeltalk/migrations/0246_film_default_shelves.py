"""rework default shelves for the film model"""

from django.db import migrations


def update_default_shelves(apps, schema_editor):
    Shelf = apps.get_model("reeltalk", "Shelf")
    ShelfBook = apps.get_model("reeltalk", "ShelfBook")

    # rename the surviving default status shelves
    for identifier, name in {
        "to-read": "Want to Watch",
        "read": "Watched",
    }.items():
        Shelf.objects.filter(identifier=identifier, editable=False).update(name=name)

    # drop the in-progress default shelves; unshelve anything on them first
    obsolete = Shelf.objects.filter(
        identifier__in=["reading", "stopped-reading"], editable=False
    )
    if obsolete.exists():
        ShelfBook.objects.filter(shelf__in=obsolete).delete()
        obsolete.delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("reeltalk", "0245_remove_sitesettings_code_of_conduct_and_more"),
    ]

    operations = [
        migrations.RunPython(update_default_shelves, noop),
    ]
