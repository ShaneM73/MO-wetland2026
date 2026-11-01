# Site build

Scripts that produce `index.html`, `data/` and `overview.html` from the analysis outputs in `~/Wetland2026` (rasters, model results). The analysis itself lives in `~/Wetland2026/scripts`; these only package its outputs for the web.

Run `build/build.sh` (or `build/build.sh <dir>` to write somewhere other than the repository root). Uses `$PY` (default `python`; here `PY=~/.conda/envs/wetland/bin/python`), with numpy, pandas, rasterio, geopandas, scipy, matplotlib and Pillow.

| Step | Adds |
|---|---|
| `prep.py` | 1 m DEM relief, TWI, outlines (→ `data.json`) |
| `prep2.py` | 3D surfaces, NWI and hydroperiod layers (→ `data2.json`) |
| `prep3.py` | site and watershed summaries (→ `data3.json`) |
| `prep4.py`, `prep4b.py`, `prep5.py` | 16 m TWI / hydroperiod, resolution AUCs, saturation calendar, packed 3D grids, USCRN soil-moisture comparison (→ `data4.json`) |
| `geo_units.py` | bedrock units coded 1–5 for the geology layer (→ `geo_units_16m.tif`) |
| `prep7.py` | radar, groundwater, thermal, Sentinel-2 and random-forest layers, model tables (→ `data7.json`) |
| `split.py` | splits `data7.json` + `template.html` into `index.html`, `data/core.json`, `data/img/`, `data/grid/` |
| `overview_build.py` | label and fold images, headline numbers, injected into `overview_template.html` → `overview.html` |

`prep7.py KEY ...` rebuilds only the named layers. The intermediate `data*.json` and `.tif` files are git-ignored.
