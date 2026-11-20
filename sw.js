/* The Hot Springs Project — offline support
   - App files and spring data are cached so search, filters and details work with no signal.
   - Map tiles you have viewed are kept (up to TILE_MAX) so recently seen areas still draw offline.
   - Wikipedia/Commons text and photos are cached after first view.
   - Google Maps photos are never cached (Google's terms); they simply don't show offline. */
const VERSION = 'wt-v73';
const SHELL = 'shell-' + VERSION;
const TILES = 'tiles-v2';
const WIKI = 'wiki-v2';
const TILE_MAX = 3000;
const WIKI_MAX = 600;
const SAVED = 'offline-v1';

const PRECACHE = [
  './', 'index.html', 'privacy.html', 'style.css', 'app.js', 'config.js', 'manifest.webmanifest',
  'data/springs.json', 'data/media.json',
  'vendor/leaflet/leaflet.js', 'vendor/leaflet/leaflet.css',
  'assets/logo-96.png?v=4', 'assets/logo-192.png?v=4', 'assets/logo-512.png?v=4', 'assets/fav-32.png?v=5', 'favicon.ico?v=5', 'assets/touch-180.png?v=5',
  'assets/apple-touch-180.png?v=4', 'assets/icon-512.png?v=4', 'assets/icon-maskable-192.png?v=4', 'assets/icon-maskable-512.png?v=4'
];

const TILE_HOSTS = ['basemap.nationalmap.gov', 'tile.opentopomap.org', 'server.arcgisonline.com', 'tile.openstreetmap.org', 'basemaps.cartocdn.com'];
const WIKI_HOSTS = ['en.wikipedia.org', 'commons.wikimedia.org', 'upload.wikimedia.org', 'thumb.wikimedia.org'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(PRECACHE.map(u => new Request(u, {cache:'reload'})))).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => (k.startsWith('shell-') && k !== SHELL) || k === 'tiles-v1' || k === 'wiki-v1').map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

async function trim(cacheName, max) {
  const c = await caches.open(cacheName); const keys = await c.keys();
  for (let i = 0; i < keys.length - max; i++) await c.delete(keys[i]);
}

// App files: try the network first so updates show up right away; fall back to the cache when
// offline or when the network is slow (ignore ?v= cache-busters when matching).
async function shellNetFirst(req) {
  const c = await caches.open(SHELL);
  const key = new Request(new URL(req.url).pathname);
  // Unversioned files (the page itself, sw-listed files) skip the browser's HTTP cache, which GitHub
  // Pages sets to 10 minutes; the server answers 304 when nothing changed, so this stays cheap.
  const url = new URL(req.url);
  const fresh = req.mode === 'navigate' ? fetch(url.href, {cache:'no-cache', credentials:'same-origin'})
              : url.search ? fetch(req) : fetch(new Request(req, {cache:'no-cache'}));
  const net = fresh.then(r => { if (r.ok) c.put(key, r.clone()); return r; });
  const timeout = new Promise(res => setTimeout(() => res(null), 4000));
  try {
    const r = await Promise.race([net, timeout]);
    if (r) return r;
  } catch (err) { /* offline */ }
  const hit = (await c.match(req, {ignoreSearch: true})) || (req.mode === 'navigate' ? await c.match('index.html') : null);
  if (hit) return hit;
  try { return await net; } catch (err) { return Response.error(); }
}

// Tiles: cache first; fetch and remember when missing.
async function tileFirst(req) {
  const saved = await (await caches.open(SAVED)).match(req);
  if (saved) return saved;
  const c = await caches.open(TILES);
  const hit = await c.match(req);
  if (hit) return hit;
  try {
    const r = await fetch(req);
    // Only keep CORS copies: Chrome counts each opaque copy as several MB of storage.
    if (r.ok) { c.put(req, r.clone()); if (Math.random() < 0.02) trim(TILES, TILE_MAX); }
    return r;
  } catch (err) { return Response.error(); }
}

// Wikipedia / Commons: network first so credits stay current, cache as fallback.
async function netFirst(req, cacheName, max) {
  const c = await caches.open(cacheName);
  try {
    const r = await fetch(req);
    if (r.ok) { c.put(req, r.clone()); if (Math.random() < 0.05) trim(cacheName, max); }
    return r;
  } catch (err) { return (await c.match(req)) || (await (await caches.open(SAVED)).match(req)) || Response.error(); }
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === self.location.origin) { e.respondWith(shellNetFirst(req)); return; }
  if (TILE_HOSTS.some(h => url.hostname === h || url.hostname.endsWith('.' + h))) { e.respondWith(tileFirst(req)); return; }
  if (WIKI_HOSTS.includes(url.hostname)) { e.respondWith(netFirst(req, WIKI, WIKI_MAX)); return; }
  // Everything else (Google Maps / Places photos and searches) goes straight to the network, uncached.
});
