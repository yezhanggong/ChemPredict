"""Export bilingual registries to audit-friendly CSV and offline browser assets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reaction-json", type=Path, required=True)
    parser.add_argument("--term-json", type=Path, required=True)
    parser.add_argument("--website-assets", type=Path, required=True)
    args = parser.parse_args()

    systems = json.loads(args.reaction_json.read_text(encoding="utf-8"))
    terms = json.loads(args.term_json.read_text(encoding="utf-8"))
    args.website_assets.mkdir(parents=True, exist_ok=True)

    system_rows = []
    for record in systems:
        row = dict(record)
        row["outputs"] = "|".join(row.get("outputs", []))
        system_rows.append(row)
    pd.DataFrame(system_rows).to_csv(
        args.reaction_json.with_suffix(".csv"), index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(terms).to_csv(args.term_json.with_suffix(".csv"), index=False, encoding="utf-8-sig")

    asset = (
        "window.CHEMPREDICT_REACTION_SYSTEMS = "
        + json.dumps(systems, ensure_ascii=False, indent=2)
        + ";\nwindow.CHEMPREDICT_TERMS = "
        + json.dumps(terms, ensure_ascii=False, indent=2)
        + ";\n"
    )
    (args.website_assets / "registries.js").write_text(asset, encoding="utf-8")
    print(f"Exported {len(systems)} reaction systems and {len(terms)} bilingual terms.")


if __name__ == "__main__":
    main()
