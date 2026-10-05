from django.conf import settings


def analytics(request):
    return {
        "ANALYTICS_ID": settings.ANALYTICS_ID,
        "ANALYTICS_HOST": settings.ANALYTICS_HOST,
        "DEBUG": settings.DEBUG,
    }
