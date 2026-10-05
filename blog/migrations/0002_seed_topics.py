"""Starter topics for the Claude fallback, plus the blog index page and a welcome post."""

import json
import uuid

from django.db import migrations
from django.utils import timezone

TOPICS = [
    ("Tracing a bug across services: a practical playbook", "APIs, logs, data and integrations; from symptom to root cause."),
    ("Automating large data requests with Python without hurting production", "Batching, read replicas, idempotency, delivering results."),
    ("What production incidents taught me about writing Django code", "Preventative fixes, observability, safer defaults."),
    ("Celery tasks that don't wake you up at night", "Retries, idempotency, timeouts, visibility."),
    ("REST vs GraphQL in a real Django codebase", "When each fit, trade-offs seen while maintaining both."),
    ("Data validation at the edges: keeping bad data out of your services", "Schemas, normalisation, error reporting."),
    ("Using Sentry and Datadog together to prioritise fixes", "Signal vs noise, linking errors to releases."),
    ("Turning recurring support tickets into code fixes", "Working with Product, measuring impact."),
    ("Redis in Django apps: caching, locks and rate limits", "Patterns and pitfalls."),
    ("Post-release troubleshooting checklist for backend engineers", "What to watch in the first hour after a deploy."),
    ("From startup client work to a global platform: lessons in maintainability", "Career reflections, code that lasts."),
    ("Writing third-party API integrations that fail gracefully", "Timeouts, retries, circuit breakers, observability."),
]

WELCOME = """I've spent 11+ years building and maintaining web applications — most recently five \
years on Prezzee's global platform — working mostly in Python and Django.

This blog is where I'll write about the practical side of that work:

- tracing issues across APIs, data and integrations
- automating the repetitive parts of operations work
- keeping Django services healthy in production

New posts go up regularly and are shared to my Facebook page. You can also follow along via \
[RSS](/blog/feed/).
"""



BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def next_child_path(Page, parent) -> str:
    """Treebeard materialised path for a new last child (steplen 4, base 36)."""
    last = (
        Page.objects.filter(path__startswith=parent.path, depth=parent.depth + 1)
        .order_by("-path")
        .values_list("path", flat=True)
        .first()
    )
    n = int(last[-4:], 36) + 1 if last else 1
    step = ""
    while n:
        n, r = divmod(n, 36)
        step = BASE36[r] + step
    return parent.path + step.rjust(4, "0")


def page_fields(apps, model: str, parent, *, title: str, slug: str, **extra):
    Page = apps.get_model("wagtailcore", "Page")
    ContentType = apps.get_model("contenttypes", "ContentType")
    app_label, model_name = model.split(".")
    path = next_child_path(Page, parent)
    now = timezone.now()
    return {
        "title": title,
        "draft_title": title,
        "slug": slug,
        "content_type": ContentType.objects.get_or_create(app_label=app_label, model=model_name)[0],
        "path": path,
        "depth": parent.depth + 1,
        "url_path": f"{parent.url_path}{slug}/",
        "locale_id": parent.locale_id,
        "translation_key": uuid.uuid4(),
        "live": True,
        "has_unpublished_changes": False,
        "first_published_at": now,
        "last_published_at": now,
        **extra,
    }


def seed(apps, schema_editor):
    TopicIdea = apps.get_model("blog", "TopicIdea")
    if not TopicIdea.objects.exists():
        TopicIdea.objects.bulk_create(TopicIdea(topic=t, notes=n) for t, n in TOPICS)

    BlogIndexPage = apps.get_model("blog", "BlogIndexPage")
    home = apps.get_model("core", "HomePage").objects.first()
    if home is None or BlogIndexPage.objects.exists():
        return
    Page = apps.get_model("wagtailcore", "Page")

    index = BlogIndexPage.objects.create(
        **page_fields(
            apps,
            "blog.blogindexpage",
            home,
            title="Blog",
            slug="blog",
            show_in_menus=True,
            search_description="Notes on Python, Django, APIs, integrations and production engineering.",
            numchild=1,
        ),
        intro="Notes on Python, Django, APIs, integrations and keeping services healthy in production.",
    )
    Page.objects.filter(pk=home.pk).update(numchild=home.numchild + 1)

    post = apps.get_model("blog", "BlogPostPage").objects.create(
        **page_fields(
            apps,
            "blog.blogpostpage",
            index,
            title="Hello, world: why I'm starting this blog",
            slug="hello-world",
        ),
        excerpt="A Python & Django engineer's notes on APIs, integrations, automation and production.",
        body=json.dumps([{"type": "markdown", "value": WELCOME, "id": str(uuid.uuid4())}]),
        queue_status="draft",
        source="manual",
        share_to_facebook=False,
    )
    tag, _ = apps.get_model("taggit", "Tag").objects.get_or_create(
        slug="meta", defaults={"name": "meta"}
    )
    apps.get_model("blog", "BlogPostTag").objects.create(tag=tag, content_object=post)


class Migration(migrations.Migration):
    dependencies = [("blog", "0001_initial"), ("core", "0002_seed_resume")]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
