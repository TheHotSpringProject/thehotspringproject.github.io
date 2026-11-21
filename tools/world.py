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

# 1. OpenStreetMap, in 30 x 60 degree tiles so no single query is too large
try:
    seen = set(); n_tiles = 0
    for s in range(-90, 90, 30):
        for w in range(-180, 180, 60):
            bb = f'{s},{w},{s + 30},{w + 60}'
            q = f'''[out:json][timeout:600];
(nwr["natural"="hot_spring"]({bb});
 nwr["amenity"="public_bath"]["bath:type"~"^(hot_spring|onsen)$"]({bb});
 nwr["leisure"="hot_spring"]({bb}););
out center tags;'''
            res = overpass(q); n_tiles += 1; got = 0
            for el in res.get('elements', []):
                key = el['type'][0] + str(el['id'])
                if key in seen: continue
                seen.add(key)
                lat = el.get('lat', el.get('center', {}).get('lat')); lon = el.get('lon', el.get('center', {}).get('lon'))
                if lat is None: continue
                tags = {k: v for k, v in el.get('tags', {}).items() if k in KEEP or k.startswith('name:')}
                # keep only a few language names to stay small
                tags = {k: v for k, v in tags.items() if not k.startswith('name:') or k in ('name:en', 'name:ja', 'name:es', 'name:is', 'name:de', 'name:fr', 'name:it')}
                tags['_id'] = key
                OUT['osm'].append([round(lat, 5), round(lon, 5), tags]); got += 1
            print(f'tile {bb}: {got}')
            time.sleep(4)
    print('osm total', len(OUT['osm']))
except Exception as e:
    OUT['notes'].append('osm failed: %r' % e); print('osm failed', e)
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
        d = by.setdefault(qid, {'qid': qid, 'name': v.get('itemLabel'), 'en': v.get('enLabel'),
                                'lon': round(float(c[0]), 5), 'lat': round(float(c[1]), 5)})
        if v.get('iso3'): d['iso3'] = v['iso3']
        if v.get('countryLabel'): d['country'] = v['countryLabel']
        if v.get('temp') and v.get('unit'):
            u = v['unit'].rsplit('/', 1)[1]
            d['temp'] = [float(v['temp']), {'Q25267': 'C', 'Q42289': 'F', 'Q11579': 'K'}.get(u, u)]
        if v.get('image'): d['image'] = urllib.parse.unquote(v['image'].rsplit('/', 1)[1])
        if v.get('enwiki'): d['enwiki'] = urllib.parse.unquote(v['enwiki'].rsplit('/', 1)[1]).replace('_', ' ')
    OUT['wd'] = list(by.values()); print('wikidata items', len(OUT['wd']))
except Exception as e:
    OUT['notes'].append('wikidata failed: %r' % e); print('wikidata failed', e)
    OUT['wd'] = PREV.get('wd', [])

json.dump(OUT, open('data/world_raw.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('notes', OUT['notes'])
