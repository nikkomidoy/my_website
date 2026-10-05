from django.urls import path
from dmr.routing import Router

from .controllers import PostListController

router = Router(
    "api/",
    [
        path("posts/", PostListController.as_view(), name="posts"),
    ],
)
