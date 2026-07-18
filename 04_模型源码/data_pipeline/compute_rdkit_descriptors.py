"""Compute reproducible 2D descriptors from the audited manual SMILES column."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from rdkit import Chem, rdBase
from rdkit.Chem import Crippen, Descriptors, Lipinski, rdMolDescriptors

from chemistry_features import discriminating_2d_descriptors, locate_product_proxy_reaction_centre


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    rows: list[dict] = []
    for record in data.to_dict(orient="records"):
        molecule = Chem.MolFromSmiles(record["manual_smiles"])
        if molecule is None:
            raise ValueError(f"Invalid SMILES for {record['id']}: {record['manual_smiles']}")
        centre = locate_product_proxy_reaction_centre(molecule)
        rows.append(
            {
                "id": record["id"],
                "rdkit_version": rdBase.rdkitVersion,
                "rdkit_canonical_smiles": Chem.MolToSmiles(molecule, canonical=True),
                "rdkit_formula": rdMolDescriptors.CalcMolFormula(molecule),
                "rdkit_mw": Descriptors.MolWt(molecule),
                "rdkit_logp": Crippen.MolLogP(molecule),
                "rdkit_mr": Crippen.MolMR(molecule),
                "rdkit_tpsa": rdMolDescriptors.CalcTPSA(molecule),
                "rdkit_fraction_csp3": rdMolDescriptors.CalcFractionCSP3(molecule),
                "rdkit_rotatable": Lipinski.NumRotatableBonds(molecule),
                "rdkit_aromatic_rings": Lipinski.NumAromaticRings(molecule),
                "rdkit_heavy_atoms": molecule.GetNumHeavyAtoms(),
                "rdkit_bertz": Descriptors.BertzCT(molecule),
                "reaction_centre_atom_index": centre.centre_atom_index,
                "product_nitrile_carbon_index": centre.nitrile_carbon_index,
                "aryl_attachment_atom_index": centre.aryl_attachment_index,
                "axis_directly_aromatic": int(centre.axis_directly_aromatic),
                **discriminating_2d_descriptors(molecule, centre),
                "discriminating_descriptor_semantics": (
                    "audited_2d_topology_for_prediction_only_not_authoritative_gate_distance"
                ),
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"RDKit {rdBase.rdkitVersion}: wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
