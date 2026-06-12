"""
Predict future emissions

Uses campus_emissions.csv and builds a few simple models to project forward:
- linear trend
- exponential decay
- a policy scenario model (lets us play with assumptions)

Outputs:
  - predictions.csv
  - model_summary.txt

Run:
  python step3_predict.py
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import os

INPUT_DIR  = "output"
OUTPUT_DIR = "output"

# scenario assumptions (can tweak these to test different futures)
SCENARIO = {
    # how much cleaner the grid gets by 2030
    "grid_clean_by_2030":       0.30,

    # yearly reduction in electricity use (efficiency upgrades etc.)
    "annual_efficiency_pct":    0.01,

    # yearly reduction in gas use (electrification / phase-out)
    "annual_gas_reduction_pct": 0.03,
}

# emission factors (using 2023 as baseline)
ELEC_EF_2023 = 0.000201
GAS_EF       = 0.0000530   # this one stays constant

# years we want predictions for
PREDICT_YEARS = list(range(2026, 2041))

# ignore earlier years (data is a bit messy / incomplete there)
REGRESSION_YEARS_FROM = 2014


# ---- linear regression ----

def linear_regression_model(campus_df):
    # simple trend line on total CO2

    train = campus_df[
        campus_df["year"] >= REGRESSION_YEARS_FROM
    ].dropna(subset=["total_co2_mt"])

    X = train["year"].values.reshape(-1, 1)
    y = train["total_co2_mt"].values

    model = LinearRegression()
    model.fit(X, y)

    slope     = model.coef_[0]
    intercept = model.intercept_
    r2        = r2_score(y, model.predict(X))

    X_future = np.array(PREDICT_YEARS).reshape(-1, 1)
    predictions = model.predict(X_future)

    # just in case it goes negative (which doesn't make sense)
    predictions = np.maximum(predictions, 0)

    return predictions.tolist(), slope, intercept, r2


# ---- exponential decay ----

def exponential_decay_model(campus_df):
    # assumes emissions change at a constant % rate

    train = campus_df[
        campus_df["year"] >= REGRESSION_YEARS_FROM
    ].dropna(subset=["total_co2_mt"])

    # log transform → linear model
    train = train[train["total_co2_mt"] > 0]

    X = train["year"].values.reshape(-1, 1)
    y = np.log(train["total_co2_mt"].values)

    model = LinearRegression()
    model.fit(X, y)

    r  = model.coef_[0]         # growth/decay rate
    A  = np.exp(model.intercept_)
    r2 = r2_score(y, model.predict(X))

    annual_rate_pct = (np.exp(r) - 1) * 100

    predictions = [A * np.exp(r * yr) for yr in PREDICT_YEARS]
    predictions = [max(0, p) for p in predictions]

    return predictions, annual_rate_pct, r2


# ---- scenario model ----

def scenario_model(campus_df, scenario=SCENARIO):
    # forward simulation starting from 2023
    # splits electricity + gas so we can model them differently

    row_2023 = campus_df[campus_df["year"] == 2023]
    if row_2023.empty:
        raise ValueError("2023 data not found")

    kwh_2023      = float(row_2023["kwh"].values[0])
    gas_cuft_2023 = float(row_2023["gas_cuft"].values[0])

    grid_reduction       = scenario["grid_clean_by_2030"]
    annual_eff           = scenario["annual_efficiency_pct"]
    annual_gas_reduction = scenario["annual_gas_reduction_pct"]

    predictions = []

    for yr in PREDICT_YEARS:
        yrs_since_2023 = yr - 2023

        # ---- electricity side ----

        # efficiency reduces usage over time
        kwh = kwh_2023 * ((1 - annual_eff) ** yrs_since_2023)

        # grid gets cleaner until 2030, then flattens
        if yr <= 2030:
            fraction_to_2030 = (yr - 2023) / (2030 - 2023)
            ef_elec = ELEC_EF_2023 * (1 - grid_reduction * fraction_to_2030)
        else:
            ef_elec = ELEC_EF_2023 * (1 - grid_reduction)

        elec_co2 = kwh * ef_elec

        # ---- gas side ----

        gas_cuft = gas_cuft_2023 * ((1 - annual_gas_reduction) ** yrs_since_2023)
        gas_co2  = gas_cuft * GAS_EF

        total_co2 = max(0, elec_co2 + gas_co2)
        predictions.append(round(total_co2, 1))

    return predictions


# ---- main ----

if __name__ == "__main__":

    # load data
    campus_path = os.path.join(INPUT_DIR, "campus_emissions.csv")
    print(f"Reading {campus_path}")
    campus_df = pd.read_csv(campus_path)

    print("\nFitting models...")

    linear_preds, slope, intercept, linear_r2 = linear_regression_model(campus_df)
    print(f"  Linear regression  R² = {linear_r2:.3f}  slope = {slope:+.1f} MT/yr")

    exp_preds, exp_rate, exp_r2 = exponential_decay_model(campus_df)
    print(f"  Exponential decay  R² = {exp_r2:.3f}  rate  = {exp_rate:+.2f}%/yr")

    scenario_preds = scenario_model(campus_df, SCENARIO)
    print(f"  Scenario model     (see SCENARIO dict)")

    # build output table
    predictions_df = pd.DataFrame({
        "year":               PREDICT_YEARS,
        "linear_co2_mt":      [round(v, 1) for v in linear_preds],
        "exponential_co2_mt": [round(v, 1) for v in exp_preds],
        "scenario_co2_mt":    scenario_preds,
    })

    historical = campus_df[["year", "total_co2_mt"]].copy()
    historical.columns = ["year", "actual_co2_mt"]

    out_path = os.path.join(OUTPUT_DIR, "predictions.csv")
    predictions_df.to_csv(out_path, index=False)
    print(f"\n✓ Saved predictions: {out_path}")

    # write summary file
    summary_lines = [
        "Hamilton College Carbon Emissions — Model Summary",
        "=" * 55,
        "",
        f"Training data: {REGRESSION_YEARS_FROM}–2025",
        f"Prediction window: {PREDICT_YEARS[0]}–{PREDICT_YEARS[-1]}",
        "",
        "── Linear Regression ──",
        f"  Slope     : {slope:+.2f} MT CO2 / year",
        f"  Intercept : {intercept:.1f}",
        f"  R²        : {linear_r2:.4f}",
        "",
        "── Exponential Decay ──",
        f"  Annual rate : {exp_rate:+.2f}% per year",
        f"  R²          : {exp_r2:.4f}",
        "",
        "── Scenario Model ──",
        f"  Grid decarb by 2030 : {SCENARIO['grid_clean_by_2030']*100:.0f}%",
        f"  Efficiency gain     : {SCENARIO['annual_efficiency_pct']*100:.1f}% / yr",
        f"  Gas reduction       : {SCENARIO['annual_gas_reduction_pct']*100:.1f}% / yr",
        "",
        "── 2030 predictions ──",
        f"  Linear      : {linear_preds[4]:,.0f}",
        f"  Exponential : {exp_preds[4]:,.0f}",
        f"  Scenario    : {scenario_preds[4]:,.0f}",
        "",
        "── 2040 predictions ──",
        f"  Linear      : {linear_preds[14]:,.0f}",
        f"  Exponential : {exp_preds[14]:,.0f}",
        f"  Scenario    : {scenario_preds[14]:,.0f}",
    ]

    summary_path = os.path.join(OUTPUT_DIR, "model_summary.txt")
    with open(summary_path, "w") as f:
        f.write("\n".join(summary_lines))

    print(f"✓ Saved model summary: {summary_path}")

    # quick print
    print("\n── Predictions 2026–2040 ──")
    print(predictions_df.to_string(index=False))
