#!/usr/bin/env python3
"""Recover separately bound publisher-written text; never assert an audio transcript."""
import argparse
import collections
from html.parser import HTMLParser
import hashlib
import json
from pathlib import Path
import re

PREFIX='Download Audio MP3\n\n'
NOTICE='This is a Channeled Message by Natalie Glasson at OmNa Sanctuary – https://omna.org'
PREFIXES=[('message_heading_and_mp3_button','Channeled Message\n\n'+PREFIX),('mp3_button',PREFIX),('audio_button','Download Audio\n\n')]
MANUALLY_READ={
 'f454daf62a808ceb7e75672c9130d52de914bff1dd3468b1481676f4069be3bc':'8837d032348c7a899b02ad1df2f6a23286c5d32ae6fa9002b0408efce66f10aa',
 '8092c4c0df670ac0af32d1ba40ebea9b714dc07fcdd77e737db2cc6dbb0a87de':'3b103470851e2dce8837665391e683454fd718560abd83b9337d57243b8bdd24',
 'e4173c8defb5ef6b7190343e70dd553fdd013b15fe3ad4a4be19628e2aae900a':'faa03e8d8b075c283c036f86c696a2b7e77a4df16b09add0ecec73c6942ad2ed',
 '082c9607092ff2d5fe65d87f88f2c2336e51fd0a3e86c25bcf6b415ba05d5862':'b5e48181f8c6b01ad716ad1839b8ad7f82562b1c6cb0f9d09d55603489742cd3',
 'd66a0b22a1c602330f4aeffb2dd8bc2b0351bb3213ed96ed0227e518d2e26cdd':'291e6960a8517624b2e713c923de0ffb24c57ec605f7c11abedd34d34bf057bf',
 'ccc563ccea1f25a590f80735533ad36c13b31376f4f8e301a8ccf37254903f77':'59e963819f827533eaf6ff36b298b18b5a98cf4cd92e5d3d4044b6ed8fa0da28',
}
def sha(b):return hashlib.sha256(b).hexdigest()
def raw_json(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

class MessageWrapper(HTMLParser):
    VOID={'area','base','br','col','embed','hr','img','input','link','meta','param','source','track','wbr'}
    BREAKS={'p','h1','h2','h3','h4','h5','h6','li','br'}
    def __init__(self,html):
        super().__init__(convert_charrefs=True);self.html=html;self.stack=[];self.parts=[];self.matches=0;self.authors=[];self.violations=[];self.interval=None
        self.line_offsets=[0];self.notice=None
        for m in re.finditer('\n',html):self.line_offsets.append(m.end())
    def character_offset(self):
        line,col=self.getpos();return self.line_offsets[line-1]+col
    def handle_starttag(self,tag,attrs):
        a=dict(attrs);active=self.stack[-1][1] if self.stack else False
        if tag=='meta' and a.get('property')=='article:author':self.authors.append(a.get('content','').strip())
        if a.get('data-id')=='342945a':
            self.matches+=1
            if a.get('data-widget_type')!='theme-post-content.default':self.violations.append('wrong_wrapper_widget_type')
            if active:self.violations.append('nested_wrapper')
            active=True;self.interval=[self.character_offset(),None]
        if active:
            if tag in {'nav','footer','aside','form','script','style'}:self.violations.append('unexpected_'+tag+'_within_message')
            if any(x in a.get('class','') for x in ['post-comments','post-navigation','nav-menu']):self.violations.append('navigation_or_comments_inside_message')
            if tag in self.BREAKS:self.parts.append('\n')
        if tag not in self.VOID:self.stack.append((tag,active,a.get('data-id')=='342945a'))
    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        if tag not in self.VOID:self.handle_endtag(tag)
    def handle_endtag(self,tag):
        if not self.stack:return
        if self.stack[-1][1] and tag in self.BREAKS:self.parts.append('\n')
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag:
                if self.stack[i][2]:self.interval[1]=self.html.find('>',self.character_offset())+1
                del self.stack[i:];return
    def handle_data(self,text):
        if self.stack and self.stack[-1][1]:self.parts.append(text)
    def extract(self):
        if self.matches!=1:raise ValueError('wrapper_count_not_one')
        if self.authors!=['Natalie Glasson']:raise ValueError('explicit_author_metadata_not_unique_Natalie_Glasson')
        if self.violations:raise ValueError(';'.join(sorted(set(self.violations))))
        if not self.interval or self.interval[1] is None:raise ValueError('wrapper_unclosed')
        paragraphs=[' '.join(p.split()) for p in ''.join(self.parts).split('\n')]
        selected='\n\n'.join(p for p in paragraphs if p)
        matches=[(variant,prefix) for variant,prefix in PREFIXES if selected.startswith(prefix)]
        if len(matches)!=1:raise ValueError('initial_audio_button_paragraph_mismatch')
        variant,prefix=matches[0];end=len(selected)
        if variant=='message_heading_and_mp3_button':
            marker='\n\n'+NOTICE
            if selected.count(marker)!=1:raise ValueError('publisher_notice_boundary_not_unique')
            end=selected.index(marker);self.notice=selected[end+2:]
            notice_paragraphs=self.notice.split('\n\n')
            if len(notice_paragraphs) not in {2,3} or notice_paragraphs[0]!=NOTICE or notice_paragraphs[1]!='The above must be included on any reproduction of this material' or (len(notice_paragraphs)==3 and not notice_paragraphs[2].startswith('Find out more about ')):raise ValueError('publisher_notice_shape_unreviewed')
        elif NOTICE in selected:raise ValueError('unexpected_publisher_notice_variant')
        body=selected[len(prefix):end]
        if not 50<=len(body.split())<=5000:raise ValueError('message_length_outside_structural_review_bounds')
        if any(p in body.split('\n\n') for p in ['Download Audio MP3','Share with friends:','Leave a Reply Cancel reply','Home Page']):raise ValueError('unexpected_boilerplate_paragraph')
        return body,{'selector':'[data-id="342945a"][data-widget_type="theme-post-content.default"]','wrapper_html_char_interval':self.interval,'wrapper_html_sha256':sha(self.html[self.interval[0]:self.interval[1]].encode()),'template_variant':variant,'removed_exact_initial_paragraph':prefix.strip(),'selected_normalized_char_interval':[len(prefix),end],'publisher_notice_sha256':sha(self.notice.encode()) if self.notice else None,'publisher_notice_char_interval':[end+2,len(selected)] if self.notice else None,'publisher_notice_preserved_privately':self.notice is not None,'publisher_author':'Natalie Glasson','author_basis':'unique article:author metadata, not a visible attribution paragraph'}


def produce(selection,output):
    output=Path(output)
    if (output/'output-manifest.json').exists():raise ValueError('Refusing to overwrite frozen recovery edition')
    (output/'private'/'texts').mkdir(parents=True,exist_ok=True)
    selection=Path(selection);source_raw=selection.read_bytes();data=json.loads(source_raw);public=[];private=[]
    for c in data['candidates']:
        row={k:c.get(k) for k in ['record_id','title','page_url','page_sha256','audio_url','youtube_ids']}
        row.update({'original_text_status':c.get('text_status'),'status':'written_message_pending','human_validated':False,'audio_equivalence':'not_established','text_origin':'publisher_written_message_not_ASR','no_youtube_download_claim':True})
        try:
            raw=Path(c['page_artifact']).read_bytes()
            if sha(raw)!=c['page_sha256']:raise ValueError('source_page_hash_mismatch')
            if len(raw)!=c['page_bytes']:raise ValueError('source_page_bytes_mismatch')
            html=raw.decode('utf-8');p=MessageWrapper(html);p.feed(html);p.close();body,locator=p.extract();body_raw=body.encode();digest=sha(body_raw)
            if c['page_sha256'] in MANUALLY_READ and digest!=MANUALLY_READ[c['page_sha256']]:raise ValueError('manually_read_message_body_changed')
            relative='private/texts/'+c['record_id']+'.txt';(output/relative).write_bytes(body_raw)
            row.update({'status':'publisher_written_message_recovered','body_sha256':digest,'body_bytes':len(body_raw),'words':len(body.split()),'locator':locator,
                        'reading_status':'manual_AI_complete_selected_message_reading' if c['page_sha256'] in MANUALLY_READ else 'automatic_structural_extraction_not_close_read',
                        'full_body_manually_read_by_ai':c['page_sha256'] in MANUALLY_READ,
                        'language_basis':'English message actually read by AI' if c['page_sha256'] in MANUALLY_READ else 'English publisher context; this message not individually language-validated',
                        'closing_status':'Entire selected message retained including its ending; no separate speaker or response boundary inferred'})
            notice_ref=None
            if p.notice is not None:
                notice_relative='private/texts/'+c['record_id']+'-publisher-notice.txt';notice_raw=p.notice.encode();(output/notice_relative).write_bytes(notice_raw);notice_ref={'file':notice_relative,'bytes':len(notice_raw),'sha256':sha(notice_raw)}
            private.append({**row,'publisher_notice_artifact':notice_ref,'body_artifact':{'file':relative,'bytes':len(body_raw),'sha256':digest},'source_page_artifact':c['page_artifact']})
        except (ValueError,OSError,UnicodeError) as e:
            row['hold_reason']=str(e) if type(e) is ValueError else 'source_page_read_or_decode_failure_'+type(e).__name__;row['reading_status']='not_read_not_recovered';row['full_body_manually_read_by_ai']=False
            private.append({**row,'source_page_artifact':c.get('page_artifact')})
        public.append(row)
    result={'schema_version':1,'module':'publisher_text_recovery','selection_binding':{'file':selection.name,'bytes':len(source_raw),'sha256':sha(source_raw)},
            'producer_sha256':sha(Path(__file__).read_bytes()),'records':public,
            'counts':{'attempted':len(public),'recovered':sum(x['status']=='publisher_written_message_recovered' for x in public),'pending':sum(x['status']=='written_message_pending' for x in public),'manually_read_messages':sum(x['full_body_manually_read_by_ai'] for x in public),'recovered_words':sum(x.get('words',0) for x in public)},
            'limits':['Separate supplementary publisher text edition; original audio records and their pending-text observations are preserved.',
                      'Join only exact record_id, page_url and page_sha256. Co-location is not waveform or YouTube transcript equivalence.',
                      'Six full selected messages read by AI; remaining recovered bodies are structurally checked automatic extractions, not human or manual semantic validation.',
                      'Claims in spiritual messages are attributed source content, not authenticated entities or validated advice.']}
    public_raw=raw_json(result);(output/'publisher-text-recovery.json').write_bytes(public_raw)
    private_raw=raw_json({'schema_version':1,'records':private,'public_sha256':sha(public_raw)});(output/'private-manifest.json').write_bytes(private_raw)
    manifest={'schema_version':1,'public_allowlist':[{'file':'publisher-text-recovery.json','bytes':len(public_raw),'sha256':sha(public_raw)}],
              'private_manifest':{'file':'private-manifest.json','bytes':len(private_raw),'sha256':sha(private_raw)}}
    (output/'output-manifest.json').write_bytes(raw_json(manifest));return result['counts']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--selection',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();print(json.dumps(produce(a.selection,a.output)))
