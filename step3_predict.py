"""
Predict future emissions

Reads campus_emissions.csv and builds three forecasting models:

  1. Linear regression     – simple trend extrapolation
  2. Exponential decay     – assumes a fixed % reduction each year
  3. Scenario model        – lets you set policy levers:
       • Grid decarbonization (% improvement in NY electricity EF by 2030)
       • Annual efficiency improvement (% reduction in kWh/yr)
       • Natural gas phase-out rate   (% reduction in gas use/yr)

Outputs:
  - predictions.csv        : predicted CO2 for each model, 2026–2040
  - model_summary.txt      : regression coefficients and fit statistics

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

# senario parameters
SCENARIO = {
    # How much cleaner does NY electricity get by 2030?
    # NY's Climate Leadership Act targets 70% renewable by 2030.
    # Express as fraction: 0.30 = 30% reduction in grid emission factor
    "grid_clean_by_2030":       0.30,

    # Annual percentage reduction in total kWh from efficiency measures
    # (insulation, LED lighting, HVAC upgrades, etc.)
    "annual_efficiency_pct":    0.01,   # 1% per year

    # Annual percentage reduction in natural gas consumption
    # (electrification of heating, heat pumps, etc.)
    "annual_gas_reduction_pct": 0.03,   # 3% per year
}

# Emission factor baseline (2023 values)
ELEC_EF_2023 = 0.000201   # MT CO2/kWh
GAS_EF        = 0.0000530  # MT CO2/cu ft (constant — combustion factor doesn't change)

# Years to predict
PREDICT_YEARS = list(range(2026, 2041))

# Use only these years for regression (drop outlier years with incomplete data)
REGRESSION_YEARS_FROM = 2014


# linear regression

def linear_regression_model(campus_df):
    """
    Fits a straight line to historical CO2 totals and extrapolates.

    Returns:
      predictions (list of floats), slope, intercept, r2_score
    """
    # Filter to training window
    train = campus_df[campus_df["year"] >= REGRESSION_YEARS_FROM].dropna(subset=["total_co2_mt"])

    X = train["year"].values.reshape(-1, 1)
    y = train["total_co2_mt"].values

    model = LinearRegression()
    model.fit(X, y)

    slope     = model.coef_[0]
    intercept = model.intercept_
    r2        = r2_score(y, model.predict(X))

    X_future   = np.array(PREDICT_YEARS).reshape(-1, 1)
    predictions = model.predict(X_future)
    predictions = np.maximum(predictions, 0)   # can't be negative

    return predictions.tolist(), slope, intercept, r2


# exponetial decay

def exponential_decay_model(campus_df):
    """
    Fits an exponential decay: CO2(t) = A * e^(r*t)
    by fitting a linear model to log(CO2).

    Returns:
      predictions (list of floats), annual_rate (%), r2_score
    """
    train = campus_df[campus_df["year"] >= REGRESSION_YEARS_FROM].dropna(subset=["total_co2_mt"])
    train = train[train["total_co2_mt"] > 0]   # log requires positive values

    X = train["year"].values.reshape(-1, 1)
    y = np.log(train["total_co2_mt"].values)

    model = LinearRegression()
    model.fit(X, y)

    r  = model.coef_[0]         # growth rate (negative = decay)
    A  = np.exp(model.intercept_)
    r2 = r2_score(y, model.predict(X))

    annual_rate_pct = (np.exp(r) - 1) * 100   # e.g. -1.2% per year

    predictions = [A * np.exp(r * yr) for yr in PREDICT_YEARS]
    predictions = [max(0, p) for p in predictions]

    return predictions, annual_rate_pct, r2


# policy senario

def scenario_model(campus_df, scenario=SCENARIO):
    """
    Forward-simulates emissions by applying three independent levers
    to the 2023 actuals (split by fuel type).

    Electricity CO2 goes down because:
      (a) the NY grid gets cleaner (lower emission factor)
      (b) buildings use less electricity (efficiency)

    Gas CO2 goes down because:
      (c) buildings use less gas (electrification/phase-out)

    Parameters come from the SCENARIO dict at the top of this file.
    """
    # Pull 2023 actuals
    row_2023 = campus_df[campus_df["year"] == 2023]
    if row_2023.empty:
        raise ValueError("2023 data not found in campus_emissions.csv")

    kwh_2023      = float(row_2023["kwh"].values[0])
    gas_cuft_2023 = float(row_2023["gas_cuft"].values[0])

    grid_reduction       = scenario["grid_clean_by_2030"]
    annual_eff           = scenario["annual_efficiency_pct"]
    annual_gas_reduction = scenario["annual_gas_reduction_pct"]

    predictions = []
    for yr in PREDICT_YEARS:
        yrs_since_2023 = yr - 2023

        # electricty side
        # Efficiency reduces kWh year over year
        kwh = kwh_2023 * ((1 - annual_eff) ** yrs_since_2023)

        # Grid emission factor improves linearly toward 2030 goal,
        # then stays at that level.
        if yr <= 2030:
            fraction_to_2030 = (yr - 2023) / (2030 - 2023)
            ef_elec = ELEC_EF_2023 * (1 - grid_reduction * fraction_to_2030)
        else:
            ef_elec = ELEC_EF_2023 * (1 - grid_reduction)

        elec_co2 = kwh * ef_elec

        # gas side
        gas_cuft = gas_cuft_2023 * ((1 - annual_gas_reduction) ** yrs_since_2023)
        gas_co2  = gas_cuft * GAS_EF

        total_co2 = max(0, elec_co2 + gas_co2)
        predictions.append(round(total_co2, 1))

    return predictions


# MAIN

if __name__ == "__main__":

    # load data
    campus_path = os.path.join(INPUT_DIR, "campus_emissions.csv")
    print(f"Reading {campus_path}")
    campus_df = pd.read_csv(campus_path)

    # run models
    print("\nFitting models...")

    linear_preds, slope, intercept, linear_r2 = linear_regression_model(campus_df)
    print(f"  Linear regression  R² = {linear_r2:.3f}  slope = {slope:+.1f} MT/yr")

    exp_preds, exp_rate, exp_r2 = exponential_decay_model(campus_df)
    print(f"  Exponential decay  R² = {exp_r2:.3f}  rate  = {exp_rate:+.2f}%/yr")

    scenario_preds = scenario_model(campus_df, SCENARIO)
    print(f"  Scenario model     (see SCENARIO dict for assumptions)")

    # tabels
    predictions_df = pd.DataFrame({
        "year":                   PREDICT_YEARS,
        "linear_co2_mt":          [round(v, 1) for v in linear_preds],
        "exponential_co2_mt":     [round(v, 1) for v in exp_preds],
        "scenario_co2_mt":        scenario_preds,
    })

    historical = campus_df[["year", "total_co2_mt"]].copy()
    historical.columns = ["year", "actual_co2_mt"]

    out_path = os.path.join(OUTPUT_DIR, "predictions.csv")
    predictions_df.to_csv(out_path, index=False)
    print(f"\n✓ Saved predictions: {out_path}")

    summary_lines = [
        "Hamilton College Carbon Emissions — Model Summary",
        "=" * 55,
        "",
        f"Training data: {REGRESSION_YEARS_FROM}–2025",
        f"Prediction window: {PREDICT_YEARS[0]}–{PREDICT_YEARS[-1]}",
        "",
        "── Model 1: Linear Regression ──",
        f"  Slope     : {slope:+.2f} MT CO2 / year",
        f"  Intercept : {intercept:.1f}",
        f"  R²        : {linear_r2:.4f}",
        f"  Interpretation: emissions are changing by {slope:+.1f} MT/yr on average",
        "",
        "── Model 2: Exponential Decay ──",
        f"  Annual rate : {exp_rate:+.2f}% per year",
        f"  R²          : {exp_r2:.4f}",
        "",
        "── Model 3: Scenario (policy levers) ──",
        f"  Grid decarbonization by 2030 : {SCENARIO['grid_clean_by_2030']*100:.0f}%",
        f"  Annual efficiency improvement: {SCENARIO['annual_efficiency_pct']*100:.1f}% / yr",
        f"  Annual gas reduction          : {SCENARIO['annual_gas_reduction_pct']*100:.1f}% / yr",
        "",
        "── Emission Factors Used ──",
        f"  Electricity: {ELEC_EF_2023} MT CO2 / kWh  (EPA eGRID 2022 NYUP)",
        f"  Natural gas: {GAS_EF} MT CO2 / cu ft",
        "",
        "── Key Predictions (2030) ──",
        f"  Linear model    : {linear_preds[4]:,.0f} MT CO2",
        f"  Exponential     : {exp_preds[4]:,.0f} MT CO2",
        f"  Scenario model  : {scenario_preds[4]:,.0f} MT CO2",
        "",
        "── Key Predictions (2040) ──",
        f"  Linear model    : {linear_preds[14]:,.0f} MT CO2",
        f"  Exponential     : {exp_preds[14]:,.0f} MT CO2",
        f"  Scenario model  : {scenario_preds[14]:,.0f} MT CO2",
    ]

    summary_path = os.path.join(OUTPUT_DIR, "model_summary.txt")
    with open(summary_path, "w") as f:
        f.write("\n".join(summary_lines))
    print(f"✓ Saved model summary: {summary_path}")

    # print
    print("\n── Predictions 2026–2040 ──")
    print(predictions_df.to_string(index=False))

    print("\nStep 3 complete. Run step4_visualize.py to generate all charts.")
