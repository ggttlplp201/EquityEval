const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3103';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const snapshot=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness/real.json');
const output=path.resolve(__dirname,'../../var/d5j-browser');
test('D5j published real result retains provenance and explicit gaps',{timeout:120000},async(t)=>{
 fs.mkdirSync(output,{recursive:true});const original=fs.readFileSync(snapshot);
 const browser=await chromium.launch({headless:true,executablePath:process.env.EQUITY_CHROMIUM_EXECUTABLE||undefined});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
 try{
  await t.test('one signed result and two operands open complete evidence',async()=>{
   await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   const panel=page.locator('[data-real-fundamentals]');await panel.waitFor();
   assert.match(await panel.locator('[data-real-margin]').innerText(),/-3.51%/);
   assert.equal(await panel.locator('[data-real-operand]').count(),2);
   assert.equal(await panel.locator('[data-real-gap]').count(),9);
   assert.match(await panel.innerText(),/2026-10-15T21:59:05.195192Z/);
   for(const button of await panel.locator('[data-real-margin], [data-real-operand]').all()){
    await button.click();const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert.ok(await dialog.locator('a[href^="https://"]').count()>=2);
    assert.match(await dialog.innerText(),/0001876042-26-000062/);
    assert.match(await dialog.innerText(),/sha256|SHA-256|Hash/i);
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
   }
   await panel.getByRole('button',{name:'Inspect policy and safety checks'}).click();
   await page.getByRole('dialog').waitFor();assert.match(await page.getByRole('dialog').innerText(),/365/);
   await page.keyboard.press('Escape');await panel.evaluate(e=>e.scrollIntoView());
   await page.screenshot({path:path.join(output,'desktop.png')});
  });
  await t.test('exact missing requirements and mobile keyboard access',async()=>{
   const gap=page.locator('[data-real-gap="current_ratio"]');await gap.locator('summary').click();
   assert.match(await gap.innerText(),/current assets.*current liabilities/i);
   for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Overflow at ${width}`);}
   await page.setViewportSize({width:390,height:900});const button=page.locator('[data-real-margin]');
   await button.focus();await page.keyboard.press('Enter');await page.getByRole('dialog').waitFor();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.screenshot({path:path.join(output,'mobile-evidence.png')});await page.keyboard.press('Escape');
   assert.equal(await button.evaluate(e=>e===document.activeElement),true);
  });
  await t.test('corrupt published artifact fails closed and Retry recovers',async()=>{
   fs.writeFileSync(snapshot,'{}');await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();assert.equal(await page.locator('[data-real-margin]').count(),0);
   fs.writeFileSync(snapshot,original);await page.getByRole('button',{name:'Retry',exact:true}).click();await page.locator('[data-real-fundamentals]').waitFor();
  });
  assert.ok(errors.every(e=>/snapshot verification failed|An error occurred in the Server Components render/i.test(e)));
  assert.ok(requests.every(r=>['127.0.0.1','localhost'].includes(new URL(r.url).hostname)));
  assert.deepEqual(requests.filter(r=>!new URL(r.url).pathname.startsWith('/_next/')&&!new URL(r.url).pathname.startsWith('/__nextjs_')).filter(r=>r.method!=='GET'),[]);
 }finally{fs.writeFileSync(snapshot,original);await browser.close();}
});
