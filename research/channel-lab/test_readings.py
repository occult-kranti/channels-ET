#!/usr/bin/env python3
"""Small integration controls for reading coverage and edition-bound support."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('readings_builder',Path(__file__).with_name('build_readings.py'))
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


class ReadingIntegrity(unittest.TestCase):
    def fixture(self,root):
        body='one two three four';p=root/'body.txt';p.write_text(body)
        r={'source_id':'doc-test','row_index':0,'selected_edition_id':'old-test',
            'legacy_source_ids':['old-test'],'body_transform':'plain_text',
            'text_artifact':{'path':str(p),'sha256':M.digest(p.read_bytes()),'bytes':p.stat().st_size},
            'body_sha256':M.digest(body.encode()),'words':4,'channel_id':'channel-test','channel_name':'Synthetic test',
            'title':'Synthetic test body','source_url':'https://example.com/test','document_kind':'publisher_written_message',
            'text_origin':'publisher_written','attribution_scope':'Synthetic test only'}
        frame={'records':[r],'coverage':{'documents':1}};f=root/'frame.json';M.write(f,frame)
        k=root/'knowledge.json';M.write(k,{'cards':[]})
        spans=[]
        for ident,lo,hi in [('first',0,7),('overlap',4,13)]:
            text=body[lo:hi];spans.append({'evidence_id':ident,'legacy_source_id':'old-test','body_sha256':r['body_sha256'],
                'start_character':lo,'end_character':hi,'span_sha256':M.digest(text.encode()),'words':len(text.split()),
                'text':text,'reading_kind':'synthetic_test','read_scope':'Synthetic integrity fixture'})
        ins={'spans':spans,'accepted_knowledge':{'path':str(k),'sha256':M.digest(k.read_bytes())},'method':{'scope':'synthetic'}}
        ip=root/'inspection.json';M.write(ip,ins)
        case={'case_id':'case-test','relation':'different_focus','question':'Synthetic question',
            'reading':'Synthetic interpretation','conditions':'Synthetic condition','counter_reading':'Synthetic counter-reading',
            'limitations':'Not source research','qualitative_theme_keys':['test'],'evidence_ids':['first','overlap'],
            'statements':[{'legacy_source_id':'old-test','proposition':'Synthetic proposition'}]}
        cp=root/'cases.json';M.write(cp,{'cases':[case],'channel_notes':{},'limitations':['Synthetic test']})
        sel=root/'selection.json';M.write(sel,{'candidates':[{'case_id':'case-test'}]})
        return f,ip,cp,sel

    def test_overlapping_spans_are_not_double_counted(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm',prefix='reading-test-') as td:
            root=Path(td);args=self.fixture(root);out=root/'output';M.build(*args,out)
            result=M.read(out/'readings.json')
            self.assertEqual(result['coverage']['primary_unique_words_read'],3)
            self.assertEqual(result['source_bindings'][0]['merged_intervals'],[[0,13]])
            self.assertNotIn(str(root),(out/'readings.json').read_text())
            self.assertNotIn('one two three',(out/'readings.json').read_text())

    def test_new_edition_cannot_inherit_old_character_support(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm',prefix='reading-test-') as td:
            root=Path(td);f,ip,cp,sel=self.fixture(root);ins=M.read(ip)
            ins['spans'][0]['body_sha256']='0'*64;M.write(ip,ins)
            with self.assertRaisesRegex(ValueError,'Canonical edition differs'):M.build(f,ip,cp,sel,root/'output')
            self.assertFalse((root/'output/output-manifest.json').exists())

    def test_unreported_candidate_cannot_disappear(self):
        with tempfile.TemporaryDirectory(dir='/dev/shm',prefix='reading-test-') as td:
            root=Path(td);f,ip,cp,sel=self.fixture(root);M.write(sel,{'candidates':[{'case_id':'case-test'},{'case_id':'not-answered'}]})
            with self.assertRaisesRegex(ValueError,'Every frozen candidate'):M.build(f,ip,cp,sel,root/'output')
            self.assertFalse((root/'output/output-manifest.json').exists())


if __name__=='__main__':unittest.main()
