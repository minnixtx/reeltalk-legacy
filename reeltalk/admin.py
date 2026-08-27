"""models that will show up in django admin for superuser"""

from django.contrib import admin
from reeltalk import models

admin.site.register(models.User)
admin.site.register(models.FederatedServer)
