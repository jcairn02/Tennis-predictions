"""Stage D of the UFC-ideas study: the best inputs of both studies together, in one model.

The earlier study ended with the suggestion "test the best features together". This stage does that with the shared
harness, which fits a logistic regression without an intercept on several inputs at once (walk-forward by season, the
same null band and family-wide line as every other row): each model is one task with several columns.

The models (per tour; a column absent from the stage files is left out and listed in stageD_summary.json):
    earlier_three     the earlier summary's suggestion: the ratings through the iid model, the points matchup over the
                      last 52 weeks and sets over the last 14 days
    earlier_adjperf   the ratings, adjperf of total points won (2-week half-life, Stage B) and sets over 14 days
    earlier_ios       the ratings, Stage B's short-memory IOS points matchup (4 weeks for the men, 13 for the women)
                      and sets over 14 days
    box_trio          the ratings, the 2-week adjperf and the short-memory IOS matchup: the three point-level measures
    new_only          Stage A's Bradley-Terry rating, the 2-week adjperf, the short-memory IOS matchup, the credit for
                      opponents lost to, the quality of wins and the 52-week grinder (Stages A-C only)
    everything        Bradley-Terry, the ratings, the games-weighted Elo, the 2-week adjperf, the short-memory IOS
                      matchup, sets over 14 days, the first matches on a surface, age (two inputs) and the credit for
                      opponents lost to
    everything_mesr   everything plus Stage A's MESR (exists only where both players have an odds history)
Each is scored alone, given Elo, given the market and, where Stage A built it, given the Bradley-Terry rating.

The ladder: for the "everything" model and for Elo alone, the walk-forward per-match log loss on the main-tour matches
with closing odds of 2022-2026, as a share of the way from a coin flip to the odds (the earlier summary's scale), beside
the raw Bradley-Terry and Elo probabilities on the same matches.

Writes, in data/studies/ufc_ideas/: stageD_features.parquet, stageD_ranking.csv, stageD_results.csv,
stageD_null_copies.csv, stageD_results.json (the harness), stageD_catalog.json, stageD_summary.json.
Run: ./python.sh src/eda/ufc_ideas/stageD_rundown.py   (a few minutes with 5 workers)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage4_rundown as R  # noqa: E402
from src.eda.ufc_ideas import common as U  # noqa: E402

FEATURES = U.OUT / "stageD_features.parquet"
CATALOG = U.OUT / "stageD_catalog.json"
SUMMARY = U.OUT / "stageD_summary.json"
EARLIER = ["rating_matchup|single", "elo_games|single", "sets_14d|single", "mu_points|52 weeks", "surface_first|single",
           "age|single", "age|single|2"]
STAGE_COLS = {"A": ["bt|single", "p_bt", "mesr|single", "p_mesr", "bt_games|single", "bt_surface|single"],
              "B": ["adjperf_tpw|decayed", "adjperf_spw|decayed", "ios_matchup_points|diagnostic: h 4 weeks",
                    "ios_matchup_points|diagnostic: h 13 weeks", "ios_matchup_points|single", "adjperf_ace|decayed",
                    "vs_bottom_third_tpw|52 weeks"],
              "C": ["revalue_lost|52 weeks", "sos_won_elo|52 weeks", "grinder|52 weeks"]}
IOS_SHORT = {"atp": "ios_matchup_points|diagnostic: h 4 weeks", "wta": "ios_matchup_points|diagnostic: h 13 weeks"}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


def assemble() -> tuple[pd.DataFrame, dict]:
    """The pool with the chosen columns of every stage file that exists (aligned on match_id, the pool's order)."""
    pool = U.load_pool(EARLIER)
    missing = {}
    for s, cols in STAGE_COLS.items():
        p = U.OUT / f"stage{s}_features.parquet"
        if not p.exists():
            missing[s] = cols
            continue
        f = pd.read_parquet(p)
        assert (f["match_id"].to_numpy() == pool["match_id"].to_numpy()).all(), f"stage {s} frame is not the pool"
        have = [c for c in cols if c in f.columns]
        for c in have:
            pool[c] = f[c].to_numpy(dtype="float64")
        if len(have) < len(cols):
            missing[s] = [c for c in cols if c not in f.columns]
    return pool, missing


def models(cols: set) -> dict:
    """Model id -> (name, description, per-tour column lists); columns absent from the frame are dropped."""
    def keep(lst):
        return [c for c in lst if c in cols]
    out = {
        "earlier_three": ("The earlier study's three", "the ratings through the iid model, the points matchup over the last 52 weeks and sets over the last 14 days",
                          {t: keep(["rating_matchup|single", "mu_points|52 weeks", "sets_14d|single"]) for t in C.TOURS}),
        "earlier_adjperf": ("Ratings + 2-week adjperf + load", "the ratings, Stage B's adjperf of total points won (2-week half-life) and sets over the last 14 days",
                            {t: keep(["rating_matchup|single", "adjperf_tpw|decayed", "sets_14d|single"]) for t in C.TOURS}),
        "earlier_ios": ("Ratings + short-memory IOS + load", "the ratings, Stage B's short-memory IOS points matchup and sets over the last 14 days",
                        {t: keep(["rating_matchup|single", IOS_SHORT[t], "sets_14d|single"]) for t in C.TOURS}),
        "box_trio": ("The three point-level measures", "the ratings through the iid model, the 2-week adjperf of total points and the short-memory IOS matchup",
                     {t: keep(["rating_matchup|single", "adjperf_tpw|decayed", IOS_SHORT[t]]) for t in C.TOURS}),
        "new_only": ("Stages A-C only", "Bradley-Terry, the 2-week adjperf, the short-memory IOS matchup, the credit for opponents lost to, the quality of wins and the 52-week grinder",
                     {t: keep(["bt|single", "adjperf_tpw|decayed", IOS_SHORT[t], "revalue_lost|52 weeks", "sos_won_elo|52 weeks", "grinder|52 weeks"]) for t in C.TOURS}),
        "everything": ("Everything", "Bradley-Terry, the ratings, the games-weighted Elo, the 2-week adjperf, the short-memory IOS matchup, sets over 14 days, the first matches on a surface, age and the credit for opponents lost to",
                       {t: keep(["bt|single", "rating_matchup|single", "elo_games|single", "adjperf_tpw|decayed", IOS_SHORT[t], "sets_14d|single",
                                 "surface_first|single", "age|single", "age|single|2", "revalue_lost|52 weeks"]) for t in C.TOURS}),
        "everything_mesr": ("Everything + MESR", "the everything model plus Stage A's market-embedded rating, where both players have an odds history",
                            {t: keep(["bt|single", "rating_matchup|single", "elo_games|single", "adjperf_tpw|decayed", IOS_SHORT[t], "sets_14d|single",
                                      "surface_first|single", "age|single", "age|single|2", "revalue_lost|52 weeks", "mesr|single"]) for t in C.TOURS}),
    }
    return {k: v for k, v in out.items() if all(len(v[2][t]) >= 2 for t in C.TOURS) and (k != "everything_mesr" or "mesr|single" in cols)}


def walk_ll(f: pd.DataFrame, tour: str, cols: list[str], base: str | None, seasons: list[int]) -> tuple[np.ndarray, np.ndarray]:
    """Per-match walk-forward log losses (NaN where not scored) of base + cols and of the base alone, on the tour's
    rows where every column exists, aligned to the frame's rows."""
    n = len(f)
    t = f["tour"].to_numpy() == tour
    X = np.column_stack([f[c].to_numpy(dtype="float64") for c in cols])
    ex = t & np.isfinite(X).all(axis=1)
    if base is not None:
        ex &= np.isfinite(f[base].to_numpy(dtype="float64"))
    idx = np.flatnonzero(ex)
    Xe = X[idx]
    sd = Xe.std(axis=0)
    Xs = Xe / np.where(sd > 0, sd, 1.0)
    year, y = f["year"].to_numpy()[idx], f["a_won"].to_numpy()[idx]
    if base is None:
        Z, b = Xs[None], None
    else:
        b = logit(np.clip(f[base].to_numpy(dtype="float64")[idx], 1e-9, 1 - 1e-9))
        Z = np.concatenate([b[:, None], Xs], axis=1)[None]
    w = R.walk(np.ascontiguousarray(Z), y, year, seasons, b)
    llm, llb = np.full(n, np.nan), np.full(n, np.nan)
    llm[idx], llb[idx] = w["llm"][0], w["llb"]
    return llm, llb


def ladder(f: pd.DataFrame, mods: dict) -> dict:
    """The earlier ladder's scale on the main-tour matches with odds of 2022-2026: (coin - log loss) / (coin - the
    odds' log loss), for Elo alone, Elo + everything (walk-forward), the raw Bradley-Terry and Elo probabilities and the
    raw ratings-through-the-iid-model probability."""
    coin = float(np.log(2))
    out = {}
    seasons = list(C.EVAL_YEARS)
    for t in C.TOURS:
        sub = ((f["tour"].to_numpy() == t) & f["evaluation"].to_numpy() & np.isfinite(f["p_mkt"].to_numpy(dtype="float64"))
               & (f["year"].to_numpy() >= 2022) & np.isin(f["group"].to_numpy(), ["GS", "FIN", "T1000", "T500", "T250"]))
        y = f["a_won"].to_numpy()[sub]

        def ll_of(p):
            p = np.clip(np.asarray(p, dtype="float64"), 1e-9, 1 - 1e-9)
            return float(np.mean(np.where(y, -np.log(p), -np.log(1 - p))))
        mk = ll_of(f["p_mkt"].to_numpy(dtype="float64")[sub])
        span = coin - mk
        rec = {"matches": int(sub.sum()), "coin_to_market_milli": 1000 * span, "market": 1.0,
               "elo_raw": (coin - ll_of(f["p_elo"].to_numpy(dtype="float64")[sub])) / span}
        if "p_bt" in f.columns:
            pb = f["p_bt"].to_numpy(dtype="float64")
            ok = sub & np.isfinite(pb)
            yy = f["a_won"].to_numpy()[ok]
            pbb = np.clip(pb[ok], 1e-9, 1 - 1e-9)
            rec["bt_raw"] = (coin - float(np.mean(np.where(yy, -np.log(pbb), -np.log(1 - pbb))))) / span
            rec["bt_raw_matches"] = int(ok.sum())
        if "everything" in mods:
            llm, llb = walk_ll(f, t, mods["everything"][2][t], "p_elo", seasons)
            m = sub & np.isfinite(llm)
            rec["elo_fit"] = (coin - float(np.nanmean(llb[m]))) / span
            rec["elo_plus_everything"] = (coin - float(np.nanmean(llm[m]))) / span
            rec["everything_matches"] = int(m.sum())
            if "p_bt" in f.columns:
                llm2, llb2 = walk_ll(f, t, [c for c in mods["everything"][2][t] if c != "bt|single"], "p_bt", seasons)
                m2 = sub & np.isfinite(llm2)
                rec["bt_fit"] = (coin - float(np.nanmean(llb2[m2]))) / span
                rec["bt_plus_everything"] = (coin - float(np.nanmean(llm2[m2]))) / span
        if "earlier_three" in mods:
            llm, llb = walk_ll(f, t, mods["earlier_three"][2][t], "p_elo", seasons)
            m = sub & np.isfinite(llm)
            rec["elo_plus_earlier_three"] = (coin - float(np.nanmean(llm[m]))) / span
        out[t] = rec
    return out


def main() -> int:
    f, missing = assemble()
    log(f"frame: {len(f):,} matches, {f.shape[1]} columns; missing: {missing}")
    mods = models(set(f.columns))
    has_bt = "p_bt" in f.columns
    f.to_parquet(FEATURES)
    tasks, catalog = [], []
    for mid, (name, desc, per_tour) in mods.items():
        for t in C.TOURS:
            cols = per_tour[t]
            scores = ["alone", "elo", "market"] + (["bt"] if has_bt and "bt|single" not in cols else [])
            tasks.append(U.task(t, mid, "together", name, "together", cols, scores=scores,
                                wta_box_from_2019=True, bases={"bt": "p_bt"} if has_bt else None))
        catalog.append({"id": mid, "form": "together", "name": name, "family": "together", "description": desc,
                        "inputs": {t: per_tour[t] for t in C.TOURS}, "tuned": "nothing: every input at its stage's frozen constants"})
    log(f"{len(tasks)} tasks ({len(mods)} models)")
    res = U.rundown(FEATURES, tasks, U.OUT / "stageD", workers=5)
    CATALOG.write_text(json.dumps(catalog, indent=1), encoding="utf-8")
    lad = ladder(f, mods)
    rank = res["ranking"]
    head = {}
    for _, r in rank.iterrows():
        head[f"{r['tour']}|{r['id']}"] = {k: (None if pd.isna(r.get(k)) else (bool(r[k]) if isinstance(r.get(k), (bool, np.bool_)) else float(r[k]) if isinstance(r.get(k), (int, float, np.floating, np.integer)) else r.get(k)))
                                         for k in ("alone_imp", "elo_imp", "elo_lo", "elo_hi", "elo_2022-2026", "elo_clears_line", "market_imp",
                                                   "market_lo", "market_hi", "market_2022-2026", "market_clears_line", "market_above_band",
                                                   "bt_imp", "bt_lo", "bt_hi", "reading", "elo_coverage", "market_coverage", "eras_positive")
                                         if k in rank.columns}
    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "models": catalog, "missing_columns": missing,
               "has_bt": has_bt, "headline": head, "ladder": lad, "lines": res["lines"], "seconds": round(time.time() - T0, 1)}
    SUMMARY.write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    log(f"wrote {SUMMARY}")
    for t in C.TOURS:
        log(f"ladder {t}: {lad[t]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
