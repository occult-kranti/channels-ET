/** Browser checks against the actual release, optionally served through an actual-file map.
 * node browser_check.mjs --url http://127.0.0.1:8765/dist/knowledge-bank/ --out /dev/shm/.../browser
 * --release-map PRIVATE_JSON is for pre-integration review only; never generates observations.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { chromium } from '/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';

const args=Object.fromEntries(process.argv.slice(2).reduce((r,x,i,a)=>i%2===0?[...r,[x.replace(/^--/,''),a[i+1]]]:r,[]));
const url=args.url||'http://127.0.0.1:8765/dist/knowledge-bank/';
const out=args.out||'/dev/shm/channels-et-knowledge-2026-11/browser';
await fs.mkdir(out,{recursive:true});
const overrides=args['release-map']?JSON.parse(await fs.readFile(args['release-map'],'utf8')):{};
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce',acceptDownloads:true});
const page=await context.newPage(), errors=[], checks=[];
page.on('pageerror',e=>errors.push(e.message));
let mode='actual',retry=false,requiredAnalysisFile='analysis.json';
let optionalFailureFiles=new Set(['asr.json','literature-register.json','retrieval.json']);
await page.route('**/knowledge-bank/**',async route=>{
  const name=new URL(route.request().url()).pathname.split('/knowledge-bank/')[1];
  if(mode==='required-failure'&&name===requiredAnalysisFile&&!retry)return route.fulfill({status:503,body:'Temporarily unavailable'});
  if(mode==='optional-failure'&&optionalFailureFiles.has(name))return route.fulfill({status:503,body:'Temporarily unavailable'});
  if(mode==='hash-failure'&&name===requiredAnalysisFile)return route.fulfill({status:200,contentType:'application/json',body:'{}'});
  if(overrides[name])return route.fulfill({status:200,body:await fs.readFile(overrides[name]),contentType:name.endsWith('.json')?'application/json':name.endsWith('.png')?'image/png':name.endsWith('.svg')?'image/svg+xml':undefined});
  return route.continue();
});
async function check(name,fn){await fn();checks.push({name,status:'passed'});}
async function ready(){await page.goto(url);await page.waitForSelector('#metric-documents');}
async function noOverflow(){assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),true);}
async function save(name){await page.locator('img').evaluateAll(async imgs=>{await Promise.all(imgs.filter(img=>{const r=img.getBoundingClientRect();return r.bottom>0&&r.top<innerHeight;}).map(img=>img.decode().catch(()=>{})));});await page.screenshot({path:path.join(out,name+'.jpg'),type:'jpeg',quality:74});}
try{
  await ready();
  await page.locator('img').evaluateAll(async imgs=>{await Promise.all(imgs.map(async img=>{img.loading='eager';await img.decode();}));});
  const manifestText=await page.evaluate(async()=>await(await fetch('manifest.json')).text());
  const manifest=JSON.parse(manifestText);
  const moduleFile=k=>typeof manifest.modules[k]==='string'?manifest.modules[k]:manifest.modules[k].file;
  requiredAnalysisFile=moduleFile('analysis');optionalFailureFiles=new Set(['asr','literature','retrieval'].filter(k=>manifest.modules[k]).map(moduleFile));
  const [analysis,knowledge]=await page.evaluate(async files=>await Promise.all(files.map(async f=>await(await fetch(f)).json())),[moduleFile('analysis'),moduleFile('knowledge')]);
  await check('Actual source/card/question counts',async()=>{
    assert.equal(await page.locator('#metric-documents').innerText(),String(analysis.documents.length));
    assert.equal(await page.locator('#metric-questions').innerText(),String(knowledge.questions.length));
    assert.equal(await page.locator('#metric-cards').innerText(),String(knowledge.cards.length));
    assert.equal(await page.locator('#metric-comparisons').innerText(),String(knowledge.comparisons.length));
  });
  for(const width of [1440,390,320])await check(`Responsive ${width}px and readable first screen`,async()=>{await page.setViewportSize({width,height:1000});await noOverflow();await page.evaluate(()=>scrollTo(0,0));await save('overview-'+width);});
  await page.setViewportSize({width:1440,height:1000});
  await check('All filters, empty state and reset',async()=>{
    await page.locator('#question-query').fill('NO_SUCH_RELEASE_QUESTION_123');assert.equal(await page.locator('#question-count').innerText(),'0');
    await page.locator('#clear-questions').click();
    for(const [selector,field] of [['#question-topic','topic_id'],['#question-type','question_type']]){
      for(const value of [...new Set(knowledge.questions.map(q=>q[field]))]){await page.locator(selector).selectOption(value);assert.equal(await page.locator('#question-count').innerText(),String(knowledge.questions.filter(q=>q[field]===value).length));}
      await page.locator('#clear-questions').click();
    }
    await page.locator('#question-relation').selectOption('explicit_contradiction');assert.equal(await page.locator('#question-count').innerText(),String(knowledge.questions.filter(q=>knowledge.comparisons.some(c=>c.question_id===q.question_id&&c.relation==='explicit_contradiction')).length));
    await page.locator('#clear-questions').click();
    for(const value of await page.locator('#question-medium option').evaluateAll(xs=>xs.map(x=>x.value).filter(x=>x!=='all'))){await page.locator('#question-medium').selectOption(value);assert.ok(Number(await page.locator('#question-count').innerText())>0);}
    await page.locator('#clear-questions').click();
  });
  await check('Inspector keyboard, nested provenance and focus return',async()=>{
    const button=page.locator('[data-inspect-kind="card"]').first();await button.focus();await page.keyboard.press('Enter');
    assert.equal(await page.locator('#inspector').evaluate(x=>x.open),true);
    assert.match(await page.locator('#inspector-body').innerText(),/Bound source spans/);
    await page.locator('#inspector [data-inspect-kind="source"]').first().click();
    await page.keyboard.press('Escape');assert.equal(await page.locator('#inspector').evaluate(x=>x.open),false);
    assert.equal(await button.evaluate(x=>document.activeElement===x),true);
  });
  await check('Provenance graph node inspection and all edge filters',async()=>{
    for(const option of await page.locator('#graph-edge option').evaluateAll(xs=>xs.map(x=>x.value)))await page.locator('#graph-edge').selectOption(option);
    await page.locator('#graph-edge').selectOption('all');
    const card=knowledge.graph.nodes.find(n=>n.type==='card'&&knowledge.cards.some(c=>c.card_id===n.id));
    await page.locator('#graph-question').selectOption('all');
    const node=page.locator('[data-graph-node]').filter({hasText:card.label.slice(0,10)}).first();
    await page.locator(`[data-graph-node="${card.id}"]`).focus();await page.keyboard.press('Enter');
    assert.match(await page.locator('#inspector-body').innerText(),/Bound source spans/);await page.keyboard.press('Escape');
    await page.locator('#graph-question').selectOption(knowledge.questions[0].question_id);
  });
  await check('Representation overlay, metadata colors and point selection',async()=>{
    for(const v of ['aligned','separate'])await page.locator('#projection-mode').selectOption(v);
    for(const v of ['cohort','text_origin','medium'])await page.locator('#projection-color').selectOption(v);
    await page.locator('#projection-labels').selectOption('on');await page.locator('#projection-labels').selectOption('off');
    const point=page.locator('[data-point]').first();await point.focus();await page.keyboard.press('Enter');
    assert.ok((await page.locator('#selected-source-summary').innerText()).includes(analysis.documents[0].title));
    await page.locator('#projection-results').scrollIntoViewIfNeeded();await save('representations-1440');
  });
  await check('Selected-title labels update immediately across keyboard selections',async()=>{
    await page.locator('#projection-labels').selectOption('on');
    for(const d of analysis.documents.slice(0,2)){
      const points=page.locator('[data-point]');const index=await points.evaluateAll((xs,id)=>xs.findIndex(x=>x.dataset.point===id),d.source_id);
      await points.nth(index).focus();await page.keyboard.press('Enter');
      assert.ok((await page.locator('.plot-label').allTextContents()).includes(d.title.slice(0,22)));
      assert.equal(await page.evaluate(()=>document.activeElement?.dataset?.point),d.source_id);
    }
    assert.ok(!(await page.locator('.plot-label').allTextContents()).includes(analysis.documents[0].title.slice(0,22)));
    await page.locator('#projection-labels').selectOption('off');
  });
  await check('Display-aligned semantic squares retain visible colored strokes',async()=>{
    await page.locator('#projection-mode').selectOption('aligned');
    assert.equal(await page.locator('rect.plot-point').count(),analysis.documents.length);
    assert.equal(await page.locator('rect.plot-point').evaluateAll(xs=>xs.every(x=>getComputedStyle(x).fill!==getComputedStyle(x).stroke)),true);
    await page.locator('#projection-results').evaluate(x=>x.scrollIntoView({block:'start'}));await save('overlay-1440');
    await page.locator('#projection-mode').selectOption('separate');
  });
  await check('Every neighbor source and pair ordering',async()=>{
    for(const row of analysis.neighbors.rows){await page.locator('#neighbor-source').selectOption(row.source_id);assert.equal(await page.locator('#neighbor-jaccard').innerText(),row.jaccard.toLocaleString('en-GB',{maximumFractionDigits:3}));}
    for(const v of ['lexical','difference','semantic'])await page.locator('#pair-order').selectOption(v);
  });
  await check('NMF source profiles preserve released factor weights',async()=>{
    const rows=analysis.topics?.weights||[];
    assert.equal(await page.locator('[aria-label="NMF source-factor profiles"] tbody tr').count(),rows.length);
    assert.equal(await page.locator('.topic-key>div').count(),analysis.topics.components.length);
    assert.ok(rows.every(r=>Math.abs(r.weights.reduce((a,b)=>a+b,0)-1)<1e-9));
  });
  if(manifest.modules.contextual_terms)await check('Every contextual term exposes exact source coverage and cosine neighbors',async()=>{
    const data=await page.evaluate(async f=>await(await fetch(f)).json(),moduleFile('contextual_terms'));
    for(const term of data.terms){
      await page.locator('#contextual-term').selectOption(term.term);
      assert.equal(await page.locator('[aria-label="Contextual term source sampling"] tbody tr').count(),data.source_contexts.filter(x=>x.term===term.term).length);
      const idx=data.terms.findIndex(x=>x.term===term.term);
      const expected=data.terms.map((x,i)=>({term:x.term,cosine:data.term_cosine_matrix[idx][i]})).filter(x=>x.term!==term.term).sort((a,b)=>b.cosine-a.cosine||a.term.localeCompare(b.term)).slice(0,5).map(x=>x.term);
      assert.deepEqual(await page.locator('[aria-label="Nearest contextual term centroids"] button').allTextContents(),expected);
    }
    await page.locator('#contextual-term').selectOption(data.terms.some(x=>x.term==='energy')?'energy':data.terms[0].term);
    await page.locator('#contextual-results').evaluate(x=>x.scrollIntoView({block:'start'}));await save('contextual-1440');
    const node=page.locator('[data-context-source]').first();await node.focus();await page.keyboard.press('Enter');
    assert.equal(await page.locator('#inspector').evaluate(x=>x.open),true);await page.keyboard.press('Escape');
    assert.equal(await node.evaluate(x=>x===document.activeElement),true);
  });
  if(manifest.modules.asr)await check('Actual paired-ASR denominators and all context filters',async()=>{
    const data=await page.evaluate(async f=>await(await fetch(f)).json(),moduleFile('asr'));
    for(const value of ['all',...new Set(data.clips.map(x=>x.context))]){
      await page.locator('#asr-context').selectOption(value);
      assert.equal(await page.locator('#asr-window-results tbody tr').count(),data.clips.filter(x=>value==='all'||x.context===value).length);
    }
    await page.locator('#asr-context').selectOption('all');
    assert.match(await page.locator('#recognition').innerText(),/not transcription error/);
    await page.locator('#recognition-title').evaluate(x=>x.scrollIntoView({block:'start'}));await save('asr-1440');
  });
  if(manifest.modules.full_asr)await check('Complete-recording coverage has separate exact denominators',async()=>{
    const data=await page.evaluate(async f=>await(await fetch(f)).json(),moduleFile('full_asr'));
    assert.equal(await page.locator('[aria-label="Complete recording recognition coverage"] tbody tr').count(),data.documents.length);
    assert.equal(data.summary.recordings,data.documents.length);
    assert.equal(data.summary.new_words,data.documents.reduce((n,r)=>n+r.new_words,0));
    assert.equal(data.summary.chunks,data.documents.reduce((n,r)=>n+r.chunks,0));
    await page.locator('[aria-label="Complete recording recognition coverage"]').evaluate(x=>x.scrollIntoView({block:'start'}));await save('full-asr-1440');
  });
  if(manifest.modules.asr_sensitivity)await check('Every counterfactual source and original-card reannotation record is inspectable',async()=>{
    const data=await page.evaluate(async f=>await(await fetch(f)).json(),moduleFile('asr_sensitivity'));
    assert.equal(await page.locator('[aria-label="Paired whole-recording recognizer editions"] tbody tr').count(),data.records.length);
    assert.equal(await page.locator('[aria-label="Source cards requiring reannotation"] tbody tr').count(),data.card_reannotation.records.length);
    for(const row of data.neighbors.rows){
      await page.locator('#sensitivity-source').selectOption(row.source_id);
      assert.equal(await page.locator('[aria-label="Original and counterfactual source neighbors"] tbody tr').count(),data.neighbors.k);
    }
    assert.equal(await page.locator('#metric-documents').innerText(),String(analysis.documents.length));
    assert.equal(await page.locator('#metric-cards').innerText(),String(knowledge.cards.length));
    await page.locator('[aria-label="Paired whole-recording recognizer editions"]').evaluate(x=>x.scrollIntoView({block:'start'}));await save('sensitivity-1440');
  });
  if(manifest.modules.retrieval)await check('Every actual retrieval query exposes measured condition rows',async()=>{
    const data=await page.evaluate(async f=>await(await fetch(f)).json(),moduleFile('retrieval'));
    for(const q of data.queries){
      await page.locator('#retrieval-query').selectOption(q.query_id);
      assert.equal(await page.locator('#retrieval-results tbody tr').count(),data.results.filter(x=>x.query_id===q.query_id).length);
      assert.ok((await page.locator('#retrieval-results').innerText()).includes(q.query));
    }
    assert.match(await page.locator('#experiments').innerText(),/post hoc/);
    await page.locator('#retrieval-query').scrollIntoViewIfNeeded();await save('retrieval-1440');
  });
  if(manifest.modules.experiments)await check('Every ledger observation is rendered with its actual execution status',async()=>{
    const data=await page.evaluate(async f=>await(await fetch(f)).json(),moduleFile('experiments'));
    for(const row of data.experiments||[]){
      const article=page.locator(`[data-experiment-id="${row.id}"]`);
      assert.equal(await article.count(),1);
      assert.equal(await article.locator('.status').innerText(),row.status.replaceAll('_',' '));
      assert.deepEqual(await article.locator('.observations li').allTextContents(),row.observations||[]);
      if(row.status==='proposed')assert.ok((await article.innerText()).includes('Current scope'));
      if(row.status==='partially_executed')assert.equal(await article.locator('.status.tension').count(),1);
    }
    const first=page.locator('[data-experiment-id="KB-H1-ASR"]');if(await first.count()){await first.evaluate(x=>x.scrollIntoView({block:'start'}));await save('experiment-observations-1440');}
  });
  await check('Published analytical images decode without missing files',async()=>{
    await page.locator('img').evaluateAll(async imgs=>{await Promise.all(imgs.map(async img=>{img.loading='eager';await img.decode();}));});
    assert.equal(await page.locator('img').evaluateAll(imgs=>imgs.every(img=>img.naturalWidth>0&&img.naturalHeight>0)),true);
  });
  await check('Visible text is serialized; plot axes have no filled area',async()=>{
    assert.ok(!(await page.locator('body').innerText()).includes('[object Object]'));
    assert.equal(await page.locator('.plot-axis').first().evaluate(x=>getComputedStyle(x).fill),'none');
  });
  if(!args['release-map'])await check('Every public artifact download matches its manifest bytes and SHA-256',async()=>{
    for(const artifact of manifest.artifacts||[]){
      const response=await context.request.get(new URL(artifact.file,url).href);
      assert.equal(response.status(),200,artifact.file);
      const body=await response.body();
      if(artifact.bytes!==undefined)assert.equal(body.byteLength,artifact.bytes,artifact.file);
      if(artifact.sha256)assert.equal(createHash('sha256').update(body).digest('hex'),artifact.sha256,artifact.file);
      if(/\.sqlite$/.test(artifact.file))assert.equal(body.subarray(0,16).toString(),'SQLite format 3\u0000');
    }
  });
  await check('Four CSV exports contain actual complete row counts',async()=>{
    for(const [selector,count] of [['#export-questions',knowledge.questions.length],['#export-edges',knowledge.graph.edges.length],['#export-neighbors',analysis.neighbors.rows.length],['#export-pairs',analysis.pairs.length]]){
      const waiting=page.waitForEvent('download');await page.locator(selector).click();const dl=await waiting;const file=await dl.path();const data=await fs.readFile(file,'utf8');assert.equal(data.trimEnd().split('\r\n').length,count+1);await dl.delete();
    }
  });
  await check('200 percent desktop zoom remains within viewport',async()=>{await page.evaluate(()=>document.documentElement.style.zoom='2');await noOverflow();await page.evaluate(()=>document.documentElement.style.zoom='');});
  await check('320px expanded graph and inspector overflow',async()=>{await page.setViewportSize({width:320,height:850});await noOverflow();await page.locator('[data-inspect-kind="card"]').first().click();assert.ok(await page.locator('#inspector').evaluate(x=>x.getBoundingClientRect().right<=innerWidth));await save('inspector-320');await page.keyboard.press('Escape');});
  await check('Required resource failure, no invented counts and retry',async()=>{mode='required-failure';await page.goto(url);await page.waitForSelector('#retry-load');assert.equal(await page.locator('#metric-documents').count(),0);retry=true;await page.locator('#retry-load').click();await page.waitForSelector('#metric-documents');mode='actual';});
  await check('Release integrity mismatch blocks observations',async()=>{mode='hash-failure';await page.goto(url);await page.waitForSelector('#retry-load');assert.equal(await page.locator('#metric-documents').count(),0);mode='actual';});
  await check('Optional module failure leaves required analysis usable',async()=>{mode='optional-failure';await ready();assert.ok(await page.locator('#metric-documents').count());assert.match(await page.locator('#recognition').innerText(),/unknown, not zero/);mode='actual';});
  await ready();
  await check('No browser JavaScript errors',async()=>assert.deepEqual(errors,[]));
  const uiBindings={};for(const file of ['index.html','app.js','styles.css']){const response=await context.request.get(new URL(file,url).href);assert.equal(response.status(),200);const body=await response.body();uiBindings[file]={sha256:createHash('sha256').update(body).digest('hex'),bytes:body.byteLength};}
  const report={status:'passed',generated_at:new Date().toISOString(),scope:args['release-map']?'Pre-integration browser review using exact existing artifact files via explicit local route mapping.':'Integrated local static release.',base_url:url,manifest_sha256:createHash('sha256').update(manifestText).digest('hex'),module_bindings:manifest.modules,ui_bindings:uiBindings,script_sha256:createHash('sha256').update(await fs.readFile(new URL(import.meta.url))).digest('hex'),checks,js_errors:errors,viewport_widths:[320,390,1440]};
  await fs.writeFile(path.join(out,'browser-report.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:'passed',checks:checks.length,scope:report.scope}));
}catch(error){await fs.writeFile(path.join(out,'browser-failure.json'),JSON.stringify({status:'failed',checks,errors,error:error.message},null,2));console.error(error);process.exitCode=1;}
finally{await browser.close();}
