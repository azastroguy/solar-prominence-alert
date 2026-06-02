# Solar Prominence Alert System

## What This Does

This Python script monitors the Sun in near real time and sends an email alert when a significant off-limb solar prominence or related plasma structure is detected in NASA SDO/AIA 304 Å imagery.

It automatically downloads the latest 1024 × 1024 image from NASA’s Solar Dynamics Observatory every 10 minutes, analyzes the region just beyond the solar limb, identifies bright limb-anchored structures, and emails you when something noteworthy appears.

The script was written by Mark Johnston as a companion tool to *The Solar Observer’s Handbook* and is offered freely to the amateur astronomy community.

Version 1.6 improves detection of low, broad, and tall thin prominences by searching closer to the solar limb, measuring height above the limb, and requiring candidate structures to be limb-anchored. It also reduces false positives from isolated noise, stars, compression artifacts, and the SDO timestamp/text area.

---

## What It Can and Cannot Detect

This script watches for:

- Tall limb-anchored prominences extending well above the solar limb
- Broad low quiescent prominences, walls, curtains, and large off-limb structures
- Compact bright eruptions
- Jets, surges, and sprays associated with active regions
- Other bright off-limb plasma structures visible in SDO/AIA 304 Å imagery

This script cannot reliably detect:

- Events that rise and fall entirely within a 10-minute window
- Filaments on the disk surface — it is designed for off-limb structures
- Flares themselves — flare detection requires different wavelengths and logic
- Events on the far side of the Sun
- Very faint structures below the brightness threshold
- Subtle H-alpha detail visible only through a good solar telescope

---

## Why 304Å and Not H-alpha?

Most amateur solar observers use H-alpha telescopes (656.28nm) which show the cool chromospheric layer where prominences appear as bright structures at the limb or dark filaments on the disk. H-alpha is excellent for visual observing and reveals extraordinary detail in prominence structure.

This script uses NASA's SDO 304Å extreme ultraviolet (EUV) imagery instead, for several important reasons:

**Coverage** — SDO images the entire solar disk continuously, 24 hours a day, from space. No weather interruptions, no day/night cycle, no atmospheric seeing.

**Wavelength sensitivity** — The 304Å channel images plasma at approximately 50,000–80,000 Kelvin, corresponding to the chromosphere and transition region. This is the same temperature regime where prominences are most clearly visible, making it well-suited for prominence detection.

**Availability** — SDO imagery is freely available in near real-time from NASA's servers. No telescope, no clear skies, and no special equipment are required to run this script.

**The tradeoff** — H-alpha shows finer structural detail and is more sensitive to the cool dense cores of prominences. A skilled observer at the eyepiece of a quality H-alpha telescope will see more than this script detects. Think of this script as an always-on automated watchdog, not a replacement for direct solar observation.

---

## How Detection Works

Each time the script runs, it performs the following steps:

1. **Download** — The latest 1024 × 1024 pixel SDO/AIA 304 Å image is downloaded from NASA's public server.

2. **Estimate the solar radius** — The script estimates the solar disk radius from the image itself using a brightness threshold and radial distance from the image center. This allows the program to adapt to the downloaded image rather than relying on a hard-coded disk size.

3. **Search close to the limb** — Version 1.6 begins searching just outside the visible solar limb, starting at 101.5% of the estimated solar radius and extending outward to 135% of the solar radius. This allows it to detect broad low prominences as well as tall thin ones.

4. **Mask the SDO text area** — The public SDO JPEG includes timestamp and channel text near the lower-left corner. The script masks this region so it is not mistaken for a bright off-limb structure.

5. **Measure brightness in the off-limb search region** — Brightness is measured within the off-limb search annulus, not across the whole image. This prevents the bright solar disk from overwhelming the threshold calculation and helps the script identify prominence material against the darker background.

6. **Identify bright candidate pixels** — Pixels above the selected brightness percentile are marked as possible off-limb prominence material.

7. **Group pixels into clusters** — The script groups connected bright pixels into clusters using connected-component analysis. This helps separate real structures from scattered noise.

8. **Require limb anchoring** — A candidate cluster must include detected material close to the solar limb. This rejects isolated far-off artifacts, stars, compression artifacts, and other disconnected bright pixels.

9. **Measure size and height** — For each qualifying cluster, the script measures cluster size, minimum height, maximum height, mean height, and radial span above the limb.

10. **Trigger alerts by category** — Alerts can be triggered by a tall limb-anchored prominence, a broad lower structure, or a compact bright eruption.

11. **Smart re-alerting** — Once an alert fires, the script suppresses repeat alerts unless four hours have passed or the structure changes significantly in size or height. This prevents a stable prominence from generating repeated identical alerts while still allowing the script to notice meaningful evolution.

---

## Key Parameters and How to Tune Them

All tunable settings are near the top of the script under USER SETTINGS and DETECTION SETTINGS.

| Parameter | Default | What It Does |
|---|---:|---|
| `CHECK_INTERVAL_SECS` | `600` | Checks every 10 minutes |
| `ALERT_COOLDOWN_SECS` | `14400` | Four hours before re-alerting on a stable event |
| `LIMB_START_RADIUS` | `1.015` | Begins searching 1.5% beyond the estimated solar radius |
| `MAX_SEARCH_RADIUS` | `1.35` | Searches out to 35% above the solar radius |
| `BRIGHT_PERCENTILE` | `99.3` | Brightness threshold within the off-limb search region |
| `MIN_CLUSTER_SIZE` | `25` | Minimum connected pixels for a cluster to be considered |
| `ANCHORED_BASE_MAX_HEIGHT_PCT` | `0.07` | Cluster must begin within 7% of the limb |
| `TALL_HEIGHT_ALERT_PCT` | `0.10` | Tall-prominence height threshold |
| `TALL_MIN_CLUSTER_SIZE` | `25` | Minimum cluster size for a tall-prominence alert |
| `BROAD_AREA_ALERT_PIXELS` | `3000` | Large-area threshold for broad structures |
| `BROAD_MIN_HEIGHT_PCT` | `0.07` | Minimum height for broad-structure alerts |
| `COMPACT_CLUSTER_SIZE` | `600` | Cluster size threshold for compact bright structures |
| `COMPACT_MIN_HEIGHT_PCT` | `0.08` | Minimum height for compact bright-eruption alerts |
| `CLUSTER_CHANGE_PCT` | `0.40` | Re-alert if cluster size changes by 40% |
| `HEIGHT_CHANGE_PCT` | `0.30` | Re-alert if detected height changes by 30% |

### Tuning suggestions

Getting too many false alerts?

- Raise `BRIGHT_PERCENTILE` slightly, for example from `99.3` to `99.5`
- Raise `MIN_CLUSTER_SIZE`
- Raise `COMPACT_CLUSTER_SIZE`
- Raise `BROAD_AREA_ALERT_PIXELS`
- Raise `TALL_HEIGHT_ALERT_PCT` if tall but insignificant wisps are triggering alerts

Missing tall thin prominences?

- Lower `TALL_HEIGHT_ALERT_PCT`
- Lower `TALL_MIN_CLUSTER_SIZE`
- Lower `BRIGHT_PERCENTILE` slightly

Missing broad low prominences?

- Lower `BROAD_AREA_ALERT_PIXELS`
- Lower `BROAD_MIN_HEIGHT_PCT`
- Keep `LIMB_START_RADIUS` close to the limb

Getting alerts from detached artifacts or isolated bright pixels?

- Lower `ANCHORED_BASE_MAX_HEIGHT_PCT` slightly to require structures to be closer to the limb
- Raise `MIN_CLUSTER_SIZE`
- Raise `BRIGHT_PERCENTILE`
---

## What to Expect by Solar Cycle Phase

## What to Expect by Solar Cycle Phase

Alert frequency will vary with the solar cycle, active-region activity, and the script sensitivity settings.

| Solar Cycle Phase | Expected Alert Frequency |
|---|---|
| Solar maximum or highly active periods | Several times per week; possibly daily during active periods |
| Declining or rising phase | Weekly to several times per month |
| Solar minimum or very quiet periods | Monthly, possibly less |

Solar Cycle 25 reached its maximum period in 2024–2025 and is now expected to trend gradually downward toward the next minimum later in the decade. That does not mean the Sun will become quiet immediately. Large active regions, eruptive prominences, sprays, surges, and impressive limb events can still occur during the declining phase.

Because this script is most sensitive to bright, limb-anchored off-limb structures in SDO/AIA 304 Å imagery, alert frequency may vary substantially from week to week.
---

## Alert Email Contents

When a detection occurs, you receive an email containing:

- Estimated solar radius in pixels
- Search start distance and outer search boundary
- Brightness cutoff percentile and brightness cutoff value
- Total bright off-limb pixel count
- Largest cluster size
- Largest cluster height above the limb
- Tallest cluster size
- Maximum detected height above the limb
- The reason for the alert
- A link to the source SDO/AIA 304 Å image
- An attached diagnostic image showing the detected structure

The diagnostic image uses the following color key:

- Yellow circle = estimated solar limb
- Cyan circle = start of the off-limb search region
- Blue circle = outer search boundary
- Red pixels = candidate bright off-limb pixels
- Green pixels = tallest qualifying limb-anchored cluster

---

## Requirements and Setup

- A Mac computer
- Python 3.10 or later
- Three Python libraries: Pillow, NumPy, SciPy
- A Gmail account with an App Password configured
- An internet connection

Important: do not upload your Gmail app password to GitHub. The public version of the script should leave the password field as a placeholder. Enter your private Gmail app password only in your local copy.

This script is offered as a companion resource for readers of *The Solar Observer’s Handbook*. The book describes the purpose and general concept of the alert system, but the current GitHub repository is the place to find the actual code and current usage notes.

---

## Data Credit

All solar imagery used by this script is courtesy of **NASA/SDO and the AIA science team**. SDO is a NASA mission operated by Goddard Space Flight Center. Images are provided free of charge via NASA's public servers at https://sdo.gsfc.nasa.gov.

---

## License and Attribution

This script may be freely shared, used, and adapted for non-commercial purposes with attribution. If you improve it, the author welcomes hearing about it.

**Author:** Mark Johnston  
**Online:** @azastroguy  
**Contact:** markj57@gmail.com  
**Version:** 1.6 — June 2026

---

*A companion tool to the Solar Observing Handbook*
