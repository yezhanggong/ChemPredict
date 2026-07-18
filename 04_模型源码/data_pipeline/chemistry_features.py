"""Shared, auditable structure helpers for ChemPredict v4.4 descriptor pipelines."""

from __future__ import annotations

from dataclasses import dataclass

from rdkit import Chem


@dataclass(frozen=True)
class ReactionCentre:
    centre_atom_index: int
    nitrile_carbon_index: int
    aryl_attachment_index: int
    centre_nitrile_bond_index: int
    centre_aryl_bond_index: int
    axis_directly_aromatic: bool


def locate_product_proxy_reaction_centre(molecule: Chem.Mol) -> ReactionCentre:
    """Locate the sp3 carbon bonded to the product nitrile and aromatic scaffold.

    The source table contains product-scaffold SMILES rather than the NHP-ether
    precursor. A nitrile attached to an aromatic substituent (for example 2n)
    is rejected as the product-forming nitrile because its neighbour is not sp3.
    """

    candidates: list[ReactionCentre] = []
    for nitrogen in molecule.GetAtoms():
        if nitrogen.GetAtomicNum() != 7:
            continue
        for triple_bond in nitrogen.GetBonds():
            if triple_bond.GetBondTypeAsDouble() != 3.0:
                continue
            nitrile_carbon = triple_bond.GetOtherAtom(nitrogen)
            if nitrile_carbon.GetAtomicNum() != 6:
                continue
            for centre in nitrile_carbon.GetNeighbors():
                if centre.GetIdx() == nitrogen.GetIdx():
                    continue
                if centre.GetHybridization() != Chem.HybridizationType.SP3:
                    continue
                aromatic_neighbours = [atom for atom in centre.GetNeighbors() if atom.GetIsAromatic()]
                if len(aromatic_neighbours) == 1:
                    aryl = aromatic_neighbours[0]
                    direct_aromatic = True
                else:
                    aromatic_atoms = [atom for atom in molecule.GetAtoms() if atom.GetIsAromatic()]
                    paths = [
                        Chem.GetShortestPath(molecule, centre.GetIdx(), atom.GetIdx())
                        for atom in aromatic_atoms
                        if atom.GetIdx() != centre.GetIdx()
                    ]
                    if not paths:
                        continue
                    shortest = min(paths, key=lambda path: (len(path), tuple(path)))
                    aryl = molecule.GetAtomWithIdx(shortest[1])
                    direct_aromatic = False
                centre_nitrile = molecule.GetBondBetweenAtoms(centre.GetIdx(), nitrile_carbon.GetIdx())
                centre_aryl = molecule.GetBondBetweenAtoms(centre.GetIdx(), aryl.GetIdx())
                candidates.append(
                    ReactionCentre(
                        centre_atom_index=centre.GetIdx(),
                        nitrile_carbon_index=nitrile_carbon.GetIdx(),
                        aryl_attachment_index=aryl.GetIdx(),
                        centre_nitrile_bond_index=centre_nitrile.GetIdx(),
                        centre_aryl_bond_index=centre_aryl.GetIdx(),
                        axis_directly_aromatic=direct_aromatic,
                    )
                )
    unique = {(item.centre_atom_index, item.nitrile_carbon_index): item for item in candidates}
    if len(unique) != 1:
        raise ValueError(f"expected one product-proxy reaction centre, found {len(unique)}")
    return next(iter(unique.values()))


def naphthyl_position(molecule: Chem.Mol, centre: ReactionCentre) -> int:
    """Return 1/2 for alpha/beta naphthyl attachment, otherwise zero."""

    if not centre.axis_directly_aromatic:
        return 0
    ring_info = molecule.GetRingInfo()
    if ring_info.NumRings() < 2 or sum(atom.GetIsAromatic() for atom in molecule.GetAtoms()) < 10:
        return 0
    fused_atoms = [
        atom.GetIdx()
        for atom in molecule.GetAtoms()
        if atom.GetIsAromatic() and ring_info.NumAtomRings(atom.GetIdx()) >= 2
    ]
    if not fused_atoms:
        return 0
    distances = [
        0
        if atom_index == centre.aryl_attachment_index
        else len(Chem.GetShortestPath(molecule, centre.aryl_attachment_index, atom_index)) - 1
        for atom_index in fused_atoms
    ]
    distance = min(distances)
    if distance == 1:
        return 1
    if distance == 2:
        return 2
    return 0


def discriminating_2d_descriptors(molecule: Chem.Mol, centre: ReactionCentre) -> dict[str, float | int]:
    periodic = Chem.GetPeriodicTable()
    halogens = {9: "f", 17: "cl", 35: "br", 53: "i"}
    values: dict[str, float | int] = {
        "naphthyl_position": naphthyl_position(molecule, centre),
        "halogen_type_f": 0,
        "halogen_type_cl": 0,
        "halogen_type_br": 0,
        "halogen_type_i": 0,
        "aryl_halogen_atomic_number_sum": 0,
        "ortho_sub_vdw_radius": 0.0,
        "ortho_sub_atomic_number_max": 0,
    }
    attachment = centre.aryl_attachment_index
    aromatic_indices = {atom.GetIdx() for atom in molecule.GetAtoms() if atom.GetIsAromatic()}
    for atom in molecule.GetAtoms():
        if atom.GetAtomicNum() in halogens and any(neighbour.GetIsAromatic() for neighbour in atom.GetNeighbors()):
            symbol = halogens[atom.GetAtomicNum()]
            values[f"halogen_type_{symbol}"] = 1
            values["aryl_halogen_atomic_number_sum"] += atom.GetAtomicNum()

    for aromatic_atom in molecule.GetAtoms():
        aromatic_index = aromatic_atom.GetIdx()
        if aromatic_index not in aromatic_indices:
            continue
        if aromatic_index == attachment:
            continue
        aromatic_path = Chem.GetShortestPath(molecule, attachment, aromatic_index)
        if len(aromatic_path) - 1 != 1 or not all(index in aromatic_indices for index in aromatic_path):
            continue
        for substituent in aromatic_atom.GetNeighbors():
            if substituent.GetIdx() in aromatic_indices:
                continue
            atomic_number = substituent.GetAtomicNum()
            values["ortho_sub_vdw_radius"] = max(
                float(values["ortho_sub_vdw_radius"]), float(periodic.GetRvdw(atomic_number))
            )
            values["ortho_sub_atomic_number_max"] = max(
                int(values["ortho_sub_atomic_number_max"]), atomic_number
            )
    return values
