const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3103';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const artifact=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness/history.json');
const output=path.resolve(__dirname,'../../var/d5l-browser');
test('D5l retained history remains blocked with inspectable evidence',{timeout:180000},async(t)=>{
 fs.mkdirSync(output,{recursive:true});const original=fs.readFileSync(artifact);
 const browser=await chromium.launch({headless:true,executablePath:process.env.EQUITY_CHROMIUM_EXECUTABLE||undefined});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
 try{
  await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
  const panel=page.locator('[data-history-review]');await panel.waitFor();
  await t.test('partial acquisition never becomes a cutoff or metric',async()=>{
   assert.match(await panel.innerText(),/46 of 47 documents/);
   assert.match(await panel.innerText(),/Not captured/);
   assert.match(await panel.innerText(),/does not claim completed accounting reconciliation/);
   assert.equal(await panel.locator('[data-history-metric]').count(),4);
   assert.equal(await page.locator('[data-broader-metric]').count(),6);
   await page.screenshot({path:path.join(output,'desktop.png')});
  });
  await t.test('all bodies have accessible evidence and exact blocked reasons',async()=>{
   await panel.locator('[data-history-roster] > summary').focus();await page.keyboard.press('Enter');
   assert.equal(await panel.locator('[data-history-body]').count(),47);
   for(const accession of ['0000950123-25-000606','0000000000-25-000390','0001876042-26-000116']){
    const row=panel.locator(`[data-history-body="${accession}"]`);await row.locator('summary').click();
    const button=row.getByRole('button');await button.click();const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert.match(await dialog.innerText(),new RegExp(accession));
    if(accession==='0000000000-25-000390')assert.match(await dialog.innerText(),/pdf_limits_unavailable/);
    if(accession==='0001876042-26-000116')assert.match(await dialog.innerText(),/No complete retained body/);
    else assert.ok(await dialog.locator('a[href^="https://www.sec.gov"]').count());
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
    assert.ok(await button.evaluate(e=>e===document.activeElement));await row.locator('summary').click();
   }
  });
  await t.test('mobile layouts fit',async()=>{
   for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);}
   await page.setViewportSize({width:390,height:900});await panel.scrollIntoViewIfNeeded();await page.screenshot({path:path.join(output,'mobile.png')});
  });
  await t.test('corrupt history artifact hides results and Retry recovers',async()=>{
   const count=errors.length;fs.writeFileSync(artifact,'{}');await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();assert.equal(await page.locator('[data-broader-metric]').count(),0);
   fs.writeFileSync(artifact,original);await page.getByRole('button',{name:'Retry',exact:true}).click();await panel.waitFor();
   assert.ok(errors.splice(count).every(e=>/snapshot verification failed|An error occurred in the Server Components render/i.test(e)));
  });
  assert.deepEqual(errors,[]);assert.ok(requests.every(r=>['127.0.0.1','localhost'].includes(new URL(r.url).hostname)));
  assert.ok(requests.filter(r=>!new URL(r.url).pathname.startsWith('/_next/')).every(r=>r.method==='GET'));
 }finally{fs.writeFileSync(artifact,original);await browser.close();}
});
