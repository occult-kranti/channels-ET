#!/usr/bin/env python3
"""Build the versioned public package for the November 2026 acquisition workstream.

The package binds sanitized public artifacts to their SHA-256 hashes and source
receipts. It contains no raw media, full transcripts, credentials, or model
weights; private evidence remains referenced by hash and private storage path.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
DIST = ROOT.parents[1] / "dist/research/acquisition-2026-11"
PACKAGE_VERSION = "2026-11-11.1"

ARTIFACTS = [
    "index.html",
    "manifest.json",
    "summary.json",
    "acquisition-ledger.json",
    "verification.json",
    "verification-reuse.json",
    "asr-summary.json",
    "all-candidates.json",
    "reference-summary.json",
    "channel-reference.csv",
    "video-reference.csv",
    "analysis/analysis.json",
    "analysis/verification.json",
    "analysis/gate-status.json",
    "analysis/sources-index.csv",
    "analysis/non-bashar-public.csv",
    "analysis/non-bashar-public.sqlite",
    "analysis/common-questions.json",
    "analysis/manual-review-questions.json",
    "analysis/fig1-funnel.svg",
    "analysis/fig1-funnel.png",
    "analysis/fig2-asr-coverage.svg",
    "analysis/fig2-asr-coverage.png",
    "analysis/fig3-entity-heatmap.svg",
    "analysis/fig3-entity-heatmap.png",
    "analysis/fig4-tfidf-similarity.svg",
    "analysis/fig4-tfidf-similarity.png",
    "analysis/fig5-question-types.svg",
    "analysis/fig5-question-types.png",
    "analysis/fig6-network.svg",
    "analysis/fig6-network.png",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build() -> None:
    DIST.mkdir(parents=True, exist_ok=True)
    rows = []
    for relative in ARTIFACTS:
        source = ROOT / relative
        target = DIST / relative
        if not source.exists():
            # CI materializes the public SQLite and PNGs from text artifacts;
            # tolerate their absence when the source SQLite is not committed.
            if relative.endswith(".png") or relative.endswith(".sqlite"):
                continue
            raise FileNotFoundError(f"Missing public artifact: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)
        rows.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
    analysis = json.loads((ROOT / "analysis/analysis.json").read_text())
    reference = json.loads((ROOT / "reference-summary.json").read_text())
    manifest = {
        "schemaVersion": 1,
        "package": "acquisition-2026-11",
        "packageVersion": PACKAGE_VERSION,
        "repository": "occult-kranti/channels-ET",
        "publicUrl": "https://occult-kranti.github.io/channels-ET/dist/research/acquisition-2026-11/",
        "packageArtifacts": len(rows),
        "observedVideos": reference["observedVideos"],
        "observedAccounts": reference["observedAccounts"],
        "candidateTerminal": reference["candidateTerminal"],
        "questionUnits": analysis["qa"]["totalUnits"],
        "mediaPublished": False,
        "transcriptBodiesPublished": False,
        "artifacts": rows,
    }
    (DIST / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Packaged {len(rows)} public artifacts into {DIST}")


if __name__ == "__main__":
    build()
