#!/usr/bin/env python3
"""Revalidate current receipts against an earlier full audio-hash receipt.

This is explicitly NOT a new full byte-hash run. It checks that current
acquisition/ledger receipts, byte sizes and current ffprobe durations still match
the earlier fully hashed media. Use CHANNELS_ET_REVERIFY_AUDIO=1 for a full rerun.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(os.environ["CHANNELS_ET_RAW_ROOT"]) / "youtube-audio"
PUBLIC = Path(__file__).resolve().parents[0]
RECEIPT = PUBLIC / "verification.json"
OUTPUT = PUBLIC / "verification-reuse.json"


def main():
    previous_bytes = RECEIPT.read_bytes()
    previous = json.loads(previous_bytes)
    checks = []
    def check(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": str(detail)[:300]})
    check("earlier full audio verification passed", previous.get("nFailed") == 0,
          f"{previous.get('nPassed')}/{previous.get('nChecks')}")
    ledger = json.loads((PUBLIC / "acquisition-ledger.json").read_text())["records"]
    ledger_by_id = {r.get("video_id", r.get("videoId")): r for r in ledger}
    records = []
    for prior in previous.get("validatedMedia", []):
        vid = prior["videoId"]
        directory = ROOT / vid
        acquisition_path = directory / "acquisition.json"
        audio = directory / "audio.mp3"
        acquisition = json.loads(acquisition_path.read_text()) if acquisition_path.exists() else {}
        ledger_record = ledger_by_id.get(vid, {})
        check(f"current receipts match earlier full hash:{vid}",
              acquisition_path.exists() and audio.exists() and
              acquisition.get("sha256") == prior["sha256"] and
              ledger_record.get("sha256", ledger_record.get("audioSha256")) == prior["sha256"] and
              acquisition.get("bytes") == prior["bytes"] == audio.stat().st_size,
              f"bytes={prior['bytes']}")
        probe = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(audio)], text=True, timeout=60))
        duration = float(probe["format"]["duration"])
        check(f"current ffprobe duration matches earlier full receipt:{vid}",
              abs(duration - prior["durationSeconds"]) <= 0.01 and
              abs(duration - float(acquisition.get("duration_seconds", duration))) <= 0.5,
              f"duration={duration:.3f}")
        records.append({"videoId": vid, "bytes": prior["bytes"],
                        "earlierFullAudioSha256": prior["sha256"],
                        "currentFfprobeDurationSeconds": duration})
    check("all earlier fully hashed media are covered by current consistency checks",
          len(records) == len(previous.get("validatedMedia", [])) == 35,
          f"records={len(records)}")
    excluded = [r for r in ledger if r.get("status") == "excluded_under_300"]
    check("seven under-300 exclusions remain explicit with quarantine bytes",
          len(excluded) == 7 and all(r.get("admittedMediaBytes") == 0 and
                                     r.get("quarantinedBytes", 0) > 0 and
                                     r.get("quarantinedAudioSha256") for r in excluded),
          f"excluded={len(excluded)}")
    output = {
        "schemaVersion": 1,
        "fullHashRerun": False,
        "reuseBasis": "Earlier full byte/hash verification plus current acquisition/ledger receipts, byte sizes and ffprobe durations",
        "previousFullVerificationSha256": hashlib.sha256(previous_bytes).hexdigest(),
        "reuseValidatedUtc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "nChecks": len(checks), "nPassed": sum(c["ok"] for c in checks),
        "nFailed": sum(not c["ok"] for c in checks), "checks": checks,
        "validatedMedia": records,
        "totals": {"files": len(records), "bytes": sum(r["bytes"] for r in records),
                   "durationSeconds": sum(r["currentFfprobeDurationSeconds"] for r in records)},
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(f"{output['nPassed']}/{output['nChecks']} consistency checks passed; fullHashRerun=false")
    return 1 if output["nFailed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
