# 3D view data for drone.html: elevation grids and draped textures for two extents (written into <out>/3d/)
#   whole: the drone flight's bounding box at 1 m;  site: the study site + 150 m (same box as the zoom-22 orthophoto) at 0.4 m
# Surface = drone LiDAR DSM (+26.05 m to NAVD88), filled with the USGS 1 m bare earth outside the flight and where the DSM sits
# more than 1 m below it (edge artefacts). Textures: orthophoto, height above bare earth, elevation-tinted relief; outside the
# flight they show the USGS bare-earth relief. Run from the drone work directory (needs relief.tif, height_rgba.tif, bare_rgba.tif, ortho.vrt).
import sys, json, os, numpy as np, rasterio, rasterio.features, geopandas as gpd
from rasterio.warp import reproject, Resampling
from PIL import Image
P = os.path.expanduser("~/Wetland2026/data/")
DSM = P + "LiDAR/BartonFen_20250415_DSM_Ortho/DSM_Preliminary_Lidar_20250415_WGS1984_UTMZone15.tif"
DEM = P + "LiDAR/USGS_3DEP_1m/dem_1m_110100070301_buf200.tif"
OFF, BASE = 26.05, 250.0
out = sys.argv[1] + "/3d"; os.makedirs(out, exist_ok=True)
with rasterio.open(DSM) as s: crs, b = s.crs, s.bounds
EXT = {"whole": ((np.floor(b.left), np.floor(b.bottom), np.ceil(b.right), np.ceil(b.top)), 1.0, 3072),
       "site": ((670181, 4168005, 670600, 4168410), 0.4, 4096)}          # site box matches Z22 in overlays.py


def warp(src, shape, t, band=1, rs=Resampling.average, nodata=None):
    a = np.full(shape, np.nan, "f4")
    with rasterio.open(src) as s:
        reproject(rasterio.band(s, band), a, dst_transform=t, dst_crs=crs, resampling=rs, src_nodata=None if nodata == "none" else (nodata if nodata is not None else s.nodata), dst_nodata=np.nan)
    return a


def rgba(src, shape, t):
    return np.dstack([np.nan_to_num(warp(src, shape, t, k, Resampling.average, nodata="none")) for k in (1, 2, 3, 4)])


site = gpd.read_file(P + "StudySite/study_site.gpkg").to_crs(crs)
meta = {"base": BASE, "scale": 0.01, "ext": {}}
for name, ((x0, y0, x1, y1), res, tex) in EXT.items():
    W, H = int(round((x1 - x0) / res)) + 1, int(round((y1 - y0) / res)) + 1        # vertices on cell corners
    tv = rasterio.Affine(res, 0, x0 - res / 2, 0, -res, y1 + res / 2)
    g = warp(DEM, (H, W), tv, rs=Resampling.bilinear)
    z = warp(DSM, (H, W), tv, nodata=-9999) + OFF
    fl = np.isfinite(z) & ~(z < g - 1)
    surf = np.where(fl, z, g)
    enc = lambda a: np.where(np.isfinite(a), np.clip(np.round((a - BASE) * 100), 0, 65534), 65535).astype("<u2")
    open(f"{out}/{name}_surface.bin", "wb").write(enc(surf).tobytes())
    open(f"{out}/{name}_ground.bin", "wb").write(enc(g).tobytes())
    # textures over the same extent
    tw = tex if (x1 - x0) >= (y1 - y0) else int(tex * (x1 - x0) / (y1 - y0)); th = int(round(tw * (y1 - y0) / (x1 - x0)))
    tt = rasterio.Affine((x1 - x0) / tw, 0, x0, 0, -(y1 - y0) / th, y1)
    bare = rgba("bare_rgba.tif", (th, tw), tt)[..., :3]
    grey = bare.mean(2, keepdims=True) * 0.55 + bare * 0.45                          # muted bare-earth relief outside the flight
    for k, src in (("ortho", "ortho.vrt"), ("relief", "relief.tif"), ("height", "height_rgba.tif")):
        c = rgba(src, (th, tw), tt); a = c[..., 3:] / 255
        if k == "height":                                                             # low heights are near-transparent: lay them on grey relief
            img = c[..., :3] * a + (grey * 0.6 + 230 * 0.4) * (1 - a)
            img = np.where(c[..., 3:] > 0, img, grey)
        else:
            img = c[..., :3] * a + grey * (1 - a)
        Image.fromarray(np.clip(img, 0, 255).astype("u1")).save(f"{out}/{name}_{k}.webp", quality=82, method=5)
    # study-site outline in grid coordinates (column, row of the vertex grid)
    ring = np.asarray(site.geometry.iloc[0].exterior.coords)
    meta["ext"][name] = dict(w=W, h=H, res=res, x0=float(x0), y1=float(y1),
                             site=[[round((x - x0) / res, 2), round((y1 - y) / res, 2)] for x, y in ring[:, :2]],
                             zmin=round(float(np.nanmin(surf)), 2), zmax=round(float(np.nanmax(surf)), 2), tex=[tw, th])
    print(name, W, H, "tex", tw, th, meta["ext"][name]["zmin"], meta["ext"][name]["zmax"])
json.dump(meta, open(f"{out}/meta.json", "w"), separators=(",", ":"))
