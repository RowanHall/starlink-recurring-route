#!/usr/bin/env python3
"""
Step 1: Merge all session data into a single flat dataset.

Joins POSE_TRACK (GPS) + GRPC_STATUS (telemetry) by nearest timestamp,
then marks each row with its outage cause (if any) from GRPC_OUTAGES.

Output: data/all_sessions.parquet
Run:    python3 analysis/01_build_dataset.py
"""

import glob
import sys
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "pacheedaht"
OUT_FILE = Path(__file__).parent.parent / "data" / "all_sessions.parquet"

# Columns to keep from GRPC_STATUS (drop raw quaternions, internal flags)
STATUS_COLS = [
    "ts", "pop_ping_latency_ms", "pop_ping_drop_rate",
    "downlink_throughput_bps", "uplink_throughput_bps",
    "signal_quality", "obstruction_currently_obstructed",
    "obstruction_fraction_obstructed", "gps_valid", "gps_sats",
    "user_mobility_class", "is_snr_above_noise_floor",
    "alert_lower_signal_than_predicted", "dish_uptime",
]


def load_window(window_dir: Path, session_meta: dict) -> pd.DataFrame | None:
    pose_file = window_dir / "POSE_TRACK-data.csv"
    status_files = list((window_dir / "grpc").glob("GRPC_STATUS-*.csv"))
    outage_files = list((window_dir / "grpc").glob("GRPC_OUTAGES-*.csv"))

    if not pose_file.exists() or not status_files:
        return None

    pose = pd.read_csv(pose_file)
    pose = pose.rename(columns={"timestamp": "ts"})
    pose["ts"] = pd.to_datetime(pose["ts"], utc=True)
    pose = pose.sort_values("ts")

    status = pd.read_csv(status_files[0])
    status = status.rename(columns={"timestamp": "ts"})
    status["ts"] = pd.to_datetime(status["ts"], utc=True)
    status = status.sort_values("ts")

    # Keep only recognised columns that exist in this file
    keep = [c for c in STATUS_COLS if c in status.columns]
    status = status[keep]

    # Join GPS onto telemetry rows by nearest timestamp (tolerance 2 s)
    merged = pd.merge_asof(
        status,
        pose[["ts", "latitude", "longitude", "altitude",
              "tilt_angle", "boresight_azimuth", "boresight_elevation"]],
        on="ts",
        direction="nearest",
        tolerance=pd.Timedelta("2s"),
    )

    # Mark each row with the active outage cause, if any
    merged["outage_cause"] = pd.NA
    if outage_files:
        outages = pd.read_csv(outage_files[0])
        outages = outages[outages["start_timestamp_ns_unix"].notna()].copy()
        if not outages.empty:
            outages["outage_start"] = pd.to_datetime(
                outages["start_timestamp_ns_unix"].astype(float) / 1e9,
                unit="s", utc=True,
            )
            outages["outage_end"] = outages["outage_start"] + pd.to_timedelta(
                outages["duration_s"].fillna(0).astype(float), unit="s"
            )
            for _, row in outages.iterrows():
                mask = (merged["ts"] >= row["outage_start"]) & \
                       (merged["ts"] < row["outage_end"])
                merged.loc[mask, "outage_cause"] = row["cause"]

    merged["session_id"] = session_meta["session_id"]
    merged["session_date"] = session_meta["session_date"]
    merged["session_hour"] = session_meta["session_hour"]
    merged["window_id"] = window_dir.name

    return merged.dropna(subset=["latitude", "longitude"])


def main():
    session_dirs = sorted(DATA_DIR.glob("session-*/"))
    if not session_dirs:
        sys.exit(f"No sessions found in {DATA_DIR}")

    all_frames = []
    skipped = 0

    for session_dir in session_dirs:
        parts = session_dir.name.split("-")  # session-YYYY-MM-DD-HH-MM-SS
        meta = {
            "session_id": session_dir.name,
            "session_date": f"{parts[1]}-{parts[2]}-{parts[3]}",
            "session_hour": int(parts[4]),
        }

        for window_dir in sorted(d for d in session_dir.iterdir() if d.is_dir()):
            try:
                df = load_window(window_dir, meta)
                if df is not None and not df.empty:
                    all_frames.append(df)
                    print(f"  OK   {window_dir.relative_to(DATA_DIR)}  ({len(df):,} rows)")
                else:
                    skipped += 1
                    print(f"  SKIP {window_dir.relative_to(DATA_DIR)}  (missing files)")
            except Exception as exc:
                skipped += 1
                print(f"  ERR  {window_dir.relative_to(DATA_DIR)}  ({exc})")

    if not all_frames:
        sys.exit("No data loaded — check DATA_DIR path.")

    combined = pd.concat(all_frames, ignore_index=True)
    combined["downlink_mbps"] = combined["downlink_throughput_bps"] / 1e6
    combined["uplink_mbps"] = combined["uplink_throughput_bps"] / 1e6
    combined["is_outage"] = combined["outage_cause"].notna()

    OUT_FILE.parent.mkdir(exist_ok=True)
    combined.to_parquet(OUT_FILE, index=False)

    print(f"\nDone: {len(all_frames)} windows loaded, {skipped} skipped")
    print(f"Total rows: {len(combined):,}")
    print(f"Output:     {OUT_FILE}")


if __name__ == "__main__":
    main()
