import hashlib
import hmac
from unittest import mock

import pytest

from blog.services import facebook


@pytest.fixture(autouse=True)
def fb(settings):
    settings.FACEBOOK_PAGE_ID = "42"
    settings.FACEBOOK_PAGE_ACCESS_TOKEN = "tok"
    settings.FACEBOOK_APP_SECRET = "sec"
    settings.FACEBOOK_GRAPH_VERSION = "v23.0"


def _resp(status, payload):
    r = mock.Mock(status_code=status, text=str(payload))
    r.headers = {"content-type": "application/json"}
    r.json.return_value = payload
    return r


def test_publish_link_posts_to_page_feed_with_proof():
    with mock.patch("requests.post", return_value=_resp(200, {"id": "42_1"})) as post:
        assert facebook.publish_link("hi", "https://x.test/a/") == "42_1"
    url = post.call_args.args[0]
    data = post.call_args.kwargs["data"]
    assert url == "https://graph.facebook.com/v23.0/42/feed"
    assert data["link"] == "https://x.test/a/"
    assert data["appsecret_proof"] == hmac.new(b"sec", b"tok", hashlib.sha256).hexdigest()


def test_publish_link_raises_with_graph_error_and_no_token():
    err = {"error": {"type": "OAuthException", "code": 190, "message": "expired"}}
    with (
        mock.patch("requests.post", return_value=_resp(400, err)),
        pytest.raises(facebook.FacebookError) as exc,
    ):
        facebook.publish_link("hi", "https://x.test/")
    assert "expired" in str(exc.value) and "tok" not in str(exc.value)


def test_not_configured(settings):
    settings.FACEBOOK_PAGE_ACCESS_TOKEN = ""
    assert not facebook.is_configured()
    with pytest.raises(facebook.FacebookError):
        facebook.publish_link("hi", "https://x.test/")
