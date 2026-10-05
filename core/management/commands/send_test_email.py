from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils.html import strip_tags


class Command(BaseCommand):
    help = "Send a test email through the default mailer to verify email settings."

    def add_arguments(self, parser):
        parser.add_argument("recipient", help="Email address to send the test message to")

    def handle(self, *args, recipient: str, **options):
        context = {"site_domain": getattr(settings, "SITE_DOMAIN", "")}
        html = render_to_string("email/test_email.html", context)
        message = EmailMultiAlternatives(
            subject="Test email",
            body=strip_tags(html),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        message.attach_alternative(html, "text/html")
        message.send()
        self.stdout.write(self.style.SUCCESS(f"Sent test email to {recipient}"))
