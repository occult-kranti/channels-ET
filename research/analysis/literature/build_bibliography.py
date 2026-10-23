#!/usr/bin/env python3
"""Render the checked bibliography; bibliography.json is the canonical source register.
No network access, source claims or execution-status changes occur in this renderer.
"""
import csv,json,pathlib
p=pathlib.Path(__file__).resolve().parent
d=json.loads((p/'bibliography.json').read_text());sources=d['papers'];repos=d['repositories']
fields=['id','title','authors','date','url','kind','readingDepth','summary','application','limitations','executionStatus']
with (p/'bibliography.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(sources)
lines=['# Primary literature and open-source methods','',f"Checked {d['checkedAt']}. This targeted review contains {len(sources)} academic sources and {len(repos)} implementation repositories. It does not claim exhaustive literature coverage or a current universal best model. Reading depth and access limits are explicit.",'']
for x in sources:
 lines += [f"## {x['id']} — {x['title']}",'',f"{x['authors']} ({x['date']}). [{x['kind']}]({x['url']}).",'',f"**Read:** {x['readingDepth']}. {x['summary']}",'',f"**Use here:** {x['application']}",'',f"**Limit:** {x['limitations']}",'']
 if x.get('supplementUrl'):lines += [f"[Inspected supplement]({x['supplementUrl']}). See the supplement manifest and round reviews for precise access and replication limits.",'']
lines += ['## Open-source repositories','']
for x in repos:lines += [f"- [{x['name']}]({x['url']}): {x['use']} Read: {x['readingDepth']}. Status: {x['executionStatus']}. {x['license']}."]
(p/'literature-review.md').write_text('\n'.join(lines))
print(f'Rendered {len(sources)} papers and {len(repos)} repositories from checked source register.')
