"""Draft a blog post with Claude when the publish queue is empty.

Drafts are saved as `needs_review` by default so nothing AI-written reaches the
site or Facebook until a human approves it (set BLOG_AI_AUTO_PUBLISH=True to skip).
"""

import anthropic
import structlog
from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, Field

from core.models import HomePage

from ..models import BlogIndexPage, BlogPostPage, TopicIdea

log = structlog.get_logger(__name__)


class PostDraft(BaseModel):
    title: str = Field(description="Specific, non-clickbait title, under 90 characters.")
    excerpt: str = Field(description="One or two sentence summary, under 280 characters.")
    body_markdown: str = Field(
        description="The article in Markdown, 700-1200 words, using ## subheadings. "
        "No top-level # title."
    )
    tags: list[str] = Field(description="3-5 short lowercase topic tags.")
    facebook_message: str = Field(
        description="2-3 sentence Facebook post teasing the article, plain text, no hashtags spam "
        "(max 2), no link (it is attached separately)."
    )


class AIDraftError(Exception):
    pass


SYSTEM_PROMPT = """You write blog posts for a software engineer's personal website, in their voice.

Write like a practitioner sharing hard-won experience with other engineers: concrete,
specific and practical. Prefer real-world examples, trade-offs and short code snippets
over generic advice. No hype, no filler intros, no "In today's fast-paced world".

Never invent employers, clients, metrics, incidents or credentials that are not in the
author profile. When drawing on experience, stay at the level of detail the profile
supports. Never include personal data about third parties."""


def is_configured() -> bool:
    return bool(settings.BLOG_AI_FALLBACK_ENABLED and settings.ANTHROPIC_API_KEY)


def _author_context() -> str:
    home = HomePage.current()
    if not home:
        return ""
    lines = [f"Name: {home.name}", f"Headline: {home.headline}", home.summary]
    for exp in home.experiences.all()[:6]:
        lines.append(f"- {exp.role} at {exp.company}: {exp.summary}")
    for group in home.skill_groups.all():
        lines.append(f"Skills ({group.name}): {group.skills}")
    return "\n".join(lines)


def generate_draft() -> BlogPostPage:
    """Ask Claude for a post on the next unused topic and save it as an unpublished page."""
    if not is_configured():
        raise AIDraftError("AI drafting disabled or ANTHROPIC_API_KEY missing")
    index = BlogIndexPage.objects.first()
    if index is None:
        raise AIDraftError("no blog index page to file the draft under")

    topic = TopicIdea.objects.first()  # unused topics sort first
    recent_titles = list(BlogPostPage.objects.order_by("-pk").values_list("title", flat=True)[:30])

    topic_text = (
        f"Topic: {topic.topic}\nNotes: {topic.notes or '-'}"
        if topic
        else "Topic: pick a useful, specific topic grounded in the author's skills."
    )
    user_prompt = (
        f"<author_profile>\n{_author_context()}\n</author_profile>\n\n"
        f"<recent_titles>\n" + "\n".join(recent_titles) + "\n</recent_titles>\n\n"
        f"{topic_text}\n\n"
        "Write one new blog post. Do not repeat or closely paraphrase any recent title."
    )

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    try:
        response = client.beta.messages.parse(
            model=settings.BLOG_AI_MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            output_format=PostDraft,
            output_config={"effort": "high"},
            # Re-run a safety-classifier decline on Anthropic's recommended fallback model.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.APIStatusError as exc:
        raise AIDraftError(f"Anthropic API error {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise AIDraftError(f"Anthropic connection error: {exc}") from exc

    if response.stop_reason == "refusal":
        raise AIDraftError("model declined to write this topic")
    if response.stop_reason == "max_tokens" or response.parsed_output is None:
        raise AIDraftError(f"incomplete draft (stop_reason={response.stop_reason})")

    draft = response.parsed_output
    status = (
        BlogPostPage.QueueStatus.QUEUED
        if settings.BLOG_AI_AUTO_PUBLISH
        else BlogPostPage.QueueStatus.NEEDS_REVIEW
    )
    post = BlogPostPage(
        title=draft.title[:200],
        excerpt=draft.excerpt[:300],
        body=[("markdown", draft.body_markdown)],
        facebook_message=draft.facebook_message,
        queue_status=status,
        source=BlogPostPage.Source.AI,
        live=False,
    )
    post.tags.add(*(t.strip().lower() for t in draft.tags[:5]))
    index.add_child(instance=post)
    post.save_revision(log_action=True)
    if topic:
        topic.used_at = timezone.now()
        topic.save(update_fields=["used_at"])
    log.info(
        "blog.ai_draft_created", post_id=post.pk, status=status, request_id=response._request_id
    )
    return post
