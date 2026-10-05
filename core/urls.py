"""Non-CMS endpoints. Everything else is served by Wagtail's page tree (config/urls.py)."""

from django.urls import path

from . import views

urlpatterns = [
    path("robots.txt", views.robots_txt, name="robots"),
    path("healthz", views.liveness, name="healthz"),
    path("readyz", views.readiness, name="readyz"),
]
