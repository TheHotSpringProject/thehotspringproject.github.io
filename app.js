/* The Hot Spring Project
   Data: NOAA Thermal Springs List for the United States (KGRD No. 12, 1980). */
(function () {
  'use strict';

  const NAMES = {'BC':'British Columbia','AB':'Alberta','YT':'Yukon','NT':'Northwest Territories','NU':'Nunavut','AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming','DC':'District of Columbia','PR':'Puerto Rico'};
  const COLORS = {B:'#b2141c', V:'#e8452a', H:'#f5962a', W:'#f5d327', C:'#4a90c8', '':'#8c939b'};
  const LABEL = {B:'Near boiling', V:'Very hot', H:'Hot', W:'Warm', C:'Cool', '':'Not available'};
  const ORDER = {'':0, C:1, W:2, H:3, V:4, B:5};
  // Temperature classes (°F): cool <90, warm 90–119, hot 120–159, very hot 160–189, near boiling ≥190.
  // Continuous colour ramp by temperature (°F): blue (cool) → yellow → orange → red → deep red (near boiling).
  const RAMP = [[60, [74, 144, 200]], [90, [245, 211, 39]], [120, [245, 150, 42]], [160, [232, 69, 42]], [200, [178, 20, 28]]];
  const LABEL_F = {B:200, V:175, H:140, W:100, C:60};   // springs listed only as boiling/hot/warm, without a number
  function rampColor(f) {
    if (f == null) return '#8c939b';
    if (f <= RAMP[0][0]) f = RAMP[0][0]; if (f >= RAMP[RAMP.length - 1][0]) f = RAMP[RAMP.length - 1][0];
    for (let k = 1; k < RAMP.length; k++) if (f <= RAMP[k][0]) {
      const [a, ca] = RAMP[k - 1], [b, cb] = RAMP[k], t = (f - a) / (b - a);
      return 'rgb(' + ca.map((v, j) => Math.round(v + (cb[j] - v) * t)).join(',') + ')';
    }
  }
  const estF = d => d.f != null ? d.f : LABEL_F[d.cls] ?? null;
  const colorOf = d => rampColor(estF(d));
  const clsOf = f => f >= 190 ? 'B' : f >= 160 ? 'V' : f >= 120 ? 'H' : f >= 90 ? 'W' : 'C';
  // Land status from USGS PAD-US (see data/springs.json land_source)
  const MGR = {USFS:'US Forest Service', BLM:'Bureau of Land Management', NPS:'National Park Service', FWS:'US Fish & Wildlife Service', USBR:'Bureau of Reclamation', DOD:'Dept. of Defense',
    SDNR:'State land', SDOL:'State land', SLB:'State trust land', SPR:'State parks', SFW:'State fish & wildlife', OTHS:'State', CNTY:'County', CITY:'City', REG:'Regional district',
    TRIB:'Tribal', NGO:'Nonprofit', PVT:'Private', UNK:'Unknown'};
  const LANDCAT = {P:['Public land · open access','pub'], R:['Public land · restricted access','res'], U:['Public land · access unknown','res'], M:['Military · closed','no'], T:['Tribal land','no'], N:['Nonprofit preserve','no'], V:['Private','no']};
  const landShort = d => d.world ? 'Not mapped' : d.ca ? 'Not mapped (Canada)' : !d.land ? 'Private or unmapped' : d.land[0] === 'P' ? 'Public' : d.land[0] === 'R' || d.land[0] === 'U' ? 'Public (limited)' : LANDCAT[d.land[0]][0];
  const PIN = '<svg width="15" height="15" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 2a7 7 0 0 0-7 7c0 5.2 7 13 7 13s7-7.8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>';
  const $ = id => document.getElementById(id);
  const CAM = '<svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9 3 7.2 5H4a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-3.2L15 3zm3 5a5 5 0 1 1 0 10 5 5 0 0 1 0-10zm0 2a3 3 0 1 0 0 6 3 3 0 0 0 0-6z"/></svg>';
  const BOOK = '<svg width="13" height="13" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M4 4a2 2 0 0 1 2-2h13v17H6a1 1 0 0 0 0 2h13v1H6a3 3 0 0 1-3-3V4zm4 2v2h8V6z"/></svg>';
  const title = s => s.replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1).toLowerCase());
  const esc = s => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const gmaps = d => 'https://www.google.com/maps/search/?api=1&query=' + d.lat + ',' + d.lon;
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  };

  // Settings carried over from the old address: #carry=<base64url JSON>[~<hash to open>]
  (() => {
    const m = /^#carry=([A-Za-z0-9_-]*)(?:~(.*))?$/.exec(location.hash);
    if (!m) return;
    try {
      const j = JSON.parse(atob(m[1].replace(/-/g, '+').replace(/_/g, '/')));
      const merge = (k, a) => {
        if (!Array.isArray(a)) return;
        let s; try { s = new Set(JSON.parse(store.get(k, '[]'))); } catch (e) { s = new Set(); }
        a.forEach(x => { if (Number.isInteger(x) && x >= 0) s.add(x); });
        store.set(k, JSON.stringify([...s]));
      };
      merge('wt-saved', j.s); merge('wt-visited', j.v);
      if (j.u === 'F' || j.u === 'C') store.set('wt-unit', j.u);
      if (typeof j.bm === 'string' && /^[a-z0-9]{1,20}$/.test(j.bm)) store.set('wt-bm2', j.bm);
    } catch (e) {}
    const rest = m[2] && /^[a-z0-9-]{1,40}$/.test(m[2]) ? '#' + m[2] : '';
    try { history.replaceState(null, '', location.pathname + location.search + rest); } catch (e) {}
  })();

  // ---------- Basemaps ----------
  const ESRI = 'https://server.arcgisonline.com/ArcGIS/rest/services/';
  const USGS = 'https://basemap.nationalmap.gov/arcgis/rest/services/';
  const MOON = '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M20.5 14.6A8.5 8.5 0 0 1 9.4 3.5a8.5 8.5 0 1 0 11.1 11.1z"/></svg>';
  const SUN = '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4.2" fill="currentColor"/><g stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6"/></g></svg>';
  const SAT = '<svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><g fill="currentColor" transform="rotate(45 13 11)"><rect x="9.4" y="8.6" width="5.2" height="6.8" rx="1"/><rect x="1.6" y="9.6" width="6.6" height="4.8" rx=".7"/><rect x="15.8" y="9.6" width="6.6" height="4.8" rx=".7"/><rect x="8.2" y="11.4" width="1.4" height="1.2"/><rect x="14.4" y="11.4" width="1.4" height="1.2"/></g><path d="M3.6 14.6a5.6 5.6 0 0 0 5.8 5.8M3.4 18.4a2.2 2.2 0 0 0 2.2 2.2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>';
  const ESRI_ATTR = 'Tiles &copy; Esri and contributors';
  const USGS_ATTR = 'Tiles: <a href="https://www.usgs.gov/programs/national-geospatial-program/national-map" target="_blank" rel="noopener">USGS The National Map</a>';
  const OSM_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors';
  // Three maps, picked with icons: Dark (Esri dark gray) and Satellite (Esri imagery), both with roads and place
  // names, and Light (USGS The National Map topo). Light keeps the id 'usgstopo' because offline areas are saved from it.
  const BASEMAPS = [
    {id:'dark', name:'Dark', icon:MOON, url:ESRI+'Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', opt:{maxNativeZoom:16, attribution:ESRI_ATTR + ' (Dark Gray Canvas)'}, dark:true, labels:true},
    {id:'usgstopo', name:'Light', icon:SUN, url:USGS+'USGSTopo/MapServer/tile/{z}/{y}/{x}', opt:{maxNativeZoom:16, attribution:USGS_ATTR}},
    {id:'imagery', name:'Satellite', icon:SAT, url:ESRI+'World_Imagery/MapServer/tile/{z}/{y}/{x}', opt:{maxNativeZoom:19, attribution:ESRI_ATTR + ' (Maxar, Earthstar Geographics)'}, imagery:true, labels:true}
  ];

  // ---------- Map ----------
  const map = L.map('map', {preferCanvas:true, zoomSnap:0.5, worldCopyJump:true, minZoom:2, maxZoom:19});
  if (/[?&]debug\b/.test(location.search)) window.__map = map;   // for automated checks
  map.fitBounds([[24.5,-125],[49.5,-66.5]]);
  window.wtMap = map;   // handy for debugging and for staging screenshots from the console
  map.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
  const renderer = L.canvas({padding:0.3, tolerance:4});

  let baseLayer = null, curBM = null;
  const labels = L.layerGroup([
    L.tileLayer(ESRI+'Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}', {maxNativeZoom:19, maxZoom:19, crossOrigin:'anonymous'}),
    L.tileLayer(ESRI+'Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {maxNativeZoom:19, maxZoom:19, crossOrigin:'anonymous', attribution:ESRI_ATTR})
  ]);
  const grid = $('bmgrid'), bmEl = $('bm');
  BASEMAPS.forEach(b => {
    const s = document.createElement('button');
    s.className = 'sw'; s.dataset.id = b.id; s.type = 'button'; s.setAttribute('role', 'menuitemradio');
    s.innerHTML = b.icon; s.title = b.name; s.setAttribute('aria-label', b.name + ' map');
    s.onclick = () => { setBM(b.id); bmEl.classList.remove('open'); $('bmbtn').setAttribute('aria-expanded', 'false'); };
    grid.appendChild(s);
  });
  function setBM(id, _picked, keep) {
    const b = BASEMAPS.find(x => x.id === id) || BASEMAPS[0];
    if (baseLayer) map.removeLayer(baseLayer);
    baseLayer = L.tileLayer(b.url, Object.assign({maxZoom:19, detectRetina:false, crossOrigin:'anonymous'}, b.opt)).addTo(map);
    baseLayer.bringToBack();
    curBM = b;
    grid.querySelectorAll('.sw').forEach(s => { s.classList.toggle('on', s.dataset.id === b.id); s.setAttribute('aria-checked', s.dataset.id === b.id); });
    if (b.labels) labels.addTo(map); else map.removeLayer(labels);   // roads and place names go with Dark and Satellite
    $('bmbtn').innerHTML = b.icon;
    $('bmbtn').title = 'Map: ' + b.name + ' (tap to change)';
    bmEl.dataset.cur = b.id;
    if (!keep) store.set('wt-bm2', b.id);
  }
  $('bmbtn').onclick = e => { e.stopPropagation(); bmEl.classList.toggle('open'); e.currentTarget.setAttribute('aria-expanded', bmEl.classList.contains('open')); };
  document.addEventListener('click', e => { if (!bmEl.contains(e.target)) bmEl.classList.remove('open'); });
  L.DomEvent.disableClickPropagation(bmEl); L.DomEvent.disableScrollPropagation(bmEl);
  L.DomEvent.disableClickPropagation($('legend'));
  { const v = store.get('wt-bm2', 'dark'); setBM(v === 'dark' || v === 'imagery' ? v : 'usgstopo'); }   // older choices (OSM, relief...) become Light

  // ---------- Locate control ----------
  let me = null, meMarker = null;
  const Locate = L.Control.extend({
    options:{position:'topleft'},
    onAdd() {
      const bar = L.DomUtil.create('div', 'leaflet-bar');
      const a = L.DomUtil.create('a', 'locate', bar);
      a.href = '#'; a.title = 'Show my location'; a.setAttribute('role', 'button'); a.innerHTML = '◎';
      L.DomEvent.on(a, 'click', e => { L.DomEvent.preventDefault(e); L.DomEvent.stopPropagation(e); locate(true); });
      this.btn = a; return bar;
    }
  });
  const locateCtl = new Locate().addTo(map);
  function locate(zoom) {
    if (!navigator.geolocation) { alertMsg('Location is not available in this browser.'); return; }
    locateCtl.btn.classList.add('busy');
    navigator.geolocation.getCurrentPosition(p => {
      locateCtl.btn.classList.remove('busy');
      gotMe(p);
      if (zoom) map.setView(me, Math.max(map.getZoom(), 8));
      update();
    }, err => {
      locateCtl.btn.classList.remove('busy');
      alertMsg('Could not get your location' + (err && err.message ? ': ' + err.message : '.'));
      if ($('sort').value === 'near') { $('sort').value = 'name'; update(); }
    }, {enableHighAccuracy:false, timeout:12000, maximumAge:300000});
  }
  function gotMe(p) {
    me = [p.coords.latitude, p.coords.longitude];
    if (meMarker) meMarker.setLatLng(me);
    else { meMarker = L.circleMarker(me, {radius:7, color:'#fff', weight:2.5, fillColor:'#1a73e8', fillOpacity:1, renderer}).addTo(map); meMarker.bindPopup('You are here'); }
  }
  function alertMsg(m) {
    const d = $('detail'); d.style.display = 'block';
    d.innerHTML = '<button class="x" title="Close">✕</button><div></div>';
    d.lastChild.textContent = m; d.querySelector('.x').onclick = () => { d.style.display = 'none'; };
  }
  function distMi(d) {
    if (!me) return null;
    const R = 3958.8, toR = Math.PI / 180;
    const dLat = (d.lat - me[0]) * toR, dLon = (d.lon - me[1]) * toR;
    const a = Math.sin(dLat/2)**2 + Math.cos(me[0]*toR) * Math.cos(d.lat*toR) * Math.sin(dLon/2)**2;
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  // Hover labels only where a real hover exists; on touch screens a tap would show the label and the popup together.
  const canHover = !!(window.matchMedia && matchMedia('(hover: hover) and (pointer: fine)').matches);

  // ---------- Saved & visited (kept on this device) ----------
  const loadSet = k => { try { return new Set(JSON.parse(store.get(k, '[]'))); } catch (e) { return new Set(); } };
  const saved = loadSet('wt-saved'), visited = loadSet('wt-visited');
  const saveSet = (k, s) => store.set(k, JSON.stringify([...s]));

  // ---------- State ----------
  let S = [], unit = store.get('wt-unit', 'F'), sel = null, current = [];
  const fmt = (d, u = unit) => d.f == null ? (d.cls ? LABEL[d.cls] : '—') : (u === 'F' ? d.f + '°F' : d.c + '°C');
  const tempLong = d => d.f == null ? (d.cls ? LABEL[d.cls] + ' (no reading listed)' : 'Not available') : d.f + '°F / ' + d.c + '°C';

  // Wikipedia article / Commons photo matched to each spring (data/media.json); text and credits load live
  let MEDIA = {};
  // Curated Wikipedia/Commons links, plus Commons photos geotagged at each spring (data/photos.json) for springs
  // without a curated photo.
  const mediaReady = Promise.all([
    fetch('data/media.json?v=4').then(r => r.ok ? r.json() : {m:{}}).catch(() => ({m:{}})),
    fetch('data/photos.json?v=2').then(r => r.ok ? r.json() : {p:{}}).catch(() => ({p:{}})),
    fetch('data/submitted.json', {cache:'no-cache'}).then(r => r.ok ? r.json() : {s:{}}).catch(() => ({s:{}}))
  ]).then(([j, ph, sub]) => {
    MEDIA = j.m || {};
    // photos shared through the app come first, then curated ones, then automatic matches
    Object.entries(sub.s || {}).forEach(([i, r]) => { MEDIA[i] = [(MEDIA[i] || [''])[0], r.file]; });
    Object.entries(ph.p || {}).forEach(([i, f]) => { if (!MEDIA[i]) MEDIA[i] = ['', f]; else if (!MEDIA[i][1]) MEDIA[i] = [MEDIA[i][0], f]; });
  });
  const recReady = fetch('data/recreation.json?v=7').then(r => r.ok ? r.json() : {}).then(j => { REC = j.r || {}; }).catch(() => {});
  // Worldwide springs (OpenStreetMap + Wikidata): preview only, with ?world in the address
  const WORLD = new URLSearchParams(location.search).has('world');
  // Grouping crowded springs into numbered bubbles: preview only for now (?world or ?group)
  const GROUP = (WORLD || new URLSearchParams(location.search).has('group')) && !new URLSearchParams(location.search).has('nogroup') && !!L.markerClusterGroup;
  let cluster = null;
  const worldReady = WORLD ? fetch('data/springs-world.json?v=1').then(r => r.ok ? r.json() : null).catch(() => null) : Promise.resolve(null);
  Promise.all([fetch('data/springs.json?v=8').then(r => r.json()), mediaReady, recReady, worldReady]).then(([j, , , w]) => init(j, w)).catch(err => {
    alertMsg('Could not load spring data (' + err + ').');
  });

  let SS_SRC = [], REC = {};
  const REC_LABEL = {D:'Known soaking spot · commercial', W:'Known soaking spot · wild', P:'Possibly used', N:'Unlikely or not allowed', U:'No evidence found'};
  const recKey = d => d.lat.toFixed(3) + ',' + d.lon.toFixed(3);
  // Known soaking spots get a symbol: a house for commercial, the hot-spring sign for wild.
  const GLYPH = {
    D:'<path d="M12 5.2 5.6 10.6h1.9v7.2h3.6v-4.4h1.8v4.4h3.6v-7.2h1.9z" fill="#fff"/>',
    W:'<g fill="none" stroke="#fff" stroke-width="1.7" stroke-linecap="round"><path d="M5.8 13.6c1.2 3.6 11.2 3.6 12.4 0"/><path d="M9 12c-1-1.3 1-2.4 0-3.7s1-2.4 0-3.4"/><path d="M12 12c-1-1.3 1-2.4 0-3.7s1-2.4 0-3.4"/><path d="M15 12c-1-1.3 1-2.4 0-3.7s1-2.4 0-3.4"/></g>'
  };
  const soakSvg = (k, fill, stroke, sw) => '<svg viewBox="0 0 24 24" width="100%" height="100%"><circle cx="12" cy="12" r="' + (11.2 - sw / 2) + '" fill="' + fill + '" stroke="' + stroke + '" stroke-width="' + sw + '"/>' + GLYPH[k] + '</svg>';
  function soakIcon(d, r, stroke, sw) {
    const px = Math.round(2 * r + 9);
    return L.divIcon({className:'soakic', html:soakSvg(d.rec[0], colorOf(d), stroke, sw), iconSize:[px, px], iconAnchor:[px / 2, px / 2]});
  }
  function init(json, world) {
    S = json.springs.map((r, i) => ({i, name:r[0] || 'Unnamed spring', unnamed:!r[0], st:r[1], lat:r[2], lon:r[3], f:r[4], c:r[5], cls:r[6], quad:(r[7] || '').replace(/^\(|\)$/g, ''), land:r[8] || null, ss:r[9] || null, moved:r[10] || null, added:r[11] === 'S' || r[11] === 'C', ca:r[11] === 'C', caSrc:r[12] || null}));
    SS_SRC = json.ss_sources || [];
    if (world) {
      Object.assign(NAMES, world.countries);
      const n0 = S.length;
      world.springs.forEach((r, k) => {
        const i = n0 + k;
        S.push({i, name:r[0] || 'Unnamed hot spring', unnamed:!r[0], st:r[1], lat:r[2], lon:r[3], f:r[4], c:r[5], cls:'', quad:'', land:null, ss:null, moved:null,
          added:true, world:true, wrec:r[6] ? [r[6], r[7]] : null, region:r[8], wsrc:r[9], osm:r[12], qid:r[13], alt:r[14]});
        if (r[10] || r[11]) MEDIA[i] = [r[10] || '', r[11] ? 'File:' + r[11] : ''];
      });
    }
    S.forEach(d => { if (d.f != null) d.cls = clsOf(d.f); });   // class follows the reading; springs listed only as boiling/hot/warm keep that label
    S.forEach(d => { d.rec = d.world ? d.wrec : REC[recKey(d)] || null; });
    const sub = document.querySelector('header .sub'); if (sub) sub.textContent = world ? S.length.toLocaleString() + ' springs worldwide (preview) · data: NOAA, state and territorial geological surveys, USGS, Natural Resources Canada, OpenStreetMap contributors and Wikidata' : S.length.toLocaleString() + ' springs across North America · data: NOAA Thermal Springs List (1980), state and territorial geological surveys, USGS and Natural Resources Canada';
    S.forEach(d => { d.noaaNoTemp = !d.added && !!d.ss && d.ss[4] === 1; });   // NOAA listed no reading, so the state survey's is shown
    // markers (hotter drawn on top)
    S.forEach(d => { d.known = !!(d.rec && (d.rec[0] === 'D' || d.rec[0] === 'W')); });
    S.slice().sort((a, b) => (a.known - b.known) || (ORDER[a.cls] - ORDER[b.cls])).forEach(d => {   // known soaking spots on top
      // Known soaking spots: the icon is only drawn; taps land on an invisible, slightly larger dot underneath,
      // handled by the same canvas hit-test as ordinary springs (icon elements alone were unreliable to tap on phones).
      if (d.known) {
        d.ic = L.marker([d.lat, d.lon], {icon:soakIcon(d, 5, '#000', 1), keyboard:false, interactive:false});
        d.hit = L.circleMarker([d.lat, d.lon], {renderer, radius:9, stroke:false, fillOpacity:0});
        d.m = GROUP ? d.hit : L.featureGroup([d.hit, d.ic]);
      } else d.m = L.circleMarker([d.lat, d.lon], {renderer, radius:5, weight:1, color:'#000', opacity:.55, fillColor:colorOf(d), fillOpacity:.95});
      if (canHover) d.m.bindTooltip(() => esc(title(d.name)) + ' · ' + fmt(d), {direction:'top', offset:[0,-4]});
      d.m.on('click', () => select(d, false));
      d.m._d = d;
    });
    if (GROUP) setupCluster();
    // state dropdown
    const counts = {};
    S.forEach(d => counts[d.st] = (counts[d.st] || 0) + 1);
    const CAN = new Set(['BC', 'AB', 'YT', 'NT', 'NU']);
    const W3 = new Set(world ? Object.keys(world.countries) : []);
    [['United States', k => !CAN.has(k) && !W3.has(k)], ['Canada', k => CAN.has(k)], ['Other countries', k => W3.has(k)]].forEach(([label, test]) => {
      const g = document.createElement('optgroup'); g.label = label;
      Object.keys(counts).filter(test).sort((a, b) => NAMES[a].localeCompare(NAMES[b])).forEach(k => {
        const o = document.createElement('option'); o.value = k; o.textContent = NAMES[k] + ' (' + counts[k] + ')'; g.appendChild(o);
      });
      if (g.children.length) $('state').appendChild(g);
    });
    if (world) {
      const li = document.createElement('li');
      li.innerHTML = '<b>Springs outside the US and Canada (preview):</b> © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>, available under the Open Database License, and <a href="https://www.wikidata.org/" target="_blank" rel="noopener">Wikidata</a> (CC0). Regions from GeoNames (CC BY 4.0). Soaking estimates for these come from map tags and names only.';
      const ul = document.querySelector('#about ul, dialog ul'); if (ul) ul.appendChild(li);
    }
    if (world) { const o = document.createElement('option'); o.value = 'world'; o.textContent = 'Outside the US and Canada'; srcSel.insertBefore(o, srcSel.querySelector('option[value="ss"]')); }
    setUnit(unit); restyle(); update();
    openFromHash();
  }

  // ---------- Grouping (preview) ----------
  // Bubbles show how many springs they hold, take the colour of the hottest one, and carry a small mark when
  // they contain known soaking spots. Grouping stops at zoom 9, so single springs always show when zoomed in.
  function setupCluster() {
    cluster = L.markerClusterGroup({
      maxClusterRadius: z => z < 6 ? 44 : 34, disableClusteringAtZoom: 9, showCoverageOnHover: false, spiderfyOnMaxZoom: false,
      chunkedLoading: true, removeOutsideVisibleBounds: true, animate: true,
      iconCreateFunction: c => {
        const ds = c.getAllChildMarkers().map(m => m._d);
        let hot = null, soak = '';
        ds.forEach(d => { const f = estF(d); if (f != null && (!hot || f > estF(hot))) hot = d; if (d.known && soak !== 'D') soak = d.rec[0]; });
        const n = ds.length, px = n < 10 ? 24 : n < 100 ? 28 : n < 1000 ? 34 : 40;
        const fill = hot ? colorOf(hot) : 'var(--na)';
        return L.divIcon({className: 'grp', iconSize: [px, px],
          html: '<div class="grpb" style="background:' + fill + '"><span>' + (n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k' : n) + '</span>' +
            (soak ? '<i class="grps">' + soakSvg(soak, '#1f2a33', '#fff', 1.4) + '</i>' : '') + '</div>'});
      }
    });
    cluster.on('clusterclick', e => e.layer.zoomToBounds({padding: [30, 30]}));
    map.addLayer(cluster);
    map.on('moveend zoomend', syncIcons); cluster.on('animationend', syncIcons);
  }
  // Soak symbols are separate from the clustered hit circles: show each only while its spring is not inside a bubble.
  let syncT = null;
  function syncIcons() {
    clearTimeout(syncT);
    syncT = setTimeout(() => {
      const b = map.getBounds().pad(0.2);
      S.forEach(d => {
        if (!d.known) return;
        const show = d.inC && b.contains([d.lat, d.lon]) && map.hasLayer(d.hit);   // unclustered springs are on the map; ones inside a bubble are not
        if (show && !map.hasLayer(d.ic)) d.ic.addTo(map); else if (!show && map.hasLayer(d.ic)) map.removeLayer(d.ic);
      });
    }, 60);
  }

  // ---------- Marker size by zoom ----------
  function restyle() {
    const z = map.getZoom(), r = z < 5 ? 4 : z < 7 ? 5 : z < 10 ? 6.5 : 8;
    const dk = curBM && (curBM.dark || curBM.imagery);
    // Known soaking spots (commercial or wild) are solid; everything else is about half transparent.
    S.forEach(d => d.known ? (d.hit.setRadius((d === sel ? r + 2 : r) + 4.5), d.ic.setIcon(soakIcon(d, d === sel ? r + 2 : r, d === sel ? '#00a3ff' : saved.has(d.i) ? '#be6b47' : dk ? '#fff' : 'rgba(0,0,0,.75)', d === sel || saved.has(d.i) ? 2.6 : 1.2)).setZIndexOffset(d === sel ? 1000 : 0)) : d.m.setStyle(d === sel ? {radius:r + 3, weight:3, color:'#00a3ff', opacity:1, fillOpacity:1} : saved.has(d.i) ? {radius:r + 1, weight:2.5, color:'#be6b47', opacity:1, fillOpacity:d.known ? 1 : .5} : {radius:r, weight:1, color:dk ? '#fff' : '#000', opacity:d.known ? (dk ? .9 : .7) : (dk ? .4 : .25), fillOpacity:d.known ? 1 : .5}));
  }
  map.on('zoomend', restyle);
  map.on('baselayerchange', restyle);

  // ---------- Filtering ----------
  const q = $('q'), stSel = $('state'), sortSel = $('sort'), minT = $('minT'), landSel = $('land'), mineSel = $('mine'), srcSel = $('src'), soakSel = $('soak');
  const minF = () => +minT.value;
  function passes(d) {
    const term = q.value.trim().toLowerCase(), st = stSel.value, m = minF(), lf = landSel.value, mf = mineSel.value;
    const kf = soakSel.value;
    if (kf && !(kf === 'DW' ? (d.rec && (d.rec[0] === 'D' || d.rec[0] === 'W')) : d.rec && d.rec[0] === kf)) return false;
    const sf = srcSel.value;
    if (sf && (sf === 'noaa' ? d.added : sf === 'added' ? !d.added : sf === 'ca' ? !d.ca : sf === 'world' ? !d.world : !(d.ss || d.added))) return false;
    if (mf && !(mf === 'saved' ? saved.has(d.i) : mf === 'visited' ? visited.has(d.i) : !visited.has(d.i))) return false;
    if (lf) {
      if (d.world || d.ca) return false;   // land status is only mapped in the US
      const c = d.land ? d.land[0] : '';
      // private = no PAD-US parcel (usually private), private ranches, or nonprofit preserves
      const ok = lf === 'open' ? c === 'P' : lf === 'limited' ? c === 'R' || c === 'U' : lf === 'public' ? 'PRU'.includes(c) && c !== '' : c === '' || c === 'V' || c === 'N';
      if (!ok) return false;
    }
    return (!st || d.st === st) && (!term || d.name.toLowerCase().includes(term) || (d.alt && d.alt.toLowerCase().includes(term))) && (m <= 40 || (estF(d) == null ? m <= 80 : estF(d) >= m));   // springs with no temperature at all stay visible up to the 80°F default
  }
  function update() {
    // A name search looks through every spring, not just the ones in view, so a match anywhere can be found.
    const inView = q.value.trim() ? null : $('inView').checked && !document.querySelector('.app').classList.contains('max') ? map.getBounds() : (lastBounds && $('inView').checked ? lastBounds : null);
    const visible = [], toAdd = [], toDel = [];
    S.forEach(d => {
      const ok = passes(d);
      if (cluster) { if (ok !== !!d.inC) { (ok ? toAdd : toDel).push(d.m); d.inC = ok; } }
      else if (ok) { if (!map.hasLayer(d.m)) d.m.addTo(map); } else if (map.hasLayer(d.m)) map.removeLayer(d.m);
      if (ok && (!inView || inView.contains([d.lat, d.lon]))) visible.push(d);
    });
    if (cluster && (toAdd.length || toDel.length)) { cluster.removeLayers(toDel); cluster.addLayers(toAdd); syncIcons(); }
    if (sel && map.hasLayer(sel.m) && sel.m.bringToFront) sel.m.bringToFront();
    const s = sortSel.value, tv = d => d.f == null ? ({B:200, V:175, H:140, W:100, C:60}[d.cls] ?? -1) : d.f;
    const clean = n => n.replace(/^\W+/, '');
    if (s === 'near' && me) visible.forEach(d => d.dist = distMi(d));
    visible.sort(
      s === 'hot' ? (a, b) => tv(b) - tv(a) :
      s === 'cold' ? (a, b) => { const x = tv(a), y = tv(b); return (x < 0) - (y < 0) || x - y; } :
      s === 'near' && me ? (a, b) => a.dist - b.dist :
      (a, b) => a.unnamed - b.unnamed || clean(a.name).localeCompare(clean(b.name)));
    current = visible;
    document.querySelector('.app').classList.toggle('near', s === 'near' && !!me);
    $('count').textContent = current.length.toLocaleString() + (inView ? ' in view' : ' of ' + S.length.toLocaleString());
    activeBadge(); renderList();
  }
  let lastBounds = null, moveTimer = null;
  map.on('moveend', () => { const sz = map.getSize(); if (!sz.x || !sz.y || !$('mapwrap').offsetWidth) return; lastBounds = map.getBounds(); clearTimeout(moveTimer); moveTimer = setTimeout(() => { if ($('inView').checked) update(); }, 60); });

  // ---------- List ----------
  const list = $('list'); let shown = 0;
  function renderList() { list.innerHTML = ''; shown = 0; list.scrollTop = 0; more(); }
  function more() {
    const frag = document.createDocumentFragment();
    for (const d of current.slice(shown, shown + 200)) {
      const el = document.createElement('div');
      el.className = 'it' + (d === sel ? ' sel' : ''); el.dataset.i = d.i;
      const dist = d.dist != null && me ? (d.dist < 10 ? d.dist.toFixed(1) : Math.round(d.dist).toLocaleString()) + ' mi' : '';
      el.innerHTML = '<span class="dot" style="background:' + colorOf(d) + '"></span>' + (saved.has(d.i) ? '<span class="fv" title="Saved">★</span>' : visited.has(d.i) ? '<span class="fv v" title="Visited">✓</span>' : '') + '<span class="nm">' + esc(title(d.name)) + '</span><span class="st">' + d.st +
        '</span><span class="tp">' + fmt(d) + '</span><span class="tc">' + (d.c == null ? '—' : d.c + '°C') + '</span><span class="cl">' + LABEL[d.cls] +
        '</span><span class="ld" title="' + esc(d.land ? d.land[2] : '') + '">' + esc(d.land ? d.land[2] : landShort(d)) + '</span><span class="qd">' + esc(d.quad) + '</span><span class="ds">' + dist +
        '</span>' + (MEDIA[d.i] ? '<span class="mi" title="' + (MEDIA[d.i][1] ? 'Has photo' : 'Has description') + '">' + (MEDIA[d.i][1] ? CAM : BOOK) + '</span>' : '<span class="mi"></span>') + '<a class="gm" title="Open in Google Maps" target="_blank" rel="noopener" href="' + gmaps(d) + '">' + PIN + '</a>';
      frag.appendChild(el);
    }
    shown += 200; list.appendChild(frag);
  }
  list.addEventListener('scroll', () => { if (list.scrollTop + list.clientHeight > list.scrollHeight - 200 && shown < current.length) more(); });
  list.addEventListener('click', e => {
    if (e.target.closest('a')) return;
    const it = e.target.closest('.it'); if (!it) return;
    goTo(S[+it.dataset.i]);
  });
  // Fly to a spring picked from the list or the search box
  function goTo(d) {
    if (app.classList.contains('max')) toggleMax(false);
    if (window.innerWidth <= 760) $('mapwrap').scrollIntoView({behavior:'smooth', block:'start'});
    select(d, true);
  }

  // ---------- Selection, popup, detail ----------
  // The popup is the main info card for a spring; "More" opens the full panel (photos, description, sources).
  function popupHtml(d) {
    const row = (k, v) => '<tr><td>' + k + '</td><td>' + v + '</td></tr>';
    const newer = d.ss && !d.added && !d.noaaNoTemp && d.ss[2] && d.ss[2] > 1980 ? row('Newer', (unit === 'F' ? d.ss[0] + '°F' : d.ss[1] + '°C') + ', ' + d.ss[2]) : '';
    const land = d.world ? '' : d.ca ? '<span class="landtag no">Not mapped in Canada</span>' : d.land ? esc(d.land[2]) + '<br><span class="landtag ' + LANDCAT[d.land[0]][1] + '">' + LANDCAT[d.land[0]][0] + '</span>' : '<span class="landtag no">Private or unmapped</span>';
    return '<div class="pop pop2"><a class="pt" target="_blank" rel="noopener" title="Open in Google Maps" href="' + gmaps(d) + '">' + esc(title(d.name)) + '</a>' +
      (d.rec ? '<div><span class="soak soak-' + d.rec[0] + '">' + REC_LABEL[d.rec[0]] + '</span></div>' + (d.rec[1] && (d.rec[0] === 'D' || d.rec[0] === 'W') ? '<div class="srccite">' + esc(d.rec[1]) + '</div>' : '') : '') +
      '<table class="pt-t">' +
      row('Temp', '<span class="dot" style="background:' + colorOf(d) + '"></span><b>' + tempLong(d).replace(' (no reading listed)', '') + '</b>' + (d.cls ? ' · ' + LABEL[d.cls] : '')) + newer +
      (d.world ? row('Country', esc(NAMES[d.st] || d.st) + (d.region ? ' · ' + esc(d.region) : '')) : row(d.ca ? 'Province' : 'State', NAMES[d.st]) + row('Land', land)) + '</table>' +
      '<div class="pbtns"><button class="pb sav' + (saved.has(d.i) ? ' on' : '') + '">' + (saved.has(d.i) ? '★ Saved' : '☆ Save') + '</button>' +
      '<button class="pb vis' + (visited.has(d.i) ? ' on' : '') + '">' + (visited.has(d.i) ? '✓ Visited' : 'Visited?') + '</button>' +
      '<a class="pb" target="_blank" rel="noopener" href="' + gmaps(d) + '">' + PIN + 'Directions</a>' +
      '<button class="pb more">More ›</button></div></div>';
  }
  function toggleMine(d, which) {
    const set = which === 'sav' ? saved : visited;
    set.has(d.i) ? set.delete(d.i) : set.add(d.i); saveSet(which === 'sav' ? 'wt-saved' : 'wt-visited', set);
    document.querySelectorAll('.pb.' + which + ', .mybtn.' + which).forEach(b => {
      const on = set.has(d.i); b.classList.toggle('on', on);
      b.textContent = which === 'sav' ? (on ? '★ Saved' : '☆ Save') : (on ? '✓ Visited' : b.classList.contains('pb') ? 'Visited?' : 'Mark visited');
    });
    if (which === 'sav') restyle(); renderList();
  }
  function select(d, fly) {
    sel = d; restyle(); if (map.hasLayer(d.m) && d.m.bringToFront) d.m.bringToFront();
    if (d.m.closeTooltip) d.m.closeTooltip();
    list.querySelectorAll('.it').forEach(el => el.classList.toggle('sel', +el.dataset.i === d.i));
    if ($('detail').style.display === 'block') showDetail(d);   // keep an open panel in step
    openPop(d, fly);
  }
  // ---------- Discover: photo cards of springs near you, or a random set ----------
  // Only springs with a freely licensed Wikimedia Commons photo are shown; a card whose photo fails to load is
  // replaced by the next spring in line.
  let discList = [], discShown = 0, discBack = null;
  function backToDiscover() {
    const det = $('detail'), b = discBack; discBack = null;
    det.innerHTML = ''; det.appendChild(b.keep); det.style.display = 'block';
    requestAnimationFrame(() => { det.scrollTop = b.scroll; });
  }
  function openDiscover() {
    discBack = null;
    const det = $('detail'); det.style.display = 'block';
    det.innerHTML = '<div class="dhead"><h2>Discover springs</h2><button class="x" title="Close">✕</button></div>' +
      '<div class="dbody"><div class="dsub" id="dsub">Finding springs near you…</div><div class="dgrid" id="dgrid"></div>' +
      '<div class="dmore"><button class="mybtn" id="dmore" hidden>Show more</button><button class="mybtn" id="dshuf" hidden>Shuffle</button></div>' +
      '<div class="srccite">Photos: Wikimedia Commons. Each spring\'s details credit the photographer and licence. Have a photo of a spring? Open it and tap “Add your photo”.</div></div>';
    det.scrollTop = 0;
    det.querySelector('.x').onclick = () => { det.style.display = 'none'; };
    $('dmore').onclick = () => discMore();
    $('dshuf').onclick = () => discStart(false);
    if (me) discStart(true);
    else if (navigator.geolocation) navigator.geolocation.getCurrentPosition(p => { gotMe(p); update(); discStart(true); }, () => discStart(false), {enableHighAccuracy:false, timeout:8000, maximumAge:600000});
    else discStart(false);
  }
  function discStart(near) {
    const grid = $('dgrid'); if (!grid) return;
    const seenF = new Set();   // one card per photo, and only named springs
    discList = S.filter(d => MEDIA[d.i] && MEDIA[d.i][1] && !d.unnamed && !/^unnamed/i.test(d.name));
    if (near) discList.sort((a, b) => distMi(a) - distMi(b));
    else discList = discList.map(d => [Math.random() + (d.known ? 0.35 : 0), d]).sort((a, b) => b[0] - a[0]).map(x => x[1]);   // known soaks come up more often
    discList = discList.filter(d => !seenF.has(MEDIA[d.i][1]) && seenF.add(MEDIA[d.i][1]));
    discShown = 0; grid.innerHTML = '';
    $('dsub').textContent = near ? 'The nearest springs with photos' : 'A random selection. Allow location to see springs near you.';
    $('dshuf').hidden = near;
    discMore();
  }
  function discMore() { for (let k = 0; k < 12; k++) discAdd(); $('dmore').hidden = discShown >= discList.length; }
  function discAdd() {
    const grid = $('dgrid'); if (!grid || discShown >= discList.length) { if ($('dmore')) $('dmore').hidden = true; return; }
    const d = discList[discShown++], dist = distMi(d);
    const c = document.createElement('button'); c.type = 'button'; c.className = 'dcard ld';
    const meta = [NAMES[d.st] || d.st, dist != null ? Math.round(dist).toLocaleString() + ' mi' : '', d.f != null ? (unit === 'F' ? d.f + '°F' : d.c + '°C') : ''].filter(Boolean).join(' · ');
    c.innerHTML = '<span class="dimg"><img alt=""></span><span class="dn"></span><span class="dm"></span>' + (d.known ? '<span class="dsoak">' + (d.rec[0] === 'D' ? 'Commercial' : 'Wild') + '</span>' : '');
    c.querySelector('.dn').textContent = title(d.name); c.querySelector('.dm').textContent = meta;
    c.onclick = () => {   // fly there and open the full details (the "More" view); closing them comes back here
      const det = $('detail'), keep = document.createDocumentFragment(), scroll = det.scrollTop;
      while (det.firstChild) keep.appendChild(det.firstChild);
      discBack = {keep, scroll};
      goTo(d); showDetail(d);
    };
    grid.appendChild(c);
    getMedia(d.i).then(m => {
      if (!m.photo) { c.remove(); discAdd(); return; }
      const img = c.querySelector('img'); img.alt = 'Photo of ' + title(d.name);
      img.onload = () => c.classList.remove('ld'); img.onerror = () => { c.remove(); discAdd(); };
      img.src = m.photo.src;
    });
  }
  $('discbtn').onclick = openDiscover;

  // ---------- Add your photo ----------
  // Photos are shared through Wikimedia Commons, so they carry a free licence and the photographer's credit. The Upload
  // Wizard opens with the spring's name, place and a link back here filled in; a weekly job (tools/submitted_photos.py)
  // finds files with that link and features them for the spring.
  function uploadUrl(d) {
    const place = NAMES[d.st] || d.st, nm = title(d.name);
    const q = {caption: nm + ', ' + place, descriptionlang: 'en',
      description: nm + ', a hot spring in ' + place + '. Shared through The Hot Spring Project (https://thehotspringproject.github.io/#spring-' + d.i + ').',
      lat: d.lat.toFixed(5), lon: d.lon.toFixed(5)};
    return 'https://commons.wikimedia.org/wiki/Special:UploadWizard?' + new URLSearchParams(q).toString();
  }
  function addPhotoHtml(d) {
    if (d.world) return '';
    return '<details class="addph"><summary>' + CAM + ' Add your photo of this spring</summary>' +
      '<p>Have a good photo of ' + esc(title(d.name)) + '? Share it and we may feature it here, credited to you.</p>' +
      '<ul><li>It must be your own photo.</li><li>Photos are shared on Wikimedia Commons under a free licence (usually CC BY-SA 4.0), which lets anyone reuse them with credit. You\'ll need a free Wikimedia account.</li>' +
      '<li>The form opens with this spring\'s name and location filled in. Please keep the link to The Hot Spring Project in the description; that\'s how we find your photo.</li>' +
      '<li>New photos usually appear within a week.</li></ul>' +
      '<a class="mybtn addgo" target="_blank" rel="noopener" href="' + esc(uploadUrl(d)) + '">Continue to Wikimedia Commons ›</a></details>';
  }

  function showDetail(d) {
    const det = $('detail'); det.style.display = 'block';
    const lat = Math.abs(d.lat).toFixed(3) + '°' + (d.lat >= 0 ? 'N' : 'S'), lon = Math.abs(d.lon).toFixed(3) + '°' + (d.lon < 0 ? 'W' : 'E');
    const dist = distMi(d);
    det.innerHTML = '<button class="x" title="Close">✕</button><h2>' + esc(title(d.name)) + '</h2>' +
      '<div class="mybtns"><button class="mybtn sav' + (saved.has(d.i) ? ' on' : '') + '">' + (saved.has(d.i) ? '★ Saved' : '☆ Save') + '</button><button class="mybtn vis' + (visited.has(d.i) ? ' on' : '') + '">' + (visited.has(d.i) ? '✓ Visited' : 'Mark visited') + '</button></div><table>' +
      (d.world ? '<tr><td>Country</td><td>' + esc(NAMES[d.st] || d.st) + '</td></tr>' + (d.region ? '<tr><td>Region</td><td>' + esc(d.region) + '</td></tr>' : '') + (d.alt ? '<tr><td>Local name</td><td>' + esc(d.alt) + '</td></tr>' : '')
        : '<tr><td>' + (d.ca ? 'Province or territory' : 'State') + '</td><td>' + NAMES[d.st] + '</td></tr>') +
      '<tr><td>Temperature</td><td>' + tempLong(d) + (d.world ? (d.f != null ? ' <span class="srcnote">(' + (d.wsrc.includes('O') ? 'OpenStreetMap' : 'Wikidata') + ')</span>' : '') : d.ca ? (d.ss ? ' <span class="srcnote">(' + esc((SS_SRC[d.ss[3]] || '').split(',')[0]) + ')</span>' : '') : d.ss && (d.added || d.noaaNoTemp) ? ' <span class="srcnote">(' + (d.ss[2] ? 'measured ' + d.ss[2] : 'date not recorded') + ')</span>' : d.f != null && !d.added ? ' <span class="srcnote">(NOAA 1980)</span>' : '') + '</td></tr>' +
      (d.ss && !d.added && !d.noaaNoTemp ? '<tr><td>' + (d.ss[2] && d.ss[2] > 1980 ? 'Newer reading' : 'Other reading') + '</td><td>' + (unit === 'F' ? d.ss[0] + '°F' : d.ss[1] + '°C') + (d.ss[2] ? ', measured ' + d.ss[2] : ', date not recorded') + '</td></tr>' : '') +
      '<tr><td>Class</td><td><span class="dot" style="background:' + colorOf(d) + ';vertical-align:-1px"></span> ' + LABEL[d.cls] + '</td></tr>' +
      '<tr><td>Latitude, longitude</td><td>' + lat + ', ' + lon + '</td></tr>' +
      (d.world ? '' : '<tr><td>Land</td><td>' + (d.ca ? '<span class="landtag no" style="margin-left:0">Not mapped in Canada</span>' : d.land ? esc(d.land[2]) + (MGR[d.land[1]] && !d.land[2].includes(MGR[d.land[1]]) ? ' <span style="color:var(--muted)">(' + MGR[d.land[1]] + ')</span>' : '') + '<br><span class="landtag ' + LANDCAT[d.land[0]][1] + '" style="margin-left:0">' + LANDCAT[d.land[0]][0] + '</span>' : '<span class="landtag no" style="margin-left:0">Private or unmapped</span>') + '</td></tr>') +
      (d.moved ? '<tr><td>Location</td><td>From state survey records; NOAA\'s 1980 point is ' + fmtDist(kmBetween(d.lat, d.lon, d.moved[0], d.moved[1])) + ' away</td></tr>' : '') +
      (d.quad ? '<tr><td>USGS quadrangle</td><td>' + esc(d.quad) + '</td></tr>' : '') +
      (d.rec ? '<tr><td>Soaking <span class="srcnote">(estimate)</span></td><td><span class="soak soak-' + d.rec[0] + '">' + REC_LABEL[d.rec[0]] + '</span>' + (d.rec[1] ? '<div class="srccite">' + esc(d.rec[1]) + '</div>' : '') + '</td></tr>' : '') +
      (d.ca ? '<tr><td>Listed in</td><td>Canadian sources<div class="srccite">' + (d.caSrc || []).map(k => esc(SS_SRC[k] || '')).join('<br>') + '</div></td></tr>' : '') +
      (d.world ? '<tr><td>Listed in</td><td>' + [d.osm ? '<a href="https://www.openstreetmap.org/' + ({n:'node', w:'way', r:'relation'})[d.osm[0]] + '/' + d.osm.slice(1) + '" target="_blank" rel="noopener">OpenStreetMap</a>' : '', d.qid ? '<a href="https://www.wikidata.org/wiki/' + esc(d.qid) + '" target="_blank" rel="noopener">Wikidata</a>' : ''].filter(Boolean).join(' · ') +
        '<div class="srccite">' + (d.osm ? '© OpenStreetMap contributors (ODbL)' : '') + (d.osm && d.qid ? ' · ' : '') + (d.qid ? 'Wikidata (CC0)' : '') + '. Not checked against official surveys.</div></td></tr>' : '') +
      (d.ca || d.world ? '' : '<tr><td>Listed in</td><td>' + (d.added ? 'Added from other data sources (not in NOAA\'s 1980 list)' : 'NOAA Thermal Springs List (1980)') +
        (d.ss || d.moved ? '<div class="srccite">' + (d.ss ? 'Reading: ' + esc(SS_SRC[d.ss[3]] || '') : '') + (d.moved && (!d.ss || d.moved[2] !== d.ss[3]) ? (d.ss ? '<br>' : '') + 'Location: ' + esc(SS_SRC[d.moved[2]] || '') : '') + (/^(Water Quality Portal|Nevada Bureau|New Mexico Bureau)/.test(SS_SRC[(d.ss || d.moved)[d.ss ? 3 : 2]] || '') ? '' : ' · via the <a href="https://doi.org/10.5281/zenodo.8125526" target="_blank" rel="noopener">National Geothermal Data System</a> (CC BY 4.0)') + '</div>' : '') + '</td></tr>') +
      (dist != null ? '<tr><td>Distance from you</td><td>' + Math.round(dist).toLocaleString() + ' mi (straight line)</td></tr>' : '') +
      '</table><div class="gphoto" id="gphoto" hidden></div>' + (MEDIA[d.i] ? '<div class="about" id="about"><div class="ab-load">Loading description…</div></div>' : '') + '<a class="gbtn" target="_blank" rel="noopener" href="' + gmaps(d) + '">' + PIN + ' Open in Google Maps</a>' + addPhotoHtml(d);
    // Pinned header (name + close) above a scrolling body, so the panel can be closed from anywhere in it.
    const head = document.createElement('div'), body = document.createElement('div');
    head.className = 'dhead'; body.className = 'dbody';
    while (det.firstChild) body.appendChild(det.firstChild);
    head.append(body.querySelector('h2'), body.querySelector('.x')); det.append(head, body); det.scrollTop = 0;
    det.querySelector('.mybtn.sav').onclick = () => toggleMine(d, 'sav');
    det.querySelector('.mybtn.vis').onclick = () => toggleMine(d, 'vis');
    if (MEDIA[d.i]) loadAbout(d);
    // Google's photo only when there is no Wikipedia/Commons photo (it also saves a paid lookup)
    if (MEDIA[d.i] && MEDIA[d.i][1]) getMedia(d.i).then(m => { if (!m.photo) loadGooglePhoto(d); }).catch(() => loadGooglePhoto(d));
    else loadGooglePhoto(d);
    det.querySelector('.x').onclick = () => {
      if (discBack) { backToDiscover(); return; }   // opened from Discover: go back to the cards, where you were
      det.style.display = 'none'; if (!map._popup || !map.hasLayer(map._popup)) deselect();
    };
  }
  function deselect() { sel = null; discBack = null; $('detail').style.display = 'none'; restyle(); list.querySelectorAll('.it.sel').forEach(e => e.classList.remove('sel')); setHash(''); }
  function openPop(d, fly) {
    // On wider screens the panel floats over the left of the map: keep the spring and its popup clear of it.
    const panelW = () => { const a = document.querySelector('aside'); return (window.innerWidth > 760 && !app.classList.contains('max') && a) ? a.getBoundingClientRect().right - $('mapwrap').getBoundingClientRect().left : 0; };
    const pw = panelW();
    const open = () => {
      const p = L.popup({offset:[0,-4], autoPan:true, autoPanPaddingTopLeft:[pw + 16, 70], autoPanPaddingBottomRight:[16, 16], closeButton:true, minWidth:230, maxWidth:300});
      p._springI = d.i;
      p.setLatLng([d.lat, d.lon]).setContent(popupHtml(d)).openOn(map);
      const el = p.getElement(); if (!el) return;
      el.querySelector('.pb.sav').onclick = () => toggleMine(d, 'sav');
      el.querySelector('.pb.vis').onclick = () => toggleMine(d, 'vis');
      el.querySelector('.pb.more').onclick = () => showDetail(d);
    };
    if (fly) {
      const z = Math.max(map.getZoom(), 11);
      const target = pw ? map.unproject(map.project([d.lat, d.lon], z).subtract([pw / 2, 0]), z) : L.latLng(d.lat, d.lon);
      map.once('moveend', open); map.flyTo(target, z, {duration:.8});
    } else open();
    setHash('spring-' + d.i);
  }
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && $('detail').style.display === 'block' && !document.querySelector('dialog[open]')) $('detail').querySelector('.x').click(); });
  // Closing a spring's popup (without the full panel open) clears the selection.
  map.on('popupclose', e => { if (sel && e.popup._springI === sel.i && $('detail').style.display !== 'block') deselect(); });

  // ---------- Description & photo (Wikipedia / Wikimedia Commons) ----------
  const mediaCache = {};
  const fmtDate = s => { if (!s) return ''; const m = /^(\d{4})(?:[-:](\d{2}))?(?:[-:](\d{2}))?/.exec(String(s).trim()); if (!m) return ''; const dt = new Date(Date.UTC(+m[1], m[2] ? +m[2] - 1 : 0, m[3] ? +m[3] : 1)); return m[3] ? dt.toLocaleDateString(undefined, {year:'numeric', month:'short', day:'numeric', timeZone:'UTC'}) : m[2] ? dt.toLocaleDateString(undefined, {year:'numeric', month:'short', timeZone:'UTC'}) : m[1]; };
  const stripHtml = s => { const el = document.createElement('div'); el.innerHTML = s || ''; return (el.textContent || '').replace(/\s+/g, ' ').trim(); };
  const WP_API = 'https://en.wikipedia.org/w/api.php', WC_API = 'https://commons.wikimedia.org/w/api.php';
  const wikiUrl = (base, params) => base + '?' + new URLSearchParams(Object.assign({action:'query', format:'json', formatversion:'2', origin:'*'}, params));
  const wpParams = title => ({prop:'extracts|revisions|info', titles:title, exintro:1, explaintext:1, exsentences:4, rvprop:'timestamp', rvlimit:1, inprop:'url', redirects:1});
  const wcParams = file => ({prop:'imageinfo', titles:file, iiprop:'url|extmetadata', iiurlwidth:640});
  async function wikiApi(base, params) { const r = await fetch(wikiUrl(base, params)); return r.json(); }
  async function getMedia(i) {
    if (mediaCache[i]) return mediaCache[i];
    const [title, file] = MEDIA[i]; const out = {};
    const jobs = [];
    if (title) jobs.push(wikiApi(WP_API, wpParams(title)).then(j => {
      const p = j.query && j.query.pages && j.query.pages[0];
      if (p && !p.missing && p.extract) out.wiki = {title:p.title, text:p.extract, url:p.fullurl, edited:p.revisions && p.revisions[0] && p.revisions[0].timestamp};
    }).catch(() => {}));
    if (file) jobs.push(wikiApi(WC_API, wcParams(file)).then(j => {
      const p = j.query && j.query.pages && j.query.pages[0], ii = p && p.imageinfo && p.imageinfo[0];
      if (!ii) return; const md = ii.extmetadata || {}; const v = k => md[k] && md[k].value;
      const lic = stripHtml(v('LicenseShortName'));
      if (!/cc|public domain|pd|gfdl|no restrictions/i.test(lic) || /fair use|non-free/i.test(lic)) return;
      out.photo = {src:ii.thumburl || ii.url, page:ii.descriptionurl, artist:stripHtml(v('Artist')) || 'Unknown author', license:lic, licenseUrl:v('LicenseUrl') || '', taken:v('DateTimeOriginal') ? stripHtml(v('DateTimeOriginal')) : '', uploaded:v('DateTime') || ''};
    }).catch(() => {}));
    await Promise.all(jobs);
    return mediaCache[i] = out;
  }
  async function loadAbout(d) {
    const m = await getMedia(d.i);
    const box = $('about'); if (!box || sel !== d) return;
    let h = '';
    if (m.photo) {
      const tk = fmtDate(m.photo.taken), up = fmtDate(m.photo.uploaded);
      const when = tk ? 'taken ' + tk : up ? 'uploaded ' + up : '';
      h += '<figure><a href="' + esc(m.photo.page) + '" target="_blank" rel="noopener"><img crossorigin="anonymous" src="' + esc(m.photo.src) + '" alt="Photo near ' + esc(title(d.name)) + '" loading="lazy"></a>' +
        '<figcaption>Photo: ' + esc(m.photo.artist) + ', <a href="' + esc(m.photo.page) + '" target="_blank" rel="noopener">Wikimedia Commons</a> · ' +
        (m.photo.licenseUrl ? '<a href="' + esc(m.photo.licenseUrl) + '" target="_blank" rel="noopener">' + esc(m.photo.license) + '</a>' : esc(m.photo.license)) + (when ? ' · ' + when : '') + '</figcaption></figure>';
    }
    if (m.wiki) {
      const txt = m.wiki.text.length > 700 ? m.wiki.text.slice(0, 700).replace(/\s+\S*$/, '') + '…' : m.wiki.text;
      h += '<p class="ab-text"></p><div class="ab-src">From Wikipedia, <a href="' + esc(m.wiki.url) + '" target="_blank" rel="noopener">“' + esc(m.wiki.title) + '”</a>' +
        (m.wiki.edited ? ', last edited ' + fmtDate(m.wiki.edited) : '') + ' · <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener">CC BY-SA 4.0</a></div>';
      box.innerHTML = h; box.querySelector('.ab-text').textContent = txt;
    } else box.innerHTML = h || '';
    if (!h) box.remove();
  }

  // ---------- Google Maps place photo (Places API, shown live; nothing is stored) ----------
  const GKEY = (window.WT_CONFIG && window.WT_CONFIG.googleMapsKey) || '';
  let gLib = null; const gCache = {};
  function loadGoogle() {
    if (!GKEY) return Promise.reject(new Error('no key'));
    if (gLib) return gLib;
    gLib = new Promise((resolve, reject) => {
      window.__wtGoogleReady = () => google.maps.importLibrary('places').then(resolve, reject);
      const s = document.createElement('script');
      s.src = 'https://maps.googleapis.com/maps/api/js?key=' + encodeURIComponent(GKEY) + '&v=weekly&loading=async&callback=__wtGoogleReady';
      s.async = true; s.onerror = () => reject(new Error('Google Maps failed to load'));
      document.head.appendChild(s);
    });
    return gLib;
  }
  const GEN = new Set(['hot','warm','spring','springs','the','of','and','at','near','in','on','thermal','mineral','unnamed','group','area','no','north','south','east','west','upper','lower','big','little','creek','river','lake','canyon','valley','mountain','mtn','mt','pool','pools','well','wells','seep','seeps','geothermal','vent','vents','fumarole','fumaroles','resort','baths','bath','spa','ranch','old','new','site','county','national','park','forest','city']);
  const toks = s => s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\(.*?\)/g, ' ').replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(Boolean);
  const distinctToks = s => toks(s).filter(w => !GEN.has(w) && w.length > 2);
  const fmtDist = k => unit === 'F' ? (k < 0.8 ? Math.round(k * 3280.84 / 50) * 50 + ' ft' : (k / 1.609).toFixed(1) + ' mi') : (k < 1 ? Math.round(k * 100) * 10 + ' m' : k.toFixed(1) + ' km');
  const kmBetween = (a, b, c, d) => { const t = Math.PI / 180, x = (c - a) * t, y = (d - b) * t; const h = Math.sin(x / 2) ** 2 + Math.cos(a * t) * Math.cos(c * t) * Math.sin(y / 2) ** 2; return 12742 * Math.asin(Math.sqrt(h)); };
  async function findGooglePhoto(d) {
    if (d.i in gCache) return gCache[d.i];
    const want = distinctToks(d.name);
    if (!want.length) return gCache[d.i] = null;           // generic names ("Hot Spring") can't be matched reliably
    const lib = await loadGoogle();
    const {places} = await lib.Place.searchByText({
      textQuery: title(d.name) + ' ' + NAMES[d.st],
      fields: ['displayName', 'location', 'photos', 'googleMapsURI', 'types'],
      locationBias: {center: {lat: d.lat, lng: d.lon}, radius: 3000},
      maxResultCount: 5
    });
    // Only places that are the spring itself: natural features first, then parks, campgrounds, pools, spas and
    // non-lodging attractions. Towns (their photos show the town) and hotels (first photo is usually the building) are skipped.
    const kind = p => { const t = p.types || []; const has = x => t.includes(x);
      if (has('natural_feature')) return 0;
      if (['park', 'national_park', 'state_park', 'hiking_area', 'campground', 'swimming_pool', 'spa'].some(has) && !has('lodging')) return 1;
      if (has('tourist_attraction') && !has('lodging')) return 2;
      return -1; };
    const cands = (places || []).filter(p => kind(p) >= 0).sort((a, b) => kind(a) - kind(b));
    for (const p of cands) {
      if (!p.photos || !p.photos.length || !p.location) continue;
      const have = new Set(toks(p.displayName || ''));
      const nameOk = want.every(w => have.has(w) || have.has(w.replace(/s$/, '')) || have.has(w + 's'));
      if (!nameOk || kmBetween(d.lat, d.lon, p.location.lat(), p.location.lng()) > 3) continue;
      const ph = p.photos[0];
      return gCache[d.i] = {src: ph.getURI({maxWidth: 640}), place: p.displayName, mapsUrl: p.googleMapsURI, authors: (ph.authorAttributions || []).map(a => ({name: a.displayName, uri: a.uri}))};
    }
    return gCache[d.i] = null;
  }
  async function loadGooglePhoto(d) {
    if (!GKEY) return;
    let g = null; try { g = await findGooglePhoto(d); } catch (e) { return; }
    const box = $('gphoto'); if (!box || sel !== d || !g) return;
    const by = g.authors.length ? g.authors.map(a => a.uri ? '<a href="' + esc(a.uri) + '" target="_blank" rel="noopener">' + esc(a.name) + '</a>' : esc(a.name)).join(', ') : 'a Google Maps contributor';
    box.innerHTML = '<figure><a href="' + esc(g.mapsUrl || gmaps(d)) + '" target="_blank" rel="noopener"><img src="' + esc(g.src) + '" alt="Google Maps photo of ' + esc(g.place) + '" loading="lazy"></a>' +
      '<figcaption>Photo of “' + esc(g.place) + '” by ' + by + ' · <a href="' + esc(g.mapsUrl || gmaps(d)) + '" target="_blank" rel="noopener">Google Maps</a></figcaption></figure>';
    box.hidden = false;
  }

  // shareable links: #spring-123
  function setHash(h) { try { history.replaceState(null, '', h ? '#' + h : location.pathname + location.search); } catch (e) {} }
  function openFromHash() {
    const m = /^#spring-(\d+)$/.exec(location.hash);
    if (m && S[+m[1]]) select(S[+m[1]], true);
  }
  window.addEventListener('hashchange', openFromHash);

  // ---------- Controls ----------
  function legendText() {
    const tk = document.querySelectorAll('#rticks span'); tk.forEach((el, k) => { const f = +el.dataset.f; el.textContent = (unit === 'F' ? f : Math.round((f - 32) * 5 / 9)) + (k < tk.length - 1 ? '°' : unit === 'F' ? '°F' : '°C'); });
  }
  function minLabel() { const v = minF(); $('minTv').textContent = v <= 40 ? 'any' : (unit === 'F' ? v + '°F' : Math.round((v - 32) * 5 / 9) + '°C'); }
  function setUnit(u) {
    unit = u; store.set('wt-unit', u);
    document.querySelectorAll('#units button').forEach(x => x.classList.toggle('on', x.dataset.u === u));
    minLabel(); legendText(); if (S.length) { renderList(); if (sel) $('detail').querySelector('h2') && select(sel, false); }
  }
  $('units').addEventListener('click', e => { const b = e.target.closest('button'); if (b) setUnit(b.dataset.u); });
  function activeBadge() {
    let n = 0; if (soakSel.value) n++; if (srcSel.value) n++; if (landSel.value) n++; if (mineSel.value) n++; if (q.value.trim()) n++; if (stSel.value) n++; if (minF() > 40) n++; if (sortSel.value !== 'name') n++; if (!$('inView').checked) n++;
    const a = $('active'); a.textContent = n + (n === 1 ? ' filter' : ' filters'); a.style.display = n ? 'inline' : 'none';
  }
  const fold = $('fold'), ctr = $('controls');
  fold.onclick = () => { const open = ctr.hidden; ctr.hidden = !open; fold.setAttribute('aria-expanded', open); if (open) q.focus({preventScroll:true}); };
  q.addEventListener('input', update);
  // Enter in the search box goes to the best match: an exact name first, then a name that starts with the text, then the top of the list
  q.addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    e.preventDefault(); update();
    const t = q.value.trim().toLowerCase(); if (!t || !current.length) return;
    const nm = d => d.name.toLowerCase();
    const d = current.find(d => nm(d) === t) || current.find(d => nm(d).startsWith(t)) || current[0];
    q.blur(); goTo(d);
  });
  landSel.addEventListener('change', update);
  mineSel.addEventListener('change', update);
  srcSel.addEventListener('change', update);
  soakSel.addEventListener('change', update);
  $('inView').addEventListener('change', update);
  sortSel.addEventListener('change', () => { if (sortSel.value === 'near' && !me) locate(false); update(); });
  minT.addEventListener('input', () => { minLabel(); update(); });
  stSel.addEventListener('change', () => {
    const st = stSel.value;
    if (!st) map.flyToBounds([[24.5,-125],[49.5,-66.5]], {duration:.6});
    else { const pts = S.filter(d => d.st === st).map(d => [d.lat, d.lon]); map.flyToBounds(L.latLngBounds(pts).pad(0.1), {duration:.6, maxZoom:9}); }
    update();
  });
  // legend collapse
  const legbtn = $('legbtn'), legbody = $('legbody');
  function setLeg(open) { legbody.hidden = !open; legbtn.setAttribute('aria-expanded', open); }
  setLeg(store.get('wt-leg', window.innerWidth > 760 ? '1' : '0') === '1');
  legbtn.onclick = () => { const open = legbody.hidden; setLeg(open); store.set('wt-leg', open ? '1' : '0'); };
  // expand table
  const app = $('app'), maxbtn = $('maxbtn');
  function toggleMax(on) {
    if (on === undefined) on = !app.classList.contains('max');
    app.classList.toggle('max', on);
    maxbtn.textContent = on ? '⤡ Show map' : '⤢ Expand';
    maxbtn.title = on ? 'Back to the map' : 'Expand the results table';
    if (!on) setTimeout(() => { map.invalidateSize(); update(); }, 0); else update();
  }
  maxbtn.onclick = () => { if (app.classList.contains('rc')) setResults(true); toggleMax(); };
  // collapsible results list (starts collapsed)
  const rfold = $('rfold');
  function setResults(open) {
    app.classList.toggle('rc', !open); rfold.setAttribute('aria-expanded', open);
    if (!open && app.classList.contains('max')) toggleMax(false);
    setTimeout(() => map.invalidateSize(), 0);
  }
  rfold.onclick = () => setResults(app.classList.contains('rc'));
  new ResizeObserver(() => { if ($('mapwrap').offsetWidth) map.invalidateSize(); }).observe($('mapwrap'));
  // ---------- Named springs layer (USGS place names; loaded only when switched on) ----------
  // ~35,000 springs, mostly cool and without readings. Drawn only from zoom 8 and up, at most 4,000 at a time.
  const NAMED_MIN_Z = 8, NAMED_MAX = 4000;
  const namedLayer = L.layerGroup();
  let NAMED = null, namedLoading = null;
  const namedChk = $('namedChk'), namedHint = $('namedHint');
  function namedPopup(r) {
    const d = {lat:r[2], lon:r[3]};
    const t = r[4] == null ? 'No reading' : (unit === 'F' ? r[4] + '°F' : Math.round((r[4] - 32) * 5 / 9) + '°C') + (r[5] ? ' (' + r[5] + ')' : '');
    return '<div class="pop"><a target="_blank" rel="noopener" title="Open in Google Maps" href="' + gmaps(d) + '">' + PIN + esc(r[0]) + '</a>' +
      '<div class="t">Temperature: <b>' + t + '</b></div><div class="t nm-src">Named spring' + (r[1] ? ', ' + (NAMES[r[1]] || r[1]) : '') + ' · USGS place names' + (r[4] != null ? '; reading from the Water Quality Portal' : '') + '</div></div>';
  }
  function drawNamed() {
    namedLayer.clearLayers();
    if (!namedChk.checked || !NAMED) { namedHint.textContent = ''; return; }
    if (map.getZoom() < NAMED_MIN_Z) { namedHint.textContent = 'Zoom in to see them'; return; }
    const b = map.getBounds().pad(0.1); let n = 0;
    for (const r of NAMED) {
      if (!b.contains([r[2], r[3]])) continue;
      if (++n > NAMED_MAX) break;
      const warm = r[4] != null && r[4] >= 90;
      L.circleMarker([r[2], r[3]], {renderer, radius:3.5, weight:1, color:'#2f5674', opacity:.8, fillColor: warm ? rampColor(r[4]) : '#a9c6de', fillOpacity:.9})
        .bindPopup(() => namedPopup(r)).addTo(namedLayer);
    }
    namedHint.textContent = n > NAMED_MAX ? 'Zoom in to see all' : '';
  }
  async function setNamed(on) {
    if (on) {
      if (!namedLayer._map) namedLayer.addTo(map);
      if (!NAMED) {
        namedHint.textContent = 'Loading…';
        try { NAMED = (await (namedLoading = namedLoading || fetch('data/named_springs.json?v=1').then(r => r.json()))).springs; }
        catch (e) { namedHint.textContent = 'Couldn\'t load (offline?)'; namedChk.checked = false; namedLoading = null; return; }
      }
      drawNamed();
    } else { namedLayer.clearLayers(); map.removeLayer(namedLayer); namedHint.textContent = ''; }
  }
  namedChk.addEventListener('change', () => setNamed(namedChk.checked));
  map.on('moveend', () => { if (namedChk.checked) drawNamed(); });

  // ---------- Saved offline areas (USGS Topo tiles + spring details) ----------
  // USGS maps are public domain, so they're the one basemap we download in bulk. Saved copies live in their
  // own cache that is never trimmed; the service worker checks it before the network.
  const OFF_CACHE = 'offline-v1', OFF_MAX = 5000, OFF_ZMAX = 16, OFF_EST = 13 * 1024;
  const USGS_TOPO = USGS + 'USGSTopo/MapServer/tile/';
  const offOk = 'caches' in window && 'serviceWorker' in navigator;
  const areasGet = () => { try { return JSON.parse(store.get('wt-offline', '[]')) || []; } catch (e) { return []; } };
  const areasSet = a => store.set('wt-offline', JSON.stringify(a));
  const tX = (lon, z) => Math.floor((lon + 180) / 360 * 2 ** z);
  const tY = (lat, z) => { const r = Math.max(-85.05, Math.min(85.05, lat)) * Math.PI / 180; return Math.floor((1 - Math.log(Math.tan(r) + 1 / Math.cos(r)) / Math.PI) / 2 * 2 ** z); };
  function tileRange(b, z) {   // b: [[s,w],[n,e]]
    const n = 2 ** z, x0 = Math.max(0, tX(b[0][1], z)), x1 = Math.min(n - 1, tX(b[1][1], z));
    const y0 = Math.max(0, tY(b[1][0], z)), y1 = Math.min(n - 1, tY(b[0][0], z));
    return {x0, x1, y0, y1, count:(x1 - x0 + 1) * (y1 - y0 + 1)};
  }
  function* tileUrls(a) { for (let z = a.zmin; z <= a.zmax; z++) { const r = tileRange(a.b, z); for (let x = r.x0; x <= r.x1; x++) for (let y = r.y0; y <= r.y1; y++) yield USGS_TOPO + z + '/' + y + '/' + x; } }
  function planArea() {
    const bb = map.getBounds(), b = [[bb.getSouth(), Math.max(-180, bb.getWest())], [bb.getNorth(), Math.min(180, bb.getEast())]];
    const zmin = Math.max(2, Math.floor(map.getZoom()) - 2);
    let zmax = Math.min(OFF_ZMAX, Math.max(zmin, Math.floor(map.getZoom()) + 6)), count = 0;
    for (;;) { count = 0; for (let z = zmin; z <= zmax; z++) count += tileRange(b, z).count; if (count <= OFF_MAX || zmax <= Math.floor(map.getZoom())) break; zmax--; }
    const springs = S.filter(d => d.lat >= b[0][0] && d.lat <= b[1][0] && d.lon >= b[0][1] && d.lon <= b[1][1]);
    const c = bb.getCenter(); let near = null, best = 1e9;
    springs.forEach(d => { const k = (d.lat - c.lat) ** 2 + ((d.lon - c.lng) * Math.cos(c.lat * Math.PI / 180)) ** 2; if (k < best) { best = k; near = d; } });
    const states = {}; springs.forEach(d => states[d.st] = (states[d.st] || 0) + 1);
    const st = Object.keys(states).sort((p, q) => states[q] - states[p]).slice(0, 2).join(' / ');
    const name = near ? 'Near ' + (near.unnamed ? 'unnamed spring' : title(near.name)) + (st ? ', ' + st : '') : 'Area at ' + c.lat.toFixed(2) + ', ' + c.lng.toFixed(2);
    return {id:'a' + Date.now().toString(36), name, b, zmin, zmax, count, tooBig:count > OFF_MAX, springs:springs.map(d => d.i), center:[c.lat, c.lng], zoom:map.getZoom()};
  }
  const fmtMB = n => n >= 1048576 ? (n / 1048576).toFixed(n >= 10485760 ? 0 : 1) + ' MB' : Math.max(1, Math.round(n / 1024)) + ' KB';
  const zoomWord = z => z >= 15 ? 'trail detail' : z >= 13 ? 'road detail' : z >= 11 ? 'town detail' : 'overview';

  // Download one area: tiles (4 at a time, polite to the USGS servers) then Wikipedia/Commons details.
  let offJob = null;
  async function saveArea(a, onProg) {
    const c = await caches.open(OFF_CACHE); let done = 0, bytes = 0, failed = 0;
    const urls = tileUrls(a); const job = offJob = {cancel:false};
    const media = a.springs.filter(i => MEDIA[i]);
    const total = a.count + media.length;
    const worker = async () => {
      for (let n = urls.next(); !n.done; n = urls.next()) {
        if (job.cancel) return;
        try {
          let r = await c.match(n.value);
          if (!r) { r = await fetch(n.value, {mode:'cors'}); if (r.ok) { const blob = await r.clone().blob(); bytes += blob.size; await c.put(n.value, r); } else failed++; }
          else bytes += OFF_EST;
        } catch (e) { failed++; }
        onProg(++done, total, bytes);
      }
    };
    await Promise.all([worker(), worker(), worker(), worker()]);
    for (const i of media) {
      if (job.cancel) break;
      const [t, f] = MEDIA[i];
      try {
        if (t) { const u = wikiUrl(WP_API, wpParams(t)); const r = await fetch(u); if (r.ok) await c.put(u, r); }
        if (f) {
          const u = wikiUrl(WC_API, wcParams(f)); const r = await fetch(u);
          if (r.ok) { const j = await r.clone().json(); await c.put(u, r); const ii = j.query && j.query.pages && j.query.pages[0] && j.query.pages[0].imageinfo; const src = ii && ii[0] && (ii[0].thumburl || ii[0].url); if (src) { const p = await fetch(src, {mode:'cors'}); if (p.ok) { bytes += (await p.clone().blob()).size; await c.put(src, p); } } }
        }
      } catch (e) { /* skip this spring */ }
      onProg(++done, total, bytes);
    }
    offJob = null;
    return {cancelled:job.cancel, bytes, failed};
  }
  async function deleteArea(id) {
    const all = areasGet(), a = all.find(x => x.id === id); if (!a) return;
    const rest = all.filter(x => x.id !== id); areasSet(rest);
    const keep = new Set(); rest.forEach(o => { for (const u of tileUrls(o)) keep.add(u); });
    const c = await caches.open(OFF_CACHE);
    for (const u of tileUrls(a)) if (!keep.has(u)) await c.delete(u);
    renderAreas();
  }
  const inArea = ll => areasGet().some(a => ll.lat >= a.b[0][0] && ll.lat <= a.b[1][0] && ll.lng >= a.b[0][1] && ll.lng <= a.b[1][1]);

  // Panel shown by the download button.
  const offPanel = $('offpanel');
  function closeOff() { if (offJob) return; offPanel.hidden = true; }
  function openOff() {
    if (!offOk) { alertMsg('Offline maps need a newer browser.'); return; }
    if (!navigator.onLine) { offPanel.hidden = false; offPanel.innerHTML = '<div class="op-h">Save this area for offline</div><p>You\'re offline. Connect to the internet to save an area.</p><div class="op-btns"><button type="button" class="op-cancel">Close</button></div>'; offPanel.querySelector('.op-cancel').onclick = closeOff; return; }
    const a = planArea();
    offPanel.hidden = false;
    if (a.tooBig) {
      offPanel.innerHTML = '<div class="op-h">Save this area for offline</div><p>This area is too large to save. Zoom in to a trip-sized area (about one county or national forest) and try again.</p><div class="op-btns"><button type="button" class="op-cancel">Close</button></div>';
      offPanel.querySelector('.op-cancel').onclick = closeOff; return;
    }
    const media = a.springs.filter(i => MEDIA[i]).length;
    offPanel.innerHTML = '<div class="op-h">Save this area for offline</div>' +
      '<div class="op-name"></div>' +
      '<ul class="op-facts"><li>USGS Topo map, ' + zoomWord(a.zmin) + ' to ' + zoomWord(a.zmax) + ' (zoom ' + a.zmin + '–' + a.zmax + ')</li>' +
      '<li>' + a.springs.length.toLocaleString() + ' spring' + (a.springs.length === 1 ? '' : 's') + (media ? ', with photos and descriptions for ' + media : '') + '</li>' +
      '<li>' + a.count.toLocaleString() + ' map tiles · about ' + fmtMB(a.count * OFF_EST) + '</li></ul>' +
      '<div class="op-prog" hidden><div class="op-bar"><span></span></div><div class="op-ptxt"></div></div>' +
      '<div class="op-btns"><button type="button" class="op-cancel">Cancel</button><button type="button" class="op-save">Save</button></div>';
    offPanel.querySelector('.op-name').textContent = a.name;
    offPanel.querySelector('.op-cancel').onclick = () => { if (offJob) offJob.cancel = true; else closeOff(); };
    offPanel.querySelector('.op-save').onclick = async e => {
      e.currentTarget.hidden = true;
      if (navigator.storage && navigator.storage.persist) { try { await navigator.storage.persist(); } catch (err) {} }
      const prog = offPanel.querySelector('.op-prog'), bar = prog.querySelector('span'), ptxt = prog.querySelector('.op-ptxt');
      prog.hidden = false;
      const res = await saveArea(a, (d, t, b) => { bar.style.width = (100 * d / t).toFixed(1) + '%'; ptxt.textContent = 'Saving… ' + Math.round(100 * d / t) + '% · ' + fmtMB(b); });
      if (res.cancelled) { closeOff(); return; }
      areasSet(areasGet().concat([{id:a.id, name:a.name, b:a.b, zmin:a.zmin, zmax:a.zmax, count:a.count, springs:a.springs.length, bytes:res.bytes, date:new Date().toISOString().slice(0, 10), center:a.center, zoom:a.zoom}]));
      renderAreas();
      offPanel.innerHTML = '<div class="op-h">Saved for offline</div><div class="op-name"></div><p>' + fmtMB(res.bytes) + ' saved' +
        (res.failed ? ' (' + res.failed + ' tiles couldn\'t be downloaded; try again later to fill gaps)' : '') + '. Find it under <b>Basemap → Offline areas</b>. With no signal, the map switches to USGS Topo here.</p>' +
        '<div class="op-btns"><button type="button" class="op-save">Done</button></div>';
      offPanel.querySelector('.op-name').textContent = a.name;
      offPanel.querySelector('.op-save').onclick = closeOff;
    };
  }
  L.DomEvent.disableClickPropagation(offPanel); L.DomEvent.disableScrollPropagation(offPanel);
  const OffCtl = L.Control.extend({
    options:{position:'topleft'},
    onAdd() {
      const bar = L.DomUtil.create('div', 'leaflet-bar');
      const a = L.DomUtil.create('a', 'offdl', bar);
      a.href = '#'; a.title = 'Save this area for offline'; a.setAttribute('role', 'button'); a.setAttribute('aria-label', 'Save this area for offline');
      a.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" d="M12 4v11m-5-5 5 5 5-5M5 20h14"/></svg>';
      L.DomEvent.on(a, 'click', e => { L.DomEvent.preventDefault(e); L.DomEvent.stopPropagation(e); if (offPanel.hidden) openOff(); else closeOff(); });
      return bar;
    }
  });
  if (offOk) new OffCtl().addTo(map);

  // Saved-area list inside the basemap menu.
  function renderAreas() {
    const box = $('offareas'), all = areasGet();
    $('offhdr').hidden = box.hidden = !offOk;
    $('bmareas').hidden = !all.length || !offOk;
    if (!all.length) { box.innerHTML = ''; return; }
    box.innerHTML = '';
    all.forEach(a => {
      const row = document.createElement('div'); row.className = 'oa';
      row.innerHTML = '<button type="button" class="oa-go" title="Show on map"><span class="oa-n"></span><span class="hint">' + fmtMB(a.bytes) + ' · ' + a.springs + (a.springs === 1 ? ' spring · ' : ' springs · ') + a.date + '</span></button><button type="button" class="oa-del" title="Delete" aria-label="Delete saved area">✕</button>';
      row.querySelector('.oa-n').textContent = a.name;
      row.querySelector('.oa-go').onclick = () => { bmEl.classList.remove('open'); map.fitBounds(a.b); if (!navigator.onLine) setBM('usgstopo', false, true); };
      row.querySelector('.oa-del').onclick = () => { if (confirm('Delete the offline copy of "' + a.name + '"?')) deleteArea(a.id); };
      box.appendChild(row);
    });
  }
  renderAreas();

  // With no signal, switch to USGS Topo when the map is over a saved area (without changing the saved choice).
  let autoSwitched = null;
  function offlineBasemap() {
    if (!navigator.onLine && curBM && curBM.id !== 'usgstopo' && inArea(map.getCenter())) { autoSwitched = curBM.id; setBM('usgstopo', false, true); }
    else if (navigator.onLine && autoSwitched) { setBM(autoSwitched, false, true); autoSwitched = null; }
  }
  grid.addEventListener('click', () => { autoSwitched = null; }, true);   // a basemap the user picks wins
  window.addEventListener('online', offlineBasemap); window.addEventListener('offline', offlineBasemap);
  map.on('moveend', offlineBasemap); offlineBasemap();

  // ---------- App: offline support, install button, offline notice ----------
  if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost')) {
    // When a new version of the app takes over, reload once so the update shows without reopening.
    const hadController = !!navigator.serviceWorker.controller; let reloaded = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => { if (hadController && !reloaded) { reloaded = true; location.reload(); } });
    window.addEventListener('load', () => navigator.serviceWorker.register('sw.js', {updateViaCache:'none'}).then(reg => {
      // Check for updates whenever the app comes back to the foreground (the Android app stays open for days).
      document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') reg.update().catch(() => {}); });
    }).catch(() => {}));
  }
  const standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  let installEvt = null;
  window.addEventListener('beforeinstallprompt', e => { e.preventDefault(); installEvt = e; if (!standalone) { $('installbtn').hidden = false; $('aboutInstall').hidden = false; } });
  const doInstall = async () => { if (!installEvt) { openAbout(); return; } installEvt.prompt(); try { await installEvt.userChoice; } catch (e) {} installEvt = null; $('installbtn').hidden = true; $('aboutInstall').hidden = true; };
  $('installbtn').onclick = doInstall; $('aboutInstall').onclick = doInstall;
  window.addEventListener('appinstalled', () => { $('installbtn').hidden = true; $('aboutInstall').hidden = true; });
  if (standalone) $('installHelp').textContent = 'You\'re using the installed app. Spring data and the areas you\'ve viewed are saved for offline use.';
  // Offline notice: a banner across the top of the map that says what still works; a short "Back online" note when the signal returns.
  let backTimer = null;
  function netState(e) {
    const el = $('offline'), wrap = $('mapwrap');
    clearTimeout(backTimer);
    if (!navigator.onLine) {
      const n = offOk ? areasGet().length : 0;
      $('offttl').textContent = "You're offline";
      $('offmsg').textContent = n
        ? 'Springs and filters still work. Maps load in your ' + (n === 1 ? 'saved area' : n + ' saved areas') + '.'
        : 'Springs and filters still work. Maps need a connection; save areas while online.';
      $('offgo').hidden = !n;
      el.classList.remove('back'); el.hidden = false; wrap.classList.add('isoff');
      document.documentElement.style.setProperty('--offh', (el.offsetHeight + 8) + 'px');   // push map controls below the banner
    } else if (!el.hidden && e && e.type === 'online') {
      $('offttl').textContent = 'Back online'; $('offmsg').textContent = ''; $('offgo').hidden = true;
      el.classList.add('back'); wrap.classList.remove('isoff');
      backTimer = setTimeout(() => { el.hidden = true; el.classList.remove('back'); }, 3000);
    } else { el.hidden = true; wrap.classList.remove('isoff'); }
  }
  $('offx').onclick = () => { $('offline').hidden = true; $('mapwrap').classList.remove('isoff'); };
  $('offgo').onclick = e => { e.stopPropagation(); bmEl.classList.add('open'); $('bmbtn').setAttribute('aria-expanded', 'true'); $('offareas').scrollIntoView({block:'nearest'}); };
  L.DomEvent.disableClickPropagation($('offline'));
  window.addEventListener('online', netState); window.addEventListener('offline', netState); netState();

  // ---------- About dialog (logo click, or #about link) ----------
  const aboutDlg = $('about');
  function openAbout() { if (!aboutDlg.open) { if (aboutDlg.showModal) aboutDlg.showModal(); else aboutDlg.setAttribute('open', ''); } }
  function closeAbout() { if (aboutDlg.close) aboutDlg.close(); else aboutDlg.removeAttribute('open'); if (location.hash === '#about') setHash(''); }
  $('aboutbtn').onclick = () => { openAbout(); setHash('about'); };
  $('aboutClose').onclick = closeAbout;
  aboutDlg.addEventListener('click', e => { if (e.target !== aboutDlg) return; const r = aboutDlg.getBoundingClientRect(); if (e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom) closeAbout(); });   // click on the backdrop
  aboutDlg.addEventListener('close', () => { if (location.hash === '#about') setHash(''); });
  if (location.hash === '#about') openAbout();
  window.addEventListener('hashchange', () => { if (location.hash === '#about') openAbout(); });
})();
