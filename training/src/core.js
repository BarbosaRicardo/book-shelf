/* ===== deck core ===== */
(function(){
"use strict";
var KEY = "deck:" + (document.body.dataset.deck || "x");
var slides = [].slice.call(document.querySelectorAll(".slide"));
var N = slides.length, cur = 0, seen = {};

function store(k, v){ try{ localStorage.setItem(KEY + ":" + k, JSON.stringify(v)); }catch(e){} }
function load(k, d){ try{ var v = localStorage.getItem(KEY + ":" + k); return v === null ? d : JSON.parse(v); }catch(e){ return d; } }

seen = load("seen", {});

/* ---- navigation ---- */
var elCount = document.getElementById("count"),
    elProg  = document.getElementById("prog"),
    elPrev  = document.getElementById("prev"),
    elNext  = document.getElementById("next");

function go(i, push){
  i = Math.max(0, Math.min(N - 1, i));
  slides[cur].classList.remove("on");
  cur = i;
  slides[cur].classList.add("on");
  seen[i] = 1; store("seen", seen); store("at", i);
  if (elCount) elCount.innerHTML = "<b>" + String(i + 1).padStart(2, "0") + "</b> / " + String(N).padStart(2, "0");
  if (elProg) elProg.style.width = ((i) / (N - 1) * 100) + "%";
  if (elPrev) elPrev.disabled = i === 0;
  if (elNext) elNext.disabled = i === N - 1;
  if (push !== false && ("#" + (i + 1)) !== location.hash) history.replaceState(null, "", "#" + (i + 1));
  window.scrollTo({ top: 0, behavior: "instant" in document.body.style ? "instant" : "auto" });
  paintOverview();
}
if (elPrev) elPrev.onclick = function(){ go(cur - 1); };
if (elNext) elNext.onclick = function(){ go(cur + 1); };

document.addEventListener("keydown", function(e){
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
  var k = e.key;
  if (k === "ArrowRight" || k === "PageDown" || k === " ") { e.preventDefault(); go(cur + 1); }
  else if (k === "ArrowLeft" || k === "PageUp") { e.preventDefault(); go(cur - 1); }
  else if (k === "Home") { e.preventDefault(); go(0); }
  else if (k === "End") { e.preventDefault(); go(N - 1); }
  else if (k === "g" || k === "G") { toggleOv(); }
  else if (k === "n" || k === "N") { toggleNotes(); }
  else if (k === "Escape") { closeOv(); }
});

/* touch */
var tx = 0, ty = 0;
document.addEventListener("touchstart", function(e){ tx = e.changedTouches[0].clientX; ty = e.changedTouches[0].clientY; }, {passive:true});
document.addEventListener("touchend", function(e){
  var dx = e.changedTouches[0].clientX - tx, dy = e.changedTouches[0].clientY - ty;
  if (Math.abs(dx) > 64 && Math.abs(dx) > Math.abs(dy) * 1.8) go(cur + (dx < 0 ? 1 : -1));
}, {passive:true});

/* ---- overview ---- */
var ov = document.getElementById("ov"), ovGrid = document.getElementById("ovGrid");
function buildOverview(){
  if (!ovGrid) return;
  ovGrid.innerHTML = "";
  slides.forEach(function(s, i){
    var b = document.createElement("button");
    b.className = "ov-card"; b.type = "button";
    var clock = s.dataset.clock || "";
    var t = s.dataset.short || (s.querySelector(".title, h1") || {}).textContent || ("Slide " + (i + 1));
    b.innerHTML = '<span class="oi"><span>' + String(i + 1).padStart(2, "0") + '</span><span>' + clock + '</span></span>' +
                  '<span class="ot"></span><span class="bar"></span>';
    b.querySelector(".ot").textContent = t.trim();
    b.onclick = function(){ closeOv(); go(i); };
    ovGrid.appendChild(b);
  });
  paintOverview();
}
function paintOverview(){
  if (!ovGrid) return;
  [].forEach.call(ovGrid.children, function(c, i){
    c.setAttribute("aria-current", i === cur ? "true" : "false");
    c.dataset.seen = seen[i] ? "1" : "0";
  });
}
function toggleOv(){ if (!ov) return; ov.hidden ? (ov.hidden = false) : closeOv(); }
function closeOv(){ if (ov) ov.hidden = true; }
var ovBtn = document.getElementById("ovBtn"), ovClose = document.getElementById("ovClose");
if (ovBtn) ovBtn.onclick = toggleOv;
if (ovClose) ovClose.onclick = closeOv;
if (ov) ov.addEventListener("click", function(e){ if (e.target === ov) closeOv(); });

/* ---- notes ---- */
function toggleNotes(){
  var on = document.body.dataset.notes === "1";
  document.body.dataset.notes = on ? "0" : "1";
  store("notes", !on);
  var b = document.getElementById("notesBtn");
  if (b) b.setAttribute("aria-pressed", String(!on));
}
var nb = document.getElementById("notesBtn");
if (nb) nb.onclick = toggleNotes;
document.body.dataset.notes = load("notes", false) ? "1" : "0";
if (nb) nb.setAttribute("aria-pressed", document.body.dataset.notes);

/* ---- checklists ---- */
[].forEach.call(document.querySelectorAll("[data-chk]"), function(list){
  var id = list.dataset.chk, saved = load("chk:" + id, {});
  var boxes = [].slice.call(list.querySelectorAll("input[type=checkbox]"));
  var bar = list.parentNode.querySelector(".chk-bar .fill");
  var cnt = list.parentNode.querySelector(".chk-bar .n");
  function paint(){
    var done = boxes.filter(function(b){ return b.checked; }).length;
    if (bar) bar.style.width = (done / boxes.length * 100) + "%";
    if (cnt) cnt.textContent = done + " of " + boxes.length;
  }
  boxes.forEach(function(b, i){
    b.checked = !!saved[i];
    b.onchange = function(){ saved[i] = b.checked; store("chk:" + id, saved); paint(); };
  });
  paint();
  var r = list.parentNode.querySelector("[data-chk-reset]");
  if (r) r.onclick = function(){ boxes.forEach(function(b, i){ b.checked = false; saved[i] = false; }); store("chk:" + id, saved); paint(); };
});

/* ---- classify / sorter ---- */
[].forEach.call(document.querySelectorAll("[data-sort]"), function(w){
  var items = [].slice.call(w.querySelectorAll("[data-ans]"));
  var out = w.querySelector("[data-sort-out]");
  var done = 0, right = 0;
  items.forEach(function(it){
    [].forEach.call(it.querySelectorAll("button[data-pick]"), function(b){
      b.onclick = function(){
        if (it.dataset.done) return;
        it.dataset.done = "1"; done++;
        var ok = b.dataset.pick === it.dataset.ans;
        if (ok) right++;
        b.classList.add(ok ? "ok" : "no");
        [].forEach.call(it.querySelectorAll("button[data-pick]"), function(x){
          x.disabled = true;
          if (!ok && x.dataset.pick === it.dataset.ans) x.classList.add("ok");
        });
        var why = it.querySelector(".why"); if (why) why.classList.add("on");
        if (out) out.textContent = right + " of " + done + " right" + (done === items.length ? " — all sorted." : "");
      };
    });
  });
});

/* ---- quiz ---- */
[].forEach.call(document.querySelectorAll("[data-quiz]"), function(q){
  var qs = [].slice.call(q.querySelectorAll(".q"));
  var scoreEl = q.querySelector("[data-score]");
  var right = 0, answered = 0;
  qs.forEach(function(item){
    var btns = [].slice.call(item.querySelectorAll(".a"));
    btns.forEach(function(b){
      b.onclick = function(){
        if (item.dataset.done) return;
        item.dataset.done = "1"; answered++;
        var ok = b.dataset.ok === "1";
        if (ok) right++;
        b.dataset.r = ok ? "ok" : "no";
        btns.forEach(function(x){ x.disabled = true; if (!ok && x.dataset.ok === "1") x.dataset.r = "ok"; });
        var why = item.querySelector(".why"); if (why) why.classList.add("on");
        if (scoreEl) scoreEl.innerHTML = "<b>" + right + "</b> / " + qs.length +
          (answered === qs.length ? " &nbsp;·&nbsp; " + (right === qs.length ? "clean sweep" : right >= qs.length - 1 ? "solid" : "worth a re-read") : "");
      };
    });
  });
});

/* ---- chart helper ---- */
window.mkChart = function(opts){
  var W = opts.w || 720, H = opts.h || 250;
  var m = opts.m || { l: 52, r: 20, t: 26, b: 32 };
  var xd = opts.x, yd = opts.y;
  var iw = W - m.l - m.r, ih = H - m.t - m.b;
  function X(v){ return m.l + (v - xd[0]) / (xd[1] - xd[0]) * iw; }
  function Y(v){ return m.t + ih - (v - yd[0]) / (yd[1] - yd[0]) * ih; }
  var s = '<svg class="chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + (opts.alt || "chart") + '">';
  (opts.rects || []).forEach(function(r){
    s += '<rect x="' + X(r.x0) + '" y="' + Y(r.y1) + '" width="' + Math.max(2, X(r.x1) - X(r.x0)) +
         '" height="' + Math.max(2, Y(r.y0) - Y(r.y1)) + '" fill="' + r.fill + '" stroke="' + (r.stroke || "none") + '" stroke-width="1"></rect>';
  });
  (opts.bands || []).forEach(function(b){
    s += '<rect x="' + X(xd[0]) + '" y="' + Y(b.to) + '" width="' + iw + '" height="' + Math.max(1, Y(b.from) - Y(b.to)) +
         '" fill="' + b.fill + '"></rect>';
    if (b.label) s += '<text x="' + (X(xd[1]) - 4) + '" y="' + (Y(b.to) - 4) + '" text-anchor="end">' + b.label + '</text>';
  });
  (opts.yTicks || []).forEach(function(t){
    s += '<line class="grid" x1="' + m.l + '" y1="' + Y(t) + '" x2="' + (W - m.r) + '" y2="' + Y(t) + '"></line>' +
         '<text x="' + (m.l - 8) + '" y="' + (Y(t) + 3.5) + '" text-anchor="end">' + (opts.yFmt ? opts.yFmt(t) : t) + '</text>';
  });
  (opts.xTicks || []).forEach(function(t){
    s += '<text x="' + X(t) + '" y="' + (H - m.b + 15) + '" text-anchor="middle">' + (opts.xFmt ? opts.xFmt(t) : t) + '</text>';
  });
  s += '<line class="axis" x1="' + m.l + '" y1="' + (m.t + ih) + '" x2="' + (W - m.r) + '" y2="' + (m.t + ih) + '"></line>';
  (opts.vlines || []).forEach(function(v){
    s += '<line x1="' + X(v.at) + '" y1="' + m.t + '" x2="' + X(v.at) + '" y2="' + (m.t + ih) +
         '" stroke="' + v.color + '" stroke-width="1.5" stroke-dasharray="3 3"></line>';
    if (v.label) s += '<text x="' + (X(v.at) + 5) + '" y="' + (m.t + 11) + '" fill="' + v.color + '">' + v.label + '</text>';
  });
  (opts.series || []).forEach(function(se){
    var d = se.pts.map(function(p, i){ return (i ? "L" : "M") + X(p[0]).toFixed(2) + " " + Y(p[1]).toFixed(2); }).join(" ");
    if (se.fill) s += '<path d="' + d + ' L' + X(se.pts[se.pts.length - 1][0]).toFixed(2) + ' ' + Y(yd[0]) + ' L' + X(se.pts[0][0]).toFixed(2) + ' ' + Y(yd[0]) + ' Z" fill="' + se.fill + '"></path>';
    s += '<path d="' + d + '" fill="none" stroke="' + se.color + '" stroke-width="' + (se.w || 2) +
         '" stroke-linejoin="round" stroke-linecap="round"' + (se.dash ? ' stroke-dasharray="5 4"' : "") + '></path>';
    if (se.end) {
      var lp = se.pts[se.pts.length - 1];
      s += '<circle cx="' + X(lp[0]).toFixed(2) + '" cy="' + Y(lp[1]).toFixed(2) + '" r="3.5" fill="' + se.color +
           '" stroke="var(--surface)" stroke-width="2"></circle>';
    }
    if (se.label) {
      var p0 = se.labelAt || se.pts[Math.floor(se.pts.length * 0.62)];
      s += '<text x="' + (X(p0[0]) + 6) + '" y="' + (Y(p0[1]) - 7) + '" fill="' + se.color + '" style="font-weight:500">' + se.label + '</text>';
    }
  });
  if (opts.yLabel) s += '<text x="' + (m.l - 8) + '" y="' + (m.t - 12) + '" text-anchor="end">' + opts.yLabel + '</text>';
  if (opts.xLabel) s += '<text x="' + (W - m.r) + '" y="' + (H - 2) + '" text-anchor="end">' + opts.xLabel + '</text>';
  return s + "</svg>";
};
window.penColor = function(){ return getComputedStyle(document.body).getPropertyValue("--pen").trim(); };
window.tok = function(n){ return getComputedStyle(document.body).getPropertyValue(n).trim(); };

/* ---- boot ---- */
buildOverview();
var start = 0;
var h = parseInt((location.hash || "").slice(1), 10);
if (h >= 1 && h <= N) start = h - 1; else start = Math.min(load("at", 0), N - 1);
slides.forEach(function(s){ s.classList.remove("on"); });
go(start, false);
window.addEventListener("hashchange", function(){
  var i = parseInt((location.hash || "").slice(1), 10);
  if (i >= 1 && i <= N && i - 1 !== cur) go(i - 1, false);
});
if (window.claude && window.claude.hot) {
  window.claude.hot.snapshot(function(){ return { at: cur }; });
}
window.deckGo = go;
})();

/* ===== generic click-through flow / node detail ===== */
window.wireFlow = function(name, content, initial){
  var wrap = document.querySelector('[data-flow="' + name + '"]');
  var out = document.querySelector('[data-flow-out="' + name + '"]');
  if (!wrap || !out) return;
  var nodes = [].slice.call(wrap.querySelectorAll(".node"));
  function pick(k){
    nodes.forEach(function(n){ n.setAttribute("aria-pressed", String(n.dataset.k === k)); });
    out.innerHTML = content[k] || "";
    if (name === "arc" && window.DECK_URLS) {
      var d = +(k || "").replace("d", "");
      if (d && d !== +document.body.dataset.deck && window.DECK_URLS[d]) {
        out.insertAdjacentHTML("beforeend",
          '<p style="margin-top:12px"><a href="' + window.DECK_URLS[d] + '" target="_blank" rel="noopener" style="font-family:var(--f-mono);font-size:12px;letter-spacing:.04em">Open the Day ' + d + ' deck &rarr;</a></p>');
      }
    }
  }
  nodes.forEach(function(n){ n.onclick = function(){ pick(n.dataset.k); }; });
  pick(initial || nodes[0].dataset.k);
};
