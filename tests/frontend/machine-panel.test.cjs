/* Browser regression tests against the actual panel, using a fake HA socket.
 * No printer, Home Assistant account, or network commands are involved.
 */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const { chromium } = require("playwright");

(async () => {
  const browser = await chromium.launch({
    headless: true, ...(process.env.BAMBU_BROWSER_CHANNEL ? { channel: process.env.BAMBU_BROWSER_CHANNEL } : {})
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1220, height: 1050 } });
    const errors = [];
    page.on("pageerror", err => errors.push(err.message));
    await page.setContent('<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;--primary-text-color:#203248;--secondary-text-color:#637389;--primary-background-color:#f5f7fb;--card-background-color:#fff;--divider-color:#dce3eb;--secondary-background-color:#edf1f6;--primary-color:#137d70;--text-primary-color:#fff}</style></head><body></body></html>');
    await page.addScriptTag({ content: fs.readFileSync(path.join(__dirname, "../../custom_components/bambu_open_network/frontend/machine-panel.js"), "utf8") });
    await page.evaluate(() => {
      window.commands = [];
      window.devices = [
        { serial: "ONE", name: "Werkstatt P1S", connected: true, ready: true, fresh: true, state: "IDLE", transport: "cloud",
          nozzle: 210, nozzle_target: 215, bed: 58, bed_target: 60, camera: "camera.one_cloud" },
        { serial: "TWO", name: '<img src=x onerror="window.pwned=true">', connected: true, ready: true, fresh: true, state: "IDLE", transport: "cloud",
          nozzle: 25, nozzle_target: 0, bed: 25, bed_target: 0 }
      ];
      const panel = document.createElement("bambu-machine-panel");
      panel.hass = { locale: { language: "de" }, callWS: async message => {
        if (message.type.endsWith("/machines")) return { printers: structuredClone(window.devices) };
        window.commands.push(message);
        if (window.failNext) { window.failNext = false; throw new Error("Delivery is unknown; no retry"); }
        return { sequence_id: String(window.commands.length), status: "accepted" };
      }};
      document.body.append(panel);
      window.panel = panel;
    });
    const q = selector => page.locator("bambu-machine-panel").locator(selector);
    await q("#printer option").first().waitFor({ state: "attached" });
    assert.equal(await q("#connection").textContent(), "Cloud · IDLE");
    assert.equal(await q("#printer option").nth(1).textContent(), '<img src=x onerror="window.pwned=true">');
    assert.equal(await page.evaluate(() => window.pwned), undefined);

    await q("#step").selectOption("0.1");
    await q('[data-axis="X"][data-sign="-1"]').click();
    await page.waitForFunction(() => window.commands.length === 1 && !window.panel.busy);
    let commands = await page.evaluate(() => window.commands);
    assert.deepEqual(commands[0].params, { axis: "X", distance: -0.1, speed: 3000 });
    assert.equal(commands[0].serial, "ONE");

    await q("#printer").selectOption("TWO");
    assert.equal(await q("#extrude").isDisabled(), true);
    await q("#printer").selectOption("ONE");
    await page.evaluate(() => { window.devices[0].state = "PAUSE"; return window.panel.refresh(); });
    assert.equal(await q("#home").isDisabled(), true);
    assert.equal(await q('[data-axis="Y"][data-sign="1"]').isDisabled(), true);
    assert.equal(await q("#resume").isDisabled(), false);

    const code = 'M105\nM114\n; <img src=x onerror="window.pwned=true">';
    await q("#gcode").fill(code);
    assert.equal(await q("#send").isDisabled(), true);
    await q("#allow").check();
    await q("#send").click();
    await page.waitForFunction(() => window.commands.length === 2 && !window.panel.busy);
    commands = await page.evaluate(() => window.commands);
    assert.equal(commands[1].params.gcode, code);
    assert.equal(commands[1].params.allow_during_print, true);
    assert.equal(await q("#log img").count(), 0);
    assert.equal(await page.evaluate(() => window.pwned), undefined);
    assert.match(await q("#notice").textContent(), /nicht bestätigt/);

    await page.evaluate(() => { window.failNext = true; });
    await q("#send").click();
    await page.waitForFunction(() => window.commands.length === 3 && !window.panel.busy);
    assert.match(await q("#notice").textContent(), /unknown/);
    await page.waitForTimeout(2100);
    assert.equal(await page.evaluate(() => window.commands.length), 3);

    await page.evaluate(() => { window.devices[0].fresh = false; return window.panel.refresh(); });
    assert.equal(await q("#send").isDisabled(), true);
    assert.equal(await q(".heater").first().isDisabled(), true);
    assert.equal(await q("#nozzleReading").textContent(), "—");

    await page.evaluate(() => {
      window.devices[0].fresh = true;
      window.devices[0].state = "IDLE";
      window.devices[1].name = "Büro A1";
      window.panel.addEventListener("hass-more-info", ev => { window.cameraEntity = ev.detail.entityId; });
      return window.panel.refresh();
    });
    await q("#camera").click();
    assert.equal(await page.evaluate(() => window.cameraEntity), "camera.one_cloud");
    await q("#allow").uncheck();
    await q("#gcode").fill("M104 S200\nM140 S60");
    const out = path.join(__dirname, "../../.test-tmp");
    fs.mkdirSync(out, { recursive: true });
    await page.evaluate(() => { window.panel.scrollTop = 0; });
    await page.screenshot({ path: path.join(out, "machine-desktop.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.evaluate(() => { window.panel.scrollTop = 0; });
    await page.screenshot({ path: path.join(out, "machine-mobile.png"), fullPage: true });

    await page.evaluate(() => window.panel.remove());
    await page.waitForTimeout(2100);
    assert.equal(await page.evaluate(() => window.commands.length), 3);
    assert.deepEqual(errors, []);
    console.log("Panel browser checks passed: printer isolation, XSS, motion locks, multiline G-code, no retry, stale status, camera and responsive layout.");
  } finally {
    await browser.close();
  }
})().catch(err => { console.error(err); process.exitCode = 1; });
