from django.apps import AppConfig
from django.db.models.signals import post_migrate


def sync_site_domain(sender, **kwargs) -> None:
    """Keep the Sites framework and Wagtail's default Site in step with DJANGO_SITE_DOMAIN.

    django.contrib.sites feeds allauth emails; Wagtail's Site drives absolute page URLs
    (sitemap, `get_full_url`).
    """
    from django.conf import settings
    from django.contrib.sites.models import Site
    from wagtail.models import Site as WagtailSite

    Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={"domain": settings.SITE_DOMAIN, "name": settings.SITE_DOMAIN},
    )
    hostname, _, port = settings.SITE_DOMAIN.partition(":")
    WagtailSite.objects.filter(is_default_site=True).update(
        hostname=hostname,
        port=int(port) if port else (80 if settings.DEBUG else 443),
        site_name=settings.WAGTAIL_SITE_NAME,
    )


class CoreConfig(AppConfig):
    name = "core"

    def ready(self) -> None:
        from . import tasks  # noqa: F401  — register @task / @cron functions

        post_migrate.connect(sync_site_domain, sender=self)
