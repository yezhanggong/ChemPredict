"""Validate the redistributable ChemPredict repository without source PDFs."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import pandas as pd


TEXT_SUFFIXES = {
    ".cff", ".cjs", ".css", ".csv", ".html", ".js", ".json", ".md",
    ".mjs", ".ps1", ".py", ".txt", ".yaml", ".yml",
}
FORBIDDEN_SUFFIXES = {".aab", ".apk", ".doc", ".docx", ".idsig", ".pdf", ".xls", ".xlsx"}
IGNORED_PARTS = {".git", ".venv", "__pycache__", "node_modules", "venv"}
SECRET_PATTERNS = {
    "GitHub token": re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"),
    "OpenAI-style token": re.compile(r"sk-[A-Za-z0-9]{20,}"),
    "Windows user path": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE),
    "local CODEX path": re.compile(r"[A-Za-z]:\\CODEX(?:\\|/)", re.IGNORECASE),
}


def fail(message: str) -> None:
    raise SystemExit(f"FAIL: {message}")


def ignored(path: Path) -> bool:
    return bool(IGNORED_PARTS.intersection(path.parts))


def scan_repository(root: Path) -> None:
    required = [
        "README.md",
        "LICENSE",
        "CITATION.cff",
        "DATA_CARD.md",
        "04_模型源码/model/artifacts/model_artifact_v44.json",
        "05_网站/index.html",
        "03_数据/整理数据/literature_registry.csv",
    ]
    missing = [relative for relative in required if not (root / relative).is_file()]
    if missing:
        fail(f"required public files missing: {missing}")

    forbidden = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not ignored(path) and path.suffix.lower() in FORBIDDEN_SUFFIXES
    ]
    if forbidden:
        fail(f"non-redistributable or binary release files found: {forbidden}")

    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or ignored(path) or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{path.relative_to(root).as_posix()}: {name}")
    if findings:
        fail("sensitive or machine-specific strings found: " + "; ".join(findings))


def validate_registry(root: Path) -> None:
    registry = pd.read_csv(root / "03_数据/整理数据/literature_registry.csv")
    required = {"reference_id", "title", "primary_url", "evidence_role", "in_numeric_training"}
    if not required.issubset(registry.columns):
        fail(f"literature registry columns missing: {sorted(required - set(registry.columns))}")
    if len(registry) < 20 or not registry["reference_id"].is_unique:
        fail("literature registry is incomplete or contains duplicate identifiers")
    numeric = registry[registry["in_numeric_training"].astype(str).str.lower() == "yes"]
    if numeric.empty or numeric["primary_url"].fillna("").eq("").any():
        fail("numerical data sources require a primary URL")


def run_data_validation(root: Path) -> Path:
    output = root / "07_验证结果/data/v4.4.0/public_release_validation.json"
    command = [
        sys.executable,
        str(root / "04_模型源码/data_pipeline/validate_data.py"),
        "--scope", str(root / "03_数据/整理数据/substrate_scope.csv"),
        "--conditions", str(root / "03_数据/整理数据/condition_screen.csv"),
        "--pubchem", str(root / "03_数据/整理数据/pubchem_properties.csv"),
        "--rdkit", str(root / "03_数据/整理数据/rdkit_descriptors.csv"),
        "--artifact", str(root / "04_模型源码/model/artifacts/model_artifact_v44.json"),
        "--mechanism-descriptors", str(root / "03_数据/整理数据/mechanism_proxy_descriptors.csv"),
        "--condition-descriptors", str(root / "03_数据/整理数据/condition_descriptors.csv"),
        "--qmdesc", str(root / "03_数据/整理数据/qmdesc_descriptors.csv"),
        "--steric", str(root / "03_数据/整理数据/steric_descriptors.csv"),
        "--reaction-systems", str(root / "03_数据/整理数据/reaction_system_registry.json"),
        "--term-dictionary", str(root / "03_数据/整理数据/chemical_term_dictionary.json"),
        "--promotion-decisions", str(root / "07_验证结果/model/v4.4.0/promotion_decisions.csv"),
        "--external-gate", str(root / "07_验证结果/model/v4.4.0/external_gate_results.csv"),
        "--metrics", str(root / "07_验证结果/model/v4.4.0/production_validation_metrics.csv"),
        "--literature-audit", str(root / "03_数据/整理数据/literature_corpus_audit.csv"),
        "--output", str(output),
    ]
    subprocess.run(command, cwd=root, check=True)
    result = json.loads(output.read_text(encoding="utf-8"))
    if result.get("status") != "PASS":
        fail("curated data validation did not pass")
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()

    scan_repository(root)
    validate_registry(root)
    output = run_data_validation(root)
    print(f"PASS: public repository audit and curated data validation ({output.relative_to(root)})")


if __name__ == "__main__":
    main()
