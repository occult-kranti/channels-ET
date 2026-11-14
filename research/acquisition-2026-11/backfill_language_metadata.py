#!/usr/bin/env python3
"""Backfill missing language metadata from existing hash-bound ASR text.

No audio is redecoded and no transcript is changed. This is a heuristic metadata
backfill, not human language validation. It preserves existing values and records
its own script hash, then lets the ordinary resume path refresh the summary.
"""
import collections
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
    changed = []
    for directory in sorted(ROOT.iterdir()):
        if not directory.is_dir():
            continue
        receipt_path = directory / 'asr-receipt.json'
        transcript_path = directory / 'asr-transcript.txt'
        if not receipt_path.exists() or not transcript_path.exists():
            continue
        receipt = json.loads(receipt_path.read_text())
        if receipt.get('status') != 'completed':
            continue
        required = ('detectedLanguage', 'languageVerified', 'languageReviewRequired',
                    'wordRateWpm', 'repeatedTrigramShare')
        if all(key in receipt for key in required):
            continue
        text = transcript_path.read_text()
        duration = float(receipt['ffprobeDurationSeconds'])
        words = text.lower().split()
        trigrams = [' '.join(words[index:index + 3]) for index in range(max(0, len(words) - 2))]
        repeated = max(collections.Counter(trigrams).values()) / max(1, len(trigrams))
        wpm = len(words) / (duration / 60)
        detected = pipeline.detect_language(text)
        receipt.update({
            'detectedLanguage': detected,
            'languageVerified': detected == 'en' and wpm >= 50 and repeated < 0.15,
            'languageReviewRequired': detected != 'en',
            'wordRateWpm': round(wpm, 2),
            'repeatedTrigramShare': round(repeated, 4),
            'languageBackfill': {
                'method': 'text_heuristic_only_no_retranscription',
                'scriptSha256': SCRIPT_SHA256,
                'backfilledUtc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'transcriptTxtSha256': receipt['outputSha256']['asr-transcript.txt'],
                'humanValidated': False,
            },
        })
        receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
        changed.append((directory.name, detected, round(wpm, 2), round(repeated, 4)))
    print(json.dumps({'backfilled': len(changed), 'records': changed,
                      'scriptSha256': SCRIPT_SHA256}, indent=2))
    if changed:
        print('Run transcribe_youtube.py to validate/reuse receipts and atomically refresh the summary.')


if __name__ == '__main__':
    main()
