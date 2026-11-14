#!/usr/bin/env python3
"""Apply the AI manual-review verdicts for the acquisition-2026-11 ASR workstream.

Reads manual-review.json (bounded excerpts + hashes only), adds a
reviewed_class column to the public qa_candidates table and CSV, and writes a
reviewSummary block into analysis.json. AI agent review
(manualReviewKind=ai_agent_review), not human annotation; humanValidated
stays false everywhere.

Usage: python3 research/acquisition-2026-11/analysis/apply_review.py
"""
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent

review = json.loads((ROOT / "manual-review.json").read_text())
if review.get("manualReviewKind") != "ai_agent_review":
    raise SystemExit("manual-review.json must be ai_agent_review")
reviewed = {i["unitId"]: i for i in review["items"]}

# ---- public sqlite: add/populate reviewed_class
db = ROOT / "non-bashar-public.sqlite"
con = sqlite3.connect(db)
cols = [r[1] for r in con.execute("PRAGMA table_info(qa_candidates)")]
if "reviewed_class" not in cols:
    con.execute("ALTER TABLE qa_candidates ADD COLUMN reviewed_class TEXT")
con.execute("UPDATE qa_candidates SET reviewed_class = NULL")
for uid, item in reviewed.items():
    con.execute("UPDATE qa_candidates SET reviewed_class=? WHERE unit_id=?",
                (item["reviewedClass"], uid))
con.commit()
applied = con.execute(
    "SELECT COUNT(*) FROM qa_candidates WHERE reviewed_class IS NOT NULL").fetchone()[0]
con.close()

# ---- public CSV: add reviewed_class column
rows = list(csv.DictReader(open(ROOT / "non-bashar-public.csv")))
fields = list(rows[0].keys()) if rows else []
if "reviewed_class" not in fields:
    fields.append("reviewed_class")
for r in rows:
    r["reviewed_class"] = reviewed.get(r["unit_id"], {}).get("reviewedClass", "")
with open(ROOT / "non-bashar-public.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    w.writerows(rows)

# ---- analysis.json: reviewSummary
analysis = json.loads((ROOT / "analysis.json").read_text())
analysis["reviewSummary"] = {
    "manualReviewKind": "ai_agent_review",
    "nReviewed": review["nReviewed"],
    "sampleRule": review["sampleRule"],
    "verdictCounts": review["verdictCounts"],
    "reclassifications": review["reclassifications"],
    "findings": review["findings"],
    "caution": "AI review, not human annotation; humanValidated stays false. "
               "Reviewed classes refine textual heuristics only; no speaker "
               "attribution, truth or consensus assessment.",
}
(ROOT / "analysis.json").write_text(json.dumps(analysis, indent=1, ensure_ascii=False))
print(f"applied {len(reviewed)} verdicts; reviewed rows in public db: {applied}")
