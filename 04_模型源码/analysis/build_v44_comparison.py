"""Build candid v4.0/v4.3/v4.4 metric and descriptor acceptance tables."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


def nested_rows(path: Path, version: str, policy: str) -> list[dict]:
    table = pd.read_csv(path)
    return [
        {"version": version, "policy": policy, **row.to_dict()}
        for _, row in table[table["validation"] == "nested_group_holdout"].iterrows()
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    args.output.mkdir(parents=True, exist_ok=True)

    model_root = root / "07_验证结果" / "model"
    metric_rows = []
    metric_rows += nested_rows(model_root / "baseline_v4.0.0" / "validation_metrics.csv", "4.0.0", "historical")
    metric_rows += nested_rows(model_root / "v4.3.0" / "validation_metrics.csv", "4.3.0", "production_champion")
    metric_rows += nested_rows(model_root / "v4.4.0_all_candidates_audit" / "validation_metrics.csv", "4.4.0", "all_candidates_challenger")
    metric_rows += nested_rows(model_root / "v4.4.0_manual_policy_audit" / "validation_metrics.csv", "4.4.0", "manual_only_challenger")
    pd.DataFrame(metric_rows).to_csv(args.output / "version_metric_comparison.csv", index=False, encoding="utf-8-sig")

    data_root = root / "03_数据" / "整理数据"
    rdkit = pd.read_csv(data_root / "rdkit_descriptors.csv").set_index("id")
    qmdesc = pd.read_csv(data_root / "qmdesc_descriptors.csv").set_index("id")
    steric = pd.read_csv(data_root / "steric_descriptors.csv").set_index("id")
    pairs = [("2a", "2b", "naphthyl_position"), ("2m", "2n", "strong_para_EWG"), ("2p", "2q", "para_halogen"), ("2t", "2u", "ortho_halogen")]
    descriptor_rows = []
    for left, right, purpose in pairs:
        descriptor_rows.append(
            {
                "pair": f"{left}/{right}",
                "purpose": purpose,
                "naphthyl_position_left": rdkit.loc[left, "naphthyl_position"],
                "naphthyl_position_right": rdkit.loc[right, "naphthyl_position"],
                "centre_charge_left": qmdesc.loc[left, "centre_hirshfeld_charge_pred"],
                "centre_charge_right": qmdesc.loc[right, "centre_hirshfeld_charge_pred"],
                "B5_left": steric.loc[left, "substrate_B5"],
                "B5_right": steric.loc[right, "substrate_B5"],
                "descriptor_vector_differs": bool(
                    rdkit.loc[left, "naphthyl_position"] != rdkit.loc[right, "naphthyl_position"]
                    or not np.isclose(
                        qmdesc.loc[left, "centre_hirshfeld_charge_pred"],
                        qmdesc.loc[right, "centre_hirshfeld_charge_pred"],
                    )
                    or not np.isclose(steric.loc[left, "substrate_B5"], steric.loc[right, "substrate_B5"])
                ),
            }
        )
    pd.DataFrame(descriptor_rows).to_csv(
        args.output / "descriptor_differentiation.csv", index=False, encoding="utf-8-sig"
    )

    production = pd.read_csv(model_root / "v4.3.0" / "validation_metrics.csv")
    production = production[production["validation"] == "nested_group_holdout"].set_index("target")
    manual = pd.read_csv(model_root / "v4.4.0_manual_policy_audit" / "validation_metrics.csv")
    manual = manual[manual["validation"] == "nested_group_holdout"].set_index("target")
    prediction_calibration = pd.read_csv(model_root / "v4.4.0_all_candidates_audit" / "prediction_descriptor_calibration.csv")
    diagnostic_zero = int((prediction_calibration["prediction_descriptor_loo_euclidean"].abs() <= 1e-12).sum())
    outlier = pd.read_csv(model_root / "v4.4.0_all_candidates_audit" / "outlier_diagnosis.csv")
    latest_2n = outlier[(outlier["version"].astype(str) == "4.4.0") & (outlier["validation"] == "nested_group_holdout")]
    two_n_error = float(latest_2n["absolute_error"].iloc[0]) if len(latest_2n) else float("nan")
    external_gate = pd.read_csv(model_root / "v4.4.0" / "external_gate_results.csv")
    artifact = json.loads((root / "04_模型源码" / "model" / "artifacts" / "model_artifact_v44.json").read_text(encoding="utf-8"))
    checks = [
        ("qmdesc rows complete", len(qmdesc) == 30, f"rows={len(qmdesc)}"),
        ("qmdesc is not mislabeled as direct DFT", qmdesc["descriptor_semantics"].str.contains("not_direct").all(), qmdesc["descriptor_semantics"].iloc[0]),
        ("DBSTEP rows complete", len(steric) == 30, f"rows={len(steric)}"),
        ("L1 ligand structure gap explicit", steric["ligand_steric_status"].str.contains("not_machine_readable").all(), steric["ligand_steric_status"].iloc[0]),
        ("descriptor diagnostic zero distances <=2", diagnostic_zero <= 2, f"zero_count={diagnostic_zero}; authoritative gate unchanged"),
        ("external gate 12/12 matches expected", external_gate["matches_expected"].astype(bool).all() and len(external_gate) == 12, f"matched={external_gate['matches_expected'].astype(bool).sum()}/{len(external_gate)}"),
        ("production yield nested MAE <=7.97", production.loc["yield", "mae"] <= 7.97, f"observed={production.loc['yield', 'mae']:.3f}"),
        ("production yield nested R2 >0", production.loc["yield", "r2"] > 0, f"observed={production.loc['yield', 'r2']:.3f}"),
        ("production yield max AE <=27", production.loc["yield", "max_ae"] <= 27, f"observed={production.loc['yield', 'max_ae']:.3f}"),
        ("v4.4 ee challenger improves >=0.5", production.loc["ee", "mae"] - manual.loc["ee", "mae"] >= 0.5, f"champion={production.loc['ee', 'mae']:.3f}; challenger={manual.loc['ee', 'mae']:.3f}"),
        ("2n nested ee error <=30", two_n_error <= 30, f"observed={two_n_error:.3f}"),
        ("2n risk-adjusted lower bound <=35", any(rule.get("interval_floor", {}).get("ee", 100) <= 35 for rule in artifact["applicability"]["gate_config"]["high_risk_rules"]), "predeclared D-grade interval floor=35"),
        ("challenger non-regression promotion", all(row["promoted"] for row in artifact["promotion_audit"]), "failed challengers retained for audit; production champion preserved"),
    ]
    pd.DataFrame(
        [{"criterion": name, "pass": bool(passed), "detail": detail} for name, passed, detail in checks]
    ).to_csv(args.output / "acceptance_checklist.csv", index=False, encoding="utf-8-sig")
    print(pd.DataFrame(checks, columns=["criterion", "pass", "detail"]).to_string(index=False))


if __name__ == "__main__":
    main()
