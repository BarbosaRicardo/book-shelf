/* ---- arc ---- */
wireFlow("arc", {
  d1: '<h4>Day 1 — Comms and the RTAC</h4><p>WebPatrol access, protecting the project through a firmware update, libraries and extensions, and DNP3 / Modbus / C37.118 configured to carry correct values fast enough.</p>' +
      '<ul><li>What today inherits: Modbus point lists and register layout, the data types the RTAC will accept, and cross-check as the tool that finds broken references.</li></ul>',
  d2: '<h4>Day 2 — Project and inverters <span class="unconfirmed" style="border-style:solid">you are here</span></h4><p>Choosing the closest existing project, cloning it safely, and converting it to a different inverter model without leaving broken cross-references behind.</p>' +
      '<ul><li>Ends by naming Day 3: Grid Connect variables, the main program, how data enters and leaves the MPC, and recording inputs and outputs for IEEE 2800 performance.</li></ul>',
  d3: '<h4>Day 3 — Control and recording</h4><p>The chain from setpoint source to individual inverter, the timing budget behind it, PID and clamping behaviour, and DDR for proving the response.</p>' +
      '<ul><li>What it inherits from today: the global structures, the custom data types, and the project-level LGI and tuning parameters declared on this morning\'s slide 11.</li></ul>'
}, "d2");

/* ---- architecture ---- */
wireFlow("arch", {
  ign: '<h4>Ignition server</h4><p>Receives PPC data and serves the operator interface. Every inverter you add needs its control and feedback points added here too.</p><ul><li>Varies per site: which devices report through it, and whether the site uses a concentrator or separate connections.</li></ul>',
  rtu: '<h4>RTU redundancy</h4><p>Receive and transmit channels between a primary and a secondary RTU. <b>The primary sends a pulse to the secondary every 200 milliseconds.</b></p><ul><li>Redundancy logic blocks commands when an RTU is not primary — generally unchanged between projects, except that new inverter references must be added to it.</li></ul>',
  inv: '<h4>Inverters</h4><p>The largest source of variation between projects: count, brand, model, and the point list each one publishes.</p><ul><li>Each needs a global variable entry, a read block, a write block, server points, register allocation, and program logic.</li></ul>',
  mtr: '<h4>Primary and backup meters</h4><p>POI metering, with points mapped on both the read side and the project side.</p><ul><li>Day 3 adds the rest of this story: quality is checked primary-to-secondary, and bad quality can trigger a ramp-down or a hold at the last valid value.</li></ul>',
  sub: '<h4>Substation</h4><p>Connected through a concentrator on some sites, directly on others — along with QSC/QTD, the met station and Ignition.</p><ul><li>Which arrangement a template uses belongs in the inventory: it changes the device tree substantially.</li></ul>',
  util: '<h4>Utility connection logic</h4><p>Curtailment and the interface to the area electric power system.</p><ul><li>Usually inherited whole from the template — the numbers change, the structure does not.</li></ul>'
}, "ign");

/* ---- what breaks ---- */
wireFlow("brk", {
  gv: '<h4>1 · Global variables</h4><p>Inverter count and feeder count — <span class="num">15</span> inverters, <span class="num">3</span> feeders in the worked example — plus the inverter-specific data type itself.</p><ul><li>Change the type here and everything downstream that referenced it goes red at once. That is the intended behaviour.</li></ul>',
  rw: '<h4>2 · Read and write blocks</h4><p>Every register mapping that named the old type now points at nothing.</p><ul><li>Register numbers and point names have to match the <b>target inverter\'s</b> point list, not the old one.</li><li>Delete references to points that do not exist on the new model rather than trying to map them to something close.</li></ul>',
  pg: '<h4>3 · Programs and function blocks</h4><p>Read/write logic, inverter status, control commands, redundancy logic and Ignition mappings all hold references you have just invalidated.</p><ul><li>Follow the cross-reference errors into each one. The error list is the work list.</li></ul>',
  sv: '<h4>4 · Server points</h4><p>Ignition control and feedback points for each inverter, mapped back to the read and write structures.</p><ul><li>Fault, comms loss, remote enable, clamp, PPC control and inverter status — per inverter, every time.</li></ul>'
}, "gv");

/* ---- template scorer ---- */
(function(){
  var t = document.querySelector('[data-tool="tmpl"]'); if (!t) return;
  var out = t.querySelector("[data-rank]"), best = document.querySelector("[data-best]");
  var W = { inv: 1, hyb: 1, met: 1, sub: 1 };
  var CANDS = [
    { n: "Mesquite Flats", d: "SunGrow, hybrid, met station, concentrator", m: { inv: 1, hyb: 1, met: 1, sub: 1 }, note: "Same inverter family and hybrid — the fewest changes by a wide margin." },
    { n: "Cholla Ridge", d: "SunGrow, PV only, met station, direct links", m: { inv: 1, hyb: 0, met: 1, sub: 0 }, note: "Same inverter, but the whole storage layer has to be built and the device tree rearranged." },
    { n: "Saguaro West", d: "SMA, hybrid, met station, concentrator", m: { inv: 0, hyb: 1, met: 1, sub: 1 }, note: "Different inverter, but the expensive parts — storage, metering, device tree — come across intact." },
    { n: "Ocotillo", d: "SMA, PV only, no met station, direct links", m: { inv: 0, hyb: 0, met: 0, sub: 0 }, note: "Nothing in common. This is a rebuild wearing a template's name." }
  ];
  function paint(){
    var total = Object.keys(W).reduce(function(a, k){ return a + W[k]; }, 0) || 1;
    var scored = CANDS.map(function(c){
      var s = 0; Object.keys(W).forEach(function(k){ if (W[k] && c.m[k]) s += 1; });
      return { c: c, s: s, pct: Math.round(s / total * 100) };
    }).sort(function(a, b){ return b.s - a.s; });
    if (best) best.textContent = scored[0].s === 0 ? "no usable base" : scored[0].c.n;
    out.innerHTML = scored.map(function(r, i){
      return '<div class="stat" style="margin-bottom:8px;' + (i === 0 && r.s > 0 ? "border-color:var(--good);background:var(--good-wash)" : "") + '">' +
        '<dt>' + r.c.n + " · " + r.c.d + "</dt>" +
        '<dd style="font-size:15px;display:flex;align-items:center;gap:10px">' + r.pct + "%" +
        '<span style="flex:1;height:4px;border-radius:2px;background:var(--rule);overflow:hidden;display:block">' +
        '<span style="display:block;height:100%;width:' + r.pct + '%;background:' + (i === 0 && r.s > 0 ? "var(--good)" : "var(--pen)") + '"></span></span></dd>' +
        '<dt style="text-transform:none;letter-spacing:0;font-family:var(--f-body);font-size:13px;color:var(--muted)">' + r.c.note + "</dt></div>";
    }).join("");
  }
  [].forEach.call(t.querySelectorAll("[data-f]"), function(b){
    b.onclick = function(){
      var on = b.getAttribute("aria-pressed") !== "true";
      b.setAttribute("aria-pressed", String(on)); W[b.dataset.f] = on ? 1 : 0; paint();
    };
  });
  var r = document.querySelector('[data-reset="tmpl"]');
  if (r) r.onclick = function(){ Object.keys(W).forEach(function(k){ W[k] = 1; });
    [].forEach.call(t.querySelectorAll("[data-f]"), function(b){ b.setAttribute("aria-pressed", "true"); }); paint(); };
  paint();
})();

/* ---- repair loop ---- */
(function(){
  var t = document.querySelector('[data-tool="loop"]'); if (!t) return;
  var steps = [].slice.call(t.querySelectorAll("[data-loop-steps] .node"));
  var ERRS = [47, 31, 12, 5, 1, 0];
  var MSG = [
    "Cross-check on the untouched clone: <b>47 cross-reference errors</b> from the inverter data type change. This is the work list.",
    "First pass: the global variables and the inverter data type are consistent. <b>31 left</b> — mostly read and write blocks now pointing at registers that moved.",
    "Second pass: read and write blocks remapped to the new point list. <b>12 left</b>, all inside programs and function blocks.",
    "Third pass: programs and status logic updated. <b>5 left</b> — the Ignition server points for the changed inverter.",
    "Fourth pass: server points mapped. <b>1 left</b> — a prior reference to <span class=\"num\">10</span> that has to become <span class=\"num\">09</span>. Small, real, and only findable this way.",
    "<b>Zero errors.</b> Five passes, one change at a time, each one saved and cross-checked. There is no faster method that converges."
  ];
  var i = 0;
  function paint(){
    t.querySelector("[data-errs]").textContent = ERRS[i];
    t.querySelector("[data-errs]").parentNode.dataset.s = ERRS[i] === 0 ? "ok" : ERRS[i] > 20 ? "bad" : "";
    t.querySelector("[data-passn]").innerHTML = i + ' <small>of 5</small>';
    t.querySelector("[data-loop-msg]").innerHTML = MSG[i];
    var lbl = document.querySelector("[data-pass]"); if (lbl) lbl.textContent = "pass " + i;
    steps.forEach(function(s, k){ s.setAttribute("aria-pressed", String(i > 0 && k === (i - 1) % 4)); });
    var adv = t.querySelector("[data-advance]");
    adv.disabled = i >= ERRS.length - 1;
    adv.textContent = i >= ERRS.length - 1 ? "Zero errors ✓" : "Advance →";
  }
  t.querySelector("[data-advance]").onclick = function(){ if (i < ERRS.length - 1) { i++; paint(); } };
  var r = document.querySelector('[data-reset="loop"]'); if (r) r.onclick = function(){ i = 0; paint(); };
  paint();
})();

/* ---- array bounds ---- */
(function(){
  var t = document.querySelector('[data-tool="bounds"]'); if (!t) return;
  var s = document.getElementById("b-idx"), msg = t.querySelector("[data-bmsg]");
  function paint(){
    var v = +s.value, ok = v >= 1 && v <= 49;
    document.getElementById("b-idx-o").textContent = v;
    msg.innerHTML = ok
      ? 'Index <b class="num">' + v + '</b> is inside the declared range <span class="num">1–49</span>. It resolves.'
      : '<b style="color:var(--crit)">Index ' + v + ' is outside the declared range 1–49.</b> The reference fails at cross-check — which is the only place you will see it before it fails on the plant.';
  }
  s.oninput = paint; paint();
})();

/* ---- evolution period ---- */
(function(){
  var t = document.querySelector('[data-tool="evo"]'); if (!t) return;
  var s = document.getElementById("e-per"), msg = t.querySelector("[data-emsg]");
  function paint(){
    var p = +s.value;
    document.getElementById("e-per-o").textContent = p + " ms";
    t.querySelector("[data-rate]").innerHTML = (1000 / p).toFixed(1) + ' <small>× per second</small>';
    t.querySelector("[data-meter]").innerHTML = "≤ " + p + ' <small>ms</small>';
    msg.innerHTML = "A <b>" + p + " ms</b> evolution period reruns the PID every " + p + " milliseconds" +
      (p >= 1000 ? " — a <b>1,000 ms</b> value reruns it once a second." : ".") +
      " <b>The meter behind it has to keep up:</b> an execution period the POI meter cannot feed is a PID acting on stale numbers. Day 3 turns this into a full timing budget.";
  }
  s.oninput = paint; paint();
})();

/* ---- fault normaliser ---- */
(function(){
  var t = document.querySelector('[data-tool="norm"]'); if (!t) return;
  var bits = [0, 0, 0, 0];
  function paint(){
    var any = bits.some(Boolean);
    var st = t.querySelector("[data-fstat]");
    st.dataset.s = any ? "bad" : "ok";
    t.querySelector("[data-fault]").textContent = "Fault = " + (any ? "TRUE" : "FALSE");
  }
  [].forEach.call(t.querySelectorAll("[data-b]"), function(b){
    b.onclick = function(){
      var i = +b.dataset.b; bits[i] = bits[i] ? 0 : 1;
      b.setAttribute("aria-pressed", String(!!bits[i])); paint();
    };
  });
  paint();
})();
