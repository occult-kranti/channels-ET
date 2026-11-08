import hashlib,importlib.util,json,tempfile,unittest
from pathlib import Path

def module(name,file):
 s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
P=module('pilot','analyze_pilot.py');G=module('graph','claim_graph.py')
class EdgeContracts(unittest.TestCase):
 def test_duplicate_text_not_counted_twice(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=root/'text.txt';p.write_text('test source content '*100);ref={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}
   records=[{'source_id':s,'medium_id':'medium','comparison_label':'label','language':'en','attribution_scope':'Explicit fixture role','text_artifact':ref} for s in ['one','two']];m=root/'manifest.json';m.write_text(json.dumps({'schema_version':1,'records':records}))
   with self.assertRaisesRegex(ValueError,'Duplicate exact text'):P.load([m])
 def test_same_person_register_merge_keeps_all_sources(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);paths=[]
   for i in [1,2]:
    data={'sources':[{'id':'s'+str(i),'url':'https://example.test/'+str(i)}],'mediums':[{'id':'m','name':'One Person','source_ids':['s'+str(i)]}],'channellees':[{'id':'e','label':'One Label','kind':'named'}],'claims':[{'id':'c'+str(i),'medium_id':'m','channellee_id':'e','relation':'claims_to_channel','source_ids':['s'+str(i)]}],'comparison_groups':[{'id':'g'+str(i),'label':'One label','channellee_ids':['e']}]};p=root/(str(i)+'.json');p.write_text(json.dumps(data));paths.append(p)
   r=G.build(paths);self.assertEqual(r['medium_records'],1);self.assertEqual(r['claims'],2);self.assertEqual(r['comparison_groups'][0]['source_ids'],['s1','s2'])
   data['mediums'][0]['name']='Different Person';paths[1].write_text(json.dumps(data))
   with self.assertRaisesRegex(ValueError,'Conflicting immutable'):G.build(paths)
 def test_contact_and_category_do_not_inflate_channelers(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'register.json';data={'sources':[{'id':'s','url':'https://example.test'}],'mediums':[{'id':'m','name':'Medium','collaboration_group_id':'joint'},{'id':'n','name':'Partner','collaboration_group_id':'joint'},{'id':'c','name':'Contactee'}],'channellees':[{'id':'e','label':'Label','kind':'named'}],'claims':[{'id':'c1','medium_id':'m','channellee_id':'e','relation':'channels_named_entity','source_ids':['s']},{'id':'c2','medium_id':'n','channellee_id':'e','relation':'channels_named_entity','source_ids':['s']},{'id':'c3','medium_id':'c','channellee_id':'e','relation':'claims_contact_with','source_ids':['s']}],'comparison_groups':[{'id':'g','label':'Label','channellee_ids':['e']}]};p.write_text(json.dumps(data));g=G.build([p])['comparison_groups'][0];self.assertEqual(g['direct_claim_medium_records'],2);self.assertEqual(g['declared_practice_groups'],1);self.assertEqual(g['new_attributed_message_documents'],0);self.assertEqual(g['text_comparison_status'],'insufficient_cross_medium_attributed_text')
if __name__=='__main__':unittest.main()
