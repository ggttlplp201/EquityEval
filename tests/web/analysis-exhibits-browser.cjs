// Retained-evidence UI: local GET-only requests; damaged artifact restored in finally.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3103';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const snapshot=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness/exhibits.json');
const output=path.resolve(__dirname,'../../var/d5d-browser');
test('D5d exhibits support a bounded review, never current eligibility',{timeout:120000},async(t)=>{
 fs.mkdirSync(output,{recursive:true});
 const original=fs.readFileSync(snapshot);
 const browser=await chromium.launch({headless:true,executablePath:process.env.EQUITY_CHROMIUM_EXECUTABLE||undefined});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[],requests=[];
 page.on('pageerror',error=>errors.push(String(error)));
 page.on('request',request=>requests.push({url:request.url(),method:request.method()}));
 try{
  await t.test('all eleven scoped findings open source evidence with keyboard',async()=>{
   await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.locator('[data-exhibit-review]').waitFor();
   assert.equal(await page.locator('[data-exhibit]').count(),11);
   assert.match(await page.locator('[data-safety-review]').innerText(),/SAVED PRE-EXHIBIT REVIEW/);
   for(const detail of await page.locator('[data-exhibit]').all()){
    await detail.locator('summary').focus();await page.keyboard.press('Enter');
    assert.match(await detail.innerText(),/Review scope/);
    await detail.getByRole('button').click();
    const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert.match(await dialog.innerText(),/Exact retained quote/);
    assert.match(await dialog.innerText(),/2026-10/);
    assert.ok(await dialog.locator('a[href^="https://www.sec.gov/"]').count());
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
    await detail.locator('summary').click();
   }
   assert.match(await page.locator('[aria-labelledby="candidate-metric-title"]').innerText(),/N\/A/);
   assert.match(await page.locator('[data-exhibit-review]').innerText(),/Current inventory is not current clearance/);
   await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  });
  await t.test('mobile disclosures and long evidence do not overflow',async()=>{
   for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:1000});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);
   }
   await page.setViewportSize({width:390,height:900});
   const annual=page.locator('[data-exhibit="exhibit-5"]');
   await annual.locator('summary').click();await annual.getByRole('button').click();
   await page.getByRole('dialog').waitFor();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:path.join(output,'mobile-evidence.png'),fullPage:true});
   await page.keyboard.press('Escape');await annual.locator('summary').click();
  });
  await t.test('changed exhibit projection fails closed and Retry recovers',async()=>{
   fs.writeFileSync(snapshot,'{}');
   await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();
   assert.equal(await page.locator('[data-analysis-input]').count(),0);
   fs.writeFileSync(snapshot,original);
   await page.getByRole('button',{name:'Retry',exact:true}).click();
   await page.locator('[data-exhibit-review]').waitFor();
  });
  assert.ok(errors.every(error=>/snapshot verification failed|An error occurred in the Server Components render/i.test(error)));
  assert.ok(requests.every(request=>['127.0.0.1','localhost'].includes(new URL(request.url).hostname)));
  assert.deepEqual(requests.filter(request=>!new URL(request.url).pathname.startsWith('/_next/')&&!new URL(request.url).pathname.startsWith('/__nextjs_')).filter(request=>request.method!=='GET'),[]);
 }finally{fs.writeFileSync(snapshot,original);await browser.close();}
});
