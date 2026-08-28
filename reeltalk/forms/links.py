"""using django model forms"""

from reeltalk import models
from .custom_form import CustomForm


class LinkDomainForm(CustomForm):
    class Meta:
        model = models.LinkDomain
        fields = ["name"]
