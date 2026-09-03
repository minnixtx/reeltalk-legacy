"""remove the Quotation model (decision 33)"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("reeltalk", "0250_rename_watchlist_shelf"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Quotation",
        ),
    ]
