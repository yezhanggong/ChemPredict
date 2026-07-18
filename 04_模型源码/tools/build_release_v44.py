"""Build a redistributable v4.4 source archive and SHA-256 inventory."""

from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path

import pandas as pd


VERSION = "4.4.0"
PREFIX = f"ChemPredict_v{VERSION}"


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def excluded(relative: Path) -> bool:
    lowered = {part.lower() for part in relative.parts}
    if any(
        name in lowered
        for name in {".venv", ".venv-v44", "__pycache__", "node_modules", ".git", "local-run"}
    ):
        return True
    if relative.suffix.lower() in {
        ".aab", ".apk", ".doc", ".docx", ".idsig", ".pdf", ".pyc", ".xls", ".xlsx", ".zip"
    }:
        return True
    if relative.parts and relative.parts[0] == "09_发布包":
        return True
    if relative.parts and relative.parts[0] in {"02_文献原文", "private-data", "references"}:
        return True
    return False


def files_for(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if excluded(relative):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.as_posix().lower())


def write_zip(root: Path, output: Path, files: list[Path]) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(root)
            archive.write(path, (Path(PREFIX) / relative).as_posix())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    args.output.mkdir(parents=True, exist_ok=True)

    public_files = files_for(root)
    public_zip = args.output / f"{PREFIX}_source.zip"
    write_zip(root, public_zip, public_files)

    inventory = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest(path),
            "in_public_archive": True,
        }
        for path in public_files
    ]
    pd.DataFrame(inventory).to_csv(
        args.output / f"{PREFIX}_源文件清单.csv", index=False, encoding="utf-8-sig"
    )
    with zipfile.ZipFile(public_zip) as archive:
        forbidden = [
            name
            for name in archive.namelist()
            if Path(name).suffix.lower()
            in {".aab", ".apk", ".doc", ".docx", ".idsig", ".pdf", ".xls", ".xlsx"}
        ]
    release_rows = [
        {
            "file": public_zip.name,
            "kind": "redistributable_source",
            "bytes": public_zip.stat().st_size,
            "sha256": digest(public_zip),
            "file_count": len(public_files),
            "contains_forbidden_file": bool(forbidden),
        }
    ]
    if forbidden:
        raise RuntimeError(f"release exclusion failed: {forbidden}")
    pd.DataFrame(release_rows).to_csv(
        args.output / f"{PREFIX}_发布包校验.csv", index=False, encoding="utf-8-sig"
    )
    print(pd.DataFrame(release_rows).to_string(index=False))


if __name__ == "__main__":
    main()
