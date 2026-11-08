import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_PKG||'/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs').href);
const root=process.cwd();
const base=process.env.BASE||'http://127.0.0.1:8055';
const out=process.env.BASHAR_RA_BROWSER_OUTPUT||'/workspace/channels-et-private/bashar-ra-2026-11/dashboard/browser';
await fs.mkdir(out,{recursive:true});
const files=['dist/bashar-ra/index.html','dist/bashar-ra/styles.css','dist/bashar-ra/app.js','dist/bashar-ra/data.json','dist/bashar-ra/collection.json','dist/bashar-ra/reading.json','research/bashar-ra/dashboard_check.mjs',...['paper.pdf','paper.md','paper.tex','references.bib','snapshot.json'].map(f=>'dist/bashar-ra/report/'+f)];
try{await fs.access('dist/bashar-ra/official-speech.json');files.push('dist/bashar-ra/official-speech.json');}catch{}
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const hashes=async()=>Object.fromEntries(await Promise.all(files.map(async f=>[f,hash(await fs.readFile(path.join(root,f)))])));
const before=await hashes();
const data=JSON.parse(await fs.readFile('dist/bashar-ra/data.json','utf8'));
if(data.synthetic_fixture_run===true||!Array.isArray(data.documents))throw new Error('Release browser checks require actual source-backed data');
const collection=JSON.parse(await fs.readFile('dist/bashar-ra/collection.json','utf8'));
const reading=JSON.parse(await fs.readFile('dist/bashar-ra/reading.json','utf8'));
const speech=collection.supplementary_studies?.official_speech==='official-speech.json'?JSON.parse(await fs.readFile('dist/bashar-ra/official-speech.json','utf8')):null;
const docs=data.documents;
const receipt={kind:'bashar-ra-dashboard-browser-verification',started_at:new Date().toISOString(),source_hashes_before:before,checks:[],screenshots:[],downloads:[],runtime_errors:[],scope:'Real source-backed release checks plus explicitly isolated HTTP failure/malformed-data tests; no scientific accuracy or screen-reader validation claim.'};
function check(value,label){receipt.checks.push({label,pass:!!value});if(!value)throw new Error(label);}
function csvRows(text){const rows=[];let row=[],cell='',quoted=false;for(let i=0;i<text.length;i++){const c=text[i];if(c==='"'){if(quoted&&text[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if(c==='\n'&&!quoted){row.push(cell.endsWith('\r')?cell.slice(0,-1):cell);rows.push(row);row=[];cell='';}else cell+=c;}if(cell||row.length){row.push(cell);rows.push(row);}return rows;}
const browser=await chromium.launch({headless:true,executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH||'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
async function shot(page,name,width){const file=path.join(out,name+'-'+width+'.png');await page.screenshot({path:file,fullPage:false});receipt.screenshots.push({name,width,file,sha256:hash(await fs.readFile(file))});}
async function noOverflow(page,label){check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),label);}
async function changeView(page,view){await page.locator('.view-nav a[href="#'+view+'"]').click();await page.waitForFunction(v=>document.querySelector('.view-nav a[aria-current="page"]')?.hash==='#'+v,view);}
async function download(page,button,name){const pending=page.waitForEvent('download');await button.click();const d=await pending;const file=path.join(out,name);await d.saveAs(file);const bytes=await fs.readFile(file);receipt.downloads.push({file,sha256:hash(bytes),bytes:bytes.length});return bytes;}
try{
 for(const width of [390,1440,320]){
  const context=await browser.newContext({viewport:{width,height:980},acceptDownloads:true,serviceWorkers:'block',reducedMotion:'reduce'});
  const page=await context.newPage();
  page.on('pageerror',e=>receipt.runtime_errors.push({width,type:'pageerror',message:e.message}));
  page.on('console',m=>{if(m.type()==='error')receipt.runtime_errors.push({width,type:'console',message:m.text()});});
  await page.goto(base+'/dist/bashar-ra/#overview',{waitUntil:'networkidle'});
  await page.locator('.source-pair').waitFor();
  check((await page.locator('.corpus-count b').allTextContents()).map(x=>Number(x.replaceAll(',',''))).reduce((a,b)=>a+b,0)===docs.length,`${width}: actual admitted source counts`);
  check(await page.locator('.source-pair .ra').count()===1&&await page.locator('.source-pair .bashar').count()===1,`${width}: corpora remain distinct`);
  check(await page.locator('#app').getAttribute('aria-busy')==='false',`${width}: loading state resolves`);
  await noOverflow(page,`${width}: overview reflows`);
  await shot(page,'overview',width);
  for(const img of await page.locator('#app img').all()){await img.scrollIntoViewIfNeeded();await img.evaluate(async el=>{if(!el.complete)await new Promise((resolve,reject)=>{el.onload=resolve;el.onerror=reject;});});check(await img.evaluate(el=>el.naturalWidth>0&&!!el.alt),`${width}: overview/acquisition figure loads with text alternative`);}
  for(const view of ['topics','networks','questions','sources','methods']){
   await changeView(page,view);
   check(await page.locator('#app h1').count()===1,`${width}: ${view} has one primary heading`);
   await noOverflow(page,`${width}: ${view} reflows`);
   for(const img of await page.locator('#app img').all()){
    await img.scrollIntoViewIfNeeded();await img.evaluate(async el=>{if(!el.complete)await new Promise((resolve,reject)=>{el.onload=resolve;el.onerror=reject;});});
    check(await img.evaluate(el=>el.naturalWidth>0&&!!el.alt),`${width}: ${view} figure loads with text alternative`);
   }
   if(view==='topics'&&speech){
    await page.locator('[data-study="official"]').first().click();await page.locator('#speech-source-explorer').waitFor();
    check(await page.locator('.study-switch [data-study="official"]').getAttribute('aria-pressed')==='true',`${width}: separate official study is selected`);
    const studyCounts=(await page.locator('.discovery-strip b').allTextContents()).map(t=>Number(t.replaceAll(',','')));
    const expectedCounts=[speech.run_scope.expected_publications,speech.run_scope.admitted_publications,...(Number.isFinite(speech.run_scope.model_clip_units)?[speech.run_scope.model_clip_units]:[]),speech.run_scope.held_publications,speech.baseline_binding.primary_documents];check(JSON.stringify(studyCounts)===JSON.stringify(expectedCounts),`${width}: official study retains independent denominators`);
    await noOverflow(page,`${width}: official study reflows`);await shot(page,'official-study',width);
    for(const img of await page.locator('#app img').all()){await img.scrollIntoViewIfNeeded();await img.evaluate(async el=>{if(!el.complete)await new Promise((resolve,reject)=>{el.onload=resolve;el.onerror=reject;});});check(await img.evaluate(el=>el.naturalWidth>0&&!!el.alt),`${width}: official figure loads with text alternative`);}
    const official=speech.documents.filter(d=>!['ra_published','bashar_context'].includes(d.stratum)),sample=official.at(-1);
    if(sample){
     await page.locator('#speech-query').fill(sample.source_id);check(await page.locator('#speech-source-explorer .source-table tbody tr').count()===1,`${width}: official source search`);
     await page.locator('#speech-source-explorer [data-source]').first().click();check((await page.locator('#source-title').textContent())===sample.title,`${width}: official source provenance dialog`);await page.keyboard.press('Escape');
     await page.locator('#speech-query').fill('zz-no-official-publication-9832');check(Number(await page.locator('.speech-result-count strong').textContent())===0,`${width}: official empty search is explicit`);await page.locator('#speech-query').fill('');
     await page.locator('#speech-stratum').selectOption(sample.stratum);check(Number(await page.locator('.speech-result-count strong').textContent())===official.filter(d=>d.stratum===sample.stratum).length,`${width}: official stratum filter`);await page.locator('#speech-stratum').selectOption('all');
     const nextOfficial=page.locator('.speech-pager button').last();if(await nextOfficial.isEnabled()){await nextOfficial.click();check((await page.locator('.speech-pager span').textContent()).startsWith('Page 2 '),`${width}: official source pagination`);}
     await page.locator('#speech-projection-source').selectOption(sample.source_id);
     const representations={lexical_full:speech.lexical.full_projection,lexical_window:speech.lexical.window_400_projection,semantic_full:speech.semantic,semantic_window:speech.semantic.window_400};
     for(const selected of [sample,official.find(d=>d.included_in_model===false)].filter(Boolean)){await page.locator('#speech-projection-source').selectOption(selected.source_id);for(const [key,fit] of Object.entries(representations)){if(!fit)continue;await page.locator('#speech-representation').selectOption(key);const expected=fit.nearest_baseline_sources.find(r=>r.source_id===(selected.model_unit_source_id||selected.source_id))?.neighbors.length||0;check(await page.locator('#speech-neighbors .source-table [data-source]').count()===expected,`${width}: ${key} uses exact source or alias-representative projection`);}}
    }
    await page.locator('.study-switch [data-study="baseline"]').click();check(await page.locator('.keyword-bars').count()===1,`${width}: returning to baseline keeps its primary comparison`);
   }
  }
  await changeView(page,'sources');
  const target=docs.find(d=>d.corpus==='ra'&&/106/.test(d.title))||docs.at(-1);
  await page.locator('#source-query').fill(target.source_id);
  check(await page.locator('.source-table [data-source]').count()===1,`${width}: exact source search`);
  check(await page.locator('.source-table [data-source]').first().getAttribute('data-source')===target.source_id,`${width}: search identity retained`);
  await page.locator('.source-table [data-source]').first().click();
  check(await page.locator('#source-dialog').evaluate(el=>el.open),`${width}: native source dialog opens`);
  check((await page.locator('#source-title').textContent())===target.title,`${width}: dialog title matches source`);
  check(await page.evaluate(()=>document.activeElement?.id==='close-source'),`${width}: initial dialog focus`);
  for(let i=0;i<7;i++){await page.keyboard.press('Tab');check(await page.evaluate(()=>document.querySelector('#source-dialog').contains(document.activeElement)),`${width}: modal Tab focus remains contained ${i+1}`);}
  await page.keyboard.press('Escape');
  check(!(await page.locator('#source-dialog').evaluate(el=>el.open)),`${width}: Escape closes source dialog`);
  check(await page.evaluate(id=>document.activeElement?.dataset.source===id,target.source_id),`${width}: source focus restored`);
  await page.locator('#source-query').fill('zz-no-matching-source-982134');
  check((await page.locator('.table-wrap').first().textContent()).includes('No records match this selection.'),`${width}: empty search is explicit`);
  await page.locator('#clear-filters').click();
  check(await page.evaluate(()=>document.activeElement?.id==='source-query'),`${width}: clearing filters restores search focus`);
  await page.locator('#source-corpus').selectOption('ra');
  check(Number(await page.locator('.result-summary strong').textContent())===docs.filter(d=>d.corpus==='ra').length,`${width}: corpus filter denominator`);
  const next=page.locator('.pager button').last();if(await next.isEnabled()){await next.click();check((await page.locator('.pager span').textContent()).startsWith('Page 2 '),`${width}: source pagination`);check(await page.evaluate(()=>!!document.activeElement?.closest('.pager')),`${width}: pagination preserves keyboard focus`);}
  const exported=await download(page,page.locator('#export-sources'),'sources-'+width+'.csv');
  const rows=csvRows(exported.toString('utf8'));
  check(rows.length===docs.filter(d=>d.corpus==='ra').length+1,`${width}: CSV exports all filtered records, not only visible page`);
  check(rows.slice(1).every(r=>r[1]==='ra'),`${width}: CSV corpus identities`);
  await page.locator('#source-corpus').selectOption('all');
  const format=docs.find(d=>d.corpus==='bashar'&&d.source_format)?.source_format;
  if(format){await page.locator('#source-format').selectOption(format);check(Number(await page.locator('.result-summary strong').textContent())===docs.filter(d=>d.source_format===format).length,`${width}: format filter keeps its own denominator`);}
  await shot(page,'sources',width);
  await changeView(page,'networks');
  await page.locator('.skip-link').focus();await page.keyboard.press('Enter');check(await page.evaluate(()=>document.activeElement?.id==='main'&&location.hash==='#networks'),`${width}: skip link preserves current view and focuses main`);
  const variant=await page.locator('#network-variant').inputValue();const fit=data.lexical.variants[variant];
  check(await page.locator('[data-node]').count()===fit.source_ids.length,`${width}: graph contains only fitted primary sources`);
  const id=fit.source_ids[0];await page.locator('#network-source').selectOption(id);
  check((await page.locator('.network-detail h3').textContent())===docs.find(d=>d.source_id===id).title,`${width}: accessible graph source selector`);
  check(await page.locator('[data-node][aria-pressed="true"]').count()===1,`${width}: selected graph node state`);
  await page.locator('#network-threshold').focus();await page.keyboard.press('Home');
  check(await page.locator('#network-threshold').inputValue()==='0',`${width}: keyboard threshold control`);
  check(await page.evaluate(()=>document.activeElement?.id==='network-threshold'),`${width}: threshold redraw preserves focus`);
  const edges=await download(page,page.locator('#export-edges'),'edges-'+width+'.csv');
  check(csvRows(edges.toString('utf8')).length>1,`${width}: real fitted edge export`);
  await page.locator('#network-corpus').selectOption('bashar');
  const corpusIDs=fit.source_ids.filter(id=>docs.find(d=>d.source_id===id)?.corpus==='bashar');
  check(await page.locator('[data-node]').count()===corpusIDs.length,`${width}: graph corpus filtering`);
  if(data.semantic?.cosine_matrix){await page.locator('#network-variant').selectOption('semantic_embeddings');check(await page.locator('[data-node]').count()===data.semantic.source_ids.filter(id=>docs.find(d=>d.source_id===id)?.corpus==='bashar').length,`${width}: semantic network uses actual fitted sources`);}
  await shot(page,'network',width);
  await changeView(page,'questions');
  check(await page.locator('.theme-comparison').count()===(reading.comparisons||[]).length,`${width}: actual qualitative reading count`);
  check(await page.locator('.retrieval-review').count()===(reading.followup?.retrieval_reviews||[]).length,`${width}: actual retrieval-review count`);
  check(await page.locator('.excerpt-claim').count()===(reading.followup?.official_excerpt?.claims||[]).length,`${width}: actual official excerpt reading count`);
  await shot(page,'questions',width);
  await context.close();
 }
 // A 1440px viewport at 200% CSS text enlargement checks wrapping separately from the 320px reflow check.
 const zoomContext=await browser.newContext({viewport:{width:1440,height:1000},serviceWorkers:'block'});const zoom=await zoomContext.newPage();
 await zoom.goto(base+'/dist/bashar-ra/#sources',{waitUntil:'networkidle'});await zoom.locator('.source-table').waitFor();
 await zoom.addStyleTag({content:'html{font-size:200%} body{font-size:30px}'});await noOverflow(zoom,'200% body text enlargement: source view has no page-wide overflow');
 check(await zoom.locator('#source-query').isVisible(),'200% body text enlargement: search remains available');await shot(zoom,'text-enlargement',1440);await zoomContext.close();
 // Controlled failure is isolated by interception; no source fixture is written to the public directory.
 const failureContext=await browser.newContext({viewport:{width:390,height:900},serviceWorkers:'block'});const failure=await failureContext.newPage();
 await failure.route('**/bashar-ra/data.json',route=>route.fulfill({status:503,contentType:'application/json',body:'{"error":"isolated browser failure test"}'}));
 await failure.goto(base+'/dist/bashar-ra/#overview');await failure.locator('#retry-load').waitFor();
 check((await failure.locator('.error-panel').textContent()).includes('analysis file is unavailable'),'Controlled HTTP failure: readable recovery state');
 await failure.unroute('**/bashar-ra/data.json');await failure.locator('#retry-load').click();await failure.locator('.source-pair').waitFor();check(await failure.locator('.error-panel').count()===0,'Retry recovers with real source data');
 await failureContext.close();
 const invalidContext=await browser.newContext({viewport:{width:390,height:900},serviceWorkers:'block'});const invalid=await invalidContext.newPage();
 await invalid.route('**/bashar-ra/data.json',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({...data,synthetic_fixture_run:true})}));
 await invalid.goto(base+'/dist/bashar-ra/#overview');await invalid.locator('.error-panel').waitFor();check((await invalid.locator('.error-panel').textContent()).includes('Synthetic test data is not an empirical research release'),'Synthetic corpus cannot render as empirical findings');await invalidContext.close();
 const assetsContext=await browser.newContext();
 for(const f of ['paper.pdf','paper.md','paper.tex','references.bib','snapshot.json']){
  const r=await assetsContext.request.get(base+'/dist/bashar-ra/report/'+f);
  check(r.ok(),`Study report asset responds: ${f}`);
  check(hash(await r.body())===hash(await fs.readFile(path.join(root,'dist/bashar-ra/report',f))),`Study report response matches retained bytes: ${f}`);
  await r.dispose();
 }
 await assetsContext.close();
 check(receipt.runtime_errors.length===0,'Actual release views have no runtime or console errors');
 receipt.source_hashes_after=await hashes();check(JSON.stringify(before)===JSON.stringify(receipt.source_hashes_after),'Public sources unchanged during verification');
 receipt.status='passed';
}catch(error){receipt.status='failed';receipt.failure=error.stack||error.message;process.exitCode=1;}
finally{receipt.finished_at=new Date().toISOString();await browser.close();await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');}
console.log(JSON.stringify({status:receipt.status,checks:receipt.checks.length,failures:receipt.checks.filter(x=>!x.pass),runtime_errors:receipt.runtime_errors,screenshots:receipt.screenshots.length,downloads:receipt.downloads.length,failure:receipt.failure}));
