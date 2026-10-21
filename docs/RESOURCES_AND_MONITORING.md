# Site resources and tower monitoring

The application runs from the repository root using `manage.py`. Site resources
and tower monitoring share its accounts, site access rules and database.

## Upgrade an existing VM

Back up the database and media together before migrating. From the repository root,
using its Python environment:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py import_resources
python manage.py collectstatic --noinput
python manage.py check
python manage.py test hub
```

Restart the Gunicorn/Django service after deploying the Python and JavaScript
changes. For example, `sudo systemctl restart carbonique`. Restart commands and
service names depend on the VM. New installations can still use
`python manage.py setup_hub --with-reference`.

`import_resources` can be rerun. It preserves edited sites, visits, caveats,
protocols and BADM records. Stable source identifiers prevent repeated imports.
Existing legacy field notes are matched only when source ID, site and visit date
agree; unmatched source summaries remain in the downloadable source archive.

## Included material and navigation

| Workspace | Canonical purpose |
| --- | --- |
| Overview | Network summary and each site's current access condition |
| Field work | Planned tasks, visits and observations; condition repeated as context |
| History | The existing visit and task history, with site-tab shortcuts |
| Sites & instruments | Site description, reference instrument specifications, tower diagrams, media and contextual equipment/files/identifier tabs |
| Equipment inventory | Network-wide tracked instruments and serial-number/service/deployment history |
| Data & processing | Caveats, cross-checks, unresolved source flags, dated configurations, processing settings and downloadable INI files |
| Site BADM | Versioned ICOS variable-group records and completeness review |
| Protocols | Shared PDF library, integrated reader and original PDF downloads |
| Tower status | Read-only network checks and per-tower measurements/diagnostics |

The supplied export includes **6 sites, 127 rewritten source-note summaries,
19 caveats, 15 images and 8 full INI files**, plus the complete Markdown/JSON
documentation. All source files are retained byte-for-byte under
`seed/ecoflux_inventory_export/` and downloadable as a ZIP from Data & processing.
Imported notes are summaries, not a replacement for verbatim legacy field notes.
The export explicitly lacks the live stock/equipment database; instrument
specifications remain visible under Sites & instruments. Purchase dates and
unknown serial numbers have not been invented to populate tracked equipment.

The protocol library contains seven bundled original PDFs. Managers/admins can
upload, replace and archive PDFs; all team roles can read/download installed
files. The data-download procedure is retired and removed by migration 0006.
Mozilla PDF.js is bundled with its Apache-2.0 license, so PDFs are not sent to an
external viewer. Protected media remains authenticated and site scoped.

Data & processing links to the current TraceAnalysis folder maintained on
GitHub. The public report uses the same link. Original configuration evidence
and source snapshots are retained as historical records. See [Processing files](PROCESSING_FILES.md).

Each site's condition has a status, statement, review/restriction date, editor
and timestamp. An overdue date prompts review; it never automatically opens a
site. Managers/admins with access can edit it. Tower media accepts MP4, WebM,
GIF, WebP, JPEG and PNG in the authenticated site resource controls.

Per-note documents, images, audio and video can be recorded in off-site planning,
on-site work and History. Files target a particular task/activity/observation,
are queued with offline field notes, and remain authenticated. The default limit
is 25 MiB per file; tower media has a separate 100 MiB limit.

Carbonique logos, colors and Roboto fonts are bundled locally. The live public
report now reads sites, visits and caveats from the database, including site
conditions and all caveat statuses. BADM, inventory, protocols, tower telemetry
and newly uploaded note media stay in the team workspace. See
[Public site](PUBLIC_SITE.md).

## BADM scope and checks

Official sources:

- https://www.icos-etc.eu/icos/documents/templates
- https://www.icos-etc.eu/icos/documents/instructions/badm
- https://doi.org/10.18160/6m8s-fy7m

The offline schema was extracted from the **27 template workbooks downloaded on
2026-10-16**, retaining each workbook's own version history, variable groups,
requirements, explanation, units, controlled vocabulary and source hash. Some
downloaded workbooks are newer than the label on the catalogue page (including
2026 vegetation, camera and management/processing definitions). There is no
spreadsheet parsing dependency in production: the app reads `seed/badm/schema.json`.
To regenerate it, install openpyxl in a development environment and run
`python scripts/build_badm_schema.py DIRECTORY` against files named
`icos-SHARE_ID.xlsx` downloaded from the official catalogue.

Managers confirm station class and the assigned ICOS identifier; an AmeriFlux
identifier is not silently substituted. Only documented latitude/longitude and
fixed EST offset are initially copied from the supplied inventory. All other
station facts must be entered/reviewed, including the correct class.

Records represent repeatable group instances with independent dates and comments.
The editor uses official variable names and vocabulary. Incomplete records can
be saved as drafts. Checks cover required fields, alternative sets, numeric/date
formats, coordinate ranges, vocabulary choices, reversed date intervals and
installation/removal event dates. Complex conditional/explanatory rules require a
manager's explicit review. Acknowledging review does not remove format errors.

The displayed station setup checklist combines core groups with additional
manager-selected applicable groups. It is a **local completeness checklist**, not
an assertion that every station has the same ICOS reporting obligations. The
result says "Local checks passed; ETC review required", never ICOS certified.
Current instrument vocabulary, cross-submission consistency and scientific
protocol obligations still require ICOS ETC review.

Every team user with site access can download a site BADM ZIP. It contains one
CSV per active variable group (observations in rows; variables in columns;
the assigned station ID in the ICOS-format filename), all records including
archived entries in JSON, the schema, profile, provenance notes and validation
results. Missing identifiers produce clearly marked UNASSIGNED draft filenames.
CSV numeric values retain their original sign and precision. Import text columns
as text in a spreadsheet. The Hub never submits files to ICOS automatically.

## Read-only tower connections on the VM

Reference implementation: https://github.com/davidulicio/EC-Monitor at `797a96c`.
Its MIT license is preserved in `EC_MONITOR_LICENSE.txt`.

The Hub queries the LI-7550/LI-7500DS over **TCP 7200**, matching EC-Monitor's
grammar. The port does not use the web/SSH login. No default LI-COR username or
password is built into this app, and it does not use SSH, port 22 or the separate
SmartFlux port 5050 service. Tower addresses live only in a private VM file. Do
not put passwords, public router forwarding addresses, real hostnames or the
private file in GitHub, public static files, site metadata, browser local storage
or deployment logs.

Create a private file **outside the repository and web root**, for example
`/etc/carbonique/monitor-stations.json`:

```json
{
  "UQAM_1": {"host": "10.0.0.20", "port": 7200, "utc_offset": -5},
  "UQAM_2": {"host": "10.0.0.21", "port": 7200, "utc_offset": -5}
}
```

Those are placeholder private addresses. Add only actual stations the VM is
authorized to reach. `utc_offset` describes the fixed time basis of the reported
SmartFlux file timestamp and defaults to EST, matching this network's documented
time basis. It is not an instruction to change the instrument clock.

Give only the service account read access to this file (for Linux, owner
`carbonique`, mode `600`) and configure the VM's private `.env`:

```dotenv
MONITOR_STATIONS_FILE=/etc/carbonique/monitor-stations.json
MONITOR_TIMEOUT=6
MONITOR_MIN_INTERVAL=30
MONITOR_STALE_SECONDS=300
```

The VM must have routing/VPN access to the tower network. Keep analyzer ports on
that private network, rather than forwarding them publicly. Expose only the
Hub's authenticated HTTPS service through the normal reverse proxy. The browser
never receives tower connection addresses, credentials, arbitrary query controls
or a socket proxy. The monitor endpoint accepts GET only, applies normal team and
site scope, and sends only exact allowlisted read queries ending in `?`. Even
admins cannot issue instrument writes through it. Calibration, restarting,
logging changes and raw console commands are absent.

`Check all towers` polls configured accessible sites in parallel with bounded
timeouts; `Check this tower` polls one. All viewers can request checks. A shared
per-site database cooldown prevents repeated clicks and multiple web workers from
opening connections continuously. The view checks again about once per minute
while open. Missing configuration, unreachable instruments, invalid responses, faults and stale measurements remain distinct. Last known readings are retained
and marked as earlier measurements after a failed check. Up to 24 hours of recent
snapshots are charted; the background collector retains seven days. They are
diagnostic snapshots, not continuous scientific data.

For updates even when nobody has the page open, enable a dedicated collector:

```bash
python manage.py poll_towers --watch --interval 60
```

`deploy/carbonique-monitor.service.example` is a Linux systemd template using the
same private environment file as the web service. A Windows VM can run the same
command as a dedicated service/scheduled process under its service account. For
Docker, bind-mount the private configuration read-only into the web/collector
container, set `MONITOR_STATIONS_FILE` to the container path and ensure it has the
required private network route. The file must not be copied into the image.

Increase the reverse proxy upload limit for videos: the supplied nginx template
uses `105m`, while `MAX_SITE_MEDIA_BYTES` defaults to 100 MiB. Media is streamed
with range requests for seeking and still requires site access. Keep
`MEDIA_ROOT` private and back it up with the database.

Live towers and the target VM are not reachable from this development session.
The protocol client is checked against parsed EC-Monitor examples and simulated
responses, including diagnostic words, split records, query guards, stale data
and failure handling. Final routing/firewall checks must be done on the VM.

## Verification

See [VALIDATION.md](VALIDATION.md) for the application checks and deployment
boundaries. The public report is generated from current records, and its HTML
export is a snapshot. Seven protocol PDFs, structured inventory records, supplied
photographs/plots and historical INI source evidence are retained. Current INIs
are linked to GitHub rather than mirrored by the app.
