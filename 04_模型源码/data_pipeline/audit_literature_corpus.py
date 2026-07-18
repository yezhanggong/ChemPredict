"""Audit a local PDF corpus before any record is admitted to model development.

The script is intentionally conservative. It extracts bibliographic clues and
keyword evidence, but never labels a paper as training-compatible by itself.
Human review must set the final data_role in the generated registry.
"""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import pandas as pd
from pypdf import PdfReader


KEYWORDS = {
    "asymmetric": re.compile(r"\b(?:asymmetric|enantioselective|enantioenriched|enantioselectivity)\b", re.I),
    "cyanation": re.compile(r"\b(?:cyanation|cyanide|nitrile)\b", re.I),
    "copper": re.compile(r"\b(?:copper|Cu\(?[I1V2]*\)?)\b", re.I),
    "photoredox": re.compile(r"\b(?:photoredox|photocatal|visible[- ]light|photoinduced)\b", re.I),
    "deoxygenative": re.compile(r"\b(?:deoxygenative|deoxygenation|alcohol)\b", re.I),
    "ligand": re.compile(r"\b(?:ligand|bisoxazoline|BOX|oxazoline)\b", re.I),
    "solvent": re.compile(r"\b(?:solvent|dichloromethane|acetonitrile|DCM|DCE)\b", re.I),
    "scope": re.compile(r"\b(?:substrate scope|scope of|optimization)\b", re.I),
}

DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean_doi(value: str) -> str:
    return value.rstrip(".,;:)]}>\"'")


def extract_text(reader: PdfReader, max_pages: int) -> tuple[str, int]:
    chunks: list[str] = []
    extracted_pages = 0
    for page in reader.pages[:max_pages]:
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        if text.strip():
            extracted_pages += 1
            chunks.append(text)
    return "\n".join(chunks), extracted_pages


def suggested_role(counts: dict[str, int]) -> str:
    if counts["asymmetric"] and counts["cyanation"] and counts["copper"]:
        return "manual_review_candidate"
    if counts["photoredox"] or counts["deoxygenative"] or counts["ligand"]:
        return "descriptor_or_mechanism_reference"
    return "background_or_out_of_scope"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("corpus", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-pages", type=int, default=30)
    args = parser.parse_args()

    rows: list[dict] = []
    for path in sorted(args.corpus.rglob("*.pdf")):
        row: dict = {
            "file_name": path.name,
            "relative_path": str(path.relative_to(args.corpus)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "read_status": "ok",
        }
        try:
            reader = PdfReader(path)
            text, extracted_pages = extract_text(reader, args.max_pages)
            metadata = reader.metadata or {}
            dois = sorted({clean_doi(match.group(0)) for match in DOI_PATTERN.finditer(text)})
            counts = {name: len(pattern.findall(text)) for name, pattern in KEYWORDS.items()}
            row.update(
                {
                    "pdf_pages": len(reader.pages),
                    "pages_text_extracted": extracted_pages,
                    "metadata_title": str(metadata.get("/Title", "") or "").strip(),
                    "metadata_author": str(metadata.get("/Author", "") or "").strip(),
                    "doi_candidates": ";".join(dois[:10]),
                    **{f"kw_{name}": value for name, value in counts.items()},
                    "suggested_role": suggested_role(counts),
                    "human_data_role": "pending_review",
                    "review_notes": "",
                }
            )
        except Exception as exc:
            row.update(
                {
                    "read_status": f"error:{type(exc).__name__}",
                    "pdf_pages": "",
                    "pages_text_extracted": 0,
                    "metadata_title": "",
                    "metadata_author": "",
                    "doi_candidates": "",
                    **{f"kw_{name}": 0 for name in KEYWORDS},
                    "suggested_role": "unreadable",
                    "human_data_role": "exclude",
                    "review_notes": str(exc),
                }
            )
        rows.append(row)

    table = pd.DataFrame(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(table[["file_name", "pdf_pages", "suggested_role", "doi_candidates"]].to_string(index=False))
    print(f"Wrote {len(table)} audited PDFs to {args.output}")


if __name__ == "__main__":
    main()
