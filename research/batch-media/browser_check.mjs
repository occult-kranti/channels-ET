import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {pathToFileURL} from 'node:url';
const {chromium}=await import(pathToFileURL(process.env.PLAYWRIGHT_PKG||'/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs').href);
const base=process.env.BASE||'http://127.0.0.1:8040';
const out=process.env.BATCH_BROWSER_OUTPUT||'/workspace/channels-et-private/batch-2026-11/browser-preliminary';
await fs.mkdir(out,{recursive:true});
const sourceFiles=['dist/app.js','dist/index.html','dist/styles.css','dist/new-round/batch-collection.json','dist/new-round/batch-analysis/analysis.json','research/batch-media/browser_check.mjs',...['recording-coverage','keyword-rates','lexical-similarity'].map(n=>'dist/new-round/batch-analysis/figures/'+n+'.svg')];
const hash=buf=>crypto.createHash('sha256').update(buf).digest('hex');
const hashes=async()=>Object.fromEntries(await Promise.all(sourceFiles.map(async p=>[p,hash(await fs.readFile(p))])));
const before=await hashes();
const data=JSON.parse(await fs.readFile('dist/new-round/batch-collection.json','utf8'));
const receipt={kind:'batch-collection-browser-verification',checkedAt:new Date().toISOString(),checks:[],errors:[],downloads:[],screenshots:[],sourceHashesBefore:before};
function check(value,label){receipt.checks.push({label,pass:!!value});if(!value)throw new Error(label);}
const browser=await chromium.launch({executablePath:process.env.PLAYWRIGHT_EXECUTABLE_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
try{
 for(const width of [390,1440]){
  const context=await browser.newContext({viewport:{width,height:1000},acceptDownloads:true,serviceWorkers:'block'});
  const page=await context.newPage();
  page.on('pageerror',e=>receipt.errors.push({width,kind:'pageerror',message:e.message}));
  page.on('console',m=>{if(m.type()==='error')receipt.errors.push({width,kind:'console',message:m.text()});});
  await page.goto(base+'/dist/#/research-update',{waitUntil:'networkidle'});
  const panel=page.locator('#batch-collection');await panel.waitFor();
  check(await panel.locator('tbody tr').count()===data.records.length,`${width}: actual retained row count matches source`);
  const numbers=await panel.locator('.stat b').allTextContents();
  check(Number(numbers[0])===data.execution.independentCreatorVideos,`${width}: creator count separate`);
  check(Number(numbers[1])===data.execution.asrCompletedSources,`${width}: actual completed ASR count`);
  check(Number(numbers[2])===data.execution.youtubeVideosInReconciledLedger,`${width}: YouTube ledger count separate`);
  check(await panel.locator('.batch-timing-note').count()===data.records.filter(r=>Number(r.asr?.timingQuality?.timestamp_repaired_segment_count)>0).length,`${width}: source-specific timestamp repairs disclosed`);
  check((await panel.textContent()).includes('264 candidate IDs are planned, not downloaded'),`${width}: proposal not presented as collection`);
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${width}: no page-wide horizontal overflow`);
  const search=page.locator('#research-update-search');await search.fill('Call to Freedom');
  check(await panel.locator('tbody tr').count()===1,`${width}: query filters retained recording`);
  await search.fill('zz-unmatched-source-zz');check((await panel.textContent()).includes('No retained recording matches'),`${width}: explicit empty search`);
  await search.fill('');
  await panel.locator('summary').click();check(await panel.getByText('Automatic ASR may omit or misrecognize speech',{exact:false}).isVisible(),`${width}: accessible methods disclosure`);
  const pending=page.waitForEvent('download');await panel.locator('a[download]').click();const download=await pending;
  const file=path.join(out,`status-${width}.json`);await download.saveAs(file);
  check(hash(await fs.readFile(file))===before['dist/new-round/batch-collection.json'],`${width}: actual downloaded bytes match source`);
  receipt.downloads.push({width,file,sha256:hash(await fs.readFile(file))});
  const screenshot=path.join(out,`collection-${width}.png`);await panel.screenshot({path:screenshot});receipt.screenshots.push({width,file:screenshot,sha256:hash(await fs.readFile(screenshot))});
  const analytical=page.locator('#batch-transcript-analysis');await analytical.waitFor();
  check((await analytical.textContent()).includes(data.records.length+' recordings;'),`${width}: actual analysis cohort count`);
  check((await analytical.textContent()).includes('one Crimson Circle creator context'),`${width}: within-creator limitation visible`);
  for(const img of await analytical.locator('img').all()){
   await img.scrollIntoViewIfNeeded();await img.evaluate(async element=>{if(!element.complete)await new Promise((resolve,reject)=>{element.onload=resolve;element.onerror=reject;});});
   check(await img.evaluate(element=>element.naturalWidth>0&&!!element.alt),`${width}: analytical figure loads with alternative text`);
  }
  const figurePending=page.waitForEvent('download');await analytical.locator('a[download]').first().click();const figureDownload=await figurePending;
  const figureFile=path.join(out,`figure-${width}.svg`);await figureDownload.saveAs(figureFile);
  check(hash(await fs.readFile(figureFile))===before['dist/new-round/batch-analysis/figures/recording-coverage.svg'],`${width}: actual SVG download integrity`);
  receipt.downloads.push({width,file:figureFile,sha256:hash(await fs.readFile(figureFile))});
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${width}: analytical figures do not overflow viewport`);
  const analyticalShot=path.join(out,`analysis-${width}.png`);await analytical.screenshot({path:analyticalShot});receipt.screenshots.push({width,file:analyticalShot,sha256:hash(await fs.readFile(analyticalShot))});
  await context.close();
 }
 check(receipt.errors.length===0,'No runtime/console errors');
 receipt.sourceHashesAfter=await hashes();check(JSON.stringify(before)===JSON.stringify(receipt.sourceHashesAfter),'Sources unchanged throughout browser verification');
 receipt.pass=true;
}catch(error){receipt.pass=false;receipt.failure=error.message;process.exitCode=1;}
finally{await browser.close();await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');}
console.log(JSON.stringify({pass:receipt.pass,checks:receipt.checks.length,errors:receipt.errors,failure:receipt.failure,downloads:receipt.downloads.length,screenshots:receipt.screenshots.length}));
