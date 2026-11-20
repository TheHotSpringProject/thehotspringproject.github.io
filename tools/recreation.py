"""Build data/recreation.json: an estimate of whether people soak in each spring at or above 90 F.
Order of precedence: hand judgements (tools/rec_judgement.py) > fixed rules (no-soaking parks, military land) >
web evidence in data/rec_evidence.json (OpenStreetMap, Wikipedia) > temperature/land fallbacks.
Keyed by "lat,lon" rounded to 3 decimals so it survives reordering of data/springs.json.
Codes: D known soaking spot, commercial; W known soaking spot, wild; P possibly used, N unlikely or not allowed, U no evidence found."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from rec_judgement import J, CA
S = json.load(open('data/springs.json'))['springs']
E = json.load(open('data/rec_evidence.json')) if os.path.exists('data/rec_evidence.json') else {}
NOPARK = re.compile(r"Yellowstone National Park|Lassen Volcanic|Hawai.i Volcanoes|Mount Rainier National Park|Wind Cave|Mammoth Cave|Valles Caldera|Craters of the Moon|Ash Meadows")
DEV_KIND = {'public_bath', 'swimming_pool', 'water_park', 'resort', 'spa', 'sports_centre', 'hotel', 'guest_house', 'camp_site'}
out, why_src = {}, {}
RANK = {'hand': 0, 'rule': 1, 'osm': 2, 'fallback': 3}
basis = {}
def put(r, code, why, src):
    k = f'{r[2]:.3f},{r[3]:.3f}'
    if k in basis and RANK[basis[k]] <= RANK[src]: return          # two records at one spot: the better-founded call wins
    out[k] = [code, why]; basis[k] = src; why_src[src] = why_src.get(src, 0) + 1
for i, r in enumerate(S):
    if r[11] == 'C':   # Canada: judged by name; otherwise only temperature-based fallbacks (no land database north of the border)
        if r[0] in CA: put(r, CA[r[0]][0], CA[r[0]][1], 'hand'); continue
        if r[4] is None or r[4] < 90: continue
        if r[4] >= 160: put(r, 'N', 'Scalding at the source, with no sign of soaking pools', 'fallback'); continue
        put(r, 'P', 'Warm, probably on Crown land, but no sign of regular use was found', 'fallback'); continue
    if r[4] is None or r[4] < 90: continue
    if i in J:
        name, code, why = J[i]
        assert name.upper()[:5] in r[0].upper(), (i, name, r[0])
        put(r, code, why, 'hand'); continue
    land = r[8] or []; unit = (land[2] if len(land) > 2 else '') or ''
    if NOPARK.search(unit): put(r, 'N', 'In ' + unit + ', where thermal features are off-limits to soaking', 'rule'); continue
    if land and land[0] == 'M': put(r, 'N', 'On military land (' + unit + ')', 'rule'); continue
    ev = E.get(str(i), {}); osm = [o for o in ev.get('osm', []) if o[2] <= 400]; wiki = ev.get('wiki', [])
    dev = [o for o in osm if o[0] in DEV_KIND or (o[0] == 'hot_spring' and any(k in o[3] for k in ('fee', 'opening_hours', 'website', 'operator')))]
    dev = [o for o in dev if (o[3].get('access') or '') not in ('private', 'no')]
    wild = [o for o in osm if (o[0] == 'hot_spring' and o[3].get('bathing') == 'yes') or o[0] == 'bathing_place']
    closed = [o for o in osm if o[3].get('access') in ('private', 'no') or o[3].get('bathing') == 'no']
    wk_dev = [w for w in wiki if w[1] <= 1000 and set(w[2]) & {'resort', 'spa', 'pool', 'pools', 'bathhouse', 'bathhouses', 'lodge', 'commercial', 'developed'} and re.search(r'(?i)spring|bath|resort|spa', w[0])]
    wk_wild = [w for w in wiki if w[1] <= 1000 and set(w[2]) & {'soak', 'soaking', 'bathing', 'bathe', 'swim', 'swimming', 'clothing-optional', 'clothing optional', 'nude', 'nudity', 'popular'} and re.search(r'(?i)spring|pool', w[0])]
    wk_closed = [w for w in wiki if w[1] <= 1000 and set(w[2]) & {'closed', 'private', 'prohibited', 'off-limits', 'off limits', 'dangerous', 'scalding'} and re.search(r'(?i)spring', w[0])]
    nm = lambda o: o[1] or o[0].replace('_', ' ')
    if dev: put(r, 'D', 'OpenStreetMap shows ' + nm(dev[0]) + ' (' + dev[0][0].replace('_', ' ') + ') here', 'osm'); continue
    if wild: put(r, 'W', 'OpenStreetMap marks a bathing spot here' + (' (' + nm(wild[0]) + ')' if wild[0][1] else ''), 'osm'); continue
    if closed: put(r, 'N', 'Mapped as private or closed', 'osm'); continue
    # Wikipedia evidence is not applied automatically: articles about former resorts read like current ones.
    # Articles about a spring itself were reviewed by hand (see tools/rec_judgement.py).
    if r[4] >= 160: put(r, 'N', 'Scalding at the source, with no sign of soaking pools', 'fallback'); continue
    if land and land[0] == 'T': put(r, 'P', 'On tribal land; visiting needs the tribe\'s permission', 'fallback'); continue
    if land and land[0] in ('P', 'R', 'U'): put(r, 'P', 'Warm and on public land, but no sign of regular use was found', 'fallback'); continue
    put(r, 'U', 'No sign of soaking found; may be on private land', 'fallback')
json.dump({'note': 'Estimate of recreational soaking for springs at or above 90 F. Hand judgements plus OpenStreetMap (ODbL, (c) OpenStreetMap contributors) Wikipedia, state-by-state web searches and Google Places lookups, all reviewed by hand. Always check access and conditions.',
           'codes': {'D': 'Known soaking spot: commercial (resort, pool, bathhouse)', 'W': 'Known soaking spot: wild (undeveloped)', 'P': 'Possibly used', 'N': 'Unlikely or not allowed', 'U': 'No evidence found'},
           'r': out}, open('data/recreation.json', 'w'), separators=(',', ':'), ensure_ascii=False)
from collections import Counter
print(len(out), 'springs;', Counter(v[0] for v in out.values()), '| by basis:', why_src)
