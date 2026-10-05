from django.conf import settings

ADMIN_PREFIXES = ("/admin/", "/django-admin/")


class AdminCSPMiddleware:
    """Swap in `SECURE_CSP_ADMIN` for the CMS and Django admin; public pages keep the strict policy."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(ADMIN_PREFIXES) and not hasattr(response, "_csp_config"):
            response._csp_config = settings.SECURE_CSP_ADMIN
        return response


def zeal_skip_admin(get_response):
    """Dev only: don't raise on N+1s inside Wagtail/Django admin internals."""
    from zeal import zeal_ignore

    def middleware(request):
        if request.path.startswith(ADMIN_PREFIXES):
            with zeal_ignore():
                return get_response(request)
        return get_response(request)

    return middleware
