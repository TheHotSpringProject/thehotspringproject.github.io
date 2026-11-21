"""Fetch hot springs worldwide (runs in GitHub Actions; this workspace can't reach these sites).

Sources
  1. OpenStreetMap via the Overpass API: natural=hot_spring, plus public baths tagged as hot-spring or onsen baths
     (amenity=public_bath with bath:type=hot_spring/onsen). Data (c) OpenStreetMap contributors, ODbL 1.0.
  2. Wikidata: items that are instances of hot spring (Q177380) or a subclass, with coordinates. CC0.
Output: data/world_raw.json  {"osm": [[lat, lon, {tags}], ...], "wd": [{...}], "notes": [...]}
Earlier results are kept for any source that fails this time.
"""
import json, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(line_buffering=True)

UA = {'User-Agent': 'TheHotSpringProject/1.0 (https://thehotspringproject.github.io/; map of hot springs)'}
try:
    PREV = json.load(open('data/world_raw.json'))
except Exception:
    PREV = {}
OUT = {'osm': [], 'wd': [], 'notes': []}

KEEP = {'name', 'name:en', 'int_name', 'official_name', 'alt_name', 'natural', 'amenity', 'leisure', 'tourism', 'bath:type',
        'bathing', 'swimming', 'fee', 'access', 'temperature', 'wikidata', 'wikipedia', 'website', 'opening_hours', 'description'}

def post(url, data, timeout):
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode(), headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

MIRRORS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter',
           'https://overpass.private.coffee/api/interpreter']

def overpass(q):
    last = None
    for attempt in range(6):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            return post(url, {'data': q}, 700)
        except Exception as e:
            last = e; print('  overpass retry', attempt, url, repr(e)[:120]); time.sleep(20 + 20 * attempt)
    raise last

# 1. OpenStreetMap. A worldwide query by tag uses Overpass's tag index and is usually quick; if the servers refuse it,
# fall back to 20-degree tiles. Progress is kept in data/world_raw.json so a later run only fetches missing tiles.
KEEP_NAMES = ('name:en', 'name:ja', 'name:es', 'name:is', 'name:de', 'name:fr', 'name:it')
QUERIES = ['nwr["natural"="hot_spring"]{bb};', 'nwr["amenity"="public_bath"]["bath:type"~"^(hot_spring|onsen)$"]{bb};', 'nwr["leisure"="hot_spring"]{bb};']
seen = set(); OUT['osm'] = []
def add(res):
    got = 0
    for el in res.get('elements', []):
        key = el['type'][0] + str(el['id'])
        if key in seen: continue
        lat = el.get('lat', el.get('center', {}).get('lat')); lon = el.get('lon', el.get('center', {}).get('lon'))
        if lat is None: continue
        seen.add(key)
        tags = {k: v for k, v in el.get('tags', {}).items() if (k in KEEP and not k.startswith('name:')) or k in KEEP_NAMES}
        tags['_id'] = key
        OUT['osm'].append([round(lat, 5), round(lon, 5), tags]); got += 1
    return got
def run(q, timeout, tries):
    last = None
    for attempt in range(tries):
        url = MIRRORS[attempt % len(MIRRORS)]
        try:
            return post(url, {'data': q}, timeout + 30)
        except Exception as e:
            last = e; print('  retry', attempt, url.split('/')[2], repr(e)[:90]); time.sleep(15 + 15 * attempt)
    raise last
T0 = time.time(); failed = []
for qq in QUERIES:
    try:
        res = run(f'[out:json][timeout:400];({qq.format(bb="")});out center tags;', 400, 4)
        print('global', qq[:40], add(res))
    except Exception as e:
        print('global query failed, using tiles:', qq[:40], repr(e)[:80])
        for s_ in range(-60, 80, 20):
            for w_ in range(-180, 180, 20):
                if time.time() - T0 > 65 * 60: failed.append((qq, s_, w_)); continue
                bb = f'({s_},{w_},{s_ + 20},{w_ + 20})'
                try:
                    res = run(f'[out:json][timeout:150];({qq.format(bb=bb)});out center tags;', 150, 3)
                    n = add(res)
                    if n: print('  tile', bb, n)
                except Exception as e2:
                    failed.append((qq, s_, w_)); print('  tile failed', bb)
                time.sleep(2)
print('osm total', len(OUT['osm']), 'failed tiles', len(failed))
if failed:
    OUT['notes'].append('osm tiles failed: %d' % len(failed))
    # keep earlier features for areas that failed this time
    for lat, lon, t in PREV.get('osm', []):
        if t.get('_id') not in seen: OUT['osm'].append([lat, lon, t]); seen.add(t.get('_id'))
if not OUT['osm']:
    OUT['osm'] = PREV.get('osm', [])

# 2. Wikidata
SPARQL = '''SELECT ?item ?itemLabel ?enLabel ?coord ?iso3 ?countryLabel ?temp ?unit ?image ?enwiki WHERE {
  ?item wdt:P31/wdt:P279* wd:Q177380 ; wdt:P625 ?coord .
  OPTIONAL { ?item wdt:P17 ?country . ?country wdt:P298 ?iso3 . }
  OPTIONAL { ?item p:P2076/psv:P2076 [ wikibase:quantityAmount ?temp ; wikibase:quantityUnit ?unit ] . }
  OPTIONAL { ?item wdt:P18 ?image . }
  OPTIONAL { ?item rdfs:label ?enLabel . FILTER(LANG(?enLabel) = "en") }
  OPTIONAL { ?enwiki schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul,ja,es,is,de,fr,it,hu,zh,ko,tr,el,ru" . }
}'''
try:
    req = urllib.request.Request('https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': SPARQL, 'format': 'json'}),
                                 headers=dict(UA, Accept='application/sparql-results+json'))
    with urllib.request.urlopen(req, timeout=300) as r:
        rows = json.loads(r.read())['results']['bindings']
    by = {}
    for b in rows:
        v = {k: x['value'] for k, x in b.items()}
        qid = v['item'].rsplit('/', 1)[1]
        c = v['coord'].replace('Point(', '').replace(')', '').split()
        try: float(c[0]); float(c[1])
        except (ValueError, IndexError): continue
        d = by.setdefault(qid, {'qid': qid, 'name': v.get('itemLabel'), 'en': v.get('enLabel'),
                                'lon': round(float(c[0]), 5), 'lat': round(float(c[1]), 5)})
        if v.get('iso3'): d['iso3'] = v['iso3']
        if v.get('countryLabel'): d['country'] = v['countryLabel']
        if v.get('temp') and v.get('unit'):
            u = v['unit'].rsplit('/', 1)[1]
            try: d['temp'] = [float(v['temp']), {'Q25267': 'C', 'Q42289': 'F', 'Q11579': 'K'}.get(u, u)]
            except ValueError: pass   # "unknown value" placeholders
        try: float(c[0]); float(c[1])
        except (ValueError, IndexError): continue
        if v.get('image'): d['image'] = urllib.parse.unquote(v['image'].rsplit('/', 1)[1])
        if v.get('enwiki'): d['enwiki'] = urllib.parse.unquote(v['enwiki'].rsplit('/', 1)[1]).replace('_', ' ')
    OUT['wd'] = list(by.values()); print('wikidata items', len(OUT['wd']))
except Exception as e:
    OUT['notes'].append('wikidata failed: %r' % e); print('wikidata failed', e)
    OUT['wd'] = PREV.get('wd', [])

json.dump(OUT, open('data/world_raw.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('notes', OUT['notes'])
