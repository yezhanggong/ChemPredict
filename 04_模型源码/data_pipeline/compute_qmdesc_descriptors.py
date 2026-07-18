"""Compute qmdesc ML-predicted atomic and bond descriptors for v4.4.

qmdesc predicts targets learned from B3LYP/def2-SVP calculations. These values
are not direct DFT calculations and are labelled accordingly in every row.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from rdkit import Chem, rdBase

from chemistry_features import locate_product_proxy_reaction_centre


SEMANTICS = "ml_predicted_b3lyp_def2svp_targets_not_direct_quantum_chemistry"


def trusted_qmdesc_handler():
    """Load qmdesc's official PyPI checkpoint with an explicit trust boundary.

    qmdesc 1.0.6 predates PyTorch 2.6, where torch.load changed its default to
    weights_only=True. The wheel's bundled checkpoint includes argparse.Namespace,
    so it requires the legacy pickle loader. The package version and wheel hash are
    pinned in the environment lock and third-party notice.
    """

    original_load = torch.load

    def compatibility_load(*args, **kwargs):
        kwargs.setdefault("weights_only", False)
        return original_load(*args, **kwargs)

    torch.load = compatibility_load
    try:
        from qmdesc import ReactivityDescriptorHandler

        return ReactivityDescriptorHandler()
    finally:
        torch.load = original_load


def descriptor_row(record: dict, handler) -> dict:
    molecule = Chem.MolFromSmiles(record["manual_smiles"])
    if molecule is None:
        raise ValueError(f"invalid SMILES for {record['id']}")
    centre = locate_product_proxy_reaction_centre(molecule)
    prediction = handler.predict(record["manual_smiles"])
    atom_count_with_h = Chem.AddHs(molecule).GetNumAtoms()
    bond_count_with_h = Chem.AddHs(molecule).GetNumBonds()
    for name in ("partial_charge", "fukui_neu", "fukui_elec", "NMR"):
        if len(prediction[name]) != atom_count_with_h:
            raise ValueError(f"{record['id']} qmdesc atom count mismatch for {name}")
    for name in ("bond_order", "bond_length"):
        if len(prediction[name]) != bond_count_with_h:
            raise ValueError(f"{record['id']} qmdesc bond count mismatch for {name}")

    return {
        "id": record["id"],
        "qmdesc_version": importlib.metadata.version("qmdesc"),
        "torch_version": torch.__version__,
        "rdkit_version": rdBase.rdkitVersion,
        "reaction_centre_atom_index": centre.centre_atom_index,
        "axis_directly_aromatic": int(centre.axis_directly_aromatic),
        "centre_hirshfeld_charge_pred": float(prediction["partial_charge"][centre.centre_atom_index]),
        "centre_fukui_nucleophilic_pred": float(prediction["fukui_neu"][centre.centre_atom_index]),
        "centre_fukui_electrophilic_pred": float(prediction["fukui_elec"][centre.centre_atom_index]),
        "centre_nmr_shielding_pred": float(prediction["NMR"][centre.centre_atom_index]),
        "centre_cn_bond_order_pred": float(prediction["bond_order"][centre.centre_nitrile_bond_index]),
        "centre_cn_bond_length_pred": float(prediction["bond_length"][centre.centre_nitrile_bond_index]),
        "centre_aryl_bond_order_pred": float(prediction["bond_order"][centre.centre_aryl_bond_index]),
        "centre_aryl_bond_length_pred": float(prediction["bond_length"][centre.centre_aryl_bond_index]),
        "molecule_charge_abs_mean_pred": float(np.mean(np.abs(prediction["partial_charge"]))),
        "molecule_fukui_neu_max_pred": float(np.max(prediction["fukui_neu"])),
        "molecule_fukui_elec_max_pred": float(np.max(prediction["fukui_elec"])),
        "descriptor_semantics": SEMANTICS,
        "model_target_level": "B3LYP/def2-SVP as documented by qmdesc",
        "source_url": "https://qmdesc.readthedocs.io/en/latest/",
        "source_doi": "10.1039/D0SC04823J",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--audit-json", type=Path)
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    handler = trusted_qmdesc_handler()
    rows = [descriptor_row(record, handler) for record in data.to_dict(orient="records")]
    output = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")

    audit = {
        "status": "PASS",
        "rows": len(output),
        "qmdesc_version": importlib.metadata.version("qmdesc"),
        "torch_version": torch.__version__,
        "semantics": SEMANTICS,
        "missing_numeric_values": int(output.select_dtypes(include=["number"]).isna().sum().sum()),
        "field_correction": (
            "The requested HOMO/LUMO and Mulliken fields are not qmdesc outputs. "
            "The pipeline uses the package's documented Hirshfeld charge, Fukui, NMR, bond-order and bond-length targets."
        ),
    }
    if args.audit_json:
        args.audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.audit_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
