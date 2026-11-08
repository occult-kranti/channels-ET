#!/usr/bin/env python3
"""Reproduce bounded text extraction from the privately retained council pages."""
import hashlib,html,json,re
from pathlib import Path
from html.parser import HTMLParser
BASE=Path('/workspace/channels-et-private/council-study-2026-11/galactic')
class Paragraphs(HTMLParser):
    def __init__(self):super().__init__();self.level=0;self.parts=[];self.rows=[]
    def handle_starttag(self,t,a):
        if t=='p':self.level+=1
    def handle_data(self,d):
        if self.level:self.parts.append(d)
    def handle_endtag(self,t):
        if t=='p' and self.level:
            self.level-=1
            if not self.level:
                value=' '.join(''.join(self.parts).split())
                if value:self.rows.append(value)
                self.parts=[]
def artifact(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
def main():
    rows=[]
    p=BASE/'found-3.html';parser=Paragraphs();parser.feed(p.read_text());start=next(i for i,v in enumerate(parser.rows) if v.startswith('“Greetings. We are the Arcturian Council.'));end=next(i for i,v in enumerate(parser.rows[start:],start) if v.endswith('We are the Arcturian Council, and we have enjoyed connecting with you.”'))
    text='\n\n'.join(parser.rows[start:end+1]);dest=BASE/'daniel-galactic-council-20190327.txt';dest.write_text(text+'\n');receipt=json.loads((BASE/'found-3.json').read_text())
    rows.append({'source_id':'galactic-daniel-20190327','canonical_url':receipt['url'],'title':'A 4th Dimensional Galactic Council ∞The 9D Arcturian Council','medium_id':'daniel-scranton','medium_name':'Daniel Scranton','publisher':"Daniel Scranton’s Channeling",'council_label_exact':'The 9D Arcturian Council','discussed_council_label':'a fourth-dimensional galactic council','source_local_attribution':'direct_to_arcturian_council_not_discussed_galactic_council','corpus_kind':'council_discussion_comparison_control','published_at':'2019-03-27T08:45:53+00:00','published_at_basis':'article:published_time metadata; schema also reports equivalent2019-03-26T22:45:53-10:00','text_artifact':artifact(dest),'raw_artifact':artifact(p),'text_scope':'Complete bounded quoted publisher message from opening self-attribution through closing signature; navigation, advertisements and recommendations excluded.','words':len(text.split()),'speaker_identity_verified':False,'notes':'Narrated proposed galactic council is separate from the Arcturian speaker: source explicitly says it will not sit physically on that council. Publication instant is supported by article metadata; current related-post dates are excluded.'})
    (BASE/'text-manifest.json').write_text(json.dumps({'schema_version':1,'scope':'Bounded source-local written message extraction; claims not authenticated.','records':rows},indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'records':len(rows),'words':sum(x['words'] for x in rows)}))
if __name__=='__main__':main()
