"""Build condition vectors without implying unsupported cross-reaction transfer.

Continuous solvent values are literature reference values used for similarity and
diagnostics. Categorical catalyst/ligand identities remain explicit one-hot fields.
The target paper varies one factor at a time, so these vectors must not be used to
claim arbitrary multi-factor optimization accuracy.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


# Dielectric constants and Reichardt ET(30) values are room-temperature reference
# values, not measurements from the target reaction. Sources are emitted per row.
REICHARDT_SOURCE = "Reichardt and Welton, Solvents and Solvent Effects in Organic Chemistry, DOI 10.1002/9783527632220"
ET30_CHECK_SOURCE = "ACS Omega 2020, DOI 10.1021/acsomega.9b03880"
SOLVENTS = {
    "CH3CN": ("CC#N", 37.50, 45.6, "tabulated"),
    "DCM": ("ClCCl", 8.93, 40.7, "tabulated"),
    "DCE": ("ClCCCl", 10.36, 41.3, "tabulated"),
    "CHCl3": ("ClC(Cl)Cl", 4.81, 39.1, "tabulated"),
    "PhCl": ("Clc1ccccc1", 5.62, 37.5, "tabulated"),
    "acetone": ("CC(=O)C", 20.70, 42.2, "tabulated"),
    "MTBE": ("COC(C)(C)C", 2.60, 34.7, "secondary_table_pending_primary_confirmation"),
}

PC_CLASS = {
    "fac-Ir(ppy)3": "ir_neutral_cyclometalated",
    "[Ir(dFCF3ppy)2(bpy)]PF6": "ir_cationic_cyclometalated",
    "4CzIPN": "organic_donor_acceptor",
    "Eosin Y": "organic_xanthene",
    "5,7,12,14-Pentacenetetrone": "organic_quinone",
    "9,10-Diphenylanthracene": "organic_hydrocarbon",
    "none": "none",
}

COPPER = {
    "CuBr": (1, "halide", 0),
    "CuCl2": (2, "halide", 0),
    "CuBr2": (2, "halide", 0),
    "CuCl": (1, "halide", 0),
    "CuCN": (1, "cyanide", 1),
    "Cu(CH3CN)4BF4": (1, "labile_nitrile_complex", 0),
    "Cu(CH3CN)4PF6": (1, "labile_nitrile_complex", 0),
}


def add_one_hot(table: pd.DataFrame, column: str, prefix: str) -> pd.DataFrame:
    categories = sorted(table[column].fillna("unknown").astype(str).unique())
    for category in categories:
        safe = "".join(character.lower() if character.isalnum() else "_" for character in category)
        while "__" in safe:
            safe = safe.replace("__", "_")
        table[f"{prefix}_{safe.strip('_')}"] = (table[column].astype(str) == category).astype(int)
    return table


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    records: list[dict] = []
    for row in data.to_dict(orient="records"):
        smiles, dielectric, et30, solvent_quality = SOLVENTS[row["solvent"]]
        oxidation_state, copper_class, contains_cyanide = COPPER[row["copper_source"]]
        records.append(
            {
                **row,
                "temperature_k": float(row["temp_c"]) + 273.15,
                "solvent_smiles": smiles,
                "solvent_dielectric_constant": dielectric,
                "solvent_reichardt_et30_kcal_mol": et30,
                "solvent_descriptor_quality": solvent_quality,
                "solvent_dielectric_source": REICHARDT_SOURCE,
                "solvent_et30_source": f"{REICHARDT_SOURCE}; cross-check: {ET30_CHECK_SOURCE}",
                "photocatalyst_class": PC_CLASS[row["photocatalyst"]],
                "copper_oxidation_state_nominal": oxidation_state,
                "copper_ligand_class": copper_class,
                "copper_contains_cyanide": contains_cyanide,
                "ligand_family": "bisoxazoline" if str(row["ligand"]).startswith("L") else "none",
                "fixed_deoxygenation_reagent": "P(OEt)3",
                "fixed_cyanide_source": "TMSCN",
                "reaction_family": "nhp_ether_deoxygenative_asymmetric_cyanation",
            }
        )
    output = pd.DataFrame(records)
    for column, prefix in (
        ("solvent", "solvent_id"),
        ("photocatalyst_class", "pc_class"),
        ("copper_source", "copper_id"),
        ("ligand", "ligand_id"),
    ):
        output = add_one_hot(output, column, prefix)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(output)} condition vectors with {len(output.columns)} columns to {args.output}")


if __name__ == "__main__":
    main()
