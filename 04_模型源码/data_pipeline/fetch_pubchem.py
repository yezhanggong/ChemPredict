"""Fetch auditable PubChem properties for the curated substrate table.

The literature product name is queried first. If it is not indexed, the manually
transcribed connectivity SMILES is submitted. The manual SMILES remains in the
output so every fallback can be reviewed against the source structure.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd


PROPERTIES = (
    "MolecularFormula,MolecularWeight,XLogP,TPSA,Complexity,"
    "HBondDonorCount,HBondAcceptorCount,RotatableBondCount,HeavyAtomCount,"
    "CanonicalSMILES,IsomericSMILES"
)
BASE = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"


def request_json(url: str) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ChemPredict-v4/1.0 (academic audit workflow)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch(identifier_type: str, identifier: str) -> tuple[dict, str]:
    encoded = urllib.parse.quote(identifier, safe="")
    url = f"{BASE}/{identifier_type}/{encoded}/property/{PROPERTIES}/JSON"
    payload = request_json(url)
    properties = payload["PropertyTable"]["Properties"][0]
    return properties, url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--delay", type=float, default=0.25)
    args = parser.parse_args()

    data = pd.read_csv(args.input)
    rows: list[dict] = []
    for record in data.to_dict(orient="records"):
        result: dict = {}
        status = "name"
        source_url = ""
        error = ""
        try:
            result, source_url = fetch("name", str(record["pubchem_query"]))
        except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as exc:
            status = "smiles_fallback"
            error = f"name query: {exc}"
            try:
                result, source_url = fetch("smiles", str(record["manual_smiles"]))
            except (urllib.error.HTTPError, urllib.error.URLError, KeyError) as exc2:
                status = "unresolved"
                error = f"{error}; SMILES query: {exc2}"

        rows.append(
            {
                "id": record["id"],
                "pubchem_status": status,
                "pubchem_retrieved": date.today().isoformat(),
                "pubchem_url": source_url,
                "pubchem_error": error,
                "pubchem_cid": result.get("CID", ""),
                "pubchem_formula": result.get("MolecularFormula", ""),
                "pubchem_mw": result.get("MolecularWeight", ""),
                "pubchem_xlogp": result.get("XLogP", ""),
                "pubchem_tpsa": result.get("TPSA", ""),
                "pubchem_complexity": result.get("Complexity", ""),
                "pubchem_hbd": result.get("HBondDonorCount", ""),
                "pubchem_hba": result.get("HBondAcceptorCount", ""),
                "pubchem_rotatable": result.get("RotatableBondCount", ""),
                "pubchem_heavy_atoms": result.get("HeavyAtomCount", ""),
                "pubchem_smiles": result.get(
                    "ConnectivitySMILES", result.get("CanonicalSMILES", result.get("SMILES", ""))
                ),
                "pubchem_isomeric_smiles": result.get("IsomericSMILES", result.get("SMILES", "")),
            }
        )
        print(f"{record['id']}: {status}")
        time.sleep(args.delay)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(rows)} records to {args.output}")


if __name__ == "__main__":
    main()
