from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.views.decorators.http import require_GET


def liveness(_request):
    """Process is alive. No external checks — must never block."""
    return HttpResponse("ok", content_type="text/plain")


def readiness(_request):
    """Process can serve traffic — DB reachable."""
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
    except OperationalError:
        return HttpResponse("db down", status=503, content_type="text/plain")
    return HttpResponse("ready", content_type="text/plain")


@require_GET
def robots_txt(_request):
    if settings.DEBUG or settings.ROBOTS_DISALLOW_ALL:
        body = "User-agent: *\nDisallow: /\n"
    else:
        body = (
            "User-agent: *\nDisallow: /admin/\nDisallow: /django-admin/\n"
            "Disallow: /accounts/\nAllow: /\n"
        )
        sitemap = getattr(settings, "SITEMAP_URL", None)
        if sitemap:
            body += f"\nSitemap: {sitemap}\n"
    return HttpResponse(body, content_type="text/plain")
