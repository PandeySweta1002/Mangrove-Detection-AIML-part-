# ═══════════════════════════════════════════════════════
# BASELINE REPORT GENERATOR
# Reads baseline_data.csv and creates a formatted
# Excel report with 4 sheets
# Run AFTER detect_mangroves.py
# ═══════════════════════════════════════════════════════

import pandas as pd
from openpyxl import load_workbook
from openpyxl.styles import (Font, PatternFill, Alignment,
                              Border, Side)
from openpyxl.utils import get_column_letter
from openpyxl.chart import BarChart, Reference
import os

# ─────────────────────────────────────────────────────
# LOAD DETECTION DATA
# ─────────────────────────────────────────────────────
CSV_PATH    = "mangrove_results/baseline_data.csv"
REPORT_PATH = "mangrove_results/BlueCarbon_Baseline_Report.xlsx"

print("Loading detection data...")
df = pd.read_csv(CSV_PATH)
print(f"Loaded {len(df)} image records")

# ─────────────────────────────────────────────────────
# STYLE HELPERS
# ─────────────────────────────────────────────────────
def make_header_style():
    return {
        "font": Font(bold=True, color="FFFFFF", size=11),
        "fill": PatternFill("solid", fgColor="1B5E20"),
        "align": Alignment(horizontal="center", vertical="center",
                           wrap_text=True),
    }

def apply_header(ws, row_num, max_col):
    style = make_header_style()
    for col in range(1, max_col + 1):
        cell = ws.cell(row=row_num, column=col)
        cell.font  = style["font"]
        cell.fill  = style["fill"]
        cell.alignment = style["align"]

def auto_width(ws):
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            try:
                max_len = max(max_len, len(str(cell.value)))
            except:
                pass
        ws.column_dimensions[col_letter].width = min(max_len + 4, 40)

# ─────────────────────────────────────────────────────
# BUILD EXCEL REPORT
# ─────────────────────────────────────────────────────
with pd.ExcelWriter(REPORT_PATH, engine="openpyxl") as writer:

    # ── SHEET 1: SUMMARY ──────────────────────────────
    summary = {
        "Metric": [
            "Report Title",
            "IPCC Standard",
            "──────────────────────────────",
            "Total Images Processed",
            "Total Mangrove Detections",
            "Total Detected Area (m²)",
            "Total Detected Area (hectares)",
            "──────────────────────────────",
            "Total Above-Ground Biomass (tC)",
            "Total Below-Ground Biomass (tC)",
            "Total Soil Organic Carbon (tC)",
            "Total Carbon Stock (tC)",
            "Total CO₂ Equivalent (tCO₂e)",
        ],
        "Value": [
            "Blue Carbon Baseline Report",
            "IPCC Wetlands Supplement 2013",
            "",
            len(df),
            int(df["detection_count"].sum()),
            round(df["total_area_m2"].sum(), 4),
            round(df["area_ha"].sum(), 6),
            "",
            round(df["agb_tC"].sum(), 4),
            round(df["bgb_tC"].sum(), 4),
            round(df["soc_tC"].sum(), 4),
            round(df["total_carbon_tC"].sum(), 4),
            round(df["total_co2e"].sum(), 4),
        ]
    }
    pd.DataFrame(summary).to_excel(
        writer, sheet_name="Summary", index=False)

    # ── SHEET 2: PER-IMAGE RESULTS ────────────────────
    cols = [
        "image_name", "detection_count", "total_area_m2",
        "area_ha", "agb_tC", "bgb_tC", "soc_tC",
        "total_carbon_tC", "total_co2e"
    ]
    df[cols].to_excel(
        writer, sheet_name="Per-Image Results", index=False)

    # ── SHEET 3: IPCC METHODOLOGY ─────────────────────
    method = {
        "Parameter": [
            "Above-Ground Biomass (AGB)",
            "Below-Ground Biomass (BGB)",
            "Root-to-Shoot Ratio",
            "Soil Organic Carbon (SOC)",
            "CO₂ Conversion Factor",
            "Carbon Formula",
            "CO₂e Formula",
        ],
        "Value Used": [
            "159.0 tC/ha",
            "77.9 tC/ha (AGB × 0.49)",
            "0.49",
            "386.0 tC/ha",
            "3.67 tCO₂e per tC",
            "Total C = (AGB + BGB + SOC) × Area_ha",
            "CO₂e = Total_C × 3.67",
        ],
        "IPCC Source": [
            "Wetlands Supplement 2013, Table 4.2",
            "Wetlands Supplement 2013 (AGB × RSR)",
            "Wetlands Supplement 2013",
            "Wetlands Supplement 2013, Table 4.2",
            "IPCC AR5",
            "IPCC Wetlands Supplement 2013",
            "IPCC AR5",
        ]
    }
    pd.DataFrame(method).to_excel(
        writer, sheet_name="IPCC Methodology", index=False)

    # ── SHEET 4: FULL RAW DATA ────────────────────────
    df.to_excel(writer, sheet_name="Raw Data", index=False)

# ─────────────────────────────────────────────────────
# FORMAT THE EXCEL FILE
# ─────────────────────────────────────────────────────
wb = load_workbook(REPORT_PATH)

for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    apply_header(ws, 1, ws.max_column)
    auto_width(ws)
    ws.freeze_panes = "A2"

    # Add alternating row colors
    light_fill = PatternFill("solid", fgColor="F1F8E9")
    for row in ws.iter_rows(min_row=2):
        if row[0].row % 2 == 0:
            for cell in row:
                cell.fill = light_fill

wb.save(REPORT_PATH)

print(f"\n{'='*50}")
print("✅ BASELINE REPORT GENERATED!")
print(f"📄 Report: {REPORT_PATH}")
print("Sheets included:")
print("  1. Summary         — totals across all images")
print("  2. Per-Image Results— one row per image")
print("  3. IPCC Methodology — formula reference")
print("  4. Raw Data        — complete export")
print(f"{'='*50}")