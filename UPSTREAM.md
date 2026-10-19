# Source provenance

This application was built for the Carbonique site network using the following source projects and workflows:

| Repository | Inspected commit | Reused content |
|---|---|---|
| https://github.com/hknox/EcoFlux_resources | `295f850fdd7d999c3f415531da2e36be312510a6` | Inventory models, original migrations 0001–0012, upload-path helpers; latest navigation, related-record layout, header photograph and icons; retained author comments |
| https://github.com/davidulicio/carbonique-field-log | `d08166970f69b09480796ba2277f7b56d49522eb` | Field workflow design and Carbonique SVG branding |
| https://github.com/davidulicio/carbonique_fieldnotes | `c75bdcff90d1f993f53f79c3137176b231ba90d7` | Public report; extracted classified notes, caveats, site reference, photographs and plots |

The field frontend, Django APIs, new workflow models, synchronization, import/backup commands and deployment package were implemented for this unified application. Original source/data attribution remains with its authors. This package does not assign a new license to upstream material.

The Field Notes report retains its supplied scientific content; obsolete editor-service hooks have been removed and file downloads use the browser. It is available as a replaceable public snapshot independently of the editable database reference.

The initial integration used EcoFlux commit
`664dc23ffcaef148b1a66e03d1cc627a7ca810a8`. Applicable navigation, related-record
and visual changes through `295f850` were adapted for the unified interface.
See [docs/UPSTREAM_UPDATE.md](docs/UPSTREAM_UPDATE.md) for compatibility guidance.

Read-only tower queries are adapted from
[EC-Monitor](https://github.com/davidulicio/EC-Monitor), inspected at `797a96c`.
Its MIT notice is preserved in [docs/EC_MONITOR_LICENSE.txt](docs/EC_MONITOR_LICENSE.txt).
The bundled PDF.js files retain their Apache-2.0 license, and Roboto font files
retain their SIL Open Font License notices under `static/hub/vendor/pdfjs/` and `static/hub/fonts/`, respectively.

ICOS BADM definitions and source workbook hashes are recorded in
`seed/badm/schema.json`. Supplied field records and processing recommendations
retain their source context and scientific uncertainties.
