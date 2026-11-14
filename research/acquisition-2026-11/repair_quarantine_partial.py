#!/usr/bin/env python3
"""Repair a quarantine partial from its exact final segment stream, without ASR.

This is a provenance-preserving derivative, not a new transcription. The final
segment JSONL is the completed form of the partial stream. Existing receipt code
hashes remain the production hashes; the repair has its own script hash.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import transcribe_youtube as pipeline

ROOT = pipeline.ROOT
SCRIPT = Path(__file__).resolve()
SCRIPT_SHA256 = hashlib.sha256(SCRIPT.read_bytes()).hexdigest()


def main():
    video_id = os.environ.get('CHANNELS_ET_QUARANTINE_VIDEO', '-KVKPRLFte4')
    directory = ROOT / video_id
    quarantine = directory / 'quarantine'
    receipt_path = directory / 'asr-receipt.json'
    receipt = json.loads(receipt_path.read_text())
    segments = quarantine / 'asr-segments.jsonl'
    source_hash = pipeline.sha256(segments)
    if receipt['outputSha256']['asr-segments.jsonl'] != source_hash:
        raise RuntimeError('Current final segments differ from the production receipt')
    partial = quarantine / 'asr-segments.partial.jsonl'
    partial.write_bytes(segments.read_bytes())
    partial_hash = pipeline.sha256(partial)
    receipt['outputSha256']['asr-segments.partial.jsonl'] = partial_hash
    receipt['partialProvenance'] = {
        'method': 'exact_copy_of_current_final_segments',
        'sourceSegmentsSha256': source_hash,
        'partialSha256': partial_hash,
        'repairScriptSha256': SCRIPT_SHA256,
        'repairedUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'noRetranscription': True,
        'humanValidated': False,
    }
    legacy = quarantine / 'legacy-exclusion-receipt.unverified.json'
    if legacy.exists():
        receipt['legacyReceiptPath'] = 'quarantine/legacy-exclusion-receipt.unverified.json'
        receipt['legacyReceiptSha256'] = pipeline.sha256(legacy)
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    pipeline.merge_summary([receipt])
    print(json.dumps({'videoId': video_id, 'partialSha256': partial_hash,
                      'sourceSegmentsSha256': source_hash,
                      'repairScriptSha256': SCRIPT_SHA256,
                      'noRetranscription': True}, indent=2))


if __name__ == '__main__':
    main()
