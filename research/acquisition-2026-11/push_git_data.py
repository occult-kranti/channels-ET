#!/usr/bin/env python3
"""Push the complete public acquisition tree via GitHub's Git Data API."""
import base64
import hashlib
import json
import os
from pathlib import Path
import time
import requests

ROOT = Path(__file__).resolve().parents[0]
REPO = "occult-kranti/channels-ET"
BRANCH = "research/acquisition-2026-11-expanded"
API = "https://api.github.com"
TOKEN = os.environ["GITHUB_TOKEN"]
HEADERS = {
    "Authorization": f"token {TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}
INCLUDE = [
    "research/acquisition-2026-11",
    "dist/research/acquisition-2026-11",
    "scripts/pages/stage_site.py",
    "scripts/pages/verify_site.py",
    "research/harvest/asr/model-manifest.json",
    "dist/research/index.html",
    "README.md",
    "source-bootstrap.json",
    "source-manifest.json",
]


def request(method, path, **kwargs):
    url = path if path.startswith("http") else API + path
    for attempt in range(3):
        response = requests.request(method, url, headers=HEADERS, timeout=90, **kwargs)
        if response.status_code < 500 and response.status_code != 429:
            if response.status_code >= 400:
                raise RuntimeError(f"{method} {path}: {response.status_code} {response.text[:500]}")
            return response.json()
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"{method} {path}: repeated server/rate errors {response.status_code}")


def main():
    ref = request("GET", f"/repos/{REPO}/git/ref/heads/{BRANCH}")
    head = ref["object"]["sha"]
    commit = request("GET", f"/repos/{REPO}/git/commits/{head}")
    base_tree = commit["tree"]["sha"]
    files = []
    for relative in INCLUDE:
        path = ROOT / relative
        if path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.is_file()))
        else:
            files.append(path)
    files = sorted(set(files))
    tree = []
    for path in files:
        relative = path.relative_to(ROOT).as_posix()
        if "__pycache__" in relative or relative.endswith((".pyc", ".tmp")):
            continue
        raw = path.read_bytes()
        blob = request("POST", f"/repos/{REPO}/git/blobs", json={
            "content": base64.b64encode(raw).decode("ascii"),
            "encoding": "base64",
        })
        tree.append({"path": relative, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print("blob", relative, len(raw), flush=True)
    new_tree = request("POST", f"/repos/{REPO}/git/trees", json={
        "base_tree": base_tree, "tree": tree,
    })
    new_commit = request("POST", f"/repos/{REPO}/git/commits", json={
        "message": "Publish November acquisition and ASR analysis workbench",
        "tree": new_tree["sha"], "parents": [head],
    })
    updated = request("PATCH", f"/repos/{REPO}/git/refs/heads/{BRANCH}", json={
        "sha": new_commit["sha"], "force": False,
    })
    print(json.dumps({"commit": new_commit["sha"], "tree": new_tree["sha"],
                      "files": len(tree), "updatedRef": updated["object"]["sha"]}, indent=2))


if __name__ == "__main__":
    main()
