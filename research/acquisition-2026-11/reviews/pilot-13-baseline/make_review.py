#!/usr/bin/env python3
"""One-off writer for manual-review.json (AI agent review, seed-stratified sample).

Verdicts were produced by reading the private review-sample.json (question and
bounded answer text). This script binds each verdict to the current question
sha256 from the private qa-full.sqlite and writes bounded excerpts only.
"""
import json
import os
from collections import Counter
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
PRIV = Path(os.environ["CHANNELS_ET_RAW_ROOT"]) / "analysis-2026-11"

sample = json.loads((PRIV / "review-sample.json").read_text())

# index -> (verdict, reviewedClass, note)
V = {
 0: ("reclassify", "secondary_report", "quoted dialogue inside the narrator's snake anecdote ('he said, what is it?'); not an interviewer question"),
 1: ("reclassify", "secondary_report", "quoted dialogue inside the same snake anecdote ('where is it?'); reported speech"),
 2: ("reclassify", "direct_interview_candidate", "live clarification exchange; 'asking me' matched the secondary pattern but the answer ('I guess I was asking you') shows a direct two-party Q&A"),
 3: ("boundary_error", "unclear_dialogue_context", "question clause cut mid-sentence ('whilst also not liking the snake?'); fragment of a larger scenario question"),
 4: ("reclassify", "direct_interview_candidate", "ethical scenario question put to the channeled voice; bounded answer captured"),
 5: ("confirm", "unclear_dialogue_context", "ASR-garbled opening clause ('Speak up the book what now?'); likely direct dialogue but wording unverifiable; conservative unclear"),
 6: ("confirm", "direct_interview_candidate", "direct second-person question to the channeled guest; answer confirms"),
 7: ("reclassify", "direct_interview_candidate", "imperative elicitation mid-phrase ('also maybe explain...'); answer supplies the requested name"),
 8: ("reclassify", "rhetorical_candidate", "solo monologue; rhetorical teaser ('a confirmation?') addressed to the audience and self-answered; no interviewer"),
 9: ("confirm", "rhetorical_candidate", "tag-only unit ('Okay?') in a narrated solo Q&A; stopword-only, family-less"),
 10: ("reclassify", "direct_interview_candidate", "opening question of an interview-format video; next segments answer it directly"),
 11: ("boundary_error", "unclear_dialogue_context", "trailing fragment ('humans and the Yahyel?') cut at segment boundary"),
 12: ("reclassify", "direct_interview_candidate", "question about the channeled collective itself ('walk amongst us'); answered in first person plural by the entity voice"),
 13: ("reclassify", "self_report", "speaker narrates her own past crisis; 'What am I supposed to do?' is her own quoted self-question"),
 14: ("reclassify", "rhetorical_candidate", "procedural invitation phrased as a question ('Why don't we take a breath...'); ASR garble 'out of the pot'; same voice continues"),
 15: ("reclassify", "rhetorical_candidate", "transitional self-prompt in monologue ('And what else?'); same voice continues immediately"),
 16: ("reclassify", "rhetorical_candidate", "audience-including rhetorical question ('how much are we willing to receive'); answer window itself is ASR-garbled"),
 17: ("confirm", "direct_interview_candidate", "practitioner asks the channeled collective for anything else; captured window mixes her own transition"),
 18: ("confirm", "direct_interview_candidate", "confirmation rephrase within interview dialogue after a 'right?' tag; answer elaborates"),
 19: ("confirm", "direct_interview_candidate", "explicit named address ('dear Ashtar, do you have anything to add'); window captures the entity response"),
 20: ("boundary_error", "rhetorical_candidate", "entity voice voices audience fears as quoted questions then asks rhetorically why address this; opening clause cut at boundary"),
 21: ("reclassify", "rhetorical_candidate", "channeled voice's own transitional question ('And so what are we saying here?'), answered by the same flow"),
 22: ("reclassify", "secondary_report", "entity voice quotes the listener's own question ('And then you say, okay, what can I do right now?')"),
 23: ("boundary_error", "secondary_report", "voiced/quoted audience anxieties ('what are they going to do?'); opening clause cut at boundary"),
 24: ("boundary_error", "unclear_dialogue_context", "question fragment ('of are you exercising?') cut mid-clause; likely 'how many of you...'"),
 25: ("reclassify", "rhetorical_candidate", "audience-directed teaching question ('Do you have a faith in yourself?') self-answered by the same voice; no interviewer"),
 26: ("confirm", "direct_interview_candidate", "closing invitation addressed by name ('dear Ashtar'); window captures the farewell message"),
 27: ("confirm", "unclear_dialogue_context", "single-word 'Who?' at the message boundary; window captures the host's post-message reflection, not an answer"),
 28: ("reclassify", "rhetorical_candidate", "repeated audience-engagement question ('Have you heard?') in solo channeling; no interviewer present"),
 29: ("reclassify", "secondary_report", "quotes a woman's question ('a lady is saying, how could that...'); opening words cut at segment boundary"),
 30: ("confirm", "unclear_dialogue_context", "ASR-garbled first-person question ('How shall and will I navigate my I am?'); addressee unrecoverable from text"),
 31: ("boundary_error", "unclear_dialogue_context", "name-tagged address ('right, George?') plus ASR-garbled second question ('How would agree?'); window truncated by next question"),
 32: ("confirm", "unclear_dialogue_context", "host-side clarification question ('The healthcare system?') in a multi-speaker exchange; speaker attribution impossible without diarization"),
 33: ("reclassify", "rhetorical_candidate", "comprehension-check tag ('You understand?') by the lecturing voice; stopword-only, family-less"),
 34: ("reclassify", "rhetorical_candidate", "confirmation tag appended to a statement ('passion within Pluto, yes?')"),
 35: ("reclassify", "secondary_report", "generic quoted self-question inside teaching monologue ('you can say afterwards, what was I thinking?'); 'you' is generic"),
 36: ("confirm", "direct_interview_candidate", "entity voice invites further questions from the hosts; captured window continues teaching, voices mixed"),
 37: ("reclassify", "direct_interview_candidate", "host poses a topical question to the channeled voice; answer addresses it"),
 38: ("confirm", "unclear_dialogue_context", "production/logistics question to a host ('How much time do we have, Georgia?'); not session content"),
 39: ("confirm", "direct_interview_candidate", "ASR-garbled host question about the trim-tab metaphor; answer develops the metaphor"),
 40: ("confirm", "direct_interview_candidate", "host question to the channeled voice; answer opens with direct affirmation"),
 41: ("reclassify", "rhetorical_candidate", "confirmation tag ('It's pretty big deep, yes?'); timing_specific orientation reflects window text, not the question"),
 42: ("boundary_error", "rhetorical_candidate", "opening clause cut; the interrogative content is the trailing tag 'you follow?'"),
 43: ("reclassify", "rhetorical_candidate", "comprehension tag ('You follow?'); stopword-only, family-less"),
 44: ("reclassify", "self_report", "practitioner narrates the entity's images; 'how do I put this into words?' is her own self-directed phrasing"),
 45: ("reclassify", "secondary_report", "practitioner relays the entity's quoted question ('He says, what is a job?')"),
 46: ("boundary_error", "unclear_dialogue_context", "clause fragment ('live streams in different cultures?') cut at segment boundary within the relayed exchange"),
 47: ("reclassify", "secondary_report", "quoted entity remark ('and he says, why not?') relayed by the practitioner"),
 48: ("reclassify", "direct_interview_candidate", "first-person question put to the channeled entity (viewer-submitted or practitioner's); answer relays the entity's response"),
 49: ("reclassify", "direct_interview_candidate", "same relay format: first-person question answered through the entity's shown images"),
 50: ("reclassify", "rhetorical_candidate", "self-answered framing question in a solo channeled monologue ('So why did it come up again?')"),
 51: ("reclassify", "rhetorical_candidate", "narrated deliberation ('why not work together?') about organizing the event; not addressed to an addressee in-session"),
 52: ("boundary_error", "direct_interview_candidate", "opening cut; direct question to a fellow panelist-practitioner about what their channeling says"),
 53: ("confirm", "unclear_dialogue_context", "panelist-to-panelist follow-up; no claimed-entity addressee"),
 54: ("reclassify", "rhetorical_candidate", "self-posed teaching question immediately answered by the same voice ('So I think...')"),
 55: ("boundary_error", "unclear_dialogue_context", "multi-question cluster with cut fragments and a closing tag; addressee unclear from text"),
 56: ("reclassify", "rhetorical_candidate", "trailing 'you know?' tag; stopword-only, family-less"),
 57: ("confirm", "direct_interview_candidate", "panelist-to-panelist practice question ('how long have you been jamming'); answer gives the duration"),
 58: ("reclassify", "rhetorical_candidate", "statement plus 'right?' confirmation tag addressed to a panelist; no content question"),
 59: ("boundary_error", "secondary_report", "quoted question inside a healing anecdote ('said, what do we do?'); opening words cut"),
 60: ("confirm", "unclear_dialogue_context", "ASR-garbled panelist question about another teacher's predictions ('has Judah Ben doing...')"),
 61: ("confirm", "rhetorical_candidate", "tag-only unit ('right?'); stopword-only, family-less"),
 62: ("boundary_error", "rhetorical_candidate", "statement fragment plus 'you know?' tag; opening cut"),
 63: ("confirm", "rhetorical_candidate", "tag-only unit ('You know?'); family-less"),
 64: ("boundary_error", "unclear_dialogue_context", "trailing clause of a self-reflective question cut at the segment boundary; window interrupted by the next question"),
 65: ("boundary_error", "rhetorical_candidate", "fragment plus 'right?' tag; statement cut mid-clause"),
 66: ("reclassify", "direct_interview_candidate", "elliptical follow-up on contact timing directed at the panel/channeled sources; answer gives timeframe commentary"),
}
assert len(V) == len(sample), (len(V), len(sample))

priv = sqlite3.connect(PRIV / "qa-full.sqlite")
items = []
for i, s in enumerate(sample):
    verdict, reviewed_class, note = V[i]
    row = priv.execute("SELECT question_sha256 FROM qa WHERE unit_id=?",
                       (s["unitId"],)).fetchone()
    assert row, s["unitId"]
    excerpt = s["questionText"][:150]
    items.append({
        "unitId": s["unitId"], "videoId": s["videoId"],
        "claimedGroup": s["claimedGroup"], "startSeconds": s["startSeconds"],
        "autoDiscourseClass": s["autoDiscourseClass"],
        "autoAnswerStatus": s["autoAnswerStatus"],
        "autoOrientation": s["autoOrientation"],
        "autoFamily": s["autoFamily"],
        "verdict": verdict, "reviewedClass": reviewed_class, "note": note,
        "questionSha256": row[0], "questionExcerpt": excerpt,
    })

verdict_counts = dict(Counter(i["verdict"] for i in items))
reclass = Counter(
    f"{i['autoDiscourseClass']} -> {i['reviewedClass']}"
    for i in items if i["verdict"] == "reclassify" and i["reviewedClass"] != i["autoDiscourseClass"])
n = len(items)
n_boundary = verdict_counts.get("boundary_error", 0)
findings = [
    f"ASR (tiny.en) emits multi-sentence segments, so mid-clause question cuts come from sentence splitting inside long segments rather than rendered-line breaks: {n_boundary}/{n} sampled units ({round(100*n_boundary/n)}%) are boundary fragments or cut clusters.",
    "Tag/comprehension-check questions (right?, you know?, you follow?, Okay?) are common in the panel/dialogue videos and are correctly rhetorical; they are stopword-only and family-less.",
    "Quoted dialogue inside anecdotes (snake story, healing story) and practitioner-relayed entity speech ('he says ...') were reclassified to secondary_report; the Megan Rose relay format mixes her own narration with the entity's shown images.",
    "Solo-monologue sources (Aurora Ray, SAM THE ILLUSIONIST, SOLi School card reading) show self-answered rhetorical framing questions; no interviewer is present in the flow.",
    "tiny.en ASR errors deform names (e.g. Yahyel as 'Diyal'/'IELT'/'Yale', Ashtar as 'Ashir'/'Ashdar', Val Nek as 'Valek'); family keys use content tokens, so such garble keeps related questions in distinct families; counts are literal-text counts, not corrected readings.",
    "Answer windows are usually captured (complete_line_cap dominates); captured answers are mostly descriptive_explanatory in shape; orientation says nothing about answer truth, agreement or consensus.",
    "Review is ai_agent_review, not human annotation; every verdict binds to the current question hash and source metadata; humanValidated stays false.",
]
out = {
    "manualReviewKind": "ai_agent_review",
    "reviewedAt": "2026-11-10",
    "reviewer": "analysis agent (not human annotation); humanValidated stays false",
    "sampleRule": f"stratified sample of {n} (>= 60) across every claimed-entity label present, from 164 extracted units (seed 20261110)",
    "nReviewed": n,
    "verdictCounts": verdict_counts,
    "reclassifications": dict(reclass),
    "findings": findings,
    "items": items,
}
(ROOT / "manual-review.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print("wrote manual-review.json", n, verdict_counts)
