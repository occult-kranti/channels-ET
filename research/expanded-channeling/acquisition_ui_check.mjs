import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {chromium} from '/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';
const base=process.env.BASE||'http://127.0.0.1:8765';
const out=process.env.ACQUISITION_BROWSER_OUTPUT||'/workspace/channels-et-private/expanded-channeling-2026-11/browser-acquisition-229';
await fs.mkdir(out,{recursive:true});
const dirs=['dist/channeling-network/','dist/subscription-audit/'];
const inputs=[dirs[0]+'acquisition.json',dirs[1]+'acquisition.json',dirs[0]+'supplements.js',dirs[1]+'publisher-audio.js',dirs[1]+'app.js',dirs[1]+'index.html',dirs[1]+'styles.css',dirs[1]+'data.json',dirs[0]+'collected-audio-analysis.json'];
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
const hashes=async()=>Object.fromEntries(await Promise.all(inputs.map(async f=>[f,hash(await fs.readFile(f))])));
const receipt={kind:'actual-frozen-acquisition-ui-verification',started_at:new Date().toISOString(),source_hashes_before:await hashes(),checks:[],screenshots:[],downloads:[],runtime_errors:[],scope:'Actual receipt-backed metadata only. Controlled HTTP failures are isolated browser tests, never published research.'};
const d=JSON.parse(await fs.readFile(inputs[0],'utf8')),s=d.summary,held=d.records.filter(r=>r.recognition_hold_active===true);
const expectedStates=[s.local_asr_completed,s.publisher_caption_linked,s.recognition_holds,s.pending_local_asr];
function check(ok,label){receipt.checks.push({label,pass:!!ok});if(!ok)throw Error(label);}
const numeric=t=>Number(t.replaceAll(',',''));
function csv(s){let rows=[],row=[],cell='',quoted=false;for(let i=0;i<s.length;i++){const c=s[i];if(c==='"'){if(quoted&&s[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if(c==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell='';}else cell+=c;}return rows;}
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
async function snap(p,name,width){const f=path.join(out,name+'-'+width+'.png');await p.screenshot({path:f});receipt.screenshots.push({file:f,sha256:hash(await fs.readFile(f))});}
try{
  check(receipt.source_hashes_before[inputs[0]]===receipt.source_hashes_before[inputs[1]],'Both dashboards use the same acquisition receipt bytes');
  check(d.records.length===s.completed_publications,'Retained count equals actual receipt records');
  check(expectedStates.reduce((a,b)=>a+b,0)===d.records.length,'Typed processing states partition the current receipt frame');
  for(const width of [320,390,1440]){
    const context=await browser.newContext({viewport:{width,height:980},acceptDownloads:true,serviceWorkers:'block'}),p=await context.newPage();
    p.on('pageerror',e=>receipt.runtime_errors.push({width,error:e.message}));
    await p.goto(base+'/dist/channeling-network/#coverage',{waitUntil:'networkidle'});await p.locator('#publisher-audio').waitFor();
    const stat=await p.locator('#publisher-audio .audio-text-metrics b').allTextContents();
    check(JSON.stringify(stat.map(numeric))===JSON.stringify(expectedStates),`${width}: network displays actual accepted/caption/held/pending counts`);
    check(numeric(await p.locator('#publisher-audio>.metrics b').first().textContent())===d.records.length,`${width}: network retained count matches receipt`);
    const table=p.locator('[aria-label="Publisher audio storage distribution"] tbody tr');
    for(let i=0;i<d.channels.length;i++){
      const m=d.channels[i].related_publisher_material,t=(await table.nth(i).locator('td').allTextContents()).map(numeric);
      check(t[0]===m.current_new_audio_sources_retained&&t[3]===m.current_new_audio_caption_linked&&t[4]===m.current_new_audio_local_asr&&t[5]===m.current_new_audio_recognition_holds&&t[6]===m.current_new_audio_asr_pending,`${width}: network ${d.channels[i].id} actual per-publisher states`);
    }
    check((await p.locator('#publisher-audio').textContent()).includes(s.normalization_repaired+' accepted ASR editions have timestamp-display repairs'),`${width}: network display-repair count is separate from accuracy`);
    await p.locator('#publisher-audio').evaluate(e=>e.scrollIntoView({block:'start'}));check(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${width}: network acquisition reflows`);await snap(p,'network-acquisition',width);
    for(const [status,count] of [['local_asr_completed',s.local_asr_completed],['publisher_caption_linked',s.publisher_caption_linked],['asr_held_after_recognition_failure',s.recognition_holds],['pending_local_asr',s.pending_local_asr]]){
      await p.locator('#audio-status').focus();await p.locator('#audio-status').selectOption(status);
      check(numeric(await p.locator('#audio-results .result-summary strong').textContent())===count,`${width}: typed ${status} filter count`);
      check(await p.evaluate(()=>document.activeElement.id==='audio-status'),`${width}: status filter keeps keyboard focus`);
    }
    await p.locator('#audio-status').selectOption('asr_held_after_recognition_failure');
    check((await p.locator('#audio-results').textContent()).includes(held[0].title),`${width}: held view names the actual held source`);
    check((await p.locator('#audio-results').textContent()).includes('repeated output with timestamp overflow'),`${width}: held view explains diagnostic reason`);
    await p.locator('#audio-results').evaluate(e=>e.scrollIntoView({block:'start'}));await snap(p,'held-source',width);await p.locator('#audio-results .table-wrap').evaluate(e=>e.scrollLeft=e.scrollWidth);await snap(p,'held-diagnostic',width);
    await p.locator('#audio-query').fill('Deeply Held Trauma');check(numeric(await p.locator('#audio-results .result-summary strong').textContent())===0,`${width}: title word Held does not create a false recognition hold`);
    await p.locator('#clear-audio').click();check(await p.evaluate(()=>document.activeElement.id==='audio-query'),`${width}: clear resets filters and focuses query`);
    check(numeric(await p.locator('#audio-results .result-summary strong').textContent())===d.records.length,`${width}: clearing restores all actual records`);
    const download=p.waitForEvent('download');await p.locator('#export-audio').click();const file=path.join(out,'audio-'+width+'.csv');await (await download).saveAs(file);const rows=csv(await fs.readFile(file,'utf8')),[headers,...body]=rows;receipt.downloads.push({file,sha256:hash(await fs.readFile(file))});
    check(body.length===d.records.length,`${width}: complete inventory CSV exports every retained record`);
    for(const r of d.records){const row=body.find(x=>x[headers.indexOf('source_id')]===r.source_id);check(row&&row[headers.indexOf('transcript_status')]===r.transcript_status&&row[headers.indexOf('recognition_hold_active')]===String(r.recognition_hold_active)&&Number(row[headers.indexOf('asr_failed_edition_count')])===r.asr_failed_edition_count,`${width}: CSV preserves typed processing provenance ${r.source_id}`);}
    await p.goto(base+'/dist/subscription-audit/#publisher-audio-acquisition',{waitUntil:'networkidle'});await p.locator('#publisher-audio-acquisition').waitFor();
    check(JSON.stringify((await p.locator('#publisher-audio-acquisition .audio-text-metrics b').allTextContents()).map(numeric))===JSON.stringify(expectedStates),`${width}: audit displays same actual text-state counts`);
    check(numeric(await p.locator('.audio-retention-metrics b').first().textContent())===d.records.length,`${width}: audit retained count matches receipt`);
    const auditRows=p.locator('[aria-label="Publisher audio storage and transcription distribution"] tbody tr');
    check(await auditRows.count()===d.channels.length,`${width}: audit includes all publisher contexts, including OmNa outside screenshot frame`);
    for(let i=0;i<d.channels.length;i++){const m=d.channels[i].related_publisher_material;check(JSON.stringify((await auditRows.nth(i).locator('td').allTextContents()).map(numeric))===JSON.stringify([m.current_new_audio_sources_retained,m.current_new_audio_caption_linked,m.current_new_audio_local_asr,m.current_new_audio_recognition_holds,m.current_new_audio_asr_pending]),`${width}: audit ${d.channels[i].id} actual per-publisher states`);}
    check(await p.locator('.audio-holds article').count()===held.length,`${width}: audit held list excludes unadmitted text`);
    check(await p.locator('.audio-holds a').getAttribute('href')===held[0].source_url,`${width}: audit held source link binds actual failed recognition record`);
    check((await p.locator('#publisher-audio-acquisition').textContent()).includes(s.normalization_repaired+' accepted ASR editions'),`${width}: audit timestamp repairs are separately disclosed`);
    await p.locator('#publisher-audio-acquisition').evaluate(e=>e.scrollIntoView({block:'start'}));check(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${width}: audit acquisition reflows`);await snap(p,'audit-acquisition',width);
    await context.close();
  }
  const context=await browser.newContext(),p=await context.newPage();await p.route('**/dist/subscription-audit/acquisition.json',r=>r.fulfill({status:503,body:'test-only unavailable'}));await p.goto(base+'/dist/subscription-audit/',{waitUntil:'networkidle'});await p.locator('#publisher-audio-acquisition .empty').waitFor();check((await p.locator('#publisher-audio-acquisition').textContent()).includes('HTTP 503'),'Isolated missing audio receipt has visible error while screening remains usable');check(await p.locator('#audit-query').count()===1,'Missing audio receipt does not disable existing screening');await context.close();
  check(receipt.runtime_errors.length===0,'No runtime errors in actual-data acquisition journeys');
  receipt.source_hashes_after=await hashes();check(JSON.stringify(receipt.source_hashes_before)===JSON.stringify(receipt.source_hashes_after),'Public input and UI hashes remain stable throughout verification');receipt.status='passed';
}catch(e){receipt.status='failed';receipt.error=e.stack;process.exitCode=1;}finally{receipt.finished_at=new Date().toISOString();await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2));await browser.close();console.log(JSON.stringify({status:receipt.status,checks:receipt.checks.length,errors:receipt.runtime_errors.length,receipt:path.join(out,'receipt.json'),error:receipt.error}));}
