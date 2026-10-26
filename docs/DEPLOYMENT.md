# Running Carbonique Hub in production

Before installing or updating, follow the [26 October security maintenance supplement](SECURITY_MAINTENANCE.md), including Python and host patch requirements.

For the existing Alliance Arbutus Ubuntu VM, start with the detailed
[Arbutus installation guide](ARBUTUS_INSTALLATION.md) and
[printable PDF](Carbonique_Arbutus_Installation_Guide.pdf). Its named-host proxy
example preserves other websites and uses loopback port 8010.

Read [Security and deployment review](../SECURITY.md) before launch. Use
`deploy/production.env.example` as the production configuration reference.

The source supports a normal Django deployment. It has not been deployed to your live server. Use a dedicated hostname and serve at `/`; the browser API and service-worker paths assume the hostname root.

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
TRUSTED_PROXY_NETWORKS=127.0.0.1/32,::1/128
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
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

Database and media have persistent named volumes. The public report reads those current records; it does not require an HTML bind mount. Do not use `docker compose down -v` unless intentionally deleting persistent data.

## Update from GitHub

GitHub Pages cannot run Django. Your host must clone/pull or receive the source and restart/redeploy the backend when Python or frontend code changes.

For a Linux checkout:

```bash
git pull
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py import_resources
python manage.py import_calibrations
python manage.py collectstatic --noinput
sudo systemctl restart carbonique
```

Changes made through team editors appear on the next public page load without a code deployment. Re-export any separately hosted HTML snapshot after updates. Replacing the historical source HTML does not update the live report. See [Public site](PUBLIC_SITE.md).

For site conditions, BADM, protocols, videos and read-only tower polling, see
[Resources and monitoring](RESOURCES_AND_MONITORING.md). The private monitor
configuration stays outside the checkout/image; the VM needs private routing to
the analyzers. The supplied nginx template allows 100 MiB tower media uploads.

## Public and private views

- `/fieldnotes/`: current public sites, visits and caveats, available by default.
- `/fieldnotes/download/`: self-contained public HTML snapshot.
- `/reference/`: redirect to the same live report.
- `/`: authenticated team application.
- `/admin/`: Django staff/superuser administration.
- `/health/`: database connectivity healthcheck; no research records.

The public report is sandboxed without same-origin privileges. All assets are embedded; no private APIs are called. Disable all public report routes with `PUBLIC_FIELDNOTES_ENABLED=False`. GitHub Pages may serve an exported snapshot; live updates require the Django server.

## Backups and restore

Use `pg_dump` or your database's normal tooling plus the media directory for live production backups. The portable `backup_hub` command includes Django fixture data and media; pause writers while it runs to keep database and files consistent. Store backups off-server and outside the repository. Secrets such as SECRET_KEY and SMTP credentials are not included and need their own secure configuration backup.

Restore portable backups only into an empty, migrated database and empty media directory. `restore_hub` refuses to overwrite an existing workspace and validates archive paths. Verify file counts and open representative attachments after restore. Back up protected INI revisions and attachments with the database; keep source archives under Git.

## Login protection and proxy limits

Install all requirements and run migrations before restarting an updated
service. Django Axes stores failed logins in the database. Five failures for the
same username/client address pause further attempts for 15 minutes. Both the
team and admin login are covered; browser/session changes do not reset the
counter. Recover an accidental lockout with
`python manage.py axes_reset_username USERNAME` from the server console.

nginx limits authentication POSTs and expensive public-report rendering
separately from ordinary requests and static assets. Adapt the limits to shared
campus/VPN traffic and run `nginx -t` before reload. Its access log format redacts
reset paths and omits query/Referer values. Container Gunicorn access logging is
left off to avoid duplicating unredacted reset URLs; retain nginx logs and server
error logs with restricted access and rotation.

`X-Real-IP` is accepted only from TRUSTED_PROXY_NETWORKS while proxy mode is
on. nginx overwrites it with the client address. Docker deployments must list the
actual proxy/bridge peer explicitly. Never expose Gunicorn directly. A reverse
proxy or VPN with MFA should protect administrator access. No native MFA is
included in the application. Default device passwords require separate tower
network protection even though this app does not use those passwords.
