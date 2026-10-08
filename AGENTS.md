# AGENTS.md

Personal Wagtail CMS (resume + blog) for Nikko Comidoy, with a daily blog → Facebook Page automation.

## Stack decisions

- CMS: Wagtail — admin `/admin/` (login via allauth), Django admin `/django-admin/`; page tree Root → `core.HomePage` → `core.ContentPage` / `blog.BlogIndexPage` → `blog.BlogPostPage`; bodies are StreamField (`core/blocks.py`).
- Settings: split — `config/settings/{base,local,production,test}.py`; `manage.py` → local, wsgi/asgi → production.
- Database: PostgreSQL 17 (dev: host Homebrew `postgresql@17` on port 5433; prod: `postgres:17` container).
- Request handling: WSGI, gunicorn.
- Custom user: `users.User` (username-based `AbstractUser`).
- Lint: Ruff (`force-exclude`, migrations excluded). Tests: pytest + pytest-django + pytest-cov (`config.settings.test`).
- Types: pyright basic + django-stubs (settings excluded).
- Pre-commit: pre-commit-hooks, ruff, uv-lock, django-upgrade, djade, djhtml, pyright, rustywind.
- Devcontainer: `.devcontainer/devcontainer.json` (Python 3.13 + uv).
- Dev tools (local.py only): django-silk (`/silk/`), django-browser-reload, django-zeal (raise on N+1; skipped under admin paths, Wagtail routing allowlisted), django-extensions; django-test-migrations (dev dep).
- Logging: structlog + django-structlog; JSON in prod; IP logging disabled; `core.logging.DropSensitiveKeysFilter`.
- Task runner: Make.
- Auth: django-allauth (login by email or username), allauth.mfa (TOTP + recovery codes), django-axes (AxesBackend first, AxesMiddleware last).
- Cache: locmem.
- Storage: django-storages S3 for media (base, when bucket set) and static (production); public URLs (`AWS_QUERYSTRING_AUTH=False`); media never overwritten (`AWS_S3_FILE_OVERWRITE=False`). Prod uses the EC2 instance role — AWS keys stay unset (`None`, never "").
- Background: `django.tasks` (default immediate backend) + django-crontask; scheduler process `manage.py crontask`.
- Email: `MAILERS` — console in dev, SMTP (SES) in prod; `core/templates/email/base.html`; `send_test_email`.
- Frontend: django-tailwind-cli (Tailwind 4) + vendored DaisyUI 5 (`tailwind-src/css/`), custom `nikko` / `nikko-dark` themes; favicon in `assets/`.
- SEO: meta/OG block in `templates/base.html` (falls back to Wagtail `seo_title` / `search_description`), Wagtail sitemap (`config/sitemaps.py`), `robots.txt` (`ROBOTS_DISALLOW_ALL`).
- REST: django-modern-rest (msgspec) — `api/` app, `GET /api/posts/`.
- Analytics: GoatCounter (`ANALYTICS_ID` / `ANALYTICS_HOST`), only when `not DEBUG`.
- Security: production.py hardening + Django 6.1 built-in CSP (nonce available as `csp_nonce`); `SECURE_CSP_ADMIN` (inline scripts, same-origin frames) applied to admin paths by `core.middleware.AdminCSPMiddleware`.
- Health: `/healthz` (liveness), `/readyz` (DB).
- Errors: Sentry (production.py, PII scrubbed).
- GDPR: SameSite=Lax, `export_user_data` / `delete_user_data`, `core.tasks.purge_login_records`, privacy page seeded.
- CI: `.github/workflows/test.yml` (PR + workflow_call). Deploy: `.github/workflows/deploy.yml` (github-ssh → EC2, GHCR image, Caddy).
- Backups: django-dbbackup 5.x via `STORAGES["dbbackup"]` (production only), scheduled by crontask.
- AI: Anthropic SDK, `client.beta.messages.parse` + Pydantic `PostDraft`, `fallbacks="default"`, model `BLOG_AI_MODEL` (default `claude-opus-5-5`).

## Layout

```
config/            settings/, urls.py, sitemaps.py, context_processors.py (analytics)
users/             custom User + GDPR export/delete commands
core/              Wagtail pages (HomePage + resume Orderables, ContentPage), StreamField blocks,
                   health/robots views, admin CSP middleware, markdownify filter, housekeeping
                   tasks, seed migration 0002_seed_resume (page tree), email templates, send_test_email
blog/              BlogIndexPage (routable: feed/), BlogPostPage (queue_status draft → needs_review
                   → queued; live = published), TopicIdea snippet, wagtail_hooks.py + admin views,
                   signals.py (share on page_published), services/{facebook,ai,publishing}.py,
                   tasks.py (daily_blog), seed migration 0002 (topics, blog index, welcome post)
api/               django-modern-rest controllers
templates/         base.html, _analytics.html
tailwind-src/css/  source.css + vendored daisyui*.mjs
assets/            favicon + compiled CSS (css/ is gitignored, built in Docker)
deploy/            docker-compose.prod.yml, Caddyfile, .env.prod.example
docs/aws-setup.md  one-time AWS / GitHub / Facebook / Claude setup
```

## Key commands

```sh
make install          # uv sync + pre-commit install
make dev              # runserver + tailwind watcher
make test             # pytest
make lint fmt typecheck
make migrate
make cron             # crontask scheduler
uv run manage.py shell -c "from blog.tasks import daily_blog; print(daily_blog.call())"
```

Deploy: push to `main` (GitHub Actions). Manual: `make deploy` on the EC2 host.

## Conventions

- `uv run …` on the host; `python manage.py …` inside containers (no uv in the runtime image).
- New env vars go in `.env.example` and `deploy/.env.prod.example`.
- New template dirs need an `@source` line in `tailwind-src/css/source.css`.
- Tasks live in `<app>/tasks.py`, imported from `AppConfig.ready()`.
- Markdown is rendered only through `markdownify` (nh3-sanitized) — including StreamField `markdown` blocks.
- Facebook share state (`BlogPostPage.SHARE_STATE_FIELDS`) is written to the page row only and preserved across revision publishes; never put it in a revision.
- Seed migrations build Wagtail pages with raw treebeard paths (historical models have no `add_child`).
