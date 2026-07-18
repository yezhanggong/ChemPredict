"""Infer a conservative precursor/radical class from an NHP-ether SMILES."""

from __future__ import annotations

import argparse
import json

from rdkit import Chem


def infer(smiles: str) -> dict:
    molecule = Chem.MolFromSmiles(smiles)
    if molecule is None:
        return {"status": "invalid_smiles", "precursor_type": "unknown", "radical_class": "unknown"}
    candidates = []
    for oxygen in molecule.GetAtoms():
        if oxygen.GetAtomicNum() != 8:
            continue
        nitrogen_neighbours = [atom for atom in oxygen.GetNeighbors() if atom.GetAtomicNum() == 7]
        carbon_neighbours = [atom for atom in oxygen.GetNeighbors() if atom.GetAtomicNum() == 6]
        for nitrogen in nitrogen_neighbours:
            carbonyl_neighbours = sum(
                any(
                    bond.GetBondType() == Chem.BondType.DOUBLE and bond.GetOtherAtom(atom).GetAtomicNum() == 8
                    for bond in atom.GetBonds()
                )
                for atom in nitrogen.GetNeighbors()
                if atom.GetAtomicNum() == 6
            )
            if carbonyl_neighbours < 2:
                continue
            candidates.extend(carbon_neighbours)
    if not candidates:
        return {
            "status": "no_nhp_ether_pattern",
            "precursor_type": "not_nhp_ether",
            "radical_class": "unknown",
        }
    centre = candidates[0]
    aromatic_neighbours = sum(atom.GetIsAromatic() for atom in centre.GetNeighbors())
    total_hydrogens = int(centre.GetTotalNumHs())
    if total_hydrogens == 1 and aromatic_neighbours >= 1:
        return {
            "status": "inferred",
            "precursor_type": "secondary_benzylic_nhp_ether",
            "radical_class": "carbon_aryl_benzylic",
            "centre_atom_index": centre.GetIdx(),
            "confidence": "substructure_rule",
        }
    if total_hydrogens == 0:
        precursor = "tertiary_nhp_ether"
    elif total_hydrogens >= 2:
        precursor = "primary_nhp_ether"
    else:
        precursor = "other_nhp_ether"
    return {
        "status": "inferred_outside_target",
        "precursor_type": precursor,
        "radical_class": "carbon_aryl_benzylic" if aromatic_neighbours else "non_benzylic",
        "centre_atom_index": centre.GetIdx(),
        "confidence": "substructure_rule",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("smiles")
    args = parser.parse_args()
    print(json.dumps(infer(args.smiles), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
