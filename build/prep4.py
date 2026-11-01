# Adds 16 m TWI + 16 m hydroperiod layers, resolution AUCs and the site daily saturation calendar to data3.json -> data4.json
import json, base64, io, numpy as np, pandas as pd, rasterio, geopandas as gpd, matplotlib
from rasterio.enums import Resampling
from rasterio.warp import reproject
from scipy.ndimage import distance_transform_edt as edt
from PIL import Image
P="/home/sgf.edubear.net/xm7303/Wetland2026/"; T=P+"data/twi/pilot_110100070301/"
dem_p=P+"data/LiDAR/USGS_3DEP_1m/dem_1m_110100070301_buf200.tif"
site=gpd.read_file(P+"data/StudySite/study_site.gpkg").to_crs(26915).geometry.iloc[0]
D=json.load(open("data3.json"))
SRC={"twi16":T+"resolution/twi_16m_110100070301.tif",
     "hps":T+"dynamic_16m/hydroperiod_mean_110100070301.tif",
     "hpu":T+"dynamic_16m_unisoil/hydroperiod_mean_110100070301.tif"}
def on(src,transform,shape,rs):
    out=np.full(shape,np.nan,"float32")
    with rasterio.open(src) as s:
        reproject(rasterio.band(s,1),out,src_nodata=s.nodata,dst_transform=transform,dst_crs=s.crs,dst_nodata=np.nan,resampling=rs)
    return out
def dem_grid(f,window=None):
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
    i=edt(np.ma.getmaskarray(z),return_distances=False,return_indices=True); zz=z.data[tuple(i)]
    gy,gx=np.gradient(zz*ex,cs); sl=np.arctan(np.hypot(gx,gy)); asp=np.arctan2(-gx,gy); al=np.radians(45)
    return np.mean([np.clip(np.sin(al)*np.cos(sl)+np.cos(al)*np.sin(sl)*np.cos(np.radians(a)-asp),0,1) for a in (225,270,315,360)],axis=0)
def webp(rgba):
    b=io.BytesIO(); Image.fromarray((rgba*255).astype("uint8"),"RGBA").save(b,"WEBP",quality=82,method=6)
    return "data:image/webp;base64,"+base64.b64encode(b.getvalue()).decode()
# value ranges: TWI 16 m from its own 2-98 percentiles, hydroperiod 0-365 days
with rasterio.open(SRC["twi16"]) as s: a=s.read(1,masked=True).compressed()
lo,hi=np.percentile(a,[2,98]).round(0)
R={"twi16":dict(cmap="Blues",lo=float(lo),hi=float(hi)),"hps":dict(cmap="YlGnBu",lo=0,hi=365),"hpu":dict(cmap="YlGnBu",lo=0,hi=365)}
def img(key,z,t,cs):
    v=on(SRC[key],t,z.shape,Resampling.nearest); h=hs(z,cs); r=R[key]; cm=matplotlib.colormaps[r["cmap"]]
    c=cm(0.08+0.92*np.clip((np.nan_to_num(v,nan=r["lo"])-r["lo"])/(r["hi"]-r["lo"]),0,1))[...,:3]
    rgb=c*(0.55+0.45*h[...,None]); grey=~np.isfinite(v)&~z.mask   # outside HUC / masked open water -> grey relief
    rgb[grey]=((0.62+0.33*h)[...,None]*np.ones(3))[grey]
    return webp(np.dstack([rgb,(np.isfinite(v)|grey).astype(float)]))
z8,t8=dem_grid(8)
cx,cy=site.centroid.x,site.centroid.y
with rasterio.open(dem_p) as d:
    win=rasterio.windows.from_bounds(cx-400,cy-400,cx+400,cy+400,d.transform).round_offsets().round_lengths()
z1,t1=dem_grid(1,win); z30,t30=dem_grid(30); z2,t2=dem_grid(2,win)
for k in SRC:
    D["ws2d"][k]=img(k,z8,t8,8); D["site2d"][k]=img(k,z1,t1,1)
    for key,(z,t,rs,nd) in {"ws3d":(z30,t30,Resampling.average,0),"site3d":(z2,t2,Resampling.nearest,1)}.items():
        v=on(SRC[k],t,z.shape,rs)[::-1]; D[key][k]=np.where(np.isfinite(v),np.round(v,nd),None).tolist()
D["ramps"]={k:{**r,"hex":[matplotlib.colors.to_hex(matplotlib.colormaps[r["cmap"]](0.08+0.92*i/10)) for i in range(11)]} for k,r in R.items()}
# resolution AUCs + dynamic runs
res=json.load(open(T+"resolution/resolution.json"))
dyn={}
for tag,r in [("dynamic",1),("dynamic_8m",8),("dynamic_16m",16),("dynamic_8m_unisoil",8),("dynamic_16m_unisoil",16)]:
    s=json.load(open(T+tag+"/summary.json"))
    dyn.setdefault("uni" if "unisoil" in tag else "soil",[]).append(dict(res=r,auc=s["auc_nwi_vegetated_mean_hydroperiod"],site_days=s["site_mean_hydroperiod_days"]["median"],site_pct=s["site_hydroperiod_percentile_in_huc"]))
D["auc"]=dict(computed=[dict(res=int(k[:-1]),auc=v["computed"]["auc_vegetated"],site_pct=v["computed"]["site_median_percentile"]) for k,v in res.items()],
              aggregated=[dict(res=int(k[:-1]),auc=v["aggregated"]["auc_vegetated"],site_pct=v["aggregated"]["site_median_percentile"]) for k,v in res.items() if "aggregated" in v],**dyn)
for k in ("computed","aggregated"): D["auc"][k].sort(key=lambda x:x["res"])
# site daily saturation by water year (rows WY, cols day of WY from Oct 1)
cal={}
for k,tag in [("soil","dynamic_16m"),("uni","dynamic_16m_unisoil")]:
    df=pd.read_csv(T+tag+"/site_daily.csv",parse_dates=["date"])
    wy=df.date.dt.year+(df.date.dt.month>=10); doy=(df.date-pd.to_datetime((wy-1).astype(str)+"-10-01")).dt.days
    years=sorted(wy.unique()); M=[[None]*366 for _ in years]; Pm=[[None]*366 for _ in years]
    for y,dd,f,p in zip(wy,doy,df.site_saturated_frac,df.P_mm):
        M[years.index(y)][dd]=int(round(f*100)); Pm[years.index(y)][dd]=round(p,1)
    cal[k]=M; cal["years"]=[int(y) for y in years]; cal["P"]=Pm
    cal[k+"_ncells"]=int(round(1/np.diff(np.unique(df.site_saturated_frac)).min()))
D["cal"]=cal
s=json.dumps(D,separators=(",",":")).replace("</","<\\/"); open("data4.json","w").write(s)
print(len(s)/1e6,"MB",R,{k:len(json.dumps(v))//1000 for k,v in D.items()},cal["years"][:3],cal["soil_ncells"])
