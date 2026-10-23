#!/usr/bin/env python3
"""Check staged files and project-prefix HTTP routes, or an actual Pages site."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import sqlite3
import tempfile
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


def verify_harvest(payloads: dict[str, bytes], file_manifest: dict) -> dict:
    """Reconcile published bookkeeping only; never follow media URLs or local raw paths."""
    def body(name: str) -> bytes:
        return payloads["dist/research/" + name]
    def load(name: str):
        return json.loads(body(name))
    bundle = load("data.json")
    harvest = bundle["harvest"]
    bindings = {
        "run": "harvest-summary.json", "inventory": "harvest-inventory-summary.json",
        "attempts": "harvest-attempts.json", "saved": "harvest-artifacts.json",
        "channels": "harvest-channel-routes.json", "rootProbe": "harvest-root-access-probe.json",
        "publisherAudio": "harvest-publisher-audio.json", "asr": "harvest-asr-summary.json",
    }
    for key, name in bindings.items():
        assert harvest[key] == load(name), f"Dashboard differs from downloadable source: {name}"
    artifact_bindings = 0
    for artifact in bundle["artifacts"]:
        if not artifact["path"].startswith("harvest-"):
            continue
        path = "dist/research/" + artifact["path"]
        assert artifact["bytes"] == file_manifest[path]["bytes"], path
        assert artifact["sha256"] == file_manifest[path]["sha256"], path
        artifact_bindings += 1
    def jsonl(name: str) -> list:
        return [json.loads(line) for line in body(name).splitlines() if line.strip()]
    videos = jsonl("harvest-video-inventory.jsonl")
    queries = jsonl("harvest-query-inventory.jsonl")
    edges = jsonl("harvest-source-edges.jsonl")
    channels = harvest["channels"]["records"]
    inventory = harvest["inventory"]
    counts = inventory["counts"]
    run = harvest["run"]
    jobs = load("harvest-jobs.json")["records"]
    view_jobs = harvest["jobs"]["records"]
    assert len(jobs) == len(view_jobs) and len({r["id"] for r in jobs}) == len(jobs)
    full_jobs = {r["id"]: r for r in jobs}
    for row in view_jobs:
        source = full_jobs[row["id"]]
        for key in ("kind", "target_id", "status", "attempt_count"):
            assert row[key] == source[key], f"Dashboard worker projection mismatch: {row['id']} {key}"
    assert len(videos) == run["inventory"]["videos"] == inventory["download_state"]["inventory_only"]
    assert len(channels) == counts["channel_routes"] == run["inventory"]["channel_jobs"]
    assert len(queries) == counts["keyword_queries"] and len(edges) == counts["explicit_relationship_edges"]
    expected_jobs = {"captions": len(videos), "metadata": len(videos), "video": len(videos),
                     "channel": len(channels), "playlist": counts["playlists"]}
    actual_jobs = Counter(r["kind"] for r in jobs)
    assert set(actual_jobs).issubset(expected_jobs), "Unreviewed worker job kind"
    assert all(actual_jobs[k] == n for k, n in expected_jobs.items()), "Worker universe differs from indexed inventory"
    observed_states = {}
    for kind in actual_jobs:
        observed_states[kind] = dict(Counter(r["status"] for r in jobs if r["kind"] == kind))
    assert observed_states == run["counts_by_kind"], "Worker state totals differ from downloadable run summary"
    attempts = harvest["attempts"]["records"]
    assert len(attempts) == run["attempts_total"] == sum(r["attempt_count"] for r in jobs)
    if run["run_status"] == "not_executed_access_gate":
        assert not attempts and all(r["status"] == "queued" for r in jobs)
    with tempfile.TemporaryDirectory(prefix="channels-et-inventory-check-") as temp:
        database = Path(temp) / "inventory.sqlite"
        database.write_bytes(body("harvest-inventory.sqlite"))
        with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
            assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            sqlite_counts = {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                             for table in ("videos", "channel_routes", "queries", "edges", "playlists")}
    assert sqlite_counts == {"videos": len(videos), "channel_routes": len(channels), "queries": len(queries),
                             "edges": len(edges), "playlists": counts["playlists"]}
    publisher = harvest["publisherAudio"]
    completed = [r for r in publisher["records"] if r["status"] == "completed"]
    assert len(completed) == publisher["completed_audio_files"]
    assert sum(r["bytes"] for r in completed) == publisher["completed_audio_bytes"]
    assert math.isclose(sum(r["duration_seconds"] for r in completed), publisher["completed_audio_seconds"], abs_tol=1e-5)
    assert publisher["not_youtube_downloads"] is True and publisher["youtube_requests"] == 0
    asr = harvest["asr"]
    full_asr = [r for r in asr["records"] if r["transcribedScope"] == "full_decoded_audio"]
    assert len(full_asr) == asr["completedFullTranscripts"]
    assert len(asr["records"]) - len(full_asr) == asr["diagnosticClips"]
    assert sum(r["segments"] for r in full_asr) == asr["totalSegments"]
    assert sum(r["words"] for r in full_asr) == asr["totalWords"]
    assert sum(f["bytes"] for r in full_asr for f in r["outputs"]) == asr["totalTranscriptBytes"]
    assert math.isclose(sum(r["sourceAudioDurationSeconds"] for r in full_asr), asr["totalAudioDurationSeconds"], abs_tol=1e-5)
    for row in asr["records"]:
        assert row["status"] == "completed" and row["humanReviewed"] is False
        assert any(p["source_id"] == row["sourceId"] and p["sha256"] == row["sourceAudioSha256"]
                   and p["enclosure_url"] == row["sourceUrl"] for p in completed), "ASR/audio source join mismatch"
    for key in ("humanReviewed", "rawTranscriptTextPublished", "youtubeVideoEditionVerified"):
        assert asr[key] is False, f"Review public interpretation before changing {key}"
    return {
        "status": "passed", "scope": "Published metadata/receipt reconciliation; no audio or transcript text fetched",
        "download_artifact_bindings": artifact_bindings,
        "inventory_videos": len(videos), "channel_routes": len(channels), "playlists": counts["playlists"],
        "worker_jobs": len(jobs), "worker_counts_by_kind": dict(actual_jobs), "worker_attempts": len(attempts),
        "worker_states": observed_states, "inventory_sqlite_counts": sqlite_counts,
        "publisher_completed_audio_files": len(completed), "publisher_completed_audio_bytes": publisher["completed_audio_bytes"],
        "asr_full_transcripts": len(full_asr), "asr_source_joins": len(asr["records"]),
        "asr_words": asr["totalWords"], "asr_transcript_bytes_private": asr["totalTranscriptBytes"],
    }


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
    payloads = {}
    routes = dict(ROUTES)
    has_harvest = "dist/research/harvest.js" in hashes
    if has_harvest:
        routes["dist/research/harvest.js"] = None
        for path in hashes:
            if path.startswith("dist/research/harvest-"):
                routes[path] = b"SQLite format 3" if path.endswith(".sqlite") else None
    for route, marker in routes.items():
        body, status = get(route)
        path = route + "index.html" if not route or route.endswith("/") else route
        assert status == 200, f"Non-200 route: {route}"
        assert marker is None or marker.lower() in body.lower(), f"Wrong response body: {route}"
        assert digest(body) == hashes[path]["sha256"], f"Download/body hash mismatch: {route}"
        payloads[path] = body
        results.append({"route": route, "status": status, "bytes": len(body), "sha256": digest(body)})
    report = {"base_url": base, "source_commit": manifest["source_commit"],
              "static_inputs_dirty": manifest.get("static_inputs_dirty"), "routes": results}
    if has_harvest:
        report["acquisition_checks"] = verify_harvest(payloads, hashes)
    return report


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
