'use strict';
window.TX={data:null,state:{view:'overview',corpus:'audio',publisher:'all',context:'all',query:'',map:'network',threshold:.2,edgeRule:'nearest',labels:true,color:'cluster',overlay:false,zoom:1,selected:null,topic:'all',heatGroup:'document',qaKind:'all',qaFamily:'all',qaQuery:'',qaPage:1,storageFrame:'youtube',storageGroup:'byPublisherGroup',storageMetric:'selected_ids',storageQuery:'',storagePage:1}};
TX.u={
 esc:v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),
 num:(v,d=0)=>v==null||!Number.isFinite(+v)?'Not recorded':Number(v).toLocaleString('en-US',{maximumFractionDigits:d}),
 bytes:v=>{if(v==null)return'Not recorded';let n=+v,k=0;const units=['B','KiB','MiB','GiB','TiB'];while(n>=1024&&k<4){n/=1024;k++}return TX.u.num(n,k?2:0)+' '+units[k]},
 percent:v=>v==null?'Not recorded':TX.u.num(v*100,1)+'%',
 ny:v=>{if(!v)return'Not recorded';const d=new Date(v);return Number.isNaN(+d)?TX.u.esc(v):new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',dateStyle:'medium',timeStyle:'short'}).format(d)+' New York'},
 human:v=>String(v??'').replaceAll('_',' '),
 time:v=>{if(v==null)return'No time locator';const n=Math.max(0,Math.floor(v));return[Math.floor(n/3600),Math.floor(n/60)%60,n%60].map(x=>String(x).padStart(2,'0')).join(':')},
 sourceLink:(url,label='Original publisher source')=>/^https?:\/\//i.test(url||'')?`<a href="${TX.u.esc(url)}" target="_blank" rel="noopener">${TX.u.esc(label)} ↗</a>`:'Source URL not recorded',
 rows:x=>Array.isArray(x)?x:x?.records||x?.documents||[],
 table:(headers,rows,cls='')=>`<div class="table-wrap"><table class="${cls}"><thead><tr>${headers.map(h=>`<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.length?rows.map(r=>`<tr>${r.map(c=>`<td>${c}</td>`).join('')}</tr>`).join(''):`<tr><td colspan="${headers.length}">No source rows match this selection.</td></tr>`}</tbody></table></div>`,
 option:(value,label,current)=>`<option value="${TX.u.esc(value)}"${String(value)===String(current)?' selected':''}>${TX.u.esc(label)}</option>`,
 heading:(eyebrow,title,lede)=>`<p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="lede">${lede}</p>`,
 empty:text=>`<p class="empty">${text}</p>`,
 sourceButton:(id,label)=>`<button type="button" class="link-button" data-source="${TX.u.esc(id)}">${TX.u.esc(label)}</button>`,
 artifact:(path,label)=>TX.data.artifacts.some(a=>a.path===path)?`<a href="${TX.u.esc(path)}" download>${TX.u.esc(label)} ↓</a>`:'Artifact not bound yet',
 badge:text=>`<span class="tag">${TX.u.esc(text)}</span>`
};
TX.docs=(corpus=TX.state.corpus)=>{
 const s=TX.state,modality=corpus==='audio'?'audio_asr':'publisher_text';
 return (TX.data.analysis?.sources||[]).filter(d=>d.modality===modality&&(s.publisher==='all'||d.publisher===s.publisher)&&(s.context==='all'||d.practitionerContext===s.context)&&(!s.query||[d.title,d.publisher,d.claimedGroup,d.sourceId].join(' ').toLowerCase().includes(s.query.toLowerCase())));
};
TX.fit=()=>TX.data.analysis?.tfidf?.[TX.state.corpus];
TX.topics=()=>TX.state.corpus==='audio'?TX.data.analysis?.topics:TX.fit()?.topics;
TX.clusters=()=>TX.state.corpus==='audio'?TX.data.analysis?.clusters:TX.fit()?.clusters;
TX.currentDocs=()=>{const docs=TX.docs(),s=TX.state;if(s.topic==='all'||s.view!=='maps')return docs;const k=+s.topic,t=TX.topics();return docs.filter(d=>{const w=t?.weights.find(x=>x.sourceId===d.sourceId)?.weights||[];return w.indexOf(Math.max(...w))===k})};
TX.visibleDocs=()=>TX.currentDocs().concat(TX.state.view==='maps'&&TX.state.map==='projection'&&TX.state.corpus==='audio'&&TX.state.overlay?TX.docs('authored'):[]);
TX.source=id=>TX.data.analysis?.sources.find(d=>d.sourceId===id);
TX.edges=(docs=TX.currentDocs())=>{
 const f=TX.fit(),ids=f?.sourceIds||[],matrix=f?.cosine||[],s=TX.state,index=new Map(ids.map((id,i)=>[id,i]));
 const pairs=[];const chosen=new Set();
 if(s.edgeRule==='nearest')for(const d of docs){const i=index.get(d.sourceId);const top=docs.filter(x=>x.sourceId!==d.sourceId).map(x=>({id:x.sourceId,value:matrix[i]?.[index.get(x.sourceId)]??0})).sort((a,b)=>b.value-a.value||a.id.localeCompare(b.id)).slice(0,2);for(const x of top)if(x.value>=s.threshold)chosen.add([d.sourceId,x.id].sort().join('|'))}
 for(let i=0;i<docs.length;i++)for(let j=i+1;j<docs.length;j++){const a=docs[i].sourceId,b=docs[j].sourceId,value=matrix[index.get(a)]?.[index.get(b)]??0;if(value>=s.threshold&&(s.edgeRule==='all'||chosen.has([a,b].sort().join('|'))))pairs.push({source:a,target:b,cosine:value})}
 return pairs.sort((a,b)=>b.cosine-a.cosine);
};
TX.export=(name,rows)=>{const storage=name.includes('storage'),s=TX.state,payload={classification:'Derived source metadata; filtered dashboard export',view:s.view,corpus:storage?null:s.corpus,filters:storage?{accountingFrame:s.storageFrame,grouping:s.storageGroup,measure:s.storageMetric,labelQuery:s.storageQuery}:{publisher:s.publisher,practitionerContext:s.context,sourceQuery:s.query,dominantTopic:s.view==='maps'?s.topic:null,qaKind:s.view==='reading'?s.qaKind:null,qaFamily:s.view==='reading'?s.qaFamily:null,qaQuery:s.view==='reading'?s.qaQuery:null},displayRule:s.view==='maps'?{map:s.map,cosineThreshold:s.threshold,edgeRule:s.edgeRule,authoredReferenceOverlay:s.overlay}:null,sourceArtifactSha256:TX.data.artifacts.find(a=>a.path===(storage?'storage-distributions.json':name.includes('qa-candidates')?'reading-qa-candidates.json':'analysis.json'))?.sha256,records:rows};const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
TX.sourceDetail=id=>{
 const d=TX.source(id);if(!d)return;const u=TX.u,topic=TX.topics()?.weights.find(x=>x.sourceId===id),cluster=TX.clusters()?.labels.find(x=>x.sourceId===id);
 document.getElementById('source-dialog-title').textContent=d.title;
 const receipt=TX.data.artifacts.find(a=>a.source===d.sourceReceipt);
 document.getElementById('source-detail').innerHTML=`<p>${u.sourceLink(d.sourceUrl)}</p><dl class="detail-grid"><dt>Source ID / short ID</dt><dd>${u.esc(d.sourceId)} / ${u.esc(d.shortId)}</dd><dt>Modality / source format</dt><dd>${u.esc(u.human(d.modality))} / ${u.esc(u.human(d.sourceFormat))}</dd><dt>Publisher</dt><dd>${u.esc(d.publisher)}</dd><dt>Practitioner context</dt><dd>${u.esc(d.practitionerContext)}</dd><dt>Source-attributed label</dt><dd>${u.esc(d.claimedGroup)}</dd><dt>Common analysis tokens</dt><dd>${u.num(d.tokenCount)} · fixed shared regex tokenizer</dd><dt>Whitespace words</dt><dd>${u.num(d.words)}</dd><dt>Acquisition receipt count</dt><dd>${u.num(d.receiptWordCount)} · ${u.esc(d.receiptWordCountDefinition)}</dd><dt>Audio duration</dt><dd>${d.durationSeconds==null?'Not an audio document':u.num(d.durationSeconds/60,2)+' minutes'}</dd><dt>Original audio bytes</dt><dd>${u.bytes(d.audioBytes)}</dd><dt>Source-text SHA-256</dt><dd class="hash">${u.esc(d.transcriptSha256)}</dd><dt>Source-audio SHA-256</dt><dd class="hash">${u.esc(d.sourceAudioSha256||'Not an audio document')}</dd><dt>Speaker identity verified</dt><dd>${d.speakerVerified?'Yes':'No'}</dd><dt>YouTube edition verified</dt><dd>${d.youtubeEditionVerified?'Yes':'No'}</dd>${cluster?`<dt>Exploratory cluster</dt><dd>${u.num(cluster.cluster+1)} within the ${TX.state.corpus} fit</dd>`:''}${topic?`<dt>NMF topic shares</dt><dd>${topic.weights.map((v,i)=>`T${i+1} ${u.percent(v)}`).join(' · ')}</dd>`:''}</dl><p class="caption">A source context or publisher attribution does not identify who is speaking in an undiarized recording. Full source text and audio are not rehosted in this explorer.</p>${receipt?u.artifact(receipt.path,'Exact source acquisition/ASR metadata'):''}`;
 const dialog=document.getElementById('source-dialog');dialog.showModal();dialog.querySelector('button').focus();
};
