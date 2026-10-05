import pytest

from blog.models import BlogPostPage


@pytest.mark.django_db
def test_list_detail_and_feed(client, make_post):
    post = make_post(
        title="Visible",
        body="**bold** <script>alert(1)</script>",
        share_to_facebook=False,
        publish=True,
    )
    assert "Visible" in client.get("/blog/").text
    detail = client.get(post.url)
    assert "<strong>bold</strong>" in detail.text
    assert "<script>alert(1)</script>" not in detail.text
    assert 'property="og:type" content="article"' in detail.text
    assert "Visible" in client.get("/blog/feed/").text


@pytest.mark.django_db
def test_tag_filter(client, make_post):
    make_post(title="Tagged one", tags=["django"], share_to_facebook=False, publish=True)
    make_post(title="Other one", share_to_facebook=False, publish=True)
    html = client.get("/blog/?tag=Django").text
    assert "Tagged one" in html and "Other one" not in html
    assert [p["title"] for p in client.get("/api/posts/?tag=django").json()] == ["Tagged one"]


@pytest.mark.django_db
def test_unpublished_posts_hidden_from_public(client, admin_client, make_post):
    post = make_post(title="Secret", queue_status=BlogPostPage.QueueStatus.NEEDS_REVIEW)
    assert client.get("/blog/secret/").status_code == 404
    assert "Secret" not in client.get("/api/posts/").text
    assert admin_client.get(f"/admin/pages/{post.pk}/edit/").status_code == 200


@pytest.mark.django_db
def test_slug_is_unique(make_post):
    a = make_post(title="Same")
    b = make_post(title="Same")
    assert a.slug == "same" and b.slug == "same-2"
