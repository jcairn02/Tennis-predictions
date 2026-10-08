"""Can each player's own sets_14d (and age) be rebuilt from Stage 0? (feature-interactions data map, round 0)

The model's sets_14d is stored only as A - B. Stage 4 (src/eda/predictability_diagnostic/stage4_features.py, state():
"activity and load"; the same definition in feature_alpha_audit/repair_features.py: context_features) computes each
player's load per row: log(1 + sets played in matches of events whose tournament date is within the 14 days before this
match's event, plus the same event's earlier rounds), missing when a played match in that window has no set total.
This script redoes it on the pre-rebuild Stage 0 (every level, every match, the Stage 0 version Stage 4 read) and checks
that load_A - load_B reproduces the model's input; age_A - age_B is checked against Stage 0's per-player age.

Seasons 2013-2024 only for the comparison. Read-only on shared data. Writes
data/studies/feature_interactions/inventory/perplayer_load_check.json and perplayer_load_2013_2024.parquet
(match_id, sets_14d_a, sets_14d_b, age_a, age_b, on the model population of 2013-2024).
Run: ./python.sh src/eda/feature_interactions/inventory/perplayer_load.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as PC  # noqa: E402  (asof_sums; read-only use)
from src.eda.predictability_diagnostic import stage3_traits as T3  # noqa: E402  (sums_before; read-only use)

S = ROOT / "data" / "studies"
OUT = S / "feature_interactions" / "inventory"
OLD = S / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
MODEL = S / "surface_rating_race" / "model" / "model_frame.parquet"
WINDOW = 14


def gap(x, y) -> dict:
    both = np.isfinite(x) & np.isfinite(y)
    return {"compared": int(both.sum()), "max_abs_gap": float(np.max(np.abs(x[both] - y[both]))),
            "share_within_1e-6": float(np.mean(np.abs(x[both] - y[both]) < 1e-6)),
            "missing_pattern_equal": bool(np.array_equal(np.isfinite(x), np.isfinite(y)))}


def main() -> int:
    mf = pd.read_parquet(MODEL, columns=["match_id", "season", "in_sets_14d", "in_age"])
    mf = mf[mf["season"] <= 2024].reset_index(drop=True)
    m = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_matches.parquet",
                        columns=["match_id", "tournament_date", "tournament_id", "round_order", "status"])
    p = pd.read_parquet(OLD / "predictability_diagnostic" / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "side", "sets_won_d", "age"])
    r = p.merge(m, on="match_id", how="left")
    played = r["status"].isin(["completed", "retired"]).to_numpy()
    sets = r["sets_won_d"].to_numpy(dtype="float64")
    V = np.column_stack([(played & ~np.isfinite(sets)).astype(float), np.where(played & np.isfinite(sets), sets, 0.0)])
    tmp = r[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    tmp["v0"], tmp["v1"] = V[:, 0], V[:, 1]
    car = PC.asof_sums(tmp, ["v0", "v1"]).to_numpy()
    day = pd.to_datetime(r["tournament_date"]).to_numpy().astype("datetime64[D]").astype("int64")
    pcode = pd.factorize(r["player_id"])[0]
    bef = T3.sums_before(pcode, day, V, pcode, day - WINDOW)
    win = car - bef
    r["sets_14d"] = np.where(win[:, 0] < 0.5, np.log1p(np.maximum(win[:, 1], 0.0)), np.nan)
    age = r["age"].to_numpy(dtype="float64")
    r["age_c"] = np.where((age >= 14) & (age <= 50), age - 25.0, np.nan)          # Stage 4's AGE_RANGE and centre
    A = mf[["match_id"]].merge(r[r["side"] == "A"][["match_id", "sets_14d", "age_c"]], on="match_id", how="left")
    B = mf[["match_id"]].merge(r[r["side"] == "B"][["match_id", "sets_14d", "age_c"]], on="match_id", how="left")
    check = {"sets_14d": gap(A["sets_14d"].to_numpy() - B["sets_14d"].to_numpy(), mf["in_sets_14d"].to_numpy(dtype=float)),
             "age": gap(A["age_c"].to_numpy() - B["age_c"].to_numpy(), mf["in_age"].to_numpy(dtype=float))}
    for k, v in check.items():
        print(k, v)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "perplayer_load_check.json").write_text(json.dumps(check, indent=1), encoding="utf-8")
    pd.DataFrame({"match_id": mf["match_id"], "sets_14d_a": A["sets_14d"], "sets_14d_b": B["sets_14d"],
                  "age_a": A["age_c"] + 25.0, "age_b": B["age_c"] + 25.0}) \
        .to_parquet(OUT / "perplayer_load_2013_2024.parquet", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
