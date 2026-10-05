from typing import TYPE_CHECKING

from django.db import models
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import (
    FieldPanel,
    FieldRowPanel,
    InlinePanel,
    MultiFieldPanel,
    ObjectList,
    TabbedInterface,
)
from wagtail.fields import StreamField
from wagtail.models import Orderable, Page
from wagtail.search import index

from .blocks import BodyBlock


class HomePage(Page):
    """Site root: the resume. Profile fields drive the header/footer on every page."""

    name = models.CharField(max_length=120)
    headline = models.CharField(max_length=200)
    location = models.CharField(max_length=120, blank=True)
    email = models.EmailField(blank=True)
    show_email = models.BooleanField(default=True)
    phone = models.CharField(max_length=40, blank=True)
    show_phone = models.BooleanField(
        default=False, help_text="Public phone numbers attract spam; off by default."
    )
    linkedin_url = models.URLField(blank=True)
    github_url = models.URLField(blank=True)
    summary = models.TextField(help_text="Markdown. Shown at the top of the home page.")
    photo = models.ForeignKey(
        "wagtailimages.Image", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    resume_pdf = models.ForeignKey(
        "wagtaildocs.Document", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    max_count = 1
    parent_page_types = ["wagtailcore.Page"]
    subpage_types = ["blog.BlogIndexPage", "core.ContentPage"]
    template = "core/home.html"

    search_fields = [*Page.search_fields, index.SearchField("summary")]

    content_panels = [
        *Page.content_panels,
        MultiFieldPanel(
            [
                FieldRowPanel([FieldPanel("name"), FieldPanel("location")]),
                FieldPanel("headline"),
                FieldPanel("summary"),
                FieldRowPanel([FieldPanel("photo"), FieldPanel("resume_pdf")]),
            ],
            heading="Profile",
        ),
        MultiFieldPanel(
            [
                FieldRowPanel([FieldPanel("email"), FieldPanel("show_email")]),
                FieldRowPanel([FieldPanel("phone"), FieldPanel("show_phone")]),
                FieldRowPanel([FieldPanel("linkedin_url"), FieldPanel("github_url")]),
            ],
            heading="Contact",
        ),
    ]
    resume_panels = [
        InlinePanel("experiences", heading="Experience", label="Role"),
        InlinePanel("skill_groups", heading="Skills", label="Skill group"),
        InlinePanel("education", heading="Education", label="School"),
        InlinePanel("certifications", heading="Certification", label="Certification"),
    ]
    edit_handler = TabbedInterface(
        [
            ObjectList(content_panels, heading="Profile"),
            ObjectList(resume_panels, heading="Resume"),
            ObjectList(Page.promote_panels, heading="Promote"),
            ObjectList(Page.settings_panels, heading="Settings"),
        ]
    )

    if TYPE_CHECKING:
        from django.db.models.fields.related_descriptors import RelatedManager

        experiences: RelatedManager["Experience"]
        skill_groups: RelatedManager["SkillGroup"]

    class Meta:
        verbose_name = "home page (resume)"

    @classmethod
    def current(cls) -> "HomePage | None":
        return cls.objects.live().first()

    def get_context(self, request, *args, **kwargs):
        from blog.models import BlogPostPage

        context = super().get_context(request, *args, **kwargs)
        context["latest_posts"] = BlogPostPage.objects.published().for_cards()[:3]
        return context


class ResumeItem(Orderable):
    """Inline row on the home page; drag to reorder in the Resume tab."""

    class Meta(Orderable.Meta):
        abstract = True


class Experience(ResumeItem):
    page = ParentalKey(HomePage, on_delete=models.CASCADE, related_name="experiences")
    company = models.CharField(max_length=160)
    client = models.CharField(max_length=160, blank=True)
    role = models.CharField(max_length=160)
    location = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave empty if current.")
    summary = models.TextField(blank=True)
    highlights = models.TextField(blank=True, help_text="One bullet per line.")

    panels = [
        FieldRowPanel([FieldPanel("role"), FieldPanel("company")]),
        FieldRowPanel([FieldPanel("client"), FieldPanel("location")]),
        FieldRowPanel([FieldPanel("start_date"), FieldPanel("end_date")]),
        FieldPanel("summary"),
        FieldPanel("highlights"),
    ]

    def __str__(self) -> str:
        return f"{self.role} — {self.company}"

    @property
    def highlight_list(self) -> list[str]:
        return [line.strip() for line in self.highlights.splitlines() if line.strip()]


class SkillGroup(ResumeItem):
    page = ParentalKey(HomePage, on_delete=models.CASCADE, related_name="skill_groups")
    name = models.CharField(max_length=80)
    skills = models.TextField(help_text="Comma-separated.")

    def __str__(self) -> str:
        return self.name

    @property
    def skill_list(self) -> list[str]:
        return [s.strip() for s in self.skills.split(",") if s.strip()]


class Education(ResumeItem):
    page = ParentalKey(HomePage, on_delete=models.CASCADE, related_name="education")
    school = models.CharField(max_length=160)
    degree = models.CharField(max_length=160)
    location = models.CharField(max_length=120, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta(ResumeItem.Meta):
        verbose_name_plural = "education"

    def __str__(self) -> str:
        return f"{self.degree} — {self.school}"


class Certification(ResumeItem):
    page = ParentalKey(HomePage, on_delete=models.CASCADE, related_name="certifications")
    name = models.CharField(max_length=200)
    issuer = models.CharField(max_length=160, blank=True)
    period = models.CharField(max_length=80, blank=True)
    url = models.URLField(blank=True)

    def __str__(self) -> str:
        return self.name


class ContentPage(Page):
    """Free-form page (privacy policy, about, uses, …)."""

    body = StreamField(BodyBlock())
    show_in_footer = models.BooleanField(default=False)

    parent_page_types = ["core.HomePage"]
    subpage_types: list[str] = []
    template = "core/page.html"

    search_fields = [*Page.search_fields, index.SearchField("body")]

    content_panels = [*Page.content_panels, FieldPanel("body")]
    promote_panels = [
        *Page.promote_panels,
        FieldPanel("show_in_footer"),
    ]
