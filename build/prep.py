import json, base64, io, numpy as np, rasterio, geopandas as gpd
from rasterio.enums import Resampling
from PIL import Image
import matplotlib; matplotlib.use("Agg"); from matplotlib import cm, colors
P="/home/sgf.edubear.net/xm7303/Wetland2026/"
dem_p=P+"data/LiDAR/USGS_3DEP_1m/dem_1m_110100070301_buf200.tif"
huc=gpd.read_file(P+"data/boundaries/pilot_huc12.gpkg",layer="huc").geometry.iloc[0]
buf=gpd.read_file(P+"data/boundaries/pilot_huc12.gpkg",layer="buf").geometry.iloc[0]
site=gpd.read_file(P+"data/StudySite/study_site.gpkg").geometry.iloc[0]
def read(f, window=None):
    with rasterio.open(dem_p) as d:
        if window is None:
            H,W=d.height//f,d.width//f
            a=d.read(1,out_shape=(H,W),resampling=Resampling.average if f>1 else Resampling.nearest,masked=True)
            t=d.transform*d.transform.scale(d.width/W,d.height/H)
        else:
            a=d.read(1,window=window,masked=True); t=d.window_transform(window)
            if f>1:
                a=a[::1,::1]; H,W=a.shape[0]//f,a.shape[1]//f
                a=np.ma.masked_invalid(a.filled(np.nan)[:H*f,:W*f].reshape(H,f,W,f).mean(axis=(1,3))); t=t*t.scale(f,f)
    return a.astype("float64"),t
def hillshade(z,cs,az=315,alt=45,ex=2):
    from scipy.ndimage import distance_transform_edt as _edt
    _i=_edt(np.ma.getmaskarray(z),return_distances=False,return_indices=True); zz=z.data[tuple(_i)]  # edge-pad with nearest valid value, no false cliff at the DEM edge
    gy,gx=np.gradient(zz*ex,cs)
    slope=np.arctan(np.hypot(gx,gy)); aspect=np.arctan2(-gx,gy)
    al=np.radians(alt)   # multi-directional: average of four azimuths so no edge sits in deep shadow
    return np.mean([np.clip(np.sin(al)*np.cos(slope)+np.cos(al)*np.sin(slope)*np.cos(np.radians(a)-aspect),0,1) for a in (225,270,315,360)],axis=0)
def rgb(z,cs,vmin,vmax):
    hs=hillshade(z,cs)
    c=matplotlib.colormaps["gist_earth"](0.12+0.75*np.clip((z.filled(vmin)-vmin)/(vmax-vmin),0,1))[...,:3]
    out=c*(0.35+0.65*hs[...,None]); alpha=(~z.mask).astype(float)
    return np.dstack([out,alpha])
def png(a,q=None):
    im=Image.fromarray((a*255).astype("uint8"),"RGBA"); b=io.BytesIO(); im.save(b,"PNG",optimize=True); return "data:image/png;base64,"+base64.b64encode(b.getvalue()).decode()
def path(g,t):
    inv=~t; parts=[]
    geoms=getattr(g,"geoms",[g])
    for p in geoms:
        for ring in [p.exterior,*p.interiors]:
            pts=[inv*(x,y) for x,y in np.asarray(ring.coords)[:,:2]]
            parts.append("M"+"L".join(f"{c:.1f},{r:.1f}" for c,r in pts)+"Z")
    return "".join(parts)
out={}
# ---- 2D whole watershed at 8 m
z,t=read(8); vmin,vmax=float(z.min()),float(z.max())
out["ws2d"]=dict(img=png(rgb(z,8,vmin,vmax)),w=z.shape[1],h=z.shape[0],huc=path(huc.simplify(8),t),buf=path(buf.simplify(8),t),
                 site=path(site,t),site_c=list(~t*(site.centroid.x,site.centroid.y)),cs=8,zmin=vmin,zmax=vmax)
# ---- 3D whole watershed at 30 m
z3,t3=read(30)
def line3d(g,t,z,step):
    xs,ys,zs=[],[],[]
    for p in getattr(g,"geoms",[g]):
        ring=p.exterior.segmentize(step); 
        for x,y in np.asarray(ring.coords)[:,:2]:
            c,r=~t*(x,y); r=int(np.clip(r,0,z.shape[0]-1)); c=int(np.clip(c,0,z.shape[1]-1))
            v=z.data[r,c] if not z.mask[r,c] else np.nan
            xs.append(round((x-t.c)/1000,4)); ys.append(round((y-(t.f+t.e*z.shape[0]))/1000,4)); zs.append(None if np.isnan(v) else round(float(v)+3,1))
        xs.append(None);ys.append(None);zs.append(None)
    return dict(x=xs,y=ys,z=zs)
Z=np.where(z3.mask,None,np.round(z3.data,1))[::-1].tolist()  # row 0 = south
out["ws3d"]=dict(z=Z,dx=30/1000,nx=z3.shape[1],ny=z3.shape[0],huc=line3d(huc.simplify(30),t3,z3,30),
                 site=line3d(site.buffer(15),t3,z3,10),zmin=vmin,zmax=vmax)
# ---- site close-up: 800 m box, 1 m for 2D, 2 m for 3D
cx,cy=site.centroid.x,site.centroid.y; half=400
with rasterio.open(dem_p) as d:
    win=rasterio.windows.from_bounds(cx-half,cy-half,cx+half,cy+half,d.transform).round_offsets().round_lengths()
zs1,ts1=read(1,win); zs2,ts2=read(2,win)
smin,smax=float(np.nanmin(zs1)),float(np.nanmax(zs1))
out["site2d"]=dict(img=png(rgb(zs1,1,smin,smax)),w=zs1.shape[1],h=zs1.shape[0],site=path(site,ts1),huc=path(huc,ts1),cs=1,zmin=smin,zmax=smax)
Zs=np.round(zs2.filled(np.nan),2)[::-1]
out["site3d"]=dict(z=np.where(np.isnan(Zs),None,Zs).tolist(),dx=2,nx=zs2.shape[1],ny=zs2.shape[0],site=None,zmin=smin,zmax=smax)
xs,ys,zz=[],[],[]
for x,y in np.asarray(site.exterior.segmentize(2).coords)[:,:2]:
    c,r=~ts2*(x,y); v=zs2.data[int(r),int(c)]
    xs.append(round(x-ts2.c,1)); ys.append(round(y-(ts2.f+ts2.e*zs2.shape[0]),1)); zz.append(round(float(v)+0.3,2))
out["site3d"]["site"]=dict(x=xs,y=ys,z=zz)
out["meta"]=dict(huc12="110100070301",name="Strother Creek",area_km2=round(huc.area/1e6,2),site_m2=round(site.area),
   dem_px=[16294,11637],site_xy=[round(cx,1),round(cy,1)])
import rasterio.mask
with rasterio.open(dem_p) as d:
    sv=rasterio.mask.mask(d,[site],crop=True,filled=False)[0].compressed()
out["meta"]["site_elev"]=[round(float(sv.min()),2),round(float(sv.max()),2),round(float(np.median(sv)),2)]
s=json.dumps(out,separators=(",",":")); open("data.json","w").write(s); print(len(s)/1e6,"MB", out["meta"], vmin,vmax,smin,smax, z3.shape, zs1.shape)
