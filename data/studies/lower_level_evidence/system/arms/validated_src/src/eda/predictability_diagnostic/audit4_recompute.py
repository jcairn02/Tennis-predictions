"""Audit B of Stage 4, check 1 (with the A/B part of check 4): the strongest features recomputed for random matches
by a separate, simple implementation that looks only at earlier matches.

The rows: the ten strongest given Elo on each tour (stage4_ranking.csv); the five strongest are the check, the rest
an extension. 13 features in all.

The matches: 100 random evaluation matches per tour (seed 20261002), plus matches where the time rule is most
delicate, drawn per tour: round-robin matches (whose same-round matches must stay unseen), the Finals' knockout
matches after a round robin, matches of a player with two events in one week, Grand Slam quarter-finals onwards,
and qualifiers' first main-draw match (whose history includes the event's qualifying rounds).

How each feature is rebuilt, for each match t and each of its players:
    history     the player's rows are filtered explicitly: tournament date before t's, or the same tournament and date
                with a smaller round order. Every sum is then taken over that list directly, in Python, from the
                Stage 0 counts (no as-of helper, no cumulative sums)
    ratings     the games-weighted Elo and Stage 3's serve and return ratings are replayed from scratch on the tour's
                matches that t may see (the same filter, applied to every match of the tour), with t's own result
                blanked, and t's pre-match values read at the end. Each replay sees nothing after t: it is not given it
    constants   the plan's frozen constants as stored (Stage 3's averages and K; Stage 4's for the new statistics;
                Stage 1's Elo constants); the games-weighted Elo's scale and Stage 3's surface log-odds are recomputed
                here and compared with the stored ones
    format      as the plan reads it (best of five from the score, the source's record, or the Next Gen Finals; a
                match tiebreak from Stage 0's format); the matches where that reading uses the match's own score are
                counted separately (check 3 sizes it)
    A and B     every feature is built as side A's value minus side B's from the explicit identities of
                player_a_id and player_b_id, so an agreement with Stage 4 also confirms its orientation

Scale-up: the same two rating passes, run once over every match, against Stage 3's stored ratings (every match) and
Stage 4's games-weighted Elo and ratings features (every match in its table).

Writes, in data/studies/predictability_diagnostic/audit4/:
    recompute_matches.csv    one row per sampled match and feature: Stage 4's value, the audit's, the difference
    recompute.json           the summary

Run: ./python.sh src/eda/predictability_diagnostic/audit4_recompute.py   (about 10 minutes with 12 workers)
"""
from __future__ import annotations

import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import audit4_common as A  # noqa: E402

N_RANDOM = 100
EXTRAS = {"round robin": 6, "Finals knockout after a round robin": 4, "two events in one week": 8,
          "Grand Slam quarter-final onwards": 4, "qualifier's first main-draw match": 4}
TOL_ABS, TOL_REL = 2e-5, 2e-5          # Stage 4 stores features as float32
WORKERS = max(1, min(12, (os.cpu_count() or 2) - 2))
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# The sample

def sample(m: pd.DataFrame, p: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    ev = m["evaluation"].to_numpy() & m["year"].between(2013, 2026).to_numpy()
    # a player with two events in one week (both rows of the match carry the event and date)
    pr = pd.DataFrame({"pid": p["player_id"].to_numpy(), "day": np.repeat(m["day"].to_numpy(), 2),
                       "ev": np.repeat(m["ev"].to_numpy(), 2)})
    n_ev = pr.groupby(["pid", "day"])["ev"].transform("nunique").to_numpy().reshape(-1, 2).max(axis=1)
    rnd = m["round"].to_numpy()
    first_main = m.groupby("ev")["round_order"].transform(lambda s: s[s >= 10].min() if (s >= 10).any() else -1).to_numpy()
    entry = p["entry"].fillna("").to_numpy().reshape(-1, 2)
    kinds = {"round robin": ev & (rnd == "RR"),
             "Finals knockout after a round robin": ev & (m["level"].to_numpy() == "FIN") & np.isin(rnd, ["SF", "F"]),
             "two events in one week": ev & (n_ev >= 2),
             "Grand Slam quarter-final onwards": ev & (m["level"].to_numpy() == "GS") & ~m["qualifying"].to_numpy(bool)
             & np.isin(rnd, ["QF", "SF", "F"]),
             "qualifier's first main-draw match": ev & ~m["qualifying"].to_numpy(bool)
             & (m["round_order"].to_numpy() == first_main) & (entry == "Q").any(axis=1)}
    rows = []
    for tour in ("atp", "wta"):
        t = m["tour"].to_numpy() == tour
        for i in rng.choice(np.flatnonzero(ev & t), N_RANDOM, replace=False):
            rows.append({"match": int(i), "tour": tour, "kind": "random"})
        for kind, k in EXTRAS.items():
            pool = np.flatnonzero(kinds[kind] & t)
            for i in rng.choice(pool, min(k, len(pool)), replace=False):
                rows.append({"match": int(i), "tour": tour, "kind": kind})
    s = pd.DataFrame(rows).drop_duplicates("match")
    return s.reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# Per-tour arrays for the rating passes

def tour_arrays(m: pd.DataFrame, p: pd.DataFrame, tour: str, ctx: dict) -> tuple[dict, dict]:
    sel = np.flatnonzero(m["tour"].to_numpy() == tour)
    mt = m.iloc[sel]
    codes, _ = pd.factorize(np.concatenate([mt["player_a_id"].to_numpy(), mt["player_b_id"].to_numpy()]))
    a, b = codes[:len(sel)], codes[len(sel):]
    ar, br = 2 * sel, 2 * sel + 1
    status = mt["status"].to_numpy()
    played = np.isin(status, ["completed", "retired"])
    a_won = mt["a_won"].to_numpy(bool)
    # the games-weighted Elo's weight: the winner's share of the games over the tour's mean share (2010-2018)
    gn, gd = p["games_won_n"].to_numpy("float64")[ar], p["games_won_d"].to_numpy("float64")[ar]
    with np.errstate(invalid="ignore", divide="ignore"):
        ga = np.where(gd > 0, gn / gd, np.nan)
    share = np.where(a_won, ga, 1 - ga)
    yr = mt["year"].to_numpy()
    base = played & (yr >= 2010) & (yr <= 2018) & np.isfinite(share)
    scale = float(share[base].mean())
    wgt = np.where(np.isfinite(share), share / scale, 1.0)
    # Stage 3: matches that move ratings, their serve points, and each surface's log-odds average (2010-2018)
    na, wa = p["spw_d"].to_numpy("float64")[ar], p["spw_n"].to_numpy("float64")[ar]
    nb, wb = p["spw_d"].to_numpy("float64")[br], p["spw_n"].to_numpy("float64")[br]
    box = np.isfinite(na) & np.isfinite(wa) & np.isfinite(nb) & np.isfinite(wb) & (na > 0) & (nb > 0)
    upd3 = (status == "completed") & mt["has_box"].to_numpy(bool) & box
    na, wa, nb, wb = (np.where(upd3, v, 0.0) for v in (na, wa, nb, wb))
    surf = mt["surf"].to_numpy()
    ref = upd3 & (yr >= 2010) & (yr <= 2018)
    tot = (wa[ref] + wb[ref]).sum() / (na[ref] + nb[ref]).sum()
    mu_tab = {0: math.log(tot / (1 - tot))}
    for s in (1, 2, 3, 4):
        r = ref & (surf == s)
        if r.sum() >= 100:
            sh = (wa[r] + wb[r]).sum() / (na[r] + nb[r]).sum()
            mu_tab[s] = math.log(sh / (1 - sh))
        else:
            mu_tab[s] = mu_tab[0]
    mu = np.array([mu_tab[s] for s in surf])
    arr = {"sel": sel, "week": mt["day"].to_numpy(), "event": mt["ev"].to_numpy(), "rnd": mt["round_order"].to_numpy(),
           "a": a, "b": b, "a_won": a_won, "surf": surf, "upd": played, "wgt": wgt, "mu": mu, "upd3": upd3,
           "na": na, "wa": wa, "nb": nb, "wb": wb, "n_players": int(codes.max()) + 1}
    meta = {"games_scale": scale, "s3_mu": {str(k): v for k, v in mu_tab.items()}}
    return arr, meta


_W: dict = {}


def init_worker(payload: dict) -> None:
    for tour, arr in payload.items():
        d = {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in arr.items()}
        d["np_week"], d["np_event"], d["np_rnd"] = arr["week"], arr["event"], arr["rnd"]
        _W[tour] = d
    _W["ctx"] = payload["_ctx"] if "_ctx" in payload else None


def run_passes(D: dict, idx: list, ctx: dict, tour: str, blank: int | None = None) -> tuple[dict, dict]:
    upd, upd3 = D["upd"], D["upd3"]
    if blank is not None:                               # the target's own result is not given to the passes
        upd, upd3 = list(upd), list(upd3)
        upd[blank] = False
        upd3[blank] = False
    k = ctx["elo"][tour]
    e = A.elo_pass(idx, D["week"], D["event"], D["rnd"], D["a"], D["b"], D["a_won"], D["surf"], upd, D["wgt"],
                   k["k0"], k["offset"], k["shape"], D["n_players"])
    c = ctx["s3"][tour]
    s = A.s3_pass(idx, D["week"], D["event"], D["rnd"], D["a"], D["b"], D["mu"], upd3, D["na"], D["wa"], D["nb"],
                  D["wb"], D["n_players"], c["var_serve"], c["var_return"], c["drift"], c["start_serve"],
                  c.get("start_return", 0.0))
    return e, s


def replay(task: tuple) -> dict:
    """The two rating passes on the matches the target may see, and the target with its result blanked."""
    tour, t, ctx = task
    D = _W[tour]
    wk, evt, rd = D["np_week"][t], D["np_event"][t], D["np_rnd"][t]
    seen = np.flatnonzero((D["np_week"] < wk) | ((D["np_event"] == evt) & (D["np_rnd"] < rd)))
    assert t not in set(seen.tolist())
    idx = seen.tolist() + [t]
    e, s = run_passes(D, idx, ctx, tour, blank=t)
    return {"tour": tour, "t": t, "elo": e[t], "s3": s[t], "history_matches": len(seen)}


# ------------------------------------------------------------------------------------------------
# Features from the passes

def elo_feature(vals, w: float) -> float:
    ova, ovb, sva, svb = vals
    sva = ova if sva is None else sva
    svb = ovb if svb is None else svb
    ra, rb = (1 - w) * ova + w * sva, (1 - w) * ovb + w * svb
    return float(A.safe_logit(1.0 / (1.0 + 10.0 ** ((rb - ra) / 400.0))))


def match_format(m: pd.DataFrame, p: pd.DataFrame, i: int) -> dict:
    """The plan's reading of the format (and whether it rests on the match's own score)."""
    sets = p["sets_won_n"].to_numpy("float64")[[2 * i, 2 * i + 1]]
    w = np.nan if np.isnan(sets).all() else np.nanmax(sets)
    recorded = (m.at[i, "best_of"] == 5) or (m.at[i, "format"] == "short_sets")
    bo5 = bool((w >= 3) if np.isfinite(w) else False) or recorded
    rule = A.final_rule(m.at[i, "level"], m.at[i, "tournament_name"], int(m.at[i, "year"]), bool(m.at[i, "qualifying"]))
    mtb = m.at[i, "format"] == "match_tiebreak"
    return {"bo": 5 if bo5 else 3, "rule": rule, "mtb": bool(mtb), "bo5_from_own_score": bool(bo5 and not recorded),
            "mtb_from_own_score": bool(mtb and "[" in str(m.at[i, "score"]))}


# ------------------------------------------------------------------------------------------------
# History features, from an explicit list of the player's earlier rows

STATS_NEEDED = ("spw", "rpw", "tpw", "hold", "brk", "first_in", "first_won", "second_won", "rpw_first", "rpw_second")


def plain_arrays(m: pd.DataFrame, p: pd.DataFrame, ctx: dict) -> dict:
    """The columns the history features read, as plain arrays (match-level ones indexed by match, player-level ones
    by player row), and each row's tour average of each statistic on its own surface."""
    X = {k: m[k].to_numpy() for k in ("day", "tournament_id", "round_order", "status", "format", "surface", "surf",
                                      "year", "minutes", "tour")}
    X["minutes"] = m["minutes"].to_numpy("float64")
    for c in ["sets_won_d", "age"] + [f"{s}_{x}" for s in RATES_USED for x in ("n", "d")]:
        X[c] = p[c].to_numpy("float64")
    X["player_id"] = p["player_id"].to_numpy()
    surf_key = np.where(np.isin(X["surface"], A.SURFACES), X["surface"], "all")
    X["mu"] = {}
    for st in STATS_NEEDED:
        tab = {k[1:]: v for k, v in ctx["means"].items() if k[0] == st}
        X["mu"][st] = np.array([tab[(t, s)] for t, s in zip(X["tour"], surf_key)])
    return X


RATES_USED = ("spw", "rpw", "tpw", "hold", "brk", "first_in", "first_won", "second_won")


def player_history(X: dict, rows_of: dict, i: int, side: int) -> list:
    """The player rows of player ``side`` (0 = A, 1 = B) of match i that the time rule lets the match see, filtered
    one by one: an earlier tournament date, or the same tournament and date with a smaller round order."""
    pid = X["player_id"][2 * i + side]
    day_t, tid_t, rnd_t = X["day"][i], X["tournament_id"][i], X["round_order"][i]
    rows = []
    for r in rows_of[pid]:
        j = r // 2
        if j == i:
            continue
        dj = X["day"][j]
        if dj < day_t or (X["tournament_id"][j] == tid_t and dj == day_t and X["round_order"][j] < rnd_t):
            rows.append(int(r))
    return rows


def stat_xd(X: dict, r: int, stat: str) -> tuple[float, float, bool]:
    """A history row's count and units of a statistic, and whether it enters the history: box-score statistics from
    completed matches in the standard format; the return points against the first or second serve from the
    opponent's serve counts of the same match."""
    j = r // 2
    box = X["status"][j] == "completed" and X["format"][j] == "standard"
    if stat in ("rpw_first", "rpw_second"):
        src = "first_won" if stat == "rpw_first" else "second_won"
        o = r + 1 if r % 2 == 0 else r - 1
        n, d = X[f"{src}_n"][o], X[f"{src}_d"][o]
        ok = box and not math.isnan(n) and not math.isnan(d)
        return (d - n, d, True) if ok else (0.0, 0.0, False)
    n, d = X[f"{stat}_n"][r], X[f"{stat}_d"][r]
    ok = box and not math.isnan(n) and not math.isnan(d)
    return (n, d, True) if ok else (0.0, 0.0, False)


def forms(X: dict, ctx: dict, i: int, rows: list, stat: str) -> dict:
    """The 52-week and decayed shrunk forms of a statistic for one player of match i."""
    tour, day_t = X["tour"][i], X["day"][i]
    K = ctx["K"][(stat, tour)]
    mu_t = X["mu"][stat][i]
    s52x = s52d = decx = decd = card = 0.0
    for r in rows:
        x, d, ok = stat_xd(X, r, stat)
        if not ok:
            continue
        j = r // 2
        xc = x - d * X["mu"][stat][j]
        age = day_t - X["day"][j]
        card += d
        wgt = 2.0 ** (-age / (7.0 * A.HALF_LIFE))
        decx += xc * wgt
        decd += d * wgt
        if X["day"][j] >= day_t - A.WEEK52:
            s52x += xc
            s52d += d
    return {"52 weeks": A.shrunk(mu_t, s52x, s52d, K) if s52d > 0.5 else np.nan,
            "decayed": A.shrunk(mu_t, decx, decd, K) if card > 0 else np.nan}


def load_window(X: dict, i: int, rows: list, days: int, what: str) -> float:
    """log(1 + minutes or sets) over the played matches of this event's earlier rounds and of events starting up to
    ``days`` before it; missing if any of them lacks the count."""
    day_t = X["day"][i]
    tot = 0.0
    for r in rows:
        j = r // 2
        if X["status"][j] not in ("completed", "retired") or X["day"][j] < day_t - days:
            continue
        v = X["minutes"][j] if what == "minutes" else X["sets_won_d"][r]
        if math.isnan(v):
            return np.nan
        tot += float(v)
    return math.log1p(max(tot, 0.0))


def surface_first(X: dict, i: int, rows: list) -> float:
    if X["surf"][i] == 0:
        return np.nan
    n = sum(1 for r in rows if X["status"][r // 2] in ("completed", "retired")
            and X["year"][r // 2] == X["year"][i] and X["surf"][r // 2] == X["surf"][i])
    return 1.0 if n < 3 else 0.0


def history_features(X: dict, ctx: dict, rows_of: dict, i: int, fmt: dict) -> dict:
    H = [player_history(X, rows_of, i, s) for s in (0, 1)]
    out = {}
    for w, name in ((14, "sets_14d|single"), (14, "minutes_14d|single")):
        what = "sets" if name.startswith("sets") else "minutes"
        va, vb = (load_window(X, i, h, w, what) for h in H)
        out[name] = va - vb
    sa, sb = (surface_first(X, i, h) for h in H)
    out["surface_first|single"] = sa - sb
    ages = []
    for s in (0, 1):
        g = X["age"][2 * i + s]
        ages.append(float(g) - 25.0 if not math.isnan(g) and 14.0 <= g <= 50.0 else np.nan)
    out["age|single"], out["age|single|2"] = ages[0] - ages[1], ages[0] ** 2 - ages[1] ** 2
    F = [{st: forms(X, ctx, i, h, st) for st in STATS_NEEDED} for h in H]
    for form in ("52 weeks", "decayed"):
        v = [{st: F[s][st][form] for st in STATS_NEEDED} for s in (0, 1)]
        out[f"tpw|{form}"] = float(A.safe_logit(v[0]["tpw"]) - A.safe_logit(v[1]["tpw"]))
        mu = {st: X["mu"][st][i] for st in ("spw", "hold", "first_won", "second_won")}

        def pts(s, o):
            return float(A.combine(v[s]["spw"], v[o]["rpw"], mu["spw"]))

        def comp(s, o):
            fi = min(max(v[s]["first_in"], 0.0), 1.0)
            return float(fi * A.combine(v[s]["first_won"], v[o]["rpw_first"], mu["first_won"])
                         + (1 - fi) * A.combine(v[s]["second_won"], v[o]["rpw_second"], mu["second_won"]))

        def games(s, o):
            return A.serve_for_hold(float(A.combine(v[s]["hold"], v[o]["brk"], mu["hold"])))
        for cid, f_, need in (("mu_points", pts, ("spw", "rpw")), ("mu_components", comp, ("first_in", "first_won",
                              "second_won", "rpw_first", "rpw_second")), ("mu_games", games, ("hold", "brk"))):
            if all(np.isfinite(v[s][st]) for s in (0, 1) for st in need):
                pa, pb = f_(0, 1), f_(1, 0)
                out[f"{cid}|{form}"] = float(A.safe_logit(A.p_match(pa, pb, fmt["bo"], fmt["rule"], fmt["mtb"])))
            else:
                out[f"{cid}|{form}"] = np.nan
    return out


# ------------------------------------------------------------------------------------------------

def main() -> int:
    m, p = A.load_tables()
    ctx = A.constants()
    f = pd.read_parquet(A.OUT / "stage4_features.parquet")
    rank = pd.read_csv(A.OUT / "stage4_ranking.csv")
    log(f"tables loaded: {len(m):,} matches")
    top = {t: rank[rank["tour"].eq(t)].nsmallest(10, "rank_given_elo")[["id", "form", "rank_given_elo"]].to_dict("records")
           for t in ("atp", "wta")}
    cols = sorted({f"{r['id']}|{r['form']}" for t in top for r in top[t]})
    rng = np.random.default_rng(A.SEED)
    smp = sample(m, p, rng)
    log(f"sample: {len(smp)} matches ({smp['kind'].value_counts().to_dict()})")

    payload, meta = {}, {}
    for tour in ("atp", "wta"):
        payload[tour], meta[tour] = tour_arrays(m, p, tour, ctx)
    # the recomputed constants against the stored ones
    s3mu = {(r["tour"], r["surface"]): r["mu"] for r in ctx["s3_mu"]}
    const_check = {}
    for tour in ("atp", "wta"):
        const_check[tour] = {"games_scale_audit": meta[tour]["games_scale"],
                             "games_scale_stage4": ctx["elo_scale"][("elo_games", tour)],
                             "s3_mu_audit": meta[tour]["s3_mu"],
                             "s3_mu_stage3": {s: s3mu[(tour, s)] for s in ("all", "Hard", "Clay", "Grass", "Carpet")}}
    log(f"constants: {const_check}")

    # replays, one per sampled match, each on the history its match may see
    loc = {}
    for tour in ("atp", "wta"):
        g2l = pd.Series(np.arange(len(payload[tour]["sel"])), index=payload[tour]["sel"])
        for r in smp[smp["tour"].eq(tour)].itertuples():
            loc[r.match] = (tour, int(g2l[r.match]))
    tasks = [(tour, t, ctx) for tour, t in loc.values()]
    log(f"replaying {len(tasks)} histories with {WORKERS} workers")
    rep = {}
    with ProcessPoolExecutor(max_workers=WORKERS, initializer=init_worker, initargs=(payload,)) as ex:
        for k, res in enumerate(ex.map(replay, tasks, chunksize=1)):
            rep[(res["tour"], res["t"])] = res
            if (k + 1) % 50 == 0:
                log(f"  {k + 1} of {len(tasks)}")
    log("replays done")

    # history features and the comparison
    rows_of = {k: np.sort(v) for k, v in p.groupby("player_id").indices.items()}
    X = plain_arrays(m, p, ctx)
    fidx = pd.Series(np.arange(len(f)), index=f["match_id"].to_numpy())
    recs = []
    for r in smp.itertuples():
        i = r.match
        tour, t = loc[i]
        fmt = match_format(m, p, i)
        res = rep[(tour, t)]
        w = ctx["elo"][tour]["w"]
        mine = {"elo_games|single": elo_feature(res["elo"], w)}
        sa, sb, ra, rb = res["s3"]
        mu = payload[tour]["mu"][t]
        mine["rating_serve|single"] = sa - sb
        pa, pb = 1 / (1 + math.exp(-(mu + sa - rb))), 1 / (1 + math.exp(-(mu + sb - ra)))
        mine["rating_matchup|single"] = float(A.safe_logit(A.p_match(pa, pb, fmt["bo"], fmt["rule"], fmt["mtb"])))
        mine.update(history_features(X, ctx, rows_of, i, fmt))
        fr = fidx[m.at[i, "match_id"]]
        for c in cols + ["age|single|2"]:
            theirs = float(f.at[fr, c]) if c in f.columns else np.nan
            mv = mine.get(c, np.nan)
            both_nan = np.isnan(theirs) and np.isnan(mv)
            diff = abs(mv - theirs) if np.isfinite(mv) and np.isfinite(theirs) else np.nan
            agree = both_nan or (np.isfinite(diff) and diff <= TOL_ABS + TOL_REL * abs(theirs))
            recs.append({"match_id": m.at[i, "match_id"], "tour": tour, "kind": r.kind, "year": int(m.at[i, "year"]),
                         "level": m.at[i, "level"], "qualifying": bool(m.at[i, "qualifying"]), "round": m.at[i, "round"],
                         "feature": c, "stage4": theirs, "audit": mv, "abs_diff": diff, "agree": bool(agree),
                         "history_matches_replayed": res["history_matches"],
                         "bo5_from_own_score": fmt["bo5_from_own_score"], "mtb_from_own_score": fmt["mtb_from_own_score"]})
    R = pd.DataFrame(recs)
    A.AUDIT.mkdir(parents=True, exist_ok=True)
    R.to_csv(A.AUDIT / "recompute_matches.csv", index=False)
    log(f"wrote recompute_matches.csv: {len(R)} comparisons, {int((~R['agree']).sum())} disagreements")

    # scale-up: one full pass per tour against Stage 3's stored ratings and Stage 4's features
    s3 = pd.read_parquet(A.OUT / "stage3_ratings.parquet", columns=["match_id", "serve_a", "serve_b", "return_a",
                                                                    "return_b", "mu_logit"])
    s3 = s3.set_index("match_id").reindex(m["match_id"]).reset_index()
    init_worker(payload)
    full = {}
    for tour in ("atp", "wta"):
        D = _W[tour]
        idx = list(range(len(D["week"])))
        e, s = run_passes(D, idx, ctx, tour)
        sel = payload[tour]["sel"]
        S = np.array([s[k] for k in idx])
        stored = s3.iloc[sel][["serve_a", "serve_b", "return_a", "return_b"]].to_numpy("float64")
        mu_stored = s3.iloc[sel]["mu_logit"].to_numpy("float64")
        w = ctx["elo"][tour]["w"]
        elo_feat = np.array([elo_feature(e[k], w) for k in idx])
        gid = m["match_id"].to_numpy()[sel]
        fr = fidx.reindex(gid).to_numpy()
        inpool = ~np.isnan(fr)
        theirs_elo = f["elo_games|single"].to_numpy("float64")[fr[inpool].astype(int)]
        theirs_rs = f["rating_serve|single"].to_numpy("float64")[fr[inpool].astype(int)]
        full[tour] = {"matches": int(len(idx)),
                      "stage3_ratings_max_abs_diff": float(np.nanmax(np.abs(S - stored))),
                      "stage3_ratings_rows_beyond_1e-5": int((np.abs(S - stored) > 1e-5).any(axis=1).sum()),
                      "stage3_mu_max_abs_diff": float(np.abs(payload[tour]["mu"] - mu_stored).max()),
                      "pool_matches": int(inpool.sum()),
                      "elo_games_max_abs_diff": float(np.nanmax(np.abs(elo_feat[inpool] - theirs_elo))),
                      "elo_games_beyond_tol": int((np.abs(elo_feat[inpool] - theirs_elo) > TOL_ABS + TOL_REL * np.abs(theirs_elo)).sum()),
                      "rating_serve_max_abs_diff": float(np.nanmax(np.abs((S[inpool, 0] - S[inpool, 1]) - theirs_rs)))}
        log(f"full pass {tour}: {full[tour]}")

    summ = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "seed": A.SEED,
            "rows_checked": top, "features": cols + ["age|single|2"], "sample": smp["kind"].value_counts().to_dict(),
            "sample_by_tour": smp.groupby(["tour", "kind"]).size().reset_index().to_dict("records"),
            "tolerance": {"abs": TOL_ABS, "rel": TOL_REL},
            "comparisons": int(len(R)), "disagreements": int((~R["agree"]).sum()),
            "by_feature": R.groupby("feature").agg(n=("agree", "size"), agree=("agree", "sum"),
                                                   both_missing=("stage4", lambda s: int(s.isna().sum())),
                                                   max_abs_diff=("abs_diff", "max")).reset_index().to_dict("records"),
            "by_kind": R.groupby("kind").agg(n=("agree", "size"), agree=("agree", "sum")).reset_index().to_dict("records"),
            "matches_with_format_from_own_score": int(R.drop_duplicates("match_id")[["bo5_from_own_score", "mtb_from_own_score"]]
                                                      .any(axis=1).sum()),
            "replayed_history_matches": {"min": int(R["history_matches_replayed"].min()),
                                         "median": float(R.drop_duplicates("match_id")["history_matches_replayed"].median()),
                                         "max": int(R["history_matches_replayed"].max())},
            "constants": const_check, "full_pass": full, "seconds": round(time.time() - T0, 1)}
    A.save_json(summ, "recompute.json")
    log("wrote recompute.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
