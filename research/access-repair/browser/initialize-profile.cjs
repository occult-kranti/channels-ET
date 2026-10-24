#!/usr/bin/env node
// Initialize only Chromium's local Certificate Manager. No external navigation.
const cp = require('child_process');
const fs = require('fs');
const {chromium} = require('/opt/codex/cua_node/lib/node_modules/playwright');
const version = cp.execFileSync('/usr/bin/chromium',['--version'],{encoding:'utf8'}).trim();
if (!version.includes('154.0.8037.57')) throw new Error('Review the new browser trust-store schema before reuse');
const proxy = process.env.HTTPS_PROXY || process.env.HTTP_PROXY;
if (!proxy) throw new Error('Inherited proxy required; no direct external route permitted');
const profile = '/workspace/channels-et-browser-profile';
fs.mkdirSync(profile,{recursive:true,mode:0o700});
(async()=>{
  const context = await chromium.launchPersistentContext(profile,{headless:true,
    executablePath:'/usr/bin/chromium',proxy:{server:proxy},ignoreHTTPSErrors:false,args:['--no-sandbox']});
  try {
    const page=await context.newPage();
    await page.goto('chrome://certificate-manager/localcerts/usercerts');
    await page.locator('#userCertsSection certificate-list').first().waitFor({state:'visible'});
  } finally { await context.close(); }
  if (!fs.existsSync(profile+'/Default/ServerCertificate')) throw new Error('Browser did not initialize its certificate store');
  console.log(JSON.stringify({status:'initialized',browserVersion:version,profileOutsideRepository:true,
    externalNavigations:0,ignoreHTTPSErrors:false}));
})().catch(e=>{console.error(e.message);process.exitCode=1});
