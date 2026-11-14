#!/usr/bin/env python3
"""Materialize binary public artifacts from committed text derivatives.

No private media or transcript body is read. The public SQLite is rebuilt from
sources-index.csv, non-bashar-public.csv, common-questions.csv, analysis.json,
manual-review.json and the historical pilot manifest. Missing PNGs are rendered
from committed SVG figures with rsvg-convert. Existing files are left intact.
"""
import base64
import csv
import hashlib
import json
import lzma
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "research/acquisition-2026-11"
ANALYSIS = SRC / "analysis"
DEST = ROOT / "dist/research/acquisition-2026-11"


def value(row, key, default=None):
    return row[key] if key in row and row[key] != "" else default


def number(value, integer=False):
    if value in (None, ""):
        return None
    return int(float(value)) if integer else float(value)


def create_sqlite(target):
    analysis = json.loads((ANALYSIS / "analysis.json").read_text())
    review = json.loads((ANALYSIS / "manual-review.json").read_text())
    reviewed = {row["unitId"]: row["reviewedClass"] for row in review["items"]}
    source_rows = list(csv.DictReader((ANALYSIS / "sources-index.csv").open()))
    qa_rows = list(csv.DictReader((ANALYSIS / "non-bashar-public.csv").open()))
    family_rows = list(csv.DictReader((ANALYSIS / "common-questions.csv").open()))
    pilot_analysis_path = SRC / "reviews/pilot-13-baseline/analysis.json"
    pilot_analysis = json.loads(pilot_analysis_path.read_text())
    pilot_ids = set(pilot_analysis["validation"]["included"])
    pilot_ids |= {row["videoId"] for row in pilot_analysis["validation"]["excluded"]}
    candidate_ids = {row["video_id"] for row in json.loads((SRC / "all-candidates.json").read_text())}
    source_columns = [
        "video_id", "title", "publisher", "practitioner_context", "claimed_group",
        "source_url", "source_type", "asr_provider", "audio_route", "audio_edition",
        "detected_language", "language_note", "retrieved_at", "asr_completed_utc",
        "segment_count", "duration_seconds", "decoded_duration_seconds",
        "candidate_metadata_duration_seconds", "last_segment_end", "asr_coverage",
        "chunks_processed", "word_count", "words_per_minute", "repeated_trigram_share",
        "audio_sha256", "audio_bytes", "transcript_txt_sha256", "segments_sha256",
        "srt_sha256", "records_sha256", "text_sha256", "settings_sha256", "code_sha256",
        "model_id", "model_revision", "ledger_status", "human_validated", "coverage_note",
        "edition_note", "metadata_note", "source_boundary",
    ]
    integer_source = {"segment_count", "chunks_processed", "word_count", "audio_bytes",
                      "human_validated"}
    float_source = {"duration_seconds", "decoded_duration_seconds",
                    "candidate_metadata_duration_seconds", "last_segment_end", "asr_coverage",
                    "words_per_minute", "repeated_trigram_share"}
    temporary = target.with_name(target.name + ".tmp")
    temporary.unlink(missing_ok=True)
    con = sqlite3.connect(temporary)
    con.executescript("""
    CREATE TABLE sources(
      video_id TEXT PRIMARY KEY, title TEXT, publisher TEXT,
      practitioner_context TEXT, claimed_group TEXT, source_url TEXT,
      source_type TEXT, asr_provider TEXT, audio_route TEXT,
      audio_edition TEXT, detected_language TEXT, language_note TEXT,
      retrieved_at TEXT, asr_completed_utc TEXT,
      segment_count INTEGER, duration_seconds REAL,
      decoded_duration_seconds REAL, candidate_metadata_duration_seconds REAL,
      last_segment_end REAL, asr_coverage REAL, chunks_processed INTEGER,
      word_count INTEGER, words_per_minute REAL, repeated_trigram_share REAL,
      audio_sha256 TEXT, audio_bytes INTEGER, transcript_txt_sha256 TEXT,
      segments_sha256 TEXT, srt_sha256 TEXT, records_sha256 TEXT,
      text_sha256 TEXT, settings_sha256 TEXT, code_sha256 TEXT,
      model_id TEXT, model_revision TEXT, ledger_status TEXT,
      human_validated INTEGER, coverage_note TEXT, edition_note TEXT,
      metadata_note TEXT, source_boundary TEXT);
    CREATE TABLE qa_candidates(
      unit_id TEXT PRIMARY KEY, video_id TEXT, publisher TEXT,
      claimed_group TEXT, language TEXT, start_seconds REAL, end_seconds REAL,
      n_question_sentences INTEGER, primary_form TEXT, discourse_class TEXT,
      question_sha256 TEXT, answer_status TEXT, answer_lines INTEGER,
      answer_seconds REAL, answer_sha256 TEXT, answer_orientation TEXT,
      question_family TEXT, family_key TEXT, reviewed_class TEXT);
    CREATE TABLE question_families(
      family_key TEXT PRIMARY KEY, occurrences INTEGER, n_publishers INTEGER,
      n_videos INTEGER, repost_risk TEXT, question_family TEXT,
      example_video_id TEXT, example_start_seconds REAL,
      example_question_sha256 TEXT);
    CREATE TABLE validation_exclusions(
      video_id TEXT, reason TEXT, in_original_pilot_list INTEGER,
      in_candidate_list INTEGER);
    """)
    for row in source_rows:
        record = []
        for column in source_columns:
            if column == "source_boundary":
                record.append(analysis["sourceBoundary"])
            elif column == "human_validated":
                raw = row.get(column, "0")
                record.append(1 if str(raw).lower() in ("1", "true") else 0)
            elif column in integer_source:
                record.append(number(row.get(column), integer=True))
            elif column in float_source:
                record.append(number(row.get(column)))
            else:
                record.append(value(row, column))
        con.execute(f"INSERT INTO sources VALUES({','.join('?' * len(source_columns))})", record)
    qa_columns = ["unit_id", "video_id", "publisher", "claimed_group", "language",
                  "start_seconds", "end_seconds", "n_question_sentences", "primary_form",
                  "discourse_class", "question_sha256", "answer_status", "answer_lines",
                  "answer_seconds", "answer_sha256", "answer_orientation", "question_family",
                  "family_key", "reviewed_class"]
    for row in qa_rows:
        record = []
        for column in qa_columns:
            if column == "reviewed_class":
                record.append(row.get(column) or reviewed.get(row["unit_id"]))
            elif column in {"start_seconds", "end_seconds", "answer_seconds"}:
                record.append(number(row.get(column)))
            elif column in {"n_question_sentences", "answer_lines"}:
                record.append(number(row.get(column), integer=True))
            elif column == "family_key":
                record.append(value(row, column))
            else:
                record.append(value(row, column))
        con.execute(f"INSERT INTO qa_candidates VALUES({','.join('?' * len(qa_columns))})", record)
    for row in family_rows:
        con.execute("INSERT INTO question_families VALUES(?,?,?,?,?,?,?,?,?)", (
            row["family_key"], int(row["occurrences"]), int(row["n_publishers"]),
            int(row["n_videos"]), row["repost_risk"], row["question_family"],
            value(row, "example_video_id"), number(row.get("example_start_seconds")),
            value(row, "example_question_sha256")))
    for row in analysis["validation"]["excluded"]:
        con.execute("INSERT INTO validation_exclusions VALUES(?,?,?,?)", (
            row["videoId"], row["reason"], int(row["videoId"] in pilot_ids),
            int(row["videoId"] in candidate_ids)))
    assert con.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    assert con.execute("SELECT COUNT(*) FROM sources").fetchone()[0] == analysis["nDocuments"]
    assert con.execute("SELECT COUNT(*) FROM qa_candidates").fetchone()[0] == analysis["qa"]["totalUnits"]
    assert con.execute("SELECT COUNT(*) FROM question_families").fetchone()[0] == analysis["qa"]["commonQuestionFamilies"]["nFamilies"]
    assert con.execute("SELECT COUNT(*) FROM qa_candidates WHERE reviewed_class IS NOT NULL").fetchone()[0] == review["nReviewed"]
    con.commit()
    con.close()
    os.replace(temporary, target)


def materialize_chunks(force=False):
    manifest_path = SRC / "chunks/manifest.json"
    if not manifest_path.exists():
        return
    manifest = json.loads(manifest_path.read_text())
    for record in manifest["records"]:
        chunks = []
        for index in range(record["chunkCount"]):
            chunk_path = SRC / "chunks" / f"{record['id']}.xz.b64.{index:03d}"
            if not chunk_path.exists():
                raise FileNotFoundError(chunk_path)
            chunks.append(chunk_path.read_text())
        compressed = base64.b64decode("".join(chunks))
        if hashlib.sha256(compressed).hexdigest() != record["xzSha256"]:
            raise RuntimeError(f"Compressed chunk hash mismatch: {record['path']}")
        raw = lzma.decompress(compressed)
        if len(raw) != record["originalBytes"] or hashlib.sha256(raw).hexdigest() != record["originalSha256"]:
            raise RuntimeError(f"Reassembled source hash mismatch: {record['path']}")
        target = SRC / record["path"]
        if target.exists() and not force:
            if target.read_bytes() != raw:
                raise RuntimeError(f"Existing source differs from chunks: {record['path']}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)


def main():
    force = "--force" in sys.argv
    materialize_chunks(force=force)
    verification = json.loads((ANALYSIS / "verification.json").read_text())
    gate = json.loads((ANALYSIS / "gate-status.json").read_text())
    candidates = json.loads((SRC / "all-candidates.json").read_text())
    ids = sorted(row["video_id"] for row in candidates)
    expected_hash = hashlib.sha256("\n".join(ids).encode()).hexdigest()
    if (verification.get("nFailed") != 0 or gate.get("ready") is not True
            or gate.get("candidateVideos") != len(ids)
            or gate.get("candidateIdsSha256") != expected_hash):
        raise RuntimeError("Refusing to materialize an unverified or ungated corpus")
    (DEST / "analysis").mkdir(parents=True, exist_ok=True)
    database = DEST / "analysis/non-bashar-public.sqlite"
    if force or not database.exists():
        create_sqlite(database)
        print("materialized analysis/non-bashar-public.sqlite")
    figure_destination = DEST / "figures"
    figure_destination.mkdir(parents=True, exist_ok=True)
    for svg in sorted((ANALYSIS / "figures").glob("*.svg")):
        target = figure_destination / svg.name
        if force or not target.exists():
            target.write_bytes(svg.read_bytes())
        png = figure_destination / f"{svg.stem}.png"
        if force or not png.exists():
            if shutil.which("rsvg-convert"):
                subprocess.run(["rsvg-convert", str(svg), "-o", str(png)], check=True)
            else:
                import cairosvg
                cairosvg.svg2png(url=str(svg), write_to=str(png))
            print(f"rendered figures/{png.name}")


if __name__ == "__main__":
    main()
