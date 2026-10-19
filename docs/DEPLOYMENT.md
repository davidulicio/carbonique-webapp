# Running Carbonique Hub in production

The source is ready for a normal Django deployment. It has not been deployed to your live server. Use a dedicated hostname and serve at `/`; the browser API and service-worker paths assume the hostname root.

## Linux with Gunicorn

1. Copy/clone the repository to `/srv/carbonique-webapp`, create a Python virtual environment and install `requirements.txt`.
2. Copy `.env.example` to `.env` and set production values.
3. Generate a random secret:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

4. Set:

```dotenv
DEBUG=False
SECRET_KEY=your-generated-secret-at-least-50-characters
ALLOWED_HOSTS=carbonique.example.org,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://carbonique.example.org
DATABASE_URL=postgresql://carbonique:your-url-encoded-password@localhost:5432/carbonique
MEDIA_ROOT=/srv/carbonique-media
TRUST_PROXY_HEADERS=True
PUBLIC_FIELDNOTES_ENABLED=True
```

Trust proxy headers only when the application port is inaccessible to external clients and nginx overwrites `X-Forwarded-Proto`. URL-encode special characters in a DATABASE_URL password. Create a new database for this application; no existing EcoFlux database is required.

5. Give the service account write access to the media directory. Run:

```bash
python manage.py migrate
python manage.py setup_hub --with-reference
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py check --deploy
gunicorn carbonique.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 120
```

6. Configure HTTPS and nginx from `deploy/nginx.conf.example`. For a persistent process, adapt `deploy/carbonique.service.example` and enable it with systemd.

WhiteNoise serves static assets. Uploaded files are served by permission-checked Django views; do not create a public media alias in nginx. Keep database and media backups together. PostgreSQL is preferable for concurrent multi-user production writes; SQLite is the local quick-start default.

SMTP settings must point to a real mail service for password reset emails. The console email backend is useful locally but does not send emails.

## Docker Compose with PostgreSQL

Requires Docker with Compose. Containers have not been executed in the build environment; use the backend tests and staging checks before a production deployment.

1. Create `.env` from `.env.example` and set a production secret, hostname and CSRF origin as above.
2. Add `POSTGRES_PASSWORD` with a strong password consisting of URL-safe characters, because Compose interpolates it into DATABASE_URL. Compose forces `DEBUG=False` and uses PostgreSQL.
3. Build and initialize:

```bash
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py setup_hub --with-reference
docker compose run --rm web python manage.py createsuperuser
docker compose up -d web
```

4. Put the HTTPS reverse proxy in front of `127.0.0.1:8000`. Include `localhost,127.0.0.1` in ALLOWED_HOSTS for the internal healthcheck.

Database and media have persistent named volumes. `public/fieldnotes/` is bind-mounted read-only into the container, so replacing its HTML on the host updates the public report without rebuilding the image. Do not use `docker compose down -v` unless intentionally deleting persistent data.

## Update from GitHub

GitHub Pages cannot run Django. Your host must clone/pull or receive the source and restart/redeploy the backend when Python or frontend code changes.

For a Linux checkout:

```bash
git pull
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py import_resources
python manage.py collectstatic --noinput
sudo systemctl restart carbonique
```

For a pure Field Notes replacement in `public/fieldnotes/index.html`, a source pull/file copy is enough; Django reads the current file at each request. Keep local uncommitted report changes separate from Git updates or commit them first.

For site conditions, BADM, protocols, videos and read-only tower polling, see
[Resources and monitoring](RESOURCES_AND_MONITORING.md). The private monitor
configuration stays outside the checkout/image; the VM needs private routing to
the analyzers. The supplied nginx template allows 100 MiB tower media uploads.

## Public and private views

- `/fieldnotes/`: public original report, available by default. Replacing its HTML updates only that public snapshot.
- `/reference/`: optional database-generated selected site/caveat reference, disabled by default. It excludes private team operations.
- `/`: authenticated team application.
- `/admin/`: Django staff/superuser administration.
- `/health/`: database connectivity healthcheck; no research records.

The public HTML is sandboxed without same-origin privileges. Do not add external scripts or separate relative files to it; use a self-contained report as in the original repository.

## Backups and restore

Use `pg_dump` or your database's normal tooling plus the media directory for live production backups. The portable `backup_hub` command includes Django fixture data and media; pause writers while it runs to keep database and files consistent. Store backups off-server and outside the repository. Secrets such as SECRET_KEY and SMTP credentials are not included and need their own secure configuration backup.

Restore portable backups only into an empty, migrated database and empty media directory. `restore_hub` refuses to overwrite an existing workspace and validates archive paths. Verify file counts and open representative attachments after restore. Keep the public HTML under Git version control.
