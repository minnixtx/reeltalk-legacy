"""testing reeltalk user import"""

from unittest.mock import patch
from django.test import TestCase
from reeltalk import models
from reeltalk.importers import ReeltalkImporter


class ReeltalkUserImport(TestCase):
    """importing from ReelTalk user import"""

    def setUp(self):
        """setting stuff up"""
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
            patch("reeltalk.suggested_users.rerank_user_task.delay"),
        ):
            self.user = models.User.objects.create_user(
                "mouse", "mouse@mouse.mouse", "password", local=True, localname="mouse"
            )

    def test_create_retry_job(self):
        """test retrying a user import"""

        job = models.reeltalk_import_job.ReeltalkImportJob.objects.create(
            user=self.user, required=[]
        )

        job.complete_job()
        self.assertEqual(job.retry, False)
        self.assertEqual(
            models.reeltalk_import_job.ReeltalkImportJob.objects.count(), 1
        )

        # retry the job
        importer = ReeltalkImporter()
        importer.create_retry_job(user=self.user, original_job=job)

        retry_job = models.reeltalk_import_job.ReeltalkImportJob.objects.last()

        self.assertEqual(
            models.reeltalk_import_job.ReeltalkImportJob.objects.count(), 2
        )
        self.assertEqual(retry_job.retry, True)
        self.assertNotEqual(job.id, retry_job.id)
