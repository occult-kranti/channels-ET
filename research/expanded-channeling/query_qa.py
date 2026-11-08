#!/usr/bin/env python3
"""Read-only private source/Q&A lookup; never uploads or marks answers verified."""
import argparse,json,sqlite3
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--database',type=Path,required=True);p.add_argument('--query',required=True);p.add_argument('--group');p.add_argument('--limit',type=int,default=10);a=p.parse_args()
if not 1<=a.limit<=100:p.error('limit must be1..100')
if not a.database.is_file():p.error('database not found')
db=sqlite3.connect(a.database.resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
terms=[x for x in a.query.lower().split() if x]; clauses=[];args=[]
for term in terms:
    clauses.append("lower(question) LIKE ? ESCAPE '\\'");args.append('%'+term.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')+'%')
if not terms:p.error('provide at least one word')
if a.group:clauses.append('group_id=?');args.append(a.group)
args.append(a.limit)
rows=db.execute('SELECT id,source_id,group_id,source_url,question,response,context,role,answer_identified FROM items WHERE '+' AND '.join(clauses)+' ORDER BY group_id,id LIMIT ?',args).fetchall()
print(json.dumps({'scope':'Private exact-word-substring lookup, not generated answers; printed roles are unverified attribution.','rows':[dict(r) for r in rows]},indent=2))
