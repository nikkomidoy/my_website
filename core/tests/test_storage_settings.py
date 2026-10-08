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
