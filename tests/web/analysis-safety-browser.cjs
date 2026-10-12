// Local GET-only UI verification; snapshot corruption is always restored.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3101';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const snapshot=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness/safety.json');
const output=path.resolve(__dirname,'../../var/d5c-browser');
test('D5c evidence review preserves the two safety conclusions',{timeout:120000},async(t)=>{
 fs.mkdirSync(output,{recursive:true});
 const original=fs.readFileSync(snapshot);
 const browser=await chromium.launch({headless:true,executablePath:process.env.EQUITY_CHROMIUM_EXECUTABLE||undefined});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[],requests=[];
 page.on('pageerror',error=>errors.push(String(error)));
 page.on('request',request=>requests.push({url:request.url(),method:request.method()}));
 try{
  await t.test('both decisions and all check evidence are accessible',async()=>{
   await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.locator('[data-safety-review]').waitFor();
   assert.match(await page.locator('[data-safety-decision="historical"]').innerText(),/Blocked/i);
   assert.match(await page.locator('[data-safety-decision="retrospective"]').innerText(),/Incomplete/i);
   assert.equal(await page.locator('[data-safety-check]').count(),8);
   for(const detail of await page.locator('[data-safety-check]').all()){
    await detail.locator('summary').focus();await page.keyboard.press('Enter');
    await detail.getByRole('button').click();
    const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert.ok((await dialog.innerText()).includes('Evidence and limits'));
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
    await detail.locator('summary').click();
   }
   assert.match(await page.locator('[aria-labelledby="candidate-metric-title"]').innerText(),/N\/A/);
   await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  });
  await t.test('exact coverage, gaps and keyboard disclosures',async()=>{
   for(const selector of ['[data-safety-profile]','[data-safety-coverage]','[data-safety-missing]']){
    const detail=page.locator(selector);await detail.locator('summary').first().focus();await page.keyboard.press('Enter');
    assert.equal(await detail.getAttribute('open'),'');
   }
   assert.equal(await page.locator('[data-safety-filing]').count(),19);
   assert.equal(await page.locator('[data-missing-exhibit]').count(),11);
   assert.equal(await page.locator('[data-later-filing]').count(),2);
   for(const filing of await page.locator('[data-safety-filing]').all()){
    await filing.locator('summary').click();
    assert.match(await filing.innerText(),/Body SHA256/);
    assert.match(await filing.locator('a').getAttribute('href'),/^https:\/\/www.sec.gov\//);
   }
   for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:1000});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);
   }
   await page.locator('[data-safety-review] details[open]').evaluateAll(elements=>elements.forEach(element=>element.removeAttribute('open')));
   await page.setViewportSize({width:390,height:900});
   await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  });
  await t.test('corrupt safety artifact fails closed and Retry restores',async()=>{
   fs.writeFileSync(snapshot,'{}');
   await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();
   assert.equal(await page.locator('[data-analysis-input]').count(),0);
   fs.writeFileSync(snapshot,original);
   await page.getByRole('button',{name:'Retry',exact:true}).click();
   await page.locator('[data-safety-review]').waitFor();
  });
  assert.ok(errors.every(error=>/snapshot verification failed|An error occurred in the Server Components render/i.test(error)));
  assert.ok(requests.every(request=>['127.0.0.1','localhost'].includes(new URL(request.url).hostname)));
  assert.deepEqual(requests.filter(request=>!new URL(request.url).pathname.startsWith('/_next/')&&!new URL(request.url).pathname.startsWith('/__nextjs_')).filter(request=>request.method!=='GET'),[]);
 }finally{fs.writeFileSync(snapshot,original);await browser.close();}
});
