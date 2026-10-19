# EcoFlux compatibility and upstream changes

The unified application adapts applicable EcoFlux changes through
`295f850fdd7d999c3f415531da2e36be312510a6`, compared with the original integration
base `664dc23ffcaef148b1a66e03d1cc627a7ca810a8`.

## Incorporated behavior

- Related-record tabs organize site reference, assigned equipment, visits, files
  and data identifiers. Equipment dialogs separate service history and files.
- Responsive navigation and the winter tower photograph inform the site selector;
  supplied Carbonique logos, typography and install icons identify this app.
- Tab actions use non-submit buttons and retain unfinished form text. Keyboard
  tab navigation supports arrows, Home and End with selected-state announcements.
- Site-specific equipment and attachment lists respect the selected site.
- Closely spaced sensor labels remain separated without changing recorded heights.
- Prepared assets participate in the service worker's cache update lifecycle.

The inspected upstream changes did not alter inventory models or migrations.
This standalone app has its own additional migrations for workflows and resources;
run `migrate` on every upgrade.

## Reviewing future upstream changes

Compare upstream commits before adapting them. Review shared model/table names
and migration dependencies against a staging copy of existing data. Keep useful
behavior within this app's shared navigation, permission and data model rather
than adding a second runtime. Update source provenance in [UPSTREAM.md](../UPSTREAM.md).

Run the application checks in [VALIDATION.md](VALIDATION.md), then check affected
browser flows, accessibility, selected-site scope and offline updates. The
deployment update procedure is in [DEPLOYMENT.md](DEPLOYMENT.md).
