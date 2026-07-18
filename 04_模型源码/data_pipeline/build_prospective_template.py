"""Build the prospective blind-test ledger with aligned, auditable columns."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import pandas as pd


COLUMNS = [
    "blind_test_id", "batch_id", "category", "candidate_id", "target_product_smiles", "precursor_smiles",
    "scope_group", "gate_status", "gate_grade", "nearest_distance", "predicted_yield_pct", "yield_interval_low",
    "yield_interval_high", "predicted_ee_pct", "ee_interval_low", "ee_interval_high", "model_artifact_sha256",
    "data_snapshot_sha256", "prediction_frozen_at_utc", "prediction_frozen_by", "operator",
    "experiment_started_at_utc", "experiment_date", "replicate_no", "substrate_mmol", "photocatalyst",
    "photocatalyst_mol_pct", "copper_source", "copper_mol_pct", "ligand", "ligand_mol_pct", "tmscn_equiv",
    "p_oet3_equiv", "solvent", "concentration_m", "temperature_c", "light_wavelength_nm",
    "light_rated_power_w", "light_sample_distance_cm", "reaction_time_h", "atmosphere", "water_control",
    "oxygen_control", "actual_yield_pct", "yield_status", "yield_detection_limit_pct", "actual_ee_pct", "ee_status",
    "yield_absolute_error", "ee_absolute_error", "raw_yield_file", "raw_chiral_file", "chiral_column", "mobile_phase",
    "retention_times_min", "peak_areas", "protocol_deviation", "unblinded_at_utc", "unblinded_by", "review_status", "notes",
]


def digest_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.name):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--conditions", type=Path, required=True)
    parser.add_argument("--virtual", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    scope = pd.read_csv(args.scope).set_index("id")
    conditions = pd.read_csv(args.conditions)
    optimized = conditions.loc[conditions["record_id"] == "OPT-01"].iloc[0]
    virtual = pd.read_csv(args.virtual).set_index("id")
    artifact_hash = hashlib.sha256(args.artifact.read_bytes()).hexdigest()
    snapshot_hash = digest_files([args.scope, args.conditions])

    protocol = {
        "substrate_mmol": 0.2,
        "photocatalyst": optimized["photocatalyst"],
        "photocatalyst_mol_pct": optimized["pc_mol_pct"],
        "copper_source": optimized["copper_source"],
        "copper_mol_pct": optimized["cu_mol_pct"],
        "ligand": optimized["ligand"],
        "ligand_mol_pct": optimized["ligand_mol_pct"],
        "tmscn_equiv": 2.0,
        "p_oet3_equiv": 2.0,
        "solvent": optimized["solvent"],
        "concentration_m": 0.1,
        "temperature_c": optimized["temp_c"],
        "light_wavelength_nm": optimized["light_nm"],
        "light_rated_power_w": 6,
        "reaction_time_h": optimized["time_h"],
        "atmosphere": "nitrogen",
        "model_artifact_sha256": artifact_hash,
        "data_snapshot_sha256": snapshot_hash,
        "review_status": "planned",
        "notes": "Protocol fields transcribed from target SI section 4; light-sample distance and water/oxygen measurements must be recorded locally.",
    }

    designs = [
        ("BT-001", "B01", "reference_replicate", "2a", 1),
        ("BT-002", "B02", "reference_replicate", "2a", 2),
        ("BT-003", "B03", "reference_replicate", "2a", 3),
        ("BT-004", "B04", "in_domain_near_neighbor", "V04", 1),
        ("BT-005", "B05", "in_domain_near_neighbor", "V05", 1),
        ("BT-006", "B06", "in_domain_near_neighbor", "V07", 1),
        ("BT-007", "B07", "in_domain_near_neighbor", "V08", 1),
        ("BT-008", "B08", "in_domain_near_neighbor", "V15", 1),
        ("BT-009", "B09", "q90_q95_boundary", "TBD-B01", 1),
        ("BT-010", "B10", "q90_q95_boundary", "TBD-B02", 1),
        ("BT-011", "B11", "q90_q95_boundary", "TBD-B03", 1),
        ("BT-012", "B12", "mechanistic_refusal_control", "TBD-R01", 1),
        ("BT-013", "B13", "mechanistic_refusal_control", "TBD-R02", 1),
    ]
    records: list[dict] = []
    for blind_id, batch_id, category, candidate_id, replicate in designs:
        record = {**protocol, "blind_test_id": blind_id, "batch_id": batch_id, "category": category,
                  "candidate_id": candidate_id, "replicate_no": replicate}
        if candidate_id == "2a":
            known = scope.loc[candidate_id]
            record.update({"target_product_smiles": known["manual_smiles"], "scope_group": known["scope_group"]})
        elif candidate_id in virtual.index:
            candidate = virtual.loc[candidate_id]
            record.update({
                "target_product_smiles": candidate["manual_smiles"], "scope_group": candidate["scope_group"],
                "gate_status": candidate["gate_status"], "gate_grade": candidate["gate_grade"],
                "nearest_distance": candidate["gate_distance"], "predicted_yield_pct": candidate["predicted_yield"],
                "yield_interval_low": candidate["yield_interval_low"], "yield_interval_high": candidate["yield_interval_high"],
                "predicted_ee_pct": candidate["predicted_ee"], "ee_interval_low": candidate["ee_interval_low"],
                "ee_interval_high": candidate["ee_interval_high"],
            })
        records.append(record)
    output = pd.DataFrame(records).reindex(columns=COLUMNS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(output)} blind-test rows with {len(output.columns)} aligned columns.")


if __name__ == "__main__":
    main()
