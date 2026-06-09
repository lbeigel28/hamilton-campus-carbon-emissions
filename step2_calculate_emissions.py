"""
Calculate Carbon Emissions

Reads the clean CSVs and applies EPA emission factors
to calculate CO2 (metric tons) for each building and for the campus.

Emission factors used:
  Electricity : 0.000201 MT CO2/kWh
                Source: EPA eGRID 2022, NYUP (New York Upstate) subregion
                https://www.epa.gov/egrid

  Natural gas : 0.0000530 MT CO2/cu ft
                Source: EPA GHG emission factor for natural gas combustion
                (53.06 kg CO2 / 1,000 cu ft × 0.001 to convert kg→MT)

Input files (from output/ folder):
  - buildings_energy.csv
  - campus_totals.csv
  - buildings_2023.csv

Output files:
  - buildings_emissions.csv   : CO2 added to per-building, per-year table
  - campus_emissions.csv      : CO2 added to campus totals table
  - buildings_2023_emissions.csv : 2023 snapshot with emissions + EUI

Run:
  python step2_calculate_emissions.py
"""

import pandas as pd
import numpy as np
import os

# Emission factors
# Changeif you want to model a different grid or fuel type.

ELEC_EF_MT_PER_KWH  = 0.000201   # MT CO2 per kWh  (NY grid, EPA eGRID 2022)
GAS_EF_MT_PER_CUFT  = 0.0000530  # MT CO2 per cu ft of natural gas

INPUT_DIR  = "output"
OUTPUT_DIR = "output"


def load_csv(filename):
    path = os.path.join(INPUT_DIR, filename)
    print(f"Reading {path}")
    return pd.read_csv(path)


# calc functions

def add_emissions(df):
    """
    Given a DataFrame with columns 'kwh' and 'gas_cuft',
    adds three new columns:
      elec_co2_mt  : CO2 from electricity  (metric tons)
      gas_co2_mt   : CO2 from natural gas  (metric tons)
      total_co2_mt : combined CO2          (metric tons)
    """
    df = df.copy()
    df["elec_co2_mt"]  = df["kwh"]      * ELEC_EF_MT_PER_KWH
    df["gas_co2_mt"]   = df["gas_cuft"] * GAS_EF_MT_PER_CUFT
    df["total_co2_mt"] = df["elec_co2_mt"] + df["gas_co2_mt"]

    # Round to 2 decimal places for readability
    df["elec_co2_mt"]  = df["elec_co2_mt"].round(2)
    df["gas_co2_mt"]   = df["gas_co2_mt"].round(2)
    df["total_co2_mt"] = df["total_co2_mt"].round(2)

    return df


def add_eui(df):
    """
    Adds Energy Use Intensity (EUI) columns to the 2023 snapshot.
    EUI = kBtu per square foot per year — a standard building efficiency metric.

    Conversion: 1 kWh = 3.412 kBtu
                1 cu ft natural gas ≈ 1.025 therms × 100 kBtu/therm = 102.5 kBtu
                (the 1.025 multiplier matches the meter log notation)
    """
    KWH_TO_KBTU    = 3.412
    CUFT_TO_KBTU   = 1.025 * 100  # ~102.5 kBtu per cu ft

    df = df.copy()
    df["total_kbtu"] = (
        df["kwh"]      * KWH_TO_KBTU  +
        df["gas_cuft"] * CUFT_TO_KBTU
    ).round(0)

    # EUI only makes sense where we have a valid square footage
    df["eui_kbtu_per_sqft"] = np.where(
        df["sqft"].notna() & (df["sqft"] > 0),
        (df["total_kbtu"] / df["sqft"]).round(1),
        np.nan
    )

    return df


def add_co2_per_sqft(df):
    """
    Adds CO2 intensity: MT CO2 per 1,000 sq ft.
    Useful for comparing buildings of different sizes.
    """
    df = df.copy()
    df["co2_per_1000sqft"] = np.where(
        df["sqft"].notna() & (df["sqft"] > 0),
        (df["total_co2_mt"] / df["sqft"] * 1000).round(3),
        np.nan
    )
    return df


# MAIN

if __name__ == "__main__":

    # load
    buildings_df  = load_csv("buildings_energy.csv")
    campus_df     = load_csv("campus_totals.csv")
    snapshot_2023 = load_csv("buildings_2023.csv")

    print(f"\nEmission factors:")
    print(f"  Electricity : {ELEC_EF_MT_PER_KWH} MT CO2 / kWh")
    print(f"  Natural gas : {GAS_EF_MT_PER_CUFT} MT CO2 / cu ft")

    # apply
    buildings_emissions  = add_emissions(buildings_df)
    campus_emissions     = add_emissions(campus_df)
    snapshot_emissions   = add_emissions(snapshot_2023)
    snapshot_emissions   = add_eui(snapshot_emissions)
    snapshot_emissions   = add_co2_per_sqft(snapshot_emissions)

    # save
    out1 = os.path.join(OUTPUT_DIR, "buildings_emissions.csv")
    out2 = os.path.join(OUTPUT_DIR, "campus_emissions.csv")
    out3 = os.path.join(OUTPUT_DIR, "buildings_2023_emissions.csv")

    buildings_emissions.to_csv(out1,  index=False)
    campus_emissions.to_csv(out2,     index=False)
    snapshot_emissions.to_csv(out3,   index=False)

    print(f"\n✓ Saved: {out1}")
    print(f"✓ Saved: {out2}")
    print(f"✓ Saved: {out3}")

    # print
    print("\n── Campus emissions by year (all years) ──")
    display_cols = ["year", "kwh", "gas_cuft", "elec_co2_mt", "gas_co2_mt", "total_co2_mt"]
    print(campus_emissions[display_cols].to_string(index=False))

    print("\n── 2023: Top 10 buildings by total CO2 ──")
    top10 = (
        snapshot_emissions
        .nlargest(10, "total_co2_mt")
        [["building", "kwh", "gas_cuft", "elec_co2_mt", "gas_co2_mt", "total_co2_mt", "eui_kbtu_per_sqft"]]
    )
    print(top10.to_string(index=False))

    print("\n── 2023: Buildings with highest CO2 intensity (MT CO2 per 1,000 sqft) ──")
    intensity = (
        snapshot_emissions
        .dropna(subset=["co2_per_1000sqft"])
        .nlargest(10, "co2_per_1000sqft")
        [["building", "total_co2_mt", "sqft", "co2_per_1000sqft"]]
    )
    print(intensity.to_string(index=False))

    total_2023 = campus_emissions.loc[campus_emissions["year"] == 2023, "total_co2_mt"].values
    if len(total_2023):
        print(f"\n── 2023 campus total: {total_2023[0]:,.1f} MT CO2 ──")

  
