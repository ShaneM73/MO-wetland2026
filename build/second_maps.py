"""Side-by-side maps of both watersheds for the 'Second watershed' section of the viewer.
Writes <out>/data/img/cmp_<huc>_<layer>.webp (layers: prob, agree, hand) on each watershed's 16 m model grid,
over grey relief; transparent outside the HUC12. Prints the image sizes."""
import sys, json, numpy as np, rasterio, matplotlib, geopandas as gpd
from rasterio.enums import Resampling
from rasterio.features import rasterize
from PIL import Image
P = "/home/sgf.edubear.net/xm7303/Wetland2026/data/"
OUT = (sys.argv[1] if len(sys.argv) > 1 else "..") + "/data/img/"
W = {"110100070301": P, "103001021306": P + "watersheds/103001021306/"}
AGREE = {3: "#1f5fa8", 1: "#e08a1e", 2: "#c2185b"}   # both, model only, NWI only (nested strict cut-off)


def hillshade(z, cs=16.0, ex=3):
    gy, gx = np.gradient(np.nan_to_num(z, nan=np.nanmean(z)) * ex, cs)
    sl = np.arctan(np.hypot(gx, gy)); asp = np.arctan2(-gx, gy)
    return np.mean([np.clip(np.sin(np.radians(45)) * np.cos(sl) + np.cos(np.radians(45)) * np.sin(sl) * np.cos(np.radians(a) - asp), 0, 1)
                    for a in (225, 270, 315, 360)], axis=0)


meta = {}
for huc, d in W.items():
    with rasterio.open(d + "model/rf_prob_all_gw_s2.tif") as s:
        prob = s.read(1).astype("f4"); sh, tr = s.shape, s.transform
    with rasterio.open(d + "model/disagreement_nested_f1.tif") as s:
        ag = s.read(1)
    with rasterio.open(d + f"Groundwater/gw_16m_{huc}.tif") as s:
        hand = s.read(s.descriptions.index("hand_1") + 1).astype("f4")
    with rasterio.open(d + f"twi/pilot_{huc}/conditioned_{huc}.tif") as s:
        z = s.read(1, out_shape=sh, resampling=Resampling.average, masked=True).filled(np.nan).astype("f4")
    inside = ag != 255                          # model cells (HUC minus open water)
    hucm = rasterize(gpd.read_file(d + "boundaries/pilot_huc12.gpkg", layer="huc").to_crs(26915).geometry, out_shape=sh, transform=tr) > 0
    h = hillshade(z)
    grey = (0.62 + 0.33 * h)[..., None] * np.ones(3)
    shade = (0.75 + 0.25 * h)[..., None]

    def save(rgb, name):
        rgba = np.dstack([np.where(inside[..., None], rgb, grey), hucm.astype(float)])
        Image.fromarray((np.clip(rgba, 0, 1) * 255).astype("u1"), "RGBA").save(OUT + f"cmp_{huc}_{name}.webp", "WEBP", quality=82, method=6)

    save(matplotlib.colormaps["YlGnBu"](np.clip(np.nan_to_num(prob), 0, 1))[..., :3] * shade, "prob")
    rgb = grey.copy()
    for v, c in AGREE.items():
        rgb[ag == v] = matplotlib.colors.to_rgb(c)
    save(rgb, "agree")
    save(matplotlib.colormaps["YlGnBu_r"](np.clip(np.nan_to_num(hand, nan=10) / 10, 0, 1))[..., :3] * shade, "hand")
    meta[huc] = dict(w=sh[1], h=sh[0], km_w=round(sh[1] * 16 / 1000, 1))
print(json.dumps(meta))
