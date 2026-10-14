"""How the tournament levels blend into each other, and what that does to the data. Descriptive; no model fitted.

On the model frame's snapshot (the 30 Sep 2026 Stage 0, common.SOURCES), seasons 2013-2024, completed and retired
matches (walkovers and defaults left out):

    ladder         each level's players by ranking at the match: quantiles, and the better and worse player's median
    band_mix       for each rank band, the share of its matches played at each level
    moves          a player's next event after an event of each tier (MT main tour, Q tour/Slam qualifying, CH
                   Challenger/WTA 125 main draw and qualifying, ITF, TEAM), by the rank band at the first event
    overlap        the share of a tier's matches in which a player also played another tier in the previous 365 days
    history        what each pool match's feature history is made of: each player's matches in the previous 365 days
                   by tier (all, and those with a box score), the share below the main tour, and the "home tier" (the
                   tier with most of them). Written per match to history.parquet for score.py
    level_shift    the same players in the same season at two tiers (main tour against Challenger, main tour against
                   qualifying): their serve and return rates at each, paired
    elo_levels     overall Elo (Stage 1's rating, every level, one K schedule) at each level: log loss against a coin,
                   calibration slope, how often the higher-rated player won
    elo_climbers   Elo's calibration for players arriving from other tiers: logistic of the result on Elo's log-odds
                   (offset) plus beta x (A's share of last year's matches below the main tour - B's), at main-tour and
                   at Challenger matches; and the mean surprise of the lower-home player in mixed matchups
    coverage       box-score share by tour, level and era (Stage 0), and the point- and shot-level share by level and
                   year from the data map's coverage cells (data held, not results; 2025-2026 included)

Writes data/studies/event_levels/blend/*.csv, blend.json and history.parquet.
Run: ./python.sh src/eda/event_levels/blend.py    (about two minutes)
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.event_levels import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as SS  # noqa: E402  (cluster_se)
from src.eda.surface_elo_pieces import common as EC  # noqa: E402  (L10)

OUT = C.OUT / "blend"
FIRST, LAST = C.TRAIN_FROM, C.LAST_SEASON
PLAYED = ("completed", "retired")
TIER_RANK = {"MT": 0, "Q": 1, "CH": 2, "ITF": 3, "TEAM": 4}          # ties in the home tier go to the higher tier
RATES = ("spw", "rpw", "tpw", "hold", "brk", "ace", "df", "first_in", "first_won", "second_won", "bp_saved")
WINDOW_DAYS = 365


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    m = pd.read_parquet(C.SOURCES["stage0_matches"][0],
                        columns=["match_id", "tour", "year", "map_level", "tournament_id", "tournament_name",
                                 "tournament_date", "round_order", "status", "a_won", "player_a_id", "player_b_id",
                                 "has_box", "order", "surface"])
    m["tier"] = m["map_level"].map(C.TIER_OF)
    m["date"] = pd.to_datetime(m["tournament_date"])
    rate_cols = [f"{r}_{x}" for r in RATES for x in ("n", "d")]
    p = pd.read_parquet(C.SOURCES["stage0_players"][0],
                        columns=["match_id", "player_id", "opponent_id", "side", "won", "rank", "entry",
                                 "has_box"] + rate_cols)
    p = p.merge(m[["match_id", "tour", "year", "map_level", "tier", "date", "order", "status", "tournament_id"]],
                on="match_id", how="left", validate="many_to_one")
    return m, p


def window(df: pd.DataFrame, lo: int = FIRST, hi: int = LAST) -> pd.DataFrame:
    return df[df["year"].between(lo, hi) & df["status"].isin(PLAYED)]


# ------------------------------------------------------------------------------------------------
# Who plays where

def ladder(m: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    pw = window(p)
    rows = []
    for (tour, lv), g in pw.groupby(["tour", "map_level"]):
        r = g["rank"].to_numpy(dtype="float64")
        ok = np.isfinite(r)
        q = np.quantile(r[ok], [0.1, 0.25, 0.5, 0.75, 0.9]) if ok.any() else [np.nan] * 5
        pair = g.pivot_table(index="match_id", columns="side", values="rank", aggfunc="first")
        better = np.nanmin(pair.to_numpy(dtype="float64"), axis=1)
        worse = np.nanmax(pair.to_numpy(dtype="float64"), axis=1)
        rows.append({"tour": tour, "level": lv, "matches": int(g["match_id"].nunique()),
                     "players": int(g["player_id"].nunique()), "ranked_share": float(ok.mean()),
                     "p10": q[0], "p25": q[1], "median": q[2], "p75": q[3], "p90": q[4],
                     "median_better": float(np.nanmedian(better)), "median_worse": float(np.nanmedian(worse))})
    out = pd.DataFrame(rows)
    out["level"] = pd.Categorical(out["level"], C.LEVELS, ordered=True)
    return out.sort_values(["tour", "level"]).reset_index(drop=True)


def band_mix(p: pd.DataFrame) -> pd.DataFrame:
    pw = window(p).copy()
    pw["band"] = C.band_of(pw["rank"].to_numpy())
    t = pw.groupby(["tour", "band", "map_level"]).size().rename("n").reset_index()
    t["share"] = t["n"] / t.groupby(["tour", "band"])["n"].transform("sum")
    wide = t.pivot_table(index=["tour", "band"], columns="map_level", values="share", fill_value=0.0)
    wide = wide[[lv for lv in C.LEVELS if lv in wide.columns]]
    wide["player_matches"] = t.groupby(["tour", "band"])["n"].sum()
    wide = wide.reset_index()
    wide["band"] = pd.Categorical(wide["band"], C.BAND_ORDER, ordered=True)
    return wide.sort_values(["tour", "band"]).reset_index(drop=True)


def player_events(p: pd.DataFrame) -> pd.DataFrame:
    """One row per player and event (tournament id + date): the event's tier for the player (MT if any main-draw
    match, else its own tier), the rank at the event, in date order."""
    pw = window(p)
    pw = pw.assign(tr=pw["tier"].map(TIER_RANK))
    ev = (pw.groupby(["tour", "player_id", "tournament_id", "date"])
          .agg(tr=("tr", "min"), rank=("rank", "min"), year=("year", "first")).reset_index())
    ev["tier"] = ev["tr"].map({v: k for k, v in TIER_RANK.items()})
    return ev.sort_values(["tour", "player_id", "date", "tr"]).reset_index(drop=True)


def moves(p: pd.DataFrame) -> pd.DataFrame:
    ev = player_events(p)
    nxt = ev.groupby(["tour", "player_id"])["tier"].shift(-1)
    gap = (ev.groupby(["tour", "player_id"])["date"].shift(-1) - ev["date"]).dt.days
    ev = ev.assign(next_tier=nxt, gap=gap)
    ev = ev[ev["next_tier"].notna() & (ev["gap"] <= 60)]               # the next event within two months
    ev["band"] = C.band_of(ev["rank"].to_numpy())
    rows = []
    for keys, g in ev.groupby(["tour", "tier", "band"]):
        n = len(g)
        rec = dict(zip(("tour", "tier", "band"), keys), events=n)
        for t in C.TIERS:
            rec[f"next_{t}"] = float((g["next_tier"] == t).mean())
        rows.append(rec)
    for keys, g in ev.groupby(["tour", "tier"]):
        rec = dict(zip(("tour", "tier"), keys), band="all", events=len(g))
        for t in C.TIERS:
            rec[f"next_{t}"] = float((g["next_tier"] == t).mean())
        rows.append(rec)
    out = pd.DataFrame(rows)
    out["band"] = pd.Categorical(out["band"], C.BAND_ORDER + ["all"], ordered=True)
    return out.sort_values(["tour", "tier", "band"]).reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# What a match's history is made of

POOL = C.MAIN + ("CH", "TQ", "GSQ", "CHQ")


def history(m: pd.DataFrame, p: pd.DataFrame, years: tuple[int, int] = (FIRST, LAST), levels=POOL,
            match_ids=None) -> pd.DataFrame:
    """For every pool match of 2013-2024 (main tour, qualifying, Challenger), each player's matches in the previous
    365 days (strictly earlier in Stage 0's order, tournament date within 365 days) by tier, all and with a box score.
    Every level's history counts, ITF and team events included, as the features' histories do. years, levels and
    match_ids choose other query matches (universe_columns.py: the feature universe's store, 2013-2026); the history
    itself is always every played match of the snapshot."""
    hist = p[p["status"].isin(PLAYED)][["tour", "player_id", "order", "date", "tier", "has_box", "won"]].copy()
    hist = hist.sort_values(["tour", "player_id", "order"]).reset_index(drop=True)
    hist["key"] = hist["tour"] + "|" + hist["player_id"]
    code, uniq = pd.factorize(hist["key"], sort=False)                # increasing: rows are grouped by player
    if not (np.diff(code) >= 0).all():
        raise RuntimeError("history rows are not grouped by player")
    days = (hist["date"] - pd.Timestamp("1990-01-01")).dt.days.to_numpy()
    if not (np.diff(days)[np.diff(code) == 0] >= 0).all():
        raise RuntimeError("Stage 0's order does not follow the tournament date within a player")
    composite = code.astype(np.int64) * 100_000 + days
    cum = {}
    for t in C.TIERS:
        is_t = (hist["tier"] == t).to_numpy()
        cum[t] = np.cumsum(is_t)
        cum[f"{t}_box"] = np.cumsum(is_t & hist["has_box"].to_numpy(bool))
        cum[f"{t}_won"] = np.cumsum(is_t & hist["won"].to_numpy(bool))
    q = window(p, *years)
    q = q[q["map_level"].isin(levels)]
    if match_ids is not None:
        q = q[q["match_id"].isin(set(match_ids))]
    q = q[["match_id", "side", "tour", "player_id", "order", "date", "map_level", "rank"]].copy()
    q["key"] = q["tour"] + "|" + q["player_id"]
    # the query row's own position in hist (same player, same match order)
    pos = pd.Series(np.arange(len(hist)), index=pd.MultiIndex.from_arrays([hist["key"], hist["order"]]))
    idx = pos.reindex(pd.MultiIndex.from_arrays([q["key"], q["order"]])).to_numpy()
    if np.isnan(idx).any():
        raise RuntimeError("a pool player row is missing from the history table")
    idx = idx.astype(np.int64)
    # the window's first row: the player's first row dated on or after the cutoff (never past the match itself)
    cutoff = (q["date"] - pd.Timedelta(days=WINDOW_DAYS) - pd.Timestamp("1990-01-01")).dt.days.to_numpy()
    lo = np.searchsorted(composite, code[idx].astype(np.int64) * 100_000 + cutoff, side="left")
    lo = np.minimum(lo, idx)

    def before(c: np.ndarray, i: np.ndarray) -> np.ndarray:          # rows [0, i) of the global cumulative count
        return np.where(i > 0, c[np.maximum(i - 1, 0)], 0)

    out = q[["match_id", "side", "tour", "player_id", "map_level", "rank"]].reset_index(drop=True)
    for t in C.TIERS:
        for suffix in ("", "_box", "_won"):
            c = cum[f"{t}{suffix}"]
            out[f"n_{t}{suffix}"] = (before(c, idx) - before(c, lo)).astype(int)
    out["n_all"] = out[[f"n_{t}" for t in C.TIERS]].sum(axis=1)
    out["n_box"] = out[[f"n_{t}_box" for t in C.TIERS]].sum(axis=1)
    out["n_won"] = out[[f"n_{t}_won" for t in C.TIERS]].sum(axis=1)
    out["win_share"] = np.where(out["n_all"] > 0, out["n_won"] / out["n_all"].clip(lower=1), np.nan)
    below = out["n_Q"] + out["n_CH"] + out["n_ITF"]
    out["low_share"] = np.where(out["n_all"] > 0, below / out["n_all"].clip(lower=1), np.nan)
    out["low_share_box"] = np.where(out["n_box"] > 0, (out["n_Q_box"] + out["n_CH_box"] + out["n_ITF_box"]) /
                                    out["n_box"].clip(lower=1), np.nan)
    counts = out[[f"n_{t}" for t in C.TIERS]].to_numpy()
    home = np.array(C.TIERS)[np.argmax(counts, axis=1)]               # argmax takes the first: the higher tier on ties
    out["home"] = np.where(out["n_all"] > 0, home, "none")
    return out


def history_spot_check(p: pd.DataFrame, h: pd.DataFrame, n: int = 300) -> dict:
    """Recount n random history rows by brute force: the player's played matches strictly earlier in Stage 0's order
    with a tournament date within the window, by tier."""
    played = p[p["status"].isin(PLAYED)]
    order_of = window(p).set_index(["match_id", "side"])["order"]
    rng = np.random.default_rng(7)
    bad = 0
    for i in rng.choice(len(h), size=min(n, len(h)), replace=False):
        r = h.iloc[i]
        o = order_of.loc[(r["match_id"], r["side"])]
        d = played.loc[(played["match_id"] == r["match_id"]) & (played["side"] == r["side"]), "date"].iloc[0]
        g = played[(played["tour"] == r["tour"]) & (played["player_id"] == r["player_id"]) & (played["order"] < o)
                   & (played["date"] >= d - pd.Timedelta(days=WINDOW_DAYS))]
        for t in C.TIERS:
            if int((g["tier"] == t).sum()) != int(r[f"n_{t}"]) or \
                    int(((g["tier"] == t) & g["has_box"].astype(bool)).sum()) != int(r[f"n_{t}_box"]) or \
                    int(((g["tier"] == t) & g["won"].astype(bool)).sum()) != int(r[f"n_{t}_won"]):
                bad += 1
                break
    return {"rows_checked": int(min(n, len(h))), "rows_wrong": bad, "passed": bad == 0}


def history_summary(h: pd.DataFrame) -> pd.DataFrame:
    h = h.copy()
    h["band"] = C.band_of(h["rank"].to_numpy())
    rows = []
    for by in (["tour", "map_level"], ["tour", "band"]):
        for keys, g in h.groupby(by):
            tot, box = g["n_all"].sum(), g["n_box"].sum()
            rec = {"by": by[1], "tour": keys[0], "group": keys[1], "player_rows": len(g),
                   "matches_per_player_year": float(g["n_all"].mean()),
                   "box_per_player_year": float(g["n_box"].mean()),
                   "median_low_share": float(np.nanmedian(g["low_share"])),
                   "share_mostly_lower": float((g["low_share"] > 0.5).mean())}
            for t in C.TIERS:
                rec[f"share_{t}"] = float(g[f"n_{t}"].sum() / tot) if tot else np.nan
                rec[f"box_share_{t}"] = float(g[f"n_{t}_box"].sum() / box) if box else np.nan
            for t in C.TIERS + ("none",):
                rec[f"home_{t}"] = float((g["home"] == t).mean())
            rows.append(rec)
    return pd.DataFrame(rows)


def overlap(h: pd.DataFrame) -> pd.DataFrame:
    """Per tour and match level: the share of matches in which at least one player played at each tier in the
    previous 365 days, and in which the players' home tiers differ."""
    a = h[h["side"] == "A"].set_index("match_id")
    b = h[h["side"] == "B"].set_index("match_id").reindex(a.index)
    rows = []
    for (tour, lv), g in a.groupby(["tour", "map_level"]):
        gb = b.loc[g.index]
        rec = {"tour": tour, "level": lv, "matches": len(g),
               "home_differs": float((g["home"] != gb["home"]).mean())}
        for t in C.TIERS:
            rec[f"any_{t}"] = float(((g[f"n_{t}"] > 0) | (gb[f"n_{t}"] > 0)).mean())
        rows.append(rec)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# The same players at two tiers

def level_shift(p: pd.DataFrame, min_box: int = 3) -> pd.DataFrame:
    pw = window(p)
    pw = pw[pw["has_box"].astype(bool)]
    tier2 = np.where(pw["map_level"].isin(C.MAIN), "MT", np.where(pw["map_level"] == "CH", "CH",
                     np.where(pw["map_level"].isin(["TQ", "GSQ"]), "Q", "other")))
    pw = pw.assign(t2=tier2)
    pw = pw[pw["t2"] != "other"]
    agg = {f"{r}_{x}": "sum" for r in RATES for x in ("n", "d")}
    agg.update({"won": "mean", "match_id": "count"})
    g = pw.groupby(["tour", "player_id", "year", "t2"]).agg(agg).rename(columns={"match_id": "box_matches"})
    opp_rank = pw.merge(p[["match_id", "player_id", "rank"]].rename(columns={"player_id": "opponent_id",
                                                                             "rank": "opp_rank"}),
                        on=["match_id", "opponent_id"], how="left")
    g["opp_rank_median"] = opp_rank.groupby(["tour", "player_id", "year", "t2"])["opp_rank"].median()
    g = g.reset_index()
    rows = []
    for lower in ("CH", "Q"):
        a = g[g["t2"] == "MT"].set_index(["tour", "player_id", "year"])
        b = g[g["t2"] == lower].set_index(["tour", "player_id", "year"])
        both = a.index.intersection(b.index)
        a, b = a.loc[both], b.loc[both]
        ok = (a["box_matches"] >= min_box) & (b["box_matches"] >= min_box)
        a, b = a[ok], b[ok]
        for tour in C.TOURS:
            sel = a.index.get_level_values("tour") == tour
            if sel.sum() < 30:
                continue
            aa, bb = a[sel], b[sel]
            players = aa.index.get_level_values("player_id").to_numpy()
            for stat in RATES + ("won", "opp_rank_median"):
                if stat in RATES:
                    va = (aa[f"{stat}_n"] / aa[f"{stat}_d"]).to_numpy(dtype="float64")
                    vb = (bb[f"{stat}_n"] / bb[f"{stat}_d"]).to_numpy(dtype="float64")
                else:
                    va, vb = aa[stat].to_numpy(dtype="float64"), bb[stat].to_numpy(dtype="float64")
                d = vb - va
                okd = np.isfinite(d)
                se, _ = SS.cluster_se(d[okd], players[okd])
                rows.append({"tour": tour, "pair": f"{lower} - MT", "stat": stat, "player_seasons": int(okd.sum()),
                             "players": int(len(np.unique(players[okd]))), "mean_MT": float(np.nanmean(va[okd])),
                             "mean_lower": float(np.nanmean(vb[okd])), "diff": float(d[okd].mean()), "se": se})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# Elo across levels

def elo_frame(m: pd.DataFrame) -> pd.DataFrame:
    pc = pd.read_parquet(C.SOURCES["pieces"][0], columns=["match_id", "R_a", "R_b"])
    e = window(m)[["match_id", "tour", "year", "map_level", "tier", "a_won", "date"]].merge(
        pc, on="match_id", how="left", validate="one_to_one")
    e["elo_logit"] = EC.L10 * (e["R_a"] - e["R_b"])
    e["y"] = e["a_won"].astype(float)
    e["block"] = C.TW.SC.blocks(e["date"].to_numpy(), 28)
    return e[np.isfinite(e["elo_logit"])]


def elo_levels(e: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (tour, lv), g in e.groupby(["tour", "map_level"]):
        x, y = g["elo_logit"].to_numpy(), g["y"].to_numpy()
        beta, se = C.fit_logistic(x[:, None], y)
        p = expit(x)
        pc = expit(beta[0] * x)
        fav = x != 0
        rows.append({"tour": tour, "level": lv, "matches": len(g), "ll_coin": float(np.log(2)),
                     "ll_elo": float(C.ll(p, y).mean()), "ll_elo_calibrated_in_sample": float(C.ll(pc, y).mean()),
                     "slope": float(beta[0]), "slope_se": float(se[0]),
                     "favourite_won": float(((x[fav] > 0) == (y[fav] == 1)).mean()),
                     "sd_elo_logit": float(np.std(x))})
    out = pd.DataFrame(rows)
    out["level"] = pd.Categorical(out["level"], C.LEVELS, ordered=True)
    return out.sort_values(["tour", "level"]).reset_index(drop=True)


def logistic_cluster(Z: np.ndarray, y: np.ndarray, clusters: np.ndarray, offset: np.ndarray | None = None):
    """Logistic regression without an intercept (side A is random), optional offset; (beta, cluster-sandwich SE with
    the G / (G - 1) factor)."""
    Z = np.asarray(Z, float)
    off = np.zeros(len(y)) if offset is None else np.asarray(offset, float)
    beta = np.zeros(Z.shape[1])
    for _ in range(100):
        p = expit(off + Z @ beta)
        H = (Z.T * (p * (1 - p))) @ Z + 1e-10 * np.eye(Z.shape[1])
        step = np.linalg.solve(H, Z.T @ (y - p))
        big = np.abs(step).max()
        if big > 4:
            step *= 4 / big
        beta += step
        if big < 1e-12:
            break
    p = expit(off + Z @ beta)
    bread = np.linalg.inv((Z.T * (p * (1 - p))) @ Z)
    labels, ix = np.unique(clusters, return_inverse=True)
    G = len(labels)
    U = np.zeros((G, Z.shape[1]))
    np.add.at(U, ix, Z * (y - p)[:, None])
    V = bread @ (G / (G - 1) * U.T @ U) @ bread
    return beta, np.sqrt(np.diag(V))


def climber_fit(x: np.ndarray, z: np.ndarray, y: np.ndarray, clusters: np.ndarray) -> dict:
    """logit P = a x + beta z: the rating's own slope at this level fitted jointly, so beta is the history effect
    beyond the level's over- or under-confidence. beta > 0: the player with more lower-level history wins more than
    the rating says."""
    b, se = logistic_cluster(np.column_stack([x, z]), y, clusters)
    return {"slope": float(b[0]), "beta": float(b[1]), "se": float(se[1]), "lo": float(b[1] - 1.96 * se[1]),
            "hi": float(b[1] + 1.96 * se[1]), "rows": int(len(y))}


def pair_history(h: pd.DataFrame) -> pd.DataFrame:
    a = h[h["side"] == "A"].set_index("match_id")
    b = h[h["side"] == "B"].set_index("match_id").reindex(a.index)
    out = pd.DataFrame({"low_a": a["low_share"], "low_b": b["low_share"], "home_a": a["home"], "home_b": b["home"],
                        "n_a": a["n_all"], "n_b": b["n_all"]}, index=a.index)
    return out


MATCHUPS = {"main tour": [("Q", "MT"), ("CH", "MT"), ("ITF", "MT")],
            "tour qualifying": [("CH", "MT"), ("ITF", "MT"), ("ITF", "CH")],
            "Challenger": [("ITF", "CH"), ("Q", "CH"), ("MT", "CH")]}


def elo_climbers(e: pd.DataFrame, h: pd.DataFrame) -> pd.DataFrame:
    """At each level: (1) beta of A's minus B's share of last year's matches below the main tour, beside the rating's
    own slope there; (2) in mixed matchups (the players' home tiers differ), the mean surprise of the first-named
    home tier's player against Elo calibrated at this level (one slope per level and tour, in-sample: a diagnostic)."""
    ph = pair_history(h)
    j = e.set_index("match_id").join(ph, how="inner")
    j = j[np.isfinite(j["low_a"]) & np.isfinite(j["low_b"])]
    rows = []
    for where, levels in (("main tour", C.MAIN), ("GS", ("GS",)), ("T1000", ("T1000",)), ("T500", ("T500",)),
                          ("T250", ("T250",)), ("tour qualifying", ("TQ", "GSQ")), ("Challenger", ("CH",))):
        for tour in C.TOURS:
            g = j[j["map_level"].isin(levels) & (j["tour"] == tour)]
            if len(g) < 300:
                continue
            x, y, cl = g["elo_logit"].to_numpy(), g["y"].to_numpy(), g["block"].to_numpy()
            # per-level slopes inside a pooled group (the main tour pools five levels)
            lv = g["map_level"].to_numpy()
            X = np.column_stack([np.where(lv == v, x, 0.0) for v in np.unique(lv)])
            z = (g["low_a"] - g["low_b"]).to_numpy()
            b, se = logistic_cluster(np.column_stack([X, z]), y, cl)
            rows.append({"test": "low_share_slope", "where": where, "tour": tour, "beta": float(b[-1]),
                         "se": float(se[-1]), "lo": float(b[-1] - 1.96 * se[-1]), "hi": float(b[-1] + 1.96 * se[-1]),
                         "rows": int(len(y)), "slopes": {str(v): float(s) for v, s in zip(np.unique(lv), b[:-1])}})
            bs, _ = logistic_cluster(X, y, cl)
            pa = expit(X @ bs)                                        # Elo calibrated at this level (in-sample)
            for low, up in MATCHUPS.get(where, MATCHUPS["main tour"] if where in C.MAIN else []):
                ma = ((g["home_a"] == low) & (g["home_b"] == up)).to_numpy()
                mb = ((g["home_b"] == low) & (g["home_a"] == up)).to_numpy()
                if ma.sum() + mb.sum() < 100:
                    continue
                yl = np.r_[y[ma], 1 - y[mb]]
                pl = np.r_[pa[ma], 1 - pa[mb]]
                d = yl - pl
                s, _ = SS.cluster_se(d, np.r_[cl[ma], cl[mb]])
                rows.append({"test": f"{low}-home vs {up}-home", "where": where, "tour": tour, "rows": int(len(d)),
                             "won": float(yl.mean()), "expected": float(pl.mean()), "surprise": float(d.mean()),
                             "se": s, "lo": float(d.mean() - 1.96 * s), "hi": float(d.mean() + 1.96 * s)})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# Data held by level

def coverage(m: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    mm = m[m["status"].isin(PLAYED)].copy()
    mm["era"] = pd.cut(mm["year"], [2009, 2012, 2018, 2024, 2026], labels=["2010-12", "2013-18", "2019-24", "2025-26"])
    box = mm.groupby(["tour", "map_level", "era"], observed=True)["has_box"].agg(["mean", "size"]).reset_index()
    box = box.rename(columns={"mean": "box_share", "size": "matches"})
    cells = pd.read_csv(C.COVERAGE_CELLS)
    cells["era"] = np.where(cells["year"] <= 2024, "2018-24", "2025-26")
    g = cells.groupby(["tour", "level", "era"])[["matches", "best_point", "best_shot", "best_stats",
                                                 "best_result"]].sum().reset_index()
    for c in ("best_point", "best_shot", "best_stats", "best_result"):
        g[f"{c}_share"] = g[c] / g["matches"]
    g["point_or_shot_share"] = (g["best_point"] + g["best_shot"]) / g["matches"]
    return box, g


def main() -> int:
    C.check_sources()
    OUT.mkdir(parents=True, exist_ok=True)
    m, p = load()
    C.log(f"Stage 0 snapshot: {len(m):,} matches, {len(p):,} player rows")
    tables = {}
    tables["ladder"] = ladder(m, p)
    tables["band_mix"] = band_mix(p)
    tables["moves"] = moves(p)
    C.log("ladder, band mix and moves done")
    h = history(m, p)
    spot = history_spot_check(p, h)
    if not spot["passed"]:
        raise RuntimeError(f"history counts fail the brute-force recount: {spot}")
    C.log(f"history spot check: {spot}")
    h.to_parquet(C.OUT / "history.parquet", index=False)
    tables["history"] = history_summary(h)
    tables["overlap"] = overlap(h)
    C.log(f"history: {len(h):,} player rows")
    tables["level_shift"] = level_shift(p)
    e = elo_frame(m)
    tables["elo_levels"] = elo_levels(e)
    tables["elo_climbers"] = elo_climbers(e, h)
    box, cells = coverage(m)
    tables["coverage_box"] = box
    tables["coverage_cells"] = cells
    for name, t in tables.items():
        t.to_csv(OUT / f"{name}.csv", index=False)
    C.write_json(C.OUT / "blend.json", {
        "what": "how the levels blend (descriptive); seasons 2013-2024, completed and retired matches, the model "
                "frame's snapshot (30 Sep 2026 Stage 0)",
        "sources": C.check_sources(), "tables": {k: f"data/studies/event_levels/blend/{k}.csv" for k in tables},
        "coverage_cells": {"path": str(C.COVERAGE_CELLS.relative_to(C.ROOT)),
                           "sha256": C.sha256_file(C.COVERAGE_CELLS)},       # the data map's, not pinned: record it
        "history_rows": int(len(h)), "window_days": WINDOW_DAYS, "history_spot_check": spot})
    with pd.option_context("display.width", 250, "display.max_columns", 40, "display.max_rows", 200):
        print(tables["ladder"].round(1).to_string(index=False))
        print(tables["elo_levels"].round(4).to_string(index=False))
        print(tables["elo_climbers"].round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
