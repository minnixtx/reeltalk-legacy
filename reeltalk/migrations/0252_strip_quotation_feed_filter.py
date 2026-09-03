"""strip 'quotation' from existing users' feed_status_types (decision 33)"""

from django.db import migrations


def strip_quotation(apps, schema_editor):
    # queryset .update() on purpose: Model.save() in a migration context does
    # not accept broadcast=, and save() would fire post_save signals + AP broadcasts
    User = apps.get_model("reeltalk", "User")
    for user in User.objects.filter(feed_status_types__contains=["quotation"]):
        types = [t for t in user.feed_status_types if t != "quotation"]
        User.objects.filter(pk=user.pk).update(feed_status_types=types)


def restore_quotation(apps, schema_editor):
    User = apps.get_model("reeltalk", "User")
    for user in User.objects.all():
        if "quotation" not in user.feed_status_types:
            types = list(user.feed_status_types) + ["quotation"]
            User.objects.filter(pk=user.pk).update(feed_status_types=types)


class Migration(migrations.Migration):

    dependencies = [
        ("reeltalk", "0251_delete_quotation"),
    ]

    operations = [
        migrations.RunPython(strip_quotation, restore_quotation),
    ]
