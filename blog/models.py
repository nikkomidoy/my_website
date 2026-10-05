from typing import ClassVar

from django.core.paginator import Paginator
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.utils.functional import cached_property
from modelcluster.contrib.taggit import ClusterTaggableManager
from modelcluster.fields import ParentalKey
from taggit.models import TaggedItemBase
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, ObjectList, TabbedInterface
from wagtail.contrib.routable_page.models import RoutablePageMixin, path
from wagtail.fields import StreamField
from wagtail.models import Page, PageManager
from wagtail.query import PageQuerySet
from wagtail.search import index

from core.blocks import BodyBlock


class BlogIndexPage(RoutablePageMixin, Page):
    intro = models.TextField(blank=True)

    max_count = 1
    parent_page_types = ["core.HomePage"]
    subpage_types = ["blog.BlogPostPage"]
    template = "blog/list.html"

    content_panels = [*Page.content_panels, FieldPanel("intro")]

    def get_context(self, request, *args, **kwargs):
        context = super().get_context(request, *args, **kwargs)
        posts = BlogPostPage.objects.published().descendant_of(self).for_cards()
        tag = request.GET.get("tag", "").strip()
        if tag:
            posts = posts.filter(tags__name__iexact=tag)
        context["page_obj"] = Paginator(posts, 10).get_page(request.GET.get("page"))
        context["tag"] = tag
        return context

    @path("feed/", name="feed")
    def feed(self, request):
        from .views import LatestPostsFeed

        return LatestPostsFeed(self)(request)


class BlogPostTag(TaggedItemBase):
    content_object = ParentalKey(
        "blog.BlogPostPage", on_delete=models.CASCADE, related_name="tagged_items"
    )


class BlogPostQuerySet(PageQuerySet):
    def published(self) -> "BlogPostQuerySet":
        return self.live().public().order_by("-first_published_at")

    def for_cards(self) -> "BlogPostQuerySet":
        return self.select_related("cover_image").prefetch_related("cover_image__renditions")

    def ready_to_publish(self) -> "BlogPostQuerySet":
        """Queued drafts whose `publish_after` (if any) has arrived, oldest-scheduled first."""
        return (
            self.not_live()
            .filter(queue_status=BlogPostPage.QueueStatus.QUEUED)
            .filter(Q(publish_after__isnull=True) | Q(publish_after__lte=timezone.now()))
            .order_by(models.F("publish_after").asc(nulls_last=True), "pk")
        )

    def awaiting_review(self) -> "BlogPostQuerySet":
        return self.not_live().filter(queue_status=BlogPostPage.QueueStatus.NEEDS_REVIEW)


BlogPostManager = PageManager.from_queryset(BlogPostQuerySet)


class BlogPostPage(Page):
    """A blog post. Publishing (by hand or by the daily task) shares it to Facebook."""

    class QueueStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        NEEDS_REVIEW = "needs_review", "Needs review (AI draft)"
        QUEUED = "queued", "Queued for daily publish"

    class Source(models.TextChoices):
        MANUAL = "manual", "Written by me"
        AI = "ai", "AI draft"

    excerpt = models.CharField(max_length=300, help_text="Shown in lists, meta and link previews.")
    body = StreamField(BodyBlock())
    cover_image = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    tags = ClusterTaggableManager(through=BlogPostTag, blank=True)

    queue_status = models.CharField(
        "daily queue",
        max_length=20,
        choices=QueueStatus.choices,
        default=QueueStatus.DRAFT,
        help_text="Unpublished posts set to Queued go live one per day via the daily task. "
        "Use Publish to put a post live right away.",
    )
    source = models.CharField(max_length=10, choices=Source.choices, default=Source.MANUAL)
    publish_after = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Queued posts publish on the first daily run at/after this time. "
        "Empty = next daily run.",
    )

    share_to_facebook = models.BooleanField(default=True)
    facebook_message = models.TextField(
        blank=True, help_text="Text for the Facebook post. Defaults to the excerpt."
    )
    facebook_post_id = models.CharField(max_length=100, blank=True)
    facebook_shared_at = models.DateTimeField(null=True, blank=True)
    facebook_error = models.TextField(blank=True)

    objects: ClassVar[BlogPostQuerySet] = BlogPostManager()  # type: ignore[assignment]

    parent_page_types = ["blog.BlogIndexPage"]
    subpage_types: list[str] = []
    template = "blog/detail.html"

    # Share state is written straight to the page row by the publishing service; keep
    # it out of revision restores so re-publishing an edit never re-shares a post.
    SHARE_STATE_FIELDS = ("facebook_post_id", "facebook_shared_at", "facebook_error")

    search_fields = [
        *Page.search_fields,
        index.SearchField("excerpt"),
        index.SearchField("body"),
        index.FilterField("queue_status"),
    ]

    content_panels = [
        *Page.content_panels,
        FieldPanel("excerpt"),
        FieldPanel("cover_image"),
        FieldPanel("body"),
        FieldPanel("tags"),
    ]
    publishing_panels = [
        MultiFieldPanel(
            [FieldPanel("queue_status"), FieldPanel("publish_after"), FieldPanel("source")],
            heading="Daily queue",
        ),
        MultiFieldPanel(
            [
                FieldPanel("share_to_facebook"),
                FieldPanel("facebook_message"),
                FieldPanel("facebook_post_id", read_only=True),
                FieldPanel("facebook_shared_at", read_only=True),
                FieldPanel("facebook_error", read_only=True),
            ],
            heading="Facebook",
        ),
    ]
    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Content"),
            ObjectList(publishing_panels, heading="Queue & Facebook"),
            ObjectList(Page.promote_panels, heading="Promote"),
            ObjectList(Page.settings_panels, heading="Settings"),
        ]
    )

    class Meta:
        indexes = [models.Index(fields=["queue_status", "publish_after"])]

    def with_content_json(self, content):
        obj = super().with_content_json(content)
        for field in self.SHARE_STATE_FIELDS:
            setattr(obj, field, getattr(self, field))
        return obj

    @cached_property
    def tag_list(self) -> list[str]:
        return [t.name for t in self.tags.all()]

    def get_meta_description(self) -> str:
        return self.search_description or self.excerpt


class TopicIdea(models.Model):
    """Seed topics the AI fallback writes about when the queue is empty."""

    topic = models.CharField(max_length=300)
    notes = models.TextField(blank=True, help_text="Angle, audience, points to cover.")
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    panels = [FieldPanel("topic"), FieldPanel("notes"), FieldPanel("used_at")]

    class Meta:
        ordering = [models.F("used_at").asc(nulls_first=True), "created_at"]

    def __str__(self) -> str:
        return self.topic
