# Split data6.json + template.html into a static site: index.html, data/core.json, data/img/*.webp, data/grid/*.json
import json, base64, sys, shutil
from pathlib import Path
out = Path(sys.argv[1]); dd = out / "data"
for sub in ("img", "grid"): (dd / sub).mkdir(parents=True, exist_ok=True)
D = json.load(open(sys.argv[2] if len(sys.argv) > 2 else "data7.json"))
keys = ["twi"] + list(D["ramps"])
for v in ("ws2d", "site2d"):
    (dd / "img" / f"{v}_elev.webp").write_bytes(base64.b64decode(D[v].pop("img").split(",", 1)[1]))
    for k in keys:
        (dd / "img" / f"{v}_{k}.webp").write_bytes(base64.b64decode(D[v].pop(k).split(",", 1)[1]))
for v in ("ws3d", "site3d"):
    for k in keys:
        (dd / "grid" / f"{v}_{k}.json").write_text(json.dumps(D[v].pop(k), separators=(",", ":")))
(dd / "core.json").write_text(json.dumps(D, separators=(",", ":")))
t = open("template.html", encoding="utf-8").read()
t = t.replace('<title>Strother Creek LiDAR DEM</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n',
  '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1">\n'
  '<title>Strother Creek wetland viewer</title>\n<meta name="description" content="Missouri wetland pilot: 1 m LiDAR DEM, TWI, hydroperiod, NWI and NISAR L-band radar for HUC12 110100070301.">\n', 1)
t = t.replace("<style>", "<style>\nbody { margin: 0; background: var(--bg); color: var(--fg); }", 1)
(out / "index.html").write_text(t.replace("</style>", "</style>\n</head>\n<body>", 1) + "\n</body>\n</html>\n", encoding="utf-8")
tot = sum(f.stat().st_size for f in out.rglob("*") if f.is_file() and ".git" not in f.parts)
print(f"{len(keys)} layers; core {(dd/'core.json').stat().st_size/1e6:.2f} MB; site {tot/1e6:.1f} MB")
