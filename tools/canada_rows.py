"""Turn data/ca_raw.json into Canadian spring rows for data/springs.json (called by merge_state_survey.py).

Sources, merged within 1.5 km:
  Yukon Geological Survey, Geothermal Thermal Springs (names, measured temperature; Yukon, northern BC, western NWT)
  Canadian Geographical Names Database (official names of hot springs; feature type Spring)
  OpenStreetMap natural=hot_spring (precise locations, names, some temperatures)
Location preference: OpenStreetMap, then Yukon GS, then CGNDB.  Temperature: Yukon GS, then OpenStreetMap.
Springs on the Alaska side of the border (in the Yukon layer) are skipped: the US data already has them.
"""
import json, math, re

SRC_YGS = 'Yukon Geological Survey, Geothermal Thermal Springs (open.yukon.ca, Open Government Licence - Yukon)'
SRC_OSM = 'OpenStreetMap contributors, natural=hot_spring (ODbL)'
SRC_CGN = 'Canadian Geographical Names Database, Natural Resources Canada (Open Government Licence - Canada)'
SRC_HAND = 'Placed by hand at the developed pools (about 300 m accuracy); not in the spring datasets'

# Alaska panhandle and the Alaska side of the 141st meridian, as a rough polygon (lon, lat)
AK = [(-141.0, 69.7), (-141.0, 60.3), (-139.07, 60.35), (-137.6, 59.24), (-135.47, 59.8), (-133.4, 58.42), (-131.83, 56.6),
      (-130.02, 55.91), (-130.0, 55.2), (-130.6, 54.7), (-134.0, 54.4), (-142.0, 58.0), (-170.0, 60.0), (-170.0, 70.0)]
def in_poly(lon, lat, poly):
    inside = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1: inside = not inside
    return inside

def km(a, b):
    return math.hypot(a[0] - b[0], (a[1] - b[1]) * math.cos(math.radians(a[0]))) * 111.2

def prov_of(lat, lon):
    if lat < 60:
        # BC / Alberta: the Continental Divide in the south, then 120 W north of about 53.8 N
        div = [(49.0, -114.06), (49.5, -114.4), (50.0, -114.7), (50.5, -115.1), (51.0, -115.6), (51.5, -116.4), (52.0, -117.0), (52.5, -117.6), (53.0, -118.3), (53.5, -119.3), (53.8, -120.0)]
        b = -120.0
        for (la1, lo1), (la2, lo2) in zip(div, div[1:]):
            if la1 <= lat <= la2: b = lo1 + (lo2 - lo1) * (lat - la1) / (la2 - la1)
        if lat < 49.0: b = -114.06
        return 'AB' if lon > b else 'BC'
    # Yukon / Northwest Territories boundary, roughly along the Mackenzie-Yukon divide
    edge = [(60, -124.2), (61, -125.5), (62, -127.6), (63, -129.3), (64, -131.0), (65, -132.7), (66, -133.8), (67, -135.4), (68.5, -136.5), (69.5, -137.0)]
    for (la1, lo1), (la2, lo2) in zip(edge, edge[1:]):
        if la1 <= lat <= la2:
            b = lo1 + (lo2 - lo1) * (lat - la1) / (la2 - la1); return 'NT' if lon > b else 'YT'
    return 'YT' if lon < -136 else 'NT'

PROV = {'British Columbia': 'BC', 'Alberta': 'AB', 'Yukon': 'YT', 'Northwest Territories': 'NT', 'Nunavut': 'NU', 'Quebec': 'QC',
        'Ontario': 'ON', 'Saskatchewan': 'SK', 'Manitoba': 'MB'}

def tidy_ygs(n):
    n = re.sub(r'\bHS\b', 'Hot Springs', n); n = re.sub(r'\bWS\b', 'Warm Springs', n)
    n = n.replace('(Godlin R.)', '(Godlin River)')
    if not re.search(r'spring', n, re.I): n += ' (thermal spring)'
    return n

def rows(us_rows, src_list):
    raw = json.load(open('data/ca_raw.json'))
    sy, so, sc, sh = (len(src_list), len(src_list) + 1, len(src_list) + 2, len(src_list) + 3)
    src_list += [SRC_YGS, SRC_OSM, SRC_CGN, SRC_HAND]
    us_pts = [(r[2], r[3]) for r in us_rows]
    cand = []   # dicts: name, lat, lon, prov, c (temp C), tsrc, lsrc, rank
    for r in raw.get('yukon', []):
        lat, lon = r['_lat'], r['_lon']
        if in_poly(lon, lat, AK) or any(km((lat, lon), p) < 5 for p in us_pts if abs(p[0] - lat) < .1): continue
        t = r.get('WATER_TEMP'); t = float(t) if t not in (None, '', 0) and float(t) > -50 else None
        cand.append(dict(name=tidy_ygs(r['NAME'].strip()), lat=lat, lon=lon, prov=prov_of(lat, lon), c=t, tsrc=sy if t is not None else None, lsrc=sy, nrank=1))
    for r in raw.get('osm', []):
        tg = r['tags']; lat, lon = r['lat'], r['lon']
        t = None
        m = re.match(r'^\s*(\d+(?:\.\d+)?)', tg.get('temperature', '') or '')
        if m: t = float(m.group(1))
        nm = tg.get('name') or ''
        if nm.startswith('('): nm = ''
        cand.append(dict(name=nm, lat=lat, lon=lon, prov=None, c=t, tsrc=so if t is not None else None, lsrc=so, nrank=2))
    for r in raw.get('cgndb', []):
        if r.get('Concise Code') != 'SPRG': continue
        lat, lon = float(r['Latitude']), float(r['Longitude'])
        cand.append(dict(name=r['Geographical Name'], lat=lat, lon=lon, prov=PROV.get(r['Province - Territory']), c=None, tsrc=None, lsrc=sc, nrank=0))
    # Well-known springs missing from all three sources (developed pools, not mapped as springs); placed by hand, about 300 m accuracy
    for name, lat, lon in [('Banff Upper Hot Springs', 51.1525, -115.5615), ('Cave and Basin', 51.1688, -115.5925)]:
        cand.append(dict(name=name, lat=lat, lon=lon, prov='AB', c=None, tsrc=None, lsrc=sh, nrank=-1, hand=True))
    # merge within 1.5 km
    groups = []
    for c in cand:
        g = next((g for g in groups if any(km((c['lat'], c['lon']), (x['lat'], x['lon'])) < 1.5 for x in g)), None)
        (g.append(c) if g else groups.append([c]))
    out = []
    LPREF = {so: 0, sy: 1, sc: 2, sh: 3}
    hand = []
    for g in groups:
        loc = min(g, key=lambda x: LPREF[x['lsrc']])
        named = [x for x in g if x['name']]
        name = min(named, key=lambda x: x['nrank'])['name'] if named else 'Unnamed hot spring'
        temps = [x for x in g if x['c'] is not None]
        tx = min(temps, key=lambda x: 0 if x['tsrc'] == sy else 1) if temps else None
        prov = next((x['prov'] for x in g if x['prov'] and x['lsrc'] in (sc, sh)), None) or prov_of(loc['lat'], loc['lon'])
        c = round(tx['c'], 1) if tx else None
        f = round(c * 9 / 5 + 32) if c is not None else None
        srcs = sorted(set(x['lsrc'] for x in g))
        if any(x.get('hand') for x in g): hand.append(name)
        out.append(dict(name=name, prov=prov, lat=round(loc['lat'], 5), lon=round(loc['lon'], 5), f=f, c=c, tsrc=tx['tsrc'] if tx else None, srcs=srcs))
    return out
