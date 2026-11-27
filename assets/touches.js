/* Granite City Digital: the moving strips, the hub and the corner Messenger button. Loaded after nav.js on the pages that use them. */

/* ---------- moving strips (the sample showreel and the Instagram reel strip) ----------
   Without this script, or with reduce motion, a strip is a plain row that scrolls sideways (touches.css). Here it becomes a
   slow moving strip: the row is copied enough times to close the loop (the copies are hidden from screen readers and the
   keyboard), and it moves by transform only. It rests under a mouse, while a tile has keyboard focus, off screen and in a
   hidden tab. It can be dragged with a mouse or a finger and swiped sideways on a trackpad; a drag never opens a tile. */
(function(){
  if(!window.requestAnimationFrame || !document.querySelectorAll) return;
  var calm = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  if(calm.matches) return;
  Array.prototype.forEach.call(document.querySelectorAll('[data-mq]'), function(win){ start(win, 0); });

  function start(win, tries){
    var track = win.querySelector('.mq-track');
    if(!track) return;
    /* Safari can run this file before the style sheet applies: wait until the track is the flex row */
    if(getComputedStyle(track).display !== 'flex'){
      if(tries < 300) requestAnimationFrame(function(){ start(win, tries + 1); });
      return;
    }
    var reals = Array.prototype.slice.call(track.children);
    if(!reals.length) return;
    var speed = parseFloat(win.getAttribute('data-speed')) || 30; /* px a second */
    var pos = 0, period = 0, raf = 0, last = 0;
    var hover = false, focus = false, drag = false, seen = !('IntersectionObserver' in window);

    function copy(li){
      var c = li.cloneNode(true);
      c.classList.add('mq-copy');
      c.setAttribute('aria-hidden', 'true');
      Array.prototype.forEach.call(c.querySelectorAll('a,button'), function(a){ a.setAttribute('tabindex', '-1'); });
      Array.prototype.forEach.call(c.querySelectorAll('[id]'), function(n){ n.removeAttribute('id'); });
      return c;
    }
    /* one period is the real row plus one gap; copies are added until the row covers the window plus one period */
    function fill(){
      var first = reals[0], end = reals[reals.length - 1];
      var gap = parseFloat(getComputedStyle(track).columnGap) || 0;
      var w = end.offsetLeft + end.offsetWidth - first.offsetLeft + gap;
      if(!(w > 0)){ period = 0; return; }
      period = w;
      var need = Math.ceil(win.clientWidth / w) + 1;
      var have = Math.round(track.children.length / reals.length) - 1;
      for(var s = have; s < need; s++){
        for(var i = 0; i < reals.length; i++) track.appendChild(copy(reals[i]));
      }
    }
    function wrap(){ if(period > 0){ pos %= period; if(pos < 0) pos += period; } }
    function apply(){ track.style.transform = 'translate3d(' + (-pos).toFixed(2) + 'px,0,0)'; }
    function running(){ return seen && !document.hidden && !hover && !focus && !drag && period > 0; }
    function frame(t){
      raf = 0;
      if(!running()){ last = 0; return; }
      var dt = last ? Math.min(t - last, 64) : 0;
      last = t;
      pos += speed * dt / 1000;
      wrap(); apply();
      raf = requestAnimationFrame(frame);
    }
    function wake(){ if(!raf && running()){ last = 0; raf = requestAnimationFrame(frame); } }

    win.scrollLeft = 0;
    win.classList.add('is-live');
    fill();
    apply();

    /* a mouse rests it; a finger does not (a tap leaves no hover behind) */
    win.addEventListener('pointerenter', function(e){ if(e.pointerType === 'mouse') hover = true; });
    win.addEventListener('pointerleave', function(e){ if(e.pointerType === 'mouse'){ hover = false; wake(); } });

    /* keyboard focus rests it and brings the focused tile into view (a mouse press also focuses a tile, and that must not hold the strip) */
    win.addEventListener('focusin', function(e){
      var key = true;
      try { key = e.target.matches(':focus-visible'); } catch(err){}
      if(!key) return;
      focus = true;
      var li = e.target.closest ? e.target.closest('.mq-item') : null;
      if(li && period > 0){
        win.scrollLeft = 0;
        pos = li.offsetLeft - Math.max(0, (win.clientWidth - li.offsetWidth) / 2);
        if(pos < 0) pos = 0;
        wrap(); apply();
      }
    });
    win.addEventListener('focusout', function(e){
      if(!e.relatedTarget || !win.contains(e.relatedTarget)){ focus = false; wake(); }
    });
    /* the strip never scrolls on its own box: a browser that scrolls it to show a focused tile is put back */
    win.addEventListener('scroll', function(){ if(win.scrollLeft) win.scrollLeft = 0; });
    /* a mouse press on a copy must not focus it, or screen readers would hear the tiles twice */
    win.addEventListener('mousedown', function(e){
      if(e.target.closest && e.target.closest('.mq-copy a')) e.preventDefault();
    }, true);

    /* drag: starts after 6 px of sideways travel, so a plain click or tap still opens the tile */
    var pid = null, sx = 0, sp = 0, moved = false, dragEnd = 0;
    win.addEventListener('pointerdown', function(e){
      if(drag || (e.pointerType === 'mouse' && e.button !== 0)) return;
      pid = e.pointerId; sx = e.clientX; sp = pos; moved = false;
    });
    win.addEventListener('pointermove', function(e){
      if(e.pointerId !== pid) return;
      /* a mouse that moves with no button held is not dragging (its release may have happened outside the strip) */
      if(e.pointerType === 'mouse' && !(e.buttons & 1)){ endDrag(e); return; }
      var dx = e.clientX - sx;
      if(!moved){
        if(Math.abs(dx) < 6) return;
        moved = true; drag = true;
        win.classList.add('is-drag');
        try { win.setPointerCapture(pid); } catch(err){}
      }
      pos = sp - dx;
      wrap(); apply();
    });
    function endDrag(e){
      if(e.pointerId !== pid) return;
      pid = null;
      if(!drag) return;
      drag = false; dragEnd = Date.now();
      win.classList.remove('is-drag');
      try { win.releasePointerCapture(e.pointerId); } catch(err){}
      wake();
    }
    win.addEventListener('pointerup', endDrag);
    win.addEventListener('pointercancel', endDrag);
    win.addEventListener('lostpointercapture', endDrag);
    win.addEventListener('click', function(e){
      if(moved && Date.now() - dragEnd < 400){ e.preventDefault(); e.stopPropagation(); }
      moved = false;
    }, true);
    win.addEventListener('dragstart', function(e){ e.preventDefault(); });
    /* a sideways swipe on a trackpad moves it too; an up and down scroll is left alone */
    win.addEventListener('wheel', function(e){
      if(Math.abs(e.deltaX) <= Math.abs(e.deltaY) || !(period > 0)) return;
      e.preventDefault();
      pos += e.deltaX;
      wrap(); apply();
    }, { passive: false });

    if('IntersectionObserver' in window){
      new IntersectionObserver(function(en){ seen = en[en.length - 1].isIntersecting; wake(); }).observe(win);
    }
    document.addEventListener('visibilitychange', wake);
    var rt = 0;
    window.addEventListener('resize', function(){
      clearTimeout(rt);
      rt = setTimeout(function(){ fill(); wrap(); apply(); wake(); }, 150);
    }, { passive: true });
    wake();
  }
})();

/* ---------- hub: six points around "Your website" ----------
   Each point is a button with aria-expanded. One reason is open at a time; pressing the open one closes it.
   Without this script every reason stays open (touches.css). */
(function(){
  var map = document.querySelector('[data-hub]');
  if(!map || !map.classList) return;
  var points = Array.prototype.slice.call(map.querySelectorAll('.hub-point'));
  if(!points.length) return;
  function set(li, open){
    var b = li.querySelector('.hub-btn');
    li.classList.toggle('is-open', open);
    if(b) b.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  points.forEach(function(li, i){
    var b = li.querySelector('.hub-btn');
    set(li, i === 0);
    if(!b) return;
    b.addEventListener('click', function(){
      var was = li.classList.contains('is-open');
      points.forEach(function(o){ if(o !== li) set(o, false); });
      set(li, !was);
    });
  });
  map.classList.add('hub-live');
})();

/* ---------- corner Messenger button: it steps aside instead of covering things ----------
   The same manners as the floating bar in nav.js. Its spot is the place it rests in, plus 8 px around it and 24 px below
   (sections glide up as much as 24 px into place). While a link, button, field, question row, form, service card or moving
   strip is in that spot, or the button would touch the floating bar, it is away (touches.css .is-away). On phones and touch
   screens it is also away while a form field has focus. It comes back only when the spot has been clear for 400 ms and
   the page has not scrolled for 250 ms. Until the first look has run it is invisible. Keyboard focus on it keeps it there. */
(function(){
  var fab = document.querySelector('.fab-msg');
  if(!fab || !fab.getBoundingClientRect || !window.requestAnimationFrame) return;
  var fb = document.querySelector('.fbar'), fpanel = fb && fb.querySelector('.fbar-panel');
  var CTRL = 'a[href],button,input:not([type=hidden]),select,textarea,summary,form,[role=button],[tabindex]:not([tabindex="-1"]),.service-card,.mq';
  var GAP = 8, RISE = 24, BAR_GAP = 16, CLEAR_MS = 400, STILL_MS = 250;
  var docEl = document.documentElement;
  var small = window.matchMedia ? window.matchMedia('(max-width:767px), (pointer:coarse)') : { matches: false };
  var phone = window.matchMedia ? window.matchMedia('(max-width:767px)') : { matches: false };
  var ready = false, away = false, clearAt = 0, scrollAt = 0, backT = 0, tick = 0, tries = 0;

  /* the button's resting box, whatever fade or press is running: its layout size around its centre */
  function box(){
    var r = fab.getBoundingClientRect();
    var w = fab.offsetWidth, h = fab.offsetHeight;
    if(!w || !h) return null;
    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    return { l: cx - w / 2, r: cx + w / 2, t: cy - h / 2, b: cy + h / 2 };
  }
  function inSpot(c, s){
    if(c === fab || (fb && fb.contains(c))) return false;
    var r = c.getBoundingClientRect();
    var x1 = Math.max(r.left, s.l), y1 = Math.max(r.top, s.t), x2 = Math.min(r.right, s.r), y2 = Math.min(r.bottom, s.b);
    if(x2 <= x1 || y2 <= y1) return false;
    if(c.closest && c.closest('.site-header')) return false;
    if(c.checkVisibility && !c.checkVisibility()) return false;
    if(getComputedStyle(c).visibility !== 'visible') return false;
    for(var a = c.parentElement; a && a !== docEl; a = a.parentElement){
      var cs = getComputedStyle(a);
      if(cs.overflowX !== 'visible' || cs.overflowY !== 'visible'){
        var q = a.getBoundingClientRect();
        x1 = Math.max(x1, q.left); y1 = Math.max(y1, q.top); x2 = Math.min(x2, q.right); y2 = Math.min(y2, q.bottom);
        if(x2 <= x1 || y2 <= y1) return false;
      }
      if(cs.position === 'fixed') break;
    }
    return true;
  }
  function spotTaken(s){
    var list = document.querySelectorAll(CTRL);
    for(var i = 0; i < list.length; i++){ if(inSpot(list[i], s)) return true; }
    return false;
  }
  /* the floating bar's resting box (the call bar on phones), shown or stepped aside, whatever fade or entrance is running.
     Nothing when the bar is not laid out, or closed for the visit on a laptop. */
  function bar(){
    if(!fpanel || !fpanel.getClientRects().length) return null;
    if(fb.classList.contains('dismissed') && !phone.matches) return null;
    var r = fpanel.getBoundingClientRect(), dx = 0, dy = 0;
    var m = /^matrix(3d)?\((.+)\)$/.exec(getComputedStyle(fb).transform || '');
    if(m){ var v = m[2].split(','); dx = parseFloat(v[m[1] ? 12 : 4]) || 0; dy = parseFloat(v[m[1] ? 13 : 5]) || 0; }
    return { l: r.left - dx, r: r.right - dx, t: r.top - dy, b: r.bottom - dy };
  }
  /* where the bar reaches the button's corner, the button is set 16 px above the bar's measured top edge, so the two never
     touch and the bar never counts the button as something in its own spot (touches.css holds the same places as a start) */
  function place(){
    var b = box(), r = bar(), want = '';
    if(b && r && r.r + 12 > b.l){
      var cur = parseFloat(getComputedStyle(fab).bottom);
      if(cur === cur) want = (Math.round((cur + b.b - (r.t - BAR_GAP)) * 100) / 100) + 'px';
    }
    if(fab.style.bottom !== want) fab.style.bottom = want;
  }
  function onBar(b){
    var r = bar();
    return !!r && !(b.r <= r.l || b.l >= r.r || b.b <= r.t || b.t >= r.b);
  }
  function typing(){
    var a = document.activeElement;
    return !!(small.matches && a && a.matches && a.matches('input,textarea,select') && a.closest('form'));
  }
  function keyOnIt(){
    if(document.activeElement !== fab) return false;
    try { return fab.matches(':focus-visible'); } catch(err){ return false; }
  }
  function setAway(on){
    if(on === away) return;
    away = on;
    fab.classList.toggle('is-away', on);
  }
  function check(){
    tick = 0;
    /* wait until the style sheet has made it the fixed button */
    if(!ready && getComputedStyle(fab).position !== 'fixed'){ if(tries++ < 300) soon(); return; }
    place();
    var b = box();
    var busy = !b || typing() || onBar(b) || spotTaken({ l: b.l - GAP, r: b.r + GAP, t: b.t - GAP, b: b.b + RISE });
    if(!ready){
      ready = true; away = busy;
      if(busy) fab.classList.add('is-away');
      fab.classList.add('is-ready');
      return;
    }
    if(busy){
      if(!away && keyOnIt()) return;
      clearAt = 0; setAway(true); return;
    }
    if(!away) return;
    var t = Date.now();
    if(!clearAt) clearAt = t;
    var wait = Math.max(clearAt + CLEAR_MS, scrollAt + STILL_MS) - t;
    if(wait <= 0){ setAway(false); return; }
    clearTimeout(backT);
    backT = setTimeout(check, wait + 16);
  }
  function soon(){ if(!tick) tick = requestAnimationFrame(check); }
  /* capture: a row scrolled sideways moves its tiles too, and that scroll does not bubble */
  window.addEventListener('scroll', function(){ scrollAt = Date.now(); soon(); }, { passive: true, capture: true });
  window.addEventListener('resize', soon, { passive: true });
  window.addEventListener('orientationchange', soon);
  document.addEventListener('focusin', function(){ if(ready && typing()) check(); else soon(); });
  document.addEventListener('focusout', soon);
  /* a press can open a row, a point or the bar's X: look on the next frame and again once it has settled */
  document.addEventListener('click', function(){ soon(); setTimeout(soon, 350); }, true);
  document.addEventListener('toggle', soon, true);
  /* content that glides or opens into place is looked at again where it lands */
  document.addEventListener('transitionend', function(e){
    var p = e.propertyName;
    if(e.target !== fab && (p === 'transform' || p === 'translate' || p === 'grid-template-rows')) soon();
  }, true);
  document.addEventListener('animationend', function(e){ if(e.target !== fab) soon(); }, true);
  window.addEventListener('load', soon);
  window.addEventListener('pageshow', soon);
  if(document.fonts && document.fonts.ready && document.fonts.ready.then) document.fonts.ready.then(soon);
  if('ResizeObserver' in window) new ResizeObserver(soon).observe(document.body);
  check();
})();
