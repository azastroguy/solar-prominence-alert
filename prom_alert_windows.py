# ═══════════════════════════════════════════════════════════════
# Solar Prominence Alert System
# Version 1.6 Windows-compatible test version — June 2026
#
# Written by Mark Johnston
#
# Detects significant off-limb structures in NASA SDO/AIA 304 Å imagery
# and sends email alerts when prominences are tall, broad, or compact/bright.
#
# Images courtesy of NASA/SDO and the AIA science team.
# https://sdo.gsfc.nasa.gov
# ═══════════════════════════════════════════════════════════════

import argparse
import smtplib
import time
import urllib.request
from email.message import EmailMessage
from pathlib import Path

from PIL import Image
import numpy as np
from scipy import ndimage


# ── USER SETTINGS ─────────────────────────────────────────────

# Email address used to send the alert.
# For Gmail, this should usually be your Gmail address.
EMAIL_FROM = "YOUR_GMAIL_ADDRESS_HERE"

# Email address that receives the alert.
# This can be the same as EMAIL_FROM or a different address.
EMAIL_TO = "ALERT_RECIPIENT_EMAIL_HERE"


# Gmail App Password.
# Do not use your normal Gmail password.
# Do not upload your real app password to GitHub.
GMAIL_APP_PW = "PASTE_YOUR_GMAIL_APP_PASSWORD_HERE"

SDO_URL = "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0304.jpg"

CHECK_INTERVAL_SECS = 600       # Check every 10 minutes
ALERT_COOLDOWN_SECS = 14400     # 4 hours before re-alerting stable event


# ── WINDOWS-SAFE FILE LOCATIONS ────────────────────────────────
# These files will be saved in the same folder as this script.

BASE_DIR = Path(__file__).resolve().parent

IMG_FILE   = BASE_DIR / "sdo_latest.jpg"
STATE_FILE = BASE_DIR / "prom_alert_state.txt"
DEBUG_FILE = BASE_DIR / "debug_detection.png"


# ── DETECTION SETTINGS ────────────────────────────────────────

LIMB_START_RADIUS = 1.015
MAX_SEARCH_RADIUS = 1.35

BRIGHT_PERCENTILE = 99.3

MIN_CLUSTER_SIZE = 25

ANCHORED_BASE_MAX_HEIGHT_PCT = 0.07

TALL_HEIGHT_ALERT_PCT = 0.10
TALL_MIN_CLUSTER_SIZE = 25

BROAD_AREA_ALERT_PIXELS = 3000
BROAD_MIN_HEIGHT_PCT = 0.07

COMPACT_CLUSTER_SIZE = 600
COMPACT_MIN_HEIGHT_PCT = 0.08

CLUSTER_CHANGE_PCT = 0.40
HEIGHT_CHANGE_PCT  = 0.30


# ── STATE MANAGEMENT ──────────────────────────────────────────

def load_state():
    """
    Load previous alert state from disk.

    Stored values:
        last_alert_time
        last_cluster_size
        last_max_height_pct
    """
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            parts = f.read().strip().split(",")

        last_alert_time = float(parts[0])
        last_cluster_size = int(parts[1])

        if len(parts) >= 3:
            last_max_height_pct = float(parts[2])
        else:
            last_max_height_pct = 0.0

        return last_alert_time, last_cluster_size, last_max_height_pct

    except Exception:
        return 0.0, 0, 0.0


def save_state(last_alert_time, last_cluster_size, last_max_height_pct):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(f"{last_alert_time},{last_cluster_size},{last_max_height_pct}")


last_alert_time, last_cluster_size, last_max_height_pct = load_state()


# ── IMAGE DOWNLOAD ────────────────────────────────────────────

def download_image():
    urllib.request.urlretrieve(SDO_URL, IMG_FILE)


# ── SOLAR RADIUS ESTIMATION ───────────────────────────────────

def estimate_solar_radius(arr):
    """
    Estimate the solar disk radius from the image itself.
    """
    h, w = arr.shape
    cx, cy = w / 2.0, h / 2.0

    threshold = np.percentile(arr, 55)

    disk_pixels = arr > threshold
    disk_pixels = ndimage.binary_fill_holes(disk_pixels)

    ys, xs = np.where(disk_pixels)

    if len(xs) < 1000:
        return min(h, w) * 0.45

    distances = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)

    solar_radius = np.percentile(distances, 95)

    return solar_radius


# ── IMAGE ANALYSIS ────────────────────────────────────────────

def analyze_image():
    """
    Analyze latest SDO/AIA 304 image for off-limb prominence structures.
    """
    img = Image.open(IMG_FILE).convert("L")
    arr = np.array(img)

    h, w = arr.shape
    cx, cy = w / 2.0, h / 2.0

    yy, xx = np.indices(arr.shape)
    r = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)

    solar_radius = estimate_solar_radius(arr)

    limb_start = solar_radius * LIMB_START_RADIUS
    max_search = solar_radius * MAX_SEARCH_RADIUS

    search_annulus = (r > limb_start) & (r < max_search)

    # Mask out the lower-left SDO annotation/date text area.
    text_mask = np.zeros_like(search_annulus, dtype=bool)
    text_mask[int(h * 0.88):h, 0:int(w * 0.70)] = True

    search_annulus = search_annulus & (~text_mask)

    annulus_pixels = arr[search_annulus]

    if annulus_pixels.size == 0:
        bright_cutoff = 255
    else:
        bright_cutoff = np.percentile(annulus_pixels, BRIGHT_PERCENTILE)

    candidate_pixels = search_annulus & (arr > bright_cutoff)

    structure = np.ones((3, 3), dtype=int)
    labeled, num_clusters = ndimage.label(candidate_pixels, structure=structure)

    total_bright_pixels = int(candidate_pixels.sum())

    largest_cluster_size = 0
    largest_cluster_height_pct = 0.0

    tallest_cluster_size = 0
    max_height_pct = 0.0

    qualifying_clusters = []

    for i in range(1, num_clusters + 1):
        cluster = labeled == i
        cluster_size = int(cluster.sum())

        if cluster_size < MIN_CLUSTER_SIZE:
            continue

        cluster_r = r[cluster]

        cluster_max_height_pct = float(cluster_r.max() / solar_radius - 1.0)
        cluster_min_height_pct = float(cluster_r.min() / solar_radius - 1.0)
        cluster_mean_height_pct = float(cluster_r.mean() / solar_radius - 1.0)
        cluster_radial_span_pct = cluster_max_height_pct - cluster_min_height_pct

        anchored_to_limb = cluster_min_height_pct <= ANCHORED_BASE_MAX_HEIGHT_PCT

        if not anchored_to_limb:
            continue

        qualifying_clusters.append({
            "label": i,
            "size": cluster_size,
            "max_height_pct": cluster_max_height_pct,
            "min_height_pct": cluster_min_height_pct,
            "mean_height_pct": cluster_mean_height_pct,
            "radial_span_pct": cluster_radial_span_pct
        })

        if cluster_size > largest_cluster_size:
            largest_cluster_size = cluster_size
            largest_cluster_height_pct = cluster_max_height_pct

        if cluster_max_height_pct > max_height_pct:
            max_height_pct = cluster_max_height_pct
            tallest_cluster_size = cluster_size

    tall_alert = (
        max_height_pct >= TALL_HEIGHT_ALERT_PCT and
        tallest_cluster_size >= TALL_MIN_CLUSTER_SIZE
    )

    broad_alert = (
        largest_cluster_size >= BROAD_AREA_ALERT_PIXELS and
        largest_cluster_height_pct >= BROAD_MIN_HEIGHT_PCT
    )

    compact_alert = (
        largest_cluster_size >= COMPACT_CLUSTER_SIZE and
        largest_cluster_height_pct >= COMPACT_MIN_HEIGHT_PCT
    )

    should_alert = tall_alert or broad_alert or compact_alert

    alert_reasons = []

    if tall_alert:
        alert_reasons.append(
            f"Tall limb-anchored prominence detected: "
            f"height {max_height_pct * 100:.1f}% above limb, "
            f"cluster {tallest_cluster_size} px"
        )

    if broad_alert:
        alert_reasons.append(
            f"Broad limb-anchored off-limb structure detected: "
            f"largest cluster {largest_cluster_size} px, "
            f"height {largest_cluster_height_pct * 100:.1f}% above limb"
        )

    if compact_alert:
        alert_reasons.append(
            f"Compact bright limb-anchored off-limb structure detected: "
            f"largest cluster {largest_cluster_size} px, "
            f"height {largest_cluster_height_pct * 100:.1f}% above limb"
        )

    if not alert_reasons:
        alert_reasons.append("No qualifying limb-anchored off-limb structure")

    return {
        "arr": arr,
        "r": r,
        "solar_radius": solar_radius,
        "limb_start": limb_start,
        "max_search": max_search,
        "bright_cutoff": bright_cutoff,
        "candidate_pixels": candidate_pixels,
        "labeled": labeled,
        "num_clusters": num_clusters,
        "total_bright_pixels": total_bright_pixels,
        "largest_cluster_size": largest_cluster_size,
        "largest_cluster_height_pct": largest_cluster_height_pct,
        "tallest_cluster_size": tallest_cluster_size,
        "max_height_pct": max_height_pct,
        "qualifying_clusters": qualifying_clusters,
        "tall_alert": tall_alert,
        "broad_alert": broad_alert,
        "compact_alert": compact_alert,
        "should_alert": should_alert,
        "alert_reasons": alert_reasons
    }


# ── DEBUG IMAGE ───────────────────────────────────────────────

def save_debug_image(result):
    """
    Save annotated debug image.

    Yellow circle = estimated solar limb
    Cyan circle   = start of off-limb search region
    Blue circle   = outer search boundary
    Red pixels    = candidate bright off-limb pixels
    Green pixels  = tallest qualifying limb-anchored cluster, if present
    """
    arr = result["arr"]
    r = result["r"]

    solar_radius = result["solar_radius"]
    limb_start = result["limb_start"]
    max_search = result["max_search"]

    candidate_pixels = result["candidate_pixels"]
    labeled = result["labeled"]
    qualifying_clusters = result["qualifying_clusters"]

    debug = np.stack([arr, arr, arr], axis=2).astype(np.uint8)

    solar_limb_edge = np.abs(r - solar_radius) < 1.5
    debug[solar_limb_edge] = [255, 255, 0]

    limb_start_edge = np.abs(r - limb_start) < 1.5
    debug[limb_start_edge] = [0, 255, 255]

    max_search_edge = np.abs(r - max_search) < 1.5
    debug[max_search_edge] = [0, 128, 255]

    debug[candidate_pixels] = [255, 0, 0]

    if qualifying_clusters:
        tallest = max(qualifying_clusters, key=lambda c: c["max_height_pct"])
        tallest_mask = labeled == tallest["label"]
        debug[tallest_mask] = [0, 255, 0]

    Image.fromarray(debug).save(DEBUG_FILE)

    return DEBUG_FILE


# ── EMAIL ALERT ───────────────────────────────────────────────

def send_email(result, reason, debug_path):
    msg = EmailMessage()
    msg["Subject"] = "Solar Prominence Alert - Off-limb structure detected"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO

    body = (
        "A significant limb-anchored off-limb structure has been detected "
        "in the latest SDO/AIA 304 Angstrom image.\n\n"
        f"Estimated solar radius       : {result['solar_radius']:.1f} px\n"
        f"Search starts at             : {LIMB_START_RADIUS * 100:.1f}% of solar radius\n"
        f"Search extends to            : {MAX_SEARCH_RADIUS * 100:.1f}% of solar radius\n"
        f"Brightness cutoff percentile : {BRIGHT_PERCENTILE:.1f}\n"
        f"Brightness cutoff value      : {result['bright_cutoff']:.1f}\n\n"
        f"Total bright off-limb pixels : {result['total_bright_pixels']}\n"
        f"Largest cluster size         : {result['largest_cluster_size']} px\n"
        f"Largest cluster height       : {result['largest_cluster_height_pct'] * 100:.1f}% above limb\n"
        f"Tallest cluster size         : {result['tallest_cluster_size']} px\n"
        f"Maximum detected height      : {result['max_height_pct'] * 100:.1f}% above limb\n\n"
        f"Alert reason:\n{reason}\n\n"
        f"Image source:\n{SDO_URL}\n\n"
        "Debug image key:\n"
        "  Yellow circle = estimated solar limb\n"
        "  Cyan circle   = start of off-limb search region\n"
        "  Blue circle   = outer search boundary\n"
        "  Red pixels    = candidate off-limb bright pixels\n"
        "  Green pixels  = tallest qualifying limb-anchored cluster\n"
    )

    msg.set_content(body)

    with open(debug_path, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="image",
            subtype="png",
            filename="prominence_detection.png"
        )

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, GMAIL_APP_PW)
        smtp.send_message(msg)

    print("  -> Email sent.")


# ── MAIN CHECK ────────────────────────────────────────────────

def run_once():
    global last_alert_time, last_cluster_size, last_max_height_pct

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Downloading SDO image...")

    try:
        download_image()
    except Exception as e:
        print(f"  Download failed: {e}")
        return

    try:
        result = analyze_image()
    except Exception as e:
        print(f"  Analysis failed: {e}")
        return

    print(
        f"  Solar radius: {result['solar_radius']:.1f} px | "
        f"Bright pixels: {result['total_bright_pixels']} | "
        f"Largest cluster: {result['largest_cluster_size']} px | "
        f"Max height: {result['max_height_pct'] * 100:.1f}%"
    )

    if result["should_alert"]:
        now = time.time()

        cooldown_expired = (now - last_alert_time) >= ALERT_COOLDOWN_SECS

        size_change = (
            abs(result["largest_cluster_size"] - last_cluster_size) /
            max(last_cluster_size, 1)
        )

        height_change = (
            abs(result["max_height_pct"] - last_max_height_pct) /
            max(last_max_height_pct, 0.001)
        )

        cluster_changed = (
            last_cluster_size == 0 or
            size_change >= CLUSTER_CHANGE_PCT or
            height_change >= HEIGHT_CHANGE_PCT
        )

        if cooldown_expired or cluster_changed:
            base_reason = "; ".join(result["alert_reasons"])

            if last_cluster_size == 0:
                reason = f"New detection - {base_reason}"

            elif cooldown_expired and not cluster_changed:
                reason = f"Cooldown expired - structure still present - {base_reason}"

            elif result["largest_cluster_size"] > last_cluster_size:
                reason = (
                    f"Cluster grew significantly "
                    f"({last_cluster_size} -> {result['largest_cluster_size']} px) - "
                    f"{base_reason}"
                )

            elif result["max_height_pct"] > last_max_height_pct:
                reason = (
                    f"Detected height increased significantly "
                    f"({last_max_height_pct * 100:.1f}% -> "
                    f"{result['max_height_pct'] * 100:.1f}%) - "
                    f"{base_reason}"
                )

            else:
                reason = f"Structure changed significantly - {base_reason}"

            print(f"  *** ALERT: {reason} ***")

            debug_path = save_debug_image(result)

            try:
                send_email(result, reason, debug_path)

                last_alert_time = now
                last_cluster_size = result["largest_cluster_size"]
                last_max_height_pct = result["max_height_pct"]

                save_state(
                    last_alert_time,
                    last_cluster_size,
                    last_max_height_pct
                )

            except Exception as e:
                print(f"  Email failed: {e}")

        else:
            mins_remaining = int(
                (ALERT_COOLDOWN_SECS - (now - last_alert_time)) / 60
            )

            print(
                f"  Structure detected but suppressed - "
                f"cooldown: {mins_remaining} min remaining | "
                f"size change: {size_change * 100:.0f}% | "
                f"height change: {height_change * 100:.0f}%"
            )

    else:
        last_cluster_size = 0
        last_max_height_pct = 0.0

        save_state(
            last_alert_time,
            last_cluster_size,
            last_max_height_pct
        )

        print("  No alert.")


# ── MAIN LOOP ─────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solar Prominence Alert System")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one check and exit. Recommended for Windows Task Scheduler."
    )
    parser.add_argument(
        "--test-email",
        action="store_true",
        help="Send a test email and exit."
    )
    args = parser.parse_args()

    if args.test_email:
        msg = EmailMessage()
        msg["Subject"] = "Solar Prominence Alert - Test Email"
        msg["From"] = EMAIL_FROM
        msg["To"] = EMAIL_TO
        msg.set_content(
            "This is a test email from the Windows version of the Solar Prominence Alert System."
        )

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(EMAIL_FROM, GMAIL_APP_PW)
                smtp.send_message(msg)

            print("Test email sent successfully.")

        except Exception as e:
            print(f"Test email failed: {e}")

    elif args.once:
        print("Prominence monitor test run started.\n")
        run_once()
        print("\nTest run complete.")

    else:
        print("Prominence monitor started. Press Ctrl+C to stop.\n")

        while True:
            run_once()
            print(f"  Next check in {CHECK_INTERVAL_SECS // 60} minutes.\n")
            time.sleep(CHECK_INTERVAL_SECS)