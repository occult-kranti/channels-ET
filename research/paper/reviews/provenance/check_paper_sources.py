#!/usr/bin/env python3
"""Independent source/denominator checks for a frozen paper round.

Uses retained observation rows and standard-library arithmetic; does not import
the producer pipeline or treat the paper's reported coverage as its own oracle.
No third-party caption text is read or emitted.
"""
from pathlib import Path
from collections import Counter, defaultdict
from statistics import mean, median
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[4]
ROUND = int(sys.argv[1])
FROZEN = ROOT / f"research/paper/rounds/round{ROUND}"
OUT = Path(__file__).parent / f"round{ROUND}-source-checks.json"

def read(path):
    return json.loads(path.read_text())

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

source_path = ROOT / "dist/analysis/data.json"
metadata_path = ROOT / "research/analysis/inputs/fresh_metadata.json"
data = read(source_path)
raw = read(metadata_path)
paper = read(FROZEN / "generated/paper-results.json")
videos = data["videos"]
captions = data["transcripts"]["rows"]
by_channel = defaultdict(list)
for v in videos:
    if v.get("channelId"):
        by_channel[v["channelId"]].append(v)
caption_counts = Counter(r["channelId"] for r in captions)
caption_ids = {r["videoId"] for r in captions}
matched = [v for v in videos if v["id"] in caption_ids
           and v.get("channelId") and v.get("titleEligible")]
matched_counts = Counter(v["channelId"] for v in matched)
matched_groups = {k for k, n in matched_counts.items() if n >= 2}
fresh_duration = sum(v.get("durationSeconds", 0) is not None
                     and v.get("durationSeconds", 0) > 0
                     and v.get("durationSource") == "fresh_watch_metadata"
                     for v in videos)
duration_n = sum(v.get("durationSeconds") is not None and v["durationSeconds"] > 0
                 for v in videos)
observed = {
    "indexedVideos": len({v["id"] for v in videos}),
    "watchMetadataSuccesses": sum(r["status"] == "success" for r in raw),
    "durationKnown": duration_n,
    "durationFresh": fresh_duration,
    "durationInherited": duration_n - fresh_duration,
    "dateKnown": sum(bool(v.get("date")) for v in videos),
    "attributedVideos": sum(bool(v.get("channelId")) for v in videos),
    "routeGroups": len(data["channels"]),
    "groupsWithVideos": len(by_channel),
    "groupsWithDurations": sum(any(v.get("durationSeconds") for v in rows)
                               for rows in by_channel.values()),
    "englishLikelyTitles": sum(bool(v.get("titleEligible")) for v in videos),
    "embeddedTitles": sum(bool(v.get("titleEligible") and v.get("channelId"))
                          for v in videos),
    "captionPilot": len(captions),
    "captionPublishers": len(caption_counts),
    "captionComparisonPublishers": sum(n >= 2 for n in caption_counts.values()),
    "captionComparisonDocuments": sum(n for n in caption_counts.values() if n >= 2),
    "matchedEligibleDocuments": len(matched),
    "matchedContributingDocuments": sum(matched_counts[k] for k in matched_groups),
    "matchedPublishers": len(matched_groups),
    "matchedPairs": len(matched_groups) * (len(matched_groups) - 1) // 2,
}
checks = []
def check(name, actual, expected):
    checks.append({"name": name, "observed": actual, "reported": expected,
                   "pass": actual == expected})

check("source snapshot hash", digest(source_path), paper["source"]["sha256"])
for key, value in observed.items():
    check(key, value, paper["coverage"][key])
for row in paper["focalDurations"]:
    durations = [v["durationSeconds"] / 60 for v in by_channel[row["id"]]
                 if v.get("durationSeconds") is not None and v["durationSeconds"] > 0]
    check("duration n: " + row["id"], len(durations), row["durationCount"])
    check("duration mean: " + row["id"], round(mean(durations), 9), round(row["meanMinutes"], 9))
    check("duration median: " + row["id"], round(median(durations), 9), round(row["medianMinutes"], 9))
pool = paper.get("chunkWeighting")
if pool:
    check("pooling source", pool["sourceSnapshotSha256"], digest(source_path))
    details = pool["documentsDetail"]
    check("pooling document identities", sorted(r["videoId"] for r in details), sorted(caption_ids))
    check("pooling chunks", sum(len(r["chunkSizes"]) for r in details), pool["totalChunks"])
    check("pooling content WordPieces", sum(sum(r["chunkSizes"]) for r in details), pool["totalContentWordpieces"])
    check("pooling neighbors changed", sum(r["changed"] for r in pool["nearestNeighbors"]), pool["nearestNeighborChanges"])

result = {
    "round": ROUND,
    "scope": "Independent arithmetic and provenance checks of frozen paper against retained observation rows; no fresh collection, no caption text, no independent re-execution of model inference.",
    "files": [{"path": str(p.relative_to(ROOT)), "sha256": digest(p)} for p in
              [source_path, metadata_path, FROZEN / "body.tex", FROZEN / "main.pdf",
               FROZEN / "generated/paper-results.json"]],
    "checks": checks,
    "requestStartRangeUtc": [min(r["retrieved_at"] for r in raw), max(r["retrieved_at"] for r in raw)],
    "failedRetrievals": sum(r["status"] != "success" for r in raw),
    "pass": all(c["pass"] for c in checks),
}
OUT.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({"round": ROUND, "pass": result["pass"], "checks": len(checks),
                  "failures": [c for c in checks if not c["pass"]],
                  "output": str(OUT.relative_to(ROOT))}, indent=2))
sys.exit(0 if result["pass"] else 1)
