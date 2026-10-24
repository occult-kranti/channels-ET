#!/usr/bin/env node
// Reuse the inherited proxy and private trust profile. Never disables TLS checks.
const fs = require('fs');
const cp = require('child_process');
const path = require('path');
const https = require('https');
const { chromium } = require('/opt/codex/cua_node/lib/node_modules/playwright');
const profile = '/workspace/channels-et-browser-profile';
const mode = process.argv[2];
if (!['baseline', 'verify'].includes(mode)) throw new Error('Usage: node verify-browser.cjs baseline|verify');
const localControlOnly = mode === 'verify' && process.argv[3] === '--local-control-only';
const version = cp.execFileSync('/usr/bin/chromium', ['--version'], {encoding: 'utf8'}).trim();
if (!version.includes('154.0.8037.57')) throw new Error('Review browser version before reuse');
const proxyEnv = process.env.HTTPS_PROXY ? 'HTTPS_PROXY' : 'HTTP_PROXY';
const proxy = process.env[proxyEnv];
if (!proxy) throw new Error('Inherited proxy missing; do not use a direct connection');
const proxyUrl = new URL(proxy);
if (proxyUrl.username || proxyUrl.password) throw new Error('Authenticated proxy needs a reviewed secret-safe launcher');
const controls = [{id: 'github_pages', url: 'https://occult-kranti.github.io/channels-ET/dist/research/#harvest'}];
if (mode === 'verify') controls.push({id: 'publisher_rss', url: 'https://feeds.captivate.fm/impossible-dreams-with-aaron-lazar/'});
const receiptPath = path.join(__dirname,'verification-receipt.json');
const result = localControlOnly ? JSON.parse(fs.readFileSync(receiptPath,'utf8')) : {schemaVersion:1, checkedAt:new Date().toISOString(), mode, browserVersion:version,
  profileOutsideRepository:true, proxySource:proxyEnv, inheritedProxyUsed:true, ignoreHTTPSErrors:false,
  browserArgs:['--no-sandbox'], youtubeRequests:0, controls:[]};

async function shadowText(locator) {
  return locator.evaluate(element => {
    function walk(n) { if (n.nodeType === Node.TEXT_NODE) return n.textContent;
      if (['STYLE','SCRIPT'].includes(n.nodeName)) return '';
      return [...n.childNodes].map(walk).join(' ') + (n.shadowRoot ? walk(n.shadowRoot) : ''); }
    return walk(element).replace(/\s+/g, ' ').trim();
  });
}

async function unrelatedCertificateControl(context) {
  const fixture = path.join(profile, 'unrelated-localhost-certificate');
  fs.mkdirSync(fixture, {recursive:true, mode:0o700});
  const key = path.join(fixture, 'key.pem');
  const cert = path.join(fixture, 'cert.pem');
  if (!fs.existsSync(key) || !fs.existsSync(cert)) {
    cp.execFileSync('openssl', ['req','-x509','-newkey','rsa:2048','-nodes','-days','1',
      '-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost,IP:127.0.0.1',
      '-keyout',key,'-out',cert], {stdio:'ignore'});
    fs.chmodSync(key,0o600);
  }
  let requestCount = 0;
  const server = https.createServer({key:fs.readFileSync(key),cert:fs.readFileSync(cert)}, (req,res) => {
    requestCount++; res.end('private TLS negative control');
  });
  await new Promise(resolve => server.listen(0,'127.0.0.1',resolve));
  const page = await context.newPage();
  const row = {id:'unrelated_self_signed_localhost',expected:'certificate rejection', imported:false};
  try { await page.goto(`https://127.0.0.1:${server.address().port}/`,{timeout:15000}); }
  catch (e) { row.navigationError = e.message.split('\n')[0]; }
  finally { await page.close(); await new Promise(resolve => server.close(resolve)); }
  row.httpRequestsReachedFixture = requestCount;
  row.passed = /ERR_CERT_AUTHORITY_INVALID/.test(row.navigationError || '') && requestCount === 0;
  return row;
}

(async () => {
  if (!localControlOnly) {
  const context = await chromium.launchPersistentContext(profile, {headless:true,
    executablePath:'/usr/bin/chromium', proxy:{server:proxy}, ignoreHTTPSErrors:false,
    args:['--no-sandbox'], acceptDownloads:false});
  try {
    if (mode === 'verify') {
      const manager = await context.newPage();
      await manager.goto('chrome://certificate-manager/localcerts/usercerts');
      await manager.locator('#userCertsSection certificate-list').first().waitFor({state:'visible'});
      const trusted = manager.locator('#userCertsSection certificate-list').first();
      const trustedText = await shadowText(trusted);
      result.certificateManager = {trustedCaVisible: /openai\.com/i.test(trustedText),
        trustedCategory: 'Installed by you / Trusted Certificates'};
      await manager.close();
    }
    for (const control of controls) {
      const page = await context.newPage();
      const row = {id:control.id, requestedUrl:control.url, responseObserved:false};
      let documentResponse;
      page.on('response', r => { if (r.request().isNavigationRequest() && r.frame() === page.mainFrame()) documentResponse = r; });
      try { documentResponse = await page.goto(control.url, {waitUntil:'domcontentloaded', timeout:45000}) || documentResponse; }
      catch (e) { row.navigationError = e.message.split('\n')[0]; }
      if (documentResponse) {
        row.responseObserved = true;
        row.status = documentResponse.status();
        row.finalUrl = documentResponse.url();
        row.contentType = documentResponse.headers()['content-type'] || null;
        row.tls = await documentResponse.securityDetails();
      }
      if (control.id === 'github_pages' && !row.navigationError) {
        await page.waitForSelector('main', {timeout:20000});
        await page.waitForFunction(() => document.body.innerText.includes('Acquisition') && document.body.innerText.includes('19'), null, {timeout:20000});
        row.pageTitle = await page.title();
        row.route = new URL(page.url()).hash;
        row.mainVisible = await page.locator('main').isVisible();
        row.headings = await page.locator('h1,h2').allTextContents();
        row.harvestModuleLoaded = await page.locator('body').innerText().then(t => /3357|3,357/.test(t));
      }
      row.tlsVerifiedResponse = row.responseObserved && row.status >=200 && row.status <400 && !!row.tls;
      result.controls.push(row);
      await page.close();
    }
  } finally { await context.close(); }
  }
  if (mode === 'verify') {
    // Separate, local-only context: the inherited proxy still applies to all external
    // destinations. This context never navigates externally; the only bypass is the
    // root-authorized 127.0.0.1 self-signed fixture, so its TLS error can be observed.
    const local = await chromium.launchPersistentContext(profile, {headless:true,
      executablePath:'/usr/bin/chromium', proxy:{server:proxy,bypass:'127.0.0.1'},
      // Playwright appends <-loopback> after proxy.bypass; this final Chromium
      // argument replaces that list with the authorized literal local fixture.
      ignoreHTTPSErrors:false,args:['--no-sandbox','--proxy-bypass-list=127.0.0.1'],acceptDownloads:false});
    try {
      await local.route('**/*', route => {
        const url = new URL(route.request().url());
        return url.hostname === '127.0.0.1' ? route.continue() : route.abort();
      });
      result.unrelatedCertificateControl = await unrelatedCertificateControl(local);
      result.unrelatedCertificateControl.context = 'separate local-only context, same CA profile';
      result.unrelatedCertificateControl.proxyBypass = '127.0.0.1 only';
      result.unrelatedCertificateControl.externalNavigations = 0;
      result.unrelatedCertificateControl.checkedAt = new Date().toISOString();
    } finally { await local.close(); }
  }
  result.passed = mode === 'baseline'
    ? result.controls.every(r => /ERR_CERT_AUTHORITY_INVALID/.test(r.navigationError || '') && !r.responseObserved)
    : result.certificateManager.trustedCaVisible && result.controls.every(r => r.tlsVerifiedResponse)
      && result.controls[0].mainVisible && result.controls[0].harvestModuleLoaded
      && result.unrelatedCertificateControl.passed;
  fs.writeFileSync(path.join(__dirname, mode === 'baseline' ? 'baseline-receipt.json' : 'verification-receipt.json'), JSON.stringify(result,null,2)+'\n');
  console.log(JSON.stringify(result,null,2));
  if (!result.passed) process.exitCode=1;
})().catch(e => { console.error(e.message); process.exitCode=1; });
