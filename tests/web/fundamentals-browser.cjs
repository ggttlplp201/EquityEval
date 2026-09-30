const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.EQUITY_PLAYWRIGHT_MODULE || 'playwright');
const base=process.env.EQUITY_PREVIEW_URL || 'http://127.0.0.1:3102';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const route=base+'/development/company/ratios';
const output=path.resolve(__dirname,'../../var/s8b-browser');
const bundle=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../../apps/web/src/features/fundamentals/fixture.json'),'utf8'));

test('S8b saved fundamentals, history and source evidence', {timeout:180000}, async t=>{
  fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage();
  const errors=[], requests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error'&&!m.location().url.endsWith('/favicon.ico'))errors.push(m.text())});
  page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
  const inspect=async(title,expected,historical=false)=>{
    const button=page.locator(`[data-evidence-value="${title}"]`);
    await button.focus();await page.keyboard.press('Enter');
    const dialog=page.getByRole('dialog');await dialog.waitFor({state:'visible'});
    assert.equal(await dialog.locator('h2').innerText(),title);
    const text=await dialog.innerText();
    for(const word of historical ? ['Snapshot identity','Historical snapshot references','eligible_snapshot_ids',expected] : ['Snapshot identity','Source evidence','selection_hash','normalizer_revision',expected])assert.ok(text.includes(word),word);
    if(historical){assert.ok(!text.includes('source_tag'));assert.ok(text.includes('Historical sample operands'));}
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
    assert.ok(await button.evaluate(n=>n===document.activeElement));
  };
  const select=async(label,value)=>{
    await page.getByLabel(label,{exact:true}).selectOption(value);
    const parameter={'History window':'years','Evaluation date':'date','Fundamentals example':'example'}[label];
    await page.waitForURL(url=>url.searchParams.get(parameter)===value);
    await page.waitForLoadState('networkidle');
    await page.getByRole('heading',{name:'Fundamentals',exact:true}).waitFor();
    assert.equal(await page.getByLabel(label,{exact:true}).inputValue(),value);
    const query=new URL(page.url()).searchParams;
    const expected=bundle.snapshots.find(s=>s.example===query.get('example')&&String(s.years)===query.get('years')&&s.payload.selector.as_of===query.get('date'));
    assert.ok(expected,'Exact selected saved snapshot must exist');
    await page.getByRole('button',{name:expected.snapshot_id,exact:true}).waitFor({state:'visible'});
    const first=page.locator(`[data-metric="${expected.payload.metrics[0].metric_id}"]`);
    await first.waitFor({state:'visible'});
    assert.equal(await first.getAttribute('data-status'),expected.payload.metrics[0].status);
    await page.getByRole('status').filter({hasText:'Loading saved selection'}).waitFor({state:'hidden'});
  };
  try{
    for(const width of [320,390,768,1440])await t.test(`saved selections at ${width}`,async()=>{
      await page.setViewportSize({width,height:1000});await page.goto(route,{waitUntil:'networkidle'});
      assert.match(await page.locator('main').innerText(),/Separate fictional example/);
      assert.deepEqual(await page.locator('[data-fundamentals-section]').evaluateAll(nodes=>nodes.map(n=>n.dataset.fundamentalsSection)),['Growth','Profitability','Cash generation','Balance sheet','Valuation']);
      assert.equal(await page.locator('[data-metric="operating_margin"] [data-evidence-value]').innerText(),'20%');
      assert.equal(await page.locator('[data-metric="free_cash_flow_ppe"] [data-evidence-value]').innerText(),'-8');
      assert.equal(await page.locator('[data-metric="trailing_pe"]').getAttribute('data-status'),'unsupported');
      await inspect('Operating margin','"formula_revision"');
      await page.getByText('Returns on capital',{exact:true}).press('Enter');
      assert.equal(await page.locator('[data-metric="return_on_assets"] [data-evidence-value]').innerText(),'10%');
      await inspect('Return on assets','"coefficients"');
      await page.getByText('Returns on capital',{exact:true}).press('Enter');
      assert.equal(await page.locator('[data-evidence-value="P25"]').innerText(),'15.5%');
      assert.equal(await page.locator('[data-evidence-value="P50"]').innerText(),'20%');
      assert.equal(await page.locator('[data-evidence-value="P75"]').innerText(),'22.5%');
      assert.equal(await page.getByRole('img',{name:/Saved Operating margin history/}).count(),1);
      await inspect('P25','0.155',true);
      await page.getByLabel('History metric',{exact:true}).selectOption('gross_margin');
      assert.equal(await page.locator('svg text').textContent(),'P25 = Median = P75');
      await page.getByLabel('History metric',{exact:true}).selectOption('operating_margin');
      for(const years of ['5','10']){
        await select('History window',years);
        assert.match(await page.locator('[data-history-window]').innerText(),new RegExp(`Requested ${years} years`));
        assert.match(await page.locator('[data-history-reasons]').innerText(),/insufficient history/);
        assert.equal(await page.locator('[data-evidence-value="Eligible history count"]').innerText(),'12');
        assert.equal(await page.locator('[data-evidence-value="Missing quarter count"]').innerText(),years==='5'?'8':'28');
        assert.equal(await page.locator('[data-evidence-value="P50"]').innerText(),'N/A');
        assert.equal(await page.getByRole('img').count(),0);
      }
      await select('History window','3');
      await select('Evaluation date','2026-03-31');
      assert.equal(await page.locator('[data-evidence-value="Eligible history count"]').innerText(),'11');
      await page.getByRole('button',{name:'Inspect full snapshot evidence',exact:true}).click();
      await page.getByRole('dialog').waitFor({state:'visible'});
      assert.ok(!(await page.getByRole('dialog').innerText()).includes('987654321'));
      await page.keyboard.press('Escape');
      await select('Evaluation date','2026-06-30');
      await page.screenshot({path:path.join(output,`fundamentals-${width}.png`),fullPage:true});
      for(const example of ['not_meaningful','missing','invalid','stale','inapplicable','balance']){
        await select('Fundamentals example',example);
        const saved=bundle.snapshots.find(s=>s.example===example&&s.years===3);
        for(const metric of saved.payload.metrics)assert.equal(await page.locator(`[data-metric="${metric.metric_id}"]`).getAttribute('data-status'),metric.status);
        for(const [status,count] of Object.entries(saved.payload.coverage.counts))assert.equal(await page.locator(`[data-coverage-status="${status}"] button`).innerText(),String(count));
        if(example==='not_meaningful')assert.equal(await page.locator('[data-evidence-value="Operating margin"]').innerText(),'N/M');
        if(example==='missing'||example==='invalid')assert.equal(await page.locator('[data-evidence-value="Operating margin"]').innerText(),'N/A');
        if(example==='stale')assert.equal(await page.locator('[data-evidence-value="Operating margin"]').innerText(),'20%');
        if(example==='balance'){assert.equal(await page.locator('[data-evidence-value="Current ratio"]').innerText(),'2×');await inspect('Current ratio','current_liabilities');}
        assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${example} ${width} overflow`);
      }
      await page.getByRole('link',{name:'Skip to main content'}).focus();await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(()=>document.activeElement.id),'main-content');
    });
    await t.test('Company, S8a and Help navigation; invalid selectors; read-only network',async()=>{
      await page.getByRole('link',{name:'Company overview example',exact:true}).click();await page.waitForURL(base+'/development/company');await page.waitForLoadState('networkidle');
      await page.getByRole('link',{name:'Separate fundamentals example ↗',exact:true}).click();await page.waitForURL(route);await page.waitForLoadState('networkidle');await page.getByRole('heading',{name:'Fundamentals',exact:true}).waitFor();
      await page.getByRole('link',{name:'Reverse DCF example',exact:true}).click();await page.waitForURL(base+'/development/valuation');await page.waitForLoadState('networkidle');await page.getByRole('heading',{name:'What must the model imply?',exact:true}).waitFor();
      await page.getByRole('navigation',{name:'Main'}).getByRole('link',{name:'Fundamentals',exact:true}).click();await page.waitForURL(route);await page.waitForLoadState('networkidle');await page.getByRole('heading',{name:'Fundamentals',exact:true}).waitFor();
      await page.getByRole('link',{name:'Fundamentals guide',exact:true}).click();await page.waitForURL(base+'/help#fundamentals');
      assert.match(await page.locator('#fundamentals').innerText(),/3, 5 or 10 years/);
      for(const query of ['?yeas=10','?years=4','?example=absent','?date=2030-01-01','?years=3&years=5']){
        await page.goto(route+query,{waitUntil:'networkidle'});assert.equal(await page.locator('[data-metric]').count(),0);
      }
      assert.deepEqual(errors,[]);
      assert.ok(requests.every(r=>r.method==='GET'&&new URL(r.url).origin===base));
      assert.ok(requests.every(r=>!new URL(r.url).pathname.startsWith('/api/')));
      fs.writeFileSync(path.join(output,'network.json'),JSON.stringify({errors,requests},null,2));
    });
  }finally{await browser.close();}
});
