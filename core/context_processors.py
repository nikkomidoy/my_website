from django.utils.functional import SimpleLazyObject
from wagtail.models import Site


def site(request):
    """Header/footer data for every template. Lazy, so emails and plain views pay nothing."""

    def home():
        wagtail_site = Site.find_for_request(request)
        return wagtail_site.root_page.specific if wagtail_site else None

    def nav_pages():
        root = site_home
        return list(root.get_children().live().in_menu()) if root else []

    def footer_pages():
        from .models import ContentPage

        return list(ContentPage.objects.live().filter(show_in_footer=True).order_by("path"))

    def blog_index():
        from blog.models import BlogIndexPage

        return BlogIndexPage.objects.live().first()

    site_home = SimpleLazyObject(home)
    return {
        "site_home": site_home,
        "nav_pages": SimpleLazyObject(nav_pages),
        "footer_pages": SimpleLazyObject(footer_pages),
        "blog_index": SimpleLazyObject(blog_index),
    }
