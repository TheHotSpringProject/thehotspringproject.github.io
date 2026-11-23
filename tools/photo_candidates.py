"""Gather candidate Wikimedia Commons photos for hand review (runs in GitHub Actions).

Springs reviewed: known soaking spots (commercial, wild), springs possibly used for soaking, and any spring that already
has a photo. For each: the current photo plus freely licensed JPEG/PNG photos (at least 800 px wide) geotagged within
1 km on Commons, maps/logos/diagrams/signs dropped, up to 12, ordered: current photo, then file names mentioning the
spring, then nearest. Output: data/photo_candidates.json, read by review.html.
"""
import json, math, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(line_buffering=True)
API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'TheHotSpringProject/1.0 (https://thehotspringproject.github.io/; photo review)'}
FREE = re.compile(r'cc[- ]?by|cc0|public domain|\bpd\b|pd-|attribution', re.I)
NOTFREE = re.compile(r'\bnc\b|non[- ]?commercial|\bnd\b|no[- ]?deriv|fair use|non-free', re.I)
BAD = re.compile(r'\bmap\b|locator|logo|diagram|chart|\bsign\b|signage|plaque|\bseal\b|coat of arms|flag of|screenshot|\.svg$', re.I)
# Learned from the first hand review: wildlife/plant photos and town scenes were never picked
SPECIES = re.compile(r'^File:[A-Z][a-z]+ [a-z]{4,}\b|inaturalist', re.I if False else 0)
TOWN = re.compile(r'church|court ?house|\bbank\b|city hall|railroad|depot|\bstation\b|ski area|highway|\bstreet\b|mercantile|bakery|'
                  r'farmers market|statue|cattle|\bbarn\b|cottage|duplex|disc golf|hydroelectric|no trespassing', re.I)
GENERIC = {'hot', 'warm', 'springs', 'spring', 'the', 'and', 'creek', 'river', 'lake', 'upper', 'lower', 'north', 'south', 'east', 'west',
           'big', 'little', 'mineral', 'sulphur', 'sulfur', 'thermal', 'group', 'resort', 'unnamed', 'near'}

def api(params):
    params = dict(params, format='json', formatversion=2)
    data = urllib.parse.urlencode(params).encode()
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(API, data=data, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            print('retry', k, repr(e)[:80]); time.sleep(5 + 10 * k)
    return {}

def km(a, b, c, d):
    t = math.pi / 180; x = (c - a) * t; y = (d - b) * t
    h = math.sin(x / 2) ** 2 + math.cos(a * t) * math.cos(c * t) * math.sin(y / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

springs = json.load(open('data/springs.json'))['springs']
rec = json.load(open('data/recreation.json'))['r']
media = json.load(open('data/media.json'))['m']
photos = json.load(open('data/photos.json'))['p']
sub = json.load(open('data/submitted.json'))['s']
def current(i):
    k = str(i)
    if k in sub: return sub[k]['file']
    if k in media and len(media[k]) > 1 and media[k][1]: return media[k][1]
    return photos.get(k)

ORDER = {'D': 0, 'W': 1, 'P': 2}
todo = []
for i, r in enumerate(springs):
    code = (rec.get(f'{r[2]:.3f},{r[3]:.3f}') or [None])[0]
    cur = current(i)
    if code in ORDER or cur:
        todo.append((ORDER.get(code, 3), r[1], r[0] or '', i, code, cur))
todo.sort()
print('springs', len(todo))

out = []; T0 = time.time()
for n, (_, st, name, i, code, cur) in enumerate(todo):
    if time.time() - T0 > 80 * 60: print('time limit'); break
    r = springs[i]
    g = api({'action': 'query', 'list': 'geosearch', 'gscoord': f'{r[2]}|{r[3]}', 'gsradius': 1000, 'gsnamespace': 6, 'gslimit': 60})
    hits = (g.get('query') or {}).get('geosearch') or []
    dist = {h['title']: h.get('dist', 0) / 1000 for h in hits}
    titles = [h['title'] for h in hits if re.search(r'\.(jpe?g|png)$', h['title'], re.I) and not BAD.search(h['title'])
              and not SPECIES.search(h['title']) and not TOWN.search(h['title'])]
    if cur and cur not in titles: titles.insert(0, cur)
    if not titles: continue
    info = {}
    for k in range(0, len(titles), 50):
        j = api({'action': 'query', 'titles': '|'.join(titles[k:k + 50]), 'prop': 'imageinfo', 'iiprop': 'size|mime|extmetadata|url',
                 'iiurlwidth': 480, 'iiextmetadatafilter': 'LicenseShortName|Artist'})
        q = j.get('query') or {}
        back = {x['to']: x['from'] for x in q.get('normalized', [])}
        for p in q.get('pages', []):
            info[back.get(p['title'], p['title'])] = p
    tk = [w for w in re.findall(r'[a-z]+', name.lower()) if len(w) >= 4 and w not in GENERIC]
    cands = []
    for t in titles:
        p = info.get(t); ii = p and (p.get('imageinfo') or [None])[0]
        if not ii: continue
        md = ii.get('extmetadata') or {}
        lic = (md.get('LicenseShortName') or {}).get('value', '')
        if t != cur and (ii.get('width', 0) < 800 or ii.get('mime') not in ('image/jpeg', 'image/png') or not FREE.search(lic) or NOTFREE.search(lic)):
            continue
        by = re.sub('<[^>]+>', '', (md.get('Artist') or {}).get('value', '')).strip()[:60]
        nm = sum(1 for w in tk if re.search(r'\b' + re.escape(w), t, re.I))
        cands.append({'f': t, 'u': ii.get('thumburl') or ii.get('url'), 'w': ii.get('width'), 'h': ii.get('height'),
                      'by': by, 'lic': lic, 'd': round(dist.get(t, -1), 2), 'cur': t == cur, '_s': (t != cur, -nm, dist.get(t, 9))})
    cands.sort(key=lambda c: c['_s'])
    for c in cands: c.pop('_s')
    cands = cands[:12]
    if cands:
        out.append({'i': i, 'name': name, 'st': st, 'soak': code or '', 'lat': r[2], 'lon': r[3], 'c': cands})
    if n % 50 == 49:
        print(f'{n + 1}/{len(todo)} springs, {len(out)} with photos, {int(time.time() - T0)} s')
        json.dump(out, open('data/photo_candidates.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    time.sleep(0.1)
json.dump(out, open('data/photo_candidates.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('done', len(out), 'springs with candidates,', sum(len(x['c']) for x in out), 'photos')
