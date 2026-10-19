# Application overview

Carbonique webapp brings field operations, site and instrument reference,
scientific metadata, protocols and tower diagnostics into one workspace. The
team workspace requires an account. It starts with a new database populated
from the supplied reference materials; an existing EcoFlux database is not required. A separate public Field Notes report is
available without signing in when enabled by the server administrator.

## 1. How to use the app

### Sign in and choose a site

Open the application homepage and sign in with your team account. An
administrator creates accounts and assigns a role and, where needed, a list of
accessible sites. The site selector carries your selected site across sections.
The Overview shows your accessible network, outstanding work, recent visits and
data caveats. Open a site card to inspect its workspace.

Read the **site condition** before planning a visit. A manager can record flooding,
hunting restrictions, access arrangements or other conditions, along with a
review/restriction date. An overdue date means the statement needs review; it
does not automatically declare the site open or safe.

### Choose the section for your task

| Section | Use it for |
|---|---|
| Overview | Scan the network and site conditions; choose where to work |
| Field work | Plan tasks, start a visit, record observations and work, and close the visit |
| History | Find previous visits, task activity, frozen reports and exports |
| Sites & instruments | Read site descriptions, sensor arrangements, deployments, assigned equipment, files and data identifiers; view tower media |
| BADM | Enter or review site metadata, inspect missing information and download a site export |
| Data & processing | Record affected data periods, caveats, evidence and versioned processing configurations |
| Inventory | Track individual instruments, serial numbers, locations and service history across the network |
| Protocols | Read maintenance/safety PDFs in the app and download originals |
| Tower status | Check all accessible towers or open one tower's measurements and diagnostics |
| Administration | Manage sites, accounts, roles, site access and maintenance checklists |

Site reference describes the installed arrangement. Inventory tracks individual
equipment identities and service history. Field work records what happened on a
visit; Data & processing records its scientific consequences. The public report
reads sites, visits and caveats directly from these records on each page load.

### Plan, record and finish field work

1. Choose a site, review its condition, protocols and outstanding tasks, and plan
   work using a checklist or individual tasks.
2. Start a visit and record the crew, work completed, observations, unplanned
   work and supporting photos/documents. Link records to equipment where useful.
3. Record a data caveat when an event affects measurements; include the affected
   period, variables, evidence and proposed handling. Researchers review drafts.
4. Close the visit after reviewing its contents. Closing creates a frozen report.
   Later task changes do not rewrite that report. Reopening and reclosing a visit
   creates another report revision.
5. Use History to retrieve the visit, its reports and task activity. Expand
   **Individual notes & attachments** to read or add files to a particular note.

Planning notes, on-site observations and task activity each accept documents,
images, audio and video, both when recorded and later. Note files stay associated
with that individual entry. Files added after closure do not rewrite a frozen
report. Files are queued with their notes offline; the default limit is 25 MiB
per file. Audio/video support protected range requests for playback and seeking.

### Prepare for disconnected work

While online, use **Prepare for fieldwork**, select the sites and choose whether
to download attachments and protocols. Preparation saves the app shell and
selected records on that device. HTTPS is required except for local development.

Open the prepared site before leaving. Offline field records enter a local sync
queue and remain visible as pending. Reopen the app after reconnecting and wait
for the queue to empty. If a session expired, sign in with the same account. Use
**Sync queue** to inspect a conflict, retry, or export a blocked record. Keep the
app open while uploading. Synchronize before signing out, clearing browser
storage or changing devices; pending records are held only on that device.

### Maintain site resources

Managers and administrators with site access can edit conditions, BADM,
protocols and tower media. Other permitted users can read these resources and
download installed protocols and BADM exports.

- **BADM:** confirm the station class and assigned ICOS identifier, then create
  records using the official variable groups. Records may repeat for different
  instruments or periods. Save incomplete work as drafts, inspect validation
  messages, and review applicable groups. The checklist reports local completeness;
  ICOS ETC review is still required. A site ZIP contains grouped CSV files, full
  JSON records, definitions, provenance and validation results.
- **Protocols:** open a document to read it or download the PDF. Managers can
  upload documents, replace revisions and archive entries. Seven protocols are
  bundled; the retired data-download procedure is removed on upgrade.
- **Tower media:** upload MP4, WebM, GIF, WebP, JPEG or PNG under the site's
  resource controls. Files remain protected by site access. The default limit
  is 100 MiB per item.

These resource editors and monitoring need a connection. Offline fieldwork
supports the queued operations described above; it does not queue every
administrative or scientific editor.

### Check tower status

Open Tower status and select **Check all towers**. Open a tower card for its
measurements, gas/flow/wind information, diagnostics, recording indicators and
recent snapshot charts. **Check this tower** requests an individual check.
Checks have a shared cooldown to avoid repeated connections.

Always read the check time and data age. Missing configuration, unreachable
instruments, stale readings and reported faults have distinct states. A failed
check may leave an older reading visible with its earlier timestamp. These are
diagnostic snapshots, not continuous scientific data. The interface provides
no calibration, restart, settings or logging controls, including for admins.

### Understand access and public information

Viewers read records. Members record field work. Researchers also maintain
scientific records and inventory. Managers additionally maintain site resources;
administrators manage accounts and sites. Site restrictions apply on the server,
not just to visible buttons. See the role table in the [README](../README.md).

`/fieldnotes/` is the public read-only report. Site descriptions/conditions,
visits and caveats update on its next load after a team edit. Drafts are labeled
awaiting review; resolved caveats remain visible. Inventory, BADM, protocols,
monitoring and uploaded note files require team access. **Download HTML** saves
a self-contained public snapshot; `/reference/` redirects to the same live report.
The timeline includes visits and caveats, with unknown affected dates kept in a
separate area. Use **Refresh public site** to reload all current public records;
changes queued offline must upload first. See [Public site](PUBLIC_SITE.md).

### Update processing INIs

Open **Data & processing → TraceAnalysis INI library** to read/download current files,
inspect versions or upload multiple files/a folder. Researchers, managers and
admins with the appropriate site access may upload. Changed files add revisions;
identical current bytes are skipped. Twenty source copies initialize this library.
The eight original configuration evidence files remain under Scientific
configuration history. The source directory is never modified or executed.
See [Processing files](PROCESSING_FILES.md).

## 2. Technical aspects and how it works

### Runtime and repository map

The app uses Python/Django with Django REST Framework, a same-origin JavaScript
frontend, and SQLite locally or PostgreSQL for a production VM. There is no
frontend build pipeline. WhiteNoise serves static assets; Gunicorn runs the
production application behind an HTTPS reverse proxy. Docker Compose is an
alternative deployment package.

| Path | Responsibility / starting point for changes |
|---|---|
| `manage.py`, `carbonique/settings.py`, `carbonique/urls.py` | Startup, environment settings and all URL/API registration |
| `inventory/models.py`, `inventory/migrations/` | Compatible EcoFlux site, equipment, field-note and attachment records |
| `hub/models.py`, `hub/resources_models.py`, `hub/migrations/` | Visits, tasks, reports, deployments, caveats, roles, resources and monitoring snapshots |
| `hub/api.py`, `hub/serializers.py`, `hub/permissions.py` | Main APIs, validation, roles and site access |
| `hub/services.py` | Ordered field operations and retry/conflict handling |
| `hub/resources_api.py`, `hub/badm.py` | Conditions, protocols, media, BADM validation and exports |
| `hub/monitor.py`, `hub/licor.py` | Server-side tower queries, allowlist, cooldowns, snapshots and response redaction |
| `hub/views.py`, `hub/public_report.py`, `templates/` | Live public projection, page rendering and report export |
| `hub/processing_files.py`, `static/hub/processing-files.js` | Versioned INI validation, permissions, downloads and interface |
| `hub/media.py` | Protected attachment/site-media range streaming |
| `static/hub/app.js` | Navigation, workspace state and field/scientific forms |
| `static/hub/resources.js`, `monitor.js`, `pdf-viewer.js` | Resource editors, monitor interface and local PDF reader |
| `static/hub/storage.js`, `sw.js` | IndexedDB, outbox, prepared files and offline app shell |
| `seed/`, `public/fieldnotes/` | Bundled reference, current INI source copies and historical report archive |
| `hub/management/commands/`, `scripts/` | Setup, imports, backup/restore, polling and source extraction |
| `deploy/`, `Dockerfile`, `compose.yaml` | VM service, reverse proxy and container examples |
| `hub/tests.py`, `hub/test_resources.py`, `hub/test_monitor.py` | Backend workflow, resource and monitoring regression coverage |
| `.github/workflows/checks.yml` | Automated Django, migration, static-file and JavaScript checks |

### Main data and request flow

After session login, `/api/bootstrap/` supplies the role, accessible sites and
checklists. The chosen site's `/api/snapshot/` supplies its working records;
`/api/overview/` supplies network summaries. Dedicated APIs handle resources and
monitoring. Django checks the session, CSRF token on writes, role and site scope.
Uploaded files use permission-checked routes rather than a public media alias.

Sites are canonical records in `inventory`. Visits can link to original
EcoFlux field notes. Tasks have immutable activity rows; closed visits have
versioned frozen reports. Deployments associate instruments with sites and
nonoverlapping periods. Caveats link affected sites and evidence; configuration
corrections create new immutable versions. Import mappings retain source IDs and
prevent duplicate imports from overwriting later edits.

Logger and measurement timestamps use fixed EST, UTC−05:00, without daylight
saving time. The scientific editors convert those values to UTC for storage.
Visits represent actual instants and display in the browser's local time.
Do not infer precise historical boundaries from ambiguous prose.

### Offline synchronization and conflicts

The service worker caches the neutral app shell and static files. It does not
cache authenticated API responses. IndexedDB holds account-scoped site snapshots,
prepared attachments and an ordered outbox. Local operations project over the
last snapshot so a pending change remains visible before upload.

`POST /api/sync/` checks stable operation IDs and saves an operation receipt with
its result. Retrying the same ID and payload returns the previous result. A
different payload under an existing ID is rejected. Versioned edits require the
expected `base_version`; a stale edit returns a conflict instead of overwriting
another user. Batch processing stops at the first failure to preserve dependency
order. Inspect `results[].ok` and `results[].status` even when the batch response
is HTTP 200. Conflicted operations remain in the queue for review.

### BADM, PDFs and monitoring

BADM definitions live in `seed/badm/schema.json`, derived from 27 official ICOS
template workbooks with source hashes and version information. `hub/badm.py`
checks required values, formats, vocabularies and supported conditional rules;
manager review handles rules that need scientific interpretation. Production
reads the JSON directly. Regeneration uses the development script and openpyxl.

Protocol originals live in protected storage or the bundled protocol directory.
PDF.js is bundled locally, so reading does not send documents to an external
viewer. Site video supports range requests for playback while retaining access
checks. Seven protocol PDFs are bundled; the retired data-download procedure
is no longer catalogued or reimported.

Tower checks read a private server file named by `MONITOR_STATIONS_FILE`. The
server sends only fixed, allowlisted read queries over TCP 7200 and returns
sanitized measurements. The browser never receives the tower connection
addresses or a general command interface. A per-site database cooldown limits
requests across users/workers. Page checks collect on demand; a separate
`poll_towers` process can collect while the page is closed. The display shows up
to 24 hours of snapshots, and the collector retains seven days.

### Development and deployment workflow

Follow the [README quick start](../README.md#start-locally), then make changes
from the repository root. After model changes, create and inspect migrations;
keep existing upstream migration identities. After changing cached frontend
assets, review the service worker's cache version/update behavior.

Run the checks in [VALIDATION.md](VALIDATION.md) before committing. Add a focused
regression for changed behavior, especially permissions, imports, conflicts or
instrument query restrictions. For UI changes, verify the relevant flow in a
browser, at a narrow viewport and offline when applicable.

On the VM, keep `.env`, database, uploads, backups and actual tower configuration
outside public source. Set `DEBUG=False`, a fresh secret, allowed hostname and
HTTPS/CSRF settings. Migrate the database, import missing resources, collect
static files and restart the application service. The optional monitor service
needs the same private environment and network route. GitHub Pages cannot host
this backend. Follow [DEPLOYMENT.md](DEPLOYMENT.md) and validate the actual VM's
routing, TLS, persistence and backups before use.

### Troubleshooting map

| Symptom | First checks |
|---|---|
| Login succeeds but no sites/actions appear | User is active, has a TeamMember role, and has access to the site; a superuser has admin access |
| A write returns 403 | Role/site permissions, archived site, current session and CSRF configuration; do not remove authorization checks |
| Sync stops or returns 409 | Inspect the first failed queue operation, current server version and account; preserve/export pending records before clearing storage |
| Public report differs from team records | Reload the live `/fieldnotes/`; exported HTML is a snapshot. Confirm database/media and the named public-field projection |
| Protocol file is missing | Check deployed seed files, protected storage and file ownership; upload a replacement with manager/admin access |
| Tower says not configured | Confirm its exact site code in the private station JSON and the service's `MONITOR_STATIONS_FILE` environment |
| Tower is unreachable or stale | VM route/VPN, firewall, TCP 7200 reachability, service logs, last check time, collector and fixed timestamp offset |
| BADM remains incomplete | Station class/identifier, required/applicable groups, record formats and outstanding scientific review |
| Upload fails | Accepted format, file size, nginx `client_max_body_size`, app limit and writable/private MEDIA_ROOT |
| Old interface persists | Deployed source, `collectstatic`, app restart and service-worker update; do not clear an unsynchronized outbox |
| Migration/import fails | Correct environment/database, migration history, duplicate site codes and explicit import mappings; investigate on a staging copy |
| Production error or missing styles | `DEBUG=False` settings, host/CSRF origins, static collection, proxy headers and application service logs |

Use browser Network/Console tools to identify the failed request, then inspect
the matching route in `carbonique/urls.py` and its handler. On a Linux VM, inspect
`journalctl -u carbonique` and, when enabled, `journalctl -u carbonique-monitor`.
Keep logs, screenshots and issue reports free of private records and credentials.

Detailed references: [Architecture](ARCHITECTURE.md), [Imports](IMPORTS.md),
[Resources and monitoring](RESOURCES_AND_MONITORING.md), [Public site](PUBLIC_SITE.md),
[Processing files](PROCESSING_FILES.md),
[Deployment](DEPLOYMENT.md) and [Source provenance](../UPSTREAM.md).
