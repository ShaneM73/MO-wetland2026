# Overlays and point-readout grids for the drone page (written into <out>/data/drone/)
import sys, json, os, numpy as np, rasterio, rasterio.features, geopandas as gpd
from rasterio.warp import reproject, Resampling
from shapely.geometry import shape, box
P = os.path.expanduser("~/Wetland2026/data/"); HID = "110100070301"
S = P + "LiDAR/BartonFen_20250415_DSM_Ortho/DSM_Preliminary_Lidar_20250415_WGS1984_UTMZone15.tif"
OFF = 26.05
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
with rasterio.open(S) as s:
    crs = s.crs; b = s.bounds
    x0, y1 = np.floor(b.left), np.ceil(b.top); W, H = int(np.ceil(b.right - x0)), int(np.ceil(y1 - b.bottom))
    t = rasterio.Affine(1, 0, x0, 0, -1, y1)
    z = np.full((H, W), np.nan, "f4"); reproject(rasterio.band(s, 1), z, dst_transform=t, dst_crs=crs, resampling=Resampling.average, src_nodata=-9999, dst_nodata=np.nan)
z += OFF
g = np.full((H, W), np.nan, "f4")
with rasterio.open(P + f"LiDAR/USGS_3DEP_1m/dem_1m_{HID}_buf200.tif") as d:
    reproject(rasterio.band(d, 1), g, dst_transform=t, dst_crs=crs, resampling=Resampling.bilinear, dst_nodata=np.nan)
enc = lambda a: np.where(np.isfinite(a), np.clip(np.round((a - 250) * 100), 0, 65534), 65535).astype("<u2")
open(f"{out}/surface_1m.bin", "wb").write(enc(z).tobytes()); open(f"{out}/ground_1m.bin", "wb").write(enc(g).tobytes())
# footprint
m = np.isfinite(z)
from scipy import ndimage
m = ndimage.binary_opening(ndimage.binary_closing(m, iterations=3), iterations=2)
geoms = [shape(gm) for gm, v in rasterio.features.shapes(m.astype("u1"), mask=m, transform=t) if v == 1]
fp = gpd.GeoSeries(geoms, crs=crs).union_all().simplify(1.0)
fp_g = gpd.GeoSeries([fp], crs=crs)
site = gpd.read_file(P + "StudySite/study_site.gpkg").to_crs(crs)
nwi = gpd.read_file(P + f"Wetlands/NWI/nwi_{HID}.gpkg").to_crs(crs)
bb = box(b.left - 100, b.bottom - 100, b.right + 100, b.top + 100)
nwi = nwi[nwi.intersects(bb)].copy(); nwi["geometry"] = nwi.geometry.intersection(bb).simplify(0.5)
def gj(gs, props=None):
    g4 = gs.to_crs(4326) if hasattr(gs, "to_crs") else gs
    return json.loads(g4.to_json(drop_id=True)) if isinstance(g4, gpd.GeoDataFrame) else json.loads(gpd.GeoDataFrame(geometry=g4).to_json(drop_id=True))
lonlat = gpd.GeoSeries.from_xy([b.left, b.right], [b.bottom, b.top], crs=crs).to_crs(4326)
meta = dict(grid=dict(x0=float(x0), y1=float(y1), w=W, h=H, epsg=crs.to_epsg(), off=OFF, scale=0.01, base=250),
            bounds=[[lonlat.y[0], lonlat.x[0]], [lonlat.y[1], lonlat.x[1]]],
            site=gj(site[["name", "geometry"]]), footprint=gj(fp_g),
            nwi=gj(nwi[["WETLAND_TYPE", "ATTRIBUTE", "geometry"]].round({}) if "ATTRIBUTE" in nwi else nwi[["WETLAND_TYPE", "geometry"]]),
            area_ha=round(fp.area / 1e4, 1), site_ha=round(float(site.area.sum()) / 1e4, 2),
            site_stats={})
Z22 = (670181, 4168005, 670600, 4168410)          # full-resolution (zoom 22) orthophoto box: study site + 150 m
zz = gpd.GeoSeries.from_xy([Z22[0], Z22[2]], [Z22[1], Z22[3]], crs=crs).to_crs(4326)
meta["z22"] = [[zz.y[0], zz.x[0]], [zz.y[1], zz.x[1]]]
# stats inside the study site (1 m)
sm = rasterio.features.rasterize(site.geometry, out_shape=(H, W), transform=t) > 0
hh = (z - g)[sm & np.isfinite(z - g)]
meta["site_stats"] = dict(surface_med=round(float(np.nanmedian(z[sm])), 2), ground_med=round(float(np.nanmedian(g[sm])), 2),
                          height_pct=[round(float(v), 2) for v in np.percentile(hh, [10, 50, 90])], share_over_2m=round(float((hh > 2).mean()), 3))
def rnd(o):
    if isinstance(o, float): return round(o, 6)
    if isinstance(o, list): return [rnd(v) for v in o]
    if isinstance(o, dict): return {k: rnd(v) for k, v in o.items()}
    return o
json.dump(rnd(meta), open(f"{out}/meta.json", "w"), separators=(",", ":"))
print(meta["area_ha"], meta["site_ha"], meta["site_stats"], len(nwi), "NWI polygons", W, H)
