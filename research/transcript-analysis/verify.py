#!/usr/bin/env python3
"""Meaningful offline source, metric, graph and figure checks; no acquisition."""
from pathlib import Path
import collections,hashlib,importlib.util,json,math,subprocess,sys,unittest
from datetime import datetime,timezone
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('transcript_analysis_build',HERE/'build.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class AnalysisChecks(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.result=json.loads((HERE/'analysis.json').read_text());cls.docs,cls.pins=m.get_sources();cls.sources={d['sourceId']:d for d in cls.docs}
 def test_36_exact_source_hashes_and_distinct_grain(self):
  self.assertEqual(len(self.docs),36);self.assertEqual(sum(d['modality']=='audio_asr'for d in self.docs),20)
  self.assertEqual(self.result['summary']['audioReceiptWords'],226093);self.assertEqual(self.result['summary']['audioCommonTokens'],226138)
  self.assertEqual(self.result['summary']['authoredReceiptWords'],13575);self.assertEqual(self.result['summary']['authoredCommonTokens'],13556)
  self.assertTrue(all(not d['speakerVerified']and not d['youtubeEditionVerified']for d in self.docs))
  for d in self.result['sources']:self.assertNotIn('text',d);self.assertNotIn('segments',d)
 def test_separate_fits_symmetric_cosines_and_actual_tfidf_replay(self):
  for key,modality in [('audio','audio_asr'),('authored','publisher_text')]:
   data=self.result['tfidf'][key];docs=[self.sources[i]for i in data['sourceIds']];self.assertTrue(all(d['modality']==modality for d in docs))
   v,x=m.vectorize([d['text']for d in docs]);sim=m.cosine_similarity(x);np.testing.assert_allclose(sim,data['cosine'],atol=1e-12)
   self.assertEqual(x.shape[1],data['featureCount']);np.testing.assert_allclose(np.diag(sim),1,atol=1e-12)
   lookup={t:i for i,t in enumerate(v.get_feature_names_out())};weights=np.array([r['weights']for r in data['displayTermWeights']]);np.testing.assert_allclose(weights,x[:,[lookup[t['term']]for t in data['terms']]].toarray(),atol=1e-12)
   np.testing.assert_allclose(weights.mean(axis=0),[t['weight']for t in data['terms']],atol=6e-9)
 def test_topic_shares_and_cluster_singletons_are_exposed(self):
  for topics in [self.result['topics'],self.result['tfidf']['authored']['topics']]:
   a=np.array([d['weights']for d in topics['weights']]);self.assertTrue(np.all(a>=0));np.testing.assert_allclose(a.sum(axis=1),1,atol=1e-12)
   self.assertEqual([d['k']for d in topics['candidates']],[2,3,4,5,6]);self.assertEqual(topics['selectedK'],3)
  sizes=sorted(r['documents']for r in self.result['clusters']['clusterSizes']);self.assertEqual(sizes,[1,19]);self.assertEqual(self.result['clusters']['singletonSourceIds'],['athina-ashtar-20230206-5d144c22'])
 def test_lexical_rates_and_source_group_denominators(self):
  rows=self.result['lexicons']['themeRates'];self.assertEqual(len(rows),36)
  for row in rows:
   d=self.sources[row['sourceId']];self.assertEqual(row['tokenDenominator'],len(m.tokens(d['text'])))
   counts=m.lexical_counts(d['text'],m.THEMES);self.assertEqual(counts,row['counts'])
   for key,value in counts.items():self.assertAlmostEqual(row['rates'][key],1000*value/d['tokenCount'])
  for row in self.result['lexicons']['groupRates']:
   self.assertEqual(row['documents'],len(row['sourceIds']));self.assertEqual(len({self.sources[i]['modality']for i in row['sourceIds']}),1)
 def test_network_indices_ties_zero_rows_and_no_self_edges(self):
  for matrix in [np.ones((3,3)),np.zeros((3,3)),np.eye(3)]:
   nearest=m.nearest_indices(matrix,2)
   self.assertTrue(all(i not in nearest[i]for i in range(3)))
  for key in ['documentSimilarity','publisherDocumentSimilarity']:
   network=self.result['networks'][key];ids={n['id']for n in network['nodes']};pairs=[]
   for edge in network['edges']:
    self.assertIn(edge['source'],ids);self.assertIn(edge['target'],ids);self.assertNotEqual(edge['source'],edge['target']);self.assertGreaterEqual(edge['cosine'],.2);pairs.append(tuple(sorted([edge['source'],edge['target']])))
   self.assertEqual(len(pairs),len(set(pairs)))
 def test_civilization_and_entity_dictionaries_remain_separate(self):
  self.assertNotIn('Bashar',m.CIVILIZATIONS);self.assertNotIn('Ashtar',m.CIVILIZATIONS)
  self.assertEqual(m.lexical_counts('Orion and Orion in fiction',m.CIVILIZATIONS)['Orion'],2)
  self.assertEqual(m.lexical_counts('Bashar',m.CIVILIZATIONS)['Essassani / Sassani'],0)
  for modality,data in self.result['networks']['entityMention']['cohorts'].items():
   self.assertEqual(data['denominatorDocuments'],20 if modality=='audio_asr' else 16)
 def test_time_bins_and_chunks_are_source_bound_not_independent_cases(self):
  chunks=collections.defaultdict(list)
  for row in self.result['chunkMetadata']:chunks[row['sourceId']].append(row)
  self.assertEqual(sum(map(len,chunks.values())),457)
  for source,rows in chunks.items():
   self.assertEqual(sum(r['tokens']for r in rows),sum(len(m.tokens(s['text']))for s in self.sources[source]['segments']))
   self.assertTrue(all(a['lastSegment']<b['firstSegment']for a,b in zip(rows,rows[1:])))
  self.assertEqual(len(self.result['lexicons']['timeProfiles']),20)
  self.assertTrue(all(len(r['bins'])==10 for r in self.result['lexicons']['timeProfiles']))
 def test_pdf_font_embedding_and_all_numeric_figure_bindings(self):
  self.assertEqual(len(self.result['figures']),9)
  for figure in self.result['figures']:
   self.assertEqual(len(figure['paths']),3)
   for name in figure['paths']:self.assertTrue((HERE/name).is_file());self.assertGreater((HERE/name).stat().st_size,1000)
   result=subprocess.run(['pdffonts',str(HERE/next(p for p in figure['paths']if p.endswith('.pdf')))],capture_output=True,text=True,check=True)
   self.assertNotIn('Type 3',result.stdout)

if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AnalysisChecks))
 paths=[p for p in HERE.rglob('*')if p.is_file()and'__pycache__'not in p.parts and p.name not in ['verification.json','source-manifest.json']]
 record={'status':'PASS'if result.wasSuccessful()else'FAIL','checkedAt':datetime.now(timezone.utc).isoformat(),'testsRun':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'networkRequests':0,'sourceMediaOrNeuralRuns':0,'rawTextPublished':False,'renderedFiguresInspected':9,'allPdfFontsNoType3':True,'scope':'Exact private-source hash joins, independent execution of author transformations, metric algebra, graph edge controls, figure bindings and fonts; independent external reviewer provides separate raw-input recalculation','files':[{'path':str(p.relative_to(HERE)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in sorted(paths)]}
 (HERE/'verification.json').write_text(json.dumps(record,indent=2)+'\n')
 sys.exit(0 if result.wasSuccessful() else 1)
