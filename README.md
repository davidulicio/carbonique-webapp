# Carbonique webapp

A unified Django application for Carbonique eddy covariance site operations, instrument records and scientific context. It brings together the workflows of **carbonique-field-log**, **EcoFlux_resources** and **carbonique_fieldnotes**.

The workspace includes site condition notices, a shared PDF protocol library,
tower videos/GIFs, versioned ICOS BADM records with validation and site exports,
the complete supplied inventory snapshot, Carbonique typography/colours, and
read-only tower monitoring adapted from EC-Monitor. See
[the site resources and private VM configuration guide](docs/RESOURCES_AND_MONITORING.md).

This is a fresh application with its own database. The setup below imports
the supplied reference records and protocols; no existing EcoFlux database
or account is required. Configure actual tower connections privately on
the VM.

## Project guide

Start with **[Application overview](docs/OVERVIEW.md)**. Its two sections explain
how to use the app and how the implementation works, including the main files,
data flow and troubleshooting steps. Detailed deployment, import and resource
guides are linked from there.

## Start locally

Requires **Python 3.12 or newer** (tested with Python 3.12), a modern browser, and no Node build step. SQLite is included with Python. Windows runs the Django development server; Gunicorn is for Linux production servers.

### Windows PowerShell

Open the `carbonique-webapp` repository root in PowerShell. Run commands one at a time, stopping if any command fails. If Python 3.12 is missing, install it before creating the environment. Then run:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py setup_hub --with-reference
.\.venv\Scripts\python.exe manage.py createsuperuser
.\.venv\Scripts\python.exe manage.py runserver
```

If your installed Python is newer, use `py -m venv .venv` instead of `py -3.12`.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py setup_hub --with-reference
python manage.py createsuperuser
python manage.py runserver
```

Open **http://127.0.0.1:8000/** for the team workspace and **http://127.0.0.1:8000/fieldnotes/** for the public Field Notes. No passwords or default login accounts are included.

`setup_hub --with-reference` imports the supplied repository snapshot: **6 sites, 127 classified visit summaries, 19 data caveats, photographs, diagnostic plots and instrument reference information**. The caveats enter the editable database as drafts; a researcher reviews them. The supplied export does not include the full live equipment database or Firebase task history. They are not required for this installation. Documented instrument specifications and all supplied inventory-export content are included; additional individual equipment records can be entered in the app.

To start without the bundled records, use `python manage.py setup_hub` without `--with-reference` and create sites under Administration.

## Calibration logs and technical references

Each site has a **Calibration log** tab under **Sites & instruments**. Record a
sensor swap, on-site calibration or lab calibration, including removed and
replacement serials, preparation, dates, comments and supporting files. The
on-site Field work panel also opens this form with the active visit selected.
Calibration records and their files can be queued offline on a prepared device.

**Reference library** holds site-specific and shared hardware documents, wiring,
troubleshooting, repair notes and OneNote web sharing links. Upload originals,
preview PDFs and images, search by category/site, and archive or restore entries
and files. These library changes require a connection. Members and higher roles
can contribute; viewers can read and download. Shared entries require
network-wide access to edit. These new sections remain internal.

The supplied historical notes include **18 completed sensor/analyzer swaps**.
`setup_hub --with-reference` installs these records, with source-visit links and
cleaned/calibrated replacement preparation reflecting project practice, including
malfunction replacements. Unknown serials and lab dates remain blank. Existing
installations can run `python manage.py import_calibrations`; rerunning preserves
edits and archived records. Use `--dry-run` to inspect matches first.

See [Calibration and reference workflows](docs/CALIBRATIONS_AND_REFERENCES.md)
for details, limits and upgrade instructions.

## Public Field Notes: current records, read only

Open **/fieldnotes/** without signing in. The server builds this report from the
current database: site descriptions and conditions, field visits and observations,
and data caveats. Saving a change in the team workspace updates the report on its
next page load. Draft caveats are labeled awaiting review; resolved caveats remain
visible with their status. The timeline includes both visits and caveats and
updates their markers from the same records. Use **Refresh public site** to load
saved changes, including current site conditions. There is no separate
publication checkbox; offline changes must finish synchronizing first.

The report retains the supplied site photographs, diagnostic plots, tower
diagrams, common setup and processing INI downloads. Inventory, BADM, protocols,
monitoring, accounts and newly uploaded operational attachments stay in the
authenticated workspace. Public visitors have no editing controls or write API.

**Download HTML** produces a self-contained snapshot with embedded assets and
INI downloads. It can be shared or hosted on GitHub Pages, but must be exported
again after later changes. The live app requires a Django server. `/reference/`
redirects to the same report. `public/fieldnotes/index.html` is retained only as
the original source archive; replacing it does not change the live report.
See [Public site behavior](docs/PUBLIC_SITE.md).

## What the team workspace includes

| Section | Features |
|---|---|
| Overview | Site network, editable site conditions, pending tasks, visits and unresolved caveats |
| Field work | Off-site planning; on-site visits; tasks; observations; checklists; documents, images, audio and video attached to individual notes |
| History | Searchable visits and all task activity, classifications, frozen report revisions, CSV exports and attachments |
| Sites & instruments | Tabs for reference metadata, sensor-height/deployment history, site equipment, visits, photos/documents and DOI records |
| Data & processing | Draft/reviewed/resolved caveats, evidence, current INI file library with revision history, and scientific configuration history |
| Inventory | Serial numbers, models, current locations, service-history/files tabs and archived equipment |
| Site resources | ICOS BADM records, completeness checks and exports; tower photos, videos and GIFs |
| Protocols | In-app PDF reading, downloads and manager/admin document uploads |
| Tower monitoring | Read-only network and individual tower checks, diagnostics and recent snapshot charts |
| Administration | Sites, accounts, roles, site access and maintenance checklists |

The selected site is shared by all sections. The browser polls changes every 15 seconds while online, and uploads queued operations when connectivity returns.

## Roles

| Role | Read records | Field work / attachments | Scientific records / inventory | Team and sites |
|---|---|---|---|---|
| Viewer | Yes | No | No | No |
| Member | Yes | Yes; may propose draft caveats | Service observations only | No |
| Researcher | Yes | Yes | Yes; may review caveats and create configurations | No |
| Manager | Yes | Yes | Yes; also site conditions, BADM, protocols and tower media | No |
| Admin | Yes | Yes | Yes | Yes |

Only managers and administrators edit site conditions, BADM, protocols and tower media. Every team role with site access can download BADM/protocols and view monitoring. A superuser is an administrator. Other accounts need a `TeamMember` role. An empty allowed-sites list means all sites; selecting sites restricts access to those sites. The public site/visit/caveat report is visible to everyone independently of team site restrictions. Write these records with that public audience in mind. Create accounts in Administration; passwords are hashed by Django. No automatic invitation email is sent.

## Offline fieldwork

1. Sign in while connected, on a trusted device.
2. Use **Prepare for fieldwork** and select the sites and attachments to download.
3. Open the prepared site. Visits, tasks, observations, draft issues and their files are stored in IndexedDB before upload. Each note and its dependent files enter the queue together; upload order preserves their associations.
4. The app can be reopened offline after its shell and site data have been prepared. This needs **HTTPS**, or `localhost` / `127.0.0.1` during development.
5. Reconnect and open the app. Check that the sync queue is empty before clearing the device.

The interface distinguishes local pending records from synchronized data. Retried operations and uploads use stable identifiers, avoiding duplicate records. Conflicting edits pause the queue and require review rather than silently overwriting another user's work. Use **Sync queue** to review, retry or export a blocked record.

The app must be open to upload; it does not promise synchronization while a phone/browser is closed. New-device login requires a connection. Server sessions can expire while offline: sign in again with the original account to upload its queued work. Browser storage can be cleared by the operating system; keep pending records synchronized when possible. Sign out and clear the device only after resolving pending work.

## Scientific record conventions

- Logger/measurement times use **fixed EST, UTC−05:00**, without daylight saving time. The configuration and caveat editors explicitly convert those timestamps to UTC for storage.
- Visit and installation timestamps use actual instants; the UI displays local browser time.
- Unknown historical boundaries remain unspecified, with an explanatory period label. The import does not infer questionable timestamps from caveat prose.
- Instrument deployment periods cannot overlap for the same individual instrument.
- Configuration records are immutable; a correction creates a new version linked to its predecessor.
- Closing a visit freezes a report. Reopening a task does not change an earlier report. Reopening and reclosing a visit creates another report revision.
- Sites, tasks and equipment are archived, not deleted through the working app.

## Supplied records and a fresh database

`migrate` creates the new database schema. `setup_hub --with-reference` loads
the bundled reference and maintenance checklists without requiring Hank's
database. It includes the six sites, 127 classified visit summaries, 19 caveats,
site/instrument descriptions, photos, diagnostic plots, eight historical processing
INI files, twenty current INI source copies and seven protocol PDFs. The scientific records retain their source IDs
and uncertainties. Site conditions, new field operations and additional BADM
records are maintained in this app.

See [docs/IMPORTS.md](docs/IMPORTS.md) for the source map and repeat imports, and
[the INI library guide](docs/PROCESSING_FILES.md) for file updates and revisions. Create your own administrator account; old
accounts and passwords are not imported.

## Updating INI files

In **Data & processing → TraceAnalysis INI library**, researchers, managers and admins
can select multiple `.ini` files, drop files onto the panel or choose a folder.
Changed files create immutable revisions; uploading identical current bytes
does not create a duplicate. Read, download and inspect prior revisions there.
All team roles can read files permitted by their site access. Shared/unassigned
files require network-wide access to update. Uploads need a connection.

Twenty files copied from the supplied TraceAnalysis directory initialize the
library. Original files are never changed or executed. See
[Processing files](docs/PROCESSING_FILES.md) for limits and repeat imports.

## Deployment

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for Linux/Gunicorn and Docker
Compose with PostgreSQL. GitHub stores source; GitHub Pages can host an exported
public snapshot, while the live report and team workspace require the server.
Serve at the root of a dedicated hostname; subpath hosting is not configured.

Before production, set a random `SECRET_KEY`, `DEBUG=False`, allowed hostname,
HTTPS/CSRF settings, persistent database/media and SMTP for password resets.
The app rejects the development secret with `DEBUG=False`.

For an existing installation: back up database/media, deploy source, run
`python manage.py migrate`, `python manage.py import_resources` and
`python manage.py collectstatic --noinput`, then restart the service. Imports
preserve existing records and later INI uploads.

## Checks and backups

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test hub
python manage.py collectstatic --noinput
python manage.py backup_hub --output backups/carbonique.zip
```

`backup_hub` includes fixture data and uploaded files. Pause writers before portable backups for a consistent snapshot. Use native database backups plus media backups for production. Keep backups private: they contain research records and account password hashes. Restore into a migrated, empty database using:

```bash
python manage.py restore_hub --file /path/to/carbonique.zip
```

The live public report is rebuilt from database records and stored scientific images/INIs. Back up database and media together; keep bundled source archives under Git.

## Important information for GitHub users

This repository contains the standalone application. Run commands from its root;
there is one Django entry point, `manage.py`. GitHub stores the source; the running
service and its persistent data belong on a VM or another Django-capable host.

- **Public content:** `/fieldnotes/` exposes all sites, visits and caveats when
  `PUBLIC_FIELDNOTES_ENABLED=True`, the default. Drafts and resolved caveats are
  included and labeled. Uploaded note files remain protected. The bundled `seed/`
  and historical HTML source files are also part of the repository.
- **Private configuration:** never commit `.env`, actual tower connection files,
  credentials, databases, uploaded media or backups. `.env.example` contains local
  development placeholders; use new production secrets.
- **Protocol catalogue:** seven PDFs are included. The data-download protocol
  has been retired and is removed by the upgrade migration.

- **Read-only monitoring:** tower queries are restricted on the server. Configure
  private network access on the VM; the application provides no instrument controls.
- **Scientific scope:** supplied visit descriptions are classified summaries,
  and ICOS BADM checks are local completeness checks requiring scientific review.
  The repository does not contain the complete live EcoFlux database.
- **Changes and support:** reproduce problems with the checks below and include
  the affected page, expected behavior and sanitized error output in an issue.
  Keep research records, accounts, hostnames and credentials out of public issues.
- **Attribution:** retain upstream author notices and bundled third-party licenses.
  See [UPSTREAM.md](UPSTREAM.md); this repository does not grant a blanket new
  license to the inherited code, scientific content or Carbonique branding.

## Upstream and implementation notes

See **[UPSTREAM.md](UPSTREAM.md)** for source provenance and **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** for data relationships, API and synchronization behavior. **[docs/VALIDATION.md](docs/VALIDATION.md)** records the checks performed for this build.
