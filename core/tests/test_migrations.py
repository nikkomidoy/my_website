import pytest


@pytest.mark.django_db
def test_seed_resume_is_idempotent(migrator):
    old = migrator.apply_initial_migration(("core", "0001_initial"))
    Page = old.apps.get_model("wagtailcore", "Page")
    ContentType = old.apps.get_model("contenttypes", "ContentType")
    ct, _ = ContentType.objects.get_or_create(app_label="core", model="homepage")
    root = Page.objects.get(depth=1)
    old.apps.get_model("core", "HomePage").objects.create(
        title="Existing",
        draft_title="Existing",
        slug="existing",
        content_type=ct,
        path=root.path + "0009",
        depth=2,
        url_path="/existing/",
        locale=old.apps.get_model("wagtailcore", "Locale").objects.first(),
        name="Existing",
        headline="h",
        summary="s",
    )
    new = migrator.apply_tested_migration(("core", "0002_seed_resume"))
    HomePage = new.apps.get_model("core", "HomePage")
    assert list(HomePage.objects.values_list("name", flat=True)) == ["Existing"]
    assert new.apps.get_model("core", "Experience").objects.count() == 0


@pytest.mark.django_db
def test_seed_builds_page_tree(migrator):
    migrator.apply_initial_migration(("core", "0001_initial"))
    new = migrator.apply_tested_migration(("blog", "0002_seed_topics"))
    Page = new.apps.get_model("wagtailcore", "Page")
    assert list(Page.objects.order_by("path").values_list("url_path", flat=True)) == [
        "/",
        "/home/",
        "/home/privacy/",
        "/home/blog/",
        "/home/blog/hello-world/",
    ]
    assert new.apps.get_model("wagtailcore", "Site").objects.get().root_page.slug == "home"
