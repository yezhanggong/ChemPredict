"""Run the v4.4 mechanism/protocol gate against registered external stress cases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "model"))
from applicability_gate import gate_check  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    cases = pd.read_csv(args.cases).fillna("")
    scope = pd.read_csv(args.scope)
    control = scope[scope["id"] == "2d"].iloc[0].to_dict()
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    applicability = artifact["applicability"]
    config = applicability["gate_config"]
    rows = []
    for case in cases.to_dict(orient="records"):
        result = gate_check(
            control,
            str(case["precursor_type"]),
            str(case["radical_class"]),
            [value for value in str(case["condition_changes"]).split("|") if value],
            reaction_family=str(case["reaction_family"]),
            gate_config=config,
            applicability=applicability,
        )
        rows.append(
            {
                **case,
                "actual_decision": result.status,
                "grade": result.grade,
                "distance": result.distance,
                "rule_ids": "|".join(result.rule_ids),
                "reasons": " | ".join(result.reasons),
                "matches_expected": result.status == str(case["expected_decision"]),
            }
        )
    output = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(output[["case_id", "expected_decision", "actual_decision", "matches_expected"]].to_string(index=False))
    if not output["matches_expected"].all():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
