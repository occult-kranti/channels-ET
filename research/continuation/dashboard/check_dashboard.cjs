const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const {chromium}=require('/opt/codex/cua_node/lib/node_modules/playwright');
const out=__dirname,publicRoot=path.resolve(out,'../../../dist/research');
let browser;
(async()=>{
 const result={round:process.env.REVIEW_ROUND||'10',reviewer:'AI implementation/browser role, not human participant research',checks:[],errors:[],screenshots:[]};
 const check=(ok,label)=>{assert(ok,label);result.checks.push(label)};
 const data=JSON.parse(fs.readFileSync(path.join(publicRoot,'data.json'),'utf8'));
 if(process.env.REQUIRE_MODELS==='1')check(!!data.models,'Final benchmark artifact present');
 if(process.env.REQUIRE_PAPER==='1')check(data.artifacts.some(a=>a.path==='paper.pdf'),'Final paper artifact present');
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>result.errors.push(e.message));
 const base=process.env.DASHBOARD_URL||'http://127.0.0.1:8012/research/';
 await page.goto(base);await page.waitForSelector('.metrics');
 check((await page.locator('main').innerText()).includes('925'),'Retained925uploadIDs rendered');
 check((await page.locator('main').innerText()).includes('949'),'Digest949candidate scope rendered');
 check((await page.locator('main').innerText()).includes('30 frozen English-caption vectors'),'Caption layer identifies retained vectors without implying raw text ships');
 for(const view of ['overview','experiments','collection','methods']){
  await page.goto(base+'#'+view);await page.waitForFunction(()=>document.querySelector('#app').textContent.length>400);
  const text=await page.locator('#app').innerText();check(!text.includes('NaN')&&!text.includes('[object Object]'),'No invalid values on '+view);
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No desktop page overflow on '+view);
 }
 await page.goto(base+'#experiments');await page.waitForFunction(()=>document.querySelector('#app').textContent.length>400);
 if(!data.models)check((await page.locator('main').innerText()).includes('No completed local-model benchmark artifact'),'Missing model output is explicitly pending');
 else{
  check((await page.locator('main').innerText()).includes(data.models.model.id),'Actual model identifier rendered');
  check((await page.locator('main').innerText()).includes('Token overlap F1'),'Quality proxy is not labeled factual accuracy');
  check(await page.locator('tbody tr').count()>data.models.arms.length,'Actual model arm rows rendered with hardware/split context');
 }
 await page.goto(base+'#collection');await page.waitForSelector('#collection-filters');
 const records=data.channelProgress?.records||[];
 check(records.length===106,'Sourcecandidate roster contains106records');
 await page.locator('[name=search]').fill('Bashar');await page.locator('#collection-filters .button').first().click();
 check((await page.locator('#collection-results').innerText()).includes('Darryl Anka'),'Entity alias filter joins only inherited candidate IDs');
 const dl=page.waitForEvent('download');await page.locator('[data-action=export-collection]').click();const download=await dl;await download.saveAs(path.join(out,'filtered-coverage-check.csv'));
 const csv=fs.readFileSync(path.join(out,'filtered-coverage-check.csv'),'utf8');check(csv.includes('Darryl Anka')&&!csv.includes('Abbey Normal'),'Coverage CSV uses the filtered candidate population');
 check(csv.includes('not_attempted_after_general_access_probe_denial'),'CSV preserves per-candidate unattempted state instead of inferred403failure');
 await page.locator('[name=search]').fill('zzzx-no-such-candidate');await page.locator('#collection-filters .button').first().click();check((await page.locator('#collection-results').innerText()).includes('No candidate matches'),'Collection no-match state meaningful');
 await page.locator('[name=search]').focus();await page.keyboard.press('Control+A');await page.keyboard.type('Calenara');await page.keyboard.press('Enter');check((await page.locator('#collection-results').innerText()).includes('Calenara'),'Keyboard form submission filters source records');
 await page.locator('[name=search]').fill('');await page.locator('#collection-filters .button').first().click();
 await page.goto(base+'#methods');await page.waitForSelector('details');const details=page.locator('details').first();await details.locator('summary').focus();await page.keyboard.press('Enter');check(await details.evaluate(e=>e.open),'Keyboard opens native source/method disclosure');
 await page.goto(base+'#overview');await page.waitForSelector('.metrics');let shot=path.join(out,`round${result.round}-overview.png`);await page.screenshot({path:shot,fullPage:true});result.screenshots.push(shot);
 await page.setViewportSize({width:390,height:844});
 for(const view of ['overview','experiments','collection','methods']){
  await page.goto(base+'#'+view);await page.waitForFunction(()=>document.querySelector('#app').textContent.length>400);
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No390pxpage overflow on '+view);
 }
 await page.goto(base+'#experiments');shot=path.join(out,`round${result.round}-experiments-mobile.png`);await page.screenshot({path:shot,fullPage:true});result.screenshots.push(shot);
 shot=path.join(out,`round${result.round}-experiments-mobile-viewport.png`);await page.screenshot({path:shot,fullPage:false});result.screenshots.push(shot);
 await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>document.documentElement.style.zoom='2');
 for(const view of ['overview','experiments','collection','methods']){
  await page.goto(base+'#'+view);await page.waitForFunction(()=>document.querySelector('#app').textContent.length>400);check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No200%CSSzoom page overflow on '+view);
 }
 await page.evaluate(()=>document.documentElement.style.zoom='1');
 result.artifacts={};
 for(const a of data.artifacts){
  const response=await page.request.get(base+a.path);check(response.ok(),'Public artifact serves '+a.path);
  const blob=fs.readFileSync(path.join(publicRoot,a.path)),sha=crypto.createHash('sha256').update(blob).digest('hex');
  check(sha===a.sha256,'Displayed artifact hash matches '+a.path);result.artifacts[a.path]={sha256:sha,bytes:blob.length};
 }
 for(const name of ['index.html','app.js','styles.css','data.json']){const bytes=fs.readFileSync(path.join(publicRoot,name));result.artifacts[name]={bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};}
 check(result.errors.length===0,'No browser page errors');result.status='PASS';result.finishedAt=new Date().toISOString();
 fs.writeFileSync(path.join(out,`round${result.round}-browser.json`),JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,checks:result.checks.length,errors:result.errors}));await browser.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exitCode=1});
