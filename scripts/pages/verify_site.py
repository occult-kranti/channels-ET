#!/usr/bin/env python3
"""Check staged files and project-prefix HTTP routes, or an actual Pages site."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

ROUTES = {
    "": b"./dist/research/",
    "dist/": b"<html",
    "dist/expansion/": b"<html",
    "dist/research/": b"Channels ET",
    "dist/research/app.js": None,
    "dist/research/data.json": None,
    "dist/research/paper.pdf": b"%PDF-",
    "dist/research/source.zip": b"PK",
    "dist/research/qwen-digest-lora-pilot.zip": b"PK",
    "dist/research/qa-candidates.sqlite": b"SQLite format 3",
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def http_verify(base: str, expected: dict | None = None) -> dict:
    base = base.rstrip("/") + "/"
    def get(relative: str) -> tuple[bytes, int]:
        request = Request(urljoin(base, quote(relative)), headers={"User-Agent": "channels-ET-deployment-verifier/1"})
        with urlopen(request, timeout=45) as response:
            return response.read(), response.status
    data, status = get("deployment-manifest.json")
    assert status == 200, "Deployment manifest is unavailable"
    manifest = json.loads(data)
    if expected is not None:
        assert manifest == expected, "Live manifest differs from the staged release"
    hashes = {row["path"]: row for row in manifest["files"]}
    results = []
    for route, marker in ROUTES.items():
        body, status = get(route)
        path = route + "index.html" if not route or route.endswith("/") else route
        assert status == 200, f"Non-200 route: {route}"
        assert marker is None or marker.lower() in body.lower(), f"Wrong response body: {route}"
        assert digest(body) == hashes[path]["sha256"], f"Download/body hash mismatch: {route}"
        results.append({"route": route, "status": status, "bytes": len(body), "sha256": digest(body)})
    return {"base_url": base, "source_commit": manifest["source_commit"],
            "static_inputs_dirty": manifest.get("static_inputs_dirty"), "routes": results}


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--serve-prefix", help="Serve directory locally at this project path and check via HTTP")
    parser.add_argument("--base-url", help="Check an existing HTTPS Pages deployment")
    parser.add_argument("--expected-commit")
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    assert args.directory or args.base_url, "Provide --directory or --base-url"
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "status": "passed"}
    manifest = None
    if args.directory:
        directory = args.directory.resolve()
        manifest = json.loads((directory / "deployment-manifest.json").read_text())
        for row in manifest["files"]:
            path = directory / row["path"]
            assert path.is_file() and not path.is_symlink(), f"Missing or unsafe artifact: {row['path']}"
            assert path.stat().st_size == row["bytes"] and digest(path.read_bytes()) == row["sha256"], row["path"]
        assert len(manifest["files"]) == manifest["file_count"]
        report["local_files_verified"] = manifest["file_count"]
        if args.serve_prefix:
            prefix = "/" + args.serve_prefix.strip("/") + "/"
            class PrefixHandler(QuietHandler):
                def do_GET(self):
                    if not self.path.startswith(prefix):
                        self.send_error(404)
                        return
                    self.path = "/" + self.path[len(prefix):]
                    super().do_GET()
            server = ThreadingHTTPServer(("127.0.0.1", 0), partial(PrefixHandler, directory=str(directory)))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            try:
                report["prefix_http"] = http_verify(f"http://127.0.0.1:{server.server_port}{prefix}", manifest)
            finally:
                server.shutdown()
                server.server_close()
                worker.join()
    if args.base_url:
        assert args.base_url.startswith("https://"), "Remote verification must preserve HTTPS"
        report["live_http"] = http_verify(args.base_url, manifest)
    commit = (report.get("live_http") or report.get("prefix_http") or manifest)["source_commit"]
    assert not args.expected_commit or args.expected_commit == commit, "Unexpected deployed commit"
    report["source_commit"] = commit
    if args.receipt:
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
