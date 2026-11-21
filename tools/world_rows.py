"""Turn data/world_raw.json (OpenStreetMap + Wikidata) into data/springs-world.json for the app.

Springs in the United States and Canada are skipped: those come from the official sources in springs.json.
OSM features of the same spring (a node and an area, or near-duplicates) are merged, then Wikidata items are
matched to OSM by their wikidata tag or by distance. Countries come from Wikidata, else the nearest GeoNames place.
The soaking estimate is a first pass from OSM tags and names only:
  D commercial  public bath, spa/resort/onsen-type names, or a fee
  W wild        tagged for bathing or swimming, no fee
  N unlikely    bathing/swimming=no, private access, or 70 C or hotter at the source
  U no evidence otherwise
Run: python3 tools/world_rows.py   (needs: pip install reverse_geocoder pycountry)
"""
import json, math, re, sys
from collections import Counter, defaultdict
import reverse_geocoder as rg, pycountry

raw = json.load(open('data/world_raw.json'))
us = json.load(open('data/springs.json'))['springs']

def km(a, b, c, d):
    t = math.pi / 180; x = (c - a) * t; y = (d - b) * t
    h = math.sin(x / 2) ** 2 + math.cos(a * t) * math.cos(c * t) * math.sin(y / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

def grid(points, cell=0.05):
    g = defaultdict(list)
    for i, p in enumerate(points): g[(int(p[0] // cell), int(p[1] // cell))].append(i)
    return g

def near(g, pts, lat, lon, r_km, cell=0.05):
    ci, cj = int(lat // cell), int(lon // cell); out = []
    span = max(1, int(math.ceil(r_km / 111 / cell)) + 1)
    for di in range(-span, span + 1):
        for dj in range(-span, span + 1):
            for i in g.get((ci + di, cj + dj), []):
                if km(lat, lon, pts[i][0], pts[i][1]) <= r_km: out.append(i)
    return out

def temp_c(v):
    if v is None: return None
    s = str(v).strip().lower().replace(',', '.')
    m = re.search(r'-?\d+(\.\d+)?', s)
    if not m: return None
    x = float(m.group())
    if 'f' in s and 'c' not in s: x = (x - 32) * 5 / 9
    elif s.endswith('k'): x -= 273.15
    return x if 5 <= x <= 105 else None

# ---- OSM: merge features of the same spring (same name within 400 m, or anything within 60 m)
osm = []
for lat, lon, t in raw.get('osm', []):
    osm.append({'lat': lat, 'lon': lon, 't': t, 'ids': [t.get('_id')]})
pts = [(o['lat'], o['lon']) for o in osm]; g = grid(pts)
dead = set()
def nm(t): return (t.get('name:en') or t.get('name') or '').strip().lower()
for i, o in enumerate(osm):
    if i in dead: continue
    for j in near(g, pts, o['lat'], o['lon'], 0.4):
        if j <= i or j in dead: continue
        p = osm[j]; same = nm(o['t']) and nm(o['t']) == nm(p['t'])
        if same or km(o['lat'], o['lon'], p['lat'], p['lon']) <= 0.06:
            for k, v in p['t'].items(): o['t'].setdefault(k, v)
            o['ids'] += p['ids']; dead.add(j)
osm = [o for i, o in enumerate(osm) if i not in dead]

# ---- Wikidata: attach to OSM by wikidata tag, else nearest OSM within 1 km (or same name within 3 km)
by_q = {o['t'].get('wikidata'): o for o in osm if o['t'].get('wikidata')}
pts = [(o['lat'], o['lon']) for o in osm]; g = grid(pts)
for w in raw.get('wd', []):
    o = by_q.get(w['qid'])
    if not o:
        wn = (w.get('en') or w.get('name') or '').lower()
        cands = sorted(near(g, pts, w['lat'], w['lon'], 3), key=lambda i: km(w['lat'], w['lon'], *pts[i]))
        for i in cands:
            if km(w['lat'], w['lon'], *pts[i]) <= 1 or (wn and nm(osm[i]['t']) == wn):
                o = osm[i]; break
    if o and 'wd' not in o: o['wd'] = w
    else:
        osm.append({'lat': w['lat'], 'lon': w['lon'], 't': {}, 'ids': [], 'wd': w})

# ---- skip anything already covered (US/Canada) and assign countries
usg = grid([(r[2], r[3]) for r in us]); usp = [(r[2], r[3]) for r in us]
geo = rg.search([(o['lat'], o['lon']) for o in osm], mode=1, verbose=False)
COUNTRY = {}
def c3(cc2):
    c = pycountry.countries.get(alpha_2=cc2)
    return (c.alpha_3, getattr(c, 'common_name', None) or c.name) if c else (cc2, cc2)

COMM = re.compile(r'\b(spa|resort|onsen|ryokan|therme|thermen|terme|termas|thermae|balneario|bad|baths?|bathhouse|banos?|baños|'
                  r'kaplıcası?|kaplica|hammam|piscinas?|aquapark|lagoon|hotel|wellness|thermal bath|thermalbad|fürdő|furdo|lázně|lazne|'
                  r'ilıcası?|toplice|banya|banja|hot pools?)\b', re.I)
rows = []; skipped = Counter()
for o, gg in zip(osm, geo):
    w = o.get('wd') or {}; t = o['t']
    cc = gg['cc']
    if w.get('iso3'):
        iso3 = w['iso3']; c = pycountry.countries.get(alpha_3=iso3)
        cname = (getattr(c, 'common_name', None) or c.name) if c else w.get('country', iso3)
    else:
        iso3, cname = c3(cc)
    if iso3 in ('USA', 'CAN') or cc in ('US', 'CA'):
        skipped['US/Canada'] += 1; continue
    if near(usg, usp, o['lat'], o['lon'], 1.5):
        skipped['already listed'] += 1; continue
    COUNTRY[iso3] = cname
    en = t.get('name:en') or t.get('int_name') or w.get('en')
    native = t.get('name') or w.get('name')
    name = en or native or ''
    alt = native if native and native != name else ''
    tc = temp_c(t.get('temperature'))
    if tc is None and w.get('temp'):
        v, u = w['temp']; tc = temp_c(f'{v} {u}')
    f = round(tc * 9 / 5 + 32) if tc is not None else None
    c = round(tc) if tc is not None else None
    # soaking estimate
    tagtxt = ' '.join(str(t.get(k, '')) for k in ('name', 'name:en', 'alt_name', 'official_name', 'int_name'))
    yes = lambda k: str(t.get(k, '')).lower() in ('yes', 'designated')
    no = lambda k: str(t.get(k, '')).lower() == 'no'
    if t.get('amenity') == 'public_bath' or t.get('leisure') in ('resort', 'water_park', 'sports_centre') or t.get('tourism') == 'hotel':
        rec = ['D', 'Public bath or resort (OpenStreetMap)']
    elif yes('fee'):
        rec = ['D', 'Entry fee listed (OpenStreetMap)']
    elif no('bathing') or no('swimming') or str(t.get('access', '')).lower() in ('no', 'private'):
        rec = ['N', 'Tagged no bathing or private (OpenStreetMap)']
    elif yes('bathing') or yes('swimming') or t.get('leisure') == 'bathing_place':
        rec = ['W', 'Tagged for bathing (OpenStreetMap)']
    elif COMM.search(tagtxt) or COMM.search(w.get('en') or ''):
        rec = ['D', 'Name suggests a bath or spa']
    elif tc is not None and tc >= 70:
        rec = ['N', 'Very hot at the source']
    else:
        rec = ['U', '']
    src = ('O' if o['ids'] else '') + ('W' if w else '')
    rows.append([name, iso3, o['lat'], o['lon'], f, c, rec[0], rec[1], gg.get('admin1') or '', src,
                 w.get('enwiki') or '', w.get('image') or '', (o['ids'] or [''])[0], w.get('qid') or '', alt])

rows.sort(key=lambda r: (r[1], r[8], r[0]))
out = {
    'fields': ['name', 'country', 'lat', 'lon', 'temp_f', 'temp_c', 'soak', 'soak_note', 'region', 'sources', 'enwiki', 'commons_image', 'osm_id', 'wikidata', 'native_name'],
    'countries': dict(sorted(COUNTRY.items())),
    'source': 'OpenStreetMap contributors (ODbL 1.0, openstreetmap.org/copyright) and Wikidata (CC0). Regions from GeoNames (CC BY 4.0) via reverse_geocoder.',
    'springs': rows,
}
json.dump(out, open('data/springs-world.json', 'w'), separators=(',', ':'), ensure_ascii=False)
cnt = Counter(r[1] for r in rows); soak = Counter(r[6] for r in rows)
print('rows', len(rows), 'skipped', dict(skipped), 'soak', dict(soak))
print('named', sum(1 for r in rows if r[0]), 'with temp', sum(1 for r in rows if r[4] is not None))
for k, v in cnt.most_common(40): print(f'  {k} {COUNTRY[k]}: {v}')
