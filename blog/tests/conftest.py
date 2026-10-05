import pytest

from blog.models import BlogIndexPage, BlogPostPage


@pytest.fixture
def make_post(db):
    """Create a blog post page under the seeded index. `publish=True` puts it live."""

    def make(*, publish: bool = False, body: str = "Body", tags=(), **kw) -> BlogPostPage:
        fields = {
            "title": "A post",
            "excerpt": "Excerpt",
            "queue_status": BlogPostPage.QueueStatus.QUEUED,
            **kw,
        }
        post = BlogPostPage(body=[("markdown", body)], live=False, **fields)
        post.tags.add(*tags)
        BlogIndexPage.objects.get().add_child(instance=post)
        revision = post.save_revision()
        if publish:
            revision.publish()
        post.refresh_from_db()
        return post

    return make
