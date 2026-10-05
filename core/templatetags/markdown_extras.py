import markdown as md
import nh3
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

ALLOWED_TAGS = {
    "a",
    "abbr",
    "blockquote",
    "br",
    "code",
    "em",
    "h2",
    "h3",
    "h4",
    "hr",
    "img",
    "li",
    "ol",
    "p",
    "pre",
    "strong",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}
ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "code": {"class"},
    "th": {"align"},
    "td": {"align"},
}


@register.filter
def markdownify(text: str) -> str:
    """Render Markdown and sanitize the HTML (AI drafts and admin input alike)."""
    html = md.markdown(text or "", extensions=["fenced_code", "tables", "sane_lists"])
    clean = nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        link_rel="noopener noreferrer nofollow",
        url_schemes={"http", "https", "mailto"},
    )
    return mark_safe(clean)  # noqa: S308 — sanitized by nh3 above
