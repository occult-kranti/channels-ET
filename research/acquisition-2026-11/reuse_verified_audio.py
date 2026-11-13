#!/usr/bin/env python3
"""Validate current audio receipts against earlier full verification evidence.

Used only when CHANNELS_ET_REVERIFY_AUDIO=0: the committed verification-reuse.json
must prove that every current audio artifact already passed a full hash run. This
script never marks failed or missing evidence as reusable.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    reuse = json.loads((ROOT / "verification-reuse.json").read_text())
    full = json.loads((ROOT / "verification.json").read_text())
    if reuse.get("nFailed") != 0 or reuse.get("fullHashRerun") is not False:
        raise RuntimeError("Reuse receipt does not prove a complete earlier full-hash run")
    if reuse.get("nPassed") != reuse.get("nChecks"):
        raise RuntimeError("Reuse receipt is incomplete")
    if full.get("nFailed") != 0:
        raise RuntimeError("Current audio verification receipt records failures")
    print(f"Reusable audio evidence: {reuse['nPassed']}/{reuse['nChecks']} checks consistent; fullHashRerun=false")


if __name__ == "__main__":
    main()
