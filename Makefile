.PHONY: install dev runserver migrate makemigrations shell superuser createsuperuser test cov lint fmt fix typecheck css cron collectstatic deploy-migrate deploy

DC = docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml

install:
	uv sync
	uv run pre-commit install

# runserver + Tailwind watcher in one process
dev:
	uv run manage.py tailwind runserver

runserver:
	uv run manage.py runserver

migrate:
	uv run manage.py migrate

makemigrations:
	uv run manage.py makemigrations

shell:
	uv run manage.py shell_plus

superuser createsuperuser:
	uv run manage.py createsuperuser

test:
	uv run pytest

cov:
	uv run pytest --cov --cov-report=html

lint:
	uv run ruff check .

fmt:
	uv run ruff format .

fix:
	uv run ruff check . --fix
	uv run ruff format .

typecheck:
	uv run pyright

css:
	uv run manage.py tailwind build

# Scheduler: daily blog/Facebook job, nightly backup, GDPR purge
cron:
	uv run manage.py crontask

collectstatic:
	uv run manage.py collectstatic --noinput

# Manual deploy on the EC2 host (CI does this automatically on push to main)
deploy-migrate:
	$(DC) run --rm web python manage.py collectstatic --noinput
	$(DC) run --rm web python manage.py migrate

deploy: deploy-migrate
	$(DC) up -d
