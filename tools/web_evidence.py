"""Second-pass soaking evidence for springs at or above 90 F that are still unclassified (P or U):
  1. Wikipedia "List of hot springs in the United States" (names + coordinates) -> data/wiki_hotsprings_list.json
  2. Google Places text search ("hot springs") within ~1.5 km of each unclassified spring, run inside the live app page
     in headless Chrome so the site's referrer-restricted Maps key works -> data/places_evidence.json
     {index: [[name, primaryType, types, businessStatus, rating, ratingCount, lat, lon], ...]}
Google results are stored only as minimal facts for classification (no photos, reviews or text)."""
import asyncio, json, re, sys, urllib.parse, urllib.request
sys.stdout.reconfigure(line_buffering=True)
UA = {'User-Agent': 'hotsprings-map/1.0 (https://hotsprings.hydrologicinsights.com/)'}

# ---- 1. Wikipedia list
def wget(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r: return json.load(r)
rows = []
try:
    j = wget('https://en.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'parse', 'page': 'List of hot springs in the United States', 'prop': 'wikitext', 'format': 'json', 'formatversion': 2}))
    wt = j['parse']['wikitext']
    state = ''
    for line in wt.split('\n'):
        h = re.match(r'^==+\s*([^=]+?)\s*==+', line)
        if h: state = h.group(1).strip(); continue
        if not line.startswith('|') or line.startswith('|-') or line.startswith('|+'): continue
        cells = [c.strip() for c in re.split(r'\|\|', line[1:])]
        name = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', cells[0]) if cells else ''
        name = re.sub(r"<[^>]+>|'''?|\{\{[^}]*\}\}", '', name).strip()
        m = re.search(r'\{\{\s*coord\s*\|([^}]*)\}\}', line, re.I)
        lat = lon = None
        if m:
            p = [x.strip() for x in m.group(1).split('|')]
            nums = []
            for x in p:
                if re.fullmatch(r'-?[\d.]+', x): nums.append(float(x))
                elif x in 'NSEW' and x: nums.append(x)
                else: break
            try:
                if len(nums) >= 2 and all(isinstance(n, float) for n in nums[:2]) and (len(nums) == 2 or not isinstance(nums[2], float)):
                    lat, lon = nums[0], nums[1]
                    if len(nums) > 3 and nums[1] == 'S': lat = -lat
                else:
                    ns = nums.index('N') if 'N' in nums else nums.index('S'); ew = nums.index('W') if 'W' in nums else nums.index('E')
                    dms = lambda a: sum(v / 60 ** k for k, v in enumerate(a))
                    lat = dms(nums[:ns]) * (1 if nums[ns] == 'N' else -1); lon = dms(nums[ns + 1:ew]) * (-1 if nums[ew] == 'W' else 1)
            except Exception: pass
        rows.append({'name': name, 'state': state, 'lat': lat, 'lon': lon, 'text': re.sub(r'\s+', ' ', re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', line))[:300]})
    print('Wikipedia list rows:', len(rows), '| with coordinates:', sum(1 for r in rows if r['lat']))
except Exception as e: print('Wikipedia list failed:', e)
json.dump(rows, open('data/wiki_hotsprings_list.json', 'w'), ensure_ascii=False, separators=(',', ':'))

# ---- 2. Google Places near each unclassified spring
S = json.load(open('data/springs.json'))['springs']
R = json.load(open('data/recreation.json'))['r']
todo = [(i, r[2], r[3]) for i, r in enumerate(S) if r[4] is not None and r[4] >= 90 and (R.get(f'{r[2]:.3f},{r[3]:.3f}') or ['U'])[0] in 'PU']
print('unclassified springs to look up:', len(todo))
JS = '''async (todo) => {
  const key = (window.WT_CONFIG || {}).googleMapsKey;
  if (!window.google || !google.maps) await new Promise((res, rej) => { window.__gr = res; const s = document.createElement('script'); s.src = 'https://maps.googleapis.com/maps/api/js?key=' + key + '&v=weekly&loading=async&callback=__gr'; s.onerror = rej; document.head.appendChild(s); });
  const {Place} = await google.maps.importLibrary('places');
  const out = {}; let n = 0, errs = 0;
  for (const [i, lat, lon] of todo) {
    const d = 0.015, dl = d / Math.cos(lat * Math.PI / 180);
    try {
      const {places} = await Place.searchByText({textQuery: 'hot springs', fields: ['displayName', 'primaryType', 'types', 'businessStatus', 'rating', 'userRatingCount', 'location'],
        locationRestriction: {south: lat - d, north: lat + d, west: lon - dl, east: lon + dl}, maxResultCount: 5});
      out[i] = (places || []).map(p => [p.displayName, p.primaryType || '', (p.types || []).slice(0, 6), p.businessStatus || '', p.rating || null, p.userRatingCount || 0, p.location.lat(), p.location.lng()]);
    } catch (e) { errs++; out[i] = 'ERR ' + String(e && e.message || e).slice(0, 80); }
    if (++n % 100 === 0) console.log('places', n);
    await new Promise(z => setTimeout(z, 120));
  }
  return {out, errs};
}'''
async def places():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page()
        pg.on('console', lambda m: print('page:', m.text) if m.text.startswith('places') else None)
        await pg.goto('https://hotsprings.hydrologicinsights.com/', wait_until='networkidle', timeout=120000)
        res = await pg.evaluate(JS, [[i, la, lo] for i, la, lo in todo])
        await b.close()
        return res
res = asyncio.run(places())
print('places done; errors:', res['errs'], '| springs with any result:', sum(1 for v in res['out'].values() if isinstance(v, list) and v))
json.dump(res['out'], open('data/places_evidence.json', 'w'), ensure_ascii=False, separators=(',', ':'))
