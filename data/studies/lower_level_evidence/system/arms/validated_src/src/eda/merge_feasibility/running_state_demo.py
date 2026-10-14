"""Running-state feature demo on the scan's provisional canonical singles matches.

Question: at tennis scale, can pre-match player features be computed for every player-match row in one
chronological pass, and what would the UFC project's per-row look-back cost instead? Builds the
two-rows-per-match facts table (facts only, no averages), orders it by tournament week then round, and
computes pre-match features that only see earlier matches: career matches and win rate, serve points won
rate, days since the previous match, a time-decayed win rate and Elo. Records timings, Parquet sizes,
ordering checks and a measured extrapolation of the per-row look-back.

Illustration only: the feature list is not a proposal. Writes data/studies/merge_feasibility/running_state_demo.json;
Parquet size probes go to the system temp directory and are deleted.
Run: ./python.sh src/eda/merge_feasibility/running_state_demo.py
"""
from __future__ import annotations

import json
import math
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan as S  # noqa: E402

STATS = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced"]
ROUND_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4, "R128": 10, "R64": 11, "R32": 12, "RR": 12, "R16": 13,
               "QF": 14, "SF": 15, "BR": 16, "F": 17}
HALF_LIFE_DAYS = 180.0


def timed(label, timings, fn, *args):
    t = time.perf_counter()
    out = fn(*args)
    timings[label] = round(time.perf_counter() - t, 2)
    S.log(f"{label}: {timings[label]}s")
    return out


def facts_table(canon):
    """Two rows per match, facts only: who played whom, who won, context, and that player's in-match stats."""
    def side(me, opp, won, prefix):
        d = pd.DataFrame({"match_id": canon["match_id"], "player_id": canon[me], "opponent_id": canon[opp],
                          "won": np.int8(won), "tdate": canon["tdate"], "round_order": canon["round_order"],
                          "tier": canon["tier"], "is_qual": canon["is_qual"]})
        for x in STATS:
            d[x] = pd.to_numeric(canon[f"{prefix}_{x}"], errors="coerce").astype("float32")
        return d
    facts = pd.concat([side("pid_w", "pid_l", 1, "w"), side("pid_l", "pid_w", 0, "l")], ignore_index=True)
    return facts.sort_values(["tdate", "round_order", "match_id"], kind="stable").reset_index(drop=True)


def vectorised_features(facts):
    """Expanding (career-to-date) features with groupby + cumulative sums shifted by one match."""
    g = facts.groupby("player_id", sort=False)
    f = pd.DataFrame({"match_id": facts["match_id"], "player_id": facts["player_id"]})
    f["matches_before"] = g.cumcount().astype("int32")
    f["wins_before"] = (g["won"].cumsum() - facts["won"]).astype("int32")
    f["win_rate_before"] = (f["wins_before"] / f["matches_before"].replace(0, np.nan)).astype("float32")
    served = facts["svpt"].fillna(0)
    won_pts = (facts["1stWon"] + facts["2ndWon"]).fillna(0)
    cum_won = won_pts.groupby(facts["player_id"], sort=False).cumsum() - won_pts
    cum_served = served.groupby(facts["player_id"], sort=False).cumsum() - served
    f["serve_pts_won_rate_before"] = (cum_won / cum_served.replace(0, np.nan)).astype("float32")
    f["days_since_last_match"] = (facts["tdate"] - g["tdate"].shift(1)).dt.days.astype("float32")
    return f


def decayed_win_rate(facts):
    """Exponentially time-decayed win rate, one pass with a per-player running state."""
    lam = math.log(2) / HALF_LIFE_DAYS
    state = {}
    out = np.full(len(facts), np.nan, dtype="float32")
    days = (facts["tdate"] - pd.Timestamp("2000-01-01")).dt.days.to_numpy()
    for i, (p, d, won) in enumerate(zip(facts["player_id"].to_numpy(), days, facts["won"].to_numpy())):
        s = state.get(p)
        if s is not None:
            w_sum, n_sum, last = s
            k = math.exp(-lam * (d - last))
            w_sum, n_sum = w_sum * k, n_sum * k
            out[i] = w_sum / n_sum if n_sum > 0 else np.nan
        else:
            w_sum = n_sum = 0.0
        state[p] = (w_sum + won, n_sum + 1.0, d)
    return out


def elo(canon):
    """Pre-match Elo for winner and loser of every match, updated in chronological order."""
    rating, played = {}, {}
    pre_w = np.empty(len(canon), dtype="float32")
    pre_l = np.empty(len(canon), dtype="float32")
    for i, (w, l) in enumerate(zip(canon["pid_w"].to_numpy(), canon["pid_l"].to_numpy())):
        rw, rl = rating.get(w, 1500.0), rating.get(l, 1500.0)
        pre_w[i], pre_l[i] = rw, rl
        expected = 1.0 / (1.0 + 10 ** ((rl - rw) / 400.0))
        kw = 250.0 / (played.get(w, 0) + 5) ** 0.4
        kl = 250.0 / (played.get(l, 0) + 5) ** 0.4
        rating[w], rating[l] = rw + kw * (1 - expected), rl - kl * (1 - expected)
        played[w], played[l] = played.get(w, 0) + 1, played.get(l, 0) + 1
    return pre_w, pre_l


def lookback_cost(facts, sample=300, seed=7):
    """Time the UFC-style per-row look-back (mask the whole table for this player before this date)."""
    rows = facts.sample(sample, random_state=seed)
    pid, tdate, served = facts["player_id"], facts["tdate"], facts["svpt"]
    t = time.perf_counter()
    for p, d in zip(rows["player_id"], rows["tdate"]):
        mask = (pid == p) & (tdate < d)
        _ = served[mask].mean()
    per_row = (time.perf_counter() - t) / sample
    return per_row


def main():
    S.MATCH_COLS = S.MATCH_COLS + [f"{s}_{x}" for s in ("w", "l") for x in STATS if f"{s}_{x}" not in S.MATCH_COLS]
    timings = {}
    canon = timed("load_and_link_sources", timings, S.build_canonical, {})
    canon["round_order"] = canon["round"].map(ROUND_ORDER).fillna(12).astype("int8")
    canon = canon.sort_values(["tdate", "round_order", "tid"], kind="stable").reset_index(drop=True)
    canon["match_id"] = np.arange(len(canon), dtype="int64")
    facts = timed("build_two_row_facts_table", timings, facts_table, canon)
    feats = timed("career_features_vectorised", timings, vectorised_features, facts)
    feats["decayed_win_rate_before"] = timed("decayed_win_rate_one_pass", timings, decayed_win_rate, facts)
    pre_w, pre_l = timed("elo_one_pass_over_matches", timings, elo, canon)

    same_slot = facts.duplicated(subset=["player_id", "tdate", "round_order"], keep=False)
    slot = facts[same_slot].merge(canon[["match_id", "round", "tid"]], on="match_id")
    rr = slot["round"].eq("RR")
    blank = slot["player_id"].eq("")
    rest = slot[~rr & ~blank]
    tids = rest.groupby(["player_id", "tdate", "round_order"])["tid"].transform("nunique")
    first = feats.groupby("player_id", sort=False).head(1)
    checks = {"player_rows_sharing_week_and_round_with_another_of_their_rows": int(same_slot.sum()),
              "of_which_round_robin": int(rr.sum()), "of_which_missing_player_id": int((~rr & blank).sum()),
              "of_which_same_player_week_round_under_two_tournament_ids": int((tids > 1).sum()),
              "of_which_same_tournament_id": int((tids == 1).sum()),
              "first_appearance_rows_with_nonzero_history": int((first["matches_before"] != 0).sum()),
              "elo_favourite_won_pct": round(100 * float((pre_w > pre_l).mean()), 1)}

    with tempfile.TemporaryDirectory() as tmp:
        sizes = {}
        for name, frame in (("facts_two_rows_per_match", facts), ("pre_match_features", feats)):
            path = Path(tmp) / f"{name}.parquet"
            frame.to_parquet(path, index=False)
            sizes[name] = {"rows": len(frame), "columns": frame.shape[1],
                           "parquet_MB": round(path.stat().st_size / 1e6, 1),
                           "in_memory_MB": round(frame.memory_usage(deep=True).sum() / 1e6, 1)}

    per_row = lookback_cost(facts)
    result = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "canonical_matches": len(canon), "player_match_rows": len(facts),
        "timings_seconds": timings,
        "table_sizes": sizes,
        "ordering_checks": checks,
        "per_row_lookback": {"seconds_per_row_measured_on_300_rows": round(per_row, 4),
                             "extrapolated_hours_per_feature_column": round(per_row * len(facts) / 3600, 1)},
        "note": "Illustrative features only. Tournament-week dates mean same-event matches are ordered by round; "
                "rows sharing a player, week and round are duplicates or round-robin matches needing per-match dates.",
    }
    (S.OUT / "running_state_demo.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
