"""Diagnostic I1: where does the current best model's edge over the closing price live?

Splits the stored out-of-sample gain of the model over the recalibrated closing price by the state each player brings
from their previous match: first match at the event or a later round, rest days, whether the previous match went the
distance, its length, and by round, level and tour. If the edge concentrates where the previous match matters (later
rounds, short rest, a long or deciding previous match), state features carried over from point-by-point data are the
better bet; if it is uniform, traits are.

Holdout discipline: 2025-2026 stays closed (the concurrent feature_interactions study's rule, adopted here). Only the
2022-2024 seasons are read. Matches in a player's debut season are left out, as in the scored comparisons elsewhere.

Forecasts: data/studies/surface_rating_race/predictions.parquet (local TabPFN-3.5, three seeds, recalibrated per tour
with slopes refitted each season): `p_elo_off` (the arm the owner adopted on 6 Oct 2026, without the per-surface IOS
profile) and `p_base` (the 54-input predecessor), against `p_market` (the recalibrated closing price).
Previous matches: Stage 0 (any level, qualifying included) in the study order; days from the match timeline's
best-estimate match day (`obs` in data/studies/match_timing/timing.parquet; `start` is the tournament start day).

Units: milli-log-loss per match; positive = the model is better than the recalibrated close; 95% intervals over
four-week blocks; an interval spanning 0 is a tie.

    ./python.sh src/eda/point_sequence/diag_edge_location.py

Writes data/studies/point_sequence/diag_edge_location.csv and .json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as PD  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = ROOT / "data" / "studies" / "point_sequence"
PRED = ROOT / "data" / "studies" / "surface_rating_race" / "predictions.parquet"
TIMING = ROOT / "data" / "studies" / "match_timing" / "timing.parquet"
SEASONS = (2022, 2024)
MODELS = ("elo_off", "base")


def previous_matches(ids: pd.Index) -> pd.DataFrame:
    """For every (match_id, player) of the given matches: the player's previous Stage 0 match in the study order and
    what it was like."""
    mp = PD.load_match_players(["match_id", "player_id", "won", "sets_won_n", "sets_won_d", "games_won_n",
                                "games_won_d"],
                               match_columns=["tournament_id", "qualifying", "best_of", "minutes", "status", "round"])
    mp = mp.reset_index(drop=True)
    # `obs` is the timeline's best-estimate match day (clipped to [es, lf]); `start` is the tournament's start day and
    # must not be used for gaps between matches (it is 0 for every pair of matches at one event)
    tm = pd.read_parquet(TIMING, columns=["match_id", "obs"])
    mp = mp.merge(tm, on="match_id", how="left", validate="many_to_one")
    mp = mp.sort_values(["player_id", "order"], kind="mergesort").reset_index(drop=True)
    same = mp["player_id"].eq(mp["player_id"].shift())
    prev = mp.shift()
    out = pd.DataFrame({
        "match_id": mp["match_id"], "player_id": mp["player_id"], "has_prev": same,
        "prev_same_event": same & mp["tournament_id"].eq(prev["tournament_id"]),
        "rest_days": np.where(same, mp["obs"] - prev["obs"], np.nan),
        "prev_sets": np.where(same, prev["sets_won_d"], np.nan),
        "prev_best_of": np.where(same, prev["best_of"], np.nan),
        "prev_minutes": np.where(same, prev["minutes"], np.nan),
        "prev_won": np.where(same, prev["won"].astype("float64"), np.nan),
        "prev_status": np.where(same, prev["status"].astype(object), None),
    })
    known = out["prev_sets"].notna() & out["prev_best_of"].notna()
    out["prev_decider"] = np.where(known, (out["prev_sets"] >= out["prev_best_of"]).astype("float64"), np.nan)
    return out[out["match_id"].isin(ids)]


def match_states(pred: pd.DataFrame) -> pd.DataFrame:
    prev = previous_matches(pd.Index(pred["match_id"]))
    m = PD.load_matches(["match_id", "player_a_id", "player_b_id", "round", "level", "best_of"])
    f = pred.merge(m, on="match_id", how="left", validate="one_to_one")
    for side in ("a", "b"):
        p = prev.rename(columns={c: f"{c}_{side}" for c in prev.columns if c not in ("match_id",)})
        f = f.merge(p, left_on=["match_id", f"player_{side}_id"], right_on=["match_id", f"player_id_{side}"],
                    how="left", validate="one_to_one")
    later = f["prev_same_event_a"].fillna(False).astype(bool).astype(int) + \
        f["prev_same_event_b"].fillna(False).astype(bool).astype(int)
    f["later_rounds"] = later.map({0: "both first at event", 1: "one later round", 2: "both later round"})
    rest = np.fmin(f["rest_days_a"], f["rest_days_b"])
    f["min_rest"] = pd.cut(rest, [-np.inf, 1, 3, 7, np.inf], labels=["<=1 day", "2-3 days", "4-7 days", ">7 days"])
    dec = f[["prev_decider_a", "prev_decider_b"]].astype("float64")
    f["prev_decider_any"] = np.where(dec.isna().all(axis=1), "unknown",
                                     np.where(dec.fillna(0).max(axis=1) > 0, "a deciding set", "no deciding set"))
    mins = np.fmax(f["prev_minutes_a"], f["prev_minutes_b"])
    f["prev_minutes_max"] = pd.cut(mins, [-np.inf, 90, 150, np.inf], labels=["<=90", "91-150", ">150"])
    f["round_group"] = np.where(f["round"].isin(["R128", "R64", "R32", "RR"]), "early rounds (R128-R32, RR)",
                                "R16 and later")
    return f


def subgroup_table(f: pd.DataFrame) -> pd.DataFrame:
    rows = []
    y = f["a_won"].astype(int).to_numpy()
    for model in MODELS:
        ll_mkt = T.ll(f["p_market"].to_numpy(), y)
        ll_mod = T.ll(f[f"p_{model}"].to_numpy(), y)
        dates = f["tournament_date"].to_numpy()
        for by in ("all", "tour", "later_rounds", "min_rest", "prev_decider_any", "prev_minutes_max", "round_group",
                   "level"):
            keys = pd.Series("all", index=f.index) if by == "all" else f[by].astype(object).fillna("unknown")
            for tour in ("both", "atp", "wta"):
                tmask = np.ones(len(f), bool) if tour == "both" else (f["tour"] == tour).to_numpy()
                for k in sorted(keys[tmask].unique(), key=str):
                    mask = tmask & (keys == k).to_numpy()
                    if mask.sum() < 150:
                        continue
                    c = T.compare(ll_mkt[mask], ll_mod[mask], dates[mask])
                    rows.append({"model": model, "split": by, "group": str(k), "tour": tour, "matches": c["n"],
                                 "gain": c["gain"], "lo": c["lo"], "hi": c["hi"],
                                 "verdict": "model better" if c["lo"] > 0 else ("close better" if c["hi"] < 0
                                                                                else "tie")})
    return pd.DataFrame(rows)


def main() -> int:
    pred = pd.read_parquet(PRED, columns=["match_id", "tour", "season", "a_won", "tournament_date", "debut_season",
                                          "p_market"] + [f"p_{m}" for m in MODELS])
    pred = pred[pred["season"].between(*SEASONS) & ~pred["debut_season"].astype(bool)].reset_index(drop=True)
    f = match_states(pred)
    R = subgroup_table(f)
    OUT.mkdir(parents=True, exist_ok=True)
    R.to_csv(OUT / "diag_edge_location.csv", index=False)
    meta = {"key": "milli-log-loss per match; positive = the model is better than the recalibrated close; 95% "
                   "intervals over four-week blocks; spanning 0 = tie",
            "seasons": list(SEASONS), "matches": int(len(f)),
            "state_coverage": {c: float(f[c].notna().mean()) for c in ("rest_days_a", "prev_sets_a", "prev_minutes_a")}}
    (OUT / "diag_edge_location.json").write_text(json.dumps(meta, indent=1))
    with pd.option_context("display.width", 220, "display.max_rows", 400):
        print(R[R["model"] == "elo_off"].round(2).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
