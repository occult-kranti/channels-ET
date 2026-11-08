import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('archive_inventory',Path(__file__).with_name('inventory.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REF={'input_id':'fixture','locator':'/fixture'}
UC1='UC'+'a'*22;UC2='UC'+'b'*22
V1='abcdefghijk';V2='ABCDEFGHIJK'

class InventoryTest(unittest.TestCase):
    def test_handle_case_but_not_accents(self):
        self.assertEqual(m.route('http://youtube.com/@ElanInteractions/videos?x=y')['key'],m.route('https://www.youtube.com/@elaninteractions')['key'])
        self.assertNotEqual(m.route('https://youtube.com/@AthinaKrol')['key'],m.route('https://youtube.com/@AthinaKról')['key'])
        self.assertNotEqual(m.route('https://youtube.com/user/danscranton')['key'],m.route('https://youtube.com/danscranton')['key'])
    def test_routes_reject_video_search_and_fake_uc(self):
        for url in ['https://youtube.com/watch?v='+V1,'https://youtube.com/shorts/'+V1,'https://youtube.com/results?search_query=x','https://youtube.com/channel/UCshort','https://notyoutube.com/@x','https://youtube.com/c/fxacrylics&source=gmail','https://youtube.com/@foo%2Fbar']:
            self.assertIsNone(m.route(url))
        self.assertEqual(m.route('https://youtube.com/channel/'+UC1+'/streams')['value'],UC1)
    def test_video_parse(self):
        self.assertEqual(m.video_id('https://youtu.be/'+V1+'?t=2'),V1)
        self.assertEqual(m.video_id('https://www.youtube-nocookie.com/embed/'+V1),V1)
        self.assertIsNone(m.video_id('https://youtube.com/watch?v=too-short'))
    def test_verified_bridge_and_weak_alias(self):
        obj=m.Inventory('/tmp');a=obj.account('https://youtube.com/channel/'+UC1,REF);b=obj.account('https://youtube.com/@Example',REF);c=obj.account('https://youtube.com/user/Example',REF)
        obj.bridges.append({'a':a,'b':b,'video_id':V1,'source_ref':REF,'observed_at':'historical'})
        obj.alias_assertions.append({'route_key':c,'asserted_aliases':['@Example'],'source_ref':REF})
        result=obj.reconcile();self.assertEqual(len(result['accounts']),2);self.assertEqual(len(result['identity_links']),1)
    def test_conflicting_handle_does_not_merge_distinct_uc(self):
        obj=m.Inventory('/tmp');h=obj.account('https://youtube.com/@Conflict',REF)
        for uc in [UC1,UC2]:
            c=obj.account('https://youtube.com/channel/'+uc,REF);obj.bridges.append({'a':c,'b':h,'video_id':V1,'source_ref':REF,'observed_at':'historical'})
        result=obj.reconcile();self.assertEqual(len(result['accounts']),3)
        self.assertTrue(all(x['status']=='conflicting_or_distinct_uc_identity_not_merged' for x in result['identity_links']))
    def test_duplicate_video_and_embed_not_uploader(self):
        obj=m.Inventory('/tmp');a=obj.account('https://youtube.com/@Example',REF)
        obj.video(V1,REF);obj.video(V1,REF);obj.link(a,V1,'publisher_embed',REF)
        r=obj.reconcile();self.assertEqual(len(r['videos']),1);self.assertIsNone(r['videos'][0]['verified_uploader_account_id'])
        self.assertEqual(r['accounts'][0]['counts']['historically_verified_uploader_video_ids'],0)
        self.assertIsNone(r['accounts'][0]['uploaded_total']);self.assertFalse(r['accounts'][0]['tabs']['shorts']['continuation_exhausted'])
    def test_jamie_excluded_without_comedian_invention(self):
        obj=m.Inventory('/tmp');a=obj.account('https://youtube.com/@JamieButlerMedium',REF,name='Jamie Butler',role='direct_channeler')
        obj.screen[a]={'status':'exclude','reason':'User exclusion','research_category':'direct_channeler','source_ref':REF}
        obj.video(V1,REF,duration=10);obj.link(a,V1,'screening_route_association',REF)
        r=obj.reconcile();self.assertEqual(r['videos'][0]['policy_decision']['status'],'excluded_account');self.assertEqual(r['accounts'][0]['roles'],['direct_channeler'])
    def test_mixed_account_item_duration_policy(self):
        obj=m.Inventory('/tmp');a=obj.account('https://youtube.com/@Mixed',REF,name='Mixed',role='reposter',labels=['Bashar','Abraham'])
        obj.video(V1,REF,title='Bashar: a message',duration=299);obj.video(V2,REF,title='Abraham message',duration=20)
        for v in [V1,V2]:obj.link(a,v,'inherited_route_association',REF)
        r=obj.reconcile();vs={v['video_id']:v for v in r['videos']}
        self.assertEqual(vs[V1]['policy_decision']['status'],'excluded_duration');self.assertEqual(vs[V2]['policy_decision']['status'],'eligible')
        self.assertEqual(r['accounts'][0]['duration_policy']['minimum_seconds'],0)
    def test_unknown_and_conflicting_duration(self):
        for vals in [[],[0],[299,301]]:self.assertEqual(m.duration_policy(True,vals)['status'],'duration_probe_required')
        self.assertEqual(m.duration_policy(True,[300])['status'],'eligible');self.assertEqual(m.duration_policy(False,[])['status'],'eligible')
    def test_nonfinite_and_boolean_duration_rejected(self):
        self.assertEqual(m.duration_policy(True,[float('nan'),float('inf'),float('-inf'),True])['status'],'duration_probe_required')
        obj=m.Inventory('/tmp');obj.video(V1,REF,duration=float('inf'));self.assertEqual(obj.videos[V1]['duration_observations'],[])
        with self.assertRaises(ValueError):m.dumps({'invalid':float('nan')})
    def test_shared_civilization_is_not_bashar(self):
        obj=m.Inventory('/tmp');a=obj.account('https://youtube.com/@ElanInteractions',REF,name='Elan Interactions',labels=['Essassani'])
        obj.video(V1,REF,title='Elan, Essassani message',duration=20);obj.link(a,V1,'research_route_association',REF)
        self.assertEqual(obj.reconcile()['videos'][0]['policy_decision']['minimum_seconds'],0)
    def test_publisher_account_video_links_require_actual_page_overlap(self):
        self.assertFalse(m.shared_page_evidence(['https://publisher.test/a'],['https://publisher.test/b']))
        self.assertFalse(m.shared_page_evidence([None],[None]))
        self.assertTrue(m.shared_page_evidence(['https://publisher.test/a'],['https://publisher.test/a']))
    def test_known_uploader_exclusion_beats_unverified_embed(self):
        obj=m.Inventory('/tmp');a=obj.account('https://youtube.com/@Excluded',REF);b=obj.account('https://youtube.com/@Included',REF)
        obj.screen[a]={'status':'exclude','reason':'irrelevant','source_ref':REF};obj.video(V1,REF,duration=10)
        obj.link(a,V1,'historical_watch_uploader',REF);obj.link(b,V1,'publisher_embed',REF)
        self.assertEqual(obj.reconcile()['videos'][0]['policy_decision']['status'],'excluded_account')

if __name__=='__main__':unittest.main()
