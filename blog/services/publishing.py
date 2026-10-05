import structlog
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags

from ..models import BlogPostPage
from . import facebook

log = structlog.get_logger(__name__)


def absolute_url(path: str) -> str:
    scheme = "http" if settings.DEBUG else "https"
    return f"{scheme}://{settings.SITE_DOMAIN}{path}"


def publish(post: BlogPostPage) -> BlogPostPage:
    """Publish the latest revision. The `page_published` receiver shares it to Facebook."""
    revision = post.get_latest_revision() or post.save_revision()
    revision.publish()
    post.refresh_from_db()
    log.info("blog.published", post_id=post.pk, slug=post.slug)
    return post


def share_to_facebook(post: BlogPostPage) -> bool:
    """Share a live post to the Facebook Page. Records the outcome on the post."""
    if post.facebook_post_id or not post.live:
        return bool(post.facebook_post_id)
    if not facebook.is_configured():
        log.info("facebook.skipped_not_configured", post_id=post.pk)
        return False
    try:
        post.facebook_post_id = facebook.publish_link(
            message=post.facebook_message or post.excerpt,
            link=absolute_url(post.get_url() or post.url_path),
        )
        post.facebook_shared_at = timezone.now()
        post.facebook_error = ""
        ok = True
    except facebook.FacebookError as exc:
        post.facebook_error = str(exc)[:2000]
        log.warning("facebook.share_failed", post_id=post.pk, error=post.facebook_error)
        ok = False
    # Row-only update: share state lives outside revisions (BlogPostPage.SHARE_STATE_FIELDS).
    BlogPostPage.objects.filter(pk=post.pk).update(
        **{field: getattr(post, field) for field in BlogPostPage.SHARE_STATE_FIELDS}
    )
    return ok


def notify_review_needed(post: BlogPostPage) -> None:
    """Email ADMINS that an AI draft is waiting for approval."""
    recipients = [address for _name, address in settings.ADMINS]
    if not recipients:
        return
    context = {
        "post": post,
        "admin_url": absolute_url(reverse("wagtailadmin_pages:edit", args=[post.pk])),
        "site_domain": settings.SITE_DOMAIN,
    }
    html = render_to_string("email/blog_review.html", context)
    message = EmailMultiAlternatives(
        subject=f"New AI blog draft to review: {post.title}",
        body=strip_tags(html),
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html, "text/html")
    message.send()
