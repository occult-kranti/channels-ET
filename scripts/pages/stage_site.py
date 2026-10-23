#!/usr/bin/env python3
"""Stage the retained static release; never crawl, train, or rebuild research."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REQUIRED = (
    "index.html", ".nojekyll", "dist/index.html", "dist/expansion/index.html",
    "dist/research/index.html", "dist/research/app.js", "dist/research/data.json",
    "dist/research/paper.pdf", "dist/research/source.zip",
    "dist/research/qwen-digest-lora-pilot.zip", "dist/research/qa-candidates.sqlite",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stage(output: Path) -> dict:
    output = output.resolve()
    if output == ROOT or output in ROOT.parents or output.is_relative_to(ROOT / "dist"):
        raise ValueError("Output must not replace the repository or its dist sources")
    if output.exists():
        raise ValueError("Output directory already exists; choose a fresh path")
    sources = [ROOT / "index.html", ROOT / ".nojekyll", *sorted((ROOT / "dist").rglob("*"))]
    for source in sources:
        if source.is_symlink():
            raise ValueError(f"Static artifact must not contain symlinks: {source.relative_to(ROOT)}")
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            raise ValueError(f"Missing static release file: {relative}")
    output.mkdir(parents=True)
    files = []
    for source in sources:
        if not source.is_file():
            continue
        relative = source.relative_to(ROOT).as_posix()
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        files.append({"path": relative, "bytes": target.stat().st_size, "sha256": sha256(target)})
    commit = os.environ.get("GITHUB_SHA") or subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    static_inputs_dirty = bool(subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", "index.html", ".nojekyll", "dist"],
        cwd=ROOT, text=True,
    ).strip())
    manifest = {
        "schema_version": 1,
        "repository": "occult-kranti/channels-ET",
        "source_commit": commit,
        "static_inputs_dirty": static_inputs_dirty,
        "commit_scope": "Checkout HEAD; per-file hashes also bind any uncommitted static inputs",
        "base_path": "/channels-ET/",
        "entry": "index.html",
        "current_dashboard": "dist/research/",
        "legacy_dashboard": "dist/",
        "method": "Copy retained root entry and complete dist tree without scientific recomputation",
        "manifest_self_excluded": True,
        "files": files,
        "file_count": len(files),
        "total_bytes": sum(x["bytes"] for x in files),
    }
    (output / "deployment-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = stage(args.output)
    print(json.dumps({k: manifest[k] for k in ("source_commit", "file_count", "total_bytes")}))


if __name__ == "__main__":
    main()
