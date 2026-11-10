"""Adversarial checks for the public artifact boundary (no network or private corpus)."""
import importlib.util
import io
from pathlib import Path
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('public_release',Path(__file__).with_name('build_public.py'))
public=importlib.util.module_from_spec(spec);spec.loader.exec_module(public)

class Boundary(unittest.TestCase):
    def test_decoded_private_paths_rejected(self):
        with self.assertRaises(ValueError): public.inspect(b'{"value":"\\u002fworkspace/secret"}','example.json')
    def test_full_transcript_fields_rejected(self):
        with self.assertRaises(ValueError): public.inspect(b'{"records":[{"transcript_text":"original"}]}','example.json')
    def test_jsonl_checks_every_line(self):
        with self.assertRaises(ValueError): public.inspect(b'{"id":1}\n{"authorization":"token"}\n','example.jsonl')
    def test_duplicate_keys_rejected(self):
        with self.assertRaises(ValueError): public.inspect(b'{"status":true,"status":false}','example.json')
    def test_active_svg_rejected(self):
        with self.assertRaises(ValueError): public.inspect(b'<svg><script>alert(1)</script></svg>','chart.svg')
    def test_zip_traversal_rejected(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z: z.writestr('../outside.json','{}')
        with self.assertRaises(ValueError): public.inspect(b.getvalue(),'metadata.zip')
    def test_zip_hidden_private_json_rejected(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,'w') as z: z.writestr('rows.jsonl','{"source_body":"original"}\n')
        with self.assertRaises(ValueError): public.inspect(b.getvalue(),'metadata.zip')
    def test_valid_metadata_and_unknowns_allowed(self):
        public.inspect(b'{"uploaded_total":null,"retained":0,"source_url":"https://example.org/"}','data.json')

if __name__=='__main__': unittest.main()
