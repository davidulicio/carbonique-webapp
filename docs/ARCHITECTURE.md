# Architecture

For a guided user/developer introduction, see [Application overview](OVERVIEW.md).

## Application layers

- **inventory** retains EcoFlux's existing tables, migrations and file paths. The previous destructive site-edit view is not used or included. Site edits are ordinary validated updates that do not delete related records.
- **hub** adds field workflows, deployments, dated settings, caveats, attachments, roles, audit events and import mappings.
- **carbonique** contains portable settings, routes and ASGI/WSGI entry points.
- **static/hub** is a dependency-free JavaScript interface. Assets are local; no frontend CDN is required during fieldwork.
- **hub/public_report.py** builds the live, read-only public report from current records.
- **public/fieldnotes/index.html** retains the original source archive only.

## Data relationships

| Record | Relationships / purpose |
|---|---|
| Site | Canonical site row; metadata and archive status; legacy publication flag retained but unused by the public projection |
| Visit | Site; optional one-to-one original EcoFlux FieldNote; crew, narrative and classification |
| Task | Site; optional equipment; current state and optimistic version |
| TaskActivity | Task; optional visit; immutable action and recorded title/author |
| VisitObservation | Visit; immutable observations; corrections are additional observations |
| VisitReport | Visit + revision; frozen text and Markdown |
| Equipment / History | Existing inventory and service-history records |
| Deployment | Instrument + site + nonoverlapping active interval; height/depth and variables |
| ConfigurationVersion | Site; optional deployment; settings and explicit effective interval; correction may supersede another version |
| DataCaveat | One or more sites; optional visit/equipment/configurations; affected period, treatment and review status |
| CalibrationLog | Site; work date/type, serviced and replacement sensors, preparation, lab dates, source visit, comments and optimistic version |
| KnowledgeEntry / KnowledgeFile | Scoped or shared reference notes, HTTP(S) notebook links, protected files, hashes and recoverable archives |
| Attachment | Permission-checked site; optional visit/task/activity/observation/equipment/caveat/configuration/calibration; hash and original filename |
| ProcessingFile / ProcessingFileVersion | Relative INI path/site and immutable protected byte revisions, hashes and source timestamps |
| SiteCondition | Site; access statement, review date, editor and optimistic version |
| BadmProfile / BadmRecord | Site; station class/identifier, applicable groups and repeatable metadata observations |
| Protocol / SiteMedia | Protected PDF library and site-specific video/image records |
| TowerStatus / TowerReading | Site; last check, cooldown and recent diagnostic snapshots |
| TeamMember | Django user; role; optional allowed-sites list |
| AuditEvent | Actor, action, entity, time and context |
| OperationReceipt | User + operation UUID + content hash; stored outcome for safe retries |
| ImportRecord | Source identifier, destination identifier and original payload |

Configuration intervals are half-open `[effective_from, effective_to)` when an end is supplied. Replacements preserve previous rows; downstream consumers should resolve `supersedes` when choosing an authoritative version. No processing pipeline automatically consumes these records in this build.

## API

Authenticated APIs use Django session authentication and CSRF validation. They are served on the same origin as the application.

| Endpoint | Purpose |
|---|---|
| GET `/api/bootstrap/` | Account role, allowed sites and checklists |
| GET `/api/snapshot/?site=ID` | Complete selected-site workflow/reference snapshot |
| GET `/api/overview/` | Counts and latest visits across accessible sites |
| GET `/api/monitor/` | Scoped read-only tower checks and snapshot history |
| `/api/sites/ID/condition/` | Manager/admin site condition updates |
| `/api/badm/schema/`, `/api/sites/ID/badm/profile/`, `/api/sites/ID/badm/records/` | BADM definitions, profile and repeatable records |
| GET `/sites/ID/badm.zip` | Site BADM export for all permitted team roles |
| `/api/protocols/`, `/protocols/ID/file/` | PDF metadata, manager/admin maintenance and protected original files |
| `/api/sites/ID/media/`, `/site-media/ID/file/` | Site media metadata and protected range streaming |
| `/api/sites/ID/calibrations/`, `/api/sites/ID/calibrations/UUID/` | Read/create/edit site calibration logs; the same mutations are supported by the offline sync API |
| `/api/knowledge/`, `/api/knowledge/UUID/` | Shared and site-scoped technical references, versioned edits and soft archives |
| `/api/knowledge/UUID/files/`, `/api/knowledge/UUID/files/FILE_ID/`, `/knowledge-files/FILE_ID/` | Atomic multi-file upload, file archive/restore and protected download |
| POST `/api/sync/` | Ordered, idempotent field operations |
| `/api/sites/`, `/api/equipment/`, `/api/deployments/`, `/api/caveats/` | Role-scoped CRUD without destructive delete endpoints |
| `/api/configurations/` | Read/create immutable scientific configuration versions |
| `/api/processing-files/`, `/processing-files/ID/` | INI library, bulk revision upload and protected original-byte downloads |
| `/fieldnotes/`, `/fieldnotes/content/`, `/fieldnotes/download/` | Public current report and self-contained export; GET only |
| `/api/dois/`, `/api/equipment-history/`, `/api/checklists/` | Related reference and maintenance records |
| `/api/team/` | Admin-only team management |
| POST `/api/attachments/` | Retry-safe multipart uploads |
| `/attachments/ID/`, `/legacy-attachments/KIND/ID/` | Permission-checked downloads |

Edits to versioned rows require `base_version`. The server returns HTTP 409 on stale edits. Field-operation failures are reported per operation in a 200 batch response; clients must inspect `results[].ok` and `results[].status`. The batch stops at the first failure, preserving dependency order. Malformed batch envelopes receive HTTP 400.

## Offline operations

The service worker caches only the neutral HTML app shell and static assets; it does not cache API responses. IndexedDB stores per-account site snapshots, downloaded attachments and an ordered outbox. Offline edits are projected over the last snapshot for immediate display.

Each operation has a unique ID, account namespace, target site, client-generated record UUID, occurrence timestamp and optional expected record version. The server checks the current user's role/site access, locks records and saves the event plus a receipt atomically. Retrying the same ID/content returns its previous result. Reusing an ID with different content is rejected.

The outbox is synchronized while the app is open. It verifies the signed-in account before sending another account's records. Notes are append-only; task state changes use optimistic concurrency. Closed visits reject new field observations until explicitly reopened. Attachments can be added later without altering a frozen report.

A note operation and its dependent files are enqueued in one IndexedDB transaction. Task activity has a stable client UUID so attachments can target an individual event before sync. Upload retries compare all association IDs and cannot silently relink files. Uploaded files remain in IndexedDB until acknowledged, then are removed from the outbox. The report and data snapshot are refreshed after syncing. A queued conflict retains its local payload until reviewed, retried, exported or discarded.

## Public reference

`/fieldnotes/` embeds the current database report in a sandboxed iframe;
`/fieldnotes/content/` also applies a response sandbox for direct access. The
named projection includes sites, visits and all caveat statuses, known scientific
images, tower diagrams and latest eligible INIs. Other resources and operational
uploads stay authenticated. `/reference/` redirects to this report.

Inline scripts/styles and embedded image/font data are permitted; same-origin
privileges, external requests and private API access are blocked. Responses use
no-store. `/fieldnotes/download/` returns a self-contained snapshot. See
[Public site](PUBLIC_SITE.md) for field scope and [Processing files](PROCESSING_FILES.md)
for version storage. The source HTML archive is not a live input.

## Boundaries

- No actual flux computation, continuous scientific data ingestion, datalogger control, or automatic changes to EddyPro/TraceAnalysis files occur. Configuration files may be attached and versioned as evidence.
- Repository reference data is included. Unseen live database and Firebase data require imports.
- Polling provides collaboration without a WebSocket server. Source snapshots are not automatically reconciled with later manual Word/HTML edits.
- Database migrations preserve the supplied upstream schema, but deployment-specific migrations must be checked in staging.

## Calibration and reference implementation

`hub/record_models.py` defines calibration and library entities;
`hub/record_resources.py` validates mutations and enforces roles, site access,
expected versions and file validation. `static/hub/record-resources.js` provides
the site tab, on-site form and reference library using the existing dialogs.
Calibration operations and dependent files are committed to IndexedDB together
and replayed in order. No automatic equipment moves or deployment changes occur.

Shared reference files use a separate model because shared entries have no site.
Uploads lock the parent, validate the complete batch before saving, suppress
active content duplicates by hash and clean storage after a failed write. Links
are HTTP(S), cannot embed credentials, and are never fetched by the server.
Downloads recheck current entry/site access. Archived records remain readable
history; archiving is not an access-revocation mechanism. Django admin treats
these records as read only to preserve application version checks.

`seed/calibration_swaps.json` is a reviewed manifest of completed swaps in the
supplied notes. `import_calibrations` uses stable UUIDs and import receipts;
missing source visits are skipped and existing imported records are preserved.
The preparation reflects the project's stated swap practice. It does not imply
an individual certificate or lab date is available. The manifest excludes
planned/cancelled work, consumables and logger/media exchanges.

The UI normalizes em dashes in displayed prose, while saved notes, code blocks,
source archives and downloadable file bytes remain intact.

## Security boundaries

`hub/security.py` applies private-response cache rules and browser security
headers. It also resolves the login client's IP, trusting X-Real-IP only from
explicit proxy peers. Django Axes 8.3.1 uses its database handler, so failed-login
counts are shared across workers and survive restarts. Both team/admin login use
the guarded authentication backend, with a 15-minute pause after five failures
for a username/address pair. The public report keeps its separate origin-isolating
sandbox policy. The deployment proxy adds request and connection limits; HTTP
429 does not turn queued field records into a permanent synchronization error.
See [SECURITY.md](../SECURITY.md) for operator recovery and remaining server work.
