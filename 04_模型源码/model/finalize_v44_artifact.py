"""Promote v4.4 challengers only when grouped nested validation is non-regressive."""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

import pandas as pd


MODEL_VERSION = "4.4.0"
MINIMUM_MAE_GAIN = 0.30


def nested_metrics(path: Path) -> dict[str, dict[str, float]]:
    table = pd.read_csv(path)
    nested = table[table["validation"] == "nested_group_holdout"]
    return {
        str(row["target"]): {
            name: float(row[name])
            for name in ("mae", "rmse", "median_ae", "max_ae", "bias", "r2", "spearman")
        }
        for _, row in nested.iterrows()
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--champion-artifact", type=Path, required=True)
    parser.add_argument("--challenger-artifact", type=Path, required=True)
    parser.add_argument("--champion-metrics", type=Path, required=True)
    parser.add_argument("--challenger-metrics", type=Path, required=True)
    parser.add_argument("--output-artifact", type=Path, required=True)
    parser.add_argument("--output-decisions", type=Path, required=True)
    args = parser.parse_args()

    champion = json.loads(args.champion_artifact.read_text(encoding="utf-8"))
    challenger = json.loads(args.challenger_artifact.read_text(encoding="utf-8"))
    champion_scores = nested_metrics(args.champion_metrics)
    challenger_scores = nested_metrics(args.challenger_metrics)

    output = deepcopy(challenger)
    output["model_version"] = MODEL_VERSION
    output["generated_with"] = "04_模型源码/model/train_v44.py + finalize_v44_artifact.py"
    output["governance"] = {
        "architecture": "champion_challenger",
        "promotion_rule": (
            "Per target: nested grouped MAE improves by at least 0.30 percentage points, "
            "with non-worse nested RMSE and maximum absolute error."
        ),
        "minimum_mae_gain": MINIMUM_MAE_GAIN,
        "independent_external_validation_available": False,
    }
    output["champion_models"] = deepcopy(champion["models"])
    output["challenger_models"] = deepcopy(challenger["models"])
    output["models"] = {}
    output["fallback_models"] = {}
    output["production_model_version_by_target"] = {}
    decisions: list[dict] = []

    for target in sorted(champion_scores):
        old = champion_scores[target]
        new = challenger_scores[target]
        mae_gain = old["mae"] - new["mae"]
        promoted = (
            mae_gain >= MINIMUM_MAE_GAIN
            and new["rmse"] <= old["rmse"]
            and new["max_ae"] <= old["max_ae"]
        )
        source = "4.4.0_challenger" if promoted else "4.3.0_champion"
        selected_artifact = challenger if promoted else champion
        selected_model = deepcopy(selected_artifact["models"][target])
        selected_model["model_origin_version"] = "4.4.0" if promoted else "4.3.0"
        selected_model["production_selection"] = source
        output["models"][target] = selected_model
        if target in selected_artifact.get("fallback_models", {}):
            output["fallback_models"][target] = deepcopy(selected_artifact["fallback_models"][target])
        output["production_model_version_by_target"][target] = selected_model["model_origin_version"]
        decisions.append(
            {
                "target": target,
                "champion_version": "4.3.0",
                "challenger_version": "4.4.0",
                "champion_nested_mae": old["mae"],
                "challenger_nested_mae": new["mae"],
                "mae_gain_champion_minus_challenger": mae_gain,
                "champion_nested_rmse": old["rmse"],
                "challenger_nested_rmse": new["rmse"],
                "champion_nested_max_ae": old["max_ae"],
                "challenger_nested_max_ae": new["max_ae"],
                "promoted": promoted,
                "production_source": source,
                "reason": (
                    "challenger passed all predeclared promotion criteria"
                    if promoted
                    else "challenger failed one or more predeclared non-regression criteria"
                ),
            }
        )

    output["promotion_audit"] = decisions
    output["production_validation_metrics"] = {
        target: (challenger_scores[target] if row["promoted"] else champion_scores[target])
        for target, row in ((row["target"], row) for row in decisions)
    }
    output["research_only_descriptor_layers"] = {
        "qmdesc": "Integrated and audited; not promoted into production because nested grouped gain was not stable.",
        "dbstep": "Integrated and audited as a product-scaffold conformer proxy; not promoted into production.",
        "xgboost": "Evaluated in the v4.4 challenger search; production promotion remains target-specific.",
    }

    args.output_artifact.parent.mkdir(parents=True, exist_ok=True)
    args.output_decisions.parent.mkdir(parents=True, exist_ok=True)
    args.output_artifact.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(decisions).to_csv(args.output_decisions, index=False, encoding="utf-8-sig")
    print(pd.DataFrame(decisions).to_string(index=False))


if __name__ == "__main__":
    main()
