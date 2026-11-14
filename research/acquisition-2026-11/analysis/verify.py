#!/usr/bin/env python3
"""Verify the acquisition-2026-11 self-run ASR analysis outputs.

Every check is bound to actual artifacts: audio bytes and hashes, ASR
receipts, transcript/segment/SRT outputs, ffprobe/decoded durations, pinned
model settings, the acquisition ledger and asr-summary.json. Exits nonzero on
any failed check: missing/mismatched audio, transcript, duration or
unsupported languages are fatal.

Usage: python3 research/acquisition-2026-11/analysis/verify.py
"""
import csv
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
PRIV = Path(os.environ["CHANNELS_ET_RAW_ROOT"]) / "analysis-2026-11"
RAW = Path(os.environ["CHANNELS_ET_RAW_ROOT"]) / "youtube-audio"
CANDIDATES = REPO / "research/acquisition-2026-11/all-candidates.json"
ORIGINAL_PILOT = REPO / "research/expansion-2026/youtube-transcripts/pilot-videos.json"
LEDGER = REPO / "research/acquisition-2026-11/acquisition-ledger.json"
ASR_SUMMARY = REPO / "research/acquisition-2026-11/asr-summary.json"
MODEL_MANIFEST = REPO / "research/harvest/asr/model-manifest.json"
CODE_EDITIONS = REPO / "research/acquisition-2026-11/asr-code-editions.json"
TRANSCRIBE_CODE = REPO / "research/acquisition-2026-11/transcribe_youtube.py"

checks = []


def check(name, ok, detail=""):
    checks.append({"check": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(("PASS" if ok else "FAIL"), name, "-", detail)


def sha256_path(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(chunk):
            h.update(b)
    return h.hexdigest()


def load_reuse_media():
    if os.environ.get("CHANNELS_ET_REVERIFY_AUDIO") != "0":
        return {}
    path = REPO / "research/acquisition-2026-11/verification-reuse.json"
    payload = json.loads(path.read_text())
    if payload.get("nFailed") != 0 or payload.get("fullHashRerun") is not False:
        raise RuntimeError("verification-reuse.json is not a passing consistency receipt")
    return {r["videoId"]: (r["earlierFullAudioSha256"], r["bytes"])
            for r in payload["validatedMedia"]}


REUSE_MEDIA = load_reuse_media()


def audio_sha256(video_id, path):
    reused = REUSE_MEDIA.get(video_id)
    if reused and path.exists() and not path.is_symlink() and path.stat().st_size == reused[1]:
        return reused[0]
    return sha256_path(path)


GERMAN_MARKERS = set("""der die das und ist nicht ich sie mit den von zu auf ein
eine auch für an werden dem wie wir sind es war hat bei im des zum oder aus als
haben dass sich so nur noch über kann aber wenn nach um am vor einer einem einen
wurden""".split())
ENGLISH_MARKERS = set("""the and is of to in that it for on with as are was at be
this have from or one had by but not what all were they we when your can said
there use an each which she do how their if will up other about out many then
them these so some""".split())
ARABIC_RE = re.compile(r"[\u0621-\u063A\u0641-\u064A\u0671-\u06D3]")
LATIN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")


def detect_language(text):
    arabic_chars = len(ARABIC_RE.findall(text))
    latin_chars = len(LATIN_RE.findall(text))
    if arabic_chars >= 40 and arabic_chars > 2 * max(1, latin_chars):
        return "ar"
    toks = re.findall(r"[a-zA-ZäöüÄÖÜß]+", text.lower())
    if not toks:
        return "unknown"
    n = len(toks)
    de = sum(1 for t in toks if t in GERMAN_MARKERS) / n
    en = sum(1 for t in toks if t in ENGLISH_MARKERS) / n
    if de > en and de > 0.08:
        return "de"
    if en > 0.08:
        return "en"
    return "unknown"


candidate_rows = json.loads(CANDIDATES.read_text())
candidates = {v["video_id"]: v for v in candidate_rows}
candidate_ids = sorted(candidates)
check("candidate list has unique video IDs", len(candidates) == len(candidate_rows),
      f"rows={len(candidate_rows)} unique={len(candidates)}")
ledger = {r.get("video_id", r.get("videoId")): r
          for r in json.loads(LEDGER.read_text())["records"]}
EXPECTED_TERMINAL_STATES = {
    **{vid: "excluded_under_300" for vid in (
        "-HH8KFobnHk", "6eZDJwSzj3Y", "DfBrQbKIWHg", "GV8PXtHeBk8",
        "Rus5nLjg8ZE", "VvOZKNFKbmo", "hSlyR0POnFw")},
    "-KVKPRLFte4": "excluded_language_mismatch",
    "8WHAw-wIuQg": "held_route_limit_over_150_minutes",
}
manifest = json.loads(MODEL_MANIFEST.read_text())
EXPECTED_SETTINGS = {
    "language": "en", "beam_size": 1, "vad_filter": True,
    "condition_on_previous_text": False, "device": "cpu", "compute_type": "int8",
    "modelId": "Systran/faster-whisper-tiny.en", "revision": manifest["revision"],
    "chunkSeconds": 300,
    "chunkingNote": ("Every sample is decoded once to 16 kHz mono and transcribed "
                     "in contiguous 300 s windows; timestamps are offset-stitched. "
                     "Window-boundary words can be split; this is a recorded limitation."),
}
EXPECTED_SETTINGS_SHA256 = hashlib.sha256(
    json.dumps(EXPECTED_SETTINGS, sort_keys=True).encode()).hexdigest()
code_manifest = json.loads(CODE_EDITIONS.read_text())
code_editions = {row["sha256"]: row for row in code_manifest["editions"]}
code_snapshot_bad = []
for code_hash, row in code_editions.items():
    snapshot = row.get("snapshotPath")
    if row.get("sourceSnapshotVerified"):
        expected_snapshot_hash = row.get("snapshotSha256", code_hash)
        snapshot_path = REPO / snapshot if snapshot else None
        if (not snapshot_path or not snapshot_path.exists()
                or sha256_path(snapshot_path) != expected_snapshot_hash
                or not row.get("snapshotTransformation")
                or any(marker in snapshot_path.read_bytes()
                       for marker in (b"/" + b"mnt/agents/", b"/" + b"workspace/",
                                          b"/" + b"home/", b"/" + b"Users/"))):
            code_snapshot_bad.append(code_hash)
    elif snapshot:
        code_snapshot_bad.append(f"{code_hash}:unverified-has-snapshot")
check("every available ASR code-edition snapshot recomputes to its manifest hash",
      not code_snapshot_bad, str(code_snapshot_bad))
check("current transcriber edition is registered without implying legacy source equivalence",
      sha256_path(TRANSCRIBE_CODE) in code_editions and
      "not a claim of source-code equivalence" in code_manifest["reusePolicy"] and
      "snapshotSha256" in code_manifest.get("snapshotPolicy", ""))

# ---- required files
required = ["protocol.json", "analysis.json", "non-bashar-public.sqlite",
            "non-bashar-public.csv", "sources-index.csv", "common-questions.csv",
            "manual-review.json", "qualitative-synthesis.md", "gate-status.json"]
for f in required:
    check(f"exists:{f}", (ROOT / f).exists())
analysis = json.loads((ROOT / "analysis.json").read_text())
review = json.loads((ROOT / "manual-review.json").read_text())
gate = json.loads((ROOT / "gate-status.json").read_text())
check("build gate was satisfied at build time", gate.get("ready") is True, str(gate))
expected_candidate_hash = hashlib.sha256("\n".join(candidate_ids).encode()).hexdigest()
check("gate is bound to the exact current candidate set",
      gate.get("candidateVideos") == len(candidate_ids) and
      gate.get("candidateIdsSha256") == expected_candidate_hash,
      f"gateCandidates={gate.get('candidateVideos')} current={len(candidate_ids)}")

# ---- gate: every candidate has a terminal acquisition/ASR/hold state
summary = json.loads(ASR_SUMMARY.read_text())
smap = {r.get("videoId"): r for r in summary.get("records", [])}
gate_bad = []
for vid in candidate_ids:
    candidate = candidates[vid]
    lg = ledger.get(vid)
    s = smap.get(vid)
    if candidate.get("selection") == "held_route_limit_over_150_minutes":
        if lg and lg.get("status") == "completed":
            gate_bad.append(f"{vid}:hold-conflicts-with-completed-acquisition")
        if s and s.get("status") == "completed":
            gate_bad.append(f"{vid}:hold-conflicts-with-completed-ASR")
        if (RAW / vid / "audio.mp3").exists():
            gate_bad.append(f"{vid}:hold-has-audio")
        continue
    if not lg:
        gate_bad.append(f"{vid}:acquisition-absent")
        continue
    status = lg.get("status")
    if status == "excluded_under_300":
        duration = lg.get("durationSeconds", lg.get("duration_seconds"))
        if not isinstance(duration, (int, float)) or not 0 < duration < 300:
            gate_bad.append(f"{vid}:invalid-under-300-duration")
        if s and s.get("status") == "completed":
            gate_bad.append(f"{vid}:under-300-has-completed-ASR")
    elif status == "excluded_language_mismatch":
        if not s or s.get("status") != "excluded_language_mismatch":
            gate_bad.append(f"{vid}:language-exclusion-not-in-ASR-summary")
    elif status == "completed":
        if not s or s.get("status") != "completed":
            gate_bad.append(f"{vid}:ASR-{s.get('status') if s else 'absent'}")
    else:
        gate_bad.append(f"{vid}:nonterminal-{status}")
check(f"all {len(candidate_ids)} candidates have terminal acquisition/ASR/hold states",
      not gate_bad, str(gate_bad))
terminal_identity_bad = []
for vid, expected in EXPECTED_TERMINAL_STATES.items():
    actual = (candidates.get(vid, {}).get("selection")
              if expected.startswith("held_") else (ledger.get(vid) or {}).get("status"))
    if actual != expected:
        terminal_identity_bad.append(f"{vid}:{actual}!={expected}")
check("known under-300, language, and route-limit identities cannot silently change state",
      not terminal_identity_bad, str(terminal_identity_bad))
receipt_code_ids = {r.get("codeSha256") for r in summary.get("records", [])}
produced_marker_bad = [code for code, row in code_editions.items()
                       if row.get("producedCurrentArtifacts") != (code in receipt_code_ids)]
check("code-edition producedCurrentArtifacts markers match actual receipts",
      not produced_marker_bad, str(produced_marker_bad))

# ---- per-candidate artifact binding (recomputed from raw bytes)
per_video_problems = {}
included_ids = {m for m in analysis["validation"]["included"]}
excluded = {e["videoId"]: e["reason"] for e in analysis["validation"]["excluded"]}
held = {e["videoId"]: e["reason"] for e in analysis["validation"].get("held", [])}
for vid in candidate_ids:
    probs = []
    d = RAW / vid
    if candidates[vid].get("selection") == "held_route_limit_over_150_minutes":
        if vid not in held or vid in included_ids or vid in excluded:
            probs.append("route-limit hold missing from held-only validation state")
        if smap.get(vid, {}).get("status") == "completed":
            probs.append("route-limit hold has completed ASR summary")
        if (d / "audio.mp3").exists():
            probs.append("route-limit hold has acquired audio")
        held_receipt = d / "asr-receipt.json"
        if held_receipt.exists() and json.loads(held_receipt.read_text()).get("status") == "completed":
            probs.append("route-limit hold has completed ASR receipt")
        if probs:
            per_video_problems[vid] = probs
        continue
    lg0 = ledger.get(vid) or {}
    if lg0.get("status") == "excluded_under_300":
        duration = lg0.get("durationSeconds", lg0.get("duration_seconds"))
        if not isinstance(duration, (int, float)) or not 0 < duration < 300:
            probs.append("invalid under-300 duration")
        if (d / "audio.mp3").exists():
            probs.append("under-300 audio remains outside quarantine")
        if vid in included_ids or "300" not in excluded.get(vid, ""):
            probs.append("under-300 record lacks explicit analysis exclusion")
        if probs:
            per_video_problems[vid] = probs
        continue
    paths = {n: d / n for n in ("acquisition.json", "audio.mp3", "asr-receipt.json",
                                "asr-segments.jsonl", "asr-transcript.txt",
                                "asr-transcript.srt")}
    for n in ("acquisition.json", "audio.mp3", "asr-receipt.json"):
        if not paths[n].exists():
            probs.append(f"missing {n}")
    if probs:
        per_video_problems[vid] = probs
        continue
    acq = json.loads(paths["acquisition.json"].read_text())
    receipt = json.loads(paths["asr-receipt.json"].read_text())
    if receipt.get("status") == "excluded_language_mismatch":
        # unsupported-language terminal state: quarantine receipt is the evidence
        a_sha_q = audio_sha256(vid, paths["audio.mp3"])
        if receipt.get("detectedLanguage") in (None, "en"):
            probs.append("quarantine receipt lacks non-English detection evidence")
        if a_sha_q != receipt.get("audioSha256") or a_sha_q != acq.get("sha256"):
            probs.append("quarantine receipt/audio/acquisition hash mismatch")
        s = smap.get(vid) or {}
        qdir = d / "quarantine"
        output_hashes = s.get("outputSha256") or {}
        expected_qoutputs = {"asr-transcript.txt", "asr-segments.jsonl",
                             "asr-transcript.srt", "asr-segments.partial.jsonl"}
        qbound = qdir.is_dir() and set(output_hashes) == expected_qoutputs and all(
            (qdir / n).exists() and sha256_path(qdir / n) == h
            for n, h in output_hashes.items())
        if receipt.get("settingsSha256") != EXPECTED_SETTINGS_SHA256:
            probs.append("quarantine settings hash mismatch")
        if receipt.get("codeSha256") not in code_editions:
            probs.append("quarantine code edition is not allowlisted")
        if s.get("status") != "excluded_language_mismatch":
            probs.append(f"summary status {s.get('status')} for quarantined video")
        if not qbound or receipt.get("outputSha256") != output_hashes:
            probs.append("quarantined outputs are not hash-bound to summary/receipt")
        if vid in included_ids:
            probs.append("quarantined unsupported-language video was included")
        if vid not in excluded or "unsupported language" not in excluded.get(vid, ""):
            probs.append("quarantined video missing explicit unsupported-language exclusion")
        if probs:
            per_video_problems[vid] = probs
        continue
    for n in ("asr-segments.jsonl", "asr-transcript.txt", "asr-transcript.srt"):
        if not paths[n].exists():
            probs.append(f"missing {n}")
    if probs:
        per_video_problems[vid] = probs
        continue
    audio = paths["audio.mp3"]
    a_sha = audio_sha256(vid, audio)
    if audio.is_symlink():
        probs.append("audio is symlink")
    if acq.get("sha256") != a_sha or receipt.get("audioSha256") != a_sha:
        probs.append("audio hash mismatch acquisition/receipt")
    lg = ledger.get(vid)
    if not lg or lg.get("sha256") != a_sha or lg.get("status") != "completed":
        probs.append("ledger missing/not completed/hash mismatch")
    if audio.stat().st_size != acq.get("bytes") or receipt.get("audioBytes") != audio.stat().st_size:
        probs.append("audio bytes mismatch")
    if abs((acq.get("duration_seconds") or 0) - (receipt.get("ffprobeDurationSeconds") or -9)) > 0.5:
        probs.append("acquisition vs ffprobe duration mismatch")
    if abs((receipt.get("decodedDurationSeconds") or 0) - (receipt.get("ffprobeDurationSeconds") or -9)) > 1.0:
        probs.append("decoded vs ffprobe duration mismatch")
    if (receipt.get("chunksProcessed") or 0) * 300 < (receipt.get("decodedDurationSeconds") or 1) - 1e-6:
        probs.append("decode windows do not cover full audio")
    for k, v in EXPECTED_SETTINGS.items():
        if (receipt.get("settings") or {}).get(k) != v:
            probs.append(f"setting {k} mismatch")
    if receipt.get("settingsSha256") != EXPECTED_SETTINGS_SHA256:
        probs.append("settingsSha256 mismatch")
    edition = code_editions.get(receipt.get("codeSha256"))
    if not edition or edition.get("compatibleReuse") is not True:
        probs.append("ASR codeSha256 is not allowlisted")
    if receipt.get("sourceType") != "public_youtube_audio_self_run_ASR":
        probs.append("sourceType mismatch")
    segs = [json.loads(l) for l in paths["asr-segments.jsonl"].read_text().splitlines() if l.strip()]
    if len(segs) != receipt.get("segmentCount"):
        probs.append("segmentCount mismatch")
    txt = paths["asr-transcript.txt"].read_text()
    if len(txt.split()) != receipt.get("wordCount"):
        probs.append("wordCount mismatch")
    n_srt = len(re.findall(r"\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d",
                           paths["asr-transcript.srt"].read_text()))
    if n_srt != len(segs):
        probs.append("SRT cue count mismatch")
    output_hashes = receipt.get("outputSha256") or {}
    if set(output_hashes) != {"asr-transcript.txt", "asr-segments.jsonl", "asr-transcript.srt"}:
        probs.append("completed receipt does not bind exactly three ASR outputs")
    for n, h in output_hashes.items():
        if sha256_path(d / n) != h:
            probs.append(f"output hash mismatch {n}")
    s = smap.get(vid) or {}
    if s.get("outputSha256") != receipt.get("outputSha256") or s.get("audioSha256") != a_sha:
        probs.append("asr-summary not bound to receipt/outputs")
    last_end = max(float(r["end"]) for r in segs) if segs else 0.0
    if abs(last_end - (receipt.get("lastSegmentEnd") or -9)) > 0.01:
        probs.append("lastSegmentEnd mismatch")
    cov = last_end / (receipt.get("ffprobeDurationSeconds") or 1)
    lang = detect_language(txt)
    wpm = len(txt.split()) / ((receipt.get("ffprobeDurationSeconds") or 1) / 60)
    if vid in included_ids:
        if cov < 0.75:
            probs.append(f"included despite ASR coverage {cov:.3f} < 0.75")
        if lang != "en":
            probs.append(f"included despite detected language {lang}")
        if wpm < 45:
            probs.append(f"included despite degenerate {wpm:.1f} wpm output")
        if receipt.get("detectedLanguage") != "en" or \
                receipt.get("languageReviewRequired") is not False or \
                not isinstance(receipt.get("wordRateWpm"), (int, float)) or \
                receipt.get("wordRateWpm") < 45 or \
                not isinstance(receipt.get("languageVerified"), bool):
            probs.append("included receipt lacks complete English language metadata")
    elif vid in excluded:
        unsupported = (lang != "en") or wpm < 45
        low_coverage = cov < 0.75
        if unsupported and "unsupported language" not in excluded[vid]:
            probs.append("excluded for language/degenerate output but reason does not say so")
        if low_coverage and "coverage" not in excluded[vid]:
            probs.append("excluded for low ASR coverage but reason does not say so")
        if not unsupported and not low_coverage:
            probs.append("valid completed English source excluded without an independent artifact reason")
    else:
        probs.append("candidate neither included nor excluded with reason")
    if probs:
        per_video_problems[vid] = probs
check(f"all {len(candidate_ids)} candidate artifacts and terminal states bind",
      not per_video_problems, json.dumps(per_video_problems)[:380])
check("included + excluded + held exactly covers every candidate once",
      included_ids.isdisjoint(excluded) and included_ids.isdisjoint(held) and
      set(excluded).isdisjoint(held) and
      included_ids | set(excluded) | set(held) == set(candidate_ids),
      f"included={len(included_ids)} excluded={len(excluded)} held={len(held)} "
      f"candidates={len(candidate_ids)}")
terminal = analysis["validation"].get("terminalStateCounts", {})
check("audio evidence mode is explicit when full hashes are reused",
      analysis["validation"].get("audioEvidenceMode") ==
      ("earlier_full_hash_plus_current_receipts" if REUSE_MEDIA else "full_rehash"),
      analysis["validation"].get("audioEvidenceMode", "missing"))
check("analysis terminal-state accounting matches validated partitions",
      terminal.get("analyzed") == len(included_ids) and
      terminal.get("excluded") == len(excluded) and
      terminal.get("held") == len(held) and
      terminal.get("totalCandidates") == len(candidate_ids), str(terminal))

# ---- private index exists with exact text; public outputs have no bodies
priv_db = PRIV / "segment-index.sqlite"
check("private segment-index.sqlite exists under analysis-2026-11", priv_db.exists())
con = sqlite3.connect(priv_db)
n_src = con.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
n_seg = con.execute("SELECT COUNT(*) FROM segments").fetchone()[0]
check("private index rows match analysis", n_src == analysis["nDocuments"],
      f"sources={n_src} docs={analysis['nDocuments']}; segments={n_seg}")
con.close()

pcon = sqlite3.connect(ROOT / "non-bashar-public.sqlite")
cols = [r[1] for r in pcon.execute("PRAGMA table_info(qa_candidates)")]
check("public qa_candidates has no text columns",
      "question_text" not in cols and "answer_text" not in cols, str(cols))
n_pub_src = pcon.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
n_pub_qa = pcon.execute("SELECT COUNT(*) FROM qa_candidates").fetchone()[0]
check("public registry source count == included count",
      n_pub_src == len(analysis["validation"]["included"]),
      f"{n_pub_src} vs {len(analysis['validation']['included'])}")
completed_candidates = {vid for vid in candidate_ids
                        if (ledger.get(vid) or {}).get("status") == "completed"}
check("public sources exactly match ledger-completed candidates admitted by artifact validation",
      n_pub_src == len(included_ids & completed_candidates) and
      included_ids <= completed_candidates,
      f"sources={n_pub_src} included={len(included_ids)} completed={len(completed_candidates)}")
expected_segments = pcon.execute("SELECT COALESCE(SUM(segment_count), 0) FROM sources").fetchone()[0]
check("private segment count equals source segment-count sum", n_seg == expected_segments,
      f"segments={n_seg} expected={expected_segments}")
check("public qa count == analysis total units",
      n_pub_qa == analysis["qa"]["totalUnits"],
      f"{n_pub_qa} vs {analysis['qa']['totalUnits']}")
priv = sqlite3.connect(PRIV / "qa-full.sqlite")
orphan = 0
for (u,) in pcon.execute("SELECT unit_id FROM qa_candidates"):
    if not priv.execute("SELECT 1 FROM qa WHERE unit_id=?", (u,)).fetchone():
        orphan += 1
check("every public qa hash links to private full row", orphan == 0, f"orphans={orphan}")
scols = [r[1] for r in pcon.execute("PRAGMA table_info(sources)")]
check("public sources table has no transcript body columns",
      not any(c in scols for c in ("text", "body", "transcript")), str(scols)[:200])
check("uploader/practitioner/claimed-entity kept as distinct columns",
      all(c in scols for c in ("publisher", "practitioner_context", "claimed_group")))
role_rows = pcon.execute(
    "SELECT COUNT(*) FROM sources WHERE publisher != practitioner_context "
    "AND practitioner_context != claimed_group").fetchone()[0]
check("publisher != practitioner != claimed entity in practice", role_rows >= 1,
      f"distinct-role rows={role_rows}")
original_pilot_ids = {r["video_id"] for r in json.loads(ORIGINAL_PILOT.read_text())}
exclusion_rows = list(pcon.execute(
    "SELECT video_id, in_original_pilot_list, in_candidate_list FROM validation_exclusions"))
exclusion_provenance_bad = [
    vid for vid, original, current in exclusion_rows
    if bool(original) != (vid in original_pilot_ids) or not current or vid not in candidates]
check("exclusion provenance distinguishes original pilot membership from current candidates",
      len(exclusion_rows) == len(excluded) and not exclusion_provenance_bad,
      str(exclusion_provenance_bad))

# ---- CSV consistency
rows = list(csv.DictReader(open(ROOT / "non-bashar-public.csv")))
check("public CSV row count == qa total", len(rows) == analysis["qa"]["totalUnits"])
srows = list(csv.DictReader(open(ROOT / "sources-index.csv")))
check("sources-index.csv rows == included", len(srows) == n_pub_src)
check("sources-index has audio+transcript hashes for every source",
      all(r["audio_sha256"] and r["transcript_txt_sha256"] and r["segments_sha256"]
          and r["srt_sha256"] and r["records_sha256"] and r["text_sha256"] for r in srows))
check("provider label is self_run_faster_whisper_tiny.en for every source",
      all(r["asr_provider"] == "self_run_faster_whisper_tiny.en" for r in srows))
check("sourceType is public_youtube_audio_self_run_ASR for every source",
      all(r["source_type"] == "public_youtube_audio_self_run_ASR" for r in srows))
check("model revision pinned to manifest for every source",
      all(r["model_revision"] == manifest["revision"] for r in srows))

# ---- registry hashes match raw artifacts on disk
mismatch = []
for r in srows:
    d = RAW / r["video_id"]
    for col, name in (("audio_sha256", "audio.mp3"),
                      ("transcript_txt_sha256", "asr-transcript.txt"),
                      ("segments_sha256", "asr-segments.jsonl"),
                      ("srt_sha256", "asr-transcript.srt")):
        p = d / name
        actual_hash = audio_sha256(r["video_id"], p) if col == "audio_sha256" else sha256_path(p)
        if not p.exists() or actual_hash != r[col]:
            mismatch.append(f"{r['video_id']}:{name}")
check("registry hashes match raw audio/transcript/segments/SRT files", not mismatch,
      str(mismatch)[:300])
code_binding_bad = []
for r in srows:
    receipt_path = RAW / r["video_id"] / "asr-receipt.json"
    receipt = json.loads(receipt_path.read_text())
    if r["code_sha256"] != receipt.get("codeSha256") or \
            r["code_sha256"] not in code_editions:
        code_binding_bad.append(r["video_id"])
check("source-registry code hashes bind to receipts and the edition manifest",
      not code_binding_bad, str(code_binding_bad))
# candidate metadata consistency
meta_bad = [r["video_id"] for r in srows
            if r["title"] != candidates[r["video_id"]]["title"]
            or r["publisher"] != candidates[r["video_id"]]["publisher"]]
check("sources-index title/publisher match candidate list", not meta_bad, str(meta_bad))

# ---- source-boundary fields
bad = [r["video_id"] for r in srows if r["human_validated"] not in ("0", "False", 0)]
check("humanValidated=false for every source", not bad, str(bad))

# ---- no unbounded transcript-body leakage into public outputs
pub_text = ""
for f in ("non-bashar-public.csv", "sources-index.csv", "common-questions.csv",
          "analysis.json", "manual-review.json", "qualitative-synthesis.md"):
    pub_text += (ROOT / f).read_text()
# SQLite and generated workbench HTML are also public. Bounded <=150-character
# review excerpts are allowed; any full segment longer than 150 chars is not.
pub_text += (ROOT / "non-bashar-public.sqlite").read_bytes().decode("utf-8", "ignore")
workbench_html = ROOT.parents[2] / "dist/research/acquisition-2026-11/index.html"
if workbench_html.exists():
    pub_text += workbench_html.read_text()
leaks = []
con = sqlite3.connect(priv_db)
for r in srows:
    for (segment_text,) in con.execute(
            "SELECT text FROM segments WHERE video_id=? AND length(text)>150",
            (r["video_id"],)):
        if segment_text in pub_text:
            leaks.append(r["video_id"])
con.close()
check("no unbounded ASR segment text leaks into public text, SQLite, or workbench HTML",
      not leaks, str(sorted(set(leaks))))

# ---- review completeness
n_rev = len(review["items"])
total_units = analysis["qa"]["totalUnits"]
target = total_units if total_units <= 60 else 60
check("manual review covers all candidates (<=60) or a stratified >=60 sample",
      n_rev >= target, f"reviewed={n_rev} target={target}")
check("review kind is ai_agent_review (not human)",
      review.get("manualReviewKind") == "ai_agent_review")
ents_reviewed = {i["claimedGroup"] for i in review["items"]}
ents_all = {r["claimed_group"] for r in rows}
check("review spans every claimed-entity label present",
      ents_all <= ents_reviewed, f"missing={ents_all - ents_reviewed}")
verdicts = [i.get("verdict") for i in review["items"]]
check("every review item has a verdict and bounded note",
      all(v in ("confirm", "reclassify", "boundary_error") for v in verdicts) and
      all(i.get("note") and len(i["note"]) <= 240 for i in review["items"]))
check("review items contain only bounded excerpts + hashes",
      all(len(i.get("questionExcerpt", "")) <= 150 and i.get("questionSha256")
          for i in review["items"]))
review_ids = [i["unitId"] for i in review["items"]]
check("review unit IDs are unique", len(set(review_ids)) == len(review_ids),
      f"unique={len(set(review_ids))} items={len(review_ids)}")
review_mismatch = []
for item in review["items"]:
    row = priv.execute("SELECT question_sha256, video_id, claimed_group FROM qa WHERE unit_id=?",
                       (item["unitId"],)).fetchone()
    expected = (item["questionSha256"], item["videoId"], item["claimedGroup"])
    if row != expected:
        review_mismatch.append(item["unitId"])
check("every review verdict binds to current question hash and source metadata",
      not review_mismatch, str(review_mismatch))
if total_units <= 60:
    check("small-corpus review covers every current extracted unit",
          set(review_ids) == {r["unit_id"] for r in rows},
          f"reviewed={len(set(review_ids))} units={len(rows)}")

# ---- analysis structure
for key in ["tfidfTopCorpus", "nmf", "kmeansDiagnostics", "overlayByPublisher",
            "overlayByPractitioner", "overlayByClaimedGroup", "documentNetwork",
            "durationProfiles", "sensitivity", "qa", "validation",
            "tokenizationDiagnostics"]:
    check(f"analysis.json has {key}", key in analysis)
check("NMF seed stability reported",
      0 <= analysis["nmf"]["seedStabilityMeanBestMatchCosine"] <= 1.0001)
check("NMF convergence and iteration caps are explicit",
      isinstance(analysis["nmf"].get("allRunsConvergedBeforeMaxIter"), bool) and
      len(analysis["nmf"].get("randomInitIterations", [])) == 10 and
      analysis["nmf"].get("maxIter", 0) >= 600 and
      "nonconverged" in analysis["nmf"].get("caution", "").lower())
check("KMeans sweep reported with cautions",
      len(analysis["kmeansDiagnostics"]["sweep"]) >= 1 and
      "diagnostic" in analysis["kmeansDiagnostics"]["caution"])
check("all included documents detected English (pinned English-only model)",
      analysis["languages"] == {"en": analysis["nDocuments"]},
      str(analysis["languages"]))
fams = set(analysis["qa"]["familyTotals"])
check("all protocol question families represented in codebook output",
      fams <= {"contact_timing", "dna_origins", "ascension", "reality_agency",
               "healing", "dreams_contact", "predictions", "other_theme",
               "not_assessed_language"}, str(fams))
protocol = json.loads((ROOT / "protocol.json").read_text())
protocol_text = json.dumps(protocol)
check("protocol matches expanded candidates, non-self ARI, and unclassified orientation",
      "all 13 pilot" not in protocol_text and "~12-13" not in protocol_text and
      "unclassified_default" in protocol_text and "ariComparisons=9" in protocol_text and
      "held_route_limit_over_150_minutes" in protocol_text)
check("document-network threshold matches protocol",
      abs(protocol["corpusAnalysis"]["documentNetwork"].get("threshold", 0.15) -
          analysis["documentNetwork"]["threshold"]) < 1e-9,
      f"actual={analysis['documentNetwork']['threshold']}")
check("document network contains no zero-weight pseudo-edges",
      all(e["weight"] > 0 for e in analysis["documentNetwork"]["edges"]))
null_families = pcon.execute(
    "SELECT COUNT(*) FROM qa_candidates WHERE family_key IS NULL OR family_key=''").fetchone()[0]
bad_common = pcon.execute(
    "SELECT COUNT(*) FROM question_families WHERE family_key IS NULL OR family_key=''").fetchone()[0]
check("stopword-only units are family-less rows and excluded from common families",
      null_families >= 1 and bad_common == 0
      and analysis["qa"]["familylessStopwordOnlyUnits"] == null_families,
      f"nullFamilies={null_families} badCommon={bad_common}")
shared_db = pcon.execute("SELECT COUNT(*) FROM question_families WHERE n_videos>1").fetchone()[0]
within_db = pcon.execute(
    "SELECT COUNT(*) FROM question_families WHERE occurrences>1 AND n_videos=1").fetchone()[0]
check("cross-video recurrence excludes same-video-only repetitions",
      analysis["qa"]["commonQuestionFamilies"]["nSharedAcrossVideos"] == shared_db and
      analysis["qa"]["commonQuestionFamilies"]["nRepeatedWithinSingleVideo"] == within_db and
      analysis["qa"]["commonQuestionFamilies"]["nRepeatedAnywhere"] == shared_db + within_db,
      f"crossVideo={shared_db} withinSingleVideo={within_db}")
token_rows = {r["videoId"]: r for r in analysis["tokenizationDiagnostics"]}
degenerate = [v for v, r in token_rows.items()
              if r["rawTokenCount"] >= 100 and r["analysisTokenCount"] < 10]
check("no large document collapses to a degenerate analysis-token projection",
      not degenerate, f"degenerate={degenerate}")
check("proper-name exclusion is implemented",
      analysis.get("properNamesExcludedFromTfidfNmf") is True)
banned_topic_tokens = {"kryon", "ryokah", "yahyel", "galactic", "federation", "bashar"}
topic_name_leaks = [
    term for topic in analysis["nmf"]["topics"] for term in topic["topTerms"]
    if banned_topic_tokens & set(term.split())]
check("claimed-entity and practitioner brand tokens are absent from NMF top terms",
      not topic_name_leaks, str(topic_name_leaks))
# temporal/duration profiles carry per-third question placement
check("duration profiles carry temporal placement (question units by third)",
      all("questionUnitsByThird" in p for p in analysis["durationProfiles"]))

# ---- independent numerical/extraction recompute from the private segment index
# Hash chains prove which bytes were used; these checks independently recompute
# the statistics and Q&A rows so a systematic stale artifact cannot pass on
# cross-artifact consistency alone.
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, adjusted_rand_score
from sklearn.metrics.pairwise import cosine_similarity

spec = importlib.util.spec_from_file_location("acquisition_build_recompute", ROOT / "build.py")
build_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build_module)
raw_con = sqlite3.connect(priv_db)
included_order = list(analysis["validation"]["included"])
source_by_id = {r["video_id"]: r for r in srows}
docs, metas, raw_units = [], [], []
raw_word_total = raw_segment_total = 0
for vid in included_order:
    source = source_by_id[vid]
    meta = {"videoId": vid, "publisher": source["publisher"],
            "practitionerContext": source["practitioner_context"],
            "claimedGroup": source["claimed_group"],
            "detectedLanguage": source["detected_language"]}
    segment_rows = list(raw_con.execute(
        "SELECT start_seconds, end_seconds, text FROM segments WHERE video_id=? ORDER BY seg_id",
        (vid,)))
    recs = [{"startSeconds": float(a), "endSeconds": float(b), "text": t}
            for a, b, t in segment_rows]
    text = " ".join(r["text"] for r in recs)
    docs.append(text)
    metas.append(meta)
    raw_word_total += len(text.split())
    raw_segment_total += len(recs)
    raw_units.extend(build_module.extract_units(meta, recs))
raw_con.close()
check("headline document/word/segment counts recompute from private segments",
      len(docs) == analysis["nDocuments"] and
      raw_word_total == sum(p["wordCount"] for p in analysis["durationProfiles"]) and
      raw_segment_total == sum(p["segmentCount"] for p in analysis["durationProfiles"]),
      f"docs={len(docs)} words={raw_word_total} segments={raw_segment_total}")

# Q&A units, answer windows, discourse/orientation labels, and family keys.
public_unit_rows = {row[0]: row for row in pcon.execute(
    "SELECT unit_id, question_sha256, answer_sha256, discourse_class, answer_status, "
    "answer_orientation, question_family, family_key, n_question_sentences, answer_lines "
    "FROM qa_candidates")}
unit_mismatch = []
if len(raw_units) != len(public_unit_rows) or len(raw_units) != analysis["qa"]["totalUnits"]:
    unit_mismatch.append(f"units raw={len(raw_units)} public={len(public_unit_rows)}")
for unit in raw_units:
    row = public_unit_rows.get(unit["unitId"])
    if not row:
        unit_mismatch.append(f"{unit['unitId']}:missing-public")
        continue
    expected = (unit["questionSha256"], unit["answerSha256"], unit["discourseClass"],
                unit["answerStatus"], unit["answerOrientation"], unit["questionFamily"],
                unit["familyKey"], unit["nQuestionSentences"], unit["answerLines"])
    if row[1:] != expected:
        unit_mismatch.append(unit["unitId"])
check("all 572 Q&A units and answer/orientation/family fields recompute exactly",
      not unit_mismatch, str(unit_mismatch[:20]))
orientation_recomputed = dict(__import__("collections").Counter(
    u["answerOrientation"] for u in raw_units))
check("unclassified_default is an explicit zero-pattern bucket, not descriptive evidence",
      orientation_recomputed == analysis["qa"]["orientationTotals"] and
      analysis["qa"]["unclassifiedDefaultUnits"] ==
      orientation_recomputed.get("unclassified_default") and
      analysis["qa"]["unclassifiedDefaultUnits"] > 0,
      str(orientation_recomputed))

# TF-IDF, NMF, KMeans, network, and sensitivity recompute.
masked = []
for meta, text in zip(metas, docs):
    stop = build_module.stoplist_for(meta["detectedLanguage"]) | build_module.PROPER_NAMES
    raw_tokens = build_module.WORD_RE.findall(text.lower())
    masked.append(" ".join(t for t in raw_tokens if t not in stop))
vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1,
                      max_df=0.95, token_pattern=r"(?u)\b\w[\wäöüß]+\b")
X = vec.fit_transform(masked)
feats = np.array(vec.get_feature_names_out())
mean_tfidf = np.asarray(X.mean(axis=0)).ravel()
top = mean_tfidf.argsort()[::-1][:40]
recomputed_top = [(feats[i], round(float(mean_tfidf[i]), 4)) for i in top]
reported_top = [(r["term"], r["score"]) for r in analysis["tfidfTopCorpus"]]
check("corpus TF-IDF top terms and scores recompute exactly",
      recomputed_top == reported_top,
      f"shape={X.shape} top={recomputed_top[:3]}")

k = analysis["nmf"]["k"]
max_iter = analysis["nmf"]["maxIter"]
nmf = NMF(n_components=k, init="nndsvda", random_state=build_module.SEED,
          max_iter=max_iter)
nmf.fit_transform(X)
Hm = nmf.components_
seed_stability = []
seed_iterations = []
for seed in [build_module.SEED + i for i in range(10)]:
    other = NMF(n_components=k, init="random", random_state=seed, max_iter=max_iter)
    other.fit_transform(X)
    seed_iterations.append(int(other.n_iter_))
    seed_stability.append(float(cosine_similarity(Hm, other.components_).max(axis=1).mean()))
all_iterations = [int(nmf.n_iter_)] + seed_iterations
check("NMF stability, iterations, and convergence recompute exactly",
      analysis["nmf"]["baseIterations"] == int(nmf.n_iter_) and
      analysis["nmf"]["randomInitIterations"] == seed_iterations and
      analysis["nmf"]["seedStabilityPerSeed"] == [round(v, 4) for v in seed_stability] and
      analysis["nmf"]["seedStabilityMeanBestMatchCosine"] == round(float(np.mean(seed_stability)), 4) and
      analysis["nmf"]["allRunsConvergedBeforeMaxIter"] == all(i < max_iter for i in all_iterations),
      f"iterations={all_iterations} stability={np.mean(seed_stability):.4f}")

kmeans_mismatch = []
Xd = X.toarray()
for reported in analysis["kmeansDiagnostics"]["sweep"]:
    kk = reported["k"]
    silhouettes, aris, labels_base = [], [], None
    for seed in [build_module.SEED + i for i in range(10)]:
        labels = KMeans(n_clusters=kk, n_init=10, random_state=seed).fit_predict(Xd)
        silhouettes.append(float(silhouette_score(Xd, labels)))
        if seed == build_module.SEED:
            labels_base = labels
        else:
            aris.append(float(adjusted_rand_score(labels_base, labels)))
    expected = (round(float(np.mean(silhouettes)), 4), round(float(np.std(silhouettes)), 4),
                round(float(np.mean(aris)), 4), len(aris))
    actual = (reported["silhouetteMean"], reported["silhouetteSd"],
              reported["seedStabilityARIvsBase"], reported["ariComparisons"])
    if expected != actual or reported.get("selfComparisonsExcluded") is not True:
        kmeans_mismatch.append({"k": kk, "expected": expected, "actual": actual})
check("KMeans silhouettes and nine non-self ARIs recompute exactly",
      not kmeans_mismatch, str(kmeans_mismatch)[:350])

sim = cosine_similarity(X)
mean_similarity = round(float(sim[np.triu_indices(len(docs), 1)].mean()), 4)
max_similarity = round(float(sim[np.triu_indices(len(docs), 1)].max()), 4)
check("document-network mean/max cosine recompute exactly",
      mean_similarity == analysis["documentNetwork"]["meanSimilarity"] and
      max_similarity == analysis["documentNetwork"]["maxSimilarity"],
      f"mean={mean_similarity} max={max_similarity}")

sensitivity_mismatch = []
for meta, text, reported in zip(metas, docs, analysis["sensitivity"]["perDocument"]):
    raw_tokens = build_module.WORD_RE.findall(text.lower())
    expected = {
        "videoId": meta["videoId"],
        "properNameHits": sum(t in build_module.PROPER_NAMES for t in raw_tokens),
        "properNameShare": round(sum(t in build_module.PROPER_NAMES for t in raw_tokens) /
                                 max(1, len(raw_tokens)), 4),
        "commercialHits": len(build_module.COMMERCIAL_RE.findall(text)),
    }
    if expected != reported:
        sensitivity_mismatch.append({"expected": expected, "actual": reported})
max_name_share = max(r["properNameShare"] for r in analysis["sensitivity"]["perDocument"])
check("every proper-name and commercial sensitivity value recomputes exactly",
      not sensitivity_mismatch, str(sensitivity_mismatch)[:350])

# ---- figures
figs = sorted((ROOT / "figures").glob("*.svg"))
check("6 figures in SVG+PNG", len(figs) == 6 and
      all((f.with_suffix(".png")).exists() for f in figs),
      f"svg={len(figs)}")
for f in figs:
    try:
        ET.parse(f)
        ok = True
    except Exception:
        ok = False
    check(f"svg well-formed: {f.name}", ok)
    png = f.with_suffix(".png")
    if png.exists():
        head = png.read_bytes()[:8]
        check(f"png valid header+size: {png.name}",
              head.startswith(b"\x89PNG") and png.stat().st_size > 20000,
              f"{png.stat().st_size} bytes")

# ---- limits text present in every figure
lim = "not rendered subtitles"
for f in figs:
    check(f"limits footnote in {f.name}", lim in f.read_text())

# ---- synthesis bound to current artifacts
synth = (ROOT / "qualitative-synthesis.md").read_text()
if total_units <= 60:
    check("synthesis binds review count to current review",
          f"all {n_rev} units" in synth, f"nReviewed={n_rev}")
expected_family_count = analysis["qa"]["commonQuestionFamilies"]["nFamilies"]
shared_family_count = analysis["qa"]["commonQuestionFamilies"]["nSharedAcrossVideos"]
check("synthesis reports current common-family result",
      f"{expected_family_count} token-keyed families" in synth and
      (shared_family_count != 0 or "zero families recur across videos" in synth),
      f"families={expected_family_count} shared={shared_family_count}")
check("synthesis and analysis name the self-run ASR provider and sourceType",
      all(name in synth and name in analysis["sourceBoundary"] + json.dumps(analysis["validation"]["providers"])
          for name in ("self_run_faster_whisper_tiny.en", "public_youtube_audio_self_run_ASR")))
n_excl = len(analysis["validation"]["excluded"])
n_held = len(analysis["validation"].get("held", []))
n_candidates = len(candidate_ids)
check("synthesis discloses candidate exclusions and holds",
      f"{n_excl} of {n_candidates}" in synth and f"{n_held} route-limit hold" in synth,
      f"excluded={n_excl} held={n_held} candidates={n_candidates}")
check("synthesis binds the maximum proper-name share to recomputation",
      f"{max_name_share * 100:.2f}%" in synth,
      f"expected={max_name_share * 100:.2f}%")
max_silhouette = max(k["silhouetteMean"] for k in analysis["kmeansDiagnostics"]["sweep"])
check("synthesis binds recomputed NMF/KMeans/network headline scalars",
      f"{np.mean(seed_stability):.4f}" in synth and f"{max_silhouette:.4f}" in synth and
      f"{mean_similarity:.4f}" in synth and f"{max_similarity:.4f}" in synth,
      f"nmf={np.mean(seed_stability):.4f} silhouette={max_silhouette:.4f} "
      f"network={mean_similarity}/{max_similarity}")
check("synthesis discloses the exact zero-pattern orientation count",
      str(analysis["qa"]["unclassifiedDefaultUnits"]) in synth and
      "unclassified_default" in synth)
for phrase in ["humanValidated=false", "not rendered subtitles",
               "publisher metadata"]:
    check(f"synthesis states '{phrase}'", phrase in synth)
synth_claims = re.sub(r"(no|never|without|not)\s+(human\s+)?peer review", "", synth)
synth_claims = re.sub(r"(no|never|not|without)\s+(claim[a-z]*\s+(of\s+)?|evidence\s+(of|for)\s+)"
                      r"(natural clusters|stable semantic structure|cross-ET agreement|"
                      r"consensus across entities)", "", synth_claims)
for forbidden in ["peer review", "peer-reviewed", "WER measured",
                  "speaker-verified", "cross-ET agreement",
                  "consensus across entities", "natural clusters",
                  "stable semantic structure"]:
    check(f"synthesis does not claim '{forbidden}'", forbidden not in synth_claims)

pcon.close()
priv.close()
summary_out = {"nChecks": len(checks),
               "nPassed": sum(1 for c in checks if c["ok"]),
               "nFailed": sum(1 for c in checks if c["ok"] is False),
               "checks": checks}
(ROOT / "verification.json").write_text(json.dumps(summary_out, indent=1))
print(f"\n{summary_out['nPassed']}/{summary_out['nChecks']} passed")
sys.exit(1 if summary_out["nFailed"] else 0)
