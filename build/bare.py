# USGS 1 m bare-earth DEM over the drone area (+100 m), hillshade tinted with the same elevation colours as the drone relief
import numpy as np, rasterio, matplotlib, os
from rasterio.warp import reproject, Resampling
P = os.path.expanduser("~/Wetland2026/data/")
S = P + "LiDAR/BartonFen_20250415_DSM_Ortho/DSM_Preliminary_Lidar_20250415_WGS1984_UTMZone15.tif"
LO, HI = 314.0, 358.0
with rasterio.open(S) as s: b = s.bounds; crs = s.crs
x0, y1 = np.floor(b.left) - 100, np.ceil(b.top) + 100; W, H = int(b.right - x0) + 101, int(y1 - b.bottom) + 101
t = rasterio.Affine(1, 0, x0, 0, -1, y1)
g = np.full((H, W), np.nan, "f4")
with rasterio.open(P + "LiDAR/USGS_3DEP_1m/dem_1m_110100070301_buf200.tif") as d:
    reproject(rasterio.band(d, 1), g, dst_transform=t, dst_crs=crs, resampling=Resampling.bilinear, dst_nodata=np.nan)
gy, gx = np.gradient(np.nan_to_num(g, nan=np.nanmean(g)))
hs = np.zeros_like(g)
for az, wgt in ((225, .25), (270, .25), (315, .4), (360, .1)):          # multidirectional, like gdaldem
    a, alt = np.radians(az), np.radians(50)
    sl = np.arctan(np.hypot(gx, gy)); asp = np.arctan2(-gx, gy)
    hs += wgt * np.clip(np.sin(alt) * np.cos(sl) + np.cos(alt) * np.sin(sl) * np.cos(a - asp), 0, 1)
cm = matplotlib.colormaps["gist_earth"]
lut = (np.array([cm(0.25 + 0.6 * i / 255) for i in range(256)])[:, :3] * 255)
i = np.clip((np.nan_to_num(g) - LO) / (HI - LO) * 255, 0, 255).astype(int)
rgb = lut[i] * (0.35 + 0.65 * hs[..., None])
rgba = np.dstack([rgb, np.isfinite(g)[..., None] * 255]).astype("u1")
p = dict(driver="GTiff", width=W, height=H, count=4, dtype="uint8", crs=crs, transform=t, compress="deflate")
with rasterio.open("bare_rgba.tif", "w", **p) as o:
    o.colorinterp = [rasterio.enums.ColorInterp.red, rasterio.enums.ColorInterp.green, rasterio.enums.ColorInterp.blue, rasterio.enums.ColorInterp.alpha]
    o.write(rgba.transpose(2, 0, 1))
