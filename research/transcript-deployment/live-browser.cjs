'use strict';
// One final functional smoke check on the actual published site.
const {chromium}=require('/opt/codex/cua_node/lib/node_modules/playwright');
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const assert=require('assert/strict');
const base='https://occult-kranti.github.io/channels-ET/';
const out=__dirname;
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
  assert(process.env.HTTPS_PROXY,'Inherited HTTPS proxy required');
  const context=await chromium.launchPersistentContext('/workspace/channels-et-browser-profile',{
    executablePath:'/usr/bin/chromium',headless:true,
    proxy:{server:process.env.HTTPS_PROXY},ignoreHTTPSErrors:false,
    viewport:{width:1440,height:1000},
    args:['--no-sandbox','--disable-background-networking','--disable-component-update']
  });
  const blocked=[],errors=[];
  try{
    await context.route('**/*',route=>{
      const u=new URL(route.request().url());
      if(u.origin==='https://occult-kranti.github.io'&&u.pathname.startsWith('/channels-ET/'))return route.continue();
      blocked.push(u.origin+u.pathname);return route.abort();
    });
    const page=await context.newPage();
    page.on('pageerror',error=>errors.push(error.message));
    const payload=page.waitForResponse(r=>r.url()===base+'dist/transcripts/data.json'&&r.status()===200);
    await page.goto(base,{waitUntil:'domcontentloaded',timeout:45000});
    const response=await payload,bytes=await response.body();
    await page.waitForFunction(()=>window.TX?.data?.analysis?.sources?.length===36);
    assert(page.url().startsWith(base+'dist/transcripts/'));
    const expected=hash(fs.readFileSync(path.join(__dirname,'../../dist/transcripts/data.json')));
    assert.equal(hash(bytes),expected);
    const counts=await page.evaluate(()=>({release:TX.data.releaseStatus,
      sources:TX.data.analysis.sources.length,selected:TX.currentDocs().length,
      archiveFiles:TX.data.archive.state.actual_local_files}));
    assert.equal(counts.release,'final');assert.equal(counts.sources,36);
    assert.equal(counts.selected,20);assert.equal(counts.archiveFiles,200);
    await page.screenshot({path:path.join(out,'live-overview.png'),fullPage:false});
    await page.selectOption('select[name="corpus"]','authored');
    await page.locator('#scope-form button').click();
    await page.waitForFunction(()=>TX.state.corpus==='authored'&&TX.currentDocs().length===16);
    assert.equal(errors.length,0);assert.equal(blocked.length,0);
    const record={status:'PASS',checkedAt:new Date().toISOString(),url:base,
      finalUrl:page.url(),sourceDataSha256:expected,sourceDataResponseStatus:response.status(),
      defaultSourceCount:20,authoredSelectionCount:16,sourceDocuments:36,localArchiveFiles:200,
      ignoreHTTPSErrors:false,inheritedProxyPreserved:true,pageErrors:errors,
      blockedOutOfScopePageRequests:blocked,scope:'Actual deployed root redirect, boot/data bytes and one corpus-switch interaction; not a repeat of full local UI review',
      scriptSha256:hash(fs.readFileSync(__filename))};
    fs.writeFileSync(path.join(out,'live-browser.json'),JSON.stringify(record,null,2)+'\n');
    process.stdout.write(JSON.stringify(record)+'\n');
  }finally{await context.close();}
})().catch(error=>{process.stderr.write(error.stack+'\n');process.exitCode=1;});
