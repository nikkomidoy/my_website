from .base import *

DEBUG = False  # surface TemplateSyntaxError instead of swallowing it
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
MAILERS = {
    "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# Django Tasks: run inline in the request thread so tests see results without a worker.
TASKS = {"default": {"BACKEND": "django.tasks.backends.immediate.ImmediateBackend"}}
# Celery: same pattern — eager execution in the calling thread, no worker required.
# Harmless when Celery isn't installed; the keys are just ignored.
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
