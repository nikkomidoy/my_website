from django.contrib import messages
from django.contrib.syndication.views import Feed
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import reverse

from core.models import HomePage

from .models import BlogIndexPage, BlogPostPage
from .services import ai, publishing


class LatestPostsFeed(Feed):
    description = "Latest blog posts."

    def __init__(self, index: BlogIndexPage):
        super().__init__()
        self.index = index

    def title(self):
        home = HomePage.current()
        return f"{home.name} — Blog" if home else "Blog"

    def link(self):
        return self.index.url

    def items(self):
        return BlogPostPage.objects.published().descendant_of(self.index)[:20]

    def item_title(self, item: BlogPostPage):
        return item.title

    def item_description(self, item: BlogPostPage):
        return item.excerpt

    def item_link(self, item: BlogPostPage):
        return item.url

    def item_pubdate(self, item: BlogPostPage):
        return item.first_published_at


# --- Wagtail admin views (registered in wagtail_hooks.py under /admin/blog/) ---


def draft_with_ai(request):
    """Confirm, then ask Claude for a draft on the next unused topic."""
    if not request.user.has_perm("blog.add_blogpostpage"):
        raise PermissionDenied
    if request.method == "POST":
        try:
            post = ai.generate_draft()
        except ai.AIDraftError as exc:
            messages.error(request, f"Draft failed: {exc}")
            return redirect("wagtailsnippets_blog_topicidea:list")
        messages.success(
            request,
            f"Drafted “{post.title}” — {BlogPostPage.QueueStatus(post.queue_status).label.lower()}.",
        )
        return redirect("wagtailadmin_pages:edit", post.pk)
    return TemplateResponse(
        request,
        "blog/admin/confirm.html",
        {
            "title": "Draft a post with Claude",
            "message": "Claude will write a draft about the next unused topic. "
            "It is saved as “Needs review” — nothing goes live until you approve it.",
            "submit_label": "Draft now",
            "cancel_url": reverse("wagtailsnippets_blog_topicidea:list"),
        },
    )


def share_to_facebook(request, page_id: int):
    """Confirm, then (re)try sharing a live post to the Facebook Page."""
    post = get_object_or_404(BlogPostPage, pk=page_id)
    if not post.permissions_for_user(request.user).can_publish():
        raise PermissionDenied
    edit_url = reverse("wagtailadmin_pages:edit", args=[post.pk])
    if request.method == "POST":
        if publishing.share_to_facebook(post):
            messages.success(request, f"Shared “{post.title}” to Facebook.")
        else:
            messages.warning(
                request,
                f"Not shared: {post.facebook_error or 'post not live or Facebook not configured'}.",
            )
        return redirect(edit_url)
    return TemplateResponse(
        request,
        "blog/admin/confirm.html",
        {
            "title": f"Share “{post.title}” to Facebook",
            "message": "Posts a link to the live page on the Facebook Page.",
            "submit_label": "Share now",
            "cancel_url": edit_url,
        },
    )
