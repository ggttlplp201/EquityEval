const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3103';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const output=path.resolve(__dirname,'../../var/d5k-browser');
const artifact=path.resolve(__dirname,'../../apps/web/src/features/analysis-readiness/broader.json');

test('D5k paired results remain scoped, inspectable and fail closed',{timeout:180000},async(t)=>{
 fs.mkdirSync(output,{recursive:true});const original=fs.readFileSync(artifact);
 const browser=await chromium.launch({headless:true,executablePath:process.env.EQUITY_CHROMIUM_EXECUTABLE||undefined});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(String(e)));page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
 try{
  await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
  const panel=page.locator('[data-broader-fundamentals]');await panel.waitFor();
  await t.test('six supported metrics use two separate period results',async()=>{
   assert.match(await page.locator('main > header').innerText(),/10 normalized source concepts/);
   assert.match(await page.locator('main > header').innerText(),/6 supported definitions · annual 4 \/ closing 2/);
   assert.match(await page.locator('main > footer').innerText(),/HISTORICAL D5a BATCH/);
   assert.match(await page.locator('#readiness-boundary-title').innerText(),/Six reported metric definitions/);
   assert.equal(await panel.locator('[data-broader-result="annual"] [data-broader-metric]').count(),4);
   assert.equal(await panel.locator('[data-broader-result="instant"] [data-broader-metric]').count(),2);
   assert.match(await panel.locator('[data-broader-metric="net_margin_consolidated"]').innerText(),/-2.53%/);
   assert.match(await panel.locator('[data-broader-metric="free_cash_flow_ppe"]').innerText(),/529,697,000 USD/);
   assert.match(await panel.locator('[data-broader-metric="current_ratio"]').innerText(),/1.0328×/);
   assert.match(await panel.locator('[data-broader-metric="net_working_capital"]').innerText(),/2,473,072,000 USD/);
   assert.match(await panel.innerText(),/not coverage after that instant/);
   await page.screenshot({path:path.join(output,'desktop.png')});
  });
  await t.test('every metric opens exact source and immutable snapshot evidence',async()=>{
   for(const button of await panel.locator('[data-broader-metric]').all()){
    await button.click();const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert.match(await dialog.innerText(),/0001876042-26-000062/);
    assert.match(await dialog.innerText(),/snapshotId/);
    assert.ok(await dialog.locator('a[href^="https://www.sec.gov"]').count());
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
    assert.ok(await button.evaluate(e=>e===document.activeElement));
   }
  });
  await t.test('scope gaps and balance identity are explicit',async()=>{
   for(const result of await panel.locator('[data-broader-result]').all()){
    await result.getByText('Explicit gaps in this result',{exact:true}).click();
    const gap=result.locator('[data-broader-gap]').first();await gap.locator('summary').focus();await page.keyboard.press('Enter');
    assert.ok((await gap.locator('p').innerText()).length>30);
    await result.locator('[data-broader-accounting]').click();const dialog=page.getByRole('dialog');await dialog.waitFor();
    assert.match(await dialog.innerText(),/"matches":true/);await page.keyboard.press('Escape');
   }
   await panel.locator('[data-broader-review]').click();const dialog=page.getByRole('dialog');await dialog.waitFor();
   assert.match(await dialog.innerText(),/PDF extension unsupported/);await page.keyboard.press('Escape');
  });
  await t.test('comparative numbers remain ineligible source rows with provenance',async()=>{
   await panel.getByText('Inspect earlier annual comparative rows',{exact:true}).click();
   assert.equal(await panel.locator('[data-broader-comparative]').count(),8);
   await panel.locator('[data-broader-comparative]').first().click();const dialog=page.getByRole('dialog');await dialog.waitFor();
   assert.match(await dialog.innerText(),/not an eligible historical analysis operand/);await page.keyboard.press('Escape');
  });
  await t.test('desktop and mobile layouts fit and keyboard disclosure works',async()=>{
   for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:1000});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow ${width}`);}
   await page.setViewportSize({width:390,height:900});await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(output,'mobile.png')});
  });
  await t.test('corrupt broader artifact hides all results and Retry recovers',async()=>{
   const count=errors.length;fs.writeFileSync(artifact,'{}');await page.goto(base+'/development/pilot/analysis',{waitUntil:'networkidle'});
   await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();assert.equal(await page.locator('[data-broader-metric]').count(),0);
   fs.writeFileSync(artifact,original);await page.getByRole('button',{name:'Retry',exact:true}).click();await page.locator('[data-broader-fundamentals]').waitFor();
   assert.ok(errors.splice(count).every(e=>/snapshot verification failed|An error occurred in the Server Components render/i.test(e)));
  });
  assert.deepEqual(errors,[]);assert.ok(requests.every(r=>['127.0.0.1','localhost'].includes(new URL(r.url).hostname)));
  assert.ok(requests.filter(r=>!new URL(r.url).pathname.startsWith('/_next/')).every(r=>r.method==='GET'));
 }finally{fs.writeFileSync(artifact,original);await browser.close();}
});
