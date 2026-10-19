# Recommended TraceAnalysis ini files

Working copies for `Calculation_Procedures/TraceAnalysis_ini/`, each carrying the fixes for the data caveats it lists. Updated 2026-09-29. Nothing here has been applied to the live database: diff before committing. Full files are in the `ini/` folder; below are the summaries and the changed excerpts.

| File | Site | Stage | Size | Addresses |
|---|---|---|---|---|
| [UQAM_2_FirstStage.ini](ini/UQAM_2_FirstStage.ini) | UQAM_2 | First stage | 64 KB | pn13, pn14 |
| [UQAM_2_SecondStage.ini](ini/UQAM_2_SecondStage.ini) | UQAM_2 | Second stage | 23 KB | pn13, pn14 |
| [UQAM_3_FirstStage.ini](ini/UQAM_3_FirstStage.ini) | UQAM_3 | First stage | 71 KB | pn13, pn15 |
| [UQAM_3_SecondStage.ini](ini/UQAM_3_SecondStage.ini) | UQAM_3 | Second stage | 25 KB | pn13, pn15 |
| [UQAM_4_FirstStage.ini](ini/UQAM_4_FirstStage.ini) | UQAM_4 | First stage | 48 KB | pn13, pn17 |
| [UQAM_4_SecondStage.ini](ini/UQAM_4_SecondStage.ini) | UQAM_4 | Second stage | 15 KB | pn13, pn17 |
| [MCGILL_1_FirstStage.ini](ini/MCGILL_1_FirstStage.ini) | McGill_1 | First stage | 51 KB | pn4, pn13, pn18 |
| [MCGILL_1_SecondStage.ini](ini/MCGILL_1_SecondStage.ini) | McGill_1 | Second stage | 19 KB | pn4, pn13, pn18 |

## UQAM_2_FirstStage.ini

- **Site:** UQAM_2 · **Stage:** First stage · **Size:** 64 KB
- **Addresses:** pn13 (Water table depth: every CS456 datum is wrong, and the offset lives in the logger); pn14 (WTD datum was 1.3 m short)

WTD_1_1_1 now reads Lvl_psi_Avg with the datum applied as a dated calibration. Sensor depth 2.05 m, measured at installation; was 0.79 m.

**What changed (excerpt):**

```ini
% Revisions
%   - 24 September 2026 (David Trejo)
%     WTD_1_1_1: sensor depth set to the measured 2.05 m (written installation
%     note); it was 2.08 m from a tie-in to the settled record.
%
%   - 23 September 2026 (David Trejo)
%
%     WATER TABLE DEPTH - AMERIFLUX SIGN CONVENTION AND DATUM  ----------------
%     Corrected 2026-09-23 after checking
%     https://ameriflux.lbl.gov/data/measurement-height/
%     "Positive values are heights, and negative values are depths."
%     So for WTD:  POSITIVE = water ABOVE the surface, NEGATIVE = below it.
%
%     That is the sign the CR1000X already produces:
%         Lvl_m = Lvl_psi*0.70307 - WTD_offset
%     Lvl_psi*0.70307 is the height of water standing ABOVE the sensor and
%     WTD_offset is the sensor's depth below the surface, so the subtraction
%     gives height relative to the surface, positive up.  The logger's SIGN was
%     never the problem - only the offset VALUES were wrong.
%
%     The trace now reads Lvl_psi_Avg (raw gauge pressure, psi) rather than
%     Lvl_m_Avg, and the datum is applied here as a dated calibration:
%         currentCalibration = [gain offset start end]  ->  value*gain + offset
%         gain   = +0.70307        psi -> m of water
%         offset = -2.05            minus the sensor's depth below the surface
%     so  WTD = Lvl_psi_Avg*0.70307 - 2.05
%
%     Keeping the datum here rather than in the logger means a correction is
%     dated, reviewable and retroactive.  Nothing anywhere recorded which
%     WTD_offset was in force on which date - it had to be recovered by
%     differencing archived Lvl_psi_Avg against Lvl_m_Avg.  The logger should
%     be changed to publish raw head only (Lvl_m = Lvl_psi*0.70307); until it
%     is, Lvl_m_Avg stays in the Met folder but must not be used.
%
%     DATUM, measured at installation (written installation note): sensor
%     2.05 m below the surface, water table 0.13 m BELOW the surface.
%     The archive starts 2026-04-27 13:30 and the sensor was still equilibrating
%     that evening (head climbed 1.41 -> 1.95 m).  By 2026-04-28 00:00 head had
%     settled at 1.9533 m, i.e. WTD = 1.9533 - 2.05 = -0.10 m, 3 cm above the
%     installation reading, as expected while a freshly augered hole recovers.
%     (An earlier tie-in to that settled reading gave 2.08 m; the measured
%     2.05 m replaces it.)  The trace starts 2026-04-28 to exclude the transient.
%
%     Barometric compensation is NOT an issue: the CS456 is a vented gauge
%     sensor and aM1! returns psiG.  Regressing 30-min changes in head on
%     30-min changes in station pressure gives a slope within 0.01 m/kPa of
%     zero, against +0.102 for a sensor with no vent compensation.
%
%

%  ...

% CHANGED 2026-09-23: AmeriFlux sign convention (+ = above the surface).
% Sourced from Lvl_psi_Avg with the datum applied here; the positive gain is the
% psi->m conversion and the offset is minus the sensor's depth below the surface:
%     WTD = Lvl_psi_Avg * 0.70307 - 2.05
% Datum measured at installation (sensor 2.05 m deep), see header.
[Trace]
    variableName        = 'WTD_1_1_1'
    title               = 'water table depth - CS456 (+ = above surface)'
    originalVariable    = 'gauge pressure above the transducer'
    inputFileName       = {'Lvl_psi_Avg'}
    inputFileName_dates = [ datenum(2026,4,28) datenum(2999,12,31)]
    measurementType     = 'Met'
    units               = 'm'
    instrument          = 'CS456'
    instrumentType      = ''
    instrumentSN        = '70010296'
    loggedCalibration   = []
    currentCalibration  = [ 0.70307 -2.05 datenum(2026,4,28) datenum(2999,12,31)]
    comments            = 'Sensor 2.05 m below the peat surface, measured at installation (water table 0.13 m below the surface then). The trace starts 2026-04-28 00:00, after the equilibration transient. Was Lvl_m_Avg with an in-logger offset of 0.79 m, which was about 1.3 m short.'
    minMax              = [-0.6 0.3]
    zeroPt              = [-9999]
[End]
```

## UQAM_2_SecondStage.ini

- **Site:** UQAM_2 · **Stage:** Second stage · **Size:** 23 KB
- **Addresses:** pn13 (Water table depth: every CS456 datum is wrong, and the offset lives in the logger); pn14 (WTD datum was 1.3 m short)

Pass-through unchanged; the title states the AmeriFlux convention and the header records the datum and the despiking still outstanding.

**What changed (excerpt):**

```ini
%
% September 23, 2026 (David Trejo)
%   - WTD_1_1_1: companion to the first-stage water table fix.  The Evaluate is
%     unchanged - the trace arrives from first stage already converted and on the
%     right sign - but the title now states the convention, because "water table
%     depth" on its own is what let a sign question go unsettled for a season.
%     AMERIFLUX CONVENTION: positive = above the surface, negative = below it
%     (https://ameriflux.lbl.gov/data/measurement-height/).
%     First stage reads Lvl_psi_Avg and applies
%     currentCalibration = [0.70307 -<sensor_depth_below_surface> <start> ...].
%     This site: sensor 2.05 m below the peat surface (measured at installation).
%   - Not done here, but worth adding: the CS456 record carries isolated
%     half-hour spikes, always downward and nearly always around midday, which
%     look like someone at the well.  They sit inside minMax so first stage does
%     not catch them.  A 3-hour running-median filter removes them cleanly
%     (5 points in the 2026 record at this site).

%  ...

% CHANGED 2026-09-23: AmeriFlux sign, + = above the surface.  Arrives from first
% stage as Lvl_psi_Avg with the datum applied there (sensor 2.05 m below the peat surface.)
[Trace]
	variableName    = 'WTD_1_1_1'
	Evaluate        = 'WTD_1_1_1 = WTD_1_1_1;'
	title           = 'water table depth - CS456 (+ = above surface)'
	units           = 'm'
[End]
```

## UQAM_3_FirstStage.ini

- **Site:** UQAM_3 · **Stage:** First stage · **Size:** 71 KB
- **Addresses:** pn13 (Water table depth: every CS456 datum is wrong, and the offset lives in the logger); pn15 (Three different datums in one season)

WTD_1_1_1 now reads Lvl_psi_Avg. Sensor depth 1.83 m, from the 11.5 cm reading of 10 June; was 0.00 then 1.75 then 1.48 m.

**What changed (excerpt):**

```ini
% Revisions
%   - 23 September 2026 (David Trejo)
%
%     WATER TABLE DEPTH - AMERIFLUX SIGN CONVENTION AND DATUM  ----------------
%     Corrected 2026-09-23 after checking
%     https://ameriflux.lbl.gov/data/measurement-height/
%     "Positive values are heights, and negative values are depths."
%     So for WTD:  POSITIVE = water ABOVE the surface, NEGATIVE = below it.
%
%     That is the sign the CR1000X already produces:
%         Lvl_m = Lvl_psi*0.70307 - WTD_offset
%     Lvl_psi*0.70307 is the height of water standing ABOVE the sensor and
%     WTD_offset is the sensor's depth below the surface, so the subtraction
%     gives height relative to the surface, positive up.  The logger's SIGN was
%     never the problem - only the offset VALUES were wrong.
%
%     The trace now reads Lvl_psi_Avg (raw gauge pressure, psi) rather than
%     Lvl_m_Avg, and the datum is applied here as a dated calibration:
%         currentCalibration = [gain offset start end]  ->  value*gain + offset
%         gain   = +0.70307        psi -> m of water
%         offset = -1.83            minus the sensor's depth below the surface
%     so  WTD = Lvl_psi_Avg*0.70307 - 1.83
%
%     Keeping the datum here rather than in the logger means a correction is
%     dated, reviewable and retroactive.  Nothing anywhere recorded which
%     WTD_offset was in force on which date - it had to be recovered by
%     differencing archived Lvl_psi_Avg against Lvl_m_Avg.  The logger should
%     be changed to publish raw head only (Lvl_m = Lvl_psi*0.70307); until it
%     is, Lvl_m_Avg stays in the Met folder but must not be used.
%
%     DATUM TIE-IN: water table 0.115 m BELOW the surface on 2026-06-10 (11.5 cm, measured).
%     Head that day averaged 1.7162 m, so the sensor sits 1.7162 + 0.115 = 1.831 -> 1.83 m
%     below the surface.  SUPERSEDES an earlier figure of 0.24 m for the same visit,
%     which would have put the sensor at 1.96 m; 1.83 m is the value to use.  With
%     1.83 m the 2026 season runs -0.49 m to +0.11 m, i.e. about 11 cm of ponding at
%     snowmelt.  The in-logger offsets were 0.00 m, then 1.75 m from 2026-04-27, then
%     1.48 m from 2026-06-10 - all wrong, so the whole 2026 record needs reprocessing.
%     The trace starts 2026-04-21 16:00, once the sensor had settled after the
%     2026-04-15 installation; 21-27 April must never be reprocessed from Lvl_m_Avg,
%     where no offset was loaded and the logger published raw head under a WTD name.
%
%     Barometric compensation is NOT an issue: the CS456 is a vented gauge
%     sensor and aM1! returns psiG.  Regressing 30-min changes in head on
%     30-min changes in station pressure gives a slope within 0.01 m/kPa of
%     zero, against +0.102 for a sensor with no vent compensation.
%
%

%  ...

% CHANGED 2026-09-23: AmeriFlux sign convention (+ = above the surface).
% Sourced from Lvl_psi_Avg with the datum applied here; the positive gain is the
% psi->m conversion and the offset is minus the sensor's depth below the surface:
%     WTD = Lvl_psi_Avg * 0.70307 - 1.83
% Datum confirmed by field measurement.
[Trace]
    variableName        = 'WTD_1_1_1'
    title               = 'water table depth - CS456 (+ = above surface)'
    originalVariable    = 'gauge pressure above the transducer'
    inputFileName       = {'Lvl_psi_Avg'}
    inputFileName_dates = [ datenum(2026,4,21,16,0,0) datenum(2999,12,31)]
    measurementType     = 'Met'
    units               = 'm'
    instrument          = 'CS456'
    instrumentType      = ''
    instrumentSN        = '70010297'
    loggedCalibration   = []
    currentCalibration  = [ 0.70307 -1.83 datenum(2026,4,21) datenum(2999,12,31)]
    comments            = 'Sensor 1.83 m below the peat surface. Tie-in: WTD = -0.115 m on 2026-06-10, head 1.7162 m. Supersedes an earlier 0.24 m figure for the same visit. Was Lvl_m_Avg with in-logger offsets of 1.75 m then 1.48 m, both wrong.'
    minMax              = [-0.8 0.5]
    zeroPt              = [-9999]
[End]
```

## UQAM_3_SecondStage.ini

- **Site:** UQAM_3 · **Stage:** Second stage · **Size:** 25 KB
- **Addresses:** pn13 (Water table depth: every CS456 datum is wrong, and the offset lives in the logger); pn15 (Three different datums in one season)

Pass-through unchanged; the title states the convention and the header records the offset history and why all of 2026 needs reprocessing.

**What changed (excerpt):**

```ini
%
% September 23, 2026 (David Trejo)
%   - WTD_1_1_1: companion to the first-stage water table fix.  The Evaluate is
%     unchanged - the trace arrives from first stage already converted and on the
%     right sign - but the title now states the convention, because "water table
%     depth" on its own is what let a sign question go unsettled for a season.
%     AMERIFLUX CONVENTION: positive = above the surface, negative = below it
%     (https://ameriflux.lbl.gov/data/measurement-height/).
%     First stage reads Lvl_psi_Avg and applies
%     currentCalibration = [0.70307 -<sensor_depth_below_surface> <start> ...].
%     This site: sensor 1.83 m below the peat surface, confirmed by tape on 2026-06-10.
%   - Not done here, but worth adding: the CS456 record carries isolated
%     half-hour spikes, always downward and nearly always around midday, which
%     look like someone at the well.  They sit inside minMax so first stage does
%     not catch them.  A 3-hour running-median filter removes them cleanly
%     (11 points in the 2026 record at this site).
%

%  ...

% CHANGED 2026-09-23: AmeriFlux sign, + = above the surface.  Arrives from first
% stage as Lvl_psi_Avg with the datum applied there (sensor 1.83 m below the peat surface, confirmed by tape on 2026-06-10.)
[Trace]
	variableName    = 'WTD_1_1_1'
	Evaluate        = 'WTD_1_1_1 = WTD_1_1_1;'
	title           = 'water table depth - CS456 (+ = above surface)'
	units           = 'm'
[End]
```

## UQAM_4_FirstStage.ini

- **Site:** UQAM_4 · **Stage:** First stage · **Size:** 48 KB
- **Addresses:** pn13 (Water table depth: every CS456 datum is wrong, and the offset lives in the logger); pn17 (WTD came from the EasyProbe, and the CS456 datum has the wrong sign)

WTD_1_1_1 moved off the EasyProbe level channel onto the CS456. Sensor depth 3.15 m: needs confirming against the 2.70 m hole depth; was −1.57 m.

**What changed (excerpt):**

```ini
% Revisions
%   - 23 September 2026 (David Trejo)
%
%     WATER TABLE DEPTH - AMERIFLUX SIGN CONVENTION AND DATUM  ----------------
%     Corrected 2026-09-23 after checking
%     https://ameriflux.lbl.gov/data/measurement-height/
%     "Positive values are heights, and negative values are depths."
%     So for WTD:  POSITIVE = water ABOVE the surface, NEGATIVE = below it.
%
%     That is the sign the CR1000X already produces:
%         Lvl_m = Lvl_psi*0.70307 - WTD_offset
%     Lvl_psi*0.70307 is the height of water standing ABOVE the sensor and
%     WTD_offset is the sensor's depth below the surface, so the subtraction
%     gives height relative to the surface, positive up.  The logger's SIGN was
%     never the problem - only the offset VALUES were wrong.
%
%     The trace now reads Lvl_psi_Avg (raw gauge pressure, psi) rather than
%     Lvl_m_Avg, and the datum is applied here as a dated calibration:
%         currentCalibration = [gain offset start end]  ->  value*gain + offset
%         gain   = +0.70307        psi -> m of water
%         offset = -3.15            minus the sensor's depth below the surface
%     so  WTD = Lvl_psi_Avg*0.70307 - 3.15
%
%     Keeping the datum here rather than in the logger means a correction is
%     dated, reviewable and retroactive.  Nothing anywhere recorded which
%     WTD_offset was in force on which date - it had to be recovered by
%     differencing archived Lvl_psi_Avg against Lvl_m_Avg.  The logger should
%     be changed to publish raw head only (Lvl_m = Lvl_psi*0.70307); until it
%     is, Lvl_m_Avg stays in the Met folder but must not be used.
%
%     DATUM TIE-IN: water found at 1.85 m depth at installation on 2026-05-15.
%     *** NEEDS CONFIRMING.  Head had settled at 1.297 m by 12:59 that day, so the tie-in
%     implies a sensor depth of 1.297 + 1.85 = 3.147 -> 3.15 m.  The field note for the
%     same visit records that the hole goes down to 270 cm, and a sensor cannot sit
%     3.15 m down a 2.70 m hole.  The likeliest explanation is that 1.85 m is where
%     water was first STRUCK while augering, not the settled water table: the record
%     starts at 10:30 with a head of only 0.169 m and fills through the day, which is
%     the hole recovering.  If the sensor is in fact at the bottom of the hole, change
%     the two numbers below to 2.70 / -2.70 and the season reads -1.10 to -1.75 m
%     instead of -1.55 to -2.20 m.  Measure the cable drop on the next visit.
%     The trace starts 2026-05-16 to exclude the day the hole was still filling.
%
%     Barometric compensation is NOT an issue: the CS456 is a vented gauge
%     sensor and aM1! returns psiG.  Regressing 30-min changes in head on
%     30-min changes in station pressure gives a slope within 0.01 m/kPa of
%     zero, against +0.102 for a sensor with no vent compensation.
%
%

%  ...

% CHANGED 2026-09-23: AmeriFlux sign convention (+ = above the surface).
% Sourced from Lvl_psi_Avg with the datum applied here; the positive gain is the
% psi->m conversion and the offset is minus the sensor's depth below the surface:
%     WTD = Lvl_psi_Avg * 0.70307 - 3.15
% *** DATUM NEEDS CONFIRMING - conflicts with the 2.70 m hole depth. See header.
[Trace]
    variableName        = 'WTD_1_1_1'
    title               = 'water table depth - CS456 (+ = above surface)'
    originalVariable    = 'gauge pressure above the transducer'
    inputFileName       = {'Lvl_psi_Avg'}
    inputFileName_dates = [ datenum(2026,5,16) datenum(2999,12,31)]
    measurementType     = 'Met'
    units               = 'm'
    instrument          = 'CS456'
    instrumentType      = ''
    instrumentSN        = '70010299'
    loggedCalibration   = []
    currentCalibration  = [ 0.70307 -3.15 datenum(2026,5,15) datenum(2999,12,31)]
    comments            = 'Sensor 3.15 m below the surface, from the tie-in WTD = -1.85 m at installation 2026-05-15 with head 1.297 m. NEEDS CONFIRMING: the field note for that visit says the hole goes down to 270 cm, so 3.15 m is not possible; 1.85 m was probably the depth at which water was struck while augering. If the sensor is at the hole bottom use 2.70. Was L_WATER_Avg from the EasyProbe, which has no water table sensor at this site.'
    minMax              = [-2.6 -1.2]
    zeroPt              = [-9999]
[End]
```

## UQAM_4_SecondStage.ini

- **Site:** UQAM_4 · **Stage:** Second stage · **Size:** 15 KB
- **Addresses:** pn13 (Water table depth: every CS456 datum is wrong, and the offset lives in the logger); pn17 (WTD came from the EasyProbe, and the CS456 datum has the wrong sign)

Pass-through; the title states the convention and the header records the disputed datum.

**What changed (excerpt):**

```ini
%
% September 23, 2026 (David Trejo)
%   - WTD_1_1_1: companion to the first-stage water table fix.  The Evaluate is
%     unchanged - the trace arrives from first stage already converted and on the
%     right sign - but the title now states the convention, because "water table
%     depth" on its own is what let a sign question go unsettled for a season.
%     AMERIFLUX CONVENTION: positive = above the surface, negative = below it
%     (https://ameriflux.lbl.gov/data/measurement-height/).
%     First stage reads Lvl_psi_Avg and applies
%     currentCalibration = [0.70307 -<sensor_depth_below_surface> <start> ...].
%     This site: sensor 3.15 m below the surface - NEEDS CONFIRMING, conflicts with the 2.70 m hole depth in the field note.
%   - Not done here, but worth adding: the CS456 record carries isolated
%     half-hour spikes, always downward and nearly always around midday, which
%     look like someone at the well.  They sit inside minMax so first stage does
%     not catch them.  A 3-hour running-median filter removes them cleanly
%     (5 points in the 2026 record at this site).

%  ...

% CHANGED 2026-09-23: AmeriFlux sign, + = above the surface.  Arrives from first
% stage as Lvl_psi_Avg with the datum applied there (sensor 3.15 m below the surface - NEEDS CONFIRMING, conflicts with the 2.70 m hole depth in the field note.)
[Trace]
	variableName    = 'WTD_1_1_1'
	Evaluate        = 'WTD_1_1_1 = WTD_1_1_1;'
	title           = 'water table depth - CS456 (+ = above surface)'
	units           = 'm'
[End]
```

## MCGILL_1_FirstStage.ini

- **Site:** McGill_1 · **Stage:** First stage · **Size:** 51 KB
- **Addresses:** pn4 (TW_5_1_1 renamed TW_1_5_1 in the logger on 2026-09-28); pn13 (Water table depth: every CS456 datum is wrong, and the offset lives in the logger); pn18 (Open water measured against a datum 1.7 m out)

TW_1_5_1 reads TW_5_1_1_Avg until 2026-09-28 11:30 and TW_1_5_1_Avg from the 12:00 record. Open water: stage over the lake bed, not a soil water table. Moved off the EasyProbe onto the CS456; sensor depth −0.16 m (the transducer sits above the bed, so the depth is legitimately negative); was 1.58 m.

**What changed (excerpt):**

```ini
%   - 29 September 2026 (David Trejo)
%
%     TW_1_5_1 - RENAMED IN THE LOGGER  ---------------------------------------
%     The deepest water thermocouple of the profile (5 cm above the bottom) was
%     logged as TW_5_1_1, which reads as a horizontal replicate.  It belongs to
%     the vertical profile, so it is TW_1_5_1.  The logger program was changed on
%     2026-09-28 at 11:40 EST: the 12:00 half-hour record is the first written as
%     TW_1_5_1, everything before it is under TW_5_1_1.
%
%     One trace reads both names through two rows of inputFileName_dates:
%         TW_5_1_1_Avg   2025-09-25 (installation)  ->  2026-09-28 11:45
%         TW_1_5_1_Avg   2026-09-28 11:45           ->  open
%     11:45 falls between the 11:30 and 12:00 records, so no record is claimed by
%     both names.
%
%     *** Column names assumed to follow the _Avg pattern of the other traces;
%     check them against the Met file headers before committing.
%     *** Still to sort out: TW_1_1_1 below is the EasyProbe (T_WATER_Avg) and
%     clashes with the thermocouple TW_1_1_1; TW_1_2_1 to TW_1_4_1 have no trace;
%     TS_1_1_1 to TS_1_4_1 are described as CS650 at 8/16/32/64 cm but the site
%     has thermocouples at 5, 10 and 20 cm.
%

[Trace]
    variableName         = 'TW_1_5_1'
    title                = 'water temperature 5cm above the bottom (thermocouple profile)'
    originalVariable     = ''
    inputFileName        = {'TW_5_1_1_Avg','TW_1_5_1_Avg'}
    inputFileName_dates  = [ datenum(2025,9,25) datenum(2026,9,28,11,45,0);
                             datenum(2026,9,28,11,45,0) datenum(2999,12,31)]
    measurementType      = 'Met'
    units                = '°C'
    instrument           = 'Thermocouple'
    instrumentSN         = ''
       loggedCalibration = [ 1 0 datenum(2025,9,25) datenum(2999,12,31)]
       currentCalibration= [ 1 0 datenum(2025,9,25) datenum(2999,12,31)]
    comments             = 'Deepest water thermocouple of the profile in the PVC pipe beside the platform, 5 cm above the bottom. Logged as TW_5_1_1 until the 11:30 record of 2026-09-28; renamed TW_1_5_1 in the logger at 11:40 EST, so the 12:00 record is the first under the new name.'
    minMax               = [-5,40]
    dependent            = ''
    zeroPt               = -9999
[End]

% Revisions
%   - 23 September 2026 (David Trejo)
%
%     WATER TABLE DEPTH - AMERIFLUX SIGN CONVENTION AND DATUM  ----------------
%     Corrected 2026-09-23 after checking
%     https://ameriflux.lbl.gov/data/measurement-height/
%     "Positive values are heights, and negative values are depths."
%     So for WTD:  POSITIVE = water ABOVE the surface, NEGATIVE = below it.
%
%     That is the sign the CR1000X already produces:
%         Lvl_m = Lvl_psi*0.70307 - WTD_offset
%     Lvl_psi*0.70307 is the height of water standing ABOVE the sensor and
%     WTD_offset is the sensor's depth below the surface, so the subtraction
%     gives height relative to the surface, positive up.  The logger's SIGN was
%     never the problem - only the offset VALUES were wrong.
%
%     The trace now reads Lvl_psi_Avg (raw gauge pressure, psi) rather than
%     Lvl_m_Avg, and the datum is applied here as a dated calibration:
%         currentCalibration = [gain offset start end]  ->  value*gain + offset
%         gain   = +0.70307        psi -> m of water
%         offset = +0.16            minus the sensor's depth below the surface
%     so  WTD = Lvl_psi_Avg*0.70307 + 0.16   (the depth is negative here)
%
%     Keeping the datum here rather than in the logger means a correction is
%     dated, reviewable and retroactive.  Nothing anywhere recorded which
%     WTD_offset was in force on which date - it had to be recovered by
%     differencing archived Lvl_psi_Avg against Lvl_m_Avg.  The logger should
%     be changed to publish raw head only (Lvl_m = Lvl_psi*0.70307); until it
%     is, Lvl_m_Avg stays in the Met folder but must not be used.
%
%     SITE CONTEXT: McGill_1 is open water.  The CS456 is a stage sensor measuring
%     the depth of the water column over the lake bed, not a well in soil.  There is
%     no unsaturated zone, so the value is positive all season by construction and
%     the sign convention never bites here - but the DATUM still does, and it was
%     out by 1.7 m.
%
%     DATUM TIE-IN: 0.87 m of water standing ABOVE the lake bed at installation on
%     2026-05-28.  Head that day averaged 0.7109 m, so the transducer sits
%     0.7109 - 0.87 = -0.159 -> -0.16 m relative to the bed, i.e. about 16 cm ABOVE
%     it, on its mount in the water column.  A NEGATIVE sensor depth is the normal
%     case at an open-water site and is not a sign error: it simply means the
%     reference surface is below the transducer.  The arithmetic is unchanged,
%     WTD = head - depth, so a negative depth adds rather than subtracts.
%
%     *** The installation was reported as reading 1.1265 psi; the archive has
%     1.0098-1.0133 psi across the whole of 28 May and never exceeds 1.10 psi before
%     2 July, so the archived value is used.  If 1.1265 psi is right the sensor sits
%     at -0.08 m instead, an 8 cm difference - worth resolving.
%
%     *** Check the Ameriflux BASE name before the next upload.  WTD is defined as
%     water table depth; this is a surface-water stage measurement at an aquatic
%     site.  Wetland sites commonly report standing water under WTD as a positive
%     value, which is what is done here, but if Ameriflux has a dedicated
%     surface-water variable it belongs there instead.  The number does not change
%     either way, only the label.
%
%     Before this change WTD_1_1_1 was fed from L_WATER_Avg with no date limit, so
%     the pre-CS456 record was EasyProbe level masquerading as water table depth.
%
%     Barometric compensation is NOT an issue: the CS456 is a vented gauge
%     sensor and aM1! returns psiG.  Regressing 30-min changes in head on
%     30-min changes in station pressure gives a slope within 0.01 m/kPa of
%     zero, against +0.102 for a sensor with no vent compensation.
%

%  ...

% CHANGED 2026-09-23: AmeriFlux sign convention (+ = above the surface).
% Sourced from Lvl_psi_Avg with the datum applied here; the positive gain is the
% psi->m conversion and the offset is minus the sensor's depth below the surface:
%     WTD = Lvl_psi_Avg * 0.70307 + 0.16   (depth is negative: sensor above the bed)
% Open water: stage over the lake bed. A negative sensor depth is normal here.
% Reported installation psi disagrees with the archive - see header.
[Trace]
    variableName        = 'WTD_1_1_1'
    title               = 'water level over the lake bed - CS456 (+ = above the bed)'
    originalVariable    = 'gauge pressure above the transducer'
    inputFileName       = {'Lvl_psi_Avg'}
    inputFileName_dates = [ datenum(2026,5,28,11,0,0) datenum(2999,12,31)]
    measurementType     = 'Met'
    units               = 'm'
    instrument          = 'CS456'
    instrumentType      = ''
    instrumentSN        = ''
    loggedCalibration   = []
    currentCalibration  = [ 0.70307 0.16 datenum(2026,5,28) datenum(2999,12,31)]
    comments            = 'Open-water site: this is the depth of the water column over the lake bed, not a soil water table. Sensor 0.16 m ABOVE the bed, so the depth is negative - normal for a stage sensor and not a sign error. Tie-in: 0.87 m of water above the bed at installation 2026-05-28, archived head 0.7109 m. The reported installation reading of 1.1265 psi does not appear anywhere on that date (archive 1.0098-1.0133 psi); if it is correct the depth becomes -0.08 m. Check the Ameriflux BASE name: WTD is water table depth and this is surface-water stage. Was L_WATER_Avg from the EasyProbe with no date limit.'
    minMax              = [0.5 1.4]
    zeroPt              = [-9999]
[End]
```

## MCGILL_1_SecondStage.ini

- **Site:** McGill_1 · **Stage:** Second stage · **Size:** 19 KB
- **Addresses:** pn4 (TW_5_1_1 renamed TW_1_5_1 in the logger on 2026-09-28); pn13 (Water table depth: every CS456 datum is wrong, and the offset lives in the logger); pn18 (Open water measured against a datum 1.7 m out)

Adds the TW_1_5_1 pass-through. Pass-through; the title says water level over the lake bed, and the header records the negative datum, the psi discrepancy and the BASE-name question.

**What changed (excerpt):**

```ini
% September 29, 2026 (David Trejo)
%   - TW_1_5_1: pass-through of the renamed deepest water thermocouple (logged as
%     TW_5_1_1 until 2026-09-28 11:30; first stage joins the two names).
%

[Trace]
	variableName    = 'TW_1_5_1'
	Evaluate        = 'TW_1_5_1 = TW_1_5_1;'
	title           = 'water temperature 5cm above the bottom (thermocouple profile)'
	units           = '°C'
[End]

%
% September 23, 2026 (David Trejo)
%   - WTD_1_1_1: companion to the first-stage water table fix.  The Evaluate is
%     unchanged - the trace arrives from first stage already converted and on the
%     right sign - but the title now states the convention, because "water table
%     depth" on its own is what let a sign question go unsettled for a season.
%     AMERIFLUX CONVENTION: positive = above the surface, negative = below it
%     (https://ameriflux.lbl.gov/data/measurement-height/).
%     First stage reads Lvl_psi_Avg and applies
%     currentCalibration = [0.70307 -<sensor_depth_below_surface> <start> ...].
%     This site: open water. The CS456 is a stage sensor over the lake bed, so the
%     depth is negative (-0.16 m, sensor above the bed) and the value is positive
%     all season by construction. Check the Ameriflux BASE name before upload:
%     WTD is water table depth, this is surface-water stage.
%   - Not done here, but worth adding: the CS456 record carries isolated
%     half-hour spikes, always downward and nearly always around midday, which
%     look like someone at the well.  They sit inside minMax so first stage does
%     not catch them.  A 3-hour running-median filter removes them cleanly
%     (0 points in the 2026 record at this site).
% 
% Aug 6, 2026 Rosie
%	- Removed RH_F_1_1_1 and RH_F_1_2_1 traces fully (commented out for now), given there is no suitable data for gap-filling.

%  ...

% CHANGED 2026-09-23: AmeriFlux sign, + = above the surface.  Arrives from first
% stage as Lvl_psi_Avg with the datum applied there. Open water: stage over the lake
% bed, sensor 0.16 m above it, so the sensor depth is negative.
[Trace]
	variableName    = 'WTD_1_1_1'
	Evaluate        = 'WTD_1_1_1 = WTD_1_1_1;'
	title           = 'water level over the lake bed - CS456 (+ = above the bed)'
	units           = 'm'
[End]
```
