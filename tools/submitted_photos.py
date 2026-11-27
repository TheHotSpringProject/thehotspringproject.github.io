"""Collect photos people shared through the app's "Add your photo" button (runs weekly in GitHub Actions).

The button opens Wikimedia Commons' Upload Wizard with the description pre-filled, including a link back to the
spring (https://thehotspringproject.github.io/#spring-<n>). This finds those files by searching Commons for that link,
checks each is a freely licensed JPEG/PNG at least 600 px wide, and writes data/submitted.json:
  {"s": {"<spring index>": {"file": "File:...", "by": "<uploader>", "date": "YYYY-MM-DD"}}}
The newest photo for each spring wins. Files deleted from Commons drop out on the next run.
Submitted photos are featured ahead of the automatic matches (see app.js).
"""
import json, re, sys, time, urllib.parse, urllib.request
sys.stdout.reconfigure(line_buffering=True)
API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'TheHotSpringProject/1.0 (https://thehotspringproject.github.io/; collects photos shared through the app)'}
FREE = re.compile(r'cc[- ]?by|cc0|public domain|\bpd\b|pd-|attribution', re.I)
NOTFREE = re.compile(r'\bnc\b|non[- ]?commercial|\bnd\b|no[- ]?deriv|fair use|non-free', re.I)
n_springs = len(json.load(open('data/springs.json'))['springs'])

def api(params):
    params = dict(params, format='json', formatversion=2)
    req = urllib.request.Request(API + '?' + urllib.parse.urlencode(params), headers=UA)
    for k in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())
        except Exception as e:
            print('retry', k, repr(e)[:80]); time.sleep(5 + 10 * k)
    return {}

titles, cont = [], {}
while True:
    j = api(dict({'action': 'query', 'list': 'search', 'srsearch': 'insource:"thehotspringproject.github.io/#spring-"',
                  'srnamespace': 6, 'srlimit': 500}, **cont))
    titles += [h['title'] for h in (j.get('query') or {}).get('search', [])]
    if 'continue' not in j: break
    cont = j['continue']
print('files found', len(titles))
# Commons' search index can lag behind new uploads by a day or more, so photos already listed are kept (and rechecked)
# even when the search misses them; ones deleted from Commons drop out below.
try:
    prev = json.load(open('data/submitted.json')).get('s', {})
except Exception:
    prev = {}
# ...and recent uploads by people who have shared photos before (the search index can lag new files by days)
for user in sorted({r.get('by') for r in prev.values() if r.get('by')}):
    j = api({'action': 'query', 'list': 'logevents', 'letype': 'upload', 'leuser': user, 'lelimit': 200})
    titles += [e['title'] for e in (j.get('query') or {}).get('logevents', []) if e.get('title', '').startswith('File:')]
titles = sorted(set(titles) | {r['file'] for r in prev.values()})

out = {}
for k in range(0, len(titles), 50):
    j = api({'action': 'query', 'titles': '|'.join(titles[k:k + 50]), 'prop': 'imageinfo|revisions', 'rvprop': 'content', 'rvslots': 'main',
             'iiprop': 'size|mime|extmetadata|user|timestamp', 'iiextmetadatafilter': 'LicenseShortName'})
    for p in (j.get('query') or {}).get('pages', []):
        ii = (p.get('imageinfo') or [None])[0]
        text = ((p.get('revisions') or [{}])[0].get('slots') or {}).get('main', {}).get('content', '')
        m = re.search(r'thehotspringproject\.github\.io/?#spring-(\d+)', text)
        if not ii or not m: continue
        i = int(m.group(1))
        lic = ((ii.get('extmetadata') or {}).get('LicenseShortName') or {}).get('value', '')
        if i >= n_springs or ii.get('mime') not in ('image/jpeg', 'image/png') or ii.get('width', 0) < 600: continue
        if not FREE.search(lic) or NOTFREE.search(lic): continue
        rec = {'file': p['title'], 'by': ii.get('user', ''), 'date': ii.get('timestamp', '')[:10]}
        if str(i) not in out or rec['date'] > out[str(i)]['date']: out[str(i)] = rec
        print(i, p['title'], rec['by'], rec['date'])

json.dump({'s': dict(sorted(out.items(), key=lambda x: int(x[0]))),
           'source': 'Photos shared through the app via Wikimedia Commons (freely licensed).'},
          open('data/submitted.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print('springs with submitted photos', len(out))
