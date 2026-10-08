"""Stage 1 of the predictability diagnostic, part 2: the baselines, each a pre-match probability that A wins.

Every baseline is walk-forward: a match is predicted before anything learns from it.

    coin      0.5.
    rank      a one-input logistic regression on the log ratio of the two ranks; points: the same on the
              log ratio of ranking points (plus one). Fitted per tour on earlier seasons only (for season Y,
              on evaluation-level matches of 2010 to Y-1), without an intercept: side A is random, so the
              probability is one half when the players are level. An unranked player is given the rank one
              below the lowest rank seen on the tour in earlier seasons, and 0 points.
    elo       overall Elo with K(n) = k0 / (n + offset) ** shape, n the player's earlier rated matches
              (FiveThirtyEight's form, as in src/ratings/elo.py).
    elo_surf  surface-blended Elo: each player also has a rating per surface (hard, clay, grass, carpet),
              updated only by matches on it, and the prediction uses (1 - w) * overall + w * surface.
    market    the closing odds' market average, normalised (stage1_odds.py), where they exist; Pinnacle
              as a check.

Elo runs over every singles match from 2010, every level and team events included, so players arriving
from the ITF and Challenger levels carry ratings. It honours the Brief's time rule exactly: a rating
used for a match includes earlier events and earlier rounds of the same event, never other matches of
the same round (a round robin) or other events of the same week (elo_pass()). src/ratings/elo.py updates
row by row, which lets a round robin's later matches see its earlier ones and one event of a week see
another; its formulas are kept (and tested equal), its row-by-row fit is not used.

Walkovers and matches of status "other" never move ratings. Retirements are run both ways, as the owner
asked: counted as a result ("ret") and skipped ("noret"). The K constants are tuned on the overall Elo's
log loss over the evaluation matches of 2013-2018 only, on a grid of 270 settings (GRID), per tour and
per retirement rule; the surface weight is then tuned on the same years with K fixed; everything is then
frozen.

Writes, in data/studies/predictability_diagnostic/:
    stage1_baselines.parquet          one row per match (all 872,704): every baseline's probability that A
                                      wins (evaluation matches; Elo for every match), and each player's
                                      pre-match overall and surface rating and rated-match count, both ways
                                      of treating retirements
    stage1_elo_tuning.csv             the K grid: log loss 2013-2018 per tour, retirement rule and constants
    stage1_elo_weights.csv            the surface-weight grid on the same years
    stage1_rank_fits.csv              the rank and points regressions: one coefficient per tour and season
    stage1_baselines_summary.json     the frozen constants, the unranked rule, and the leakage checks

Run after stage1_odds.py: ./python.sh src/eda/predictability_diagnostic/stage1_baselines.py   (about 5½ minutes)
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

BASELINES = C.OUT / "stage1_baselines.parquet"
TUNING = C.OUT / "stage1_elo_tuning.csv"
WEIGHTS_CSV = C.OUT / "stage1_elo_weights.csv"
RANK_FITS = C.OUT / "stage1_rank_fits.csv"
SUMMARY = C.OUT / "stage1_baselines_summary.json"
ODDS = C.OUT / "stage1_odds.parquet"

START = 1500.0                                   # every player's first rating (src/ratings/elo.py's default)
SURFACES = ("Hard", "Clay", "Grass", "Carpet")   # src/ratings/elo.py's surfaces
UPDATES = {"ret": ("completed", "retired"),      # the statuses whose result moves ratings
           "noret": ("completed",)}
RULE_NAMES = {"ret": "retirements counted", "noret": "retirements skipped"}
TUNE_YEARS = range(2013, 2019)
# A first grid (k0 to 400, offset from 1, shape to 0.6) put the best at its corner for both tours; this
# one reaches past it, so the best lies inside. The loss surface is a long flat valley in which a larger
# k0 trades against a larger shape (stage1_elo_tuning.csv).
GRID = {"k0": [150, 200, 250, 300, 400, 500, 600, 800, 1200], "offset": [0.5, 1, 2, 5, 10],
        "shape": [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]}
DEFAULT_K = {"k0": 250.0, "offset": 5.0, "shape": 0.4}   # FiveThirtyEight's, src/ratings/elo.py's default
SURFACE_WEIGHTS = [round(x, 2) for x in np.arange(0.0, 1.0001, 0.05)]
K_AT = (0, 5, 10, 25, 50, 100, 250, 500, 1000)   # rated-match counts at which the summary reports K
EPS = 1e-12
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# Elo under the Brief's time rule

def k_factor(n, k0: float, offset: float, shape: float):
    """FiveThirtyEight's K: large for a player with few rated matches, shrinking with their number."""
    return k0 / (n + offset) ** shape


def expected(r_a, r_b):
    """The probability that A beats B from the two ratings."""
    return 1.0 / (1.0 + 10.0 ** ((r_b - r_a) / 400.0))


def elo_pass(week, event, rnd, a, b, a_won, surf, upd, n_players: int, k0: float = 250.0, offset: float = 5.0,
             shape: float = 0.4, surface: bool = True) -> np.ndarray:
    """One chronological pass. Inputs are sequences in the table's order: week (the tournament date),
    event (a code unique within its week), rnd (round order), a and b (player codes 0..n_players-1),
    a_won, surf (0-3, or -1 when unknown), upd (whether the result moves ratings).

    Returns an array with one row per match: A's and B's overall rating before it, their rated-match
    counts, and the same four for the match's surface (missing when the surface is unknown or
    ``surface`` is False).

    The time rule. A player's rating for a match is their rating at the start of its week plus what
    their matches of the same event in earlier rounds added. What a round adds is held back until the
    next round of that event (so a round robin's matches never see each other) and what an event adds
    reaches the player's other events only once the week is over (so two events of one week never see
    each other). Every update uses the ratings and counts the match was predicted with, as Elo does.
    """
    R = [START] * n_players
    N = [0] * n_players
    RS = [[START] * n_players for _ in SURFACES]
    NS = [[0] * n_players for _ in SURFACES]
    out = np.full((len(week), 8), np.nan)
    # per player and event (and surface) within the current week:
    # [delta of earlier rounds, count of earlier rounds, round of the pending entry, pending delta, pending count]
    lo: dict = {}
    ls: dict = {}
    cur = None
    for i in range(len(week)):
        if week[i] != cur:
            for (p, _), st in lo.items():
                R[p] += st[0] + st[3]
                N[p] += st[1] + st[4]
            for (p, _, s), st in ls.items():
                RS[s][p] += st[0] + st[3]
                NS[s][p] += st[1] + st[4]
            lo.clear()
            ls.clear()
            cur = week[i]
        e, r, s, pa, pb = event[i], rnd[i], surf[i], a[i], b[i]
        xa = lo.get((pa, e))
        if xa is None:
            xa = lo[(pa, e)] = [0.0, 0, r, 0.0, 0]
        elif xa[2] < r:
            xa[0] += xa[3]; xa[1] += xa[4]; xa[2] = r; xa[3] = 0.0; xa[4] = 0
        xb = lo.get((pb, e))
        if xb is None:
            xb = lo[(pb, e)] = [0.0, 0, r, 0.0, 0]
        elif xb[2] < r:
            xb[0] += xb[3]; xb[1] += xb[4]; xb[2] = r; xb[3] = 0.0; xb[4] = 0
        ra, rb, na, nb = R[pa] + xa[0], R[pb] + xb[0], N[pa] + xa[1], N[pb] + xb[1]
        out[i, 0], out[i, 1], out[i, 2], out[i, 3] = ra, rb, na, nb
        do_s = surface and s >= 0
        if do_s:
            ya = ls.get((pa, e, s))
            if ya is None:
                ya = ls[(pa, e, s)] = [0.0, 0, r, 0.0, 0]
            elif ya[2] < r:
                ya[0] += ya[3]; ya[1] += ya[4]; ya[2] = r; ya[3] = 0.0; ya[4] = 0
            yb = ls.get((pb, e, s))
            if yb is None:
                yb = ls[(pb, e, s)] = [0.0, 0, r, 0.0, 0]
            elif yb[2] < r:
                yb[0] += yb[3]; yb[1] += yb[4]; yb[2] = r; yb[3] = 0.0; yb[4] = 0
            sa, sb, nsa, nsb = RS[s][pa] + ya[0], RS[s][pb] + yb[0], NS[s][pa] + ya[1], NS[s][pb] + yb[1]
            out[i, 4], out[i, 5], out[i, 6], out[i, 7] = sa, sb, nsa, nsb
        if upd[i]:
            res = 1.0 if a_won[i] else 0.0
            surprise = res - 1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))
            xa[3] += k0 / (na + offset) ** shape * surprise
            xb[3] -= k0 / (nb + offset) ** shape * surprise
            xa[4] += 1
            xb[4] += 1
            if do_s:
                surprise = res - 1.0 / (1.0 + 10.0 ** ((sb - sa) / 400.0))
                ya[3] += k0 / (nsa + offset) ** shape * surprise
                yb[3] -= k0 / (nsb + offset) ** shape * surprise
                ya[4] += 1
                yb[4] += 1
    return out


def blend(out: np.ndarray, w: float) -> np.ndarray:
    """P(A wins) from the blended ratings (1 - w) * overall + w * surface; overall alone when the surface
    is unknown."""
    sa = np.where(np.isnan(out[:, 4]), out[:, 0], out[:, 4])
    sb = np.where(np.isnan(out[:, 5]), out[:, 1], out[:, 5])
    return expected((1 - w) * out[:, 0] + w * sa, (1 - w) * out[:, 1] + w * sb)


def history_arrays(m: pd.DataFrame) -> dict:
    """The inputs of elo_pass() for one tour's matches, already in the table's order."""
    players, codes = np.unique(np.concatenate([m["player_a_id"].to_numpy(), m["player_b_id"].to_numpy()]),
                               return_inverse=True)
    return {"week": (m["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")).tolist(),
            "event": pd.factorize(m["tournament_date"].astype(str) + "|" + m["tournament_id"])[0].tolist(),
            "rnd": m["round_order"].astype(int).tolist(),
            "a": codes[:len(m)].tolist(), "b": codes[len(m):].tolist(),
            "a_won": m["a_won"].astype(bool).tolist(),
            "surf": m["surface"].map({s: i for i, s in enumerate(SURFACES)}).fillna(-1).astype(int).tolist(),
            "n_players": int(len(players))}


def run_elo(h: dict, status: pd.Series, rule: str, k: dict, surface: bool = True) -> np.ndarray:
    upd = status.isin(UPDATES[rule]).tolist()
    return elo_pass(h["week"], h["event"], h["rnd"], h["a"], h["b"], h["a_won"], h["surf"], upd, h["n_players"],
                    k["k0"], k["offset"], k["shape"], surface=surface)


def log_loss(p, y) -> float:
    p = np.clip(np.asarray(p, dtype="float64"), EPS, 1 - EPS)
    y = np.asarray(y, dtype=bool)
    return float(-np.mean(np.where(y, np.log(p), np.log(1 - p))))


# ------------------------------------------------------------------------------------------------
# Tuning (2013-2018 only) and the frozen passes

def tune(m: pd.DataFrame) -> tuple[dict, pd.DataFrame, pd.DataFrame, dict]:
    """Per tour and retirement rule: the K constants with the lowest overall-Elo log loss on the evaluation
    matches of 2013-2018, then the surface weight on the same matches with K fixed. Returns the frozen
    settings, both grids, and each tour's final passes."""
    chosen, rows, wrows, passes = {}, [], [], {}
    for tour in C.TOURS:
        t = m[m["tour"].eq(tour)].reset_index(drop=True)
        h = history_arrays(t)
        last = int(np.flatnonzero(t["year"].le(TUNE_YEARS[-1]).to_numpy()).max())
        early = t.iloc[:last + 1].reset_index(drop=True)                 # tuning needs no later history
        he = history_arrays(early)
        tune_rows = (early["evaluation"] & early["year"].isin(list(TUNE_YEARS))).to_numpy()
        y = early["a_won"].to_numpy(dtype=bool)[tune_rows]
        for rule in UPDATES:
            for k0, off, sh in itertools.product(GRID["k0"], GRID["offset"], GRID["shape"]):
                k = {"k0": float(k0), "offset": float(off), "shape": float(sh)}
                out = run_elo(he, early["status"], rule, k, surface=False)
                p = expected(out[tune_rows, 0], out[tune_rows, 1])
                rows.append({"tour": tour, "rule": rule, **k, "log_loss_2013_2018": log_loss(p, y), "matches": int(tune_rows.sum())})
            g = pd.DataFrame([r for r in rows if r["tour"] == tour and r["rule"] == rule])
            best = g.loc[g["log_loss_2013_2018"].idxmin()]
            k = {c: float(best[c]) for c in ("k0", "offset", "shape")}
            out_early = run_elo(he, early["status"], rule, k, surface=True)
            for w in SURFACE_WEIGHTS:
                wrows.append({"tour": tour, "rule": rule, "w": w,
                              "log_loss_2013_2018": log_loss(blend(out_early[tune_rows], w), y), "matches": int(tune_rows.sum())})
            wg = pd.DataFrame([r for r in wrows if r["tour"] == tour and r["rule"] == rule])
            w = float(wg.loc[wg["log_loss_2013_2018"].idxmin(), "w"])
            chosen[(tour, rule)] = {**k, "w": w}
            out = run_elo(h, t["status"], rule, k, surface=True)                 # frozen: the whole history
            assert np.allclose(out[:len(early)], out_early, equal_nan=True)     # the tuning pass is its prefix
            passes[(tour, rule)] = out
            log(f"{tour} {rule}: K {k}, surface weight {w}")
    return chosen, pd.DataFrame(rows), pd.DataFrame(wrows), passes


# ------------------------------------------------------------------------------------------------
# Rank and points

def rank_inputs(m: pd.DataFrame) -> pd.DataFrame:
    """Each match's two ranks and ranking points (as of the tournament's start), by side."""
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "side", "rank", "rank_points"])
    a = mp[mp["side"].eq("A")].set_index("match_id")
    b = mp[mp["side"].eq("B")].set_index("match_id")
    return pd.DataFrame({"rank_a": m["match_id"].map(a["rank"]).to_numpy(), "rank_b": m["match_id"].map(b["rank"]).to_numpy(),
                         "pts_a": m["match_id"].map(a["rank_points"]).to_numpy(),
                         "pts_b": m["match_id"].map(b["rank_points"]).to_numpy()}, index=m.index)


def unranked_rank(m: pd.DataFrame, r: pd.DataFrame) -> pd.Series:
    """Per tour and season: one below the lowest rank seen on the tour in earlier seasons (2010 uses its
    own, being history only)."""
    worst = pd.concat([r["rank_a"], r["rank_b"]], axis=1).max(axis=1).groupby([m["tour"], m["year"]]).max()
    out = {}
    for tour in C.TOURS:
        s = worst.loc[tour].sort_index()
        prior = s.cummax().shift(1)
        prior.iloc[0] = s.iloc[0]
        for year, v in prior.items():
            out[(tour, int(year))] = float(v) + 1
    return pd.Series(out)


def rank_models(m: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """p_rank and p_points for evaluation matches, each season fitted on the earlier seasons only."""
    r = rank_inputs(m)
    unr = unranked_rank(m, r)
    fill = pd.Series([unr[(t, int(y))] for t, y in zip(m["tour"], m["year"])], index=m.index)
    ra, rb = r["rank_a"].fillna(fill), r["rank_b"].fillna(fill)
    pa, pb = r["pts_a"].fillna(0.0).clip(lower=0), r["pts_b"].fillna(0.0).clip(lower=0)
    x = pd.DataFrame({"rank": np.log(rb) - np.log(ra), "points": np.log1p(pa) - np.log1p(pb)}, index=m.index)
    scope = m["level"].isin(C.EVAL_LEVELS) & m["status"].isin(C.EVAL_STATUSES)
    probs = pd.DataFrame(np.nan, index=m.index, columns=["p_rank", "p_points"])
    fits = []
    for tour in C.TOURS:
        for year in C.EVAL_YEARS:
            train = scope & m["tour"].eq(tour) & (m["year"] < year)
            test = m["evaluation"] & m["tour"].eq(tour) & m["year"].eq(year)
            if not test.any():
                continue
            for name in ("rank", "points"):
                lr = LogisticRegression(fit_intercept=False, C=np.inf)
                lr.fit(x.loc[train, [name]].to_numpy(), m.loc[train, "a_won"].astype(int).to_numpy())
                probs.loc[test, f"p_{name}"] = lr.predict_proba(x.loc[test, [name]].to_numpy())[:, 1]
                fits.append({"tour": tour, "season": year, "input": name, "coefficient": float(lr.coef_[0, 0]),
                             "training_matches": int(train.sum()), "training_seasons": f"2010-{year - 1}",
                             "unranked_rank": unr[(tour, year)]})
    ev = m["evaluation"]
    unranked = {}
    for tour in C.TOURS:
        e = ev & m["tour"].eq(tour)
        miss = r.loc[e, ["rank_a", "rank_b"]].isna()
        unranked[tour] = {"evaluation_matches": int(e.sum()), "player_rows_unranked": int(miss.to_numpy().sum()),
                          "matches_with_an_unranked_player": int(miss.any(axis=1).sum()),
                          "matches_with_both_unranked": int(miss.all(axis=1).sum()),
                          "points_missing_with_a_rank": int((r.loc[e, ["pts_a", "pts_b"]].isna().to_numpy()
                                                             & ~miss.to_numpy()).sum())}
    return probs, pd.DataFrame(fits), unranked


# ------------------------------------------------------------------------------------------------
# A black-box leakage probe cut by date, event and round (the audit's P3)

def probe_by_round(h: dict, ratings, n_cuts: int = 12, seed: int = 20260930, from_quantile: float = 0.5) -> dict:
    """Black-box check of a rating pass ``ratings(h) -> array (one row per match)``.

    At each of ``n_cuts`` random cut matches, the result of every match that is not earlier than the cut
    under the Brief's rule (the cut's own round and later rounds of its event, the week's other events,
    every later week) is flipped at random, and the pass is re-run. A pass that honours the rule leaves
    unchanged the pre-match values of every match of earlier weeks and of the cut event's rounds up to
    and including the cut's round (a round robin's other matches too). The Stage 0 probe cuts by the
    table's order instead, and cannot see leaks between matches the rule calls simultaneous (audit P3)."""
    rng = np.random.default_rng(seed)
    base = ratings(h)
    week, event, rnd = np.asarray(h["week"]), np.asarray(h["event"]), np.asarray(h["rnd"])
    won = np.asarray(h["a_won"], dtype=bool)
    cand = np.flatnonzero(week >= np.quantile(week, from_quantile))
    changed_protected, protected, changed_open = 0, 0, 0
    for c in rng.choice(cand, size=min(n_cuts, len(cand)), replace=False):
        later = (week > week[c]) | ((week == week[c]) & ((event != event[c]) | (rnd >= rnd[c])))
        keep = (week < week[c]) | ((week == week[c]) & (event == event[c]) & (rnd <= rnd[c]))
        flip = later & (rng.random(len(week)) < 0.5)
        got = ratings({**h, "a_won": np.where(flip, ~won, won).tolist()})
        diff = ~np.all(np.isclose(got, base, equal_nan=True), axis=1)
        protected += int(keep.sum())
        changed_protected += int((diff & keep).sum())
        changed_open += int((diff & ~keep).sum())
    return {"cuts": int(min(n_cuts, len(cand))), "protected_matches_checked": protected,
            "protected_matches_changed": changed_protected, "later_matches_changed": changed_open}


# ------------------------------------------------------------------------------------------------

def main() -> int:
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "evaluation", "status", "surface",
                        "tournament_id", "tournament_date", "round_order", "player_a_id", "player_b_id", "a_won"])
    log(f"matches: {len(m):,}")
    chosen, grid, wgrid, passes = tune(m)
    grid.to_csv(TUNING, index=False)
    wgrid.to_csv(WEIGHTS_CSV, index=False)

    out = m[["match_id", "tour", "year", "evaluation", "a_won"]].copy()
    out["p_coin"] = np.where(out["evaluation"], 0.5, np.nan)
    probs, fits, unranked = rank_models(m)
    out["p_rank"], out["p_points"] = probs["p_rank"], probs["p_points"]
    fits.to_csv(RANK_FITS, index=False)
    log("rank and points regressions fitted")
    cols = ["elo_a", "elo_b", "n_a", "n_b", "elo_surf_a", "elo_surf_b", "n_surf_a", "n_surf_b"]
    for rule in UPDATES:
        block = np.full((len(m), 8), np.nan)
        p_elo, p_surf = np.full(len(m), np.nan), np.full(len(m), np.nan)
        for tour in C.TOURS:
            idx = np.flatnonzero(m["tour"].eq(tour).to_numpy())
            res = passes[(tour, rule)]
            block[idx] = res
            p_elo[idx] = expected(res[:, 0], res[:, 1])
            p_surf[idx] = blend(res, chosen[(tour, rule)]["w"])
        for j, c in enumerate(cols):
            out[f"{c}_{rule}"] = block[:, j].astype("float32")   # ratings to 0.001 point; counts exact below 2**24
        out[f"p_elo_{rule}"] = p_elo
        out[f"p_elo_surf_{rule}"] = p_surf
    odds = pd.read_parquet(ODDS, columns=["match_id", "p_avg_a", "p_ps_a"]).set_index("match_id")
    out["p_market"] = out["match_id"].map(odds["p_avg_a"]).where(out["evaluation"])
    out["p_pinnacle"] = out["match_id"].map(odds["p_ps_a"]).where(out["evaluation"])
    out.to_parquet(BASELINES, index=False, compression="zstd")
    log(f"wrote {BASELINES.name}")

    # the date-and-round probe on the real history, both tours and both retirement rules
    probes = {}
    for tour, rule in itertools.product(C.TOURS, UPDATES):
        t = m[m["tour"].eq(tour)].reset_index(drop=True)
        h = history_arrays(t)
        upd, k = t["status"].isin(UPDATES[rule]).tolist(), chosen[(tour, rule)]

        def ratings(hh, upd=upd, k=k):
            return elo_pass(hh["week"], hh["event"], hh["rnd"], hh["a"], hh["b"], hh["a_won"], hh["surf"], upd,
                            hh["n_players"], k["k0"], k["offset"], k["shape"])

        probes[f"{tour}_{rule}"] = probe_by_round(h, ratings, n_cuts=6, from_quantile=0.85)
        log(f"probe {tour} {rule}: {probes[f'{tour}_{rule}']}")

    summary = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
               "tuning_years": [TUNE_YEARS[0], TUNE_YEARS[-1]], "grid": GRID, "surface_weights": SURFACE_WEIGHTS,
               "default_k": DEFAULT_K, "start_rating": START, "surfaces": list(SURFACES),
               "updates": {k: list(v) for k, v in UPDATES.items()}, "rule_names": RULE_NAMES,
               "chosen": [{"tour": t, "rule": r, **v} for (t, r), v in chosen.items()]}
    detail = []
    for (tour, rule), v in chosen.items():
        g = grid[grid["tour"].eq(tour) & grid["rule"].eq(rule)].sort_values("log_loss_2013_2018")
        d = g[(g["k0"] == DEFAULT_K["k0"]) & (g["offset"] == DEFAULT_K["offset"]) & (g["shape"] == DEFAULT_K["shape"])]
        wg = wgrid[wgrid["tour"].eq(tour) & wgrid["rule"].eq(rule)]
        inner = g[(g["k0"] > min(GRID["k0"])) & (g["k0"] < max(GRID["k0"])) & (g["offset"] > min(GRID["offset"]))
                  & (g["offset"] < max(GRID["offset"])) & (g["shape"] > min(GRID["shape"])) & (g["shape"] < max(GRID["shape"]))]
        ib = inner.iloc[0]
        detail.append({"tour": tour, "rule": rule,
                       "k_at_matches": {str(k): round(float(k_factor(k, v["k0"], v["offset"], v["shape"])), 1) for k in K_AT},
                       "best_inside_grid": {"k0": float(ib["k0"]), "offset": float(ib["offset"]), "shape": float(ib["shape"]),
                                            "log_loss": float(ib["log_loss_2013_2018"])},
                       "best": float(g["log_loss_2013_2018"].iloc[0]),
                       "default_538": float(d["log_loss_2013_2018"].iloc[0]),
                       "worst": float(g["log_loss_2013_2018"].iloc[-1]),
                       "within_1_milli_of_best": int((g["log_loss_2013_2018"] <= g["log_loss_2013_2018"].iloc[0] + 0.001).sum()),
                       "grid_points": int(len(g)),
                       "on_grid_edge": {c: bool(v[c] in (min(GRID[c]), max(GRID[c]))) for c in ("k0", "offset", "shape")},
                       "surface_w0": float(wg.loc[wg["w"].eq(0.0), "log_loss_2013_2018"].iloc[0]),
                       "surface_best": float(wg["log_loss_2013_2018"].min()), "matches": int(g["matches"].iloc[0])})
    summary["tuning_detail"] = detail
    summary["default_k_at_matches"] = {str(k): round(float(k_factor(k, **DEFAULT_K)), 1) for k in K_AT}
    summary["unranked"] = unranked
    summary["unranked_rank_by_tour_season"] = [{"tour": t, "season": y, "rank": v}
                                               for (t, y), v in unranked_rank(m, rank_inputs(m)).items()]
    summary["probe_by_round"] = probes
    summary["seconds"] = round(time.time() - T0, 1)
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log(f"wrote {SUMMARY.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
