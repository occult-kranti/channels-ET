#!/usr/bin/env python3
"""Create compressed, hash-bound chunks for large public artifacts.

The chunks are ordinary ASCII text and can be pushed through GitHub's file API.
materialize_public_artifacts.py deterministically reassembles and verifies them.
No private media or third-party transcript body is read by the reassembler.
"""
import base64
import hashlib
import json
import lzma
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "research/acquisition-2026-11"
DEST = SOURCE / "chunks"
CHUNK_SIZE = 60_000
DEFAULTS = [
    "video-reference.csv", "channel-reference.csv", "asr-summary.json",
    "analysis/analysis.json", "analysis/non-bashar-public.csv",
    "analysis/non-bashar-public.sqlite",
]


def main():
    requested = sys.argv[1:] or DEFAULTS
    files = []
    for relative in requested:
        path = SOURCE / relative
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        else:
            files.append(path)
    if not files:
        raise SystemExit("No input files")
    DEST.mkdir(exist_ok=True)
    records = []
    for path in files:
        if not path.is_file():
            raise FileNotFoundError(path)
        relative = path.relative_to(SOURCE).as_posix()
        raw = path.read_bytes()
        compressed = lzma.compress(raw, preset=lzma.PRESET_EXTREME)
        encoded = base64.b64encode(compressed).decode("ascii")
        identifier = hashlib.sha256(relative.encode()).hexdigest()[:16]
        chunks = [encoded[index:index + CHUNK_SIZE]
                  for index in range(0, len(encoded), CHUNK_SIZE)] or [""]
        for index, chunk in enumerate(chunks):
            (DEST / f"{identifier}.xz.b64.{index:03d}").write_text(chunk)
        records.append({
            "id": identifier, "path": relative, "originalBytes": len(raw),
            "originalSha256": hashlib.sha256(raw).hexdigest(),
            "xzBytes": len(compressed), "xzSha256": hashlib.sha256(compressed).hexdigest(),
            "base64Bytes": len(encoded), "chunkCount": len(chunks),
            "chunkBytes": CHUNK_SIZE,
        })
        print(relative, len(raw), "->", len(compressed), "bytes,", len(chunks), "chunks")
    manifest_path = DEST / "manifest.json"
    previous = json.loads(manifest_path.read_text())["records"] if manifest_path.exists() else []
    merged = {row["path"]: row for row in previous}
    merged.update({row["path"]: row for row in records})
    records = [merged[path] for path in sorted(merged)]
    manifest = {
        "schemaVersion": 1,
        "format": "xz+base64 chunks; reassemble by path, then verify xz and original SHA-256",
        "chunkBytes": CHUNK_SIZE,
        "records": records,
    }
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("wrote", DEST / "manifest.json", "records", len(records))


if __name__ == "__main__":
    main()
