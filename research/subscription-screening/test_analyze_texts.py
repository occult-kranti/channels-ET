import copy,hashlib,json,tempfile,unittest
from pathlib import Path
import analyze_texts as S

class SourceAdmissionTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def artifact(self,name,value):
        p=self.root/name;p.write_bytes(value if isinstance(value,bytes) else (json.dumps(value).encode() if not isinstance(value,str) else value.encode()))
        return {'path':str(p),'bytes':p.stat().st_size,'sha256':S.A.sha(p)}
    def fixture(self,fmt='srt'):
        sid='publisher:'+fmt
        if fmt=='srt':
            raw=self.artifact('source.srt',b'1\n00:00:01,000 --> 00:00:03,000\nA complete source question?\n');turns=S.parse_srt(Path(raw['path']).read_bytes());ex={'cues':1}
        else:
            raw=self.artifact('source.pdf',b'%PDF-1.4\nfixture');ex={'pages_reported':2,'extracted_artifact':self.artifact('extracted.txt','Page one\fPage two\f'),'pdfinfo_artifact':self.artifact('info.txt','Pages: 2\n')};turns=S.pdf_pages('Page one\fPage two\f',2)
        text='\n'.join(t['text'] for t in turns);norm=self.artifact('normalized.json',{'source_id':sid,'text':text,'turns':turns})
        rec={'source_id':sid,'status':200,'raw_artifact':raw,'normalized_artifact':norm,'extraction':ex,'received_bytes':raw['bytes']};receipt=self.artifact('receipt.json',rec)
        row={'source_id':sid,'coverage_status':'complete_text_extraction_unvalidated','raw_artifact':raw,'text_artifact':norm,'evidence':[receipt],'extraction':ex,'source_format':fmt,'duration_seconds_publisher':10,'turn_count':len(turns),'whitespace_words':len(text.split()),'text_content_sha256':hashlib.sha256(text.encode()).hexdigest(),'medium_id':'tracy_kumbera','source_kind':'publisher_hosted_caption_origin_unverified','language':'en','source_url':'https://example.com/source?secret=omit','download_url':'https://example.com/source.srt?secret=omit'}
        acq=self.artifact('acquisition.json',{'records':[row]});manifest={'schema_version':1,'records':[row],'counts':{'requested':1,'whitespace_words':len(text.split())},'acquisition_manifest':acq};path=Path(self.artifact('manifest.json',manifest)['path']);return path,manifest,row
    def test_source_srt_and_pdf_are_reconstructed_from_bound_artifacts(self):
        for fmt in ('srt','pdf'):
            p,_,_=self.fixture(fmt);docs,audit=S.load_manifest(p,expected_count=1);self.assertEqual(len(docs),1);self.assertNotIn('secret',docs[0]['summary']['source_url'])
    def test_partial_frame_is_not_silent_success(self):
        p,_,_=self.fixture()
        with self.assertRaisesRegex(ValueError,'complete source-frame'):S.load_manifest(p,expected_count=2)
    def test_source_artifact_tampering_fails(self):
        p,m,row=self.fixture();Path(row['raw_artifact']['path']).write_text('corrupt')
        with self.assertRaisesRegex(ValueError,'artifact (size|hash)'):S.load_manifest(p,expected_count=1)
    def test_changed_normalization_fails_even_with_rebound_metadata(self):
        p,m,row=self.fixture();n=json.loads(Path(row['text_artifact']['path']).read_text());n['text']='changed';norm=self.artifact('normalized.json',n);row['text_artifact']=norm
        rec=json.loads(Path(row['evidence'][0]['path']).read_text());rec['normalized_artifact']=norm;row['evidence']=[self.artifact('receipt.json',rec)];m['acquisition_manifest']=self.artifact('acquisition.json',{'records':[row]});p.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'Normalized text differs'):S.load_manifest(p,expected_count=1)
    def test_fixture_flag_is_rejected(self):
        p,m,_=self.fixture();m['fixture_only']=True;p.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError,'Fixture input'):S.load_manifest(p,expected_count=1)
    def test_nonenglish_transcripts_and_references_are_retained_but_not_modeled(self):
        p,m,row=self.fixture();row['language']='pt';p.write_text(json.dumps(m));docs,_=S.load_manifest(p,expected_count=1);self.assertFalse(docs[0]['summary']['primary_eligible'])
        row['language']='en';row['source_kind']='third_party_republished_reference_pdf';p.write_text(json.dumps(m));docs,_=S.load_manifest(p,expected_count=1);self.assertFalse(docs[0]['summary']['primary_eligible'])

class TransformTests(unittest.TestCase):
    def test_caption_body_is_preserved_in_source_and_cleaned_only_for_analysis(self):
        raw=b'1\n00:00:00,000 --> 00:00:01,000\n<i>Don\'t &amp; change</i>\n';rows=S.parse_srt(raw);self.assertIn('<i>',rows[0]['text']);self.assertEqual(S.clean_text(rows[0]['text'],'srt'),"Don't & change")
    def test_invalid_srt_clock_order_or_hidden_block_fails(self):
        for raw in (b'1\n00:75:00,000 --> 01:00:00,000\nBad',b'1\n00:00:02,000 --> 00:00:01,000\nBad',b'1\n00:00:00,000 --> 00:00:01,000\nFine\n\nUndecoded block'):
            with self.assertRaises(ValueError):S.parse_srt(raw)
    def test_pdf_page_boundary_is_not_silently_dropped(self):
        with self.assertRaisesRegex(ValueError,'page-count'):S.pdf_pages('page1\fpage2\f',1)
    def test_name_mask_preserves_negative_and_future_contractions(self):
        text="don't don’t we'll we’ll Tracy Magenta";self.assertEqual(S.mask(text),"don't don’t we'll we’ll    ")
    def test_source_window_retains_numbers_and_punctuation(self):
        text='Prefix Alpha, 123 beta? Gamma suffix End';doc={'text':text,'tokens':S.A.tokens(text)};self.assertEqual(S.window(doc,4),'Alpha, 123 beta? Gamma suffix');self.assertIsNone(S.window(doc,99))
    def test_exact_caption_duplicate_does_not_claim_audio_identity(self):
        docs=[]
        for sid in ('a','b'):
            docs.append({'summary':{'source_id':sid,'corpus':'tracy_kumbera','source_format':'srt','source_artifact_sha256':'a'*64,'primary_eligible':True},'raw_text':'same'})
        units,aliases=S.collapse_exact_text(docs);self.assertEqual(len(units),1);self.assertEqual(len(docs),2);self.assertIn('audio identity',aliases[0]['basis']);self.assertFalse(docs[1]['summary']['included_in_model'])
    def test_same_bytes_cannot_hide_inconsistent_extraction(self):
        docs=[{'summary':{'source_id':sid,'corpus':'x','source_format':'srt','source_artifact_sha256':'a'*64,'primary_eligible':True},'raw_text':sid} for sid in ('a','b')]
        with self.assertRaisesRegex(ValueError,'different text'):S.collapse_exact_text(docs)
if __name__=='__main__':unittest.main()
