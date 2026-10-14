"""A1-T / I2 step 1: the per player-match statistics on the real sequences and on iid replays of every match.

Pre-registration: data/studies/point_sequence/trait_prereg.md. Run:  ./python.sh src/eda/point_sequence/trait_build.py

1. The population (trait_common.population), its points, and a check that the sequence's winner is Stage 0's.
2. The statistics on the real points (trait_common.point_stats).
3. De-noised day-rate priors fitted on seasons <= 2018 only (trait_common.fit_priors), then, per variant (V1, V05, V15,
   VPS) and replay (3 each): true day rates drawn per player-match, every match replayed point by point under its own
   format and first server, and the same statistics computed on the replayed points.

Writes (data/studies/point_sequence/):
    trait_population.parquet            one row per analysed match (mcode, ids, players, format, first server, obs)
    trait_player_matches.parquet        per world (real, V1_0..V1_2) x player-match: X_/D_ of S1-S5, S4r, P0, totals
    trait_player_matches_variants.parquet   the same for V05_*, V15_*, VPS_*
    trait_matches.parquet               per world x match: points, A's points, tie-breaks, sets, A won, true rates
    trait_build.json                    population steps, checks, priors, timings
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import trait_common as TC  # noqa: E402

STAT_COLS = [f"{p}_{s}" for s in TC.STATS for p in ("X", "D")]
TOTALS = ["svc_games", "holds", "ret_games", "breaks", "svpt", "svpt_won", "set1_n", "set1_w", "late_n", "late_w"]


def subset_points(P: dict, keep_codes: np.ndarray, n_old: int) -> dict:
    """Points of the kept matches, with match codes renumbered 0..k-1 in the kept order."""
    new = np.full(n_old, -1, np.int64)
    new[keep_codes] = np.arange(len(keep_codes))
    sel = new[P["m"]] >= 0
    out = {k: v[sel] for k, v in P.items()}
    out["m"] = new[out["m"]]
    order = np.argsort(out["m"], kind="stable")
    return {k: v[order] for k, v in out.items()}


def compact(pm: pd.DataFrame, world: str) -> pd.DataFrame:
    d = pm[["mcode", "side"] + STAT_COLS + TOTALS].copy()
    for c in STAT_COLS + TOTALS:
        d[c] = d[c].astype("float32")
    d["side"] = d["side"].astype("int8")
    d.insert(0, "world", world)
    return d


def main() -> int:
    t0 = time.time()
    info: dict = {"seed": TC.SEED, "replays_per_variant": TC.REPLAYS}
    pop, steps = TC.population()
    info["population"] = steps
    TC.log(f"population: {len(pop):,} matches ({pop['tour'].value_counts().to_dict()})")
    P = TC.real_points(pop)
    n = len(pop)
    have = np.bincount(P["m"], minlength=n)
    assert (have > 0).all(), "a population match without points"
    last = np.r_[np.flatnonzero(np.diff(P["m"])), len(P["m"]) - 1]
    seq_a_won = P["winner"][last] == 1
    agree = seq_a_won == pop["a_won"].to_numpy()
    info["winner_disagreements_dropped"] = int((~agree).sum())
    if (~agree).any():
        keep = np.flatnonzero(agree)
        P = subset_points(P, keep, n)
        pop = pop.iloc[keep].reset_index(drop=True)
        pop["mcode"] = np.arange(len(pop), dtype=np.int64)
        n = len(pop)
    first = np.r_[0, np.flatnonzero(np.diff(P["m"])) + 1]
    pop["s0"] = P["server"][first].astype(np.int64)
    pop["late_set"] = np.where(pop["bo"] == 3, 2, 3)
    info["matches"] = {t: int((pop["tour"] == t).sum()) for t in ("atp", "wta")}
    info["points_real"] = int(len(P["m"]))
    TC.log(f"real points {len(P['m']):,}; winner disagreements dropped {info['winner_disagreements_dropped']}")
    pm, tot = TC.point_stats(P, n, pop["late_set"].to_numpy())
    TC.log("real statistics done")
    rows = TC.player_match_rates(pop, pm)
    pri = TC.fit_priors(rows)
    info["priors"] = pri
    TC.log(f"priors fitted on {pri['rows_used']:,} player-matches (seasons <= 2018)")
    keep_pop = ["mcode", "match_id", "tour", "year", "level", "map_level", "qualifying", "surface", "bo", "final",
                "final_code", "s0", "late_set", "player_a_id", "player_b_id", "a_won", "obs", "tournament_id",
                "tournament_date", "round", "round_order", "source", "strict", "tier"]
    pop[keep_pop].to_parquet(TC.OUT / "trait_population.parquet", index=False)
    main_frames = [compact(pm, "real")]
    var_frames = []
    match_frames = [pd.DataFrame({"world": "real", "mcode": np.arange(n), **{k: tot[k].to_numpy() for k in tot},
                                  "pa_true": np.nan, "pb_true": np.nan})]
    bo, fc, s0 = pop["bo"].to_numpy(), pop["final_code"].to_numpy(), pop["s0"].to_numpy()
    late = pop["late_set"].to_numpy()
    timings = {}
    for vi, variant in enumerate(TC.VARIANTS):
        for r in range(TC.REPLAYS):
            t1 = time.time()
            rng = np.random.default_rng([TC.SEED, vi, r])
            true = TC.draw_rates(rows, pri, variant, rng)
            pa, pb = true[:n], true[n:]
            Q = TC.replay_points(pa, pb, bo, fc, s0, rng)
            pmr, totr = TC.point_stats(Q, n, late)
            world = f"{variant}_{r}"
            (main_frames if variant == "V1" else var_frames).append(compact(pmr, world))
            match_frames.append(pd.DataFrame({"world": world, "mcode": np.arange(n), **{k: totr[k].to_numpy() for k in totr},
                                              "pa_true": pa, "pb_true": pb}))
            timings[world] = round(time.time() - t1, 1)
            TC.log(f"{world}: {len(Q['m']):,} points, {timings[world]}s")
            del Q, pmr
    pd.concat(main_frames, ignore_index=True).to_parquet(TC.OUT / "trait_player_matches.parquet", index=False)
    pd.concat(var_frames, ignore_index=True).to_parquet(TC.OUT / "trait_player_matches_variants.parquet", index=False)
    mf = pd.concat(match_frames, ignore_index=True)
    for c in mf.columns:
        if c not in ("world", "mcode"):
            mf[c] = mf[c].astype("float32")
    mf.to_parquet(TC.OUT / "trait_matches.parquet", index=False)
    info["timings_seconds"] = {**timings, "total": round(time.time() - t0, 1)}
    (TC.OUT / "trait_build.json").write_text(json.dumps(info, indent=1, default=float) + "\n", encoding="utf-8")
    TC.log("wrote trait_population, trait_player_matches(_variants), trait_matches, trait_build.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
