# MO-wetland2026 — Strother Creek wetland viewer

Interactive viewer for the Missouri wetland-mapping pilot: HUC12 110100070301 (Strother Creek, Iron County) and the Barton Fen study site.

**▶ Open the viewer: https://shanem73.github.io/MO-wetland2026/**

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
| `rfw` | Terrain + radar model as a wetland map: 2 = wet at the F1-optimal cut-off (p ≥ 0.61), 1 = wet only at the ROC (Youden) cut-off (p ≥ 0.13), 0 = dry; NWI drawn on top |

Sources: USGS 3DEP 1 m DEM; NWI (US Fish & Wildlife Service); NCEP Stage IV precipitation; gridMET reference ET; NOAA USCRN Salem 10 W soil moisture; NLCD 2021; NISAR L2 GCOV Provisional (NASA/ASF); Sentinel-1 OPERA L2 RTC-S1 (NASA JPL/ASF; contains Copernicus Sentinel data 2026). Display copies are downsampled; the analysis runs on full-resolution rasters outside this repository.

Local preview: `python3 -m http.server` in this folder, then open http://localhost:8000 (the page fetches its data, so opening the file directly does not work).
