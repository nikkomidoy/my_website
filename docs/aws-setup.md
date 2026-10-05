# AWS + Facebook setup (one-time)

Target: one EC2 instance running Docker Compose (Caddy → gunicorn, cron, Postgres 17),
static + media in S3, mail through SES, deployed by GitHub Actions on every push to `main`.
Rough cost: t4g.small (~US$12/mo) + S3/SES pennies.

## 1. S3 buckets

Create two buckets in your region (e.g. `ca-central-1`):

| Bucket | Purpose | Public? |
|---|---|---|
| `nikkocomidoy-assets` | `static/` + `media/` | read-only on those two prefixes |
| `nikkocomidoy-backups` | nightly `pg_dump` | **private**, add a lifecycle rule (e.g. expire after 60 days) |

On the assets bucket: keep *Object Ownership = Bucket owner enforced*, turn off
"Block public access" for **bucket policies only**, enable versioning, and add:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadStaticMedia",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": [
      "arn:aws:s3:::nikkocomidoy-assets/static/*",
      "arn:aws:s3:::nikkocomidoy-assets/media/*"
    ]
  }]
}
```

CORS on the assets bucket (fonts/CSS loaded cross-origin):

```json
[{"AllowedMethods": ["GET", "HEAD"], "AllowedOrigins": ["https://YOUR_DOMAIN"], "AllowedHeaders": ["*"], "MaxAgeSeconds": 86400}]
```

Optional: put CloudFront in front and set `AWS_S3_CUSTOM_DOMAIN`.

## 2. IAM user for the app (least privilege)

Create user `nikkocomidoy-app`, attach this inline policy, create an access key and put it in
`deploy/.env.prod` (`AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY`):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect": "Allow", "Action": ["s3:ListBucket"],
     "Resource": ["arn:aws:s3:::nikkocomidoy-assets", "arn:aws:s3:::nikkocomidoy-backups"]},
    {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"],
     "Resource": ["arn:aws:s3:::nikkocomidoy-assets/*", "arn:aws:s3:::nikkocomidoy-backups/*"]}
  ]
}
```

## 3. SES (email)

Verify your domain in SES, request production access (out of the sandbox), then create
**SMTP credentials** → `DJANGO_MAIL_USERNAME` / `DJANGO_MAIL_PASSWORD`;
host `email-smtp.<region>.amazonaws.com`.

## 4. EC2

1. Launch **Ubuntu 24.04 LTS**, `t4g.small` (arm64; the image is built for arm64 + amd64), 20 GB gp3.
2. Security group: inbound 22 (your IP only), 80, 443.
3. Allocate an **Elastic IP** and point DNS `A` records for `YOUR_DOMAIN` and `www.YOUR_DOMAIN` at it.
4. Install Docker and prepare the deploy directory:

   ```sh
   ssh ubuntu@YOUR_IP
   curl -fsSL https://get.docker.com | sudo sh
   sudo usermod -aG docker ubuntu && newgrp docker
   sudo mkdir -p /srv/nikkocomidoy/deploy && sudo chown -R ubuntu: /srv/nikkocomidoy
   sudo timedatectl set-ntp true   # TOTP 2FA needs an accurate clock
   ```

5. Copy `deploy/.env.prod.example` to `/srv/nikkocomidoy/deploy/.env.prod` on the server and fill
   it in (`chmod 600`). Generate the secret key with
   `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`.

## 5. GitHub

Repository → Settings:

- **Secrets** (Actions): `SSH_HOST` (Elastic IP), `SSH_USER` (`ubuntu`), `SSH_KEY` (a deploy
  private key whose public half is in `~/.ssh/authorized_keys` on the server), `GHCR_TOKEN`
  (classic PAT with `read:packages`, used by the server to pull the image).
- **Variables**: `SITE_DOMAIN` = `YOUR_DOMAIN` (post-deploy smoke test).
- **Environments**: create `production` (optionally require approval).

Push to `main` → tests → image build → deploy → health check.

## 6. Facebook Page token

The Graph API can post to a **Page** you manage — not to a personal profile.

1. Create a Facebook Page for your blog (if you don't have one) and note its **Page ID**
   (Page → About → Page transparency, or `GET /me/accounts`).
2. At <https://developers.facebook.com/apps> create an app (type *Business*). Note the
   **App ID** and **App secret** → `FACEBOOK_APP_SECRET`.
3. In the **Graph API Explorer**, select the app, and generate a *User* token with
   `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
4. Exchange it for a long-lived user token:
   `GET /oauth/access_token?grant_type=fb_exchange_token&client_id=APP_ID&client_secret=APP_SECRET&fb_exchange_token=SHORT_TOKEN`
5. `GET /me/accounts?access_token=LONG_LIVED_USER_TOKEN` → the `access_token` for your Page is a
   **non-expiring Page token** → `FACEBOOK_PAGE_ACCESS_TOKEN`; its `id` → `FACEBOOK_PAGE_ID`.

As the app's admin posting to your own Page, the app can stay in development mode. If a share
fails, the error is stored on the post (Wagtail → the post → *Queue & Facebook* tab) and retried on
the next daily run; use **Share to Facebook** in the page header's more menu to retry manually.

## 7. Claude (AI fallback drafts)

Create an API key at <https://platform.claude.com> → `ANTHROPIC_API_KEY`. With the default
`BLOG_AI_AUTO_PUBLISH=False`, AI drafts are saved as *Needs review* and you get an email
(`DJANGO_ADMINS`); approve it in Wagtail by setting the daily queue to *Queued*, or just publish it.

## Backups and restore

The `cron` container runs `dbbackup --clean` nightly (03:17) into the backups bucket, keeping 14.
Restore drill (do one before you rely on it):

```sh
cd /srv/nikkocomidoy
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml exec -T web python manage.py listbackups
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml exec -T web python manage.py dbrestore --database=default
```
