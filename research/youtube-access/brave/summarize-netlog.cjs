#!/usr/bin/env node
// Offline, allowlisted extraction. The complete browser NetLog stays private.
const fs=require('fs'),path=require('path');
function summarize(){
 const file='/workspace/channels-et-brave-profile/watch-netlog.json';
 const log=JSON.parse(fs.readFileSync(file,'utf8'));
 const types=Object.fromEntries(Object.entries(log.constants.logEventTypes).map(([k,v])=>[v,k]));
 const sends=log.events.filter(e=>types[e.type]==='HTTP_TRANSACTION_SEND_TUNNEL_HEADERS'&&
   /^CONNECT www\.youtube\.com:443 HTTP\/\d/.test(e.params?.line||''));
 const sources=new Set(sends.map(e=>e.source.id));
 const evidence=log.events.filter(e=>sources.has(e.source.id)&&
   ['HTTP_TRANSACTION_SEND_TUNNEL_HEADERS','HTTP_TRANSACTION_READ_TUNNEL_RESPONSE_HEADERS'].includes(types[e.type])).map(e=>{
   const headers=e.params?.headers||[],lines=Array.isArray(headers)?headers:[String(headers)];
   const status=lines.find(x=>/^HTTP\/\d/.test(x)),server=lines.find(x=>/^server:/i.test(x));
   return {event:types[e.type],sourceId:e.source.id,connectAuthority:'www.youtube.com:443',
     ...(status?{statusLine:status,statusCode:+status.split(' ')[1]}:{}),
     ...(server?{server:server.split(':').slice(1).join(':').trim()}:{}),rawHeadersPublished:false};
 });
 return {proxyTunnelEvidence:evidence,targetConnectRequestsObserved:sends.length,
   proxyConnectStatus:evidence.find(e=>e.statusCode)?.statusCode??null,
   rawNetLogPublished:false,extractionMode:'offline allowlist; exact authority and same network source ID only'};
}
module.exports=summarize;
if(require.main===module){
 const p=path.join(__dirname,'watch-receipt.json'),r=JSON.parse(fs.readFileSync(p,'utf8'));
 Object.assign(r,summarize());
 fs.writeFileSync(p,JSON.stringify(r,null,2)+'\n');
 console.log(JSON.stringify({proxyTunnelEvidence:r.proxyTunnelEvidence,targetConnectRequestsObserved:r.targetConnectRequestsObserved,proxyConnectStatus:r.proxyConnectStatus},null,2));
}
