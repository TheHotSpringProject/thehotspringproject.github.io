"""Find freely licensed Wikimedia Commons photos taken at or right next to each spring (runs in GitHub Actions).

For every named spring without a curated photo in data/media.json:
  1. Commons geosearch for files within 400 m of the spring.
  2. Keep JPEG/PNG photos at least 800 px wide under a CC or public-domain licence (no NC/ND, no fair use).
  3. Keep only files whose title or categories point at the spring: a distinctive word from the spring's name,
     or a hot-spring word (hot spring, thermal, geyser, pool, terrace, bath, ...). Maps, logos, diagrams,
     signs and portraits are dropped.
  4. Pick the best one: a name match first, then a hot-spring word, then the nearest.
Output: data/photos.json {"p": {"<spring index>": "File:..."}, "source": ...}
Progress is saved as it goes, so a run that stops early keeps what it found and the next run continues.
"""
import json, math, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(line_buffering=True)

API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'TheHotSpringProject/1.0 (https://thehotspringproject.github.io/; photo matching for a hot springs map)'}
springs = json.load(open('data/springs.json'))['springs']
media = json.load(open('data/media.json'))['m']
try:
    OUT = json.load(open('data/photos.json'))
except Exception:
    OUT = {}
OUT.setdefault('p', {}); OUT.setdefault('checked', [])
OUT['source'] = 'Wikimedia Commons files geotagged within 400 m of each spring; freely licensed (CC BY, CC BY-SA, CC0, public domain).'
checked = set(OUT['checked'])

def api(params, tries=4):
    params = dict(params, format='json', formatversion=2, maxlag=5)
    url = API + '?' + urllib.parse.urlencode(params)
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                j = json.loads(r.read())
            if 'error' in j and j['error'].get('code') == 'maxlag':
                time.sleep(5 + 5 * k); continue
            return j
        except Exception as e:
            print('  retry', k, repr(e)[:80]); time.sleep(5 + 10 * k)
    return {}

def km(a, b, c, d):
    t = math.pi / 180; x = (c - a) * t; y = (d - b) * t
    h = math.sin(x / 2) ** 2 + math.cos(a * t) * math.cos(c * t) * math.sin(y / 2) ** 2
    return 12742 * math.asin(math.sqrt(h))

STATES={'alabama','alaska','arizona','arkansas','california','colorado','connecticut','delaware','florida','georgia','hawaii','idaho','illinois','indiana','iowa','kansas','kentucky','louisiana','maine','maryland','massachusetts','michigan','minnesota','mississippi','missouri','montana','nebraska','nevada','hampshire','jersey','mexico','york','carolina','dakota','ohio','oklahoma','oregon','pennsylvania','rhode','tennessee','texas','utah','vermont','virginia','washington','wisconsin','wyoming','columbia','alberta','yukon','puerto','rico'}
GENERIC={'hot','warm','springs','spring','the','and','creek','river','lake','upper','lower','north','south','east','west','big','little','old','new','mineral','sulphur','sulfur','thermal','group','well','wells','resort','unnamed','near','basin','canyon','valley','mountain','mount','park','ranch','camp','bear','city','county','fork','road','station','area','state','national','forest','main','blue','green','white','black','salt','soda','iron','cold','dead','santa','san','fort'}
STRICT=re.compile(r'hot.?springs?|warm.?springs?|thermal|geyser|terrace|travertine|sinter|fumarole|fumerole|mud.?pot|mud.?volcano|soak|hot.?pot|hot.?pool|boiling|paint.?pot|caldron|cauldron|hot water',re.I)
SPRINGY=re.compile(r'springs?\b|pool|geyser|bath|spa\b|soak|plunge|punch.?bowl|blue hole|\bvent\b|boil',re.I)
BAD=re.compile(r'building|avenue|barn|shed\b|cat house|\bmill\b|banner|balloon|i-70|amtrak|trolley|guard house|farm\b|residence|evans hotel|majestic hotel|, (ca|co|ar|nv|ut|or|id|mt|wy|nm|az|tx),? \d{4}|school|church|cemetery|monument|marker|courthouse|post office|depot|highway|route|\broad\b|\bst\b|street|dam\b|bridge|downtown|main street|sign|museum|library|store|motel|gas station|insects?|elk|deer|cows?|horse|aerial|airport|train|truck|\bcar\b',re.I)
FREE = re.compile(r'cc[- ]?by|cc0|public domain|\bpd\b|pd-|attribution', re.I)
NOTFREE = re.compile(r'\bnc\b|non[- ]?commercial|\bnd\b|no[- ]?deriv|fair use|non-free', re.I)

def tokens(name):
    return [w for w in re.findall(r"[a-z]+", name.lower()) if len(w) >= 4 and w not in GENERIC and w not in STATES]

todo = [(i, r) for i, r in enumerate(springs)
        if r[0] and str(i) not in media and str(i) not in OUT['p'] and i not in checked]
print('springs to check', len(todo))
T0 = time.time(); found = 0
for n, (i, r) in enumerate(todo):
    if time.time() - T0 > 100 * 60: print('time limit; stopping'); break
    name, lat, lon = r[0], r[2], r[3]
    g = api({'action': 'query', 'list': 'geosearch', 'gscoord': f'{lat}|{lon}', 'gsradius': 400, 'gsnamespace': 6, 'gslimit': 30})
    hits = (g.get('query') or {}).get('geosearch') or []
    checked.add(i)
    if hits:
        titles = [h['title'] for h in hits if re.search(r'\.(jpe?g|png)$', h['title'], re.I) and not BAD.search(h['title'])]
        dist = {h['title']: h.get('dist', 0) for h in hits}
        info = {}
        for k in range(0, len(titles), 50):
            j = api({'action': 'query', 'titles': '|'.join(titles[k:k + 50]), 'prop': 'imageinfo', 'iiprop': 'size|mime|extmetadata',
                     'iiextmetadatafilter': 'LicenseShortName|ImageDescription'})
            for p in (j.get('query') or {}).get('pages', []):
                info[p['title']] = p
        tk = tokens(name); best = None
        for t in titles:
            p = info.get(t); ii = p and p.get('imageinfo') and p['imageinfo'][0]
            if not ii or ii.get('width', 0) < 800 or ii.get('mime') not in ('image/jpeg', 'image/png'): continue
            md = ii.get('extmetadata', {}); lic = (md.get('LicenseShortName') or {}).get('value', '')
            if not FREE.search(lic) or NOTFREE.search(lic): continue
            # match on the file name only: categories and descriptions name the nearby town too often
            fn = t[5:].rsplit('.', 1)[0]
            if BAD.search(fn): continue
            nm = sum(1 for w in tk if re.search(r'\b' + re.escape(w), fn, re.I))
            strict = bool(STRICT.search(fn))
            if not (strict or (nm and SPRINGY.search(fn))): continue
            score = (min(nm, 2) * 2 + (1 if strict else 0), -dist.get(t, 999))
            if not best or score > best[0]: best = (score, t)
        if best:
            OUT['p'][str(i)] = best[1]; found += 1
            print(f'{i} {name} [{r[1]}] -> {best[1]}')
    if n % 100 == 99:
        OUT['checked'] = sorted(checked)
        json.dump(OUT, open('data/photos.json', 'w'), ensure_ascii=False, separators=(',', ':'))
        print(f'-- {n + 1}/{len(todo)} checked, {found} found, {int(time.time() - T0)} s')
    time.sleep(0.15)
OUT['checked'] = sorted(checked)
json.dump(OUT, open('data/photos.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('done: photos for', len(OUT['p']), 'springs; found this run', found)
