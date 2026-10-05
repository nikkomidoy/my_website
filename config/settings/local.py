from .base import *

if DEBUG:
    INSTALLED_APPS += ["silk"]
    # AFTER SecurityMiddleware, not before. Prepending at index 0 routes
    # the profiler around Django's security headers on every request.
    sec_idx = MIDDLEWARE.index("django.middleware.security.SecurityMiddleware")
    MIDDLEWARE.insert(sec_idx + 1, "silk.middleware.SilkyMiddleware")
    SILKY_MAX_RECORDED_REQUESTS = 1000
    SILKY_MAX_RECORDED_REQUESTS_CHECK_PERCENT = 10

if DEBUG:
    INSTALLED_APPS += ["django_browser_reload"]
    # Append last — it must run after any middleware that encodes the response
    # (e.g. GZipMiddleware); it injects the reload <script> before </body>.
    MIDDLEWARE += ["django_browser_reload.middleware.BrowserReloadMiddleware"]

if DEBUG:
    INSTALLED_APPS += ["zeal"]
    MIDDLEWARE += [
        "zeal.middleware.zeal_middleware",  # required to scope detection per request
        "core.middleware.zeal_skip_admin",  # must come after zeal_middleware
    ]
    ZEAL_RAISE_ON_VIOLATION = True
    # Wagtail routes URLs with one `.get()` per tree level — by design, not an N+1.
    ZEAL_ALLOWLIST = [{"model": "wagtailcore.Page", "field": "get*"}]

INSTALLED_APPS += ["django_extensions"]
