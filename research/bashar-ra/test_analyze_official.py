import json
from pathlib import Path
import tempfile
import unittest
import analyze_official as S


class OfficialEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def artifact(self,name,value,role):
        p=self.root/name
        p.write_text(json.dumps(value) if isinstance(value,dict) else value)
        return {'path':str(p),'bytes':p.stat().st_size,'sha256':S.A.sha(p),'role':role}
    def record(self):
        sid='vimeo:123:captions:en-x-autogen';text=' '.join(['synthetic fixture consciousness choice physical reality meditation']*6)
        vtt=self.artifact('source.vtt','WEBVTT\n\n1\n00:00:01.000 --> 00:00:09.000\n'+text+'\n','source_caption')
        player=self.artifact('player.json',{'id':'123','uploader_id':'basharcommunications','duration':10,'fixture_only':True},'player_metadata')
        receipt={'source_id':sid,'http_status':200,'caption_language_label':'en-x-autogen','caption_artifact':vtt,'player_metadata':player,'duration_seconds':10,'cues':1,'words':len(text.split()),'fixture_only':True}
        proof=self.artifact('receipt.json',receipt,'caption_acquisition_receipt')
        normalized={'source_id':sid,'text':text,'turns':[{'turn_id':sid+':cue:1','role':'unknown','start_seconds':1.,'end_seconds':9.,'text':text}],'fixture_only':True}
        doc=self.artifact('normalized.json',normalized,'normalized_text')
        row={'source_id':sid,'session_id':'vimeo:123','corpus':'bashar','source_kind':'machine_asr','source_format':'official_session_excerpt_platform_asr','collection_status':'retrieved','language':'en','coverage_status':'partial','edition_id':vtt['sha256'],'text_artifact':doc,'evidence':[vtt,player,proof]}
        manifest=self.artifact('manifest.json',{'schema_version':1,'fixture_only':True,'records':[row]},'fixture_manifest')
        return row,normalized,Path(manifest['path'])
    def test_fixture_cannot_become_actual_speech(self):
        row,doc,path=self.record()
        with self.assertRaisesRegex(ValueError,'Synthetic manifest'):S.load_official([path])
    def test_complete_available_caption_track_remains_partial_session(self):
        row,doc,path=self.record();docs,held,editions,_=S.load_official([path],allow_fixtures=True)
        self.assertEqual(len(docs),1);self.assertFalse(held or editions)
        self.assertEqual(docs[0]['summary']['coverage_status'],'partial')
        self.assertEqual(docs[0]['summary']['unit'],'publisher_selected_public_clip')
        self.assertEqual(docs[0]['summary']['transcription_origin'],'platform_auto_caption')
    def test_repeated_identical_evidence_is_one_binding_not_conflicting_sources(self):
        row,doc,path=self.record();row['evidence'].append(dict(row['evidence'][2]));path.write_text(json.dumps({'schema_version':1,'fixture_only':True,'records':[row]}))
        self.assertEqual(len(S.load_official([path],allow_fixtures=True)[0]),1)
    def test_normalized_caption_changes_rejected_even_when_rehashed(self):
        row,doc,path=self.record();doc['turns'][0]['text']='changed words';doc['text']='changed words'
        row['text_artifact']=self.artifact('edited.json',doc,'normalized_text');path.write_text(json.dumps({'schema_version':1,'fixture_only':True,'records':[row]}))
        with self.assertRaisesRegex(ValueError,'source text or timing'):S.load_official([path],allow_fixtures=True)
    def test_publisher_identity_required(self):
        row,doc,path=self.record();roles=S.evidence_by_role(row,{},True)
        player=Path(roles['player_metadata'][0]['path']);value=json.loads(player.read_text());value['uploader_id']='different';player.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'Publisher player identity'):S.validate_caption(row,doc,roles)
    def test_timestamp_order_and_duration_guard(self):
        text='WEBVTT\n\n1\n00:00:10.000 --> 00:00:20.000\ntext\n'
        with self.assertRaisesRegex(ValueError,'timestamps exceed'):S.parse_vtt(text.encode(),5)
        text='WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\ntext\n\n2\n00:00:00.000 --> 00:00:01.000\ntext\n'
        with self.assertRaisesRegex(ValueError,'timestamps exceed'):S.parse_vtt(text.encode(),5)
    def test_caption_markup_and_entities_have_exact_derivation(self):
        cues=S.parse_vtt(b'WEBVTT\n\n1\n00:00:01.000 --> 00:00:02.000\n<i>one</i> &amp; two\n',5)
        self.assertEqual(cues[0]['text'],'one & two')
    def test_explicit_held_publication_keeps_denominator(self):
        p=Path(self.artifact('held.json',{'schema_version':1,'records':[{'source_id':'vimeo:321','session_id':'vimeo:321','collection_status':'held','hold_reason':'Explicit translated-language source'}]},'manifest')['path'])
        docs,held,_,_=S.load_official([p]);self.assertFalse(docs);self.assertEqual(held[0]['publication_id'],'vimeo:321')
    def local_fixture(self):
        publication='vimeo:456';text='Synthetic fixture speech about physical reality and choice.'
        original=self.artifact('original.mp4','synthetic audio bytes','audio')
        acquisition=self.artifact('acquisition.json',{'fixture_only':True,'source_id':publication,'audio':original},'acquisition_receipt')
        source={'provider':'publisher_audio','source_id':publication,'local_path':original['path'],'sha256':original['sha256'],'bytes':original['bytes'],'duration_seconds':10}
        proof=self.artifact('proof.json',{'fixture_only':True,'verified_artifacts':[{**source,'status':'verified'}],'acquisition_receipt':acquisition},'source_verification')
        source['verification_receipt']={'path':proof['path'],'sha256':proof['sha256']}
        binding={'source':source,'storage':{'retain_decoded_audio':False},'asr':{}}
        signature=S.hashlib.sha256(S.A.encoded(binding).encode()).hexdigest();sid=publication+':local-asr:'+signature[:16]
        segment={'start_seconds':1.,'end_seconds':8.,'text':text}
        segments=self.artifact('segments.json',{'fixture_only':True,'source_id':publication,'text':text,'segments':[segment]},'asr_segments')
        omitted={'local_path':str(self.root/'audio-16khz-mono.wav'),'sha256':'0'*64,'bytes':100,'kind':'audio','retained':False,'disposition':'new_derivative_removed_after_verification'}
        artifacts=[{'local_path':r['path'],'sha256':r['sha256'],'bytes':r['bytes'],'kind':'audio' if r is original else 'transcript'} for r in (original,segments)]+[omitted]
        receipt={'fixture_only':True,'kind':'source-bound-audio-analysis','status':'completed','source_id':publication,'binding':binding,'binding_sha256':signature,'decoded_duration_seconds':10,'verified_artifacts':artifacts,'asr':{'segments':1,'whitespace_word_count':len(text.split())}}
        proofreceipt=self.artifact('receipt.json',receipt,'asr_receipt')
        row={'source_id':sid,'session_id':publication,'asr_receipt_source_id':publication,'evidence':[original,acquisition,proof,segments,proofreceipt]}
        normalized={'source_id':sid,'text':text,'turns':[{'turn_id':sid+':1','role':'unknown',**segment}]}
        return row,normalized,receipt,Path(proofreceipt['path'])
    def test_edition_mapping_keeps_executed_receipts_unchanged(self):
        row,doc,receipt,path=self.local_fixture();roles=S.evidence_by_role(row,{},True);result=S.validate_local_asr(row,doc,roles,{})
        self.assertEqual(result['executed_source_id'],'vimeo:456');self.assertFalse(result['decoded_pcm_retained'])
        self.assertNotEqual(row['source_id'],receipt['source_id'])
        row['asr_receipt_source_id']='vimeo:999'
        with self.assertRaisesRegex(ValueError,'map to the declared publication'):S.validate_local_asr(row,doc,roles,{})
    def test_only_exact_declared_pcm_derivative_may_be_absent(self):
        row,doc,receipt,path=self.local_fixture();S.verify_audio_completion(path,receipt['binding'])
        for mutation in ({'local_path':str(self.root/'different.wav')},{'kind':'transcript'},{'disposition':'missing'},{'bytes':True}):
            modified=json.loads(json.dumps(receipt));modified['verified_artifacts'][-1].update(mutation);path.write_text(json.dumps(modified))
            with self.assertRaisesRegex(ValueError,'discarded new decoded derivative'):S.verify_audio_completion(path,modified['binding'])
        modified=json.loads(json.dumps(receipt));modified['verified_artifacts'][0].update(retained=False,disposition='new_derivative_removed_after_verification');path.write_text(json.dumps(modified))
        with self.assertRaisesRegex(ValueError,'discarded new decoded derivative'):S.verify_audio_completion(path,modified['binding'])


class OfficialMeasurementTests(unittest.TestCase):
    def test_known_incomplete_media_and_material_duration_gap_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'Known incomplete'):S.check_media_integrity(next(iter(S.KNOWN_INCOMPLETE_MEDIA)))
        with self.assertRaisesRegex(ValueError,'source-integrity review'):S.check_decode_duration(310.954667,304.96)
        S.check_decode_duration(310.954667,310.954)
    def test_packet_audit_handles_aac_priming_but_rejects_missing_interval(self):
        p={'format':{'duration':'0.042666'},'packets':[{'pts_time':'-0.021333'},{'pts_time':'0','duration_time':'0.021333'},{'pts_time':'.021333','duration_time':'.021333'}]}
        self.assertEqual(S.check_packet_continuity(p),3)
        p['packets'][-1]['pts_time']='6.021333'
        with self.assertRaisesRegex(ValueError,'Packet gap'):S.check_packet_continuity(p)
    def test_packet_audit_rejects_missing_initial_and_terminal_intervals(self):
        p={'format':{'duration':1.02},'packets':[{'pts_time':'1','duration_time':'.02'}]}
        with self.assertRaisesRegex(ValueError,'initial boundary'):S.check_packet_continuity(p)
        p={'format':{'duration':1.02},'packets':[{'pts_time':'0','duration_time':'.02'}]}
        with self.assertRaisesRegex(ValueError,'terminal boundary'):S.check_packet_continuity(p)
    def test_packet_audit_rejects_nonmonotonic_timestamps(self):
        p={'packets':[{'pts_time':'1','duration_time':'.02'},{'pts_time':'0','duration_time':'.02'}]}
        with self.assertRaisesRegex(ValueError,'timestamp order'):S.check_packet_continuity(p)
    def test_mask_reuses_corrected_contraction_aware_baseline(self):
        text="don't don’t we'll we’ll I'll I’ll you’ll";self.assertEqual(S.mask(text),text)
    def test_title_is_not_used_to_infer_genre(self):
        self.assertEqual(S.classify({'source_format':'session_excerpt','title':'Holiday greeting and product'}),'official_excerpt')
        for f in ('event_promotion','publisher_product_introduction','publisher_product_explainer_kirby_seid'):
            self.assertEqual(S.classify({'source_format':f}),'official_promotion')
        self.assertEqual(S.classify({'source_format':'standalone_greeting_scope_unverified'}),'official_greeting')
    def test_overlap_interval_union_is_not_speech_accuracy(self):
        value=S.timing_coverage([{'start_seconds':1,'end_seconds':4},{'start_seconds':3,'end_seconds':6}],10)
        self.assertEqual(value['cue_interval_union_seconds'],5);self.assertEqual(value['cue_interval_fraction'],.5)
    def test_machine_edit_distance_is_explicit_disagreement(self):
        result=S.edit_disagreement('one two three','one four three five')
        self.assertEqual(result['token_edit_distance'],2);self.assertAlmostEqual(result['distance_per_caption_token'],2/3)
        self.assertIn('not ASR accuracy',result['interpretation'])
    def test_length_control_abstains_for_short_text(self):
        self.assertIsNone(S.window_tokens({'tokens':['word']*399}));self.assertEqual(len(S.window_tokens({'tokens':['word']*500})),400)
    def test_semantic_window_retains_interior_punctuation_and_numbers(self):
        text='Prefix Alpha, 123 beta? Gamma suffix End';doc={'text':text,'tokens':S.A.tokens(text)}
        self.assertEqual(S.window_text(doc,4),'Alpha, 123 beta? Gamma suffix')
    def test_held_edition_does_not_double_count_admitted_publication(self):
        clips=[{'summary':{'publication_id':'vimeo:123'}}];held=[{'publication_id':'vimeo:123'},{'publication_id':'vimeo:456'}]
        self.assertEqual(S.disposition_counts(clips,held),{'admitted_publications':1,'held_publications':1,'held_editions':2,'observed_publication_dispositions':2})
    def test_exact_media_grouping_preserves_all_publication_rows(self):
        docs=[{'summary':{'publication_id':'vimeo:'+str(i),'source_id':'vimeo:'+str(i),'source_audio_sha256':'a'*64 if i<3 else 'b'*64,'stratum':'official_excerpt','transcription_origin':'local_asr'}} for i in (1,2,3)]
        chosen,aliases,families=S.collapse_exact_media(docs)
        self.assertEqual(len(docs),3);self.assertEqual(len(chosen),2);self.assertEqual(len(aliases),1);self.assertEqual(len(families),2)
        self.assertEqual(docs[1]['summary']['model_unit_source_id'],'vimeo:1');self.assertFalse(docs[1]['summary']['included_in_model'])
    def test_genre_conflict_inside_exact_media_family_requires_review(self):
        docs=[{'summary':{'publication_id':'vimeo:'+str(i),'source_id':'vimeo:'+str(i),'source_audio_sha256':'a'*64,'stratum':kind,'transcription_origin':'local_asr'}} for i,kind in [(1,'official_excerpt'),(2,'official_promotion')]]
        with self.assertRaisesRegex(ValueError,'conflicting source-genre'):S.collapse_exact_media(docs)
    def test_zero_vocabulary_rows_are_not_treated_as_evidence_of_dissimilarity(self):
        docs=[{'summary':{'source_id':sid,'stratum':kind}} for sid,kind in [('a','ra_published'),('b','official_excerpt'),('c','official_excerpt')]]
        r=S.projection_result(S.np.array([[1,.3,0],[.3,1,0],[0,0,0]]),docs,1,[True,True,False])
        self.assertEqual(r['zero_vector_source_ids'],['c']);self.assertEqual(len(r['pair_summary']),1);self.assertEqual(r['pair_summary'][0]['pairs'],1)
        self.assertEqual(r['nearest_baseline_sources'][-1]['neighbors'],[])


if __name__=='__main__':unittest.main()
