#!/usr/bin/env python3
"""Copy public metadata sources into this inventory without editing either origin."""
import argparse
import datetime
import hashlib
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def capture(bashar, atlas):
    files = []
    selections = [('bashar-index', bashar, [bashar / 'index.html', *sorted((bashar / 'data').rglob('*'))]),
                  ('channels-ET', atlas, [atlas / p for p in ['dist/analysis/data.json', 'dist/data.json', 'research/expansion/acquisition/collection-plan.json']])]
    repositories = {}
    for name, root, paths in selections:
        repositories[name] = {'origin': 'https://github.com/occult-kranti/' + name,
                              'head': subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()}
        for original in paths:
            if not original.is_file():
                continue
            relative = original.relative_to(root)
            content = original.read_bytes()
            target = HERE / 'sourcepins' / name / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            # Reading the origin again detects a source change during capture.
            if content != original.read_bytes():
                raise RuntimeError('Source changed during capture: ' + str(original))
            files.append({'source_id': name + ':' + str(relative), 'repository': name,
                          'origin_path': str(relative), 'snapshot_path': str(target.relative_to(HERE)),
                          'sha256': sha(content), 'bytes': len(content)})
    manifest = {'schema_version': 1, 'captured_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'scope': 'Public metadata/link sources only; no video, audio, captions or model weights.',
                'repositories': repositories, 'files': sorted(files, key=lambda x: x['source_id'])}
    (HERE / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'source_files': len(files), 'source_bytes': sum(x['bytes'] for x in files)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bashar-root', type=pathlib.Path, default=pathlib.Path('/workspace/bashar-index'))
    parser.add_argument('--atlas-root', type=pathlib.Path, default=HERE.parents[2])
    args = parser.parse_args()
    capture(args.bashar_root, args.atlas_root)
