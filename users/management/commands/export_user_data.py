import json

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import serializers
from django.core.management.base import BaseCommand
from wagtail.users.models import UserProfile


class Command(BaseCommand):
    help = "GDPR Art. 15/20: export a user's personal data as JSON."

    # The export goes to the data subject — internal auth state stays out,
    # and the password hash above all.
    EXCLUDE = {"password", "is_staff", "is_superuser", "groups", "user_permissions"}

    def add_arguments(self, parser):
        parser.add_argument("user_id", type=int)

    def handle(self, *args, user_id, **opts):
        user = get_user_model().objects.get(pk=user_id)
        data = json.loads(serializers.serialize("json", [user]))
        for obj in data:
            obj["fields"] = {k: v for k, v in obj["fields"].items() if k not in self.EXCLUDE}
        # User-owned rows from project apps / third-party apps.
        data += json.loads(serializers.serialize("json", EmailAddress.objects.filter(user=user)))
        data += json.loads(serializers.serialize("json", UserProfile.objects.filter(user=user)))
        self.stdout.write(json.dumps(data, indent=2))
