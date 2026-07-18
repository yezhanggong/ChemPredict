"""Build the offline virtual candidate library with reproducible descriptors."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from compute_mechanism_descriptors import calculate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    seeds = pd.read_csv(args.input)
    calculated = pd.DataFrame(calculate(record) for record in seeds.to_dict(orient="records"))
    output = seeds.merge(calculated, on="id", validate="one_to_one")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(output)} virtual candidates to {args.output}")


if __name__ == "__main__":
    main()
