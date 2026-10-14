"""Audit step 20: S9 - the within-edition court and day cells flagged in a12 (>= 8 rows, |mean residual| >= 2 km/h,
|t| >= 3; men; 2023-2026 editions), corrected by their mean residual, and their reach into spd_L (scenarios A and B), with
the project's functions; plus S10 = S8 (a14) + S9. Read-only on the repo."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 250)
pd.set_option("display.max_rows", 200)
from src.eda.serve_speed_tabpfn import features as F  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import features_latency as FL  # noqa: E402

SD_L = float(json.loads(FL.META.read_text(encoding="utf-8"))["standardisation_sd_km_h"]["B_M1"])
COEF = json.loads((ROOT / "data/studies/serve_speed_tabpfn/adaptive/coefficients.json").read_text())
B_L = {int(k): v["b_shrunk"] for k, v in COEF["L_weekly"].items()}
p0 = FL.load_panel()
rd = FL.release_days(p0)
keys = P.load_frame_keys()
t = F.side_targets(keys)
sel = t["tour"].eq("atp") & t["season"].between(2024, 2026)
A = t[sel & t["side"].eq("A")]
Bs = t[sel & t["side"].eq("B")]
tm = pd.concat([A, Bs], ignore_index=True)
nm = len(A)


def spd_cols(pp, rel_b, box):
    out = {}
    for scen in ("A", "B"):
        S = FL.Scenario("A", pp, None, None) if scen == "A" else FL.Scenario("B", pp, rel_b, box)
        hist = FL.histories_rel(pp, tm, None if scen == "A" else rel_b)
        f = FL.side_values_v(S, tm, dict(FL.MEN, hl=28.0), hist=hist)["f_hat"].to_numpy(float)
        out[f"fA_{scen}"], out[f"fB_{scen}"] = f[:nm], f[nm:]
        out[f"spd_L_{scen}"] = np.clip((f[:nm] - f[nm:]) / SD_L, -4, 4)
    return pd.DataFrame(out, index=A["match_id"].to_numpy())


base = pd.read_parquet(SCR / "prop_base.parquet")
R = pd.read_parquet(SCR / "panel_resid.parquet", columns=["match_id", "side", "tour", "edition", "court", "obs",
                                                           "resid", "ident"])
R["date"] = pd.to_datetime(R["obs"], unit="D").dt.date
cells = pd.read_csv(SCR / "t_within_cells.csv")
fl = cells[(cells["tour"] == "atp") & (cells["rows"] >= 8) & (cells["mean_resid"].abs() >= 2) & (cells["t"].abs() >= 3)
           & (cells["year"] >= 2023) & cells["by"].isin(["court", "date"])]
print(f"flagged men's cells 2023-26: {len(fl)} ({fl['by'].value_counts().to_dict()})")
R["date"] = R["date"].astype(str)
corr = pd.Series(0.0, index=pd.MultiIndex.from_frame(R[["match_id", "side"]]))
for c in fl.itertuples(index=False):
    col = "court" if c.by == "court" else "date"
    m = (R["tour"] == "atp") & (R["edition"] == c.edition) & (R[col].astype(str) == str(c.cell))
    idx = pd.MultiIndex.from_frame(R.loc[m, ["match_id", "side"]])
    corr.loc[idx] = corr.loc[idx] + c.mean_resid
key = pd.MultiIndex.from_frame(p0[["match_id", "side"]])
shift = corr.reindex(key).fillna(0.0).to_numpy()
print(f"panel rows corrected: {int((shift != 0).sum())}; |shift| mean {np.abs(shift[shift != 0]).mean():.2f}")

info = pd.read_parquet(SCR / "prop_info.parquet").reindex(base.index)
bL = info["season"].map(B_L).to_numpy()
rows = []
pp = p0.copy()
pp["y"] = pp["y"] - shift
cf9 = spd_cols(pp, rd["B"].to_numpy(np.int64), rd["box"].to_numpy(np.int64))
cf9.to_parquet(SCR / "prop_S9_cells.parquet")
for name, cf in (("S9_cells", cf9),):
    for scen in ("A", "B"):
        d = (base[f"spd_L_{scen}"] - cf[f"spd_L_{scen}"]).to_numpy()
        ad = np.abs(d)
        rows.append({"scenario": name, "avail": scen, "moved_ge_0.05": int((ad >= .05).sum()),
                     "moved_ge_0.25": int((ad >= .25).sum()), "moved_ge_0.5": int((ad >= .5).sum()),
                     "moved_ge_1": int((ad >= 1).sum()), "max_abs_units": float(ad.max()),
                     "max_abs_pp_at_50pc": float(25 * np.max(np.abs(bL * d)))})
print(pd.DataFrame(rows).round(3).to_string(index=False))
