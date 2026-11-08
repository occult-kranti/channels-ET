#!/usr/bin/env python3
"""Publish explicit reviewed channel-lab allowlists, never private source bodies."""
import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shutil

MODULE_FILES = {'registry': 'registry.json', 'analysis': 'analysis.json',
                'batch_asr': 'batch-asr.json', 'readings': 'readings.json',
                'asr_effects': 'asr-effects.json'}
FORBIDDEN_KEYS = {'full_text', 'transcript_text', 'source_body', 'private_evidence_text', 'private_path'}
PRIVATE_MEDIA_SUFFIXES = {'.mp4', '.mkv', '.webm', '.mp3', '.wav', '.flac', '.opus', '.m4a', '.ogg', '.safetensors', '.pt', '.pth'}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def safe_path(root, name):
    if not isinstance(name, str) or not name or '\\' in name or ':' in name:
        raise ValueError('Invalid release path')
    p = Path(name)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError('Unsafe release path')
    target = (root / p).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Release path escapes its directory')
    return target


def inspect_public_json(raw):
    if any(marker in raw for marker in (b'/workspace/', b'/dev/shm/', b'channels-et-private', b'private_evidence_text')):
        raise ValueError('Private path/evidence marker in public JSON')
    value = json.loads(raw)
    def visit(node):
        if isinstance(node, dict):
            if FORBIDDEN_KEYS & node.keys():
                raise ValueError('Private source-body field in public JSON')
            for child in node.values(): visit(child)
        elif isinstance(node, list):
            for child in node: visit(child)
        elif isinstance(node, float) and not math.isfinite(node):
            raise ValueError('Public JSON contains a non-finite numeric value')
    visit(value)
    return value


def publish(args):
    site = args.site.resolve() / 'dist/channel-lab'
    site.mkdir(parents=True, exist_ok=True)
    modules, artifacts, copies = {}, {}, []

    def copy(source, name, label=None, expected=None):
        if source.suffix.lower() in PRIVATE_MEDIA_SUFFIXES:
            raise ValueError('Raw media or model weights cannot enter this static release')
        raw = source.read_bytes()
        if expected and (len(raw) != expected['bytes'] or digest(raw) != expected['sha256']):
            raise ValueError('Producer artifact differs: ' + name)
        if source.suffix == '.json': inspect_public_json(raw)
        if name in artifacts:
            if artifacts[name]['sha256'] != digest(raw):
                raise ValueError('Different producer artifacts use the same public path: ' + name)
            return artifacts[name]
        target = safe_path(site, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        extra = max(0, len(raw) - (target.stat().st_size if target.exists() else 0))
        if shutil.disk_usage(site).free - extra < args.disk_floor_bytes:
            raise ValueError('Public copy would cross the recorded free-disk floor')
        target.write_bytes(raw)
        if target.read_bytes() != raw: raise ValueError('Published bytes differ')
        ref = {'file': name, 'bytes': len(raw), 'sha256': digest(raw), 'label': label or name}
        artifacts[name] = ref
        copies.append({'source_path': str(source.resolve()), **ref})
        return ref

    for key, filename in MODULE_FILES.items():
        folder = getattr(args, key)
        if folder is None: continue
        manifest_path = folder / 'output-manifest.json'
        producer = json.loads(manifest_path.read_text())
        entries = producer.get('public_allowlist', producer.get('files'))
        if not isinstance(entries, list) or not entries:
            raise ValueError('Producer must supply an explicit nonempty public allowlist')
        seen = set()
        for entry in entries:
            name = entry['file']
            if name in seen: raise ValueError('Duplicate producer allowlist path')
            seen.add(name)
            source = safe_path(folder, name)
            destination = ('figures/' + name if len(Path(name).parts) == 1 and
                           Path(name).suffix in ('.png', '.svg', '.pdf') else name)
            ref = copy(source, destination, entry.get('label', entry.get('title')), entry)
            if name == filename:
                modules[key] = {k: ref[k] for k in ('file', 'bytes', 'sha256')}
                modules[key]['required'] = key in ('registry', 'analysis')
            elif key == 'registry' and name == 'collection-coverage.json':
                modules['coverage'] = {k: ref[k] for k in ('file', 'bytes', 'sha256')}
                modules['coverage']['required'] = False
        if key not in modules:
            raise ValueError('Producer omitted its primary module: ' + filename)
        if key == 'registry':
            frame = producer.get('frame')
            if not frame: raise ValueError('Registry producer omitted its private frame binding')
            frame_path = safe_path(folder, frame.get('file', 'frame.json'))
            frame_raw = frame_path.read_bytes()
            if len(frame_raw) != frame['bytes'] or digest(frame_raw) != frame['sha256']:
                raise ValueError('Private source frame changed before publication')
            modules[key]['source_frame'] = {k: frame[k] for k in ('bytes', 'sha256')}

    if not {'registry', 'analysis'} <= modules.keys():
        raise ValueError('Registry and analysis are required for publication')
    repo = Path(__file__).resolve().parents[2]
    for name in ('README.md', 'PROTOCOL.md', 'METHODS.md', 'ASR-METHODS.md', 'ASR-EFFECTS.md',
                 'READINGS.md', 'PANEL.md', 'REVIEW.md', 'DESIGN.md', 'SOURCE-SCHEMA.md'):
        p = repo / 'research/channel-lab' / name
        if p.is_file(): copy(p, 'docs/' + name, name)
    manifest = {'schema_version': 1,
        'title': 'Channel and recording analysis laboratory',
        'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': 'Reconciled retained-source analysis and separate recognition editions; unknown YouTube totals are not estimated.',
        'modules': modules, 'artifacts': list(artifacts.values()),
        'builder_sha256': digest(Path(__file__).read_bytes())}
    raw = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    (site / 'manifest.json').write_bytes(raw)
    receipt = {'manifest_sha256': digest(raw), 'created_at': manifest['generated_at'], 'copies': copies}
    if args.receipt:
        if not args.receipt.resolve().is_relative_to(Path('/workspace/channels-et-private')):
            raise ValueError('Copy receipt must remain private')
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({'modules': list(modules), 'artifacts': len(artifacts), 'manifest_sha256': digest(raw)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in MODULE_FILES:
        parser.add_argument('--' + key.replace('_', '-'), type=Path)
    parser.add_argument('--site', type=Path, required=True)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--disk-floor-bytes', type=int, default=2 * 1024**3)
    publish(parser.parse_args())
