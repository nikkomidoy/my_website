import pytest
from storages.backends.s3 import S3Storage


@pytest.fixture
def fake_aws_credentials(monkeypatch):
    # boto3 needs *some* credentials to build a client; no request is ever sent.
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")


def test_optional_s3_settings_are_none_not_empty(settings):
    # "" makes boto3 fail ("Invalid endpoint", blank credentials); None means "use the default".
    for name in ("AWS_S3_ENDPOINT_URL", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        assert getattr(settings, name) != "", name


@pytest.mark.usefixtures("fake_aws_credentials")
def test_s3_client_builds_from_project_settings():
    storage = S3Storage(bucket_name="example-bucket", region_name="us-east-2")
    meta = storage.connection.meta
    assert meta is not None
    assert meta.client.meta.region_name == "us-east-2"


@pytest.mark.usefixtures("fake_aws_credentials")
def test_empty_endpoint_reproduces_deploy_failure(settings):
    settings.AWS_S3_ENDPOINT_URL = ""
    storage = S3Storage(bucket_name="example-bucket", region_name="us-east-2")
    with pytest.raises(ValueError, match="Invalid endpoint"):
        _ = storage.connection


def test_s3_file_urls_match_csp_allowlist(monkeypatch):
    """Production settings: storage URLs must use a host the CSP allows (deploy regression)."""
    import importlib
    import sys
    from urllib.parse import urlsplit

    for key, value in {
        "DJANGO_DEBUG": "False",
        "DJANGO_SECRET_KEY": "test-secret-key-not-real-0123456789-abcdefghijklmnopqrstuvwxyz",
        "DJANGO_SITE_DOMAIN": "example.com",
        "DJANGO_MAIL_HOST": "localhost",
        "DEFAULT_FROM_EMAIL": "t@example.com",
        "DATABASE_URL": "sqlite:////tmp/unused.sqlite3",
        "AWS_STORAGE_BUCKET_NAME": "example-assets",
        "AWS_S3_REGION_NAME": "us-east-2",
        "AWS_S3_CUSTOM_DOMAIN": "",
        "AWS_S3_ENDPOINT_URL": "",
        "DBBACKUP_BUCKET": "example-backups",
    }.items():
        monkeypatch.setenv(key, value)
    for name in [m for m in sys.modules if m.startswith("config.settings")]:
        monkeypatch.delitem(sys.modules, name)
    prod = importlib.import_module("config.settings.production")

    expected = "https://example-assets.s3.us-east-2.amazonaws.com"
    assert prod.AWS_S3_CUSTOM_DOMAIN == "example-assets.s3.us-east-2.amazonaws.com"
    for url in (prod.STATIC_URL, prod.MEDIA_URL):
        host = f"{urlsplit(url).scheme}://{urlsplit(url).netloc}"
        assert host == expected
    for directive in ("style-src", "img-src", "font-src", "script-src"):
        assert expected in prod.SECURE_CSP[directive], directive
