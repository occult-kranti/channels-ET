import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SPEC=importlib.util.spec_from_file_location('recovery',Path(__file__).with_name('recover_asr_terminal.py'))
R=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(R)

class RecoveryTests(unittest.TestCase):
    def fixture(self,root,end=105,first_end=10,exhausted=True,failure_index=1):
        source={'source_id':'s','decoded_16k_mono':{'sample_count':1600000,'raw_pcm_sha256':'a'*64,'duration_seconds':100}}
        receipt=root/'source.json';receipt.write_text('{}')
        request={'source_id':'s','acquisition_receipt':R.C.artifact(receipt),'decoder':source['decoded_16k_mono']}
        R.C.dump(root/'request.json',request)
        rows=[{'segment_index':0,'start_repr':'0','end_repr':str(first_end),'text':' First text '},
              {'segment_index':1,'start_repr':'95','end_repr':str(end),'text':' Final words '}]
        raw=root/'raw.jsonl';raw.write_text('\n'.join(json.dumps(x) for x in rows)+'\n')
        completion={'status':'diagnostic_only_not_admitted','inference_stream_exhausted':exhausted,
                    'request_sha256':R.C.sha(root/'request.json'),'raw_segments':R.C.artifact(raw),'raw_segment_count':2,
                    'first_timestamp_failure':{'reason':'beyond_duration','segment_index':failure_index}}
        R.C.dump(root/'asr-diagnostic-completion.json',completion)
        return source

    def test_last_end_only_and_text_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=self.fixture(root)
            with patch.object(R.C,'completed',return_value=source):_,_,_,rows,quality=R.validate_diagnostic(root)
            self.assertEqual(rows[-1]['end_seconds'],100);self.assertEqual(rows[-1]['original_end_seconds'],105)
            self.assertEqual([r['text'] for r in rows],['First text','Final words'])
            self.assertFalse(quality['text_changed_by_repair']);self.assertEqual(quality['timestamp_maximum_adjustment_seconds'],5)

    def test_invalid_diagnostics_rejected(self):
        for kw in [{'end':135},{'first_end':101},{'exhausted':False},{'failure_index':0}]:
            with self.subTest(kw=kw),tempfile.TemporaryDirectory() as t:
                root=Path(t);source=self.fixture(root,**kw)
                with patch.object(R.C,'completed',return_value=source),self.assertRaises(ValueError):R.validate_diagnostic(root)

    def test_tampered_raw_stream_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=self.fixture(root);(root/'raw.jsonl').write_text('[]')
            with patch.object(R.C,'completed',return_value=source),self.assertRaises(ValueError):R.validate_diagnostic(root)

if __name__=='__main__':unittest.main()
