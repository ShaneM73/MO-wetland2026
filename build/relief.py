# Drone DSM -> (1) hillshade tinted by elevation, RGBA at native resolution; (2) height above the USGS 1 m bare-earth DEM, 0.25 m.
# The drone DSM is ~26.05 m below the USGS DEM (NAVD88) everywhere on open ground (ellipsoid vs geoid heights); shifted to match.
import numpy as np, rasterio, matplotlib, subprocess, os
from rasterio.warp import reproject, Resampling
from rasterio.windows import Window
S = os.path.expanduser("~/Wetland2026/data/LiDAR/BartonFen_20250415_DSM_Ortho/DSM_Preliminary_Lidar_20250415_WGS1984_UTMZone15.tif")
DEM = os.path.expanduser("~/Wetland2026/data/LiDAR/USGS_3DEP_1m/dem_1m_110100070301_buf200.tif")
OFF, LO, HI = 26.05, 314.0, 358.0
E = os.path.expanduser("~/.conda/envs/wetland/bin/")
if not os.path.exists("hs.tif"):
    subprocess.run([E + "gdaldem", "hillshade", "-multidirectional", "-alt", "50", "-q", "-co", "TILED=YES", "-co", "COMPRESS=DEFLATE", S, "hs.tif"], check=True)
cm = matplotlib.colormaps["gist_earth"]
lut = (np.array([cm(0.25 + 0.6 * i / 255) for i in range(256)])[:, :3] * 255)
with rasterio.open(S) as s, rasterio.open("hs.tif") as h:
    prof = s.profile.copy(); prof.update(count=4, dtype="uint8", nodata=None, compress="deflate", tiled=True, blockxsize=512, blockysize=512, BIGTIFF="YES", predictor=2)
    with rasterio.open("relief.tif", "w", **prof) as o:
        o.colorinterp = [rasterio.enums.ColorInterp.red, rasterio.enums.ColorInterp.green, rasterio.enums.ColorInterp.blue, rasterio.enums.ColorInterp.alpha]
        for r0 in range(0, s.height, 2048):
            w = Window(0, r0, s.width, min(2048, s.height - r0))
            z = s.read(1, window=w) + OFF; v = s.read(1, window=w) > -9000; hs = h.read(1, window=w).astype("f4") / 255
            i = np.clip((z - LO) / (HI - LO) * 255, 0, 255).astype(int)
            rgb = lut[i] * (0.35 + 0.65 * hs[..., None])
            o.write(np.dstack([rgb, v[..., None] * 255]).astype("u1").transpose(2, 0, 1), window=w)
    # height above bare earth at 0.25 m
    R = 0.25
    W_, H_ = int((s.bounds.right - s.bounds.left) / R), int((s.bounds.top - s.bounds.bottom) / R)
    t = rasterio.Affine(R, 0, s.bounds.left, 0, -R, s.bounds.top)
    d = np.full((H_, W_), np.nan, "f4"); reproject(rasterio.band(s, 1), d, dst_transform=t, dst_crs=s.crs, resampling=Resampling.average, src_nodata=-9999, dst_nodata=np.nan)
    g = np.full((H_, W_), np.nan, "f4")
    with rasterio.open(DEM) as dm:
        reproject(rasterio.band(dm, 1), g, dst_transform=t, dst_crs=s.crs, resampling=Resampling.bilinear, dst_nodata=np.nan)
    ht = d + OFF - g
    p = dict(driver="GTiff", width=W_, height=H_, count=1, dtype="float32", crs=s.crs, transform=t, nodata=np.nan, compress="deflate", tiled=True)
    with rasterio.open("height.tif", "w", **p) as o: o.write(ht, 1)
    print("height pct", np.nanpercentile(ht, [1, 5, 25, 50, 75, 95, 99]).round(2))
    # colour: < 0.5 m nearly transparent (ground / low herbs), then a green ramp to 30 m
    cm2 = matplotlib.colormaps["YlGn"]
    x = np.clip(ht / 30, 0, 1); f = np.isfinite(ht)
    rgba = (cm2(0.15 + 0.85 * np.nan_to_num(x)) * 255).astype("u1")
    a = np.where(~f, 0, np.where(ht < 0.5, 60, 235)); rgba[..., 3] = a
    rgba[f & (ht < -1)] = (150, 150, 150, 140)          # > 1 m below the USGS ground: artefacts, mostly along the flight edge
    with rasterio.open("height_rgba.tif", "w", **dict(p, count=4, dtype="uint8", nodata=None)) as o:
        o.colorinterp = [rasterio.enums.ColorInterp.red, rasterio.enums.ColorInterp.green, rasterio.enums.ColorInterp.blue, rasterio.enums.ColorInterp.alpha]
        o.write(rgba.transpose(2, 0, 1))
