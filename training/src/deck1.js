/* ---- slide 2: the arc ---- */
wireFlow("arc", {
  d1: '<h4>Day 1 — Comms and the RTAC <span class="unconfirmed" style="border-style:solid">you are here</span></h4>' +
      '<p>Getting into the box, protecting the project, and making DNP3, Modbus and C37.118 carry correct values at a usable rate.</p>' +
      '<ul><li>Ends by naming the next session: device setup, project bindings, GridConnect mapping, error resolution, and a project built from scratch.</li></ul>',
  d2: '<h4>Day 2 — Project and inverters</h4>' +
      '<p>Choosing the closest existing project, saving it as a new one, and converting it to a different inverter model without leaving broken cross-references behind.</p>' +
      '<ul><li>Depends on Day 1 for: Modbus point lists, register layout, data types the RTAC will accept.</li>' +
      '<li>Ends by naming Day 3: Grid Connect variables, the main program, how data enters and leaves the MPC.</li></ul>',
  d3: '<h4>Day 3 — Control and recording</h4>' +
      '<p>The control chain from setpoint source to individual inverter — bumpless transfer, PFR, limits, ramp, PID, clamping — and DDR for proving the response.</p>' +
      '<ul><li>Depends on Day 1 for: how fast the POI meter can actually deliver data.</li>' +
      '<li>Depends on Day 2 for: the data types and global structures the control blocks read and write.</li></ul>'
}, "d1");

/* ---- slide 4: which send ---- */
(function(){
  var t = document.querySelector('[data-tool="send"]'); if (!t) return;
  var out = t.querySelector("[data-out]");
  var ANS = {
    yes: '<div class="call rule"><span class="tag">Send the full project</span>Forcing values requires a full project download. It reboots the project — plan for that.</div>',
    no:  '<div class="call"><span class="tag">Send IEC 61131-3 logic only</span>The RTAC keeps running and the whole project does not reboot. The trade: <b>you cannot force values</b> afterwards. Advanced send settings can also exclude selected areas — Ethernet or reader settings — from the download.</div>'
  };
  [].forEach.call(t.querySelectorAll("[data-v]"), function(b){
    b.onclick = function(){
      [].forEach.call(t.querySelectorAll("[data-v]"), function(x){ x.setAttribute("aria-pressed", String(x === b)); });
      out.hidden = false; out.innerHTML = ANS[b.dataset.v] +
        '<p class="verdict">Either way: <b>cross-check first.</b> A save that looks clean is not a project that is clean.</p>';
    };
  });
  var r = document.querySelector('[data-reset="send"]');
  if (r) r.onclick = function(){ out.hidden = true; [].forEach.call(t.querySelectorAll("[data-v]"), function(x){ x.setAttribute("aria-pressed", "false"); }); };
})();

/* ---- slide 6: DNP3 decision tree ---- */
(function(){
  var t = document.querySelector('[data-tool="dnp"]'); if (!t) return;
  var q = t.querySelector("[data-q]"), a = t.querySelector("[data-a]"), out = t.querySelector("[data-out]");
  var TREE = {
    start: { q: "Does the RTAC see <b>any</b> traffic from the device — pings, TCP handshakes, ACKs?",
      opts: [ { v: "No traffic at all", go: "noip" }, { v: "Traffic is flowing and acknowledged", go: "app" } ] },
    noip: { q: "Does the port show as open when you check it from the security tools?",
      opts: [ { v: "Port is closed", end: "fw" }, { v: "Port is open, still nothing", end: "ipport" } ] },
    app: { q: "Is more than one DNP3 client running on this RTAC?",
      opts: [ { v: "Yes, several clients", end: "clientport" }, { v: "Just this one", end: "addr" } ] }
  };
  var END = {
    fw: ['Firewall.', 'A port that will not show as open is almost always blocked upstream. This needs the <b>network team</b> — no amount of DNP3 configuration will open it.'],
    ipport: ['Server IP or port mismatch.', 'For a DNP3 client, the <b>server IP and server port must match the remote server configuration</b> exactly. Check the far side rather than assuming your own settings are right.'],
    clientport: ['Client IP port collision.', 'The client IP port identifies the local source of the connection, and <b>each DNP3 client needs its own</b>. RTAC Architect can increment them automatically. Use <code>netstat -an</code> or a capture to find what is already using the port, then change it.'],
    addr: ['Reversed or mismatched DNP addresses.', 'This is the signature failure: <b>IP traffic acknowledged, application layer dead, device offline.</b> The DNP server address and the DNP client&#8202;/&#8202;master address must line up — a client address is commonly <span class="num">0</span> unless the system requires otherwise. Confirm what is actually on the wire in Wireshark\'s application-layer view; a server allowing anonymous connections still needs the addresses to agree.']
  };
  function step(k){
    var n = TREE[k];
    out.hidden = true; q.innerHTML = n.q; a.innerHTML = "";
    n.opts.forEach(function(o){
      var b = document.createElement("button");
      b.className = "opt"; b.type = "button";
      b.innerHTML = '<span class="v">' + o.v + "</span>";
      b.onclick = function(){ o.end ? finish(o.end) : step(o.go); };
      a.appendChild(b);
    });
  }
  function finish(k){
    q.innerHTML = "Most likely cause:"; a.innerHTML = "";
    out.hidden = false;
    out.innerHTML = '<div class="call trap"><span class="tag">' + END[k][0] + "</span>" + END[k][1] + "</div>";
  }
  step("start");
  var r = document.querySelector('[data-reset="dnp"]'); if (r) r.onclick = function(){ step("start"); };
})();

/* ---- slide 7: variation picker ---- */
(function(){
  var t = document.querySelector('[data-tool="var"]'); if (!t) return;
  var out = t.querySelector("[data-out]"), kind = null, ts = null;
  var MAP = {
    float: { g: "30 / 32", nm: "Analog input — measured value",
      yes: "variation with flag (and time for events)", no: "variation without flag",
      warn: "Pick an <b>integer</b> variation here and your float arrives truncated to a whole number." },
    int: { g: "30 / 32", nm: "Analog input — integer",
      yes: "16- or 32-bit with flag", no: "16- or 32-bit without flag",
      warn: "Pick a measured-value type for integer data and you carry a float where the far side expects a count." },
    bin: { g: "1 / 2", nm: "Binary input",
      yes: "with flag; events (group 2) carry the time", no: "packed / with-status, no time",
      warn: "Double-bit inputs are a different thing entirely — four states: no value, on, off, invalid. <b>IEC 104 reads them differently; do not treat them as identical to DNP3.</b>" },
    cnt: { g: "20 / 21", nm: "Counter / frozen counter",
      yes: "with flag; group 21 is the frozen value", no: "without flag",
      warn: "Counter is object <span class=\"num\">20</span>, frozen counter is <span class=\"num\">21</span>. Reading the wrong one gives you a number that never moves." }
  };
  function paint(){
    if (!kind || ts === null) return;
    var m = MAP[kind];
    out.hidden = false;
    out.innerHTML =
      '<div class="stats">' +
        '<div class="stat"><dt>Object group</dt><dd>' + m.g + "</dd></div>" +
        '<div class="stat"><dt>Type</dt><dd style="font-size:14px;line-height:1.35">' + m.nm + "</dd></div>" +
      "</div>" +
      '<p class="verdict">Use the <b>' + (ts === "1" ? m.yes : m.no) + "</b>. Static data uses the first group, events the second — and <b>point numbers have to match between client and server</b> either way.</p>" +
      '<div class="call trap"><span class="tag">Wrong variation looks like</span>' + m.warn + "</div>";
  }
  [].forEach.call(t.querySelectorAll("[data-k] [data-v]"), function(b){
    b.onclick = function(){ kind = b.dataset.v;
      [].forEach.call(t.querySelectorAll("[data-k] [data-v]"), function(x){ x.setAttribute("aria-pressed", String(x === b)); }); paint(); };
  });
  [].forEach.call(t.querySelectorAll("[data-t] [data-v]"), function(b){
    b.onclick = function(){ ts = b.dataset.v;
      [].forEach.call(t.querySelectorAll("[data-t] [data-v]"), function(x){ x.setAttribute("aria-pressed", String(x === b)); }); paint(); };
  });
})();

/* ---- slide 9: Modbus register map ---- */
(function(){
  var t = document.querySelector('[data-tool="mb"]'); if (!t) return;
  var map = t.querySelector("[data-map]"), dec = t.querySelector("[data-decode]"),
      cnt = document.querySelector("[data-count]"), order = "msb";
  var pts = [ { k: "32", n: "P_kW" }, { k: "16", n: "Status" } ];
  var NAMES = { "16": ["Status", "Mode", "Fault_Code", "Ramp_Rate"], "32": ["P_kW", "Q_kVAr", "V_ll", "Freq_Hz"], bits: ["Alarms", "Trips", "Flags"] };
  function paint(){
    var addr = 0, html = "";
    pts.forEach(function(p, i){
      if (p.k === "32") {
        html += '<div class="reg" data-part="hi"><span class="a">' + addr + '</span><span class="l">' + p.n + '</span><span class="a">high word</span></div>';
        html += '<div class="reg" data-part="lo"><span class="a">' + (addr + 1) + '</span><span class="l">' + p.n + '</span><span class="a">low word</span></div>';
        addr += 2;
      } else if (p.k === "bits") {
        html += '<div class="reg" data-part="one"><span class="a">' + addr + '</span><span class="l">' + p.n + '</span><span class="a">bits 0–15</span></div>';
        addr += 1;
      } else {
        html += '<div class="reg" data-part="one"><span class="a">' + addr + '</span><span class="l">' + p.n + '</span><span class="a">int16</span></div>';
        addr += 1;
      }
    });
    for (var f = 0; f < 4; f++) html += '<div class="reg"><span class="a">' + (addr + f) + '</span><span class="l">—</span><span class="a">free</span></div>';
    map.innerHTML = html;
    if (cnt) cnt.textContent = pts.length + (pts.length === 1 ? " point" : " points") + " · " + addr + " registers";
    var first = pts[0];
    if (first && first.k === "32") {
      dec.innerHTML = order === "msb"
        ? 'Far side reads <b>MSB first</b>: register 0 is the high word, register 1 the low word. <span class="num">0x447A 0000</span> decodes as <b class="num">1000.0</b>.'
        : 'Far side reads <b>LSB first</b> while you wrote MSB first. The same two registers now decode as <span class="num">0x0000 447A</span> — about <b class="num">2.5&#215;10<sup>-41</sup></b> instead of <b class="num">1000.0</b>. No error is raised anywhere. <b>Wrong word order fails silently.</b>';
    } else {
      dec.innerHTML = "Add a 32-bit value to see what word order does to it.";
    }
  }
  [].forEach.call(t.querySelectorAll("[data-add]"), function(b){
    b.onclick = function(){
      var k = b.dataset.add, used = pts.filter(function(p){ return p.k === k; }).length;
      pts.push({ k: k, n: NAMES[k][used % NAMES[k].length] + (used >= NAMES[k].length ? "_" + used : "") });
      paint();
    };
  });
  [].forEach.call(t.querySelectorAll("[data-order]"), function(b){
    b.onclick = function(){ order = b.dataset.order;
      [].forEach.call(t.querySelectorAll("[data-order]"), function(x){ x.setAttribute("aria-pressed", String(x === b)); });
      var o = document.getElementById("mb-order-o");
      if (o) o.textContent = order === "msb" ? "MSB first (big-endian)" : "LSB first (word-swapped)";
      paint(); };
  });
  var r = document.querySelector('[data-reset="mb"]'); if (r) r.onclick = function(){ pts = []; paint(); };
  paint();
})();

/* ---- slide 10: C37.118 cycle time ---- */
(function(){
  var t = document.querySelector('[data-tool="c37"]'); if (!t) return;
  var sps = document.getElementById("c-sps"), cyc = document.getElementById("c-cyc");
  function paint(){
    var s = +sps.value, c = +cyc.value, frame = 1000 / s, need = Math.floor(frame);
    document.getElementById("c-sps-o").textContent = s + " samples/s";
    document.getElementById("c-cyc-o").textContent = c + " ms";
    t.querySelector("[data-f]").innerHTML = frame.toFixed(1) + ' <small>ms</small>';
    t.querySelector("[data-need]").innerHTML = "≤ " + need + ' <small>ms</small>';
    var ok = c <= frame;
    var st = t.querySelector("[data-verdict-stat]");
    st.dataset.s = ok ? "ok" : "bad";
    t.querySelector("[data-v]").textContent = ok ? "Keeps up" : "Drops frames";
    t.querySelector("[data-msg]").innerHTML = ok
      ? "A <b>" + c + " ms</b> cycle against a frame every <b>" + frame.toFixed(1) + " ms</b> — the RTAC processes every frame. This is the configuration the session called for at 60 samples per second: roughly <b>15–16 ms</b>."
      : "A <b>" + c + " ms</b> cycle cannot service a frame arriving every <b>" + frame.toFixed(1) + " ms</b>. The rate is not achieved regardless of what the meter is capable of — <b>a 100 ms cycle cannot support 60 samples per second.</b>";
  }
  sps.oninput = cyc.oninput = paint; paint();
})();
