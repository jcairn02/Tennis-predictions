"""Audit step 16: where each counterfactual moves spd_L (men's 2024-26 frame matches): by event and round, and whether the
A - B difference cancels (both sides moved alike) or not. Reads the scratch outputs of a14 only."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path.cwd()
SCR = Path.cwd() / "data" / "studies" / "input_data_audit" / "speed"   # run from the repo root
pd.set_option("display.width", 260)
pd.set_option("display.max_rows", 300)
pd.set_option("display.max_columns", 30)
COEF = json.loads((ROOT / "data/studies/serve_speed_tabpfn/adaptive/coefficients.json").read_text())
B_L = {int(k): v["b_shrunk"] for k, v in COEF["L_weekly"].items()}
SD_L = 1.9496051535048338
base = pd.read_parquet(SCR / "prop_base.parquet")
info = pd.read_parquet(SCR / "prop_info.parquet")
info["event"] = info["tournament_name"].astype(str) + " " + info["season"].astype(str)
info["date"] = pd.to_datetime(info["es"], unit="D").dt.date


def breakdown(name: str, scen: str, top: int = 25):
    cf = pd.read_parquet(SCR / f"prop_{name}.parquet")
    d = pd.DataFrame({"dA": base[f"fA_{scen}"] - cf[f"fA_{scen}"], "dB": base[f"fB_{scen}"] - cf[f"fB_{scen}"],
                      "dL": base[f"spd_L_{scen}"] - cf[f"spd_L_{scen}"]}, index=base.index).join(info)
    d["b"] = d["season"].map(B_L)
    d["dpp50"] = 25.0 * d["b"] * d["dL"]
    mv = d[(d["dA"].abs() > 0.02) | (d["dB"].abs() > 0.02)]
    # cancellation: the share of the two sides' movement that cancels in A - B
    both = mv[(mv["dA"].abs() > 0.02) & (mv["dB"].abs() > 0.02)]
    canc = 1 - (mv["dA"] - mv["dB"]).abs().sum() / (mv["dA"].abs() + mv["dB"].abs()).sum() if len(mv) else np.nan
    print(f"\n===== {name}, scenario {scen}: sides moved (> 0.02 km/h) in {len(mv)} matches; both sides moved in "
          f"{len(both)}; share of movement cancelled in A - B: {canc:.2f}")
    g = mv.groupby(["event"]).agg(matches=("dL", "size"), both_sides=("dA", lambda s: int(((s.abs() > 0.02)
                                                                                         & (mv.loc[s.index, 'dB'].abs() > 0.02)).sum())),
                                  mean_abs_fA=("dA", lambda s: s.abs().mean()), mean_abs_dL=("dL", lambda s: s.abs().mean()),
                                  max_abs_dL=("dL", lambda s: s.abs().max()), first=("date", "min"), last=("date", "max"))
    print(g.sort_values("first").head(top).round(3).to_string())
    big = d.loc[d["dL"].abs().sort_values(ascending=False).index[:12]]
    print(big[["event", "round", "date", "dA", "dB", "dL", "dpp50"]].round(3).to_string())
    return d


for name in ("S1_ao24_const", "S2_ao24_court"):
    d = breakdown(name, "A")
    ao = d[d["event"].str.startswith("Australian Open 2024")]
    print("AO 2024 by round (scenario A): mean |dA|, |dB| km/h, mean |dL| units")
    print(ao.groupby("round").agg(n=("dL", "size"), dA=("dA", lambda s: s.abs().mean()), dB=("dB", lambda s: s.abs().mean()),
                                  dAB_kmh=("dL", lambda s: (s.abs() * SD_L).mean()), dL=("dL", lambda s: s.abs().mean()),
                                  max_dL=("dL", lambda s: s.abs().max())).round(3).to_string())
    breakdown(name, "B", top=12)
for name in ("S3_rg_stale", "S4_ao25_courts", "S5_w_break"):
    breakdown(name, "A", top=15)
    breakdown(name, "B", top=10)
for name in ("S6_handoff", "S7_mantd", "S8_all"):
    d = breakdown(name, "B", top=10)
    print("by season (scenario B): matches with |dL| >= 0.25 / 0.5 / 1")
    print(d.groupby("season")["dL"].agg(lambda s: f"{int((s.abs() >= 0.25).sum())} / {int((s.abs() >= 0.5).sum())} / "
                                             f"{int((s.abs() >= 1).sum())}").to_string())
