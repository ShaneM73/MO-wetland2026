import json, base64, io, numpy as np, rasterio, rasterio.mask, geopandas as gpd, matplotlib
from rasterio.enums import Resampling
from rasterio.warp import reproject
from PIL import Image
P="/home/sgf.edubear.net/xm7303/Wetland2026/"
dem_p=P+"data/LiDAR/USGS_3DEP_1m/dem_1m_110100070301_buf200.tif"
twi_p=P+"data/twi/pilot_110100070301/twi_110100070301.tif"
site=gpd.read_file(P+"data/StudySite/study_site.gpkg").geometry.iloc[0]
D=json.load(open("data.json"))
LO,HI=2.0,14.0
cmap=matplotlib.colormaps["Blues"]
def twi_on(transform,shape,rs):
    out=np.full(shape,np.nan,"float32")
    with rasterio.open(twi_p) as s:
        reproject(rasterio.band(s,1),out,dst_transform=transform,dst_crs=s.crs,dst_nodata=np.nan,resampling=rs)
    return out
def dem_grid(f=None,window=None):
    with rasterio.open(dem_p) as d:
        if window is None:
            H,W=d.height//f,d.width//f
            z=d.read(1,out_shape=(H,W),resampling=Resampling.average,masked=True); t=d.transform*d.transform.scale(d.width/W,d.height/H)
        else:
            z=d.read(1,window=window,masked=True); t=d.window_transform(window)
            if f>1:
                H,W=z.shape[0]//f,z.shape[1]//f
                z=np.ma.masked_invalid(z.filled(np.nan)[:H*f,:W*f].reshape(H,f,W,f).mean(axis=(1,3))); t=t*t.scale(f,f)
    return z.astype("float64"),t
def hs(z,cs,ex=2):
    from scipy.ndimage import distance_transform_edt as _edt
    _i=_edt(np.ma.getmaskarray(z),return_distances=False,return_indices=True); zz=z.data[tuple(_i)]  # edge-pad with nearest valid value, no false cliff at the DEM edge
    gy,gx=np.gradient(zz*ex,cs)
    sl=np.arctan(np.hypot(gx,gy)); asp=np.arctan2(-gx,gy); al=np.radians(45)
    return np.mean([np.clip(np.sin(al)*np.cos(sl)+np.cos(al)*np.sin(sl)*np.cos(np.radians(a)-asp),0,1) for a in (225,270,315,360)],axis=0)
def webp(rgba):
    b=io.BytesIO(); Image.fromarray((rgba*255).astype("uint8"),"RGBA").save(b,"WEBP",quality=82,method=6)
    return "data:image/webp;base64,"+base64.b64encode(b.getvalue()).decode()
def twi_img(z,t,cs,rs):
    tw=twi_on(t,z.shape,rs); h=hs(z,cs)
    c=cmap(0.08+0.92*np.clip((np.nan_to_num(tw,nan=LO)-LO)/(HI-LO),0,1))[...,:3]
    rgb=c*(0.55+0.45*h[...,None])
    ring=~np.isfinite(tw)&~z.mask           # buffer ring: DEM but no TWI (TWI is clipped to the HUC12)
    g=(0.62+0.33*h)[...,None]*np.array([1.0,1.0,1.0])
    rgb[ring]=g[ring]; a=(np.isfinite(tw)|ring).astype(float)
    return webp(np.dstack([rgb,a])), tw
def reimg(key):  # re-encode existing elevation PNG as WebP to save space
    b=base64.b64decode(D[key]["img"].split(",")[1]); im=Image.open(io.BytesIO(b)).convert("RGBA")
    o=io.BytesIO(); im.save(o,"WEBP",quality=82,method=6); D[key]["img"]="data:image/webp;base64,"+base64.b64encode(o.getvalue()).decode()
for k in ("ws2d","site2d"): reimg(k)
# 2D watershed (8 m, max keeps narrow wet channels visible at display scale)
z,t=dem_grid(8); D["ws2d"]["twi"],_=twi_img(z,t,8,Resampling.max)
# 2D site 1 m
cx,cy=site.centroid.x,site.centroid.y
with rasterio.open(dem_p) as d:
    win=rasterio.windows.from_bounds(cx-400,cy-400,cx+400,cy+400,d.transform).round_offsets().round_lengths()
z1,t1=dem_grid(1,win); D["site2d"]["twi"],_=twi_img(z1,t1,1,Resampling.nearest)
# 3D surface colors on the same grids as the 3D DEMs (rows south->north)
z3,t3=dem_grid(30); tw3=twi_on(t3,z3.shape,Resampling.max)[::-1]
D["ws3d"]["twi"]=np.where(np.isfinite(tw3),np.round(tw3,1),None).tolist()
z2,t2=dem_grid(2,win); tw2=twi_on(t2,z2.shape,Resampling.average)[::-1]
D["site3d"]["twi"]=np.where(np.isfinite(tw2),np.round(tw2,1),None).tolist()
# histograms at full 1 m
with rasterio.open(twi_p) as s:
    a=s.read(1,masked=True).compressed()
    sv=rasterio.mask.mask(s,[site],crop=True,filled=False)[0].compressed()
edges=np.arange(-1,20.01,0.5)
hw,_=np.histogram(np.clip(a,-1,19.99),edges); hsite,_=np.histogram(np.clip(sv,-1,19.99),edges)
D["hist"]=dict(edges=edges.round(2).tolist(),ws=(hw/hw.sum()).round(5).tolist(),site=(hsite/hsite.sum()).round(5).tolist(),
  ws_n=int(a.size),site_n=int(sv.size),ws_med=float(np.median(a)),site_med=float(np.median(sv)),
  ws_p95=float(np.percentile(a,95)),site_p75=float(np.percentile(sv,75)),pct_site_med=float((a<np.median(sv)).mean()*100))
D["twi_range"]=[LO,HI]
D["twi_ramp"]=[matplotlib.colors.to_hex(cmap(0.08+0.92*i/10)) for i in range(11)]
s=json.dumps(D,separators=(",",":")); open("data2.json","w").write(s)
print(len(s)/1e6,"MB",{k:len(json.dumps(v))//1000 for k,v in D.items()}, D["twi_ramp"], {k:v for k,v in D["hist"].items() if not isinstance(v,list)})
