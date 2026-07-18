"""Fail-fast validation for the curated release data and artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


EXPECTED_SCOPE = {
    "2a": (95, 90), "2b": (84, 90), "2c": (71, 80), "2d": (86, 87),
    "2e": (61, 91), "2f": (74, 85), "2g": (50, 80), "2h": (79, 79),
    "2i": (76, 60), "2j": (70, 92), "2k": (70, 90), "2l": (71, 84),
    "2m": (72, 84), "2n": (70, 41), "2o": (86, 80), "2p": (85, 86),
    "2q": (80, 86), "2r": (80, 90), "2s": (80, 90), "2t": (88, 94),
    "2u": (85, 95), "2v": (85, 91), "2w": (89, 93), "2x": (75, 95),
    "2y": (80, 86), "2z": (70, 75), "3a": (50, 90), "3b": (54, 27),
    "3c": (80, 60), "3d": (80, 19),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--conditions", type=Path, required=True)
    parser.add_argument("--pubchem", type=Path, required=True)
    parser.add_argument("--rdkit", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument(
        "--references",
        type=Path,
        help="Optional local source-document directory. Public releases omit publisher PDFs.",
    )
    parser.add_argument("--mechanism-descriptors", type=Path, required=True)
    parser.add_argument("--condition-descriptors", type=Path, required=True)
    parser.add_argument("--qmdesc", type=Path, required=True)
    parser.add_argument("--steric", type=Path, required=True)
    parser.add_argument("--reaction-systems", type=Path, required=True)
    parser.add_argument("--term-dictionary", type=Path, required=True)
    parser.add_argument("--promotion-decisions", type=Path, required=True)
    parser.add_argument("--external-gate", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    parser.add_argument("--literature-audit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    scope = pd.read_csv(args.scope)
    conditions = pd.read_csv(args.conditions)
    pubchem = pd.read_csv(args.pubchem)
    rdkit = pd.read_csv(args.rdkit)
    mechanism = pd.read_csv(args.mechanism_descriptors)
    condition_descriptors = pd.read_csv(args.condition_descriptors)
    qmdesc = pd.read_csv(args.qmdesc)
    steric = pd.read_csv(args.steric)
    reaction_systems = json.loads(args.reaction_systems.read_text(encoding="utf-8"))
    term_dictionary = json.loads(args.term_dictionary.read_text(encoding="utf-8"))
    promotion_decisions = pd.read_csv(args.promotion_decisions)
    external_gate = pd.read_csv(args.external_gate)
    metrics = pd.read_csv(args.metrics)
    literature_audit = pd.read_csv(args.literature_audit)
    artifact = json.loads(args.artifact.read_text(encoding="utf-8"))
    checks: list[dict] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "pass": bool(passed), "detail": detail})

    check("scope row count", len(scope) == 30, f"observed={len(scope)} expected=30")
    check("scope identifiers unique", scope["id"].nunique() == 30, str(scope["id"].nunique()))
    check("condition identifiers unique", conditions["record_id"].is_unique, str(len(conditions)))
    check(
        "numeric outcomes bounded",
        scope["yield_pct"].between(0, 100).all() and scope["ee_pct"].between(0, 100).all(),
        "yield and ee must be in [0,100]",
    )
    observed = {row.id: (int(row.yield_pct), int(row.ee_pct)) for row in scope.itertuples()}
    mismatches = {key: (EXPECTED_SCOPE[key], observed.get(key)) for key in EXPECTED_SCOPE if observed.get(key) != EXPECTED_SCOPE[key]}
    check("scope transcription fixture", not mismatches, json.dumps(mismatches, ensure_ascii=False))
    unresolved = pubchem[pubchem["pubchem_status"] == "unresolved"]["id"].tolist()
    check("PubChem records resolved", not unresolved, f"unresolved={unresolved}")
    check("RDKit structures present", len(rdkit) == 30 and rdkit["rdkit_canonical_smiles"].notna().all(), f"rows={len(rdkit)}")
    comparison = rdkit.merge(pubchem, on="id", validate="one_to_one")
    registered = comparison[pd.to_numeric(comparison["pubchem_cid"], errors="coerce").fillna(0) > 0]
    formula_mismatches = registered[registered["rdkit_formula"] != registered["pubchem_formula"]]["id"].tolist()
    check(
        "RDKit/PubChem formula cross-check",
        not formula_mismatches and len(registered) >= 27,
        f"registered={len(registered)} mismatches={formula_mismatches}",
    )
    check("artifact training count", artifact["training_count"] == 26, str(artifact["training_count"]))
    check("artifact challenge count", artifact["challenge_count"] == 4, str(artifact["challenge_count"]))
    check("artifact version", artifact["model_version"] == "4.4.0", str(artifact["model_version"]))
    check(
        "mechanism proxies complete and honestly labelled",
        len(mechanism) == 30
        and mechanism["id"].is_unique
        and set(mechanism["descriptor_semantics"]) == {"2D_empirical_proxies_not_quantum_chemistry"},
        f"rows={len(mechanism)} semantics={sorted(mechanism['descriptor_semantics'].unique())}",
    )
    check(
        "condition vectors complete",
        len(condition_descriptors) == 33 and condition_descriptors["record_id"].is_unique,
        f"rows={len(condition_descriptors)} columns={len(condition_descriptors.columns)}",
    )
    qmdesc_required = {
        "centre_hirshfeld_charge_pred",
        "centre_fukui_nucleophilic_pred",
        "centre_fukui_electrophilic_pred",
        "centre_cn_bond_order_pred",
    }
    check(
        "qmdesc predictions complete and honestly labelled",
        len(qmdesc) == 30
        and qmdesc["id"].is_unique
        and qmdesc_required.issubset(qmdesc.columns)
        and qmdesc[list(qmdesc_required)].notna().all().all()
        and set(qmdesc["descriptor_semantics"])
        == {"ml_predicted_b3lyp_def2svp_targets_not_direct_quantum_chemistry"},
        f"rows={len(qmdesc)} semantics={sorted(qmdesc['descriptor_semantics'].unique())}",
    )
    steric_required = {"substrate_B1", "substrate_B5", "substrate_L"}
    check(
        "DBSTEP conformer proxies complete and ligand gap explicit",
        len(steric) == 30
        and steric["id"].is_unique
        and steric_required.issubset(steric.columns)
        and steric[list(steric_required)].notna().all().all()
        and steric["ligand_steric_status"].astype(str).str.contains("not_machine_readable").all(),
        f"rows={len(steric)} ligand_status={sorted(steric['ligand_steric_status'].unique())}",
    )
    quantitative_systems = [row for row in reaction_systems if row["status"] == "quantitative"]
    check(
        "reaction-system registry prevents numerical pooling",
        len(reaction_systems) == 9
        and len(quantitative_systems) == 1
        and quantitative_systems[0]["system_id"] == "nhp_deoxygenative_asymmetric_cyanation"
        and quantitative_systems[0]["quantitative_rows"] == 26
        and quantitative_systems[0]["condition_rows"] == 33,
        f"systems={len(reaction_systems)} quantitative={[row['system_id'] for row in quantitative_systems]}",
    )
    required_terms = set(conditions["solvent"]) | set(conditions["photocatalyst"]) | set(
        conditions["copper_source"]
    ) | set(conditions["ligand"])
    available_terms = {row["key"] for row in term_dictionary}
    check(
        "bilingual chemical dictionary covers condition identities",
        required_terms.issubset(available_terms),
        f"missing={sorted(required_terms - available_terms)} terms={len(term_dictionary)}",
    )
    check(
        "champion-challenger promotion audit complete",
        set(promotion_decisions["target"]) == {"yield", "ee"}
        and not promotion_decisions["promoted"].astype(str).str.lower().eq("true").any()
        and set(artifact["production_model_version_by_target"].values()) == {"4.3.0"},
        promotion_decisions.to_json(orient="records"),
    )
    check(
        "only nonconstant numeric model features retained",
        all(
            feature not in {"benzylic", "hetero_n", "hetero_s", "alpha_carbonyl", "propargyl"}
            for model in artifact["models"].values()
            for feature in model["features"]
        ),
        "active=" + ";".join(sorted({feature for model in artifact["models"].values() for feature in model["features"]})),
    )
    check(
        "all challenge classes refused",
        all(row["final_decision"] == "REFUSE" for row in artifact["challenge_applicability"]),
        json.dumps(artifact["challenge_applicability"], ensure_ascii=False),
    )
    gate_config = artifact["applicability"]["gate_config"]
    check(
        "structured four-part gate present",
        gate_config["allowed_precursor_types"] == ["secondary_benzylic_nhp_ether"]
        and gate_config["allowed_radical_classes"] == ["carbon_aryl_benzylic"]
        and gate_config["max_condition_changes"] == 1
        and bool(gate_config["distance_thresholds"])
        and bool(gate_config["high_risk_rules"]),
        json.dumps(gate_config, ensure_ascii=False),
    )
    loo = artifact["applicability"]["loo_distance_summary"]
    check(
        "training-domain q90 calibration",
        loo["inside_q90_count"] >= 24 and loo["training_count"] == 26,
        f"inside_q90={loo['inside_q90_count']}/{loo['training_count']}",
    )
    check(
        "group-aware interval fallback policy present",
        all(
            model.get("cross_conformal", {}).get("group_minimum_n") == 4
            and bool(model.get("cross_conformal", {}).get("group_calibration"))
            for model in artifact["models"].values()
        ),
        "group minimum n must be 4 for both production targets",
    )
    external_rows = external_gate[external_gate["case_id"].astype(str).str.startswith("EXT-")]
    control_rows = external_gate[external_gate["case_id"].astype(str).str.startswith("CTRL-")]
    check(
        "external gate stress tests",
        len(external_rows) >= 7
        and (external_rows["actual_decision"] == "REFUSE").all()
        and len(control_rows) >= 1
        and (control_rows["actual_decision"] != "REFUSE").all(),
        f"external_refused={(external_rows['actual_decision'] == 'REFUSE').sum()}/{len(external_rows)} controls={len(control_rows)}",
    )
    nested = metrics[metrics["validation"] == "nested_group_holdout"]
    check(
        "nested grouped metrics present",
        set(nested["target"]) == {"yield", "ee"} and nested[["mae", "rmse", "max_ae"]].notna().all().all(),
        nested[["target", "mae", "rmse", "max_ae"]].to_json(orient="records"),
    )
    check(
        "literature corpus human-screened",
        len(literature_audit) >= 40
        and not literature_audit["human_data_role"].astype(str).str.contains("pending", case=False).any()
        and (literature_audit["numeric_training_eligible"].astype(str).str.lower() == "no").all(),
        f"rows={len(literature_audit)} pending={(literature_audit['human_data_role'].astype(str).str.contains('pending', case=False)).sum()}",
    )

    manifest = []
    if args.references:
        for path in sorted(args.references.glob("*")):
            if path.is_file() and not path.name.endswith(".page.png"):
                manifest.append(
                    {"file": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
                )
        check("reference manifest nonempty", len(manifest) >= 8, f"files={len(manifest)}")
    else:
        check(
            "public release uses DOI registry instead of source PDFs",
            True,
            "source-document manifest intentionally omitted",
        )

    result = {
        "status": "PASS" if all(item["pass"] for item in checks) else "FAIL",
        "checks": checks,
        "reference_manifest": manifest,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(pd.DataFrame(checks).to_string(index=False))
    print(f"STATUS={result['status']}")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
