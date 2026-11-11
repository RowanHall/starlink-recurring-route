#!/usr/bin/env python3
"""
Step 2: Bin the merged dataset by GPS grid cell and compute per-cell stats.

Grid resolution: 0.001 degrees (~100 m) in both lat and lon.
For each cell, computes:
  - median and 90th-percentile latency
  - median downlink and uplink throughput
  - outage rate (fraction of rows that are in an outage)
  - dominant outage cause
  - sample count and session count

Output: data/route_grid.csv
Run:    python3 analysis/02_grid_analysis.py
"""

import pandas as pd
from pathlib import Path

DATA_FILE = Path(__file__).parent.parent / "data" / "all_sessions.parquet"
OUT_FILE  = Path(__file__).parent.parent / "data" / "route_grid.csv"

GRID_DEG = 0.001  # ~100 m per cell


def main():
    print(f"Loading {DATA_FILE} ...")
    df = pd.read_parquet(DATA_FILE)
    print(f"  {len(df):,} rows, {df['session_id'].nunique()} sessions")

    # Assign each row to a grid cell
    df["lat_cell"] = (df["latitude"]  / GRID_DEG).round() * GRID_DEG
    df["lon_cell"] = (df["longitude"] / GRID_DEG).round() * GRID_DEG

    # Outage rate and dominant cause per cell
    outage_rate = df.groupby(["lat_cell", "lon_cell"])["is_outage"].mean()
    dominant_cause = (
        df[df["is_outage"]]
        .groupby(["lat_cell", "lon_cell"])["outage_cause"]
        .agg(lambda x: x.value_counts().idxmax() if len(x) else pd.NA)
    )

    grid = df.groupby(["lat_cell", "lon_cell"]).agg(
        n_rows=("ts", "count"),
        n_sessions=("session_id", "nunique"),
        latency_median=("pop_ping_latency_ms", "median"),
        latency_p90=("pop_ping_latency_ms", lambda x: x.quantile(0.90)),
        downlink_median_mbps=("downlink_mbps", "median"),
        uplink_median_mbps=("uplink_mbps", "median"),
        signal_quality_median=("signal_quality", "median"),
        drop_rate_median=("pop_ping_drop_rate", "median"),
        tilt_median=("tilt_angle", "median"),
    ).reset_index()

    grid = grid.join(outage_rate.rename("outage_rate"), on=["lat_cell", "lon_cell"])
    grid = grid.join(dominant_cause.rename("dominant_outage_cause"), on=["lat_cell", "lon_cell"])

    # Time-of-day breakdown: median latency per hour group per cell
    for hour_label, hours in [("morning", [13]), ("afternoon", [15, 16, 17, 18]), ("evening", [21])]:
        sub = df[df["session_hour"].isin(hours)]
        col = sub.groupby(["lat_cell", "lon_cell"])["pop_ping_latency_ms"].median()
        grid = grid.join(col.rename(f"latency_median_{hour_label}"), on=["lat_cell", "lon_cell"])

    grid = grid.sort_values(["lat_cell", "lon_cell"])
    grid.to_csv(OUT_FILE, index=False)

    print(f"Grid cells: {len(grid):,}")
    print(f"Output:     {OUT_FILE}")

    # Quick sanity summary
    print("\nLatency (ms) across all cells:")
    print(grid["latency_median"].describe().round(1).to_string())
    print("\nDownlink throughput (Mbps):")
    print(grid["downlink_median_mbps"].describe().round(2).to_string())
    print("\nOutage rate:")
    print(grid["outage_rate"].describe().round(3).to_string())


if __name__ == "__main__":
    main()
