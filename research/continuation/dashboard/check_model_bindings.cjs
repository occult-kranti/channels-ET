const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const {chromium}=require('/opt/codex/cua_node/lib/node_modules/playwright');
const out=__dirname,root=path.resolve(out,'../../..'),pub=path.join(root,'dist/research');let browser;
(async()=>{
 const r={round:process.env.REVIEW_ROUND||'10',checks:[],errors:[],artifacts:{},reviewer:'AI implementation role; focused check of changed model/paper bindings'};
 const check=(ok,label)=>{assert(ok,label);r.checks.push(label)};
 const d=JSON.parse(fs.readFileSync(path.join(pub,'data.json')));
 check(d.models?.status==='completed','Completed benchmark artifact present');check(d.models.arms.length===5,'Five actual benchmark arms');check(d.predictions.records.length===50,'Fifty actual prediction outputs');
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>r.errors.push(e.message));
 const base=process.env.DASHBOARD_URL||'http://127.0.0.1:8012/research/';await page.goto(base+'#experiments');await page.waitForSelector('#prediction-filter');
 await page.locator('summary').filter({hasText:'Inspect hardware, source split and training provenance'}).click();
 let text=await page.locator('#app').innerText();
 for(const label of ['Qwen/Qwen2.5-0.5B-Instruct','65.04','270,336','Strict marker emission on controls','plain-language refusal can score zero','not establish general superiority'])check(text.includes(label),'Visible actual scope/method: '+label);
 check(!text.includes('Control abstention'),'Old ambiguous control heading removed');
 await page.locator('summary').filter({hasText:'Inspect hardware, source split and training provenance'}).click();
 const control=d.predictions.records.find(x=>x.control);await page.locator('[name=predictionId]').selectOption(control.id);await page.locator('#prediction-filter button').click();
 check(await page.locator('#prediction-results .response').count()===5,'Control inspector compares all five output arms');check((await page.locator('#prediction-results').innerText()).includes(control.question),'Selected control question rendered');
 const raw=d.predictions.records.find(x=>x.id===control.id&&x.arm==='qwen_lora_closed');check((await page.locator('#prediction-results').innerText()).includes(raw.output),'Actual LoRA control output is inspectable');
 await page.locator('[name=predictionId]').focus();await page.keyboard.press('ArrowDown');await page.keyboard.press('Enter');await page.locator('#prediction-filter button').focus();await page.keyboard.press('Enter');check(await page.locator('#prediction-results .response').count()===5,'Keyboard selects and submits prediction inspector');
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No desktop overflow in expanded experiment view');
 await page.screenshot({path:path.join(out,`round${r.round}-experiments-actual.png`),fullPage:true});
 await page.setViewportSize({width:390,height:844});check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No390px overflow in actual experiment view');await page.screenshot({path:path.join(out,`round${r.round}-experiments-mobile-actual.png`),fullPage:false});
 await page.goto(base+'#methods');await page.waitForSelector('.artifact-list');check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No390px artifact/hash overflow');
 await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>document.documentElement.style.zoom='2');await page.goto(base+'#experiments');check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'No200%CSSzoom overflow in actual experiment view');
 for(const artifact of d.artifacts){
  const response=await page.request.get(base+artifact.path);check(response.ok(),'ArtifactHTTP200 '+artifact.path);const b=fs.readFileSync(path.join(pub,artifact.path)),sha=crypto.createHash('sha256').update(b).digest('hex');check(sha===artifact.sha256,'Displayed SHA matches '+artifact.path);check(b.equals(fs.readFileSync(path.join(root,artifact.source))),'Public bytes match source '+artifact.path);r.artifacts[artifact.path]={sha256:sha,bytes:b.length};
 }
 check(r.errors.length===0,'No browser page errors');r.status='PASS';r.finishedAt=new Date().toISOString();fs.writeFileSync(path.join(out,`round${r.round}-model-bindings.json`),JSON.stringify(r,null,2));console.log(JSON.stringify({status:r.status,checks:r.checks.length,errors:r.errors}));await browser.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exitCode=1});
