#!/usr/bin/env python3
"""Copy explicit reviewed allowlists and bind a static knowledge-bank manifest."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import zipfile


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ref(path, relative, **extra):
    return {'file': relative, 'bytes': path.stat().st_size, 'sha256': digest(path), **extra}


def publish(args):
    repo = Path(__file__).resolve().parents[2]
    out = args.site.resolve() / 'dist/knowledge-bank'; out.mkdir(parents=True, exist_ok=True)
    modules, artifacts, copied = {}, {}, []

    def copy(source, relative, label=None):
        name = Path(relative)
        if name.is_absolute() or '..' in name.parts: raise ValueError('Unsafe artifact path')
        target = out / name; target.parent.mkdir(parents=True, exist_ok=True)
        if source.suffix == '.json':
            raw = source.read_bytes()
            if any(marker in raw for marker in (b'/workspace/', b'private_evidence_text', b'channels-et-private')):
                raise ValueError('Private marker in public JSON: ' + source.name)
        shutil.copy2(source, target)
        if digest(source) != digest(target): raise ValueError('Copied artifact differs')
        r = ref(target, relative)
        copied.append({'source': str(source), **r})
        if label: artifacts[relative] = {**r, 'label': label}
        return r

    def release(folder, key, filename):
        data = json.loads((folder / 'output-manifest.json').read_text())
        entries = data.get('public_allowlist', data.get('files'))
        if not entries: raise ValueError('No explicit public allowlist')
        for entry in entries:
            name = entry['file']; p = Path(name)
            if p.is_absolute() or len(p.parts) != 1: raise ValueError('Unexpected release path')
            source = folder / name
            if source.stat().st_size != entry['bytes'] or digest(source) != entry['sha256']:
                raise ValueError('Release artifact changed: ' + name)
            if name == filename:
                modules[key] = {**copy(source, name, name), 'required': key in ('analysis', 'knowledge')}
            elif p.suffix in ('.png', '.svg', '.pdf'):
                copy(source, 'figures/' + name, entry.get('title', name))
            elif name in ('questions.sqlite', 'question-bank.md'):
                copy(source, name, 'Queryable question database' if name.endswith('.sqlite') else 'Question-bank reading document')
            else:
                raise ValueError('Unrecognized public release member: ' + name)
        if key not in modules: raise ValueError('Release omitted primary module: ' + key)

    release(args.analysis, 'analysis', 'analysis.json')
    release(args.knowledge, 'knowledge', 'knowledge.json')
    release(args.retrieval, 'retrieval', 'retrieval.json')
    for key, source, filename in [('asr', args.asr, 'asr-benchmark.json'),
            ('literature', args.literature, 'literature-register.json'),
            ('experiments', args.experiments, 'experiments.json'),
            ('full_asr', args.full_asr, 'asr-full.json')]:
        if source: modules[key] = {**copy(source, filename, filename), 'required': False}
    if args.sensitivity: release(args.sensitivity, 'asr_sensitivity', 'asr-sensitivity.json')
    if args.contextual_terms: release(args.contextual_terms, 'contextual_terms', 'contextual-terms.json')
    for filename in ('README.md', 'PROTOCOL.md', 'METHODS.md', 'CODEBOOK.md', 'LITERATURE.md',
            'PANEL.md', 'DATASET-CARD.md', 'asr_METHODS.md', 'INDEPENDENT-REVIEW.md', 'REVIEW.md'):
        source = repo / 'research/knowledge-bank' / filename
        if source.is_file(): copy(source, 'docs/' + filename, filename)
    query_cli = repo / 'research/knowledge-bank/question_query.py'
    copy(query_cli, 'question_query.py', 'Offline Python question-bank query tool')
    skill_root = repo / 'research/knowledge-bank/skills'
    skill_files = sorted(p for p in skill_root.rglob('*') if p.is_file())
    if skill_files:
        target = out / 'project-skills.zip'
        with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for p in skill_files: z.write(p, str(p.relative_to(skill_root)))
        with zipfile.ZipFile(target) as z:
            if z.testzip() is not None: raise ValueError('Skill bundle integrity failure')
        artifacts[target.name] = ref(target, target.name, label='Three reusable project research skills')
    if args.report:
        report = json.loads((args.report / 'manifest.json').read_text())
        entries = report.get('public_allowlist', report.get('artifacts', []))
        if not entries: raise ValueError('Report lacks publication allowlist')
        for entry in entries:
            name = entry.get('file', entry.get('path'))
            if name not in ('report.pdf', 'source.zip', 'report.md', 'main.tex'): continue
            p = args.report / name
            if digest(p) != entry['sha256'] or p.stat().st_size != entry['bytes']: raise ValueError('Report artifact changed')
            copy(p, 'report/' + name, 'Technical report / portable source: ' + name)
    manifest = {'schema_version': 1, 'title': 'Channeling knowledge bank and recognition laboratory',
        'generated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope': 'Separate, source-bound text, curated-question, retrieval and speech-recognition frames. Source assertions and model outputs remain distinct from authenticated claims.',
        'modules': modules, 'artifacts': list(artifacts.values()),
        'builder_sha256': digest(Path(__file__))}
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    if args.receipt:
        receipt = args.receipt.resolve()
        if not receipt.is_relative_to(Path('/workspace/channels-et-private')): raise ValueError('Private receipt path required')
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({'generated_at': manifest['generated_at'], 'manifest_sha256': digest(out / 'manifest.json'),
            'source_files': copied, 'modules': list(modules)}, indent=2) + '\n')
    print(json.dumps({'modules': list(modules), 'artifacts': len(artifacts), 'manifest_sha256': digest(out / 'manifest.json')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('analysis', 'knowledge', 'retrieval', 'asr', 'literature', 'experiments', 'site'):
        p.add_argument('--' + name, type=Path, required=True)
    for name in ('full-asr', 'sensitivity', 'contextual-terms', 'report', 'receipt'):
        p.add_argument('--' + name, type=Path)
    publish(p.parse_args())
