"""Focused integrity/privacy failure tests, using temporary synthetic data only."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

SPEC = importlib.util.spec_from_file_location('archive', Path(__file__).with_name('archive.py'))
archive = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(archive)
sys.modules['archive'] = archive
RESTORE_SPEC = importlib.util.spec_from_file_location('restore', Path(__file__).with_name('restore.py'))
restorer = importlib.util.module_from_spec(RESTORE_SPEC)
RESTORE_SPEC.loader.exec_module(restorer)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'; self.source.mkdir()

    def tearDown(self): self.temp.cleanup()

    def inventory(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return archive.inventory(self.base / 'inventory', {'fixture': self.source})

    def test_aliases_empty_files_symlinks_and_exclusions(self):
        (self.source / 'a.txt').write_text('same retained bytes')
        (self.source / 'b.txt').hardlink_to(self.source / 'a.txt')
        (self.source / 'c.txt').write_text('same retained bytes')
        (self.source / 'empty').touch()
        (self.source / 'link').symlink_to('a.txt')
        (self.source / 'outside').symlink_to('/etc/passwd')
        (self.source / '.env').write_text('password=synthetic')
        (self.source / 'model-cache').mkdir()
        (self.source / 'model-cache' / 'model.bin').write_bytes(b'fake weights')
        value = self.inventory()
        self.assertEqual(value['counts']['logical_regular_file_paths'], 4)
        self.assertEqual(value['counts']['unique_content_objects'], 2)
        self.assertEqual(value['counts']['symlinks_recorded'], 2)
        self.assertEqual(value['counts']['explicit_exclusions'], 2)
        self.assertEqual(max(o['aliases'] for o in value['objects']), 3)

    def test_known_token_excluded_without_disclosing_value(self):
        # Deliberately synthetic recognizable token, never a live credential.
        token = 'ghp_' + 'x' * 40
        (self.source / 'accidental.txt').write_text(token)
        value = self.inventory()
        self.assertEqual(value['counts']['credential_bearing_files_excluded'], 1)
        self.assertNotIn(token, json.dumps(value))

    def test_roundtrip_local_archive_and_original_preserved(self):
        (self.source / 'unicode-α.txt').write_text('Synthetic research fixture\n' * 100)
        value = self.inventory()
        inv = self.base / 'inventory/inventory.json'; plan = self.base / 'plan.json'
        archive.plan(inv, plan, 8192)
        shard = self.base / 'shard.tar.zst'
        result = archive.build_shard(inv, plan, 1, shard, floor=0)
        self.assertEqual(result['objects_verified'], 1)
        self.assertEqual(result['source_bytes_verified'], value['counts']['unique_content_bytes'])
        self.assertTrue((self.source / 'unicode-α.txt').exists())
        self.assertFalse(result['source_files_removed'])

    def test_source_change_rejected(self):
        path = self.source / 'a.txt'; path.write_text('frozen')
        self.inventory()
        inv = self.base / 'inventory/inventory.json'; plan = self.base / 'plan.json'
        archive.plan(inv, plan, 8192)
        path.write_text('edited')
        with self.assertRaisesRegex(ValueError, 'differs'):
            archive.build_shard(inv, plan, 1, self.base / 'shard.tar.zst', floor=0)
        self.assertEqual(path.read_text(), 'edited')

    def test_restoration_recovers_aliases_and_preserves_source(self):
        (self.source/'a.txt').write_text('Fixture content')
        (self.source/'b.txt').write_text('Fixture content')
        self.inventory()
        inv=self.base/'inventory/inventory.json'; plan=self.base/'plan.json'
        archive.plan(inv,plan,8192)
        archive.build_shard(inv,plan,1,self.base/'shard-001.tar.zst',floor=0)
        count=restorer.restore(inv,plan,self.base,self.base,self.base/'restored',hardlinks=True)
        self.assertEqual(count,2)
        self.assertEqual((self.base/'restored/fixture/a.txt').read_text(),'Fixture content')
        self.assertEqual((self.base/'restored/fixture/a.txt').stat().st_ino,(self.base/'restored/fixture/b.txt').stat().st_ino)
        self.assertTrue((self.source/'a.txt').exists())
        with self.assertRaisesRegex(ValueError,'fresh'):
            restorer.restore(inv,plan,self.base,self.base,self.base/'restored')

    def test_tampered_plan_binding_rejected(self):
        (self.source/'a.txt').write_text('Fixture content')
        self.inventory()
        inv=self.base/'inventory/inventory.json'; plan=self.base/'plan.json'
        archive.plan(inv,plan,8192)
        inv.write_text(inv.read_text()+'\n')
        with self.assertRaisesRegex(ValueError,'different inventory'):
            archive.build_shard(inv,plan,1,self.base/'shard.tar.zst',floor=0)

    def test_wrong_remote_download_bytes_rejected(self):
        ref={'file':'test.tar.zst','bytes':3,'sha256':archive.hashlib.sha256(b'yes').hexdigest()}
        asset={'name':ref['file'],'size':3,'state':'uploaded','digest':None}
        process=mock.Mock();process.stdout=io.BytesIO(b'no!');process.wait.return_value=0;process.poll.return_value=0
        with mock.patch.object(archive,'repository'),mock.patch.object(archive,'release_info',return_value={'assets':[asset]}),mock.patch.object(archive.subprocess,'Popen',return_value=process):
            with self.assertRaisesRegex(ValueError,'Remote bytes differ'):
                archive.verify_remote('fixture/private','v1',ref)

    def test_unsafe_archive_members_and_relative_paths_rejected(self):
        for name in ['/etc/passwd', '../outside', 'safe/../../outside', 'a\\b']:
            with self.assertRaises(ValueError): archive.allowed_relative(name)
        raw = self.base / 'unsafe.tar'
        with tarfile.open(raw, 'w') as tf:
            item = tarfile.TarInfo('../outside'); item.size = 3
            tf.addfile(item, io.BytesIO(b'bad'))
        zipped = self.base / 'unsafe.tar.zst'
        with zipped.open('wb') as out:
            subprocess.run(['zstd', '-q', '-c', str(raw)], stdout=out, check=True)
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            archive.check_shard(zipped, {})

    def test_public_destination_rejected(self):
        with mock.patch.object(archive, 'run', return_value=json.dumps({'private': False})):
            with self.assertRaisesRegex(ValueError, 'not private'):
                archive.repository('fixture/public')

    def test_wrong_remote_api_digest_rejected_before_download(self):
        ref = {'file': 'test.tar.zst', 'bytes': 1, 'sha256': 'a'*64}
        asset = {'name': ref['file'], 'size': 1, 'state': 'uploaded', 'digest': 'sha256:'+'b'*64}
        with mock.patch.object(archive, 'repository'), mock.patch.object(archive, 'release_info', return_value={'assets':[asset]}):
            with self.assertRaisesRegex(ValueError, 'digest differs'):
                archive.verify_remote('fixture/private', 'v1', ref)

    def test_exactly_two_gib_payload_is_not_permitted(self):
        with self.assertRaisesRegex(ValueError, 'headroom'):
            archive.plan(self.base/'unused', self.base/'plan', 2*1024**3)


if __name__ == '__main__': unittest.main()
