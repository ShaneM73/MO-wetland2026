# Adds the USCRN Salem soil-moisture comparison (observed 0-100 cm water vs model store) to data4.json
import json, numpy as np, pandas as pd
T="/home/sgf.edubear.net/xm7303/Wetland2026/data/twi/pilot_110100070301/"
D=json.load(open("data4.json"))
df=pd.read_csv(T+"validation/soil_moisture/daily_compare.csv",parse_dates=["date"])
S=json.load(open(T+"validation/soil_moisture/summary.json"))
def rel(s): return ((s-s.min())/(s.max()-s.min())*100).round(0)
i=lambda s:[None if pd.isna(v) else int(v) for v in s]
D["sm"]=dict(start=str(df.date.iloc[0].date()),obs=i(rel(df.obs_mm)),mod=i(rel(df.S_huc)),obs_mm=i(df.obs_mm.round(0)),mod_mm=i(df.S_huc.round(0)),
  rain=[None if pd.isna(v) else round(v,1) for v in df.P_station],
  score={k:S["scores"][f"{k}__vs__obs_mm"] for k in ("S_huc","S_station","site_sat_soil","site_sat_uni")},
  sweep=S["s_max_sweep_station_rain"],rain_yr=S["rain_mm_per_yr"],obs_range=[int(df.obs_mm.min()),int(df.obs_mm.max())])
s=json.dumps(D,separators=(",",":")).replace("</","<\\/"); open("data4.json","w").write(s)
print(len(s)/1e6,"MB",len(D["sm"]["obs"]),D["sm"]["score"]["S_huc"])
