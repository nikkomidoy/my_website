"""Housekeeping jobs run by the `crontask` process."""

from datetime import timedelta

import structlog
from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from crontask import cron
from django.apps import apps
from django.conf import settings
from django.core.management import call_command
from django.tasks import task
from django.utils import timezone

log = structlog.get_logger(__name__)


@cron("30 3 * * *")
@task()
def purge_login_records() -> int:
    """GDPR storage limitation: drop login-attempt records (IP + username) past retention."""
    cutoff = timezone.now() - timedelta(days=settings.PRIVACY_LOGIN_ATTEMPT_RETENTION_DAYS)
    deleted = 0
    deleted += AccessAttempt.objects.filter(attempt_time__lt=cutoff).delete()[0]
    deleted += AccessLog.objects.filter(attempt_time__lt=cutoff).delete()[0]
    deleted += AccessFailureLog.objects.filter(attempt_time__lt=cutoff).delete()[0]
    log.info("privacy.purged_login_records", deleted=deleted)
    return deleted


@cron("17 3 * * *")
@task()
def backup_database() -> str:
    """Nightly pg_dump to the private DBBACKUP_BUCKET (production only)."""
    if not apps.is_installed("dbbackup"):
        return "skipped: dbbackup not installed (non-production settings)"
    call_command("dbbackup", "--clean", "--noinput")
    log.info("dbbackup.completed")
    return "ok"
