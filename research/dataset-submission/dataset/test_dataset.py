#!/usr/bin/env python3
"""Semantic and source-binding release tests; no network or model inference."""
import hashlib, importlib.util, json, sqlite3, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('dataset_builder',Path(__file__).with_name('build_dataset.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
P=Path('/workspace/channels-et-private/dataset-submission-2026-11')

class Semantics(unittest.TestCase):
    def test_same_article_whitespace_only_merges(self):
        old={'publication_url':'https://omna.org/example/','selected_edition_id':'old'}
        new={'publication_url':'https://omna.org/example','selected_edition_id':'new'}
        self.assertIsNotNone(b.edition_link(old,new,'one\n\ntwo','one two'))
    def test_same_article_semantic_change_requires_review(self):
        with self.assertRaises(ValueError):b.edition_link({'publication_url':'https://omna.org/example','selected_edition_id':'old'},{'publication_url':'https://omna.org/example','selected_edition_id':'new'},'one three','one two')
    def test_container_url_cannot_merge(self):
        old={'publication_url':'https://omna.org/','selected_edition_id':'old'}
        self.assertIsNone(b.edition_link(old,dict(old,selected_edition_id='new'),'same','same'))
    def test_same_body_different_publication_not_url_merge(self):
        self.assertIsNone(b.edition_link({'publication_url':'https://omna.org/one','selected_edition_id':'old'},{'publication_url':'https://omna.org/two','selected_edition_id':'new'},'same','same'))

@unittest.skipUnless((P/'frame.json').exists(),'Private source artifacts required for release integration checks')
class Release(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.frame=b.read(P/'frame.json');cls.public=b.read(ROOT/'dist/dataset-submission/dataset.json')
    def test_full_selected_artifact_rehash_and_selection(self):
        rows=b.load_sources().load_frame(P/'frame.json');self.assertEqual(len(rows),683);self.assertEqual(sum(x['record']['words']for x in rows),1599556)
        for r in self.frame['records']:
            selected=[e for e in self.frame['alternate_editions']if e['source_id']==r['source_id']and e['selected']]
            self.assertEqual(len(selected),1);self.assertEqual(selected[0]['edition_id'],r['selected_edition_id']);self.assertEqual(selected[0]['body_sha256'],r['body_sha256'])
    def test_public_private_document_join_exact(self):
        self.assertEqual(self.public['documents'],[b.public_record(r)for r in self.frame['records']])
        self.assertEqual(self.public['frame_sha256'],hashlib.sha256((P/'frame.json').read_bytes()).hexdigest())
    def test_census_unknowns_not_zero(self):
        self.assertIsNone(self.public['summary']['youtube_uploaded_total'])
        self.assertTrue(all(c['youtube_uploaded_total']is None for c in self.public['channels']))
        self.assertEqual(self.public['summary']['youtube_downloads'],0)
        accounts=[json.loads(s)for s in (ROOT/'dist/dataset-submission/youtube-accounts.jsonl').read_text().splitlines()]
        videos=[json.loads(s)for s in (ROOT/'dist/dataset-submission/youtube-videos.jsonl').read_text().splitlines()]
        self.assertEqual(len(accounts),297);self.assertEqual(len(videos),2812)
        self.assertEqual(len({v['video_id']for v in videos}),2812)
        refs=[json.loads(s)for s in (ROOT/'dist/dataset-submission/youtube-account-video-links.jsonl').read_text().splitlines()]
        self.assertTrue(all(r['account_id']in {a['account_id']for a in accounts}and r['video_id']in {v['video_id']for v in videos}for r in refs))
    def test_media_and_editions_have_valid_sources(self):
        ids={r['source_id']for r in self.frame['records']}
        self.assertTrue(all(m['source_id']in ids for m in self.public['media']))
        self.assertTrue(all(e['source_id']in ids for e in self.public['text_editions']))
        self.assertEqual(len(self.public['text_editions']),694)
        self.assertEqual(sum(e['selected']for e in self.public['text_editions']),683)
        self.assertEqual(len(self.public['new_merge_links']),2)
    def test_sqlite_bodies_equal_frame(self):
        db=sqlite3.connect(P/'corpus.sqlite');self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        rows=db.execute('SELECT source_id,body_sha256,words,text FROM documents').fetchall();db.close()
        self.assertEqual(len(rows),683)
        for sid,digest,words,text in rows:
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),digest);self.assertEqual(len(text.split()),words)
    def test_no_public_raw_text_or_private_path(self):
        for p in (ROOT/'dist/dataset-submission').glob('*'):
            if p.suffix not in {'.json','.jsonl','.csv'}:continue
            raw=p.read_text()
            for marker in ['/workspace/','/dev/shm/','/tmp/','"text":']:self.assertNotIn(marker,raw,str(p))

if __name__=='__main__':unittest.main()
