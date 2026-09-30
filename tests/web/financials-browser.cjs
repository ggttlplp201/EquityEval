const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.EQUITY_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.EQUITY_PREVIEW_URL||'http://127.0.0.1:3102';
assert.ok(['127.0.0.1','localhost'].includes(new URL(base).hostname));
const route=base+'/development/company/financials';
const output=path.resolve(__dirname,'../../var/s8c-browser');
const fixturePath=path.resolve(__dirname,'../../apps/web/src/features/financials/fixture.json');
const originalBytes=fs.readFileSync(fixturePath);
const bundle=JSON.parse(originalBytes);

test('S8c selected statements, editions and evidence',{timeout:180000},async t=>{
  fs.mkdirSync(output,{recursive:true});
  const browser=await chromium.launch({headless:true});
  const page=await browser.newPage();
  const errors=[],requests=[];
  page.on('pageerror',e=>errors.push(String(e)));
  page.on('console',m=>{if(m.type()==='error'&&!m.location().url.endsWith('/favicon.ico'))errors.push(m.text())});
  page.on('request',r=>requests.push({url:r.url(),method:r.method()}));
  const ready=async edition=>{
    const saved=bundle.snapshots.find(s=>s.edition===edition);
    await page.locator(`main[data-snapshot="${saved.snapshot_id}"]`).waitFor({state:'visible'});
    await page.locator('[data-concept="revenue"]').waitFor({state:'visible'});
    assert.equal(await page.getByLabel('Saved edition',{exact:true}).inputValue(),edition);
  };
  const inspect=async(title,expected)=>{
    const button=page.locator(`[data-evidence-value="${title}"]`);
    await button.focus();await page.keyboard.press('Enter');
    const dialog=page.getByRole('dialog');await dialog.waitFor({state:'visible'});
    const text=await dialog.innerText();
    for(const word of ['Snapshot identity','Exact source evidence','source_hash','source_locator','known_on','retrieved_at','identity_decimal',expected])assert.ok(text.includes(word),word);
    await page.keyboard.press('Escape');await dialog.waitFor({state:'hidden'});
    assert.ok(await button.evaluate(n=>n===document.activeElement));
  };
  try{
    for(const width of [320,390,768,1440])await t.test(`financial statements at ${width}`,async()=>{
      await page.setViewportSize({width,height:1000});await page.goto(route,{waitUntil:'networkidle'});await ready('annual_original');
      assert.equal(await page.locator('[data-evidence-value="Revenue"]').innerText(),'100.1235');
      assert.deepEqual(await page.locator('[data-statement]').evaluateAll(nodes=>nodes.map(n=>n.dataset.statement)),['income','balance_sheet','cash_flow']);
      assert.match(await page.locator('#income').innerText(),/2025-01-01 – 2025-12-31/);
      assert.match(await page.locator('#balance_sheet').innerText(),/At 2025-12-31/);
      assert.equal(await page.getByRole('button',{name:'TTM · N/A',exact:true}).isDisabled(),true);
      await inspect('Revenue','100.1234567');
      for(const [family,title] of [['income','Income statement'],['balance_sheet','Balance sheet'],['cash_flow','Cash flow']]){
        const statement=bundle.snapshots[0].statements.find(s=>s.family===family);
        for(const [field,label] of [['available','available lines'],['requested','requested lines']]){
          const name=title+' · '+label;
          assert.equal(await page.locator(`[data-evidence-value="${name}"]`).innerText(),String(statement.coverage[field]));
          const button=page.locator(`[data-evidence-value="${name}"]`);
          await button.focus();await page.keyboard.press('Enter');await page.getByRole('dialog').waitFor({state:'visible'});
          const text=await page.getByRole('dialog').innerText();
          const exact=JSON.parse(await page.getByRole('dialog').locator('section').filter({has:page.getByRole('heading',{name:'Exact source evidence',exact:true})}).locator('dd').innerText());
          assert.deepEqual(exact.coverage,statement.coverage);assert.deepEqual(exact.rows,statement.rows);
          for(const expected of [bundle.snapshots[0].snapshot_id,statement.rows[0].evidence.source_id,...statement.rows.map(row=>row.concept)])assert.ok(text.includes(expected),expected);
          await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});
          assert.ok(await button.evaluate(node=>node===document.activeElement));
        }
      }

      await inspect('Cash and cash equivalents','"period_kind": "instant"');
      assert.equal(await page.locator('[data-evidence-value="Dividends paid"]').innerText(),'N/A');
      await inspect('Dividends paid','source_not_supplied');
      await page.getByRole('button',{name:'Inspect full snapshot evidence',exact:true}).click();
      await page.getByRole('dialog').waitFor({state:'visible'});assert.ok(!(await page.getByRole('dialog').innerText()).includes('102.9876543'));await page.keyboard.press('Escape');
      await page.getByLabel('Saved edition',{exact:true}).selectOption('annual_revised');await page.waitForURL(url=>url.searchParams.get('edition')==='annual_revised');await ready('annual_revised');
      assert.equal(await page.locator('[data-evidence-value="Revenue"]').innerText(),'102.9877');
      assert.match(await page.locator('[data-concept="revenue"]').innerText(),/Restated/);
      assert.match(await page.locator('[data-concept="gross_profit"]').innerText(),/Unchanged/);
      await inspect('Revenue',bundle.snapshots[0].statements[0].rows[0].evidence.evidence_id);
      await page.evaluate(()=>{document.activeElement.blur();scrollTo(0,0)});
      assert.ok(await page.locator("table").evaluateAll(nodes=>nodes.every(n=>n.scrollWidth<=n.clientWidth)),"Statement columns must fit their container");
      await page.screenshot({path:path.join(output,`financials-${width}.png`),fullPage:true});
      await page.getByRole('button',{name:'Quarterly',exact:true}).click();await page.waitForURL(url=>url.searchParams.get('basis')==='quarter');await ready('quarter');
      assert.equal(await page.locator('[data-evidence-value="Revenue"]').innerText(),'30');
      assert.match(await page.locator('#income').innerText(),/2026-01-01 – 2026-03-31/);
      assert.match(await page.locator('#balance_sheet').innerText(),/At 2026-03-31/);
      assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`${width} overflow`);
      await page.getByRole('link',{name:'Skip to main content'}).focus();await page.keyboard.press('Enter');assert.equal(await page.evaluate(()=>document.activeElement.id),'main-content');
    });
    await t.test('navigation, unavailable selections and GET-only requests',async()=>{
      await page.getByRole('link',{name:'Company overview example',exact:true}).click();await page.waitForURL(base+'/development/company');await page.waitForLoadState('networkidle');
      await page.getByRole('link',{name:'Separate financials example ↗',exact:true}).click();await page.waitForURL(route);await ready('annual_original');
      await page.getByRole('link',{name:'Fundamentals example',exact:true}).click();await page.waitForURL(base+'/development/company/ratios');await page.getByRole('heading',{name:'Fundamentals',exact:true}).waitFor();
      await page.getByRole('navigation',{name:'Main'}).getByRole('link',{name:'Financials',exact:true}).click();await page.waitForURL(route);await ready('annual_original');
      await page.getByRole('link',{name:'Financials guide ↗',exact:true}).click();await page.waitForURL(base+'/help#financials');assert.match(await page.locator('#financials').innerText(),/Balance sheet/);
      for(const query of ['?basis=ttm','?edition=missing','?basis=quarter&edition=annual_original','?basis=annual&basis=quarter','?unexpected=true']){
        await page.goto(route+query,{waitUntil:'networkidle'});assert.equal(await page.locator('[data-statement]').count(),0);await page.getByRole('heading',{name:'N/A',exact:true}).waitFor();
        assert.equal(await page.getByRole('link',{name:'Choose a saved edition ↗',exact:true}).count(),1);
      }
      assert.deepEqual(errors,[]);
      assert.ok(requests.every(r=>r.method==='GET'&&new URL(r.url).origin===base));
      assert.ok(requests.every(r=>!new URL(r.url).pathname.startsWith('/api/')));
      fs.writeFileSync(path.join(output,'network.json'),JSON.stringify({errors,requests},null,2));
    });
    await t.test('pending selection and actual missing-fixture error recover without stale values',async()=>{
      await page.goto(route,{waitUntil:'networkidle'});await ready('annual_original');
      let release;const gate=new Promise(resolve=>{release=resolve});
      const pattern='**/development/company/financials?basis=quarter*';
      await page.route(pattern,async r=>{await gate;await r.continue()});
      let pendingTimer;
      const pendingState=new Promise((resolve,reject)=>{
        pendingTimer=setTimeout(()=>reject(new Error('Pending state was not rendered')),5000);
        page.on('console',message=>{if(message.text().startsWith('S8C_PENDING:'))resolve(JSON.parse(message.text().slice(12)))});
      });
      // Observe the current document before holding navigation; Playwright frame reads
      // wait for that held navigation and would deadlock the test itself.
      await page.evaluate(()=>{
        const observer=new MutationObserver(()=>{
          const text=document.querySelector('[role=status]')?.textContent;
          if(text==='Loading saved financials…'){
            console.debug('S8C_PENDING:'+JSON.stringify({text,disabled:document.querySelector('select').disabled}));
            observer.disconnect();
          }
        });
        observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true});
      });
      try{
        await page.getByRole('button',{name:'Quarterly',exact:true}).click({noWaitAfter:true});
        const pending=await pendingState;
        assert.deepEqual(pending,{text:'Loading saved financials…',disabled:true});
        fs.writeFileSync(path.join(output,'loading-state.json'),JSON.stringify(pending));
      }finally{clearTimeout(pendingTimer);release();}
      await page.waitForURL(url=>url.searchParams.get('basis')==='quarter');await ready('quarter');await page.unroute(pattern);
      // Exercise the real server read failure; restore the exact checked fixture even on error.
      fs.renameSync(fixturePath,fixturePath+'.s8c-test-backup');
      try{
        await page.goto(route,{waitUntil:'networkidle'});
        await page.locator('main[role=alert]').waitFor();
        assert.match(await page.locator('main[role=alert]').innerText(),/FINANCIALS/);
        assert.equal(await page.locator('[data-statement]').count(),0);
        await page.screenshot({path:path.join(output,'error.png')});
      }finally{fs.renameSync(fixturePath+'.s8c-test-backup',fixturePath);}
      assert.deepEqual(fs.readFileSync(fixturePath),originalBytes);
      await page.getByRole('button',{name:'Retry',exact:true}).click();await ready('annual_original');
    });
  }finally{await browser.close();}
});
