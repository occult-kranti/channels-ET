#!/usr/bin/env python3
"""Synthetic local exporter fixtures; no YouTube retrieval or empirical media claims."""
import copy
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('export_verified', Path(__file__).with_name('export_verified.py'))
exporter = importlib.util.module_from_spec(spec); spec.loader.exec_module(exporter)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='et-export-synthetic-'); self.root = Path(self.temp.name)
        self.raw = self.root / 'raw'; self.folder = self.raw / 'quarantine/00000000000/video/fixture'; self.folder.mkdir(parents=True)
        self.video = self.folder / '00000000000.mp4'; self.video.write_bytes(b'SYNTHETIC LOCAL BYTES; FFPROBE IS MOCKED; NOT A YOUTUBE DOWNLOAD')
        self.info = self.folder / '00000000000.info.json'
        self.metadata = {'id': '00000000000', 'webpage_url': 'https://www.youtube.com/watch?v=00000000000', 'duration': 600,
                         'media_type': 'video', 'channel_id': 'UC' + 'A' * 22, 'channel': 'Synthetic test channel', 'title': 'Synthetic source fixture'}
        self.info.write_text(json.dumps(self.metadata))
        self.validation = {'source_video_id': '00000000000', 'metadata_sha256': exporter.sha(self.info), 'ffprobe_duration_seconds': 600}
        self.db = self.raw / 'state.sqlite'
        with sqlite3.connect(self.db) as con:
            con.executescript('''CREATE TABLE items(source_id TEXT,video_id TEXT,selected INTEGER,metadata_json TEXT,metadata_sha256 TEXT,metadata_verified_at REAL,format_verified INTEGER,classification TEXT);
                CREATE TABLE jobs(source_id TEXT,kind TEXT,status TEXT,attempts INTEGER);
                CREATE TABLE artifacts(path TEXT,source_id TEXT,kind TEXT,bytes INTEGER,sha256 TEXT,validation_json TEXT,status TEXT);
                CREATE TABLE bashar_slots(source_id TEXT);''')
            con.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?)', ('youtube:00000000000','00000000000',1,json.dumps(self.metadata),exporter.sha(self.info),946684800,1,'other_not_bashar_labeled'))
            con.execute('INSERT INTO jobs VALUES(?,?,?,?)', ('youtube:00000000000','video','verified_quarantine',1))
            con.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?)', (str(self.video.relative_to(self.raw)),'youtube:00000000000','video',self.video.stat().st_size,exporter.sha(self.video),json.dumps(self.validation),'verified_quarantine'))
        self.selection = self.root / 'selection.json'
        self.candidate = {'video_id':'00000000000','source_id':'youtube:00000000000','context_associations':[{'context_id':'person-z','name':'Synthetic Z'},{'context_id':'person-a','name':'Synthetic A'}]}
        self.selection.write_text(json.dumps({'schema_version':1,'records':[self.candidate]}))
        self.output = self.root / 'output'
        self.probe = {'format':{'duration':'600'},'streams':[{'codec_type':'video','height':360},{'codec_type':'audio'}]}

    def tearDown(self): self.temp.cleanup()

    def run_export(self, probe=None):
        with patch.object(exporter, 'probe_media', return_value=probe or self.probe):
            result = exporter.export_verified(self.db,self.selection,self.raw,self.output)
        manifest = json.loads(Path(result['manifest']).read_text())
        proof = json.loads(Path(result['verification_receipt']['path']).read_text())
        return result,manifest,proof

    def update_metadata(self, **changes):
        self.metadata.update(changes); self.info.write_text(json.dumps(self.metadata))
        self.validation['metadata_sha256'] = exporter.sha(self.info)
        with sqlite3.connect(self.db) as con:
            con.execute('UPDATE items SET metadata_json=?,metadata_sha256=?',(json.dumps(self.metadata),exporter.sha(self.info)))
            con.execute('UPDATE artifacts SET validation_json=?',(json.dumps(self.validation),))

    def update_validation(self, **changes):
        self.validation.update(changes)
        with sqlite3.connect(self.db) as con: con.execute('UPDATE artifacts SET validation_json=?',(json.dumps(self.validation),))

    def test_legacy_old_capture_is_accepted_without_now_ttl_and_preserves_contexts(self):
        before = exporter.sha(self.db); result,manifest,proof = self.run_export()
        self.assertEqual(result['verified'],1); self.assertEqual(exporter.sha(self.db),before)
        row=manifest['records'][0]; self.assertEqual(row['medium_id'],'person-a');self.assertEqual(row['context_associations'],self.candidate['context_associations'])
        self.assertEqual(row['acquisition_validated_at'],'2000-01-01T00:00:00+00:00'); self.assertEqual(row['duration_scope'],'source_video')
        self.assertEqual(row['verification_receipt']['sha256'],exporter.sha(Path(row['verification_receipt']['path'])))
        self.assertEqual(proof['verified_artifacts'][0]['status'],'verified');self.assertEqual(proof['network_requests'],0)

    def test_new_captured_proof_survives_later_item_metadata_refresh(self):
        self.update_validation(metadata_refreshed_at_acquisition=True,validated_at='2000-01-01T00:01:00+00:00',acquisition_started_at='2000-01-01T00:00:20+00:00',
            admission_metadata={'metadata_sha256':'a'*64,'metadata_verified_at':946684800},source_classification_at_acquisition='other_not_bashar_labeled',non_shorts_verified_at_acquisition=True)
        with sqlite3.connect(self.db) as con:con.execute('UPDATE items SET metadata_sha256=?,metadata_json=?',('b'*64,'{}'))
        result,manifest,_=self.run_export();self.assertEqual(result['verified'],1);self.assertEqual(manifest['records'][0]['acquisition_proof_basis'],'artifact_captured_admission_and_validation')

    def test_new_proof_rejects_stale_at_acquisition_metadata(self):
        self.update_validation(metadata_refreshed_at_acquisition=True,validated_at='2000-01-01T01:01:00+00:00',acquisition_started_at='2000-01-01T01:00:20+00:00',
            admission_metadata={'metadata_sha256':'a'*64,'metadata_verified_at':946684800},source_classification_at_acquisition='other_not_bashar_labeled',non_shorts_verified_at_acquisition=True)
        result,_,proof=self.run_export();self.assertEqual(result['verified'],0);self.assertIn('acquisition_time_proof_invalid',proof['excluded'][0]['reasons'])

    def test_missing_media_or_hash_mismatch_never_exports(self):
        self.video.write_bytes(b'changed')
        result,_,proof=self.run_export();self.assertEqual(result['verified'],0);self.assertIn('artifact_bytes_mismatch',proof['excluded'][0]['reasons'])

    def test_mismatched_captured_metadata_never_uses_current_description(self):
        self.info.write_text('{}')
        result,_,proof=self.run_export();self.assertEqual(result['verified'],0);self.assertIn('captured_metadata_hash_or_identity_mismatch',proof['excluded'][0]['reasons'])

    def test_positive_shorts_and_missing_format_are_held(self):
        for changes in ({'media_type':'short'},{'is_short':True},{'media_type':None},{'title':'Synthetic #shorts'},{'is_live':True}):
            with self.subTest(changes=changes):
                self.update_metadata(media_type='video',is_short=None,title='Synthetic',is_live=False);self.update_metadata(**changes)
                self.output=self.root/('result-'+str(len(list(self.root.glob('result-*')))))
                result,_,proof=self.run_export();self.assertEqual(result['verified'],0);self.assertIn('non_shorts_completed_format_unproven',proof['excluded'][0]['reasons'])

    def test_channel_id_and_measured_streams_must_be_proven(self):
        self.update_metadata(channel_id='unverified-name')
        result,_,proof=self.run_export();self.assertEqual(result['verified'],0);self.assertIn('canonical_channel_id_missing',proof['excluded'][0]['reasons'])
        self.update_metadata(channel_id='UC'+'A'*22);self.output=self.root/'no-audio'
        result,_,proof=self.run_export({'format':{'duration':'600'},'streams':[{'codec_type':'video','height':360}]});self.assertEqual(result['verified'],0)

    def test_bashar_requires_slot_and_consistent_captured_classification(self):
        self.update_metadata(title='Bashar synthetic fixture')
        with sqlite3.connect(self.db) as con:con.execute("UPDATE items SET classification='bashar'")
        result,_,proof=self.run_export();self.assertEqual(result['verified'],0);self.assertIn('bashar_cap_slot_missing',proof['excluded'][0]['reasons'])
        with sqlite3.connect(self.db) as con:con.execute('INSERT INTO bashar_slots VALUES(?)',('youtube:00000000000',))
        self.output=self.root/'with-slot';self.assertEqual(self.run_export()[0]['verified'],1)

    def test_path_traversal_and_parent_symlink_are_rejected(self):
        with sqlite3.connect(self.db) as con:con.execute('UPDATE artifacts SET path=?',('../outside.mp4',))
        result,_,proof=self.run_export();self.assertEqual(result['verified'],0);self.assertIn('artifact_relative_path_invalid',proof['excluded'][0]['reasons'])
        link=self.raw/'quarantine/link';link.symlink_to(self.folder,target_is_directory=True)
        with sqlite3.connect(self.db) as con:con.execute('UPDATE artifacts SET path=?',('quarantine/link/00000000000.mp4',))
        self.output=self.root/'symlink-result';result,_,proof=self.run_export();self.assertEqual(result['verified'],0);self.assertIn('path_symlink_or_traversal',proof['excluded'][0]['reasons'])

    def test_existing_output_and_git_output_are_not_overwritten(self):
        self.output.mkdir();sentinel=self.output/'private.txt';sentinel.write_text('preserve')
        with self.assertRaises(exporter.ExportError):self.run_export()
        self.assertEqual(sentinel.read_text(),'preserve')
        git=self.root/'repo';(git/'.git').mkdir(parents=True);(git/'.git/HEAD').write_text('ref: refs/heads/fixture\n');self.output=git/'result'
        with self.assertRaises(exporter.ExportError):self.run_export()
        self.assertFalse(self.output.exists())

    def test_empty_managed_workspace_git_placeholder_is_not_a_checkout(self):
        (self.root/'.git').mkdir()
        self.assertEqual(self.run_export()[0]['verified'],1)

    def test_selection_duplicates_and_missing_contexts_fail_without_outputs(self):
        for rows in ([self.candidate,self.candidate],[{**self.candidate,'context_associations':[]}],[{**self.candidate,'source_id':'youtube:wrongID0001'}]):
            self.selection.write_text(json.dumps({'records':rows}))
            with self.assertRaises(exporter.ExportError):self.run_export()
            self.assertFalse(self.output.exists())

    def test_empty_ledger_yields_honest_zero_record_manifest(self):
        with sqlite3.connect(self.db) as con:con.execute('DELETE FROM artifacts')
        result,manifest,proof=self.run_export();self.assertEqual(result['verified'],0);self.assertEqual(manifest['records'],[]);self.assertEqual(proof['verified_artifacts'],[]);self.assertEqual(result['excluded'],1)

    def test_changed_source_during_probe_is_rejected(self):
        def mutation(path):path.write_bytes(b'changed during read');return self.probe
        with patch.object(exporter,'probe_media',side_effect=mutation):result=exporter.export_verified(self.db,self.selection,self.raw,self.output)
        self.assertEqual(result['verified'],0);proof=json.loads(Path(result['verification_receipt']['path']).read_text());self.assertIn('media_or_metadata_changed_during_verification',proof['excluded'][0]['reasons'])

    def test_stored_duration_and_height_bounds_rechecked(self):
        self.update_validation(video_height_limit=360)
        bad=copy.deepcopy(self.probe);bad['streams'][0]['height']=1080
        result,_,proof=self.run_export(bad);self.assertEqual(result['verified'],0);self.assertIn('actual_height_mismatch',proof['excluded'][0]['reasons'])
        self.output=self.root/'wrong-duration';bad=copy.deepcopy(self.probe);bad['format']['duration']='900'
        result,_,proof=self.run_export(bad);self.assertEqual(result['verified'],0);self.assertIn('actual_duration_mismatch',proof['excluded'][0]['reasons'])

    def test_declared_japanese_survives_export_and_english_only_asr_refuses(self):
        self.update_metadata(language='ja',subtitles={'en':[{'url':'https://caption.invalid/'}]})
        _,manifest,proof=self.run_export();row=manifest['records'][0]
        self.assertEqual(row['source_language'],'ja');self.assertEqual(proof['verified_artifacts'][0]['source_language'],'ja')
        self.assertEqual(row['source_language_status'],'declared')
        audio_spec=importlib.util.spec_from_file_location('batch_audio_language_check',Path(__file__).with_name('audio.py'))
        audio=importlib.util.module_from_spec(audio_spec);audio_spec.loader.exec_module(audio)
        with self.assertRaises(ValueError):audio.language_plan(row,{'language_mode':'english-only'},'en')

    def test_unknown_invalid_and_conflicting_languages_are_explicit_not_subtitle_guesses(self):
        for value,status in [(None,'missing'),('','missing'),('English','invalid'),(['ja','en'],'conflicting'),(123,'invalid')]:
            with self.subTest(value=value):
                self.update_metadata(language=value,subtitles={'en':[{'url':'https://caption.invalid/'}]})
                self.output=self.root/('language-'+str(len(list(self.root.glob('language-*')))))
                _,manifest,proof=self.run_export();row=manifest['records'][0]
                self.assertEqual(row['source_language'],'unknown');self.assertEqual(row['source_language_status'],status)
                self.assertEqual(proof['verified_artifacts'][0]['source_language_status'],status)


if __name__=='__main__':unittest.main()
