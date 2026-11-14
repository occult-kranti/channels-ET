#!/usr/bin/env python3
"""Capture the round-15 corrected snapshot from one canonical integration tree."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(os.environ.get("CHANNELS_ET_INTEGRATION_ROOT", Path(__file__).resolve().parents[4]))
OUT = ROOT / "research/acquisition-2026-11/reviews/round15"
REQUIRED = [
    "research/acquisition-2026-11/all-candidates.json",
    "research/acquisition-2026-11/supplemental-candidates.json",
    "research/acquisition-2026-11/acquisition-ledger.json",
    "research/acquisition-2026-11/summary.json",
    "research/acquisition-2026-11/asr-summary.json",
    "research/acquisition-2026-11/asr-code-editions.json",
    "research/acquisition-2026-11/transcribe_youtube.py",
    "research/acquisition-2026-11/backfill_language_metadata.py",
    "research/acquisition-2026-11/repair_quarantine_partial.py",
    "research/acquisition-2026-11/verify_audio.py",
    "research/acquisition-2026-11/reuse_verified_audio.py",
    "research/acquisition-2026-11/verification.json",
    "research/acquisition-2026-11/verification-reuse.json",
    "research/acquisition-2026-11/build_reference.py",
    "research/acquisition-2026-11/download_y2mate.py",
    "research/acquisition-2026-11/materialize_public_artifacts.py",
    "research/acquisition-2026-11/prepare_source_bootstrap.py",
    "research/acquisition-2026-11/push_git_data.py",
    "research/acquisition-2026-11/chunk_public_sources.py",
    "research/acquisition-2026-11/chunks/manifest.json",
    "research/acquisition-2026-11/source-bootstrap.json",
    "research/acquisition-2026-11/source-manifest.json",
    "research/acquisition-2026-11/package_acquisition.py",
    "research/acquisition-2026-11/README.md",
    "research/acquisition-2026-11/HANDOFF.md",
    "research/acquisition-2026-11/analysis/build.py",
    "research/acquisition-2026-11/analysis/verify.py",
    "research/acquisition-2026-11/analysis/protocol.json",
    "research/acquisition-2026-11/analysis/analysis.json",
    "research/acquisition-2026-11/analysis/manual-review.json",
    "research/acquisition-2026-11/analysis/qualitative-synthesis.md",
    "research/acquisition-2026-11/analysis/verification.json",
    "research/acquisition-2026-11/analysis/sources-index.csv",
    "research/acquisition-2026-11/analysis/non-bashar-public.csv",
    "research/acquisition-2026-11/analysis/common-questions.csv",
    "research/acquisition-2026-11/reference-summary.json",
    "research/acquisition-2026-11/video-reference.csv",
    "research/acquisition-2026-11/channel-reference.csv",
    "research/harvest/asr/model-manifest.json",
    "research/acquisition-2026-11/reviews/round15/README.md",
    "research/acquisition-2026-11/reviews/round15/browser-report.json",
    "research/acquisition-2026-11/reviews/round15/desktop.har",
    "research/acquisition-2026-11/reviews/round15/mobile.har",
    "research/acquisition-2026-11/reviews/round15/ci-fallback-receipt.json",
    "research/acquisition-2026-11/reviews/round15/integration-verification.json",
    "research/acquisition-2026-11/reviews/round15/staged-verification.json",
    "research/acquisition-2026-11/reviews/round15/capture_snapshot.py",
    "scripts/pages/stage_site.py",
    "scripts/pages/verify_site.py",
    "dist/research/index.html",
    "dist/research/acquisition-2026-11/manifest.json",
    "README.md",
]


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: capture_snapshot.py <integration-head-commit>")
    head = sys.argv[1]
    paths = REQUIRED + [
        str(p.relative_to(ROOT)) for p in sorted((ROOT / "research/acquisition-2026-11/code-editions").glob("*.py"))
    ] + [
        str(p.relative_to(ROOT)) for p in sorted((ROOT / "research/acquisition-2026-11/analysis/figures").glob("*.svg"))
    ] + [
        str(p.relative_to(ROOT)) for p in sorted((ROOT / "research/acquisition-2026-11/chunks").glob("*.xz.b64.*"))
    ]
    if len(paths) != len(set(paths)):
        raise RuntimeError("Duplicate snapshot paths")
    files = []
    for relative in paths:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        files.append({"path": relative, "bytes": path.stat().st_size,
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    remote_verified = os.environ.get("CHANNELS_ET_REMOTE_VERIFIED") == "1"
    payload = {
        "schemaVersion": 1,
        "round": 15,
        "capturedAtUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "baseMainCommit": "bf6a40f01fd693da00ecce6a6752273985df95a3",
        "integrationBranch": "research/acquisition-2026-11-expanded",
        "integrationHeadCommit": head,
        "canonicalRoot": "integration://research/acquisition-2026-11-expanded",
        "sourceCommitRepresentsCurrentWork": remote_verified,
        "staticInputsDirty": not remote_verified,
        "stagedDirectory": "staged://acquisition-2026-11-v6",
        "digestRecipe": "SHA-256 of canonical compact JSON (sort_keys=True, separators=(',', ':')) with snapshotSha256 omitted",
        "files": files,
    }
    payload["snapshotSha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (OUT / "snapshot.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"files": len(files), "integrationHeadCommit": head,
                      "snapshotSha256": payload["snapshotSha256"],
                      "sourceCommitRepresentsCurrentWork": remote_verified}, indent=2))


if __name__ == "__main__":
    main()
