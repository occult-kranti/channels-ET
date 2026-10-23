#!/usr/bin/env python3
"""Experimental local question-window extractor for authorized caption segments.

Raw candidate windows must remain outside Git. A public manifest contains only
hashes, time boundaries and regex category indicators. This CLI has been tested
with synthetic fixtures only; no empirical caption extraction is implied.
"""
from __future__ import annotations
import argparse, hashlib, json, math, pathlib, re
from build_qa import classify, THEMES, MODALITY

def inside_git(path):
    path = path.resolve()
    # Managed sandboxes mount empty reserved .git directories at /tmp and
    # /workspace. They are not repository metadata; do not confuse them with a
    # checkout. Recognize real directory HEADs and linked-worktree gitdir files.
    for parent in (path, *path.parents):
        meta = parent / ".git"
        if meta.is_dir() and (meta / "HEAD").is_file(): return True
        if meta.is_file() and meta.read_text().strip().startswith("gitdir:"): return True
    return False

def validate(document):
    if not isinstance(document,dict) or not re.fullmatch(r"[A-Za-z0-9_-]{11}",str(document.get("video_id",""))):
        raise ValueError("Caption document requires an 11-character YouTube video_id")
    segments=document.get("segments")
    if not isinstance(segments,list):raise ValueError("segments must be a list")
    prior=-1
    for s in segments:
        if not isinstance(s,dict) or not isinstance(s.get("text"),str):raise ValueError("Every segment requires text")
        for key in ["start","duration"]:
            value=s.get(key)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:
                raise ValueError("Every segment requires finite nonnegative start and duration")
        if s["start"]<prior:raise ValueError("Segments must be ordered by start time")
        if not math.isfinite(s["start"]+s["duration"]):raise ValueError("Segment end must be finite")
        prior=s["start"]
    if document.get("is_generated") is not None and not isinstance(document["is_generated"],bool):
        raise ValueError("is_generated must be a boolean or unknown")
    if document.get("language_code") is not None and not isinstance(document["language_code"],str):
        raise ValueError("language_code must be text or unknown")
    for key in ["source_url","publisher_id"]:
        if document.get(key) is not None and not isinstance(document[key],str):
            raise ValueError(key+" must be text or unknown")
    for key in ["practitioner_names","context_entity_labels"]:
        if key in document and (not isinstance(document[key],list) or not all(isinstance(x,str) for x in document[key])):
            raise ValueError(key+" must be a list of inherited labels")

def extract(document):
    validate(document)
    vid = document["video_id"]
    segments = document["segments"]
    candidates = []
    for i, s in enumerate(segments):
        if "?" not in s.get("text", ""):
            continue
        following = []
        for j in range(i + 1, min(len(segments), i + 13)):
            next_segment = segments[j]
            # Exclude a whole segment crossing the cap; caption text has no
            # within-segment alignment that would justify textual truncation.
            if "?" in next_segment.get("text", "") or next_segment["start"] + next_segment["duration"] > s["start"] + 120:
                break
            following.append(next_segment)
        if not following:
            continue
        candidates.append({"id": f"caption-window-{vid}-{i:05d}", "video_id": vid,
                           "question_candidate": s["text"],
                           "answer_window_candidate": " ".join(x["text"] for x in following),
                           "question_segment_index": i, "question_start_seconds": s["start"],
                           "question_end_seconds": s["start"] + s["duration"],
                           "answer_start_seconds": following[0]["start"],
                           "answer_end_seconds": max(x["start"] + x["duration"] for x in following),
                           "speaker_verified": False, "turn_boundary_verified": False,
                           "evidence_type": "punctuation_based_caption_window_candidate",
                           "human_reviewed": False})
    return candidates

def run(input_path, output_path, manifest_path):
    if inside_git(input_path):
        raise ValueError("Raw caption input must remain outside every Git checkout")
    if inside_git(output_path):
        raise ValueError("Raw question/answer windows must be written outside every Git checkout")
    if output_path.resolve() == manifest_path.resolve():
        raise ValueError("Manifest and raw output require different paths")
    if output_path.exists() or manifest_path.exists():
        raise ValueError("Choose fresh output paths; existing files are never overwritten")
    document = json.loads(input_path.read_text())
    rows = extract(document)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps({"status": "unvalidated_candidates", "records": rows}, ensure_ascii=False, indent=2))
    public = [{"id": r["id"], "video_id": r["video_id"], "question_start_seconds": r["question_start_seconds"],
               "question_end_seconds": r["question_end_seconds"],
               "answer_start_seconds": r["answer_start_seconds"], "answer_end_seconds": r["answer_end_seconds"],
               "question_sha256": hashlib.sha256(r["question_candidate"].encode()).hexdigest(),
               "answer_window_sha256": hashlib.sha256(r["answer_window_candidate"].encode()).hexdigest(),
               "question_themes": classify(r["question_candidate"], THEMES),
               "answer_themes": classify(r["answer_window_candidate"], THEMES),
               "answer_modality_markers": classify(r["answer_window_candidate"], MODALITY),
               "speaker_verified": False, "turn_boundary_verified": False, "human_reviewed": False}
              for r in rows]
    source={"source_url":document.get("source_url") or "https://www.youtube.com/watch?v="+document["video_id"],
            "source_url_basis":"caller_supplied_unverified" if document.get("source_url") else "canonical_URL_from_video_ID_not_fetched",
            "language_code":document.get("language_code"),"is_generated":document.get("is_generated"),
            "practitioner_names":document.get("practitioner_names",[]),
            "context_entity_labels":document.get("context_entity_labels",[]),
            "publisher_id":document.get("publisher_id"),
            "attribution_status":"caller_supplied_labels_unverified" if any(document.get(k) for k in ["practitioner_names","context_entity_labels","publisher_id"]) else "unknown",
            "video_or_audio_inspected":False}
    for record in public:
        record.update(source)
        record["evidence_type"]="punctuation_based_caption_window_candidate"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"source_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
                                        "source":source,
                                        "evidence_type":"punctuation_based_caption_window_candidate",
                                        "method": "Question-mark-bearing segment followed by at most 12 whole segments ending within 120 seconds of question start, until the next question mark; no diarization",
                                        "status": "unvalidated_candidates", "records": public}, indent=2))
    return public

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=pathlib.Path);p.add_argument("raw_output", type=pathlib.Path)
    p.add_argument("public_manifest", type=pathlib.Path)
    a = p.parse_args()
    print(json.dumps({"candidate_windows": len(run(a.input, a.raw_output, a.public_manifest)), "speaker_validated": False}))
