import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {chromium} from '/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';

const base=process.env.BASE||'http://127.0.0.1:8765';
const out=process.env.COUNCIL_BROWSER_OUTPUT||'/workspace/channels-et-private/council-study-2026-11/browser-final-01';
const root='dist/council-study/';
await fs.mkdir(out,{recursive:true});
const html=await fs.readFile(root+'index.html','utf8');
const config=JSON.parse(html.match(/<script id="data-files" type="application\/json">([\s\S]*?)<\/script>/)[1]);
const analysis=JSON.parse(await fs.readFile(root+config.analysis,'utf8'));
const registers=await Promise.all(config.registers.map(async file=>JSON.parse(await fs.readFile(root+file,'utf8'))));
const acquisition=config.acquisition?JSON.parse(await fs.readFile(root+config.acquisition,'utf8')):null;
const documents=analysis.documents;
const sources=[...new Map(registers.flatMap(r=>r.sources||[]).map(s=>[s.source_id||s.id,s])).values()];
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const inputs=['index.html','styles.css','app.js','../channeling-network/styles.css',config.analysis,...config.registers,...(config.acquisition?[config.acquisition]:[]),...analysis.figures.map(f=>'figures/'+f.file)].map(f=>root+f);
const hashes=async()=>Object.fromEntries(await Promise.all(inputs.map(async p=>[p,hash(await fs.readFile(p))])));
const receipt={kind:'council-study-actual-data-browser-check',started_at:new Date().toISOString(),source_hashes_before:await hashes(),checks:[],screenshots:[],downloads:[],runtime_errors:[],scope:'Actual public source/analysis snapshots in Chromium at320/390/1440px, keyboard, exports, source inspectors and source-reading controls. Controlled failed requests/flags are separate interface tests, never public observations. CSSzoom is not a native browser zoom or screen-reader certification.'};
function check(ok,label){receipt.checks.push({label,pass:!!ok});if(!ok)throw Error(label);}
const n=s=>Number(String(s).replaceAll(',',''));
const csvOriginal=s=>/^'[=+\-@]/.test(s)?s.slice(1):s;
function csv(s){const rows=[],row=[];let c='',quoted=false;for(let i=0;i<s.length;i++){const x=s[i];if(x==='"'){if(quoted&&s[i+1]==='"'){c+='"';i++;}else quoted=!quoted;}else if(x===','&&!quoted){row.push(c);c='';}else if(x==='\n'&&!quoted){row.push(c.replace(/\r$/,''));rows.push([...row]);row.length=0;c='';}else c+=x;}return rows;}
async function download(p,selector,name,width){const pending=p.waitForEvent('download');await p.locator(selector).click();const d=await pending,f=path.join(out,name+'-'+width+'.csv');await d.saveAs(f);const b=await fs.readFile(f);receipt.downloads.push({file:f,bytes:b.length,sha256:hash(b)});return csv(b.toString().replace(/^\ufeff/,''));}
async function screenshot(p,name,width){const f=path.join(out,name+'-'+width+'.png');await p.screenshot({path:f});receipt.screenshots.push({file:f,sha256:hash(await fs.readFile(f))});}
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
try{
  check(analysis.synthetic_fixture_run!==true&&!registers.some(r=>r.synthetic_fixture_run===true),'Public release is observed data, not a fixture');
  check(documents.length===analysis.coverage.documents,'Public document count equals source records');
  check(new Set(documents.map(d=>d.source_id)).size===documents.length,'Unique analyzed source IDs');
  for(const width of [320,390,1440]){
    const context=await browser.newContext({viewport:{width,height:980},acceptDownloads:true,serviceWorkers:'block',reducedMotion:'reduce'}),p=await context.newPage();
    p.on('pageerror',e=>receipt.runtime_errors.push({width,message:e.message}));p.on('console',m=>{if(m.type()==='error')receipt.runtime_errors.push({width,message:m.text()});});
    await p.goto(base+'/'+root,{waitUntil:'networkidle'});await p.locator('#message-results').waitFor();
    check(n(await p.locator('#metric-documents').textContent())===documents.length,`${width}: actual study document denominator`);
    check(await p.locator('h1').count()===1,`${width}: one primary heading`);
    check(await p.locator('#app').getAttribute('aria-busy')==='false',`${width}: loading state resolves`);
    check(await p.locator('.problem-note').count()===0,`${width}: all declared data resources loaded`);
    check(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${width}: initial page reflow`);
    await p.keyboard.press('Tab');check(await p.evaluate(()=>document.activeElement.classList.contains('skip-link')),`${width}: keyboard skip link first`);
    check(await p.evaluate(()=>getComputedStyle(document.activeElement).outlineStyle!=='none'),`${width}: visible keyboard focus`);
    await screenshot(p,'overview',width);
    const exported=await download(p,'#export-messages','messages',width);
    check(exported.length===documents.length+1,`${width}: complete metadata export rather than visible page`);
    check(JSON.stringify(exported.slice(1).map(r=>csvOriginal(r[0])))===JSON.stringify(documents.map(d=>d.source_id)),`${width}: exported source order/identity`);
    const first=documents[0];await p.locator('#message-query').fill(first.source_id);
    check(n(await p.locator('#message-count').textContent())===documents.filter(d=>[d.source_id,d.title,d.medium,d.council_label_exact,d.text_origin].join(' ').toLocaleLowerCase().includes(first.source_id.toLocaleLowerCase())).length,`${width}: real source-ID search`);
    await p.locator('#message-results [data-inspect]').first().click();
    check(await p.locator('#source-dialog').evaluate(el=>el.open),`${width}: evidence inspector opens`);
    check(await p.evaluate(()=>document.activeElement.id==='close-source'),`${width}: dialog initial focus`);
    check((await p.locator('#source-detail').textContent()).includes(first.text_artifact_sha256||first.text_sha256),`${width}: inspector exposes actual source hash`);
    for(let i=0;i<8;i++){await p.keyboard.press('Tab');check(await p.evaluate(()=>!document.hasFocus()||document.querySelector('#source-dialog').contains(document.activeElement)),`${width}: modal page focus stays inside dialog; browser chrome remains reachable ${i+1}`);}
    await screenshot(p,'source-inspector',width);await p.keyboard.press('Escape');
    check(await p.evaluate(()=>document.activeElement.dataset.inspect!==undefined),`${width}: Escape restores source trigger`);
    await p.locator('#message-query').fill('zz-no-matching-research-source-zz');check(n(await p.locator('#message-count').textContent())===0,`${width}: honest empty search`);
    await p.locator('#clear-messages').click();check(n(await p.locator('#message-count').textContent())===documents.length,`${width}: clear restores frame`);
    for(const id of [...new Set(documents.map(d=>d.medium_id))]){
      await p.locator('#message-medium').selectOption(id);check(n(await p.locator('#message-count').textContent())===documents.filter(d=>d.medium_id===id).length,`${width}: medium filter ${id}`);
    }
    await p.locator('#clear-messages').click();
    for(const name of [...new Set(documents.map(d=>d.council_label_exact))]){
      await p.locator('#message-council').selectOption(name);check(n(await p.locator('#message-count').textContent())===documents.filter(d=>d.council_label_exact===name).length,`${width}: exact-name filter ${name}`);
    }
    await p.locator('#clear-messages').click();
    for(const origin of [...new Set(documents.map(d=>d.text_origin))]){
      await p.locator('#message-origin').selectOption(origin);check(n(await p.locator('#message-count').textContent())===documents.filter(d=>d.text_origin===origin).length,`${width}: text-origin filter ${origin}`);
    }
    await p.locator('#clear-messages').click();
    const mapNode=p.locator('[data-map-council]').first(),mapName=await mapNode.getAttribute('data-map-council');await mapNode.focus();await p.keyboard.press('Enter');
    check(await p.locator('#message-council').inputValue()===mapName,`${width}: keyboard map link filters exact label`);
    check(n(await p.locator('#message-count').textContent())===documents.filter(d=>d.council_label_exact===mapName).length,`${width}: map count matches selected texts`);
    await p.locator('#clear-messages').click();
    if(analysis.lexical.status==='fitted'){
      for(const mode of ['whole','window']){
        await p.locator('#matrix-mode').selectOption(mode);
        const ids=mode==='whole'?analysis.lexical.source_ids:analysis.lexical.window_300_source_ids,matrix=mode==='whole'?analysis.lexical.matrix:analysis.lexical.window_300_matrix;
        if(!ids.length){check((await p.locator('#matrix-results').textContent()).includes('No texts satisfy'),`${width}: empty length subset explicit`);continue;}
        const size=ids.length>40?20:ids.length;
        check(await p.locator('#matrix-results tbody tr').count()===size,`${width}: ${mode} bounded matrix rows`);
        const cells=await p.locator('#matrix-results tbody tr').all();
        for(let i=0;i<cells.length;i++){
          check(await cells[i].locator('[data-inspect]').getAttribute('data-inspect')===ids[i],`${width}: ${mode} matrix row identity ${i}`);
          const values=await cells[i].locator('td').allTextContents();
          for(let j=0;j<values.length;j++)check(Math.abs(n(values[j])-matrix[i][j])<=.00051,`${width}: ${mode} actual cosine ${i},${j}`);
        }
        const full=await download(p,'#export-matrix','matrix-'+mode,width);check(full.length===ids.length*ids.length+1,`${width}: ${mode} full matrix export size`);
        for(let i=1;i<full.length;i++){const [a,b,value]=full[i],ai=ids.indexOf(csvOriginal(a)),bi=ids.indexOf(csvOriginal(b));check(ai>=0&&bi>=0&&Math.abs(Number(value)-matrix[ai][bi])<1e-10,`${width}: ${mode} exported source pair ${i}`);}
        if(ids.length>40){await p.locator('#matrix-rows').selectOption('1');await p.locator('#matrix-columns').selectOption('1');check(await p.locator('#matrix-results tbody [data-inspect]').first().getAttribute('data-inspect')===ids[20],`${width}: next matrix block preserves global IDs`);}
      }
      await p.locator('#matrix-mode').selectOption('whole');
      for(const kind of ['all','cross','same-label']){
        await p.locator('#pair-kind').selectOption(kind);const expected=analysis.lexical.pairs.filter(r=>kind==='all'||(kind==='cross'?!r.same_medium:!r.same_medium&&r.same_exact_label));
        check((await p.locator('#pair-results>.caption').textContent()).startsWith(expected.length.toLocaleString('en-GB')+' eligible pairs'),`${width}: ${kind} pair denominator`);
      }
      await screenshot(p,'comparisons',width);
    }
    for(const key of Object.keys(analysis.keywords?.dictionary||{})){
      await p.locator('#keyword-name').selectOption(key);const trs=await p.locator('#keyword-results tbody tr').all();
      check(trs.length===analysis.keywords.rows.length,`${width}: keyword row count ${key}`);
      for(const tr of trs){const id=await tr.locator('[data-inspect]').getAttribute('data-inspect'),row=analysis.keywords.rows.find(r=>r.source_id===id),cells=await tr.locator('td').allTextContents();check(n(cells[1])===row.counts[key],`${width}: keyword actual count ${id}/${key}`);check(Math.abs(n(cells[2])-row.rates[key])<=.00051,`${width}: keyword actual rate ${id}/${key}`);}
    }
    const readingRows=analysis.reading?.reading_matrix?.rows||[],dimensions=[...new Set(readingRows.flatMap(r=>Object.keys(r.cells)))];
    for(const dimension of dimensions){await p.locator('#reading-dimension').selectOption(dimension);check(await p.locator('#qualitative-results tbody tr').count()===readingRows.length,`${width}: qualitative source rows ${dimension}`);const text=await p.locator('#qualitative-results').textContent();for(const r of readingRows)check(text.includes(r.cells[dimension].summary),`${width}: exact bounded paraphrase ${r.source_id}/${dimension}`);}
    if(readingRows.length){await p.locator('#qualitative-results summary').first().click();check((await p.locator('#qualitative-results').textContent()).includes('audio alignment')||(await p.locator('#qualitative-results').textContent()).includes('alignment unverified'),`${width}: source reading alignment limit`);const rows=await download(p,'#export-readings','readings',width);check(rows.length===readingRows.reduce((n,r)=>n+Object.keys(r.cells).length,0)+1,`${width}: complete reading-cell export`);await screenshot(p,'source-readings',width);}
    for(const reading of analysis.supplemental_readings||analysis.reading?.supplemental_readings||[]){const card=p.locator('[data-reading-source='+JSON.stringify(reading.source_id)+']');check(await card.count()===1,`${width}: supplemental source reading ${reading.source_id}`);const text=await card.textContent();for(const observation of reading.observations){check(text.includes(observation.paraphrase),`${width}: exact supplemental observation ${reading.source_id}/${observation.id}`);if(observation.qualifying_note)check(text.includes(observation.qualifying_note),`${width}: supplemental qualification ${reading.source_id}/${observation.id}`);}check(text.includes(reading.text_artifact_sha256),`${width}: supplemental reading text hash ${reading.source_id}`);}
    for(const review of analysis.lexical_retrieval?.context_reviews||[]){const card=p.locator('.context-reviews article').filter({hasText:review.source_id});check(await card.count()===1,`${width}: earlier mention-context source ${review.source_id}`);check((await card.textContent()).includes(review.paraphrase),`${width}: exact bounded context reading ${review.source_id}`);check((await card.textContent()).includes(review.context_sha256),`${width}: context provenance hash ${review.source_id}`);}
    if(acquisition){check(n(await p.locator('#audio-retained').textContent())===acquisition.summary.completed_publications,`${width}: actual retained audio count`);check(await p.locator('.collection-table tbody tr').count()===acquisition.records.length,`${width}: actual audio receipt rows`);const rows=await download(p,'#export-acquisition','audio',width);check(rows.length===acquisition.records.length+1,`${width}: complete audio export`);check(JSON.stringify(rows.slice(1).map(r=>csvOriginal(r[0])))===JSON.stringify(acquisition.records.map(r=>r.publication_id)),`${width}: audio export source identities`);await screenshot(p,'collection',width);}
    check(n(await p.locator('#source-count').textContent())===sources.length,`${width}: unique research source count`);
    const firstSource=sources[0];await p.locator('#source-query').fill(firstSource.source_id||firstSource.id);check(n(await p.locator('#source-count').textContent())>=1,`${width}: source search works`);await p.locator('#source-results [data-inspect]').first().click();check(await p.locator('#source-dialog').evaluate(el=>el.open),`${width}: research source inspector`);await p.locator('#close-source').click();
    if(width===1440){for(const item of sources.filter(s=>typeof s.notes==='string'&&s.notes)){const id=item.source_id||item.id;await p.locator('#source-query').fill(id);await p.locator('#source-results [data-inspect='+JSON.stringify(id)+']').click();check((await p.locator('#source-detail').textContent()).includes(item.notes),`Research source qualifications preserved: ${id}`);if(typeof item.paraphrase==='string')check((await p.locator('#source-detail').textContent()).includes(item.paraphrase),`Research source paraphrase separately retained: ${id}`);await p.locator('#close-source').click();}}
    if(width===1440){for(const d of documents.filter(d=>d.primary_source_id)){const primary=sources.find(s=>(s.source_id||s.id)===d.primary_source_id);await p.locator('#message-query').fill(d.source_id);await p.locator('#message-results [data-inspect]').first().click();const detail=await p.locator('#source-detail').textContent();check(detail.includes(d.primary_source_id),'ASR edition inspector exposes explicit primary source binding: '+d.source_id);if(primary?.notes)check(detail.includes(primary.notes),'Bound ASR edition preserves publisher source qualifications: '+d.source_id);await p.locator('#close-source').click();await p.locator('#clear-messages').click();}}
    for(const image of await p.locator('.figure img').all()){await image.scrollIntoViewIfNeeded();await image.evaluate(img=>img.complete?Promise.resolve():new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=reject;}));check(await image.evaluate(img=>img.naturalWidth>0),`${width}: actual analytical image loaded`);check((await image.getAttribute('alt')).length>15,`${width}: analytical image has descriptive alternative`);}
    check(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${width}: all content reflows without document overflow`);
    check(await p.locator('input,select').evaluateAll(xs=>xs.every(x=>parseFloat(getComputedStyle(x).fontSize)>=16))||width>680,`${width}: mobile form text avoids focus zoom`);
    await context.close();
  }
  const failures=await browser.newContext({serviceWorkers:'block'}),p=await failures.newPage();
  await p.route('**/council-study/analysis.json',r=>r.fulfill({status:503,body:'controlled failure'}));await p.goto(base+'/'+root);await p.locator('.error-panel').waitFor();check(await p.locator('#metric-documents').count()===0,'Failed analysis has no invented data counts');await p.unroute('**/council-study/analysis.json');await p.locator('#retry-load').click();await p.locator('#message-results').waitFor();check(n(await p.locator('#metric-documents').textContent())===documents.length,'Retry restores actual analysis');await failures.close();
  if(acquisition){const unavailable=await browser.newContext({serviceWorkers:'block'}),u=await unavailable.newPage();await u.route('**/council-study/acquisition.json',r=>r.fulfill({status:503,body:'controlled unavailable receipt'}));await u.goto(base+'/'+root);await u.locator('#message-results').waitFor();check(n(await u.locator('#metric-documents').textContent())===documents.length,'Missing optional acquisition keeps actual text denominator');check(await u.locator('#audio-retained').count()===0,'Missing optional acquisition reports unknown instead of zero');for(const d of documents.filter(d=>d.primary_source_id)){await u.locator('#message-query').fill(d.source_id);await u.locator('#message-results [data-inspect]').first().click();check((await u.locator('#source-detail').textContent()).includes(d.primary_source_id),'Explicit analysis source binding remains available without optional audio receipt');await u.locator('#close-source').click();}await unavailable.close();}
  const bad=await browser.newContext(),b=await bad.newPage();await b.route('**/council-study/analysis.json',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...analysis,synthetic_fixture_run:true})}));await b.goto(base+'/'+root);await b.locator('.error-panel').waitFor();check(await b.locator('#message-results').count()===0,'Synthetic-flagged analysis is rejected');await bad.close();
  const zoomContext=await browser.newContext({viewport:{width:1440,height:980}}),z=await zoomContext.newPage();await z.goto(base+'/'+root,{waitUntil:'networkidle'});await z.locator('#message-results').waitFor();await z.evaluate(()=>document.documentElement.style.zoom='2');check(await z.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'200% CSS zoom reflow');check(await z.evaluate(()=>csvValue('=1').startsWith('"\'')&&csvValue('@name').startsWith('"\'')),'Formula-leading CSV values escaped');await zoomContext.close();
  check(receipt.runtime_errors.length===0,'No runtime or console errors in actual release views');receipt.source_hashes_after=await hashes();check(JSON.stringify(receipt.source_hashes_before)===JSON.stringify(receipt.source_hashes_after),'Actual tested source inputs unchanged');receipt.status='passed';
}catch(e){receipt.status='failed';receipt.failure=e.stack||e.message;process.exitCode=1;}finally{await browser.close();receipt.finished_at=new Date().toISOString();await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');}
console.log(JSON.stringify({status:receipt.status,checks:receipt.checks.length,screenshots:receipt.screenshots.length,downloads:receipt.downloads.length,runtime_errors:receipt.runtime_errors,failure:receipt.failure}));
