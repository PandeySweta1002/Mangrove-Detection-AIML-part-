# ═══════════════════════════════════════════════════════
# MANGROVE DETECTION + BLUE CARBON CALCULATOR
# Uses your trained YOLOv8 model (best.pt)
# Reads all images from your zip file
# Calculates Blue Carbon using IPCC formula
# ═══════════════════════════════════════════════════════

import zipfile
import os
import json
import pandas as pd
from ultralytics import YOLO
from PIL import Image
import cv2

# ─────────────────────────────────────────────────────
# CONFIGURATION — change these if your file names differ
# ─────────────────────────────────────────────────────
MODEL_PATH    = "best.pt"       # your trained model
ZIP_PATH      = "images.zip"    # your images zip file
OUTPUT_DIR    = "mangrove_results"
EXTRACT_DIR   = os.path.join(OUTPUT_DIR, "images")
ANNOTATED_DIR = os.path.join(OUTPUT_DIR, "annotated")

# ─────────────────────────────────────────────────────
# PIXEL TO METER CONVERSION
# THIS IS THE MOST IMPORTANT SETTING TO CHANGE!
# It depends on how your images were captured:
#
#   Drone at ~50m altitude  → 0.0009  (3cm/pixel GSD)
#   Drone at ~120m altitude → 0.0049  (7cm/pixel GSD)
#   Satellite Sentinel-2    → 100.0   (10m/pixel)
#   Satellite PlanetScope   → 9.0     (3m/pixel)
#
# If unsure, keep 0.09 as a rough placeholder
# ─────────────────────────────────────────────────────
PIXEL_TO_M2 = 0.09

# ─────────────────────────────────────────────────────
# IPCC BLUE CARBON CONSTANTS
# Source: IPCC Wetlands Supplement 2013
# ─────────────────────────────────────────────────────
AGB_FACTOR       = 159.0   # tC/ha — Above-Ground Biomass
ROOT_SHOOT_RATIO = 0.49    # IPCC default for mangroves
BGB_FACTOR       = AGB_FACTOR * ROOT_SHOOT_RATIO  # Below-Ground Biomass
SOC_FACTOR       = 386.0   # tC/ha — Soil Organic Carbon
CO2_EQUIVALENT   = 3.67    # tCO2e per tC (IPCC AR5)
CONF_THRESHOLD   = 0.25    # detection confidence cutoff (0–1)

# ─────────────────────────────────────────────────────
# SETUP OUTPUT FOLDERS
# ─────────────────────────────────────────────────────
os.makedirs(EXTRACT_DIR, exist_ok=True)
os.makedirs(ANNOTATED_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────
# IPCC BLUE CARBON FORMULA
# Total Carbon = AGB + BGB + SOC (per hectare)
# Total CO2e   = Total Carbon × 3.67
# ─────────────────────────────────────────────────────
def calculate_blue_carbon(area_m2):
    area_ha      = area_m2 / 10000
    agb          = area_ha * AGB_FACTOR
    bgb          = area_ha * BGB_FACTOR
    soc          = area_ha * SOC_FACTOR
    total_carbon = agb + bgb + soc
    total_co2e   = total_carbon * CO2_EQUIVALENT
    return {
        "area_ha":         round(area_ha, 6),
        "agb_tC":          round(agb, 4),
        "bgb_tC":          round(bgb, 4),
        "soc_tC":          round(soc, 4),
        "total_carbon_tC": round(total_carbon, 4),
        "total_co2e":      round(total_co2e, 4),
    }

# ─────────────────────────────────────────────────────
# LOAD YOUR YOLO MODEL
# ─────────────────────────────────────────────────────
print("Loading model...")
model = YOLO(MODEL_PATH)
print(f"Model loaded. Classes: {model.names}")

# ─────────────────────────────────────────────────────
# EXTRACT ALL IMAGES FROM ZIP
# ─────────────────────────────────────────────────────
print(f"\nExtracting images from {ZIP_PATH}...")
with zipfile.ZipFile(ZIP_PATH, 'r') as z:
    z.extractall(EXTRACT_DIR)

# Find all image files
image_extensions = ('.jpg', '.jpeg', '.png',
                    '.tif', '.tiff', '.bmp')
image_files = []
for root, dirs, files in os.walk(EXTRACT_DIR):
    for f in files:
        if f.lower().endswith(image_extensions):
            image_files.append(os.path.join(root, f))

print(f"Found {len(image_files)} images to process\n")

if len(image_files) == 0:
    print("ERROR: No images found in the zip file!")
    print("Make sure your zip contains .jpg, .jpeg, .png, or .tif files")
    exit()

# ─────────────────────────────────────────────────────
# PROCESS EACH IMAGE
# ─────────────────────────────────────────────────────
records = []

for idx, img_path in enumerate(image_files):
    img_name = os.path.basename(img_path)
    print(f"Processing [{idx+1}/{len(image_files)}]: {img_name}")

    # Get image size
    img = Image.open(img_path)
    W, H = img.size

    # Run detection
    results = model.predict(
        source=img_path,
        conf=CONF_THRESHOLD,
        save=False,
        verbose=False
    )
    result = results[0]
    boxes  = result.boxes

    detection_count  = len(boxes)
    total_pixel_area = 0
    detections_list  = []

    for box in boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        conf   = float(box.conf[0])
        cls    = int(box.cls[0])
        label  = model.names[cls]
        bw     = x2 - x1
        bh     = y2 - y1
        px_area = bw * bh
        total_pixel_area += px_area
        detections_list.append({
            "class":       label,
            "confidence":  round(conf, 4),
            "bbox":        [round(x1,1), round(y1,1),
                             round(x2,1), round(y2,1)],
            "pixel_area":  round(px_area, 2),
        })

    # Convert pixel area to real-world area
    total_area_m2 = total_pixel_area * PIXEL_TO_M2

    # Calculate blue carbon
    carbon = calculate_blue_carbon(total_area_m2)

    # Save annotated image (with boxes drawn)
    annotated = result.plot()
    out_path  = os.path.join(ANNOTATED_DIR, img_name)
    cv2.imwrite(out_path, annotated)

    # Store result
    records.append({
        "image_name":       img_name,
        "image_width_px":   W,
        "image_height_px":  H,
        "detection_count":  detection_count,
        "total_pixel_area": round(total_pixel_area, 2),
        "total_area_m2":    round(total_area_m2, 4),
        **carbon,
        "detections_json":  json.dumps(detections_list),
    })

    print(f"  ✓ {detection_count} detections | "
          f"{carbon['area_ha']} ha | "
          f"{carbon['total_co2e']} tCO2e")

# ─────────────────────────────────────────────────────
# SAVE RESULTS TO CSV
# ─────────────────────────────────────────────────────
df = pd.DataFrame(records)
csv_path = os.path.join(OUTPUT_DIR, "baseline_data.csv")
df.to_csv(csv_path, index=False)

print(f"\n{'='*50}")
print(f"DONE! Processed {len(records)} images")
print(f"Total detections: {df['detection_count'].sum()}")
print(f"Total area: {df['area_ha'].sum():.4f} ha")
print(f"Total CO2e: {df['total_co2e'].sum():.4f} tCO2e")
print(f"Results saved to: {csv_path}")
print(f"Annotated images: {ANNOTATED_DIR}/")
print(f"{'='*50}")