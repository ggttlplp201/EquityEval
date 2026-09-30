const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const zlib=require('node:zlib');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3102';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const route=base+'/development/company';
const root=path.resolve(__dirname,'../..');
const output=path.join(root,'var/s8d-browser');
const fixturePath=path.join(root,'apps/web/src/features/company/overview.json');
const originalBytes=fs.readFileSync(fixturePath);
const manifest=JSON.parse(originalBytes);
const bundle=JSON.parse(zlib.gunzipSync(fs.readFileSync(path.join(root,'apps/web/src/features/company/fixture.json.gz'))));
test('S8d Overview identity, evidence and read-only integration',{timeout:240000},async t=>{
 fs.mkdirSync(output,{recursive:true});
 const browser=await chromium.launch({headless:true});const page=await browser.newPage();
 const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(String(e)));
 page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
 const ready=async(company='computing-01',date='2026-06-30')=>{
  const view=bundle.views[date+'|'+company];
  await page.locator(`main[data-view-id="${view.id}"]`).waitFor({state:'visible'});
  await page.locator('[data-workspace="overview"]').waitFor({state:'visible'});
 };
 const inspect=async(button,expected)=>{
  await button.focus();await page.keyboard.press('Enter');
  const dialog=page.getByRole('dialog');await dialog.waitFor({state:'visible'});
  const text=await dialog.innerText();for(const word of expected)assert.ok(text.includes(word),word);
  await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
  assert.ok(await button.evaluate(n=>n===document.activeElement));
 };
 try{
  for(const width of [320,390,768,1440])await t.test(`Overview at ${width}`,async()=>{
   await page.setViewportSize({width,height:1000});await page.goto(route,{waitUntil:'networkidle'});await ready();
   assert.ok((await page.title()).startsWith('Company Overview'));
   assert.deepEqual(await page.locator('[data-workspace]').evaluateAll(nodes=>nodes.map(n=>n.dataset.linkage)),['ready','separate','separate','separate']);
   for(const metric of ['pe','ps','pfcf'])assert.match(await page.locator(`[data-metric-id="${metric}"] button`).innerText(),/×/);
   assert.match(await page.locator('[data-metric-id="revenue_yoy"] button').innerText(),/%/);
   assert.match(await page.getByRole('table',{name:/Financial source amounts/}).locator('tbody tr').first().innerText(),/\$/);
   assert.match(await page.locator('#balance-title').locator('..').locator('..').innerText(),/N\/A[\s\S]*Cash, debt, assets, liabilities and equity are not supplied/);
   assert.match(await page.locator('#profitability-title').locator('..').locator('..').innerText(),/matching gross profit and consolidated net income were not supplied/);
   for(const [id,phrase] of [['cash-title','Separate CFO and cash PPE operands'],['valuation-title','Price per share, EPS, forward P/E']])assert.ok((await page.locator(`section[aria-labelledby="${id}"]`).innerText()).includes(phrase));
   const view=bundle.views['2026-06-30|computing-01'];const entry=manifest.entries[view.id];
   for(const label of Object.keys(entry.counts)){
    const button=page.locator(`[data-linkage-count="${label}"]`);assert.equal(await button.innerText(),label+': '+entry.counts[label]);
    await inspect(button,[view.id,view.snapshotId,'issuer_id: mismatch','security_id: proof unavailable',manifest.files['valuation/fixture.json']]);
   }
   for(const card of entry.cards){
    await inspect(page.getByRole('button',{name:card.title+' evaluation date. Inspect linkage evidence',exact:true}),[view.id,'Exact destination metadata','known_at','retrieved_at']);
   }
   const pe=view.metrics.find(m=>m.id==='pe');await inspect(page.locator('[data-metric-id="pe"] button'),[pe.value,view.snapshotId]);
   for(const years of ['3','5','10']){
    await page.getByRole('button',{name:years+'Y',exact:true}).click();
    const h=view.history[years];await inspect(page.getByRole('button',{name:h.coverageLabel,exact:true}),[h.windowStart,h.windowEnd,...h.missingDates]);
   }
   await page.getByRole('button',{name:'3Y',exact:true}).click();
   assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),width+' overflow');
   await page.evaluate(()=>{document.activeElement.blur();scrollTo(0,0)});await page.screenshot({path:path.join(output,`overview-${width}.png`),fullPage:true});
   await page.getByRole('link',{name:'Skip to main content'}).focus();await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>document.activeElement.id),'main-content');
  });
  await t.test('strict selectors and separate navigation',async()=>{
   await page.goto(route,{waitUntil:'networkidle'});await ready();
   await page.getByLabel('Evaluation date',{exact:true}).selectOption('2026-03-31');await ready('computing-01','2026-03-31');
   assert.equal(await page.getByLabel('Evaluation date',{exact:true}).inputValue(),'2026-03-31');
   for(const [title,destination] of [['Financials','/development/company/financials'],['Fundamentals','/development/company/ratios'],['Reverse DCF','/development/valuation']]){
    const card=page.locator('[data-workspace]').filter({has:page.getByRole('heading',{name:title,exact:true})});
    assert.match(await card.innerText(),/Separate fictional example[\s\S]*Opens its own default/);
    await card.getByRole('link',{name:'Open '+title+' ↗',exact:true}).click();await page.waitForURL(base+destination);await page.waitForLoadState('networkidle');
    assert.equal(new URL(page.url()).search,'');
    await page.goto(route+'?company=computing-01&asOf=2026-03-31',{waitUntil:'networkidle'});await ready('computing-01','2026-03-31');
   }
   for(const query of ['?unexpected=1','?company=CRCL','?company=','?asOf=2026-04-01','?company=computing-01&company=computing-01','?asOf=2026-06-30&asOf=2026-06-30']){
    await page.goto(route+query,{waitUntil:'networkidle'});await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();assert.equal(await page.locator('[data-workspace]').count(),0);
   }
   await page.getByRole('button',{name:'Choose a saved company ↗',exact:true}).click();await ready();
   assert.deepEqual(errors,[]);assert.ok(requests.every(r=>r.method==='GET'&&new URL(r.url).origin===base&&!new URL(r.url).pathname.startsWith('/api/')));
   fs.writeFileSync(path.join(output,'network.json'),JSON.stringify({errors,requests},null,2));
  });
  await t.test('pending state, missing manifest and Retry recovery',async()=>{
   await page.goto(route,{waitUntil:'networkidle'});await ready();
   let release;const gate=new Promise(resolve=>release=resolve);const pattern='**/development/company?company=computing-02*';
   await page.route(pattern,async r=>{await gate;await r.continue()});let timer;
   const pending=new Promise((resolve,reject)=>{timer=setTimeout(()=>reject(new Error('Pending state missing')),5000);page.on('console',m=>{if(m.text().startsWith('S8D_PENDING:'))resolve(JSON.parse(m.text().slice(12)))});});
   await page.evaluate(()=>{const observer=new MutationObserver(()=>{const text=document.querySelector('[role=status]')?.textContent;if(text==='Loading the selected company snapshot…'){console.debug('S8D_PENDING:'+JSON.stringify({text,disabled:[...document.querySelectorAll('select')].slice(0,2).every(n=>n.disabled)}));observer.disconnect();}});observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true});});
   const selecting=page.getByLabel('Fictional company',{exact:true}).selectOption('computing-02');
   try{assert.deepEqual(await pending,{text:'Loading the selected company snapshot…',disabled:true});}finally{clearTimeout(timer);release();await selecting;}
   await ready('computing-02');await page.unroute(pattern);
   fs.renameSync(fixturePath,fixturePath+'.s8d-test-backup');
   try{await page.goto(route,{waitUntil:'networkidle'});await page.locator('main[role=alert]').waitFor();assert.equal(await page.locator('[data-workspace]').count(),0);await page.screenshot({path:path.join(output,'error.png')});}finally{fs.renameSync(fixturePath+'.s8d-test-backup',fixturePath);}
   assert.deepEqual(fs.readFileSync(fixturePath),originalBytes);await page.getByRole('button',{name:'Retry',exact:true}).click();await ready();
  });
 }finally{await browser.close();}
});
