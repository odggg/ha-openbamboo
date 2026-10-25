/* Actual multipart MJPEG in Chromium, with fake HA state and scoped test tokens. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const http = require("node:http");
const path = require("node:path");
const { chromium } = require("playwright");

(async () => {
  const active = new Map();
  const requests = [];
  const frames = {};
  let failNext = false;
  let requestId = 0;
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, "http://localhost");
    if (!url.pathname.startsWith("/api/camera_proxy_stream/")) {
      res.writeHead(200, { "Content-Type": "text/html" });
      res.end('<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;--primary-text-color:#203248;--secondary-text-color:#637389;--primary-background-color:#f5f7fb;--card-background-color:#fff;--divider-color:#dce3eb;--secondary-background-color:#edf1f6;--primary-color:#137d70;--text-primary-color:#fff}</style></head><body></body></html>');
      return;
    }
    const entity = decodeURIComponent(url.pathname.split("/").pop());
    requests.push({ entity, token: url.searchParams.get("token") });
    if (failNext) {
      failNext = false;
      res.writeHead(503);
      res.end();
      return;
    }
    if (!frames[entity] || !url.searchParams.get("token")?.startsWith("fixture-")) {
      res.writeHead(401);
      res.end();
      return;
    }
    const id = ++requestId;
    active.set(id, entity);
    res.writeHead(200, {
      "Content-Type": "multipart/x-mixed-replace; boundary=frame",
      "Cache-Control": "no-store",
    });
    const write = () => {
      const data = frames[entity];
      res.write("--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + data.length + "\r\n\r\n");
      res.write(data);
      res.write("\r\n");
    };
    write();
    const timer = setInterval(write, 150);
    res.on("close", () => { clearInterval(timer); active.delete(id); });
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  const base = "http://127.0.0.1:" + server.address().port;
  const browser = await chromium.launch({
    headless: true, ...(process.env.BAMBU_BROWSER_CHANNEL ? { channel: process.env.BAMBU_BROWSER_CHANNEL } : {})
  });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.goto(base);
    for (const [entity, width, color] of [["camera.one_cloud", 64, "#8b4560"], ["camera.two_cloud", 80, "#247e95"]]) {
      frames[entity] = Buffer.from(await page.evaluate(({ width, color }) => {
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = 48;
        const ctx = canvas.getContext("2d");
        ctx.fillStyle = color;
        ctx.fillRect(0, 0, width, 48);
        return canvas.toDataURL("image/jpeg").split(",")[1];
      }, { width, color }), "base64");
    }
    await page.addScriptTag({ content: fs.readFileSync(path.join(__dirname, "../../custom_components/bambu_open_network/frontend/machine-panel.js"), "utf8") });
    await page.evaluate(() => {
      window.commands = [];
      window.devices = [
        { serial: "ONE", name: "Werkstatt P1S", connected: true, ready: true, fresh: true, state: "IDLE", transport: "cloud", camera: "camera.one_cloud",
          camera_status: "streaming", camera_frame_age: 0.1, nozzle: 210, nozzle_target: 215, bed: 58, bed_target: 60 },
        { serial: "TWO", name: "Büro A1", connected: true, ready: true, fresh: true, state: "IDLE", transport: "cloud", camera: "camera.two_cloud",
          camera_status: "streaming", camera_frame_age: 0.2, nozzle: 25, nozzle_target: 0, bed: 25, bed_target: 0 }
      ];
      const panel = document.createElement("bambu-machine-panel");
      window.testHass = {
        locale: { language: "de" }, hassUrl: path => location.origin + path,
        states: {
          "camera.one_cloud": { state: "idle", attributes: { access_token: "fixture-one" } },
          "camera.two_cloud": { state: "idle", attributes: { access_token: "fixture-two" } }
        },
        callWS: async msg => {
          if (msg.type.endsWith("/machines")) return { printers: structuredClone(window.devices) };
          window.commands.push(msg);
          return { sequence_id: "1", status: "accepted" };
        }
      };
      panel.hass = window.testHass;
      document.body.append(panel);
      window.panel = panel;
    });
    const q = selector => page.locator("bambu-machine-panel").locator(selector);
    const loaded = width => page.waitForFunction(width =>
      window.panel.shadowRoot.querySelector("#cameraStage img")?.naturalWidth === width, width);
    await loaded(64);
    assert.match(await q("#cameraTitle").textContent(), /Werkstatt P1S/);
    const initialRequests = requests.length;
    await page.evaluate(async () => { await window.panel.refresh(); window.panel.hass = window.testHass; });
    await page.waitForTimeout(300);
    assert.equal(requests.length, initialRequests, "Status updates must keep the existing stream");
    await q('[data-axis="X"][data-sign="1"]').click();
    assert.equal(await page.evaluate(() => window.commands.length), 1);
    assert.equal(await q("#cameraStage img").count(), 1);

    await page.evaluate(() => { window.oldImage = window.panel.cameraImage; });
    await q("#printer").selectOption("TWO");
    assert.equal(await page.evaluate(() => !window.oldImage.isConnected && !window.oldImage.hasAttribute("src")), true);
    await loaded(80);
    assert.match(await q("#cameraTitle").textContent(), /Büro A1/);
    await page.waitForTimeout(250);
    assert.deepEqual([...active.values()], ["camera.two_cloud"]);

    // A rotated HA camera token must replace the request without showing another printer.
    await page.evaluate(() => {
      window.testHass.states["camera.two_cloud"].attributes.access_token = "fixture-two-rotated";
      window.panel.hass = window.testHass;
    });
    await loaded(80);
    assert.equal(requests.at(-1).token, "fixture-two-rotated");

    // Backend decoder timestamps, rather than image changes, detect a stale scene.
    await page.evaluate(() => { window.devices[1].camera_frame_age = 20; return window.panel.refresh(); });
    assert.equal(await q("#cameraStage img").count(), 0);
    assert.match(await q("#cameraStatus").textContent(), /veraltet/);
    await page.evaluate(() => { window.devices[1].camera_frame_age = 0.1; return window.panel.refresh(); });
    await q("#cameraRetry").click();
    await loaded(80);

    // An HTTP error clears the image and reconnects with backoff.
    failNext = true;
    await page.evaluate(() => { window.panel.cameraRetryDelay = 50; window.panel.stopCamera(); window.panel.updateCamera(); });
    await page.waitForFunction(() => window.panel.cameraRetryTimer != null && !window.panel.cameraImage);
    assert.match(await q("#cameraStatus").textContent(), /erneut/);
    await loaded(80);

    // Hidden pages release their camera connection and resume the selected printer.
    await page.evaluate(() => {
      Object.defineProperty(document, "hidden", { configurable: true, value: true });
      document.dispatchEvent(new Event("visibilitychange"));
    });
    assert.equal(await q("#cameraStage img").count(), 0);
    await page.waitForTimeout(250);
    assert.equal(active.size, 0);
    await page.evaluate(() => {
      delete document.hidden;
      document.dispatchEvent(new Event("visibilitychange"));
    });
    await loaded(80);

    await page.evaluate(() => {
      window.devices[1].connected = false;
      return window.panel.refresh();
    });
    assert.equal(await q("#cameraStage img").count(), 0);
    assert.match(await q("#cameraStatus").textContent(), /nicht verbunden/);
    await page.evaluate(() => {
      window.devices[1].connected = true;
      return window.panel.refresh();
    });
    await loaded(80);

    await page.evaluate(() => { window.testHass.states["camera.two_cloud"].state = "unavailable"; window.panel.hass = window.testHass; });
    assert.equal(await q("#cameraStage img").count(), 0);
    await page.evaluate(() => { window.testHass.states["camera.two_cloud"].state = "idle"; window.panel.hass = window.testHass; });
    await loaded(80);
    await page.evaluate(() => { window.devices[1].camera = null; return window.panel.refresh(); });
    assert.equal(await q("#cameraStage img").count(), 0);
    assert.match(await q("#cameraStatus").textContent(), /keine Cloud-Kamera/);

    await q("#printer").selectOption("ONE");
    await loaded(64);
    const out = path.join(__dirname, "../../.test-tmp");
    fs.mkdirSync(out, { recursive: true });
    await page.evaluate(() => { window.panel.scrollTop = 0; });
    await page.screenshot({ path: path.join(out, "inline-camera-desktop.png"), fullPage: true });
    await page.setViewportSize({ width: 390, height: 844 });
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    await page.screenshot({ path: path.join(out, "inline-camera-mobile.png"), fullPage: true });
    await page.evaluate(() => window.panel.remove());
    await page.waitForTimeout(250);
    assert.equal(active.size, 0);
    const disconnectedRequests = requests.length;
    await page.waitForTimeout(300);
    assert.equal(requests.length, disconnectedRequests);
    assert.deepEqual(errors, []);
    console.log("Inline camera browser checks passed: real MJPEG, simultaneous controls, printer switch, token rotation, stable stream, stale/error recovery, visibility, unavailable state, cleanup and responsive layout.");
  } finally {
    await browser.close();
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
