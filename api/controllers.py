from dmr import Controller, Query
from dmr.plugins.msgspec import MsgspecSerializer

from blog.models import BlogPostPage

from .schemas import PostOut, PostQuery


class PostListController(Controller[MsgspecSerializer]):
    """Public, read-only list of published posts."""

    def get(self, parsed_query: Query[PostQuery]) -> list[PostOut]:
        posts = BlogPostPage.objects.published().prefetch_related("tagged_items__tag")
        if parsed_query.tag:
            posts = posts.filter(tags__name__iexact=parsed_query.tag)
        limit = max(1, min(parsed_query.limit, 100))
        return [
            PostOut(
                title=p.title,
                slug=p.slug,
                url=p.get_url() or "",
                excerpt=p.excerpt,
                tags=[item.tag.name for item in p.tagged_items.all()],
                published_at=p.first_published_at,
            )
            for p in posts[:limit]
        ]
