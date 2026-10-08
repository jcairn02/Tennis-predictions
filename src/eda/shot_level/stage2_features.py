"""Stage 2, part 1: pre-match features from the shot-level statistics, for every match of the earlier studies' pool.

For each statistic of stage1_match_stats.parquet (src/eda/shot_level/stats.py) and each player, the player's earlier
matches are summed under the predictability diagnostic's time rule (common.asof_sums: earlier events, and earlier rounds
of the same event) in three memories, as the UFC study's Stage B did:

    dec2      every earlier match, weighted 2^(-age / 2 weeks): the two-week half-life of the men's box-score lead
    w52       the matches of the last 52 weeks (events starting up to 364 days before), unweighted
    career    every earlier match, unweighted

Each match's count is first centred on the tour's average on its surface (2010-2018), so a history played mostly on
clay is not mistaken for a style. A player's form is then the shrunk average excess, r = sum(n - d mu_surface) /
(sum d + K), with K the statistic's empirical-Bayes constant (between-player spread against within-player noise, from
player-seasons of 2010-2018, per tour; no result is read), and the player's value is mu_tour + r.

Three kinds of feature per statistic (every feature is A's value minus B's; shares on the log-odds scale, speeds in
km/h, the sequence excesses as they are):

    off       the player's own statistic
    def       what the player's opponents did against the player (for statistics where that is a skill of the
              player: how often opponents' serve-plus-one beat them, the winners they conceded, ...)
    adj       the player's statistic above what each opponent usually allowed: each earlier match's count is centred on
              d x (the opponent's def value as of that match, career memory) instead of the surface average

Two features combine statistics: the change in first-serve speed (dec2 minus w52 of spd1), and the long-rally edge where
long rallies are likely (A - B of rally9, and that difference times how far the two players' long_share is above the
tour's).

The pool is the ufc_ideas harness's (data/studies/predictability_diagnostic/stage4_features.parquet), read without its
result column for this build. A feature is missing for a match when either player has no earlier match carrying the
statistic in the memory.

Run:  ./python.sh src/eda/shot_level/stage2_features.py   (a few minutes)
Writes data/studies/shot_level/:
    stage2_features.parquet     the pool's columns (its result included, for the harness) plus every feature
    stage2_constants.json       surface and tour averages, the shrinkage constants K, the feature catalogue
    stage2_leak_probe.json      the black-box probe: features rebuilt with what was played from a cut redrawn
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic.stage3_traits import lookback_sums, sums_before  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import stats as T  # noqa: E402

HALF_LIFE = 2.0
WEEK52 = 364
PRIOR_YEARS = range(2010, 2019)
EPS = 1e-4
DEF_STATS = ["srv_quick", "ret_quick", "ret_inplay", "winner_rate", "error_rate", "w_ratio", "net_rate", "net_won",
             "deep_ret", "consolidate", "break_back", "serve_set"]
ADJ_STATS = ["srv_quick", "ret_quick", "rally5", "rally9", "ret_inplay", "winner_rate", "error_rate", "ue_share",
             "w_ratio", "net_won", "deep_ret", "consolidate", "break_back", "serve_set"]
# zero-sum within a match: the opponent's value is one minus the player's, so the allowed norm is one minus own
ZERO_SUM = {"rally5", "rally9", "ue_share"}
SURFACES = ("Hard", "Clay", "Grass", "Carpet")


def scale(stat: str, v: np.ndarray) -> np.ndarray:
    if stat in T.LEVEL or stat in T.EXCESS:
        return v
    return logit(np.clip(v, EPS, 1 - EPS))


def load_rows() -> pd.DataFrame:
    """Every Stage 0 player-match row (both sides of every match, every level, 2010-2026) in the chronological order, with
    the shot-level counts where they exist (0 elsewhere) and the opponent's row index."""
    mp = C.load_match_players(["match_id", "player_id", "opponent_id", "side"], match_columns=["tour", "year", "surface"])
    st = pd.read_parquet(S.OUT / "stage1_match_stats.parquet")
    cols = [f"{s}_{k}" for s in T.ALL_STATS + ["spd1_sq", "spd2_sq"] for k in ("n", "d")]
    mp = mp.merge(st[["match_id", "side"] + cols], on=["match_id", "side"], how="left")
    for c in cols:
        mp[c] = mp[c].fillna(0.0).astype("float64")
    mp["day"] = mp["tournament_date"].to_numpy().astype("datetime64[D]").astype("int64")
    mp["pcode"] = pd.factorize(mp["player_id"])[0].astype("int64")
    pos = pd.Series(np.arange(len(mp)), index=pd.MultiIndex.from_arrays([mp["match_id"], mp["side"]]))
    other = mp["side"].map({"A": "B", "B": "A"})
    mp["opp_row"] = pos.reindex(pd.MultiIndex.from_arrays([mp["match_id"], other])).to_numpy()
    mp["surface"] = mp["surface"].where(mp["surface"].isin(SURFACES), "Hard")
    return mp


def averages(rows: pd.DataFrame) -> dict:
    """mu per statistic, tour and surface (and per tour), pooled over 2010-2018, falling back to all years where a
    statistic starts later."""
    out = {}
    for s in T.ALL_STATS:
        n, d = rows[f"{s}_n"], rows[f"{s}_d"]
        early = rows["year"].isin(list(PRIOR_YEARS)) & (d > 0)
        use = early if (rows.loc[early, f"{s}_d"].sum() > 0) else (d > 0)
        for t in C.TOURS:
            m = use & rows["tour"].eq(t)
            if rows.loc[m, f"{s}_d"].sum() == 0:
                m = (d > 0) & rows["tour"].eq(t)
            tot = rows.loc[m, f"{s}_n"].sum() / max(rows.loc[m, f"{s}_d"].sum(), 1e-9)
            out[(s, t, "all")] = float(tot) if s not in T.EXCESS else 0.0
            for sf in SURFACES:
                ms = m & rows["surface"].eq(sf)
                dsum = rows.loc[ms, f"{s}_d"].sum()
                out[(s, t, sf)] = (float(rows.loc[ms, f"{s}_n"].sum() / dsum) if dsum >= 1000 else out[(s, t, "all")]) \
                    if s not in T.EXCESS else 0.0
    return out


def eb_constant(n: np.ndarray, d: np.ndarray, kind: str, sq: np.ndarray | None = None) -> float:
    """K from player-seasons (n, d): the within-player noise per unit over the between-player variance of true rates
    (method of moments). Shares: binomial noise mu (1 - mu); excesses: 1/4 per unit (a bound); levels (speeds): the
    pooled within-player-season variance of single serves, from the sums of squares."""
    keep = d > 0
    n, d = n[keep], d[keep]
    if len(d) < 30:
        return float("inf")
    x = n / d
    mu = n.sum() / d.sum()
    if kind == "level":
        within = float((sq[keep] - n * n / d).sum() / max((d - 1).clip(min=0).sum(), 1))
    elif kind == "excess":
        within = 0.25
    else:
        within = float(mu * (1 - mu))
    num = float((d * (x - mu) ** 2).sum()) - (len(d) - 1) * within
    den = float(d.sum() - (d * d).sum() / d.sum())
    tau2 = num / den if den > 0 else 0.0
    return float(within / tau2) if tau2 > 0 else float("inf")


def kind_of(s: str) -> str:
    return "level" if s in T.LEVEL else "excess" if s in T.EXCESS else "share"


def split_half_constant(rows: pd.DataFrame, s: str, t: str, min_matches: int = 30) -> tuple[float, dict]:
    """K for a statistic whose per-point noise is not binomial (the sequence excesses are measured against the player's
    own rate in the same match, which shrinks them): from the split-half reliability. For players with min_matches or
    more matches carrying the statistic (2010-2018; all years if fewer than 100 such players), the correlation r between
    the rates of their odd- and even-numbered matches; a half's mean denominator D; then K = D (1 - r) / r, the K at
    which a history of D units counts r against the average (no result is read). r <= 0 gives an infinite K."""
    info = {}
    for years in (PRIOR_YEARS, range(2010, 2027)):
        m = rows["tour"].eq(t) & rows["year"].isin(list(years)) & (rows[f"{s}_d"] > 0)
        g = rows[m][["pcode", f"{s}_n", f"{s}_d"]].copy()
        g["k"] = g.groupby("pcode").cumcount() % 2
        cnt = g.groupby("pcode").size()
        a = g.groupby(["pcode", "k"])[[f"{s}_n", f"{s}_d"]].sum().unstack()
        a = a[(cnt.reindex(a.index) >= min_matches).to_numpy()]
        a = a[(a[(f"{s}_d", 0)] > 0) & (a[(f"{s}_d", 1)] > 0)]
        if len(a) >= 100 or years.stop == 2027:
            break
    if len(a) < 30:
        return float("inf"), {"players": int(len(a))}
    r0 = (a[(f"{s}_n", 0)] / a[(f"{s}_d", 0)]).to_numpy()
    r1 = (a[(f"{s}_n", 1)] / a[(f"{s}_d", 1)]).to_numpy()
    r = float(np.corrcoef(r0, r1)[0, 1])
    D = float(np.concatenate([a[(f"{s}_d", 0)].to_numpy(), a[(f"{s}_d", 1)].to_numpy()]).mean())
    info = {"players": int(len(a)), "split_half_r": r, "half_units": D, "years": [years.start, years.stop - 1]}
    return (float(D * (1 - r) / r) if r > 0 else float("inf")), info


SPLIT_HALF_INFO: dict = {}


def constants(rows: pd.DataFrame, opp: np.ndarray) -> dict:
    """K per (statistic, tour, off / def) from player-seasons of 2010-2018 (all years where a statistic starts later);
    for the sequence excesses, from the split-half reliability (split_half_constant)."""
    out = {}
    for s in T.ALL_STATS:
        for t in C.TOURS:
            if s in T.EXCESS:
                k, info = split_half_constant(rows, s, t)
                out[(s, t, "off")] = out[(s, t, "def")] = k
                SPLIT_HALF_INFO[f"{s}|{t}"] = info
                continue
            for side in ("off", "def"):
                m = rows["tour"].eq(t).to_numpy()
                early = m & rows["year"].isin(list(PRIOR_YEARS)).to_numpy()
                n = rows[f"{s}_n"].to_numpy() if side == "off" else rows[f"{s}_n"].to_numpy()[opp]
                d = rows[f"{s}_d"].to_numpy() if side == "off" else rows[f"{s}_d"].to_numpy()[opp]
                sq = None
                if s in ("spd1", "spd2"):
                    sq = rows[f"{s}_sq_n"].to_numpy() if side == "off" else rows[f"{s}_sq_n"].to_numpy()[opp]
                use = early if d[early].sum() > 0 else m
                g = pd.DataFrame({"p": rows["pcode"].to_numpy()[use], "y": rows["year"].to_numpy()[use],
                                  "n": n[use], "d": d[use], "sq": sq[use] if sq is not None else 0.0})
                g = g[g["d"] > 0].groupby(["p", "y"])[["n", "d", "sq"]].sum()
                out[(s, t, side)] = eb_constant(g["n"].to_numpy(), g["d"].to_numpy(), kind_of(s), g["sq"].to_numpy())
    return out


def mu_rows(rows: pd.DataFrame, mu: dict, s: str, level: str = "surface") -> np.ndarray:
    t, sf = rows["tour"].to_numpy(), rows["surface"].to_numpy()
    out = np.zeros(len(rows))
    for tt in C.TOURS:
        for x in SURFACES:
            m = (t == tt) & (sf == x)
            out[m] = mu[(s, tt, x if level == "surface" else "all")]
    return out


def forms(rows: pd.DataFrame, V: np.ndarray) -> dict:
    """As-of sums of the columns of V in the three memories."""
    career, dec = lookback_sums(rows, V, half_lives=(HALF_LIFE,))
    before = sums_before(rows["pcode"].to_numpy(), rows["day"].to_numpy(), V, rows["pcode"].to_numpy(),
                         rows["day"].to_numpy() - WEEK52)
    return {"career": career, "dec2": dec[HALF_LIFE], "w52": career - before}


def build(rows: pd.DataFrame, mu: dict, K: dict, stats=None) -> tuple[dict, dict]:
    """Per player-match row, every feature value (the player's side, before A - B): {name: array}, and the denominators
    {name: array} that say whether it exists."""
    stats = stats or T.ALL_STATS
    opp = rows["opp_row"].to_numpy()
    has_opp = ~np.isnan(opp.astype("float64"))
    opp = np.where(has_opp, opp, 0).astype("int64")
    tour = rows["tour"].to_numpy()
    vals, dens = {}, {}

    def kmap(s, side):
        return np.where(tour == "atp", K[(s, "atp", side)], K[(s, "wta", side)])

    for s in stats:
        n, d = rows[f"{s}_n"].to_numpy(), rows[f"{s}_d"].to_numpy()
        mus = mu_rows(rows, mu, s, "surface")
        mut = mu_rows(rows, mu, s, "all")
        c = n - d * mus
        cols = [c, d]
        if s in DEF_STATS:
            no, do = np.where(has_opp, n[opp], 0.0), np.where(has_opp, d[opp], 0.0)
            cols += [no - do * mus, do]
        F = forms(rows, np.column_stack(cols))
        k_off = kmap(s, "off")
        for f, arr in F.items():
            r = arr[:, 0] / (arr[:, 1] + k_off)
            vals[f"{s}|off|{f}"] = scale(s, mut + r)
            dens[f"{s}|off|{f}"] = arr[:, 1]
        if s in DEF_STATS:
            k_def = kmap(s, "def")
            for f, arr in F.items():
                r = arr[:, 2] / (arr[:, 3] + k_def)
                vals[f"{s}|def|{f}"] = scale(s, mut + r)
                dens[f"{s}|def|{f}"] = arr[:, 3]
            # the opponent's allowed norm as of this match (career memory), for the adjusted form
            r_def_car = F["career"][:, 2] / (F["career"][:, 3] + k_def)
            vals[f"_{s}|allowed"] = mut + r_def_car
        if s in ADJ_STATS:
            if s in ZERO_SUM:
                r_off_car = F["career"][:, 0] / (F["career"][:, 1] + k_off)
                allowed_o = np.where(has_opp, 1.0 - (mut[opp] + r_off_car[opp]), mut)
            else:
                allowed_o = np.where(has_opp, vals[f"_{s}|allowed"][opp], mut)
            # the opponent's norm, re-centred on this match's surface
            exp = np.clip(allowed_o + (mus - mut), EPS, 1 - EPS)
            FA = forms(rows, np.column_stack([n - d * exp, d]))
            for f in ("dec2", "w52"):
                r = FA[f][:, 0] / (FA[f][:, 1] + k_off)
                vals[f"{s}|adj|{f}"] = scale(s, mut + r)
                dens[f"{s}|adj|{f}"] = FA[f][:, 1]
    # speed change: recent against the player's own year
    if "spd1" in stats:
        vals["spd1_change|off|dec2-w52"] = vals["spd1|off|dec2"] - vals["spd1|off|w52"]
        dens["spd1_change|off|dec2-w52"] = np.minimum(dens["spd1|off|dec2"], dens["spd1|off|w52"])
    return vals, dens


def to_pool(rows: pd.DataFrame, vals: dict, dens: dict, pool: pd.DataFrame) -> pd.DataFrame:
    """A - B per pool match for every feature; missing where either player has no history in the memory. Also the
    two-input long-rally interaction."""
    pos = pd.Series(np.arange(len(rows)), index=pd.MultiIndex.from_arrays([rows["match_id"], rows["side"]]))
    ia = pos.reindex(pd.MultiIndex.from_arrays([pool["match_id"], np.full(len(pool), "A")])).to_numpy()
    ib = pos.reindex(pd.MultiIndex.from_arrays([pool["match_id"], np.full(len(pool), "B")])).to_numpy()
    assert not (np.isnan(ia.astype(float)).any() or np.isnan(ib.astype(float)).any())
    ia, ib = ia.astype(int), ib.astype(int)
    out = {}
    for name, v in vals.items():
        if name.startswith("_"):
            continue
        dn = dens[name]
        ok = (dn[ia] > 0) & (dn[ib] > 0)
        out[name] = np.where(ok, v[ia] - v[ib], np.nan).astype("float32")
    # the long-rally edge where long rallies are likely: rally9 (A - B) and its product with the expected long share
    if "rally9|off|w52" in out and "long_share|off|w52" in vals:
        ls = vals["long_share|off|w52"]
        mu_ls = float(np.nanmean(ls[dens["long_share|off|w52"] > 0]))
        exp_long = (ls[ia] + ls[ib]) / 2 - mu_ls
        okl = (dens["long_share|off|w52"][ia] > 0) & (dens["long_share|off|w52"][ib] > 0)
        out["rally_edge|x_long|w52"] = np.where(okl, out["rally9|off|w52"] * exp_long, np.nan).astype("float32")
    return pd.DataFrame(out, index=pool.index)


def catalog(cols: list[str]) -> list[dict]:
    words = {"off": "the player's own", "def": "what opponents did against the player:", "adj": "opponent-adjusted"}
    mem = {"dec2": "two-week half-life", "w52": "last 52 weeks", "career": "career", "dec2-w52": "two-week minus 52-week"}
    out = []
    for c in cols:
        s, kind, f = c.split("|")
        out.append({"id": c, "statistic": s, "family": T.FAMILY_OF.get(s, "rally" if s.startswith("rally") else "speed"),
                    "kind": kind, "memory": f, "description": f"{words.get(kind, kind)} {s}, {mem.get(f, f)}"})
    return out


def probe(rows: pd.DataFrame, mu: dict, K: dict, stats: list[str], n_cuts: int = 4) -> dict:
    """Black-box leak probe: from a cut in the chronological order, every later match's statistics are redrawn; no feature
    value of a match before the cut may change (the earlier studies' probe). A leaky control (the match's own counts in
    its history) must change."""
    rng = np.random.default_rng(20261002)
    base, _ = build(rows, mu, K, stats)
    orders = np.sort(rows["order"].unique())
    cuts = rng.choice(orders[int(len(orders) * 0.8):], size=n_cuts, replace=False)
    ords = rows["order"].to_numpy()
    s0 = stats[0]

    def leaky(r: pd.DataFrame) -> np.ndarray:
        """A deliberately leaky control: the career form with the match's own counts added."""
        n, d = r[f"{s0}_n"].to_numpy(), r[f"{s0}_d"].to_numpy()
        mus = mu_rows(r, mu, s0, "surface")
        F = forms(r, np.column_stack([n - d * mus, d]))
        return (F["career"][:, 0] + n - d * mus) / (F["career"][:, 1] + d + K[(s0, "atp", "off")])

    base_leaky = leaky(rows)
    changed_before = changed_at = leaky_at = 0
    for c in cuts:
        pert = rows.copy()
        late = ords >= c
        for s in stats:
            for k in ("n", "d"):
                col = f"{s}_{k}"
                pert.loc[late, col] = rng.integers(0, 50, int(late.sum())).astype("float64")
            pert.loc[late, f"{s}_n"] = np.minimum(pert.loc[late, f"{s}_n"], pert.loc[late, f"{s}_d"])
        got, _ = build(pert, mu, K, stats)
        for name in base:
            if name.startswith("_"):
                continue
            a, b = base[name], got[name]
            diff = ~np.isclose(a, b, equal_nan=True, atol=1e-9)
            changed_before += int((diff & (ords < c)).sum())
            changed_at += int((diff & (ords == c)).sum())
        lk = ~np.isclose(base_leaky, leaky(pert), equal_nan=True, atol=1e-9)
        leaky_at += int((lk & (ords == c)).sum())
    return {"cuts": int(len(cuts)), "stats": stats, "changed_before_cut": changed_before, "changed_at_cut": changed_at,
            "leaky_control_changed_at_cut": leaky_at}


def main() -> int:
    S.log("rows and counts")
    rows = load_rows()
    opp = np.where(np.isnan(rows["opp_row"].to_numpy(dtype=float)), 0, rows["opp_row"]).astype(int)
    S.log(f"  {len(rows)} player-match rows; {int((rows[[f'{s}_d' for s in T.ALL_STATS]].sum(axis=1) > 0).sum())} with a shot-level count")
    mu = averages(rows)
    K = constants(rows, opp)
    S.log("  averages and constants set; building features")
    vals, dens = build(rows, mu, K)
    from src.eda.ufc_ideas import common as U
    pool = pd.read_parquet(U.STAGE4_FEATURES, columns=U.POOL_COLS)
    pool["era"] = pool["era"].astype(object).fillna("").astype(str)
    feats = to_pool(rows, vals, dens, pool)
    frame = pd.concat([pool, feats], axis=1)
    frame.to_parquet(S.OUT / "stage2_features.parquet", index=False)
    cols = list(feats.columns)
    S.log(f"wrote stage2_features.parquet ({len(frame)} matches, {len(cols)} features)")
    cov = {}
    mkt = frame["evaluation"].astype(bool) & frame["p_mkt"].notna()
    for c in cols:
        ex = frame[c].notna()
        cov[c] = {t: {"evaluation": int((ex & frame["evaluation"].astype(bool) & frame["tour"].eq(t)).sum()),
                      "market": int((ex & mkt & frame["tour"].eq(t)).sum())} for t in C.TOURS}
    S.log("leak probe")
    pr = probe(rows, mu, K, ["srv_quick", "winner_rate", "spd1", "consolidate", "net_won", "rally5"])
    (S.OUT / "stage2_leak_probe.json").write_text(json.dumps(pr, indent=1), encoding="utf-8")
    S.log(f"  probe: {pr}")
    (S.OUT / "stage2_constants.json").write_text(json.dumps({
        "half_life_weeks": HALF_LIFE, "window_days": WEEK52, "prior_years": [PRIOR_YEARS.start, PRIOR_YEARS.stop - 1],
        "mu": {"|".join(k): v for k, v in mu.items()}, "K": {"|".join(k): (v if np.isfinite(v) else None) for k, v in K.items()},
        "split_half": SPLIT_HALF_INFO, "catalog": catalog(cols), "coverage": cov}, indent=1), encoding="utf-8")
    for c in cols[:200]:
        print(f"{c:36s} atp market {cov[c]['atp']['market']:6d}  wta market {cov[c]['wta']['market']:6d}")
    print({"|".join(k): (round(v, 1) if np.isfinite(v) else None) for k, v in K.items() if k[2] == "off"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
