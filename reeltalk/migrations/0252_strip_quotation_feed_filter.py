"""strip 'quotation' from existing users' feed_status_types (decision 33)"""

from django.db import migrations


def strip_quotation(apps, schema_editor):
    User = apps.get_model("reeltalk", "User")
    for user in User.objects.filter(feed_status_types__contains=["quotation"]):
        user.feed_status_types = [
            t for t in user.feed_status_types if t != "quotation"
        ]
        user.save(broadcast=False, update_fields=["feed_status_types"])


def restore_quotation(apps, schema_editor):
    User = apps.get_model("reeltalk", "User")
    for user in User.objects.all():
        if "quotation" not in user.feed_status_types:
            user.feed_status_types.append("quotation")
            user.save(broadcast=False, update_fields=["feed_status_types"])


class Migration(migrations.Migration):

    dependencies = [
        ("reeltalk", "0251_delete_quotation"),
    ]

    operations = [
        migrations.RunPython(strip_quotation, restore_quotation),
    ]
