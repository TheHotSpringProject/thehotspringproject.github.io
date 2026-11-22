"""Find more spring photos from two free sources (runs in GitHub Actions; this workspace can't reach Wikimedia).

1. Wikidata: hot springs in the US and Canada that have an image (P18) and coordinates. Matched to our springs
   within 1 km, or within 5 km when a distinctive word of the name matches. CC0 data; the photos are on Commons.
2. Wikimedia Commons categories named after the spring, e.g. "Category:Jerry Johnson Hot Springs" or
   "Category:Burgdorf Hot Springs (Idaho)". Only names with a distinctive word are tried (not "Hot Springs" or
   "Soda Spring"), and a photo is rejected if it is geotagged more than 25 km from the spring.
Every photo must be a JPEG/PNG at least 800 px wide under a CC BY/BY-SA/CC0/public-domain licence.
Results are added to data/photos.json without replacing photos already there.
"""
import json, math, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(line_buffering=True)
API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'TheHotSpringProject/1.0 (https://thehotspringproject.github.io/; photo matching for a hot springs map)'}
springs = json.load(open('data/springs.json'))['springs']
media = json.load(open('data/media.json'))['m']
PH = json.load(open('data/photos.json'))
have = {k for k, v in media.items() if len(v) > 1 and v[1]} | set(PH['p'])
STATE = {'AK':'Alaska','AL':'Alabama','AR':'Arkansas','AZ':'Arizona','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware',
 'FL':'Florida','GA':'Georgia','HI':'Hawaii','IA':'Iowa','ID':'Idaho','IL':'Illinois','IN':'Indiana','KS':'Kansas','KY':'Kentucky','LA':'Louisiana',
 'MA':'Massachusetts','MD':'Maryland','ME':'Maine','MI':'Michigan','MN':'Minnesota','MO':'Missouri','MS':'Mississippi','MT':'Montana',
 'NC':'North Carolina','ND':'North Dakota','NE':'Nebraska','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NV':'Nevada','NY':'New York',
 'OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','PR':'Puerto Rico','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota',
 'TN':'Tennessee','TX':'Texas','UT':'Utah','VA':'Virginia','VT':'Vermont','WA':'Washington','WI':'Wisconsin','WV':'West Virginia','WY':'Wyoming',
 'BC':'British Columbia','AB':'Alberta','YT':'Yukon','NT':'Northwest Territories','NU':'Nunavut'}
GENERIC = {'hot','warm','springs','spring','the','and','creek','river','lake','upper','lower','north','south','east','west','big','little','old',
 'new','mineral','sulphur','sulfur','thermal','group','well','wells','resort','unnamed','near','basin','canyon','valley','mountain','mount','park',
 'ranch','camp','city','county','fork','road','station','area','state','national','forest','main','blue','green','white','black','salt','soda',
 'iron','cold','dead','santa','san','fort','big','boiling','lithia','magnesia','seep','seeps','pool','pools','bath','baths',
 'fumarole','fumaroles','mudpot','mudpots','geyser','geysers','vent','vents','sink','gas','coastal','sampling','drinking','tunnel'}
FREE = re.compile(r'cc[- ]?by|cc0|public domain|\bpd\b|pd-|attribution', re.I)
NOTFREE = re.compile(r'\bnc\b|non[- ]?commercial|\bnd\b|no[- ]?deriv|fair use|non-free', re.I)
BAD = re.compile(r'routes?\b|newspaper|register|herald|\(page \d|advert|trail \(|atv|\bmap\b|locator|logo|diagram|chart|\bsign\b|signage|plaque|portrait|\bseal\b|coat of arms|flag of|screenshot|postcard back|'
                 r'menu|ticket|\.svg$|\.tiff?$|\.pdf$|\.djvu$', re.I)

def api(params, tries=4):
    params = dict(params, format='json', formatversion=2, maxlag=5)
    data = urllib.parse.urlencode(params).encode()
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(API, data=data, headers=UA), timeout=60) as r:
                j = json.loads(r.read())
            if 'error' in j and j['error'].get('code') == 'maxlag': time.sleep(5 + 5 * k); continue
            return j
        except Exception as e:
            print('  retry', k, repr(e)[:80]); time.sleep(5 + 10 * k)
    return {}

def km(a, b, c, d):
    t = math.pi / 180; x = (c - a) * t; y = (d - b) * t
    h = math.sin(x / 2) ** 2 + math.cos(a * t) * math.cos(c * t) * math.sin(y / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

def tokens(name):
    return [w for w in re.findall(r"[a-z]+", name.lower()) if len(w) >= 4 and w not in GENERIC and w.title() not in STATE.values()]

def good_files(titles, near=None):
    """Return the usable files among titles (in order), checking licence, size, type and geotag distance."""
    out = []
    titles = [t for t in titles if re.search(r'\.(jpe?g|png)$', t, re.I) and not BAD.search(t)]
    for k in range(0, len(titles), 50):
        j = api({'action': 'query', 'titles': '|'.join(titles[k:k + 50]), 'prop': 'imageinfo|coordinates',
                 'iiprop': 'size|mime|extmetadata', 'iiextmetadatafilter': 'LicenseShortName'})
        pages = {p['title']: p for p in (j.get('query') or {}).get('pages', [])}
        for t in titles[k:k + 50]:
            p = pages.get(t); ii = p and p.get('imageinfo') and p['imageinfo'][0]
            if not ii or ii.get('width', 0) < 800 or ii.get('mime') not in ('image/jpeg', 'image/png'): continue
            lic = ((ii.get('extmetadata') or {}).get('LicenseShortName') or {}).get('value', '')
            if not FREE.search(lic) or NOTFREE.search(lic): continue
            if near and p.get('coordinates'):
                c = p['coordinates'][0]
                if km(near[0], near[1], c['lat'], c['lon']) > 25: continue
            out.append(t)
    return out

added = {}
# ---------- 1. Wikidata images ----------
try:
    q = '''SELECT ?item ?coord ?image ?label WHERE {
      ?item wdt:P31/wdt:P279* wd:Q177380 ; wdt:P625 ?coord ; wdt:P18 ?image ; wdt:P17 ?c .
      VALUES ?c { wd:Q30 wd:Q16 }
      OPTIONAL { ?item rdfs:label ?label . FILTER(LANG(?label) = "en") } }'''
    req = urllib.request.Request('https://query.wikidata.org/sparql?' + urllib.parse.urlencode({'query': q, 'format': 'json'}),
                                 headers=dict(UA, Accept='application/sparql-results+json'))
    with urllib.request.urlopen(req, timeout=300) as r:
        rows = json.loads(r.read())['results']['bindings']
    wd = []
    for b in rows:
        c = b['coord']['value'].replace('Point(', '').replace(')', '').split()
        try: lon, lat = float(c[0]), float(c[1])
        except Exception: continue
        f = 'File:' + urllib.parse.unquote(b['image']['value'].rsplit('/', 1)[1]).replace('_', ' ')
        wd.append((lat, lon, f, b.get('label', {}).get('value', '')))
    print('wikidata items with images', len(wd))
    cand = {}
    for i, r in enumerate(springs):
        if str(i) in have: continue
        tk = tokens(r[0] or '')
        for lat, lon, f, lab in wd:
            if abs(lat - r[2]) > 0.06 or abs(lon - r[3]) > 0.08: continue
            d = km(r[2], r[3], lat, lon)
            nm = any(re.search(r'\b' + re.escape(w), lab, re.I) for w in tk)
            named = r[0] and not re.match('unnamed', r[0], re.I)
            if (d <= 5 and nm) or (d <= 0.3 and named):
                if str(i) not in cand or d < cand[str(i)][0]: cand[str(i)] = (d, f)
    ok = set(good_files(sorted({f for _, f in cand.values()})))
    for k, (d, f) in cand.items():
        if f in ok: added[k] = f; print('wikidata', springs[int(k)][0], '->', f)
except Exception as e:
    print('wikidata failed', repr(e)[:200])
have |= set(added)

# ---------- 2. Commons categories named after the spring ----------
SPRINGWORD = re.compile(r'springs?\b|sprs?\b|geyser|hot pool|blue hole|sink\b|warm|hot\b', re.I)
def variants(name, st):
    out = []
    for part in [re.sub(r'\s*\([^)]*\)', '', name).split(',')[0]] + re.split(r',|;|\(|\)', name):
        part = re.sub(r'\s+(near|nr|at|in|above|below)\s+.*$', '', part.strip(), flags=re.I)
        part = re.sub(r'\bSprs?\b\.?', 'Springs', part)
        if not part or not tokens(part) or not SPRINGWORD.search(part): continue
        t = ' '.join(w if (w.isupper() and len(w) <= 3 and w not in ('HOT',)) else w.capitalize() for w in part.split())
        for base in {t, t.replace(' Hot Spring', ' Hot Springs') if not t.endswith('Springs') else t}:
            out += [base, f'{base} ({STATE.get(st, st)})', f'{base}, {STATE.get(st, st)}']
    return list(dict.fromkeys(out))

todo = [(i, r) for i, r in enumerate(springs) if r[0] and str(i) not in have and not re.match('unnamed', r[0], re.I)]
want = {}
for i, r in todo:
    for v in variants(r[0], r[1]): want.setdefault('Category:' + v, []).append(i)
print('springs', len(todo), 'category names to try', len(want))
cats = list(want); exist = []
for k in range(0, len(cats), 50):
    j = api({'action': 'query', 'titles': '|'.join(cats[k:k + 50]), 'redirects': 1, 'prop': 'categories', 'cllimit': 'max'})
    q = j.get('query') or {}
    norm = {n['from']: n['to'] for n in q.get('normalized', [])}
    redir = {n['from']: n['to'] for n in q.get('redirects', [])}
    # skip categories for towns (Pagosa Springs, Hot Springs, Palm Springs...): their photos are of the town
    TOWN = re.compile(r'cities|towns|villages|populated places|unincorporated communities|census-designated|county seats|municipalities|neighbo', re.I)
    present = set()
    for p in q.get('pages', []):
        if p.get('missing') or p.get('invalid'): continue
        parents = ' '.join(c['title'] for c in p.get('categories', []))
        if TOWN.search(parents) or not SPRINGWORD.search(p['title']): continue
        present.add(p['title'])
    for c in cats[k:k + 50]:
        t = redir.get(norm.get(c, c), norm.get(c, c))
        if t in present: exist.append((c, t))
    time.sleep(0.2)
print('categories found', len(exist))
done = set()
for c, t in exist:
    for i in want[c]:
        if str(i) in have or i in done: continue
        r = springs[i]
        j = api({'action': 'query', 'list': 'categorymembers', 'cmtitle': t, 'cmtype': 'file', 'cmlimit': 40})
        files = [m['title'] for m in (j.get('query') or {}).get('categorymembers', [])]
        g = good_files(files, near=(r[2], r[3]))
        if g:
            # prefer a file whose name mentions the spring, else the first usable one
            tk = tokens(r[0])
            g.sort(key=lambda f: -sum(1 for w in tk if re.search(r'\b' + re.escape(w), f, re.I)))
            added[str(i)] = g[0]; done.add(i); print('category', r[0], '|', t, '->', g[0])
        time.sleep(0.2)

PH['p'].update({k: v for k, v in added.items() if k not in PH['p']})
PH['p'] = dict(sorted(PH['p'].items(), key=lambda x: int(x[0])))
PH['source'] = ('Wikimedia Commons photos: files geotagged at the spring and matched by file name, the image on the spring\'s '
                'Wikidata item, or files in a Commons category named after the spring. Freely licensed (CC BY, CC BY-SA, CC0, public domain).')
json.dump(PH, open('data/photos.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('added', len(added), 'total', len(PH['p']))
