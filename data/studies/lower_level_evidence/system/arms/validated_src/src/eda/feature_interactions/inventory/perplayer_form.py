"""Can each player's own two-week profile value be rebuilt from stored data? (feature-interactions data map, round 0)

The model's form_<s>, formdef_<s> and adjperf_tpw_2w inputs are stored only as A - B differences. Stage B
(src/eda/ufc_ideas/stageB_adjperf.py) computes each player's value in Ctx.pool_values (val_a, val_b) and returns their
difference. Its per-match z's are stored per player-match row in data/studies/ufc_ideas/stageB_adj.parquet. This script
redoes step 3 from those z's (each player's earlier box-score matches under Stage 0's time rule, weight 2^(-age/h3) with
age in days from tournament dates, h3 = 2 weeks, val = sum w z / (sum w + K3), tau = 0 for every chosen constant; exists
when the player has any earlier z) and checks that val_A - val_B reproduces the model frame's inputs.

Seasons 2013-2024 only. Stage 0 from the pre-rebuild copy (the version Stage B read). Read-only on shared data.
Writes data/studies/feature_interactions/inventory/perplayer_form_check.json and, for the analysts,
data/studies/feature_interactions/inventory/perplayer_form_2013_2024.parquet (match_id, then <input>_a and <input>_b for
the 17 inputs, on the model population of 2013-2024).
Run: ./python.sh src/eda/feature_interactions/inventory/perplayer_form.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as PC  # noqa: E402  (asof_sums: the time rule; read-only use)

S = ROOT / "data" / "studies"
OUT = S / "feature_interactions" / "inventory"
OLD = S / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
MODEL = S / "surface_rating_race" / "model" / "model_frame.parquet"
REF_DAY = int(np.datetime64("2018-01-01", "D").astype("int64"))       # stage3_traits.REF_DAY
INPUTS = {f"form_{s}": f"adjperf_{s}" for s in ("ace", "df", "first_in", "first_won", "second_won", "hold", "bp_saved",
                                                "bp_faced_pg", "brk", "bp_conv", "rpw_first", "rpw_second")}
INPUTS.update({f"formdef_{s}": f"adjdef_{s}" for s in ("ace", "df", "first_in", "bp_faced_pg")})
INPUTS["adjperf_tpw_2w"] = "adjperf_tpw"


def main() -> int:
    used = json.loads((S / "ufc_ideas" / "stageB_adj_summary.json").read_text(encoding="utf-8"))["used"]
    mf = pd.read_parquet(MODEL)
    mf = mf[mf["season"] <= 2024].reset_index(drop=True)
    m0 = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_matches.parquet",
                         columns=["match_id", "tour", "tournament_date", "tournament_id", "round_order",
                                  "player_a_id", "player_b_id"])
    adj = pd.read_parquet(S / "ufc_ideas" / "stageB_adj.parquet",
                          columns=["match_id", "player_id", "tour"] + [f"z_{v}" for v in INPUTS.values()])
    box = adj.merge(m0[["match_id", "tournament_date", "tournament_id", "round_order"]], on="match_id", how="left")
    q = mf[["match_id"]].merge(m0, on="match_id", how="left")
    qa = q.assign(player_id=q["player_a_id"], _side="a")
    qb = q.assign(player_id=q["player_b_id"], _side="b")
    cols = ["match_id", "player_id", "tour", "tournament_date", "tournament_id", "round_order"]
    allr = pd.concat([box.assign(_side="box"), qa[cols + ["_side"]], qb[cols + ["_side"]]], ignore_index=True)
    day = pd.to_datetime(allr["tournament_date"]).to_numpy().astype("datetime64[D]").astype("int64")
    out = {"match_id": mf["match_id"].to_numpy()}
    check = {}
    is_a = (allr["_side"] == "a").to_numpy()
    is_b = (allr["_side"] == "b").to_numpy()
    tour = allr["tour"].to_numpy()
    for name, col in INPUTS.items():
        z = allr[f"z_{col}"].to_numpy(dtype="float64") if f"z_{col}" in allr else np.full(len(allr), np.nan)
        ok = np.isfinite(z) & (allr["_side"] == "box").to_numpy()
        val = np.full(len(allr), np.nan)
        for t in ("atp", "wta"):
            k = used[col][t]
            h3, K3, tau = float(k["h3"]), float(k["K3"]), int(k["tau"])
            if tau != 0:
                raise ValueError(f"{col} {t}: tau {tau} is not handled here")
            f = np.exp2((day - REF_DAY) / (7.0 * h3))
            tmp = allr[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
            sel = tour == t
            tmp["s1"] = np.where(ok & sel, z, 0.0) * f
            tmp["s0"] = np.where(ok & sel, 1.0, 0.0) * f
            tmp["n"] = np.where(ok & sel, 1.0, 0.0)
            sums = PC.asof_sums(tmp, ["s1", "s0", "n"]).to_numpy()
            s1, s0, n = sums[:, 0] / f, sums[:, 1] / f, sums[:, 2]
            v = np.where(n > 0.5, s1 / (s0 + K3), np.nan)
            val = np.where(sel, v, val)
        va, vb = val[is_a], val[is_b]
        out[f"{name}_a"], out[f"{name}_b"] = va, vb
        model = mf[f"in_{name}"].to_numpy(dtype="float64")
        diff = np.where(np.isfinite(va) & np.isfinite(vb), va - vb, np.nan)
        both = np.isfinite(diff) & np.isfinite(model)
        check[name] = {"compared": int(both.sum()),
                       "max_abs_gap": float(np.max(np.abs(diff[both] - model[both]))),
                       "share_within_1e-5": float(np.mean(np.abs(diff[both] - model[both]) < 1e-5)),
                       "corr": float(np.corrcoef(diff[both], model[both])[0, 1]),
                       "missing_pattern_equal": bool(np.array_equal(np.isfinite(diff), np.isfinite(model))),
                       "sd_model": float(np.nanstd(model)),
                       "sd_player_a": float(np.nanstd(va))}
        print(f"{name:22s} {check[name]}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "perplayer_form_check.json").write_text(json.dumps(check, indent=1), encoding="utf-8")
    pd.DataFrame(out).to_parquet(OUT / "perplayer_form_2013_2024.parquet", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
