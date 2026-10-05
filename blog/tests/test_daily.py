from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from blog import tasks
from blog.models import BlogPostPage, TopicIdea
from blog.services import ai, facebook


@pytest.fixture
def fb_configured(settings):
    settings.FACEBOOK_PAGE_ID = "123"
    settings.FACEBOOK_PAGE_ACCESS_TOKEN = "page-token"
    settings.FACEBOOK_APP_SECRET = "app-secret"
    settings.SITE_DOMAIN = "example.com"


@pytest.fixture(autouse=True)
def clean_posts(db):
    BlogPostPage.objects.all().delete()  # drop the seeded welcome post


Queue = BlogPostPage.QueueStatus


def test_publishes_next_queued_post_and_shares(fb_configured, make_post):
    later = make_post(title="Later", publish_after=timezone.now() + timedelta(days=2))
    first = make_post(title="First")
    with mock.patch.object(facebook, "publish_link", return_value="123_456") as share:
        result = tasks.daily_blog.call()

    first.refresh_from_db()
    later.refresh_from_db()
    assert result == f"published {first.slug}"
    assert first.live and first.first_published_at
    assert first.facebook_post_id == "123_456"
    assert not later.live
    share.assert_called_once_with(message="Excerpt", link=f"https://example.com/blog/{first.slug}/")


def test_only_one_post_per_day(fb_configured, make_post):
    make_post(share_to_facebook=False, publish=True)
    queued = make_post(title="Tomorrow")
    result = tasks.daily_blog.call()
    queued.refresh_from_db()
    assert result.startswith("skipped")
    assert not queued.live


def test_facebook_failure_is_recorded_and_retried(fb_configured, make_post):
    post = make_post()
    with mock.patch.object(facebook, "publish_link", side_effect=facebook.FacebookError("boom")):
        tasks.daily_blog.call()
    post.refresh_from_db()
    assert post.live
    assert post.facebook_error == "boom" and not post.facebook_post_id

    with mock.patch.object(facebook, "publish_link", return_value="1_2"):
        assert tasks.retry_failed_shares() == 1
    post.refresh_from_db()
    assert post.facebook_post_id == "1_2" and post.facebook_error == ""


def test_republishing_never_reshares(fb_configured, make_post):
    with mock.patch.object(facebook, "publish_link", return_value="9_9") as share:
        post = make_post(publish=True)
        post.title = "Edited"
        post.save_revision().publish()
    post.refresh_from_db()
    share.assert_called_once()
    assert post.title == "Edited" and post.facebook_post_id == "9_9"


def test_empty_queue_drafts_with_ai_for_review(settings, mailoutbox, make_post):
    settings.ANTHROPIC_API_KEY = "test"
    settings.ADMINS = [("me", "me@example.com")]
    draft = make_post(queue_status=Queue.DRAFT, source=BlogPostPage.Source.AI)

    def fake_generate():
        draft.queue_status = Queue.NEEDS_REVIEW
        draft.save()
        return draft

    with mock.patch.object(ai, "generate_draft", side_effect=fake_generate):
        result = tasks.daily_blog.call()
    assert "awaiting review" in result
    assert len(mailoutbox) == 1 and draft.title in mailoutbox[0].subject
    assert f"/admin/pages/{draft.pk}/edit/" in mailoutbox[0].alternatives[0].content


def test_waits_while_ai_draft_awaits_review(settings, make_post):
    settings.ANTHROPIC_API_KEY = "test"
    make_post(queue_status=Queue.NEEDS_REVIEW)
    with mock.patch.object(ai, "generate_draft") as gen:
        result = tasks.daily_blog.call()
    gen.assert_not_called()
    assert "awaiting review" in result


def test_ai_disabled_without_key(settings):
    settings.ANTHROPIC_API_KEY = ""
    assert tasks.daily_blog.call() == "queue empty; AI fallback disabled"


def test_generate_draft_saves_needs_review(settings):
    settings.ANTHROPIC_API_KEY = "test"
    settings.BLOG_AI_AUTO_PUBLISH = False
    response = mock.Mock(
        stop_reason="end_turn",
        _request_id="req_1",
        parsed_output=ai.PostDraft(
            title="Tracing bugs",
            excerpt="How to trace.",
            body_markdown="## Hi\n\nText",
            tags=["Python", "Debugging"],
            facebook_message="New post!",
        ),
    )
    with mock.patch("anthropic.Anthropic") as client_cls:
        client_cls.return_value.beta.messages.parse.return_value = response
        post = ai.generate_draft()

    kwargs = client_cls.return_value.beta.messages.parse.call_args.kwargs
    assert kwargs["model"] == settings.BLOG_AI_MODEL
    assert kwargs["output_format"] is ai.PostDraft
    post.refresh_from_db()
    assert post.queue_status == Queue.NEEDS_REVIEW and post.source == BlogPostPage.Source.AI
    assert not post.live and post.get_latest_revision() is not None
    assert sorted(post.tag_list) == ["debugging", "python"]
    assert post.body[0].block_type == "markdown"
    assert TopicIdea.objects.filter(used_at__isnull=False).count() == 1


def test_generate_draft_handles_refusal(settings):
    settings.ANTHROPIC_API_KEY = "test"
    response = mock.Mock(stop_reason="refusal", parsed_output=None)
    with mock.patch("anthropic.Anthropic") as client_cls:
        client_cls.return_value.beta.messages.parse.return_value = response
        with pytest.raises(ai.AIDraftError):
            ai.generate_draft()
