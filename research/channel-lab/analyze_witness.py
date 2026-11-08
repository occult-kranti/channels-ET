#!/usr/bin/env python3
"""Create a portable witness edition from the trusted local producer's NPZ.

The legacy producer emits feature names with object dtype. Only use this on its
own trusted private output: loading an arbitrary pickle-backed NPZ is unsafe.
No text, numerical values, original files or scientific outputs are changed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import numpy as np


def reference(path):
    return {'file': str(path), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def convert(source, destination, analysis_sha256):
    source, destination = Path(source), Path(destination)
    original = source / 'core-vectors.npz'
    destination.mkdir(exist_ok=False)
    with np.load(original, allow_pickle=True) as loaded:
        arrays = {key: loaded[key] for key in loaded.files}
    object_keys = [key for key, value in arrays.items() if value.dtype.hasobject]
    if object_keys != ['features']:
        raise ValueError('Expected only the trusted producer feature-name object array')
    features = arrays['features']
    if not all(isinstance(value, str) for value in features):
        raise ValueError('Feature names must all be strings')
    old_arrays = dict(arrays)
    arrays['features'] = np.asarray(features, dtype=str)
    portable = destination / original.name
    np.savez(portable, **arrays)
    with np.load(portable, allow_pickle=False) as checked:
        for key, value in old_arrays.items():
            if not np.array_equal(checked[key], value):
                raise ValueError('Portable conversion changed array values: ' + key)
    for item in source.iterdir():
        if item.name != original.name and item.is_file():
            os.link(item, destination / item.name)
    receipt = {'status': 'portable_witness_only', 'parent': reference(original),
               'portable': reference(portable), 'converted_keys': object_keys,
               'numerical_arrays_identical': True, 'all_array_values_identical': True,
               'features_before_dtype': str(features.dtype),
               'features_after_dtype': str(arrays['features'].dtype),
               'analysis_sha256': analysis_sha256}
    (destination / 'portable-witness-receipt.json').write_text(
        json.dumps(receipt, indent=2) + '\n')
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trusted-source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--analysis-sha256', required=True)
    args = parser.parse_args()
    print(json.dumps(convert(args.trusted_source, args.destination, args.analysis_sha256)))
