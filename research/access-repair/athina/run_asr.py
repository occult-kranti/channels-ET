#!/usr/bin/env python3
"""Run the pinned existing ASR core with an explicitly isolated source ledger."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CORE = ROOT / 'research/harvest/asr/transcribe.py'
EXPECTED_CORE = 'f42b8bcf2ad8f69238119c2da16022d310d99b0c02af40aa7214b9c054ee3a1a'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    if sha(CORE) != EXPECTED_CORE:
        raise ValueError('The source adapter requires the reviewed ASR core; inspect any changed version first')
    ledger_path = HERE / 'publisher_sources/publisher-summary.json'
    ledger = json.loads(ledger_path.read_text())
    rows = ledger['records']
    if not ledger.get('terminal') or len(rows) != 1 or rows[0]['status'] != 'completed':
        raise ValueError('Require exactly one completed, terminal original-publisher source')
    row = rows[0]
    original_ledger = ROOT / 'research/harvest/publisher_sources/publisher-summary.json'
    original_sha = sha(original_ledger)
    old = json.loads(original_ledger.read_text())
    if row['sha256'] in {r.get('sha256') for r in old['records']}:
        raise ValueError('Do not overwrite an earlier cohort receipt for identical audio bytes')
    out = HERE / 'asr'
    out.mkdir(exist_ok=True)
    model_source = CORE.parent / 'model-manifest.json'
    model_target = out / 'model-manifest.json'
    if model_target.exists() and model_target.read_bytes() != model_source.read_bytes():
        raise ValueError('Isolated model manifest changed')
    shutil.copyfile(model_source, model_target)
    retained = out / ('executed-core-' + EXPECTED_CORE + '.py')
    if retained.exists() and sha(retained) != EXPECTED_CORE:
        raise ValueError('Retained decoder source changed')
    shutil.copyfile(CORE, retained)
    source_ledger_sha = sha(ledger_path)
    adapter = {'schemaVersion': 1, 'startedAt': datetime.now(timezone.utc).isoformat(),
               'status': 'started', 'corePath': str(CORE.relative_to(ROOT)), 'coreSha256': EXPECTED_CORE,
               'adapterSha256': sha(Path(__file__)), 'sourceId': row['source_id'],
               'sourceLedgerSha256': source_ledger_sha, 'audioSha256': row['sha256'],
               'adaptedConstants': {'HERE': str(out)},
               'adaptationScope': 'Isolated publisher ledger, public receipt directory and identical model manifest. Original decoder/settings/raw-output path are unchanged.',
               'networkRequests': 0, 'originalNineteenCohortMutated': False}
    adapter_path = out / 'adapter-execution.json'
    adapter_path.write_text(json.dumps(adapter, indent=2) + '\n')
    spec = importlib.util.spec_from_file_location('reviewed_primary_audio_asr', CORE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.HERE = out
    before_argv = sys.argv
    sys.argv = [str(CORE), '--audio', row['raw_local_path'], '--source-id', row['source_id'],
                '--source-url', row['enclosure_url'], '--source-sha256', row['sha256'], '--cpu-threads', '2']
    try:
        module.main()
        if sha(ledger_path) != source_ledger_sha or sha(original_ledger) != original_sha:
            raise ValueError('Source ledger changed during decoding')
        receipt_path = out / (row['sha256'][:20] + '-receipt.json')
        receipt = json.loads(receipt_path.read_text())
        if receipt['status'] != 'completed' or receipt['transcribedScope'] != 'full_decoded_audio':
            raise ValueError('Decoder did not produce a full-audio result')
        adapter.update(status='completed', completedAt=datetime.now(timezone.utc).isoformat(),
                       publicReceipt=receipt_path.name, publicReceiptSha256=sha(receipt_path),
                       segments=receipt['segments'], words=receipt['words'],
                       sourceAudioDurationSeconds=receipt['sourceAudioDurationSeconds'],
                       humanAccuracyValidated=False, youtubeEditionEquivalenceVerified=False)
    except Exception as exc:
        adapter.update(status='failed', errorType=type(exc).__name__, error=str(exc))
        raise
    finally:
        sys.argv = before_argv
        adapter_path.write_text(json.dumps(adapter, indent=2) + '\n')
    print(json.dumps({k: adapter[k] for k in ('status', 'sourceId', 'segments', 'words', 'sourceAudioDurationSeconds')}))


if __name__ == '__main__':
    main()
