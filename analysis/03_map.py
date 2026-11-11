#!/usr/bin/env python3
"""
Step 3: Generate an interactive map of Starlink performance along the route.

Reads data/route_grid.csv and produces gh-pages/map.html — an interactive
Folium/Leaflet map with per-cell colored circles. Color encodes latency by
default; a layer control lets you switch to throughput or outage rate.

Run:    python3 analysis/03_map.py
"""

import pandas as pd
import folium
from folium.plugins import MarkerCluster
from pathlib import Path

GRID_FILE = Path(__file__).parent.parent / "data" / "route_grid.csv"
OUT_FILE  = Path(__file__).parent.parent / "gh-pages" / "map.html"

# Color scale for latency: green (low) → yellow → red (high)
def latency_color(ms):
    if pd.isna(ms):
        return "#888888"
    if ms < 25:
        return "#1a9641"
    elif ms < 35:
        return "#a6d96a"
    elif ms < 50:
        return "#ffffbf"
    elif ms < 100:
        return "#fdae61"
    elif ms < 200:
        return "#d7191c"
    else:
        return "#7b0000"


def outage_color(rate):
    if pd.isna(rate):
        return "#888888"
    if rate < 0.05:
        return "#1a9641"
    elif rate < 0.15:
        return "#a6d96a"
    elif rate < 0.30:
        return "#fdae61"
    elif rate < 0.50:
        return "#d7191c"
    else:
        return "#7b0000"


def downlink_color(mbps):
    if pd.isna(mbps) or mbps == 0:
        return "#888888"
    if mbps >= 50:
        return "#1a9641"
    elif mbps >= 20:
        return "#a6d96a"
    elif mbps >= 5:
        return "#ffffbf"
    elif mbps >= 1:
        return "#fdae61"
    else:
        return "#d7191c"


def main():
    df = pd.read_csv(GRID_FILE)
    print(f"Loaded {len(df):,} grid cells")

    center_lat = df["lat_cell"].mean()
    center_lon = df["lon_cell"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=11,
        tiles="CartoDB positron",
    )

    # Three separate feature groups so the legend layer control works
    latency_layer   = folium.FeatureGroup(name="Latency (ms)", show=True)
    outage_layer    = folium.FeatureGroup(name="Outage rate", show=False)
    downlink_layer  = folium.FeatureGroup(name="Downlink (Mbps)", show=False)

    for _, row in df.iterrows():
        tooltip = (
            f"<b>Latency:</b> {row['latency_median']:.0f} ms "
            f"(p90: {row['latency_p90']:.0f} ms)<br>"
            f"<b>Downlink:</b> {row['downlink_median_mbps']:.1f} Mbps<br>"
            f"<b>Uplink:</b> {row['uplink_median_mbps']:.1f} Mbps<br>"
            f"<b>Outage rate:</b> {row['outage_rate']*100:.1f}%"
        )
        if pd.notna(row.get("dominant_outage_cause")):
            tooltip += f"<br><b>Dominant cause:</b> {row['dominant_outage_cause']}"
        tooltip += (
            f"<br><b>Samples:</b> {int(row['n_rows']):,} "
            f"({int(row['n_sessions'])} sessions)"
        )

        kwargs = dict(
            location=[row["lat_cell"], row["lon_cell"]],
            radius=6,
            weight=0,
            fill=True,
            fill_opacity=0.75,
            tooltip=tooltip,
        )

        folium.CircleMarker(fill_color=latency_color(row["latency_median"]),  **kwargs).add_to(latency_layer)
        folium.CircleMarker(fill_color=outage_color(row["outage_rate"]),      **kwargs).add_to(outage_layer)
        folium.CircleMarker(fill_color=downlink_color(row["downlink_median_mbps"]), **kwargs).add_to(downlink_layer)

    latency_layer.add_to(m)
    outage_layer.add_to(m)
    downlink_layer.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    OUT_FILE.parent.mkdir(exist_ok=True)
    m.save(str(OUT_FILE))
    print(f"Map saved to {OUT_FILE}")
    print("Open in browser: file://" + str(OUT_FILE.resolve()))


if __name__ == "__main__":
    main()
