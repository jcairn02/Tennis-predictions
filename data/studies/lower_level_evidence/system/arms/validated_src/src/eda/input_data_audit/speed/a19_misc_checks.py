"""Audit step 19: remaining checks. Sackmann Speed_KMH vs Speed_MPH (unit consistency per file); identical A/B values;
date placement (obs vs tournament start) by source; the 12 identical-side matches. Read-only."""
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path.cwd()
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)

print("=== Sackmann files: Speed_KMH / Speed_MPH where both > 0")
rows = []
for f in sorted((ROOT / "data/dump/points/sackmann_archive/slam_pointbypoint").glob("*-points.parquet")):
    if "doubles" in f.name or "mixed" in f.name:
        continue
    cols = pq.read_schema(f).names
    if "Speed_KMH" not in cols:
        rows.append({"file": f.stem, "note": "no Speed_KMH"})
        continue
    use = ["Speed_KMH"] + (["Speed_MPH"] if "Speed_MPH" in cols else [])
    p = pd.read_parquet(f, columns=use)
    k = pd.to_numeric(p["Speed_KMH"], errors="coerce")
    r = {"file": f.stem, "kmh_pos": int((k > 0).sum())}
    if "Speed_MPH" in p:
        m = pd.to_numeric(p["Speed_MPH"], errors="coerce")
        b = (k > 0) & (m > 0)
        ratio = (k[b] / m[b])
        r.update(both=int(b.sum()), ratio_median=round(float(ratio.median()), 4) if b.any() else None,
                 ratio_off=int(((ratio - 1.609).abs() > 0.03).sum()) if b.any() else None,
                 mph_only=int(((m > 0) & ~(k > 0)).sum()))
    rows.append(r)
print(pd.DataFrame(rows).to_string(index=False))

P = pd.read_parquet(ROOT / "data/studies/serve_speed_tabpfn/speed_panel.parquet")
u = P[P["use"]]
print("\n=== obs (match day used by the filter) minus tournament start, by source (days)")
d = (u["obs"] - u["tdate"])
print(u.assign(d=d).groupby("source")["d"].describe().round(2).to_string())
print("share obs == tdate by source:", u.assign(z=d.eq(0)).groupby("source")["z"].mean().round(3).to_dict())
print("share with an exact clock (timing 'exact'):", u.groupby("source")["exact"].mean().round(3).to_dict())

print("\n=== matches whose two sides carry the identical value and n")
ab = u.pivot_table(index="match_id", columns="side", values="y_raw", aggfunc="first").dropna()
abn = u.pivot_table(index="match_id", columns="side", values="n", aggfunc="first").reindex(ab.index)
same = ab[(ab["A"] == ab["B"]) & (abn["A"] == abn["B"])].index
print(u[u["match_id"].isin(same)][["match_id", "side", "source", "y_raw", "n", "spd2_raw", "spd_max"]].to_string(index=False))
