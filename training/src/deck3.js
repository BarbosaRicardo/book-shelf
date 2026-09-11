/* ---- arc ---- */
wireFlow("arc", {
  d1: '<h4>Day 1 — Comms and the RTAC</h4><p>DNP3, Modbus and C37.118 configured to carry correct values at a usable rate.</p>' +
      '<ul><li>What today spends: the protocol choice. C37.118 at ~16 ms instead of DNP3 at ~500 ms is what makes a 100 ms execution period possible at all.</li>' +
      '<li>Also inherited: DDR needs both its library and its extension installed.</li></ul>',
  d2: '<h4>Day 2 — Project and inverters</h4><p>Cloning the closest project and converting it to a different inverter model.</p>' +
      '<ul><li>What today spends: the global structures and custom data types the control blocks read and write, and the project-level LGI and tuning parameters.</li>' +
      '<li>Today also qualifies it — mixed vendors need parameters at the variable level, not in one shared type.</li></ul>',
  d3: '<h4>Day 3 — Control and recording <span class="unconfirmed" style="border-style:solid">you are here</span></h4><p>The chain from setpoint source to individual inverter, the timing budget behind it, PID and clamping behaviour, and DDR for proving the response.</p>' +
      '<ul><li>Ends pointing at a working session on the Grid Connect extension — the answer to most of Day 2\'s manual conversion work.</li></ul>'
}, "d3");

/* ---- the chain ---- */
wireFlow("chain", {
  src: '<h4>01 · Source select</h4><p>Active sources may include SCADA, QSC or another project input. <b>Only the active source supplies the standard setpoint.</b></p><ul><li>The others are ignored until they become active — at which point stage 02 handles the handover.</li></ul>',
  bt: '<h4>02 · Bumpless transfer</h4><p>External or internal setpoints pass through bumpless transfer, so <b>a change of source produces a smooth transition rather than a step response</b>.</p><ul><li>Setpoint feedback is reused here for P, Q and V whenever the active source changes.</li></ul>',
  pfr: '<h4>03 · Arithmetic and PFR compensation</h4><p>PFR calculates a real-power compensation from the POI frequency deviation and applies the resulting delta to the MPC P setpoint.</p><ul><li>Reactive control applies voltage compensation and power-factor limits — 0.95 to 1.05 in the example given.</li></ul>',
  int: '<h4>04 · Intermediate setpoint</h4><p>The standard setpoint plus arithmetic and PFR compensation. Not yet limited.</p><ul><li>This is the last point at which the number reflects what was asked for rather than what the plant is allowed to do.</li></ul>',
  lgi: '<h4>05 · LGI limits</h4><p>Final P setpoints are constrained by the LGI limits. <b>A 50 MW limit prevents an output above 50 MW</b>, whatever the source requested.</p><ul><li>LGI and tuning settings are project-specific: plant rating, Q rating, evolution period, Q high/low limits, jetband, P-limit delay.</li></ul>',
  fin: '<h4>06 · Final plant setpoint</h4><p>The target that ramp logic, PID control and the individual inverters all chase.</p><ul><li>Everything downstream is about <em>how</em> the plant gets here, not <em>where</em> here is.</li></ul>',
  ramp: '<h4>07 · Ramp</h4><p>Rate-limits the move to the final setpoint.</p><ul><li>The ramp time sets the whole timing budget: POI meter at least 10× faster, PID at least 3–4× faster (5× preferred).</li><li>Voltage control ramps toward a voltage setpoint too — but bypasses the ramp during a Volt-VAR event.</li></ul>',
  pid: '<h4>08 · PID</h4><p>Closes the loop against POI feedback.</p><ul><li>Grid Connect\'s PI accumulates the previous P-term with the new error × KP term, so it can reach 100% even with KI at zero. <code>SCLutils.PID</code> cannot.</li><li>PI reset clears accumulated parameters after a source change or a DFR/PFR event.</li></ul>',
  disp: '<h4>09 · Inverter dispatch</h4><p>The MPC block assigns setpoints directly to each inverter.</p><ul><li><b>That assignment is not visible in the main program</b> — expose it through DDR or a dedicated global variable.</li><li>Inverters excluded by remote enable, feeder-level control or individual include control drop out of the calculation here.</li></ul>'
}, "src");

/* ---- P/Q error compensation ---- */
(function(){
  var t = document.querySelector('[data-tool="pqe"]'); if (!t) return;
  var cmd = document.getElementById("pq-cmd"), meas = document.getElementById("pq-meas");
  function paint(){
    var c = +cmd.value, m = +meas.value, gap = c - m, pct = m > 0 ? (gap / m * 100) : 0;
    document.getElementById("pq-cmd-o").textContent = c.toFixed(2) + " MW";
    document.getElementById("pq-meas-o").textContent = m.toFixed(2) + " MW";
    t.querySelector("[data-gap]").innerHTML = gap.toFixed(2) + ' <small>MW</small>';
    t.querySelector("[data-pct]").innerHTML = (pct >= 0 ? "+" : "") + pct.toFixed(1) + ' <small>%</small>';
    t.querySelector("[data-pqmsg]").innerHTML = Math.abs(gap) < 0.01
      ? "Command and measurement agree — no compensation needed."
      : "Commanding <b>" + c.toFixed(2) + " MW</b> and measuring <b>" + m.toFixed(2) + " MW</b> is a <b>systematic</b> difference, not noise. It is corrected as a percentage on the command, so the PID is not left chasing a bias it cannot remove.";
  }
  cmd.oninput = meas.oninput = paint; paint();
})();

/* ---- timing budget ---- */
(function(){
  var t = document.querySelector('[data-tool="tb"]'); if (!t) return;
  var r = document.getElementById("tb-ramp");
  var PROTO = [
    { n: "C37.118 from an SEL-735", ms: 16.7, note: "60 samples/s — needs an RTAC cycle of ~15–16 ms" },
    { n: "DNP3 or SEL protocol from an SEL-735", ms: 500, note: "the meter itself will not serve faster" },
    { n: "Inverter Modbus write cycle", ms: 225, note: "read/write/read, 200–250 ms typical — the command path, not the meter" }
  ];
  function paint(){
    var ramp = +r.value, meter = ramp * 1000 / 10, pid = ramp * 1000 / 5;
    document.getElementById("tb-ramp-o").textContent = ramp.toFixed(1) + " s";
    t.querySelector("[data-tb-meter]").innerHTML = "≤ " + Math.round(meter) + ' <small>ms</small>';
    t.querySelector("[data-tb-pid]").innerHTML = "≤ " + Math.round(pid) + ' <small>ms</small>';
    t.querySelector("[data-tb-msg]").innerHTML = "A <b>" + ramp.toFixed(1) + " s</b> ramp needs POI data at <b>" + Math.round(meter) +
      " ms</b> or faster, and the PID running at <b>" + Math.round(pid) + " ms</b> or faster (5&#215; the ramp — the preferred figure; 3–4&#215; is the stated minimum).";
    t.querySelector("[data-tb-proto]").innerHTML = PROTO.map(function(p){
      var ok = p.ms <= meter, isCmd = p.n.indexOf("Modbus") >= 0;
      return '<div class="stat" data-s="' + (isCmd ? "" : ok ? "ok" : "bad") + '" style="display:flex;align-items:baseline;justify-content:space-between;gap:12px">' +
        '<dt style="text-transform:none;letter-spacing:0;font-family:var(--f-body);font-size:14px;color:var(--ink)">' + p.n +
        '<span style="display:block;font-size:12px;color:var(--muted)">' + p.note + "</span></dt>" +
        '<dd style="font-size:15px;white-space:nowrap">' + p.ms + " ms" +
        (isCmd ? "" : " · " + (ok ? "fits" : "too slow")) + "</dd></div>";
    }).join("");
  }
  r.oninput = paint; paint();
})();

/* ---- PFR ---- */
(function(){
  var t = document.querySelector('[data-tool="pfr"]'); if (!t) return;
  var f = document.getElementById("pfr-f"), db = document.getElementById("pfr-db"), dr = document.getElementById("pfr-dr");
  var RATING = 50; /* MW */
  function paint(){
    var fr = +f.value, dbv = +db.value / 1000, droop = +dr.value / 100;
    var dev = fr - 60, eff = 0;
    if (Math.abs(dev) > dbv) eff = dev - Math.sign(dev) * dbv;
    var dP = -(eff / 60) / droop * RATING;
    document.getElementById("pfr-f-o").textContent = fr.toFixed(3) + " Hz";
    document.getElementById("pfr-db-o").textContent = (+db.value) + " mHz";
    document.getElementById("pfr-dr-o").textContent = (+dr.value) + " %";
    t.querySelector("[data-pfr-dev]").innerHTML = (dev * 1000).toFixed(0) + ' <small>mHz</small>';
    var d = t.querySelector("[data-pfr-dp]");
    d.innerHTML = (dP >= 0 ? "+" : "") + dP.toFixed(1) + ' <small>MW</small>';
    d.parentNode.dataset.s = Math.abs(dP) < 0.05 ? "" : dP > 0 ? "ok" : "bad";
    t.querySelector("[data-pfr-msg]").innerHTML = Math.abs(eff) < 1e-9
      ? "Inside the dead band — <b>no compensation applied.</b> The delta added to the MPC P setpoint is zero."
      : (dev < 0
        ? "Frequency is <b>low</b>. PFR asks the plant for <b>" + Math.abs(dP).toFixed(1) + " MW more</b>, added as a delta on the MPC P setpoint — the plant setpoint itself has not changed."
        : "Frequency is <b>high</b>. PFR backs the plant off by <b>" + Math.abs(dP).toFixed(1) + " MW</b>, applied as a negative delta on the MPC P setpoint.");
  }
  f.oninput = db.oninput = dr.oninput = paint; paint();
})();

/* ---- live plant mimic (slide 11) ---- */
(function(){
  var t = document.querySelector('[data-tool="mimic"]'); if (!t) return;
  var sim = new Plant({ inverters: 15 });
  sim.set("PSetpoint", 30000);
  sim.preroll(150);
  var trend = t.querySelector("[data-mimic-trend]"),
      array = t.querySelector("[data-mimic-array]"),
      msg   = t.querySelector("[data-mimic-msg]");
  var lamps = {};
  document.querySelectorAll("[data-lamp]").forEach(function(l){ lamps[l.dataset.lamp] = l; });

  function fmt(kw){ return (kw / 1000).toFixed(1); }
  function paint(){
    trend.innerHTML = sim.trendSVG(560, 172, 90);
    t.querySelector("[data-m-poi]").innerHTML = fmt(sim.poiP) + ' <small>MW</small>';
    t.querySelector("[data-m-irr]").innerHTML = Math.round(sim.irradiance * 100) + ' <small>%</small>';
    var err = sim.p.PSetpoint - sim.poiP;
    var e = t.querySelector("[data-m-err]");
    e.innerHTML = (err >= 0 ? "+" : "") + Math.round(err).toLocaleString() + ' <small>kW</small>';
    e.parentNode.dataset.s = Math.abs(err) <= sim.p.PDeadband ? "ok" : Math.abs(err) > 4000 ? "bad" : "caution";
    var clamped = sim.inv.filter(function(v){ return v.clamped; }).length;
    var cl = t.querySelector("[data-m-clamped]");
    cl.textContent = clamped;
    cl.parentNode.dataset.s = clamped ? "bad" : "ok";

    if (lamps.band) lamps.band.dataset.on = Math.abs(err) > sim.p.PDeadband ? "1" : "0";
    if (lamps.clamp) lamps.clamp.dataset.on = clamped ? "1" : "0";

    array.innerHTML = sim.inv.map(function(v){
      var pct = Math.round(v.out / v.rating * 100);
      var state = v.clamped ? "bad" : !v.responsive ? "caution" : "";
      return '<div class="stat" style="padding:6px 5px;gap:2px' + (state === "bad" ? ";border-color:var(--alarm)" : state === "caution" ? ";border-color:var(--caution)" : "") + '">' +
        '<dt style="font-size:8.5px">INV ' + String(v.id).padStart(2, "0") + "</dt>" +
        '<dd style="font-size:12px' + (state === "bad" ? ";color:var(--alarm)" : "") + '">' + pct + '<small>%</small></dd>' +
        '<span class="bargraph" style="height:3px"><i style="width:' + pct + '%"></i></span></div>';
    }).join("");

    var stuck = sim.inv.filter(function(v){ return !v.responsive; });
    msg.innerHTML = clamped
      ? "<b>Inverter " + sim.inv.filter(function(v){ return v.clamped; })[0].id +
        " is held at 115% of what it is actually producing</b> — the adaptive power limit, capping it at <b>" +
        Math.round(sim.inv.filter(function(v){ return v.clamped; })[0].adaptive) +
        " kW</b>. Without that cap it would wind up against a setpoint it cannot meet, and dump the difference the moment its shading cleared."
      : stuck.length
      ? "<b>Inverter " + stuck[0].id + " has stopped following its setpoint.</b> The controller has not reacted yet — it waits <b>" +
        sim.p.PLimitDelay + " s</b> before applying the adaptive limit."
      : sim.irradiance < 0.98
      ? "Irradiance is down to <b>" + Math.round(sim.irradiance * 100) + "%</b>. Every inverter is making less than its limit allows, so the POI falls with the sun — no controller action can recover power that is not there."
      : "Plant is following setpoint inside the <b>" + sim.p.PDeadband + " kW</b> deadband. Stall an inverter or pass a cloud.";
  }

  var runner = new PlantRunner(sim, paint, 20);
  document.getElementById("m-sp").oninput = function(){
    sim.set("PSetpoint", +this.value);
    document.getElementById("m-sp-o").textContent = (+this.value).toLocaleString() + " kW";
  };
  document.getElementById("m-delay").oninput = function(){
    sim.set("PLimitDelay", +this.value);
    document.getElementById("m-delay-o").textContent = this.value + " s" + (+this.value >= 120 ? "  (library default)" : "");
  };
  t.querySelector('[data-act="stall"]').onclick = function(){
    var v = sim.inv[2], stalling = v.responsive;
    /* shade this one inverter and stop it following its limit back up */
    v.responsive = !stalling;
    v.derate = stalling ? 0.35 : 1;
    if (!stalling) { v.stuckSince = null; v.adaptive = null; v.clamped = false; }
    this.setAttribute("aria-pressed", String(stalling));
    this.querySelector(".v").textContent = stalling ? "Release inverter 3" : "Stall inverter 3";
    this.querySelector(".d").textContent = stalling ? "restores output and control" : "loses output, stops following";
  };
  t.querySelector('[data-act="cloud"]').onclick = function(){ sim.passCloud(0.55, 14); };

  /* only run while the slide is on screen */
  var myIndex = [].indexOf.call(document.querySelectorAll(".slide"), t.closest(".slide"));
  onSlideChange(function(i){ i === myIndex ? runner.start() : runner.stop(); });
  paint();
})();

/* ---- PID: the two libraries, side by side ---- */
(function(){
  var t = document.querySelector('[data-tool="pid"]'); if (!t) return;
  var kp = document.getElementById("pid-kp"), KI = 0.01;
  var host = t.querySelector("[data-pid-chart]");
  var dt = 0.05, T = 20, tau = 1.0, L = 0.35, nL = Math.round(L / dt);
  /* Grid Connect: accumulates the previous P-term with the new error x KP term,
     so it reaches 100% even with KI at zero. */
  function gridConnect(KP, ki){
    var y = 0, I = 0, u = 0, pts = [], us = [];
    for (var i = 0; i * dt <= T; i++) {
      var e = 100 - y; I += e * dt;
      u = Math.max(0, Math.min(145, u + (KP * 0.7 * e + ki * 0.05 * I) * dt));
      us.push(u);
      y += ((us.length > nL ? us[us.length - 1 - nL] : 0) - y) / tau * dt;
      pts.push([i * dt, y]);
    }
    return pts;
  }
  /* SCLutils.PID: positional form - with KI at zero it cannot reach 100% response. */
  function sclUtils(KP, ki){
    var y = 0, I = 0, pts = [], us = [];
    for (var i = 0; i * dt <= T; i++) {
      var e = 100 - y; I += e * dt;
      us.push(Math.max(0, Math.min(145, KP * 2.8 * e + ki * 0.05 * I)));
      y += ((us.length > nL ? us[us.length - 1 - nL] : 0) - y) / tau * dt;
      pts.push([i * dt, y]);
    }
    return pts;
  }
  function paint(){
    var KP = +kp.value;
    document.getElementById("pid-kp-o").textContent = KP.toFixed(2);
    var tag = document.querySelector("[data-pid-tag]");
    if (tag) tag.textContent = "KP " + KP.toFixed(2) + " · KI " + KI.toFixed(3);
    var a = gridConnect(KP, KI), b = sclUtils(KP, KI);
    var peak = a.reduce(function(m, p){ return Math.max(m, p[1]); }, 0);
    var over = Math.max(0, peak - 100);
    var bFinal = b[b.length - 1][1];
    host.innerHTML = mkChart({
      w: 720, h: 240, x: [0, 20], y: [0, 145],
      xTicks: [0, 5, 10, 15, 20], yTicks: [0, 50, 100, 145],
      yFmt: function(v){ return v + "%"; }, xLabel: "seconds", yLabel: "response",
      alt: "Step response of the Grid Connect PI compared with SCLutils.PID at the chosen KP and KI",
      series: [
        { pts: [[0, 100], [20, 100]], color: "var(--rule-strong)", w: 2, dash: true },
        { pts: b, color: "var(--ink-2)", w: 2, dash: true, end: true },
        { pts: a, color: "var(--pen)", w: 2, end: true }
      ]
    });
    var os = t.querySelector("[data-pid-os]");
    os.innerHTML = over < 0.5 ? "none" : over.toFixed(0) + ' <small>%</small>';
    os.parentNode.dataset.s = over > 20 ? "bad" : over < 8 ? "ok" : "";
    var ss = t.querySelector("[data-pid-ss]");
    ss.innerHTML = bFinal.toFixed(0) + ' <small>% of setpoint</small>';
    ss.parentNode.dataset.s = bFinal > 95 ? "ok" : "bad";
    var msg;
    if (KI === 0 && Math.abs(KP - 0.4) < 0.001) msg = "<b>This is the configuration they settled on.</b> KI at zero, KP 0.4 alone — viable only because Grid Connect accumulates the previous P-term with the new error &#215; KP term. <b><code>SCLutils.PID</code> plateaus at " + bFinal.toFixed(0) + "%</b> and stays there. Same numbers, different block, different outcome.";
    else if (KI === 0) msg = "<b>KI is zero.</b> Grid Connect still climbs to 100% through its accumulation; <b><code>SCLutils.PID</code> plateaus at " + bFinal.toFixed(0) + "%</b> — on the standard form, P-term = error &#215; KP can never close the last of the error.";
    else if (over > 20) msg = "<b>KP is too high.</b> This is exactly what they ran into: <b>KP was the side making the problem</b>, which is why it was KI that went to zero and KP that was tuned. The loop is boosted into overshoot faster than anything can settle it — at the POI that arrives as a step.";
    else if (KP < 0.25) msg = "KP is below the suggested starting range. <b>Start around 0.3–0.4</b> and watch the shape. <b>KI 0.01 with KP 0.2 was tested and gave no trouble</b> — the trouble was always on the KP side.";
    else msg = "KP is in the suggested <b>0.3–0.4</b> starting range. KP is the booster; KI provides the compensation and takes the damping out.";
    t.querySelector("[data-pid-msg]").innerHTML = msg +
      ' <span class="unconfirmed">illustrative first-order plant with 350 ms of loop delay — the shape and the library difference, not your plant\'s numbers</span>';
  }
  kp.oninput = paint;
  [].forEach.call(t.querySelectorAll("[data-ki] [data-v]"), function(b){
    b.onclick = function(){ KI = +b.dataset.v;
      [].forEach.call(t.querySelectorAll("[data-ki] [data-v]"), function(x){ x.setAttribute("aria-pressed", String(x === b)); }); paint(); };
  });
  var r = document.querySelector('[data-reset="pid"]');
  if (r) r.onclick = function(){ kp.value = 0.4; KI = 0.01;
    [].forEach.call(t.querySelectorAll("[data-ki] [data-v]"), function(x){ x.setAttribute("aria-pressed", String(x.dataset.v === "0.01")); }); paint(); };
  paint();
})();

/* ---- deadband ---- */
(function(){
  var t = document.querySelector('[data-tool="db"]'); if (!t) return;
  var mw = document.getElementById("db-mw"), cl = document.getElementById("db-cl");
  function paint(){
    var m = +mw.value, c = +cl.value;
    /* the manual's rule of thumb: 10% of max generation, then the clamping % on top.
       56 MW at 5% -> 5.6 MW x 5% = 280 kW -> round up to ~300 kW, as worked through in the session. */
    var lowOutput = m * 0.10, deadband = lowOutput * c / 100 * 1000;  /* MW -> kW */
    document.getElementById("db-mw-o").textContent = m + " MW";
    document.getElementById("db-cl-o").textContent = c + " %";
    var rounded = Math.ceil(deadband / 50) * 50;
    t.querySelector("[data-db-msg]").innerHTML =
      "Ten percent of a <b>" + m + " MW</b> plant is <b class=\"num\">" + lowOutput.toFixed(1) +
      " MW</b> — the plant on a bad day. At <b>" + c + "%</b> clamping that leaves <b class=\"num\">" + Math.round(deadband) +
      " kW</b>, so the deadband wants to be above it — about <b class=\"num\">" + rounded +
      " kW</b>. <b>Deadband has to account for clamping</b>: this is the arithmetic that gave ~280 kW, and a suggested 300 kW, for a 56 MW plant at 5%.";
  }
  mw.oninput = cl.oninput = paint; paint();
})();

/* ---- DDR builder ---- */
(function(){
  var t = document.querySelector('[data-tool="ddr"]'); if (!t) return;
  var out = t.querySelector("[data-ddr-out]"), n = document.querySelector("[data-ddr-n]");
  var picked = [], mode = "event";
  var REF = {
    "P at POI": ["POI.PRG.main.P_MW", "MW"], "Q at POI": ["POI.PRG.main.Q_MVAr", "MVAr"],
    "Plant setpoint": ["GridConnect.PRG.main.PlantSP", "MW"], "POI frequency": ["POI.PRG.main.Freq", "Hz"],
    "Inverter 03 setpoint": ["MPC.PRG.main.InvSP[3]", "kW"], "Clamping state": ["MPC.PRG.main.Clamped[3]", "bool"]
  };
  function paint(){
    if (n) n.textContent = picked.length + (picked.length === 1 ? " channel" : " channels");
    var per = +document.getElementById("ddr-per").value;
    var lines = [
      "trigger      : " + (mode === "event" ? "event-driven" : "periodic"),
      "sampling     : " + per + " ms",
      "time base    : UTC",
      "output path  : /ddr/pcod/          (project side — not your laptop)",
      "file name    : pcod_response",
      ""
    ];
    if (!picked.length) lines.push("channels     : none selected — pick the signals you need to prove the response");
    else picked.forEach(function(p, i){
      lines.push("channel " + String(i + 1).padStart(2, "0") + "   : " + REF[p][0].padEnd(32) + " [" + REF[p][1] + "]   " + p);
    });
    if (picked.length) {
      lines.push("");
      var has = picked.indexOf("P at POI") >= 0 && picked.indexOf("Plant setpoint") >= 0;
      lines.push(has
        ? "→ P and setpoint together: this CSV can show 100% response within 5 minutes of a 0-to-100 setpoint change."
        : "→ add both P at POI and Plant setpoint to validate the 0-to-100 response requirement.");
      if (per > 100) lines.push("→ " + per + " ms sampling is coarse for a PFR trace; the session's use was high-speed data.");
    }
    out.textContent = lines.join("\n");
  }
  [].forEach.call(t.querySelectorAll("[data-sig]"), function(b){
    b.onclick = function(){
      var s = b.dataset.sig, i = picked.indexOf(s);
      if (i >= 0) picked.splice(i, 1); else picked.push(s);
      b.setAttribute("aria-pressed", String(i < 0)); paint();
    };
  });
  [].forEach.call(t.querySelectorAll("[data-mode]"), function(b){
    b.onclick = function(){ mode = b.dataset.mode;
      [].forEach.call(t.querySelectorAll("[data-mode]"), function(x){ x.setAttribute("aria-pressed", String(x === b)); }); paint(); };
  });
  document.getElementById("ddr-per").oninput = paint;
  var r = document.querySelector('[data-reset="ddr"]');
  if (r) r.onclick = function(){ picked = [];
    [].forEach.call(t.querySelectorAll("[data-sig]"), function(x){ x.setAttribute("aria-pressed", "false"); }); paint(); };
  paint();
})();
