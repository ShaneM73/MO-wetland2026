# MO-wetland2026 — Strother Creek wetland viewer

Interactive viewer for the Missouri wetland-mapping pilot: HUC12 110100070301 (Strother Creek, Iron County) and the Barton Fen study site.

**▶ Open the viewer: https://shanem73.github.io/MO-wetland2026/**

**▶ Project overview for presentations: https://shanem73.github.io/MO-wetland2026/overview.html**: a nine-step 3D walk-through (question, study area, data, method, validation, results, Barton Fen, next steps). Arrow keys step through it; F toggles full-screen presentation mode.

The viewer is served by GitHub Pages from `index.html` at the repository root. The page loads `data/core.json` (charts, outlines, relief) and then each map layer's files on first use:

- `data/img/{ws2d,site2d}_<layer>.webp` — 2D map images (watershed at 8 m display, fen close-up at 1 m)
- `data/grid/{ws3d,site3d}_<layer>.json` — 3D surface colours (watershed 30 m, close-up 2 m)

| Layer key | Content |
|---|---|
| `twi`, `twi16` | Topographic wetness index, ln(a / tan β), FD8, on the 1 m and 16 m DEM |
| `hps`, `hpu` | Mean days/yr saturated (2003–2025), dynamic TWI model, 250 mm root-zone store; SSURGO or uniform soil |
| `nhh`, `nhv` | NISAR L2 GCOV L-band HH / HV backscatter (dB), mean of 9 descending passes (track 12), 27 Jun – 13 Oct 2026 |
| `nchg`, `nhvchg` | NISAR HH / HV, mean of 4 passes after rain minus 4 dry-spell passes (dB) |
| `nratio` | NISAR HH − HV (dB) |
| `svv`, `svh` | Sentinel-1 C-band VV / VH (OPERA RTC-S1, 30 m), mean of 12 summer 2026 passes (dB) |
| `svvchg`, `wvvchg` | Sentinel-1 VV wet − dry, summer (5 vs 3 passes) and winter / leaf-off (1 vs 3 passes) |
| `rft`, `rfa` | Random-forest probability of NWI wetland, terrain only / terrain + radar (spatial 3 km block cross-validation) |
| `hand` | Height above nearest drainage (m), 16 m DEM, D8, streams = 0.1 km² drainage area |
| `swt` | SSURGO annual minimum water-table depth (cm; ≥ 200 = none recorded) |
| `gwt` | Landsat 8/9 surface temperature 2013–2026: median winter minus median summer anomaly (°C), each scene corrected for land cover, sun exposure (slope/aspect at the scene's sun angle) and elevation |
| `snow` | Snow-free share in 9 snow scenes beyond what the pixel's sun exposure predicts |
| `seep` | Seep candidates: valley-floor cells (HAND < 3 m) in the top 5% of both `gwt` and `snow`; no NWI used |
| `econ` | ECOSTRESS 70 m surface temperature 2018–2026: median anomaly on Dec–Feb night passes (°C), each pass corrected for land cover and elevation |
| `ndmi` | Sentinel-2 10 m normalised difference moisture index, mid-August to September 2017–2026: median anomaly against like land cover, averaged to 16 m |
| `geo` | Missouri Geological Survey 1:100,000 bedrock units |
| `rfg` | Random-forest probability, best model: terrain + both radars + groundwater proxies (HAND, distance to stream, SSURGO water table / drainage / bedrock / hydric) + Sentinel-2 phenology anomalies |
| `rfw` | Best model as a wetland map: 2 = wet at the F1-optimal cut-off (p ≥ 0.65), 1 = wet only at the ROC (Youden) cut-off (p ≥ 0.10), 0 = dry; NWI drawn on top |

Sources: USGS 3DEP 1 m DEM; NWI (US Fish & Wildlife Service); NCEP Stage IV precipitation; gridMET reference ET; NOAA USCRN Salem 10 W soil moisture; NLCD 2021; SSURGO (USDA NRCS); Landsat 8/9 Collection 2 Level-2 surface temperature (USGS, via Microsoft Planetary Computer); ECOSTRESS L2T LSTE v002 (NASA JPL / LP DAAC); Sentinel-2 L2A (ESA Copernicus, via Microsoft Planetary Computer); Missouri DNR / Missouri Geological Survey bedrock geology and springs; NISAR L2 GCOV Provisional (NASA/ASF); Sentinel-1 OPERA L2 RTC-S1 (NASA JPL/ASF; contains Copernicus Sentinel data 2026). Display copies are downsampled; the analysis runs on full-resolution rasters outside this repository.

Rebuilding: the scripts in `build/` regenerate `index.html`, `data/` and `overview.html` from the analysis outputs (see `build/README.md`).

Local preview: `python3 -m http.server` in this folder, then open http://localhost:8000 (the page fetches its data, so opening the file directly does not work).
