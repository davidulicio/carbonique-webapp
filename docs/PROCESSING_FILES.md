# TraceAnalysis INI library and revision history

**Data & processing → TraceAnalysis INI library** is the working library of processing
documents. It is separate from **Scientific configuration history**, which
retains dated configurations, descriptions and links to caveats as evidence.
An upload does not assert a processing effective date or run any computation.

## Using the library

Select multiple `.ini` files, drag files onto the panel or use folder selection
to retain relative paths. A leading `TraceAnalysis_ini/` is removed. Station
filenames such as `UQAM_2_FirstStage.ini` are grouped under their station code
even when selected individually. Upload matching relative paths for updates;
other paths create distinct documents. Paths are matched case-insensitively
by the upload API. Parent/absolute/drive paths are rejected.

An optional revision note describes the change. Changed bytes produce a new
immutable revision; identical latest bytes are skipped. Reverting to an older
file creates another revision. **Read** previews text, **Download** returns the
exact stored bytes, and **Versions** lists prior files, notes, dates, sizes and
SHA-256 hashes. Source modification time describes a source file, not the date
the settings took effect. A missing source time is left unknown.

Uploads accept UTF-8 or Windows-1252 text, at most 100 files per batch, 5 MiB per
file and 25 MiB total. Invalid batches are rejected together. Contents are never
executed or rewritten. Keep credentials and private tower addresses out of files
that will appear in the public reference.

All team roles may read accessible station files and shared includes. Researchers,
managers and admins may upload for their writable sites. Updating shared or
unassigned station files requires network-wide access. Unknown station codes do
not create sites automatically. The supplied UQAM_0 pair remains unassigned and
visible to network-wide team accounts; it is not published as a registered site.
Editing needs a connection and is not part of the offline fieldwork queue.

## Supplied files and imports

Twenty INIs were copied from the supplied TraceAnalysis directory: eight shared
includes and first/second stage pairs for MCGILL_1 and UQAM_0 through UQAM_4.
`seed/processing_files/catalogue.json` records relative paths, hashes, sizes and
source modification times. Git treats these files as binary for line-ending
purposes, preserving the original bytes. Original source files were read only.

Initial setup and `import_resources` call the bundled import:

```bash
python manage.py import_processing_files
```

Bundled initialization skips files already having revisions, preserving newer
team uploads. To copy later files from a directory available to the server:

```powershell
python manage.py import_processing_files --directory 'W:\Database\Calculation_Procedures\TraceAnalysis_ini'
```

The explicit directory import reads recursively and adds changed versions; it
never writes to the source. A VM need not mount that directory: use browser
uploads from your workstation instead. Shared includes and current files for
registered sites are incorporated into the public report on its next load.

## Developer map

- `ProcessingFile` identifies a relative path and site; `ProcessingFileVersion`
  stores protected bytes and immutable revision metadata.
- `hub/processing_files.py` validates, authorizes, versions and serves files.
  `GET/POST /api/processing-files/` lists/uploads; authenticated
  `/processing-files/<version-id>/` downloads and `?preview=1` previews text.
- `static/hub/processing-files.js` provides upload, filtering and history UI.
- `import_processing_files` shares validation/storage with the API, while the
  public projection embeds only latest eligible documents.

Database and media backups are both required. File history is stored in protected
media, not committed back into Git or copied into the original source directory.
