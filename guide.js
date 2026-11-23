// The Hot Spring Project: a short guided tour of the app's features.
// Runs once on first launch, and again from About → "Take the tour". Each step highlights a part of the screen
// (skipped if that part isn't on screen) with a short explanation; Back / Next / Skip, or swipe and arrow keys.
(() => {
  const KEY = 'wt-guide-done-v1';
  const phone = () => window.innerWidth <= 760;
  const STEPS = [
    {t: 'Welcome to The Hot Spring Project', b: 'Over 6,000 hot springs across North America. Here is a 30-second tour of what you can do. You can see it again anytime from About.'},
    {el: '#legend', t: 'Colors show temperature', b: 'Each dot is a spring, from blue (cool) to deep red (near boiling). A house marks a known commercial soak; the hot-spring symbol marks a known wild soak.'},
    {el: '#map', t: 'Tap a spring for details', b: 'Tap any spring to see its photo, soaking estimate and temperature. Swipe the details left or right to step through nearby springs.', pad: -40},
    {el: '#map', t: 'Long press to explore', b: 'Press and hold anywhere on the map to jump to the nearest spring, then swipe to explore the area around it.', pad: -40, desktop: 'Right-click anywhere on the map to jump to the nearest spring, then use the arrows to explore the area.'},
    {el: '#discbtn', t: 'Discover', b: 'Photos of the springs nearest you, or a random selection. Tap a photo to see that spring.'},
    {el: '#bmbtn', t: 'Dark, light or satellite', b: 'Switch the map style. The dark map shows roads and place names.'},
    {el: '.leaflet-control .locate', t: 'Find springs near you', b: 'Show your location on the map and how far each spring is from you.'},
    {el: '.leaflet-control .offdl', t: 'Save areas for offline', b: 'Heading somewhere without signal? Save a trip area and its springs, maps and details work offline.'},
    {el: '#fold', t: 'Filter the springs', b: 'Show only known soaking spots, springs with photos, a minimum temperature, a state or province, land manager and more.'},
    {el: '#rfold', t: 'Results', b: 'A list of the springs in view. Sort it, open the full table, and save or tick off the springs you have visited.'},
    {el: '#units', t: '°F or °C', b: 'Choose your temperature units.'},
    {el: '#aboutbtn', t: 'About and more', b: 'Where the data comes from, how to add your own photos, and this tour again. Enjoy your soak, and please leave springs better than you found them.'}
  ];
  let i = 0, steps = [], ov, hole, card, prevFocus;

  function visible(el) {
    if (!el) return false;
    const r = el.getBoundingClientRect(), s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
  }
  function build() {
    ov = document.createElement('div'); ov.className = 'tour'; ov.setAttribute('role', 'dialog'); ov.setAttribute('aria-modal', 'true');
    ov.innerHTML = '<div class="tour-hole"></div><div class="tour-card" role="document"><div class="tour-n"></div><h3></h3><p></p>' +
      '<div class="tour-btns"><button type="button" class="tour-skip">Skip</button><span></span><button type="button" class="tour-back">Back</button><button type="button" class="tour-next">Next</button></div></div>';
    document.body.appendChild(ov);
    hole = ov.querySelector('.tour-hole'); card = ov.querySelector('.tour-card');
    ov.querySelector('.tour-skip').onclick = end;
    ov.querySelector('.tour-back').onclick = () => go(i - 1);
    ov.querySelector('.tour-next').onclick = () => (i >= steps.length - 1 ? end() : go(i + 1));
    ov.addEventListener('click', e => { if (e.target === ov || e.target === hole) go(i + 1 >= steps.length ? i : i + 1); });
    let x0 = null;
    ov.addEventListener('touchstart', e => { x0 = e.touches[0].clientX; }, {passive: true});
    ov.addEventListener('touchend', e => { if (x0 == null) return; const dx = e.changedTouches[0].clientX - x0; x0 = null; if (Math.abs(dx) > 60) go(dx < 0 ? i + 1 : i - 1); }, {passive: true});
    document.addEventListener('keydown', onKey);
    window.addEventListener('resize', place);
  }
  function onKey(e) {
    if (!ov) return;
    if (e.key === 'Escape') end();
    else if (e.key === 'ArrowRight' || e.key === 'Enter') { e.preventDefault(); i >= steps.length - 1 ? end() : go(i + 1); }
    else if (e.key === 'ArrowLeft') go(i - 1);
  }
  function go(n) {
    if (n < 0 || n >= steps.length) return;
    i = n;
    const s = steps[i], el = s.el && document.querySelector(s.el);
    if (el && el.scrollIntoView) el.scrollIntoView({block: 'center', behavior: 'instant' in document.documentElement.style ? 'instant' : 'auto'});
    card.querySelector('.tour-n').textContent = (i + 1) + ' of ' + steps.length;
    card.querySelector('h3').textContent = s.t;
    card.querySelector('p').textContent = (!phone() && s.desktop) || s.b;
    ov.querySelector('.tour-back').style.visibility = i ? 'visible' : 'hidden';
    ov.querySelector('.tour-next').textContent = i === steps.length - 1 ? 'Done' : 'Next';
    requestAnimationFrame(place);
    ov.querySelector('.tour-next').focus({preventScroll: true});
  }
  function place() {
    if (!ov) return;
    const s = steps[i], el = s.el && document.querySelector(s.el), W = window.innerWidth, H = window.innerHeight;
    if (!el || !visible(el)) {   // centred card, no highlight
      hole.style.cssText = 'left:50%;top:50%;width:0;height:0';
      card.style.left = Math.max(12, (W - card.offsetWidth) / 2) + 'px';
      card.style.top = Math.max(12, (H - card.offsetHeight) / 2) + 'px';
      return;
    }
    const r = el.getBoundingClientRect(), pad = s.pad != null ? s.pad : 6;
    const L = Math.max(4, r.left - pad), T = Math.max(4, r.top - pad), R = Math.min(W - 4, r.right + pad), B = Math.min(H - 4, r.bottom + pad);
    hole.style.cssText = `left:${L}px;top:${T}px;width:${R - L}px;height:${B - T}px`;
    const cw = card.offsetWidth, ch = card.offsetHeight, gap = 12;
    let top = B + gap <= H - ch - 8 ? B + gap : T - gap - ch >= 8 ? T - gap - ch : Math.max(8, (H - ch) / 2);
    let left = Math.min(Math.max(8, (L + R) / 2 - cw / 2), W - cw - 8);
    card.style.left = left + 'px'; card.style.top = top + 'px';
  }
  function end() {
    try { localStorage.setItem(KEY, '1'); } catch (e) {}
    document.removeEventListener('keydown', onKey); window.removeEventListener('resize', place);
    if (ov) ov.remove(); ov = null;
    window.scrollTo(0, 0);
    if (prevFocus && prevFocus.focus) prevFocus.focus({preventScroll: true});
  }
  function start() {
    if (ov) return;
    const det = document.getElementById('detail');
    if (det && det.style.display === 'block') { const x = det.querySelector('.dhead .x'); if (x) x.click(); }
    steps = STEPS.filter(s => !s.el || s.el === '#map' || visible(document.querySelector(s.el)));
    prevFocus = document.activeElement; build(); go(0);
  }
  window.startTour = start;
  // First launch: wait for the map and springs, and skip for links straight to a spring and for automated browsers
  let seen = false; try { seen = !!localStorage.getItem(KEY); } catch (e) { seen = true; }
  if (!seen && !navigator.webdriver && !/^#spring-/.test(location.hash) && !/[?&](noguide|debug)\b/.test(location.search)) {
    const wait = () => document.querySelector('#legend') && document.querySelector('.leaflet-control .locate') ? setTimeout(start, 900) : setTimeout(wait, 300);
    window.addEventListener('load', wait);
  }
})();
