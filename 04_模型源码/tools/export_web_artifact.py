"""Wrap the JSON artifact as a script for file:// and Android WebView use."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--virtual-library", type=Path)
    args = parser.parse_args()
    artifact = json.loads(args.input.read_text(encoding="utf-8"))
    if args.virtual_library:
        import pandas as pd

        artifact["virtual_candidates"] = (
            pd.read_csv(args.virtual_library).fillna("").to_dict(orient="records")
        )
    payload = json.dumps(artifact, ensure_ascii=False, indent=2)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        f"window.CHEMPREDICT_ARTIFACT = {payload};\n",
        encoding="utf-8",
    )
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(payload + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
