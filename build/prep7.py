# Adds radar (NISAR, Sentinel-1) and random-forest layers, all on the 16 m TWI grid, + tables to data4.json -> data7.json
# Categorical layers (cats) are coloured per class value; 0 and no data show as grey relief
# 3D grids packed as uint8: value = off + u/scale, 255 = no data
import json, base64, io, sys, numpy as np, pandas as pd, rasterio, geopandas as gpd, matplotlib
from rasterio.enums import Resampling
from rasterio.warp import reproject
from scipy.ndimage import distance_transform_edt as edt
from PIL import Image
P="/home/sgf.edubear.net/xm7303/Wetland2026/"; ST=P+"data/SAR/NISAR/stack/"
dem_p=P+"data/LiDAR/USGS_3DEP_1m/dem_1m_110100070301_buf200.tif"
S1D=P+"data/SAR/Sentinel1/stack/"; MD=P+"data/model/"
FILES={"n":ST+"desc_t012_summary_16m.tif","ss":S1D+"s1_summer_summary_16m.tif","sw":S1D+"s1_leafoff_summary_16m.tif",
       "pt":MD+"rf_prob_topo.tif","pa":MD+"rf_prob_topo_all.tif","wet":MD+"rf_wet_all_gw_s2.tif","pg":MD+"rf_prob_all_gw_s2.tif","th":P+"data/Thermal/thermal_16m.tif","sc":P+"data/Thermal/seep_candidates_16m.tif","geo":"geo_units_16m.tif","gw":P+"data/Groundwater/gw_16m_110100070301.tif","eco":P+"data/Thermal/eco_16m.tif","s2":P+"data/Imagery/Sentinel2/s2_pheno_16m.tif","coh":P+"data/SAR/NISAR/GUNW/coh_16m.tif"}
BAND={"nhh":("n","HH_all"),"nchg":("n","HH_change"),"nhv":("n","HV_all"),"nhvchg":("n","HV_change"),"nratio":("n",("HH_all","HV_all")),
      "svv":("ss","VV_all"),"svh":("ss","VH_all"),"svvchg":("ss","VV_change"),"wvvchg":("sw","VV_change"),
      "rft":("pt",1),"rfa":("pa",1),"rfg":("pg",1),"rfw":("wet",1),"hand":("gw","hand_01"),"gwt":("th","gw_thermal"),"snow":("th","snowfree_resid"),"seep":("sc",1),"geo":("geo",1),"swt":("gw","ssurgo_wt_cm"),"econ":("eco","night_winter"),"ndmi":("s2","ndmi_latesummer"),"cohd":("coh","coh_D_mean12"),"coha":("coh","coh_A_mean12"),"cohdrop":("coh","coh_D_drop")}   # tuple = first minus second (dB); int = band number
KEYS=sys.argv[1:] or list(BAND)
R={"nhh":dict(cmap="gray",lo=-14,hi=-2,sym=False),"nchg":dict(cmap="BrBG",lo=-2.5,hi=2.5,sym=True),"nhv":dict(cmap="gray",lo=-20,hi=-8,sym=False),
   "nhvchg":dict(cmap="BrBG",lo=-2.5,hi=2.5,sym=True),"nratio":dict(cmap="Purples",lo=3,hi=8.5,sym=False),
   "svv":dict(cmap="gray",lo=-16,hi=-4,sym=False),"svh":dict(cmap="gray",lo=-22,hi=-10,sym=False),
   "svvchg":dict(cmap="BrBG",lo=-2.5,hi=2.5,sym=True),"wvvchg":dict(cmap="BrBG",lo=-2.5,hi=2.5,sym=True),
   "rft":dict(cmap="YlGnBu",lo=0,hi=1,sym=False),"rfa":dict(cmap="YlGnBu",lo=0,hi=1,sym=False),
   "rfg":dict(cmap="YlGnBu",lo=0,hi=1,sym=False),"hand":dict(cmap="YlGnBu_r",lo=0,hi=10,sym=False),"swt":dict(cmap="YlGnBu_r",lo=0,hi=200,sym=False),
   "gwt":dict(cmap="RdBu_r",lo=-2,hi=2,sym=True),"econ":dict(cmap="RdBu_r",lo=-2,hi=2,sym=True),"ndmi":dict(cmap="BrBG",lo=-0.1,hi=0.1,sym=True),"snow":dict(cmap="PuOr_r",lo=-0.3,hi=0.3,sym=True),
   "cohd":dict(cmap="cividis",lo=0.2,hi=0.9,sym=False),"coha":dict(cmap="cividis",lo=0.1,hi=0.65,sym=False),"cohdrop":dict(cmap="BrBG",lo=-0.2,hi=0.2,sym=True),
   "seep":dict(cmap=None,lo=0,hi=1,sym=False,cats=[[1,"#e7298a","Seep candidate (thermal)"]]),
   "geo":dict(cmap=None,lo=0,hi=5,sym=False,cats=[[1,"#d8c48f","Eminence Dolomite"],[2,"#9cc0a8","Gasconade Dolomite"],[3,"#b79bc6","Potosi Dolomite"],[4,"#8ea1cf","Davis Formation"],[5,"#d6a07a","Roubidoux Formation"]]),
   "rfw":dict(cmap=None,lo=0,hi=2,sym=False,cats=[[1,"#8fbde0","Wet at the lenient (ROC) cut-off only"],[2,"#1f5fa8","Wet at the strict (F1) cut-off"]])}
site=gpd.read_file(P+"data/StudySite/study_site.gpkg").to_crs(26915).geometry.iloc[0]
D=json.load(open("data4.json"))
SRC={}
for k in KEYS:
    f,b=BAND[k]
    with rasterio.open(FILES[f]) as s:
        rd=lambda b:s.read(b if isinstance(b,int) else s.descriptions.index(b)+1).astype("float32")
        a=rd(b[0])-rd(b[1]) if isinstance(b,tuple) else rd(b)
        if s.nodata is not None and np.isfinite(s.nodata): a[a==s.nodata]=np.nan
        SRC[k]=a; src_t=s.transform; src_crs=s.crs
def on(k,transform,shape,rs=Resampling.nearest):
    out=np.full(shape,np.nan,"float32")
    reproject(SRC[k],out,src_transform=src_t,src_crs=src_crs,src_nodata=np.nan,dst_transform=transform,dst_crs=src_crs,dst_nodata=np.nan,resampling=rs)
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
def webp(rgba,q=80):
    b=io.BytesIO(); Image.fromarray((rgba*255).astype("uint8"),"RGBA").save(b,"WEBP",quality=q,method=6)
    return "data:image/webp;base64,"+base64.b64encode(b.getvalue()).decode()
def frac(k,v):
    r=R[k]; return np.clip((np.nan_to_num(v,nan=r["lo"])-r["lo"])/(r["hi"]-r["lo"]),0,1)
def img(k,z,t,cs):
    # radar values shown flat (no relief shading, which would read as backscatter); grey relief outside the HUC
    v=on(k,t,z.shape); h=hs(z,cs)
    if R[k].get("cats"):
        rgb=np.zeros(v.shape+(3,))
        for val,col,_ in R[k]["cats"]: rgb[v==val]=matplotlib.colors.to_rgb(col)
        v=np.where(np.isin(v,[c[0] for c in R[k]["cats"]]),v,np.nan)
    else:
        rgb=matplotlib.colormaps[R[k]["cmap"]](frac(k,v))[...,:3]
    grey=~np.isfinite(v)&~z.mask
    rgb[grey]=((0.62+0.33*h)[...,None]*np.ones(3))[grey]
    return webp(np.dstack([rgb,(np.isfinite(v)|grey).astype(float)]))
def pack(v,k):
    r=R[k]; sc=254/(r["hi"]-r["lo"])
    u=np.where(np.isfinite(v),np.clip(np.round((v-r["lo"])*sc),0,254),255).astype("u1")   # categorical: 0 stays a value (neutral colour in 3D)
    return dict(b64=base64.b64encode(u.tobytes()).decode(),ny=v.shape[0],nx=v.shape[1],scale=sc,off=r["lo"],u8=1)
z8,t8=dem_grid(8)
cx,cy=site.centroid.x,site.centroid.y
with rasterio.open(dem_p) as d:
    win=rasterio.windows.from_bounds(cx-400,cy-400,cx+400,cy+400,d.transform).round_offsets().round_lengths()
z1,t1=dem_grid(1,win); z30,t30=dem_grid(30); z2,t2=dem_grid(2,win)
for k in KEYS:
    D["ws2d"][k]=img(k,z8,t8,8); D["site2d"][k]=img(k,z1,t1,1)
    D["ws3d"][k]=pack(on(k,t30,z30.shape)[::-1],k); D["site3d"][k]=pack(on(k,t2,z2.shape)[::-1],k)
    if R[k].get("cats"): D["ramps"][k]={**R[k],"hex":[c[1] for c in R[k]["cats"]]}
    else:
        cm=matplotlib.colormaps[R[k]["cmap"]]
        D["ramps"][k]={**R[k],"hex":[matplotlib.colors.to_hex(cm(i/10)) for i in range(11)]}
# pass table + land-cover-stratified AUCs
q=pd.read_csv(P+"data/SAR/NISAR/GCOV/pass_wetness.csv")
q=q[q.use&q.direction.str.startswith("D")&(q["mode"]==4005)].sort_values("start")
E=json.load(open(ST+"stack_eval.json"))
grp=lambda d:"wet" if d in E["wet_dates"] else "dry" if d in E["dry_dates"] else "—"
D["nisar"]=dict(passes=[dict(date=s[:10],S=round(a),rain7=round(b,1),hh=round(c,2),hv=round(e,2),g=grp(s[:10]))
                        for s,a,b,c,e in zip(q.start,q.S_pass_mm,q.rain7_mm,q.hh_db_median_valid,q.hv_db_median_valid)],
                auc={c:dict(n=E["by_cover"][c]["n_wetland"],n0=E["by_cover"][c]["n_other"],v=E["by_cover"][c]["auc"]) for c in ("forest","open")},
                fen=E["by_cover"]["fen"])
# Sentinel-1 passes and scores, valley-floor comparison, random-forest results
w=pd.read_csv(P+"data/SAR/Sentinel1/OPERA_RTC/pass_wetness.csv").sort_values("start")
E1=json.load(open(S1D+"s1_stack_eval.json"))
used={d for se in E1.values() for d in se["passes"]}
D["s1"]=dict(passes=[dict(date=r.start[:10],S=round(r.S_pass_mm),rain7=round(r.rain7_mm,1),vv=round(r.vv_db_median_valid,2),vh=round(r.vh_db_median_valid,2),
                          g=(r.group if isinstance(r.group,str) and r.start[:10] in used else "—"),season=("winter" if r.start[:10] in E1["leafoff"]["passes"] else "summer" if r.start[:10] in E1["summer"]["passes"] else "not used"))
                     for r in w.itertuples()],
             auc={se:{c:dict(n=E1[se]["by_cover"][c]["n_wetland"],v=E1[se]["by_cover"][c]["auc"]) for c in ("forest","open")} for se in E1},
             fen={se:E1[se]["by_cover"]["fen"] for se in E1})
D["valley"]=pd.read_csv(P+"data/SAR/radar_valley_auc.csv").to_dict("records")
RF=json.load(open(MD+"rf_results.json"))
D["rf"]={k:RF[k] for k in ("cells","block_m","folds","baseline","sets","importance_full","fen_median_prob")}
D["rf"]["thr"]=json.load(open(MD+"rf_thresholds.json"))
G=json.load(open(P+"data/Groundwater/gw_eval.json"))
TE=json.load(open(P+"data/Thermal/thermal_eval.json")); GE=json.load(open(P+"data/Geology/geology_eval.json"))
EE=json.load(open(P+"data/Thermal/eco_eval.json")); SE=json.load(open(P+"data/Imagery/Sentinel2/s2_eval.json"))
EV=(TE,GE,EE,SE)
D["th"]={"auc":{c:{k:v for e in EV for k,v in e["by_cover"][c]["auc"].items()} for c in ("forest","open")},
         "fen_pct":{k:v for e in EV for k,v in e["by_cover"]["fen"]["percentile_among_open"].items()},
         "fen":{**TE["by_cover"]["fen"]["median"],**GE["fen_values"],**EE["by_cover"]["fen"]["median"],**SE["by_cover"]["fen"]["median"]},"n":{k:len(v) for k,v in TE["scenes"].items()},
         "seep":json.load(open(P+"data/Thermal/seep_candidates.json")),"units":GE["units"],
         "eco":{"passes":EE["passes"],"fen_valley":EE["fen_pct_in_valley"],"rho":EE["spearman_vs_landsat_gw"]},
         "s2":{"scenes":SE["scenes"],"fen_valley":SE["fen_pct_in_valley"]}}
D["gw"]={"auc":{c:G["by_cover"][c]["auc"] for c in ("forest","open")},"n":{c:G["by_cover"][c]["n_wetland"] for c in ("forest","open")},
         "fen":G["fen_values"],"fen_pct":G["by_cover"]["fen"]["percentile_among_open"],"rho":G["spearman_vs_twi"]}
for v in D["rf"]["sets"].values(): v.pop("features",None)
RB=json.load(open(MD+"robustness.json")); DL=json.load(open(MD+"dl_results.json"))
D["rob"]={"sets":{k:{f:v[f] for f in ("ap_ci","ap_no_edge","ap_fold")} for k,v in RB["sets"].items()},"paired":RB["paired_ap_diff"],
          "edge_share":RB["edge_share_of_wetland"],"no_skill_no_edge":RB["no_skill_ap_no_edge"],"random_cv":RB["random_cv"],
          "emergent":{k:{m:v[m]["open"]|{"fen_pct_all":v[m]["fen_pct_all"]} for m in ("standard","held_out")} for k,v in RB["emergent_holdout"].items()},
          "learners":RB["learners"],"dl":{k:DL[k] for k in ("unet","pixel")}}
# NISAR GUNW coherence: composites, viewing geometry, random-forest ablation (Wetland2026/scripts/37-40)
GD=P+"data/SAR/NISAR/GUNW/"; CE=json.load(open(GD+"coherence_eval.json")); CG=json.load(open(GD+"coherence_geometry.json")); CR=json.load(open(MD+"coherence_rf.json"))
D["coh"]={"pairs":pd.read_csv(GD+"granules.csv")[["direction","ref","sec","days"]].astype({"ref":str,"sec":str}).to_dict("records"),
          "comp":{k:{f:v.get(f) for f in ("fen_median","fen_pct_open","fen_pct_valley_open","open_median","forest_median","auc_open","auc_open_no_edge","auc_emergent_open")} for k,v in CE["composites"].items()},
          "geom":{d:{f:g[f] for f in ("fen_lia_median","fen_shadow_share","fen_near_share","geometry_r2_open","fen_pct_open_raw","fen_pct_open_residual")}|{"inc":round(g["los"]["inc"],1)} for d,g in CG.items()},
          "rf":{"sets":{k:{f:v[f] for f in ("ap","ap_ci","ap_no_edge","auc_open","fen_pct_all")} for k,v in CR["sets"].items()},"paired":CR["paired"],
                "emergent":CR["emergent_holdout"],"best_rank":min(r for f,(r,_) in CR["impurity_rank"].items() if f.startswith("coh_")),"n_feat":len(json.loads(str(np.load(MD+"rf_cache.npz")["sets"]))["all_gw_s2"])+len(CR["features"])}}
s=json.dumps(D,separators=(",",":")).replace("</","<\\/"); open("data7.json","w").write(s)
print(len(s)/1e6,"MB",{k:{c:len(json.dumps(D[c][k]))//1000 for c in ("ws2d","site2d","ws3d","site3d")} for k in KEYS})
