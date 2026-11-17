/* Granite City Digital: top bar menu, Services dropdown, phone menu, floating bar (its X and how it steps aside) and hero pause. Loaded on every page. */

/* ---------- sections glide in on a timer, once ----------
   One .reveal block per section. In one step this script hides the blocks below the screen (html.rv-on) and marks every
   block already on screen as shown, so nothing on the first screen ever blinks. A block glides in (CSS: .9 s, 24 px) when
   about 10% of it is on screen or its top is 15% of the screen above the bottom edge, whichever comes first, and anything
   still hidden on screen when scrolling stops glides in too. Nothing replays. Anchor jumps, keyboard focus and printing
   show blocks at once. No script, no IntersectionObserver, reduce motion, or a return by Back or reload: nothing is hidden. */
(function(){
  var root = document.documentElement;
  if(!('IntersectionObserver' in window) || !root.classList) return;
  if(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  try {
    var nav = performance.getEntriesByType('navigation')[0];
    if(nav && (nav.type === 'back_forward' || nav.type === 'reload')) return;
  } catch(err){}
  /* blocks that glide the same way without a class in the page: the footer, the home trust row, the /faq/ list (its side nav
     and each group), each part of the legal pages, the client portal form and side cards, the /get-started/ form section.
     Never one inside another block, so nothing moves twice. (The /contact/ form stays still: its first field is there at once.) */
  Array.prototype.forEach.call(document.querySelectorAll('.site-footer > .container, .trust > .container, .faq-body .faq-nav, .faq-body .faq-group, .legal-body .legal > *, .portal-layout > .form-card, .portal-side > *, #start > .container'), function(el){
    if(!el.closest('.reveal') && !el.querySelector('.reveal')) el.classList.add('reveal');
  });
  var blocks = Array.prototype.slice.call(document.querySelectorAll('.reveal'));
  if(!blocks.length) return;
  var left = blocks.length;
  function vh(){ return window.innerHeight || root.clientHeight; }
  function show(b, now){
    if(b.classList.contains('is-in')) return;
    if(now) b.classList.add('rv-now');
    b.classList.add('is-in');
    left--;
    near.unobserve(b); tenth.unobserve(b);
  }
  function onScreen(b){ var r = b.getBoundingClientRect(); return r.bottom > 0 && r.top < vh() && r.height > 0; }
  /* the blocks around an anchor target: the one holding it and any that share the screen with it once the jump lands */
  function showAround(t){
    if(!t || !t.getBoundingClientRect) return;
    var top = t.getBoundingClientRect().top, h = vh();
    blocks.forEach(function(b){
      var r = b.getBoundingClientRect();
      if(b.contains(t) || t.contains(b) || (r.bottom > top - h && r.top < top + h)) show(b, true);
    });
  }
  function target(hash){
    var id = (hash || '').slice(1);
    if(!id) return null;
    try { return document.getElementById(decodeURIComponent(id)); } catch(err){ return null; }
  }
  var pick = function(en){ en.forEach(function(e){ if(e.isIntersecting && (e.rootBounds === null || e.intersectionRatio > 0)) show(e.target); }); };
  var near = new IntersectionObserver(pick, { rootMargin: '0px 0px -15% 0px', threshold: 0 });
  var tenth = new IntersectionObserver(function(en){ en.forEach(function(e){ if(e.intersectionRatio >= 0.1) show(e.target); }); }, { threshold: 0.1 });
  /* first pass, before anything is hidden: what is on screen (or is the anchor being arrived at) stays as it is */
  var landing = target(location.hash);
  var keep = blocks.filter(onScreen);
  if(landing) showAround(landing);
  keep.forEach(function(b){ show(b, true); });
  /* the blocks being hidden go straight to their hidden state (no 0.9 s fade out), then get their glide back two frames later */
  var wait = blocks.filter(function(b){ return !b.classList.contains('is-in'); });
  wait.forEach(function(b){ b.classList.add('rv-now'); });
  root.classList.add('rv-on');
  requestAnimationFrame(function(){ requestAnimationFrame(function(){
    wait.forEach(function(b){ if(!b.classList.contains('is-in')) b.classList.remove('rv-now'); });
  }); });
  blocks.forEach(function(b){ if(!b.classList.contains('is-in')){ near.observe(b); tenth.observe(b); } });
  /* when scrolling stops, nothing on screen stays hidden, and a block that a fast scroll carried past the screen between two
     observer callbacks (now above it) is shown at once, so it is there when the reader scrolls back */
  var still = 0;
  function settle(){
    clearTimeout(still);
    if(left > 0) blocks.forEach(function(b){
      if(b.classList.contains('is-in')) return;
      if(onScreen(b)) show(b);
      else if(b.getBoundingClientRect().bottom <= 0) show(b, true);
    });
  }
  window.addEventListener('scroll', function(){ clearTimeout(still); still = setTimeout(settle, 80); }, { passive: true });
  window.addEventListener('scrollend', settle, { passive: true });
  window.addEventListener('resize', function(){ clearTimeout(still); still = setTimeout(settle, 100); }, { passive: true });
  /* same page anchor links and hash changes land on content that is already there */
  document.addEventListener('click', function(e){
    var a = e.target.closest && e.target.closest('a[href*="#"]');
    if(!a || a.origin !== location.origin || a.pathname !== location.pathname) return;
    showAround(target(a.hash));
  }, true);
  window.addEventListener('hashchange', function(){ showAround(target(location.hash)); });
  /* a link or field reached by Tab inside a hidden block shows at once */
  document.addEventListener('focusin', function(e){
    var b = e.target.closest && e.target.closest('.reveal');
    if(b) show(b, true);
  });
  window.addEventListener('beforeprint', function(){ blocks.forEach(function(b){ show(b, true); }); });
  window.addEventListener('load', function(){ setTimeout(settle, 50); });
})();

(function(){
  var h = document.querySelector('.site-header');
  if(!h) return;

  /* ---------- phone menu ---------- */
  var mb = h.querySelector('.menu-btn');
  function setMenu(o){
    h.classList.toggle('is-open', o);
    mb.setAttribute('aria-expanded', o ? 'true' : 'false');
    mb.setAttribute('aria-label', o ? 'Close menu' : 'Open menu');
  }
  if(mb){
    mb.addEventListener('click', function(){ setMenu(!h.classList.contains('is-open')); });
    h.addEventListener('click', function(e){ if(e.target.closest('.menu-panel a')) setMenu(false); });
    document.addEventListener('click', function(e){ if(h.classList.contains('is-open') && !h.contains(e.target)) setMenu(false); });
    /* Tab past the last row (or Shift Tab out of the top bar) closes it, the same rule as the Services dropdown,
       so keyboard focus never lands on the page hidden under the open panel */
    h.addEventListener('focusout', function(e){
      if(h.classList.contains('is-open') && e.relatedTarget && !h.contains(e.relatedTarget)) setMenu(false);
    });
  }

  /* phone menu: Services row expands its list */
  var sb = h.querySelector('.menu-sub-btn'), sub = sb && document.getElementById(sb.getAttribute('aria-controls'));
  if(sb && sub){
    sb.addEventListener('click', function(){
      var o = sb.getAttribute('aria-expanded') !== 'true';
      sb.setAttribute('aria-expanded', o ? 'true' : 'false');
      sub.hidden = !o;
    });
  }

  /* ---------- Services dropdown (top bar) ---------- */
  var dd = h.querySelector('[data-dd]'), btn = dd && dd.querySelector('.nav-dd-btn');
  var items = dd ? Array.prototype.slice.call(dd.querySelectorAll('.dd-item')) : [];
  var timer = 0, hoverOpenedAt = 0;
  function isOpen(){ return dd && dd.classList.contains('is-open'); }
  function setDd(o){
    if(!dd) return;
    clearTimeout(timer);
    dd.classList.toggle('is-open', o);
    btn.setAttribute('aria-expanded', o ? 'true' : 'false');
  }
  if(dd && btn){
    var fine = window.matchMedia('(hover:hover) and (pointer:fine)');
    dd.addEventListener('pointerenter', function(e){
      if(e.pointerType !== 'mouse' || !fine.matches) return;
      clearTimeout(timer);
      if(!isOpen()){ setDd(true); hoverOpenedAt = Date.now(); }
    });
    dd.addEventListener('pointerleave', function(e){
      if(e.pointerType !== 'mouse' || !fine.matches) return;
      clearTimeout(timer);
      /* the mouse left: close, even when a click left focus on the button; only focus placed by keyboard keeps it open */
      timer = setTimeout(function(){ var a = document.activeElement; if(!(dd.contains(a) && a.matches(':focus-visible'))) setDd(false); }, 140);
    });
    btn.addEventListener('click', function(){
      /* a click right after hover opened it keeps it open instead of closing it */
      if(isOpen() && Date.now() - hoverOpenedAt < 400){ hoverOpenedAt = 0; return; }
      setDd(!isOpen());
    });
    btn.addEventListener('keydown', function(e){
      if(e.key === 'ArrowDown'){ e.preventDefault(); setDd(true); if(items[0]) items[0].focus(); }
    });
    dd.addEventListener('keydown', function(e){
      if(e.key === 'Escape' && isOpen()){ e.preventDefault(); setDd(false); btn.focus(); return; }
      if(e.target === btn) return;
      var i = items.indexOf(document.activeElement);
      if(i < 0) return;
      if(e.key === 'ArrowDown'){ e.preventDefault(); items[(i + 1) % items.length].focus(); }
      else if(e.key === 'ArrowUp'){ e.preventDefault(); if(i === 0) btn.focus(); else items[i - 1].focus(); }
      else if(e.key === 'Home'){ e.preventDefault(); items[0].focus(); }
      else if(e.key === 'End'){ e.preventDefault(); items[items.length - 1].focus(); }
    });
    dd.addEventListener('focusout', function(e){
      if(isOpen() && (!e.relatedTarget || !dd.contains(e.relatedTarget))){
        /* leaving by keyboard closes it; a mouse still over the panel keeps it */
        if(!dd.matches(':hover')) setDd(false);
      }
    });
    document.addEventListener('click', function(e){ if(isOpen() && !dd.contains(e.target)) setDd(false); });
  }

  /* Escape closes whatever is open and returns focus to its button */
  document.addEventListener('keydown', function(e){
    if(e.key !== 'Escape') return;
    if(h.classList.contains('is-open')){ setMenu(false); mb.focus(); }
  });

  /* ---------- floating bar: the X closes it for this visit ----------
     Laptops hide the whole bar; phones hide only the line, so Call and Get my free preview stay.
     If storage is blocked the bar simply shows again on the next page. */
  var narrow = window.matchMedia('(max-width:767px)');
  var fb = document.querySelector('.fbar'), KEY = 'gcd-fbar-closed';
  var fpanel = fb && fb.querySelector('.fbar-panel');
  if(fb){
    var stored = false;
    try { stored = window.sessionStorage.getItem(KEY) === '1'; } catch(err){}
    if(stored) fb.classList.add('dismissed');
    var x = fb.querySelector('.fbar-x');
    if(x){
      x.addEventListener('click', function(ev){
        /* keep keyboard focus on the bar when the X disappears */
        var next = fb.querySelector('.fbar-actions .btn-primary');
        var byKey = ev.detail === 0 || (x.matches && x.matches(':focus-visible'));
        fb.classList.add('dismissed');
        try { window.sessionStorage.setItem(KEY, '1'); } catch(err){}
        if(next && narrow.matches){ next.focus(); return; }
        /* laptops: the whole bar is gone, so focus goes to the last link before it (the footer),
           and the next Tab carries on from there instead of starting over at the top */
        var all = document.querySelectorAll('a[href], button:not([disabled]), input:not([type=hidden]):not([disabled]), select, textarea, summary, [tabindex]:not([tabindex="-1"])');
        for(var i = all.length - 1; i >= 0; i--){
          var el = all[i];
          if(!(el.compareDocumentPosition(fb) & Node.DOCUMENT_POSITION_FOLLOWING)) continue;
          if(el.closest('[inert],[hidden]') || !el.getClientRects().length || getComputedStyle(el).visibility === 'hidden') continue;
          /* a mouse click never scrolls; by keyboard, a link far off screen is brought into view */
          el.focus({ preventScroll: true });
          if(byKey){
            var lr = el.getBoundingClientRect();
            if(lr.top < 0 || lr.bottom > window.innerHeight){
              /* centre, not nearest: the page gets shorter once the bar's room at the bottom goes away */
              try { el.scrollIntoView({ block: 'center', behavior: 'instant' }); } catch(err){ el.scrollIntoView(false); }
            }
          }
          break;
        }
      });
    }
  }

  /* ---------- floating bar: it steps aside instead of covering things ----------
     Its spot is the place the panel rests in when shown, plus 8 px above it. While a link, button, field, question row or a
     form's own box is in that spot, or the visitor has focus in a form field, the bar is away (gcd.css .is-away: a calm fade,
     no clicks from the first frame, hidden from the keyboard and screen readers once faded). It comes back only when the spot
     has been clear for 400 ms and the page has not scrolled for 250 ms, so it stays away through one long scroll instead of
     blinking and returns once the reader rests on a clear place. Until the first check has run the bar is invisible
     (gcd.css), so it never flashes over a button while the page loads; when the spot is clear at that first check it rises in
     as it always has. Keyboard focus inside the bar keeps it where it is. The X is separate: .dismissed, above.
     Each check is one pass of reads and at most one class change, never more than one a frame. */
  if(fb && fpanel){
    var CTRL = 'a[href],button,input:not([type=hidden]),select,textarea,summary,form,[role=button],[tabindex]:not([tabindex="-1"])';
    var GAP = 8, RISE = 24, CLEAR_MS = 400, STILL_MS = 250;
    var docEl = document.documentElement;
    var ready = false, away = false, clearAt = 0, scrollAt = 0, backT = 0, tick = 0, tries = 0;
    /* the panel's resting box, whatever fade, slide or entrance is running: its box now, less the bar's own shift, with
       8 px more above. It also reaches 24 px below the panel: sections glide up as much as 24 px into place, so a button
       that is still that far under the bar is about to land beneath it. Nothing when the bar is not laid out (phones on /get-started/). */
    function spot(){
      if(!fpanel.getClientRects().length) return null;
      var r = fpanel.getBoundingClientRect(), dx = 0, dy = 0;
      var m = /^matrix(3d)?\((.+)\)$/.exec(getComputedStyle(fb).transform || '');
      if(m){ var v = m[2].split(','); dx = parseFloat(v[m[1] ? 12 : 4]) || 0; dy = parseFloat(v[m[1] ? 13 : 5]) || 0; }
      return { l: r.left - dx, r: r.right - dx, t: r.top - dy - GAP, b: r.bottom - dy + RISE };
    }
    /* is a part of this control that a visitor can see inside the spot? Its box is cut by every clipping parent, so a card
       scrolled out of a strip or a link in a closed question row does not count. When unsure it counts: a wrong yes only
       hides the bar, a wrong no would cover a button. */
    function inSpot(c, s){
      var r = c.getBoundingClientRect();
      var x1 = Math.max(r.left, s.l), y1 = Math.max(r.top, s.t), x2 = Math.min(r.right, s.r), y2 = Math.min(r.bottom, s.b);
      if(x2 <= x1 || y2 <= y1) return false;
      if(fb.contains(c) || c.closest('.site-header, .menu-panel')) return false;
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
    /* focus in a form field: the visitor is already doing what the bar asks for */
    function typing(){
      var a = document.activeElement;
      return !!(a && a.matches && a.matches('input,textarea,select') && a.closest('form') && !fb.contains(a));
    }
    function keyInBar(){
      var a = document.activeElement;
      if(!a || !fb.contains(a)) return false;
      try { return a.matches(':focus-visible'); } catch(err){ return false; }
    }
    function setAway(on){
      if(on === away) return;
      away = on;
      if(on) fb.classList.remove('is-entering');
      fb.classList.toggle('is-away', on);
    }
    function check(){
      tick = 0;
      /* Safari can run this file before the style sheet applies: wait until the bar is the fixed bar */
      if(!ready && getComputedStyle(fb).position !== 'fixed'){ if(tries++ < 300) soon(); return; }
      var s = spot();
      var busy = !s || typing() || spotTaken(s);
      if(!ready){
        ready = true; away = busy;
        fb.classList.add('is-ready', busy ? 'is-away' : 'is-entering');
        return;
      }
      if(busy){
        /* keyboard focus inside a bar that is showing keeps it: it never goes away under the focused link */
        if(!away && keyInBar()) return;
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
    /* capture: a strip scrolled sideways moves its cards too, and that scroll does not bubble */
    window.addEventListener('scroll', function(){ scrollAt = Date.now(); soon(); }, { passive: true, capture: true });
    window.addEventListener('resize', soon, { passive: true });
    window.addEventListener('orientationchange', soon);
    /* a field takes focus: away at once, before the helper below looks at the bar */
    document.addEventListener('focusin', function(){ if(ready && typing()) check(); else soon(); });
    document.addEventListener('focusout', soon);
    /* a press can open a row or change a form step: look on the next frame and again once it has settled */
    document.addEventListener('click', function(){ soon(); setTimeout(soon, 350); }, true);
    document.addEventListener('toggle', soon, true);
    /* content that glides into place (sections arriving, the hero settling) is looked at again where it lands */
    document.addEventListener('transitionend', function(e){ if(e.propertyName === 'transform' && !fb.contains(e.target)) soon(); }, true);
    document.addEventListener('animationend', function(e){ if(e.target === fb) fb.classList.remove('is-entering'); else soon(); }, true);
    window.addEventListener('load', soon);
    window.addEventListener('pageshow', soon);
    if(document.fonts && document.fonts.ready && document.fonts.ready.then) document.fonts.ready.then(soon);
    if('ResizeObserver' in window) new ResizeObserver(soon).observe(document.body);
    check();
  }

  /* ---------- keep the focused field clear of the bottom bar ----------
     Chrome scrolls a text box only far enough to show its caret, so a tall box can stay half under the bar. */
  /* the bar on screen: /get-started/ has its Call and Text bar on phones and the floating bar on laptops.
     Checked when focus arrives and again once the browser's own (smooth) focus scroll has settled, since a field far down the
     page is only brought to the screen's bottom edge after the focus event. */
  var cbar = document.querySelector('.callbar');
  function clearOfBar(t){
    if(h.classList.contains('is-open') || document.activeElement !== t) return;
    var cb = cbar && cbar.getClientRects().length ? cbar : fpanel;
    if(!cb || !cb.getClientRects().length) return;
    if(!t.getBoundingClientRect || cb.contains(t)) return;
    /* a floating bar that has stepped aside is not there (it may still be fading) */
    if(cb === fpanel && fb.classList.contains('is-away')) return;
    var c = cb.getBoundingClientRect();
    if(c.height === 0 || getComputedStyle(cb === fpanel ? fb : cb).visibility === 'hidden') return;
    /* a radio or checkbox is a small hidden input inside its label: measure the label the visitor sees */
    var v = (t.type === 'radio' || t.type === 'checkbox') && t.closest ? (t.closest('label') || t) : t;
    var r = v.getBoundingClientRect();
    if(r.bottom > c.top - 8 && r.top < c.bottom){
      /* instant: Safari cuts a smooth scroll short while its own focus scroll runs; an older browser that does not know 'instant' throws,
         so the plain form follows with the page's smooth scrolling switched off for that one call */
      var d = r.bottom - c.top + 16;
      try { window.scrollBy({ top: d, behavior: 'instant' }); } catch(err){
        var hs = document.documentElement.style, was = hs.scrollBehavior;
        hs.scrollBehavior = 'auto'; window.scrollBy(0, d); hs.scrollBehavior = was;
      }
    }
  }
  if(cbar || fpanel){
    /* after focus arrives, the check runs again once scrolling has been still for 120 ms (for up to 2 s) */
    var settleFocus = 0, focusT = null, focusAt = 0;
    function again(){ clearTimeout(settleFocus); settleFocus = setTimeout(function(){ var t = focusT; focusT = null; if(t) clearOfBar(t); }, 120); }
    document.addEventListener('focusin', function(e){
      clearOfBar(e.target);
      focusT = e.target; focusAt = Date.now(); again();
    });
    window.addEventListener('scroll', function(){ if(focusT && Date.now() - focusAt < 2000) again(); }, { passive: true });
  }


  /* ---------- /get-started/ sample strip: a card that takes keyboard focus comes into view ----------
     The moving strip is paused while focused, so it is slid until the card sits in the middle;
     the still strip (reduced motion) scrolls the card into view instead. */
  var sw = document.querySelector('.strip-wrap'), st = sw && sw.querySelector('.strip');
  if(st){
    /* a mouse press on a card in the copy set (aria-hidden) must not focus it, or screen readers hear the 9 links twice */
    sw.addEventListener('mousedown', function(e){
      if(e.target.closest && e.target.closest('.strip-set[aria-hidden="true"] a')) e.preventDefault();
    }, true);
    sw.addEventListener('focusin', function(e){
      var card = (e.target.closest && e.target.closest('a')) || e.target;
      /* keyboard focus only: a mouse press also focuses the card, and sliding it then makes the click miss */
      if(!(card.matches && card.matches(':focus-visible'))) return;
      requestAnimationFrame(function(){
        var a = st.getAnimations ? st.getAnimations()[0] : null;
        if(a && a.effect){
          sw.scrollLeft = 0;
          var half = st.scrollWidth / 2, dur = Number(a.effect.getTiming().duration) || 0;
          var tx = new DOMMatrix(getComputedStyle(st).transform).m41;
          var r = card.getBoundingClientRect(), w = sw.getBoundingClientRect();
          var want = tx + (w.left + w.width / 2) - (r.left + r.width / 2);
          if(half > 0 && dur > 0) a.currentTime = Math.min(Math.max(-want / half, 0), 0.999) * dur;
        } else {
          card.scrollIntoView({ block: 'nearest', inline: 'center' });
        }
      });
    });
  }

  /* ---------- home hero: pause the light sweep when it is off screen ---------- */
  var hero = document.querySelector('.hero');
  if(hero && 'IntersectionObserver' in window){
    var seen = true;
    var sync = function(){ hero.classList.toggle('is-paused', !seen || document.hidden); };
    new IntersectionObserver(function(en){ seen = en[0].isIntersecting; sync(); }).observe(hero);
    document.addEventListener('visibilitychange', sync);
  }
})();

/* ---------- question lists: one answer open at a time on the page, rows glide open and shut ----------
   A press (mouse, Enter, Space) opens the row and closes the one that was open; both heights glide 200 ms ease out together
   while the pressed question is held still on screen, and a press during a glide turns it around from where it is.
   Reduce motion or no Web Animations: the rows switch at once, as before. No script: plain details. toggle catches any
   other open (for example find in page). */
(function(){
  var SEL = 'details.faq-item', MS = 200;
  var calm = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : { matches: false };
  var canGlide = typeof Element !== 'undefined' && !!Element.prototype.animate;
  function others(d){
    return Array.prototype.filter.call(document.querySelectorAll(SEL + '[open]'), function(o){ return o !== d && !o.classList.contains('is-closing'); });
  }
  function scrollFix(dy){
    try { window.scrollBy({ top: dy, behavior: 'instant' }); } catch(err){
      var hs = document.documentElement.style, was = hs.scrollBehavior;
      hs.scrollBehavior = 'auto'; window.scrollBy(0, dy); hs.scrollBehavior = was;
    }
  }
  function closeOthers(d){
    var list = others(d);
    if(!list.length) return;
    var s = d.querySelector('summary') || d, before = s.getBoundingClientRect().top;
    list.forEach(function(o){ o.open = false; });
    var shift = s.getBoundingClientRect().top - before;
    if(Math.abs(shift) >= 1) scrollFix(shift);
  }
  /* keep the pressed question where it is while rows above it change height */
  var holdUntil = 0, holdEl = null, holdTop = 0;
  function hold(s){
    holdEl = s; holdTop = s.getBoundingClientRect().top;
    var running = holdUntil > performance.now();
    holdUntil = performance.now() + MS + 80;
    if(running) return;
    (function step(){
      var dy = holdEl.getBoundingClientRect().top - holdTop;
      if(Math.abs(dy) >= 0.5) scrollFix(dy);
      if(performance.now() < holdUntil) requestAnimationFrame(step);
    })();
  }
  function edge(d){ var cs = getComputedStyle(d); return (parseFloat(cs.borderTopWidth) || 0) + (parseFloat(cs.borderBottomWidth) || 0); }
  function glide(d, open){
    var s = d.querySelector('summary');
    var from = d.getBoundingClientRect().height;
    if(d._gcdGlide){ d._gcdGlide.cancel(); d._gcdGlide = null; }
    d.classList.toggle('is-closing', !open);
    if(open) d.open = true;
    var to = open ? d.getBoundingClientRect().height : s.getBoundingClientRect().height + edge(d);
    /* nothing to glide (a second press landed before the row had moved): the glide just cancelled may have left its clip behind,
       and a row at rest must not clip its focus ring */
    if(Math.abs(to - from) < 1){ if(!open){ d.open = false; d.classList.remove('is-closing'); } d.style.overflow = ''; return; }
    d.style.overflow = 'hidden';
    var a = d.animate([{ height: from + 'px' }, { height: to + 'px' }], { duration: MS, easing: 'ease-out', fill: 'forwards' });
    d._gcdGlide = a;
    a.onfinish = function(){
      if(d._gcdGlide !== a) return;
      d._gcdGlide = null;
      if(!open){ d.open = false; d.classList.remove('is-closing'); }
      d.style.overflow = '';
      a.cancel();
    };
  }
  document.addEventListener('click', function(e){
    if(e.defaultPrevented || !e.target.closest) return;
    var s = e.target.closest('summary'), d = s && s.parentElement;
    if(!d || !d.matches(SEL) || d.querySelector('summary') !== s) return;
    if(calm.matches || !canGlide){ if(!d.open) closeOthers(d); return; }
    e.preventDefault();
    var opening = !d.open || d.classList.contains('is-closing');
    if(opening){
      var list = others(d);
      if(list.length) hold(s);
      list.forEach(function(o){ glide(o, false); });
      glide(d, true);
    } else {
      glide(d, false);
    }
  });
  document.addEventListener('toggle', function(e){
    var d = e.target;
    if(d && d.open && d.matches && d.matches(SEL) && !d.classList.contains('is-closing')) closeOthers(d);
  }, true);
  /* arrow keys on a question: Down and Up move to the next or previous question, Home and End to the first and last */
  document.addEventListener('keydown', function(e){
    if(e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    var k = e.key, s = e.target;
    if(k !== 'ArrowDown' && k !== 'ArrowUp' && k !== 'Home' && k !== 'End') return;
    if(!s || !s.matches || !s.matches(SEL + ' > summary')) return;
    var all = Array.prototype.filter.call(document.querySelectorAll(SEL + ' > summary'), function(x){ return x.getClientRects().length; });
    var i = all.indexOf(s), n = all.length;
    if(i < 0 || n < 2) return;
    e.preventDefault();
    var to = k === 'Home' ? 0 : k === 'End' ? n - 1 : k === 'ArrowDown' ? Math.min(i + 1, n - 1) : Math.max(i - 1, 0);
    all[to].focus();
  });
})();

/* ---------- img[data-src]: requested when its card is 200px from view (built in lazy loading starts too early here), then fades in.
   No script: the <noscript> copy shows. */
(function(){
  var imgs = Array.prototype.slice.call(document.querySelectorAll('img[data-src]'));
  if(!imgs.length) return;
  function show(img){
    if(!img.hasAttribute('data-src')) return;
    img.classList.add('is-loading');
    var done = function(){ img.classList.remove('is-loading'); };
    img.addEventListener('load', done, { once: true });
    img.addEventListener('error', done, { once: true });
    if(img.hasAttribute('data-srcset')) img.srcset = img.getAttribute('data-srcset');
    img.src = img.getAttribute('data-src');
    img.removeAttribute('data-srcset'); img.removeAttribute('data-src');
    if(img.complete) done();
  }
  window.addEventListener('beforeprint', function(){ imgs.forEach(show); });
  if(!('IntersectionObserver' in window)){ imgs.forEach(show); return; }
  var io = new IntersectionObserver(function(en){
    en.forEach(function(e){
      if(!e.isIntersecting) return;
      io.unobserve(e.target);
      imgs.forEach(function(img){ if(img.parentElement === e.target) show(img); });
    });
  }, { rootMargin: '200px 0px' });
  imgs.forEach(function(img){ io.observe(img.parentElement); });
})();

/* ---------- arriving at a #section from another page ----------
   Safari now and then drops the smooth scroll to the section and leaves the page at the top.
   Once, shortly after load: if this was a fresh visit (not reload or back), the visitor has not touched the page,
   the page is still at the top and the section is not in place, jump to it (scroll-margin-top keeps the usual gap). */
(function(){
  var id = location.hash.slice(1);
  if(!id || !window.addEventListener) return;
  try {
    var nav = performance.getEntriesByType('navigation')[0];
    if(nav && nav.type !== 'navigate') return;
  } catch(err){}
  var touched = false;
  function mark(){ touched = true; }
  var kinds = ['wheel', 'touchstart', 'pointerdown', 'keydown'];
  kinds.forEach(function(k){ window.addEventListener(k, mark, { capture: true, passive: true }); });
  function check(){
    kinds.forEach(function(k){ window.removeEventListener(k, mark, { capture: true }); });
    if(touched || window.scrollY >= 5 || location.hash.slice(1) !== id) return;
    var t = null;
    try { t = document.getElementById(decodeURIComponent(id)); } catch(err){}
    if(!t || Math.abs(t.getBoundingClientRect().top) <= 60) return;
    try { t.scrollIntoView({ block: 'start', behavior: 'instant' }); } catch(err){ t.scrollIntoView(true); }
  }
  function later(){ setTimeout(check, 250); }
  if(document.readyState === 'complete') later(); else window.addEventListener('load', later);
})();

/* ---------- the grid under the mouse: a soft flashlight on the granite grid ----------
   A real mouse only (hover and a fine pointer) and only when motion is allowed: phones, touch screens and reduce motion get
   the still grid and this never starts. One fixed layer behind the page (gcd.css .grid-glow): a faint pool of light and the
   same 64 px lines much brighter, seen through a soft round mask. One passive pointer listener sets the target;
   requestAnimationFrame eases the layer after it and moves it by transform only (the lines inside move back by the opposite
   transform, so they sit exactly on the page grid): nothing is painted again while it follows. The loop stops once the glow
   has caught up (mouse idle) and while the tab is hidden; the glow fades out when the mouse leaves the window. */
(function(){
  if(!window.matchMedia || !window.requestAnimationFrame || !document.body) return;
  var fine = window.matchMedia('(hover: hover) and (pointer: fine)');
  var calm = window.matchMedia('(prefers-reduced-motion: reduce)');
  if(!fine.matches || calm.matches) return;
  /* slow frame guard, Firefox only: a Firefox that paints without the GPU can drop to 15 frames a second while the glow
     moves. There a running mean of the frame time is kept while it moves; if it stays over 40 ms for 20 frames
     in a row, the glow fades out and stays off for this visit (every page). Chrome and Safari move it on the GPU, so they
     never run the guard and never read its old flag: a visitor who tripped it before still sees the glow there. */
  var gecko = /\bFirefox\//.test(navigator.userAgent);
  var OFF = 'gcd-glow-off';
  if(gecko){ try { if(window.sessionStorage.getItem(OFF) === '1') return; } catch(err){} }
  /* the layer's size is fixed here and set on the layer itself (gcd.css .grid-glow says the same 720 px), so nothing is
     measured: Safari can run this file before the style sheets apply, and a size read then would be wrong */
  var D = 720, R = D / 2;
  var g = document.createElement('div');
  g.className = 'grid-glow';
  g.setAttribute('aria-hidden', 'true');
  g.style.width = g.style.height = D + 'px';
  var lines = document.createElement('div');
  lines.className = 'grid-glow-lines';
  g.appendChild(lines);
  document.body.appendChild(g);
  var tx = 0, ty = 0, x = 0, y = 0, px = null, py = null, raf = 0, last = 0, on = false, mean = 16.7, slow = 0;
  function stop(){
    if(raf){ cancelAnimationFrame(raf); raf = 0; }
    on = false; last = 0;
    window.removeEventListener('pointermove', move);
    document.removeEventListener('mouseout', out);
    document.removeEventListener('visibilitychange', vis);
    g.classList.remove('is-on');
    try { window.sessionStorage.setItem(OFF, '1'); } catch(err){}
    /* gone from the page once it has faded (gcd.css: 600 ms) */
    setTimeout(function(){ if(g.parentNode) g.parentNode.removeChild(g); }, 700);
  }
  function frame(t){
    raf = 0;
    var dt = last ? Math.min(t - last, 64) : 16.7;
    if(gecko && last){
      mean += (dt - mean) * 0.1;
      slow = mean > 40 ? slow + 1 : 0;
      if(slow >= 20){ stop(); return; }
    }
    last = t;
    /* about 14% of the way each 60 Hz frame: the glow trails the cursor and settles in roughly half a second */
    var k = 1 - Math.pow(0.86, dt / 16.7);
    x += (tx - x) * k; y += (ty - y) * k;
    /* whole pixels only, so its lines sit exactly on the page grid */
    var rx = Math.round(x), ry = Math.round(y);
    if(rx !== px || ry !== py){
      g.style.transform = 'translate3d(' + (rx - R) + 'px,' + (ry - R) + 'px,0)';
      lines.style.transform = 'translate3d(' + (R - rx) + 'px,' + (R - ry) + 'px,0)';
      px = rx; py = ry;
    }
    if(Math.abs(tx - x) > 0.5 || Math.abs(ty - y) > 0.5) raf = requestAnimationFrame(frame);
    else last = 0;
  }
  function wake(){ if(!raf && !document.hidden) raf = requestAnimationFrame(frame); }
  function move(e){
    if(e.pointerType !== 'mouse' || calm.matches) return;
    tx = e.clientX; ty = e.clientY;
    if(!on){
      on = true;
      /* it fades in where the cursor is instead of flying in from the last place it was */
      if(!g.classList.contains('was-on')){ x = tx; y = ty; }
      g.classList.add('is-on', 'was-on');
    }
    wake();
  }
  function out(e){ if(!e.relatedTarget){ on = false; g.classList.remove('is-on'); } }
  function vis(){
    if(document.hidden){ if(raf){ cancelAnimationFrame(raf); raf = 0; } last = 0; } else if(on) wake();
  }
  window.addEventListener('pointermove', move, { passive: true });
  document.addEventListener('mouseout', out);
  document.addEventListener('visibilitychange', vis);
})();
