"""Attach guarded group-aware intervals to the promoted production artifact."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


def finite_sample_quantile(values: np.ndarray, coverage: float) -> float:
    ordered = np.sort(np.asarray(values, dtype=float))
    rank = min(len(ordered), math.ceil((len(ordered) + 1) * coverage))
    return float(ordered[rank - 1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    parser.add_argument("--coverage", type=float, default=0.90)
    parser.add_argument("--minimum-group-size", type=int, default=4)
    args = parser.parse_args()

    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    table = pd.read_csv(args.predictions)
    table = table[table["validation"] == "nested_group_holdout"].copy()
    output_rows: list[dict] = []

    for target, target_rows in table.groupby("target"):
        residual = np.abs(target_rows["observed"].to_numpy() - target_rows["predicted"].to_numpy())
        global_width = finite_sample_quantile(residual, args.coverage)
        empirical_q80 = float(np.quantile(residual, 0.80, method="higher"))
        groups: dict[str, dict] = {}
        for group, group_rows in target_rows.groupby("scope_group"):
            group_residual = np.abs(
                group_rows["observed"].to_numpy() - group_rows["predicted"].to_numpy()
            )
            raw_width = finite_sample_quantile(group_residual, args.coverage)
            eligible = len(group_rows) >= args.minimum_group_size and raw_width < global_width
            selected_width = raw_width if eligible else global_width
            source = "group" if eligible else "global_fallback"
            groups[str(group)] = {
                "n": int(len(group_rows)),
                "raw_half_width": raw_width,
                "selected_half_width": selected_width,
                "source": source,
            }
            output_rows.append(
                {
                    "target": target,
                    "scope_group": group,
                    "n": len(group_rows),
                    "mae": float(group_residual.mean()),
                    "raw_half_width": raw_width,
                    "selected_half_width": selected_width,
                    "global_half_width": global_width,
                    "interval_source": source,
                    "minimum_group_size": args.minimum_group_size,
                }
            )
        artifact["models"][target]["cross_conformal"].update(
            {
                "group_calibration": groups,
                "group_minimum_n": args.minimum_group_size,
                "empirical_q80_half_width": empirical_q80,
                "group_interval_policy": "Use a narrower family interval only when n>=4; otherwise use global fallback.",
            }
        )

    args.artifact.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    args.output_csv.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(output_rows).to_csv(args.output_csv, index=False, encoding="utf-8-sig")
    print(pd.DataFrame(output_rows).to_string(index=False))


if __name__ == "__main__":
    main()
