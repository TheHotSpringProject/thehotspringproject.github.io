"""Check that every Wikimedia photo and Wikipedia article the app uses was taken at / is about the right place
(runs in GitHub Actions; this workspace can't reach Wikimedia).

For each spring's photo (data/media.json, data/photos.json, data/submitted.json, data/springs-world.json) it reads the
file's coordinates from Commons: the camera/object location templates (prop=coordinates, all of them) and the EXIF
GPS fields. For each Wikipedia article (media.json, springs-world.json) it reads the article's coordinates.
  - more than 10 km from the spring: removed (photo or article dropped from the data)
  - 3-10 km: kept, listed in the report for a look
  - no coordinates: kept, listed in the report
Report: data/photo_coord_check.json
"""
import json, math, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(line_buffering=True)
UA = {'User-Agent': 'TheHotSpringProject/1.0 (https://thehotspringproject.github.io/; checking photo locations)'}
FAR, NEAR = 10.0, 3.0

def api(base, params):
    params = dict(params, format='json', formatversion=2)
    data = urllib.parse.urlencode(params).encode()
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(base, data=data, headers=UA), timeout=60) as r:
                return json.loads(r.read())
        except Exception as e:
            print('retry', k, repr(e)[:80]); time.sleep(5 + 10 * k)
    return {}

def km(a, b, c, d):
    t = math.pi / 180; x = (c - a) * t; y = (d - b) * t
    h = math.sin(x / 2) ** 2 + math.cos(a * t) * math.cos(c * t) * math.sin(y / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

def num(v):
    try: return float(re.sub('<[^>]+>', '', str(v)).strip())
    except Exception: return None

springs = json.load(open('data/springs.json'))['springs']
media = json.load(open('data/media.json'))
photos = json.load(open('data/photos.json'))
submitted = json.load(open('data/submitted.json'))
try: world = json.load(open('data/springs-world.json'))
except Exception: world = None

# (source, key, name, lat, lon, file or article)
files, arts = [], []
for k, v in media['m'].items():
    r = springs[int(k)]
    if len(v) > 1 and v[1]: files.append(('media', k, r[0], r[2], r[3], v[1]))
    if v and v[0]: arts.append(('media', k, r[0], r[2], r[3], v[0]))
for k, f in photos['p'].items():
    r = springs[int(k)]; files.append(('photos', k, r[0], r[2], r[3], f))
for k, v in submitted['s'].items():
    r = springs[int(k)]; files.append(('submitted', k, r[0], r[2], r[3], v['file']))
if world:
    for n, r in enumerate(world['springs']):
        if r[11]: files.append(('world', n, r[0], r[2], r[3], 'File:' + r[11]))
        if r[10]: arts.append(('world', n, r[0], r[2], r[3], r[10]))
print('photos to check', len(files), 'articles', len(arts))

def coords_for(base, titles, files_mode):
    out = {}
    for k in range(0, len(titles), 50):
        p = {'action': 'query', 'titles': '|'.join(titles[k:k + 50]), 'prop': 'coordinates', 'coprimary': 'all', 'colimit': 'max', 'redirects': 1}
        if files_mode:
            p.update({'prop': 'coordinates|imageinfo', 'iiprop': 'extmetadata', 'iiextmetadatafilter': 'GPSLatitude|GPSLongitude'})
        j = api(base, p)
        q = j.get('query') or {}
        back = {}
        for n in q.get('normalized', []): back[n['to']] = n['from']
        for n in q.get('redirects', []): back[n['to']] = back.get(n['from'], n['from'])
        for pg in q.get('pages', []):
            pts = [(c['lat'], c['lon']) for c in pg.get('coordinates', [])]
            if files_mode:
                md = ((pg.get('imageinfo') or [{}])[0].get('extmetadata') or {})
                la, lo = num((md.get('GPSLatitude') or {}).get('value')), num((md.get('GPSLongitude') or {}).get('value'))
                if la is not None and lo is not None: pts.append((la, lo))
            t = pg['title']; out[back.get(t, t)] = pts; out[t] = pts
        time.sleep(0.2)
    return out

fc = coords_for('https://commons.wikimedia.org/w/api.php', sorted({f[5] for f in files}), True)
ac = coords_for('https://en.wikipedia.org/w/api.php', sorted({a[5] for a in arts}), False)

report = {'removed': [], 'review': [], 'no_coords': []}
drop_files, drop_arts = set(), set()
for kind, items, cmap in (('photo', files, fc), ('article', arts, ac)):
    for src, k, name, lat, lon, t in items:
        pts = cmap.get(t, [])
        if not pts:
            report['no_coords'].append([kind, src, k, name, t]); continue
        d = min(km(lat, lon, a, b) for a, b in pts)
        row = [kind, src, k, name, t, round(d, 1)]
        if d > FAR:
            report['removed'].append(row); (drop_files if kind == 'photo' else drop_arts).add((src, str(k)))
            print('REMOVE', row)
        elif d > NEAR:
            report['review'].append(row)

# apply removals
for src, k in drop_files:
    if src == 'media': media['m'][k][1] = ''
    elif src == 'photos': photos['p'].pop(k, None)
    elif src == 'submitted': submitted['s'].pop(k, None)
    elif src == 'world': world['springs'][int(k)][11] = ''
for src, k in drop_arts:
    if src == 'media': media['m'][k][0] = ''
    elif src == 'world': world['springs'][int(k)][10] = ''
media['m'] = {k: v for k, v in media['m'].items() if any(v)}
json.dump(media, open('data/media.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(photos, open('data/photos.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(submitted, open('data/submitted.json', 'w'), ensure_ascii=False, separators=(',', ':'))
if world: json.dump(world, open('data/springs-world.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump(report, open('data/photo_coord_check.json', 'w'), ensure_ascii=False, indent=1)
print('removed', len(report['removed']), 'review', len(report['review']), 'no coordinates', len(report['no_coords']))
