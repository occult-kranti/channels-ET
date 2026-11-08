#!/usr/bin/env python3
"""Recompute the public typed claim graph and check its source references."""
import argparse
import json
from pathlib import Path
from claim_graph import build


def verify(root):
    paths = [root / 'et-register.json', root / 'traditions-register.json']
    for path in paths:
        raw = path.read_text()
        assert not any(s in raw for s in ('/workspace/', '/tmp/', 'access_token=', 'X-Amz-Signature='))
        data = json.loads(raw)
        for field in ('mediums', 'channellees', 'sources', 'claims'):
            assert len(data[field]) == len({row['id'] for row in data[field]}), field
        assert not any('jamie-butler' in c['medium_id'] for c in data['claims'])
    actual = json.loads((root / 'claim-graph-statistics.json').read_text())
    expected = build(paths, root / 'new-message-pilot.json')
    assert actual == expected, 'Claim statistics do not match the shipped registers and pilot'
    assert all(g['identity_equivalence'] is False and g['independence_established'] is False for g in actual['comparison_groups'])
    return {'status': 'passed', 'source_records': actual['source_records'],
            'person_records': actual['medium_records'], 'source_specific_labels': actual['channellee_records'],
            'relationships': actual['claims'], 'comparison_groups': len(actual['comparison_groups']),
            'scope': 'Typed references and exact graph recomputation; roles and source claims require the separate source review.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--public-dir', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(verify(args.public_dir), indent=2))
