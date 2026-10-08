# AWS + Facebook setup (one-time)

Target: one EC2 instance running Docker Compose (Caddy → gunicorn, cron, Postgres 17),
static + media in S3, mail through SES, deployed by GitHub Actions on every push to `main`.
Rough cost: t4g.small (~US$12/mo) + S3/SES pennies.

## 1. S3 buckets

Create two buckets in your account's region (this account: `us-east-2`, Ohio):

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

## 2. IAM role for the server (no access keys)

The app gets S3 access from an **instance role** attached to the EC2 server: AWS hands the
server short-lived credentials automatically, so there are no long-lived keys to store or leak.
Leave `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` **empty** in `deploy/.env.prod`.

1. IAM → **Roles** → **Create role** → *Trusted entity type*: **AWS service** →
   *Use case*: **EC2** → Next → skip *Add permissions* → Next.
2. Role name `nikkocomidoy-ec2` → **Create role**.
3. Open the role → **Add permissions** → **Create inline policy** → **JSON** → paste (change the
   bucket names if yours differ) → name it `s3-access` → **Create policy**:

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

You attach this role to the server when you launch it (section 4).

## 3. Email (Gmail SMTP)

This account can't create IAM users, which Amazon SES SMTP credentials require, so the site
sends through Gmail. That covers a personal site's volume (password resets, the daily
AI-draft review email) without a domain or SES approval.

1. Turn on **2-Step Verification** for the Google account: <https://myaccount.google.com/security>.
2. Create an **app password**: <https://myaccount.google.com/apppasswords> → name it
   `nikkocomidoy` → copy the 16-character password (shown once).
3. In `deploy/.env.prod`: `DJANGO_MAIL_PASSWORD=<app password>`; the other Gmail values are
   pre-filled in `deploy/.env.prod.example`.
4. After deploying, test it on the server:
   `docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml exec web python manage.py send_test_email nikkomidoy@gmail.com`

Later, to send from your own domain: switch to Amazon SES through the instance role
(django-anymail's SES backend), which needs no SMTP user.

## 4. EC2

1. Launch **Ubuntu 24.04 LTS**, `t4g.small` (arm64; the image is built for arm64 + amd64), 20 GB gp3.
   Under **Advanced details**:
   - **IAM instance profile**: `nikkocomidoy-ec2` (the role from section 2).
   - **Metadata version**: *V2 only (token required)*.
   - **Metadata response hop limit**: **2**. The app runs inside Docker containers, which are one
     network hop further from the server; with the default of 1 they can't fetch the role's
     credentials and every S3 upload fails with "Unable to locate credentials".
   Forgot? EC2 → the instance → **Actions → Security → Modify IAM role**, and
   **Actions → Instance settings → Modify instance metadata options** (hop limit 2).
2. Security group: inbound 22, 80, 443 from anywhere. Port 22 must stay open to
   `0.0.0.0/0` because GitHub Actions deploys over SSH from changing IP addresses; it is
   key-only (Ubuntu disables password login), so keep your private keys safe.
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
