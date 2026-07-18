"""Create matched-control condition effects and censoring sensitivity tables."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


ANCHORS = {
    "solvent": "SOLV-02",
    "photocatalyst": "PC-01",
    "copper_source": "CU-07",
    "ligand": "LIG-01",
    "temperature": "TEMP-01",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    effects: list[dict] = []
    for axis, anchor_id in ANCHORS.items():
        axis_rows = data[data["screen_axis"] == axis].copy()
        anchor = data[data["record_id"] == anchor_id].iloc[0]
        for _, row in axis_rows.iterrows():
            effects.append(
                {
                    "record_id": row["record_id"],
                    "screen_axis": axis,
                    "candidate": row[axis] if axis != "temperature" else row["temp_c"],
                    "yield_status": row["yield_status"],
                    "yield_pct": row["yield_pct"],
                    "ee_pct": row["ee_pct"],
                    "matched_anchor": anchor_id,
                    "delta_yield_pct": (
                        float(row["yield_pct"] - anchor["yield_pct"])
                        if pd.notna(row["yield_pct"])
                        else np.nan
                    ),
                    "delta_ee_pct": (
                        float(row["ee_pct"] - anchor["ee_pct"])
                        if pd.notna(row["ee_pct"])
                        else np.nan
                    ),
                    "source_table": row["source_table"],
                    "source_pdf_page": row["source_pdf_page"],
                }
            )
    pd.DataFrame(effects).to_csv(
        args.output_dir / "matched_control_effects.csv", index=False, encoding="utf-8-sig"
    )

    sensitivity_rows: list[dict] = []
    rank_axes = ["solvent", "photocatalyst"]
    for assumed_trace in (0.0, 2.0, 5.0):
        for axis in rank_axes:
            subset = data[data["screen_axis"] == axis].copy()
            subset["sensitivity_yield"] = subset["yield_pct"]
            censored = subset["yield_status"].isin(["trace", "not_detected"])
            subset.loc[censored, "sensitivity_yield"] = assumed_trace
            subset = subset.sort_values(
                ["sensitivity_yield", "ee_pct"], ascending=[False, False], na_position="last"
            )
            subset["rank"] = subset["sensitivity_yield"].rank(
                method="min", ascending=False
            ).astype(int)
            for _, row in subset.iterrows():
                sensitivity_rows.append(
                    {
                        "trace_assumption_pct": assumed_trace,
                        "screen_axis": axis,
                        "record_id": row["record_id"],
                        "candidate": row[axis],
                        "yield_used_for_sensitivity": row["sensitivity_yield"],
                        "rank": row["rank"],
                        "original_status": row["yield_status"],
                    }
                )
    sensitivity = pd.DataFrame(sensitivity_rows)
    sensitivity.to_csv(
        args.output_dir / "censoring_sensitivity.csv", index=False, encoding="utf-8-sig"
    )

    checks = []
    for label, record_ids in {
        "50/88 anchor duplicated across S1/S2/S3": ["SOLV-02", "PC-01", "CU-07"],
        "90/90 anchor duplicated across S3/S4/S5": ["CU-05", "LIG-01", "TEMP-01"],
    }.items():
        subset = data[data["record_id"].isin(record_ids)]
        checks.append(
            {
                "check": label,
                "record_ids": ";".join(record_ids),
                "yield_range_pct": float(subset["yield_pct"].max() - subset["yield_pct"].min()),
                "ee_range_pct": float(subset["ee_pct"].max() - subset["ee_pct"].min()),
                "pass": bool(
                    subset["yield_pct"].nunique() == 1 and subset["ee_pct"].nunique() == 1
                ),
            }
        )
    optimized = data[data["record_id"] == "OPT-01"].iloc[0]
    repeat = data[data["record_id"] == "REP-01"].iloc[0]
    checks.append(
        {
            "check": "optimized condition repeat at 0.2 mmol",
            "record_ids": "OPT-01;REP-01",
            "yield_range_pct": abs(float(repeat["yield_pct"] - optimized["yield_pct"])),
            "ee_range_pct": abs(float(repeat["ee_pct"] - optimized["ee_pct"])),
            "pass": bool(
                abs(float(repeat["yield_pct"] - optimized["yield_pct"])) <= 5
                and abs(float(repeat["ee_pct"] - optimized["ee_pct"])) <= 2
            ),
        }
    )
    pd.DataFrame(checks).to_csv(
        args.output_dir / "source_internal_consistency.csv", index=False, encoding="utf-8-sig"
    )
    print(pd.DataFrame(checks).to_string(index=False))


if __name__ == "__main__":
    main()
