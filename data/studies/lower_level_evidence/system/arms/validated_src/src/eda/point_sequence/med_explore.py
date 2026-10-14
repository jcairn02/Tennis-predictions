"""E1 mechanism gate, step 3 (EXPLORATORY, not registered): is the TREATED -> M1 signal a state or a trait proxy?

Run:  ./python.sh src/eda/point_sequence/med_explore.py

Adds, to the registered M1 model for TREATED, the player's own history before t (her own earlier matches in Stage 0
order, so safe by construction): retirements and walkovers she gave in the 365 days before t, matches played in
those days, and TREATED logged matches in those days. If the risk ratio holds, the event in t carries information
beyond a retirement-prone or often-treated player. Also: the permutation tails of the registered placebo.
Writes med_explore.json. Labelled exploratory everywhere: no pass/fail rests on it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import common as C  # noqa: E402
from src.eda.point_sequence import med_build as B  # noqa: E402
from src.eda.point_sequence import med_estimate as E  # noqa: E402
from src.eda.point_sequence import med_stats as S  # noqa: E402
from src.eda.predictability_diagnostic import common as S0  # noqa: E402

OUT = C.OUT


def history() -> pd.DataFrame:
    """Per (player, match) counts over her earlier matches in the previous 365 days (2018 on, holdout masked)."""
    m = S0.load_matches(["match_id", "tour", "year", "status"])
    m = m[m["tour"].eq("wta") & m["year"].between(2018, 2024)]
    t = pd.read_parquet(B.TIMING, columns=["match_id", "obs"])
    m = m.merge(t, on="match_id")
    mp = pd.read_parquet(S0.MATCH_PLAYERS, columns=["match_id", "player_id", "won"])
    r = mp.merge(m, on="match_id").sort_values(["player_id", "order"], kind="mergesort").reset_index(drop=True)
    r = r[r["obs"] < B.D_HOLD]
    r["played"] = r["status"].isin(["completed", "retired", "other"]).astype(float)
    r["m1ev"] = (r["status"].isin(["retired", "walkover"]) & ~r["won"].astype(bool)).astype(float)
    pairs = pd.read_parquet(OUT / "med_pairs.parquet", columns=["player_id", "match_id", "treated", "logged"])
    r = r.merge(pairs, on=["player_id", "match_id"], how="left")
    r["tr"] = r["treated"].astype("boolean").fillna(False).astype(float)
    out = []
    for pid, g in r.groupby("player_id", sort=False):
        d = g["obs"].to_numpy(float)
        cs = {c: np.r_[0.0, np.cumsum(g[c].to_numpy(float))] for c in ("played", "m1ev", "tr")}
        lo = np.searchsorted(d, d - 365.0, side="left")
        idx = np.arange(len(g))                    # strictly earlier rows (Stage 0 order) within 365 days
        rec = {"player_id": pid, "match_id": g["match_id"].to_numpy()}
        for c in ("played", "m1ev", "tr"):
            rec[f"h_{c}"] = cs[c][idx] - cs[c][np.minimum(lo, idx)]
        out.append(pd.DataFrame(rec))
    return pd.concat(out, ignore_index=True)


def main() -> None:
    p = E.load()
    h = history()
    d, _ = E.add_ps(E.contrast_frame(p, "treated"), "treated")
    d = d.merge(h, on=["player_id", "match_id"], how="left")
    for c in ("h_played", "h_m1ev", "h_tr"):
        d[c] = d[c].fillna(0.0)
    d["h_log_played"] = np.log1p(d["h_played"])
    d["h_log_m1ev"] = np.log1p(d["h_m1ev"])
    d["h_any_tr"] = (d["h_tr"] > 0).astype(float)
    res = {"label": "EXPLORATORY, not registered", "rows": []}
    for window in ("discovery", "replication"):
        g = d[(d["window"] == window) & d["m1"].notna()]
        for name, num in (("registered", []),
                          ("+ own retirement/walkover history", ["h_log_m1ev", "h_log_played"]),
                          ("+ history + earlier TREATED", ["h_log_m1ev", "h_log_played", "h_any_tr"])):
            cat = {"min_dec": list(range(10)), "days_cat": E.DAYS_LABELS, "surface_n": E.SURF,
                   "ps_q": list(range(5))}
            X, names = S.design(g, ["age_c", "age_c2", "age_missing", "won_t"] + num, cat, first=["treated"])
            fit = S.poisson_fit(g["m1"].to_numpy(float), X, g["player_id"].to_numpy(object))
            row = {"window": window, "model": name, **S.coef_summary(fit, 1, log_scale=True)}
            for c in num:
                j = names.index(c)
                row[f"rr_{c}"] = float(np.exp(fit["coef"][j]))
            res["rows"].append(row)
        res[f"history_means_{window}"] = g.groupby("treated")[["h_played", "h_m1ev", "h_any_tr"]].mean().to_dict()
    pl = pd.read_csv(OUT / "med_placebo.csv")
    obs = {r["window"]: r for r in res["rows"] if r["model"] == "registered"}
    tails = {}
    for window in ("discovery", "replication"):
        e = pl[(pl["endpoint"] == "M1") & (pl["window"] == window)]["est"].to_numpy()
        o = obs[window]["est"]
        tails[window] = {"perms": int(len(e)), "upper_one_sided_p": float((1 + np.sum(e >= o)) / (1 + len(e))),
                         "two_sided_p": float((1 + np.sum(np.abs(np.log(e)) >= abs(np.log(o)))) / (1 + len(e))),
                         "placebo_max": float(e.max())}
    res["placebo_m1_tails"] = tails
    C.write_json(OUT / "med_explore.json", res)
    with pd.option_context("display.width", 250, "display.max_columns", 20):
        print(pd.DataFrame(res["rows"]).to_string(float_format=lambda v: f"{v:.4g}"))
    print(tails)
    for window in ("discovery", "replication"):
        print(window, res[f"history_means_{window}"])


if __name__ == "__main__":
    main()
