// Run against the local preview only. No application writes or external navigation.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');

const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3101';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const output=path.resolve(__dirname,'../../var/d5b-browser');
const snapshot=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness/snapshot.json');

test('D5b analysis readiness is accurate, linked and usable',{timeout:120000},async(t)=>{
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({headless:true,executablePath:process.env.EQUITY_CHROMIUM_EXECUTABLE||undefined});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[],requests=[];
 const original=fs.readFileSync(snapshot);
 page.on('pageerror',error=>errors.push(String(error)));
 page.on('console',message=>{if(message.type()==='error'&&!(message.location().url===base+'/favicon.ico'&&/404/.test(message.text())))errors.push(message.text());});
 page.on('request',request=>requests.push({url:request.url(),method:request.method()}));
 try{
  await t.test('direct view shows inputs but withholds a result',async()=>{
   await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.locator('main[data-analysis-readiness-kind]').waitFor();
   assert.equal(await page.locator('main').getAttribute('data-analysis-readiness-kind'),'real-crcl-analysis-readiness');
   assert.match(await page.getByRole('heading',{name:/Analysis gate/}).innerText(),/Analysis gate/);
   assert.equal(await page.locator('[data-analysis-input]').count(),2);
   assert.deepEqual(await page.locator('[data-analysis-input] button strong').allInnerTexts(),['$2.75B','−$96.44M']);
   for(const [label,exact] of [['Revenue and reserve income','2746642000'],['Operating income (loss)','-96435000']]){
    await page.getByRole('button',{name:`Inspect ${label} evidence`,exact:true}).click();
    const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert.match(await dialog.innerText(),new RegExp(exact));
    assert.match(await dialog.innerText(),/2026-09-21/);
    assert.equal(await dialog.getByRole('region',{name:'Source chain',exact:true}).locator('a').count(),3);
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
   }
   assert.match(await page.locator('main > header').innerText(),/Observed 2026-10-15/);
   assert.match(await page.locator('main > header').innerText(),/Published 2026-10-16/);
   const metric=page.locator('[aria-labelledby="candidate-metric-title"]');
   assert.match(await metric.innerText(),/N\/A/);
   assert.match(await metric.innerText(),/No ratio was published from this September checkpoint/);
   assert.equal(await page.locator('[data-readiness-gate]').count(),5);
   await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  });
  await t.test('all gates work with the keyboard and layout does not overflow',async()=>{
   for(const detail of await page.locator('[data-readiness-gate]').all()){
    await detail.locator('summary').focus();
    await page.keyboard.press('Enter');
    assert.equal(await detail.getAttribute('open'),'');
    assert.ok((await detail.locator('p').innerText()).length>30);
   }
   for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:1000});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);
   }
   await page.setViewportSize({width:390,height:900});
   await page.evaluate(()=>document.activeElement?.blur());
   await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  });
  await t.test('pipeline and normalization link to the same checked view',async()=>{
   await page.goto(base+'/development/pilot/pipeline',{waitUntil:'networkidle'});
   await page.locator('[data-stage="analysis"]').click();
   assert.match(await page.locator('#stage-panel').innerText(),/2 normalized inputs · 0 published metrics/);
   await page.getByRole('link',{name:'Inspect analysis readiness'}).click();
   await page.waitForURL(base+'/development/pilot/analysis');
   await page.getByRole('link',{name:'Inspect source evidence'}).click();
   await page.waitForURL(base+'/development/pilot/normalization');
   await page.getByRole('link',{name:'Inspect analysis readiness'}).click();
   await page.waitForURL(base+'/development/pilot/analysis');
   await page.reload({waitUntil:'networkidle'});
   await page.locator('main[data-analysis-readiness-kind]').waitFor();
  });
  await t.test('corrupt snapshot shows N/A and restores with Retry',async()=>{
   const priorErrors=errors.length;
   fs.writeFileSync(snapshot,'{}');
   await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();
   assert.equal(await page.locator('[data-analysis-input]').count(),0);
   fs.writeFileSync(snapshot,original);
   await page.getByRole('button',{name:'Retry',exact:true}).click();
   await page.locator('main[data-analysis-readiness-kind]').waitFor();
   const expectedRecoveryErrors=errors.splice(priorErrors);
   assert.ok(expectedRecoveryErrors.every(error=>/snapshot verification failed|An error occurred in the Server Components render/i.test(error)));
  });
  assert.deepEqual(errors,[]);
  const applicationRequests=requests.filter(request=>{
   const pathname=new URL(request.url).pathname;
   return !pathname.startsWith('/_next/')&&!pathname.startsWith('/__nextjs_');
  });
  const mutations=applicationRequests.filter(request=>request.method!=='GET');
  assert.deepEqual(mutations,[]);
  assert.ok(requests.every(request=>['127.0.0.1','localhost'].includes(new URL(request.url).hostname)));
 }finally{fs.writeFileSync(snapshot,original);await browser.close();}
});
