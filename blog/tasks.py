"""Daily blog automation: publish one post a day and share it to Facebook.

Order of preference on each run:
1. The next queued post whose `publish_at` has arrived (your own writing first).
2. Otherwise, if no AI draft is already waiting for review, ask Claude for one
   (saved as "Needs review" — approve it in Wagtail by setting the daily queue to Queued,
   or just hit Publish).
Also retries Facebook shares that failed in the last few days.
"""

from datetime import timedelta

import structlog
from crontask import cron
from django.conf import settings
from django.tasks import task
from django.utils import timezone

from .models import BlogPostPage
from .services import ai, publishing

log = structlog.get_logger(__name__)


@cron(settings.BLOG_DAILY_CRON)
@task()
def daily_blog() -> str:
    retried = retry_failed_shares()

    today = timezone.localdate()
    if BlogPostPage.objects.live().filter(first_published_at__date=today).exists():
        log.info("blog.daily.already_published_today")
        return f"skipped: already published today (retried {retried} shares)"

    post = BlogPostPage.objects.ready_to_publish().first()
    if post:
        publishing.publish(post)
        return f"published {post.slug}"

    if BlogPostPage.objects.awaiting_review().exists():
        log.info("blog.daily.waiting_for_review")
        return "queue empty; AI draft already awaiting review"

    if not ai.is_configured():
        log.info("blog.daily.queue_empty_no_ai")
        return "queue empty; AI fallback disabled"

    try:
        draft = ai.generate_draft()
    except ai.AIDraftError as exc:
        log.error("blog.daily.ai_failed", error=str(exc))
        raise

    if draft.queue_status == BlogPostPage.QueueStatus.QUEUED:  # BLOG_AI_AUTO_PUBLISH
        publishing.publish(draft)
        return f"AI post published {draft.slug}"
    publishing.notify_review_needed(draft)
    return f"AI draft {draft.pk} awaiting review"


def retry_failed_shares() -> int:
    cutoff = timezone.now() - timedelta(days=3)
    failed = (
        BlogPostPage.objects.live()
        .filter(share_to_facebook=True, facebook_post_id="", first_published_at__gte=cutoff)
        .exclude(facebook_error="")
    )
    return sum(publishing.share_to_facebook(p) for p in failed)
