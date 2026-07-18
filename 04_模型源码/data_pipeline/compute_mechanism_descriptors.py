"""Compute reproducible structure and reaction-centre proxy descriptors.

These descriptors are inexpensive 2D cheminformatics quantities. Gasteiger
charges are empirical charge proxies, not DFT/NBO charges, and the output labels
make that limitation explicit so they cannot be misrepresented as quantum data.
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

import pandas as pd
from rdkit import Chem, rdBase
from rdkit.Chem import AllChem, Crippen, Descriptors, Lipinski, rdMolDescriptors


def nitrile_pairs(molecule: Chem.Mol) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    for bond in molecule.GetBonds():
        if bond.GetBondType() != Chem.BondType.TRIPLE:
            continue
        first, second = bond.GetBeginAtom(), bond.GetEndAtom()
        if {first.GetAtomicNum(), second.GetAtomicNum()} != {6, 7}:
            continue
        carbon = first if first.GetAtomicNum() == 6 else second
        nitrogen = second if carbon is first else first
        pairs.append((carbon.GetIdx(), nitrogen.GetIdx()))
    return pairs


def reaction_centre(molecule: Chem.Mol) -> tuple[int, int]:
    candidates: list[tuple[int, int, int]] = []
    for nitrile_carbon, _ in nitrile_pairs(molecule):
        carbon = molecule.GetAtomWithIdx(nitrile_carbon)
        for neighbour in carbon.GetNeighbors():
            if neighbour.GetAtomicNum() == 7:
                continue
            score = 0
            if not neighbour.GetIsAromatic():
                score += 3
            if neighbour.GetHybridization() == Chem.HybridizationType.SP3:
                score += 2
            if any(atom.GetIsAromatic() for atom in neighbour.GetNeighbors()):
                score += 2
            candidates.append((score, neighbour.GetIdx(), nitrile_carbon))
    if not candidates:
        raise ValueError("No product nitrile reaction centre could be identified")
    _, centre, nitrile_carbon = max(candidates)
    return centre, nitrile_carbon


def finite_charge(atom: Chem.Atom) -> float:
    value = float(atom.GetProp("_GasteigerCharge"))
    return value if math.isfinite(value) else 0.0


def local_environment(molecule: Chem.Mol, centre_index: int) -> dict[str, float]:
    distances = Chem.GetDistanceMatrix(molecule)
    centre = molecule.GetAtomWithIdx(centre_index)
    hetero_distances = [
        distances[centre_index, atom.GetIdx()]
        for atom in molecule.GetAtoms()
        if atom.GetAtomicNum() not in {1, 6} and atom.GetIdx() != centre_index
    ]
    radius_two = [
        atom for atom in molecule.GetAtoms()
        if atom.GetIdx() != centre_index and distances[centre_index, atom.GetIdx()] <= 2
    ]
    return {
        "centre_heavy_degree": float(sum(atom.GetAtomicNum() > 1 for atom in centre.GetNeighbors())),
        "centre_aromatic_neighbours": float(sum(atom.GetIsAromatic() for atom in centre.GetNeighbors())),
        "centre_radius2_atomic_number_sum": float(sum(atom.GetAtomicNum() for atom in radius_two)),
        "centre_radius2_heavy_count": float(sum(atom.GetAtomicNum() > 1 for atom in radius_two)),
        "min_hetero_topological_distance": float(min(hetero_distances) if hetero_distances else 99.0),
    }


def calculate(record: dict) -> dict:
    molecule = Chem.MolFromSmiles(str(record["manual_smiles"]))
    if molecule is None:
        raise ValueError(f"Invalid SMILES for {record['id']}: {record['manual_smiles']}")
    centre_index, nitrile_carbon_index = reaction_centre(molecule)
    AllChem.ComputeGasteigerCharges(molecule, nIter=24, throwOnParamFailure=True)
    crippen = Crippen._GetAtomContribs(molecule)
    centre = molecule.GetAtomWithIdx(centre_index)
    nitrile_carbon = molecule.GetAtomWithIdx(nitrile_carbon_index)
    aromatic_neighbours = [atom for atom in centre.GetNeighbors() if atom.GetIsAromatic()]
    aryl_charge = finite_charge(aromatic_neighbours[0]) if aromatic_neighbours else 0.0
    charges = [finite_charge(atom) for atom in molecule.GetAtoms()]
    local = local_environment(molecule, centre_index)
    return {
        "id": record["id"],
        "descriptor_engine": f"RDKit {rdBase.rdkitVersion}",
        "descriptor_semantics": "2D_empirical_proxies_not_quantum_chemistry",
        "canonical_smiles": Chem.MolToSmiles(molecule, canonical=True),
        "reaction_centre_atom_index": centre_index,
        "nitrile_count": len(nitrile_pairs(molecule)),
        "gasteiger_centre_charge": finite_charge(centre),
        "gasteiger_nitrile_c_charge": finite_charge(nitrile_carbon),
        "gasteiger_aryl_attachment_charge": aryl_charge,
        "gasteiger_max_abs_charge": max(abs(value) for value in charges),
        "centre_crippen_logp_contrib": float(crippen[centre_index][0]),
        "centre_crippen_mr_contrib": float(crippen[centre_index][1]),
        "mol_logp": float(Crippen.MolLogP(molecule)),
        "mol_mr": float(Crippen.MolMR(molecule)),
        "mol_tpsa": float(rdMolDescriptors.CalcTPSA(molecule)),
        "mol_fraction_csp3": float(rdMolDescriptors.CalcFractionCSP3(molecule)),
        "mol_rotatable_bonds": float(Lipinski.NumRotatableBonds(molecule)),
        "mol_bertz_complexity": float(Descriptors.BertzCT(molecule)),
        "mol_heavy_atoms": float(molecule.GetNumHeavyAtoms()),
        "mol_heteroatoms": float(rdMolDescriptors.CalcNumHeteroatoms(molecule)),
        **local,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    rows = [calculate(record) for record in data.to_dict(orient="records")]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"RDKit {rdBase.rdkitVersion}: wrote {len(rows)} rows to {args.output}")


if __name__ == "__main__":
    main()
