"""B2-skeptic review of F16: are the "copied speed blocks" copies, or coincidences of integer key statistics? Read-only.

Key statistics are integers (km/h, counts), and a player's values vary little from match to match, so identical values
recur by chance. Two null models, each from 200 permutations (seeded):
  (a) same player, two different matches, identical (y_raw, n, spd2_raw, spd_max): permute spd2_raw, spd_max and n
      independently across the player's own valid key-statistic matches (one record per player-match, ManTennisData
      preferred, as the panel chooses), keeping y_raw; count matching pairs.
  (b) one match, both sides identical (y_raw, n): within each source and year, re-pair side B's (y_raw, n) with
      another match's side A; count matches with identical values.
Writes data/studies/input_data_audit/fixes/B2-skeptic/f16_null.json
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
OUT = ROOT / "data/studies/input_data_audit/fixes/B2-skeptic"
SP = ROOT / "data/studies/serve_speed_tabpfn"


def pairs_identical(df: pd.DataFrame, cols: list[str]) -> int:
    g = df.groupby(["player_id"] + cols).match_id.nunique()
    return int((g * (g - 1) // 2).sum())


def main() -> None:
    rng = np.random.default_rng(20261008)
    pan = pd.read_parquet(SP / "speed_panel.parquet")
    u = pan[pan["use"] & pan["kind"].eq("keystat")][["match_id", "side", "player_id", "source", "year", "y_raw", "n",
                                                      "spd2_raw", "spd_max"]].dropna()
    res = {"keystat_use_rows": int(len(u))}
    k4 = ["y_raw", "n", "spd2_raw", "spd_max"]
    k3 = ["y_raw", "spd2_raw", "spd_max"]
    res["a_observed_pairs_4"] = pairs_identical(u, k4)
    res["a_observed_pairs_3"] = pairs_identical(u, k3)
    sims4, sims3 = [], []
    for _ in range(200):
        s = u.copy()
        for c in ("spd2_raw", "spd_max", "n"):
            s[c] = s.groupby("player_id")[c].transform(lambda v: v.sample(frac=1.0, random_state=int(rng.integers(1e9))).to_numpy())
        sims4.append(pairs_identical(s, k4))
        sims3.append(pairs_identical(s, k3))
    res["a_null_pairs_4_mean"] = float(np.mean(sims4))
    res["a_null_pairs_4_p95"] = float(np.quantile(sims4, 0.95))
    res["a_null_pairs_3_mean"] = float(np.mean(sims3))
    res["a_null_pairs_3_p95"] = float(np.quantile(sims3, 0.95))
    # (b) both sides identical (y_raw, n), all chosen rows (any kind)
    v = pan[pan["use"]][["match_id", "side", "source", "year", "y_raw", "n"]].dropna()
    w = v.pivot_table(index=["match_id", "source", "year"], columns="side", values=["y_raw", "n"], aggfunc="first").dropna()
    w.columns = [f"{a}_{b}" for a, b in w.columns]
    w = w.reset_index()
    same = (w["y_raw_A"] == w["y_raw_B"]) & (w["n_A"] == w["n_B"])
    res["b_matches_both_sides_chosen"] = int(len(w))
    res["b_observed_identical"] = int(same.sum())
    res["b_observed_identical_by_source"] = w[same].groupby("source").size().to_dict()
    res["b_observed_equal_y"] = int((w["y_raw_A"] == w["y_raw_B"]).sum())
    res["b_observed_equal_n"] = int((w["n_A"] == w["n_B"]).sum())
    sims = []
    for _ in range(200):
        x = w.copy()
        x[["y_raw_B", "n_B"]] = x.groupby(["source", "year"])[["y_raw_B", "n_B"]].transform(
            lambda c: c.sample(frac=1.0, random_state=int(rng.integers(1e9))).to_numpy())
        sims.append(int(((x["y_raw_A"] == x["y_raw_B"]) & (x["n_A"] == x["n_B"])).sum()))
    res["b_null_identical_mean"] = float(np.mean(sims))
    res["b_null_identical_p95"] = float(np.quantile(sims, 0.95))
    # independence estimate: P(equal y) * P(equal n) * matches, by source
    est = {}
    for src, g in w.groupby("source"):
        est[src] = round(float((g["y_raw_A"] == g["y_raw_B"]).mean() * (g["n_A"] == g["n_B"]).mean() * len(g)), 2)
    res["b_independence_estimate_by_source"] = est
    (OUT / "f16_null.json").write_text(json.dumps(res, indent=1))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
