// Run against the local preview only. No application writes or external navigation.
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require(process.env.EQUITY_PLAYWRIGHT_MODULE || "playwright");
const base = process.env.EQUITY_PREVIEW_URL || "http://127.0.0.1:3101";
assert.ok(["127.0.0.1", "localhost"].includes(new URL(base).hostname), "Only local previews are allowed");
const output = path.resolve(__dirname, "../../var/d4a-browser");
const route = "/development/pilot/pipeline";

test("saved CRCL pipeline interactions and accessibility", { timeout: 120000 }, async (t) => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({
    headless: true, executablePath: process.env.EQUITY_CHROMIUM_EXECUTABLE || undefined,
  });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [], requests = [], knownWarnings = [];
  page.on("pageerror", (error) => errors.push(String(error)));
  page.on("console", (message) => {
    if (message.type() !== "error") return;
    const warning = { text: message.text(), url: message.location().url };
    // Existing D2 preview warning, independently reproduced; all other errors fail.
    if (warning.url === base + "/favicon.ico" && /404/.test(warning.text)) knownWarnings.push(warning);
    else errors.push(warning);
  });
  page.on("request", (request) => requests.push({ url: request.url(), method: request.method() }));
  const go = (url) => page.goto(base + url, { waitUntil: "networkidle" });
  const select = async (id) => {
    const button = page.locator(`[data-stage="${id}"]`);
    await button.click();
    assert.equal(await button.getAttribute("aria-pressed"), "true");
    assert.equal(await page.locator('[data-stage][aria-pressed="true"]').count(), 1);
    assert.equal(await button.getAttribute("aria-controls"), "stage-panel");
  };
  try {
    await t.test("discoverable from pilot and readiness; preserves the seven-company pilot", async () => {
      await go("/development/pilot?company=MSTR");
      assert.equal(await page.locator("main").getAttribute("data-pilot-ticker"), "MSTR");
      assert.equal(await page.locator("select option").count(), 7);
      await page.getByRole("link", { name: "Inspect CRCL’s application pipeline" }).click();
      await page.waitForURL(base + route);
      await page.locator("main[data-pipeline-kind]").waitFor();
      assert.equal(await page.locator("main").getAttribute("data-pipeline-kind"), "real-application-pipeline-snapshot");
      await go("/sectors");
      await page.getByRole("link", { name: "Inspect CRCL’s application pipeline" }).click();
      await page.waitForURL(base + route);
      await page.getByRole("heading", { name: /From source to analysis/ }).waitFor();
    });
    await t.test("counts, scope and default blocker accurately describe the saved state", async () => {
      for (const [id, value] of Object.entries({ source_captures: 12, source_fetch_attempts: 12,
        analysis_requests: 3, issuers: 1, securities: 1, security_identifiers: 0,
        watchlist_memberships: 0, normalization_batches: 0 })) {
        assert.equal(await page.locator(`[data-count="${id}"] dd`).innerText(), String(value));
      }
      assert.equal(await page.locator('[data-stage="registration"]').getAttribute("aria-pressed"), "true");
      const scope = await page.getByRole("region", { name: "Application snapshot scope" }).innerText();
      assert.match(scope, /Acquisition readiness is not financial-analysis readiness/);
      assert.match(scope, /separate from the fictional company\/sector/);
      assert.match(await page.locator("#stage-panel").innerText(), /Quote currency needs source evidence/);
      assert.equal(await page.locator("[data-amount-id], [data-metric-id], svg, canvas").count(), 0);
      await page.screenshot({ path: path.join(output, "desktop.png"), fullPage: true });
    });
    await t.test("official-source search explains unresolved meaning, dates and retention", async () => {
      const search = page.getByRole("region", { name: "Official-source search" });
      assert.match(await search.innerText(), /No qualifying quotation-currency evidence acquired/);
      assert.match(await search.innerText(), /not archived application evidence/);
      assert.match(await search.innerText(), /cannot be backdated to the IPO/);
      const notes = search.locator("[data-search-source]");
      assert.equal(await notes.count(), 4);
      for (const note of await notes.all()) {
        await note.locator("summary").focus();
        await page.keyboard.press("Enter");
        assert.equal(await note.getAttribute("open"), "");
        assert.match(await note.innerText(), /Date context/);
        assert.match(await note.innerText(), /Retention \/ source policy/);
        for (const link of await note.getByRole("link").all()) {
          const url = new URL(await link.getAttribute("href"));
          assert.equal(url.protocol, "https:");
          assert.ok(["www.sec.gov", "www.nyse.com", "www.ice.com", "ftp.nyse.com", "investor.circle.com", "www.circle.com"].includes(url.hostname));
          assert.equal(url.search, "");
        }
      }
      assert.match(await search.locator('[data-search-source="nyse-quote"]').innerText(), /no explicit quotation-currency field/);
      assert.match(await search.locator('[data-search-source="circle-ir"]').innerText(), /security check/);
      for (const width of [320, 390, 768, 1440]) {
        await page.setViewportSize({ width, height: 1000 });
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Search overflow at ${width}`);
      }
      await page.screenshot({ path: path.join(output, "source-search.png"), fullPage: true });
    });
    await t.test("saved filing monitor distinguishes new checks from reused source evidence", async () => {
      const monitor = page.getByRole("region", { name: "SEC filing monitor" });
      assert.equal(await monitor.getAttribute("data-monitor-kind"), "real-filing-monitor-snapshot");
      assert.match(await monitor.innerText(), /recurring schedule not configured/);
      assert.match(await monitor.innerText(), /Acceptance cutoff/);
      assert.match(await monitor.innerText(), /Downstream analysis · not dispatched/);
      assert.equal(await monitor.locator("[data-monitor-outcome]").getAttribute("data-monitor-outcome"), "no_change");
      const filings = monitor.getByText("Inspect 6 scoped filings at the cutoff", { exact: true });
      await filings.focus(); await page.keyboard.press("Enter");
      assert.match(await monitor.innerText(), /previously observed filings/);
      const first = monitor.locator("details[open] details").first();
      await first.locator("summary").click();
      assert.match(await first.innerText(), /Source locator/);
      assert.match(await first.innerText(), /SEC acceptance/);
      const evidence = monitor.getByText("Baseline, request and retained response evidence", { exact: true });
      await evidence.click();
      assert.match(await monitor.innerText(), /Reviewed D3c acquisition/);
      assert.match(await monitor.innerText(), /Every complete HTTP 200 body is retained/);
      await monitor.getByText("Current saved totals after this filing check", { exact: true }).click();
      assert.equal(await monitor.locator('[data-monitor-count="sec_filing_monitor"] dd').innerText(), "1");
      assert.equal(await monitor.locator('[data-monitor-count="source_bootstrap"] dd').innerText(), "3");
      for (const width of [320, 390, 768, 1440]) {
        await page.setViewportSize({ width, height: 1000 });
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Monitor overflow at ${width}`);
      }
      await page.evaluate(() => document.activeElement?.blur());
      await monitor.screenshot({ path: path.join(output, "monitor.png") });
    });
    await t.test("every stage can be selected with the keyboard and announces its status", async () => {
      for (const id of ["plan", "captures", "identity", "registration", "normalization", "analysis"]) {
        const button = page.locator(`[data-stage="${id}"]`);
        await button.focus();
        await page.keyboard.press("Enter");
        assert.equal(await button.getAttribute("aria-pressed"), "true");
        assert.equal(await button.evaluate((node) => node === document.activeElement), true);
        assert.ok(await button.evaluate((node) => getComputedStyle(node).outlineStyle !== "none"));
        const name = await button.locator("strong").innerText();
        assert.equal(await page.locator("#stage-title").innerText(), name);
        assert.match(await page.getByRole("status").innerText(), new RegExp(name));
      }
      assert.match(await page.locator("#stage-panel").innerText(), /No financial-analysis result/);
      await select("normalization");
      assert.match(await page.locator("#stage-panel").innerText(), /zero normalization batches/);
    });
    await t.test("capture disclosures retain exact source hashes, UTC dates and safe source links", async () => {
      await select("captures");
      assert.equal(await page.locator("#stage-panel details").count(), 5);
      assert.match(await page.locator("#stage-panel").innerText(), /five captures.*12 application captures at the D3f checkpoint/s);
      for (const details of await page.locator("#stage-panel details").all()) {
        await details.locator("summary").focus();
        await page.keyboard.press("Enter");
        assert.equal(await details.getAttribute("open"), "");
        const href = await details.getByRole("link").getAttribute("href");
        assert.ok(["www.sec.gov", "data.sec.gov"].includes(new URL(href).hostname));
        assert.equal(await details.locator("time").count(), 2);
        assert.match(await details.innerText(), /Body SHA256/);
        await details.locator("summary").press("Enter");
        assert.equal(await details.getAttribute("open"), null);
      }
    });
    await t.test("identity evidence keeps listing date and missing currency distinct", async () => {
      await select("identity");
      assert.equal(await page.locator("[data-identity-field]").count(), 7);
      const currency = page.locator('[data-identity-field="quote_currency"]');
      assert.match(await currency.innerText(), /Unsubstantiated/);
      assert.equal(await currency.locator("details").count(), 0);
      const listing = page.locator('[data-identity-field="valid_from"]');
      assert.match(await listing.innerText(), /2025-06-05/);
      await listing.locator("summary").click();
      assert.match(await listing.locator("blockquote").innerText(), /Since June 5, 2025/);
      assert.match(await listing.innerText(), /2026-09-21T17:07:36/);
      await page.getByText("Why reporting currency does not resolve the gap", { exact: true }).click();
      assert.match(await page.locator("#stage-panel").innerText(), /not substitutes for the missing evidence/);
      for (const width of [320, 390, 768, 1440]) {
        await page.setViewportSize({ width, height: 1000 });
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Evidence overflow at ${width}`);
      }
    });
    await t.test("narrow layout, skip link, audit disclosure and navigation remain usable", async () => {
      await page.setViewportSize({ width: 390, height: 900 });
      await select("registration");
      await page.getByText("Snapshot provenance and audit references", { exact: true }).click();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
      await page.getByText("Snapshot provenance and audit references", { exact: true }).click();
      await page.getByRole("link", { name: "Skip to main content" }).focus();
      await page.keyboard.press("Enter");
      assert.equal(await page.evaluate(() => document.activeElement.id), "main-content");
      await page.screenshot({ path: path.join(output, "narrow.png"), fullPage: true });
      await page.getByRole("link", { name: "Archived company observations" }).click();
      await page.waitForURL(base + "/development/pilot?company=CRCL");
      await page.getByRole("button", { name: "10Y", exact: true }).click();
      assert.equal(await page.getByRole("button", { name: "10Y", exact: true }).getAttribute("aria-pressed"), "true");
      assert.equal(await page.locator("[data-amount-id]").count(), 2);
    });
    await t.test("read-only interactions emit no mutations, provider fetches or browser errors", async () => {
      await go(route);
      assert.deepEqual(errors, []);
      assert.ok(requests.every((request) => request.method === "GET"));
      assert.ok(requests.every((request) => new URL(request.url).origin === new URL(base).origin));
      assert.ok(requests.every((request) => !new URL(request.url).pathname.startsWith("/api/")));
      const serialized = await page.content();
      for (const forbidden of ["blob_key", "postgresql://", "SEC_USER_AGENT", "/Users/leon/"]) {
        assert.ok(!serialized.includes(forbidden), `Private metadata: ${forbidden}`);
      }
      fs.writeFileSync(path.join(output, "network.json"), JSON.stringify({requests, knownWarnings, errors}, null, 2));
    });
  } finally {
    await browser.close();
  }
});
