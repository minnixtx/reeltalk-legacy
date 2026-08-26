"""cleanup tasks"""

import math
from datetime import datetime, timedelta, timezone

from django.db import transaction
from django.db.models import DateTimeField, IntegerField

from reeltalk import models
from reeltalk.models.job import ParentJob, ParentTask
from reeltalk.tasks import app, MISC


class CleanUpUserExportFilesJob(ParentJob):
    """A job to clean up old export files"""

    expiry_date = DateTimeField()
    tasks = IntegerField(default=0)
    completed_tasks = IntegerField(default=0)

    @property
    def percent_complete(self):
        """How many tasks are done?"""

        if not self.tasks:
            return 0

        return math.floor(self.completed_tasks / self.tasks * 100)

    def start_job(self):
        """schedule the tasks"""

        self.set_status("active")

        export_jobs = models.ReeltalkExportJob.objects.filter(
            complete=True, updated_date__lt=self.expiry_date
        )

        for export in export_jobs:
            if export.export_data.name:
                self.tasks += 1
                self.save(update_fields=["tasks"])
                delete_user_export_file_task.delay(job_id=self.id, export_id=export.id)

        if self.tasks == 0:
            self.complete_job()


class CleanUpExportsTask(ParentTask):
    """Task to delete expired user export files"""

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """Handler called when the task returns"""

        with transaction.atomic():
            job = CleanUpUserExportFilesJob.objects.select_for_update().get(
                id=kwargs["job_id"]
            )
            job.completed_tasks += 1
            job.save(update_fields=["completed_tasks"])
            is_finished = job.completed_tasks == job.tasks

        if is_finished:
            job.complete_job()


@app.task(queue=MISC, base=CleanUpExportsTask)
def delete_user_export_file_task(**kwargs):
    """A task to delete a specific export file"""

    export_id = kwargs.get("export_id")
    if export_id:
        file = models.ReeltalkExportJob.objects.get(id=export_id)
        file.export_data.delete()


@app.task(queue=MISC)
def start_export_deletions(**kwargs):
    """trigger the job from scheduler"""

    user = models.User.objects.get(id=kwargs["user"])
    site = models.SiteSettings.objects.get()
    hours = site.export_files_lifetime_hours

    expiry_date = datetime.now(timezone.utc) - timedelta(hours=hours)
    job = CleanUpUserExportFilesJob.objects.create(user=user, expiry_date=expiry_date)

    job.start_job()
