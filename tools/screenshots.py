"""Play Store screenshots of the live site, each with a caption band above the app.

Runs in GitHub Actions (map tiles load there). Output: store/screens/<device>-<n>-<scene>.png
  phone     1080x1920 (9:16)   7" tablet 1152x2048 (9:16)
  10" tablet 2560x1440 (16:9)  desktop   1920x1080 (16:9)
Google requests are blocked: no paid Places lookups, no Google contributor photos.
"""
import asyncio, base64, os, pathlib, sys
from playwright.async_api import async_playwright

SITE = 'https://thehotspringproject.github.io/'
OUT = 'store/screens'
FONTS = pathlib.Path(__file__).parent / 'fonts'

# final size, device pixel ratio, caption band height (px), touch/mobile, zoom offset vs. the base views
DEVICES = {
    'phone':    dict(size=(1080, 1920), dpr=3, band=300, mobile=True,  dz=0),
    'tablet7':  dict(size=(1152, 2048), dpr=2, band=330, mobile=True,  dz=0.5),
    'tablet10': dict(size=(2560, 1440), dpr=2, band=210, mobile=True,  dz=-0.5),
    'desktop':  dict(size=(1920, 1080), dpr=1, band=160, mobile=False, dz=0),
}

# key, headline, detail line, basemap, view for portrait, view for landscape, hash, actions
SCENES = [
    ('overview', '6,000 hot springs across North America', 'Colored by water temperature, from cool to near boiling',
     'dark', [46.0, -117.0, 3.6], [47.0, -114.0, 4.3], '', ['legend']),
    ('soaks', 'Find a place to soak', 'Commercial and wild soaking spots marked at a glance',
     'esritopo', [44.3, -115.3, 8], [44.2, -115.4, 8.5], '', ['legend', 'soak', 'results:wide']),
    ('detail', 'Everything about a spring', 'Temperature, land manager, photos and directions',
     'esritopo', None, None, '#spring-791', ['legend:wide']),
    ('table', 'Sort and filter every spring', 'A full table of known soaking spots, hottest first',
     'dark', [41.5, -114.5, 4.5], [40.5, -112.5, 5.5], '', ['allspots', 'soak', 'hottest', 'max']),
    ('satellite', 'Topo, satellite and street maps', 'Save map areas to use offline',
     'imagery', [44.62, -110.75, 9.5], [44.6, -110.7, 10], '', ['legend:wide']),
    ('offline', 'Works with no signal', 'Save trip areas; springs, maps and details work offline',
     'usgstopo', None, None, '#spring-738', ['seedarea', 'offline']),
]

def wants(acts, name, wide):
    for a in acts:
        n, _, cond = a.partition(':')
        if n == name and (not cond or (cond == 'wide') == wide):
            return True
    return False

async def app_shot(b, dev, sc):
    d = DEVICES[dev]; W, H = d['size']; dpr = d['dpr']
    wide = W > H
    key, _, _, bm, vp, vl, hsh, acts = sc
    view = vl if wide else vp
    css = {'width': round(W / dpr), 'height': round((H - d['band']) / dpr)}
    ctx = await b.new_context(viewport=css, device_scale_factor=dpr, is_mobile=d['mobile'] and not wide, has_touch=d['mobile'])
    await ctx.route('**/*', lambda r: r.abort() if 'googleapis.com' in r.request.url or 'gstatic.com/maps' in r.request.url else r.continue_())
    await ctx.add_init_script("localStorage.setItem('wt-bm2','%s');localStorage.setItem('wt-leg','%s');"
                              % (bm, '1' if wants(acts, 'legend', wide) else '0'))
    if wants(acts, 'seedarea', wide):   # a saved trip area around the Salmon River near Stanley, Idaho
        await ctx.add_init_script("""localStorage.setItem('wt-offline', JSON.stringify([{id:'shot1', name:'Salmon River near Stanley, Idaho',
            b:[[44.15,-115.0],[44.35,-114.6]], zmin:9, zmax:15, count:3400, springs:11, bytes:46000000, date:'2026-11-20'}]))""")
    pg = await ctx.new_page()
    for attempt in range(2):
        try:
            await pg.goto(SITE + '?shot=2' + hsh, wait_until='load', timeout=60000); break
        except Exception:
            if attempt: raise
    await pg.wait_for_timeout(2500)
    if view:
        await pg.evaluate('([a,b,z]) => { window.wtMap.setView([a,b], z, {animate:false}); return 0; }', [view[0], view[1], view[2] + d['dz']])
    js = []
    if wants(acts, 'allspots', wide):
        js.append("(()=>{const c=document.getElementById('inView'); if (c.checked){c.checked=false; c.dispatchEvent(new Event('change'));}})()")
    if wants(acts, 'soak', wide):
        js.append("(()=>{const s=document.getElementById('soak'); s.value='DW'; s.dispatchEvent(new Event('change'));})()")
    if wants(acts, 'hottest', wide):
        js.append("(()=>{const s=document.getElementById('sort'); s.value='hot'; s.dispatchEvent(new Event('change'));})()")
    if wants(acts, 'results', wide):
        js.append("(()=>{const r=document.getElementById('rfold'); if (r && r.getAttribute('aria-expanded')!=='true') r.click();})()")
    if wants(acts, 'max', wide):
        js.append("document.getElementById('maxbtn').click()")
    for s in js:
        await pg.evaluate(s); await pg.wait_for_timeout(300)
    await pg.add_style_tag(content='#gphoto{display:none!important}')
    try:
        await pg.wait_for_load_state('networkidle', timeout=20000)
    except Exception:
        pass
    await pg.wait_for_timeout(4000)
    if wants(acts, 'offline', wide):   # cut the connection once the map has loaded: the app shows its offline banner
        await ctx.set_offline(True)
        await pg.wait_for_timeout(1200)
    png = await pg.screenshot()
    await ctx.close()
    return png

def font_face(name, file):
    data = base64.b64encode((FONTS / file).read_bytes()).decode()
    return "@font-face{font-family:'%s';src:url(data:font/otf;base64,%s)}" % (name, data)

async def compose(b, dev, sc, png, n):
    d = DEVICES[dev]; W, H = d['size']; band = d['band']
    wide = W > H
    h1 = round(H * 0.052) if wide else round(W * 0.064)
    h2 = round(h1 * 0.5)
    html = f"""<!doctype html><html><head><style>
{font_face('HD', 'InterDisplay-Bold.otf')}{font_face('HM', 'Inter-Medium.otf')}
html,body{{margin:0;width:{W}px;height:{H}px;overflow:hidden;background:#1d5b88}}
.band{{height:{band}px;box-sizing:border-box;padding:0 {round(W*0.06)}px;display:flex;flex-direction:column;justify-content:center;
  background:linear-gradient(135deg,#1d5b88,#2a7ab0);color:#fff}}
h1{{margin:0;font:{h1}px/1.08 HD,sans-serif;letter-spacing:-.01em}}
p{{margin:{round(h2*0.45)}px 0 0;font:{h2}px/1.25 HM,sans-serif;color:#ffd977}}
img{{display:block;width:{W}px;height:{H-band}px}}
</style></head><body><div class="band"><h1>{sc[1]}</h1><p>{sc[2]}</p></div>
<img src="data:image/png;base64,{base64.b64encode(png).decode()}"></body></html>"""
    ctx = await b.new_context(viewport={'width': W, 'height': H}, device_scale_factor=1)
    pg = await ctx.new_page()
    await pg.set_content(html); await pg.wait_for_timeout(300)
    path = f'{OUT}/{dev}-{n}-{sc[0]}.png'
    await pg.screenshot(path=path)
    await ctx.close()
    print('saved', path, flush=True)

async def main():
    os.makedirs(OUT, exist_ok=True)
    for f in pathlib.Path(OUT).glob('*.png'):
        f.unlink()
    only = sys.argv[1:]
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for dev in DEVICES:
            if only and dev not in only:
                continue
            for n, sc in enumerate(SCENES, 1):
                await compose(b, dev, sc, await app_shot(b, dev, sc), n)
        await b.close()

asyncio.run(main())
