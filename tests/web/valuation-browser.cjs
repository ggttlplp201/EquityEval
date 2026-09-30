const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require(process.env.EQUITY_PLAYWRIGHT_MODULE || 'playwright');
const base = process.env.EQUITY_PREVIEW_URL || 'http://127.0.0.1:3102';
assert.ok(['127.0.0.1', 'localhost'].includes(new URL(base).hostname));
const output = path.resolve(__dirname, '../../var/s8a-browser');

test('S8a read-only valuation flows and responsive states', { timeout: 120000 }, async (t) => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, executablePath: process.env.EQUITY_CHROMIUM_EXECUTABLE || undefined });
  const page = await browser.newPage();
  const errors = [], requests = [];
  page.on('pageerror', error => errors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error' && !message.location().url.endsWith('/favicon.ico')) errors.push(message.text()); });
  page.on('request', request => requests.push({ url: request.url(), method: request.method() }));
  try {
    for (const width of [320, 390, 768, 1440]) {
      await t.test(`reference, keyboard, sensitivities and evidence at ${width}`, async () => {
        await page.setViewportSize({ width, height: 1000 });
        await page.goto(base + '/development/valuation', { waitUntil: 'networkidle' });
        assert.equal(await page.getByRole('button', { name: 'Reverse DCF', exact: true }).getAttribute('aria-pressed'), 'true');
        assert.match(await page.locator('main').innerText(), /173.4375/);
        assert.match(await page.locator('main').innerText(), /193.4375/);
        const selector = page.getByLabel('Scenario', { exact: true });
        await selector.focus(); await page.keyboard.press('r'); await page.keyboard.press('Enter');
        await selector.selectOption('1');
        assert.match(await page.getByRole('status').innerText(), /reference.*Unique solution/);
        assert.match(await page.locator('main').innerText(), /20%/);
        await page.getByText('Numerical evidence · exact intervals', { exact: true }).press('Enter');
        assert.match(await page.locator('details[open]').innerText(), /Root intervals/);
        await page.getByText('Numerical evidence · exact intervals', { exact: true }).press('Enter');
        const forecast = page.getByText('Forecast and terminal amounts · exact USD', { exact: true });
        await forecast.press('Enter');
        const first = page.locator('details[open] tbody tr').first();
        assert.deepEqual((await first.locator('td').allTextContents()).map(Number), [1, 110, 22, 5.5, 16.5, 5.5, 11, 10]);
        await forecast.press('Enter');
        const evidence = page.getByRole('button', { name: 'Implied parameter: 20%. Inspect evidence' });
        await evidence.focus(); await page.keyboard.press('Enter');
        await page.getByRole('dialog').waitFor({ state: 'visible' });
        assert.match(await page.getByRole('dialog').innerText(), /Source lineage/);
        assert.match(await page.getByRole('dialog').innerText(), /decimal80_half_even_interval_outward_v1/);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        await page.keyboard.press('Escape');
        await page.getByRole('dialog').waitFor({ state: 'hidden' });
        assert.equal(await evidence.evaluate(node => document.activeElement === node), true);
        await page.getByRole('button', { name: 'Sensitivity', exact: true }).press('Enter');
        assert.equal(await page.getByRole('table').filter({ has: page.locator('caption', { hasText: 'Discount rate and terminal growth' }) }).count(), 1);
        await page.getByLabel('Grid', { exact: true }).selectOption('1');
        const cell = page.getByRole('button', { name: '17.34375', exact: true });
        await cell.focus(); await page.keyboard.press('Enter');
        assert.equal(await cell.getAttribute('aria-pressed'), 'true');
        assert.match(await page.locator('[aria-live="polite"]').innerText(), /terminal operating margin: 0.2/);
        assert.match(await page.locator('[aria-live="polite"]').innerText(), /reinvestment to revenue: 0.05/);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `overflow ${width}`);
        await page.screenshot({ path: path.join(output, `sensitivity-${width}.png`), fullPage: true });
        await page.getByRole('button', { name: 'Reverse DCF', exact: true }).click();
        await page.screenshot({ path: path.join(output, `reverse-${width}.png`), fullPage: true });
        for (const state of ['no_solution_in_domain', 'non_unique', 'inconclusive', 'unavailable', 'missing']) {
          await page.getByLabel('Fictional example', { exact: true }).focus();
          await page.getByLabel('Fictional example', { exact: true }).selectOption(state);
          await page.waitForURL(base + '/development/valuation?example=' + state, { timeout: 10000 }).catch(async error => { throw new Error(`${error.message}; actual URL ${page.url()}; status ${await page.getByRole('status').innerText()}; selected ${await page.getByLabel('Fictional example', { exact: true }).inputValue()}`); });
          await page.waitForLoadState('networkidle');
          if (state === 'missing') assert.match(await page.locator('main').innerText(), /Missing saved result/);
          else {
            assert.equal(await page.locator('[data-solve-state]').getAttribute('data-solve-state'), state);
            assert.match(await page.getByRole('button', { name: /^Implied parameter:/ }).innerText(), /N\/A/);
            await page.getByRole('button', { name: 'Sensitivity', exact: true }).click();
            assert.match(await page.getByRole('region', { name: 'Sensitivity', exact: true }).innerText(), /N\/A/);
          }
          assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${state} overflow ${width}`);
        }
      });
    }
    assert.ok(requests.every(request => !new URL(request.url).pathname.startsWith('/development/company')), 'No unrelated Company fixture prefetch');
    await t.test('navigation, skip link and read-only network', async () => {
      await page.goto(base + '/development/company', { waitUntil: 'networkidle' });
      await page.getByRole('link', { name: 'Fictional reverse DCF' }).click();
      await page.waitForURL(base + '/development/valuation');
      await page.getByRole('link', { name: 'Skip to main content' }).focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'main-content');
      await page.getByRole('link', { name: 'Valuation guide', exact: true }).click();
      await page.waitForURL(base + '/help#valuation');
      assert.match(await page.locator('#valuation').innerText(), /root interval/);
      assert.deepEqual(errors, []);
      assert.ok(requests.every(request => request.method === 'GET' && new URL(request.url).origin === base));
      assert.ok(requests.every(request => !new URL(request.url).pathname.startsWith('/api/')));
      fs.writeFileSync(path.join(output, 'network.json'), JSON.stringify({ errors, requests }, null, 2));
    });
  } finally { await browser.close(); }
});
