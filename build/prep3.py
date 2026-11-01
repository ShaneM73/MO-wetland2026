import json, numpy as np, rasterio, geopandas as gpd
from rasterio.enums import Resampling
P="/home/sgf.edubear.net/xm7303/Wetland2026/"
dem_p=P+"data/LiDAR/USGS_3DEP_1m/dem_1m_110100070301_buf200.tif"
D=json.load(open("data2.json"))
g=gpd.read_file(P+"data/Wetlands/NWI/nwi_110100070301.gpkg")
cls={"Lake":"water","Freshwater Pond":"water","Riverine":"river"}
g["cls"]=g.WETLAND_TYPE.map(cls).fillna("veg")
site=gpd.read_file(P+"data/StudySite/study_site.gpkg").to_crs(26915).geometry.iloc[0]
with rasterio.open(dem_p) as d:
    H,W=d.height//8,d.width//8; t8=d.transform*d.transform.scale(d.width/W,d.height/H)
    cx,cy=site.centroid.x,site.centroid.y
    win=rasterio.windows.from_bounds(cx-400,cy-400,cx+400,cy+400,d.transform).round_offsets().round_lengths()
    t1=d.window_transform(win)
def path(geom,t,tol):
    inv=~t; out=[]
    geom=geom.simplify(tol) if tol else geom
    for p in getattr(geom,"geoms",[geom]):
        if p.geom_type!="Polygon": continue
        for ring in [p.exterior,*p.interiors]:
            pts=[inv*(x,y) for x,y in np.asarray(ring.coords)[:,:2]]
            out.append("M"+"L".join(f"{c:.1f},{r:.1f}" for c,r in pts)+"Z")
    return "".join(out)
from shapely.geometry import box
sbox=box(cx-400,cy-400,cx+400,cy+400)
ws,sv=[],[]
for _,r in g.iterrows():
    rec=dict(cls=r.cls,code=r.ATTRIBUTE,type=r.WETLAND_TYPE,ha=round(r.area_ha,2))
    p=path(r.geometry,t8,4)
    if p: ws.append({**rec,"d":p})
    if r.geometry.intersects(sbox):
        p=path(r.geometry.intersection(sbox),t1,0)
        if p: sv.append({**rec,"d":p})
summ=g.groupby("cls").agg(n=("area_ha","size"),ha=("in_huc_ha","sum")).round(1).to_dict("index")
D["nwi"]=dict(ws=ws,site=sv,summary=summ)
s=json.dumps(D,separators=(",",":")); open("data3.json","w").write(s)
print(len(s)/1e6,"MB", len(ws), len(sv), summ)
