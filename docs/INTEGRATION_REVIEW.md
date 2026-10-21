# Integration and data compatibility

This repository contains one standalone Django application. `manage.py` at the
repository root launches the Carbonique workspace, its APIs and the public report.
There is no separate legacy server to start from this checkout.

## Fresh installation

Use a new empty database and run `migrate`, `setup_hub --with-reference` and
`createsuperuser`. The supplied reference materials populate the app; Hank's
database and previous accounts are not required. See [IMPORTS.md](IMPORTS.md).

## Retained data identities

The `inventory` application retains EcoFlux model/table identities and original
migrations 0001–0012. Later migrations extend those records and add workflow
tables in `hub`. Existing EcoFlux field notes can be linked to visits without
replacing their IDs, text or attachment paths. Run all additional migrations
before opening an upgraded database.

These compatibility identities do not require importing an old database.
Any future migration from another installation should be separately validated
against staging data with explicit source mappings.

## Reference sources and editable records

The bundled snapshot contains six sites, 127 classified visit summaries,
19 data caveats, photographs, plots and eight historical TraceAnalysis INI files.
The original twenty-file INI snapshot remains archival material. The workspace
and public report now link to the maintained GitHub folder instead of showing
a current local revision library.
Imports retain source IDs and preserve later edits. Classified summaries are
not verbatim source field notes. Unknown equipment identities and historical
period boundaries remain unspecified for review.

The public report now reads current sites, visits and caveats directly. Draft,
reviewed and resolved statuses remain visible. Unknown imported authors are valid;
review timestamps are recorded on later transitions. The original HTML remains
a source archive; downloaded HTML is a standalone snapshot.

Original retained protocol PDFs remain unchanged. Seven are bundled; the retired
data-download procedure and its installed protected copy are removed by migration.
Runtime uploads, databases, credentials and backups stay outside Git. The source
reference media and processing-file copies are intentionally tracked. The supplied
TraceAnalysis source directory is read only; uploads create protected revisions.
See [Public site](PUBLIC_SITE.md) and [Processing files](PROCESSING_FILES.md).

## Application boundaries

Inventory tracks individual equipment; site reference tracks installed geometry;
visits record work; caveats and configuration versions record data consequences.
These views share canonical records rather than separate editable copies.
Tower monitoring is diagnostic and read-only. It does not change instruments,
run flux processing or replace a scientific data archive.

Source attribution is in [UPSTREAM.md](../UPSTREAM.md). For navigation through the
implementation, see [Application overview](OVERVIEW.md) and
[Architecture](ARCHITECTURE.md). Verification is recorded in
[VALIDATION.md](VALIDATION.md).
