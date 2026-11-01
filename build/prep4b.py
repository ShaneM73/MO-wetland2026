# Pack the new 3D surfacecolor layers as base64 uint16 (value*scale, 65535 = no data) to fit the 16 MB page limit
import json, base64, numpy as np
D=json.load(open("data4.json"))
SC={"twi16":10,"hps":1,"hpu":1}
for key in ("ws3d","site3d"):
    for k,sc in SC.items():
        a=np.array([[np.nan if v is None else v for v in row] for row in D[key][k]],"f8")
        u=np.where(np.isfinite(a),np.clip(np.round(a*sc),0,65534),65535).astype("<u2")
        D[key][k]=dict(b64=base64.b64encode(u.tobytes()).decode(),ny=a.shape[0],nx=a.shape[1],scale=sc)
s=json.dumps(D,separators=(",",":")).replace("</","<\\/"); open("data4.json","w").write(s)
print(len(s)/1e6,"MB",{k:len(json.dumps(v))//1000 for k,v in D.items()})
