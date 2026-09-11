/* ============================================================
   Plant simulator.
   Structure and defaults follow the GridConnect Instruction Manual
   (date code 20180927): fb_MasterPlantController and fb_PvInverter.
   Simplified — it models the control path the decks teach, not the library.
   ============================================================ */
(function(){
"use strict";

/* What the library ships with. Quoted in the decks; several are deliberately
   conservative placeholders rather than values you would run a plant on. */
var MANUAL = {
  PlantPRating: 50000,           /* kW    */
  PSetpoint: 50000,              /* kW    */
  PDeadband: 500,                /* kW    */
  QDeadband: 250,                /* kVAR  */
  VDeadband: 0.02,               /* kV    */
  PFDeadband: 0.0002,            /* PF    */
  PKp: 1, PKi: 0, QKp: 1, QKi: 0, VKp: 1, VKi: 0, PFKp: 1, PFKi: 0,
  PLimitRampSetpoint: 10,        /* kW/s      0 disables ramp supervision */
  QRampSetpoint: 10,             /* kVAR/s    */
  PFRampSetpoint: 0.02,          /* PF/s      */
  PLimitDelay: 120,              /* s         adaptive power limit delay */
  EvaluationPeriod: 5,           /* s         closed-loop execution period */
  ControlRetryPeriod: 20,        /* s         */
  CapacitorOperationPeriod: 300, /* s         */
  InverterModeChangeControlDelay: 10,
  PlantLowPowerCutoff: 25,       /* kW        */
  PFLagLimit: 0.95, PFLeadLimit: -0.95,
  VLimitHigh: 1.05, VLimitLow: 0.95,
  dV_dQ: 0.01,                   /* Volts/VAR */
  AdaptiveLimitFactor: 1.15      /* 115% of present output */
};

/* What the simulator starts from. A 10 kW/s ramp is the library default and
   would take a 50 MW plant most of an hour to reach setpoint, so the sim runs
   a rate a real site would use and shows the default alongside it. */
var DEFAULTS = {
  PlantPRating: 50000,
  PSetpoint: 50000,
  PDeadband: 500,
  PKp: 1,
  PKi: 0,
  PLimitRampSetpoint: 2500,      /* kW/s — 5% of rating per second */
  PLimitDelay: 15,               /* s    — the value the session settled on */
  EvaluationPeriod: 0.5,
  AdaptiveLimitFactor: 1.15,
  PlantLowPowerCutoff: 25
};

function Plant(opts){
  opts = opts || {};
  this.p = {};
  for (var k in DEFAULTS) this.p[k] = (opts[k] !== undefined) ? opts[k] : DEFAULTS[k];
  var n = opts.inverters || 15;
  var rating = this.p.PlantPRating / n;
  this.inv = [];
  for (var i = 0; i < n; i++) {
    this.inv.push({
      id: i + 1, rating: rating,
      out: 0,                    /* kW actually produced */
      limit: rating,             /* kW commanded limit  */
      avail: rating,             /* kW the sun allows   */
      responsive: true,          /* does it follow the limit */
      derate: 1,                 /* local shading on this inverter alone */
      included: true, fault: false, offline: false,
      clamped: false, stuckSince: null, adaptive: null
    });
  }
  this.t = 0;
  this.acc = 0;                  /* time since last control evaluation */
  this.I = 0;                    /* PI integral */
  this.cmd = 0;                  /* ramped plant power limit, kW */
  this.poiP = 0;
  this.irradiance = 1;           /* 0..1 */
  this.cloud = null;
  this.hist = [];                /* {t, sp, poi} ring, sampled not stepped */
  this.maxHist = 480;
  this.sampleEvery = 0.25;       /* s — 480 samples is then two minutes of trace */
  this.sampleAcc = 0;
  this.quality = true;
}

Plant.prototype.availableRating = function(){
  var r = 0, c = 0;
  this.inv.forEach(function(v){
    if (v.offline || v.fault || !v.included) c += v.out;   /* constant, uncontrollable */
    else r += v.rating;
  });
  return { rating: r, constant: c };
};

/* one control evaluation — runs every EvaluationPeriod */
Plant.prototype.evaluate = function(){
  var a = this.availableRating();
  var target = this.p.PSetpoint - a.constant;
  var err = target - (this.poiP - a.constant);

  /* deadband: inside it the controller does not act */
  if (Math.abs(err) < this.p.PDeadband) { this.outOfBand = false; return; }
  this.outOfBand = true;

  this.I += err * this.p.EvaluationPeriod;
  var demand = target + this.p.PKp * err * 0.25 + this.p.PKi * this.I * 0.02;
  this.demand = Math.max(0, Math.min(this.p.PlantPRating, demand));
};

Plant.prototype.step = function(dt){
  this.t += dt;

  /* sun */
  if (this.cloud) {
    this.cloud.t += dt;
    var c = this.cloud;
    var k = c.t < c.fall ? c.t / c.fall
          : c.t < c.fall + c.hold ? 1
          : c.t < c.fall + c.hold + c.rise ? 1 - (c.t - c.fall - c.hold) / c.rise : 0;
    this.irradiance = 1 - c.depth * Math.max(0, Math.min(1, k));
    if (c.t > c.fall + c.hold + c.rise) { this.cloud = null; this.irradiance = 1; }
  }

  /* control evaluation on its own period */
  this.acc += dt;
  if (this.acc >= this.p.EvaluationPeriod) { this.acc = 0; this.evaluate(); }
  if (this.demand === undefined) this.demand = this.p.PSetpoint;

  /* ramp supervision on the plant limit — 0 disables it */
  var want = this.demand;
  if (this.p.PLimitRampSetpoint > 0) {
    var maxStep = this.p.PLimitRampSetpoint * dt;
    this.cmd += Math.max(-maxStep, Math.min(maxStep, want - this.cmd));
  } else this.cmd = want;

  /* dispatch: simple power limit — share across available inverters */
  var a = this.availableRating();
  var share = a.rating > 0 ? Math.max(0, this.cmd - a.constant) / a.rating : 0;
  var self = this, poi = 0;

  this.inv.forEach(function(v){
    v.avail = v.rating * self.irradiance * v.derate;
    if (v.offline) { v.out = 0; v.clamped = false; return; }
    if (v.fault || !v.included) { poi += v.out; return; }

    var cmdLimit = v.rating * share;

    /* adaptive power limit: an inverter that will not follow its setpoint is
       held to 115% of what it is presently producing, after PLimitDelay. */
    if (v.responsive) { v.stuckSince = null; v.adaptive = null; v.clamped = false; }
    else {
      if (v.stuckSince === null) v.stuckSince = self.t;
      if (self.t - v.stuckSince >= self.p.PLimitDelay) {
        v.adaptive = v.out * self.p.AdaptiveLimitFactor;
        v.clamped = true;
      }
    }
    if (v.adaptive !== null) cmdLimit = Math.min(cmdLimit, v.adaptive);
    v.limit = cmdLimit;

    var goal = Math.min(cmdLimit, v.avail);
    if (!v.responsive && v.adaptive === null) goal = Math.min(v.out, v.avail);
    v.out += (goal - v.out) * Math.min(1, dt / 0.8);       /* inverter lag */
    poi += v.out;
  });

  this.poiP = poi;
  this.sampleAcc += dt;
  if (this.sampleAcc >= this.sampleEvery) {
    this.sampleAcc = 0;
    this.hist.push({ t: this.t, sp: this.cmd, poi: this.poiP });
    if (this.hist.length > this.maxHist) this.hist.shift();
  }
};

/* Run the plant forward before anyone looks at it, so the trend opens with
   history instead of a single point crawling in from the left. */
Plant.prototype.preroll = function(seconds){
  var dt = 0.05, n = Math.round((seconds || 120) / dt);
  for (var i = 0; i < n; i++) this.step(dt);
};
Plant.prototype.passCloud = function(depth, hold){
  this.cloud = { t: 0, depth: depth === undefined ? 0.55 : depth,
                 fall: 4, hold: hold === undefined ? 12 : hold, rise: 7 };
};
Plant.prototype.set = function(k, v){ this.p[k] = v; };
Plant.prototype.reset = function(){
  this.t = 0; this.acc = 0; this.I = 0; this.cmd = 0; this.poiP = 0;
  this.hist = []; this.sampleAcc = 0; this.cloud = null; this.irradiance = 1; this.demand = undefined;
  this.inv.forEach(function(v){
    v.out = 0; v.clamped = false; v.stuckSince = null; v.adaptive = null;
    v.fault = false; v.offline = false; v.included = true; v.responsive = true; v.derate = 1;
  });
};

/* ---- rolling trend renderer ---- */
Plant.prototype.trendSVG = function(w, h, window_s){
  w = w || 560; h = h || 150; window_s = window_s || 90;
  var m = { l: 46, r: 10, t: 20, b: 18 }, iw = w - m.l - m.r, ih = h - m.t - m.b;
  var yMax = this.p.PlantPRating;
  var t1 = Math.max(window_s, this.t), t0 = t1 - window_s;
  var X = function(t){ return m.l + (t - t0) / window_s * iw; };
  var Y = function(v){ return m.t + ih - Math.max(0, Math.min(yMax, v)) / yMax * ih; };
  var pts = this.hist.filter(function(s){ return s.t >= t0; });
  function path(key){
    return pts.map(function(s, i){ return (i ? "L" : "M") + X(s.t).toFixed(1) + " " + Y(s[key]).toFixed(1); }).join(" ");
  }
  var s = '<svg class="chart" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="Plant setpoint against POI output">';
  [0, .25, .5, .75, 1].forEach(function(f){
    var v = yMax * f;
    s += '<line class="grid" x1="' + m.l + '" y1="' + Y(v) + '" x2="' + (w - m.r) + '" y2="' + Y(v) + '"></line>' +
         '<text x="' + (m.l - 7) + '" y="' + (Y(v) + 3.5) + '" text-anchor="end">' + Math.round(v / 1000) + '</text>';
  });
  s += '<text x="' + m.l + '" y="' + (m.t - 7) + '">MW</text>';
  if (pts.length > 1) {
    s += '<path d="' + path("sp") + '" fill="none" stroke="var(--bezel-hi)" stroke-width="1.5" stroke-dasharray="4 3"></path>';
    s += '<path d="' + path("poi") + '" fill="none" stroke="var(--pen)" stroke-width="2" stroke-linejoin="round"></path>';
    var last = pts[pts.length - 1];
    s += '<circle cx="' + X(last.t).toFixed(1) + '" cy="' + Y(last.poi).toFixed(1) +
         '" r="3" fill="var(--pen-lit)"></circle>';
  }
  return s + "</svg>";
};

/* ---- a driver that only runs while its slide is on screen ---- */
function Runner(sim, onTick, rate){
  this.sim = sim; this.onTick = onTick; this.rate = rate || 20; this.on = false;
}
Runner.prototype.start = function(){
  if (this.on) return; this.on = true;
  var self = this, dt = 1 / this.rate, speed = 4;   /* 4x wall clock, so a 120 s delay is watchable */
  this.timer = setInterval(function(){
    for (var i = 0; i < speed; i++) self.sim.step(dt);
    self.onTick(self.sim);
  }, 1000 / this.rate);
};
Runner.prototype.stop = function(){ clearInterval(this.timer); this.on = false; };

window.Plant = Plant;
window.PlantRunner = Runner;
window.PLANT_DEFAULTS = DEFAULTS;
window.GC_MANUAL = MANUAL;
})();
