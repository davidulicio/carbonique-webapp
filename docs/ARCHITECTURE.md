# Architecture

For a guided user/developer introduction, see [Application overview](OVERVIEW.md).

## Application layers

- **inventory** retains EcoFlux's existing tables, migrations and file paths. The previous destructive site-edit view is not used or included. Site edits are ordinary validated updates that do not delete related records.
- **hub** adds field workflows, deployments, dated settings, caveats, attachments, roles, audit events and import mappings.
- **carbonique** contains portable settings, routes and ASGI/WSGI entry points.
- **static/hub** is a dependency-free JavaScript interface. Assets are local; no frontend CDN is required during fieldwork.
- **public/fieldnotes/index.html** is an independently replaceable public editorial snapshot.

## Data relationships

| Record | Relationships / purpose |
|---|---|
| Site | Existing canonical site row; metadata, archive status, publication flag |
| Visit | Site; optional one-to-one original EcoFlux FieldNote; crew, narrative and classification |
| Task | Site; optional equipment; current state and optimistic version |
| TaskActivity | Task; optional visit; immutable action and recorded title/author |
| VisitObservation | Visit; immutable observations; corrections are additional observations |
| VisitReport | Visit + revision; frozen text and Markdown |
| Equipment / History | Existing inventory and service-history records |
| Deployment | Instrument + site + nonoverlapping active interval; height/depth and variables |
| ConfigurationVersion | Site; optional deployment; settings and explicit effective interval; correction may supersede another version |
| DataCaveat | One or more sites; optional visit/equipment/configurations; affected period, treatment and review status |
| Attachment | Permission-checked site; optional visit/equipment/caveat/configuration; hash and original filename |
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
| POST `/api/sync/` | Ordered, idempotent field operations |
| `/api/sites/`, `/api/equipment/`, `/api/deployments/`, `/api/caveats/` | Role-scoped CRUD without destructive delete endpoints |
| `/api/configurations/` | Read/create immutable configuration versions |
| `/api/dois/`, `/api/equipment-history/`, `/api/checklists/` | Related reference and maintenance records |
| `/api/team/` | Admin-only team management |
| POST `/api/attachments/` | Retry-safe multipart uploads |
| `/attachments/ID/`, `/legacy-attachments/KIND/ID/` | Permission-checked downloads |

Edits to versioned rows require `base_version`. The server returns HTTP 409 on stale edits. Field-operation failures are reported per operation in a 200 batch response; clients must inspect `results[].ok` and `results[].status`. The batch stops at the first failure, preserving dependency order. Malformed batch envelopes receive HTTP 400.

## Offline operations

The service worker caches only the neutral HTML app shell and static assets; it does not cache API responses. IndexedDB stores per-account site snapshots, downloaded attachments and an ordered outbox. Offline edits are projected over the last snapshot for immediate display.

Each operation has a unique ID, account namespace, target site, client-generated record UUID, occurrence timestamp and optional expected record version. The server checks the current user's role/site access, locks records and saves the event plus a receipt atomically. Retrying the same ID/content returns its previous result. Reusing an ID with different content is rejected.

The outbox is synchronized while the app is open. It verifies the signed-in account before sending another account's records. Notes are append-only; task state changes use optimistic concurrency. Closed visits reject new field observations until explicitly reopened. Attachments can be added later without altering a frozen report.

Uploaded files remain in IndexedDB until the upload is acknowledged, then are removed from the outbox. The report and data snapshot are refreshed after syncing. A queued conflict retains its local payload until reviewed, retried, exported or discarded.

## Public reference

`/fieldnotes/` embeds the report in a sandboxed iframe; `/fieldnotes/content/` also applies a response-level sandbox so direct access remains isolated. Inline scripts and styles and embedded image data are allowed, but same-origin privileges and authenticated API access are not. Every request reads the configured file, with caching disabled.

The optional `/reference/` renders explicitly publishable database records. It is intentionally a smaller view and does not include crews, private visit logs, uploaded operational documents or equipment serial numbers.

## Boundaries

- No actual flux computation, continuous scientific data ingestion, datalogger control, or automatic changes to EddyPro/TraceAnalysis files occur. Configuration files may be attached and versioned as evidence.
- Repository reference data is included. Unseen live database and Firebase data require imports.
- Polling provides collaboration without a WebSocket server. Source snapshots are not automatically reconciled with later manual Word/HTML edits.
- Database migrations preserve the supplied upstream schema, but deployment-specific migrations must be checked in staging.
