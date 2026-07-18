"""Fail fast when the v4.4 release layout or governance claims drift."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root
    required = [
        "README.md",
        "LICENSE",
        "CITATION.cff",
        "DATA_CARD.md",
        "03_数据/整理数据/qmdesc_descriptors.csv",
        "03_数据/整理数据/steric_descriptors.csv",
        "03_数据/整理数据/reaction_system_registry.json",
        "03_数据/整理数据/chemical_term_dictionary.json",
        "04_模型源码/model/artifacts/model_artifact_v44.json",
        "05_网站/index.html",
        "05_网站/app-v44.js",
        "05_网站/model-v44.js",
        "07_验证结果/data/v4.4.0/public_release_validation.json",
        "07_验证结果/browser/v4.4.0/ui_test_result.json",
        "08_说明文档/模型卡_v4.4.0.md",
        "08_说明文档/优化对比报告_v4.4.0.md",
    ]
    checks = []
    for relative in required:
        checks.append({"check": f"required:{relative}", "pass": (root / relative).is_file()})
    artifact_path = root / "04_模型源码/model/artifacts/model_artifact_v44.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    checks.extend(
        [
            {"check": "artifact_version_4.4.0", "pass": artifact["model_version"] == "4.4.0"},
            {"check": "production_champion_preserved", "pass": set(artifact["production_model_version_by_target"].values()) == {"4.3.0"}},
            {"check": "nine_reaction_systems", "pass": len(json.loads((root / "03_数据/整理数据/reaction_system_registry.json").read_text(encoding="utf-8"))) == 9},
            {"check": "data_validation_pass", "pass": json.loads((root / "07_验证结果/data/v4.4.0/public_release_validation.json").read_text(encoding="utf-8"))["status"] == "PASS"},
            {"check": "ui_validation_pass", "pass": json.loads((root / "07_验证结果/browser/v4.4.0/ui_test_result.json").read_text(encoding="utf-8"))["status"] == "PASS"},
            {"check": "no_apk_in_project", "pass": not any(root.rglob("*.apk"))},
            {"check": "no_pdf_in_public_project", "pass": not any(root.rglob("*.pdf"))},
        ]
    )
    table = pd.DataFrame(checks)
    output = root / "07_验证结果" / "release" / "v4.4.0" / "release_verification.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(output, index=False, encoding="utf-8-sig")
    print(table.to_string(index=False))
    if not table["pass"].all():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
