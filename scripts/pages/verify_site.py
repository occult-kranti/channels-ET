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


def verify_access_repair(payloads: dict[str, bytes], file_manifest: dict) -> dict:
    """Check the separate dated supplement without rerunning access/media probes."""
    def load(name: str):
        return json.loads(payloads["dist/research/" + name])
    bundle = load("data.json")
    repair = bundle["harvest"]["accessRepair"]
    bindings = {
        "watchProbe": "access-repair-watch-probe.json", "proxyResponse": "access-repair-proxy-response.json",
        "browser": "access-repair-browser-verification.json", "primarySources": "access-repair-primary-sources.json",
        "athinaPublisher": "access-repair-athina-audio.json", "athinaExecution": "access-repair-athina-asr-execution.json",
        "athinaAsr": "access-repair-athina-asr.json",
    }
    for key, name in bindings.items():
        assert repair[key] == load(name), f"Supplement differs from downloadable source: {name}"
    artifacts = {a["path"]: a for a in bundle["artifacts"] if a["path"].startswith("access-repair-")}
    assert set(bindings.values()).issubset(artifacts), "Missing supplement download metadata"
    for name, artifact in artifacts.items():
        source = file_manifest["dist/research/" + name]
        assert artifact["bytes"] == source["bytes"] and artifact["sha256"] == source["sha256"], name
    watch, proxy, browser = (repair[k] for k in ("watchProbe", "proxyResponse", "browser"))
    assert watch["status"] == "request_failed" and watch["proxyTunnelDenied"] is True
    assert watch["tlsVerificationEnabled"] is True and watch["proxyConfigurationPreserved"] is True
    assert proxy["proxyConnectStatus"] == 403 and proxy["originTlsStarted"] is False
    assert browser["passed"] is True and browser["ignoreHTTPSErrors"] is False
    assert browser["inheritedProxyUsed"] is True and browser["youtubeRequests"] == 0
    assert {c["id"] for c in browser["controls"]} == {"github_pages", "publisher_rss"}
    assert all(c["status"] == 200 and c["tlsVerifiedResponse"] is True for c in browser["controls"])
    negative = browser["unrelatedCertificateControl"]
    assert negative["passed"] is True and negative["imported"] is False
    assert "ERR_CERT_AUTHORITY_INVALID" in negative["navigationError"]
    assert negative["httpRequestsReachedFixture"] == 0 and negative["externalNavigations"] == 0
    primary = repair["primarySources"]
    assert primary["youtube_requests"] == 0 and primary["fixed_nineteen_episode_study_changed"] is False
    daniel, paul, athina_feed = (primary[k] for k in ("daniel", "paul", "athina"))
    assert len(daniel["items"]) == daniel["items_extracted"]
    assert sum(r["text"]["word_count"] for r in daniel["items"]) == daniel["total_rendered_item_words"]
    assert all(r["entity_origin_or_transcription_accuracy_verified"] is False for r in daniel["items"])
    assert paul["status"] == "retrieved" and paul["http_status"] == 200 and paul["pdf_magic_verified"] is True
    assert paul["tls_certificate_verification_enabled"] is True and paul["full_text_publicly_rehosted"] is False
    assert paul["pages"] > 0 and paul["text"]["word_count"] > 0
    assert paul["source_kind"] == "publisher_issued_spiritual_Guides_transcript"
    assert paul["human_transcription_or_speaker_accuracy_verified"] is False
    publisher, execution, asr = (repair[k] for k in ("athinaPublisher", "athinaExecution", "athinaAsr"))
    completed = [r for r in publisher["records"] if r["status"] == "completed"]
    assert publisher["terminal"] is True and publisher["not_youtube_downloads"] is True and publisher["youtube_requests"] == 0
    assert len(completed) == publisher["completed_audio_files"]
    assert sum(r["bytes"] for r in completed) == publisher["completed_audio_bytes"]
    assert math.isclose(sum(r["duration_seconds"] for r in completed), publisher["completed_audio_seconds"], abs_tol=1e-5)
    assert asr["status"] == "completed" and asr["transcribedScope"] == "full_decoded_audio"
    source = next((r for r in completed if r["source_id"] == asr["sourceId"]
                   and r["sha256"] == asr["sourceAudioSha256"] and r["enclosure_url"] == asr["sourceUrl"]), None)
    assert source is not None, "Supplement ASR/audio source join mismatch"
    assert source["audio_rehosted_publicly"] is False and source["tls_verified"] is True
    assert math.isclose(source["duration_seconds"], asr["sourceAudioDurationSeconds"], abs_tol=1e-5)
    assert source["source_proof"]["sha256"] == file_manifest["dist/research/access-repair-primary-sources.json"]["sha256"]
    assert source["feed_sha256"] == athina_feed["response"]["sha256"]
    assert athina_feed["unique_exact_episode_present"] is True and len(athina_feed["exact_episode_matches"]) == 1
    episode = athina_feed["exact_episode_matches"][0]
    assert episode["enclosure"]["url"] == source["enclosure_url"]
    assert episode["link"] == source["source_proof"]["creator_episode_url"]
    for record in (asr["publisherAcquisitionRecord"], asr["executionProtocol"]):
        assert record["sourceId"] == source["source_id"] and record["audioSha256"] == source["sha256"]
        assert record.get("enclosureUrl", record.get("sourceUrl")) == source["enclosure_url"]
    assert execution["status"] == "completed" and execution["networkRequests"] == 0
    assert execution["originalNineteenCohortMutated"] is False
    assert execution["sourceId"] == asr["sourceId"] and execution["audioSha256"] == asr["sourceAudioSha256"]
    assert execution["coreSha256"] == asr["executionProtocol"]["scriptSha256"]
    assert execution["sourceLedgerSha256"] == file_manifest["dist/research/access-repair-athina-audio.json"]["sha256"]
    assert execution["publicReceiptSha256"] == file_manifest["dist/research/access-repair-athina-asr.json"]["sha256"]
    assert execution["segments"] == asr["segments"] and execution["words"] == asr["words"]
    assert math.isclose(execution["sourceAudioDurationSeconds"], asr["sourceAudioDurationSeconds"], abs_tol=1e-5)
    assert {r["name"] for r in asr["outputs"]} == {"segments.jsonl", "transcript.txt", "transcript.srt"}
    for key in ("humanReviewed", "speakerDiarizationPerformed", "youtubeVideoEditionVerified"):
        assert asr[key] is False, f"Review supplement interpretation before changing {key}"
    assert execution["humanAccuracyValidated"] is False and execution["youtubeEditionEquivalenceVerified"] is False
    assert asr["sourceId"] not in {r["source_id"] for r in bundle["harvest"]["publisherAudio"]["records"]}
    frozen_receipt = Path(__file__).resolve().parents[2] / "research/deployment/final-live-verification.json"
    frozen = {r["route"]: r["sha256"] for r in json.loads(frozen_receipt.read_text())["live_http"]["routes"]}
    old_cohort = ("dist/research/harvest-publisher-audio.json", "dist/research/harvest-asr-summary.json")
    assert all(file_manifest[p]["sha256"] == frozen[p] for p in old_cohort), "Original cohort changed inside separate supplement"
    return {
        "status": "passed", "scope": "Public supplement metadata and retained probe receipts; no live media/access probe rerun",
        "download_artifact_bindings": len(artifacts), "network_probe_revision": watch["runtimeObservationBeforeProbe"]["specRevision"],
        "recorded_proxy_connect_status": proxy["proxyConnectStatus"], "recorded_origin_tls_started": proxy["originTlsStarted"],
        "browser_recorded_https_controls": len(browser["controls"]), "browser_unrelated_certificate_rejection": True,
        "browser_recorded_explicit_youtube_operations": browser["youtubeRequests"], "daniel_rss_items": len(daniel["items"]),
        "daniel_reported_rendered_words": daniel["total_rendered_item_words"], "paul_reported_pdf_pages": paul["pages"],
        "paul_reported_words": paul["text"]["word_count"], "paul_scope": paul["scope"],
        "athina_audio_files": len(completed), "athina_audio_bytes": publisher["completed_audio_bytes"],
        "athina_audio_seconds": publisher["completed_audio_seconds"], "athina_asr_words": asr["words"],
        "athina_asr_segments": asr["segments"], "athina_source_join": asr["sourceId"],
        "original_cohort_public_metadata_hashes_preserved": list(old_cohort),
    }


def verify_current_collection(payloads: dict[str, bytes], file_manifest: dict) -> dict:
    """Reconcile the current plan and diagnostics without contacting source services."""
    root = Path(__file__).resolve().parents[2]
    bindings = json.loads((root / "research/youtube-access/dashboard/input-manifest.json").read_text())["inputs"]
    def body(name: str) -> bytes:
        return payloads["dist/research/" + name]
    def load(name: str):
        return json.loads(body(name))
    bundle = load("data.json")
    sources = bundle["harvest"]["currentSupplement"]["sources"]
    artifacts = {a["path"]: a for a in bundle["artifacts"]}
    for row in bindings:
        name = row["target"]
        assert name.startswith("youtube-access-") and "/" not in name, "Unsafe supplement filename"
        actual = file_manifest["dist/research/" + name]
        assert digest(body(name)) == row["sha256"] == actual["sha256"] == artifacts[name]["sha256"], name
        source = (root / row["source"]).resolve()
        assert source.is_relative_to(root) and digest(source.read_bytes()) == row["sha256"], f"Current source differs from published binding: {row['source']}"
        assert len(body(name)) == actual["bytes"] == artifacts[name]["bytes"], name
        if row.get("key"):
            assert sources[row["key"]] == load(name), f"Dashboard/source mismatch: {name}"
    selection = [json.loads(line) for line in body("youtube-access-selection.jsonl").splitlines() if line.strip()]
    selected = [json.loads(line) for line in body("youtube-access-selected-default.jsonl").splitlines() if line.strip()]
    policy = sources["policy"]
    definition = sources["policyDefinition"]
    counts = policy["all_upload_ids"]
    assert len(selection) == len({r["video_id"] for r in selection}) == counts["indexed"]
    assert counts["indexed"] == sum(counts[k] for k in ("eligible", "under_minimum", "unknown_duration", "conflicting_duration"))
    assert len(selected) == len({r["video_id"] for r in selected})
    assert {r["video_id"] for r in selected} == {r["video_id"] for r in selection if r["selected_default"]}
    assert all(r["eligible_on_inherited_metadata"] and r["duration_seconds"] >= 300 and not r["shorts_evidence"]
               and r["metadata_refresh_required"] is True for r in selected)
    bashar_selected = sum(r["classification"] == "explicit_bashar_association" for r in selected)
    assert bashar_selected <= 100 and definition["minimum_duration_seconds"] == 300
    assert definition["bashar_youtube_upload_cap"] == 100 and definition["other_practitioner_limit"] is None
    assert sum(r["eligible_on_inherited_metadata"] for r in selection) == counts["eligible"]
    assert sum(r["classification"] == "explicit_bashar_association" for r in selection) == policy["explicit_bashar_association"]["indexed"]
    assert all(not r["selected_default"] for r in selection if r["classification"] == "ambiguous_bashar_context")
    assert policy["downloads_performed_by_this_layer"] == 0
    assert policy["whole_channel_lifetime_bashar_upload_count"] is None
    routes = load("youtube-access-bashar-routes.json")["records"]
    assert len(routes) == policy["bashar_relevant_literal_routes"]
    assert sum(r["indexed_bashar_count"] for r in routes) == policy["bashar_video_route_edges"]
    assert len(set().union(*(set(r["known_bashar_video_ids"]) for r in routes))) == policy["bashar_ids_with_any_route"]
    watch, control = sources["braveWatch"], sources["braveControl"]
    assert watch["ordinaryWatchNavigations"] == watch["targetConnectRequestsObserved"] == 1
    assert watch["proxyConnectStatus"] == 403 and watch["responses"] == []
    assert watch["ignoreHTTPSErrors"] is False and watch["proxyConfigurationPreserved"] is True
    assert control["passed"] is True and control["ignoreHTTPSErrors"] is False
    drive = sources["drive"]
    assert drive["actual_drive_uploaded_files"] == drive["actual_drive_upload_attempts"] == 0
    assert drive["actual_drive_folder_created"] is False and drive["actual_quota_checked"] is False
    archive = load("youtube-access-drive-plan.json")
    assert archive["canonical_file_count"] == len(archive["files"]) == drive["plan"]["canonical_file_count"]
    assert archive["canonical_bytes"] == sum(r["bytes"] for r in archive["files"]) == drive["plan"]["canonical_bytes"]
    assert Counter(r["kind"] for r in archive["files"]) == archive["kinds"]
    assert archive["uploaded_files"] == 0 and archive["drive_folder_created"] is False
    runner, dry_run = sources["runnerSummary"], sources["runnerDryRun"]
    runner_plan_name = next(r["target"] for r in bindings if r["source"] == "research/collection-runner/plan.jsonl")
    jobs = [json.loads(line) for line in body(runner_plan_name).splitlines() if line.strip()]
    assert runner["items"] == len(selection) and runner["jobs"] == len(jobs)
    assert dict(Counter(j["kind"] for j in jobs)) == runner["by_kind"]
    assert len({j["job_id"] for j in jobs}) == len(jobs)
    source_sets = {kind: {j["source_id"] for j in jobs if j["kind"] == kind} for kind in runner["by_kind"]}
    assert source_sets["metadata"] == {r["source_id"] for r in selection}
    assert source_sets["video"] == source_sets["captions"] == {r["source_id"] for r in selected}
    assert all(j["attempts"] == 0 and j["status"] == "queued" for j in jobs)
    assert runner["attempts"] == runner["verified_quarantine_artifacts"] == runner["bashar_unique_youtube_slots_used"] == 0
    assert runner["policy"]["bashar_limit"] == 100 and runner["policy"]["selection_key"] == "selected_default"
    assert dry_run["plan"] == runner and dry_run["gate"]["ready"] is False and dry_run["network_collection_requests"] == 0
    return {"status": "passed", "scope": "Source-bound metadata only; no YouTube or Drive requests",
            "download_artifact_bindings": len(bindings), "indexed_ids": len(selection),
            "default_selected_ids": len(selected), "bashar_selected_ids": bashar_selected,
            "other_selected_ids": len(selected) - bashar_selected,
            "bashar_relevant_overlapping_routes": len(routes), "complete_lifetime_count_known": False,
            "brave_target_connects": watch["targetConnectRequestsObserved"], "brave_connect_status": watch["proxyConnectStatus"],
            "planned_private_archive_files": len(archive["files"]), "drive_uploaded_files": 0,
            "policy_runner_jobs": len(jobs), "policy_runner_kind_counts": runner["by_kind"],
            "policy_runner_attempts": 0, "policy_runner_access_gate_ready": False}


def verify_transcript_study(payloads: dict[str, bytes], file_manifest: dict) -> dict:
    """Verify the published study without fetching its private corpus or audio."""
    root = Path(__file__).resolve().parents[2]
    inputs = json.loads((root / "research/transcript-dashboard/inputs.json").read_text())["inputs"]
    def body(name: str) -> bytes:
        return payloads["dist/transcripts/" + name]
    bundle = json.loads(body("data.json"))
    artifacts = {a["path"]: a for a in bundle["artifacts"]}
    for row in inputs:
        target = row["target"]
        assert not target.startswith("/") and ".." not in Path(target).parts, "Unsafe study artifact path"
        actual = file_manifest["dist/transcripts/" + target]
        assert digest(body(target)) == row["sha256"] == actual["sha256"] == artifacts[target]["sha256"], target
        source = (root / row["source"]).resolve()
        assert source.is_relative_to(root) and digest(source.read_bytes()) == row["sha256"], f"Current study source differs from published binding: {row['source']}"
        assert len(body(target)) == actual["bytes"] == artifacts[target]["bytes"], target
        if row.get("key"):
            embedded = bundle
            for key in row["key"].split("."):
                embedded = embedded[key]
            assert embedded == json.loads(body(target)), f"Interactive study/source mismatch: {target}"
    analysis, reading = bundle["analysis"], bundle["reading"]
    sources = {r["sourceId"]: r for r in analysis["sources"]}
    documents = {r["sourceId"]: r for r in reading["documents"]["documents"]}
    assert len(sources) == len(analysis["sources"]) == len(documents) == 36 and set(sources) == set(documents)
    assert Counter(r["modality"] for r in sources.values()) == {"audio_asr": 20, "publisher_text": 16}
    for source_id, row in sources.items():
        assert row["transcriptSha256"] == documents[source_id]["transcriptSha256"]
        assert row["speakerVerified"] is False and row["youtubeEditionVerified"] is False
    for fit_name, modality in (("audio", "audio_asr"), ("authored", "publisher_text")):
        fit = analysis["tfidf"][fit_name]
        ids = fit["sourceIds"]
        assert set(ids) == {r["sourceId"] for r in sources.values() if r["modality"] == modality}
        assert len(ids) == len(fit["cosine"]) and all(len(row) == len(ids) for row in fit["cosine"])
        for i, values in enumerate(fit["cosine"]):
            assert math.isclose(values[i], 1, abs_tol=1e-9)
            for k, value in enumerate(values):
                assert math.isfinite(value) and -1e-9 <= value <= 1 + 1e-9
                assert math.isclose(value, fit["cosine"][k][i], abs_tol=1e-9)
    summary = reading["summary"]
    assert summary["documents"] == 36 and summary["inspectedWindows"] == len(reading["windows"]["windows"]) == 105
    windows = {r["windowId"]: r for r in reading["windows"]["windows"]}
    candidates = reading["qa"]["records"]
    assert len(candidates) == summary["qaCandidateRecords"] == 37
    assert Counter(r["candidateKind"] for r in candidates) == summary["qaCandidateKinds"]
    for row in candidates:
        assert row["sourceId"] in sources and row["supportWindowId"] in windows
        assert windows[row["supportWindowId"]]["sourceId"] == row["sourceId"]
        assert row["sourceTranscriptSha256"] == sources[row["sourceId"]]["transcriptSha256"]
        assert row["humanValidated"] is False and row["exactQuotePublished"] is False
    assert math.isclose(summary["asrWordCoverageFraction"], summary["uniqueAsrWordsRead"] / summary["asrWordsTotal"])
    assert math.isclose(summary["publisherTextWordCoverageFraction"], summary["uniquePublisherTextWordsRead"] / summary["publisherTextWordsTotal"])
    sqlite_target = next(r["target"] for r in inputs if r["source"] == "research/transcript-reading/qa-candidates.sqlite")
    with tempfile.TemporaryDirectory(prefix="transcript-qa-deployment-check-") as temp:
        path = Path(temp) / "qa.sqlite"
        path.write_bytes(body(sqlite_target))
        with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True) as connection:
            assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            for table, count in (("documents", 36), ("windows", 105), ("codes", 10), ("document_codes", 142), ("qa_candidates", 37)):
                assert connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == count, table
    distributions = bundle["distributions"]
    archive = bundle["archive"]["state"]
    assert distributions["localArchive"] == archive
    assert archive["actual_local_archive_completed"] is True and archive["hash_verified"] is True
    assert archive["actual_local_files"] == 200 and archive["actual_local_bytes"] == 1703879268
    assert archive["actual_drive_uploaded_files"] == 0 and archive["chat_attachment_created"] is False
    assert distributions["summary"]["actualYouTubeVideos"] == analysis["summary"]["newYoutubeVideoDownloads"] == 0
    for name, rows in distributions["youtube"].items():
        assigned = set().union(*(set(r["video_ids"]) for r in rows))
        coverage = distributions["attributionCoverage"][name]
        assert coverage["indexedDenominator"] == 942 and coverage["assignedUniqueIds"] == len(assigned)
        assert coverage["unassignedUniqueIds"] == 942 - len(assigned)
        assert coverage["groupMemberships"] == sum(r["indexed_ids"] for r in rows)
    return {"status": "passed", "scope": "Published derived data/source joins and artifact bytes; no private source/media request",
            "source_bound_artifacts": len(inputs), "source_documents": len(sources),
            "asr_documents": 20, "authored_documents": 16, "inspected_windows": 105,
            "typed_qa_candidates": 37, "actual_local_archive_files": 200,
            "actual_local_archive_bytes": 1703879268, "drive_uploaded_files": 0, "youtube_downloaded_videos": 0}


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
    has_access_repair = "dist/research/access-repair-watch-probe.json" in hashes
    if has_access_repair:
        for path in hashes:
            if path.startswith("dist/research/access-repair-"):
                routes[path] = None
    has_current_collection = "dist/research/youtube-access.js" in hashes
    if has_current_collection:
        for path in hashes:
            if path.startswith("dist/research/youtube-access"):
                routes[path] = None
    has_transcript_study = "dist/transcripts/data.json" in hashes
    if has_transcript_study:
        routes[""] = b"./dist/transcripts/"
        routes["dist/transcripts/"] = b"<html"
        for path in hashes:
            if path.startswith("dist/transcripts/"):
                routes[path] = None
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
    if has_access_repair:
        report["access_repair_checks"] = verify_access_repair(payloads, hashes)
    if has_current_collection:
        report["current_collection_checks"] = verify_current_collection(payloads, hashes)
    if has_transcript_study:
        report["transcript_study_checks"] = verify_transcript_study(payloads, hashes)
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
