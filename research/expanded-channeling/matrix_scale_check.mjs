import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {chromium} from '/opt/codex/runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright/index.mjs';

const base=process.env.BASE||'http://127.0.0.1:8057',out=process.env.MATRIX_SCALE_BROWSER_OUTPUT||'/workspace/channels-et-private/expanded-channeling-2026-11/browser-matrix-scale';
await fs.mkdir(out,{recursive:true});
const actual=JSON.parse(await fs.readFile('dist/channeling-network/collected-audio-analysis.json','utf8'));
const files=['dist/channeling-network/studies.js','dist/channeling-network/collected-audio-analysis.json','research/expanded-channeling/matrix_scale_check.mjs'];
const hash=b=>crypto.createHash('sha256').update(b).digest('hex'),hashes=async()=>Object.fromEntries(await Promise.all(files.map(async f=>[f,hash(await fs.readFile(f))]))),before=await hashes();
const receipt={kind:'bounded-matrix-ui-scale-verification',started_at:new Date().toISOString(),source_hashes_before:before,actual_source_count:actual.lexical.source_ids.length,fixture_policy:'Synthetic matrices are generated only inside isolated headless-browser memory after actual-data checks. No fixture JSON, figure or research output is written to the public site. Screenshots and exported fixture CSVs are private and marked as stress fixtures.',checks:[],screenshots:[],downloads:[],runtime_errors:[]};
function check(condition,label){receipt.checks.push({label,pass:!!condition});if(!condition)throw Error(label);}
function csvRows(s){let rows=[],row=[],cell='',quoted=false;for(let i=0;i<s.length;i++){const c=s[i];if(c==='"'){if(quoted&&s[i+1]==='"'){cell+='"';i++;}else quoted=!quoted;}else if(c===','&&!quoted){row.push(cell);cell='';}else if(c==='\n'&&!quoted){row.push(cell.replace(/\r$/,''));rows.push(row);row=[];cell='';}else cell+=c;}return rows;}
const identity=s=>s.startsWith("'")?s.slice(1):s;
const score=(i,j)=>i===j?1:(((Math.min(i,j)+1)*257+Math.max(i,j)+1)%1000)/1000;
async function download(page,name){const pending=page.waitForEvent('download');await page.locator('#export-collected-similarities').click();const d=await pending,file=path.join(out,name+'.csv');await d.saveAs(file);const bytes=await fs.readFile(file);receipt.downloads.push({file,bytes:bytes.length,sha256:hash(bytes)});return csvRows(bytes.toString('utf8').replace(/^\ufeff/,''));}
async function screenshot(page,name){const file=path.join(out,name+'.png');await page.screenshot({path:file});receipt.screenshots.push({file,sha256:hash(await fs.readFile(file))});}
const browser=await chromium.launch({headless:true,executablePath:'/usr/bin/chromium',args:['--no-sandbox','--disable-dev-shm-usage']});
try{
  for(const width of [320,1440]){
    const context=await browser.newContext({viewport:{width,height:980},acceptDownloads:true,serviceWorkers:'block'}),page=await context.newPage();
    page.on('pageerror',e=>receipt.runtime_errors.push({width,message:e.message}));page.on('console',m=>{if(m.type()==='error')receipt.runtime_errors.push({width,message:m.text()});});
    await page.goto(base+'/dist/channeling-network/#analysis',{waitUntil:'networkidle'});await page.locator('#collected-matrix-results table').waitFor();
    check(actual.lexical.source_ids.length<=40,`${width}: actual publication exercises unchanged small-matrix branch`);
    check(await page.locator('.matrix-block-controls').count()===0,`${width}: actual small matrix adds no block controls`);
    check(await page.locator('#collected-matrix-results tbody td').count()===actual.lexical.source_ids.length**2,`${width}: all actual small-matrix cells remain visible`);
    const cells=await page.locator('#collected-matrix-results tbody tr').evaluateAll(rows=>rows.map(row=>[...row.querySelectorAll('td')].map(td=>td.textContent)));
    check(cells.every((r,i)=>r.every((v,j)=>v===actual.lexical.matrix[i][j].toLocaleString(undefined,{maximumFractionDigits:3}))),`${width}: every actual matrix cell retains its released value`);
    await page.locator('#collected-matrix-mode').selectOption('window');check(await page.locator('#collected-matrix-results tbody tr').count()===actual.lexical.window_300_source_ids.length,`${width}: actual window membership unchanged`);await page.locator('#collected-matrix-mode').selectOption('whole');
    const actualCsv=await download(page,'actual-source-pairs-'+width);check(actualCsv.length===actual.lexical.source_ids.length*(actual.lexical.source_ids.length-1)/2+1,`${width}: actual complete pair export unchanged`);
    check(actualCsv.slice(1).every(row=>{const i=actual.lexical.source_ids.indexOf(identity(row[0])),j=actual.lexical.source_ids.indexOf(identity(row[1]));return i>=0&&j>i&&Number(row[2])===actual.lexical.matrix[i][j];}),`${width}: actual exported pair identities and values unchanged`);

    for(const size of [40,41,81,229]){
      const timings=await page.evaluate(size=>{
        const ids=Array.from({length:size},(_,i)=>'fixture:source:'+i),score=(i,j)=>i===j?1:(((Math.min(i,j)+1)*257+Math.max(i,j)+1)%1000)/1000;
        const documents=ids.map((id,i)=>({source_id:id,publication_id:id,title:'ISOLATED STRESS FIXTURE ONLY · source '+(i+1),group_id:'stress_fixture',group_label:'Not research data',text_origin:'synthetic_stress_fixture',source_role:'unknown',words:30,source_url:''}));
        const matrix=ids.map((_,i)=>ids.map((_,j)=>score(i,j))),positions=ids.map((_,i)=>i).filter(i=>i%2===1),windowIds=positions.map(i=>ids[i]);
        extraStudies.collected={schema_version:1,synthetic_fixture_run:true,scope:'Isolated in-memory browser stress test; never a public study',documents,coverage:{groups:[]},lexical:{status:'fitted',source_ids:ids,matrix,window_300_source_ids:windowIds,window_300_matrix:positions.map(i=>positions.map(j=>i===j?1:score(i,j)/2)),scope:'SYNTHETIC STRESS FIXTURE ONLY',window_rule:'Odd global indices only, for testing non-contiguous membership'},clusters:{assignments:[]},paired_written_editions:[]};
        Object.assign(collectedState,{matrix:'whole',matrixRowBlock:0,matrixColumnBlock:0});document.querySelector('#collected-matrix-mode').value='whole';
        document.querySelector('#collected-audio-study>.section-head h2').textContent='ISOLATED SYNTHETIC STRESS FIXTURE · '+size+' sources · not research';
        const start=performance.now();document.querySelector('#collected-matrix-results').innerHTML=collectedSimilarityMatrix();return {size,milliseconds:performance.now()-start};
      },size);
      receipt.checks.push({label:`${width}: fixture ${size} render timing`,pass:true,informational_milliseconds:timings.milliseconds});
      const bounded=size>40,blocks=Math.ceil(size/20),visible=bounded?20:size;
      check(await page.locator('#collected-matrix-results tbody td').count()===visible**2,`${width}: fixture ${size} bounds rendered numeric cells`);
      check(await page.locator('.matrix-block-controls').count()===(bounded?1:0),`${width}: fixture ${size} threshold behavior`);
      if(!bounded)continue;
      check((await page.locator('.matrix-subset-summary').textContent()).includes(size+' eligible source-text units'),`${width}: fixture ${size} explicitly states total outside subset`);
      await page.locator('#collected-matrix-rows').focus();await page.keyboard.press('ArrowDown');
      check(await page.locator('#collected-matrix-rows').inputValue()==='1',`${width}: fixture ${size} row block changes by keyboard`);check(await page.evaluate(()=>document.activeElement?.id==='collected-matrix-rows'),`${width}: fixture ${size} row control retains keyboard focus`);
      await page.locator('#collected-matrix-columns').selectOption(String(blocks-1));check(await page.evaluate(()=>document.activeElement?.id==='collected-matrix-columns'),`${width}: fixture ${size} column control retains focus`);
      const firstSource=await page.locator('#collected-matrix-results tbody [data-collected-source]').first().getAttribute('data-collected-source');check(firstSource==='fixture:source:20',`${width}: fixture ${size} row block retains global source ID`);
      const columnStart=(blocks-1)*20,headers=await page.locator('#collected-matrix-results thead th').allTextContents();check(Number(headers[1])===columnStart+1,`${width}: fixture ${size} column block retains global source number`);
      check(Number(await page.locator('#collected-matrix-results tbody tr').first().locator('td').first().textContent())===score(20,columnStart),`${width}: fixture ${size} cross-block value uses global matrix indices`);
      await page.locator('#collected-matrix-rows').selectOption(String(blocks-1));check(await page.locator('#collected-matrix-results tbody td').count()===(size-columnStart)**2,`${width}: fixture ${size} partial final blocks remain bounded`);
      await page.locator('#collected-matrix-results tbody [data-collected-source]').first().focus();await page.keyboard.press('Enter');check((await page.locator('#record-title').textContent()).includes('ISOLATED STRESS FIXTURE'),`${width}: fixture ${size} global row opens correct source inspector`);await page.keyboard.press('Escape');check(await page.evaluate(()=>document.activeElement?.hasAttribute('data-collected-source')),`${width}: fixture ${size} source inspector returns focus`);
      await page.locator('#collected-matrix-mode').selectOption('window');const windowCount=Math.floor(size/2),windowBounded=windowCount>40;
      check(await page.locator('.matrix-block-controls').count()===(windowBounded?1:0),`${width}: fixture ${size} window threshold uses eligible subset size`);check(Number(await page.locator('#collected-matrix-results thead th').nth(1).textContent())===2,`${width}: fixture ${size} window source numbers preserve non-contiguous global membership`);
      if(windowBounded){check(await page.locator('#collected-matrix-rows').inputValue()==='0'&&await page.locator('#collected-matrix-columns').inputValue()==='0',`${width}: fixture ${size} switching text modes resets blocks`);await page.locator('#collected-matrix-rows').selectOption('1');await page.locator('#collected-matrix-columns').selectOption('2');check(await page.locator('#collected-matrix-results tbody [data-collected-source]').first().getAttribute('data-collected-source')==='fixture:source:41',`${width}: fixture ${size} window row uses eligible-to-global mapping`);check(Number(await page.locator('#collected-matrix-results thead th').nth(1).textContent())===82,`${width}: fixture ${size} window column uses global ordinal`);check(Number(await page.locator('#collected-matrix-results tbody tr').first().locator('td').first().textContent())===Number((score(41,81)/2).toLocaleString(undefined,{maximumFractionDigits:3})),`${width}: fixture ${size} window cross-block value is correct`);}
      check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`${width}: fixture ${size} no whole-page horizontal overflow`);
      if(size===229){
        const allPairs=await download(page,'SYNTHETIC-STRESS-ONLY-229-source-pairs-'+width);check(allPairs.length===size*(size-1)/2+1,`${width}: fixture ${size} export includes all26,106 pairs despite a bounded window view`);
        check(allPairs.slice(1).every(row=>{const i=Number(row[0].split(':').at(-1)),j=Number(row[1].split(':').at(-1));return i<j&&Number(row[2])===score(i,j)&&(i%2===1&&j%2===1?Number(row[3])===score(i,j)/2:row[3]==='');}),`${width}: fixture ${size} all exported whole/window scores and exclusions match`);
        await page.locator('#collected-matrix-results').evaluate(el=>el.scrollIntoView({block:'start'}));await screenshot(page,'SYNTHETIC-STRESS-ONLY-229-matrix-'+width);
      }
    }
    await context.close();
  }
  check(receipt.runtime_errors.length===0,'Actual and isolated stress views have no runtime errors');receipt.source_hashes_after=await hashes();check(JSON.stringify(before)===JSON.stringify(receipt.source_hashes_after),'Public UI and research inputs unchanged during stress verification');receipt.status='passed';
}catch(e){receipt.status='failed';receipt.failure=e.stack||e.message;process.exitCode=1;}finally{await browser.close();receipt.finished_at=new Date().toISOString();await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify(receipt,null,2)+'\n');}
console.log(JSON.stringify({status:receipt.status,checks:receipt.checks.length,screenshots:receipt.screenshots.length,downloads:receipt.downloads.length,runtime_errors:receipt.runtime_errors,failures:receipt.checks.filter(c=>!c.pass),failure:receipt.failure}));
