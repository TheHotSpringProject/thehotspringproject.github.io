"""Fetch springs from the National Geothermal Data System (state geological surveys, AASG-GDS, CC BY 4.0), the
Nevada Bureau of Mines and Geology geothermal database, the New Mexico Bureau of Geology (springs above 30 C) and
the Water Quality Portal (spring sites with water temperature), and match them to the NOAA 1980 list in
data/noaa1980.json. Water Quality Portal sites are added as new springs only when 20 C or warmer; all of them are
also written to /tmp/wqp_sites.json for tools/named_springs.py.

Writes data/ss_raw.json = {SRC: [citations], U: [updates for NOAA springs], NW: [new springs]}:
  U row:  [noaa_index, temp_f, temp_c, year, src] + optionally [lat, lon, land, loc_src] when a
          name-matched state-survey record gives a more precise location 0.1-2 km away
  NW row: [name, state, lat, lon, temp_f, temp_c, year, src, land]
Run by .github/workflows/state-survey.yml (GitHub's runners can reach the ArcGIS services)."""
import json, math, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor

AASG = 'https://services1.arcgis.com/Ezk9fcjSUkeadg6u/arcgis/rest/services/ngdsdata/FeatureServer/2/query'
PADUS = 'https://services.arcgis.com/v01gqwM5QqNysAAi/arcgis/rest/services/Fee_Managers_PADUS/FeatureServer/0/query'

def get(url, params, tries=4):
    q = url + '?' + urllib.parse.urlencode(params)
    for t in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers={'User-Agent': 'hotsprings-map'}), timeout=60) as r:
                j = json.load(r)
            if 'error' in j: raise RuntimeError(j['error'])
            return j
        except Exception:
            if t == tries - 1: raise
            time.sleep(2 + 2 * t)

GEN = set('HOT WARM SPRING SPRINGS SPGS SPG SPR THERMAL UNNAMED UNKNOWN NO NUMBER AREA GROUP WELL AT NEAR NR THE OF AND COUNTY CO A B C D E N S W NORTH SOUTH EAST WEST UPPER LOWER LITTLE BIG OLD NEW 1 2 3 4 5 6'.split())
def toks(s, minlen=1, extra=()):
    ws = re.sub(r'[^A-Z0-9 ]', ' ', (s or '').upper()).split()
    return list(dict.fromkeys(w[:-1] if w.endswith('S') else w for w in ws if len(w) >= minlen and w not in GEN and w not in extra))
def lev(a, b):
    if abs(len(a) - len(b)) > 2: return 9
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1): cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]
def hit(w, lst): return any(x == w or (len(w) >= 5 and len(x) >= 5 and lev(w, x) <= 2) for x in lst)
def km(a, b, c, d):
    t = math.pi / 180; x = (c - a) * t; y = (d - b) * t
    h = math.sin(x / 2) ** 2 + math.cos(a * t) * math.cos(c * t) * math.sin(y / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
def dec(v):
    s = repr(float(v)); return len(s.split('.')[1]) if '.' in s and s.split('.')[1] != '0' else 0

EAST = {'TN', 'WV', 'VA', 'GA', 'NC', 'MA', 'NH', 'MD', 'PA', 'NY', 'VT', 'ME', 'CT', 'AL', 'KY', 'SC'}
FIXED = [0]

# ---- fetch state-survey records
F = 'OBJECTID,springname,othername,featuretype,originating_state,latdegree,longdegree,temperature,temperatureunits,tempmeasurementdatetime,source'
raw, off = [], 0
while True:
    j = get(AASG, {'where': '1=1', 'outFields': F, 'orderByFields': 'OBJECTID', 'resultOffset': off, 'resultRecordCount': 2000, 'f': 'json'})
    raw += [f['attributes'] for f in j['features']]
    if len(j['features']) < 2000: break
    off += 2000
print('state-survey records:', len(raw))

A = []
for a in raw:
    lat, lon = a.get('latdegree'), a.get('longdegree')
    if not lat or not lon or abs(lat) > 90: continue
    u = (a.get('temperatureunits') or '').strip(); t = a.get('temperature'); c = None
    if re.fullmatch(r'-?[\d.]+', u): c = float(u)            # some rows carry the reading in the units field
    elif t is not None and t > -99: c = (t - 32) * 5 / 9 if u == 'F' else t
    # Eastern springs top out near 40 C (Hot Springs, VA); a Celsius reading above 45 there is really Fahrenheit
    if c is not None and u != 'F' and c > 45 and a.get('originating_state') in EAST: c = (c - 32) * 5 / 9; FIXED[0] += 1
    if c is not None and c > 45 and a.get('originating_state') in EAST: c = None; FIXED[0] += 1   # still impossible there: treat as unknown
    if c is not None and not (0 <= c <= 105): c = None
    d = a.get('tempmeasurementdatetime') or ''; yr = int(d[:4]) if d[:4].isdigit() and int(d[:4]) > 1901 else None   # 1899-1901 are placeholders
    src = re.sub(r'\s+', ' ', (a.get('source') or '').strip())
    ft = (a.get('featuretype') or '').lower(); name = (a.get('springname') or '').strip()
    A.append(dict(id=a['OBJECTID'], name=name, st=a.get('originating_state'), lat=lat, lon=lon, prec=min(dec(lat), dec(lon)), c=c, yr=yr, src=src,
                  copy=bool(re.search(r'NOAA National Geophysical|Berry, George|Berry, G\.W|Thermal Springs List', src, re.I)),
                  well=('well' in ft and 'spring' not in ft), tk=toks(name + ' ' + (a.get('othername') or ''))))


# ---- more sources: Nevada Bureau of Mines and Geology, New Mexico Bureau of Geology, Water Quality Portal
FIPS = {'01':'AL','02':'AK','04':'AZ','05':'AR','06':'CA','08':'CO','09':'CT','10':'DE','11':'DC','12':'FL','13':'GA','15':'HI','16':'ID','17':'IL','18':'IN','19':'IA','20':'KS','21':'KY','22':'LA','23':'ME','24':'MD','25':'MA','26':'MI','27':'MN','28':'MS','29':'MO','30':'MT','31':'NE','32':'NV','33':'NH','34':'NJ','35':'NM','36':'NY','37':'NC','38':'ND','39':'OH','40':'OK','41':'OR','42':'PA','44':'RI','45':'SC','46':'SD','47':'TN','48':'TX','49':'UT','50':'VT','51':'VA','53':'WA','54':'WV','55':'WI','56':'WY','72':'PR'}
def sane(c, st):
    if c is None or not (0 <= c <= 105): return None
    if c > 45 and st in EAST: return None
    return c
def rec(fam, name, st, lat, lon, c, yr, src, prec=4, well=False):
    return dict(id=f'{fam}:{len(A)}', name=(name or '').strip(), st=st, lat=lat, lon=lon, prec=prec, c=sane(c, st), yr=yr, src=src, copy=False, well=well,
                tk=toks(name), fam=fam)
for a in A: a['fam'] = 'aasg'
counts = {}

# Nevada Bureau of Mines and Geology geothermal database ("Hot Springs and Wells"): one record per site, newest sample
NB = 'https://web2.nbmg.unr.edu/arcgis/rest/services/Nevada_data/05_GeothermalData/MapServer/8/query'
SPRING_T = {'S', 'SP', 'SPRING', 'SS', 'S?'}
try:
    rows, off = [], 0
    while True:
        j = get(NB, {'where': '1=1', 'outFields': 'SITE_ID,DATE,NAME,TYPE,STATE,REFERENCE,TEMP_C', 'outSR': 4326, 'resultOffset': off, 'resultRecordCount': 1000, 'orderByFields': 'OBJECTID', 'f': 'json'})
        rows += j['features']
        if len(j['features']) < 1000: break
        off += 1000
    site = {}
    for f in rows:
        at, g = f['attributes'], f.get('geometry') or {}
        if (at.get('TYPE') or '').upper() not in SPRING_T or not g.get('x'): continue
        k = at.get('SITE_ID') or f"{g['y']:.4f},{g['x']:.4f}"
        t = at.get('TEMP_C'); t = None if t is None or t < -90 else t
        ms = at.get('DATE'); yr = time.gmtime(ms / 1000).tm_year if isinstance(ms, (int, float)) and ms > 0 else None
        cur = site.get(k)
        if cur is None or ((t is not None) and (cur['t'] is None or (yr or 0) > (cur['yr'] or 0))):
            site[k] = dict(t=t, yr=yr, at=at, g=g)
    for s in site.values():
        at = s['at']; nm = at.get('NAME') or ''
        if re.fullmatch(r'(?i)(spring|unnamed( spring)?|well|)', nm.strip()): nm = 'Unnamed spring'
        ref = (at.get('REFERENCE') or '').strip()
        src = 'Nevada Bureau of Mines and Geology geothermal database' + (' (' + ref + ')' if ref and not re.fullmatch(r'(?i)this study|unknown|n/?a|none|-+', ref) else '')
        nm = re.sub(r'\bSp(r|g|gs)?\.?(?=\s|$)', lambda m: 'Springs' if (m.group(1) or '') == 'gs' else 'Spring', nm, flags=re.I)
        A.append(rec('nbmg', nm, at.get('STATE'), round(s['g']['y'], 5), round(s['g']['x'], 5), s['t'], s['yr'], src))
    counts['nbmg'] = len(site)
except Exception as e:
    print('NBMG failed:', e)

# New Mexico Bureau of Geology: springs discharging above 30 C (Kelley 2015, doi:10.15121/1223849, CC BY 4.0)
try:
    import subprocess, sys
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', 'xlrd', 'pyproj'], check=True)
    import xlrd
    from pyproj import Transformer
    with urllib.request.urlopen(urllib.request.Request('https://gdr.openei.org/files/558/NewMexicoSpgs_Over_30C_AMP.xls', headers={'User-Agent': 'hotsprings-map'}), timeout=120) as r:
        sh = xlrd.open_workbook(file_contents=r.read()).sheet_by_index(0)
    hdr = sh.row_values(0); ix = {h: i for i, h in enumerate(hdr)}
    tz = {z: Transformer.from_crs(f'EPSG:269{z}', 'EPSG:4326', always_xy=True) for z in (12, 13)}
    n = 0
    for ri in range(1, sh.nrows):
        v = sh.row_values(ri)
        e, nn = v[ix['NAD83 UTM Easting']], v[ix['NAD83 UTM Northing']]
        if not e or not nn: continue
        lon, lat = tz[13].transform(e, nn)
        if lon < -109.06: lon, lat = tz[12].transform(e, nn)
        if not (31.3 <= lat <= 37.1 and -109.1 <= lon <= -103): continue
        t = v[ix['Sample Value']] if v[ix['Field Parameter']] == 'T' else None
        u = str(v[ix['Units']])
        if t not in ('', None) and 'F' in u: t = (t - 32) * 5 / 9
        d = v[ix['Collection Date']]; yr = xlrd.xldate_as_tuple(d, 0)[0] if isinstance(d, float) and d > 0 else None
        A.append(rec('nm', 'Unnamed spring (' + str(v[ix['Point ID']]) + ')', 'NM', round(lat, 5), round(lon, 5), t if t != '' else None, yr,
                     'New Mexico Bureau of Geology and Mineral Resources, Aquifer Mapping Program: springs discharging above 30 °C (Kelley, 2015, doi:10.15121/1223849, CC BY 4.0)'))
        n += 1
    counts['nm'] = n
except Exception as e:
    print('New Mexico failed:', e)

# Water Quality Portal (USGS, EPA, National Park Service and others): spring sites with water temperature, newest reading per site
import csv, io, zipfile
WQP = 'https://www.waterqualitydata.us/data/'
def wqp(kind, st, extra):
    p = dict({'statecode': 'US:' + st, 'siteType': 'Spring', 'characteristicName': 'Temperature, water', 'mimeType': 'csv', 'zip': 'yes'}, **extra)
    for t in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(WQP + kind + '/search?' + urllib.parse.urlencode(p), headers={'User-Agent': 'hotsprings-map'}), timeout=900) as r:
                b = r.read()
            if not b: return []
            z = zipfile.ZipFile(io.BytesIO(b))
            with z.open(z.namelist()[0]) as fh:
                return list(csv.DictReader(io.TextIOWrapper(fh, 'utf-8', errors='replace')))
        except zipfile.BadZipFile:
            return []
        except Exception as e:
            if t == 2: print('WQP', kind, st, 'failed:', e); return []
            time.sleep(10)
WQP_SITES = []
def wqp_state(code):
    stn = wqp('Station', code, {})
    if not stn: return []
    res = wqp('Result', code, {'dataProfile': 'narrowResult'})
    best = {}
    for r in res:
        try: v = float(r.get('ResultMeasureValue') or '')
        except ValueError: continue
        u = (r.get('ResultMeasure/MeasureUnitCode') or '').lower()
        c = (v - 32) * 5 / 9 if 'f' in u else v
        d = r.get('ActivityStartDate') or ''
        k = r['MonitoringLocationIdentifier']
        if k not in best or d > best[k][1]: best[k] = (c, d)
    out = []
    for s in stn:
        k = s['MonitoringLocationIdentifier']
        try: lat, lon = float(s['LatitudeMeasure']), float(s['LongitudeMeasure'])
        except ValueError: continue
        if k not in best or not lat or not lon: continue
        c, d = best[k]
        out.append(dict(name=s.get('MonitoringLocationName') or '', st=FIPS.get(code), lat=round(lat, 5), lon=round(lon, 5), c=c, yr=int(d[:4]) if d[:4].isdigit() else None,
                        org=s.get('OrganizationFormalName') or s.get('OrganizationIdentifier') or '', prec=min(dec(lat), dec(lon))))
    return out
with ThreadPoolExecutor(4) as ex:
    for lst in ex.map(wqp_state, sorted(FIPS)): WQP_SITES += lst
STREAM = re.compile(r'\b(abv|above|below|blw|bl|upstream|downstream|u/s|d/s|confluence|bridge|mouth|run|rn|creek at|cr at|nr mouth|outlet|outflow|ditch|canal|pipe|tap|well)\b', re.I)
def clean_wqp(nm):
    nm = (nm or '').strip()
    nm = re.sub(r'^\d{3}[A-Z]?\s+[NS]\d+\s+[EW]\d+\s+\S+\s+(\d+\s+)?', '', nm)    # Nevada township/range prefix: "054 N31 E48 08D 1 "
    nm = re.sub(r'^\(?[A-Z]-?\d+-\d+\)?\S*\s+', '', nm)                                  # Utah/Idaho cadastral prefix
    nm = re.sub(r'\b(Th\.?\s+)?Sp(r|g|gs)?\.?(?=\s|$)', lambda m: ('Thermal ' if m.group(1) else '') + ('Springs' if (m.group(2) or '') == 'gs' else 'Spring'), nm, flags=re.I)
    nm = re.sub(r'\s+\d+(SE|SW|NE|NW|[NSEW])$', '', nm)                                     # trailing "4SE" direction-from-town notes
    nm = re.split(r'\s+[-–]\s+', nm)[0]                                                    # drop "- main pool at boil" style notes
    if not [w for w in re.findall(r'[A-Za-z]{3,}', nm) if not re.fullmatch(r'[a-dA-D]+', w)]: return 'Unnamed spring'   # only codes left
    if re.fullmatch(r'(?i)un\s*named( spring)?', nm): return 'Unnamed spring'
    if re.fullmatch(r'[A-Za-z]*\d[\w-]*', nm): return 'Unnamed spring'                             # a single sampling code, e.g. HOR010C1, LIR-10
    if re.search(r'\d', nm) and not re.search(r'(?i)\b(springs?|seep|vent|hot|warm|ojo|agua|boil|geyser|pool|tub|bath)', nm): return 'Unnamed spring'
    return nm
skipped_stream = 0
for s in WQP_SITES:
    stream = bool(STREAM.search(s['name'] or ''))
    skipped_stream += stream
    A.append(rec('wqp', clean_wqp(s['name']), s['st'], s['lat'], s['lon'], s['c'], s['yr'], 'Water Quality Portal: ' + s['org'], prec=s['prec'], well=stream))
print('Water Quality Portal stream/well points skipped:', skipped_stream)
counts['wqp'] = len(WQP_SITES)
json.dump([[s['name'], s['st'], s['lat'], s['lon'], None if sane(s['c'], s['st']) is None else round(sane(s['c'], s['st']), 1), s['yr'], s['org']] for s in WQP_SITES],
          open('/tmp/wqp_sites.json', 'w'))
print('more sources:', counts)

S = json.load(open('data/noaa1980.json'))['springs']
N = [dict(i=i, lat=r[2], lon=r[3], tk=toks(r[0])) for i, r in enumerate(S)]

# ---- match each record to the best NOAA spring (name words, small spelling slips allowed; distance-only only when very close)
for a in A:
    if a['copy'] or a['well']: continue
    best = None
    for n in N:
        if abs(n['lat'] - a['lat']) > 0.05 or abs(n['lon'] - a['lon']) > 0.07: continue
        d = km(n['lat'], n['lon'], a['lat'], a['lon'])
        if d > 4: continue
        if n['tk']:
            sc = sum(hit(w, a['tk']) for w in n['tk']) / len(n['tk'])
            if sc >= 0.5: kind = 'name'
            elif d <= 0.25: kind, sc = 'near', 0.1
            else: continue
        else:
            if d > 0.3: continue
            kind, sc = 'near', 0.05
        key = sc * 10 - d
        if not best or key > best[0]: best = (key, n['i'], d, kind)
    if best: a['m'], a['md'], a['kind'] = best[1], best[2], best[3]

per = {}
for a in A:
    if 'm' in a: per.setdefault(a['m'], []).append(a)
out = {}
for i, l in per.items():
    temps = sorted([a for a in l if a['c'] is not None], key=lambda a: (-(a['yr'] or 0), a['kind'] != 'name', a['md']))
    locs = sorted([a for a in l if a['fam'] == 'aasg' and a['kind'] == 'name' and a['prec'] >= 4 and 0.1 <= a['md'] <= 2], key=lambda a: (-a['prec'], a['md']))
    if temps or locs: out[i] = (temps[0] if temps else None, locs[0] if locs else None)

# ---- new springs: every unmatched spring (any temperature), not near or named like a NOAA spring
GEN2 = {'COMPLEX'}
NT = [dict(lat=r[2], lon=r[3], tk=toks(r[0], 3, GEN2)) for r in S]
def clean(n): return re.sub(r'\s+', ' ', re.sub(r'^[A-Za-z .]+ County ', '', n)).strip()
cands = [a for a in A if 'm' not in a and not a['copy'] and not a['well'] and (a['fam'] != 'wqp' or (a['c'] is not None and a['c'] >= 20))
         and not re.search(r'fumarole|gas vent|\bgas\b|\bmine\b|\bwell\b', a['name'], re.I)]
cands = [a for a in cands if not any(abs(la - a['lat']) < 0.01 and abs(lo - a['lon']) < 0.013 and km(la, lo, a['lat'], a['lon']) < 0.5 for la, lo in ((r[2], r[3]) for r in S))]
cands = [a for a in cands if not any(abs(n['lat'] - a['lat']) < 0.05 and abs(n['lon'] - a['lon']) < 0.07 and km(n['lat'], n['lon'], a['lat'], a['lon']) < 5
                                     and set(toks(clean(a['name']), 3, GEN2)) & set(n['tk']) for n in NT)]
cands.sort(key=lambda a: (a['c'] is None, a['fam'] == 'wqp', -(a['yr'] or 0), -a['prec']))
keep = []
for a in cands:
    if not any(abs(k['lat'] - a['lat']) < 0.003 and abs(k['lon'] - a['lon']) < 0.004 and km(k['lat'], k['lon'], a['lat'], a['lon']) < 0.3 and (any(hit(w, a['tk']) for w in k['tk']) or not k['tk'] or not a['tk']) for k in keep):
        keep.append(a)
for a in keep:
    n = clean(a['name']) or 'Unnamed spring'
    mid = re.match(r'^[A-Z]{2}_([A-Za-z]+)_\d+S?$', n)          # Tennessee records are named by ID, e.g. TN_Anderson_0044S
    if mid: n = 'Unnamed spring (' + re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', mid.group(1)) + ' County)'
    a['dname'] = 'Unnamed spring' if re.match(r'^(unnamed|no name|spring$|missing$|unknown$|none$)', n, re.I) and not mid else n

# ---- land ownership (PAD-US 4.1 Fee Managers) at new springs and moved locations
ORDER = {'OA': 0, 'RA': 1, 'UK': 2, 'XA': 3}
def land(lat, lon):
    j = get(PADUS, {'geometry': f'{lon},{lat}', 'geometryType': 'esriGeometryPoint', 'inSR': 4326, 'spatialRel': 'esriSpatialRelIntersects',
                    'outFields': 'Mang_Type,Mang_Name,Pub_Access,Unit_Nm', 'returnGeometry': 'false', 'f': 'json'})
    fs = sorted(j.get('features') or [], key=lambda f: ORDER.get(f['attributes'].get('Pub_Access'), 4))
    if not fs: return None
    a = fs[0]['attributes']; mt, mn = a.get('Mang_Type'), a.get('Mang_Name')
    c = 'T' if mt == 'TRIB' else 'M' if mn in ('DOD', 'ARMY', 'NAVY', 'USAF', 'USMC') else 'N' if mt == 'NGO' else 'V' if mt == 'PVT' else {'OA': 'P', 'RA': 'R', 'XA': 'R', 'UK': 'U'}.get(a.get('Pub_Access'), 'U')
    return [c, mn, a.get('Unit_Nm') or '']
jobs = [a for a in keep] + [loc for t, loc in out.values() if loc]
with ThreadPoolExecutor(6) as ex:
    for a, l in zip(jobs, ex.map(lambda a: land(a['lat'], a['lon']), jobs)): a['land'] = l

# ---- package
SRC, si = [], {}
def sidx(s):
    if len(s) > 220: s = re.sub(r'\s+\S*$', '', s[:217]) + '…'
    if s not in si: si[s] = len(SRC); SRC.append(s)
    return si[s]
r1 = lambda v: None if v is None else round(v, 1)
ll = lambda v: round(v, 5)
F_ = lambda c: None if c is None else round(c * 9 / 5 + 32)
U = []
for i in sorted(out):
    t, loc = out[i]
    row = [i, F_(t['c']) if t else None, r1(t['c']) if t else None, t['yr'] if t else None, sidx(t['src']) if t else None]
    if loc: row += [ll(loc['lat']), ll(loc['lon']), loc['land'], sidx(loc['src'])]
    U.append(row)
NW = [[a['dname'], a['st'], ll(a['lat']), ll(a['lon']), F_(a['c']), r1(a['c']), a['yr'], sidx(a['src']), a['land']] for a in keep]
json.dump({'SRC': SRC, 'U': U, 'NW': NW, 'fetched': time.strftime('%Y-%m-%d')}, open('data/ss_raw.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print('eastern C/F fixes:', FIXED[0])
print('NOAA springs updated:', len(U), '| moved:', sum(1 for r in U if len(r) > 5), '| new springs:', len(NW), '| sources:', len(SRC))
