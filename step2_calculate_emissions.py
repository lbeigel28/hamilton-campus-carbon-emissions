"""
Calculate Carbon Emissions

Takes the cleaned CSVs and adds CO2 calculations using EPA factors.
Outputs:
- per-building emissions
- campus-wide emissions
- 2023 snapshot with emissions + EUI

Run:
  python step2_calculate_emissions.py
"""

import pandas as pd
import numpy as np
import os

# emission factors (EPA)
# can tweak these later if we want a different region / assumptions

ELEC_EF_MT_PER_KWH  = 0.000201   # NY grid (eGRID 2022)
GAS_EF_MT_PER_CUFT  = 0.0000530  # natural gas


INPUT_DIR  = "output"
OUTPUT_DIR = "output"


def load_csv(filename):
    path = os.path.join(INPUT_DIR, filename)
    print(f"Reading {path}")
    return pd.read_csv(path)


# ---- emissions calculations ----

def add_emissions(df):
    # adds CO2 columns based on kwh + gas usage

    df = df.copy()

    df["elec_co2_mt"]  = df["kwh"]      * ELEC_EF_MT_PER_KWH
    df["gas_co2_mt"]   = df["gas_cuft"] * GAS_EF_MT_PER_CUFT
    df["total_co2_mt"] = df["elec_co2_mt"] + df["gas_co2_mt"]

    # rounding just to keep things readable
    df["elec_co2_mt"]  = df["elec_co2_mt"].round(2)
    df["gas_co2_mt"]   = df["gas_co2_mt"].round(2)
    df["total_co2_mt"] = df["total_co2_mt"].round(2)

    return df


def add_eui(df):
    # energy use intensity (kBtu / sqft)
    # standard way to compare buildings of different sizes

    KWH_TO_KBTU  = 3.412
    CUFT_TO_KBTU = 1.025 * 100  # ~102.5 kBtu per cu ft

    df = df.copy()

    df["total_kbtu"] = (
        df["kwh"]      * KWH_TO_KBTU +
        df["gas_cuft"] * CUFT_TO_KBTU
    ).round(0)

    # only compute EUI if sqft exists and is valid
    df["eui_kbtu_per_sqft"] = np.where(
        df["sqft"].notna() & (df["sqft"] > 0),
        (df["total_kbtu"] / df["sqft"]).round(1),
        np.nan
    )

    return df


def add_co2_per_sqft(df):
    # CO2 intensity (scaled per 1,000 sqft so numbers are easier to read)

    df = df.copy()

    df["co2_per_1000sqft"] = np.where(
        df["sqft"].notna() & (df["sqft"] > 0),
        (df["total_co2_mt"] / df["sqft"] * 1000).round(3),
        np.nan
    )

    return df


# ---- main ----

if __name__ == "__main__":

    # load inputs
    buildings_df  = load_csv("buildings_energy.csv")
    campus_df     = load_csv("campus_totals.csv")
    snapshot_2023 = load_csv("buildings_2023.csv")

    print(f"\nEmission factors:")
    print(f"  Electricity : {ELEC_EF_MT_PER_KWH} MT CO2 / kWh")
    print(f"  Natural gas : {GAS_EF_MT_PER_CUFT} MT CO2 / cu ft")

    # apply calculations
    buildings_emissions = add_emissions(buildings_df)
    campus_emissions    = add_emissions(campus_df)

    snapshot_emissions  = add_emissions(snapshot_2023)
    snapshot_emissions  = add_eui(snapshot_emissions)
    snapshot_emissions  = add_co2_per_sqft(snapshot_emissions)

    # save outputs
    out1 = os.path.join(OUTPUT_DIR, "buildings_emissions.csv")
    out2 = os.path.join(OUTPUT_DIR, "campus_emissions.csv")
    out3 = os.path.join(OUTPUT_DIR, "buildings_2023_emissions.csv")

    buildings_emissions.to_csv(out1,  index=False)
    campus_emissions.to_csv(out2,     index=False)
    snapshot_emissions.to_csv(out3,   index=False)

    print(f"\n✓ Saved: {out1}")
    print(f"✓ Saved: {out2}")
    print(f"✓ Saved: {out3}")

    # ---- quick outputs ----

    print("\n── Campus emissions by year ──")
    display_cols = ["year", "kwh", "gas_cuft", "elec_co2_mt", "gas_co2_mt", "total_co2_mt"]
    print(campus_emissions[display_cols].to_string(index=False))

    print("\n── 2023: Top 10 buildings by total CO2 ──")
    top10 = (
        snapshot_emissions
        .nlargest(10, "total_co2_mt")
        [["building", "kwh", "gas_cuft", "elec_co2_mt", "gas_co2_mt", "total_co2_mt", "eui_kbtu_per_sqft"]]
    )
    print(top10.to_string(index=False))

    print("\n── 2023: highest CO2 intensity (per 1,000 sqft) ──")
    intensity = (
        snapshot_emissions
        .dropna(subset=["co2_per_1000sqft"])
        .nlargest(10, "co2_per_1000sqft")
        [["building", "total_co2_mt", "sqft", "co2_per_1000sqft"]]
    )
    print(intensity.to_string(index=False))

    total_2023 = campus_emissions.loc[
        campus_emissions["year"] == 2023, "total_co2_mt"
    ].values

    if len(total_2023):
        print(f"\n── 2023 campus total: {total_2023[0]:,.1f} MT CO2 ──")
