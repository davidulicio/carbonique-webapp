# Loading the supplied reference materials

This application starts with a new database. An existing EcoFlux database,
old account, Firebase project or data export from another server is not needed.

## Initial setup

From the repository root with the application's Python environment active:

```bash
python manage.py migrate
python manage.py setup_hub --with-reference
python manage.py createsuperuser
```

`migrate` creates the schema. `setup_hub` creates maintenance checklists and
`--with-reference` calls `import_resources` to load the bundled materials.
`createsuperuser` creates your own administrator; no existing passwords or
default accounts are supplied. Create other accounts under Administration.

## What is included

| Source | How it is used |
|---|---|
| `seed/ecoflux_inventory_export/data/` | Six sites, 127 classified visit summaries, 19 caveats, site/instrument descriptions and processing reference |
| `seed/ecoflux_inventory_export/images/`, `seed/media/` | Supplied tower/site photographs and diagnostic plots, linked to the reference records |
| `seed/ecoflux_inventory_export/ini/` | Eight complete TraceAnalysis configuration files, with descriptions and caveat links |
| `seed/ecoflux_inventory_export/*.md` | Human-readable source descriptions, conventions and known gaps; included in the source export download |
| `seed/protocols/`, `catalogue.json` | Seven bundled protocol PDFs; the data-download procedure is retired |
| `seed/processing_files/`, `catalogue.json` | Original supplied INI snapshot, SHA-256 hashes and source modification times; archival only, not current GitHub settings |
| `seed/badm/schema.json` | Official ICOS template definitions, vocabulary, requirements and source/version information |
| `public/fieldnotes/index.html` | Original source archive; live public report now reads database records |
| `static/hub/` | Carbonique logos, colors, Roboto typography and local application/PDF assets |

The supplied inventory export contains summaries rather than every original
database table. All supplied export content is retained; unspecified serial
numbers, purchase dates and instrument identities are not invented. Instrument
specifications remain visible under Sites & instruments. Add individual equipment
records under Inventory as the team documents them.

Caveats enter the database as drafts for researcher review. Date-only visits use
noon fixed EST as a storage placeholder, with that precision limitation retained
in provenance. Uncertain affected periods remain explicit prose rather than
inferred precise timestamps. The UQAM_5 activation date is a documented import
placeholder and needs confirmation before use as commissioning metadata.

The supplied public HTML and inventory-export overview have had obsolete
editor-service integrations removed; scientific records, figures, photographs,
protocol PDFs and processing files retain their supplied content.

## Processing files and protocol changes

`import_resources` installs seven protocols and historical configuration evidence.
The retired data-download procedure is removed by migration 0006, including its
installed protected file. Its original outside the app is untouched.

The former twenty-file working INI library is no longer initialized by normal
setup. Current settings are maintained in GitHub and linked from the app and
public report. Original source snapshots and prior private revisions remain
archival evidence. See [Processing files](PROCESSING_FILES.md).

## Repeat imports and later updates

```bash
python manage.py import_resources
```

Source IDs and import mappings make repeat imports idempotent. Later team edits
are preserved. Replacing source files does not silently overwrite a reviewed
caveat or edited site. Reconcile changed source records deliberately through
the app, retaining provenance.

The live public report reads current records; edit them in the team workspace.
The original HTML remains an archive. For a separately reviewed historical
source import, extraction tools remain available:

```bash
python scripts/extract_fieldnotes.py public/fieldnotes/index.html --output /private/path/reference-extract
python manage.py import_fieldnotes --file /private/path/reference-extract/fieldnotes.json
```

The extractor reads JSON constants and decodes embedded images without executing
JavaScript. JSON imports accept UTF-8 and an optional BOM, preserving accented
names and scientific symbols on Windows and Linux.

## Developer notes

Upstream inventory migrations remain in the code to preserve model history;
they are applied normally to a new empty database. Compatibility commands such
as `backfill_visits` and `import_field_log` remain available for separately
authorized migrations, but are not part of this installation. Do not configure
the new application to write to another application's production database.

After initialization, verify the site/visit/caveat counts, open representative
attachments, inspect the protocol catalogue and review scientific caveats.
Back up database and protected media together. Keep runtime files and exports
outside Git. See [DEPLOYMENT.md](DEPLOYMENT.md) and
[Application overview](OVERVIEW.md).
