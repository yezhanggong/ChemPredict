"""Score the precomputed offline virtual candidate library."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "model"))

from predict_v43 import predict  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    parser.add_argument("library", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    library = pd.read_csv(args.library)
    rows: list[dict] = []
    for record in library.to_dict(orient="records"):
        result = predict(
            artifact,
            {
                "features": record,
                "precursor_type": "secondary_benzylic_nhp_ether",
                "radical_class": "carbon_aryl_benzylic",
                "reaction_family": "nhp_ether_deoxygenative_asymmetric_cyanation",
                "condition_changes": [],
            },
        )
        row = {
            **record,
            "gate_status": result["status"],
            "gate_grade": result["grade"],
            "gate_distance": result.get("distance"),
            "gate_reasons": " | ".join(result.get("reasons", [])),
        }
        if result.get("prediction_emitted"):
            for target in ("yield", "ee"):
                payload = result["targets"][target]
                row.update(
                    {
                        f"predicted_{target}": payload["point"],
                        f"{target}_interval_low": payload["low"],
                        f"{target}_interval_high": payload["high"],
                        f"{target}_model_source": payload["model_source"],
                    }
                )
        rows.append(row)
    output = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(output[["id", "gate_status", "gate_grade", "predicted_yield", "predicted_ee"]].to_string(index=False))


if __name__ == "__main__":
    main()
