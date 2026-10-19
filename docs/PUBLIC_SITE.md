# Public site

The live report is available without login at `/fieldnotes/`; its content is at
`/fieldnotes/content/`. `/reference/` redirects to the same report. Set
`PUBLIC_FIELDNOTES_ENABLED=False` to disable all report/export routes.

## Content and updates

The report reads the current database on each request, with caching disabled:

- Every site, including archived sites, with general reference information,
  current site conditions, supplied photos, active deployment geometry and
  reference sensor specifications. Unknown heights do not produce a diagram.
- Every visit, including in-progress visits, with crew, narrative, observations
  and completed work. Pending planning tasks are not published.
- Every caveat, including drafts labeled awaiting review, reviewed and resolved
  entries. Shared caveats appear once and can be filtered by affected site.
  A review or resolution changes its public status; reopening updates it again.
- Supplied diagnostic plots, common setup and latest INI downloads for registered
  sites and shared includes. Before the INI library is initialized, the original
  configuration evidence remains available as a fallback.

Save changes using the appropriate team editor and reload the public report.
Publication flags from earlier versions no longer filter this agreed content.
Unknown historical authors are allowed; review and resolution timestamps are
recorded on later status transitions. Measurement periods display fixed EST
(UTC−05:00); change timestamps are labeled UTC.

Inventory, BADM, protocols, telemetry, private connection settings and account
records are outside the public report. New documents/images/audio/video attached
to operational notes require authentication and site access. Only the known
imported scientific images are embedded publicly. Do not put confidential content
in site/visit/caveat text, since those records are public.

The public page and its timeline read the same current records. New visits,
observations, completed work, caveats, review statuses, site descriptions,
conditions, reference metadata, deployments and eligible INIs appear on the next
load. Use **Refresh public site** in the public header to load the latest saved
records. The team workspace's Public Field Notes link also opens a fresh report.
Offline changes must finish uploading through the existing sync queue first.

The timeline uses teal circles for routine maintenance, yellow squares for major
work and red diamonds for faults. Purple rings represent open/draft caveats;
green rings represent resolved caveats. A shared caveat has a marker in each
affected site's row, linking to one public entry, and counts once in the total.

Caveats with a known affected start use that date in fixed EST. If only the end
is known, that date is explicitly labeled as the affected end. Unknown dates
remain in a separate **Date unknown** area; reporting/update dates are never
substituted for measurement dates. Editing dates, affected sites or review status
updates the current markers without a separate publishing or rebuild step.
Hover or focus a marker for details; select it to open its record. Arrow keys
move through dated and undated markers. Site/type/search filters apply to both.

## Export and hosting

**Download HTML** (`/fieldnotes/download/`) produces a self-contained report with
embedded fonts, logo, images, styles, scripts and byte-preserving INI downloads.
Open it locally or host it on GitHub Pages. It is a snapshot: export and replace
it again after changes. Exported snapshots do not offer a live refresh control.
GitHub Pages cannot run the database or the live app.

`public/fieldnotes/index.html` is the retained original source, not a live page.
Changing that archive does not publish or overwrite database records. Historical
extraction/import commands remain documented in [Imports](IMPORTS.md).

## Implementation

`hub/public_report.py` selects named public fields and assembles the report;
`templates/public_report.html` and partials render them. The public CSS and
JavaScript are under `static/hub/public-report.*`. Browser code only filters,
searches, opens images and downloads embedded content; it makes no private API
requests. Public routes accept GET only.

The iframe and response Content-Security-Policy sandbox omit same-origin
privileges. Embedded images/fonts, inline styles/scripts and downloads are
allowed; private workspace cookies/APIs and external assets are isolated.
HTML text is escaped or sanitized. Review this projection and permissions when
adding new fields; never serialize arbitrary site metadata or attachment rows.
