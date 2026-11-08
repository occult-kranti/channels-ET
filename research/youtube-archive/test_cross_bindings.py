"""Independent metadata integration fixtures; no acquisition or source content."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


HERE = Path(__file__).parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Verify the exact adjacent modules even if a broader test session already
# imported another study's generic build_public or verify_inventory modules.
BUILDER = load('archive_cross_builder', 'build_public.py')
INVENTORY_VERIFIER = load('archive_cross_inventory', 'verify_inventory.py')
with mock.patch.dict(sys.modules, {'build_public': BUILDER,
                                   'verify_inventory': INVENTORY_VERIFIER}):
    VERIFIER = load('archive_cross_release', 'verify_release.py')


def encode(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


def binding(name, raw):
    return {'file': name, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


class CrossBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='archive-cross-fixture-', dir='/dev/shm')
        self.addCleanup(self.temp.cleanup)
        self.site = Path(self.temp.name)
        self.public = self.site / 'dist/youtube-archive'
        self.public.mkdir(parents=True)
        self.aid, self.bid = 'synthetic-a', 'synthetic-b'
        self.cid, self.did = 'UC' + 'a' * 22, 'UC' + 'b' * 22
        self.vid, self.other = 'AbCdEfGhI_1', 'AbCdEfGhI_2'
        self.discovery = {'videos': [{'identity': self.vid}]}
        self.inventory = {
            'accounts': [{'account_id': self.aid}, {'account_id': self.bid}],
            'videos': [{'video_id': self.vid}, {'video_id': self.other}],
            'coverage': {'accounts': 2, 'unique_observed_video_ids': 2},
            'inputs': [binding('publisher-discovery.json', encode(self.discovery))]}
        def account(aid, cid):
            return {'account_id': aid, 'channel_id': cid,
                    'retained_video_ids': [], 'retained_audio_ids': [],
                    'retained_caption_ids': [], 'retained_transcript_ids': []}
        self.collection = {
            'accounts': [account(self.aid, self.cid), account(self.bid, self.did)],
            'videos': [{'video_id': self.vid, 'verified_owner_channel_id': self.cid},
                       {'video_id': self.other, 'verified_owner_channel_id': self.did}],
            'coverage': {'distinct_observed_video_ids': 2,
                         'tab_requests_this_run': 0, 'metadata_requests_this_run': 0,
                         'media_requests_this_run': 0, 'caption_requests_this_run': 0},
            'network_gate': {'status': 'gateway_connect_denied'},
            'inventory_binding': binding('inventory.json', encode(self.inventory))}

    def write(self, refresh_inventory_binding=False, refresh_discovery_binding=False):
        if refresh_discovery_binding:
            self.inventory['inputs'] = [binding('publisher-discovery.json', encode(self.discovery))]
        if refresh_inventory_binding:
            self.collection['inventory_binding'] = binding('inventory.json', encode(self.inventory))
        for name, obj in (('inventory.json', self.inventory),
                          ('collector-status.json', self.collection),
                          ('publisher-discovery.json', self.discovery)):
            (self.public / name).write_bytes(encode(obj))

    def reject(self, message):
        self.write()
        with self.assertRaisesRegex(ValueError, message):
            VERIFIER.verify_cross_bindings(self.site)

    def test_valid_exact_editions_and_owner_credit(self):
        self.collection['accounts'][0]['retained_audio_ids'] = [self.vid]
        self.write()
        result = VERIFIER.verify_cross_bindings(self.site)
        self.assertEqual(result['inventory_accounts'], 2)
        self.assertEqual(result['inventory_video_ids'], 2)
        self.assertEqual(result['discovery_ids'], 1)

    def test_stale_collector_inventory_hash_or_bytes(self):
        original = copy.deepcopy(self.collection['inventory_binding'])
        for field, value in (('sha256', '0' * 64), ('bytes', original['bytes'] + 1)):
            with self.subTest(field=field):
                self.collection['inventory_binding'] = {**original, field: value}
                self.reject('Collector does not bind this exact inventory')

    def test_stale_discovery_edition_hash(self):
        # The ID is already in the inventory, so only edition binding fails.
        self.discovery['videos'].append({'identity': self.other})
        self.reject('Inventory does not bind this exact discovery edition')

    def test_inventory_cannot_omit_discovered_id_even_with_fresh_hash_binding(self):
        self.discovery['videos'].append({'identity': 'AbCdEfGhI_3'})
        self.write(refresh_inventory_binding=True, refresh_discovery_binding=True)
        with self.assertRaisesRegex(ValueError, 'inventory omits this discovery edition IDs'):
            VERIFIER.verify_cross_bindings(self.site)

    def test_collector_cannot_omit_indexed_video(self):
        self.collection['videos'].pop()
        self.collection['coverage']['distinct_observed_video_ids'] = 1
        self.reject('Collector omitted indexed IDs')

    def test_mismatched_account_set(self):
        self.collection['accounts'][1]['account_id'] = 'synthetic-wrong-context'
        self.reject('Collector account set differs')

    def test_duplicate_collector_account_rows_cannot_collapse_into_set(self):
        self.collection['accounts'].append(copy.deepcopy(self.collection['accounts'][0]))
        self.reject('Duplicate collector account identities')

    def test_duplicate_collector_video_rows_cannot_collapse_into_set(self):
        self.collection['videos'].append(copy.deepcopy(self.collection['videos'][0]))
        self.reject('Duplicate collector video identities')

    def test_generic_failed_transport_holds_current_operations(self):
        self.collection['network_gate']['status'] = 'failed'
        self.collection['coverage']['metadata_requests_this_run'] = 1
        self.reject('requests proceeded after shared gateway gate')

    def test_retained_credit_requires_exact_verified_uploader(self):
        for kind in ('retained_video_ids', 'retained_audio_ids', 'retained_caption_ids', 'retained_transcript_ids'):
            with self.subTest(kind=kind):
                self.collection['accounts'][1][kind] = [self.vid]
                self.reject('credited to an unverified uploader')
                self.collection['accounts'][1][kind] = []
        self.collection['accounts'][0]['retained_audio_ids'] = [self.vid]
        self.collection['videos'][0]['verified_owner_channel_id'] = None
        self.reject('credited to an unverified uploader')

    def test_shared_gate_prevents_each_current_request_class(self):
        for key in ('tab_requests_this_run', 'metadata_requests_this_run',
                    'media_requests_this_run', 'caption_requests_this_run'):
            with self.subTest(key=key):
                self.collection['coverage'][key] = 1
                self.reject('requests proceeded after shared gateway gate')
                self.collection['coverage'][key] = 0


if __name__ == '__main__':
    unittest.main()
