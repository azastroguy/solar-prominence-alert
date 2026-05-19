# Solar Prominence Alert System

## What This Does

This Python script monitors the Sun in near real-time and sends you an email alert when a large solar prominence or other off-limb structure is detected extending significantly beyond the solar limb. It does this by automatically downloading the latest image from NASA's Solar Dynamics Observatory (SDO) every 10 minutes, analyzing it, and emailing you when something noteworthy appears.

It was written by Mark Johnston of the Astronomical Society of the Pacific as a companion tool to his Solar Observing Handbook, and is offered freely to the amateur astronomy community.

---

## What It Can and Cannot Detect

**This script watches for:**
- Large eruptive prominences
- Coronal mass ejection (CME) lift-off structures
- Jets, surges, and sprays associated with active regions
- Any bright off-limb plasma structure extending more than 12% beyond the solar radius (~83,500 km above the limb)

**This script cannot detect:**
- Events that rise and fall entirely within a 10-minute window (some jets last only 5-10 minutes)
- Filaments on the disk surface — only off-limb structures are detected
- Flares themselves — flare detection requires different wavelengths and logic
- Events on the far side of the Sun

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

Each time the script runs it performs the following steps:

**1. Download** — The latest 1024×1024 pixel SDO 304Å image is downloaded from NASA's public server.

**2. Find the solar disk edge** — The script estimates the solar radius by identifying bright pixels and measuring their distance from the image center. The 95th percentile of those distances is used as the solar radius estimate, which makes it robust against image artifacts and bright active regions near the limb.

**3. Set the alert boundary** — A circle is drawn at 112% of the estimated solar radius — that is, 12% beyond the limb. Any bright structure detected outside this boundary is a candidate for an alert.

**4. Measure brightness relative to the off-limb region** — Critically, brightness is measured relative to the region outside the alert circle, not the whole image. This prevents the brilliant solar disk from overwhelming the threshold calculation and allows the script to detect prominences that are much dimmer than the disk surface.

**5. Cluster analysis** — The script doesn't simply count bright pixels. It identifies contiguous groups (clusters) of bright pixels using connected-component analysis. A scattered handful of pixels around the entire limb is ignored. Only a concentrated structure — a genuine prominence or eruption — with at least 200 connected pixels triggers an alert.

**6. Smart re-alerting** — Once an alert fires, the script records the cluster size as a baseline. It will not re-alert unless either (a) four hours have passed, or (b) the cluster size changes by more than 40% from baseline — indicating a new or significantly evolved event. This prevents a stable quiescent prominence or polar crown filament from generating dozens of identical alerts over days, while still catching new eruptions from active regions even if a quiescent prominence is already present.

---

## Key Parameters and How to Tune Them

All tunable settings are at the top of the script under USER SETTINGS.

| Parameter | Default | What It Does |
|---|---|---|
| `EXPAND_RADIUS_BY` | 1.12 | Alert boundary — 1.12 means 12% beyond the limb |
| `BRIGHT_PERCENTILE` | 99.7 | How bright a pixel must be relative to the off-limb region |
| `MIN_BRIGHT_PIXELS` | 400 | Minimum total bright pixels outside boundary to consider |
| `MIN_CLUSTER_SIZE` | 200 | Minimum contiguous pixels required to trigger alert |
| `ALERT_COOLDOWN_SECS` | 14400 | Seconds before re-alerting on a stable event (4 hours) |
| `CLUSTER_CHANGE_PCT` | 0.40 | Re-alert if cluster changes by this fraction (40%) |
| `CHECK_INTERVAL_SECS` | 600 | How often to check in seconds (600 = 10 minutes) |

**Getting too many alerts?** Raise `MIN_CLUSTER_SIZE` to 400 or `EXPAND_RADIUS_BY` to 1.15.

**Missing events you read about elsewhere?** Lower `MIN_CLUSTER_SIZE` to 100 or `EXPAND_RADIUS_BY` to 1.08.

**Near solar minimum with a quiet Sun?** Lower `EXPAND_RADIUS_BY` to 1.08 and `MIN_CLUSTER_SIZE` to 150 to catch smaller events.

---

## What to Expect by Solar Cycle Phase

| Solar Cycle Phase | Expected Alert Frequency |
|---|---|
| Solar maximum (active) | Several times per week; possibly daily during active periods |
| Rising/declining phase | Weekly to several times per month |
| Solar minimum (quiet) | Monthly, possibly less |

We are currently in the declining phase of Solar Cycle 25, approaching minimum. Alert frequency will decrease gradually over the next few years.

---

## Alert Email Contents

When a detection occurs you receive an email containing:
- Estimated solar radius in pixels
- Alert boundary distance in pixels
- Total bright pixel count outside the boundary
- Largest contiguous cluster size
- The reason for the alert (new detection, growing structure, cooldown expiry)
- A link to the SDO image source
- An attached diagnostic image showing the yellow alert boundary circle and red pixels marking the detected structure

---

## Requirements and Setup

- A Mac or Windows computer (setup instructions for both platforms are provided separately)
- Python 3.10 or later
- Three Python libraries: Pillow, NumPy, SciPy
- A Gmail account with an App Password configured
- An internet connection

Full setup instructions are included in the companion document. For readers of the Solar Observing Handbook the relevant appendix walks through installation step by step for both Mac and Windows.

---

## Data Credit

All solar imagery used by this script is courtesy of **NASA/SDO and the AIA science team**. SDO is a NASA mission operated by Goddard Space Flight Center. Images are provided free of charge via NASA's public servers at https://sdo.gsfc.nasa.gov.

---

## License and Attribution

This script may be freely shared, used, and adapted for non-commercial purposes with attribution. If you improve it, the author welcomes hearing about it.

**Author:** Mark Johnston  
**Organization:** Astronomical Society of the Pacific  
**Contact:** markj57@gmail.com  
**Version:** 1.3 — May 2026

---

*A companion tool to the Solar Observing Handbook*
