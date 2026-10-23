const fs=require('fs'),path=require('path'),assert=require('assert'),crypto=require('crypto');
const {chromium}=require('/opt/codex/cua_node/lib/node_modules/playwright');
const out=__dirname,pub=path.resolve(out,'../../../dist/research');let browser;
(async()=>{
 const d=JSON.parse(fs.readFileSync(path.join(pub,'data.json'))),r={round:'12',checks:[],errors:[]},check=(ok,label)=>{assert(ok,label);r.checks.push(label)};
 const comparison=d.annotationComparison,conditions=comparison.conditions;
 check(conditions.length===3,'Three executed source-bound annotation conditions present');
 check(JSON.stringify(conditions.map(x=>x.parsedRecords))==='[9,9,12]','Parsed counts preserved separately from twelve attempts');
 check(conditions.every(x=>x.n===12&&x.maxNewTokens===96),'All three annotation conditions attempted same12with96token cap');
 check(JSON.stringify(conditions.map(x=>x.sourceSpanExactCount))==='[0,0,10]','Exact-substring counts distinguish source copying');
 check(JSON.stringify(conditions.map(x=>x.sourceSpanExactAndShortCount))==='[0,0,5]','Combined short-exact compliance remains separate');
 const original=d.contentLabelPredictions.records,reversed=d.optionOrderPredictions.records,newer=d.newFamilyLabelPredictions.records;
 for(const list of [original,reversed,newer])check(JSON.stringify(list.map(x=>x.id))===JSON.stringify(comparison.sameSourceIds),'Condition uses exact shared sourceID sequence');
 for(const binding of comparison.sourceBindings)check(crypto.createHash('sha256').update(fs.readFileSync(path.join(pub,binding.file))).digest('hex')===binding.sha256,'Comparison binds unchanged raw outputs '+binding.file);
 for(const c of conditions){
  const rows=c.id==='qwen25_original'?original:c.id==='qwen25_reversed'?reversed:newer;
  let exact=0,combined=0,over=0,nonexact=0;
  for(const row of rows){const p=c.id==='qwen25_reversed'?row.reversedParsed:row.parsed;if(!p)continue;const e=p.evidence||'',isExact=!!e&&row.answerGist.includes(e),short=e.trim().split(/\s+/).length<=8;exact+=+isExact;combined+=+(isExact&&short);over+=+(isExact&&!short);nonexact+=+!isExact;}
  check(exact===c.sourceSpanExactCount&&combined===c.sourceSpanExactAndShortCount&&over===c.sourceSpanExactButOverLengthCount&&nonexact===c.sourceSpanNonexactCount,'Independent raw quote diagnostics '+c.id);
 }
 check(d.optionOrder.pairedParsedRecords===8&&d.optionOrder.pairedThemeChangedCount===6,'Paired order sensitivity uses8parsed-in-both cases');
 check(d.optionOrder.reversedFirstOptionCount===0,'Reversed order does not simply pick first option');
 check(conditions[0].conditionalMethodAgreementCount===conditions[0].conditionalAlwaysYesBaselineAgreementCount&&conditions[2].conditionalMethodAgreementCount===conditions[2].conditionalAlwaysYesBaselineAgreementCount,'Original and newer conditional concordance equals always-yes baseline');
 const qa=JSON.parse(fs.readFileSync(path.resolve(out,'../../expansion/qa/qa-candidates.json'))).records,l=d.lexiconSensitivity;
 // Python source rules use only syntax shared by JavaScript here; no flags other than case-insensitivity.
 const oldRule=new RegExp(l.originalRegex,'i'),newRule=new RegExp(l.stricterRegex,'i');
 check(qa.filter(x=>oldRule.test(x.answerGist)).length===60&&qa.filter(x=>newRule.test(x.answerGist)).length===58,'Exact published regexes replay60to58over949answergists');
 browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>r.errors.push(e.message));const base=process.env.DASHBOARD_URL||'http://127.0.0.1:8012/research/';await page.goto(base+'#experiments');await page.waitForSelector('#annotation-comparison');
 await page.locator('[data-scroll="annotation-comparison"]').focus();await page.keyboard.press('Enter');check(await page.evaluate(()=>location.hash==='#experiments'&&document.activeElement.id==='annotation-comparison'),'Keyboard jump focuses comparison without losing experiment route');
 const text=await page.locator('#annotation-comparison').innerText();
 check(text.includes('6/8 cases parsed in both'),'UI explicitly reports paired6of8denominator');
 check(text.includes('reversed 0/9'),'First-option disconfirmation preserved');
 check(text.includes('Five Qwen3.5 spans are exact but overlength'),'Exact overlength quotes not called invented');
 check(text.includes('equals the always-yes baseline'),'Constant yes diagnostic has baseline context');
 check(text.includes('not corpus theme prevalence')&&text.includes('No general model ranking'),'Output themes not represented as corpus results or model ranking');
 for(const c of conditions)check((await page.locator(`#annotation-comparison tr[data-condition="${c.id}"]`).innerText()).includes(`${c.parsedRecords}/${c.n}`),'UI preserves condition parse denominator '+c.id);
 const raw=page.locator('#annotation-raw-cases');await raw.locator(':scope > summary').focus();await page.keyboard.press('Enter');check(await raw.evaluate(x=>x.open),'Keyboard opens all-condition raw inspector');
 check(await raw.locator('.annotation-case').count()===12,'All12source cases inspectable across conditions');
 const first=raw.locator('.annotation-case').first();await first.locator(':scope > summary').focus();await page.keyboard.press('Enter');
 for(const [condition,rawOutput]of [['qwen25_original',original[0].rawModelOutput],['qwen25_reversed',reversed[0].reversedRawOutput],['qwen35_original',newer[0].rawModelOutput]])check((await first.locator(`article[data-condition="${condition}"] .run-output`).innerText()).trim()===rawOutput.trim(),'Browser displays exact raw output '+condition);
 check((await first.innerText()).includes(original[0].sourceSha256)&& (await first.innerText()).includes(original[0].sourcePointer),'Raw cases retain source digest hash and pointer');
 const failure=raw.locator('.annotation-case').nth(original.findIndex(x=>!x.parsed));await failure.locator(':scope > summary').click();check((await failure.innerText()).includes('JSON: failed')&&(await failure.innerText()).includes('not evaluable'),'Failed outputs stay visible with nonevaluable span status');
 await page.locator('#lexicon-sensitivity > summary').click();check((await page.locator('#lexicon-sensitivity').innerText()).includes('60/949')&&(await page.locator('#lexicon-sensitivity').innerText()).includes('58/949'),'Post-hoc lexical sensitivity scoped to949gists');
 await page.locator('#annotation-comparison').evaluate(e=>e.scrollIntoView({block:'start'}));await page.screenshot({path:path.join(out,'round12-annotation-comparison.png'),fullPage:false});
 await page.setViewportSize({width:390,height:844});check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Annotation comparison fits390pxpage width');await page.locator('#annotation-comparison').evaluate(e=>e.scrollIntoView({block:'start'}));await page.screenshot({path:path.join(out,'round12-annotation-mobile.png'),fullPage:false});
 await page.setViewportSize({width:1440,height:1000});await page.evaluate(()=>document.documentElement.style.zoom='2');check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Annotation comparison keeps page width at200percent CSSzoom');
 check(r.errors.length===0,'No final annotation inspector browser errors');r.status='PASS';r.finishedAt=new Date().toISOString();r.publicDataSha256=crypto.createHash('sha256').update(fs.readFileSync(path.join(pub,'data.json'))).digest('hex');fs.writeFileSync(path.join(out,'round12-annotations.json'),JSON.stringify(r,null,2));console.log(JSON.stringify({status:r.status,checks:r.checks.length,errors:r.errors}));await browser.close();
})().catch(async e=>{console.error(e);if(browser)await browser.close();process.exitCode=1});
