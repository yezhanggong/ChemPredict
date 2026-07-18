"""Evaluate external mechanism-gate fixtures and write an auditable result table."""

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
    parser.add_argument("artifact", type=Path)
    parser.add_argument("cases", type=Path)
    parser.add_argument("scope", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    cases = pd.read_csv(args.cases).fillna("")
    scope = pd.read_csv(args.scope)
    control = scope[scope["id"] == "2d"].iloc[0].to_dict()
    applicability = artifact["applicability"]
    rows = []
    for case in cases.to_dict(orient="records"):
        changes = [value for value in str(case["condition_changes"]).split("|") if value]
        result = gate_check(
            control,
            case["precursor_type"],
            case["radical_class"],
            changes,
            reaction_family=case["reaction_family"],
            gate_config=applicability["gate_config"],
            applicability=applicability,
        )
        rows.append(
            {
                **case,
                "actual_decision": result.status,
                "pass": result.status == case["expected_decision"],
                "distance": result.distance,
                "reasons": " | ".join(result.reasons),
            }
        )
    output = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(output[["case_id", "expected_decision", "actual_decision", "pass"]].to_string(index=False))
    if not output["pass"].all():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
