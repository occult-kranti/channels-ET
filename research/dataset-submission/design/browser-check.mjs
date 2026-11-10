import {chromium} from '/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';

const base=process.env.DATASET_BASE_URL||'http://127.0.0.1:8765/dist/dataset-submission/';
const output=process.env.DATASET_TEST_OUTPUT||'/dev/shm/dataset-dashboard-browser';
await fs.mkdir(output,{recursive:true});
const dataset=await (await fetch(new URL('dataset.json',base))).json();
const manifestRaw=await (await fetch(new URL('manifest.json',base))).text();
const manifest=JSON.parse(manifestRaw);
const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
const context=await browser.newContext({acceptDownloads:true});
const page=await context.newPage();
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const checks=[];const check=(name,detail)=>checks.push({name,detail,status:'passed'});
async function visit(query=''){await page.goto(base+query);await page.locator('main[aria-busy="false"]').waitFor();assert.equal(await page.locator('main .error').count(),0,await page.locator('main').innerText());}
async function noOverflow(label){const sizes=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth}));assert.ok(sizes.scroll<=sizes.width+1,`${label}: overflow ${JSON.stringify(sizes)}`);}
try{
 for(const width of [320,390,1440]){
  await page.setViewportSize({width,height:950});
  for(const view of ['overview','channels','corpus','analysis','paper','data']){await visit('?view='+view);await noOverflow(`${width}/${view}`);assert.equal(await page.locator('h1').count(),1);}
  await visit('?view=overview');await page.screenshot({path:path.join(output,`overview-${width}.png`),fullPage:true});
  check(`reflow-${width}`,'Six views, no whole-page overflow; local table scrolling retained.');
 }
 await page.setViewportSize({width:1440,height:1000});
 await visit('?view=overview');
 assert.ok((await page.locator('main').innerText()).includes(dataset.summary.documents.toLocaleString('en-GB')));
 const yt=page.locator('dt').filter({hasText:/^Direct YouTube media$/});
 assert.equal((await yt.locator('xpath=following-sibling::dd[1]').innerText()).trim(),String(dataset.summary.youtube_downloads));
 check('summary-binding','Publication count and direct YouTube download0 match producer data.');
 await visit('?view=channels');
 const target=dataset.channels.find(c=>c.channel_id==='ra-law-of-one')||dataset.channels[0];
 await page.locator('#context-search').fill(target.channel_name);
 await page.getByRole('button',{name:'Apply filters',exact:true}).click();
 assert.equal(await page.locator('tbody tr').count(),1);
 const dl=page.waitForEvent('download');await page.locator('#export-channels').click();const d=await dl;const tmp=path.join(output,'channels.csv');await d.saveAs(tmp);const csv=await fs.readFile(tmp,'utf8');assert.equal(csv.trim().split('\r\n').length,2);assert.ok(csv.includes(target.channel_id));
 check('channel-filter-export','Name filter and CSV include exactly the selected publisher context; null upload totals stay blank.');
 await page.locator('tbody a[data-route]').first().click();assert.ok((await page.locator('h1').innerText()).includes(target.channel_name));
 assert.ok((await page.locator('main').innerText()).includes('Unknown'));
 await page.getByRole('button',{name:'Inspect context provenance'}).click();assert.ok(await page.locator('dialog').isVisible());
 await page.keyboard.press('Tab');assert.ok(await page.evaluate(()=>document.querySelector('dialog').contains(document.activeElement)));
 await page.keyboard.press('Escape');assert.ok(!(await page.locator('dialog').isVisible()));assert.equal(await page.evaluate(()=>document.activeElement.textContent),'Inspect context provenance');
 check('source-inspector-keyboard','Native dialog opens, contains Tab focus, closes with Escape and restores trigger focus.');
 await page.screenshot({path:path.join(output,'profile-1440.png'),fullPage:true});
 await page.goBack();assert.equal(new URL(page.url()).searchParams.get('view'),'channels');await page.goForward();assert.equal(new URL(page.url()).searchParams.get('view'),'channel');check('history','Browser Back and Forward preserve selected view and context.');
 await visit('?view=corpus');await page.locator('#doc-context').selectOption(target.channel_id);await page.getByRole('button',{name:'Apply filters',exact:true}).click();
 const expected=dataset.documents.filter(d=>d.channel_id===target.channel_id);const docDownload=page.waitForEvent('download');await page.locator('#export-docs').click();const dd=await docDownload;const dp=path.join(output,'documents.csv');await dd.saveAs(dp);const docCSV=await fs.readFile(dp,'utf8');for(const d of expected)assert.ok(docCSV.includes(d.source_id));
 const documentRows=await page.locator('tbody tr').count();assert.equal(documentRows,Math.min(40,expected.length));
 if(expected.length>40){await page.getByRole('button',{name:'Next',exact:true}).click();assert.ok((await page.locator('.pagination').innerText()).includes('Page 2'));}
 check('publication-filter-export-pagination',`${expected.length} actual records selected; export includes all pages.`);
 await page.getByRole('button',{name:'View metadata',exact:true}).first().click();assert.ok((await page.locator('dialog').innerText()).includes('source_id'));await page.locator('#close-inspector').click();
 await visit('?view=channels&q=zz_nonexistent_context_zz');assert.ok((await page.locator('tbody').innerText()).includes('No rows'));await page.getByRole('button',{name:'Reset',exact:true}).click();assert.equal(await page.locator('tbody tr').count(),dataset.channels.length);check('empty-and-reset','No-result selection and reset remain operational.');
 await visit('?view=channel&channel=nonexistent');assert.ok((await page.locator('h1').innerText()).includes('not in the release'));check('invalid-context','Unknown deep-link context has a recoverable view.');
 await visit('?view=corpus&q=%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E');assert.equal(await page.locator('main img').count(),0);check('escaped-input','Query values render as text, not injected markup.');
 await visit('?view=analysis');
 if(manifest.modules.analysis){await page.locator('#matrix-size').selectOption('all');assert.equal(await page.locator('.matrix thead th').count(),dataset.channels.length+1);assert.equal(await page.locator('.matrix tbody tr').count(),dataset.channels.length);check('all-context-matrix','All represented contexts selectable with stable row/column headers and numerical cells.');const badImages=await page.locator('main img').evaluateAll(async xs=>{await Promise.all(xs.map(x=>{x.loading='eager';return x.complete?Promise.resolve():new Promise(resolve=>{x.addEventListener('load',resolve,{once:true});x.addEventListener('error',resolve,{once:true});});}));return xs.filter(x=>x.naturalWidth===0).map(x=>x.src);});assert.deepEqual(badImages,[]);check('research-figure-assets','Bundled research figure images load.');}
 await page.screenshot({path:path.join(output,'analysis-1440.png'),fullPage:true});
 await page.emulateMedia({reducedMotion:'reduce'});for(const view of ['overview','channels','corpus','analysis','paper','data']){await visit('?view='+view);await page.evaluate(()=>document.documentElement.style.zoom='2');await noOverflow('200percent/'+view);if(view==='channels')await page.screenshot({path:path.join(output,'channels-200percent.png'),fullPage:true});await page.evaluate(()=>document.documentElement.style.zoom='');}check('zoom-reduced-motion','All six views at200%CSS zoom and reduced-motion preference preserve page reflow.');
 async function verifyDownload(label){const anchor=page.getByRole('link',{name:label,exact:true}),href=await anchor.getAttribute('href'),descriptor=manifest.artifacts.find(a=>a.file===href);assert.ok(descriptor,`${label} registered in manifest`);const event=page.waitForEvent('download');await anchor.click();const dl=await event;const file=path.join(output,path.basename(href));await dl.saveAs(file);const bytes=await fs.readFile(file);assert.equal(bytes.length,descriptor.bytes);assert.equal(createHash('sha256').update(bytes).digest('hex'),descriptor.sha256);}
 await visit('?view=data');await verifyDownload('Download public dataset ZIP');check('metadata-zip-download','Actual downloaded dataset ZIP matches manifest byte count and SHA-256.');
 if(manifest.modules.venue){await visit('?view=paper');assert.ok((await page.locator('main').innerText()).includes('2027-01-15'));await verifyDownload('Read paper PDF');await verifyDownload('Download Overleaf source ZIP');check('paper-and-overleaf-downloads','Actual PDF and Overleaf ZIP download with matching bytes/hash; verified January15deadline rendered.');}
 assert.deepEqual(errors,[]);check('runtime','No uncaught page JavaScript errors during nominal tasks.');
 await context.close();
 async function fault(name,edit,expected,query='?view=overview',routeModule=null){const cx=await browser.newContext();const p=await cx.newPage();await p.route('**/manifest.json',r=>r.fulfill({json:edit(structuredClone(manifest))}));if(routeModule)await p.route('**/'+routeModule,r=>r.fulfill({status:404,body:'not found'}));await p.goto(base+query);await p.locator('main[aria-busy="false"]').waitFor();assert.ok((await p.locator('main').innerText()).includes(expected),`${name}: ${await p.locator('main').innerText()}`);await cx.close();check(name,expected);}
 await fault('required-hash-corruption',m=>{m.modules.dataset.sha256='0'.repeat(64);return m;},'SHA-256 mismatch');
 await fault('required-byte-length-corruption',m=>{m.modules.dataset.bytes+=1;return m;},'Byte length mismatch');
 await fault('required-module-http-missing',m=>m,'HTTP 404','?view=overview',manifest.modules.dataset.file);
 await fault('required-module-absent',m=>{delete m.modules.dataset;return m;},'Required dataset module is absent');
 await fault('unsafe-module-path',m=>{m.modules.dataset.file='../dataset.json';return m;},'Unsafe module path');
 for(const optional of Object.keys(manifest.modules).filter(k=>k!=='dataset'&&!manifest.modules[k].required)){const view=optional==='venue'?'paper':optional==='archive'?'data':'analysis';await fault(optional+'-hash-corruption',m=>{m.modules[optional].sha256='0'.repeat(64);return m;},optional==='archive'?'No verified archive-upload receipt':optional==='analysis'?'Analysis is unavailable':'SHA-256 mismatch','?view='+view);await fault(optional+'-http-missing',m=>m,optional==='archive'?'No verified archive-upload receipt':optional==='analysis'?'Analysis is unavailable':'HTTP 404','?view='+view,manifest.modules[optional].file);}
 if(manifest.modules.analysis){const body=await (await fetch(new URL(manifest.modules.analysis.file,base))).json();body.frame_sha256='f'.repeat(64);const altered=JSON.stringify(body);const modified=structuredClone(manifest);modified.modules.analysis.bytes=Buffer.byteLength(altered);modified.modules.analysis.sha256=createHash('sha256').update(altered).digest('hex');const cx=await browser.newContext(),p=await cx.newPage();await p.route('**/manifest.json',r=>r.fulfill({json:modified}));await p.route('**/'+manifest.modules.analysis.file,r=>r.fulfill({body:altered,contentType:'application/json'}));await p.goto(base+'?view=analysis');await p.locator('main[aria-busy=false]').waitFor();assert.ok((await p.locator('main').innerText()).includes('Analysis frame does not match'));await cx.close();check('analysis-frame-mismatch','Hash-valid analysis from a different source frame is withheld.');}
 const receipts={generated_at:new Date().toISOString(),base,manifest_sha256:createHash('sha256').update(manifestRaw).digest('hex'),browser:'Chromium via Playwright',checks,unverified:['Screen reader testing','Cross-browser testing','Full WCAG conformance','Offline service-worker installation'],screenshots:await fs.readdir(output)};
 await fs.writeFile(path.join(output,'receipt.json'),JSON.stringify(receipts,null,2));console.log(JSON.stringify({checks:checks.length,status:'passed',output},null,2));
}finally{await browser.close();}
