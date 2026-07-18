"""Generate conformer-ensemble DBSTEP steric descriptors for v4.4.

The available SMILES describe product scaffolds, not transition states or the
NHP-ether precursors. Values are therefore explicitly labelled product-scaffold
3D proxies and are never represented as experimental or DFT geometries.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path

import numpy as np
import pandas as pd
import dbstep.Dbstep as db
from rdkit import Chem, rdBase
from rdkit.Chem import AllChem

from chemistry_features import locate_product_proxy_reaction_centre


SEMANTICS = "rdkit_etkdgv3_mmff_or_uff_product_scaffold_proxy_not_transition_state"


def optimized_conformers(molecule: Chem.Mol, seed: int, count: int) -> tuple[Chem.Mol, list[tuple[int, float]], str]:
    mol_h = Chem.AddHs(molecule)
    params = AllChem.ETKDGv3()
    params.randomSeed = seed
    params.pruneRmsThresh = 0.25
    params.useSmallRingTorsions = True
    params.useMacrocycleTorsions = True
    conformer_ids = list(AllChem.EmbedMultipleConfs(mol_h, numConfs=count, params=params))
    if not conformer_ids:
        raise ValueError("RDKit could not generate a 3D conformer")
    if AllChem.MMFFHasAllMoleculeParams(mol_h):
        method = "MMFF94"
        optimized = AllChem.MMFFOptimizeMoleculeConfs(mol_h, maxIters=1000)
    else:
        method = "UFF"
        optimized = AllChem.UFFOptimizeMoleculeConfs(mol_h, maxIters=1000)
    ranked = sorted(
        ((conformer_id, float(result[1])) for conformer_id, result in zip(conformer_ids, optimized, strict=True)),
        key=lambda item: (item[1], item[0]),
    )
    return mol_h, ranked, method


def one_conformer(molecule: Chem.Mol, conformer_id: int) -> Chem.Mol:
    single = Chem.Mol(molecule)
    conformer = Chem.Conformer(molecule.GetConformer(conformer_id))
    single.RemoveAllConformers()
    single.AddConformer(conformer, assignId=True)
    return single


def aggregate(values: list[float], prefix: str) -> dict[str, float]:
    array = np.asarray(values, dtype=float)
    return {
        prefix: float(np.median(array)),
        f"{prefix}_min": float(np.min(array)),
        f"{prefix}_max": float(np.max(array)),
        f"{prefix}_range": float(np.max(array) - np.min(array)),
    }


def descriptor_row(record: dict, conformer_count: int, retained_count: int) -> dict:
    molecule = Chem.MolFromSmiles(record["manual_smiles"])
    if molecule is None:
        raise ValueError(f"invalid SMILES for {record['id']}")
    centre = locate_product_proxy_reaction_centre(molecule)
    seed = 440000 + sum(ord(character) for character in str(record["id"]))
    mol_h, ranked, force_field = optimized_conformers(molecule, seed, conformer_count)
    selected = ranked[: min(retained_count, len(ranked))]
    measurements: dict[str, list[float]] = {"B1": [], "B5": [], "L": [], "buried": [], "volume": []}
    for conformer_id, _ in selected:
        single = one_conformer(mol_h, conformer_id)
        result = db.dbstep(
            single,
            atom1=centre.centre_atom_index + 1,
            atom2=centre.aryl_attachment_index + 1,
            sterimol=True,
            volume=True,
            measure="classic",
            quiet=True,
            verbose=False,
            commandline=False,
        )
        measurements["B1"].append(float(result.Bmin))
        measurements["B5"].append(float(result.Bmax))
        measurements["L"].append(float(result.L))
        measurements["buried"].append(float(result.bur_vol))
        measurements["volume"].append(float(AllChem.ComputeMolVolume(single)))

    return {
        "id": record["id"],
        "dbstep_version": importlib.metadata.version("dbstep"),
        "rdkit_version": rdBase.rdkitVersion,
        "conformers_generated": len(ranked),
        "conformers_retained": len(selected),
        "force_field": force_field,
        "lowest_energy": float(selected[0][1]),
        "retained_energy_window": float(selected[-1][1] - selected[0][1]),
        **aggregate(measurements["B1"], "substrate_B1"),
        **aggregate(measurements["B5"], "substrate_B5"),
        **aggregate(measurements["L"], "substrate_L"),
        **aggregate(measurements["buried"], "substrate_buried_volume_pct"),
        **aggregate(measurements["volume"], "substrate_volume"),
        "ligand_B1": "",
        "ligand_B5": "",
        "ligand_L": "",
        "ligand_steric_status": "not_computed_l1_structure_not_machine_readable_in_source_data",
        "axis_definition": "product nitrile-bearing sp3 carbon to aryl attachment atom",
        "axis_directly_aromatic": int(centre.axis_directly_aromatic),
        "descriptor_semantics": SEMANTICS,
        "source_url": "https://github.com/patonlab/DBSTEP",
        "source_doi": "10.5281/zenodo.4702097",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--audit-json", type=Path)
    parser.add_argument("--conformers", type=int, default=12)
    parser.add_argument("--retain", type=int, default=5)
    args = parser.parse_args()
    if args.conformers < 1 or args.retain < 1:
        raise ValueError("conformer counts must be positive")

    data = pd.read_csv(args.input)
    rows = [
        descriptor_row(record, args.conformers, args.retain)
        for record in data.to_dict(orient="records")
    ]
    output = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    audit = {
        "status": "PASS",
        "rows": len(output),
        "dbstep_version": importlib.metadata.version("dbstep"),
        "rdkit_version": rdBase.rdkitVersion,
        "semantics": SEMANTICS,
        "ligand_status": "not computed because L1 has no machine-readable structure in the audited source table",
        "missing_training_descriptors": int(
            output[["substrate_B1", "substrate_B5", "substrate_L", "substrate_volume"]].isna().sum().sum()
        ),
    }
    if args.audit_json:
        args.audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.audit_json.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
