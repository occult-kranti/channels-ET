#!/usr/bin/env python3
"""Build provenance-linked candidate Q&A from released AI digests, not raw speech.

This is an exploratory retrieval layer. It does not recover speaker turns,
validate a transcript, infer entity identity, or measure answer agreement.
"""
from __future__ import annotations
import argparse, collections, csv, hashlib, json, pathlib, re, sqlite3

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
ATLAS = REPO
THEMES = [
    ("contact", "ET contact and disclosure", r"\b(?:contact|disclosure|extraterrestrial|alien|ufo|uap|hybrid|gr[ae]ys?|sassani|anunnaki)\b"),
    ("excitement", "Excitement and life direction", r"\b(?:excite\w*|passion\w*|purpose|career|calling|abundance|money|wealth)\b"),
    ("belief", "Beliefs, emotions and relationships", r"\b(?:belie\w*|fear\w*|emotion\w*|relation\w*|trauma\w*|anx\w*|worth\w*|love|family)\b"),
    ("consciousness", "Consciousness and parallel realities", r"\b(?:conscious\w*|parallel|realit\w*|dimension\w*|oversoul|soul\w*|dream\w*|spirit\w*|reincarn\w*|karma)\b"),
    ("practice", "Channeling and spiritual practices", r"\b(?:channel\w*|meditat\w*|permission slips?|synchronic\w*|telepath\w*|intuition)\b"),
    ("physical", "Body, health and physical claims", r"\b(?:health\w*|heal\w*|disease\w*|diet\w*|brain\w*|physics|quantum|frequency|frequencies|vibrat\w*|energy|energies)\b"),
    ("prediction", "Time windows and predictions", r"\b(?:predict\w*|future\w*|probab\w*|timeline\w*|timeframe\w*|202[0-9]|203[0-9]|2040)\b"),
    ("society", "History, society and institutions", r"\b(?:histor\w*|ancient|atlant\w*|government\w*|politic\w*|religion\w*|society|humanity|civilization\w*)\b"),
]
MODALITY = [
    ("conditional", r"\b(?:if|unless|depend\w*|provided|as long as)\b"),
    ("possibility", r"\b(?:may|might|could|possibly|perhaps|potential\w*)\b"),
    ("probability", r"\b(?:likely|unlikely|probab\w*|chance\w*)\b|\b\d+\s*%"),
    ("absolute", r"\b(?:always|never|everyone|everything|nothing|all|must|guarantee\w*)\b"),
    ("imperative", r"^(?:follow|act|choose|trust|use|find|remember|let|focus|be|don't|do not)\b"),
]

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write_json(p, obj):
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
def classify(text, rules):
    return [r[0] for r in rules if re.search(r[-1], text, re.I)]
def normalize(text): return " ".join(re.findall(r"[a-z0-9]+", text.casefold()))
def safe_cell(value):
    """Keep released CSV cells literal even for Excel-style formula prefixes."""
    if value is None: s = ""
    elif isinstance(value, (list, dict, bool)): s = json.dumps(value, ensure_ascii=False)
    else: s = str(value)
    return "'" + s if s and s[:1] in "=+-@" else s

def build(output=HERE):
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    output.mkdir(parents=True, exist_ok=True)
    atlas_path = ATLAS / "dist/analysis/data.json"
    discovery_path = ATLAS / "dist/data.json"
    atlas = json.loads(atlas_path.read_text())
    discovery = json.loads(discovery_path.read_text())["discovery"]
    videos = {v["id"]: v for v in atlas["videos"]}
    channels = {c["id"]: c for c in atlas["channels"]}
    rows, source_rows = [], []
    formats, publishers = collections.defaultdict(list), collections.defaultdict(list)
    for path in sorted((REPO / "data/digests").glob("*.json")):
        data = json.loads(path.read_text())
        vid = data["video_id"]
        v = videos.get(vid)
        if v is None:
            raise ValueError(f"Digest {path.name} has no Atlas video identity")
        source_url = data.get("url") or v["url"]
        source_path = str(path.relative_to(REPO))
        source_hash = digest(path)
        source_rows.append({"videoId": vid, "sourcePath": source_path, "sourceSha256": source_hash,
                            "sourceUrl": source_url, "digestSourceUrl": data.get("digest_source"),
                            "digestGenerated": data.get("digest_generated"), "format": data.get("format"),
                            "researcherNote": data.get("researcher_note"),
                            "qaCount": len(data.get("qa_topics", []))})
        for index, pair in enumerate(data.get("qa_topics", [])):
            q, a = pair["question"].strip(), pair["answer_gist"].strip()
            if not q or not a:
                raise ValueError(f"Empty candidate in {path.name} at {index}")
            row = {"id": f"qa-{vid}-{index:03d}", "videoId": vid,
                   "sourceUrl": source_url, "sourcePath": source_path,
                   "sourceSha256": source_hash, "sourcePointer": f"/qa_topics/{index}",
                   "digestSourceUrl": data.get("digest_source"), "question": q, "answerGist": a,
                   "practitionerNames": v.get("people", []),
                   "contextEntityLabels": v.get("entities", []),
                   "publisherId": v.get("channelId"),
                   "publisherName": channels.get(v.get("channelId"), {}).get("name") or v.get("observedPublisher") or data.get("author"),
                   "format": data.get("format"), "evidenceType": "ai_digest_paraphrase",
                   "speakerVerified": False, "timestampSeconds": None,
                   "entityIsSpeaker": None, "originalSessionId": None,
                   "questionThemes": classify(q, THEMES), "answerThemes": classify(a, THEMES),
                   "answerModalityMarkers": classify(a, MODALITY),
                   "medicalOrPhysicalClaimVerified": False,
                   "attributionBasis": "Inherited Atlas practitioner/entity context; not turn-level attribution",
                   "humanReviewed": False}
            rows.append(row)
            formats[row["format"]].append(row)
            group_key = row["publisherId"] or "unresolved-name-" + hashlib.sha256(row["publisherName"].encode()).hexdigest()[:12]
            row["publisherGroupKey"] = group_key
            publishers[group_key].append(row)

    qvector = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2),
                              sublinear_tf=True, min_df=1, norm="l2")
    qmatrix = qvector.fit_transform([r["question"] for r in rows])
    avector = TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2),
                              sublinear_tf=True, min_df=1, norm="l2")
    amatrix = avector.fit_transform([r["answerGist"] for r in rows])
    qsim = cosine_similarity(qmatrix)
    asim = cosine_similarity(amatrix)
    similarities = []
    for i in range(len(rows)):
        for j in range(i + 1, len(rows)):
            left, right = rows[i], rows[j]
            if left["videoId"] == right["videoId"] or qsim[i, j] < .4:
                continue
            similarities.append({"leftId": left["id"], "rightId": right["id"],
                                 "leftQuestion": left["question"], "rightQuestion": right["question"],
                                 "leftVideoId": left["videoId"], "rightVideoId": right["videoId"],
                                 "questionCosine": round(float(qsim[i, j]), 6),
                                 "answerCosine": round(float(asim[i, j]), 6),
                                 "sameNormalizedQuestion": normalize(left["question"]) == normalize(right["question"]),
                                 "samePublisher": left["publisherId"] == right["publisherId"] if left["publisherId"] is not None and right["publisherId"] is not None else None,
                                 "comparisonScope": "within Darryl Anka/Bashar context across uploads",
                                 "originalSessionIndependence": "unknown",
                                 "answerAgreement": "not_assessed",
                                 "potentialSharedSource": "same normalized question; check original session reuse" if normalize(left["question"]) == normalize(right["question"]) else "not_assessed"})
    similarities.sort(key=lambda p: (-p["questionCosine"], p["leftId"], p["rightId"]))
    terms = qvector.get_feature_names_out()
    key_scores = np.asarray(qmatrix.sum(axis=0)).ravel()
    keywords = [{"term": str(terms[i]), "tfidfSum": round(float(key_scores[i]), 6),
                 "questionDocumentFrequency": int((qmatrix[:, i] > 0).sum())}
                for i in sorted(range(len(terms)), key=lambda i: (-key_scores[i], terms[i]))[:100]]
    exact = collections.defaultdict(list)
    for row in rows: exact[normalize(row["question"])].append(row)
    repeated = [{"normalizedQuestion": k, "question": vv[0]["question"],
                 "candidateIds": [r["id"] for r in vv], "uploadCount": len({r["videoId"] for r in vv}),
                 "qaCount": len(vv)} for k, vv in exact.items() if len(vv) > 1]
    repeated.sort(key=lambda x: (-x["uploadCount"], x["normalizedQuestion"]))
    practitioner_counts = collections.Counter(p for row in rows for p in row["practitionerNames"])
    normalized_qa = {(normalize(r["question"]), normalize(r["answerGist"])) for r in rows}
    pair_counts = collections.Counter(tuple(sorted((p["leftVideoId"],p["rightVideoId"]))) for p in similarities)
    sensitivity = {"identicalNormalizedQADeduplication": {"retainedCandidates": len(normalized_qa), "removedCandidates": len(rows)-len(normalized_qa),
                    "interpretation": "Different gists of the same source may survive; this is not original-session deduplication."},
                   "identicalNormalizedQuestionDeduplication": {"retainedQuestions": len(exact), "removedCandidates": len(rows)-len(exact),
                    "interpretation": "Dropping repeated question wording does not establish independent sessions."},
                   "similarQuestionPairsExcludingIdenticalQuestionWording": {"retainedPairs": sum(not p["sameNormalizedQuestion"] for p in similarities),
                    "removedPairs": sum(p["sameNormalizedQuestion"] for p in similarities), "threshold": .4},
                   "uploadPairsWithMultipleSimilarQuestions": [{"leftVideoId": k[0],"rightVideoId":k[1],"similarQuestionPairs":n,
                    "interpretation":"Possible shared source or recurrent topic; original-session identity unresolved"}
                    for k,n in sorted(pair_counts.items(), key=lambda x:(-x[1],x[0])) if n>1]}
    sensitivity["retrievalThresholds"] = [{"minimumQuestionCosine": threshold,
                                           "candidatePairs": sum(p["questionCosine"] >= threshold for p in similarities),
                                           "distinctUploadPairs": len({tuple(sorted((p["leftVideoId"],p["rightVideoId"]))) for p in similarities if p["questionCosine"] >= threshold})}
                                          for threshold in [.4,.5,.6,.7,.8,.9]]
    sensitivity["retrievalThresholdScope"] = "Recounts the retained >=0.40 lexical candidates; thresholds are exploratory retrieval choices, not validated question-equivalence cutoffs."
    sorted_upload_pairs = sorted(pair_counts.items(),key=lambda x:(-x[1],x[0]))
    top_three = sorted_upload_pairs[:3]
    sensitivity["uploadPairConcentration"] = {"distinctUploadPairs": len(pair_counts), "totalQuestionPairs": len(similarities),
        "topThreeUploadPairs": [{"leftVideoId": k[0],"rightVideoId": k[1],"candidatePairs":n} for k,n in top_three],
        "topThreeUploadPairCandidateMatches":sum(n for k,n in top_three),
        "topThreeUploadPairShare":round(sum(n for k,n in top_three)/len(similarities),6) if similarities else None,
        "interpretation":"Concentration of retrieval matches; neither an independent-session count nor a measured repost rate."}
    frame_path = HERE.parent / "acquisition/practitioner-frame.json"
    people = json.loads(frame_path.read_text())["people"] if frame_path.exists() else discovery["people"]
    practitioner_coverage = [{"id": p["id"], "name": p["name"],
                              "contextEntityLabels": p.get("entities", []),
                              "accountUrls": p.get("accountUrls", []),
                              "sourceRecordIds": p.get("recordIds", []),
                              "sourceUrls": p.get("sourceUrls", []),
                              "identityStatus": "inherited_candidate_not_revalidated",
                              "qaCandidateCount": practitioner_counts.get(p["name"], 0),
                              "qaAvailability": "digest_paraphrases_only" if practitioner_counts.get(p["name"], 0) else "no_usable_qa_text_in_this_release",
                              "transcriptTurnCount": 0,
                              "humanReviewedCount": 0,
                              "attributionJoin": "exact inherited practitioner name; no entity or uploader inference"}
                             for p in people]
    review_path = HERE / "close-reading.json"
    review = json.loads(review_path.read_text()) if review_path.exists() else {"status": "pending", "records": []}
    pair_review_path = HERE / "pair-close-reading.json"
    pair_review = json.loads(pair_review_path.read_text()) if pair_review_path.exists() else {"status": "pending", "records": []}
    limitations = [
        "All candidate pairs are inherited AI-generated digest paraphrases, not transcript quotations or observed speaker turns.",
        "All 949 current candidates share Darryl Anka/Bashar practitioner context. Cross-practitioner question or answer comparisons are unavailable.",
        "Publishing accounts are distribution routes; comparing them is not comparing different mediums or attributed entities.",
        "Bashar is a contextual entity label. Interview answers may be Darryl Anka's speech; no turn-level entity attribution has been verified.",
        "Question wording, answer gist, inclusions and omissions were selected by the earlier digest generator. Counts describe digest entries, not every question asked.",
        "Different uploads may repeat an original session. Near-question pairs are retrieval suggestions, not independent repetitions or agreement evidence.",
        "TF-IDF question/answer cosine measures shared lexical features. It does not establish semantic equivalence, contradiction, influence, or answer agreement.",
        "Regex themes overlap and are unvalidated descriptive indicators. Absent markers do not establish absent themes or certainty.",
        "No timestamps, audio/video listening, caption-error audit or human labels were produced by this extraction.",
        "The model-assisted close-reading subset inspects existing digest pairs only; it is not independent transcript or human construct validation."
    ]
    meta = {"schemaVersion": "1.0", "kind": "candidate_qa_retrieval", "source": "committed AI-generated Bashar digests",
            "sourceSnapshotSha256": digest(atlas_path), "unit": "one inherited digest question/answer-gist pair",
            "selection": "all qa_topics entries from all committed data/digests/*.json, sorted by filename and original index",
            "reconstruction": "python research/expansion/qa/build_qa.py",
            "method": {"themes": "case-insensitive regex, overlapping categories; question and answer separately",
                       "commonQuestions": "all distinct-upload pairs with word unigram/bigram sublinear TF-IDF cosine >= 0.40; English stop words; no inference of independent sessions",
                       "answerComparison": "independent answer-gist TF-IDF cosine for retrieval context only; agreement not assessed",
                       "keywordExtraction": "100 highest summed normalized word unigram/bigram TF-IDF features across candidate questions",
                       "uncertainty": "lexical possibility/conditional/probability/absolute/imperative markers; no validated epistemic scale",
                       "tfidfParameters": {"fitSeparately":"questions and answer gists", "analyzer":"word", "ngram_range":[1,2],
                            "lowercase":True, "stop_words":"english", "sublinear_tf":True, "min_df":1, "max_df":1.0,
                            "use_idf":True, "smooth_idf":True, "norm":"l2", "strip_accents":None,
                            "token_pattern":r"(?u)\b\w\w+\b", "max_features":None}}}
    summary = {"meta": meta,
               "coverage": {"digestVideos": len(source_rows), "videosWithQACandidates": len({r["videoId"] for r in rows}), "qaCandidates": len(rows),
                            "practitionersWithQA": len(practitioner_counts),
                            "publishingAccountsWithQA": len({r["publisherId"] for r in rows if r["publisherId"] is not None}),
                            "publisherGroupsIncludingUnresolvedNames": len(publishers),
                            "unresolvedPublisherNameGroups": len({r["publisherName"] for r in rows if r["publisherId"] is None}),
                            "candidatesWithoutResolvedPublisherId": sum(r["publisherId"] is None for r in rows),
                            "atlasPractitionerRecords": len(discovery["people"]),
                            "crossPractitionerComparisonAvailable": len(practitioner_counts) > 1,
                            "practitionerCandidates": dict(practitioner_counts),
                            "literalTranscriptTurns": 0, "speakerVerifiedCandidates": 0,
                            "modelCloseReadCandidates": len(review.get("records", [])),
                            "humanReviewedCandidates": 0, "questionSimilarityPairsAt040": len(similarities),
                            "distinctNormalizedQuestions": len(exact), "repeatedNormalizedQuestions": len(repeated)},
               "themes": [{"id": tid, "label": label,
                           "questionCount": sum(tid in r["questionThemes"] for r in rows),
                           "answerCount": sum(tid in r["answerThemes"] for r in rows),
                           "eitherCount": sum(tid in r["questionThemes"] or tid in r["answerThemes"] for r in rows)}
                          for tid, label, regex in THEMES],
               "formats": [{"format": key, "videos": len({r["videoId"] for r in rr}), "qaCandidates": len(rr)}
                           for key, rr in sorted(formats.items())],
               "publishers": [{"id": rr[0]["publisherId"], "groupKey": key, "name": rr[0]["publisherName"],
                               "identityStatus": "inherited_account_id" if rr[0]["publisherId"] else "unresolved_publisher_name_only",
                               "videoCount": len({r["videoId"] for r in rr}), "qaCandidates": len(rr)}
                              for key, rr in sorted(publishers.items(), key=lambda kv: (-len(kv[1]), str(kv[0])))],
               "questionPairs": similarities[:100], "repeatedQuestions": repeated,
               "questionPairsPreview": {"shown":len(similarities[:100]),"total":len(similarities),
                                         "truncated":len(similarities)>100,"fullArtifact":"question-pairs.json"},
               "practitionerCoverage": practitioner_coverage,
               "sensitivity": sensitivity,
               "keywords": keywords, "review": {k: v for k, v in review.items() if k != "records"},
               "pairReview": {**{k: v for k, v in pair_review.items() if k != "records"}, "pairCount": len(pair_review.get("records", []))},
               "limitations": limitations}
    write_json(output / "qa-candidates.json", {"meta": meta, "records": rows})
    write_json(output / "source-manifest.json", {"atlasSha256": digest(atlas_path), "records": source_rows})
    write_json(output / "summary.json", summary)
    write_json(output / "question-pairs.json", {"meta": meta, "threshold": .4, "records": similarities})
    write_json(output / "practitioner-coverage.json", {"joinRule": "exact inherited practitioner name; no entity or uploader inference", "records": practitioner_coverage})
    write_json(output / "codebook.json", {"themes": [{"id": x[0], "label": x[1], "regex": x[2]} for x in THEMES],
                                         "modality": [{"id": x[0], "regex": x[1]} for x in MODALITY],
                                         "validation": "Unvalidated, overlapping descriptive indicators; no human agreement or criterion validity claim"})
    with (output / "qa-candidates.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]));writer.writeheader()
        writer.writerows({k: safe_cell(v) for k, v in row.items()} for row in rows)
    dbpath = output / "qa-candidates.sqlite"
    if dbpath.exists(): dbpath.unlink()
    db = sqlite3.connect(dbpath)
    db.executescript("""
        PRAGMA foreign_keys=ON;
        CREATE TABLE sources (video_id TEXT PRIMARY KEY, source_path TEXT NOT NULL, sha256 TEXT NOT NULL,
                              source_url TEXT NOT NULL, digest_source_url TEXT, format TEXT);
        CREATE TABLE qa_candidates (id TEXT PRIMARY KEY, video_id TEXT NOT NULL REFERENCES sources(video_id),
            source_pointer TEXT NOT NULL, question TEXT NOT NULL, answer_gist TEXT NOT NULL,
            practitioner_names TEXT NOT NULL, context_entity_labels TEXT NOT NULL, publisher_id TEXT,
            publisher_name TEXT, evidence_type TEXT NOT NULL, speaker_verified INTEGER NOT NULL CHECK(speaker_verified=0),
            timestamp_seconds REAL CHECK(timestamp_seconds IS NULL), entity_is_speaker INTEGER CHECK(entity_is_speaker IS NULL),
            human_reviewed INTEGER NOT NULL CHECK(human_reviewed=0));
        CREATE TABLE keyword_annotations (candidate_id TEXT REFERENCES qa_candidates(id), layer TEXT,
            category TEXT, PRIMARY KEY(candidate_id, layer, category));
        CREATE TABLE question_pairs (left_id TEXT REFERENCES qa_candidates(id), right_id TEXT REFERENCES qa_candidates(id),
            question_cosine REAL CHECK(question_cosine>=0 AND question_cosine<=1.000001), answer_cosine REAL,
            same_publisher INTEGER, session_independence TEXT, answer_agreement TEXT, PRIMARY KEY(left_id,right_id));
        CREATE TABLE model_close_reading (candidate_id TEXT PRIMARY KEY REFERENCES qa_candidates(id),
            interpretation TEXT, caution TEXT, role TEXT);
        CREATE TABLE model_pair_reading (left_id TEXT REFERENCES qa_candidates(id), right_id TEXT REFERENCES qa_candidates(id),
            reading TEXT, interpretation TEXT, caution TEXT, answer_agreement TEXT CHECK(answer_agreement='undetermined'),
            PRIMARY KEY(left_id,right_id));
        CREATE TABLE practitioner_coverage (id TEXT PRIMARY KEY, name TEXT NOT NULL, entity_labels TEXT,
            account_urls TEXT, source_record_ids TEXT, source_urls TEXT, identity_status TEXT,
            qa_candidate_count INTEGER NOT NULL, qa_availability TEXT, transcript_turn_count INTEGER NOT NULL CHECK(transcript_turn_count=0));
        CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE INDEX video_idx ON qa_candidates(video_id);
        CREATE INDEX publisher_idx ON qa_candidates(publisher_id);
    """)
    db.executemany("INSERT INTO sources VALUES(?,?,?,?,?,?)", [(s["videoId"], s["sourcePath"], s["sourceSha256"], s["sourceUrl"], s["digestSourceUrl"], s["format"]) for s in source_rows])
    db.executemany("INSERT INTO qa_candidates VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   [(r["id"], r["videoId"], r["sourcePointer"], r["question"], r["answerGist"],
                     json.dumps(r["practitionerNames"]), json.dumps(r["contextEntityLabels"]), r["publisherId"],
                     r["publisherName"], r["evidenceType"], 0, None, None, 0) for r in rows])
    db.executemany("INSERT INTO keyword_annotations VALUES(?,?,?)", [(r["id"], layer, cat)
                   for r in rows for layer, key in [("question_theme", "questionThemes"), ("answer_theme", "answerThemes"), ("answer_modality", "answerModalityMarkers")] for cat in r[key]])
    db.executemany("INSERT INTO question_pairs VALUES(?,?,?,?,?,?,?)", [(p["leftId"], p["rightId"], p["questionCosine"], p["answerCosine"], int(p["samePublisher"]) if p["samePublisher"] is not None else None, "unknown", "not_assessed") for p in similarities])
    db.executemany("INSERT INTO model_close_reading VALUES(?,?,?,?)", [(r["candidateId"], r["interpretation"], r["caution"], "AI close reading of digest only") for r in review.get("records", [])])
    db.executemany("INSERT INTO model_pair_reading VALUES(?,?,?,?,?,?)", [(r["leftId"], r["rightId"],r["reading"],r["interpretation"],r["caution"],"undetermined") for r in pair_review.get("records", [])])
    db.executemany("INSERT INTO practitioner_coverage VALUES(?,?,?,?,?,?,?,?,?,?)",
                   [(p["id"],p["name"],json.dumps(p["contextEntityLabels"]),json.dumps(p["accountUrls"]),
                     json.dumps(p["sourceRecordIds"]),json.dumps(p["sourceUrls"]),p["identityStatus"],p["qaCandidateCount"],p["qaAvailability"],0)
                    for p in practitioner_coverage])
    db.execute("INSERT INTO metadata VALUES(?,?)", ("description", json.dumps(meta)))
    db.commit()
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    db.close()
    print(json.dumps(summary["coverage"], ensure_ascii=False))
    return summary

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__);p.add_argument("--output", type=pathlib.Path, default=HERE)
    build(p.parse_args().output)
