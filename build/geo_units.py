# Bedrock units as one coded raster for the viewer's geology layer (1-5 = Ce, Og, Cp, Celd, Or; 0 = other) -> geo_units_16m.tif
import rasterio, numpy as np
with rasterio.open("/home/sgf.edubear.net/xm7303/Wetland2026/data/Geology/geology_16m_110100070301.tif") as s:
    d = dict(zip(s.descriptions, s.read())); prof = s.profile
order = ["geo_Ce", "geo_Og", "geo_Cp", "geo_Celd", "geo_Or"]
u = np.zeros(d[order[0]].shape, "f4")
for i, k in enumerate(order, 1): u[d[k] == 1] = i
prof.update(count=1, dtype="float32", nodata=np.nan)
with rasterio.open("geo_units_16m.tif", "w", **prof) as o: o.write(u, 1)
