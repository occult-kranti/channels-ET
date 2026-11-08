import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('acquire_bashar',Path(__file__).with_name('acquire_bashar.py'))
B=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(B)

class RetainedCorpusTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.audio=self.root/'audio.mp3';self.audio.write_bytes(b'synthetic fixture audio')
        self.folder=self.root/'asr';self.folder.mkdir()
        self.rows=[{'id':1,'start':0.0,'end':5.0,'text':'A synthetic test sentence with a question?'}]
        (self.folder/'segments.jsonl').write_text(json.dumps(self.rows[0])+'\n')
        (self.folder/'transcript.txt').write_text(self.rows[0]['text']+'\n')
        (self.folder/'transcript.srt').write_text('1\n00:00:00,000 --> 00:00:05,000\n'+self.rows[0]['text']+'\n')
        self.pub={'source_id':'synthetic:test','fixture_only':True,'status':'completed',
            'source_kind':'independent_original_publisher_rss_audio','raw_local_path':str(self.audio),
            'bytes':self.audio.stat().st_size,'sha256':B.sha(self.audio),'duration_seconds':600,
            'enclosure_url':'https://example.org/audio.mp3'}
        protocol={'sourceId':self.pub['source_id'],'sourceUrl':self.pub['enclosure_url'],'audioSha256':self.pub['sha256']}
        self.rec={'sourceId':self.pub['source_id'],'fixture_only':True,'status':'completed','sourceKind':'publisher_original_audio',
            'transcribedScope':'full_decoded_audio','clipSeconds':None,'executionProtocol':protocol,
            'executionSignature':hashlib.sha256(json.dumps(protocol,sort_keys=True).encode()).hexdigest(),
            'sourceAudioPath':str(self.audio),'sourceAudioSha256':self.pub['sha256'],'sourceUrl':self.pub['enclosure_url'],
            'sourceAudioDurationSeconds':600,'segments':1,'words':len(self.rows[0]['text'].split()),
            'outputs':[{'name':n,'bytes':(self.folder/n).stat().st_size,'sha256':B.sha(self.folder/n)} for n in ('segments.jsonl','transcript.txt','transcript.srt')]}
        self.sync()
    def tearDown(self):self.temp.cleanup()
    def sync(self):
        (self.folder/'receipt.json').write_text(json.dumps(self.rec))
        self.summary=copy.deepcopy(self.rec)|{'transcriptDirectory':str(self.folder)}
    def validate(self):
        with patch.object(B,'probe_audio',return_value=600):return B.verify_pair(self.pub,self.summary,allow_fixtures=True)
    def test_exact_chain_control(self):
        result=self.validate();self.assertEqual(result['text'],self.rows[0]['text'])
    def test_fixture_not_actual(self):
        with self.assertRaisesRegex(ValueError,'Synthetic'):B.verify_pair(self.pub,self.summary)
    def test_source_identity_cannot_drift(self):
        self.pub['source_id']='synthetic:other'
        with self.assertRaisesRegex(ValueError,'identity'):self.validate()
    def test_changed_audio_is_rejected(self):
        self.audio.write_bytes(b'different same-length data')
        with self.assertRaisesRegex(ValueError,'bytes changed'):self.validate()
    def test_digest_is_not_transcript(self):
        self.rec['sourceKind']='AI_digest';self.sync()
        with self.assertRaisesRegex(ValueError,'not publisher-audio'):self.validate()
    def test_summary_cannot_promote_different_receipt(self):
        self.rec['status']='failed';(self.folder/'receipt.json').write_text(json.dumps(self.rec))
        with self.assertRaisesRegex(ValueError,'Summary differs'):self.validate()
    def test_protocol_tampering_is_rejected(self):
        self.rec['executionProtocol']['sourceUrl']='https://example.org/other.mp3';self.sync()
        with self.assertRaisesRegex(ValueError,'binding changed'):self.validate()
    def test_partial_clip_not_full_source(self):
        self.rec['clipSeconds']=60;self.sync()
        with self.assertRaisesRegex(ValueError,'partial'):self.validate()
    def test_changed_transcript_hash_rejected(self):
        (self.folder/'transcript.txt').write_text('changed\n')
        with self.assertRaisesRegex(ValueError,'bytes changed'):self.validate()
    def test_claimed_count_recomputed(self):
        self.rec['words']+=1;self.sync()
        with self.assertRaisesRegex(ValueError,'counts differ'):self.validate()
    def test_unsafe_private_path(self):
        link=self.root/'link';link.symlink_to(self.folder,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Symlink'):B.private_path(link/'transcript.txt')
    def test_only_linked_handout_origin_and_dedup(self):
        url='https://d11n7da8rpqbjy.cloudfront.net/basharet/a.pdf'
        rows=B.handout_links(f'<a href="{url}">One</a><a href="{url}">Two</a><a href="https://other.example/a.pdf">No</a><a href="javascript:alert(1)">No</a>')
        self.assertEqual(rows,[{'source_url':url,'title':'One'}])
    def test_public_urls_drop_credentials_and_queries(self):
        self.assertEqual(B.safe_url('https://example.org/a?token=not-real#x'),'https://example.org/a')
        self.assertIsNone(B.safe_url('https://user:pass@example.org/a'))
    def test_official_body_strips_repeated_navigation_and_script(self):
        html='<head><title>Site</title></head><nav>Teaching</nav><script>not body</script><h1>Teaching</h1><p>Actual first paragraph.</p><p>Actual second paragraph.</p><footer>© Publisher</footer>'
        text,method=B.official_body(html,'Teaching')
        self.assertEqual(text,'Teaching\nActual first paragraph.\nActual second paragraph.')
        self.assertEqual(method['visible_text_start_index'],1)
    def test_official_body_refuses_unbounded_template(self):
        with self.assertRaisesRegex(ValueError,'footer boundary'):
            B.official_body('<h1>Teaching</h1><p>Text with no expected footer.</p>','Teaching')
    def test_handout_plan_cannot_add_unlinked_pdf(self):
        listing=self.root/'listing.html';listing.write_text('<a href="https://d11n7da8rpqbjy.cloudfront.net/basharet/a.pdf">One</a>')
        plan=self.root/'plan.json';plan.write_text(json.dumps({'source_page':{'final_url':'https://www.bashar.org/handouts','status':200,'local_path':str(listing),'bytes':listing.stat().st_size,'sha256':B.sha(listing)},'records':[{'source_url':'https://d11n7da8rpqbjy.cloudfront.net/basharet/hidden.pdf','title':'Two','head_status':200,'declared_bytes':10}]}))
        with patch.object(B,'urlopen',side_effect=AssertionError('No network allowed')):
            with self.assertRaisesRegex(ValueError,'exact linked PDF frame'):
                B.download_handouts(plan,self.root/'new')

class VimeoBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.info={'id':'392834325','uploader_id':'basharcommunications','duration':422,
            'formats':[{'vcodec':'none','format_id':'hls-fastly_skyfire-audio-high-Original'}]}
        self.profile={'entries':[{'id':'392834325'}]}
        self.oembed={'video_id':392834325,'duration':422,'author_url':'https://vimeo.com/basharcommunications',
            'html':'<iframe src="https://player.vimeo.com/video/392834325?app_id=122963"></iframe>'}
    def test_three_independent_metadata_links_agree(self):
        self.assertEqual(B.validate_vimeo_pilot(self.info,self.profile,self.oembed)[0],'392834325')
    def test_unlisted_video_does_not_inherit_publisher_identity(self):
        with self.assertRaisesRegex(ValueError,'retained publisher profile'):
            B.validate_vimeo_pilot(self.info,{'entries':[]},self.oembed)
    def test_wrong_author_is_rejected(self):
        self.oembed['author_url']='https://vimeo.com/unverified'
        with self.assertRaisesRegex(ValueError,'publisher identity'):
            B.validate_vimeo_pilot(self.info,self.profile,self.oembed)
    def test_short_clip_is_not_admitted(self):
        self.info['duration']=299
        with self.assertRaisesRegex(ValueError,'five-minute'):
            B.validate_vimeo_pilot(self.info,self.profile,self.oembed)
    def test_non_audio_format_is_not_admitted(self):
        self.info['formats'][0]['vcodec']='h264'
        with self.assertRaisesRegex(ValueError,'audio-only'):
            B.validate_vimeo_pilot(self.info,self.profile,self.oembed)
    def test_unlinked_player_is_not_admitted(self):
        self.oembed['html']=''
        with self.assertRaisesRegex(ValueError,'public oEmbed|Public oEmbed'):
            B.validate_vimeo_pilot(self.info,self.profile,self.oembed)

class CaptionBoundaryTests(unittest.TestCase):
    def test_webvtt_retains_ordered_times_and_unescapes_text(self):
        value=B.parse_vtt(b'WEBVTT\n\ncue-1\n00:00:10.000 --> 00:00:12.000 align:start\n<v Speaker>A &amp; B</v>\n\n00:12.000 --> 00:13.000\nSecond cue\n',300)
        self.assertEqual(value,[{'start_seconds':10.,'end_seconds':12.,'text':'A & B'},{'start_seconds':12.,'end_seconds':13.,'text':'Second cue'}])
    def test_caption_cannot_extend_beyond_its_public_excerpt(self):
        with self.assertRaisesRegex(ValueError,'outside the public excerpt'):
            B.parse_vtt(b'WEBVTT\n\n00:00:10.000 --> 00:10:12.000\nText\n',300)
    def test_html_response_is_not_a_caption(self):
        with self.assertRaisesRegex(ValueError,'WebVTT'):
            B.parse_vtt(b'<html>login</html>',300)
    def test_caption_requires_nonempty_valid_cues(self):
        with self.assertRaisesRegex(ValueError,'No caption'):
            B.parse_vtt(b'WEBVTT\n\nNOTE empty file\n',300)

class FrameBudgetTests(unittest.TestCase):
    def setUp(self):
        self.frame={'records':[{'video_id':'123','status':'retrieved','duration_seconds':300}]}
        self.plan={'records':[{'video_id':'123','planning_max_bytes':100}]}
    def test_exact_finite_frame_and_caps_pass(self):
        self.assertEqual(set(B.validate_vimeo_frame(self.frame,self.plan,100)[0]),{'123'})
    def test_traversal_id_is_rejected_before_output_creation(self):
        self.frame['records'][0]['video_id']='../escape'
        with self.assertRaisesRegex(ValueError,'numeric Vimeo IDs'):
            B.validate_vimeo_frame(self.frame,self.plan,100)
    def test_negative_or_boolean_caps_cannot_reduce_total_budget(self):
        for value in (-10,True,101):
            self.plan['records'][0]['planning_max_bytes']=value
            with self.subTest(value=value),self.assertRaisesRegex(ValueError,'positive bounded'):
                B.validate_vimeo_frame(self.frame,self.plan,100)
    def test_missing_frame_entry_is_rejected(self):
        self.plan['records']=[]
        with self.assertRaisesRegex(ValueError,'equal the inspected frame'):
            B.validate_vimeo_frame(self.frame,self.plan,100)
    def test_nonfinite_metadata_duration_is_rejected(self):
        self.frame['records'][0]['duration_seconds']=float('nan')
        with self.assertRaisesRegex(ValueError,'unavailable or short'):
            B.validate_vimeo_frame(self.frame,self.plan,100)

if __name__=='__main__':unittest.main()
