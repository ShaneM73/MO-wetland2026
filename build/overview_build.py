# Build overview.html (project infographic) for the MO-wetland2026 site.
# Makes two extra watershed images on the viewer's 8 m grid (NWI training labels, spatial-CV folds),
# gathers the headline numbers from the model outputs, and injects them into overview_template.html.
# Run from the viz directory: python overview_build.py ~/MO-wetland2026
import sys, json
from pathlib import Path
import numpy as np, geopandas as gpd, rasterio, rasterio.features
from rasterio.warp import reproject, Resampling
from PIL import Image

P = Path("/home/sgf.edubear.net/xm7303/Wetland2026"); MD = P / "data/model"; HID = "110100070301"
out = Path(sys.argv[1]); img = out / "data/img"

# viewer's watershed grid: the 1 m DEM averaged 8 x 8 (same as prep7.dem_grid(8))
with rasterio.open(P / f"data/LiDAR/USGS_3DEP_1m/dem_1m_{HID}_buf200.tif") as d:
    H, W = d.height // 8, d.width // 8
    t8 = d.transform * d.transform.scale(d.width / W, d.height / H); crs = d.crs
assert (W, H) == Image.open(img / "ws2d_elev.webp").size, "grid differs from the viewer images"

nwi = gpd.read_file(P / f"data/Wetlands/NWI/nwi_{HID}.gpkg").to_crs(crs)
veg = nwi[~nwi.WETLAND_TYPE.isin(["Lake", "Freshwater Pond", "Riverine"])]
emerg = veg.WETLAND_TYPE.str.contains("Emergent")
lab = np.zeros((H, W), "u1")
lab[rasterio.features.rasterize(veg[~emerg].geometry, out_shape=(H, W), transform=t8) > 0] = 1
lab[rasterio.features.rasterize(veg[emerg].geometry, out_shape=(H, W), transform=t8) > 0] = 2
rgba = np.zeros((H, W, 4), "u1")
rgba[lab == 1] = (235, 104, 52, 255); rgba[lab == 2] = (214, 39, 140, 255)
# grow thin polygons by one pixel so they read at small size
from scipy.ndimage import binary_dilation
for c, col in ((1, (235, 104, 52, 255)), (2, (214, 39, 140, 255))):
    rgba[binary_dilation(lab == c) & (rgba[..., 3] == 0)] = col
Image.fromarray(rgba).save(img / "ws2d_nwilab.webp", lossless=True)

# spatial-CV folds from the model cache, on the 16 m grid, then onto the 8 m viewer grid
C = np.load(MD / "rf_cache.npz")
with rasterio.open(P / f"data/twi/pilot_{HID}/resolution/twi_16m_{HID}.tif") as s:
    t16 = s.transform
f16 = np.full(tuple(C["shape"]), 255, "u1"); f16[C["rows"], C["cols_px"]] = C["fold"]
f8 = np.full((H, W), 255, "u1")
reproject(f16, f8, src_transform=t16, src_crs=crs, src_nodata=255, dst_transform=t8, dst_crs=crs, dst_nodata=255, resampling=Resampling.nearest)
pal = [(31, 111, 92), (113, 172, 156), (196, 140, 60), (120, 94, 170), (60, 120, 190)]
rgba = np.zeros((H, W, 4), "u1")
for k, col in enumerate(pal):
    rgba[f8 == k] = (*col, 235)
# block edges as thin light lines
blk16 = np.full(tuple(C["shape"]), -1, "i4"); blk16[C["rows"], C["cols_px"]] = C["block"]
b8 = np.full((H, W), -1, "i4")
reproject(blk16, b8, src_transform=t16, src_crs=crs, src_nodata=-1, dst_transform=t8, dst_crs=crs, dst_nodata=-1, resampling=Resampling.nearest)
edge = ((b8 != np.roll(b8, 1, 0)) | (b8 != np.roll(b8, 1, 1))) & (b8 >= 0)
rgba[edge] = (255, 255, 255, 255)
Image.fromarray(rgba).save(img / "ws2d_folds.webp", lossless=True)

# headline numbers
RF = json.load(open(MD / "rf_results.json")); RB = json.load(open(MD / "robustness.json")); DL = json.load(open(MD / "dl_results.json"))
TH = json.load(open(MD / "rf_thresholds.json"))
core = json.load(open(out / "data/core.json"))
N = dict(
    cells=RF["cells"], share=RF["baseline"]["wetland_share"], blocks=RB["blocks"], wetland=RB["wetland"], edge_share=RB["edge_share_of_wetland"],
    sets={k: dict(ap=v["ap"], ci=v["ap_ci"], ne=v["ap_no_edge"], auc=RF["sets"][k]["auc"], open=RF["sets"][k]["auc_open"]) for k, v in RB["sets"].items()},
    paired={**RB["paired_ap_diff"], **json.load(open(MD / "coherence_rf.json"))["paired"]}, random_cv=RB["random_cv"],
    learners={**{k: dict(ap=v["ap"], ci=v["ap_ci"], ne=v["ap_no_edge"], fen=v.get("fen_median")) for k, v in RB["learners"].items()},
              **{k: dict(ap=DL[k]["ap"], ci=DL[k]["ap_ci"], ne=DL[k]["ap_no_edge"], fen=DL[k]["fen_median"]) for k in ("unet", "pixel")}},
    emergent={k: dict(std=v["standard"]["open"]["auc"], held=v["held_out"]["open"]["auc"], ap=v["held_out"]["open"]["ap"],
                      chance=v["held_out"]["open"]["no_skill"], fen=v["held_out"]["fen_pct_all"]) for k, v in RB["emergent_holdout"].items()},
    fen_prob=RF["fen_median_prob"], thr={k: TH["all_gw_s2"][k] for k in ("f1", "roc")}, nwi_ha=TH["all_gw_s2"]["nwi_ha"],
    importance=dict(list(RF["importance_full"].items())[:8]),
    th=dict(eco=core["th"]["eco"], s2=core["th"]["s2"], seep=core["th"]["seep"], fen_pct=core["th"]["fen_pct"]),
    geom=dict(w=W, h=H, huc=core["ws2d"]["huc"], site_c=core["ws2d"]["site_c"]),
    meta=core["meta"],
)
t = Path("overview_template.html").read_text(encoding="utf-8")
(out / "overview.html").write_text(t.replace("/*__DATA__*/null", json.dumps(N, separators=(",", ":")).replace("</", "<\\/")), encoding="utf-8")
print("overview.html", (out / "overview.html").stat().st_size // 1000, "kB")
