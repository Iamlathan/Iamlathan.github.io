/* Granite City Digital free website check (/free-check/).
   Every submission goes to Lathan through Web3Forms, the same way as the home page forms.
   The automatic layer asks Microlink (keyless, from the visitor's browser) for a phone screenshot
   and a few page facts. Only the site address is sent to Microlink, never the name or phone. */
(function(){
"use strict";

/* Switch for the whole automatic layer. Set to false and every check is done by hand. */
var AUTO_CHECK = true;

var W3F_KEY = "9e32707b-f0a0-4a7a-80fe-50b2923f04c7";
var ML_ENDPOINT = "https://api.microlink.io/";
var ML_DEVICE = "iPhone 15";
var ML_TIMEOUT = 25000;
var BLOCK_KEY = "gcd_fc_ml_block";

var WEIGHTS = {loads:25, call:20, phone:20, hours:15, https:10, speed:10};
var ORDER = ["loads","call","phone","hours","https","speed"];
var NAMES = {loads:"It loads", call:"Call button", phone:"Fits a phone", hours:"Hours shown", https:"Secure address", speed:"Load time estimate"};

/* Pick one of my samples by words in the business name. */
var SAMPLES = [
  /* \b at the start of each group: a word only counts where it begins, so "Street" never matches "tree". */
  [/\b(?:plumb|drain|septic|water heater)/i, "steady-flow-plumbing", "a plumber"],
  [/\b(?:roof|gutter|siding|construct)/i, "rainline-seamless-gutters", "a gutter and roofing business"],
  [/\bpaint/i, "true-line-painting", "a painter"],
  [/\b(?:garage|auto|body ?shop|body works|tire|motor|mechanic|transmission|towing)/i, "westbrook-body-and-tire", "an auto body and tire shop"],
  [/\b(?:caf[eé]|diner|grill|restaurant|kitchen|burger|sandwich|pizza|bbq|barbecue|breakfast|bakery|coffee|eatery)/i, "sunup-southern-breakfast", "a breakfast and lunch spot"],
  [/\b(?:salon|hair|nail|esthetic|beauty|spa\b|barber|lash|brows?\b)/i, "willow-lane-skin-studio", "an esthetician"],
  [/\b(?:trees?\b|lawn|landscap|mow|garden)/i, "high-limb-tree-service", "a tree service"],
  [/\b(?:grading|hauling|concrete|paving)/i, "red-clay-concrete-grading", "a grading business"]
];
var DEFAULT_SAMPLE = ["", "steady-flow-plumbing", "a plumber"];

var $ = function(id){ return document.getElementById(id); };
var form = $("fc-form");
if(!form) return;
var errBox = $("fc-err"), waitBox = $("fc-wait");
var busy = false;
var reduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/* ---------- input checks ---------- */
function normalizeUrl(raw){
  var s = String(raw || "").trim();
  if(!s || s.length > 300 || /\s/.test(s)) return null;
  if(/^\/\//.test(s)) s = s.slice(2);
  if(!/^https?:\/\//i.test(s)){
    if(/^[a-z][a-z0-9+.\-]*:(?!\d)/i.test(s)) return null; /* mailto:, javascript: and the like */
    s = "https://" + s;
  }
  var u;
  try { u = new URL(s); } catch(e){ return null; }
  if(u.protocol !== "http:" && u.protocol !== "https:") return null;
  if(u.username || u.password) return null;
  var host = u.hostname.toLowerCase().replace(/\.$/, "");
  if(host.indexOf(".") < 0) return null;
  if(/^\d+(\.\d+){3}$/.test(host) || host.indexOf(":") >= 0) return null; /* bare IP addresses */
  var parts = host.split(".");
  for(var i = 0; i < parts.length; i++){
    if(!/^[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?$/.test(parts[i])) return null;
  }
  var tld = parts[parts.length - 1];
  if(!/^[a-z]{2,24}$/.test(tld) && !/^xn--[a-z0-9]+$/.test(tld)) return null;
  if(/(^|\.)(localhost|local|internal|example|invalid|test)$/.test(host)) return null;
  return u.href;
}
function loginWalled(href){
  var h = new URL(href).hostname.toLowerCase();
  return /(^|\.)(facebook\.com|fb\.com|fb\.me|instagram\.com)$/.test(h);
}
function phoneOk(p){
  if(!p) return true;
  var d = p.replace(/\D/g, "");
  return d.length === 10 || (d.length === 11 && d.charAt(0) === "1");
}

/* ---------- daily limit memory (so a used up limit does not cost a 25 second wait) ---------- */
function today(){ var d = new Date(); return d.getFullYear() + "-" + (d.getMonth() + 1) + "-" + d.getDate(); }
function blockedToday(){ try { return localStorage.getItem(BLOCK_KEY) === today(); } catch(e){ return false; } }
function blockForToday(){ try { localStorage.setItem(BLOCK_KEY, today()); } catch(e){} }

/* ---------- the automatic check ---------- */
function runCheck(url){
  if(!AUTO_CHECK) return Promise.resolve({ok:false, reason:"automatic check is switched off"});
  if(blockedToday()) return Promise.resolve({ok:false, reason:"free automatic checks used up today"});
  if(!window.fetch || !window.URLSearchParams) return Promise.resolve({ok:false, reason:"old browser"});
  var q = new URLSearchParams();
  q.set("url", url);
  q.set("screenshot", "true");
  q.set("device", ML_DEVICE);
  q.set("meta", "false");
  q.set("data.tel.selectorAll", 'a[href^="tel:"]');
  q.set("data.tel.attr", "href");
  q.set("data.viewport.selector", 'meta[name="viewport"]');
  q.set("data.viewport.attr", "content");
  q.set("data.text.selector", "body");
  q.set("data.text.attr", "text");
  var ctrl = window.AbortController ? new AbortController() : null;
  var timer = setTimeout(function(){ if(ctrl) ctrl.abort(); }, ML_TIMEOUT);
  var t0 = Date.now();
  var timeout = new Promise(function(res){ setTimeout(function(){ res({ok:false, reason:"timed out"}); }, ML_TIMEOUT + 500); });
  var call = fetch(ML_ENDPOINT + "?" + q.toString(), {method:"GET", credentials:"omit", referrerPolicy:"no-referrer", signal: ctrl ? ctrl.signal : undefined})
    .then(function(r){
      var trip = Date.now() - t0;
      var left = r.headers.get("x-rate-limit-remaining");
      /* Use Microlink's own fetch time only when it is a real measurement. A cached answer
         (x-cache-status HIT) reports 0ms, so then, or when the header is missing or 0,
         fall back to this browser's round trip for the request. Either way it is rough. */
      var fetchMs = parseFetchTime(r.headers.get("x-fetch-time"));
      var cached = /HIT/i.test(r.headers.get("x-cache-status") || "");
      var speedMs = (fetchMs !== null && fetchMs > 0 && !cached) ? fetchMs : trip;
      if(left !== null && left !== "" && Number(left) <= 0) blockForToday();
      if(r.status === 429){ blockForToday(); return {ok:false, reason:"daily free automatic checks used up (429)"}; }
      return r.json().then(function(j){
        if(!j || j.status !== "success" || !j.data){
          return {ok:false, reason:"checking service error" + (j && j.code ? " " + String(j.code).slice(0, 40) : " (HTTP " + r.status + ")")};
        }
        return {ok:true, result: scoreIt(j, url, speedMs)};
      }, function(){ return {ok:false, reason:"checking service sent an unreadable answer (HTTP " + r.status + ")"}; });
    })
    .catch(function(e){ return {ok:false, reason: e && e.name === "AbortError" ? "timed out" : "could not reach the checking service"}; });
  return Promise.race([call, timeout]).then(function(v){ clearTimeout(timer); if(ctrl) ctrl.abort(); return v; });
}
function parseFetchTime(v){
  if(!v) return null;
  var m = /([\d.]+)\s*(ms|s)?/i.exec(String(v));
  if(!m) return null;
  var n = parseFloat(m[1]);
  if(!isFinite(n)) return null;
  var unit = (m[2] || "").toLowerCase();
  if(unit === "ms") return n;
  if(unit === "s") return n * 1000;
  return n >= 100 ? n : n * 1000;
}

var DAY = "(?:mon|tue|wed|thu|fri|sat|sun)[a-z]*\\.?";
var TIME = "\\d{1,2}(?::\\d{2})?\\s*(?:a\\.?m\\.?|p\\.?m\\.?)";
var HOURS_TESTS = [
  new RegExp("\\b" + TIME + "\\s*(?:-|\\u2013|\\u2014|to|until|till)\\s*(?:\\d{1,2}(?::\\d{2})?\\s*(?:a\\.?m\\.?|p\\.?m\\.?)?|noon|midnight|close)", "i"),
  new RegExp("\\b" + DAY + "\\s*(?:-|\\u2013|\\u2014|to|through|thru)\\s*" + DAY + "[\\s\\S]{0,30}?\\d", "i"),
  /opening\s*hours|openinghours|business hours|hours of operation|store hours|shop hours|office hours|our hours/i,
  /\bhours\b[\s\S]{0,80}?\b(?:mon|tue|wed|thu|fri|sat|sun)/i,
  /open 24 hours|24\s*\/\s*7/i
];
function hasHours(text){
  var t = String(text || "").slice(0, 400000);
  for(var i = 0; i < HOURS_TESTS.length; i++){ if(HOURS_TESTS[i].test(t)) return true; }
  return false;
}
function first(v){ return Array.isArray(v) ? v[0] : v; }
function safeShot(d){
  var s = d && d.screenshot && d.screenshot.url;
  if(typeof s !== "string") return "";
  try {
    var u = new URL(s);
    if(u.protocol === "https:" && /(^|\.)microlink\.io$/.test(u.hostname)) return u.href;
  } catch(e){}
  return "";
}

function scoreIt(j, url, ms){
  var d = j.data;
  var answered = j.statusCode !== null && j.statusCode !== undefined && j.statusCode !== "" && isFinite(Number(j.statusCode)) && Number(j.statusCode) > 0;
  var code = answered ? Number(j.statusCode) : NaN;
  var finalUrl = typeof d.url === "string" && d.url ? d.url : url;
  var tel = d.tel; tel = Array.isArray(tel) ? tel : (tel ? [tel] : []);
  var pass = {
    loads: code >= 200 && code < 300,
    https: answered && /^https:\/\//i.test(finalUrl),
    phone: /width\s*=\s*device-width/i.test(String(first(d.viewport) || "")),
    call: tel.some(function(t){ return /^tel:\s*\+?[\d\s().\-]{7,}/i.test(String(t)); }),
    hours: hasHours(d.text)
  };
  d.text = null; /* page text is dropped right after the hours search */
  var secs = Math.max(0.1, Math.round(ms / 100) / 10);
  var speedPts = ms <= 5000 ? WEIGHTS.speed : (ms <= 10000 ? WEIGHTS.speed / 2 : 0);
  if(!pass.loads){ pass.phone = pass.call = pass.hours = false; speedPts = 0; }
  var pts = {}, total = 0;
  ORDER.forEach(function(k){
    pts[k] = k === "speed" ? speedPts : (pass[k] ? WEIGHTS[k] : 0);
    total += pts[k];
  });
  pass.speed = speedPts === WEIGHTS.speed;
  return {score: total, pass: pass, pts: pts, secs: secs, loaded: pass.loads, answered: answered, shot: pass.loads ? safeShot(d) : "", finalUrl: finalUrl, code: isFinite(code) ? code : null};
}

/* ---------- plain lines: the symptom, never the fix ---------- */
function secText(s){ return "about " + (s >= 10 ? Math.round(s) : s) + " seconds"; }
function linesFor(r){
  var bad = {
    loads: "Your site address did not work when I checked it.",
    call: "There is no button that calls you when someone taps it on a phone.",
    phone: "On a phone the page comes up shrunk like a desktop page, so the words are tiny.",
    hours: "I could not find your hours on the page.",
    https: "Your site shows as not secure in the address bar.",
    speed: "It took " + secText(r.secs) + " to open when I checked it."
  };
  var good = {
    loads: "Your site opened fine when I checked it.",
    call: "There is a button that calls you when someone taps it on a phone.",
    phone: "Your site is set up to fit a phone screen.",
    hours: "Your hours are on the page.",
    https: "The address is secure and starts with https.",
    speed: "It opened in " + secText(r.secs) + " when I checked it."
  };
  if(!r.answered){
    return [
      {bad:true, text:bad.loads},
      {bad:true, text:"Nothing came back from the address, so I could not see your call button or your hours."},
      {bad:true, text:"I could not tell how it looks on a phone or whether it is secure."}
    ];
  }
  if(!r.loaded){
    return [
      {bad:true, text:bad.loads},
      {bad:!r.pass.https, text:r.pass.https ? good.https : bad.https},
      {bad:true, text:"Because the page did not open, I could not see your call button, hours or how it fits a phone."}
    ];
  }
  var out = [];
  ORDER.forEach(function(k){ if(!r.pass[k]) out.push({bad:true, text:bad[k]}); });
  ORDER.forEach(function(k){ if(r.pass[k]) out.push({bad:false, text:good[k]}); });
  return out.slice(0, 3);
}
function breakdownFor(r){
  return ORDER.map(function(k){
    var said;
    if(k === "speed") said = r.loaded ? secText(r.secs) : "Not checked";
    else if(!r.loaded && k !== "loads" && (k !== "https" || !r.answered)) said = "Not checked";
    else said = r.pass[k] ? "Yes" : "No";
    return {key:k, name:NAMES[k], said:said, pts:r.pts[k], max:WEIGHTS[k]};
  });
}

/* ---------- Web3Forms ---------- */
function sendW3F(subject, fields){
  var data = {access_key:W3F_KEY, subject:subject, from_name:"Granite City Digital website", botcheck:false};
  for(var k in fields) data[k] = fields[k];
  var ctrl = window.AbortController ? new AbortController() : null, timer = ctrl ? setTimeout(function(){ ctrl.abort(); }, 20000) : 0;
  return fetch("https://api.web3forms.com/submit", {method:"POST", headers:{"Content-Type":"application/json", "Accept":"application/json"}, body:JSON.stringify(data), keepalive:true, signal: ctrl ? ctrl.signal : undefined})
    .then(function(r){ return r.json().then(function(j){ return {ok:r.ok, j:j}; }, function(){ return {ok:false, j:null}; }); })
    .then(function(res){ clearTimeout(timer); return !!(res.ok && res.j && res.j.success === true); })
    .catch(function(){ clearTimeout(timer); return false; });
}

/* ---------- visitor leaves during the automatic check: send the request anyway ----------
   One pending job per submission. The beacon goes out at most once, and when it has gone
   out the normal send is skipped. FormData body, no custom headers, so no preflight. */
var job = null;
function leftEarly(e){
  if(e && e.type === "visibilitychange" && document.visibilityState !== "hidden") return;
  if(!job || job.done || job.beaconed || !navigator.sendBeacon || !window.FormData) return;
  var fd = new FormData();
  fd.append("access_key", W3F_KEY);
  fd.append("subject", "Free check tool: " + job.biz);
  fd.append("from_name", "Granite City Digital website");
  fd.append("business", job.biz);
  fd.append("website", job.site);
  fd.append("phone", job.phone || "Not given");
  fd.append("check", "Visitor left during the automatic check");
  var queued = false;
  try { queued = navigator.sendBeacon("https://api.web3forms.com/submit", fd); } catch(err){ queued = false; }
  if(queued) job.beaconed = true;
}
window.addEventListener("pagehide", leftEarly);
document.addEventListener("visibilitychange", leftEarly);

/* ---------- page states ---------- */
function setSending(on, label){
  var b = form.querySelector('button[type="submit"]'), l = b.querySelector(".lbl");
  if(!b.dataset.label) b.dataset.label = l.textContent;
  b.disabled = on; form.setAttribute("aria-busy", on ? "true" : "false");
  var s = b.querySelector(".spin");
  if(on){ if(!s){ s = document.createElement("span"); s.className = "spin"; s.setAttribute("aria-hidden", "true"); b.insertBefore(s, l); } l.textContent = label || "Sending"; }
  else { if(s) s.remove(); l.textContent = b.dataset.label; waitBox.textContent = ""; }
}
function showErr(msg, withContact){
  errBox.textContent = msg;
  if(withContact){
    errBox.appendChild(document.createTextNode(" Try again, or text "));
    var a = document.createElement("a"); a.href = "sms:+17432220985"; a.textContent = "(743) 222-0985"; errBox.appendChild(a);
    errBox.appendChild(document.createTextNode(" or email "));
    var m = document.createElement("a"); m.href = "mailto:lathan@granitecitydigital.me"; m.textContent = "lathan@granitecitydigital.me"; errBox.appendChild(m);
    errBox.appendChild(document.createTextNode(" and I'll take it from there."));
  }
  errBox.hidden = false;
}
function bad(input, msg){ showErr(msg, false); input.setAttribute("aria-invalid", "true"); input.focus(); }
function pickSample(biz){
  for(var i = 0; i < SAMPLES.length; i++){ if(SAMPLES[i][0].test(biz)) return SAMPLES[i]; }
  return DEFAULT_SAMPLE;
}
function prettySite(href){
  try { var u = new URL(href); return (u.hostname.replace(/^www\./, "") + (u.pathname === "/" ? "" : u.pathname)).slice(0, 80); } catch(e){ return href; }
}
function countUp(el, to){
  if(reduced || !window.requestAnimationFrame){ el.textContent = String(to); return; }
  var t0 = null, dur = 700;
  function step(t){
    if(t0 === null) t0 = t;
    var p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 4);
    el.textContent = String(Math.round(to * e));
    if(p < 1) requestAnimationFrame(step);
  }
  el.textContent = "0";
  requestAnimationFrame(step);
}
function reveal(el){
  el.hidden = false;
  el.classList.remove("in"); void el.offsetWidth; el.classList.add("in");
  el.focus({preventScroll:true});
  el.scrollIntoView({behavior: reduced ? "auto" : "smooth", block:"start"});
}

function renderResult(r, biz, site, sent){
  $("fc-site").textContent = prettySite(site);
  var lines = $("fc-lines"); lines.textContent = "";
  linesFor(r).forEach(function(x){
    var li = document.createElement("li"); li.className = x.bad ? "is-bad" : "is-good"; li.textContent = x.text; lines.appendChild(li);
  });
  var br = $("fc-break"); br.textContent = "";
  breakdownFor(r).forEach(function(x){
    var li = document.createElement("li");
    var n = document.createElement("span"); n.textContent = x.name;
    var s = document.createElement("span"); s.className = "said"; s.textContent = x.said;
    var p = document.createElement("b"); p.textContent = x.pts + " of " + x.max;
    li.appendChild(n); li.appendChild(s); li.appendChild(p); br.appendChild(li);
  });
  var theirs = $("fc-theirs"); theirs.textContent = "";
  function noPic(msg){ var p = document.createElement("p"); p.className = "nopic"; p.textContent = msg; theirs.textContent = ""; theirs.appendChild(p); }
  if(r.shot){
    var img = new Image();
    img.referrerPolicy = "no-referrer";
    img.alt = "Phone view of the site for " + biz;
    img.width = 393; img.height = 736; img.decoding = "async";
    img.onerror = function(){ noPic("The picture of your site did not come back."); };
    img.src = r.shot;
    theirs.appendChild(img);
  } else {
    noPic(r.loaded ? "The picture of your site did not come back." : "No picture, because the page did not open.");
  }
  var sm = pickSample(biz);
  $("fc-ours").src = "/work/shots/" + sm[1] + ".webp";
  $("fc-ours").alt = "Phone view of one of my samples, a site for " + sm[2];
  $("fc-ours-link").href = "/designs/" + sm[1] + "/";
  var note = $("fc-sentnote"); note.textContent = "";
  if(sent){ note.textContent = "Your details reached me too, so I can follow up."; }
  else {
    note.className = "fc-sentnote warn";
    note.appendChild(document.createTextNode("Your details didn't reach me this time, so text me at "));
    var a = document.createElement("a"); a.href = "sms:+17432220985"; a.textContent = "(743) 222-0985"; note.appendChild(a);
    note.appendChild(document.createTextNode(" and I'll take it from there."));
  }
  form.hidden = true;
  $("fc-done-site").textContent = prettySite(site);
  $("fc-done").hidden = false;
  var res = $("fc-result");
  reveal(res);
  countUp($("fc-num"), r.score);
}
function renderManual(reason, hasPhone){
  var why = $("fc-manual-why");
  var msg = "";
  if(/facebook|login/i.test(reason)) msg = "Facebook and Instagram pages need a login to see, so the automatic check can't open them.";
  else if(!/switched off/.test(reason)) msg = "The automatic check couldn't run this time.";
  why.textContent = msg; why.hidden = !msg;
  $("fc-manual-nophone").hidden = !!hasPhone;
  form.hidden = true;
  var m = $("fc-manual");
  m.hidden = false; m.focus();
}
function resetAll(){
  if(job) job.done = true;
  job = null;
  form.reset(); form.hidden = false; errBox.hidden = true;
  ["fc-result", "fc-manual", "fc-done"].forEach(function(id){ $(id).hidden = true; });
  var note = $("fc-sentnote"); note.className = "fc-sentnote";
  window.scrollTo({top:0, behavior: reduced ? "auto" : "smooth"});
  form.elements.biz.focus({preventScroll:true});
}
Array.prototype.forEach.call(document.querySelectorAll(".fc-again"), function(b){ b.addEventListener("click", resetAll); });
Array.prototype.forEach.call(form.querySelectorAll("input"), function(i){ i.addEventListener("input", function(){ i.removeAttribute("aria-invalid"); errBox.hidden = true; }); });

form.addEventListener("submit", function(e){
  e.preventDefault();
  if(busy) return;
  errBox.hidden = true;
  if(form.elements.botcheck && form.elements.botcheck.checked) return;
  var biz = form.elements.biz.value.trim();
  var rawSite = form.elements.site.value.trim();
  var phone = form.elements.phone.value.trim();
  if(!biz) return bad(form.elements.biz, "Type your business name.");
  if(!rawSite) return bad(form.elements.site, "Type your website address or your Facebook page link.");
  var site = normalizeUrl(rawSite);
  if(!site) return bad(form.elements.site, "That doesn't look like a website address. Try something like yourbusiness.com, or paste your Facebook page link.");
  if(!phoneOk(phone)) return bad(form.elements.phone, "That phone number looks short or long. Check it, or leave it empty.");

  busy = true;
  var walled = loginWalled(site);
  var auto = AUTO_CHECK && !walled && !blockedToday();
  setSending(true, auto ? "Checking your site" : "Sending");
  waitBox.textContent = auto ? "Looking at your site on a phone. This can take up to 25 seconds." : "";
  var mine = auto ? (job = {biz:biz, site:site, phone:phone, beaconed:false, done:false}) : null;
  var checking = walled ? Promise.resolve({ok:false, reason:"Facebook or Instagram page (behind a login)"}) : runCheck(site);

  checking.then(function(chk){
    if(auto) waitBox.textContent = "Sending it to me.";
    var fields = {business:biz, website:site, phone:phone || "Not given"};
    if(chk.ok){
      var r = chk.result;
      fields.check = "Automatic";
      fields.score = r.score + " out of 100";
      fields.results = linesFor(r).map(function(x){ return x.text; }).join(" | ");
      fields.checks = breakdownFor(r).map(function(x){ return x.name + ": " + x.said + " (" + x.pts + "/" + x.max + ")"; }).join(", ");
      fields.final_address = r.finalUrl;
      fields.screenshot = r.shot || "none";
    } else {
      fields.check = "By hand. Automatic check skipped: " + chk.reason;
    }
    var sending;
    if(mine && mine.beaconed){ sending = Promise.resolve(true); }
    else { if(mine) mine.done = true; sending = sendW3F("Free check tool: " + biz, fields); }
    return sending.then(function(sent){
      busy = false;
      setSending(false);
      if(chk.ok){ renderResult(chk.result, biz, site, sent); }
      else if(sent){ renderManual(chk.reason, !!phone); }
      else { showErr("That didn't go through, and everything you typed is still here.", true); }
    });
  }).catch(function(){
    if(mine) mine.done = true;
    busy = false; setSending(false);
    showErr("That didn't go through, and everything you typed is still here.", true);
  });
});
})();
