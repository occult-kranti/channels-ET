import json
import math
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).parent))
import query_semantic as Q
import retrieve_graph as R


class ArbitraryQueryTest(unittest.TestCase):
    def test_candidate_filters_precede_ranking_and_ties_are_stable(self):
        ids=['b','a','excluded','zero','bad'];scores=[.5,.5,1.,0.,math.nan]
        rows=Q.rank_values(ids,scores,{'a','b','zero','bad'},positive=True)
        self.assertEqual([r['source_id'] for r in rows],['a','b'])
        self.assertEqual(Q.rank_values(ids,scores,set()),[])

    def test_empty_query_and_invalid_limit_fail_before_artifact_access(self):
        with self.assertRaises(ValueError):Q.query('missing',' ','rrf','missing','missing','missing')
        with self.assertRaises(ValueError):Q.query('missing','text','rrf','missing','missing','missing',limit=0)

    def test_empty_filtered_universe_uses_real_sql_without_loading_model(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dbpath=root/'private.sqlite';analysis=root/'analysis.json';witness=root/'core-vectors.npz'
            analysis.write_text(json.dumps({'documents':[{'source_id':'a'}]}));np.savez(witness,source_ids=np.array(['a']))
            db=sqlite3.connect(dbpath)
            db.executescript('CREATE TABLE meta(key TEXT,value_json TEXT); CREATE TABLE sources(source_id TEXT,title TEXT,source_url TEXT,body_sha256 TEXT,body TEXT,channel_id TEXT,creator_id TEXT,text_origin TEXT,publication_date TEXT);')
            db.execute('INSERT INTO meta VALUES (?,?)',('bindings',json.dumps({'analysis':{'sha256':R.sha(analysis.read_bytes())}})))
            db.execute('INSERT INTO sources VALUES (?,?,?,?,?,?,?,?,?)',('a','Title','https://example.org','bodyhash','body','present','creator','written',None))
            db.commit();db.close()
            contract=root/'contract.json';contract.write_text(json.dumps({'bindings':{name:{'sha256':R.sha(path.read_bytes())} for name,path in [('database',dbpath),('analysis',analysis),('vector_witness',witness)]}}))
            result=Q.query(dbpath,'contact','rrf',analysis,root,contract,channel="missing' OR 1=1 --")
            self.assertEqual(result['status'],'empty_filtered_universe');self.assertEqual(result['matches'],[])
            self.assertEqual(result['eligible_sources'],0)
            db=sqlite3.connect(dbpath);self.assertEqual(db.execute('SELECT COUNT(*) FROM sources').fetchone()[0],1);db.close()


if __name__=='__main__':unittest.main()
