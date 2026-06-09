"""
STEP 4: Visualize Everything
==============================
Generates a set of clear, publication-quality charts saved as PNGs.

Charts produced (all saved to output/charts/):
  1. campus_trend.png          – historical campus CO2 by year
  2. elec_vs_gas.png           – stacked area: electricity vs gas CO2
  3. top_buildings_2023.png    – horizontal bar: top 15 buildings
  4. building_breakdown.png    – pie chart: share of total CO2 by building
  5. predictions.png           – historical + all 3 model forecasts
  6. eui_distribution.png      – Energy Use Intensity across buildings
  7. co2_by_use_type.png       – box plot of CO2 by building use type

Run:
  python step4_visualize.py
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os

INPUT_DIR  = "output"
CHART_DIR  = os.path.join("output", "charts")
os.makedirs(CHART_DIR, exist_ok=True)

# ── Consistent style across all charts ────────────────────────────────────────
BLUE   = "#3266AD"
ORANGE = "#E07B39"
GREEN  = "#3B9E60"
GRAY   = "#888780"
RED    = "#C0392B"

plt.rcParams.update({
    "figure.facecolor":  "white",
    "axes.facecolor":    "white",
    "axes.grid":         True,
    "grid.color":        "#EEEEEE",
    "grid.linewidth":    0.8,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "font.family":       "sans-serif",
    "font.size":         11,
    "axes.titlesize":    14,
    "axes.titleweight":  "bold",
    "axes.labelsize":    11,
})


def save(name):
    path = os.path.join(CHART_DIR, name)
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  ✓ Saved {path}")


def load(filename):
    return pd.read_csv(os.path.join(INPUT_DIR, filename))


# ══════════════════════════════════════════════════════════════════════════════
# CHART 1: Historical campus CO2 trend
# ══════════════════════════════════════════════════════════════════════════════

def chart_campus_trend(campus_df):
    df = campus_df.sort_values("year")

    fig, ax = plt.subplots(figsize=(11, 5))

    ax.plot(df["year"], df["total_co2_mt"], color=BLUE, linewidth=2.5,
            marker="o", markersize=5, label="Total CO₂ (MT)")

    # Shade the region to show declining trend
    ax.fill_between(df["year"], df["total_co2_mt"], alpha=0.12, color=BLUE)

    # Annotate peak and most recent year
    peak_row = df.loc[df["total_co2_mt"].idxmax()]
    ax.annotate(
        f"Peak: {peak_row['total_co2_mt']:,.0f} MT\n({int(peak_row['year'])})",
        xy=(peak_row["year"], peak_row["total_co2_mt"]),
        xytext=(peak_row["year"] - 2, peak_row["total_co2_mt"] + 80),
        arrowprops=dict(arrowstyle="->", color=GRAY),
        fontsize=9, color=GRAY,
    )
    last = df.iloc[-1]
    ax.annotate(
        f"{int(last['year'])}: {last['total_co2_mt']:,.0f} MT",
        xy=(last["year"], last["total_co2_mt"]),
        xytext=(last["year"] - 3, last["total_co2_mt"] - 250),
        arrowprops=dict(arrowstyle="->", color=GRAY),
        fontsize=9, color=GRAY,
    )

    ax.set_title("Hamilton College — Campus CO₂ Emissions (2004–2025)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Metric Tons CO₂e")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_xticks(df["year"])
    ax.tick_params(axis="x", rotation=45)
    ax.legend()

    plt.tight_layout()
    save("campus_trend.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 2: Electricity vs gas CO2 stacked area
# ══════════════════════════════════════════════════════════════════════════════

def chart_elec_vs_gas(campus_df):
    df = campus_df.sort_values("year")

    fig, ax = plt.subplots(figsize=(11, 5))

    ax.stackplot(
        df["year"],
        df["elec_co2_mt"],
        df["gas_co2_mt"],
        labels=["Electricity CO₂", "Natural Gas CO₂"],
        colors=[BLUE, ORANGE],
        alpha=0.85,
    )

    ax.set_title("Campus CO₂ by Energy Source — Electricity vs. Natural Gas")
    ax.set_xlabel("Year")
    ax.set_ylabel("Metric Tons CO₂e")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    ax.set_xticks(df["year"])
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="upper left")

    plt.tight_layout()
    save("elec_vs_gas.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 3: Top 15 buildings by 2023 CO2
# ══════════════════════════════════════════════════════════════════════════════

def chart_top_buildings(snapshot_df, n=15):
    df = snapshot_df.nlargest(n, "total_co2_mt").sort_values("total_co2_mt")

    fig, ax = plt.subplots(figsize=(10, n * 0.55 + 1.5))

    bars_elec = ax.barh(df["building"], df["elec_co2_mt"], color=BLUE,
                        label="Electricity CO₂", height=0.6)
    bars_gas  = ax.barh(df["building"], df["gas_co2_mt"],  color=ORANGE,
                        left=df["elec_co2_mt"], label="Natural Gas CO₂", height=0.6)

    # Label each bar with the total
    for _, row in df.iterrows():
        ax.text(
            row["total_co2_mt"] + 5,
            row["building"],
            f"{row['total_co2_mt']:.0f} MT",
            va="center", fontsize=8.5, color=GRAY,
        )

    ax.set_title("2023 CO₂ Emissions — Top 15 Buildings")
    ax.set_xlabel("Metric Tons CO₂e")
    ax.legend()

    plt.tight_layout()
    save("top_buildings_2023.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 4: Pie chart — share of total campus CO2 (top buildings + other)
# ══════════════════════════════════════════════════════════════════════════════

def chart_co2_pie(snapshot_df, n=8):
    df = snapshot_df[snapshot_df["total_co2_mt"] > 0].copy()
    top_n  = df.nlargest(n, "total_co2_mt")
    others = df["total_co2_mt"].sum() - top_n["total_co2_mt"].sum()

    labels = list(top_n["building"]) + ["All other buildings"]
    values = list(top_n["total_co2_mt"]) + [others]

    colors = [BLUE, ORANGE, GREEN, "#7F77DD", "#D85A30", "#1D9E75",
              "#BA7517", "#A32D2D", GRAY]

    fig, ax = plt.subplots(figsize=(9, 7))
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        colors=colors,
        autopct=lambda pct: f"{pct:.1f}%" if pct > 3 else "",
        startangle=140,
        pctdistance=0.82,
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
    )
    for t in autotexts:
        t.set_fontsize(9)

    ax.set_title("Share of 2023 Campus CO₂ Emissions by Building")
    plt.tight_layout()
    save("building_breakdown.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 5: Predictions — historical + 3 forecast models
# ══════════════════════════════════════════════════════════════════════════════

def chart_predictions(campus_df, pred_df):
    hist = campus_df.sort_values("year")
    pred = pred_df.sort_values("year")

    fig, ax = plt.subplots(figsize=(12, 6))

    # Historical
    ax.plot(hist["year"], hist["total_co2_mt"],
            color=BLUE, linewidth=2.5, marker="o", markersize=4,
            label="Historical (actual)", zorder=3)

    # Predictions — connect from last historical point
    last_yr  = hist["year"].max()
    last_co2 = float(hist.loc[hist["year"] == last_yr, "total_co2_mt"].values[0])

    def connect_and_plot(color, col, label, dash):
        years = [last_yr] + list(pred["year"])
        vals  = [last_co2] + list(pred[col])
        ax.plot(years, vals, color=color, linewidth=2,
                linestyle=dash, marker="o", markersize=4, label=label)

    connect_and_plot(ORANGE, "linear_co2_mt",      "Linear regression",     "--")
    connect_and_plot(GREEN,  "scenario_co2_mt",    "Policy scenario",        "-")
    connect_and_plot(GRAY,   "exponential_co2_mt", "Exponential decay",     ":")

    # Mark 2030 net-zero targets reference
    ax.axhline(0, color="black", linewidth=0.8, linestyle="--", alpha=0.3)

    # Shade forecast region
    ax.axvspan(last_yr, pred["year"].max(), alpha=0.04, color=GRAY, label="_Forecast zone")
    ax.text(last_yr + 0.3, hist["total_co2_mt"].max() * 0.98,
            "← Historical   Forecast →", fontsize=9, color=GRAY)

    ax.set_title("Hamilton College — Carbon Emissions Forecast (2026–2040)")
    ax.set_xlabel("Year")
    ax.set_ylabel("Metric Tons CO₂e")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    all_years = sorted(list(hist["year"]) + list(pred["year"]))
    ax.set_xticks(all_years)
    ax.tick_params(axis="x", rotation=45)
    ax.legend(loc="upper right")

    plt.tight_layout()
    save("predictions.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 6: Energy Use Intensity distribution
# ══════════════════════════════════════════════════════════════════════════════

def chart_eui(snapshot_df):
    df = snapshot_df.dropna(subset=["eui_kbtu_per_sqft"]).copy()
    df = df[df["eui_kbtu_per_sqft"] > 0].sort_values("eui_kbtu_per_sqft", ascending=False)

    # Truncate very long names
    df["short_name"] = df["building"].str.slice(0, 25)

    fig, ax = plt.subplots(figsize=(10, max(5, len(df) * 0.45 + 1.5)))

    colors = [ORANGE if v > 300 else (BLUE if v > 150 else GREEN)
              for v in df["eui_kbtu_per_sqft"]]

    bars = ax.barh(df["short_name"], df["eui_kbtu_per_sqft"], color=colors, height=0.6)

    # Reference line: ENERGY STAR median for higher education ~150 kBtu/sqft
    ax.axvline(150, color=RED, linewidth=1.2, linestyle="--", alpha=0.7,
               label="ENERGY STAR baseline ~150 kBtu/sqft/yr")

    ax.set_title("2023 Energy Use Intensity (EUI) by Building")
    ax.set_xlabel("kBtu / sq ft / year")
    ax.legend()

    plt.tight_layout()
    save("eui_distribution.png")


# ══════════════════════════════════════════════════════════════════════════════
# CHART 7: CO2 by building use type
# ══════════════════════════════════════════════════════════════════════════════

def chart_by_use_type(snapshot_df):
    df = snapshot_df[snapshot_df["total_co2_mt"] > 0].copy()
    df["use"] = df["use"].fillna("Unknown")

    grouped = (
        df.groupby("use")["total_co2_mt"]
        .agg(["sum", "mean", "count"])
        .reset_index()
        .sort_values("sum", ascending=False)
    )

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Left: total CO2 by use type
    ax = axes[0]
    bars = ax.bar(grouped["use"], grouped["sum"], color=BLUE, alpha=0.85)
    ax.set_title("Total CO₂ by Building Use Type (2023)")
    ax.set_ylabel("Metric Tons CO₂e")
    ax.tick_params(axis="x", rotation=30)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    for bar in bars:
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 5,
                f"{bar.get_height():,.0f}",
                ha="center", fontsize=8.5, color=GRAY)

    # Right: average CO2 per building within each use type
    ax2 = axes[1]
    bars2 = ax2.bar(grouped["use"], grouped["mean"], color=ORANGE, alpha=0.85)
    ax2.set_title("Average CO₂ per Building by Use Type (2023)")
    ax2.set_ylabel("Avg Metric Tons CO₂e per Building")
    ax2.tick_params(axis="x", rotation=30)
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    for bar in bars2:
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 bar.get_height() + 2,
                 f"{bar.get_height():,.0f}",
                 ha="center", fontsize=8.5, color=GRAY)

    plt.suptitle("Carbon Emissions by Building Use Category", fontsize=14, fontweight="bold")
    plt.tight_layout()
    save("co2_by_use_type.png")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    print("Loading data...")
    campus_df   = load("campus_emissions.csv")
    snapshot_df = load("buildings_2023_emissions.csv")
    pred_df     = load("predictions.csv")

    print("\nGenerating charts...")
    chart_campus_trend(campus_df)
    chart_elec_vs_gas(campus_df)
    chart_top_buildings(snapshot_df)
    chart_co2_pie(snapshot_df)
    chart_predictions(campus_df, pred_df)
    chart_eui(snapshot_df)
    chart_by_use_type(snapshot_df)

    print(f"\nAll charts saved to {CHART_DIR}/")
    print("Step 4 complete — your project is done!")
