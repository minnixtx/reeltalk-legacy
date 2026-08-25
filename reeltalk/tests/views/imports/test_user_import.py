"""test for app action functionality"""

import pathlib
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.response import TemplateResponse
from django.test import TestCase
from django.test.client import RequestFactory

from reeltalk import forms, models, views
from reeltalk.tests.validate_html import validate_html


class ImportUserViews(TestCase):
    """user import views"""

    def setUp(self):
        """we need basic test data and mocks"""
        self.site = models.SiteSettings.get()
        self.factory = RequestFactory()
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            self.local_user = models.User.objects.create_user(
                "mouse@local.com",
                "mouse@mouse.mouse",
                "password",
                local=True,
                localname="mouse",
            )

    def test_get_user_import_page(self):
        """there are so many views, this just makes sure it LOADS"""
        view = views.UserImport.as_view()
        request = self.factory.get("")
        request.user = self.local_user
        result = view(request)
        self.assertIsInstance(result, TemplateResponse)
        validate_html(result.render())
        self.assertEqual(result.status_code, 200)

    def test_user_import_post(self):
        """does the import job start?"""

        view = views.UserImport.as_view()
        form = forms.ImportUserForm()
        archive_path = pathlib.Path(__file__).parent.joinpath(
            "../../data/reeltalk_account_export.tar.gz"
        )

        with open(archive_path, "rb") as archive_file:
            form.data["archive_file"] = SimpleUploadedFile(
                archive_path,
                archive_file.read(),
                content_type="application/gzip",
            )

        form.data["include_user_settings"] = ""

        request = self.factory.post("", form.data)
        request.user = self.local_user

        with patch("reeltalk.models.reeltalk_import_job.ReeltalkImportJob.start_job"):
            view(request)
        job = models.ReeltalkImportJob.objects.get()
        self.assertEqual(job.required, [])
