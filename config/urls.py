from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.contrib.sitemaps.views import sitemap
from wagtail.documents import urls as wagtaildocs_urls

from api.urls import router
from config.sitemaps import sitemaps

# Both admin logins go through allauth so MFA and axes always apply.
login_redirect = RedirectView.as_view(pattern_name="account_login", query_string=True)

urlpatterns = [
    path("admin/login/", login_redirect),
    path("admin/", include(wagtailadmin_urls)),
    path("django-admin/login/", login_redirect),
    path("django-admin/", admin.site.urls),
    path("documents/", include(wagtaildocs_urls)),
    path("accounts/", include("allauth.urls")),
    path(router.prefix, include((router.urls, "api"), namespace="api")),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("", include("core.urls")),
]

# Gate dev-only apps on INSTALLED_APPS, not DEBUG: production settings never list them,
# and the prod image is built with `uv sync --no-dev`.
if "silk" in settings.INSTALLED_APPS:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]

if "django_browser_reload" in settings.INSTALLED_APPS:
    urlpatterns += [path("__reload__/", include("django_browser_reload.urls"))]

if settings.DEBUG and not settings.AWS_STORAGE_BUCKET_NAME:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Wagtail's page tree catches everything else — keep it last.
urlpatterns += [path("", include(wagtail_urls))]
