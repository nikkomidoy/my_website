# nikkocomidoy

Nikko Comidoy's personal CMS: a resume/portfolio site plus a blog. A daily job publishes the next
queued post and shares it to a Facebook Page. When the queue is empty, Claude drafts a post for
review instead. The site is privacy-first (GDPR) and deploys to AWS EC2 through GitHub Actions.

## Features

- **Wagtail CMS** at `/admin/`: the resume is the site's home page (profile, experience, skills,
  education, certifications as inline panels), with free-form content pages and the blog under it.
  The page tree has drafts, revisions, live preview, scheduled publishing and an image/document
  library. The first `migrate` seeds it from the 2026 resume. Django admin moved to `/django-admin/`.
- **Blog** at `/blog/`: StreamField posts (Markdown, rich text, figure, code and quote blocks;
  Markdown is sanitized with nh3), cover images on S3, tags, an RSS feed at `/blog/feed/`,
  OpenGraph tags for Facebook link previews, a sitemap, and a read-only JSON API at `/api/posts/`.
- **Daily automation** (`blog/tasks.py`, run by the `cron` process at `BLOG_DAILY_CRON`, default 09:00 America/Toronto):
  1. Publishes the next unpublished post whose **Daily queue** is *Queued* and whose
     `publish_after` has arrived (one post per day).
  2. Shares it to your **Facebook Page** via the Graph API, and retries failed shares for 3 days.
     Publishing a post by hand in Wagtail shares it too; republishing an edit never re-shares.
  3. If the queue is empty, asks **Claude** (`claude-opus-5-5`, structured output) to draft a post
     from the next unused **Topic idea**. The draft is saved as *Needs review*, and `DJANGO_ADMINS`
     get an email. Approve it by setting the post's daily queue to *Queued* (or just **Publish**).
     **Topic ideas** has a *Draft a post with Claude now* button.
- **GDPR-friendly**: no tracking cookies (GoatCounter is cookieless), no IPs in logs, Sentry PII
  scrubbing, login-attempt records purged after 30 days, `export_user_data` / `delete_user_data`
  commands, and a privacy policy page at `/privacy/`. Wagtail's Gravatar lookups and update-check
  pings are off.
- **Production**: Docker image, Caddy with automatic TLS, Postgres 17, S3 for static and media,
  SES for email, nightly `pg_dump` backups to S3, Sentry, and a CSP with HSTS.

## Stack

| Area | Choice |
|---|---|
| CMS | Wagtail (page tree, StreamField, images, documents, snippets, redirects, sitemap) |
| Framework | Django 6.1, split settings (`config/settings/{base,local,production,test}.py`), WSGI (gunicorn) |
| Database | PostgreSQL 17 (dev: Homebrew `postgresql@17` on port **5433**) |
| User model | `users.User` (username-based `AbstractUser`) |
| Auth | django-allauth (email **or** username login), allauth.mfa (TOTP 2FA), django-axes lockout |
| Background | `django.tasks` + django-crontask (`manage.py crontask`) |
| Email | console in dev, SMTP (Amazon SES) in prod; branded HTML base template |
| Frontend | Tailwind 4 via django-tailwind-cli + DaisyUI 5 (custom teal `nikko` / `nikko-dark` themes) |
| Storage | django-storages S3 (static + media); local `./media` fallback in dev |
| Cache | locmem |
| REST | django-modern-rest (msgspec) |
| SEO | meta/OG tags (Wagtail *Promote* tab), Wagtail `sitemap.xml`, `robots.txt` |
| Analytics | GoatCounter (cookieless) |
| Observability | structlog (JSON in prod), Sentry |
| Security | production hardening, Django 6.1 built-in CSP, `/healthz` + `/readyz` |
| DX | Ruff, pytest (+cov), pyright + django-stubs, pre-commit, devcontainer, Make, django-silk, django-browser-reload, django-zeal, django-test-migrations, django-extensions |
| CI/CD | GitHub Actions: test → build multi-arch image to GHCR → SSH deploy to EC2 |
| Backups | django-dbbackup → private S3 bucket, nightly |

Pinned versions are in `pyproject.toml` / `uv.lock`.

## Getting started

Prerequisites: [uv](https://docs.astral.sh/uv/) and PostgreSQL 15 or newer. Homebrew's
`postgresql@17` runs on port 5433, next to an existing PG14.

```bash
make install
```

```bash
cp .env.example .env
```

Set `DJANGO_SECRET_KEY` in `.env`, then create the database and load the seeded content:

```bash
createdb -p 5433 nikkocomidoy
```

```bash
make migrate
```

```bash
make superuser
```

```bash
make dev
```

Open <http://127.0.0.1:8000/>. The Wagtail admin is at `/admin/`, Django admin (users, axes) at
`/django-admin/`, and the profiler at `/silk/` (dev only). Both admins sign in through allauth at
`/accounts/login/`, so TOTP and axes lockout apply.

### Key commands

| Command | What it does |
|---|---|
| `make dev` | runserver + Tailwind watcher |
| `make test` / `make cov` | pytest / with HTML coverage |
| `make lint` / `make fmt` / `make fix` | Ruff |
| `make typecheck` | pyright |
| `make migrate` / `make makemigrations` | migrations |
| `make shell` | `shell_plus` (django-extensions) |
| `make css` | production Tailwind build |
| `make cron` | run the scheduler locally (daily blog job, purge, backup) |
| `uv run manage.py send_test_email you@example.com` | verify the mailer |
| `uv run manage.py export_user_data <id>` / `delete_user_data <id>` | GDPR access and erasure |

Try the daily job once without waiting for the schedule:

```bash
uv run manage.py shell -c "from blog.tasks import daily_blog; print(daily_blog.call())"
```

### Pre-commit

`make install` runs `pre-commit install`. The hooks are whitespace, Ruff, uv-lock, django-upgrade,
djade, djhtml, pyright and rustywind. Bump them with `uv run pre-commit autoupdate`.

### Devcontainer

`.devcontainer/` opens the project in a Python 3.13 + uv container. It reaches the host's Postgres
on port 5433 through `host.docker.internal`. For that, Postgres must listen on that interface, and
`pg_hba.conf` must allow the Docker network.

## Configuration

`.env.example` lists every environment variable, and `deploy/.env.prod.example` is the production
template. The important ones for the automation:

| Variable | Purpose |
|---|---|
| `BLOG_DAILY_CRON` | crontab in `DJANGO_TIME_ZONE` (default `0 9 * * *`) |
| `FACEBOOK_PAGE_ID`, `FACEBOOK_PAGE_ACCESS_TOKEN`, `FACEBOOK_APP_SECRET` | Facebook Page sharing (see [docs/aws-setup.md](docs/aws-setup.md#6-facebook-page-token)) |
| `ANTHROPIC_API_KEY`, `BLOG_AI_FALLBACK_ENABLED`, `BLOG_AI_AUTO_PUBLISH`, `BLOG_AI_MODEL` | Claude fallback drafts |

## Deploy

One-time AWS, GitHub and Facebook setup is in [docs/aws-setup.md](docs/aws-setup.md).

After that, every push to `main` runs `.github/workflows/deploy.yml`:

1. Runs the test workflow: Ruff, pyright, pre-commit, `check --deploy`, the migration check, and pytest.
2. Builds the `prod` image (amd64 + arm64) and pushes it to GHCR as `:latest` and `:<sha>`.
3. Copies `deploy/docker-compose.prod.yml` and `deploy/Caddyfile` to `/srv/nikkocomidoy` on EC2.
4. Over SSH: `pull`, `collectstatic` (to S3), `migrate`, `up -d`, waits for `web` to report healthy,
   then prunes old images.
5. Smoke-tests `https://$SITE_DOMAIN/readyz`.

Manual deploy on the host (the one-shot `migrate` must run before `up -d`, or the first boot hits
an empty database):

```sh
ssh user@vps
cd /srv/nikkocomidoy
export GITHUB_REPOSITORY=owner/repo
# --env-file is required on every compose call — compose auto-loads only ./.env, not deploy/.env.prod
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml pull
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml run --rm web python manage.py collectstatic --noinput
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml run --rm web python manage.py migrate
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d
docker image prune -f   # old :latest layers otherwise accumulate until the disk fills
```

### Rollback

Every deploy is tagged with its commit SHA:

```sh
ssh user@vps
cd /srv/nikkocomidoy
export GITHUB_REPOSITORY=owner/repo IMAGE_TAG=<known-good commit sha>
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml pull web
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d web
```

Migrations are not reversed automatically. If a bad deploy shipped a destructive migration, run
`manage.py migrate <app> <previous_migration>` before `up -d`.

### Backups

The `cron` container runs `dbbackup --clean` nightly at 03:17 into `DBBACKUP_BUCKET`, keeping the
latest 14. Do a restore drill once; the commands are in [docs/aws-setup.md](docs/aws-setup.md#backups-and-restore).

## Added by seedkit (2026-10-05): Wagtail CMS

The hand-rolled CMS models were replaced with Wagtail pages:

| Before | Now |
|---|---|
| `core.Profile` + `Experience` / `SkillGroup` / `Education` / `Certification` | `core.HomePage` (site root, `/`) with inline panels |
| `core.Page` at `/p/<slug>/` | `core.ContentPage` at `/<slug>/` (*Show in menus* / *Show in footer*) |
| `blog.Post` (`status`, `publish_at`, `published_at`) | `blog.BlogPostPage` under `blog.BlogIndexPage` (`live`, `queue_status`, `publish_after`, `first_published_at`) |
| comma-separated `tags` | taggit tags (`?tag=` filter) |
| Markdown `body` | StreamField (`core/blocks.py`) |
| `blog.TopicIdea` admin | Wagtail snippet with a *Draft a post with Claude now* button |
| Django admin actions | Wagtail Publish; *Share to Facebook* in the page header's more menu |

In production, `core.middleware.AdminCSPMiddleware` applies `SECURE_CSP_ADMIN` to `/admin/` and
`/django-admin/`. It allows inline scripts because Wagtail's InlinePanel and date pickers need
them, and allows same-origin frames for live preview. Public pages keep the nonce-based policy.

Built with [Seedkit](https://github.com/viewflow/seedkit).
