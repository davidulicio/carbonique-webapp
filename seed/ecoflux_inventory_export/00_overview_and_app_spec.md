# EcoFlux / Carbonique field notes: overview and app specification

This folder contains the Carbonique eddy-covariance tower network reference export: site descriptions, classified visit summaries, data caveats, photographs, plots and processing files. This document describes its structure, conventions and known gaps.

| File | Content |
|---|---|
| `00_overview_and_app_spec.md` | This file: purpose, data model, screens, rules, conventions, known gaps |
| `01_sites_and_towers.md` | The 6 sites: description, coordinates, AmeriFlux ID, tower, power, every instrument with model, variables, heights/depths, separations, north offset, processing settings, plus the setup common to all sites |
| `02_field_notes.md` | All 127 field notes (Jul 2024 to 17 Sep 2026), grouped by site, with id, date, submitter, type, title and description |
| `03_data_caveats.md` | All 19 data-pipeline caveats with status (open/resolved), period, what happened, how to handle it, cross-checks, "needs confirming" flags, links and plots |
| `04_traceanalysis_ini_files.md` | The 8 recommended TraceAnalysis ini files: summary, caveats addressed, changed excerpt |
| `data/*.json` | The same content as structured JSON (best input for seeding a database) |
| `images/` | 8 diagnostic plots (`p_*.jpg`) and 7 site photos (`photo_<SITE>_<n>.jpg`) |
| `ini/` | Full text of the 8 ini files |

**Snapshot date:** field notes up to 2026-09-17; caveats up to edition 2026-09-29; site information from *Info on Carbonique EC sites.docx* (parsed 2026-09-24, corrected 2026-09-29). Exported 2026-10-16.

---

## 1. What the app is for

The Carbonique project (carbon dynamics in southern Quebec wetlands) runs six eddy-covariance flux towers. Field technicians record every site visit in the **EcoFlux Inventory** (a login-protected web app at `grandwazoo.ddns.net/ecoflux/`). On top of that, the data team keeps a list of **data caveats**: known problems in the recorded data that whoever processes it must correct.

The reference app combines these so that:

- a technician can see what was done at a tower, when a part was last swapped, and what is still pending for the next visit;
- a data processor can see which periods of data are affected by what, and how to correct them;
- anyone can look up a tower's instruments, heights and processing settings.

## 2. Source system: the EcoFlux Inventory (what is known of its structure)

These details come from reading the Inventory through a browser. They describe the parts used so far, not the whole app.

| Page | URL | Known content |
|---|---|---|
| Field notes list | `/ecoflux/fieldnotes/` | One table with every note (no pagination). Each row links to `/ecoflux/fieldnotes/edit/<id>/` and carries the submitter's name. |
| Field note form | `/ecoflux/fieldnotes/edit/<id>/` | Fields: `date_visited` (date input), `site` (select of site codes), `summary` (text input, sometimes empty), body (textarea, free text, often bulleted). |
| Sites list | `/ecoflux/sites/` | One row per site, including a **Notes** column with the number of field notes per site. |

**Field note ids** are integers, not contiguous, and not in date order.

**Not exported (not yet read):** the Inventory most likely has other pages too, such as equipment and instrument records, serial numbers, stock and site details. Those pages were not accessible for this export. The instrument information here comes from the *Info on Carbonique EC sites* Word document and from serial numbers quoted in field notes. Section 9 says how to complete this.

## 3. Data model

### Site

| Field | Type | Example |
|---|---|---|
| `code` | string, unique | `UQAM_3` (note: the Word document writes `MCGILL_1`, the Inventory `McGill_1`) |
| `name` | string | Carbonique Lac-à-la-Tortue Forested bog |
| `ameriflux_id` | string | `CA-CQ3` |
| `location` | string | Notre-Dame-du-Mont-Carmel, Quebec |
| `lat`, `lon` | decimal degrees | 46.5280, -72.6462 |
| `active_since` | date | 2025-04-10 |
| `ecosystem` / short description | text | Natural forested bog... |
| `description` | long text | from the Word document |
| `tower`, `power` | text | tall tower, certified yearly / EFOY methanol fuel cell |
| `canopy_height` | text or number (m) | 12.6 m (with displacement height and roughness length) |
| `photos[]` | image files | `images/photo_UQAM_3_1.jpg` |
| `sections[]` | ordered list of `{heading, items[{label, value}], instruments[]}` | Site info / Instruments info / Processing settings |

### Instrument (belongs to a site)

| Field | Type | Example |
|---|---|---|
| `kind` (section heading) | string | Sonic anemometer, CO2/H2O gas analyzer, Net Radiometer... |
| `model` | string | Campbell Scientific CSAT3B |
| `variables` | list | `WS_1_1_1, WD_1_1_1` |
| `height` / `depth` | text or m | 21.9 m / 8 cm |
| other labelled attributes | label → value | `North offset: 332°`, `Northward separation: 10 cm` |

In the source document instruments are free-form label/value lists. Keep them flexible (a key-value table), but normalise these labels because the mast diagram and the overview table depend on them: `Sonic height`, `TA_1_x_1, RH_1_x_1 (...)` levels, `Height`, `Intake heights`, `North offset`, `AmeriFlux ID`, `Station active since`, `Canopy height set in SmartFlux`.

### FieldNote (belongs to a site)

| Field | JSON key | Type | Notes |
|---|---|---|---|
| id | `id` | int | Inventory note id |
| site | `s` | site code | |
| date visited | `d` | date `YYYY-MM-DD` | |
| submitter | `w` | string | person's name |
| type | `t` | enum `routine` / `major` / `issue` | see rules in section 5 |
| title | `ti` | string | the Inventory summary, or a title derived from the content when the summary was empty |
| description | `b` | text | **rewritten prose** of the original note body (not the verbatim original); faults start with `PROBLEM:`; pending "next visit" tasks are at the end |

### DataCaveat (belongs to a site, or to `ALL`)

| Field | JSON key | Type | Notes |
|---|---|---|---|
| id | `id` | string | `pn1`... |
| site | `s` | site code or `ALL` | |
| edition | `ed` | date | the date this caveat was first written down |
| title | `ti` | string | |
| affected period | `period` | text | e.g. `2025-11-21 → 2026-05-07`, `All data to date` |
| what happened | `b` | HTML | may contain lists, tables, code |
| how to handle it | `fix` | HTML | |
| cross-check | `xref` | HTML | the field notes agree |
| needs confirming | `flag` | HTML | the field notes contradict it, or a detail is doubtful; a question for the data owner, never silently corrected |
| links | `links[]` | `{t, u}` | |
| plots | `plots[]` | `{k, c, file}` | image key, caption, file |
| status | `status` / `res` / `resnote` | open or resolved + date + note | |
| ini files | `ini_files[]` | file names | ini files carrying the fix |

### IniFile

`f` file name, `s` site, `st` stage (First stage / Second stage), `sum` summary, `adds[]` caveat ids it fixes, `ex` changed excerpt, full text in `ini/`, `kb` size.

### Relationships

```
Site 1 ── * Instrument
Site 1 ── * FieldNote
Site 1 ── * DataCaveat      (plus caveats with site = ALL)
DataCaveat * ── * IniFile   (IniFile.adds)
DataCaveat 1 ── * Plot
Site 1 ── * Photo
```

## 4. Screens of the existing reference page

The public reference page (`public/fieldnotes/index.html`) has two views.

**Maintenance log**

1. Summary tiles: field notes, routine visits, major work, faults, open data caveats (+ number resolved).
2. Visit timeline: one horizontal track per site, a marker per visit (circle = routine, square = major work, diamond = fault), three lanes to avoid overlap. Hover shows site, type, title, date, submitter; click scrolls to the note.
3. "Applies to every tower" banner listing the open `ALL` caveats.
4. Sticky filter bar: Everything / Routine / Major work / Faults / Data caveats only, plus a search box that matches notes and caveats; shows "N of M items shown".
5. One card per site: code, name, coordinates, active since, note count and date range, fault count; the site's open caveats; then every visit chronologically (date + submitter, type badge, title, description).
6. **Resolved caveats**: a collapsible section showing caveats already handled, with the recorded resolution date. The public report is read-only; authorized users manage caveats in the team workspace.
7. Recommended ini files: per file, tags, summary, the caveats it addresses (links), changed excerpt, "Show whole file", "Download".
8. Plot lightbox (click a plot to enlarge).

**Sites & towers**

1. At-a-glance table: AmeriFlux ID, EC (sonic) height, TA/RH heights, the TA/RH level closest to the EC height (used for gap-filling), north offset, canopy height, start date.
2. One card per site: description, photos, a mast diagram with the height of every sensor (canopy shaded when fixed), site information, one box per instrument, processing settings.
3. Setup common to all sites: variable naming, time base, data acquisition, SmartFlux processing, file locations.

Deep links: `#sites` opens the Sites view, `#site-UQAM_3` jumps to a site.

General: light/dark mode, works on a phone, fully self-contained (no external dependencies), Carbonique branding.

## 5. Rules for classifying visits

| Type | Use when |
|---|---|
| `routine` | Scheduled upkeep: sensor/mirror cleaning, data download and USB swaps, washer-fluid and methanol refills, guy-wire tightening, drone and vegetation surveys, debris and ice removal. |
| `major` | Planned significant work: installation and commissioning, instrument or logger upgrades, seasonal preparation, structural changes, tower certification, new sensors added. |
| `issue` | Driven by a fault or unplanned condition: instrument stopped, communication loss, blown fuse, clogged filter / flow drive at 100%, animal or weather damage, diagnostic visit, emergency trip. |

- A visit that combines routine tasks with a fault is `issue`.
- An `issue` description starts with `PROBLEM:`, then states the symptom, the diagnosis and what was done.
- Planned work that only reveals a problem is `issue` only if the problem is the main story.
- Pending or "next visit" tasks go at the end of the description.
- Serial numbers, firmware versions and part sizes are copied exactly.

## 6. Conventions

- **Variable names** follow AmeriFlux `VAR_H_V_R` (horizontal position, vertical level, replicate). For air sensors level 1 is the highest (`TA_1_1_1` is the top HygroVUE10). For soil, `_1_1_1` to `_1_4_1` are the profile from shallow to deep, `_2_1_1` to `_5_1_1` horizontal replicas.
- **Time:** all loggers and SmartFlux units record in EST (UTC-5) all year, with no daylight saving time.
- **Heights** are above the ground unless the site card says otherwise.
- **Spelling in the source notes varies:** desiccant / dessicant (also silica, sachet). "Desiccant" alone means the enclosure-box desiccant. The sonic anemometer's internal desiccant is written as "desiccant in the sonic".
- **Site codes:** `McGill_1` in the Inventory, `MCGILL_1` in the Word document and ini files.

## 7. Where the content comes from

| Source | Used for |
|---|---|
| EcoFlux Inventory field notes (login required) | Every visit |
| Word document *Inconsistencies, issues and sensor changes in the stations to tackle on the data pipeline* | Data caveats and their plots |
| Word document *Info on Carbonique EC sites* | Sites & towers view, photos |
| SmartFlux `.metadata` inside each `.ghg` file | Sonic heights, north offsets, separations, canopy heights |
| TraceAnalysis ini files (Calculation_Procedures/TraceAnalysis_ini/) | Recommended ini files |

## 8. Suggested features for a rebuilt app

These are what the current page does, plus what the static page cannot do:

- create/edit field notes directly (date, site, submitter, type, title, body, pending tasks as a checklist);
- a proper instrument register per site with serial numbers and swap history (the field notes mention many swaps that are not in a structured table yet);
- open/resolved workflow for data caveats with who resolved and when;
- a list of open "next visit" tasks across all sites;
- search and filter as in section 4.

## 9. Known gaps in this export

1. **Field notes after 2026-09-17 are missing.** The live Inventory could not be read for this export.
2. **The Inventory's own equipment, instrument and site pages were not read.** If they exist, they are not in this export.
3. **Field note descriptions are rewritten summaries**, not the verbatim original text, though serial numbers and figures are kept.
4. Pending and "next visit" tasks appear inside the note descriptions, not as a separate structured field.
