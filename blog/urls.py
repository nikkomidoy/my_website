"""Wagtail admin URLs for the blog, mounted under /admin/blog/ by wagtail_hooks.py."""

from django.urls import path

from . import views

app_name = "blog_admin"

urlpatterns = [
    path("draft-with-ai/", views.draft_with_ai, name="draft_with_ai"),
    path("posts/<int:page_id>/share/", views.share_to_facebook, name="share_to_facebook"),
]
