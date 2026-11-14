#!/usr/bin/env python3
"""Package the complete public acquisition source for hash-pinned transport."""
import hashlib
import json
import os
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "research/acquisition-2026-11"
OUT = ROOT / "source-bootstrap.tar.xz"
MANIFEST = ROOT / "source-manifest.json"
INCLUDE = [
    "research/acquisition-2026-11",
    "dist/research/acquisition-2026-11",
    "scripts/pages/stage_site.py",
    "scripts/pages/verify_site.py",
    "research/harvest/asr/model-manifest.json",
    "dist/research/index.html",
    "README.md",
]


def main():
    files = []
    for relative in INCLUDE:
        path = ROOT / relative
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        else:
            files.append(path)
    files = sorted(set(files))
    records = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if "__pycache__" in relative or relative.endswith((".pyc", ".tmp")):
            continue
        records.append({"path": relative, "bytes": path.stat().st_size,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {
        "schemaVersion": 1,
        "sourceCommit": os.environ.get("CHANNELS_ET_SOURCE_COMMIT", "research/acquisition-2026-11-expanded"),
        "fileCount": len(records),
        "files": records,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
    records.append({"path": MANIFEST.name, "bytes": MANIFEST.stat().st_size,
                    "sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest()})
    with tarfile.open(OUT, "w:xz", preset=9) as archive:
        for record in records:
            path = ROOT / record["path"]
            archive.add(path, arcname=record["path"])
    print(json.dumps({"archive": str(OUT), "bytes": OUT.stat().st_size,
                      "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
                      "files": len(records)}, indent=2))


if __name__ == "__main__":
    main()
