# ═══════════════════════════════════════════════════════════════
# Solar Prominence Alert System
# Version 1.3 — May 2026
#
# Written by Mark Johnston
# Astronomical Society of the Pacific
#
# Detects large off-limb structures in NASA SDO 304Å imagery
# and sends email alerts when prominences exceed 12% of the
# solar radius.
#
# Images courtesy of NASA/SDO and the AIA science team.
# https://sdo.gsfc.nasa.gov
#
# For questions or feedback contact: markj57@gmail.com
#
# May be freely shared and adapted for non-commercial use
# with attribution.
# ═══════════════════════════════════════════════════════════════

import urllib.request
import smtplib
import time
from email.message import EmailMessage
from PIL import Image
import numpy as np
from scipy import ndimage

# ── USER SETTINGS ─────────────────────────────────────────────
EMAIL_FROM            = "your_gmail_address@gmail.com"
EMAIL_TO              = "your_gmail_address@gmail.com"  # can be same or different
GMAIL_APP_PW          = "xxxx xxxx xxxx xxxx"  # replace with your Gmail App Password

EXPAND_RADIUS_BY      = 1.12   # 12% beyond solar radius
BRIGHT_PERCENTILE     = 99.7   # brightness threshold (off-limb region only)
MIN_BRIGHT_PIXELS     = 400    # minimum total pixels to consider
MIN_CLUSTER_SIZE      = 200    # minimum contiguous pixels to alert
ALERT_COOLDOWN_SECS   = 14400  # 4 hours before re-alerting stable event
CLUSTER_CHANGE_PCT    = 0.40   # re-alert if cluster changes by 40%
CHECK_INTERVAL_SECS   = 600    # check every 10 minutes

SDO_URL  = "https://sdo.gsfc.nasa.gov/assets/img/latest/latest_1024_0304.jpg"
IMG_FILE = "sdo_latest.jpg"
# ──────────────────────────────────────────────────────────────

# Alert state tracking
last_alert_time     = 0
last_cluster_size   = 0

def download_image():
    urllib.request.urlretrieve(SDO_URL, IMG_FILE)

def analyze_image():
    img = Image.open(IMG_FILE).convert("L")
    arr = np.array(img)
    h, w = arr.shape
    cx, cy = w / 2.0, h / 2.0

    threshold = np.percentile(arr, 70)
    disk_pixels = arr > threshold
    ys, xs = np.where(disk_pixels)
    distances = np.sqrt((xs - cx)**2 + (ys - cy)**2)
    solar_radius = np.percentile(distances, 95)

    alert_radius = solar_radius * EXPAND_RADIUS_BY

    yy, xx = np.indices(arr.shape)
    r = np.sqrt((xx - cx)**2 + (yy - cy)**2)

    outside_alert_circle = r > alert_radius
    outside_pixels = arr[outside_alert_circle]
    bright_cutoff = np.percentile(outside_pixels, BRIGHT_PERCENTILE)
    bright_pixels = arr > bright_cutoff
    candidate_pixels = outside_alert_circle & bright_pixels
    count = int(candidate_pixels.sum())

    largest_cluster = 0
    if count >= MIN_BRIGHT_PIXELS:
        labeled, num_clusters = ndimage.label(candidate_pixels)
        if num_clusters > 0:
            cluster_sizes = [int(np.sum(labeled == i)) for i in range(1, num_clusters + 1)]
            largest_cluster = max(cluster_sizes)

    return solar_radius, alert_radius, count, largest_cluster

def save_debug_image(alert_radius):
    img = Image.open(IMG_FILE).convert("L")
    arr = np.array(img)
    h, w = arr.shape
    cx, cy = w / 2.0, h / 2.0
    yy, xx = np.indices(arr.shape)
    r = np.sqrt((xx - cx)**2 + (yy - cy)**2)

    outside_alert_circle = r > alert_radius
    outside_pixels = arr[outside_alert_circle]
    bright_cutoff = np.percentile(outside_pixels, BRIGHT_PERCENTILE)
    bright_pixels = arr > bright_cutoff
    candidate_pixels = outside_alert_circle & bright_pixels

    debug = np.stack([arr, arr, arr], axis=2)
    circle_edge = np.abs(r - alert_radius) < 1.5
    debug[circle_edge] = [255, 255, 0]
    debug[candidate_pixels] = [255, 0, 0]
    debug_path = "debug_detection.png"
    Image.fromarray(debug.astype(np.uint8)).save(debug_path)
    return debug_path

def send_email(solar_radius, alert_radius, count, largest_cluster, reason, debug_path):
    msg = EmailMessage()
    msg["Subject"] = "☀️ Solar Prominence Alert — Large off-limb structure detected"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    body = (
        f"A large off-limb structure has been detected in the latest SDO 304Å image.\n\n"
        f"  Estimated solar radius : {solar_radius:.1f} px\n"
        f"  Alert boundary (112%)  : {alert_radius:.1f} px\n"
        f"  Bright pixels outside  : {count}\n"
        f"  Largest cluster size   : {largest_cluster} px\n"
        f"  Alert reason           : {reason}\n\n"
        f"Image source: {SDO_URL}\n"
        f"Check the attached debug image for a visual.\n"
    )
    msg.set_content(body)

    with open(debug_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="image",
                           subtype="png", filename="prominence_detection.png")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_FROM, GMAIL_APP_PW)
        smtp.send_message(msg)
    print("  → Email sent.")

def run_once():
    global last_alert_time, last_cluster_size

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Downloading SDO image...")
    try:
        download_image()
    except Exception as e:
        print(f"  Download failed: {e}")
        return

    solar_radius, alert_radius, count, largest_cluster = analyze_image()
    print(f"  Solar radius: {solar_radius:.1f} px | Alert radius: {alert_radius:.1f} px | "
          f"Bright pixels outside: {count} | Largest cluster: {largest_cluster}")

    if count >= MIN_BRIGHT_PIXELS and largest_cluster >= MIN_CLUSTER_SIZE:
        now = time.time()
        cooldown_expired = (now - last_alert_time) >= ALERT_COOLDOWN_SECS
        cluster_changed = (last_cluster_size == 0 or
                          abs(largest_cluster - last_cluster_size) /
                          max(last_cluster_size, 1) >= CLUSTER_CHANGE_PCT)

        if cooldown_expired or cluster_changed:
            if cooldown_expired and not cluster_changed:
                reason = "Cooldown expired — stable structure still present"
            elif cluster_changed and last_cluster_size == 0:
                reason = "New detection"
            elif largest_cluster > last_cluster_size:
                reason = f"Cluster grew significantly ({last_cluster_size} → {largest_cluster} px)"
            else:
                reason = f"Cluster changed significantly ({last_cluster_size} → {largest_cluster} px)"

            print(f"  *** ALERT: {reason} ***")
            debug_path = save_debug_image(alert_radius)
            try:
                send_email(solar_radius, alert_radius, count, largest_cluster, reason, debug_path)
                last_alert_time = now
                last_cluster_size = largest_cluster
            except Exception as e:
                print(f"  Email failed: {e}")
        else:
            mins_remaining = int((ALERT_COOLDOWN_SECS - (now - last_alert_time)) / 60)
            print(f"  Structure detected but suppressed — cooldown: {mins_remaining} min remaining, "
                  f"cluster change: {abs(largest_cluster - last_cluster_size) / max(last_cluster_size, 1) * 100:.0f}%")
    else:
        last_cluster_size = 0
        print("  No alert.")

# ── MAIN LOOP ──────────────────────────────────────────────────
if __name__ == "__main__":
    print("Prominence monitor started. Press Ctrl+C to stop.\n")
    while True:
        run_once()
        print(f"  Next check in {CHECK_INTERVAL_SECS // 60} minutes.\n")
        time.sleep(CHECK_INTERVAL_SECS)