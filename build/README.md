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

## Drone page

`build/drone_build.sh` makes `drone.html` and `data/drone/` from the drone files in `~/Wetland2026/data/LiDAR/BartonFen_20250415_DSM_Ortho` (about 7 minutes; work files go to `build/drone_work/`, git-ignored). `relief.py` makes the shaded surface model and the height above the USGS DEM (the drone elevations are shifted up 26.05 m to match NAVD88), `bare.py` the USGS 1 m comparison layer, `overlays.py` the study site, NWI, coverage outline and the 1 m readout grids; `drone3d.py` the 3D view's elevation grids (study site at 0.4 m, whole flight at 1 m) and draped textures; `gdal2tiles` cuts the WebP tiles (orthophoto to zoom 21, plus zoom 22 around the study site). The page itself is `drone_template.html`, copied as is.
