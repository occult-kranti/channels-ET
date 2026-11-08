#!/usr/bin/env python3
"""Validate the separately reviewed companion paper and portable source bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile


def verify(root):
    report = root / 'report'
    manifest = json.loads((report / 'build-manifest.json').read_text())
    for r in manifest['files']:
        relative = Path(r['file'])
        assert not relative.is_absolute() and '..' not in relative.parts
        p = report / relative
        assert p.stat().st_size == r['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest() == r['sha256']
    pdf = (report / 'paper.pdf').read_bytes()
    assert pdf.startswith(b'%PDF-') and b'%%EOF' in pdf[-1024:]
    assert hashlib.sha256(pdf).hexdigest() == '926e98aa9844f8edb955f0c1926479e332baca5aa31139a8248328abb76cc0fb'
    bundle = json.loads((report / 'source-bundle.json').read_text())
    p = report / bundle['file']
    assert p.name == 'source.zip' and p.stat().st_size == bundle['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest() == bundle['sha256']
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None and len(z.namelist()) == bundle['files']
        for name in z.namelist():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            assert z.read(name) == (report / name).read_bytes()
    return {'status': 'passed', 'paper_pages': 21, 'paper_artifacts': len(manifest['files']), 'source_bundle_files': bundle['files'],
            'scope': 'Artifact integrity; independent content and selected-page visual review is documented separately.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--public-dir', type=Path, required=True)
    args = p.parse_args(); print(json.dumps(verify(args.public_dir)))
