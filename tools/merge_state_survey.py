"""Build data/springs.json (what the app loads) from data/noaa1980.json + data/ss_raw.json.

Fields per spring: name, state, lat, lon, temp_f, temp_c, class, usgs_quad, land, ss, moved, origin
  ss     [temp_f, temp_c, year, source_index, used_as_main] - newest state-survey reading (null if none, or if it
         disagrees with NOAA by more than 40 F, which usually means a mismatched record)
  moved  [noaa_lat, noaa_lon, source_index] when the marker uses a more precise state-survey location
  origin 'N' = NOAA 1980 list, 'S' = added from the state geological surveys, 'C' = Canada (tools/canada_rows.py)
Springs added from the state surveys come after the 1,661 NOAA springs, so NOAA indexes never change."""
import json
noaa = json.load(open('data/noaa1980.json')); ss = json.load(open('data/ss_raw.json'))
cls = lambda f, name='': ('B' if f >= 190 else 'V' if f >= 160 else 'H' if f >= 120 else 'W' if f >= 90 else 'C') if f is not None else ('H' if 'HOT' in name.upper() else 'W' if 'WARM' in name.upper() else '')
rows = [r[:9] + [None, None, 'N'] for r in noaa['springs']]
dropped = 0
for u in ss['U']:
    i, f, c, yr, src = u[:5]; r = rows[i]
    if f is not None:
        if r[4] is not None and abs(r[4] - f) > 40: dropped += 1
        else:
            r[9] = [f, c, yr, src, 0]
            if r[4] is None:                          # NOAA listed no reading: use the state survey's
                r[4], r[5] = f, c; r[9][4] = 1
                r[6] = cls(f)                         # class follows the reading now shown
    if len(u) > 5:
        lat, lon, land, lsrc = u[5:9]
        r[10] = [r[2], r[3], lsrc]; r[2], r[3], r[8] = lat, lon, land
for name, st, lat, lon, f, c, yr, src, land in ss['NW']:
    rows.append([name, st, lat, lon, f, c, cls(f, name), '', land, [f, c, yr, src, 1], None, 'S'])
import sys; sys.path.insert(0, 'tools')
from canada_rows import rows as ca_rows
SRC = list(ss['SRC'])
ca = ca_rows(rows, SRC)
for d in ca:   # origin 'C' = Canada; 13th field lists the Canadian sources that mention the spring
    rows.append([d['name'], d['prov'], d['lat'], d['lon'], d['f'], d['c'], cls(d['f']), '', None,
                 [d['f'], d['c'], None, d['tsrc'], 1] if d['tsrc'] is not None else None, None, 'C', d['srcs']])
# origin 'H' = historic sites added by hand (data/historic.json), e.g. springs since drilled over; 13th field holds the note and sources
for h in json.load(open('data/historic.json')):
    rows.append([h['name'], h['st'], h['lat'], h['lon'], h['f'], h['c'], cls(h['f']), '', None, None, None, 'H',
                 {'note': h['note'], 'temp': h['temp'], 'loc': h['loc'], 'sources': h['sources']}])
out = dict(noaa)
out['fields'] = ['name', 'state', 'lat', 'lon', 'temp_f', 'temp_c', 'class', 'usgs_quad', 'land', 'ss', 'moved', 'origin', 'ca_sources']
out['ss_source'] = ('State geological survey thermal-spring records from the National Geothermal Data System, republished as AASG-GDS '
                    '(Zaffos and Richard, 2025, doi:10.5281/zenodo.8125526, CC BY 4.0), fetched ' + ss['fetched'] + '.')
out['ss_sources'] = SRC
out['springs'] = rows
json.dump(out, open('data/springs.json', 'w'), separators=(',', ':'), ensure_ascii=False)
print(len(ca), 'Canadian;', len(rows), 'springs;', sum(r[11] == 'S' for r in rows), 'added;', sum(r[9] is not None for r in rows if r[11] == 'N'), 'NOAA with state reading;',
      sum(r[10] is not None for r in rows), 'moved;', dropped, 'readings dropped (>40 F off)')
