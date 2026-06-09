"""
STEP 1: Extract & Clean Energy Data
-------------------------------------------
Reads the two Hamilton College spreadsheets and produces a clean
CSV for each: one with per-building annual energy data, one with
campus-wide totals per year.

Input files:
  - files/Hamilton College Electric & Gas Meter Log.xls
  - files/Sq Foot Hamilton College 2023.xlsx

Output files (saved to /output/):
  - buildings_energy.csv   : one row per building per year
  - campus_totals.csv      : one row per year (campus-wide)
  - buildings_2023.csv     : snapshot of 2023 data with sq footage merged in

Run:
  python step1_extract_data.py

"""

import pandas as pd
import numpy as np
import os

# File paths
METER_FILE  = "files/Hamilton College Electric & Gas Meter Log.xls"
SQ_FT_FILE  = "files/Sq Foot Hamilton College 2023.xlsx"
OUTPUT_DIR  = "output"

os.makedirs(OUTPUT_DIR, exist_ok=True)


# Parse meter log

def extract_one_year(df):
    """
    Scans every row and returns a dict:
      { building_name: {"kwh": float, "gas_cuft": float} }
    """
    results = {}
    current_building = None

    for i in range(len(df)):
        row   = df.iloc[i]
        col0  = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        col1  = str(row.iloc[1]).strip().upper() if pd.notna(row.iloc[1]) else ""

        # Electricity / energy row
        if col0 and col0 not in ["NAN", ""] and col1 in ["KWH", "MWH", "MW"]:
            current_building = col0

            monthly_values = []
            for col_idx in range(2, min(14, len(df.columns))):
                try:
                    monthly_values.append(float(row.iloc[col_idx]))
                except (ValueError, TypeError):
                    monthly_values.append(0.0)

            annual_kwh = sum(monthly_values)
            results[current_building] = {
                "kwh":      annual_kwh if annual_kwh > 0 else None,
                "gas_cuft": None,
            }

        # Gas row 
        elif "GAS" in col0.upper() and "CU.FT" in col0.upper() and current_building:
            monthly_gas = []
            for col_idx in range(2, min(14, len(df.columns))):
                try:
                    monthly_gas.append(float(row.iloc[col_idx]))
                except (ValueError, TypeError):
                    monthly_gas.append(0.0)

            total_gas = sum(monthly_gas)
            if total_gas > 0 and current_building in results:
                results[current_building]["gas_cuft"] = total_gas

    return results


def load_meter_log(filepath):
    """
    Reads every sheet (one per year) from the meter log.
    Returns a nested dict: { year (int): { building: {kwh, gas_cuft} } }
    """
    print(f"Reading meter log: {filepath}")
    all_sheets = pd.read_excel(filepath, engine="xlrd", sheet_name=None)

    year_data = {}
    for sheet_name, df in all_sheets.items():
        try:
            year = int(sheet_name)
            year_data[year] = extract_one_year(df)
            print(f"  Parsed year {year}: {len(year_data[year])} buildings")
        except ValueError:
            print(f"  Skipping non-year sheet: '{sheet_name}'")

    return year_data


# Parse square footage 

def load_sq_footage(filepath):
    """
    Reads the square footage file.
    Returns a dict: { building_name: {sqft, fuel, use, year_built} }
    """
    print(f"\nReading square footage file: {filepath}")
    df = pd.read_excel(filepath)

    # Rename the column with trailing space if present
    df.columns = [c.strip() for c in df.columns]

    sq_dict = {}
    for _, row in df.iterrows():
        name = str(row.get("Building Name", "")).strip()
        if not name or name.lower() == "nan":
            continue

        try:
            sqft = float(row.get("Gross Area sq. ft.", None))
        except (ValueError, TypeError):
            sqft = None

        fuel      = str(row.get("Heating Fuel", "")).strip() or "Unknown"
        use       = str(row.get("Use",          "")).strip() or "Unknown"
        year_raw  = row.get("Year Built", None)
        year_built = int(year_raw) if pd.notna(year_raw) else None

        sq_dict[name] = {
            "sqft":       sqft,
            "fuel":       fuel,
            "use":        use,
            "year_built": year_built,
        }

    print(f"  Found {len(sq_dict)} buildings in sq footage file")
    return sq_dict



# Long format


def build_buildings_table(year_data):
    """
    Converts the nested year_data dict into a flat DataFrame with columns:
      year, building, kwh, gas_cuft
    """
    rows = []
    for year, buildings in year_data.items():
        for building, vals in buildings.items():
            rows.append({
                "year":     year,
                "building": building,
                "kwh":      vals.get("kwh")      or 0.0,
                "gas_cuft": vals.get("gas_cuft") or 0.0,
            })

    df = pd.DataFrame(rows)
    df = df.sort_values(["building", "year"]).reset_index(drop=True)
    return df



# Campus-wide annual totals

def build_campus_totals(buildings_df):
    """
    Aggregates all buildings into one row per year.
    """
    campus = (
        buildings_df
        .groupby("year")[["kwh", "gas_cuft"]]
        .sum()
        .reset_index()
        .sort_values("year")
    )
    return campus


# 2023 snapshot


def build_2023_snapshot(buildings_df, sq_dict):

    df_2023 = buildings_df[buildings_df["year"] == 2023].copy()

    # Build a lookup from sq_dict
    sq_rows = []
    for name, meta in sq_dict.items():
        sq_rows.append({"sq_name": name, **meta})
    sq_df = pd.DataFrame(sq_rows)

    # Helper: find the best sq_name match for a meter building name
    def best_match(meter_name):
        meter_lower = meter_name.lower()
        for sq_name in sq_dict.keys():
            sq_lower = sq_name.lower()
            # Check if any significant word overlaps
            meter_words = set(meter_lower.split())
            sq_words    = set(sq_lower.split())
            if len(meter_words & sq_words) >= 2:
                return sq_name
            # Single-word names (e.g. "Gym", "Chapel")
            if meter_lower in sq_lower or sq_lower in meter_lower:
                return sq_name
        return None

    df_2023["sq_name"]   = df_2023["building"].apply(best_match)
    df_2023["sqft"]      = df_2023["sq_name"].map(lambda n: sq_dict.get(n, {}).get("sqft"))
    df_2023["fuel"]      = df_2023["sq_name"].map(lambda n: sq_dict.get(n, {}).get("fuel"))
    df_2023["use"]       = df_2023["sq_name"].map(lambda n: sq_dict.get(n, {}).get("use"))
    df_2023["year_built"]= df_2023["sq_name"].map(lambda n: sq_dict.get(n, {}).get("year_built"))

    df_2023 = df_2023.drop(columns=["year", "sq_name"])
    df_2023 = df_2023[df_2023["kwh"] + df_2023["gas_cuft"] > 0].reset_index(drop=True)
    return df_2023


# MAIN

if __name__ == "__main__":

    # raw data load
    year_data = load_meter_log(METER_FILE)
    sq_dict   = load_sq_footage(SQ_FT_FILE)

    # tables
    print("\nBuilding output tables...")
    buildings_df  = build_buildings_table(year_data)
    campus_df     = build_campus_totals(buildings_df)
    snapshot_2023 = build_2023_snapshot(buildings_df, sq_dict)

    # CSV
    out_bld  = os.path.join(OUTPUT_DIR, "buildings_energy.csv")
    out_cmp  = os.path.join(OUTPUT_DIR, "campus_totals.csv")
    out_snap = os.path.join(OUTPUT_DIR, "buildings_2023.csv")

    buildings_df.to_csv(out_bld,  index=False)
    campus_df.to_csv(out_cmp,     index=False)
    snapshot_2023.to_csv(out_snap, index=False)

    # Summary and printout
    print(f"\n✓ Saved: {out_bld}  ({len(buildings_df)} rows)")
    print(f"✓ Saved: {out_cmp}  ({len(campus_df)} rows)")
    print(f"✓ Saved: {out_snap}  ({len(snapshot_2023)} rows)")

    print("\n── Campus totals (most recent years) ──")
    print(campus_df.tail(6).to_string(index=False))

    print("\n── 2023 top 5 buildings by electricity use ──")
    top5 = snapshot_2023.nlargest(5, "kwh")[["building","kwh","gas_cuft","sqft"]]
    print(top5.to_string(index=False))

    print("\nStep 1 complete. Run step2_calculate_emissions.py next.")
