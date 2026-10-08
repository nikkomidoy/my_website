from django.utils.csp import CSP

from .base import *

# MIDDLEWARE += [...]                      # order doesn't matter
# MIDDLEWARE.insert(1, "...")              # order matters (e.g. WhiteNoise after SecurityMiddleware)

ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# Configures the enrolled factors and issuer name; enrollment stays opt-in from
# the account page — allauth.mfa has no setting that forces MFA at login.
MFA_TOTP_ISSUER = env("DJANGO_SITE_DOMAIN", default="example.com")
MFA_SUPPORTED_TYPES = ["totp", "recovery_codes"]
ACCOUNT_REAUTHENTICATION_REQUIRED = True

if AWS_STORAGE_BUCKET_NAME:
    STORAGES = {
        **STORAGES,
        "staticfiles": {
            "BACKEND": "storages.backends.s3boto3.S3StaticStorage",
            # collectstatic must replace changed CSS/JS in place, not add suffixed copies.
            "OPTIONS": {"location": "static", "file_overwrite": True},
        },
    }

    if AWS_S3_CUSTOM_DOMAIN:
        STATIC_URL = f"{AWS_S3_URL_PROTOCOL}//{AWS_S3_CUSTOM_DOMAIN}/static/"
    elif AWS_S3_ENDPOINT_URL:
        # Non-AWS provider without a custom domain: serve from the endpoint host.
        STATIC_URL = f"{AWS_S3_ENDPOINT_URL.rstrip('/')}/{AWS_STORAGE_BUCKET_NAME}/static/"
    else:
        # AWS without CloudFront — bucket vhost. us-east-1 omits the region.
        _region = "" if AWS_S3_REGION_NAME == "us-east-1" else f".{AWS_S3_REGION_NAME}"
        STATIC_URL = f"https://{AWS_STORAGE_BUCKET_NAME}.s3{_region}.amazonaws.com/static/"

# HTTPS — env-toggle so smoke / staging / direct-gunicorn access can run
# without TLS. Hardcoding True returns 301 on every plain-HTTP probe.
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
# Exempt healthcheck endpoints — internal probes hit the container directly
# without traversing the TLS proxy.
SECURE_REDIRECT_EXEMPT = [r"^healthz$", r"^readyz$"]

# X-Forwarded-Proto trust. ONLY enable when there's a TLS-terminating proxy
# (Caddy / nginx / ALB) in front of gunicorn. Without one, any client on the
# open port can spoof X-Forwarded-Proto: https.
if env.bool("DJANGO_BEHIND_PROXY", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Cookies
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HSTS
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False  # opt in only after every subdomain serves HTTPS
SECURE_HSTS_PRELOAD = False  # opt in only after manual review of the consequences

# These two are deliberate opt-outs above, so silence the matching
# `manage.py check --deploy` warnings.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

# Other browser hardening
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CONTENT_TYPE_NOSNIFF = True  # Django default but worth being explicit

# Required behind a TLS-terminating proxy whenever Django sees the request
# as HTTP. Without it, admin / allauth POSTs return 403 with "Origin checking failed".
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Content Security Policy — Django 6.1 built-in
MIDDLEWARE = [*MIDDLEWARE, "django.middleware.csp.ContentSecurityPolicyMiddleware"]

SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.UNSAFE_INLINE],  # Admin needs inline styles.
    "img-src": [CSP.SELF, "data:"],
    "font-src": [CSP.SELF],
    "connect-src": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
}
TEMPLATES[0]["OPTIONS"]["context_processors"] += [
    "django.template.context_processors.csp",
]

# storage-s3: static + media are served from the bucket / CDN host.
if AWS_STORAGE_BUCKET_NAME:
    from urllib.parse import urlsplit

    _ASSET_HOSTS = sorted(
        {
            f"{urlsplit(u).scheme}://{urlsplit(u).netloc}"
            for u in (STATIC_URL, MEDIA_URL)
            if "://" in u
        }
    )
    for _directive in ("script-src", "style-src", "img-src", "font-src"):
        SECURE_CSP[_directive] += _ASSET_HOSTS

# analytics-goatcounter
SECURE_CSP["script-src"] += ["https://gc.zgo.at"]
if ANALYTICS_HOST:
    SECURE_CSP["connect-src"] += [ANALYTICS_HOST]
    SECURE_CSP["img-src"] += [ANALYTICS_HOST]

# Wagtail / Django admin still render a few inline <script> tags (InlinePanel, date
# pickers) and the live preview runs in a same-origin iframe. Relax the policy for the
# admin paths only — core.middleware.AdminCSPMiddleware attaches it to those responses.
SECURE_CSP_ADMIN = {
    **SECURE_CSP,
    "script-src": [s for s in SECURE_CSP["script-src"] if s != CSP.NONCE] + [CSP.UNSAFE_INLINE],
    "img-src": [*SECURE_CSP["img-src"], "blob:"],
    "frame-src": [CSP.SELF],
    "frame-ancestors": [CSP.SELF],
}
# Must come after ContentSecurityPolicyMiddleware so it runs first on the response.
MIDDLEWARE = [*MIDDLEWARE, "core.middleware.AdminCSPMiddleware"]

# Error reporting — Sentry (server-side only; no browser SDK, so no CSP entry)
SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    # GDPR: strip credentials/cookies before events leave the box.
    def _scrub(event, hint):
        request = event.get("request") or {}
        headers = request.get("headers") or {}
        for h in ("Authorization", "Cookie"):
            headers.pop(h, None)
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        release=env("SENTRY_RELEASE", default=None),
        send_default_pii=False,
        before_send=_scrub,
        # traces_sample_rate=0.1,  # tracing — Sentry SaaS / GlitchTip only
    )

# Database backups — django-dbbackup 5.x (STORAGES["dbbackup"]; the old
# DBBACKUP_STORAGE* settings raise). Gated on `not DEBUG` so the image build
# (DJANGO_DEBUG=True) never evaluates the required env vars.
if not DEBUG:
    INSTALLED_APPS += ["dbbackup"]

    STORAGES = {
        **STORAGES,
        "dbbackup": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {
                # None → instance role (see base.py)
                "access_key": AWS_ACCESS_KEY_ID,
                "secret_key": AWS_SECRET_ACCESS_KEY,
                "bucket_name": env("DBBACKUP_BUCKET"),  # SEPARATE bucket from media
                "region_name": AWS_S3_REGION_NAME,
                "default_acl": "private",
                "querystring_auth": True,
            },
        },
    }

    DBBACKUP_CLEANUP_KEEP = 14  # daily backups retained
    DBBACKUP_FILENAME_TEMPLATE = "{databasename}-{servername}-{datetime}.{extension}"
