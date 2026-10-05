from wagtail.signals import page_published

from .models import BlogPostPage
from .services import publishing


def share_on_publish(sender, instance: BlogPostPage, **kwargs):
    """Share to Facebook whenever a post goes live — admin Publish or the daily task."""
    if instance.share_to_facebook:
        publishing.share_to_facebook(instance)


page_published.connect(share_on_publish, sender=BlogPostPage)
