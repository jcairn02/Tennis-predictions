"""Design R1 (speed-data engineer), step 6: plausibility and noise of player-match first-serve speeds. Values only; no
result is read.

    * the distribution of harmonised player-match means by tour and source, and the low tail (men < 120, women < 100)
    * timed first serves per player-match (n1) and the half-timed gate: what fails it, by source
    * outliers against the player's OWN earlier matches only (a leak-free cleaning rule): |y - median of his previous
      up to 10 timed matches| in km/h, and in units of the robust spread
    * the second serve, the maximum and the first-serve fault speed: availability by source and year

Run: ./python.sh src/eda/serve_speed_tabpfn/design/engineer_noise.py
Writes data/studies/serve_speed_tabpfn/design/engineer_noise.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

PANEL0 = EC.OUT / "engineer_panel0.parquet"


def own_history_outliers(p: pd.DataFrame, k: int = 10) -> pd.DataFrame:
    """For each player-match, the median of the same player's previous (own order) up to k timed matches."""
    p = p.sort_values(["tour", "player_id", "tournament_date", "round_order"]).copy()
    med = np.full(len(p), np.nan)
    cnt = np.zeros(len(p), int)
    y = p["spd1"].to_numpy()
    tdate = p["tournament_date"].to_numpy()
    tid = p["tournament_id"].to_numpy()
    ro = p["round_order"].to_numpy()
    keys = (p["tour"] + "|" + p["player_id"].astype(str)).to_numpy()
    starts = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1]])
    ends = np.r_[starts[1:], len(p)]
    for s, e in zip(starts, ends):
        for i in range(s, e):
            j = np.arange(s, i)
            j = j[(tdate[j] < tdate[i]) | ((tid[j] == tid[i]) & (ro[j] < ro[i]))]
            if len(j):
                h = y[j[-k:]]
                med[i] = np.median(h)
                cnt[i] = len(h)
    p["own_med"], p["own_k"] = med, cnt
    p["dev"] = p["spd1"] - p["own_med"]
    return p


def main() -> None:
    p = pd.read_parquet(PANEL0)
    res = {"reads_results": False}
    res["distribution"] = {f"{t}|{s}": EC.q(g["spd1"], (0.001, 0.01, 0.05, 0.5, 0.95, 0.99, 0.999))
                           for (t, s), g in p.groupby(["tour", "source"])}
    res["low_tail"] = {
        "men_lt_120": int(((p["tour"] == "atp") & (p["spd1"] < 120)).sum()),
        "men_120_140": int(((p["tour"] == "atp") & p["spd1"].between(120, 140)).sum()),
        "women_lt_100": int(((p["tour"] == "wta") & (p["spd1"] < 100)).sum()),
        "women_100_120": int(((p["tour"] == "wta") & p["spd1"].between(100, 120)).sum()),
        "men_lt_120_by_source": p[(p["tour"] == "atp") & (p["spd1"] < 120)]["source"].value_counts().to_dict()}
    res["n1"] = {f"{t}|{s}": EC.q(g["n1"], (0.01, 0.05, 0.25, 0.5)) for (t, s), g in p.groupby(["tour", "source"])}
    res["n1_lt_10"] = int((p["n1"] < 10).sum())
    res["n1_lt_20"] = int((p["n1"] < 20).sum())
    # the half-timed gate on point sources (records, before the choice)
    r = pd.read_parquet(EC.RECORDS)
    pts = r[r["basis"].eq("point_mean") & r["linked"] & (r["n1"] > 0)]
    res["gate"] = (pts.groupby("source").agg(timed_any=("n1", "size"), pass_half=("gate_half", "sum"),
                                             share_ge_90=("timed_share", lambda x: float((x >= 0.9).mean())))
                   .round(3).reset_index().to_dict(orient="records"))
    # own-history outliers
    o = own_history_outliers(p[~p["implausible"]])
    oo = o[o["own_k"] >= 5]
    res["own_history_dev_kmh"] = {"n": int(len(oo)), "q": EC.q(oo["dev"], (0.001, 0.01, 0.05, 0.5, 0.95, 0.99, 0.999)),
                                  "abs_gt_10": int((oo["dev"].abs() > 10).sum()),
                                  "abs_gt_15": int((oo["dev"].abs() > 15).sum()),
                                  "abs_gt_20": int((oo["dev"].abs() > 20).sum())}
    big = oo[oo["dev"].abs() > 15]
    res["own_history_gt15_by_source"] = big["source"].value_counts().to_dict()
    res["own_history_gt15_share_by_source"] = (big["source"].value_counts() / oo["source"].value_counts()).dropna() \
        .round(4).to_dict()
    # other speed columns
    res["other_columns"] = (p.groupby(["tour", "source"]).agg(rows=("spd1", "size"), spd2=("spd2", lambda x: int(x.notna().sum())),
                                                              spd_max=("spd_max", lambda x: int(x.notna().sum())),
                                                              fault1=("fault1", lambda x: int(x.notna().sum())))
                            .reset_index().to_dict(orient="records"))
    # second serve and max against first serve (sanity)
    res["spd2_minus_spd1"] = EC.q(p["spd2"] - p["spd1"], (0.001, 0.01, 0.5, 0.99, 0.999))
    res["max_minus_spd1"] = EC.q(p["spd_max"] - p["spd1"], (0.001, 0.01, 0.5, 0.99, 0.999))
    res["max_lt_spd1"] = int((p["spd_max"] < p["spd1"] - 1).sum())
    res["spd2_gt_spd1_plus_10"] = int((p["spd2"] > p["spd1"] + 10).sum())
    (EC.OUT / "engineer_noise.json").write_text(json.dumps(res, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(res, indent=1, default=str)[:9000])


if __name__ == "__main__":
    main()
