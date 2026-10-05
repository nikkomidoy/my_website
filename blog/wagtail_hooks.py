from django.urls import include, path, reverse
from wagtail import hooks
from wagtail.admin.ui.menus.pages import PageMenuItem
from wagtail.admin.widgets import HeaderButton
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import IndexView, SnippetViewSet

from . import urls
from .models import BlogPostPage, TopicIdea


def register_blog_admin_urls():
    return [path("blog/", include(urls))]


hooks.register("register_admin_urls", register_blog_admin_urls)


class TopicIdeaIndexView(IndexView):
    @property
    def header_buttons(self):
        return [
            *super().header_buttons,
            HeaderButton(
                "Draft a post with Claude now",
                url=reverse("blog_admin:draft_with_ai"),
                icon_name="edit",
            ),
        ]


class TopicIdeaViewSet(SnippetViewSet):
    model = TopicIdea
    add_to_admin_menu = True
    list_display = ["topic", "used_at", "created_at"]
    index_view_class = TopicIdeaIndexView


register_snippet(TopicIdeaViewSet(icon="help", menu_label="Topic ideas", menu_order=300))


class ShareToFacebookMenuItem(PageMenuItem):
    label = "Share to Facebook"
    icon_name = "link-external"
    url_name = "blog_admin:share_to_facebook"
    priority = 70

    def is_shown(self, user):
        return self.page.live and self.page.permissions_for_user(user).can_publish()


def facebook_share_button(page, user, view_name, next_url=None):
    if issubclass(page.specific_class or object, BlogPostPage):
        yield ShareToFacebookMenuItem(page=page)


hooks.register("register_page_header_buttons", facebook_share_button)
