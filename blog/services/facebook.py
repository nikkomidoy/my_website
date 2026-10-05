"""Share blog posts to a Facebook Page via the Graph API.

Facebook only allows API posting to Pages (not personal profiles). Needs a
long-lived Page access token with `pages_manage_posts` + `pages_read_engagement`.
"""

import hashlib
import hmac

import requests
import structlog
from django.conf import settings

log = structlog.get_logger(__name__)

GRAPH_URL = "https://graph.facebook.com"
TIMEOUT = 15


class FacebookError(Exception):
    pass


def is_configured() -> bool:
    return bool(settings.FACEBOOK_PAGE_ID and settings.FACEBOOK_PAGE_ACCESS_TOKEN)


def _appsecret_proof(token: str) -> str | None:
    # Recommended by Meta: proves calls come from a server holding the app secret.
    if not settings.FACEBOOK_APP_SECRET:
        return None
    return hmac.new(
        settings.FACEBOOK_APP_SECRET.encode(), token.encode(), hashlib.sha256
    ).hexdigest()


def publish_link(message: str, link: str) -> str:
    """Create a Page feed post with a link preview. Returns the Facebook post id."""
    if not is_configured():
        raise FacebookError("FACEBOOK_PAGE_ID / FACEBOOK_PAGE_ACCESS_TOKEN not set")

    token = settings.FACEBOOK_PAGE_ACCESS_TOKEN
    data = {"message": message, "link": link, "access_token": token}
    if proof := _appsecret_proof(token):
        data["appsecret_proof"] = proof

    url = f"{GRAPH_URL}/{settings.FACEBOOK_GRAPH_VERSION}/{settings.FACEBOOK_PAGE_ID}/feed"
    try:
        resp = requests.post(url, data=data, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise FacebookError(f"network error: {exc}") from exc

    payload = (
        resp.json()
        if resp.headers.get("content-type", "").startswith(("application/json", "text/javascript"))
        else {}
    )
    if resp.status_code != 200 or "id" not in payload:
        err = payload.get("error", {}) if isinstance(payload, dict) else {}
        # Never log the token — only Graph's error fields.
        raise FacebookError(
            f"HTTP {resp.status_code}: {err.get('type', '')} {err.get('code', '')} "
            f"{err.get('message', resp.text[:200])}".strip()
        )
    log.info("facebook.shared", post_id=payload["id"])
    return payload["id"]
