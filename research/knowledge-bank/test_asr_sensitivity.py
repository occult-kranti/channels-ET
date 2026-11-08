import random
import copy
import json
import sys
import tempfile
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).parent))
import asr_sensitivity as A


def slow_distance(a,b):
    row=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        new=[i]
        for j,y in enumerate(b,1):new.append(min(new[-1]+1,row[j]+1,row[j-1]+(x!=y)))
        row=new
    return row[-1]


class ArtifactFixture:
    """Synthetic independent receipts with two windows per source and a short tail."""
    def __init__(self, root):
        self.root = Path(root)
        self.old = []
        docs, clips = [], []
        for index in range(4):
            old_id = f'synthetic-source-{index}'
            new_id = old_id + ':alternative'
            audio = self.artifact(f'audio-{index}', b'synthetic input bytes')
            old_text = self.artifact(f'old-text-{index}', {'text': 'Original words.'})
            acquisition = self.artifact(f'acquisition-{index}', {'audio': audio})
            old_receipt = self.artifact(f'old-receipt-{index}', {
                'publication_id': f'publication-{index}',
                'acquisition_receipt': acquisition,
                'decoder': {'raw_pcm_sha256': 'a' * 64, 'sample_count': 480002}})
            pcm = {'sha256': 'a' * 64, 'sample_count': 480002,
                   'duration_seconds': 480002 / 16000, 'sample_rate': 16000,
                   'channels': 1, 'format': 's16le', 'matches_old_decoder': True}
            f32 = dict(pcm, sha256='b' * 64, format='f32le', conversion='int16 /32768')
            del f32['matches_old_decoder']
            chunks, turns = [], []
            for j, (start, end, text) in enumerate([(0, 480000, 'It is not certain.'),
                                                    (480000, 480002, '2034')]):
                clip_id = f'{old_id}-{j}'
                output = {'clip_id': clip_id, 'source_id': old_id, 'text': text,
                          'words': len(text.split()), 'start_sample': start,
                          'end_sample': end, 'pcm_sha256': 'c' * 64,
                          'encoder_exhausted': True}
                chunks.append(dict(output, asr_output=self.artifact(clip_id, output)))
                clips.append({'clip_id': clip_id, 'source_id': old_id,
                              'start_sample': start, 'end_sample': end,
                              'pcm': {'sha256': 'c' * 64}})
                turns.append({'id': clip_id, 'start': start / 16000,
                              'end': end / 16000, 'text': text, 'speaker_role': 'unknown'})
            body = ' '.join(t['text'] for t in turns)
            normalized = {'source_id': new_id, 'counterpart_source_id': old_id,
                          'speaker_role': 'unknown', 'text': body, 'words': len(body.split()),
                          'turns': turns}
            doc = {'source_id': new_id, 'counterpart_source_id': old_id,
                   'publication_id': f'publication-{index}', 'audio_artifact': audio,
                   'old_text_artifact': old_text, 'old_asr_receipt': old_receipt,
                   'canonical_s16_pcm': pcm, 'decoded_pcm': f32, 'chunks': chunks,
                   'text_artifact': self.artifact(f'text-{index}', normalized),
                   'plain_text_artifact': self.artifact(f'plain-{index}', body.encode()),
                   'coverage': {'input_samples': 480002, 'covered_samples': 480002,
                                'chunk_count': 2, 'contiguous': True, 'starts_at_zero': True,
                                'ends_at_sample_count': True, 'all_encoder_exhausted': True}}
            docs.append(doc)
            self.old.append({'record': {'source_id': old_id, 'document_kind': 'machine_transcript',
                                       'text_artifact': old_text, 'body_sha256': 'd' * 64},
                             'text': 'Original words.'})
        frame = self.artifact('frame', {'status': 'prepared_full_sample_coverage',
                                       'documents': copy.deepcopy(docs), 'clips': clips})
        for index, doc in enumerate(docs):
            receipt = dict(doc, status='completed_full_chunked_asr',
                           model_id='nvidia/parakeet-tdt-0.6b-v3',
                           model_revision='541d1f99c6b0c3cd0b11a95167540bb8edefd82b',
                           full_frame=frame)
            doc['asr_receipt'] = self.artifact(f'new-receipt-{index}', receipt)
        self.manifest = {'status': 'completed_full_chunked_asr',
                         'model_id': 'nvidia/parakeet-tdt-0.6b-v3',
                         'model_revision': '541d1f99c6b0c3cd0b11a95167540bb8edefd82b',
                         'input_frame': frame, 'documents': docs}

    def artifact(self, name, value):
        raw = value if isinstance(value, bytes) else json.dumps(value).encode()
        path = self.root / name
        path.write_bytes(raw)
        return {'path': str(path), 'bytes': len(raw), 'sha256': A.sha(raw)}


class SensitivityTest(unittest.TestCase):
    def test_edit_distance_known_boundaries(self):
        self.assertEqual(A.edit_distance([],['x','y']),2)
        self.assertEqual(A.edit_distance(list('kitten'),list('sitting')),3)
        self.assertEqual(A.edit_distance(['not','this','year'],['this','year']),1)

    def test_bitvector_matches_independent_dynamic_program(self):
        randomizer=random.Random(73)
        for _ in range(100):
            a=[randomizer.choice('abcde') for i in range(randomizer.randint(0,70))]
            b=[randomizer.choice('abcde') for i in range(randomizer.randint(0,70))]
            self.assertEqual(A.edit_distance(a,b),slow_distance(a,b))

    def test_edit_distance_long_repeated_tokens(self):
        a=['the']*1000+['not']+['year']*200;b=['the']*1000+['year']*200
        self.assertEqual(A.edit_distance(a,b),1)

    def test_recognition_tokenization_retains_numbers_and_negation(self):
        self.assertEqual(A.recognition_tokens("Don't say 2031—say 2034."),["don't",'say','2031','say','2034'])

    def test_incomplete_manifest_cannot_enter_analysis(self):
        with self.assertRaises(ValueError):A.validate_new([],{'status':'running','documents':[]})

    def test_complete_exact_four_inputs_and_partial_tails_are_admitted(self):
        with tempfile.TemporaryDirectory() as root:
            fixture = ArtifactFixture(root)
            rows = A.validate_new(fixture.old, fixture.manifest)
            self.assertEqual(len(rows), 4)
            self.assertTrue(all(r['sample_count'] == 480002 and r['chunk_count'] == 2 for r in rows))

    def test_changed_artifact_bytes_rejected_even_when_text_remains_valid(self):
        with tempfile.TemporaryDirectory() as root:
            fixture = ArtifactFixture(root)
            ref = fixture.manifest['documents'][0]['text_artifact']
            Path(ref['path']).write_bytes(Path(ref['path']).read_bytes() + b' ')
            with self.assertRaisesRegex(ValueError, 'Changed source artifact'):
                A.validate_new(fixture.old, fixture.manifest)

    def test_missing_sample_gap_and_different_canonical_audio_rejected(self):
        for mutation, expected in [('gap', 'gap or overlap'), ('pcm', 'PCM differs'),
                                   ('count', 'all samples covered')]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as root:
                fixture = ArtifactFixture(root)
                doc = fixture.manifest['documents'][0]
                if mutation == 'gap':doc['chunks'][1]['start_sample'] += 1
                if mutation == 'pcm':doc['canonical_s16_pcm']['sha256'] = 'e' * 64
                if mutation == 'count':doc['coverage']['covered_samples'] -= 1
                with self.assertRaisesRegex(ValueError, expected):
                    A.validate_new(fixture.old, fixture.manifest)

    def test_duplicate_recordings_cannot_replace_the_exact_four_pairs(self):
        with tempfile.TemporaryDirectory() as root:
            fixture = ArtifactFixture(root)
            fixture.manifest['documents'][3] = copy.deepcopy(fixture.manifest['documents'][0])
            with self.assertRaisesRegex(ValueError, 'four frozen ASR counterparts'):
                A.validate_new(fixture.old, fixture.manifest)

    def test_raw_window_pcm_must_match_prepared_input(self):
        with tempfile.TemporaryDirectory() as root:
            fixture = ArtifactFixture(root)
            fixture.manifest['documents'][0]['chunks'][0]['pcm_sha256'] = 'e' * 64
            with self.assertRaisesRegex(ValueError, 'prepared PCM'):
                A.validate_new(fixture.old, fixture.manifest)

    def test_empty_recognition_is_rejected_before_embedding(self):
        with tempfile.TemporaryDirectory() as root:
            fixture = ArtifactFixture(root)
            doc = fixture.manifest['documents'][0]
            normalized = json.loads(Path(doc['text_artifact']['path']).read_text())
            normalized.update(text='', words=0)
            doc['text_artifact'] = fixture.artifact('empty-transcript', normalized)
            receipt = json.loads(Path(doc['asr_receipt']['path']).read_text())
            receipt['text_artifact'] = doc['text_artifact']
            doc['asr_receipt'] = fixture.artifact('empty-receipt', receipt)
            with self.assertRaisesRegex(ValueError, 'Empty recognized edition'):
                A.validate_new(fixture.old, fixture.manifest)


if __name__=='__main__':unittest.main()
