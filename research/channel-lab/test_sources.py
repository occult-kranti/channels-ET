import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('channel_sources',Path(__file__).with_name('sources.py'))
S=importlib.util.module_from_spec(spec);spec.loader.exec_module(S)


def row(i, channel='a', text=None, url=None, priority=20):
    text=text or ('different body '+str(i))
    return {'edition_id':'ed-'+str(i),'cohort':'test','priority':priority,'channel_id':channel,'channel_name':channel,
        'creator_id':'creator-'+channel,'creator_name':channel,'publisher_id':'publisher-'+channel,'publisher_name':channel,
        'body_sha256':S.sha_bytes(text.encode()),'words':len(text.split()),'publication_url':url,
        'publication_id':'1','recording_family_id':None,'audio_sha256':None,'media_artifact':None,'duration_seconds':None,
        'text_artifact':{'sha256':S.sha_bytes(text.encode()),'bytes':len(text)},'text_origin':'test',
        'document_kind':'publisher_written','claimed_label':None,'legacy_source_ids':['ed-'+str(i)]}


class SourcesTest(unittest.TestCase):
    def test_publisher_local_id_collision_not_joined(self):
        records,_,_=S.reconcile([row(1,'a'),row(2,'b')])
        self.assertEqual(len(records),2)

    def test_exact_body_cross_context_keeps_all_attributions(self):
        records,editions,links=S.reconcile([row(1,'a','same body'),row(2,'b','same body')])
        self.assertEqual(len(records),1);self.assertTrue(records[0]['cross_context_alias'])
        self.assertEqual({x['channel_id'] for x in records[0]['original_contexts']},{'a','b'})
        self.assertEqual(len(editions),2);self.assertTrue(any(x['basis']=='body_sha256' for x in links))

    def test_written_preference_one_unit_multiple_editions(self):
        a=row(1,url='https://example.org/message',priority=20)
        b=row(2,url='https://example.org/message',priority=5)
        records,editions,_=S.reconcile([a,b])
        self.assertEqual(records[0]['selected_edition_id'],'ed-2')
        self.assertEqual(len(editions),2);self.assertEqual(sum(x['selected'] for x in editions),1)

    def test_url_normalization_preserves_query_identity_and_path_case(self):
        self.assertEqual(S.canonical_url('https://EXAMPLE.org/One/%e2%88%9e/?p=1#frag'),'https://example.org/One/%E2%88%9E?p=1')
        self.assertNotEqual(S.canonical_url('https://example.org/?p=1'),S.canonical_url('https://example.org/?p=2'))

    def test_encoded_video_not_encoded_audio(self):
        a=row(1);a.update(document_kind='video_asr',audio_sha256='a'*64,media_artifact={'sha256':'a'*64})
        records,editions,_=S.reconcile([a]);r=records[0]
        self.assertIsNone(r['audio_sha256']);self.assertEqual(r['media_hash_kind'],'encoded_video_file')
        self.assertEqual(r['recording_id'],'media-sha256:'+'a'*64)
        self.assertIsNone(editions[0]['audio_sha256'])

    def test_private_loader_rejects_artifact_tamper(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'body.txt';p.write_text('Hello world')
            ref=S.artifact(p);self.assertEqual(S.body(ref,'plain_text'),'Hello world')
            p.write_text('Hello altered world')
            with self.assertRaises(ValueError):S.body(ref,'plain_text')

    def test_json_html_transform_then_unicode_normalization(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'source.json';p.write_text(json.dumps({'text':'  <i>Ａ &amp; B</i>  '}))
            self.assertEqual(S.body(S.artifact(p),'json_text_html_clean'),'A & B')

    def test_public_projection_cannot_export_private_artifact_paths(self):
        a=row(1);a['text_artifact']['path']='/private/body.txt';a['body_transform']='plain_text'
        a['media_artifact']={'path':'/private/audio.opus','sha256':'b'*64,'probe':{'filename':'/private/audio.opus'}}
        projected=S.public_record(a)
        self.assertNotIn('/private/',json.dumps(projected));self.assertNotIn('body_transform',projected)


if __name__=='__main__':unittest.main()
