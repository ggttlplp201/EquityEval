const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3102';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const route=base+'/development/pilot/normalization';
const output=path.resolve(__dirname,'../../var/d5a-browser');
const snapshot=path.resolve(__dirname,'../../apps/web/src/features/normalization/snapshot.json');
test('D5a real normalization, exact evidence and recoverable read-only view',{timeout:180000},async t=>{
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({headless:true});const page=await browser.newPage();
 const requests=[],errors=[];page.on('request',r=>requests.push({url:r.url(),method:r.method()}));page.on('pageerror',e=>errors.push(String(e)));
 const ready=()=>page.locator('main[data-normalization-kind="real-crcl-normalization"]').waitFor();
 const inspect=async(button,expected)=>{await button.focus();await page.keyboard.press('Enter');const dialog=page.getByRole('dialog');await dialog.waitFor();const text=await dialog.innerText();for(const value of expected)assert.ok(text.includes(value),value);await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});assert.ok(await button.evaluate(n=>n===document.activeElement));};
 const original=fs.readFileSync(snapshot);
 try{
  for(const width of [320,390,768,1440])await t.test('real facts and evidence at '+width,async()=>{
   await page.setViewportSize({width,height:1000});await page.goto(route,{waitUntil:'networkidle'});await ready();
   assert.match(await page.locator('[data-normalized-concept="revenue"]').innerText(),/\$2,746,642,000/);
   assert.match(await page.locator('[data-normalized-concept="operating_income"]').innerText(),/\$-96,435,000/);
   await inspect(page.getByRole('button',{name:'Inspect Revenue and reserve income',exact:true}),['2746642000','0001876042-26-000062','2026-09-21','2,746,642','Decimals','-3','REAL APPLICATION / CRCL']);
   await inspect(page.getByRole('button',{name:'View calculation status ↗'}),['inventory_history_incomplete','event_history_incomplete','False']);
   await page.getByLabel('History selection').selectOption('before_filing');assert.equal(await page.locator('[data-normalized-concept] strong').allTextContents().then(x=>x.join('|')),'N/A|N/A');
   await inspect(page.getByRole('button',{name:'Inspect Revenue and reserve income',exact:true}),['coverage_unavailable','2026-03-08']);
   await page.getByLabel('History selection').selectOption('original');await inspect(page.getByRole('button',{name:'Inspect Revenue and reserve income',exact:true}),['earliest_available','2746642000']);
   await page.getByLabel('History selection').selectOption('as_filed');
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
   await page.evaluate(()=>{document.activeElement.blur();scrollTo(0,0)});await page.screenshot({path:path.join(output,`normalization-${width}.png`),fullPage:true});
  });
  await t.test('pipeline links to actual published stage and help',async()=>{
   await page.getByRole('link',{name:'← Application pipeline'}).click();await page.locator('[data-stage="normalization"]').click();
   assert.equal(await page.locator('[data-stage="normalization"]').getAttribute('data-state'),'verified');
   await page.getByRole('link',{name:'Inspect normalized financials ↗'}).click();await ready();
   await inspect(page.getByRole('button',{name:'Inspect publication dates and evidence'}),['923458e4-242d-4731-9f57-9fd6779d7e9a','2026-09-30','9 retained Company Facts candidates']);
   await page.getByRole('link',{name:'User guide ↗',exact:true}).click();await page.locator('#real-normalization').waitFor();
   assert.deepEqual(errors,[]);assert.ok(requests.every(r=>r.method==='GET'&&new URL(r.url).origin===base&&!new URL(r.url).pathname.startsWith('/api/')));
   fs.writeFileSync(path.join(output,'network.json'),JSON.stringify({requests,errors},null,2));
  });
  await t.test('corrupt snapshot shows N/A and restores with Retry',async()=>{
   fs.writeFileSync(snapshot,'{}');await page.goto(route,{waitUntil:'networkidle'});await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();assert.equal(await page.locator('[data-normalized-concept]').count(),0);
   fs.writeFileSync(snapshot,original);await page.getByRole('button',{name:'Retry',exact:true}).click();await ready();
  });
 }finally{fs.writeFileSync(snapshot,original);await browser.close();}
});
