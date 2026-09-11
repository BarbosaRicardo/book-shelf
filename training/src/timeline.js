/* ===== shared cover timeline: three mornings on one time axis ===== */
(function(){
"use strict";
var host = document.getElementById("timeline");
if (!host) return;
var DAYS = [
  { d: 1, label: "Mon 8 Sep", t: "RTAC Configuration & Protocols",   s: 15.77, e: 140.05, dur: "2h 04m" },
  { d: 2, label: "Tue 9 Sep", t: "Template Conversion & Inverters",  s: 10.50, e: 106.65, dur: "1h 36m" },
  { d: 3, label: "Wed 10 Sep", t: "Grid Connect Control Logic & DDR", s: 14.60, e: 106.82, dur: "1h 32m" }
];
var me = parseInt(document.body.dataset.pen, 10);
var ALL = !(me >= 1 && me <= 3);           /* landing page: no single day is current */
var LINKS = window.DECK_LINKS || null;
var W = 720, H = 132, L = 74, R = 16, T = 20, rowH = 26;
var T0 = 0, T1 = 150; /* 06:50 -> 09:20 */
function X(m){ return L + (m - T0) / (T1 - T0) * (W - L - R); }
function hhmm(m){ var t = 410 + m; return String(Math.floor(t / 60)).padStart(2, "0") + ":" + String(Math.round(t % 60)).padStart(2, "0"); }

/* clock ticks for THIS deck, read from the slides themselves */
var ticks = [].slice.call(document.querySelectorAll(".slide[data-clock]")).map(function(s, i){
  var p = (s.dataset.clock || "").split(":");
  if (p.length !== 2) return null;
  return { m: (+p[0]) * 60 + (+p[1]) - 410, i: [].indexOf.call(document.querySelectorAll(".slide"), s), label: s.dataset.short || "" };
}).filter(Boolean);

var s = '<svg class="chart" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="The three morning sessions on one time axis">';
[0, 30, 60, 90, 120, 150].forEach(function(m){
  s += '<line class="grid" x1="' + X(m) + '" y1="' + (T - 6) + '" x2="' + X(m) + '" y2="' + (T + rowH * 3 - 8) + '"></line>' +
       '<text x="' + X(m) + '" y="' + (T + rowH * 3 + 8) + '" text-anchor="middle">' + hhmm(m) + '</text>';
});
DAYS.forEach(function(day, r){
  var y = T + r * rowH, on = ALL || day.d === me;
  if (LINKS && LINKS[day.d]) s += '<a href="' + LINKS[day.d] + '" aria-label="Open the Day ' + day.d + ' deck">';
  var c = "var(--pen-" + day.d + ")";
  s += '<text x="' + (L - 10) + '" y="' + (y + 4) + '" text-anchor="end" fill="' + (on ? c : "var(--faint)") + '"' +
       (on ? ' style="font-weight:500"' : "") + '>' + day.label + '</text>';
  s += '<rect x="' + X(day.s) + '" y="' + (y - 5) + '" width="' + (X(day.e) - X(day.s)) + '" height="10" rx="5" fill="' + c + '"' +
       (on ? "" : ' opacity="0.28"') + '></rect>';
  s += '<text x="' + (X(day.e) + 7) + '" y="' + (y + 4) + '" fill="var(--faint)">' + day.dur + '</text>';
  if (LINKS && LINKS[day.d]) {
    s += '<rect x="' + (L - 66) + '" y="' + (y - 11) + '" width="' + (W - L + 60) + '" height="22" fill="transparent"></rect></a>';
  }
  if (on && !ALL) ticks.forEach(function(tk){
    if (tk.m < day.s - 1 || tk.m > day.e + 1) return;
    s += '<line class="tk" data-i="' + tk.i + '" x1="' + X(tk.m) + '" y1="' + (y - 9) + '" x2="' + X(tk.m) + '" y2="' + (y + 9) +
         '" stroke="var(--surface)" stroke-width="1.5"></line>';
  });
});
s += "</svg>";
host.innerHTML = s +
  '<div class="trend-legend">' +
    DAYS.map(function(d){ return '<span><i style="background:var(--pen-' + d.d + ');' + (ALL || d.d === me ? "" : "opacity:.35") + '"></i>' +
      "Day " + d.d + " · " + d.t + "</span>"; }).join("") +
  "</div>";
})();
