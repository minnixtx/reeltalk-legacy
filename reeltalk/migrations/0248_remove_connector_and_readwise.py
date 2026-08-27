"""remove the connector model and the readwise api key field"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("reeltalk", "0247_replace_books_with_films"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Connector",
        ),
        migrations.RemoveField(
            model_name="user",
            name="readwise_api_key",
        ),
    ]
