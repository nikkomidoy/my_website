import pytest


@pytest.mark.django_db
def test_smoke(client):
    assert client.get("/accounts/login/").status_code == 200
    assert client.get("/django-admin/").status_code == 302
