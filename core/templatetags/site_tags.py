from django import template

register = template.Library()


@register.filter
def in_section(page, section) -> bool:
    """True when `page` is `section` or one of its descendants (nav highlighting)."""
    if not page or not section or not hasattr(page, "path"):
        return False
    return page.path.startswith(section.path)
