from django.apps import AppConfig


class BlogConfig(AppConfig):
    name = "blog"

    def ready(self) -> None:
        from . import signals, tasks  # noqa: F401  — page_published receiver, @task / @cron
