from datetime import timedelta

import pytest
from axes.models import AccessAttempt
from django.core.management import call_command
from django.utils import timezone

from core.models import Experience, HomePage
from core.tasks import purge_login_records


@pytest.mark.django_db
def test_home_renders_seeded_resume(client):
    assert HomePage.objects.live().count() == 1
    assert Experience.objects.count() == 6
    html = client.get("/").text
    assert "Nikko Comidoy" in html and "Prezzee" in html


@pytest.mark.django_db
def test_phone_hidden_unless_enabled(client):
    HomePage.objects.update(phone="555-0100")
    assert "555-0100" not in client.get("/").text  # show_phone is off by default
    HomePage.objects.update(show_phone=True)
    assert "555-0100" in client.get("/").text


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    [
        "/",
        "/blog/",
        "/privacy/",
        "/blog/feed/",
        "/blog/hello-world/",
        "/sitemap.xml",
        "/robots.txt",
        "/healthz",
        "/readyz",
        "/api/posts/",
    ],
)
def test_public_urls(client, url):
    assert client.get(url).status_code == 200


@pytest.mark.django_db
def test_nav_footer_and_sitemap(client):
    html = client.get("/").text
    assert 'href="/blog/"' in html and 'href="/privacy/"' in html and 'href="/blog/feed/"' in html
    sitemap = client.get("/sitemap.xml").text
    assert "/blog/hello-world/" in sitemap and "/privacy/" in sitemap


@pytest.mark.django_db
@pytest.mark.parametrize("url", ["/admin/login/", "/django-admin/login/"])
def test_admin_logins_go_through_allauth(client, url):
    response = client.get(url + "?next=/admin/")
    assert response.status_code == 302
    assert response.url == "/accounts/login/?next=/admin/"


@pytest.mark.django_db
def test_wagtail_admin_requires_login(client):
    response = client.get("/admin/")
    assert response.status_code == 302 and response.url.startswith("/accounts/login/")


@pytest.mark.django_db
def test_wagtail_admin_edit_views_render(admin_client):
    home = HomePage.objects.get()
    assert admin_client.get("/admin/").status_code == 200
    assert admin_client.get(f"/admin/pages/{home.pk}/edit/").status_code == 200
    assert admin_client.get(f"/admin/pages/add/core/contentpage/{home.pk}/").status_code == 200


@pytest.mark.django_db
def test_robots_disallow_all_toggle(client, settings):
    settings.ROBOTS_DISALLOW_ALL = True
    assert "Disallow: /\n" in client.get("/robots.txt").text


@pytest.mark.django_db
def test_purge_login_records(settings):
    settings.PRIVACY_LOGIN_ATTEMPT_RETENTION_DAYS = 30
    old = AccessAttempt.objects.create(username="x", ip_address="1.2.3.4", failures_since_start=1)
    AccessAttempt.objects.filter(pk=old.pk).update(attempt_time=timezone.now() - timedelta(days=31))
    AccessAttempt.objects.create(username="y", ip_address="1.2.3.5", failures_since_start=1)
    assert purge_login_records.call() == 1
    assert AccessAttempt.objects.get().username == "y"


@pytest.mark.django_db
def test_gdpr_export_and_delete(django_user_model, capsys):
    user = django_user_model.objects.create_user("jane", "jane@example.com", "pw")
    call_command("export_user_data", user.pk)
    out = capsys.readouterr().out
    assert "jane@example.com" in out and "pbkdf2" not in out and '"password"' not in out
    call_command("delete_user_data", user.pk)
    assert not django_user_model.objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_send_test_email(mailoutbox):
    call_command("send_test_email", "a@example.com")
    assert mailoutbox[0].to == ["a@example.com"]


@pytest.mark.parametrize(("path", "relaxed"), [("/admin/pages/", True), ("/blog/", False)])
def test_admin_csp_override(rf, settings, path, relaxed):
    from django.http import HttpResponse

    from core.middleware import AdminCSPMiddleware

    settings.SECURE_CSP_ADMIN = {"script-src": ["'unsafe-inline'"]}
    response = AdminCSPMiddleware(lambda request: HttpResponse())(rf.get(path))
    assert (getattr(response, "_csp_config", None) == settings.SECURE_CSP_ADMIN) is relaxed
