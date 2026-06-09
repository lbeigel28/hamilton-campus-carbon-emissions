Hamilton College — Carbon Emissions Prediction Project
=======================================================

A step-by-step Python project that reads Hamilton College energy meter data,
calculates CO2 emissions per building, forecasts future emissions using three
models, and produces publication-quality charts.


──────────────────────────────────────────────────────
FOLDER STRUCTURE
──────────────────────────────────────────────────────

hamilton_carbon/
│
├── Hamilton_College_Electric___Gas_Meter_Log.xls   ← put your data files here
├── Sq_Foot_Hamilton_College_2023.xlsx               ← put your data files here
│
├── step1_extract_data.py        reads raw spreadsheets → clean CSVs
├── step2_calculate_emissions.py applies emission factors → CO2 columns
├── step3_predict.py             three forecasting models → predictions CSV
├── step4_visualize.py           generates 7 charts as PNGs
│
├── requirements.txt             Python packages to install
└── output/                      all CSV and chart outputs (auto-created)
    ├── buildings_energy.csv
    ├── campus_totals.csv
    ├── buildings_2023.csv
    ├── buildings_emissions.csv
    ├── campus_emissions.csv
    ├── buildings_2023_emissions.csv
    ├── predictions.csv
    ├── model_summary.txt
    └── charts/
        ├── campus_trend.png
        ├── elec_vs_gas.png
        ├── top_buildings_2023.png
        ├── building_breakdown.png
        ├── predictions.png
        ├── eui_distribution.png
        └── co2_by_use_type.png


──────────────────────────────────────────────────────
SETUP (one time only)
──────────────────────────────────────────────────────

1. Install Python 3.9 or later if you haven't already.
   https://www.python.org/downloads/

2. Open a terminal in VS Code  (Terminal → New Terminal).

3. Install required packages:

     pip install -r requirements.txt

4. Copy your two spreadsheet files into this folder:
     Hamilton_College_Electric___Gas_Meter_Log.xls
     Sq_Foot_Hamilton_College_2023.xlsx


──────────────────────────────────────────────────────
HOW TO RUN
──────────────────────────────────────────────────────

Run each script in order from the terminal:

     python step1_extract_data.py
     python step2_calculate_emissions.py
     python step3_predict.py
     python step4_visualize.py

Each script prints what it's doing and where it saved its outputs.
You can re-run any step independently if you want to change settings.


──────────────────────────────────────────────────────
HOW TO CUSTOMIZE
──────────────────────────────────────────────────────

Change emission factors (step2_calculate_emissions.py, top of file):
  ELEC_EF_MT_PER_KWH = 0.000201   ← swap in a different EPA eGRID value
  GAS_EF_MT_PER_CUFT = 0.0000530

Change forecast scenario (step3_predict.py, top of file):
  SCENARIO = {
      "grid_clean_by_2030":       0.30,   ← 30% cleaner NY grid by 2030
      "annual_efficiency_pct":    0.01,   ← 1% less electricity/yr
      "annual_gas_reduction_pct": 0.03,   ← 3% less gas/yr
  }


──────────────────────────────────────────────────────
DATA SOURCES & METHODOLOGY
──────────────────────────────────────────────────────

Electricity emission factor:
  0.000201 MT CO2 / kWh
  EPA eGRID 2022, NYUP (New York Upstate) subregion
  https://www.epa.gov/egrid

Natural gas emission factor:
  0.0000530 MT CO2 / cu ft  (= 53.06 kg CO2 / 1,000 cu ft)
  EPA Emission Factors for Greenhouse Gas Inventories (2024)
  Natural gas combustion, CO2 only

Energy Use Intensity (EUI):
  kBtu / sq ft / year
  Conversions: 1 kWh = 3.412 kBtu
               1 cu ft natural gas = 102.5 kBtu (1.025 × 100 kBtu/therm)

Forecasting models:
  1. Linear regression   — sklearn LinearRegression on 2014–2025 actuals
  2. Exponential decay   — sklearn LinearRegression on log(CO2) vs year
  3. Policy scenario     — forward simulation applying three independent levers


──────────────────────────────────────────────────────
NOTES ON THE RAW DATA
──────────────────────────────────────────────────────

- Gas data is present for some buildings (Gym, Dunham, Commons, C.A. Johnson,
  Buttrick) but not all.  Most buildings are electrically heated or gas data
  was not separately metered.

- The Main Gas House meter (MCF × 10.25 multiplier) records aggregate campus
  gas intake and is NOT double-counted with individual building meters.

- Some building names changed between years (e.g. "Admissions" →
  "E.Root (Old Admissions)").  The scripts treat these as separate meters.

- Years 2003 and 2006 have incomplete data and are excluded from regression.
