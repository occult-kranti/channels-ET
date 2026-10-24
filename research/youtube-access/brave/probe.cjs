#!/usr/bin/env node
// Bounded browser diagnostic. Watch mode is guarded against a second navigation.
const fs=require('fs'),path=require('path'),cp=require('child_process');
const {chromium}=require('/opt/codex/cua_node/lib/node_modules/playwright');
const mode=process.argv[2];
if(!['initialize','control','watch'].includes(mode))throw Error('Usage: node probe.cjs initialize|control|watch');
const here=__dirname,profile='/workspace/channels-et-brave-profile';
const binary='/workspace/channels-et-brave-runtime/extracted/opt/brave.com/brave/brave';
const version=cp.execFileSync(binary,['--version'],{encoding:'utf8'}).trim();
if(version!=='Brave Browser 156.1.98.60 unknown')throw Error('Unexpected Brave build; review before use');
const proxy=process.env.HTTPS_PROXY||process.env.HTTP_PROXY;
if(!proxy)throw Error('Inherited proxy required; no direct connection permitted');
const u=new URL(proxy);if(u.username||u.password)throw Error('Authenticated proxy needs a reviewed secret-safe launcher');
const target=mode==='control'?'https://occult-kranti.github.io/channels-ET/dist/research/#harvest':'https://www.youtube.com/watch?v=fZmY4xS_qXE';
const watchMarker=path.join(profile,'youtube-watch-navigation-started.json');
if(mode==='watch'){
 const c=JSON.parse(fs.readFileSync(path.join(here,'control-receipt.json'),'utf8'));
 if(!c.passed||c.ignoreHTTPSErrors!==false)throw Error('Verified allowed HTTPS control required before watch navigation');
 if(fs.existsSync(watchMarker))throw Error('Watch navigation already started; no retry authorized by this script');
}
fs.mkdirSync(profile,{recursive:true,mode:0o700});
const receipt={schemaVersion:1,checkedAt:new Date().toISOString(),mode,browserVersion:version,
 runtimeObservation:{specRevision:'6',mode:'unrestricted',state:'unknown',observationsCurrent:true,observationBasis:'cloud_environment.environment_status read during this bounded setup; not a destination-access guarantee'},
 proxy:'same inherited HTTPS_PROXY/HTTP_PROXY',proxyConfigurationPreserved:true,ignoreHTTPSErrors:false,
 browserArgs:['--no-sandbox'],profileOutsideRepository:true,pageRequests:[],blockedPageRequests:[],
 responses:[],failedRequests:[],cdpFailures:[],ordinaryWatchNavigations:0};
(async()=>{
 const args=['--no-sandbox'];
 const netlog=path.join(profile,'watch-netlog.json');
 if(mode==='watch')args.push('--log-net-log='+netlog,'--net-log-capture-mode=Default');
 receipt.browserArgs=args;
 const context=await chromium.launchPersistentContext(profile,{headless:true,executablePath:binary,
   proxy:{server:proxy},ignoreHTTPSErrors:false,args,acceptDownloads:false});
 try{
  const page=await context.newPage(),cdp=await context.newCDPSession(page);
  receipt.engine=await cdp.send('Browser.getVersion');
  await cdp.send('Network.enable');
  cdp.on('Network.loadingFailed',e=>receipt.cdpFailures.push({type:e.type,errorText:e.errorText,canceled:e.canceled,blockedReason:e.blockedReason||null}));
  if(mode==='initialize'){
   await page.goto('brave://certificate-manager/localcerts/usercerts');
   await page.locator('#userCertsSection certificate-list').first().waitFor({state:'visible'});
   receipt.certificateManagerInitialized=true;
   receipt.passed=true;
  }else{
   if(mode==='control'){
    const manager=await context.newPage();
    await manager.goto('brave://certificate-manager/localcerts/usercerts');
    await manager.locator('#userCertsSection certificate-list').first().waitFor({state:'visible'});
    const text=await manager.locator('#userCertsSection certificate-list').first().evaluate(element=>{
     function walk(n){if(n.nodeType===Node.TEXT_NODE)return n.textContent;if(['STYLE','SCRIPT'].includes(n.nodeName))return '';return [...n.childNodes].map(walk).join(' ')+(n.shadowRoot?walk(n.shadowRoot):'')}
     return walk(element).replace(/\s+/g,' ').trim();
    });
    receipt.managedCaVisibleInTrustedCategory=/openai\.com/i.test(text);
    await manager.close();
   }
   await context.route('**/*',route=>{
    const request=route.request(),url=request.url();
    const permitted=mode==='control'?new URL(url).hostname==='occult-kranti.github.io':url===target;
    if(permitted)return route.continue();
    receipt.blockedPageRequests.push({url,method:request.method(),resourceType:request.resourceType()});
    return route.abort();
   });
   page.on('request',r=>receipt.pageRequests.push({url:r.url(),method:r.method(),resourceType:r.resourceType(),navigation:r.isNavigationRequest()}));
   page.on('requestfailed',r=>receipt.failedRequests.push({url:r.url(),method:r.method(),failure:r.failure()?.errorText||null}));
   const responseTasks=[];
   page.on('response',r=>responseTasks.push((async()=>{if(r.request().isNavigationRequest())receipt.responses.push({url:r.url(),status:r.status(),tls:await r.securityDetails(),headers:{server:r.headers().server||null,contentType:r.headers()['content-type']||null}})})()));
   if(mode==='watch'){
    fs.writeFileSync(watchMarker,JSON.stringify({startedAt:receipt.checkedAt,url:target,ordinaryNavigationBudget:1}),{flag:'wx',mode:0o600});
    receipt.ordinaryWatchNavigations=1;
   }
   receipt.requestedUrl=target;
   try{await page.goto(target,{waitUntil:'domcontentloaded',timeout:45000})}
   catch(e){receipt.navigationError=e.message.split('\n')[0]}
   await Promise.all(responseTasks);
   receipt.finalUrl=page.url();
   if(mode==='control'&&!receipt.navigationError){
    await page.waitForSelector('#harvest-access-repair',{timeout:20000});
    receipt.pageTitle=await page.title();
    receipt.actualAcquisitionDashboardRendered=await page.locator('#harvest-access-repair').isVisible();
   }
   receipt.passed=mode==='control'?(!receipt.navigationError&&receipt.responses.some(r=>r.status===200&&r.tls)&&receipt.actualAcquisitionDashboardRendered&&receipt.managedCaVisibleInTrustedCategory):undefined;
   if(mode==='watch')receipt.outcome=receipt.navigationError?'navigation_failed':'navigation_completed';
  }
 }finally{await context.close()}
 if(mode==='watch'&&fs.existsSync(netlog)){
  Object.assign(receipt,require('./summarize-netlog.cjs')());
 }
 receipt.completedAt=new Date().toISOString();
 fs.writeFileSync(path.join(here,mode+'-receipt.json'),JSON.stringify(receipt,null,2)+'\n');
 console.log(JSON.stringify(receipt,null,2));
 if(mode==='control'&&!receipt.passed)process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exitCode=1});
