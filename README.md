# The Hot Spring Project

A map of hot springs across North America (the United States and Canada).

Live at https://thehotspringproject.github.io/

An interactive map of US springs: the 1,661 thermal springs of NOAA's 1980 list (the data behind NOAA's retired NGDC hot springs viewer), thousands more from state geological surveys, the Nevada and New Mexico geological surveys and the Water Quality Portal, and an optional layer of about 33,000 named springs from USGS place names.

## Features

- Basemaps: USGS Topo, OpenTopoMap, satellite imagery (Esri), USGS imagery + topo, Esri Topo, shaded relief, OpenStreetMap streets, and Esri light and dark gray
- An optional road and place-label overlay for the imagery basemaps
- Springs colored on a continuous temperature ramp (blue for cool through yellow and orange to deep red near boiling); the minimum-temperature slider starts at 80 °F and goes up to 212 °F
- A popup for each spring showing its name, linked to Google Maps, and its temperature
- Search by name, filter by state or minimum temperature, and sort by name, temperature or distance from you
- A results list limited to the current map view, which can expand into a full-screen table
- A "locate me" button and a distance column
- A land filter (any ownership, on public land, on public land with open access, on public land without open access, or on private land), with each spring's land unit and manager shown in its details
- Descriptions and photos for 174 springs from Wikipedia and Wikimedia Commons, with author, license and date credits
- Installable as an app (home-screen icon, full screen) with offline use: spring data, filters, saved springs and recently viewed map areas work without a signal
- **Save this area for offline** (download button under the locate button): saves USGS Topo tiles for the area on screen, down to trail-level detail (up to 5,000 tiles per area), plus Wikipedia/Commons details for the springs in it. Saved areas are listed under Basemap → Offline areas, and with no signal the map switches to USGS Topo inside a saved area. Only USGS maps are downloadable in bulk (public domain); other basemaps' terms don't allow it.
- Saved and visited springs, kept on your device, with a filter for each
- A °F/°C switch
- Shareable links to individual springs, such as `#spring-547`

## Data

*Thermal Springs List for the United States* — G. W. Berry, P. J. Grim and J. A. Ikelman, NOAA Key to Geophysical Records Documentation No. 12 (1980). The list was archived when NOAA decommissioned the product in May 2025: <https://doi.org/10.25921/c8p0-zs06>. The digitized copy used here comes from [dgketchum/ncei-thermal-springs](https://github.com/dgketchum/ncei-thermal-springs).

`data/springs.json` fields: `name, state, lat, lon, temp_f, temp_c, class, usgs_quad`. Class is `B` (≥ 90 °C), `H` (50–89 °C), `W` (< 50 °C), or the source's own B/H/W label when no temperature was recorded.

Land ownership comes from USGS [PAD-US 4.1](https://www.usgs.gov/programs/gap-analysis-project/science/pad-us-web-services) (the Fee Managers layer), checked at each spring's listed coordinates in November 2026. Each spring's last field, `land`, holds `[category, manager code, unit name]`, or `null` when no PAD-US parcel covers the point, which usually means private land. Temperature classes: Boiling ≥194 °F, Hot 122–193 °F, Warm 68–121 °F, Cool <68 °F. Category codes: `P` public with open access, `R` public with restricted access, `U` public with unknown access, `M` military, `T` tribal, `N` nonprofit preserve, `V` private. In the app, "On public land" means P, R or U, "On public land & open access" means P only, "On public land without open access" means R or U, and "On private land" means no PAD-US parcel, `V` or `N`. Some 1980 coordinates are off by hundreds of meters, so a spring near a boundary may be classed wrongly.

`data/media.json` matches 166 springs to an English Wikipedia article and/or a Wikimedia Commons photo (95 photos; commercial soaking spots may show the resort or bathhouse rather than the water), by name and distance, with every match checked by hand (Nov 2026). Photos were reviewed one by one and kept only if they show the spring, pool or thermal feature itself (not signs, buildings, towns, maps or postcards). The text, photographer, license and dates load live from the Wikipedia and Commons APIs when a spring is opened, so credits stay current. Photos whose license isn't free are never shown. Google Maps photos are only taken from places Google classifies as natural features, parks, campgrounds, pools, spas or non-lodging attractions; towns and hotels are skipped. Wikipedia text is CC BY-SA 4.0.

The list has not been updated since 1980. Many springs are on private or closed land, so check access before you go.

## Install on a phone

**iPhone/iPad:** open the site in Safari, tap Share, then Add to Home Screen. **Android:** tap "Install app" in the header, or use the browser menu. The service worker in `sw.js` caches the app and data for offline use. Map tiles you view are kept, up to about 3,000; saved offline areas go in a separate `offline-v1` cache that is never trimmed. Tiles and photos are loaded with CORS so cached copies don't count as oversized "opaque" entries against storage. Google Maps photos are never cached.

## Deploy

This is a static site with no build step. To publish it with GitHub Pages, go to **Settings → Pages → Build and deployment**, choose **Deploy from a branch**, then select `main` and `/ (root)`.

To run it locally: `python3 -m http.server`, then open http://localhost:8000.

Leaflet 1.9.4 (BSD-2-Clause) is included in `vendor/leaflet`. Map tiles © USGS, Esri, OpenTopoMap and OpenStreetMap contributors, as credited on the map.

## Added data sources

`tools/state_survey.py` (run by `.github/workflows/state-survey.yml` on GitHub Actions, on changes and quarterly) pulls the 4,701 thermal-spring records that state geological surveys contributed to the National Geothermal Data System, republished as AASG-GDS (Zaffos and Richard, 2025, [doi:10.5281/zenodo.8125526](https://doi.org/10.5281/zenodo.8125526), CC BY 4.0), and matches them to the NOAA list by distinctive name words and distance. `tools/merge_state_survey.py` then builds `data/springs.json` from the untouched NOAA file `data/noaa1980.json` and the results in `data/ss_raw.json`:

- **Newer readings** for 826 NOAA springs (the newest dated reading, shown next to NOAA's 1980 value; readings that disagree with NOAA by more than 40 °F are dropped as likely mismatches). Where NOAA listed no temperature, the survey reading is used.
- **More precise locations** for 423 NOAA springs: a name-matched survey record given to 4+ decimal places, 0.1–2 km from NOAA's point. NOAA's original point is kept in the `moved` field.
- **1,982 added springs** of every temperature (1,498 are Cool, under 68 °F; Tennessee's 965 come from a 1956 groundwater survey and are named by county): survey records not matched to any NOAA spring, more than 0.5 km from any NOAA spring and not sharing a name with one within 5 km. Wells, fumaroles, mine features and NOAA-derived records are excluded, and duplicates within 300 m are merged. In eastern states, where springs top out near 40 °C, "Celsius" readings above 45 are converted from Fahrenheit, and any still above 45 °C are treated as unknown.

Land ownership for added and moved springs is looked up in PAD-US at the new point. Each spring's source citation is shown in the app.

### More sources (same pipeline)

`tools/state_survey.py` also pulls, and matches the same way:

- **Nevada Bureau of Mines and Geology** geothermal database, *Hot Springs and Wells* layer (spring records only; newest sample per site, with its reference).
- **New Mexico Bureau of Geology and Mineral Resources**, springs discharging above 30 °C (Kelley, 2015, [doi:10.15121/1223849](https://doi.org/10.15121/1223849), CC BY 4.0). Points are given only as UTM coordinates and IDs.
- **Water Quality Portal** (USGS, EPA, National Park Service and others): every site typed *Spring* with a water-temperature result, state by state; the newest reading per site. Readings attach to matched springs (newest dated reading wins); unmatched sites are added only at 20 °C (68 °F) or warmer, since most are cold monitoring points. Site names are cleaned (survey-code prefixes removed, "Sp"/"Spr" expanded), and stream, ditch and well sampling points are skipped.

Marker locations are only ever moved using state geological survey records.

### Named springs layer

`tools/named_springs.py` builds `data/named_springs.json` from the USGS Geographic Names Information System (feature class *Spring*, public domain): every named spring not already among the main springs (within 150 m, or 600 m with a shared name word). A Water Quality Portal temperature is attached when a spring site with a matching name lies within 1 km, or any site within 200 m. The app loads this file only when **Named springs** is ticked in the legend, and draws it from zoom 8 in (up to 4,000 points at a time). These springs are not in the list, filters or offline saves.

## Soaking estimate

For springs at or above 90 °F, `data/recreation.json` (built by `tools/recreation.py`) gives an estimate of recreational use, keyed by `lat,lon` rounded to 3 decimals: **D** known soaking spot, commercial (resort, pool, bathhouse), **W** known soaking spot, wild (undeveloped pools people use), **P** possibly used, **N** unlikely or not allowed, **U** no evidence found, each with a one-line reason. Precedence:

1. Hand judgements in `tools/rec_judgement.py` (about 460 springs, from two review passes; the second matched famous soaks listed under generic names, such as Deep Creek, Sykes and the Long Valley tubs, by location: well-known resorts and wild soaks, closed or private former resorts, power plants, volcanic vents).
2. Rules: thermal areas in parks where soaking is banned (Yellowstone, Lassen, Mount Rainier, Valles Caldera, Ash Meadows and others) and military land are **N**.
3. OpenStreetMap evidence from `tools/rec_evidence.py` (public baths, pools and bathing spots within 400 m). The public Overpass servers refused most requests from GitHub's runners, so this currently contributes little.
4. Fallbacks: scalding (160 °F+) with no evidence of pools is **N**; warm springs on public land are **P**; the rest **U**.

Wikipedia articles near each spring are gathered in `data/rec_evidence.json` but not applied automatically (articles about former resorts read like current ones); articles about a spring itself were reviewed by hand.

A third pass searched the web state by state and ran Google Places text searches near every unclassified spring at or above 90 °F (`tools/web_evidence.py`, run in GitHub Actions; results in `data/places_evidence.json`, only the place name, type, status, review count and location are kept). Matches were reviewed by hand and recorded in `tools/rec_judgement.py`.


## Canadian springs

About 90 Canadian springs come from three open sources, fetched by `tools/canada.py` (GitHub Actions, manual) into `data/ca_raw.json` and merged by `tools/canada_rows.py`:

- Yukon Geological Survey, Geothermal Thermal Springs (names and measured temperatures for the Yukon, northern BC and the western NWT; Open Government Licence – Yukon). Springs on the Alaska side of the border are skipped.
- Canadian Geographical Names Database (official hot-spring names; Open Government Licence – Canada).
- OpenStreetMap `natural=hot_spring` (precise locations, some temperatures; ODbL).

Points within 1.5 km are merged. Banff Upper Hot Springs and Cave and Basin are placed by hand. There is no land-ownership layer for Canada, and many Canadian springs have no published temperature yet. Soaking estimates for Canadian springs are judged by name in `tools/rec_judgement.py` (`CA`).
