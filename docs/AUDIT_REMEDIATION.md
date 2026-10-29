# Application audit corrections, 29 October 2026

This release addresses the twelve confirmed findings in the 29 October audit.
It preserves the live scientific records, account identities, public report
scope and per-account pending work. The audit's original reproduction scripts
asserted faulty behavior; the new tests assert the corrected behavior.

## Corrections

| Finding | Corrected behavior | Main implementation |
| --- | --- | --- |
| F01: administrator scope | Account listing, creation, password resets, activation and role/site grants require a network-wide administrator. Scoped admins retain editing of their assigned sites. New sites and shared checklists also require network-wide administration. | `hub/permissions.py`, `hub/api.py` |
| F02: overlapping site loads | Loads capture account, site and generation. Late responses cannot replace the selected site's state or use another site's cache key. The previous site's form data is cleared while a new site loads. | `static/hub/app.js` |
| F03: sign-out data loss | Sign-out checks the account's whole outbox and clears only that account's metadata, snapshots and downloads in one IndexedDB transaction. Other accounts' records remain. Sealed sessions cannot enqueue later writes. | `static/hub/storage.js` |
| F04: changed account in another tab | Private requests carry an expected account and noncredential session fingerprint. The server checks both before dispatch and stamps responses. Changed sessions pause the workspace; tab broadcasts and storage guards prevent stale writes. Older browser fetches must reload. | `hub/security.py`, `static/hub/app.js` |
| F05: obsolete protocol PDF | Cache keys include the content digest/version. Online readers refresh the catalog; new bytes are SHA-256 checked before caching. Field preparation uses the same helper. Offline readers identify the saved revision. | `static/hub/resources.js`, `static/hub/offline-state.js` |
| F06: partial synchronization | Each acknowledgement updates the durable site snapshot before its outbox entry is deleted, in one transaction. Snapshot revision checks prevent a concurrent older response from overwriting it. Saved records remain visible when a later operation fails. | `static/hub/storage.js`, `static/hub/offline-state.js`, `hub/services.py` |
| F07: revoked receipt access | Current site authorization is checked before a receipt is returned. Authorized retries against archived sites remain idempotent. | `hub/services.py` |
| F08: shared caveat metadata | Both snapshot and direct API responses filter private configuration identifiers and details to the caller's allowed sites. The audit-before representation retains the request context. | `hub/serializers.py`, `hub/api.py` |
| F09: future deployment state | New installation/removal timestamps in the future are rejected with an explanation. This app records completed physical transitions; it does not schedule future deployments. | `hub/serializers.py`, `static/hub/app.js` |
| F10: malformed input | Workspace JSON writes require an object. Checklist titles/details and account text fields are type checked; invalid types return 400 responses. | `hub/parsers.py`, `hub/serializers.py`, `hub/api.py` |
| F11: negative visit duration | Closing before the recorded start is rejected without changing the visit or freezing a report. The open visit's start and an invalid queued close event can be explicitly corrected. | `hub/services.py`, `static/hub/app.js` |
| F12: archived source site | Equipment changes check the original site as well as the destination. Deployment creation checks the instrument's original site too. Restore an archived site before moving its instruments. | `hub/api.py` |

## Using the corrected workflows

### Accounts and shared devices

An administrator with any explicit site restriction cannot manage accounts,
even accounts restricted to the same site. A network-wide administrator can
create and maintain team accounts through Administration. An existing Django
superuser remains the recovery authority for its own access and permissions.

If another tab changes the signed-in account or session, the older workspace
pauses. Reload it and use the account that owns the work. Pending operations
remain associated with their original account and never migrate to another one.
The session fingerprint is a keyed hash, not the session cookie or a login token.

**Sign out & clear account** requires no pending records for that account. A
transaction rechecks this requirement so another tab cannot add work between
the check and deletion. A record arriving before the clear blocks it; a later
stale write is rejected. Other accounts' copies and pending records are preserved.
An explicit login with a new session re-enables that account's storage.

The queue shows pending counts by site, other-account pending totals without
identifying those accounts, selected-site freshness and estimated device storage.
Every pending entry can be exported, including entries that have not encountered
a server error. Export before deliberately discarding a record. An operation
export is JSON and an upload export is its original file; these are recovery
copies, not an automatic full-device restore format.

### Visit clock errors and deployments

Correct the device clock first. For an open visit, use **Visit details** to
correct the recorded start when it was wrong. For an invalid queued visit close,
use **Sync queue > Review & retry**, inspect the current server record and set
the recorded end explicitly before applying the correction. The retry receives
a new operation identifier; timestamps of other queued records remain intact.
Earlier closed report revisions remain preserved when a visit is reopened.

Record installation and removal after the work happens. Future scheduling is
not supported. Existing imported dates are preserved. If an older installation
already contains future-dated deployment rows, review and correct them against
actual field activity before relying on their location/status. The reviewed
local workspace had no deployment rows to migrate.

### Protocols and administrator editing

Online protocol reading checks the current catalog before selecting cached
bytes. The displayed revision must match the cached digest. Offline use requires
that revision to have been prepared; a missing revision requires a connection.
Obsolete cache entries do not replace a current PDF, but can occupy space until
that account's copies are cleared.

Operational inventory and hub records are read only in Django admin. Use the
workspace editors so version checks, permission rules, derived inventory state
and application audit events run together. Operational Django admin inspection and team membership recovery are restricted
to a superuser. This deliberately replaces direct admin
editing of deployments, caveats, equipment, sites and other operational records.

## Verification and developer checks

- `hub/test_audit_regressions.py` covers backend account/site boundaries, private
  response binding, malformed input, chronology and archival rules.
- `tests/frontend/offline.test.cjs` deterministically controls request ordering
  and partial acknowledgements in the actual site loader and synchronization
  functions, and checks the shared pure projection module.
- `tests/browser/workspace.spec.cjs` exercises the running app in Chromium with
  real IndexedDB. It covers overlapping loads, partial synchronization/reload,
  two-account sign-out, changed cookies, PDF replacement, atomic storage guards,
  snapshot revision protection, a phone viewport and prepared offline reopening.
- `hub/test_postgres_concurrency.py` checks duplicate receipts, competing edits
  and simultaneous overlapping deployments against actual PostgreSQL locks.
  These three tests skip on SQLite and run in the PostgreSQL CI job.
- `hub/test_backup_restore.py` performs a portable backup/restore drill with
  synthetic account hashes, linked records and exact private-file bytes in an
  isolated database and directories.

CI is configured to run the Django suite against SQLite and PostgreSQL, plus Node behavior tests,
audits of Python and npm development dependencies, and Chromium browser tests.
The first hosted matrix passed SQLite and exposed direct streaming-response
cleanup in several PostgreSQL tests. Those tests now consume the download iterator,
verify its bytes and confirm the response closes without ending the enclosing
test transaction. See [Validation](VALIDATION.md) for the reproduction and results.
The browser runner creates disposable databases/files and test-only accounts;
it disables dotenv loading and never seeds the normal application database.
Node and Playwright are development tools and are not needed on the production
VM. The Docker image excludes their manifests, runner and fixture scripts.

From a development checkout with patched Python and Node 24:

```bash
python manage.py test hub
npm ci --ignore-scripts
npm audit --audit-level=moderate
npm run test:frontend
npx playwright install chromium
npm run test:browser
```

`TEST_PYTHON` can select the virtual environment's interpreter for the browser
runner. Its server uses loopback port 8786, refuses to reuse another server, and
creates a temporary SQLite database/media directory. Browser tests never connect
to production or real tower endpoints. Production tests must not be pointed at
the live database. See [Validation](VALIDATION.md) for recorded results.

## Deploying this correction

1. Back up the production database, private media and protected configuration.
   Review the target site of existing pending records before synchronizing them.
   Export uncertain entries for review; this release cannot infer the intended
   site of work recorded while an older cache was inconsistent.
2. Deploy the reviewed source, install the Python requirements and run the normal
   Django configuration/migration checks. This release adds no migration and
   does not require repeating imports, setup or account creation.
3. Collect static files and restart the app service using its normal production
   account/environment. Review the host work in [Security maintenance](SECURITY_MAINTENANCE.md).
4. Close or reload older workspace tabs while online. Browser requests from
   older unbound fetch clients return 409 with a reload explanation. The normal
   nonbrowser API authentication/authorization policy remains in place.
5. Allow service worker **carbonique-shell-v11** to install, then prepare the
   needed sites and protocol revisions again before fieldwork. The IndexedDB
   database name/version and existing outbox entries are retained. Do not clear
   browser storage as an upgrade step.
6. Check login/account switching, authorized site edits, public synchronization,
   an attachment, current protocols, the pending queue and offline reopening in
   staging. The live VM/proxy/tower connectivity still needs its own checks.

## Remaining larger work

Visible, idle workspaces refresh snapshots once per minute instead of every
15 seconds; hidden tabs and open dialogs do not poll. Legacy attachment lookups
prefetch their related objects. This reduces routine work, but historical
pagination and conditional snapshot tokens still need measurement with realistic
multi-year data before changing offline/history completeness. The full history
continues to be available; this release does not silently truncate it.

The local restore drill verifies the portable format. A production PostgreSQL
backup/restore rehearsal, actual proxy/TLS/firewall configuration, OS/interpreter
patch verification and real private tower connectivity remain staging/operator
tasks. No changes were made to the Arbutus VM by this release.
