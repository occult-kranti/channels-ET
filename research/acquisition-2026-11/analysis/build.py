#!/usr/bin/env python3
"""Build the non-Bashar self-run ASR analysis layer (acquisition-2026-11).

Adapted from research/expansion-2026/non-bashar-analysis/build.py to actual
self-run YouTube ASR sources under
${CHANNELS_ET_RAW_ROOT}/youtube-audio/<video_id>/ with acquisition.json,
audio.mp3, asr-receipt.json and asr-segments.jsonl / asr-transcript.txt /
asr-transcript.srt. Segment records carry start/end/text and are normalized to
startSeconds/endSeconds for analysis.

The build is GATED: it refuses to write final outputs until every record in
research/acquisition-2026-11/all-candidates.json has an artifact-bound terminal
state. Completed acquisitions need completed ASR receipts and matching output
hashes; under-300 and unsupported-language records need explicit exclusions;
held_route_limit_over_150_minutes remains held and is never counted as analyzed.

Validates audio/acquisition hashes, ASR settings, durations and full-decode
coverage; builds a private source+segment index (exact text) under
${CHANNELS_ET_RAW_ROOT}/analysis-2026-11 and public metadata/hashes-only
outputs; runs corpus analysis (TF-IDF, NMF seed stability, KMeans diagnostics,
publisher/practitioner/claimed-entity overlays, document cosine network,
temporal/duration profiles, name/commercial sensitivity); extracts literal
question units with bounded answer windows and token-keyed common-question
families (stopword-only units stay family-less); writes an AI-review sample.

Provider label: self_run_faster_whisper_tiny.en. sourceType:
public_youtube_audio_self_run_ASR. Deterministic (seed 20261110).

Usage: python3 research/acquisition-2026-11/analysis/build.py
"""
import csv
import hashlib
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[2]
RAW = Path(os.environ["CHANNELS_ET_RAW_ROOT"]) / "youtube-audio"
PRIV = Path(os.environ["CHANNELS_ET_RAW_ROOT"]) / "analysis-2026-11"
CANDIDATES = REPO / "research/acquisition-2026-11/all-candidates.json"
ORIGINAL_PILOT = REPO / "research/expansion-2026/youtube-transcripts/pilot-videos.json"
LEDGER = REPO / "research/acquisition-2026-11/acquisition-ledger.json"
ASR_SUMMARY = REPO / "research/acquisition-2026-11/asr-summary.json"
MODEL_MANIFEST = REPO / "research/harvest/asr/model-manifest.json"
CODE_EDITIONS = REPO / "research/acquisition-2026-11/asr-code-editions.json"
PRIOR_INDEX = (REPO / "research/expansion-2026/non-bashar-analysis/"
               "sources-index.csv")
SEED = 20261110
PROTOCOL = json.loads((ROOT / "protocol.json").read_text())

MERGE_GAP = PROTOCOL["questionExtraction"]["mergeRule"]["maxGapSeconds"]
ANS_MAX_LINES = PROTOCOL["answerWindow"]["maxLines"]
ANS_MAX_SEC = PROTOCOL["answerWindow"]["maxSeconds"]

PROVIDER = "self_run_faster_whisper_tiny.en"
SOURCE_TYPE = "public_youtube_audio_self_run_ASR"
MIN_SUPPORTED_WPM = 45.0   # degenerate-output guard; see protocol
MIN_ASR_COVERAGE = 0.75

_manifest = json.loads(MODEL_MANIFEST.read_text())
EXPECTED_SETTINGS = {
    "language": "en", "beam_size": 1, "vad_filter": True,
    "condition_on_previous_text": False, "device": "cpu", "compute_type": "int8",
    "modelId": "Systran/faster-whisper-tiny.en", "revision": _manifest["revision"],
    "chunkSeconds": 300,
}
EXPECTED_SETTINGS_SHA256 = hashlib.sha256(
    json.dumps({**EXPECTED_SETTINGS,
                "chunkingNote": ("Every sample is decoded once to 16 kHz mono and "
                                 "transcribed in contiguous 300 s windows; timestamps "
                                 "are offset-stitched. Window-boundary words can be "
                                 "split; this is a recorded limitation.")},
               sort_keys=True).encode()).hexdigest()
CODE_EDITION_MANIFEST = json.loads(CODE_EDITIONS.read_text())
CODE_EDITION_MAP = {row["sha256"]: row for row in CODE_EDITION_MANIFEST["editions"]}

LIMIT_LINE = ("Self-run baseline ASR (faster-whisper tiny.en int8 CPU, English-only, "
              "300 s windows) over public YouTube audio; not rendered subtitles or "
              "original caption tracks; no diarization; no human WER; "
              "humanValidated=false; ASR accuracy unmeasured; small corpus; "
              "uploader != practitioner != claimed entity; claimed-entity labels "
              "are publisher metadata only.")

# ---------------------------------------------------------------- patterns
TAG_RE = re.compile(
    r"^(right|okay|ok|yeah|yes|no|correct|huh|isn't it|isnt it|aren't they|"
    r"don't you|dont you|you know|you know what i mean|does that make sense|"
    r"make sense|does that resonate|you see|oder|nicht wahr|gell|ne|ja)[\s,!?\.]*$",
    re.I)
SEC_RE = re.compile(
    r"\b(people (always |sometimes |often )?ask|people wanted to know|"
    r"they ask|he asked|she asked|someone asked|somebody asked|folks ask|"
    r"i get asked|i'm asked|i am asked|i was asked|"
    r"they asked (me|him|her|us)|asked me\b|asking me\b|"
    r"question i get|everybody asks|people want to know|"
    r"leute fragen|ich werde gefragt|man fragt)\b", re.I)
SELF_RE = re.compile(
    r"\b(i (ask|asked) myself|i wonder|i wondered|i keep asking myself|"
    r"i have to ask myself|ich frage mich)\b", re.I)
IMP_RE = re.compile(
    r"^(tell (me|us) about|talk about|tell (me|us) more|explain|describe|"
    r"share with (me|us)|walk (me|us) through|"
    r"can you (tell|share|explain|describe|talk))", re.I)
WH_RE = re.compile(
    r"\b(what|why|how|when|where|who|which|whose|whom|"
    r"was|wie|warum|wieso|wann|wer|wen|wem|wo|woher|wohin|welche|welcher|"
    r"welches|wessen|womit|worüber|worum)\b", re.I)
YN_RE = re.compile(
    r"\b(do|does|did|can|could|would|will|is|isn't|are|aren't|was|were|"
    r"have|has|had|shall|should|may|might|must)\s+"
    r"(you|we|they|he|she|it|i|there|that|this|these|those|people|"
    r"anyone|everyone|somebody|anybody)\b|"
    r"^(kannst|kann|könntest|könnte|sind|ist|bist|hast|haben|hat|werden|"
    r"wirst|darf|darfst|soll|sollen|gibt es)\s", re.I)
ADDRESS_RE = re.compile(
    r"\b(you|your|yours|yourself|y'all|channel|channeling|channeled|"
    r"et|ets|extraterrestrial|extraterrestrials|alien|aliens|"
    r"pleiadian|pleiadians|yahyel|arcturian|arcturians|galactic federation|"
    r"federation of light|ashtar|val nek|ryokah|ishuwa|orella|germane|"
    r"starseed|starseeds|du|dich|dein|deine|ihr|euch)\b", re.I)

STOP_EN = set("""
i me my we our you your he him his she her it its they them their this that
these those am is are was were be been being have has had having do does did
doing will would shall should can could may might must ought im youre hes shes
its weve dont doesnt didnt isnt arent wasnt werent wont wouldnt shouldnt
couldnt havent hasnt hadnt a an the and but if or because as until while of at
by for with about into through during before after above below to from up down
in out on off over under again further then once here there when where why how
what who whom whose which
all any both each few more most other some such no nor not only own same so
than too very just also really actually like yeah yes okay ok right well now
know think going go gonna want get got thing things people lot kind stuff way
say said says see look let lets make much many one two three even back still
take come came uh um hmm oh ah wow hey hi hello thank thanks thankyou bye
""".split())
STOP_DE = set("""
ich du er sie es wir ihr sie mich dich ihn uns euch mein dein sein ihr unser
euer der die das den dem des ein eine einer eines einem einen und oder aber
denn wenn als wie auch nur noch schon sehr so dann da dort hier jetzt immer
wieder mehr viel viele alle alles nicht kein keine keinen keinem keiner am im
in an auf aus bei mit nach von vor zu zur zum über unter durch für gegen ohne
um ist sind war waren bin bist seid habe hast hat haben hatte hatten kann
kannst können konnte konnten will willst wollen soll sollen muss musst müssen
darf darfst dürfen werde wirst wird werden wurde wurden was wer wann wo warum
wieso welche welcher welches wessen man ja nein doch mal halt eben auch
""".split())
STOP_AR = set("""
في من على إلى الى عن مع هذا هذه ذلك التي الذي هو هي هم نحن أنا إنا انت أنت
نعم لا لم لن ما ماذا لماذا كيف متى أين هل كان كانت يكون تكون قد لقد كل بعد
قبل بين أو و ثم حتى إذا اذا عند عندما هناك أيضا ايضا فقط جدا الآن اليوم سنة
سنوات شيء أشياء بسبب خلال دون غير ليس ليست لكن لقد قد فإن إن أن إنما بينما
""".split())
EXTRA_STOP = set("""
video videos youtube channel subscribe like comment below link description
today welcome going really actually going right okay hey um uh
""".split())

PROPER_NAMES = set("""
bashar darryl anka essassani ishuwa yahyel shaun swanson ryokah tyler ellison
calenara caroline leo ashtar ra translucid megan rose val nek christine day
blossom goodchild barbara marciniak pavlina klemm orella sam illusionist
aurora ray jj brighton pamela aaralyn anjie hipple daniel scranton lyssa
royal holt germane orion pleiades lyra sirius andromeda arcturus tartaria
kryon lee carroll monika muranyi alcazar prageet harris ryo sassani starshine
galactic federation
""".split())

COMMERCIAL_RE = re.compile(
    r"\b(promo code|use code|sponsored by|sponsor|advertis|discount|"
    r"dot com|\.com\b|go to [a-z]+\.com|merch|patreon|paypal|buy now|"
    r"link in the (description|bio)|check out my|coupon)\b", re.I)

FAMILY_PATTERNS = {
    "contact_timing": re.compile(
        r"\b(when|how soon|timing).{0,60}\b(contact|disclosure|landing|arrival|"
        r"reveal|open contact)\b|\b(contact|disclosure|landing).{0,60}\b"
        r"(when|soon|happen|occur)\b|\bfirst contact\b|\bopen contact\b", re.I),
    "dna_origins": re.compile(
        r"\b(dna|genetic|genetics|genome|origin|origins|ancestry|ancestor|"
        r"lineage|hybrid|hybrids|starseed origin|where do (we|i|humans) come from|"
        r"related to)\b", re.I),
    "ascension": re.compile(
        r"\b(ascension|ascend|5d|fifth dimension|fifth density|new earth|"
        r"shift|shifting|raise.{0,20}(frequency|vibration)|dimensions|"
        r"density|higher (self|consciousness|frequency))\b", re.I),
    "reality_agency": re.compile(
        r"\b(reality|manifest|manifestation|create.{0,20}reality|belief|beliefs|"
        r"free will|agency|law of attraction|vibration|parallel (reality|"
        r"realities|lives)|past lives|past life|simulation)\b", re.I),
    "healing": re.compile(
        r"\b(heal|healing|health|disease|illness|symptom|symptoms|body|pain|"
        r"trauma|energy healing|heilung|gesundheit|körper)\b", re.I),
    "dreams_contact": re.compile(
        r"\b(dream|dreams|dreaming|astral|sleep|lucid|visitation|"
        r"contact.{0,20}dream|dream.{0,20}contact|traum|träume)\b", re.I),
    "predictions": re.compile(
        r"\b(predict|prediction|prophecy|future|will happen|going to happen|"
        r"solar flash|eclipse|event|202[0-9]|203[0-9]|coming (years|months)|"
        r"prepare)\b", re.I),
}

ORIENTATION_PATTERNS = {
    "process_practice_oriented": re.compile(
        r"\b(focus|breathe|breath|allow|practice|meditat|align|release|"
        r"integrat|surrender|open yourself|let go|ground|center|"
        r"arbeitet|übung|atmen|öffnet|erlaubt)\b", re.I),
    "conditional_hedged": re.compile(
        r"\b(depends|may|might|could|if you|in your (own )?timing|not yet|"
        r"perhaps|it is up to|your choice|free will)\b", re.I),
    "timing_specific": re.compile(
        r"\b(20[0-9][0-9]|in the coming (years|months|weeks)|within \d+|"
        r"\bsoon\b|next (year|month)|by (the end of|20)|very shortly)\b", re.I),
    "descriptive_explanatory": re.compile(
        r"\b(is|are|was|were|means|refers|consists|structure|energy|"
        r"frequency|consciousness)\b", re.I),
}

GERMAN_MARKERS = set("""
der die das und ist nicht ich sie mit den von zu auf ein eine auch für an
werden dem wie wir sind es war hat bei im des zum oder aus als haben dass
sich so nur noch über kann aber wenn nach um am vor einer einem einen wurden
""".split())
ENGLISH_MARKERS = set("""
the and is of to in that it for on with as are was at be this have from or
one had by but not what all were they we when your can said there use an each
which she do how their if will up other about out many then them these so some
""".split())

WORD_RE = re.compile(r"[^\W\d_]{2,}", re.UNICODE)
ARABIC_RE = re.compile(r"[\u0621-\u063A\u0641-\u064A\u0671-\u06D3]")
LATIN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]")


def detect_language(text):
    # Script evidence must precede Latin stopword ratios. Otherwise an Arabic
    # document with two incidental Latin tokens can be silently called English.
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


def stoplist_for(lang):
    if lang == "de":
        return STOP_DE | EXTRA_STOP
    if lang == "ar":
        return STOP_AR | EXTRA_STOP
    if lang == "unknown":
        return set(EXTRA_STOP)
    return STOP_EN | EXTRA_STOP


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


def sha256_text(t):
    return hashlib.sha256(t.encode()).hexdigest()


def sentences(t):
    return [s.strip() for s in re.split(r"(?<=[.!?؟۔])\s+", t.strip()) if s.strip()]


def qsentences(t):
    return [s for s in sentences(t) if "?" in s or "؟" in s]


def classify_form(s):
    core = re.sub(r"[\?؟\.\!]+$", "", s).strip()
    if TAG_RE.match(core.lower()):
        return "tag_question"
    if IMP_RE.match(core.lower()):
        return "imperative_prompt"
    if WH_RE.search(core):
        return "wh_question"
    if YN_RE.search(core):
        return "yes_no_question"
    return "other_unclassified_qmark"


def classify_family(qtext):
    for fam, pat in FAMILY_PATTERNS.items():
        if pat.search(qtext):
            return fam
    return "other_theme"


def classify_orientation(atext, status):
    if status in ("no_answer_window", "no_answer_end_of_transcript") or not atext.strip():
        return "not_captured"
    counts = {k: len(v.findall(atext)) for k, v in ORIENTATION_PATTERNS.items()}
    best = max(counts, key=lambda k: counts[k])
    if counts[best] == 0:
        return "unclassified_default"
    if best == "timing_specific" and counts["timing_specific"] >= 1:
        return "timing_specific"
    return best


def tokens(text, lang):
    toks = WORD_RE.findall(text.lower())
    stop = stoplist_for(lang) | PROPER_NAMES
    return [t for t in toks if t not in stop]


def trigram_repeat_share(toks):
    if len(toks) < 4:
        return 0.0
    tri = [tuple(toks[i:i + 3]) for i in range(len(toks) - 2)]
    c = Counter(tri)
    return sum(v for v in c.values() if v > 1) / len(tri)


# ---------------------------------------------------------------- phase 0
def load_candidates():
    rows = json.loads(CANDIDATES.read_text())
    candidates = {v["video_id"]: v for v in rows}
    if len(candidates) != len(rows):
        raise ValueError("all-candidates.json contains duplicate video_id values")
    return candidates


def summary_gate(candidate_ids):
    """Require one terminal, artifact-bound state for every candidate.

    Completed acquisition records require completed, hash-bound ASR. Explicit
    under-300 and language exclusions do not get silently promoted into the
    analysis corpus. A route-limit hold is terminal for this run but remains a
    separate held state rather than an exclusion or an analyzed document.
    """
    problems = []
    if not ASR_SUMMARY.exists():
        return [f"asr-summary.json missing at {ASR_SUMMARY}"]
    candidates = load_candidates()
    summary = json.loads(ASR_SUMMARY.read_text())
    recs = {r.get("videoId"): r for r in summary.get("records", [])}
    ledger_rows = json.loads(LEDGER.read_text()).get("records", [])
    ledger = {r.get("video_id", r.get("videoId")): r for r in ledger_rows}
    for vid in candidate_ids:
        candidate = candidates[vid]
        lg = ledger.get(vid)
        if candidate.get("selection") == "held_route_limit_over_150_minutes":
            if lg and lg.get("status") == "completed":
                problems.append(f"{vid}: route-limit hold conflicts with completed acquisition")
            if recs.get(vid, {}).get("status") == "completed":
                problems.append(f"{vid}: route-limit hold conflicts with completed ASR summary")
            if (RAW / vid / "audio.mp3").exists():
                problems.append(f"{vid}: route-limit hold has acquired audio outside the hold receipt")
            held_receipt = RAW / vid / "asr-receipt.json"
            if held_receipt.exists() and \
                    json.loads(held_receipt.read_text()).get("status") == "completed":
                problems.append(f"{vid}: route-limit hold has a completed ASR receipt")
            continue
        if not lg:
            problems.append(f"{vid}: absent from acquisition-ledger.json")
            continue
        acquisition_status = lg.get("status")
        if acquisition_status == "excluded_under_300":
            duration = lg.get("durationSeconds", lg.get("duration_seconds"))
            if not isinstance(duration, (int, float)) or not 0 < duration < 300:
                problems.append(f"{vid}: invalid under-300 duration {duration!r}")
            if (RAW / vid / "audio.mp3").exists():
                problems.append(f"{vid}: under-300 audio was not quarantined")
            if recs.get(vid, {}).get("status") == "completed":
                problems.append(f"{vid}: under-300 record has completed ASR")
            continue
        s = recs.get(vid)
        if not s:
            problems.append(f"{vid}: absent from asr-summary.json")
            continue
        receipt_path = RAW / vid / "asr-receipt.json"
        receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
        audio_path = RAW / vid / "audio.mp3"
        audio_sha = audio_sha256(vid, audio_path) if audio_path.exists() else None
        if acquisition_status == "excluded_language_mismatch":
            if s.get("status") != "excluded_language_mismatch":
                problems.append(f"{vid}: ASR summary does not preserve language exclusion")
            if receipt.get("status") != "excluded_language_mismatch":
                problems.append(f"{vid}: language exclusion lacks matching receipt")
            if receipt.get("detectedLanguage") in (None, "en"):
                problems.append(f"{vid}: quarantine receipt without non-English evidence")
            if not audio_sha or receipt.get("audioSha256") != audio_sha:
                problems.append(f"{vid}: quarantine receipt audioSha256 != audio file")
            if receipt.get("settingsSha256") != EXPECTED_SETTINGS_SHA256:
                problems.append(f"{vid}: quarantine settings hash mismatch")
            if receipt.get("codeSha256") not in CODE_EDITION_MAP:
                problems.append(f"{vid}: quarantine code edition is not allowlisted")
            qdir = RAW / vid / "quarantine"
            outputs = s.get("outputSha256") or {}
            expected_outputs = {"asr-transcript.txt", "asr-segments.jsonl",
                                "asr-transcript.srt", "asr-segments.partial.jsonl"}
            if set(outputs) != expected_outputs or receipt.get("outputSha256") != outputs or \
                    not all((qdir / n).exists() and sha256_path(qdir / n) == h
                            for n, h in outputs.items()):
                problems.append(f"{vid}: four quarantined outputs missing or hash mismatch")
            continue
        if acquisition_status != "completed":
            problems.append(f"{vid}: nonterminal acquisition status {acquisition_status}")
            continue
        if s.get("status") != "completed":
            problems.append(f"{vid}: asr-summary status {s.get('status')}")
            continue
        if not receipt_path.exists():
            problems.append(f"{vid}: summary completed but asr-receipt.json missing on disk")
            continue
        if receipt.get("status") != "completed":
            problems.append(f"{vid}: summary completed but receipt status "
                            f"{receipt.get('status')}")
            continue
        if not audio_sha or s.get("audioSha256") != audio_sha or \
                receipt.get("audioSha256") != audio_sha:
            problems.append(f"{vid}: summary/receipt/audio hash mismatch")
        if s.get("outputSha256") != receipt.get("outputSha256"):
            problems.append(f"{vid}: summary outputSha256 != receipt outputSha256")
        for name, h in (s.get("outputSha256") or {}).items():
            p = RAW / vid / name
            if not p.exists() or sha256_path(p) != h:
                problems.append(f"{vid}: summary-bound {name} missing or hash mismatch")
    return problems


# ---------------------------------------------------------------- phase 1
def validate_sources():
    """Validate candidates against acquisition/ASR receipts and raw artifacts."""
    candidates = load_candidates()
    ledger = json.loads(LEDGER.read_text())
    lmap = {r.get("video_id", r.get("videoId")): r
            for r in ledger.get("records", [])}
    summary_recs = {}
    if ASR_SUMMARY.exists():
        summary_recs = {r.get("videoId"): r
                        for r in json.loads(ASR_SUMMARY.read_text()).get("records", [])}
    prior_lang = {}
    if PRIOR_INDEX.exists():
        for row in csv.DictReader(open(PRIOR_INDEX)):
            prior_lang[row["video_id"]] = row.get("detected_language") or ""
    included, excluded, held = [], [], []
    for vid in sorted(candidates):
        p = candidates[vid]
        d = RAW / vid
        reasons, notes = [], []
        lg = lmap.get(vid)

        def fail(msg):
            reasons.append(msg)

        if p.get("selection") == "held_route_limit_over_150_minutes":
            held.append({"videoId": vid, "status": "held_route_limit_over_150_minutes",
                         "reason": "Ordinary public conversion route held this recording because "
                                   "its duration exceeds 150 minutes; no media, ASR, or analysis "
                                   "completion is claimed."})
            continue
        acquisition_status = lg.get("status") if lg else "absent"
        if acquisition_status == "excluded_under_300":
            duration = lg.get("durationSeconds", lg.get("duration_seconds"))
            excluded.append({
                "videoId": vid, "status": "excluded_under_300",
                "reason": f"Measured duration {duration} seconds is below the 300-second "
                          f"policy minimum; audio and ASR are quarantined/not analyzed."})
            continue
        if not lg:
            excluded.append({"videoId": vid, "reason": "missing acquisition-ledger record"})
            continue
        if acquisition_status not in ("completed", "excluded_language_mismatch"):
            excluded.append({"videoId": vid,
                             "reason": f"nonterminal acquisition status {acquisition_status}"})
            continue

        acq_path = d / "acquisition.json"
        audio_path = d / "audio.mp3"
        receipt_path = d / "asr-receipt.json"
        seg_path = d / "asr-segments.jsonl"
        txt_path = d / "asr-transcript.txt"
        srt_path = d / "asr-transcript.srt"
        for path in (acq_path, audio_path, receipt_path):
            if not path.exists():
                fail(f"missing artifact {path.name}")
        if reasons:
            excluded.append({"videoId": vid, "reason": "; ".join(reasons)})
            continue
        try:
            acq = json.loads(acq_path.read_text())
            receipt = json.loads(receipt_path.read_text())
        except Exception as e:
            excluded.append({"videoId": vid, "reason": f"unreadable receipt JSON: {e}"})
            continue
        # --- quarantined unsupported-language records: receipt is the evidence;
        # ASR outputs are retained under quarantine/ and never analyzed.
        if receipt.get("status") == "excluded_language_mismatch":
            det = receipt.get("detectedLanguage")
            audio_sha_q = audio_sha256(vid, audio_path) if not audio_path.is_symlink() else None
            if det in (None, "en"):
                fail("quarantine receipt lacks non-English detection evidence")
            if audio_sha_q != receipt.get("audioSha256") or \
                    audio_sha_q != acq.get("sha256"):
                fail("quarantine receipt audioSha256 != audio/acquisition hash")
            if receipt.get("settingsSha256") != EXPECTED_SETTINGS_SHA256:
                fail("quarantine settings hash mismatch")
            if receipt.get("codeSha256") not in CODE_EDITION_MAP:
                fail("quarantine code edition is not allowlisted")
            qdir = d / "quarantine"
            qoutputs = receipt.get("outputSha256") or {}
            expected_qoutputs = {"asr-transcript.txt", "asr-segments.jsonl",
                                 "asr-transcript.srt", "asr-segments.partial.jsonl"}
            if set(qoutputs) != expected_qoutputs:
                fail("quarantine output hashes do not cover all four ASR artifacts")
            else:
                for name, h in qoutputs.items():
                    if not (qdir / name).exists() or sha256_path(qdir / name) != h:
                        fail(f"quarantine output hash mismatch: {name}")
            base_reason = ("unsupported language for pinned English-only ASR: "
                           f"receipt excluded_language_mismatch (detected '{det}', "
                           f"expected 'en', model tiny.en); quarantined ASR outputs "
                           f"retained under quarantine/ and not analyzed; "
                           f"hash-bound audio")
            if reasons:
                base_reason += "; " + "; ".join(reasons)
            excluded.append({"videoId": vid, "reason": base_reason})
            continue
        for path in (seg_path, txt_path, srt_path):
            if not path.exists():
                fail(f"missing artifact {path.name}")
        if reasons:
            excluded.append({"videoId": vid, "reason": "; ".join(reasons)})
            continue
        # --- identity
        if acq.get("video_id") != vid:
            fail("acquisition video_id != directory name")
        if receipt.get("videoId") != vid:
            fail("receipt videoId != directory name")
        for doc, name in ((acq, "acquisition"), (receipt, "receipt")):
            if vid not in (doc.get("sourceUrl") or ""):
                fail(f"{name} sourceUrl does not contain video id")
        if acq.get("sourceUrl") != p.get("source_url"):
            fail("acquisition sourceUrl mismatch vs candidate list")
        # --- acquisition status + audio hash chain
        if acq.get("status") != "completed":
            fail(f"acquisition status {acq.get('status')}")
        if audio_path.is_symlink():
            fail("audio.mp3 is a symlink")
        audio_sha = audio_sha256(vid, audio_path)
        audio_bytes = audio_path.stat().st_size
        if audio_sha != acq.get("sha256"):
            fail("audio sha256 mismatch vs acquisition.json")
        if audio_bytes != acq.get("bytes"):
            fail("audio bytes mismatch vs acquisition.json")
        # --- ASR receipt
        if receipt.get("status") != "completed":
            fail(f"asr receipt status {receipt.get('status')}")
        if receipt.get("sourceType") != SOURCE_TYPE:
            fail(f"unexpected sourceType {receipt.get('sourceType')}")
        if receipt.get("audioSha256") != audio_sha:
            fail("receipt audioSha256 != audio file hash")
        if receipt.get("audioBytes") != audio_bytes:
            fail("receipt audioBytes != audio file size")
        settings = receipt.get("settings") or {}
        for k, v in EXPECTED_SETTINGS.items():
            if settings.get(k) != v:
                fail(f"ASR setting {k}: {settings.get(k)!r} != pinned {v!r}")
        if receipt.get("settingsSha256") != EXPECTED_SETTINGS_SHA256:
            fail("settingsSha256 does not recompute from pinned settings")
        code_edition = CODE_EDITION_MAP.get(receipt.get("codeSha256"))
        if not code_edition or code_edition.get("compatibleReuse") is not True:
            fail("ASR codeSha256 is not an allowlisted compatible receipt edition")
        for name, h in (receipt.get("outputSha256") or {}).items():
            op = d / name
            if not op.exists():
                fail(f"receipt-listed output {name} missing")
            elif sha256_path(op) != h:
                fail(f"receipt outputSha256 mismatch for {name}")
        if set((receipt.get("outputSha256") or {})) != {
                "asr-transcript.txt", "asr-segments.jsonl", "asr-transcript.srt"}:
            fail("receipt outputSha256 does not cover exactly the three ASR outputs")
        if receipt.get("humanValidated") is not False:
            fail("receipt humanValidated != false")
        if receipt.get("fullLength") is not True:
            fail("receipt fullLength != true")
        # --- segments (start/end/text -> startSeconds/endSeconds)
        recs = []
        try:
            for line in seg_path.read_text().splitlines():
                if line.strip():
                    r = json.loads(line)
                    recs.append({"startSeconds": float(r["start"]),
                                 "endSeconds": float(r["end"]),
                                 "text": (r["text"] or "").strip()})
        except Exception as e:
            fail(f"unreadable asr-segments.jsonl: {e}")
            recs = []
        if receipt.get("segmentCount") != len(recs):
            fail(f"segmentCount {receipt.get('segmentCount')} != jsonl lines {len(recs)}")
        prev = -1.0
        bad_ts = 0
        for r in recs:
            s, e = r["startSeconds"], r["endSeconds"]
            if s < 0 or e <= s:
                bad_ts += 1
            elif s < prev:
                bad_ts += 1
            else:
                prev = s
            if not r["text"]:
                fail("empty text segment")
                break
        if bad_ts:
            fail(f"{bad_ts} bad/non-monotonic timestamps")
        txt_text = txt_path.read_text()
        txt_words = len(txt_text.split())
        if receipt.get("wordCount") != txt_words:
            fail(f"receipt wordCount {receipt.get('wordCount')} != transcript words {txt_words}")
        n_srt_cues = len(re.findall(r"\d\d:\d\d:\d\d,\d\d\d --> \d\d:\d\d:\d\d,\d\d\d",
                                    srt_path.read_text()))
        if n_srt_cues != len(recs):
            fail(f"SRT cue count {n_srt_cues} != segment count {len(recs)}")
        # --- durations + full ASR coverage
        ff_dur = receipt.get("ffprobeDurationSeconds")
        dec_dur = receipt.get("decodedDurationSeconds")
        acq_dur = acq.get("duration_seconds")
        if not isinstance(ff_dur, (int, float)) or ff_dur <= 0:
            fail("receipt ffprobeDurationSeconds missing/invalid")
            ff_dur = None
        if ff_dur and isinstance(acq_dur, (int, float)):
            if abs(acq_dur - ff_dur) > 0.5:
                fail(f"acquisition duration {acq_dur} != ffprobe {ff_dur}")
        else:
            fail("acquisition duration_seconds missing/invalid")
        if ff_dur and isinstance(dec_dur, (int, float)):
            if abs(dec_dur - ff_dur) > 1.0:
                fail(f"decoded duration {dec_dur} != ffprobe {ff_dur}")
        else:
            fail("receipt decodedDurationSeconds missing/invalid")
        chunks = receipt.get("chunksProcessed")
        if not isinstance(chunks, int) or chunks < 1:
            fail("receipt chunksProcessed missing/invalid")
        elif isinstance(dec_dur, (int, float)) and \
                chunks * EXPECTED_SETTINGS["chunkSeconds"] < dec_dur - 1e-6:
            fail(f"decode windows ({chunks}x{EXPECTED_SETTINGS['chunkSeconds']}s) "
                 f"do not cover decoded duration {dec_dur}")
        last_end = recs[-1]["endSeconds"] if recs else 0.0
        if abs((receipt.get("lastSegmentEnd") or 0.0) - last_end) > 0.01:
            fail("receipt lastSegmentEnd != last jsonl segment end")
        coverage = (last_end / ff_dur) if ff_dur else 0.0
        coverage_note = "ok"
        if ff_dur:
            if coverage < MIN_ASR_COVERAGE:
                fail(f"ASR text coverage {coverage:.2f} < {MIN_ASR_COVERAGE} of audio duration")
            elif coverage < 0.95:
                coverage_note = (f"ASR text covers {coverage:.3f} of audio duration; "
                                 f"tail may be speech-free (VAD) or music")
            elif coverage > 1.0:
                coverage_note = (f"ASR last segment end exceeds ffprobe duration "
                                 f"({coverage:.4f}); final segment extends beyond nominal duration")
        # --- candidate metadata (uploader != practitioner != claimed entity)
        meta_notes = []
        for fk, pk in (("title", "title"), ("publisher", "publisher"),
                       ("practitionerContext", "practitioner"),
                       ("claimedGroup", "entity")):
            a, b = (acq.get(fk) or ""), (p.get(pk) or "")
            ra = receipt.get(fk) or ""
            if a != b or ra != b:
                if a.startswith(b) or b.startswith(a):
                    meta_notes.append(f"{fk}: acquisition '{a}' vs candidate '{b}' "
                                      f"(prefix-compatible; treated as same source)")
                else:
                    fail(f"{fk} mismatch vs candidate list (acquisition/receipt)")
        pilot_dur = p.get("duration_seconds")
        if ff_dur and isinstance(pilot_dur, (int, float)) and abs(pilot_dur - ff_dur) > 5:
            meta_notes.append(f"candidate metadata duration {pilot_dur}s vs audio "
                              f"{ff_dur:.1f}s (metadata rounded/different edition)")
        # --- ledger binding
        lg = lmap.get(vid)
        ledger_status = lg.get("status") if lg else "absent"
        if not lg:
            fail("no acquisition-ledger record")
        elif lg.get("status") != "completed":
            fail(f"ledger status {lg.get('status')}")
        else:
            if lg.get("sha256") != audio_sha:
                fail("ledger sha256 != audio hash")
            if lg.get("bytes") != audio_bytes:
                fail("ledger bytes != audio bytes")
            if ff_dur and isinstance(lg.get("duration_seconds"), (int, float)) and \
                    abs(lg["duration_seconds"] - ff_dur) > 0.5:
                fail("ledger duration_seconds != ffprobe duration")
        # --- summary binding (already gated, re-checked per record)
        s = summary_recs.get(vid)
        if not s or s.get("status") != "completed":
            fail("asr-summary.json does not show this candidate completed")
        elif s.get("audioSha256") != audio_sha or \
                s.get("outputSha256") != receipt.get("outputSha256"):
            fail("asr-summary record not bound to on-disk receipt/outputs")
        # --- language: pinned model is English-only
        full_text = "\n".join(r["text"] for r in recs)
        detected = detect_language(full_text)
        wpm = txt_words / (ff_dur / 60) if ff_dur else 0.0
        word_tokens = full_text.lower().split()
        rep3 = trigram_repeat_share(word_tokens)
        lang_note = "ok"
        if receipt.get("detectedLanguage") != detected or \
                receipt.get("languageReviewRequired") is not False or \
                not isinstance(receipt.get("wordRateWpm"), (int, float)) or \
                receipt.get("wordRateWpm") < MIN_SUPPORTED_WPM or \
                not isinstance(receipt.get("languageVerified"), bool):
            fail("completed receipt lacks complete language metadata/backfill")
        if detected != "en":
            fail(f"unsupported language for pinned English-only ASR: detected "
                 f"'{detected}' in ASR output")
        elif wpm < MIN_SUPPORTED_WPM:
            fail(f"unsupported language for pinned English-only ASR: degenerate "
                 f"output at {wpm:.1f} words/min over {ff_dur:.0f}s with repeated-"
                 f"trigram share {rep3:.3f} (tiny.en forced onto non-English audio "
                 f"emits sparse repetitive hallucinated English, not a transcript)")
        prior = prior_lang.get(vid)
        edition_note = "ok"
        if prior and prior != "en" and detected == "en":
            edition_note = (f"prior provider-rendered subtitle edition for this video "
                            f"was detected '{prior}' while the audio ASR detects English; "
                            f"editions differ (subtitle edition is not the audio language)")
        if detected == "en" and rep3 > 0.20:
            lang_note = (f"elevated repeated-trigram share {rep3:.3f}; ASR repetition "
                         f"loops possible in passages (style or hallucination); flagged, "
                         f"not excluded at {wpm:.1f} words/min")
        canonical = json.dumps(recs, ensure_ascii=False, sort_keys=True)
        meta = {
            "videoId": vid,
            "title": acq.get("title"),
            "publisher": acq.get("publisher"),
            "practitionerContext": acq.get("practitionerContext"),
            "claimedGroup": acq.get("claimedGroup"),
            "sourceUrl": acq.get("sourceUrl"),
            "sourceType": SOURCE_TYPE,
            "asrProvider": PROVIDER,
            "audioRoute": acq.get("route"),
            "audioEdition": receipt.get("audioEdition"),
            "detectedLanguage": detected,
            "languageNote": lang_note,
            "coverageNote": coverage_note,
            "editionNote": edition_note,
            "metadataNote": "; ".join(meta_notes) if meta_notes else "ok",
            "retrievedAt": acq.get("retrievedAt"),
            "asrCompletedUtc": receipt.get("completedUtc"),
            "segmentCount": len(recs),
            "durationSeconds": ff_dur,
            "decodedDurationSeconds": dec_dur,
            "candidateMetadataDurationSeconds": pilot_dur,
            "lastSegmentEnd": last_end,
            "asrCoverage": round(coverage, 4),
            "chunksProcessed": chunks,
            "wordCount": txt_words,
            "wordsPerMinute": round(wpm, 1),
            "repeatedTrigramShare": round(rep3, 4),
            "audioSha256": audio_sha,
            "audioBytes": audio_bytes,
            "transcriptTxtSha256": (receipt.get("outputSha256") or {}).get("asr-transcript.txt"),
            "segmentsSha256": (receipt.get("outputSha256") or {}).get("asr-segments.jsonl"),
            "srtSha256": (receipt.get("outputSha256") or {}).get("asr-transcript.srt"),
            "recordsSha256": sha256_text(canonical),
            "textSha256": sha256_text(full_text),
            "settingsSha256": receipt.get("settingsSha256"),
            "codeSha256": receipt.get("codeSha256"),
            "codeEditionStatus": (code_edition or {}).get("status", "unknown"),
            "codeEditionSourceSnapshotVerified": bool(
                (code_edition or {}).get("sourceSnapshotVerified")),
            "modelId": EXPECTED_SETTINGS["modelId"],
            "modelRevision": EXPECTED_SETTINGS["revision"],
            "asrVersions": receipt.get("versions"),
            "ledgerStatus": ledger_status,
            "humanValidated": False,
        }
        if reasons:
            excluded.append({"videoId": vid, "reason": "; ".join(reasons)})
        else:
            included.append((meta, recs))
    off_candidate = sorted(d.name for d in RAW.iterdir()
                           if d.is_dir() and d.name not in candidates)
    return included, excluded, held, candidates, ledger, off_candidate


# ---------------------------------------------------------------- phase 2
def build_segment_index(included):
    PRIV.mkdir(parents=True, exist_ok=True)
    db = PRIV / "segment-index.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE sources(
      video_id TEXT PRIMARY KEY, title TEXT, publisher TEXT,
      practitioner_context TEXT, claimed_group TEXT, source_url TEXT,
      source_type TEXT, asr_provider TEXT, detected_language TEXT,
      retrieved_at TEXT, asr_completed_utc TEXT,
      segment_count INTEGER, duration_seconds REAL, decoded_duration_seconds REAL,
      last_segment_end REAL, asr_coverage REAL, word_count INTEGER,
      audio_sha256 TEXT, audio_bytes INTEGER, transcript_txt_sha256 TEXT,
      segments_sha256 TEXT, srt_sha256 TEXT, records_sha256 TEXT,
      text_sha256 TEXT, settings_sha256 TEXT, human_validated INTEGER);
    CREATE TABLE segments(
      video_id TEXT, seg_id INTEGER, start_seconds REAL, end_seconds REAL,
      text TEXT, n_words INTEGER, PRIMARY KEY(video_id, seg_id));
    """)
    for meta, recs in included:
        con.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (meta["videoId"], meta["title"], meta["publisher"],
                     meta["practitionerContext"], meta["claimedGroup"],
                     meta["sourceUrl"], meta["sourceType"], meta["asrProvider"],
                     meta["detectedLanguage"], meta["retrievedAt"],
                     meta["asrCompletedUtc"], meta["segmentCount"],
                     meta["durationSeconds"], meta["decodedDurationSeconds"],
                     meta["lastSegmentEnd"], meta["asrCoverage"], meta["wordCount"],
                     meta["audioSha256"], meta["audioBytes"],
                     meta["transcriptTxtSha256"], meta["segmentsSha256"],
                     meta["srtSha256"], meta["recordsSha256"], meta["textSha256"],
                     meta["settingsSha256"], int(bool(meta["humanValidated"]))))
        con.executemany(
            "INSERT INTO segments VALUES(?,?,?,?,?,?)",
            [(meta["videoId"], i, r["startSeconds"], r["endSeconds"], r["text"],
              len(r["text"].split())) for i, r in enumerate(recs)])
    con.commit()
    con.close()


# ---------------------------------------------------------------- phase 3
def extract_units(meta, recs):
    """Extract literal question units with bounded answer windows."""
    qflag = [bool(qsentences(r["text"])) for r in recs]
    units = []
    i = 0
    while i < len(recs):
        if not qflag[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(recs) and qflag[j + 1] and \
                recs[j + 1]["startSeconds"] - recs[j]["endSeconds"] <= MERGE_GAP:
            j += 1
        block = recs[i:j + 1]
        qs, selfans = [], False
        for r in block:
            ss = sentences(r["text"])
            for idx, x in enumerate(ss):
                if "?" in x or "؟" in x:
                    qs.append(x)
                    if idx + 1 < len(ss):
                        selfans = True
        forms = [classify_form(q) for q in qs]
        nontag = [f for f in forms if f != "tag_question"]
        primary = nontag[0] if nontag else "tag_only"
        qtext = " ".join(qs)
        if SEC_RE.search(qtext):
            disc = "secondary_report"
        elif SELF_RE.search(qtext):
            disc = "self_report"
        elif primary == "tag_only":
            disc = "rhetorical_candidate"
        elif IMP_RE.search(qtext.lower()) or ADDRESS_RE.search(qtext):
            disc = "direct_interview_candidate"
        else:
            disc = "unclear_dialogue_context"
        # answer window
        asegs, status = [], None
        k = j + 1
        while k < len(recs):
            if qflag[k]:
                status = "interrupted_by_next_question" if asegs else "no_answer_window"
                break
            asegs.append(recs[k])
            if len(asegs) >= ANS_MAX_LINES:
                status = "complete_line_cap"
                break
            if recs[k]["endSeconds"] - block[-1]["endSeconds"] >= ANS_MAX_SEC:
                status = "complete_time_cap"
                break
            k += 1
        if status is None:
            status = ("no_answer_end_of_transcript" if not asegs
                      else "end_of_transcript_boundary_unknown")
        atext = " ".join(r["text"] for r in asegs)
        if meta["detectedLanguage"] in ("en", "de"):
            family = classify_family(qtext)
            orientation = classify_orientation(atext, status)
        else:
            # Question marks and answer windows are still literal/verifiable,
            # but the English/German semantic codebooks must not be imposed on
            # unsupported languages. AI review may add a bounded textual note.
            family = "not_assessed_language"
            orientation = "not_assessed_language"
        toks = sorted(set(tokens(qtext, meta["detectedLanguage"])))
        fam_key = hashlib.sha256(" ".join(toks).encode()).hexdigest()[:16] if toks else None
        units.append({
            "unitId": f'{meta["videoId"]}:{i}',
            "videoId": meta["videoId"],
            "publisher": meta["publisher"],
            "practitioner": meta["practitionerContext"],
            "claimedGroup": meta["claimedGroup"],
            "language": meta["detectedLanguage"],
            "startSeconds": block[0]["startSeconds"],
            "endSeconds": block[-1]["endSeconds"],
            "nQuestionSentences": len(qs),
            "primaryForm": primary,
            "forms": forms,
            "discourseClass": disc,
            "selfAnsweredSameFlow": selfans,
            "questionText": qtext,
            "questionSha256": sha256_text(qtext),
            "answerStatus": status,
            "answerLines": len(asegs),
            "answerSeconds": round(asegs[-1]["endSeconds"] - asegs[0]["startSeconds"], 1) if asegs else 0,
            "answerText": atext,
            "answerSha256": sha256_text(atext),
            "answerOrientation": orientation,
            "questionFamily": family,
            "familyKey": fam_key,
        })
        i = j + 1
    return units


# ---------------------------------------------------------------- phase 4
def corpus_analysis(included, all_units):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.decomposition import NMF
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score, adjusted_rand_score
    from sklearn.metrics.pairwise import cosine_similarity

    docs, metas = [], []
    for meta, recs in included:
        docs.append(" ".join(r["text"] for r in recs))
        metas.append(meta)
    n = len(docs)
    langs = [m["detectedLanguage"] for m in metas]
    # Language-aware Unicode tokenization and stopword/proper-name masking.
    # Diagnostics make a large source reduced to a handful of analysis tokens
    # visible instead of letting it silently distort NMF or the network.
    masked, token_diagnostics = [], []
    for meta, text, lg in zip(metas, docs, langs):
        stop = stoplist_for(lg) | PROPER_NAMES
        raw_tokens = WORD_RE.findall(text.lower())
        kept = [t for t in raw_tokens if t not in stop]
        masked.append(" ".join(kept))
        token_diagnostics.append({
            "videoId": meta["videoId"], "detectedLanguage": lg,
            "rawTokenCount": len(raw_tokens), "analysisTokenCount": len(kept),
            "analysisUniqueTokenCount": len(set(kept)),
            "analysisTokenShare": round(len(kept) / max(1, len(raw_tokens)), 4)})
    out = {"nDocuments": n, "languages": dict(Counter(langs)),
           "tokenizationDiagnostics": token_diagnostics,
           "properNamesExcludedFromTfidfNmf": True,
           "limits": LIMIT_LINE}
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, min_df=1,
                          max_df=0.95, token_pattern=r"(?u)\b\w[\wäöüß]+\b")
    X = vec.fit_transform(masked)
    feats = np.array(vec.get_feature_names_out())
    # corpus-level top terms
    mean_tfidf = np.asarray(X.mean(axis=0)).ravel()
    top = mean_tfidf.argsort()[::-1][:40]
    out["tfidfTopCorpus"] = [{"term": feats[i], "score": round(float(mean_tfidf[i]), 4)}
                             for i in top]
    # per-document top terms
    out["tfidfTopPerDocument"] = {}
    for m, row in zip(metas, X):
        r = row.toarray().ravel()
        idx = r.argsort()[::-1][:15]
        out["tfidfTopPerDocument"][m["videoId"]] = [
            {"term": feats[i], "score": round(float(r[i]), 4)}
            for i in idx if r[i] > 0]
    # overlays: publisher / practitioner / claimed-entity (three distinct roles)
    def overlay(key):
        groups = defaultdict(list)
        for i, m in enumerate(metas):
            groups[m[key]].append(i)
        res = {}
        for g, idxs in sorted(groups.items()):
            sub = np.asarray(X[idxs].mean(axis=0)).ravel()
            ti = sub.argsort()[::-1][:12]
            res[g] = {"nDocs": len(idxs),
                      "topTerms": [{"term": feats[t], "score": round(float(sub[t]), 4)}
                                   for t in ti if sub[t] > 0]}
        return res
    out["overlayByPublisher"] = overlay("publisher")
    out["overlayByPractitioner"] = overlay("practitionerContext")
    out["overlayByClaimedGroup"] = overlay("claimedGroup")

    # NMF topics + seed stability
    k = min(6, max(2, n - 1))
    rng_seeds = [SEED + i for i in range(10)]
    # base model: deterministic nndsvda init; stability runs: random init,
    # because nndsvda is seed-independent and would trivially score 1.0.
    nmf_max_iter = 1200
    nmf = NMF(n_components=k, init="nndsvda", random_state=SEED, max_iter=nmf_max_iter)
    Wm = nmf.fit_transform(X)
    Hm = nmf.components_
    topic_seeds = []
    topic_seed_iterations = []
    for s in rng_seeds:
        nmf2 = NMF(n_components=k, init="random", random_state=s, max_iter=nmf_max_iter)
        nmf2.fit_transform(X)
        topic_seeds.append(nmf2.components_)
        topic_seed_iterations.append(int(nmf2.n_iter_))
    # seed stability: greedy best-match cosine of topic vectors vs base
    stab = []
    for H2 in topic_seeds:
        sims = cosine_similarity(Hm, H2)
        stab.append(float(sims.max(axis=1).mean()))
    topics = []
    for ti in range(k):
        ti_idx = Hm[ti].argsort()[::-1][:12]
        topics.append({"topic": ti,
                       "topTerms": [feats[x] for x in ti_idx],
                       "weights": [round(float(Hm[ti][x]), 4) for x in ti_idx]})
    all_nmf_iterations = [int(nmf.n_iter_)] + topic_seed_iterations
    all_nmf_converged = all(i < nmf_max_iter for i in all_nmf_iterations)
    n_nonconverged = sum(i >= nmf_max_iter for i in all_nmf_iterations)
    convergence_note = ("No nonconverged runs occurred; all runs stopped before the iteration cap."
                        if all_nmf_converged else
                        f"{n_nonconverged} run(s) were nonconverged at the iteration cap; "
                        "the stability statistic is descriptive only.")
    out["nmf"] = {"k": k, "topics": topics,
                  "seedStabilityMeanBestMatchCosine": round(float(np.mean(stab)), 4),
                  "seedStabilityPerSeed": [round(s, 4) for s in stab],
                  "maxIter": nmf_max_iter,
                  "baseIterations": int(nmf.n_iter_),
                  "randomInitIterations": topic_seed_iterations,
                  "allRunsConvergedBeforeMaxIter": all_nmf_converged,
                  "caution": f"NMF on {n} short ASR documents is a diagnostic only; "
                             f"no population significance and no stable semantic "
                             f"structure is claimed. Base model uses deterministic "
                             f"nndsvda init; seed stability compares 10 random-init "
                             f"runs against it (best-match cosine). {convergence_note}",
                  "stabilityProtocol": f"base=nndsvda(seed {SEED}); 10 runs init=random"}
    out["nmfDocWeights"] = {m["videoId"]: [round(float(v), 4) for v in Wm[i]]
                            for i, m in enumerate(metas)}
    # topic x claimed-entity matrix
    ent = sorted({m["claimedGroup"] for m in metas})
    txe = np.zeros((k, len(ent)))
    for i, m in enumerate(metas):
        txe[:, ent.index(m["claimedGroup"])] += Wm[i]
    out["topicXEntity"] = {"entities": ent,
                           "matrix": [[round(float(v), 3) for v in row] for row in txe]}
    # KMeans diagnostics
    kd = []
    Xd = X.toarray()
    for kk in range(2, min(9, n)):
        sils, aris = [], []
        labels_base = None
        for s in rng_seeds:
            km = KMeans(n_clusters=kk, n_init=10, random_state=s)
            lab = km.fit_predict(Xd)
            sils.append(float(silhouette_score(Xd, lab)))
            if s == SEED:
                labels_base = lab
            elif labels_base is not None:
                # The base-vs-itself ARI=1 is not evidence and is excluded.
                aris.append(float(adjusted_rand_score(labels_base, lab)))
        kd.append({"k": kk, "silhouetteMean": round(float(np.mean(sils)), 4),
                   "silhouetteSd": round(float(np.std(sils)), 4),
                   "seedStabilityARIvsBase": round(float(np.mean(aris)), 4),
                   "ariComparisons": len(aris), "selfComparisonsExcluded": True})
    out["kmeansDiagnostics"] = {"sweep": kd,
                                "caution": f"KMeans on {n} documents is unstable by "
                                           f"construction; silhouettes and ARI are "
                                           f"reported as diagnostics, not evidence of "
                                           f"natural clusters."}
    # document similarity network
    sim = cosine_similarity(X)
    thr = 0.10
    edges = {}
    for i in range(n):
        for j in range(i + 1, n):
            if sim[i, j] >= thr:
                edges[(i, j)] = round(float(sim[i, j]), 3)
    # Keep each node's single strongest positive neighbor below threshold as a
    # documented visualization aid. All-zero nodes remain isolated: a zero-
    # weight edge would falsely imply a meaningful strongest relationship.
    for i in range(n):
        j_best = max((j for j in range(n) if j != i), key=lambda j: sim[i, j])
        if sim[i, j_best] > 0:
            key = (min(i, j_best), max(i, j_best))
            edges.setdefault(key, round(float(sim[key]), 3))
    out["documentNetwork"] = {"nodes": [m["videoId"] for m in metas],
                              "edges": [{"a": metas[i]["videoId"],
                                         "b": metas[j]["videoId"], "weight": w}
                                        for (i, j), w in sorted(edges.items())],
                              "threshold": thr,
                              "weakestEdgeRule": "each node with a positive-similarity "
                                                 "neighbor keeps its strongest edge even "
                                                 "below threshold; all-zero nodes remain isolated",
                              "meanSimilarity": round(float(sim[np.triu_indices(n, 1)].mean()), 4),
                              "maxSimilarity": round(float(sim[np.triu_indices(n, 1)].max()), 4)}
    # temporal / duration profiles
    prof = []
    for m, recs in included:
        u = [x for x in all_units if x["videoId"] == m["videoId"]]
        mins = m["durationSeconds"] / 60
        direct = [x for x in u if x["discourseClass"] == "direct_interview_candidate"]
        thirds = [0, 0, 0]
        for x in u:
            frac = x["startSeconds"] / m["durationSeconds"] if m["durationSeconds"] else 0
            thirds[min(2, int(frac * 3))] += 1
        prof.append({"videoId": m["videoId"], "publisher": m["publisher"],
                     "claimedGroup": m["claimedGroup"],
                     "language": m["detectedLanguage"],
                     "durationSeconds": m["durationSeconds"],
                     "decodedDurationSeconds": m["decodedDurationSeconds"],
                     "asrCoverage": m["asrCoverage"],
                     "lastSegmentEnd": m["lastSegmentEnd"],
                     "segmentCount": m["segmentCount"], "wordCount": m["wordCount"],
                     "wordsPerMinute": m["wordsPerMinute"],
                     "segmentsPerMinute": round(m["segmentCount"] / mins, 2) if mins else 0,
                     "repeatedTrigramShare": m["repeatedTrigramShare"],
                     "questionUnits": len(u),
                     "directQuestions": len(direct),
                     "questionsPer10Min": round(len(u) / mins * 10, 2) if mins else 0,
                     "questionUnitsByThird": {"first": thirds[0], "middle": thirds[1],
                                              "last": thirds[2]}})
    out["durationProfiles"] = prof
    # proper-name / commercial sensitivity
    sens = []
    for m, text in zip(metas, docs):
        toks = WORD_RE.findall(text.lower())
        name_hits = sum(1 for t in toks if t in PROPER_NAMES)
        comm_hits = len(COMMERCIAL_RE.findall(text))
        sens.append({"videoId": m["videoId"], "properNameHits": name_hits,
                     "properNameShare": round(name_hits / max(1, len(toks)), 4),
                     "commercialHits": comm_hits})
    out["sensitivity"] = {"perDocument": sens,
                          "note": "TF-IDF/NMF already exclude the proper-name list and "
                                  "commercial tokens are counted with an English-oriented "
                                  "regex, not a cross-language advertisement detector; top "
                                  "terms are computed with names removed to show sensitivity."}
    # topic-vs-ET comparison note
    out["topicVsEntityNote"] = (
        "Topics are compared against claimed-entity labels as publisher-attached "
        "metadata only; no physical-origin or ontological claim is made or implied.")
    return out, (vec, X, feats, Wm, Hm, metas, sim)


# ---------------------------------------------------------------- phase 5
def qa_aggregation(all_units, included):
    """Per-ET/per-publisher question aggregates + common-question families."""
    by_entity = defaultdict(list)
    by_publisher = defaultdict(list)
    for u in all_units:
        by_entity[u["claimedGroup"]].append(u)
        by_publisher[u["publisher"]].append(u)

    def rollup(units):
        fams = Counter(u["questionFamily"] for u in units)
        forms = Counter(u["primaryForm"] for u in units)
        disc = Counter(u["discourseClass"] for u in units)
        orient = Counter(u["answerOrientation"] for u in units)
        status = Counter(u["answerStatus"] for u in units)
        return {"nUnits": len(units), "nQuestionSentences": sum(u["nQuestionSentences"] for u in units),
                "families": dict(fams), "forms": dict(forms), "discourseClasses": dict(disc),
                "answerOrientations": dict(orient), "answerStatuses": dict(status)}
    # common-question families across sources
    fam_groups = defaultdict(list)
    familyless = 0
    for u in all_units:
        # Tag-only and other stopword-only units carry no content tokens;
        # grouping them would create a spurious empty-key 'common question'.
        # They stay family-less in the public rows and are excluded here; the
        # rule is documented in protocol.json.
        if not u["familyKey"]:
            familyless += 1
            continue
        fam_groups[u["familyKey"]].append(u)
    common = []
    for key, us in sorted(fam_groups.items(), key=lambda kv: -len(kv[1])):
        pubs = {x["publisher"] for x in us}
        vids = {x["videoId"] for x in us}
        risk = "high" if len(pubs) >= 2 else ("medium" if len(vids) >= 2 else "low")
        example = max(us, key=lambda x: len(x["questionText"]))
        common.append({
            "familyKey": key,
            "occurrences": len(us),
            "nPublishers": len(pubs), "nVideos": len(vids),
            "repostRisk": risk,
            "questionFamily": Counter(x["questionFamily"] for x in us).most_common(1)[0][0],
            "exampleQuestionSha256": example["questionSha256"],
            "exampleVideoId": example["videoId"],
            "exampleStartSeconds": example["startSeconds"],
            "exampleParaphraseNote": "exact text held in private index only",
        })
    repeated_anywhere = [c for c in common if c["occurrences"] >= 2]
    shared_across_videos = [c for c in common if c["nVideos"] >= 2]
    repeated_within_one_video = [c for c in repeated_anywhere if c["nVideos"] == 1]
    qa = {
        "totalUnits": len(all_units),
        "totalQuestionSentences": sum(u["nQuestionSentences"] for u in all_units),
        "perClaimedEntity": {k: rollup(v) for k, v in sorted(by_entity.items())},
        "perPublisher": {k: rollup(v) for k, v in sorted(by_publisher.items())},
        "familyTotals": dict(Counter(u["questionFamily"] for u in all_units)),
        "discourseTotals": dict(Counter(u["discourseClass"] for u in all_units)),
        "orientationTotals": dict(Counter(u["answerOrientation"] for u in all_units)),
        "unclassifiedDefaultUnits": sum(u["answerOrientation"] == "unclassified_default" for u in all_units),
        "answerStatusTotals": dict(Counter(u["answerStatus"] for u in all_units)),
        "familylessStopwordOnlyUnits": familyless,
        "commonQuestionFamilies": {
            "nFamilies": len(common),
            "nSharedAcrossVideos": len(shared_across_videos),
            "nRepeatedWithinSingleVideo": len(repeated_within_one_video),
            "nRepeatedAnywhere": len(repeated_anywhere),
            "riskTotalsAllFamilies": dict(Counter(c["repostRisk"] for c in common)),
            "families": common[:50]},
        "caution": ("Question classes are textual heuristics without diarization; "
                    "orientation describes answer-text shape only; no truth/agreement/"
                    "consensus assessment is made. Entity labels are publisher metadata."),
    }
    return qa, common


# ---------------------------------------------------------------- phase 6
def write_public_outputs(included, excluded, all_units, common, qa):
    # private full Q&A DB (exact text) -- private root only
    qdb = PRIV / "qa-full.sqlite"
    if qdb.exists():
        qdb.unlink()
    con = sqlite3.connect(qdb)
    con.execute("""CREATE TABLE qa(
      unit_id TEXT PRIMARY KEY, video_id TEXT, publisher TEXT, practitioner TEXT,
      claimed_group TEXT, language TEXT, start_seconds REAL, end_seconds REAL,
      n_question_sentences INTEGER, primary_form TEXT, discourse_class TEXT,
      question_text TEXT, question_sha256 TEXT, answer_status TEXT,
      answer_lines INTEGER, answer_seconds REAL, answer_text TEXT,
      answer_sha256 TEXT, answer_orientation TEXT, question_family TEXT,
      family_key TEXT)""")
    for u in all_units:
        con.execute("INSERT INTO qa VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (u["unitId"], u["videoId"], u["publisher"], u["practitioner"],
                     u["claimedGroup"], u["language"], u["startSeconds"], u["endSeconds"],
                     u["nQuestionSentences"], u["primaryForm"], u["discourseClass"],
                     u["questionText"], u["questionSha256"], u["answerStatus"],
                     u["answerLines"], u["answerSeconds"], u["answerText"],
                     u["answerSha256"], u["answerOrientation"], u["questionFamily"],
                     u["familyKey"]))
    con.commit()
    con.close()

    # public metadata/hashes-only registry (sqlite)
    pdb = ROOT / "non-bashar-public.sqlite"
    if pdb.exists():
        pdb.unlink()
    con = sqlite3.connect(pdb)
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
      question_family TEXT, family_key TEXT);
    CREATE TABLE question_families(
      family_key TEXT PRIMARY KEY, occurrences INTEGER, n_publishers INTEGER,
      n_videos INTEGER, repost_risk TEXT, question_family TEXT,
      example_video_id TEXT, example_start_seconds REAL,
      example_question_sha256 TEXT);
    CREATE TABLE validation_exclusions(
      video_id TEXT, reason TEXT, in_original_pilot_list INTEGER,
      in_candidate_list INTEGER);
    """)
    for meta, recs in included:
        con.execute("INSERT INTO sources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (meta["videoId"], meta["title"], meta["publisher"],
                     meta["practitionerContext"], meta["claimedGroup"],
                     meta["sourceUrl"], meta["sourceType"], meta["asrProvider"],
                     meta["audioRoute"], meta["audioEdition"],
                     meta["detectedLanguage"], meta["languageNote"],
                     meta["retrievedAt"], meta["asrCompletedUtc"],
                     meta["segmentCount"], meta["durationSeconds"],
                     meta["decodedDurationSeconds"], meta["candidateMetadataDurationSeconds"],
                     meta["lastSegmentEnd"], meta["asrCoverage"], meta["chunksProcessed"],
                     meta["wordCount"], meta["wordsPerMinute"], meta["repeatedTrigramShare"],
                     meta["audioSha256"], meta["audioBytes"], meta["transcriptTxtSha256"],
                     meta["segmentsSha256"], meta["srtSha256"], meta["recordsSha256"],
                     meta["textSha256"], meta["settingsSha256"], meta["codeSha256"],
                     meta["modelId"], meta["modelRevision"], meta["ledgerStatus"],
                     int(bool(meta["humanValidated"])), meta["coverageNote"],
                     meta["editionNote"], meta["metadataNote"], LIMIT_LINE))
    for u in all_units:
        con.execute("INSERT INTO qa_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (u["unitId"], u["videoId"], u["publisher"], u["claimedGroup"],
                     u["language"], u["startSeconds"], u["endSeconds"],
                     u["nQuestionSentences"], u["primaryForm"], u["discourseClass"],
                     u["questionSha256"], u["answerStatus"], u["answerLines"],
                     u["answerSeconds"], u["answerSha256"], u["answerOrientation"],
                     u["questionFamily"], u["familyKey"]))
    for c in common:
        con.execute("INSERT INTO question_families VALUES(?,?,?,?,?,?,?,?,?)",
                    (c["familyKey"], c["occurrences"], c["nPublishers"], c["nVideos"],
                     c["repostRisk"], c["questionFamily"], c["exampleVideoId"],
                     c["exampleStartSeconds"], c["exampleQuestionSha256"]))
    original_pilot_ids = {v["video_id"] for v in json.loads(ORIGINAL_PILOT.read_text())}
    candidate_ids = set(load_candidates())
    for e in excluded:
        con.execute("INSERT INTO validation_exclusions VALUES(?,?,?,?)",
                    (e["videoId"], e["reason"], int(e["videoId"] in original_pilot_ids),
                     int(e["videoId"] in candidate_ids)))
    con.commit()
    con.close()

    # public CSVs
    with open(ROOT / "non-bashar-public.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["unit_id", "video_id", "publisher", "claimed_group", "language",
                    "start_seconds", "end_seconds", "n_question_sentences",
                    "primary_form", "discourse_class", "question_sha256",
                    "answer_status", "answer_lines", "answer_seconds",
                    "answer_sha256", "answer_orientation", "question_family",
                    "family_key"])
        for u in all_units:
            w.writerow([u["unitId"], u["videoId"], u["publisher"], u["claimedGroup"],
                        u["language"], u["startSeconds"], u["endSeconds"],
                        u["nQuestionSentences"], u["primaryForm"], u["discourseClass"],
                        u["questionSha256"], u["answerStatus"], u["answerLines"],
                        u["answerSeconds"], u["answerSha256"], u["answerOrientation"],
                        u["questionFamily"], u["familyKey"] or ""])
    with open(ROOT / "sources-index.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["video_id", "title", "publisher", "practitioner_context",
                    "claimed_group", "source_url", "source_type", "asr_provider",
                    "audio_route", "audio_edition", "detected_language",
                    "language_note", "retrieved_at", "asr_completed_utc",
                    "segment_count", "duration_seconds",
                    "decoded_duration_seconds", "candidate_metadata_duration_seconds",
                    "last_segment_end", "asr_coverage", "chunks_processed",
                    "word_count", "words_per_minute", "repeated_trigram_share",
                    "audio_sha256", "audio_bytes", "transcript_txt_sha256",
                    "segments_sha256", "srt_sha256", "records_sha256",
                    "text_sha256", "settings_sha256", "code_sha256",
                    "model_id", "model_revision", "ledger_status",
                    "human_validated", "coverage_note", "edition_note",
                    "metadata_note"])
        for meta, recs in included:
            w.writerow([meta["videoId"], meta["title"], meta["publisher"],
                        meta["practitionerContext"], meta["claimedGroup"],
                        meta["sourceUrl"], meta["sourceType"], meta["asrProvider"],
                        meta["audioRoute"], meta["audioEdition"],
                        meta["detectedLanguage"], meta["languageNote"],
                        meta["retrievedAt"], meta["asrCompletedUtc"],
                        meta["segmentCount"], meta["durationSeconds"],
                        meta["decodedDurationSeconds"], meta["candidateMetadataDurationSeconds"],
                        meta["lastSegmentEnd"], meta["asrCoverage"], meta["chunksProcessed"],
                        meta["wordCount"], meta["wordsPerMinute"], meta["repeatedTrigramShare"],
                        meta["audioSha256"], meta["audioBytes"], meta["transcriptTxtSha256"],
                        meta["segmentsSha256"], meta["srtSha256"], meta["recordsSha256"],
                        meta["textSha256"], meta["settingsSha256"], meta["codeSha256"],
                        meta["modelId"], meta["modelRevision"], meta["ledgerStatus"],
                        meta["humanValidated"], meta["coverageNote"],
                        meta["editionNote"], meta["metadataNote"]])
    with open(ROOT / "common-questions.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["family_key", "occurrences", "n_publishers", "n_videos",
                    "recurrence_scope", "repost_risk", "question_family", "example_video_id",
                    "example_start_seconds", "example_question_sha256"])
        for c in common:
            scope = ("cross_video" if c["nVideos"] > 1 else
                     "within_single_video" if c["occurrences"] > 1 else "singleton")
            w.writerow([c["familyKey"], c["occurrences"], c["nPublishers"],
                        c["nVideos"], scope, c["repostRisk"], c["questionFamily"],
                        c["exampleVideoId"], c["exampleStartSeconds"],
                        c["exampleQuestionSha256"]])

    # review sample for the AI manual review (private: contains text)
    import random
    rng = random.Random(SEED)
    if len(all_units) <= 60:
        sample = list(range(len(all_units)))
        rule = (f"all extracted question units ({len(all_units)} <= 60 target), "
                f"spanning every claimed-entity label present")
    else:
        by_ent = defaultdict(list)
        for i, u in enumerate(all_units):
            by_ent[u["claimedGroup"]].append(i)
        target = 66
        per_ent = {k: max(1, round(target * len(v) / max(1, len(all_units))))
                   for k, v in by_ent.items()}
        sample = []
        for k, idxs in by_ent.items():
            rng.shuffle(idxs)
            sample.extend(idxs[:per_ent[k]])
        # top up to target
        rest = [i for i in range(len(all_units)) if i not in sample]
        rng.shuffle(rest)
        sample.extend(rest[:max(0, target - len(sample))])
        rule = (f"stratified sample of {len(sample)} (>= 60) across claimed-entity "
                f"labels from {len(all_units)} units, seed {SEED}")
    review = []
    for i in sorted(sample):
        u = all_units[i]
        review.append({"unitId": u["unitId"], "videoId": u["videoId"],
                       "claimedGroup": u["claimedGroup"],
                       "startSeconds": u["startSeconds"],
                       "questionText": u["questionText"],
                       "answerText": u["answerText"][:1200],
                       "autoDiscourseClass": u["discourseClass"],
                       "autoAnswerStatus": u["answerStatus"],
                       "autoOrientation": u["answerOrientation"],
                       "autoFamily": u["questionFamily"]})
    (PRIV / "review-sample.json").write_text(json.dumps(review, indent=1, ensure_ascii=False))
    return len(review), rule


# ---------------------------------------------------------------- phase 7
def short_label(meta):
    pub = (meta["publisher"] or meta["videoId"])
    return pub[:22]


def make_figures(included, excluded, all_units, analysis, model):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import networkx as nx

    vec, X, feats, Wm, Hm, metas, sim = model
    figdir = ROOT / "figures"
    figdir.mkdir(exist_ok=True)
    plt.rcParams.update({"font.size": 8, "figure.dpi": 200})

    def foot(fig):
        fig.text(0.01, 0.005, LIMIT_LINE, fontsize=5.5, color="#555", wrap=True)

    def save(fig, name):
        fig.savefig(figdir / f"{name}.svg", bbox_inches="tight")
        fig.savefig(figdir / f"{name}.png", bbox_inches="tight")
        plt.close(fig)

    lang_colors = {"en": "#4477aa", "de": "#cc6677", "ar": "#aa9944", "unknown": "#999999"}

    # fig1 corpus/source coverage
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6),
                             gridspec_kw={"width_ratios": [2.4, 1]})
    labels = [short_label(m) for m in metas]
    words = [m["wordCount"] for m in metas]
    durs = [m["durationSeconds"] / 60 for m in metas]
    colors = [lang_colors.get(m["detectedLanguage"], "#999") for m in metas]
    y = np.arange(len(metas))
    axes[0].barh(y - 0.2, words, height=0.4, color=colors, label="words")
    ax2 = axes[0].twiny()
    ax2.barh(y + 0.2, durs, height=0.4, color="#dddddd", edgecolor="#888",
             label="minutes")
    axes[0].set_yticks(y, labels)
    axes[0].invert_yaxis()
    axes[0].set_xlabel("ASR whitespace words (colored by detected language)")
    ax2.set_xlabel("audio duration (minutes)", color="#666")
    axes[0].set_title("Included records: size and duration")
    ncomp = len(metas)
    nexcl_lang = sum(1 for e in excluded if "unsupported language" in e["reason"])
    nexcl_other = len(excluded) - nexcl_lang
    terminal = analysis["validation"]["terminalStateCounts"]
    cats = ["completed\n(included)", "excluded\n(unsupported lang.)", "excluded\n(other)",
            "held\n(route limit)"]
    vals = [ncomp, nexcl_lang, nexcl_other, terminal["held"]]
    axes[1].bar(cats, vals, color=["#4477aa", "#cc6677", "#ee8866", "#999999"])
    for i, v in enumerate(vals):
        axes[1].text(i, v + 0.1, str(v), ha="center")
    axes[1].set_title(f"Candidate validation outcomes ({terminal['totalCandidates']} records)")
    axes[1].set_ylim(0, max(vals + [1]) + 1.5)
    fig.suptitle("Fig 1. Non-Bashar self-run ASR corpus and source coverage", y=0.99)
    fig.tight_layout(rect=[0, 0.05, 1, 0.92])
    foot(fig)
    save(fig, "fig1_corpus_source_coverage")

    # fig2 NMF topic terms
    topics = analysis["nmf"]["topics"]
    k = len(topics)
    cols = 2
    rows = (k + 1) // 2
    fig, axes = plt.subplots(rows, cols, figsize=(10.5, 2.5 * rows))
    axes = np.array(axes).ravel()
    for t, ax in zip(topics, axes):
        terms = t["topTerms"][:10][::-1]
        wts = t["weights"][:10][::-1]
        ax.barh(terms, wts, color="#4477aa")
        ax.set_title(f"Topic {t['topic']}", fontsize=9)
    for ax in axes[len(topics):]:
        ax.axis("off")
    fig.suptitle(f"Fig 2. NMF topic top terms (k={k}; diagnostic, n={analysis['nDocuments']} docs; "
                 f"seed stability cosine={analysis['nmf']['seedStabilityMeanBestMatchCosine']})")
    fig.tight_layout(rect=[0, 0.03, 1, 0.95])
    foot(fig)
    save(fig, "fig2_topic_terms")

    # fig3 topic x claimed-entity heatmap
    txe = np.array(analysis["topicXEntity"]["matrix"])
    ents = analysis["topicXEntity"]["entities"]
    fig, ax = plt.subplots(figsize=(max(7, 1.1 * len(ents)), 3.6))
    im = ax.imshow(txe, aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(ents)),
                  [e[:26] for e in ents], rotation=35, ha="right")
    ax.set_yticks(range(txe.shape[0]), [f"topic {i}" for i in range(txe.shape[0])])
    for i in range(txe.shape[0]):
        for j in range(txe.shape[1]):
            if txe[i, j] >= 0.05:
                ax.text(j, i, f"{txe[i, j]:.1f}", ha="center", va="center",
                        fontsize=7, color="white")
    fig.colorbar(im, label="summed NMF weight")
    ax.set_title("Fig 3. Topic × claimed-entity label (metadata labels only; not physical origins)")
    fig.tight_layout(rect=[0, 0.04, 1, 1])
    foot(fig)
    save(fig, "fig3_topic_x_entity_heatmap")

    # fig4 document similarity network
    G = nx.Graph()
    for m in metas:
        G.add_node(m["videoId"])
    for e in analysis["documentNetwork"]["edges"]:
        G.add_edge(e["a"], e["b"], weight=e["weight"])
    pos = nx.spring_layout(G, seed=SEED)
    fig, ax = plt.subplots(figsize=(8.2, 6))
    node_colors = [lang_colors.get(m["detectedLanguage"], "#999") for m in metas]
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=700, ax=ax,
                           edgecolors="#333")
    widths = [max(0.6, G[u][v]["weight"] * 8) for u, v in G.edges]
    nx.draw_networkx_edges(G, pos, width=widths, alpha=0.55, ax=ax,
                           edge_color="#666")
    nx.draw_networkx_edge_labels(
        G, pos, {(u, v): f"{G[u][v]['weight']:.2f}" for u, v in G.edges},
        font_size=6, ax=ax)
    nx.draw_networkx_labels(G, pos,
                            {m["videoId"]: short_label(m) for m in metas},
                            font_size=7, ax=ax)
    dn = analysis["documentNetwork"]
    ax.set_title(f"Fig 4. Document similarity network (TF-IDF cosine; threshold "
                 f"{dn['threshold']} + strongest-neighbor rule; color = detected language)")
    ax.axis("off")
    foot(fig)
    save(fig, "fig4_document_network")

    # fig5 question families x entity + repost risk
    fams_order = list(FAMILY_PATTERNS.keys()) + ["other_theme"]
    fams_order += sorted({u["questionFamily"] for u in all_units} - set(fams_order))
    ent_list = sorted({m["claimedGroup"] for m in metas})
    mat = np.zeros((len(fams_order), len(ent_list)))
    for u in all_units:
        mat[fams_order.index(u["questionFamily"]), ent_list.index(u["claimedGroup"])] += 1
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6),
                             gridspec_kw={"width_ratios": [1.5, 1]})
    im = axes[0].imshow(mat, aspect="auto", cmap="magma")
    axes[0].set_xticks(range(len(ent_list)), [e[:22] for e in ent_list],
                       rotation=35, ha="right")
    axes[0].set_yticks(range(len(fams_order)), fams_order)
    vmax = max(1.0, mat.max())
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if mat[i, j] > 0:
                tc = "white" if mat[i, j] < 0.6 * vmax else "black"
                axes[0].text(j, i, int(mat[i, j]), ha="center", va="center",
                             fontsize=7, color=tc)
    axes[0].set_title("Question units: family × claimed-entity label")
    fig.colorbar(im, ax=axes[0], label="units")
    risks = Counter(analysis["qa"]["commonQuestionFamilies"]["riskTotalsAllFamilies"])
    axes[1].bar(["low", "medium", "high"],
                [risks.get("low", 0), risks.get("medium", 0), risks.get("high", 0)],
                color=["#4477aa", "#ddcc77", "#cc6677"])
    axes[1].set_title(f"All {analysis['qa']['commonQuestionFamilies']['nFamilies']} families by repost risk\n"
                      "(wording overlap; singletons included)")
    fig.suptitle("Fig 5. Question-family and common-question view (question TYPES only; "
                 "no truth/agreement assessment)")
    fig.tight_layout(rect=[0, 0.03, 1, 0.93])
    foot(fig)
    save(fig, "fig5_question_families")

    # fig6 duration vs question rates (temporal/duration profile view)
    prof = analysis["durationProfiles"]
    fig, ax = plt.subplots(figsize=(8.2, 5))
    ent_color = {e: plt.cm.tab20(i % 20) for i, e in enumerate(ent_list)}
    for p in prof:
        ax.scatter(p["durationSeconds"] / 60, p["questionsPer10Min"],
                   color=ent_color[p["claimedGroup"]], s=60, edgecolor="#333",
                   zorder=3)
        ax.annotate(p["publisher"][:18],
                    (p["durationSeconds"] / 60, p["questionsPer10Min"]),
                    fontsize=6.5, xytext=(4, 4), textcoords="offset points")
    ax.set_xlabel("audio duration (minutes, ffprobe of acquired audio)")
    ax.set_ylabel("question units per 10 minutes")
    ax.set_title("Fig 6. Duration profiles vs question rates (all discourse classes)")
    foot(fig)
    save(fig, "fig6_duration_question_rates")


# ---------------------------------------------------------------- main
def main():
    candidates = load_candidates()
    candidate_ids = sorted(candidates)
    problems = summary_gate(candidate_ids)
    if problems:
        print("Candidate terminal-state gate not satisfied; final build/verify must wait:")
        for pr in problems:
            print("  -", pr)
        (ROOT / "gate-status.json").write_text(json.dumps(
            {"ready": False, "candidateVideos": len(candidate_ids),
             "problems": problems}, indent=1))
        sys.exit(2)
    candidate_hash = sha256_text("\n".join(candidate_ids))
    (ROOT / "gate-status.json").write_text(json.dumps(
        {"ready": False, "candidateVideos": len(candidate_ids),
         "candidateIdsSha256": candidate_hash,
         "problems": ["build in progress; public outputs are not yet certified"]}, indent=1))
    included, excluded, held, candidates, ledger, off_candidate = validate_sources()
    print(f"included={len(included)} excluded={len(excluded)} held={len(held)} "
          f"offCandidateOnDisk={len(off_candidate)}")
    if not included:
        print("no validated sources; refusing to write outputs")
        sys.exit(2)
    build_segment_index(included)
    all_units = []
    for meta, recs in included:
        all_units.extend(extract_units(meta, recs))
    print(f"question units={len(all_units)}")
    analysis, model = corpus_analysis(included, all_units)
    qa, common = qa_aggregation(all_units, included)
    analysis["qa"] = qa
    analysis["validation"] = {
        "included": [m["videoId"] for m, _ in included],
        "excluded": excluded,
        "held": held,
        "offCandidateRecordsOnDisk": off_candidate,
        "candidateVideoCount": len(candidates),
        "audioEvidenceMode": ("earlier_full_hash_plus_current_receipts"
                              if REUSE_MEDIA else "full_rehash"),
        "terminalStateCounts": {
            "analyzed": len(included), "excluded": len(excluded), "held": len(held),
            "totalCandidates": len(candidates)},
        "languageNotes": {m["videoId"]: m["languageNote"] for m, _ in included
                          if m["languageNote"] != "ok"},
        "coverageNotes": {m["videoId"]: m["coverageNote"] for m, _ in included
                          if m["coverageNote"] != "ok"},
        "editionNotes": {m["videoId"]: m["editionNote"] for m, _ in included
                         if m["editionNote"] != "ok"},
        "metadataNotes": {m["videoId"]: m["metadataNote"] for m, _ in included
                          if m["metadataNote"] != "ok"},
        "providers": {m["videoId"]: {
            "asrProvider": m["asrProvider"], "sourceType": m["sourceType"],
            "audioRoute": m["audioRoute"], "modelId": m["modelId"],
            "modelRevision": m["modelRevision"],
            "settingsSha256": m["settingsSha256"],
            "codeSha256": m["codeSha256"],
            "codeEditionStatus": m["codeEditionStatus"],
            "codeEditionSourceSnapshotVerified": m["codeEditionSourceSnapshotVerified"],
            "asrVersions": m["asrVersions"]} for m, _ in included},
        "codeEditionCounts": [
            {"codeSha256": h, "status": status, "count": count}
            for (h, status), count in sorted(Counter(
                (m["codeSha256"], m["codeEditionStatus"]) for m, _ in included).items())],
        "codeEditionCaution": ("Historical receipt code hashes are allowlisted for artifact reuse. "
                               "Editions labeled legacy_receipt_hash_snapshot_unavailable have no "
                               "surviving source snapshot; pinned settings and output hashes are "
                               "verified, but source-code equivalence is not claimed."),
        "codeEditionManifestSha256": sha256_path(CODE_EDITIONS),
    }
    analysis["seed"] = SEED
    analysis["sourceBoundary"] = LIMIT_LINE
    analysis["generatedBy"] = "build.py (gated on asr-summary; deterministic seed 20261110)"
    n_review, rule = write_public_outputs(included, excluded, all_units, common, qa)
    analysis["manualReviewSampleSize"] = n_review
    analysis["manualReviewSampleRule"] = rule
    make_figures(included, excluded, all_units, analysis, model)
    (ROOT / "analysis.json").write_text(json.dumps(analysis, indent=1, ensure_ascii=False))
    (ROOT / "gate-status.json").write_text(json.dumps(
        {"ready": True, "candidateVideos": len(candidate_ids),
         "candidateIdsSha256": candidate_hash}, indent=1))
    print("wrote analysis.json, public sqlite/csv, figures, and final candidate gate")


if __name__ == "__main__":
    main()
