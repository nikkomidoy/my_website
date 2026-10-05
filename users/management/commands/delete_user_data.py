from axes.models import AccessAttempt, AccessFailureLog, AccessLog
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


class Command(BaseCommand):
    help = "GDPR Art. 17: erase a user and their personal data."

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int)

    def handle(self, *args, user_id, **opts):
        User = get_user_model()
        with transaction.atomic():
            user = User.objects.get(pk=user_id)
            # axes keys rows by username, not FK — erase them explicitly.
            AccessAttempt.objects.filter(username=user.get_username()).delete()
            AccessLog.objects.filter(username=user.get_username()).delete()
            AccessFailureLog.objects.filter(username=user.get_username()).delete()
            # allauth EmailAddress / MFA authenticators cascade via FK.
            user.delete()
        self.stdout.write(self.style.SUCCESS(f"deleted user {user_id}"))
