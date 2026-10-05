"""Seed the Wagtail page tree with the 2026 resume and the privacy page.

Replaces Wagtail's default "Welcome" page with a HomePage at the site root. Runs once;
skipped if a HomePage already exists. Everything is editable afterwards in /admin/.
"""

import json
import uuid
from datetime import date

from django.db import migrations
from django.utils import timezone

SUMMARY = """Software engineer with 11+ years building and maintaining web applications, \
including 5+ years working on Prezzee's global platform. Focused on Python, Django, backend \
services, APIs, integrations, and practical automation.

Brings feature development and full-stack experience together with deep knowledge of how \
applications behave in production. Works with product and engineering teams to turn \
requirements and recurring problems into maintainable code."""

EXPERIENCES = [
    {
        "company": "Deel Inc.",
        "client": "Prezzee",
        "role": "Applications Development and Support Engineer",
        "location": "Kitchener, Ontario (remote)",
        "start_date": date(2023, 2, 1),
        "end_date": date(2026, 9, 30),
        "summary": "Continued five years of work on Prezzee's platform, combining application "
        "development, backend maintenance, automation, and production problem solving.",
        "highlights": "\n".join(
            [
                "Built Python tools and workflow automation for large data requests and repetitive processes, reducing manual work and making results easier to deliver.",
                "Developed and maintained application code and backend workflows for business-critical services, translating operational needs into software changes.",
                "Investigated defects in customer-facing services and implemented fixes and improvements with Engineering and Product partners.",
                "Worked with APIs, application data, and integrations to trace issues across services and support reliable end-to-end behavior.",
                "Used production findings to prioritize code fixes and preventative improvements; contributed to releases and post-release troubleshooting.",
            ]
        ),
    },
    {
        "company": "Prezzee",
        "client": "engaged through Yempo",
        "role": "Software Engineer",
        "location": "Manila, Philippines",
        "start_date": date(2021, 8, 1),
        "end_date": date(2023, 1, 31),
        "summary": "Developed and maintained applications and backend services for Prezzee's "
        "business-critical workflows.",
        "highlights": "\n".join(
            [
                "Developed Python/Django application features and maintained backend services used by Prezzee teams.",
                "Built and supported REST APIs and service integrations using Python, Django, SQL, Redis, and GraphQL.",
                "Delivered bug fixes and enhancements by tracing behavior through application code, data, and connected services.",
                "Collaborated with developers and Product to translate requirements and production feedback into application improvements.",
                "Tested and debugged changes and maintained existing services as business needs evolved.",
            ]
        ),
    },
    {
        "company": "ZEN Rooms",
        "client": "",
        "role": "Senior Python Engineer",
        "location": "Taguig, Philippines",
        "start_date": date(2020, 7, 1),
        "end_date": date(2021, 3, 31),
        "summary": "Built internal tools and backend applications for accommodation and business workflows.",
        "highlights": "\n".join(
            [
                "Designed and developed Python/Django tools that automated business processes and streamlined internal workflows.",
                "Built APIs and integrated backend services to connect existing systems and support application features.",
                "Turned product requirements into technical solutions with engineering and cross-functional partners.",
                "Contributed to code reviews, testing, debugging, and improvements in application maintainability.",
            ]
        ),
    },
    {
        "company": "Thorgate Digital OÜ",
        "client": "",
        "role": "Software Engineer",
        "location": "Tallinn, Estonia",
        "start_date": date(2019, 7, 1),
        "end_date": date(2020, 2, 29),
        "summary": "Delivered full-stack web applications with Python, Django, and React.",
        "highlights": "\n".join(
            [
                "Designed Python/Django backend services and APIs for web application features.",
                "Built React and JavaScript interfaces and connected them to backend APIs for end-to-end functionality.",
                "Resolved bugs across frontend and backend code and participated in reviews and testing.",
            ]
        ),
    },
    {
        "company": "Detail Online Technology",
        "client": "",
        "role": "Software Developer",
        "location": "Davao, Philippines",
        "start_date": date(2018, 6, 1),
        "end_date": date(2019, 5, 31),
        "summary": "Developed software for data validation, processing, and management.",
        "highlights": "\n".join(
            [
                "Designed and developed application components that validated and processed data to improve accuracy.",
                "Translated business and technical requirements into software design and implementation work.",
                "Debugged application and data-processing issues and contributed to testing and maintenance.",
            ]
        ),
    },
    {
        "company": "Ingenuity Global Consulting",
        "client": "",
        "role": "Software Developer",
        "location": "Davao, Philippines",
        "start_date": date(2014, 12, 1),
        "end_date": date(2017, 9, 30),
        "summary": "Built software applications for multiple startup clients across changing "
        "product requirements and technology environments.",
        "highlights": "\n".join(
            [
                "Implemented web application features, integrations, and supporting services from development through deployment.",
                "Contributed to backend and frontend development, database design, and API implementation across client projects.",
                "Worked with clients, project managers, and developers to turn requirements into working software.",
                "Debugged defects and delivered fixes and enhancements to improve application behavior and quality.",
            ]
        ),
    },
]

SKILL_GROUPS = [
    ("Backend", "Python, Django, REST APIs, Backend services, Celery"),
    ("Data & integration", "SQL, Redis, GraphQL, API integrations, Data validation"),
    ("Frontend", "React, JavaScript, TypeScript, Node.js"),
    ("Development", "Git, GitHub, GitLab, Code review, Testing, Debugging"),
    ("Production tools", "Datadog, Sentry, Jira, Confluence"),
]

PRIVACY_POLICY = """_Last updated: October 2026_

This site is a personal portfolio and blog. It is built to collect as little personal data as possible.

## What is collected

- **Analytics (no cookies).** Page views are counted with [GoatCounter](https://www.goatcounter.com/), which sets no cookies and does not track you across sites. It records the page, referrer, browser/OS family, screen size and country derived from your IP address; the IP itself is not stored.
- **Server logs.** Requests are logged for security and debugging **without your IP address**. Logs are rotated and kept for a short period.
- **Error reports.** If a page crashes, a technical error report is sent to Sentry with cookies and authorization headers stripped and no personal data attached.
- **Accounts (optional).** If you create an account, your username, email address and a hashed password are stored. Failed login attempts (username, IP address, time) are recorded to block brute-force attacks and are **deleted automatically after 30 days**.

## Cookies

The site sets no tracking or advertising cookies. Strictly necessary cookies are only set when you submit a form or sign in (`csrftoken`, `sessionid`). No consent banner is needed for these.

## Facebook

New blog posts are shared to a Facebook Page. This site does not embed Facebook scripts, pixels or "like" buttons, so Facebook receives nothing from your visit here. If you follow a link to Facebook, Facebook's own privacy policy applies there.

## Where data is stored

The site is hosted on Amazon Web Services. Uploaded images and database backups are stored in private Amazon S3 buckets.

## Your rights (GDPR / PIPEDA)

You can ask for a copy of your data, its correction, or its deletion at any time by emailing the address below. Account data is exported or erased within 30 days of a verified request.

## Contact

nikkomidoy@gmail.com
"""



def markdown_stream(text: str) -> str:
    return json.dumps([{"type": "markdown", "value": text, "id": str(uuid.uuid4())}])


def page_fields(apps, model: str, *, title: str, slug: str, path: str, url_path: str, **extra):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Locale = apps.get_model("wagtailcore", "Locale")
    app_label, model_name = model.split(".")
    now = timezone.now()
    return {
        "title": title,
        "draft_title": title,
        "slug": slug,
        "content_type": ContentType.objects.get_or_create(app_label=app_label, model=model_name)[0],
        "path": path,
        "depth": len(path) // 4,
        "url_path": url_path,
        "locale": Locale.objects.order_by("pk").first(),
        "translation_key": uuid.uuid4(),
        "live": True,
        "has_unpublished_changes": False,
        "first_published_at": now,
        "last_published_at": now,
        **extra,
    }


def seed(apps, schema_editor):
    HomePage = apps.get_model("core", "HomePage")
    if HomePage.objects.exists():
        return
    Page = apps.get_model("wagtailcore", "Page")
    Site = apps.get_model("wagtailcore", "Site")

    # Wagtail's stock "Welcome to your new Wagtail site!" page (its Site cascades with it).
    Page.objects.filter(
        depth=2, content_type__app_label="wagtailcore", content_type__model="page"
    ).delete()
    root = Page.objects.get(depth=1)

    home = HomePage.objects.create(
        **page_fields(
            apps,
            "core.homepage",
            title="Nikko Comidoy",
            slug="home",
            path=root.path + "0001",
            url_path="/home/",
            seo_title="Senior Software Engineer | Python & Django",
            numchild=1,
        ),
        name="Nikko Comidoy",
        headline="Senior Software Engineer | Python & Django",
        location="Kitchener, Ontario",
        email="nikkomidoy@gmail.com",
        show_email=True,
        phone="",
        show_phone=False,
        linkedin_url="https://www.linkedin.com/in/nikkocomidoy",
        summary=SUMMARY,
    )
    Page.objects.filter(pk=root.pk).update(numchild=Page.objects.filter(depth=2).count())
    Site.objects.create(
        hostname="localhost", port=80, root_page_id=home.pk, is_default_site=True
    )

    Experience = apps.get_model("core", "Experience")
    for i, exp in enumerate(EXPERIENCES):
        Experience.objects.create(page=home, sort_order=i, **exp)

    SkillGroup = apps.get_model("core", "SkillGroup")
    for i, (name, skills) in enumerate(SKILL_GROUPS):
        SkillGroup.objects.create(page=home, sort_order=i, name=name, skills=skills)

    apps.get_model("core", "Education").objects.create(
        page=home,
        sort_order=0,
        school="University of Southeastern Philippines",
        degree="Bachelor of Science in Information Technology",
        location="Davao, Philippines",
        start_date=date(2010, 6, 1),
        end_date=date(2014, 4, 30),
    )
    apps.get_model("core", "Certification").objects.create(
        page=home,
        sort_order=0,
        name="Verified International Academic Qualifications",
        issuer="World Education Services",
        period="Apr 2023 – Present",
    )
    apps.get_model("core", "ContentPage").objects.create(
        **page_fields(
            apps,
            "core.contentpage",
            title="Privacy policy",
            slug="privacy",
            path=home.path + "0001",
            url_path="/home/privacy/",
            search_description="How this site handles personal data.",
        ),
        body=markdown_stream(PRIVACY_POLICY),
        show_in_footer=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_initial"),
        ("wagtailcore", "0098_apitoken"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
