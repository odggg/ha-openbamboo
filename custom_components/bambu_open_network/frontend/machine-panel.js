/* Local HA web component. No CDN, token storage, or commands on reconnect. */
class BambuMachinePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this.items = [];
    this.serial = "";
    this.busy = false;
    this.polling = false;
    this.generation = 0;
  }

  set hass(value) {
    this._hass = value;
    if (!this.built && this.isConnected) this.build();
  }
  get hass() { return this._hass; }
  text(de, en) {
    return (this.hass?.locale?.language || this.hass?.language || "en").startsWith("de") ? de : en;
  }
  $(selector) { return this.shadowRoot.querySelector(selector); }
  connectedCallback() {
    if (this.hass && !this.built) this.build();
    this.timer = setInterval(() => this.refresh(), 2000);
    this.refresh();
  }
  disconnectedCallback() {
    clearInterval(this.timer);
    this.generation++;
    this.items = [];
    if (this.built) this.updateStatus();
  }

  build() {
    this.built = true;
    // Only this constant template uses innerHTML. Printer names, errors and
    // submitted G-code always use textContent / DOM nodes.
    this.shadowRoot.innerHTML = '<style>' +
      ':host{display:block;height:100%;overflow:auto;color:var(--primary-text-color);background:var(--primary-background-color);font-family:var(--paper-font-body1_-_font-family,system-ui)}' +
      '*{box-sizing:border-box}header{display:flex;align-items:center;gap:14px;padding:16px 24px;border-bottom:1px solid var(--divider-color);background:var(--card-background-color)}' +
      'h1{font-size:21px;margin:0;font-weight:600}header small{display:block;color:var(--secondary-text-color);font-size:12px;margin-top:3px}.menu{font-size:22px;border:0;padding:7px}' +
      'main{max-width:1160px;margin:auto;padding:24px}.top{display:flex;gap:16px;align-items:end;flex-wrap:wrap;margin-bottom:20px}.printer{min-width:220px;flex:1}.badge{padding:8px 12px;border-radius:20px;background:var(--secondary-background-color);font-size:13px}.ok{color:var(--success-color,#208548)}' +
      '.grid{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:14px;padding:22px;min-width:0}' +
      'h2{font-size:17px;margin:0 0 18px}p{line-height:1.5}.hint{font-size:12px;color:var(--secondary-text-color);margin:12px 0 0}.wide{grid-column:1/-1}' +
      'label{display:block;font-size:13px;color:var(--secondary-text-color);margin-bottom:6px}select,input,textarea,button{font:inherit;color:inherit;border:1px solid var(--divider-color);border-radius:8px;background:var(--card-background-color);padding:10px}' +
      'input,select{width:100%;min-width:0}input[type=checkbox]{width:auto;margin-right:8px}button{cursor:pointer;min-height:40px}button:hover:enabled{background:var(--secondary-background-color)}button:disabled{opacity:.4;cursor:default}' +
      '.primary{background:var(--primary-color)!important;color:var(--text-primary-color,#fff);border-color:transparent}.danger{color:var(--error-color,#db4437)}' +
      '.jog{display:grid;grid-template-columns:repeat(3,1fr) 22px 1fr;gap:8px;margin:18px 0}.jog button{font-weight:600;font-size:17px}.yplus{grid-column:2}.zplus{grid-column:5}.xminus{grid-column:1}.home{grid-column:2}.xplus{grid-column:3}.zminus{grid-column:5}.yminus{grid-column:2}' +
      '.row{display:flex;gap:10px;align-items:end;flex-wrap:wrap}.row>div{flex:1;min-width:80px}.row button{white-space:nowrap}.reading{font-size:26px;font-weight:500;margin:4px 0 14px;font-variant-numeric:tabular-nums}.reading small{font-size:14px;color:var(--secondary-text-color)}' +
      '.heaters{display:grid;grid-template-columns:1fr 1fr;gap:18px}.divider{border-top:1px solid var(--divider-color);margin:22px 0}.fan{margin-top:18px}' +
      'textarea{width:100%;min-height:150px;resize:vertical;font-family:ui-monospace,monospace;line-height:1.6}.console-row{display:flex;gap:18px;align-items:center;justify-content:space-between;margin-top:12px}.console-row label{margin:0}' +
      '#notice{margin:0 0 18px;font-size:14px}#notice.error{color:var(--error-color,#db4437)}#log{padding:0;margin:18px 0 0;list-style:none;max-height:280px;overflow:auto;background:var(--secondary-background-color);border-radius:8px}' +
      '#log li{padding:12px 14px;border-bottom:1px solid var(--divider-color);font-size:12px;white-space:pre-wrap;overflow-wrap:anywhere;font-family:ui-monospace,monospace}.tools{display:flex;gap:8px;flex-wrap:wrap}' +
      '@media(max-width:780px){main{padding:14px}.grid{grid-template-columns:1fr}.wide{grid-column:auto}.card{padding:18px}header{padding:12px 16px}.console-row{align-items:start;flex-direction:column}}' +
      '</style><header><button class="menu" aria-label="Menu">☰</button><div><h1>Bambu Control</h1><small>Open Bamboo Network · Home Assistant</small></div></header>' +
      '<main><div class="top"><div class="printer"><label for="printer" data-label="printer"></label><select id="printer"></select></div><span class="badge" id="connection"></span><button id="camera" data-label="camera"></button></div>' +
      '<p id="notice" role="status" aria-live="polite"></p><div class="grid">' +
      '<section class="card"><h2 data-label="motion"></h2><div class="row"><div><label for="step" data-label="step"></label><select id="step"><option>0.1</option><option>1</option><option selected>10</option></select></div><div><label for="feed" data-label="feed"></label><input id="feed" type="number" min="60" max="6000" value="3000"></div></div>' +
      '<div class="jog"><button class="yplus motion" data-axis="Y" data-sign="1">Y +</button><button class="zplus motion" data-axis="Z" data-sign="1">Z +</button><button class="xminus motion" data-axis="X" data-sign="-1">X −</button><button class="home motion" id="home">⌂ Home</button><button class="xplus motion" data-axis="X" data-sign="1">X +</button><button class="zminus motion" data-axis="Z" data-sign="-1">Z −</button><button class="yminus motion" data-axis="Y" data-sign="-1">Y −</button></div>' +
      '<p class="hint" data-label="motionHint"></p><div class="divider"></div><h2 data-label="extruder"></h2><div class="row"><div><label for="extrusion">mm</label><input id="extrusion" type="number" value="5" min="0.1" max="20" step="0.1"></div><button id="retract" class="extrude" data-label="retract"></button><button id="extrude" class="extrude" data-label="extrude"></button></div><p class="hint" data-label="extrudeHint"></p></section>' +
      '<section class="card"><h2 data-label="temperatures"></h2><div class="heaters"><div><label data-label="nozzle"></label><div id="nozzleReading" class="reading">—</div><label for="nozzleTarget">°C</label><input id="nozzleTarget" type="number" min="0" max="300" value="200"><div class="tools" style="margin-top:10px"><button class="control heater" data-heater="nozzle" data-label="set"></button><button class="control off" data-heater="nozzle" data-label="off"></button></div></div><div><label data-label="bed"></label><div id="bedReading" class="reading">—</div><label for="bedTarget">°C</label><input id="bedTarget" type="number" min="0" max="120" value="60"><div class="tools" style="margin-top:10px"><button class="control heater" data-heater="bed" data-label="set"></button><button class="control off" data-heater="bed" data-label="off"></button></div></div></div>' +
      '<div class="fan row"><div><label for="fan" data-label="fan"></label><input id="fan" type="number" min="0" max="100" step="10" value="100"></div><button id="setFan" class="control" data-label="set"></button></div><p class="hint" data-label="heaterHint"></p>' +
      '<div class="divider"></div><div class="tools"><button id="pause" data-label="pause"></button><button id="resume" data-label="resume"></button><button id="stop" class="danger" data-label="stop"></button></div><p class="hint" data-label="stopHint"></p></section>' +
      '<section class="card wide"><h2 data-label="console"></h2><label for="gcode" data-label="gcodeLabel"></label><textarea id="gcode" spellcheck="false" placeholder="M105&#10;M114"></textarea><div class="console-row"><label><input id="allow" type="checkbox"><span data-label="allow"></span></label><button id="send" class="primary" data-label="send"></button></div><p class="hint" data-label="consoleHint"></p><ul id="log" aria-live="polite"></ul></section></div></main>';
    const labels = {
      printer: ["Drucker", "Printer"], camera: ["Kamera öffnen", "Open camera"],
      motion: ["Achsen bewegen", "Move axes"], step: ["Schrittweite (mm)", "Step size (mm)"],
      feed: ["X/Y Vorschub (mm/min)", "X/Y feed rate (mm/min)"],
      motionHint: ["Nur im Leerlauf. Z ist auf 600 mm/min begrenzt. Vor dem Verfahren gegebenenfalls homen; Druckraum freihalten. Achsvorzeichen beziehen sich auf G-Code-Koordinaten.", "Idle only. Z feed is capped at 600 mm/min. Home first if needed and keep the build volume clear. Signs refer to G-code axes."],
      extruder: ["Aktiver Extruder", "Active extruder"], retract: ["Zurückziehen", "Retract"], extrude: ["Extrudieren", "Extrude"],
      extrudeHint: ["Nur im Leerlauf, ab 170 °C. Betrifft die aktive Düse.", "Idle only, at least 170 °C. Operates on the active nozzle."],
      temperatures: ["Temperaturen & Lüfter", "Temperatures & fan"], nozzle: ["Aktive Düse", "Active nozzle"], bed: ["Druckbett", "Bed"],
      set: ["Setzen", "Set"], off: ["Aus", "Off"], fan: ["Bauteillüfter (%)", "Part cooling fan (%)"],
      heaterHint: ["Firmware- und Modellgrenzen gelten weiterhin. Angezeigt werden gemeldete Ist- / Zielwerte.", "Firmware and model limits still apply. Readings show reported current / target values."],
      pause: ["Pause", "Pause"], resume: ["Fortsetzen", "Resume"], stop: ["Druck abbrechen", "Cancel print"],
      stopHint: ["Druckabbruch ist kein Not-Aus.", "Cancel print is not an emergency stop."],
      console: ["G-Code-Konsole", "G-code console"], gcodeLabel: ["Ein oder mehrere Befehle, je eine Zeile", "One or more commands, one per line"],
      allow: ["G-Code auch während eines Drucks erlauben", "Allow G-code during a print"],
      send: ["G-Code senden", "Send G-code"],
      consoleHint: ["Eigene Befehle können Bewegungen und Heizung auslösen und umgehen die Grenzen der Achstasten. Maximal 16 KiB. „Übermittelt“ bestätigt die Annahme durch Open Bamboo, nicht die Ausführung am Drucker. Kein serielles ok-Protokoll; M105/M114 liefern hier keine Terminal-Antwort. Verlauf nur in dieser Sitzung.", "Custom commands can move or heat the printer and bypass jog-button limits. Maximum 16 KiB. Accepted means Open Bamboo accepted delivery, not firmware execution. No serial ok protocol; M105/M114 do not produce terminal responses here. Session-only history."]
    };
    this.shadowRoot.querySelectorAll("[data-label]").forEach(el => {
      el.textContent = this.text(...labels[el.dataset.label]);
    });
    this.$(".menu").onclick = () => this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
    this.$("#printer").onchange = () => {
      this.serial = this.$("#printer").value;
      this.$("#allow").checked = false;
      this.updateStatus();
    };
    this.shadowRoot.querySelectorAll("[data-axis]").forEach(button => {
      button.onclick = () => this.send("jog", {
        axis: button.dataset.axis, distance: Number(this.$("#step").value) * Number(button.dataset.sign),
        speed: button.dataset.axis === "Z" ? 600 : Number(this.$("#feed").value)
      });
    });
    this.$("#home").onclick = () => {
      if (confirm(this.text("Alle Achsen homen? Druckraum muss frei sein.", "Home all axes? Keep the build volume clear."))) this.send("home");
    };
    this.$("#extrude").onclick = () => this.send("extrude", { distance: Number(this.$("#extrusion").value) });
    this.$("#retract").onclick = () => this.send("extrude", { distance: -Number(this.$("#extrusion").value) });
    this.shadowRoot.querySelectorAll(".heater,.off").forEach(button => {
      button.onclick = () => this.send("temperature", { heater: button.dataset.heater,
        value: button.classList.contains("off") ? 0 : Number(this.$("#" + button.dataset.heater + "Target").value) });
    });
    this.$("#setFan").onclick = () => this.send("fan", { value: Number(this.$("#fan").value) });
    this.$("#pause").onclick = () => this.send("pause");
    this.$("#resume").onclick = () => this.send("resume");
    this.$("#stop").onclick = () => {
      if (confirm(this.text("Aktiven Druck wirklich abbrechen?", "Cancel the active print?"))) this.send("stop");
    };
    this.$("#allow").onchange = () => this.updateStatus();
    this.$("#gcode").oninput = () => this.updateStatus();
    this.$("#send").onclick = () => this.send("gcode", { gcode: this.$("#gcode").value,
      allow_during_print: this.$("#allow").checked });
    this.$("#camera").onclick = () => {
      const camera = this.items.find(item => item.serial === this.serial)?.camera;
      if (camera) this.dispatchEvent(new CustomEvent("hass-more-info", { detail: { entityId: camera }, bubbles: true, composed: true }));
    };
    this.updateStatus();
    this.refresh();
  }

  async refresh() {
    if (!this.built || !this.isConnected || !this.hass || this.polling) return;
    this.polling = true;
    const generation = this.generation;
    try {
      const response = await this.hass.callWS({ type: "bambu_open_network/machines" });
      if (!this.isConnected || generation !== this.generation) return;
      this.items = response.printers;
      const select = this.$("#printer");
      const signature = JSON.stringify(this.items.map(item => [item.serial, item.name]));
      if (signature !== this.optionsSignature) {
        this.optionsSignature = signature;
        select.replaceChildren(...this.items.map(item => {
          const option = document.createElement("option");
          option.value = item.serial;
          option.textContent = item.name;
          return option;
        }));
      }
      if (!this.items.some(item => item.serial === this.serial)) {
        this.serial = this.items[0]?.serial || "";
        this.$("#allow").checked = false;
      }
      select.value = this.serial;
      this.updateStatus();
    } catch (error) {
      if (!this.isConnected || generation !== this.generation) return;
      this.items = [];
      this.updateStatus();
      this.notice(this.text("Statusabruf fehlgeschlagen: ", "Unable to fetch status: ") + (error.message || String(error)), true);
    } finally {
      this.polling = false;
    }
  }

  updateStatus() {
    if (!this.built) return;
    const item = this.items.find(item => item.serial === this.serial);
    const ready = Boolean(item?.ready && item?.fresh && !this.busy);
    const idle = ["IDLE", "FINISH", "FAILED"].includes(item?.state);
    this.shadowRoot.querySelectorAll(".control").forEach(button => { button.disabled = !ready; });
    this.shadowRoot.querySelectorAll(".motion").forEach(button => { button.disabled = !ready || !idle; });
    this.shadowRoot.querySelectorAll(".extrude").forEach(button => { button.disabled = !ready || !idle || !(item?.nozzle >= 170); });
    this.$("#send").disabled = !ready || (!idle && !this.$("#allow").checked) || !this.$("#gcode").value.trim();
    this.$("#pause").disabled = !ready || item?.state !== "RUNNING";
    this.$("#resume").disabled = !ready || item?.state !== "PAUSE";
    this.$("#stop").disabled = !ready || !["RUNNING", "PAUSE", "PREPARE", "SLICING"].includes(item?.state);
    this.$("#printer").disabled = this.busy || !this.items.length;
    this.$("#camera").disabled = !item?.camera;
    const badge = this.$("#connection");
    badge.classList.toggle("ok", Boolean(item?.ready && item?.fresh));
    badge.textContent = !item?.connected ? this.text("Nicht verbunden", "Disconnected")
      : !item.ready ? this.text("Signierung nicht bereit", "Signing not ready")
      : !item.fresh ? this.text("Warte auf Druckerstatus", "Waiting for printer status")
      : (item.transport === "cloud" ? "Cloud" : "LAN") + " · " + item.state;
    ["nozzle", "bed"].forEach(heater => {
      const value = item?.[heater];
      const target = item?.[heater + "_target"];
      this.$("#" + heater + "Reading").textContent = item?.fresh && typeof value === "number"
        ? value.toFixed(0) + " / " + (typeof target === "number" ? target.toFixed(0) : "—") + " °C" : "—";
    });
  }

  notice(message, error = false) {
    this.$("#notice").textContent = message;
    this.$("#notice").classList.toggle("error", error);
  }
  log(message) {
    const row = document.createElement("li");
    row.textContent = new Date().toLocaleTimeString() + " · " + message;
    const log = this.$("#log");
    log.prepend(row);
    while (log.children.length > 100) log.lastChild.remove();
  }

  async send(action, params = {}) {
    if (this.busy || !this.serial) return;
    const serial = this.serial;
    const name = this.items.find(item => item.serial === serial)?.name || serial;
    const generation = this.generation;
    this.busy = true;
    this.updateStatus();
    this.notice(this.text("Übertrage Befehl …", "Transmitting command …"));
    this.log(name + " · " + action + (params.gcode ? "\n" + params.gcode : " " + JSON.stringify(params)));
    try {
      const result = await this.hass.callWS({ type: "bambu_open_network/machine_command", serial, action, params });
      if (!this.isConnected || generation !== this.generation) return;
      const message = this.text("Übermittelt an Open Bamboo. Ausführung am Drucker nicht bestätigt.", "Accepted by Open Bamboo. Firmware execution not confirmed.");
      this.notice(message);
      this.log(name + " · #" + result.sequence_id + " · " + message);
    } catch (error) {
      if (!this.isConnected || generation !== this.generation) return;
      const message = error.message || String(error);
      this.notice(message, true);
      this.log(name + " · " + message);
    } finally {
      this.busy = false;
      this.updateStatus();
      this.refresh();
    }
  }
}
if (!customElements.get("bambu-machine-panel")) customElements.define("bambu-machine-panel", BambuMachinePanel);
