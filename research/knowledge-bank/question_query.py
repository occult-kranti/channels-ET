#!/usr/bin/env python3
"""Search the source-bound public question bank without a model or network."""
import argparse
import json
from pathlib import Path
import re
import sqlite3


def query(database, text=None, question=None, source=None, relation=None, limit=20):
    if not 1<=limit<=200: raise ValueError('Limit must be between 1 and 200')
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        if relation:
            sql='''SELECT x.comparison_id,x.relation,x.reason,x.qualification,q.question,
            a.source_id AS left_source_id,a.paraphrase AS left_paraphrase,
            b.source_id AS right_source_id,b.paraphrase AS right_paraphrase
            FROM comparisons x JOIN questions q USING(question_id)
            JOIN cards a ON a.card_id=x.left_card_id JOIN cards b ON b.card_id=x.right_card_id
            WHERE x.relation=?''';args=[relation]
            if question:sql+=' AND x.question_id=?';args.append(question)
            sql+=' ORDER BY x.comparison_id LIMIT ?';args.append(limit)
            return [dict(r) for r in db.execute(sql,args)]
        sql='''SELECT c.card_id,c.question_id,q.question_type,q.question,c.source_id,s.medium,
        s.claimed_label,s.source_url,c.paraphrase,c.conditions,c.time_scope,c.qualifying_note
        FROM cards c JOIN questions q USING(question_id) JOIN sources s USING(source_id)'''
        args=[];filters=[]
        if text:
            words=re.findall(r"[\w'-]+",text,flags=re.UNICODE)
            if not words:return []
            expression=' AND '.join('"'+w.replace('"','""')+'"' for w in words)
            filters.append('c.card_id IN (SELECT card_id FROM card_search WHERE card_search MATCH ?)');args.append(expression)
        if question:filters.append('c.question_id=?');args.append(question)
        if source:filters.append('c.source_id=?');args.append(source)
        if filters:sql+=' WHERE '+' AND '.join(filters)
        sql+=' ORDER BY c.question_id,c.card_id LIMIT ?';args.append(limit)
        return [dict(r) for r in db.execute(sql,args)]


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True)
    p.add_argument('--query');p.add_argument('--question');p.add_argument('--source')
    p.add_argument('--relation',choices=['shared_proposition','compatible','different_focus','conditional_tension','explicit_contradiction','unresolved']);p.add_argument('--limit',type=int,default=20)
    a=p.parse_args();print(json.dumps(query(a.database,a.query,a.question,a.source,a.relation,a.limit),indent=2,ensure_ascii=False))
