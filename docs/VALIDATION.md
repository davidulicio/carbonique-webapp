# Validation and release checks

The standalone application was checked on Windows with Python 3.12 and
Django 5.2.18. Its 76 backend tests cover field workflows, role/site restrictions,
retry-safe operations, version conflicts, frozen reports, imports, resource
permissions, BADM checks/exports, protected media and read-only monitoring.

## Repeatable checks

From the repository root, using its Python environment:

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test hub
python manage.py collectstatic --noinput
```

JavaScript modules can be checked without a build step, using Node.js:

```bash
node --check static/hub/app.js
node --check static/hub/resources.js
node --check static/hub/monitor.js
node --check static/hub/pdf-viewer.js
node --check static/hub/storage.js
node --check static/hub/sw.js
```

GitHub Actions runs these checks on Linux from
`.github/workflows/checks.yml`. Test accounts, temporary databases and generated
static files are excluded from Git.

## Scope

The monitor tests use simulated responses and a localhost TCP exchange to verify
the fixed read queries, parsing, diagnostic interpretation, stale/failure
handling, cooldowns and absence of private connection details in API output.
They do not establish connectivity to actual towers.

Browser checks during feature development covered the public report, offline
fieldwork/reconnection, site tabs, forms, mobile layout, multi-page protocol
reading, BADM forms, network checks and individual tower status. The standalone
public report retains the supplied data and uses native browser downloads.

## Deployment validation

The target VM, live instruments, production TLS, SMTP and operational databases
have not been exercised. Container examples are supplied, but this local release
check does not run Docker or PostgreSQL. Validate these on the intended host.

For the first installation, initialize a new database from the supplied reference,
reconcile counts, inspect representative attachments and test the team's roles.
For later upgrades, validate against a staging database/media copy first. Verify private routing to analyzers, service startup, timestamps,
file limits and persistence across restarts. Test a backup restore before relying
on it. See [DEPLOYMENT.md](DEPLOYMENT.md) and [IMPORTS.md](IMPORTS.md).
