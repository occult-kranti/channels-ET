import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

SPEC=importlib.util.spec_from_file_location('bashar_ra_analysis',Path(__file__).with_name('analyze.py'))
A=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(A)

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def file(self,name,value):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True)
        if isinstance(value,(dict,list)):p.write_text(json.dumps(value))
        elif isinstance(value,bytes):p.write_bytes(value)
        else:p.write_text(value)
        return {'path':str(p),'bytes':p.stat().st_size,'sha256':A.sha(p)}
    def record(self,sid='fixture:one',kind='authored_reference',corpus='bashar',text=None):
        text=text or ('consciousness freedom choice body love learning reality evidence uncertainty ' * 6)
        doc={'source_id':sid,'text':text,'turns':[]}
        artifact=self.file(sid.replace(':','_')+'.json',doc)
        source=self.file(sid.replace(':','_')+'.html','<main>'+text+'</main>')
        return {'source_id':sid,'corpus':corpus,'session_id':sid,'duplicate_family_id':sid,'edition_id':'fixture-edition',
            'source_kind':kind,'source_format':'synthetic_fixture','title':sid,'source_url':'https://example.org/source?tracking=private',
            'published_at':'2001-01-01','language':'en','collection_status':'retrieved','coverage_status':'full',
            'text_artifact':artifact,'evidence':[{**source,'role':'source'}]},doc
    def manifest(self,rows,fixture=True):return Path(self.file('manifest.json',{'schema_version':1,'fixture_only':fixture,'records':rows})['path'])
    def load(self,rows,**kwargs):return A.load_manifests([self.manifest(rows)],allow_fixtures=True,**kwargs)
    def test_actual_mode_rejects_fixture_chain(self):
        row,_=self.record()
        with self.assertRaisesRegex(ValueError,'Synthetic'):A.load_manifests([self.manifest([row])])
    def test_full_reference_admitted_without_fabricated_qa(self):
        row,_=self.record();docs,excluded,aliases,_=self.load([row]);self.assertEqual(len(docs),1);self.assertFalse(excluded or aliases)
        pairs,candidates,counts=A.qa_records(docs[0]);self.assertFalse(pairs or candidates);self.assertEqual(counts['verified_substantive_questions'],0)
    def test_partial_source_explicitly_excluded(self):
        row,_=self.record();row['coverage_status']='partial';docs,excluded,_,_=self.load([row]);self.assertFalse(docs);self.assertEqual(excluded[0]['reason'],'not_full_retained_text')
    def test_declared_expected_source_set_requires_explicit_rows(self):
        row,_=self.record();manifest=self.manifest([row]);value=json.loads(manifest.read_text())
        value['expected_source_ids']=[row['source_id'],'fixture:missing'];manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'expected source set'):A.load_manifests([manifest],allow_fixtures=True)
        value['expected_source_ids']=[row['source_id'],row['source_id']];manifest.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'unique valid list'):A.load_manifests([manifest],allow_fixtures=True)
        value['expected_source_ids']=[row['source_id']];value['records'][0]['coverage_status']='partial';manifest.write_text(json.dumps(value))
        docs,excluded,_,_=A.load_manifests([manifest],allow_fixtures=True);self.assertFalse(docs);self.assertEqual(len(excluded),1)
    def test_missing_and_modified_evidence_fail(self):
        row,_=self.record();Path(row['evidence'][0]['path']).write_text('changed')
        with self.assertRaisesRegex(ValueError,'size changed'):self.load([row])
    def test_normalized_identity_and_turn_join_must_match(self):
        row,doc=self.record();doc['turns']=[{'turn_id':'1','role':'unknown','text':'different'}];row['text_artifact']=self.file('changed.json',doc)
        with self.assertRaisesRegex(ValueError,'ordered turns'):self.load([row])
    def test_nonenglish_exclusion(self):
        row,_=self.record();row['language']='hi';self.assertEqual(self.load([row])[1][0]['reason'],'not_declared_English')
    def test_duplicate_ids_conflicting_text_fail(self):
        a,_=self.record();b,_=self.record('fixture:two',text='different private text astronomy planet alignment orbit ' * 8);b['source_id']=a['source_id']
        value=json.loads(Path(b['text_artifact']['path']).read_text());value['source_id']=a['source_id'];b['text_artifact']=self.file('variant.json',value)
        with self.assertRaisesRegex(ValueError,'conflicting editions'):self.load([a,b])
    def test_exact_text_alias_does_not_inflate_sample(self):
        a,_=self.record();b,_=self.record('fixture:two');docs,_,aliases,_=self.load([a,b]);self.assertEqual(len(docs),1);self.assertEqual(aliases[0]['reason'],'exact_text_duplicate')
    def test_multiple_session_editions_fail(self):
        a,_=self.record();b,_=self.record('fixture:two',text='different private astronomy orbit planet alignment ' * 8);b['session_id']=a['session_id']
        with self.assertRaisesRegex(ValueError,'Multiple text editions'):self.load([a,b])
    def test_upstream_fixture_marker_cannot_be_lost(self):
        row,_=self.record();row['evidence']=[{**self.file('proof.json',{'fixture_only':True}),'role':'source'}]
        with self.assertRaisesRegex(ValueError,'Fixture marker'):A.load_manifests([self.manifest([row],fixture=False)])
    def test_url_strips_query_credentials_and_nonhttp(self):
        self.assertEqual(A.safe_url('https://example.org/a?token=x#part'),'https://example.org/a')
        self.assertIsNone(A.safe_url('https://name:password@example.org/a'));self.assertIsNone(A.safe_url('file:///private'))
    def test_private_text_cannot_be_inside_git_or_symlink(self):
        p=self.root/'checkout';p.mkdir();(p/'.git').mkdir();(p/'.git'/'HEAD').write_text('ref: refs/heads/main');(p/'text').write_text('data')
        with self.assertRaisesRegex(ValueError,'outside Git'):A.safe_path(p/'text',private=True)
        link=self.root/'link';link.symlink_to(p/'text')
        with self.assertRaisesRegex(ValueError,'Symlink'):A.safe_path(link)
    def test_publisher_extraction_must_bind_exact_normalized_text(self):
        row,doc=self.record(kind='publisher_transcript',corpus='ra')
        receipt={'source_id':row['source_id'],'edition_id':row['edition_id'],'source':row['evidence'][0],
            'normalized':row['text_artifact'],'turns':0,'whitespace_words':len(doc['text'].split())}
        row['evidence'].append({**self.file('extract.json',receipt),'role':'extraction_receipt'})
        self.assertEqual(len(self.load([row])[0]),1)
        receipt=json.loads(json.dumps(receipt));receipt['normalized']['sha256']='0'*64;row['evidence'][-1]={**self.file('extract.json',receipt),'role':'extraction_receipt'}
        with self.assertRaisesRegex(ValueError,'normalized artifact differs'):self.load([row])
    def test_asr_without_completed_source_proof_is_refused(self):
        row,_=self.record(kind='machine_asr')
        with self.assertRaisesRegex(ValueError,'completed ASR receipt'):self.load([row])

class MeasurementTests(unittest.TestCase):
    def doc(self,text,corpus='ra',kind='publisher_transcript',turns=None):
        return {'summary':{'source_id':'test:'+corpus,'session_id':'test:'+corpus,'corpus':corpus,'source_kind':kind},'text':text,'tokens':A.tokens(text),'turns':turns or []}
    def test_keywords_count_forms_not_claim_truth(self):
        rates=A.keyword_rates(A.tokens('Not love; love is quoted. No fear.'))
        self.assertEqual(rates['relationships']['mentions'],2);self.assertEqual(rates['fear']['mentions'],1)
    def test_format_sensitivity_matches_actual_publisher_metadata(self):
        docs=[{'summary':{'source_format':f}} for f in ('interview','skeptical_commentary','publisher_promotional_interview',None)]
        self.assertEqual(A.exclude_promotional_commentary(docs),[docs[0],docs[3]])
    def test_placeholder_and_orphan_qa_are_preserved_as_such(self):
        turns=[{'turn_id':'a','role':'response','text':'A source introduction?','question_id':'1.0'},
            {'turn_id':'b','role':'questioner','text':'[Question lost]','question_id':'1.1'},
            {'turn_id':'c','role':'response','text':'Published response.','question_id':'1.1'},
            {'turn_id':'d','role':'questioner','text':'Thank you.','question_id':'1.2'},
            {'turn_id':'e','role':'response','text':'Acknowledged.','question_id':'1.2'}]
        pairs,candidates,q=A.qa_records(self.doc('\n'.join(t['text'] for t in turns),turns=turns))
        self.assertEqual(len(pairs),2);self.assertEqual(q['publisher_pairs_with_missing_question_text'],1)
        self.assertEqual(q['responses_without_present_questioner_turn'],1);self.assertEqual(q['publisher_prompts_with_question_mark'],0);self.assertFalse(candidates)
    def test_asr_following_context_not_called_answer(self):
        turns=[{'turn_id':'a','role':'unknown','text':'What do you mean?'},{'turn_id':'b','role':'unknown','text':'A possible continuation.'}]
        pairs,candidates,q=A.qa_records(self.doc('x','bashar','machine_asr',turns));self.assertFalse(pairs);self.assertFalse(candidates[0]['answer_identified'])
    def test_mismatched_question_ids_do_not_pair(self):
        turns=[{'turn_id':'a','role':'questioner','question_id':'1.1','text':'Why?'},{'turn_id':'b','role':'response','question_id':'1.2','text':'Something.'}]
        self.assertEqual(A.qa_records(self.doc('x',turns=turns))[2]['unpaired_publisher_prompts'],1)
    def test_short_documents_excluded_only_from_length_sensitivity(self):
        doc=self.doc('truth consciousness freedom '*100)
        self.assertTrue(A.token_variant(doc,'raw'));self.assertFalse(A.token_variant(doc,'matched_length'))
    def test_name_mask_preserves_negation_and_unrelated_wordforms(self):
        out=A.token_variant(self.doc('Ra does not prove gratitude or knowledge'),'name_masked')
        self.assertNotIn('ra',out);self.assertIn('not',out);self.assertIn('gratitude',out)
    def test_semantic_mask_preserves_straight_and_curly_contractions(self):
        contractions="don't don’t we'll we’ll I'll I’ll you'll you’ll won't wouldn't isn't aren't never no not y'all'll wouldn't've"
        self.assertEqual(A.mask_source_markers(contractions),contractions)
        self.assertEqual(A.mask_source_markers('Don LL Ra Bashar Darryl Anka'), '           ')
        self.assertEqual(A.mask_source_markers("Don's researcher's radar llama"),"Don's researcher's radar llama")
        self.assertEqual(A.mask_source_markers('RA/LL; Don.'),' / ;  .')
    def test_bracket_sensitivity_does_not_mutate_source(self):
        doc=self.doc('There is [editorial addition] a spiritual claim.');before=doc['text'];out=A.token_variant(doc,'bracket_removed')
        self.assertNotIn('editorial',out);self.assertEqual(doc['text'],before)
    def test_lexical_scores_do_not_use_context_labels_to_fit(self):
        docs=[self.doc(('choice body learning contact '+str(i)+' ')*25,corpus='ra' if i%2 else 'bashar') for i in range(6)]
        for i,d in enumerate(docs):d['summary']['source_id']='test:'+str(i)
        a,_,_,_=A.fit_lexical(docs,'name_masked')
        for d in docs:d['summary']['corpus']='bashar' if d['summary']['corpus']=='ra' else 'ra'
        b,_,_,_=A.fit_lexical(docs,'name_masked')
        np.testing.assert_array_equal(a['cosine_matrix'],b['cosine_matrix'])
    def test_empty_vocabulary_abstains(self):
        docs=[self.doc('the and of '*20),self.doc('the and of '*20)]
        self.assertEqual(A.fit_lexical(docs,'content')[0]['status'],'empty_vocabulary')
    def test_network_has_no_self_edges_or_duplicate_edges(self):
        docs=[self.doc('x',corpus='ra'),self.doc('y',corpus='bashar')]
        for i,d in enumerate(docs):d['summary'].update(source_id=str(i),short_id=str(i))
        net=A.network({'source_ids':['0','1'],'cosine_matrix':[[1,.4],[.4,1]]},docs)
        self.assertEqual(len(net['edges']),1);self.assertTrue(net['edges'][0]['cross_corpus'])
    def test_near_duplicate_scores_are_flags_not_removals(self):
        docs=[self.doc('one two three four five six seven eight'),self.doc('one two three four five six seven eight nine')]
        docs[0]['summary']['source_id']='first';docs[1]['summary']['source_id']='second'
        result=A.near_duplicate_diagnostics(docs);self.assertEqual(result['pairs_checked'],1)
        self.assertEqual(len(result['flagged_pairs']),1);self.assertEqual(result['flagged_pairs'][0]['smaller_document_shingle_containment'],1)
        self.assertEqual(len(docs),2)
    def test_sqlite_preserves_units_and_candidate_status(self):
        with tempfile.TemporaryDirectory() as root:
            doc=self.doc('Some text','bashar','machine_asr',[{'turn_id':'1','role':'unknown','text':'Some text'}]);doc['summary']['title']='Fixture'
            counts=A.sqlite_qa(Path(root)/'q.sqlite',[doc],[],[]);self.assertEqual(counts['documents'],1);self.assertEqual(counts['publisher_prompt_response_pairs'],0)

@unittest.skipUnless(Path('/workspace/channels-et-private/bashar-ra-2026-11/model-cache/minilm-1110a243/manifest.json').is_file(),'Pinned local model not available; no download is triggered by tests')
class LocalEncoderTests(unittest.TestCase):
    def test_full_coverage_tail_cache_and_tampering(self):
        with tempfile.TemporaryDirectory() as root:
            enc=A.FrozenEncoder('/workspace/channels-et-private/bashar-ra-2026-11/model-cache/minilm-1110a243',Path(root))
            text='science astronomy biology learning ' * 170+'unique terminal phrase'
            out=enc.encode([('full',text),('alias',text)]);self.assertEqual(out['full'][2]['truncated_content_wordpieces'],0)
            self.assertGreater(out['full'][2]['content_wordpieces'],512);self.assertGreater(out['full'][2]['chunks'],2)
            np.testing.assert_array_equal(out['full'][0],out['alias'][0]);self.assertAlmostEqual(float(np.linalg.norm(out['full'][0])),1,places=5)
            reused=enc.encode([('full',text)]);np.testing.assert_allclose(out['full'][0],reused['full'][0],atol=1e-7)
            path=next(Path(root).glob('*.npz'));path.write_bytes(b'corrupted')
            with self.assertRaisesRegex(ValueError,'cache binding'):enc.encode([('full',text)])

if __name__=='__main__':unittest.main()
