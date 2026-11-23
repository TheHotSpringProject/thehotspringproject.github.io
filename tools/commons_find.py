"""Look up recent Wikimedia Commons files for one spring (manual helper; runs in GitHub Actions).
Usage: python tools/commons_find.py "<name>" <lat> <lon>
Prints files geotagged within 2 km and files whose title or description mentions the name, newest first,
with uploader, upload date, size, licence and whether the description links back to the app."""
import json, sys, urllib.parse, urllib.request
API = 'https://commons.wikimedia.org/w/api.php'
UA = {'User-Agent': 'TheHotSpringProject/1.0 (https://thehotspringproject.github.io/)'}
def api(p):
    p = dict(p, format='json', formatversion=2)
    with urllib.request.urlopen(urllib.request.Request(API + '?' + urllib.parse.urlencode(p), headers=UA), timeout=60) as r:
        return json.loads(r.read())
name, lat, lon = sys.argv[1], sys.argv[2], sys.argv[3]
t = set()
g = api({'action': 'query', 'list': 'geosearch', 'gscoord': f'{lat}|{lon}', 'gsradius': 2000, 'gsnamespace': 6, 'gslimit': 100})
t |= {h['title'] for h in g.get('query', {}).get('geosearch', [])}
for q in [f'"{name}"', f'intitle:"{name}"', f'insource:"#spring-"  "{name.split()[0]}"']:
    s = api({'action': 'query', 'list': 'search', 'srsearch': q, 'srnamespace': 6, 'srlimit': 50})
    t |= {h['title'] for h in s.get('query', {}).get('search', [])}
# also the newest uploads to Commons mentioning the first word of the name (search index can lag; this cannot)
rc = api({'action': 'query', 'list': 'logevents', 'letype': 'upload', 'lelimit': 500})
t |= {e['title'] for e in rc.get('query', {}).get('logevents', []) if name.split()[0].lower() in e['title'].lower()}
rows = []
tl = sorted(t)
for k in range(0, len(tl), 50):
    j = api({'action': 'query', 'titles': '|'.join(tl[k:k + 50]), 'prop': 'imageinfo|revisions', 'rvprop': 'content', 'rvslots': 'main',
             'iiprop': 'size|user|timestamp|extmetadata', 'iiextmetadatafilter': 'LicenseShortName'})
    for p in j.get('query', {}).get('pages', []):
        ii = (p.get('imageinfo') or [{}])[0]
        txt = ((p.get('revisions') or [{}])[0].get('slots') or {}).get('main', {}).get('content', '')
        rows.append((ii.get('timestamp', ''), p['title'], ii.get('user'), ii.get('width'), ii.get('height'),
                     ((ii.get('extmetadata') or {}).get('LicenseShortName') or {}).get('value'), 'thehotspringproject' in txt))
for r in sorted(rows, reverse=True)[:60]:
    print('|'.join(str(x) for x in r))
