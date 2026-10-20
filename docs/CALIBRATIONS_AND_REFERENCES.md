# Calibration and reference workflows

## Record a calibration

1. Select a site and open **Sites & instruments → Calibration log**.
2. Choose **Record calibration** and select Sensor swap, On-site calibration or
   Lab calibration. During an on-site visit, **Calibration / sensor swap** opens
   the same form with that visit selected.
3. Record the sensor/model and known serial numbers. Inventory links are optional
   for historical instruments. For swaps, identify the replacement by an
   inventory link, serial or description and record its preparation. The default
   is Cleaned and lab calibrated. Use Cleaned only or Not confirmed when needed.
4. Add the replacement's lab calibration date when known, the optional next due
   date, laboratory, personnel, certificate reference and comments. Lab dates
   cannot follow the work date; due dates cannot precede it.
5. Attach certificates, calibration tables, documents, images or other media and
   save. The record and files are queued together and synchronize in order.

Prepare the site while connected before offline work. Queued records survive
reloads and remain visible with Pending sync until acknowledged. Resolve version
conflicts through the Sync queue. Files are limited to 25 MB each. Unknown dates
and serials should stay blank; record uncertainty in the comments.

Sensor swaps record the work performed. They do not move inventory or close/open
deployments. Researchers update those records separately when necessary.
Archive a mistaken record to retain the history; Show archived records permits
restoration. All permitted site roles can read; members and higher roles can
write, unless the site is archived.

## Historical swaps

The supplied notes support 18 completed sensor/analyzer swaps. The reviewed
manifest records one row per instrument, including LI-7550 analyzer control
units. Replacements are marked cleaned and calibrated under the project's
confirmed practice, including malfunction replacements. Lab dates, certificates
and serials not documented in the notes are not invented. The 2026-01-30
UQAM_3 BaroVUE10 entry explicitly flags ambiguous serial pairs.

New reference installations include these records automatically. For an existing
installation, after applying migrations:

```bash
python manage.py import_calibrations --dry-run
python manage.py import_calibrations
```

Rerunning preserves edits, archive status and source visits. It does not infer
future swaps automatically from free text; use the calibration form for new work.
Follow **Open source visit** to read the original narrative. Planned exchanges,
consumable changes, USB swaps, cancelled swaps and logger replacements are not
entered as sensor calibrations.

## Technical reference library

Create one entry for a manual, wiring topic, troubleshooting issue, repair
history or notebook. Choose a site or Shared network and a category. Add notes,
HTTP(S) links, and documents/images. Members and higher roles can write entries
for permitted active sites; editing a shared entry requires network-wide site
access. Viewers can read and download.

For OneNote, paste its web sharing link. This opens the notebook in its provider;
the app does not copy, embed or synchronize notebook contents. The link's
permissions remain controlled by that provider. Native .one files can also be
stored for download. Keep passwords and embedded credentials out of links.

Upload up to 10 files at once, totaling at most 25 MB. PDFs and images are
validated before a batch is stored. PDFs open in the app; other documents
retain their original bytes for download. Duplicate active content in an entry
is skipped on retries. If a reference saves but file upload fails, the dialog
reports this and Save retries the upload against the saved entry.

Search titles, notes and filenames; filter by site/shared scope and category.
Archive/restore entries and individual files as needed. Archived files remain
available to authorized readers as history. Library updates and file downloads
require a connection. Prepared site snapshots retain entry notes for offline
reading; reference uploads are not part of the offline outbox.

Use Protocols for approved procedures, Data & processing for INI revisions and
data consequences, and the library for technical supporting information.
Calibration records and library uploads do not enter the public Field Notes.

## Upgrade and troubleshooting

Back up the database and private media, then run:

```bash
python manage.py migrate
python manage.py import_calibrations
python manage.py collectstatic --noinput
python manage.py check
```

Restart the VM application service after deployment and reload the browser.
The service worker upgrades to shell version 8 while keeping prepared data and
pending operations. A missing calibration table means the database migrations
have not been applied. A 409 response means another device changed that record;
reload or compare versions before retrying. A denied shared-reference edit can
mean the account is restricted to specific sites. Missing file errors indicate
the private media storage needs to be restored or mounted.
