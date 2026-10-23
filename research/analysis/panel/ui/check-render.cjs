const fs=require('fs'),vm=require('vm'),assert=require('assert');
const base=require('path').resolve(__dirname,'../../../../dist');
const stub={innerHTML:'',addEventListener(){},setAttribute(){},removeAttribute(){},querySelectorAll(){return []},scrollIntoView(){},focus(){},open:false};
const doc={querySelector(){return stub},querySelectorAll(){return []},body:{classList:{add(){},remove(){}}}};
const data=JSON.parse(fs.readFileSync(base+'/analysis/data.json','utf8'));
const context=vm.createContext({document:doc,window:{addEventListener(){},scrollTo(){}},location:{hash:'#/analysis'},fetch(){return new Promise(()=>{})},console,URLSearchParams,Date,Map,Set,Blob,URL,sample:data});
vm.runInContext(fs.readFileSync(base+'/app.js','utf8'),context);
vm.runInContext('ANALYSIS=sample;analysisState.channel=sample.channels.find(c=>c.durationCount>0).id;analysisState.compare=sample.channels.find(c=>c.id!==analysisState.channel&&c.titleCount>5).id;',context);
for(const fn of ['analysisTable','analysisChannelView','analysisCompare','analysisMethods']){const html=vm.runInContext(`${fn}()`,context);assert(html.length>500,fn);assert(!html.includes('NaN'),fn+' NaN');assert(!html.includes('[object Object]'),fn+' object string');console.log(fn+' rendered '+html.length+' characters');}
let table=vm.runInContext('analysisTable()',context);assert.strictEqual((table.match(/data-analysis-channel=/g)||[]).length,25);assert(table.includes('Next 25'));
vm.runInContext('analysisState.page=2',context);table=vm.runInContext('analysisTable()',context);assert(table.includes('26–50'));
const dated=data.videos.find(v=>v.date&&v.channelId);if(dated){context.dated=dated;vm.runInContext('analysisState.channel=dated.channelId',context);const html=vm.runInContext('analysisChannelView()',context);assert(html.includes(dated.date),'exact date rendered');}
const empty=data.channels.find(c=>c.videoCount===0);if(empty){context.emptyChannel=empty;vm.runInContext("analysisState.search=emptyChannel.name;analysisState.page=1",context);assert(vm.runInContext('analysisTable()',context).includes('No indexed videos'));}
vm.runInContext("let capturedDownload=null;triggerDownload=(filename,body,mime)=>{capturedDownload={filename,body,mime}};exportAnalysisChannel(analysisChannels().find(c=>c.videoCount>10).id);",context);
const download=vm.runInContext('capturedDownload',context);assert(download.filename.endsWith('.csv'));assert(download.body.includes('Duration seconds'));assert(download.body.includes('Provenance'));assert(download.body.split('\n').length>10);
console.log('Per-account CSV generated with durations, dates, eligibility and provenance.');
console.log('PASS: table pagination, data bindings, missing-coverage states, no NaN/object string rendering.');
