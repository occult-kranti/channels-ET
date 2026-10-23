#!/usr/bin/env python3
"""Public, bounded YouTube discovery and caption acquisition with failure ledgers.

No authentication, cookies, proxy rotation, CAPTCHA workarounds or media download.
The inherited platform proxy/TLS trust remains in force. HTTP 403/429 and tool
block indications stop the current collection. A failed search is not a zero hit.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import hashlib
import importlib.metadata
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ATLAS = HERE.parents[2]


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def sanitize(message):
    # Deliberately omit original HTTP bodies, request headers and URL query values.
    text = re.sub(r"(?i)(https?://)[^/@\s]+:[^/@\s]+@", r"\1[redacted]@", str(message))
    text = re.sub(r"(?i)(authorization|cookie|token|key|password)(\s*[:=]\s*)[^\s,;]+", r"\1\2[redacted]", text)
    return text[-1200:]


def is_block(message):
    return bool(re.search(r"403|429|forbidden|too many requests|requestblocked|ipblocked|sign in to confirm|bot|access denied", message, re.I))


def inside_git(path):
    """Recognize actual checkouts, not sandbox-reserved empty .git directories."""
    resolved = path.resolve()
    for parent in (resolved, *resolved.parents):
        metadata_path = parent / ".git"
        if metadata_path.is_dir() and (metadata_path / "HEAD").is_file():
            return True
        if metadata_path.is_file() and metadata_path.read_text().strip().startswith("gitdir:"):
            return True
    return False


def plan():
    discovery = read(ATLAS / "dist/data.json")["discovery"]
    snapshot = read(ATLAS / "dist/analysis/data.json")
    people = discovery["people"]
    jobs = []
    for p in people:
        name = p["name"].strip()
        phrases = [f'"{name}" channeling', f'"{name}" questions answers', f'"{name}" interview']
        phrases += [f'"{name}" "{entity}"' for entity in p.get("entities", []) if entity and entity.casefold() != name.casefold()]
        for query in dict.fromkeys(phrases):
            jobs.append({"id": "query-" + digest((p["id"] + query).encode())[:14],
                         "kind": "keyword_search", "person_id": p["id"], "person_name": name,
                         "query": query, "url": "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query),
                         "entity_labels": p.get("entities", []), "identity_status": "inherited_candidate_not_revalidated",
                         "source_record_ids": p.get("recordIds", []), "status": "planned"})
    accounts = {}
    for r in discovery["records"]:
        if r.get("kind") != "account":
            continue
        url = r["url"].rstrip("/")
        key = url.casefold()
        people_ids = [p["id"] for p in people if r["id"] in p.get("recordIds", [])]
        accounts[key] = {"id": "account-" + digest(key.encode())[:14], "kind": "channel_crawl",
                         "url": url + "/videos", "person_ids": people_ids, "source_record_ids": [r["id"]],
                         "relationship_inherited": r.get("relationship"),
                         "identity_status": "inherited_route_not_officiality_proof", "status": "planned"}
    for p in people:
        for url in p.get("accountUrls", []):
            key = url.rstrip("/").casefold()
            entry = accounts.setdefault(key, {"id": "account-" + digest(key.encode())[:14], "kind": "channel_crawl",
                                               "url": url.rstrip("/") + "/videos", "person_ids": [],
                                               "identity_status": "inherited_route_not_officiality_proof", "status": "planned"})
            if p["id"] not in entry["person_ids"]:
                entry["person_ids"].append(p["id"])
    caption_manifest = read(ATLAS / "research/analysis/corpus/corpus_manifest.json")["records"]
    inherited_ids = {v["id"] for v in snapshot["videos"]}
    caption_ids = {v["video_id"] for v in caption_manifest}
    # Deterministic, first-per-publisher breadth sample, prior pilot first so its
    # reacquirability can be measured. Existing pilot is purposeful, not random.
    caption_jobs = [{"id": "caption-" + r["video_id"], "video_id": r["video_id"],
                     "inherited_person_key": r.get("person"), "person_name_inherited": r.get("person_name"),
                     "person_id": None,
                     "person_ids": [p["id"] for p in people if "https://www.youtube.com/watch?v=" + r["video_id"] in p.get("videoUrls", [])],
                     "identity_status": "inherited_person_key_is_not_stable_candidate_id; candidate_links_require_existing_video_URL_edge",
                     "entity_label": r.get("entity_inherited"), "selection": "historical_pilot_reacquisition",
                     "historical_status": r.get("transcript_status"), "status": "planned"} for r in caption_manifest]
    first_by_channel = {}
    for v in sorted(snapshot["videos"], key=lambda x: x["id"]):
        if v["id"] not in caption_ids and v.get("channelId"):
            first_by_channel.setdefault(v["channelId"], v)
    for channel, v in sorted(first_by_channel.items()):
        caption_jobs.append({"id": "caption-" + v["id"], "video_id": v["id"], "channel_id": channel,
                             "selection": "lexicographically_first_nonpilot_id_per_inherited_publisher",
                             "status": "planned"})
    data = {"schema_version": 1, "created_at": now(), "source_snapshot_sha256": digest((ATLAS / "dist/analysis/data.json").read_bytes()),
            "scope": "All 106 inherited practitioner/lineage/partial-name records; candidate discovery, not a census or identity verification.",
            "units": {"practitioner_candidates": len(people), "keyword_queries": len(jobs), "account_routes": len(accounts),
                      "historical_upload_ids": len(inherited_ids), "caption_candidates": len(caption_jobs)},
            "selection_policy": "Fixed keyword templates for each inherited name/entity; all inherited account routes; historical pilot then one nonpilot ID per publisher, sorted deterministically. No inferred name merges.",
            "searches": jobs, "accounts": list(accounts.values()), "captions": caption_jobs}
    write(HERE / "collection-plan.json", data)
    write(HERE / "practitioner-frame.json", {"people": people, "notes": "Preserves inherited attribution and unresolved identities; no newly verified ET identity or human count."})
    identity = [{"practitioner_id": p["id"], "name": p["name"], "entity_labels_inherited": p.get("entities", []),
                 "account_urls_inherited": p.get("accountUrls", []), "video_urls_inherited": p.get("videoUrls", []),
                 "source_record_ids": p.get("recordIds", []), "source_urls": p.get("sourceUrls", []),
                 "identity_status": "inherited_candidate_not_revalidated",
                 "not_a_unique_human_or_official_account_assertion": True} for p in people]
    write(HERE / "identity-map.json", {"schema_version": 1, "records": identity,
                                       "join_rule": "Existing explicit record edges only; never fuzzy-name merge or assume uploader=medium=entity=original-session."})
    def urlkey(url):
        parsed = urllib.parse.urlsplit(url)
        return (parsed.hostname or "").lower().removeprefix("www.") + parsed.path.rstrip("/").casefold()
    channel_urls = collections.defaultdict(set)
    for channel in snapshot["channels"]:
        for url in [channel.get("url")] + channel.get("aliases", []):
            if url:
                channel_urls[urlkey(url)].add(channel["id"])
    linked = []
    for record in identity:
        matches = [{"publisher_group_id": cid, "inherited_account_url": url,
                    "join_basis": "exact normalized URL matches retained channel URL/explicit alias; snapshot attribution, not independent person verification"}
                   for url in record["account_urls_inherited"] for cid in sorted(channel_urls.get(urlkey(url), []))]
        linked.append({"practitioner_id": record["practitioner_id"], "name": record["name"], "publisher_matches": matches,
                       "match_status": "inherited_explicit_route_match" if matches else "no_retained_exact_route_match"})
    write(HERE / "identity-publisher-links.json", {"schema_version": 1, "source_sha256": data["source_snapshot_sha256"],
                                                  "normalization": "Remove www., normalize URL host/path case, strip terminal slash; do not join by names. Existing explicit aliases retained.",
                                                  "records": linked})
    return data


def preflight():
    url = "https://www.youtube.com/watch?v=fZmY4xS_qXE"
    record = {"operation": "watch_metadata_preflight", "url": url, "retrieved_at": now()}
    try:
        with urllib.request.urlopen(url, timeout=20) as response:
            blob = response.read()
            record.update(status="success", http_status=response.status, response_bytes=len(blob), sha256=digest(blob),
                          matching_video_id=b'fZmY4xS_qXE' in blob)
    except Exception as error:
        msg = sanitize(error)
        record.update(status="blocked" if is_block(msg) else "failed", error_type=type(error).__name__, error=msg)
    return record


def discover(job, limit):
    target = "ytsearch" + str(limit) + ":" + job["query"] if job["kind"] == "keyword_search" else job["url"]
    command = [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-cache-dir", "--skip-download", "--flat-playlist",
               "--dump-single-json", "--playlist-end", str(limit), "--retries", "0", "--extractor-retries", "0",
               "--fragment-retries", "0", "--socket-timeout", "20", "--no-warnings", target]
    p = subprocess.run(command, capture_output=True, text=True, timeout=75)
    if p.returncode:
        msg = sanitize(p.stderr)
        return {"status": "blocked" if is_block(msg) else "failed", "exit_code": p.returncode, "error": msg}
    d = json.loads(p.stdout)
    rows = []
    for e in d.get("entries", []):
        if not e:
            continue
        vid = e.get("id")
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", vid or ""):
            continue
        rows.append({"video_id": vid, "title": e.get("title"), "source_url": "https://www.youtube.com/watch?v=" + vid,
                     "uploader": e.get("uploader"), "channel_id": e.get("channel_id"), "channel_url": e.get("channel_url"),
                     "duration_seconds": e.get("duration"), "view_count_observed": e.get("view_count"),
                     "access_depth": "flat_playlist_metadata_not_playback_or_speech_review"})
    return {"status": "success", "rows": rows, "result_count": len(rows), "response_sha256": digest(p.stdout.encode())}


def captions(job, raw_dir):
    from requests import Session
    from youtube_transcript_api import YouTubeTranscriptApi
    class LimitedSession(Session):
        def request(self, *args, **kwargs):
            kwargs.setdefault("timeout", 20)
            self.cookies.clear()
            return super().request(*args, **kwargs)
    tracks = list(YouTubeTranscriptApi(http_client=LimitedSession()).list(job["video_id"]))
    if not tracks:
        return {"status": "unavailable", "reason": "No offered caption tracks"}
    track = next((x for x in tracks if x.language_code in ("en", "en-US", "en-GB")), tracks[0])
    fetched = track.fetch()
    document = {"video_id": job["video_id"], "language_code": fetched.language_code,
                "is_generated": fetched.is_generated, "segments": fetched.to_raw_data()}
    blob = json.dumps(document, ensure_ascii=False, indent=2).encode()
    output = raw_dir / (job["video_id"] + ".json")
    if output.exists() and output.read_bytes() != blob:
        output = raw_dir / (job["video_id"] + "-" + digest(blob)[:12] + ".json")
    output.write_bytes(blob)
    return {"status": "success", "language_code": fetched.language_code, "is_generated": fetched.is_generated,
            "segment_count": len(document["segments"]), "word_count": sum(len(x["text"].split()) for x in document["segments"]),
            "raw_sha256": digest(blob), "raw_local_path": str(output), "source_url": "https://www.youtube.com/watch?v=" + job["video_id"],
            "rights": "Third-party captions retained outside Git for local analysis; no full text in research exports."}


def metadata(job):
    url = "https://www.youtube.com/watch?v=" + job["video_id"]
    with urllib.request.urlopen(url, timeout=20) as response:
        blob = response.read()
    page = blob.decode("utf-8")
    player = {}
    for marker in ("var ytInitialPlayerResponse = ", "ytInitialPlayerResponse = "):
        if marker in page:
            try:
                player = json.JSONDecoder().raw_decode(page.split(marker, 1)[1])[0]
                break
            except (ValueError, TypeError):
                continue
    detail = player.get("videoDetails", {})
    if detail.get("videoId") != job["video_id"]:
        return {"status": "unavailable", "reason": "Matching public watch metadata not exposed"}
    micro = player.get("microformat", {}).get("playerMicroformatRenderer", {})
    return {"status": "success", "video_id": job["video_id"], "source_url": url,
            "title": detail.get("title"), "publisher": detail.get("author"),
            "channel_id": detail.get("channelId"), "channel_url": micro.get("ownerProfileUrl"),
            "duration_seconds": int(detail["lengthSeconds"]) if detail.get("lengthSeconds") else None,
            "published_at": micro.get("publishDate"), "uploaded_at": micro.get("uploadDate"),
            "playability_status": player.get("playabilityStatus", {}).get("status"),
            "access_depth": "public_watch_metadata_not_playback_or_speech_review", "response_sha256": digest(blob)}


def input_video_jobs(path):
    data = read(path)
    records = data.get("records", []) if isinstance(data, dict) else data
    ids = []
    for r in records:
        for row in r.get("rows", [r]):
            vid = row.get("video_id", row.get("id"))
            if re.fullmatch(r"[A-Za-z0-9_-]{11}", vid or "") and vid not in ids:
                ids.append(vid)
    return [{"id": "metadata-" + vid, "video_id": vid, "source_input": str(path)} for vid in ids]


def round_robin(jobs):
    groups = collections.defaultdict(collections.deque)
    for job in jobs:
        person = job.get("person_id") or next(iter(job.get("person_ids", [])), "unresolved")
        groups[person].append(job)
    result = []
    while any(groups.values()):
        for key in sorted(groups):
            if groups[key]:
                result.append(groups[key].popleft())
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=("plan", "preflight", "search", "channels", "captions", "metadata"))
    p.add_argument("--max-jobs", type=int, default=3)
    p.add_argument("--per-job", type=int, default=8)
    p.add_argument("--output", type=pathlib.Path)
    p.add_argument("--raw-dir", type=pathlib.Path, default=pathlib.Path("/workspace/channeling-raw"))
    p.add_argument("--input", type=pathlib.Path, help="metadata: flat result manifest or records of video_id")
    p.add_argument("--person-id", action="append", default=[], help="restrict to inherited practitioner ID; repeatable")
    p.add_argument("--job-id", action="append", default=[], help="restrict to explicit plan job ID; repeatable")
    p.add_argument("--resume", action="store_true", help="append only not-yet-attempted jobs in this output")
    args = p.parse_args()
    if args.max_jobs < 1 or args.per_job < 1:
        p.error("limits must be positive")
    if args.mode == "plan":
        print(json.dumps(plan()["units"]))
        return
    result = {"mode": args.mode, "started_at": now(), "records": [], "blocked": False,
              "software": {name: importlib.metadata.version(name) for name in ("yt-dlp", "youtube-transcript-api")}}
    output = args.output or HERE / (args.mode + "-run.json")
    if output.exists() and not args.resume:
        p.error("output already exists; choose a new path to preserve the earlier run")
    if args.resume and args.mode == "preflight":
        p.error("preflight probes require a new dated output after a meaningful state change")
    if args.resume and output.exists():
        previous = read(output)
        if previous.get("mode") != args.mode:
            p.error("cannot resume a different operation mode")
        result["records"] = previous.get("records", [])
        result["run_history"] = previous.get("run_history", [])
    first_this_run = len(result["records"])
    if args.mode == "preflight":
        result["records"] = [preflight()]
    else:
        data = read(HERE / "collection-plan.json")
        if args.mode == "metadata":
            if args.input is None:
                p.error("metadata requires --input discovery results or video IDs")
            jobs = input_video_jobs(args.input)
        else:
            jobs = data[{"search": "searches", "channels": "accounts", "captions": "captions"}[args.mode]]
        if args.person_id:
            jobs = [j for j in jobs if j.get("person_id") in args.person_id or set(j.get("person_ids", [])) & set(args.person_id)]
        if args.job_id:
            jobs = [j for j in jobs if j["id"] in args.job_id]
        jobs = round_robin(jobs)
        existing = {r["job_id"] for r in result["records"] if "job_id" in r}
        pending = [j for j in jobs if j["id"] not in existing]
        if args.mode == "captions":
            raw = args.raw_dir.resolve()
            if inside_git(raw):
                p.error("raw captions must be outside all Git checkouts")
            raw.mkdir(parents=True, exist_ok=True)
        for job in pending[:args.max_jobs]:
            try:
                if args.mode == "captions":
                    record = captions(job, raw)
                elif args.mode == "metadata":
                    record = metadata(job)
                else:
                    record = discover(job, args.per_job)
            except Exception as error:
                msg = sanitize(error)
                record = {"status": "blocked" if is_block(msg) else "failed", "error_type": type(error).__name__, "error": msg}
            record = dict(record)
            record.update(job_id=job["id"], retrieved_at=now(), input_provenance={k: v for k, v in job.items() if k != "status"})
            result["records"].append(record)
            write(output, result)
            if record["status"] == "blocked":
                result["blocked"] = True
                break
            time.sleep(0.5)
        result["planned_jobs"] = len(jobs)
        result["selected_limit"] = args.max_jobs
        result["unattempted_jobs"] = sum(j["id"] not in {r.get("job_id") for r in result["records"]} for j in jobs)
    current = result["records"][first_this_run:]
    result["blocked"] |= any(x["status"] == "blocked" for x in current)
    result["has_blocked_history"] = any(x["status"] == "blocked" for x in result["records"])
    result["finished_at"] = now()
    result["successful_operations"] = sum(x["status"] == "success" for x in result["records"])
    result["attempted_this_run"] = len(current)
    result.setdefault("run_history", []).append({"started_at": result["started_at"], "finished_at": result["finished_at"],
                                               "attempted": len(current), "blocked": result["blocked"]})
    write(output, result)
    print(json.dumps({k: v for k, v in result.items() if k != "records"}))
    return 2 if any(x["status"] != "success" for x in current) else 0


if __name__ == "__main__":
    sys.exit(main())
