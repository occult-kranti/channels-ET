const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const {chromium}=require('/opt/codex/cua_node/lib/node_modules/playwright');
const root=path.resolve(__dirname,'../../..'),pub=path.join(root,'dist/research'),base=process.env.DASHBOARD_URL||'http://127.0.0.1:8014/channels-ET/dist/research/';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const r={checkedAt:new Date().toISOString(),scope:'Local current-supplement UI acceptance; no external source, OAuth or upload operation',checks:[],errors:[],artifacts:{},externalRequestsBlocked:0};
const check=(ok,label)=>{assert(ok,label);r.checks.push(label)};let browser;
(async()=>{
 const d=JSON.parse(fs.readFileSync(path.join(pub,'data.json'))),s=d.harvest.currentSupplement.sources,p=s.policy;
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
 await context.route('**/*',route=>new URL(route.request().url()).hostname==='127.0.0.1'?route.continue():(r.externalRequestsBlocked++,route.abort()));
 const page=await context.newPage();page.on('pageerror',e=>r.errors.push(e.message));
 await page.goto(new URL('../../',base).href+'#harvest');await page.waitForSelector('#harvest-current-supplement');
 check(page.url()===base+'#harvest','Project-prefix root preserves acquisition route');
 const policy=await page.locator('#current-policy').innerText();
 for(const phrase of [`${p.default.total_new_youtube_ids_selected} YouTube IDs selected`,'Shorts','300 seconds','fresh source checks','15 Bashar cap-held','0.'])check(policy.includes(phrase),'Policy states actual source/selection constraint: '+phrase);
 const figure=await page.locator('#current-selection-figure').innerText();
 for(const phrase of ['942 indexed IDs','748 eligible','123','61','10','115 Bashar-labeled','633 other','733 planned','100 Bashar','not added again','downloads: 0'])check(figure.includes(phrase),'Quantitative figure source value/limit visible: '+phrase);
 check(await page.locator('.selection-track').count()===3,'Selection figure has three aligned942-ID stages');
 // CSSOM serializes percentage widths with limited decimal precision. Exact
 // source-count arithmetic is checked separately in verify_sources.py.
 for(let i=0;i<3;i++){const total=await page.locator('.selection-track').nth(i).locator('span').evaluateAll(rows=>rows.reduce((n,x)=>n+parseFloat(x.style.width),0));check(Math.abs(total-100)<1e-3,'Every selection stage uses the same942-ID total '+i)}
 await page.locator('#current-policy-scope>summary').focus();await page.keyboard.press('Enter');check(await page.locator('#current-policy-scope').evaluate(x=>x.open),'Policy scope inspector keyboard operable');
 const scope=await page.locator('#current-policy-scope').innerText();for(const phrase of ['733','714','173','68','unknown','overlapping inherited'])check(scope.includes(phrase),'Indexed/lifetime scope distinction: '+phrase);
 const brave=await page.locator('#current-brave').innerText();for(const phrase of ['one diagnostic','403','cause remains unknown','TLS verification','No origin page response'])check(brave.toLowerCase().includes(phrase.toLowerCase()),'Brave outcome distinction: '+phrase);
 const drive=await page.locator('#current-drive').innerText();for(const phrase of ['connection pending','choice is not authentication','0 / 0','0 / 0 / 0','user-reported / not verified','200 planned uploads','not an uploaded-file count'])check(drive.includes(phrase),'Drive readiness distinction: '+phrase);
 const runner=await page.locator('#current-runner').innerText();for(const phrase of ['2,408 planned jobs','942 indexed items','Worker job attempts: 0','slots used: 0','artifacts: 0','ready: no','blocked_before_claim_or_network','share the same upload-ID cap'])check(runner.includes(phrase),'Runner planned/actual distinction: '+phrase);
 const current=await page.locator('#harvest-current-supplement').innerText();check(!current.includes('NaN')&&!current.includes('[object Object]'),'Current supplement renders without invalid values');
 check((await page.locator('#harvest-current-supplement').innerText()).includes('20 saved audio files'),'Independent20publisheraudio files stay separate');
 const pane=page.locator('#current-supplement-downloads');await pane.evaluate(x=>x.open=true);
 check(await pane.locator('a[download]').count()===d.artifacts.filter(x=>x.path.startsWith('youtube-access-')).length,'Every current metadata artifact discoverable in supplement');
 const target=d.artifacts.find(x=>x.path==='youtube-access-selected-default.jsonl');
 const downloadWait=page.waitForEvent('download');await page.locator('#current-policy a[href="'+target.path+'"]').click();const download=await downloadWait;check(sha(fs.readFileSync(await download.path()))===target.sha256,'Actual clickable default-selection download returns exact reviewed bytes');
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Current supplement fits desktop page width');
 await pane.evaluate(x=>x.open=false);await page.locator('#current-policy-scope').evaluate(x=>x.open=false);
 await page.locator('#current-selection-figure').screenshot({path:path.join(__dirname,'selection-desktop.png')});
 await page.locator('#current-brave').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(__dirname,'execution-desktop.png'),fullPage:false});
 await page.setViewportSize({width:390,height:844});await page.locator('#current-policy-scope').evaluate(x=>x.open=true);await pane.evaluate(x=>x.open=true);
 check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Expanded policy/source metadata fits390px page width');
 await page.locator('#current-selection-figure').screenshot({path:path.join(__dirname,'selection-mobile.png')});
 await page.locator('#current-drive').scrollIntoViewIfNeeded();await page.screenshot({path:path.join(__dirname,'drive-mobile.png'),fullPage:false});
 await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>document.documentElement.style.zoom='2');check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Expanded current supplement fits200percent CSSzoom');await page.evaluate(()=>document.documentElement.style.zoom='1');
 for(const a of d.artifacts){const response=await page.request.get(base+a.path);check(response.ok(),'Download HTTP200: '+a.path);const b=await response.body();check(b.length===a.bytes&&sha(b)===a.sha256,'Downloaded bytes/hash equal displayed provenance: '+a.path);check(b.equals(fs.readFileSync(path.join(root,a.source))),'Download equals current retained source: '+a.path);r.artifacts[a.path]={bytes:b.length,sha256:sha(b)}}
 for(const f of ['data.json','youtube-access.js','youtube-access.css','harvest.js','app.js','index.html','styles.css']){const response=await page.request.get(base+f);check(response.ok(),'Current asset HTTP200: '+f);const b=await response.body();check(b.equals(fs.readFileSync(path.join(pub,f))),'Current asset served bytes match build: '+f);r.artifacts[f]={bytes:b.length,sha256:sha(b)}}
 for(const view of ['overview','experiments','methods']){await page.goto(base+'#'+view);await page.waitForSelector('h1');const text=await page.locator('#app').innerText();check(!text.includes('NaN')&&!text.includes('[object Object]'),'Preserved view renders without invalid values: '+view)}
 check(r.errors.length===0,'No browser runtime errors');r.status='PASS';r.completedAt=new Date().toISOString();fs.writeFileSync(path.join(__dirname,'browser-verification.json'),JSON.stringify(r,null,2)+'\n');console.log(JSON.stringify({status:r.status,checks:r.checks.length,downloads:d.artifacts.length,errors:r.errors}));await browser.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exitCode=1});
