// GET-only local preview checks; immutable projection bytes restored after corruption test.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3103';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const snapshot=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness/prospectus.json');
const output=path.resolve(__dirname,'../../var/d5g-browser');
test('D5g prospectus evidence never becomes an eligible batch by implication',{timeout:120000},async(t)=>{
 fs.mkdirSync(output,{recursive:true});
 const original=fs.readFileSync(snapshot);
 const browser=await chromium.launch({headless:true,executablePath:process.env.EQUITY_CHROMIUM_EXECUTABLE||undefined});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
 try{
  await t.test('current findings, reconciliation and annual rows open provenance',async()=>{
   await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.locator('[data-prospectus-review]').waitFor();
   assert.equal(await page.locator('[data-prospectus-check]').count(),4);
   assert.match(await page.locator('[data-prospectus-candidate]').innerText(),/BLOCKED/);
   assert.match(await page.locator('[data-exhibit-review]').innerText(),/SAVED ELEVEN-EXHIBIT REVIEW/);
   for(const detail of await page.locator('[data-prospectus-check]').all()){
    await detail.locator('summary').focus();await page.keyboard.press('Enter');
    await detail.getByRole('button').click();const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert.ok(await dialog.locator('a[href^="https://"]').count());
    assert.match(await dialog.innerText(),/Evidence and limits|Cross-edition reconciliation/);
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
    await detail.locator('summary').click();
   }
   assert.match(await page.locator('[data-prospectus-review]').innerText(),/registration history unreviewed/);
   assert.match(await page.locator('[aria-labelledby="candidate-metric-title"]').innerText(),/N\/A/);
   await page.screenshot({path:path.join(output,'desktop.png')});
  });
  await t.test('mobile and keyboard keep all cutoff meanings readable',async()=>{
   for(const width of [320,390,768,1440]){
    await page.setViewportSize({width,height:1000});
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);
   }
   await page.setViewportSize({width:390,height:900});
   const detail=page.locator('[data-prospectus-check="statements"]');
   await detail.locator('summary').click();await detail.getByRole('button').click();
   await page.getByRole('dialog').waitFor();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:path.join(output,'mobile-evidence.png')});
   await page.keyboard.press('Escape');await detail.locator('summary').click();
  });
  await t.test('corrupt prospectus artifact fails closed and Retry restores',async()=>{
   fs.writeFileSync(snapshot,'{}');
   await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();
   assert.equal(await page.locator('[data-analysis-input]').count(),0);
   fs.writeFileSync(snapshot,original);await page.getByRole('button',{name:'Retry',exact:true}).click();
   await page.locator('[data-prospectus-review]').waitFor();
  });
  assert.ok(errors.every(e=>/snapshot verification failed|An error occurred in the Server Components render/i.test(e)));
  assert.ok(requests.every(r=>['127.0.0.1','localhost'].includes(new URL(r.url).hostname)));
  assert.deepEqual(requests.filter(r=>!new URL(r.url).pathname.startsWith('/_next/')&&!new URL(r.url).pathname.startsWith('/__nextjs_')).filter(r=>r.method!=='GET'),[]);
 }finally{fs.writeFileSync(snapshot,original);await browser.close();}
});
