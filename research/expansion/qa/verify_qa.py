#!/usr/bin/env python3
"""Independent source-to-candidate and database-integrity checks."""
from __future__ import annotations
import collections, csv, hashlib, json, pathlib, sqlite3, tempfile
from ingest_captions import extract, run

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parents[2]
def main():
    rows = json.loads((HERE / "qa-candidates.json").read_text())["records"]
    summary = json.loads((HERE / "summary.json").read_text())
    lookup = {r["id"]: r for r in rows}
    checks = 0
    def check(ok, msg):
        nonlocal checks
        checks += 1
        if not ok: raise AssertionError(msg)
    expected = sum(len(json.loads(p.read_text()).get("qa_topics", [])) for p in (REPO / "data/digests").glob("*.json"))
    check(len(rows) == expected, "Every original qa_topics entry must survive once")
    check(len(rows) == len(lookup), "Unique candidate primary keys")
    for r in rows:
        path = REPO / r["sourcePath"]
        source = json.loads(path.read_text())
        qindex = int(r["sourcePointer"].split("/")[-1])
        q = source["qa_topics"][qindex]
        check(hashlib.sha256(path.read_bytes()).hexdigest() == r["sourceSha256"], r["id"] + " source hash")
        check(r["question"] == q["question"].strip() and r["answerGist"] == q["answer_gist"].strip(), r["id"] + " exact digest pointer")
        check(r["videoId"] == source["video_id"] and r["videoId"] in r["sourceUrl"], r["id"] + " video/url identity")
        check(r["timestampSeconds"] is None and not r["speakerVerified"] and r["entityIsSpeaker"] is None, "No inferred speaker/timestamp")
    db = sqlite3.connect(HERE / "qa-candidates.sqlite")
    check(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity")
    check(not db.execute("PRAGMA foreign_key_check").fetchall(), "SQLite foreign keys")
    check(db.execute("SELECT count(*) FROM qa_candidates").fetchone()[0] == len(rows), "SQLite matches JSON candidates")
    check(db.execute("SELECT count(*) FROM practitioner_coverage").fetchone()[0] == len(summary["practitionerCoverage"]), "All practitioner candidates retained")
    check(sum(p["qaCandidateCount"] for p in summary["practitionerCoverage"]) == len(rows), "Practitioner exact-name joins reconcile")
    check(summary["coverage"]["crossPractitionerComparisonAvailable"] is False, "Single-practitioner candidate frame")
    check(len([r for r in rows if r["publisherId"] is None]) == summary["coverage"]["candidatesWithoutResolvedPublisherId"], "Unknown publisher records retained")
    pairs=json.loads((HERE / "question-pairs.json").read_text())["records"]
    for pair in pairs:
        left,right=lookup[pair["leftId"]],lookup[pair["rightId"]]
        check(left["videoId"] != right["videoId"] and pair["questionCosine"] >= .4, "Distinct-upload candidate threshold")
        check(pair["answerAgreement"] == "not_assessed" and pair["originalSessionIndependence"] == "unknown", "No agreement/independence inference")
        if left["publisherId"] is None or right["publisherId"] is None:
            check(pair["samePublisher"] is None, "Unknown publishers cannot become matched accounts")
    for point in summary["sensitivity"]["retrievalThresholds"]:
        selected=[p for p in pairs if p["questionCosine"]>=point["minimumQuestionCosine"]]
        check(point["candidatePairs"]==len(selected),"Threshold candidate count")
        check(point["distinctUploadPairs"]==len({tuple(sorted((p["leftVideoId"],p["rightVideoId"]))) for p in selected}),"Threshold upload-pair count")
    concentration=summary["sensitivity"]["uploadPairConcentration"]
    grouped=collections.Counter(tuple(sorted((p["leftVideoId"],p["rightVideoId"]))) for p in pairs)
    check(concentration["distinctUploadPairs"]==len(grouped),"Distinct upload-pair concentration denominator")
    check(concentration["topThreeUploadPairCandidateMatches"]==sum(sorted(grouped.values(),reverse=True)[:3]),"Top-three match concentration numerator")
    check(abs(concentration["topThreeUploadPairShare"]-sum(sorted(grouped.values(),reverse=True)[:3])/len(pairs))<.000001,"Top-three match concentration share")
    preview=summary["questionPairsPreview"]
    check(preview["shown"]==len(summary["questionPairs"]) and preview["total"]==len(pairs) and preview["truncated"]==(len(pairs)>len(summary["questionPairs"])),"Preview disclosure matches full export")
    with (HERE/"qa-candidates.csv").open(newline="") as f:csvrows=list(csv.DictReader(f))
    check(len(csvrows)==len(rows),"CSV candidate row count")
    check(all(r["speakerVerified"]=="false" and r["humanReviewed"]=="false" for r in csvrows),"CSV preserves false booleans rather than blank missing values")
    check(all(r["timestampSeconds"]=="" and r["entityIsSpeaker"]=="" for r in csvrows),"CSV empty values remain unknown")
    review=json.loads((HERE/"close-reading.json").read_text())
    check(len(review["records"])==20 and len({r["candidateId"] for r in review["records"]})==20,"Twenty distinct model-read candidates")
    check(all(r["candidateId"] in lookup for r in review["records"]),"Close-reading rows resolve")
    pair_review=json.loads((HERE/"pair-close-reading.json").read_text())
    check(len(pair_review["records"])==12,"Twelve exploratory paired readings")
    for pair in pair_review["records"]:
        for side in ["left","right"]:
            r=lookup[pair[side+"Id"]]
            check(pair[side+"Source"]=={k:r[k] for k in ["sourceUrl","sourcePath","sourceSha256","sourcePointer"]},"Paired reading source binding")
        check(pair["classification"]["answerAgreement"]=="undetermined" and not pair["classification"]["humanValidated"],"No semantic agreement ground truth")
    check(db.execute("SELECT count(*) FROM model_pair_reading").fetchone()[0]==12,"Paired readings retained in SQLite")
    # Synthetic fixture exercises punctuation segmentation, bounds and release separation.
    synthetic={"video_id":"SYNTHETIC01","segments":[{"text":"What might happen?","start":1,"duration":2},
       {"text":"A possible answer window.","start":4,"duration":3},
       {"text":"Second question?","start":8,"duration":2},
       {"text":"Next answer.","start":11,"duration":2}]}
    extracted=extract(synthetic)
    check(len(extracted)==2 and extracted[0]["answer_end_seconds"]==7,"Caption candidate windows stop at next question")
    for bad in [{**synthetic,"video_id":"bad"},
                {**synthetic,"segments":[{"text":"Q?","start":float('nan'),"duration":2}]},
                {**synthetic,"segments":[{"text":"Q?","start":2,"duration":-1}]},
                {**synthetic,"segments":[{"text":"Q?","start":2,"duration":1},{"text":"A","start":1,"duration":1}]},
                {**synthetic,"is_generated":"yes"}]:
        try:extract(bad)
        except ValueError:check(True,"Malformed caption metadata/timing rejected")
        else:check(False,"Malformed caption document accepted")
    bound={"video_id":"SYNTHETIC01","segments":[{"text":"Q?","start":0,"duration":1},
           {"text":"A.","start":2,"duration":2},{"text":"Too long.","start":119,"duration":2}]}
    check(extract(bound)[0]["answer_end_seconds"]==4,"Whole segment crossing 120-second end cap excluded")
    overlap={"video_id":"SYNTHETIC01","segments":[{"text":"Q?","start":0,"duration":1},
             {"text":"A.","start":2,"duration":10},{"text":"Overlap.","start":3,"duration":1}]}
    check(extract(overlap)[0]["answer_end_seconds"]==12 and extract(overlap)[0]["question_end_seconds"]==1,"Caption windows retain maximum overlapping segment end and question end")
    with tempfile.TemporaryDirectory(prefix="qa-fixture-") as td:
        temp=pathlib.Path(td); inp=temp/"synthetic.json";inp.write_text(json.dumps(synthetic))
        pub=run(inp,temp/"raw.json",temp/"manifest.json")
        check("question_candidate" not in pub[0] and "answer_window_candidate" not in pub[0],"Public caption manifest excludes source text")
        check(pub[0]["language_code"] is None and pub[0]["is_generated"] is None and pub[0]["attribution_status"]=="unknown", "Absent caption provenance remains unknown")
        check(pub[0]["evidence_type"]=="punctuation_based_caption_window_candidate" and not pub[0]["speaker_verified"],"Candidate provenance retains unvalidated evidence type")
        try:run(inp,REPO/"forbidden-raw.json",temp/"manifest2.json")
        except ValueError:check(True,"Raw caption output to Git is rejected")
        else:check(False,"Raw caption output leaked into Git")
    receipt={"status":"PASS","checks":checks,"candidateCount":len(rows),"sourceDigests":75,
             "videosWithQACandidates":len({r["videoId"] for r in rows}),
             "sourceHashPointersVerified":len(rows),"sqliteIntegrity":"ok",
             "captionWindowTests":"synthetic fixture only; no real raw captions used",
             "summarySha256":hashlib.sha256((HERE/"summary.json").read_bytes()).hexdigest()}
    (HERE/"verification.json").write_text(json.dumps(receipt,indent=2)+"\n")
    print(json.dumps(receipt,indent=2))
if __name__=="__main__":main()
