# Field notes

Every field note from the EcoFlux Inventory, 127 in total, from 2024-07-08 to 2026-09-17. Each visit is classified as **Routine maintenance**, **Major work** or **Fault / intervention** (a visit that mixes routine tasks with a fault counts as a fault, and its description starts with `PROBLEM:`). Descriptions are rewritten as prose from the original note body; serial numbers, firmware versions and part sizes are kept verbatim. `id` is the EcoFlux Inventory note id (`/ecoflux/fieldnotes/edit/<id>/`).

## Counts

| Site | Notes | Routine | Major work | Faults | First visit | Last visit |
|---|---|---|---|---|---|---|
| McGill_1 | 26 | 6 | 8 | 12 | 2025-06-28 | 2026-09-11 |
| UQAM_1 | 33 | 18 | 5 | 10 | 2024-07-08 | 2026-09-15 |
| UQAM_2 | 22 | 12 | 5 | 5 | 2025-06-03 | 2026-09-01 |
| UQAM_3 | 25 | 10 | 3 | 12 | 2025-07-02 | 2026-09-01 |
| UQAM_4 | 18 | 3 | 10 | 5 | 2025-10-14 | 2026-09-17 |
| UQAM_5 | 3 | 1 | 2 | 0 | 2026-07-22 | 2026-08-11 |
| **Total** | **127** | 50 | 33 | 44 | | |

Submitters: Chloe Kaplan (61), David Trejo (58), Laurent (4), Mathis Vossaert (2), Martina Schlaipfer (1), not recorded (1)


## McGill_1 — Lac Saint-Pierre Restored Marsh (26 notes)

### 2025-06-28 · Installation

- **Note id:** 59
- **Site:** McGill_1
- **Date visited:** 2025-06-28
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Installed PAR sensors and the bottom HygroVUE10; connected power cables to the distribution box; mounted the LI-7700, CSAT3B and tipping bucket. Re-used the original LI-7550 (the one that had fallen into the water) after confirming it was undamaged.

### 2025-07-04 · Installation

- **Note id:** 60
- **Site:** McGill_1
- **Date visited:** 2025-07-04
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Installed the CNR4 and top HygroVUE10, fitted the LI-7200 head, connected the AM16/32 to the CR1000X, mounted the wind monitor and ran power from the electrical box to the power box.

### 2025-07-09 · Installation

- **Note id:** 61
- **Site:** McGill_1
- **Date visited:** 2025-07-09
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Installed the platform ladder; repositioned the sonic anemometer, IRGA head and LI-7700 into their correct orientations; routed radiation-sensor cables along the boom guy wires; added a horizontal pipe for the snow-height sensor; downloaded data from the battery-box CR1000.

### 2025-07-16 · Installation: grounding and solar fusing

- **Note id:** 62
- **Site:** McGill_1
- **Date visited:** 2025-07-16
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Short day (diverted by the Phenocam failure at UQAM_1). Connected the ground electrical box to the battery box, built the grounding system for the solar array and installed 20 A inline fuses on each solar string.

### 2025-07-23 · Installation: wiring completed

- **Note id:** 63
- **Site:** McGill_1
- **Date visited:** 2025-07-23
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Fitted proper electrical clamps on the lightning-protection cables, brought power to the towers and finished wiring the station.

### 2025-07-29 · Installation + muskrat cable damage

- **Note id:** 64
- **Site:** McGill_1
- **Date visited:** 2025-07-29
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

Installed a 20 A load breaker in the battery box, fitted surge protectors and wired the whole EC system. PROBLEM: the outer rubber of the electrical cables had been chewed, most likely by the muskrats on site. Metal armour and inner rubber still keep water out, but further diagnosis and a permanent solution are needed. Access through the marsh is difficult: suggested a rope between the battery system and the tower to pull boats across.

### 2025-07-31 · Installation: station commissioned

- **Note id:** 65
- **Site:** McGill_1
- **Date visited:** 2025-07-31
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Configured the system and assigned IPs to every component; entered site information into the EC system; sealed electrical box inlets with electrical putty and left desiccants inside; protected most cable glands against humidity. Station running and transmitting data from this date. Zip ties deliberately left unclipped as bird deterrents. Still missing: snow-depth sensor, soil/water sensors, battery-box internet, Phenocam.

### 2025-08-07 · Vegetation survey + antennas

- **Note id:** 66
- **Site:** McGill_1
- **Date visited:** 2025-08-07
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Vegetation survey of the area (species to be confirmed in the lab and added to the Phenocam site). Connected internet antennas to give the battery-box datalogger connectivity and installed an Ethernet surge protector on the Phenocam.

### 2025-08-13 · Clean-up (cut short by storm)

- **Note id:** 67
- **Site:** McGill_1
- **Date visited:** 2025-08-13
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Intended to remove all remaining boxes and parts and configure the Phenocam, but heavy rain and a thunderstorm stopped work. Only pallets and scraps were brought back to UQAM. Dave visited to see the solar-panel platform as a model for the natural marsh site.

### 2025-08-19 · Excessive noise in the LI-7200

- **Note id:** 68
- **Site:** McGill_1
- **Date visited:** 2025-08-19
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the IRGA produced wildly noisy concentrations (from negative values to thousands) with strongly varying signal strength, alternating with periods of correct measurement. Worked through LI-COR's troubleshooting protocol (check LI-7550 Power/Ready LEDs, reseat and inspect the head cable and connectors for dust or bent pins, check the intake rain cap for blockage, listen to the chopper for grinding, swap head and cable if spares exist). Also found the IRGA base had shifted: probably wind-bent intake tube. Straightening the tube and reseating the cables appeared to fix it, but the fault returned after leaving the site. Phenocam also configured.

### 2025-08-21 · Whole LI-7200 system replaced

- **Note id:** 69
- **Site:** McGill_1
- **Date visited:** 2025-08-21
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

Since the 2025-08-19 visit did not resolve the noise, the entire IRGA system (LI-7200 head, intake tube, cables and LI-7550) was swapped out so the faulty set could be analysed in the lab while data collection continued. EC system reconfigured. Ethernet cable changed so the Phenocam runs on PoE and is fully protected by the Ethernet surge protector.

### 2025-09-05 · EasyProbe installed

- **Note id:** 70
- **Site:** McGill_1
- **Date visited:** 2025-09-05
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned LI-7700 mirrors, installed the EasyProbe and updated the program to McGill_05 to include the thermocouples.

### 2025-09-10 · Improvements

- **Note id:** 71
- **Site:** McGill_1
- **Date visited:** 2025-09-10
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Connected the water- and soil-temperature thermocouples to the loggers (not yet measuring). Basic maintenance: sensor cleaning and data download.

### 2025-09-25 · Thermocouple profile installation

- **Note id:** 72
- **Site:** McGill_1
- **Date visited:** 2025-09-25
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Cleaned the CH4 sensor and moved the thermocouple Ethernet cable from the brainbox to the VOLT116. Installed thermocouples in the large PVC pipe beside the platform: drilled drainage holes, could not hammer the pipe deeper than -20 cm so the -50 cm sensor could not be installed (one spare thermocouple left over); sensors secured with pairs of zip ties, larger access holes drilled for the 50 cm and 100 cm sensors; pipe hammered in and fixed to the adjacent metal pipe. PROBLEM: the wires became tangled during installation and could not be sorted without dismantling; a return visit is needed to unplug and reconnect them at the junction box so each sensor can be identified.

### 2025-11-10 · Winter preparation

- **Note id:** 73
- **Site:** McGill_1
- **Date visited:** 2025-11-10
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Connected 12 V, 24 V and current measurements to the main CR1000X for remote monitoring (program modified, now McGill_V06). Replaced desiccant bags. Installed the SnowVUE10 (calibration file updated to the real sensor height on 2025-11-11). Removed the EasyProbe (freezing damage risk) and removed the sonic wicks to stop ice building on the transducers.

### 2026-01-07 · Flow drive at 100%

- **Note id:** 74
- **Site:** McGill_1
- **Date visited:** 2026-01-07
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the flow module's drive had risen to 100%. Reached the site on foot over ice thick enough to carry heavy loads. Changed the LI-7200 intake rain cap and the Swagelok filter of the heated intake tube (2 µm → 15 µm). Levelled the scaffolding to the platform's new inclination, re-tensioned the guy wires and cleaned the LI-7700.

### 2026-04-23 · Eddy system failure: emergency visit after winter

- **Note id:** 85
- **Site:** McGill_1
- **Date visited:** 2026-04-23
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the eddy system stopped working on Friday 17 April. The site access permit had not been renewed, so an emergency supervised visit had to be arranged with National Defence. Diagnosis: the LI-7550 (SN 2497) was damaged, most likely the analog board. Replaced it with SN 2495 and updated the calibration coefficients to the correct IRGA (all calibration files saved). Grounding checked on every sensor and the network switch in the datalogger box also grounded. Levelled platform and tower after the ice melt, tightened tower and solar-structure guy wires and nuts, cleaned the methane sensor, refilled washer fluid with 70% 2-propanol, replaced the SmartFlux (SN00817 → SN00782, 40 GB) and updated firmware to v2.4.4, replaced the LI-7200 intake filter and rain cap, reinstalled the EasyProbe for summer, swapped USB sticks and replaced box desiccants. Pending until the permit is renewed: clean and calibrate the IRGAs, install a security camera, replace the instrument desiccants, ground the battery-box logger.

### 2026-05-28 · No communication with the battery-monitoring logger

- **Note id:** 102
- **Site:** McGill_1
- **Date visited:** 2026-05-28
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: no communication with the CR1000 battery-monitoring logger. The Campbell box had been opened and some Ethernet cables were damaged; they were replaced but further troubleshooting is still required. Grounded the box, the logger and the whole battery-monitoring system, plus the electrical box at the tower. Cleaned the methane and radiation sensors, sorted the thermocouple cables and added a CS456 to measure water table depth (values are negative because the water sits above ground: this is correct). Notes: the tipping bucket had no mesh (replacement ordered); the antennas appear powered but do not communicate.

### 2026-06-11 · Antenna diagnosis

- **Note id:** 96
- **Site:** McGill_1
- **Date visited:** 2026-06-11
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

Cleaned the LI-7700 and diagnosed the antennas. PROBLEM traced to the battery system's network switch: neither the logger nor the antenna can be reached through it, so it needs replacing.

### 2026-06-25 · Cleaning

- **Note id:** 107
- **Site:** McGill_1
- **Date visited:** 2026-06-25
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700, removed spider webs from the sensors and along the tower, drilled a hole for the boom-holding pin and added an Ethernet switch to the battery box: the antenna connection still needs more troubleshooting.

### 2026-07-08 · Maintenance and LI-7700 troubleshooting

- **Note id:** 112
- **Site:** McGill_1
- **Date visited:** 2026-07-08
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

Cleaned the methane sensor and swapped the LI-7200 and LI-7550 for calibrated units (72H-1201, AIU-2491). PROBLEM: the methane sensor (TGA-1078) was not working; a blown fuse in the power box blew again as soon as it was replaced, so the power board is probably damaged. Put new desiccant into the sonic anemometer. Next visit: bring a replacement LI-7700 and diagnose the failing one in the lab.

### 2026-07-15 · LI-7700 fault resolved; solar panels down

- **Note id:** 116
- **Site:** McGill_1
- **Date visited:** 2026-07-15
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

Brought a replacement LI-7700 (TG1-1030), but the original (TG1-1027) turned out to have only a loose cable and worked once reconnected: probably shaken loose by vibration, so the pipes holding the 7700 were adjusted to reduce movement. Cleaned the Phenocam. PROBLEM: two solar panels fell; the other two in that series were disconnected, so the station now runs on four panels. Next visit: build a new solar-panel structure (current setup should hold through the summer).

### 2026-07-30 · Cleaning

- **Note id:** 120
- **Site:** McGill_1
- **Date visited:** 2026-07-30
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

LI-7700 cleaning.

### 2026-08-18 · Thorough cleaning and maintenance

- **Note id:** 125
- **Site:** McGill_1
- **Date visited:** 2026-08-18
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the station was full of spiders, spider eggs and webs, and the LI-7700's signal strength had been wiggling badly as a result; webs strung between the sensor legs move in the wind and modulate the RSSI. An intense cleaning was done but they are expected to come back. Routine work alongside: cleaned the LI-7700, replaced its desiccant and refilled the washer tank, releveled the floating platform, retightened the guy wires, reconnected remote communication to the CR1000 logging the battery-box variables, and photographed the site for the environmental report. Also noted: the sonic anemometer is missing its wicks.

### 2026-09-04 · LI-7700 swap and solar panel structure destroyed by wind

- **Note id:** 134
- **Site:** McGill_1
- **Date visited:** 2026-09-04
- **Submitted by:** Mathis Vossaert
- **Type:** Fault / intervention (`issue`)

PROBLEM: powerful winds put almost all of the solar panels on the ground. The mounting structures were heavily damaged and many wires and connectors with them; most panels still appear functional but one is cracked. To stop the batteries draining to 0 V the system was shut down almost completely, leaving only the sonic anemometer running, and the panels were stacked facing each other so they would stop generating. Separately the LI-7700 was swapped for a new unit and cleaned with alcohol: pressure data looks better afterwards and, per Zoran, the methane concentration now looks correct for the site. A new SIM card was inserted, spider webs were cleared everywhere including inside the PhenoCam, and the rain gauge checked out fine. The sonic wicks were again not installed because they could not be found.

### 2026-09-11 · Four solar panels reconnected after the wind damage

- **Note id:** 135
- **Site:** McGill_1
- **Date visited:** 2026-09-11
- **Submitted by:** Mathis Vossaert
- **Type:** Fault / intervention (`issue`)

PROBLEM: follow-up to the 4 September storm damage. Four solar panels were reconnected in series and the modem rebooted with the new SIM card. The array was generating 44 A and the battery charging normally, and the sensors came back on and functional. Some cleaning and vegetation measurements were done at UQAM_5 on the same trip.


## UQAM_1 — Lac Saint-Pierre Disturbed Marsh (33 notes)

### 2024-07-08 · Flux tower installation: full instrumentation record

- **Note id:** 4
- **Site:** UQAM_1
- **Date visited:** 2024-07-08
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

System installed 8–16 July 2024, configured in UTC-5 (EST); LI-COR and CSI data sent to the McGill server for processing. EC sensors: LI-7200RS (SN 72H-1201), LI-7700 (SN TG1-1008), CSAT3B sonic (SN 1891), north offset 285°, sensor height 7.11 m, mounted on a retractable outrigger. Radiation: CNR4 (SN 234083) with CNF4 ventilation at 190° from north; PAR Apogee SQ-521 incoming (SN 5724) and outgoing (SN 5747). Boxes: SDM-CD16ACA SN 5143; SmartFlux2 SN00775; CR1000X SN 50873; VOLT116 SN 7700; BaroVUE10 SN 2790/2726; Airlink RV50X; AM16/32B SN 40259; LI-7550 SN AIU-491; FlowModule SN FM2-311; water reservoir; electrician's boxes. Soil: heat-flux plates at 50 and 100 cm either side of the CS650 profile, 8 cm depth (SN 23095–23098); CS650 profile at 8, 16, 32 and 64 cm (SN 61421, 61422, 61407, 61408). HygroVue10 SN E5508 at 2 m and SN E5509 at 7 m. Rain gauge TE525WS SN 96386-0923; SnowVUE10 SN 10954 at 2 m; Young 05103 wind monitor SN 196257 on top of the scaffolding; StarDot CAM-SEC5I Phenocam.

### 2024-08-29 · Electrical troubleshooting

- **Note id:** 20
- **Site:** UQAM_1
- **Date visited:** 2024-08-29
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the AC line supplying the tower is shared with the farmer's pump system, so an independent electrical supply is needed. As a stopgap a small battery was installed to power the Biomet sensors while there is no AC power.

### 2024-09-18 · Improvements: AC supply isolated

- **Note id:** 21
- **Site:** UQAM_1
- **Date visited:** 2024-09-18
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Replaced the boom retriever pipes, cleaned the LI-7700 lenses, installed guy-wire protection and added a 20 W solar panel to the Biomet electrical system. The electrician isolated the tower's electrical system from the pump's, so the AC line now runs smoothly.

### 2024-10-17 · Maintenance

- **Note id:** 22
- **Site:** UQAM_1
- **Date visited:** 2024-10-17
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700 lenses (signal strength recovered), cut back the remaining aluminium pipe supporting the eddy boom, downloaded data and changed the SmartFlux and LI-7550 USB sticks, cleaned the radiation-sensor lenses. Flagged for next visit: the box humidity indicators show the desiccant packs need changing; the aluminium pipe needs protecting to prevent injuries.

### 2024-11-08 · Maintenance: winter preparation

- **Note id:** 23
- **Site:** UQAM_1
- **Date visited:** 2024-11-08
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Data downloaded, USB sticks exchanged, LI-7700 mirrors cleaned, water reservoir filled with -40 °C windshield fluid, radiation-sensor mirrors cleaned, Phenocam case and lens cleaned, desiccants of every box changed and boxes cleaned, protection added to the aluminium lateral stabiliser pipe, sonic wicks removed to prevent snow and ice accumulating on the transducers over winter.

### 2025-01-17 · Winter maintenance

- **Note id:** 24
- **Site:** UQAM_1
- **Date visited:** 2025-01-17
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700 lenses, downloaded data, removed ice from the rain-gauge tipping bucket and installed the security camera and surveillance sign. Observations: the padlocks were frozen and the gate padlock could not be closed; the EasyProbe could not be checked because everything was frozen inside the pipe.

### 2025-02-07 · Clogged pump

- **Note id:** 25
- **Site:** UQAM_1
- **Date visited:** 2025-02-07
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the flow module's drive had risen to 87%. Replaced the cap filter and the 15 µm filter of the LI-7200, which brought the flow drive back to 50%. The old filters were taken to the lab for ultrasonic cleaning. Data downloaded and LI-7700 lenses cleaned.

### 2025-06-17 · Seeding under the radiation sensor

- **Note id:** 26
- **Site:** UQAM_1
- **Date visited:** 2025-06-17
- **Submitted by:** Martina Schlaipfer
- **Type:** Major work (`major`)

Soy seeding beneath the radiation sensor with UQAM, McGill and ULaval participants. Seeding density ~170,000 seeds/acre, 30" between rows, ~1" between beans in a row, ~2" depth. Loosening the soil across the whole area would have taken too long, so only the seeded rows were worked: leaving some vegetation on the surface so the patch does not match the rest of the field. Next year: rent a motor-driven tiller or bring a larger team with better tools.

### 2025-07-04 · LI-7700 mirror cleaning

- **Note id:** 27
- **Site:** UQAM_1
- **Date visited:** 2025-07-04
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700 mirrors. Observation: despite weekly cleaning the methane sensor's mirrors keep getting very dirty; possibly something being sprayed on the agricultural field. The seeded strip under the radiation sensor still looks different from the rest of the field because the machinery did not pass there; more extensive plant removal is recommended before seeding next year.

### 2025-07-09 · LI-7700 mirror cleaning

- **Note id:** 28
- **Site:** UQAM_1
- **Date visited:** 2025-07-09
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Quick stop to clean the methane sensor mirrors.

### 2025-07-16 · Phenocam repair

- **Note id:** 29
- **Site:** UQAM_1
- **Date visited:** 2025-07-16
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the Phenocam had stopped working. Diagnosis: adding the security camera to the same load raised power consumption and burned the 1 A fuse. Solution: replaced it with a 2 A fuse. Also cleaned the LI-7700 mirrors, downloaded data and swapped the USB stick.

### 2025-07-17 · Drone survey and vegetation height

- **Note id:** 30
- **Site:** UQAM_1
- **Date visited:** 2025-07-17
- **Submitted by:** not recorded
- **Type:** Routine maintenance (`routine`)

Drone flights with the Mavic-3 Pro (RGB) over the sites (Alexandre Roy and Sarah-Ève Dionne). Soy height measured at 10 random points: 26, 31, 24, 24, 20, 25, 24, 26, 27, 26 cm.

### 2025-07-29 · Drone survey, vegetation and tower maintenance

- **Note id:** 31
- **Site:** UQAM_1
- **Date visited:** 2025-07-29
- **Submitted by:** Laurent
- **Type:** Routine maintenance (`routine`)

Drone survey over the UQAM_1 footprint. Vegetation heights 20–47 cm at 21 random points; mean ~55 cm under the snow-depth sensor with some bare soil. Cleaned the CH4 sensor and adjusted the turnbuckles. Rest of the installation looked good.

### 2025-08-05 · More soil sensors added; EasyProbe removed

- **Note id:** 32
- **Site:** UQAM_1
- **Date visited:** 2025-08-05
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Added four CS650 probes as horizontal replicas of soil temperature, moisture and conductivity. PROBLEM: the EasyProbe was removed because it was not measuring correctly; clay works into the pipes and alters the readings, and the sensor was probably damaged over winter when it could not be pulled out of the ground. It went to the lab for checking. Also cleaned the methane sensor and cleared debris from the tipping bucket.

### 2025-08-14 · Drone survey, vegetation and tower maintenance

- **Note id:** 33
- **Site:** UQAM_1
- **Date visited:** 2025-08-14
- **Submitted by:** Laurent
- **Type:** Routine maintenance (`routine`)

Drone survey over the footprint. Vegetation heights 38–75 cm at 20 random points. Less vegetation under the snow-depth sensor than before, following the digging for the soil sensors. CH4 sensor cleaned.

### 2025-09-05 · Sonic anemometer noise diagnosed

- **Note id:** 34
- **Site:** UQAM_1
- **Date visited:** 2025-09-05
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: noise in the sonic anemometer occurring at the same time as drops in LI-7700 signal strength. Probable cause identified as the missing sonic wicks on the transducers; wicks to be fitted on the next visit to protect them from water. Basic maintenance also performed.

### 2025-09-10 · Basic maintenance

- **Note id:** 35
- **Site:** UQAM_1
- **Date visited:** 2025-09-10
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

LI-7700 mirrors cleaned, data downloaded, tipping bucket cleared of debris, guy wires tightened.

### 2025-09-18 · Drone survey, vegetation and tower maintenance

- **Note id:** 36
- **Site:** UQAM_1
- **Date visited:** 2025-09-18
- **Submitted by:** Laurent
- **Type:** Routine maintenance (`routine`)

Drone survey over the footprint. Vegetation heights 53–78 cm at 20 random points. Still limited vegetation under the snow-depth sensor: a mix of bare soil and small plants. CH4 cleaned and turnbuckles adjusted.

### 2025-10-03 · Drone survey, vegetation and tower maintenance

- **Note id:** 37
- **Site:** UQAM_1
- **Date visited:** 2025-10-03
- **Submitted by:** Laurent
- **Type:** Routine maintenance (`routine`)

Drone survey over the footprint. Vegetation heights 52–72 cm, measured at the top of the highest beans since no leaves remain in the field. CH4 cleaned and turnbuckles adjusted.

### 2025-11-10 · Basic maintenance

- **Note id:** 38
- **Site:** UQAM_1
- **Date visited:** 2025-11-10
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the methane sensor and the tipping bucket.

### 2025-12-15 · Filter and rain cap clogged

- **Note id:** 39
- **Site:** UQAM_1
- **Date visited:** 2025-12-15
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: flow drive at 100%. Replaced the clogged rain cap and filter (15 µm fitted). Remaining concern: the flow drive was at 100% but head pressure was only around -2.5 kPa when the pump should reach -3.5 to -4 kPa, so the system needs checking for leaks on a future visit; hose, connections, filters and everything from the sensor to the pump.

### 2026-01-07 · Basic maintenance

- **Note id:** 40
- **Site:** UQAM_1
- **Date visited:** 2026-01-07
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the methane sensor and re-secured the small solar panel that was working loose.

### 2026-05-01 · Power failure and summer preparation

- **Note id:** 90
- **Site:** UQAM_1
- **Date visited:** 2026-05-01
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: a power failure at the tower, caused by an exposed soil-sensor cable lying in water that short-circuited and blew several fuses. A muskrat was also living in the tower stairs. Diagnosed, troubleshot and fixed the power fault. Installed sonic wicks on the transducers; swapped the LI-7200 (72H-1201) and LI-7550 (AIU-2491) for cleaned and calibrated units (72H-1210 and AIU-2499); cleaned the methane sensor mirrors; replaced the SmartFlux SN00775 with SN00783 (40 GB) and updated firmware to v2.4.4.

### 2026-05-07 · Repairs

- **Note id:** 91
- **Site:** UQAM_1
- **Date visited:** 2026-05-07
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

Realigned the Phenocam, which had moved on 1 May and stayed misaligned until this visit. Repaired the tipping bucket and fixed it at the top of the tower. Replaced the PPFD_out sensor (SQ-521 SN 5747) with a new one (SQ-521 SN 5757). Cleaned the LI-7700 and CNR4. Connected an EasyProbe20 (SN 10237156) and a CS456 pressure transducer (SN 70010295).

### 2026-05-28 · Two soil sensors removed after animal damage

- **Note id:** 103
- **Site:** UQAM_1
- **Date visited:** 2026-05-28
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

Cleaned the methane sensor, filled the fluid washer and checked the station. PROBLEM: two CS650 sensors were found damaged with their cables chewed by an animal, so TS, SWC, S_CS650, E_CS650 and a_CS650 at positions 2_1_1 and 4_1_1 stopped working. Both sensors were taken to the lab for troubleshooting.

### 2026-06-04 · Seeding and pluvio installation

- **Note id:** 104
- **Site:** UQAM_1
- **Date visited:** 2026-06-04
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Installed the pluvio sensor structure with a small wooden platform for the solar panel and batteries. The antenna and solar mountings had not yet arrived. PROBLEM: the controller had a burned fuse, so the batteries could not be properly connected. Also seeded the soil under the radiation sensors with soy beans: the intention was to seed the same day the farmer seeded the rest of the field.

### 2026-06-11 · Starting the pluvio system and tower maintenance

- **Note id:** 97
- **Site:** UQAM_1
- **Date visited:** 2026-06-11
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700, added an antenna to the tower, reconnected a CS650 soil-moisture probe repaired in the lab (position 2_1_1 measuring again) and installed a security sign as a deterrent. Pluvio: replaced the blown controller fuse and added an internet connection.

### 2026-06-25 · Cleaning

- **Note id:** 108
- **Site:** UQAM_1
- **Date visited:** 2026-06-25
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700, tightened the pluvio guy wires and checked the amount of water accumulated in the pluvio.

### 2026-07-08 · Maintenance

- **Note id:** 113
- **Site:** UQAM_1
- **Date visited:** 2026-07-08
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the methane sensor, swapped USB sticks and removed the pluvio's transport bolts.

### 2026-07-30 · Cleaning

- **Note id:** 119
- **Site:** UQAM_1
- **Date visited:** 2026-07-30
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700.

### 2026-08-11 · LI-7200 troubleshooting

- **Note id:** 122
- **Site:** UQAM_1
- **Date visited:** 2026-08-11
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM with the LI-7200 system: swapped boards in the LI-7550, using the board from 72H-1206/AIU-2495 while keeping the original sensor and flow module, and replaced a fuse in the 7550. Also cleaned the LI-7700 and installed a soil sensor (SN 69277).

### 2026-08-18 · Maintenance

- **Note id:** 126
- **Site:** UQAM_1
- **Date visited:** 2026-08-18
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700, replaced the desiccant in both the LI-7700 and the CSAT3B, refilled the washer tank and retightened the guy wires. Worth watching: the Campbell datalogger enclosure is slowly disintegrating and releasing glass fibre, which none of the other boxes in the network are doing.

### 2026-09-15 · PhenoCam repair and maintenance

- **Note id:** 132
- **Site:** UQAM_1
- **Date visited:** 2026-09-15
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the PhenoCam had stopped sending images on 24 August. A basic reboot and reconfiguration fixed it. Also cleaned the LI-7700 and refilled the washer tank, swapped the USB sticks, checked the tipping bucket, swapped the modem SIM card from Telus to Bell, and tightened the guy wires on the pluviometer structure. Left for next visit: assemble the solar panel structure for the pluvio sensor and replace the rusty padlocks.


## UQAM_2 — Natural Lac-à-la-Tortue Open bog (22 notes)

### 2025-06-03 · Improved grounding system

- **Note id:** 5
- **Site:** UQAM_2
- **Date visited:** 2025-06-03
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Improved the lightning-protection system to avoid ground loops. Took down a string of solar panels that was tilting: a temporary measure until guy wires can be installed on the solar structure. Removed waste from the landowner's property (not all of it produced by the installation).

### 2025-07-02 · Reinstallation of EC sensors

- **Note id:** 6
- **Site:** UQAM_2
- **Date visited:** 2025-07-02
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Reinstalled the LI-7700, LI-7200 head and LI-7550. Installed cross wooden beams on the base structure of the solar panels and five screw piles around them for guy wires. Six-person team from UQAM, McGill and UQTR.

### 2025-07-08 · Ethernet surge protectors and configuration

- **Note id:** 7
- **Site:** UQAM_2
- **Date visited:** 2025-07-08
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Continued installing screw piles around the solar base, fitted Ethernet surge protectors inline at both ends of the LI-7700 and LI-7550 connections, and reconfigured the station so it began measuring again.

### 2025-07-16 · Communication issue: solar cables disconnected

- **Note id:** 8
- **Site:** UQAM_2
- **Date visited:** 2025-07-16
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the tower could not be reached remotely. On site the cables from the solar panels were found disconnected from the system. Power was restored by reconnecting the MC4 connectors, but the batteries needed several days to recharge before the system could run again. Also cleaned the methane sensor and installed guy wires for the solar system. Planned follow-up: improve the power system and bury all cables to avoid accidental disconnections.

### 2025-07-22 · Flow module not recording data

- **Note id:** 9
- **Site:** UQAM_2
- **Date visited:** 2025-07-22
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the flow module was not recording. Diagnosis: during the LI-7550 replacement the flow module had not been reconnected to the 7550, although it kept drawing air at 15 L/min all week. Quickly resolved by reconnecting it. Guy wires tightened and methane sensor cleaned.

### 2025-07-30 · CH4 sensor cleaning and guide wires

- **Note id:** 10
- **Site:** UQAM_2
- **Date visited:** 2025-07-30
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the CH4 sensor and adjusted the guide wires.

### 2025-08-07 · CH4 sensor cleaning and guide wires

- **Note id:** 11
- **Site:** UQAM_2
- **Date visited:** 2025-08-07
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the CH4 sensor and adjusted the guide wires.

### 2025-08-12 · CH4 sensor cleaning

- **Note id:** 12
- **Site:** UQAM_2
- **Date visited:** 2025-08-12
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the CH4 sensor.

### 2025-08-19 · CH4 sensor cleaning

- **Note id:** 13
- **Site:** UQAM_2
- **Date visited:** 2025-08-19
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the methane sensor.

### 2025-08-26 · Maintenance: bird spikes added

- **Note id:** 14
- **Site:** UQAM_2
- **Date visited:** 2025-08-26
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

The whole EC system was covered in bird droppings, a recurring problem, so bird spikes were added to the sensors. Phenocam refocused, sensors cleaned, water reservoir refilled.

### 2025-09-04 · Cleaning and electrical improvements

- **Note id:** 15
- **Site:** UQAM_2
- **Date visited:** 2025-09-04
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

The LI-7700 is still getting dirty: the birds appear unbothered by the spikes. Added a PV array isolator and an inline fuse for the solar panels to improve safety.

### 2025-09-11 · Maintenance and voltage measurements

- **Note id:** 16
- **Site:** UQAM_2
- **Date visited:** 2025-09-11
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Basic maintenance (sensor cleaning, data download) and connection of the 12 V and 24 V measurements.

### 2025-11-24 · Maintenance after hunting season

- **Note id:** 17
- **Site:** UQAM_2
- **Date visited:** 2025-11-24
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Reinstalled the solar panels, changed the cable from the solar panels to the tower, removed the electrical box and replaced it with MC4 connectors. Cleaned the LI-7700, tipping bucket and radiation sensor; filled the washer reservoir with 2-propanol for winter (lower toxicity than regular washer fluid); returned several boxes and materials to UQAM; removed the sonic wicks for winter. Future tasks: more MC4 connectors for the battery box, replace and bury the second solar array's cable, add guy wires and screw piles to the solar structure, return remaining boxes and pipes.

### 2025-12-17 · LI-7200 and LI-7550 replaced

- **Note id:** 18
- **Site:** UQAM_2
- **Date visited:** 2025-12-17
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the LI-7xx0 software was flagging sensor issues. On arrival the eddy boom was found to have moved at some point (visible in the data around midnight on 1 December) which may have damaged something, and corroded connections were found in the LI-7550. Weather was too bad for a thorough field diagnosis, so the LI-7550 (AIU-2495) and LI-7200 (72H-1206) were swapped for new units (AIU-2496, 72H-1207) and the originals taken for lab diagnosis. Methane sensor cleaned.

### 2026-01-19 · Basic maintenance

- **Note id:** 19
- **Site:** UQAM_2
- **Date visited:** 2026-01-19
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Sealed the boxes properly, changed the box desiccant, cleaned the LI-7700 and installed a parallel MC4 connector on the positive power cables from the solar panels. Next visits: install the parallel MC4 connector on the negative cables, check guy-wire tension, add screw piles with guy wires to hold the solar structure, replace the swivel clamp with the better Global Truss one.

### 2026-03-13 · Basic maintenance

- **Note id:** 79
- **Site:** UQAM_2
- **Date visited:** 2026-03-13
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700 mirrors, removed ice that had accumulated on the sensors and replaced the USB thumb drive.

### 2026-04-27 · Maintenance and SmartFlux upgrade

- **Note id:** 86
- **Site:** UQAM_2
- **Date visited:** 2026-04-27
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Replaced the SmartFlux with a 40 GB unit and updated its firmware to v2.4.4. Built a wooden-plank boardwalk between the solar structure and the tower (a permanent walkway is not permitted) to avoid sinking into the peat. Replaced the old boom swivel clamps with stronger ones, cleaned the LI-7700 mirrors, filled the fluid washer with 2-propanol, fitted sonic wicks to the CSAT3B and tightened the guy wires. Pending: replace the power cable and use MC4 connectors throughout, fit a longer boom retriever pipe, reposition the boxes to reduce tension on sensor cables, replace desiccants, add guy wires and screw piles to the solar structure and tighten every part of it.

### 2026-05-20 · LI-7550 not working

- **Note id:** 100
- **Site:** UQAM_2
- **Date visited:** 2026-05-20
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the eddy system was not working. The cause was a blown fuse in the LI-7550: an easy fix. Grounding lugs were double-checked and some tightened. Methane sensor cleaned.

### 2026-06-10 · Basic maintenance

- **Note id:** 95
- **Site:** UQAM_2
- **Date visited:** 2026-06-10
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700, replaced the pipe that moves the boom with a stronger steel one and tidied the cables on the tower.

### 2026-07-09 · Cleaning

- **Note id:** 115
- **Site:** UQAM_2
- **Date visited:** 2026-07-09
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700 and retrieved an auger left in the field.

### 2026-08-20 · Soil probe audit: HFP01 wiring does not match the cal file

- **Note id:** 128
- **Site:** UQAM_2
- **Date visited:** 2026-08-20
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the soil heat flux plates have an inconsistency between the field wiring and the logger's .cal file. The coefficients in the .cal are listed in ascending serial-number order, but the plates are not wired in that order, so each channel carries the wrong sensitivity. The error is purely multiplicative and can be fixed in the pipeline as G_corrected = G_logged x (S_used / S_true). Measured values: UQAM0137 SN 23102 on 2H/2L, 60.03 uV/W/m2 (16.6583 W/m2 per mV); UQAM0134 SN 23099 on 4H/4L, 61.33 uV/W/m2 (16.3052); UQAM0135 SN 23100 on 6H/6L, 62.61 uV/W/m2 (15.9719); UQAM0136 SN 23101 on 8H/8L, 61.08 uV/W/m2 (16.3720). Every CS650 location, serial number and installation was also rechecked and all were correct: vertical profile 1H SN 61438 (8 cm), 3H SN 61418 (16 cm), 5H SN 61426 (32 cm), 7H SN 61425 (64 cm); horizontal replicates 11H SN 61430, 13H SN 61415, 15H SN 61416, 17H SN 61417, all at 8 cm. Routine work alongside: cleaned the LI-7700, refilled the washer tank and repaired the wooden bridge to the site.

### 2026-09-01 · SIM card switch and cleaning

- **Note id:** 131
- **Site:** UQAM_2
- **Date visited:** 2026-09-01
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700 and switched the modem SIM card to Bell, which requires the updated IP address to be entered.


## UQAM_3 — Carbonique Lac-à-la-Tortue Forested bog (25 notes)

### 2025-07-02 · Basic maintenance

- **Note id:** 41
- **Site:** UQAM_3
- **Date visited:** 2025-07-02
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700 mirrors and radiation sensors. The cleaning protocol was demonstrated to Jacob Isabelle (UQTR). Six-person team from UQAM, McGill and UQTR.

### 2025-07-16 · Communication error: LI-7700 short circuit

- **Note id:** 42
- **Site:** UQAM_3
- **Date visited:** 2025-07-16
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the station could not be reached remotely. Diagnosis: the LI-7700 was short-circuiting. Disconnecting the methane sensor brought the rest of the system back online; no fuse had blown, only the LI-7700 was dead. Planned follow-up: replace the methane sensor, but only after installing a proper Ethernet surge protector on the cables. Also connected an Ethernet cable to the EFOY fuel cell for remote monitoring.

### 2025-07-22 · LI-7700 replaced

- **Note id:** 43
- **Site:** UQAM_3
- **Date visited:** 2025-07-22
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

Replaced the damaged LI-7700 with a newer unit, then cleaned and reconnected it: this time through Ethernet surge protectors.

### 2025-07-30 · CH4 sensor cleaned

- **Note id:** 44
- **Site:** UQAM_3
- **Date visited:** 2025-07-30
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the CH4 sensor.

### 2025-08-12 · CH4 sensor cleaning

- **Note id:** 45
- **Site:** UQAM_3
- **Date visited:** 2025-08-12
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the CH4 sensor.

### 2025-08-26 · Maintenance: EFOY online, wind monitor reoriented

- **Note id:** 46
- **Site:** UQAM_3
- **Date visited:** 2025-08-26
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Connected the EFOY 2800 hybrid system to the internet and linked it to the EFOY cloud (a licence is needed for remote viewing) and updated its firmware. Cleaned the methane sensor, refocused and grounded the Phenocam. PROBLEM found: the wind monitor box was oriented 300° from north instead of facing south, and was corrected; wind-direction data from before 26-08-2025 14:00 needs a correction applied first.

### 2025-09-04 · LI-7700 mirror cleaning

- **Note id:** 47
- **Site:** UQAM_3
- **Date visited:** 2025-09-04
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700 mirrors.

### 2025-09-11 · Basic maintenance

- **Note id:** 48
- **Site:** UQAM_3
- **Date visited:** 2025-09-11
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

LI-7700 cleaning and data download.

### 2025-11-24 · Maintenance after hunting season

- **Note id:** 49
- **Site:** UQAM_3
- **Date visited:** 2025-11-24
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Replaced the methanol canisters with new ones. Cleaned the LI-7700, tipping bucket and radiation sensor; filled the washer reservoir with 2-propanol for winter; returned several boxes and materials to UQAM; removed the sonic wicks in preparation for winter. Several pallets and boxes still to be removed.

### 2025-12-17 · Hybrid power system check: excess methanol consumption

- **Note id:** 51
- **Site:** UQAM_3
- **Date visited:** 2025-12-17
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the EFOY hybrid system had been consuming much more methanol than expected. The whole system was reviewed with an SFC/EFOY technician on the phone; everything was correctly connected and the conclusion was that the electrical requirements had been underestimated, so the system will need extra batteries and the hardware to connect them. The technician modified the EFOY heater temperature settings to reduce consumption and one air vent was blocked to keep cold air out (to be removed in warmer months). One methanol canister filled, 2.5 tanks left on site; methane sensor cleaned; 12 V and 24 V measurements connected to the logger.

### 2026-01-19 · SDI-12 sensors not working

- **Note id:** 52
- **Site:** UQAM_3
- **Date visited:** 2026-01-19
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the SDI-12 sensors were returning large numbers of NAN values. Diagnosis: no visible damage inside the boxes, but the BaroVUE10 (SN 2801) was dead and was replaced with a new one (SN 2896); the old one to be checked in the lab. Terminal screws had loosened, probably from temperature swings, and were retightened. The SnowVUE10 was not working but recovered after a restart. Also sealed the boxes, changed the box desiccant, swapped USB sticks; LI-7700 cleaning was not possible because of heavy snow. Next visits: check guy-wire tension and replace the swivel clamp. Potential improvement: add a relay to power-cycle the SDI-12 sensors remotely.

### 2026-01-30 · Maintenance: filters and BaroVUE10

- **Note id:** 53
- **Site:** UQAM_3
- **Date visited:** 2026-01-30
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: flow drive at 100%, so the LI-7200 filters had to be changed. The SDI-12 sensors were also still producing a few NAN values per period, mostly from the BaroVUE10 (SN 2801/2728), which was swapped for another unit (SN 2896/2820) to test whether that fixed it.

### 2026-02-16 · SDI-12 NAN assessment

- **Note id:** 50
- **Site:** UQAM_3
- **Date visited:** 2026-02-16
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: continued SDI-12 failures, specifically the HygroVUE10s (air temperature and RH) and the BaroVUE10 on C5. On site the CR1000X was measuring none of those variables. Conductivity was fine on all ports and terminal blocks (other SDI-12 sensors on the same terminals measured correctly) and a previous BaroVUE10 replacement had not helped. After updating the CR1000X firmware from 8.1.0 to 8.5.0 and reconfiguring naming and Ethernet settings, measurements returned, but NANs came back within a day along with many skipped scans and records. Also moved the SDI-12 sensor power to relay port 14, moved the modem power to the CR1000X 12 V, cleaned the LI-7700 and refilled the methanol canister. Next visits: tighten tower guy wires, measure power drain and voltage drop of each SDI-12 sensor individually, move the brainbox network switch to 12 V, and possibly replace the CR1000X.

### 2026-02-19 · SDI-12 issue: root cause found

- **Note id:** 81
- **Site:** UQAM_3
- **Date visited:** 2026-02-19
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

Final diagnosis of the long-running SDI-12 fault. After swapping the CR1000X (SN 50875 → SN 50878) without improvement, each sensor was tested individually and all worked; connecting them one by one revealed that the SQ-521 (PPFD_IN) was the culprit: although the sensor itself worked, it generated noise that prevented the logger from reading the other sensors. The sensor was removed and a replacement was to be brought on the next visit.

### 2026-03-13 · Basic maintenance

- **Note id:** 78
- **Site:** UQAM_3
- **Date visited:** 2026-03-13
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Reinstalled the PPFD_IN (PAR) sensor, refilled the methanol canister and cleaned ice off the LI-7700, anemometer, wind monitor and wherever else it had accumulated.

### 2026-03-27 · Eddy boom found rotated

- **Note id:** 80
- **Site:** UQAM_3
- **Date visited:** 2026-03-27
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the eddy boom was found pointing at 60° instead of its usual 332°. The old clamps securing the booms were replaced with heavy-duty ones to prevent further movement. Also tightened the guy wires, returned four pallets to UQAM (four remaining), refilled the LI-7700 washer with 2-propanol and cleaned the methane sensor.

### 2026-04-02 · Site tidy-up and cleaning

- **Note id:** 84
- **Site:** UQAM_3
- **Date visited:** 2026-04-02
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Removed pallets from the site (two still remain), cleaned the methane sensors and fitted nuts to the turnbuckles: some of the bottom nuts are still missing.

### 2026-04-09 · Tower re-certification

- **Note id:** 82
- **Site:** UQAM_3
- **Date visited:** 2026-04-09
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

The tower was certified for another year by engineer Luc Pelletier and everything went well. Note: some 3/4" reverse-thread nuts are missing from the turnbuckles and need to be installed.

### 2026-04-15 · Site preparation for summer season

- **Note id:** 83
- **Site:** UQAM_3
- **Date visited:** 2026-04-15
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

After winter the IRGA needed cleaning and calibration: signal strength was around 96%. Rain made field cleaning impractical, so the units were swapped for recently cleaned and calibrated ones: LI-7550 AIU-2494 → AIU-2492 and LI-7200 72H-1205 → 72H-1203 (the removed units to be cleaned and calibrated in the lab). Fitted sonic wicks to the CSAT3B. Swapped SmartFlux SN00780 → SN00785 (upgraded from 8 GB to 40 GB) and updated its firmware to v2.4.4. Installed a CS456 pressure transducer connected to the AM16/32 multiplexer: it still needs a logger program change to work. Water depth 11.5 cm; total tube length 309 cm with 110 cm sticking out.

### 2026-04-27 · Basic maintenance and EFOY Modbus configuration

- **Note id:** 87
- **Site:** UQAM_3
- **Date visited:** 2026-04-27
- **Submitted by:** David Trejo
- **Type:** Routine maintenance (`routine`)

Filled the methanol tanks, cleaned the methane sensor and configured Modbus on the EFOY computer (Modbus TCP port 502, remote access disabled, IP 192.168.13.55, subnet 255.255.255.0, gateway 192.168.13.31, DNS 8.8.4.4 and 1.1.1.1).

### 2026-06-10 · Cleaning and fuel-cell troubleshooting

- **Note id:** 94
- **Site:** UQAM_3
- **Date visited:** 2026-06-10
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

Cleaned the LI-7700. PROBLEM: the fuel cell reported that methanol was completely empty although one container was still full; troubleshooting on site did not work. The fuel manager has a fault on port 1: only one port is working. An email was sent to SFC and a response is awaited.

### 2026-06-22 · Profile system installation and EFOY troubleshooting

- **Note id:** 106
- **Site:** UQAM_3
- **Date visited:** 2026-06-22
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the EFOY was not working, so the system had to be shut down. Set up the profile system (housing and tubing attached at four levels on the tower and the two profile-system boxes fixed to the tower) but it is not running properly because the tower has no power. Next time: bring the missing 12 V positive cable, grounding clamp and cable, and extend the power cable.

### 2026-07-09 · New battery and profile system

- **Note id:** 114
- **Site:** UQAM_3
- **Date visited:** 2026-07-09
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Replaced the battery and connected the profile system's power cables to the batteries: the power system still needs updating before the profile system is fully operational. Powered the eddy system back up, cleaned the LI-7700, replaced the USB sticks, put Carbonique stickers on the boxes and swapped the desiccant of both the LI-7700 and the sonic anemometer. To bring next time: new Ethernet cable head, crimpers, network switch and new filters.

### 2026-08-20 · Soil probe audit: HFP01 wiring does not match the cal file

- **Note id:** 127
- **Site:** UQAM_3
- **Date visited:** 2026-08-20
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: same fault as UQAM_2 on the same day. The .cal coefficients are in ascending serial-number order but the plates are wired in a different order, so each channel uses the wrong sensitivity. Per-plate error: HFP(1) on 2H/2L -0.74 %, HFP(2) on 4H/4L +2.58 %, HFP(3) on 6H/6L -3.24 %, HFP(4) on 8H/8L +1.50 %; worst case about 3.2 %. At a soil heat flux of 30 W/m2 that is 0.2-1.0 W/m2 and at 100 W/m2 it is 0.7-2.6 W/m2. The four errors very nearly cancel in the mean (+0.03 %), so a plate-averaged G is essentially unaffected: the problem shows up in per-plate values, in spatial variability between plates, and in any energy-balance closure done plate by plate. It sits well below the HFP01's own ~3 % repeatability and 15 % nominal accuracy, so it is not data-destroying, but it is a genuine per-channel systematic bias and is trivially corrected in the pipeline as G_corrected = G_logged x (S_used / S_true). Measured values: UQAM0139 SN 23104 on 2H/2L, 61.60 uV/W/m2 (16.2338 W/m2 per mV); UQAM0140 SN 23105 on 4H/4L, 63.19 uV/W/m2 (15.8253); UQAM0141 SN 23106 on 6H/6L, 61.14 uV/W/m2 (16.3559); UQAM0138 SN 23103 on 8H/8L, 62.06 uV/W/m2 (16.1134). All CS650 locations and serials were rechecked and correct: vertical profile 1H SN 61423 / U0187 (8 cm), 3H SN 61432 / U0183 (16 cm), 5H SN 61434 / U0188 (32 cm), 7H SN 61427 / U0182 (64 cm); horizontal replicates 11H SN 61431 / U0184, 13H SN 61410 / U0181, 15H SN 61437 / U0185, 17H SN 61433 / U0186, all at 8 cm. Routine work alongside: cleaned the LI-7700, refilled the washer tank and repaired the wooden bridge to the site.

### 2026-09-01 · EFOY swapped for a loaner unit

- **Note id:** 130
- **Site:** UQAM_3
- **Date visited:** 2026-09-01
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the EFOY fuel cell was exchanged for a loaner. The fuel manager and the original generator unit were removed to be sent back to EFOY, leaving the system running on a single methanol cell. Also cleaned the LI-7700 and replaced the SIM card with a new Bell one, which needs the new IP address entered.


## UQAM_4 — Saint-Remi Disturbed Forested Peatland (18 notes)

### 2025-10-14 · Site preparation

- **Note id:** 54
- **Site:** UQAM_4
- **Date visited:** 2025-10-14
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Installed the screw pile and the base of the tower.

### 2025-12-10 · Installation (10–11 Dec): halted by snowstorms

- **Note id:** 55
- **Site:** UQAM_4
- **Date visited:** 2025-12-10
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Installed the tower infrastructure over 10–11 December but could not continue because of intense snowstorms; installation to resume after the holidays. Still missing: wiring all sensors, grounding several boxes, powering the station and configuring the system. The design uses two systems: a stationary AC-powered tower on the berm carrying the full eddy system, 2 HygroVUE10, a Phenocam, a Texas TE525WS tipping bucket, a Young 05103 wind monitor, a BaroVUE10, an EasyProbe and a CS456; plus a battery- and solar-powered moving tripod inside the field with CNR4 + CNF4, 5 HFP01, 5 CS650, a SnowVUE10, a SoilVUE10 and 2 SQ-521.

### 2026-01-12 · Final installation

- **Note id:** 56
- **Site:** UQAM_4
- **Date visited:** 2026-01-12
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Stations finished and now remotely accessible on a fixed IP; the Phenocam website is running. PROBLEM: frozen soil prevented installing most of the soil sensors; only one CS650 (TS_3_1_1) went in; a return visit with better weather is needed. Tower: AC power via TECK90 AWG10 cable to the electrical box, with 24 V and 12 V supplies; its CR1000X is the main logger, running the same program and configuration as the other stations. Tripod: 100 W solar panel, MPPT charger and a 12 V 100 Ah lead-carbon battery, with a rover CR1000X on local IP 192.168.13.214 and PakBus address 2. Pending: soil sensors, CNF4 connection, TECK90 cable brackets, anti-tilt solution for the tripod, wireless antennas between the two systems (currently an Ethernet cable), check the solar panel's influence on the radiation sensors, ferrite core on the wind-monitor cable, voltage measurements.

### 2026-01-22 · Finishing touches: 12 V supply replaced

- **Note id:** 57
- **Site:** UQAM_4
- **Date visited:** 2026-01-22
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the 12 V power supply was not working correctly and was replaced with a new one. Reconnected the Phenocam. Connected the CR1000X to the Campbell PS150 battery so power-down alerts arrive and supply voltages can be seen remotely, and added 12 V and 24 V measurements to the CR1000X (variables Voltage_12V and Voltage_24V).

### 2026-02-09 · CR1000X and modem communication failure

- **Note id:** 58
- **Site:** UQAM_4
- **Date visited:** 2026-02-09
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

PROBLEM: the CR1000X had not been working properly since around 23:00 on 7 January. Because the modem and network switch are powered from the logger's SW12-1 and SW12-2, they were down too. Extreme cold (about -31 °C wind chill) left no time to troubleshoot properly; the logger appeared to be stuck in an infinite reboot loop. The logger SN 50876 was swapped for SN 52479, the network switch moved onto the 12 V from the power supply and the modem onto the 12 V from the CR1000X. Improvement identified for all stations: move modem and network-switch power onto the relay so they can be controlled.

### 2026-04-08 · Site preparation for summer season

- **Note id:** 88
- **Site:** UQAM_4
- **Date visited:** 2026-04-08
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Trailer construction 50% complete. Updated the SmartFlux2 firmware. Installed the soil sensors: SoilVue10 SN 4403 on SDI-12 address 1; CS650 on addresses 2–5 (SN 69250, 69251, 69252, 69253); HFP01 plates SN 23107–23110 with sensitivities 59.54, 61.12, 59.65 and 61.05. Cleaned the methane sensor mirrors and tightened the guy wires.

### 2026-04-17 · Site preparation for summer season

- **Note id:** 89
- **Site:** UQAM_4
- **Date visited:** 2026-04-17
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Finished assembling the trailer for the rover tripod and mounted the system on top of it. Installed the EasyProbe SN 10237155 in the water canal beside the field that feeds water to the crops. Installed antennas on the tower and tripod so the tripod has internet access without an Ethernet cable.

### 2026-05-08 · Foldable boom system; trailer moved out of the field

- **Note id:** 93
- **Site:** UQAM_4
- **Date visited:** 2026-05-08
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Moved the EasyProbe20 to controller C7 so its different sampling rate stops interfering with the other SDI-12 sensors. Moved the trailer out of the field to the side so the farmer could plant lettuce: from this point the outward radiation variables (PPFD, SW and LW) no longer represent the field until the trailer goes back. Reinstalled all soil sensors in a new position inside the field. Improved the boom system so it can be folded when needed. Cleaned the sensors and station and filled the fluid washer with 2-propanol.

### 2026-05-15 · Installation of water table depth sensor

- **Note id:** 99
- **Site:** UQAM_4
- **Date visited:** 2026-05-15
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Installed a CS456 WTD sensor (SN 70010299). Water was found at 1.85 m depth and the hole goes down to 270 cm, so readings below that value are not valid. Also modified the code slightly so the EasyProbe does not interfere with the other SDI-12 sensors.

### 2026-05-22 · Trailer moved back into the field

- **Note id:** 101
- **Site:** UQAM_4
- **Date visited:** 2026-05-22
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Moved the trailer back into the field after lettuce planting, so the outward radiation variables (SW, LW and PPFD) are meaningful again. Cleaned the station and sensors.

### 2026-06-12 · Cleaning and blocked LI-7200 filter

- **Note id:** 98
- **Site:** UQAM_4
- **Date visited:** 2026-06-12
- **Submitted by:** Chloe Kaplan
- **Type:** Fault / intervention (`issue`)

Cleaned the LI-7700 and added a vertical support pipe plus a new swivel clamp so the boom can be moved easily for field operations. PROBLEM: the LI-7200 filter was blocked; water and compressed air were tried but it never fully unclogged.

### 2026-06-15 · Filter replacement

- **Note id:** 105
- **Site:** UQAM_4
- **Date visited:** 2026-06-15
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

Replaced the flow filter with a 15 µm one, which brought the flow drive down from 100% to 44%. General cleaning of the station.

### 2026-06-30 · Maintenance

- **Note id:** 109
- **Site:** UQAM_4
- **Date visited:** 2026-06-30
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the methane sensor, refilled the alcohol, replaced the desiccant in the sonic anemometer, realigned the sonic to be straight and confirmed the connection for the water multiprobe. Outstanding: the CNF4 needs reconnecting.

### 2026-07-02 · Moving the trailer

- **Note id:** 110
- **Site:** UQAM_4
- **Date visited:** 2026-07-02
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Moved the trailer onto the grass off the fields, reburied the soil sensors, heat-flux plates and SoilVue, and aligned the solar panel to face south.

### 2026-07-07 · Moving the trailer back

- **Note id:** 111
- **Site:** UQAM_4
- **Date visited:** 2026-07-07
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Moved the trailer back into the field and reinstalled the heat-flux plates, SoilVue and soil-moisture probes. Swapped the LI-7550 and LI-7200 for newly calibrated units (AIU-2494, 72H-1205) and cleaned the methane sensor.

### 2026-08-12 · Cleaning

- **Note id:** 124
- **Site:** UQAM_4
- **Date visited:** 2026-08-12
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700, swapped out the USB sticks and refilled the washing unit with alcohol.

### 2026-08-26 · Cleaning

- **Note id:** 129
- **Site:** UQAM_4
- **Date visited:** 2026-08-26
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700, refilled the washer fluid and moved the trailer onto the grass so the field could be harvested.

### 2026-09-17 · Trailer returned to the field; SnowVUE not working

- **Note id:** 133
- **Site:** UQAM_4
- **Date visited:** 2026-09-17
- **Submitted by:** David Trejo
- **Type:** Fault / intervention (`issue`)

PROBLEM: the SnowVUE has stopped working and needs to be swapped on the next visit, with the faulty one taken back to the lab for diagnosis. The flow drive is also over 70 %, so the filter and rain cap will need replacing next time. The trailer was moved back inside the field and all the soil probes reinstalled in it; general cleaning of the tower (lots of spiders), cleaned the methane sensor and filled the washer tank, and swapped the LI-7550 and SmartFlux USB sticks for empty ones.


## UQAM_5 — Saint-François du Lac Natural Marsh (3 notes)

### 2026-07-22 · Power system and tower installation (20–22 July)

- **Note id:** 118
- **Site:** UQAM_5
- **Date visited:** 2026-07-22
- **Submitted by:** Chloe Kaplan
- **Type:** Major work (`major`)

Solar structure: fixed the panel structure to the platform, replaced the previous bolts with longer, more stable ones, connected the panels to the structure, grounded the solar system, connected it to the batteries, added lightning protection and ran the connection to the tower. Tower structure: built the scaffolding, connected the booms, attached the power, multiplexer, logging and electrical boxes, and added lightning protection. Next time: fit the LI-COR and biomet sensors, configure the system and clear the remaining equipment from the field.

### 2026-08-06 · Installation details of UQAM_5

- **Note id:** 121
- **Site:** UQAM_5
- **Date visited:** 2026-08-06
- **Submitted by:** David Trejo
- **Type:** Major work (`major`)

Natural marsh site that floods in spring, with water reaching up to 3 m in extreme events. The system sits on two wooden platforms on certified screw piles 3 m above the ground (one for the solar panels and battery bank, one for the scaffolding and equipment) with power carried over two 70 m 4C 10AWG TECK90 cables. Access can require a boat during flooding and a couple of kilometres of walking in winter. Installed in stages: platforms in autumn 2025 to test them against flooding and freezing, then the solar panels, then the full eddy covariance system on 20–22 July, 4, 6 and 11 August 2026. Data should be considered valid from 2026-08-06 16:00 onwards. Soil: four HFP01 (SN 23111–23114, sensitivities 61.50–62.22) and four CS650 (SN 69255, 69259, 69260, 69261) as horizontal replicas 5 cm below the surface. No vertical profile could be installed (the site was still too flooded to dig) to be retried in the autumn. Instruments: CSAT3B SN 1901 at 4.85 m with north offset 267°; LI-7200 SN 72H-1209 (tube 71.1 cm, flow 18.2); LI-7700 SN TG1-1027. Missing: connect the CNF4 data cables to the logger and the cables to read system voltages.

### 2026-08-11 · Cleaning / finishing installation

- **Note id:** 123
- **Site:** UQAM_5
- **Date visited:** 2026-08-11
- **Submitted by:** Chloe Kaplan
- **Type:** Routine maintenance (`routine`)

Cleaned the LI-7700, added the cable for the CNF4 ventilation unit, added and configured the Phenocam, and brought some equipment back to UQAM: scaffolding and larger items were left in the field closer to the road.

