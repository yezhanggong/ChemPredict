"""Apply the recorded human screening decision to the local PDF corpus audit."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


SELECTED = {
    "carson-et-al-2024-free-radical-deoxygenative-amination-of-alcohols-via-copper-metallaphotoredox-catalysis-1.pdf": (
        "selected_mechanism_reference",
        "Copper metallaphotoredox alcohol deoxygenation; supports pathway-factor inventory only.",
    ),
    "Zhe.pdf": (
        "selected_mechanism_reference",
        "Metallaphotoredox alcohol deoxygenation; supports precursor-activation boundary only.",
    ),
    "Ni-catalyzed enantioconvergent deoxygenative reductive cross-coupling of unactivated alkyl alcohols and aryl bromides.pdf": (
        "selected_negative_transfer_reference",
        "Enantioconvergent but Ni cross-coupling; demonstrates why catalyst and reaction family cannot be pooled.",
    ),
    "ja408971t.pdf": (
        "selected_precursor_reference",
        "Foundational N-hydroxyphthalimide radical-precursor chemistry; no target yield or ee labels transferred.",
    ),
    "FBF10B8D5DC64B61A1A51E52BDC52E39-mark.pdf": (
        "selected_asymmetric_method_context",
        "Recent asymmetric photoredox context after DOI-level review; retained as qualitative context only.",
    ),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    table = pd.read_csv(args.input)
    roles: list[str] = []
    notes: list[str] = []
    selected_flags: list[bool] = []
    for name in table["file_name"].astype(str):
        if name in SELECTED:
            role, note = SELECTED[name]
            selected = True
        else:
            role = "excluded_after_title_abstract_screen"
            note = "Not sufficiently matched to the target precursor, Cu/photoredox cycle, product-forming step, and asymmetric outcome."
            selected = False
        roles.append(role)
        notes.append(note)
        selected_flags.append(selected)
    table["human_data_role"] = roles
    table["review_notes"] = notes
    table["selected_for_local_reference"] = selected_flags
    table["numeric_training_eligible"] = "no"
    table["numeric_transfer_reason"] = (
        "No corpus paper matches the target precursor, catalyst network, product-forming step, protocol, and label definition simultaneously."
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Human-screened {len(table)} PDFs; retained {sum(selected_flags)} for qualitative local reference.")


if __name__ == "__main__":
    main()
