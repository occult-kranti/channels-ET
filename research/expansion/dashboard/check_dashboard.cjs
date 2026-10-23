const fs = require('fs');
const path = require('path');
const assert = require('assert');
const crypto = require('crypto');
const {chromium} = require('/opt/codex/cua_node/lib/node_modules/playwright');
const out = __dirname;
let browser;
(async()=>{
 browser = await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const result = {role:'AI implementation/browser reviewer, not human usability research',round:process.env.REVIEW_ROUND||'7',checks:[],errors:[],screenshots:[]};
 const page = await browser.newPage({viewport:{width:1440,height:1000},acceptDownloads:true});
 page.on('pageerror',e=>result.errors.push(e.message));
 const check=(ok,label)=>{assert(ok,label);result.checks.push(label)};
 const base=process.env.DASHBOARD_URL||'http://127.0.0.1:8002/expansion/';
 await page.goto(base);await page.waitForSelector('.metrics');
 check((await page.locator('body').innerText()).includes('925'),'925 retained upload IDs rendered');
 check((await page.locator('#collection-status').innerText()).includes('blocked'),'Collection block explicit in persistent status');
 for(const route of ['overview','accounts','collection','questions','methods']){
  await page.goto(base+'#'+route);await page.waitForFunction(()=>document.querySelector('#app').textContent.length>500);
  check(!(await page.locator('#app').innerText()).includes('[object Object]'),'No object strings on '+route);
  check(!(await page.locator('#app').innerText()).includes('NaN'),'No NaN on '+route);
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No desktop horizontal page overflow on '+route);
 }
 await page.goto(base+'#accounts');await page.waitForSelector('#account-filters');
 await page.locator('[name=accountSearch]').fill('Calenara');await page.locator('#account-filters button').click();
 check(await page.locator('#account-results tbody tr').count()===1,'Account text filter changes table to one Calenara row');
 const dl1=page.waitForEvent('download');await page.locator('[data-action=export-accounts]').click();const d1=await dl1;await d1.saveAs(path.join(out,'filtered-accounts-check.csv'));
 const csv1=fs.readFileSync(path.join(out,'filtered-accounts-check.csv'),'utf8');check(csv1.includes('Calenara')&&!csv1.includes('Daniel Scranton'),'Account CSV preserves filtered population');
 await page.locator('[name=accountSearch]').fill('zzzx-no-such-name');await page.locator('#account-filters button').click();check((await page.locator('#account-results').innerText()).includes('No account matches'),'Account empty state meaningful');
 await page.goto(base+'#collection');await page.waitForSelector('#plan-filters');await page.locator('[name=planSearch]').fill('Bashar');await page.locator('#plan-filters button').click();check(await page.locator('#plan-results tbody tr').count()>0,'Keyword plan filter returns actual planned rows');check((await page.locator('#plan-results').innerText()).includes('Planned; not executed'),'Planned queries not presented as results');
 check((await page.locator('#coverage-results').innerText()).includes('Darryl Anka'),'Inherited candidate roster filters entity alias Bashar to practitioner context');
 await page.goto(base+'#questions');await page.waitForSelector('#qa-filters');
 check((await page.locator('#app').innerText()).includes('949'),'949 digest candidates rendered');
 check((await page.locator('#app').innerText()).includes('Cross-practitioner answer comparison is unavailable'),'Unsupported cross-practitioner analysis explicit');
 check((await page.locator('#app').innerText()).includes('67'),'67 source uploads with candidate Q&A rendered');
 check((await page.locator('#app').innerText()).includes('27 resolved account IDs and 7 unresolved name groups'),'QA resolved and unresolved publisher groups remain distinct');
 check((await page.locator('#app').innerText()).includes('download all 127'),'Pair preview discloses full127 qualifying pair population');
 check(await page.locator('#qa-sensitivity tbody tr').count()===6,'Six retrieval-threshold sensitivity rows rendered from reviewed summary');
 await page.locator('summary').filter({hasText:'Sources & comparison limits'}).first().click();check((await page.locator('#app').innerText()).includes('Original-session independence: unknown'),'Pair source details disclose unknown recording independence');
 await page.locator('[name=qaSearch]').fill('blueprints');await page.locator('#qa-filters button').click();check(await page.locator('.question').count()>0,'QA keyword filter operates on actual candidates');
 const dl2=page.waitForEvent('download');await page.locator('[data-action=export-qa]').click();const d2=await dl2;await d2.saveAs(path.join(out,'filtered-qa-check.csv'));
 const csv2=fs.readFileSync(path.join(out,'filtered-qa-check.csv'),'utf8');check(csv2.includes('blueprints')&&csv2.includes('ai_digest_paraphrase'),'QA filtered CSV preserves classification and selected rows');check(csv2.includes('"false"'),'QA CSV preserves false review/speaker flags as false, not missing');
 await page.locator('[name=qaSearch]').fill('zzzx-no-such-question');await page.locator('#qa-filters button').click();check((await page.locator('#qa-results').innerText()).includes('No candidate matches'),'QA empty state meaningful');
 await page.locator('[name=qaSearch]').fill('');await page.locator('#qa-filters button').click();
 await page.goto(base+'#overview');await page.waitForSelector('.metrics');
 let screenshot=path.join(out,`round${result.round}-overview.png`);await page.screenshot({path:screenshot,fullPage:true});result.screenshots.push(screenshot);
 await page.setViewportSize({width:390,height:844});
 for(const route of ['overview','accounts','collection','questions','methods']){
  await page.goto(base+'#'+route);await page.waitForFunction(()=>document.querySelector('#app').textContent.length>500);
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No 390px horizontal page overflow on '+route);
 }
 await page.goto(base+'#questions');await page.waitForSelector('.question');
 screenshot=path.join(out,`round${result.round}-questions-mobile.png`);await page.screenshot({path:screenshot,fullPage:true});result.screenshots.push(screenshot);
 screenshot=path.join(out,`round${result.round}-questions-mobile-viewport.png`);await page.screenshot({path:screenshot,fullPage:false});result.screenshots.push(screenshot);
 await page.keyboard.press('Tab');check(await page.locator(':focus').count()===1,'Keyboard can focus navigation/control');
 await page.goto(base+'#accounts');await page.waitForSelector('#account-filters');
 await page.locator('[name=accountSearch]').focus();await page.keyboard.press('Control+A');await page.keyboard.type('Calenara');await page.keyboard.press('Enter');
 check(await page.locator('#account-results tbody tr').count()===1,'Keyboard search submission filters publishing account table');
 await page.goto(base+'#questions');await page.waitForSelector('summary');const detail=page.locator('details').first();await detail.locator('summary').focus();await page.keyboard.press('Enter');
 check(await detail.evaluate(e=>e.open),'Keyboard Enter expands native source disclosure');
 await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>document.documentElement.style.zoom='2');
 for(const route of ['overview','accounts','collection','questions','methods']){
  await page.goto(base+'#'+route);await page.waitForFunction(()=>document.querySelector('#app').textContent.length>500);
  check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No page overflow under 200% CSS zoom on '+route);
 }
 await page.evaluate(()=>document.documentElement.style.zoom='1');
 for(const file of ['paper.pdf','source.zip','qa-candidates.sqlite','qa-question-pairs.json','acquisition-status.json']){
  const response=await page.request.get(base+file);check(response.ok(),'Public artifact is served: '+file);
 }
 check(result.errors.length===0,'No browser page errors');
 const publicRoot=path.resolve(out,'../../../dist/expansion');
 result.artifacts={};
 for(const name of ['index.html','app.js','styles.css','evidence.json','diagnostics.json','qa.json','qa-summary.json','qa-candidates.sqlite','qa-question-pairs.json','paper.pdf','source.zip','acquisition-status.json']){
  const bytes=fs.readFileSync(path.join(publicRoot,name));result.artifacts[name]={bytes:bytes.length,sha256:crypto.createHash('sha256').update(bytes).digest('hex')};
 }
 for(const [source,dest] of [['../paper/channeling-atlas-expansion-paper.pdf','paper.pdf'],['../paper/channeling-atlas-expansion-source.zip','source.zip'],['../qa/qa-candidates.sqlite','qa-candidates.sqlite'],['../qa/summary.json','qa-summary.json']]){
  check(fs.readFileSync(path.resolve(out,source)).equals(fs.readFileSync(path.join(publicRoot,dest))),'Public artifact bytes match reviewed source: '+dest);
 }
 result.status='PASS';result.finishedAt=new Date().toISOString();
 fs.writeFileSync(path.join(out,`round${result.round}-browser.json`),JSON.stringify(result,null,2));
 console.log(JSON.stringify({status:result.status,checks:result.checks.length,errors:result.errors}));
 await browser.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exitCode=1});
