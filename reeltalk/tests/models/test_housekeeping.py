"""test file management"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from os import listdir
import pathlib
from unittest.mock import patch

from django.core.files.base import ContentFile
from django.test import TestCase, TransactionTestCase

from reeltalk.models import (
    ReeltalkExportJob,
    CleanUpUserExportFilesJob,
    SiteSettings,
    start_export_deletions,
    User,
)
from reeltalk.settings import DOMAIN
from reeltalk.models.housekeeping import (
    CleanUpExportsTask,
    delete_user_export_file_task,
)


class TestCleanUpExportFiles(TestCase):
    """export files should be deleted periodically"""

    def setUp(self):
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            self.user = User.objects.create_user(
                f"mouse@{DOMAIN}",
                "mouse@mouse.mouse",
                "mouseword",
                local=True,
                localname="mouse",
                name="hi",
                summary="a summary",
                reeltalk_user=False,
            )

            expiry_date = datetime.now(timezone.utc) - timedelta(hours=2)
            self.job = CleanUpUserExportFilesJob.objects.create(
                user=self.user, expiry_date=expiry_date
            )

            SiteSettings.objects.create()

    def test_export_file_deleted(self, *_):
        """did the file actually get deleted?"""

        export_updated_date = datetime.now(timezone.utc) - timedelta(hours=3)
        export = ReeltalkExportJob.objects.create(
            user=self.user,
            export_data=ContentFile(b"..", name="zzz_testfile.tar.gz"),
            updated_date=export_updated_date,
            complete=True,
        )

        self.assertTrue(export.export_data.name)
        delete_user_export_file_task(job_id=self.job.id, export_id=export.id)
        export.refresh_from_db()
        self.assertFalse(export.export_data.name)

    def test_renamed_file_deleted(self, *_):
        """files with duplicate names get renamed like filename.tar7x9e.gz"""

        export_updated_date = datetime.now(timezone.utc) - timedelta(hours=3)
        export = ReeltalkExportJob.objects.create(
            user=self.user,
            export_data=ContentFile(b"...", name="zzz_testfile.tar.gz"),
            updated_date=export_updated_date,
            complete=True,
        )

        self.assertTrue(export.export_data)
        export.refresh_from_db()
        delete_user_export_file_task(job_id=self.job.id, export_id=export.id)
        export.refresh_from_db()
        self.assertFalse(export.export_data.name)

    def test_start_export_deletions(self, *_):
        """does start_export_deletions actually start a job?"""

        self.assertEqual(CleanUpUserExportFilesJob.objects.count(), 1)

        start_export_deletions(user=self.user.id)

        self.assertEqual(CleanUpUserExportFilesJob.objects.count(), 2)
        self.assertNotEqual(CleanUpUserExportFilesJob.objects.last().status, "pending")

    def tearDown(self):
        """clean up any files"""

        for filename in listdir("exports"):
            if "zzz_testfile.tar" in filename:
                pathlib.Path(f"exports/{filename}").unlink(missing_ok=True)


class TestCleanUpExportsTask(TransactionTestCase):
    """the task reports its completion back to the job"""

    def setUp(self):
        with (
            patch("reeltalk.suggested_users.rerank_suggestions_task.delay"),
            patch("reeltalk.activitystreams.populate_stream_task.delay"),
            patch("reeltalk.lists_stream.populate_lists_task.delay"),
        ):
            self.user = User.objects.create_user(
                f"mouse@{DOMAIN}",
                "mouse@mouse.mouse",
                local=True,
                localname="mouse",
            )
            SiteSettings.objects.create()

        self.job = CleanUpUserExportFilesJob.objects.create(
            user=self.user,
            expiry_date=datetime.now(timezone.utc) - timedelta(hours=2),
            tasks=10,
        )

    def test_concurrent_task_returns_complete_the_job_once(self):
        def report_completion(_):
            CleanUpExportsTask().after_return(
                None, None, None, None, {"job_id": self.job.id}, None
            )

        with patch.object(CleanUpUserExportFilesJob, "complete_job") as complete_job:
            with ThreadPoolExecutor(max_workers=10) as pool:
                list(pool.map(report_completion, range(10)))

        self.job.refresh_from_db()
        self.assertEqual(self.job.completed_tasks, 10)
        complete_job.assert_called_once()
