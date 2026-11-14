#!/usr/bin/env python3
"""Bind expanded AI-agent verdicts to the current private Q&A artifacts.

Input verdicts are produced by analysis agents reading the private stratified
sample. This is not human annotation. Public output contains bounded question
excerpts and hashes only; answer text remains private.
"""
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRIV = Path(os.environ["CHANNELS_ET_RAW_ROOT"]) / "analysis-2026-11"
ALLOWED_VERDICTS = {"confirm", "reclassify", "boundary_error"}
ALLOWED_CLASSES = {
    "direct_interview_candidate", "unclear_dialogue_context",
    "rhetorical_candidate", "secondary_report", "self_report",
}

sample = json.loads((PRIV / "review-sample.json").read_text())
verdict_rows = json.loads((PRIV / "review-verdicts.json").read_text())
analysis = json.loads((ROOT / "analysis.json").read_text())
by_unit = {}
for row in verdict_rows:
    uid = row["unitId"]
    if uid in by_unit:
        raise ValueError(f"duplicate verdict for {uid}")
    if row.get("verdict") not in ALLOWED_VERDICTS:
        raise ValueError(f"invalid verdict for {uid}")
    if row.get("reviewedClass") not in ALLOWED_CLASSES:
        raise ValueError(f"invalid reviewedClass for {uid}")
    if not row.get("note") or len(row["note"]) > 240:
        raise ValueError(f"missing or overlong note for {uid}")
    by_unit[uid] = row
sample_ids = [row["unitId"] for row in sample]
if set(by_unit) != set(sample_ids) or len(by_unit) != len(sample):
    raise ValueError(f"verdict/sample mismatch: verdicts={len(by_unit)} sample={len(sample)}")

priv = sqlite3.connect(PRIV / "qa-full.sqlite")
items = []
for index, source in enumerate(sample):
    verdict = by_unit[source["unitId"]]
    row = priv.execute(
        "SELECT question_sha256, video_id, claimed_group FROM qa WHERE unit_id=?",
        (source["unitId"],)).fetchone()
    if not row:
        raise ValueError(f"sample unit absent from current private DB: {source['unitId']}")
    question_sha, video_id, claimed_group = row
    if video_id != source["videoId"] or claimed_group != source["claimedGroup"]:
        raise ValueError(f"sample/source metadata mismatch: {source['unitId']}")
    items.append({
        "unitId": source["unitId"], "videoId": video_id,
        "claimedGroup": claimed_group, "startSeconds": source["startSeconds"],
        "autoDiscourseClass": source["autoDiscourseClass"],
        "autoAnswerStatus": source["autoAnswerStatus"],
        "autoOrientation": source["autoOrientation"],
        "autoFamily": source["autoFamily"],
        "verdict": verdict["verdict"], "reviewedClass": verdict["reviewedClass"],
        "note": verdict["note"], "questionSha256": question_sha,
        "questionExcerpt": source["questionText"][:150],
    })
priv.close()

n = len(items)
verdict_counts = dict(Counter(i["verdict"] for i in items))
reclass = Counter(
    f"{i['autoDiscourseClass']} -> {i['reviewedClass']}"
    for i in items if i["verdict"] == "reclassify" and
    i["reviewedClass"] != i["autoDiscourseClass"])
n_boundary = verdict_counts.get("boundary_error", 0)
entity_counts = Counter(i["claimedGroup"] for i in items)
answer_counts = Counter(i["autoAnswerStatus"] for i in items)
top_transitions = "; ".join(f"{key} ({value})" for key, value in reclass.most_common(4))
findings = [
    f"Boundary review: {n_boundary}/{n} sampled units ({round(100*n_boundary/n)}%) "
    "are fragments, cut clusters, or turn-alignment failures; these are not clean Q&A evidence.",
    f"Most frequent class corrections: {top_transitions or 'none'}.",
    "The expanded Kryon sample contains many speaker-posed or audience-ventriloquized "
    "questions in solo monologue; address terms such as 'dear one' and 'you might say' "
    "are not sufficient evidence of a two-party interview.",
    "Quoted dialogue in anecdotes and practitioner-relayed entity speech remains "
    "secondary_report; direct audience Q&A is promoted only where the bounded text "
    "shows a responsive exchange.",
    f"Review allocation spans {len(entity_counts)} claimed-entity labels; "
    f"Kryon contributes {entity_counts.get('Kryon', 0)} items and Ryokah/Sassani "
    f"{entity_counts.get('Ryokah / Sassani', 0)}. This is a stratified diagnostic "
    "sample, not a population estimate.",
    f"Automatic answer-window states in the sample: {dict(answer_counts)}. Orientation "
    "and family labels describe text shape only, not answer truth or consensus.",
    "tiny.en ASR errors, long multi-sentence segments, and absent diarization limit "
    "speaker/addressee inference. Review is ai_agent_review, not human annotation; "
    "every verdict binds to the current question hash and source metadata; "
    "humanValidated stays false.",
]
out = {
    "manualReviewKind": "ai_agent_review",
    "reviewedAt": "2026-11-11",
    "reviewer": "three analysis agents (not human annotation); humanValidated stays false",
    "sampleRule": (f"{analysis['manualReviewSampleRule']}; {n} verdicts across "
                   f"{analysis['qa']['totalUnits']} current extracted units"),
    "nReviewed": n,
    "verdictCounts": verdict_counts,
    "reclassifications": dict(reclass),
    "findings": findings,
    "items": items,
}
(ROOT / "manual-review.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print("wrote manual-review.json", n, verdict_counts)
