# Validation and release checks

The standalone application was checked on Windows with Python 3.12 and
Django 5.2.18. Its 167 backend tests cover field workflows, role/site restrictions,
retry-safe operations, version conflicts, frozen reports, imports, resource
permissions, BADM checks/exports, protected media, live public reports, imported
caveat review, per-note uploads, INI revisioning, synchronized caveat timelines,
site-condition publication, snapshot refresh behavior and read-only monitoring.

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
node --check static/hub/record-resources.js
node --check static/hub/resources.js
node --check static/hub/monitor.js
node --check static/hub/pdf-viewer.js
node --check static/hub/storage.js
node --check static/hub/sw.js
node --check static/hub/processing-files.js
node --check static/hub/public-report.js
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
public report retains the supplied scientific material and uses native browser
downloads. The latest isolated browser checks covered resolving an imported
caveat while retaining eight linked configurations, current public status and
site diagrams/photos, a second INI revision with its original retained, planning
attachments, offline note/photo/document persistence across a full reload,
reconnection without duplicate uploads, and files added to a closed visit note.
No test accounts or test scientific edits are installed in the working database.

## Deployment validation

The target VM, live instruments, production TLS, SMTP and operational databases
have not been exercised. Container examples are supplied, but this local release
check does not run Docker or PostgreSQL. Validate these on the intended host.

For the first installation, initialize a new database from the supplied reference,
reconcile counts, inspect representative attachments and test the team's roles.
For later upgrades, validate against a staging database/media copy first. Verify private routing to analyzers, service startup, timestamps,
file limits and persistence across restarts. Test a backup restore before relying
on it. See [DEPLOYMENT.md](DEPLOYMENT.md) and [IMPORTS.md](IMPORTS.md).

## Calibration and reference update

The update adds 28 backend checks covering sensor swap validation, on-site/lab
records, linked visits, role and site restrictions, archive/restore, stale edits,
offline operation retries, calibration file association and protected downloads.
Library checks cover shared access, credential-free HTTP(S) links, exact file
bytes, image/PDF validation, batch size, duplicate retries, rollback cleanup and
public exclusion. Historical-import checks verify repeat runs preserve edits,
dry runs and missing visits do not write, and planned/cancelled swaps are omitted.

Browser verification used a separate SQLite database and harmless documents,
with a member and viewer account. The checks included a sensor swap with serials,
lab dates, comments, a linked visit and a queued file; an on-site calibration;
reference notes and OneNote link; search and shared filters; PDF rendering;
file archive/restore; and unavailable-server calibration recording, reload and
reconnection with an empty queue after synchronization. Test accounts, documents
and records are kept outside the application repository and live database.

## Security update

Twenty-one additional security tests cover persistent login lockouts, attempts
through both login routes, forged forwarding headers, cooldown/reset behavior,
password masking, CSRF, open redirects, host headers, private endpoints, CORS and
public write rejection. The complete suite now contains 167 tests. Dependency
and static-analysis results, triage, remaining VM checks and the point-in-time
limits of this review are documented in [SECURITY.md](../SECURITY.md).

The final installed-repository run passed all 167 tests after the security
migration. Browser smoke checks opened every main section, including
Administration, BADM, processing and the reference library. An imported caveat
was resolved successfully and then displayed as Resolved in the public report;
the public timeline remained present and displayed prose contained no em dashes.
Protected PDFs rendered without browser errors. A controlled HTTP 429 retained
a calibration as pending without a conflict, and a retry emptied the queue. A
fifth failed sign-in for a nonexistent QA account displayed the 15-minute pause
screen. These actions used an isolated database and cookie names; real user
accounts and scientific records were preserved.
