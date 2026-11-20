"""Build data/named_springs.json: every spring in the USGS Geographic Names Information System (GNIS, public domain)
that isn't already one of the app's main springs, with a Water Quality Portal temperature attached where a spring
site with a matching name lies within 1 km (or any site within 200 m). Loaded by the app only when the
"Named springs" layer is switched on.
Rows: [name, state, lat, lon, temp_f or null, year or null]"""
import csv, io, json, math, re, urllib.request, zipfile, os
from collections import defaultdict
URL = 'https://prd-tnm.s3.amazonaws.com/StagedProducts/GeographicNames/DomesticNames/DomesticNames_National_Text.zip'
ST = {'Alabama':'AL','Alaska':'AK','Arizona':'AZ','Arkansas':'AR','California':'CA','Colorado':'CO','Connecticut':'CT','Delaware':'DE','District of Columbia':'DC','Florida':'FL','Georgia':'GA','Hawaii':'HI','Idaho':'ID','Illinois':'IL','Indiana':'IN','Iowa':'IA','Kansas':'KS','Kentucky':'KY','Louisiana':'LA','Maine':'ME','Maryland':'MD','Massachusetts':'MA','Michigan':'MI','Minnesota':'MN','Mississippi':'MS','Missouri':'MO','Montana':'MT','Nebraska':'NE','Nevada':'NV','New Hampshire':'NH','New Jersey':'NJ','New Mexico':'NM','New York':'NY','North Carolina':'NC','North Dakota':'ND','Ohio':'OH','Oklahoma':'OK','Oregon':'OR','Pennsylvania':'PA','Rhode Island':'RI','South Carolina':'SC','South Dakota':'SD','Tennessee':'TN','Texas':'TX','Utah':'UT','Vermont':'VT','Virginia':'VA','Washington':'WA','West Virginia':'WV','Wisconsin':'WI','Wyoming':'WY','Puerto Rico':'PR'}
GEN = set('HOT WARM SPRING SPRINGS SPGS SPG SPR THERMAL UNNAMED UNKNOWN NO NUMBER AREA GROUP WELL AT NEAR NR THE OF AND COUNTY CO NORTH SOUTH EAST WEST UPPER LOWER LITTLE BIG OLD NEW'.split())
def toks(s): return {w[:-1] if w.endswith('S') else w for w in re.sub(r'[^A-Z ]', ' ', (s or '').upper()).split() if len(w) > 2 and w not in GEN}
def km(a, b, c, d):
    t = math.pi / 180; x = (c - a) * t; y = (d - b) * t
    h = math.sin(x / 2) ** 2 + math.cos(a * t) * math.cos(c * t) * math.sin(y / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
def grid(points):               # 0.05-degree buckets for quick neighbour lookups
    g = defaultdict(list)
    for p in points: g[(int(p[0] // 0.05), int(p[1] // 0.05))].append(p)
    return g
def near(g, lat, lon):
    a, b = int(lat // 0.05), int(lon // 0.05)
    for i in (a - 1, a, a + 1):
        for j in (b - 1, b, b + 1): yield from g.get((i, j), ())

with urllib.request.urlopen(urllib.request.Request(URL, headers={'User-Agent': 'hotsprings-map'}), timeout=600) as r:
    z = zipfile.ZipFile(io.BytesIO(r.read()))
name = [n for n in z.namelist() if n.lower().endswith('.txt')][0]
G = []
with z.open(name) as fh:
    for r in csv.DictReader(io.TextIOWrapper(fh, 'utf-8-sig', errors='replace'), delimiter='|'):
        if r.get('feature_class') != 'Spring': continue
        try: lat, lon = float(r['prim_lat_dec']), float(r['prim_long_dec'])
        except ValueError: continue
        if not lat or not lon: continue
        G.append([r['feature_name'].strip(), ST.get(r.get('state_name') or '', ''), round(lat, 5), round(lon, 5)])
print('GNIS springs:', len(G))

main = json.load(open('data/springs.json'))['springs']
mg = grid([(r[2], r[3], toks(r[0])) for r in main])
wq = json.load(open('/tmp/wqp_sites.json')) if os.path.exists('/tmp/wqp_sites.json') else []
wg = grid([(w[2], w[3], toks(w[0]), w[4], w[5]) for w in wq if w[4] is not None])
out, dup, temps = [], 0, 0
for nm, st, lat, lon in G:
    tk = toks(nm)
    if any((d := km(lat, lon, p[0], p[1])) < 0.15 or (d < 0.6 and tk & p[2]) for p in near(mg, lat, lon)): dup += 1; continue
    best = None
    for p in near(wg, lat, lon):
        d = km(lat, lon, p[0], p[1])
        if d < 0.2 or (d < 1 and tk & p[2]):
            k = (not (tk & p[2]), d)
            if best is None or k < best[0]: best = (k, p)
    f = yr = None
    if best: f, yr = round(best[1][3] * 9 / 5 + 32), best[1][4]; temps += 1
    out.append([nm, st, round(lat, 4), round(lon, 4), f, yr])
json.dump({'source': 'U.S. Geological Survey, Geographic Names Information System (GNIS), feature class Spring; temperatures from the Water Quality Portal (USGS, EPA, National Park Service and others) where a spring site matches.',
           'fields': ['name', 'state', 'lat', 'lon', 'temp_f', 'year'], 'springs': out}, open('data/named_springs.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('named springs:', len(out), '| skipped as main springs:', dup, '| with temperature:', temps)
