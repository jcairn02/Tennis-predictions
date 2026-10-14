"""B-OVERREACT, the price over-reacts to salient recent results (round-2 family: signed sum, signs declared per
member, weight 0.5; TabPFN difference columns or nudge).

    I-025 conversion luck (-)  Lambda_A - Lambda_B; Lambda = sum_k 2^(-age_k / 91 days) e_k / (sum_k 2^(-age_k / 91) + 3) over
                           the player's earlier completed box-score matches (MEC-08's 13-week half-life and shrinkage 3),
                           e_k = y_k - sigmoid(beta_f (t_k - 1/2)), y_k the player's win, t_k his share of all points;
                           beta_f per tour and best-of, a no-intercept logistic fitted WALK-FORWARD for each target season
                           on completed matches (every level with box scores) with lf + 1 <= the season's earliest start
                           (the math audit's fix: never the target season's outcomes); probed (run this file)
    I-085 drifting favourite (+)  abs(r) sign(F), r = z - F, with r held (rulings MKT-R4: r 1[sign r != sign F] =
                           r/2 - abs(r) sign(F)/2 exactly, so the identifiable column is abs(r) sign F, sign +). F is the
                           fit-free Elo forecast c x (elo_overall + elo_surf_offset), c = SD(price)/SD(offset Elo) per tour
                           on 2014-2018 (SD-matching: no outcome). It replaces the no-odds TabPFN sibling, which exists only
                           from 2019 (38% / 32% of 2014-2021): one source for every season, no 2019 break, coverage 100%
    I-086 last-round narrative (-)  1[round >= QF] x Delta s (as written: an uncentred indicator, Delta s held), s = 1 - p_prev, the player's own de-vigged average closing
                           price in his previous main-draw match at this event (a win, or he would not be here). The
                           missingness rule (critique S11; the feasibility card's 43-45%): s = 0 when the player has no
                           previous main-draw match at this event (no narrative: a first match, or after a qualifying
                           run) or that match was a walkover; missing only when it was played without a price, flagged
    I-091 head-to-head (-)  raw x 1[n >= 3] (uncentred, as written; raw itself is not held, as the card sets), raw = (wins_A - wins_B)/(n + 1) over their earlier played meetings at every
                           level; the shrunk Elo residual of those meetings, sum(y - p_elo)/(n + 2) (k = 2, MEC-08 arm b's
                           pair shrinkage), held as a control

Each member divided by its RMS on 2014-2021, multiplied by its declared sign and summed (block tested +). Controls
(per member): I-025's named inputs (elo_games, elo_overall, adjperf_tpw_2w, points_52w); r (I-085); Delta s and the
missing-price indicator A - B (I-086, critique S11); the head-to-head Elo residual (I-091); the M-set (I-085's); Std.
eta-modulator controls: I-085's disagreement indicator, 1[round >= QF], the missing-price indicator, 1[n >= 3].
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.features import mkt_common as M  # noqa: E402
from src.eda.feature_interactions.features.f11_retirement import season_cutoffs  # noqa: E402
from src.eda.feature_interactions.panel import OLD  # noqa: E402

LUCK_HALF_LIFE, LUCK_SHRINK, H2H_K, MIN_ROWS = 91.0, 3.0, 2.0, 1000
OUT = C.OUT / "round2" / "market"


def luck_rows(H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(ok, y, t - 1/2) per row: completed matches with a points total, the player's win and points share."""
    n, d = H["tpw_n"].to_numpy(float), H["tpw_d"].to_numpy(float)
    ok = (H["status"].astype(str).to_numpy() == "completed") & H["played"].to_numpy(bool) & (d > 0) & np.isfinite(n)
    y = H["won"].astype(bool).to_numpy().astype(float)
    return ok, y, np.where(ok, n / np.where(d > 0, d, 1.0) - 0.5, 0.0)


def fit_beta(y: np.ndarray, u: np.ndarray) -> float:
    """No-intercept logistic slope of y on u (Newton; the relation is symmetric about u = 0)."""
    b = 40.0
    for _ in range(50):
        p = 1.0 / (1.0 + np.exp(-b * u))
        g = np.sum((y - p) * u)
        h = np.sum(p * (1 - p) * u * u)
        step = g / max(h, 1e-12)
        b += step
        if abs(step) < 1e-10:
            break
    return float(b)


def betas_for(H: pd.DataFrame, cut: float) -> dict:
    ok, y, u = luck_rows(H)
    train = ok & (H["lf"].to_numpy(float) + 1 <= cut)
    tour, bo = H["tour"].astype(str).to_numpy(), H["best_of"].to_numpy(float)
    out = {}
    for t in C.TOURS:
        for b in (3.0, 5.0):
            m = train & (tour == t) & (bo == b)
            out[(t, b)] = fit_beta(y[m], u[m]) if m.sum() >= MIN_ROWS else np.nan
        if not np.isfinite(out[(t, 5.0)]):
            out[(t, 5.0)] = out[(t, 3.0)]          # no women's best-of-five: the tour's best-of-three slope
    return out


def luck_by_season(H: pd.DataFrame, P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, dict]:
    ok, y, u = luck_rows(H)
    tour, bo = H["tour"].astype(str).to_numpy(), H["best_of"].to_numpy(float)
    season = P["season"].astype(int).to_numpy()
    la, lb, used = np.full(len(P), np.nan), np.full(len(P), np.nan), {}
    den = M.decayed(H, ok.astype(float), LUCK_HALF_LIFE) + LUCK_SHRINK
    for yv, cut in season_cutoffs(P).items():
        rows = season == yv
        if not rows.any():
            continue
        beta = betas_for(H, cut)
        used[int(yv)] = {f"{t}_bo{int(b)}": round(v, 3) for (t, b), v in beta.items()}
        five = bo == 5.0
        bk = np.select([(tour == 'atp') & five, tour == 'atp', (tour == 'wta') & five],
                       [beta[('atp', 5.0)], beta[('atp', 3.0)], beta[('wta', 5.0)]], beta[('wta', 3.0)])
        e = np.where(ok, y - 1.0 / (1.0 + np.exp(-bk * u)), 0.0)
        lam = M.decayed(H, e, LUCK_HALF_LIFE) / den
        a, b = M.at_model(H, P, lam)
        la[rows], lb[rows] = a[rows], b[rows]
    return la, lb, used


def surprise_rows(H: pd.DataFrame) -> np.ndarray:
    """Per row: 1 - the player's own de-vigged price in his previous main-draw match at this event; 0 without such a
    match (or after a walkover there); NaN when it was played without a price."""
    o = pd.read_parquet(OLD / "predictability_diagnostic" / "stage1_odds.parquet", columns=["match_id", "p_avg_a"])
    o["match_id"] = o["match_id"].astype(str)
    pa = H["match_id"].map(o.drop_duplicates("match_id").set_index("match_id")["p_avg_a"]).to_numpy(float)
    p_own = np.where(H["side"].to_numpy() == "A", pa, 1.0 - pa)
    main = ~H["qualifying"].astype(bool).to_numpy()
    tid = H["tournament_id"].astype(str).to_numpy()
    same = np.r_[False, (H["pc"].to_numpy()[1:] == H["pc"].to_numpy()[:-1]) & (tid[1:] == tid[:-1])]
    prev_main = M.shift_own(H, main.astype(float)) > 0.5
    prev_played = M.shift_own(H, H["played"].to_numpy(float)) > 0.5
    prev_p = M.shift_own(H, p_own)
    prev_won = M.shift_own(H, H["won"].astype(bool).to_numpy().astype(float)) > 0.5
    has_prev = same & prev_main & main & prev_won          # (a round-robin loss is no surprise win: 0)
    return np.where(has_prev & prev_played, 1.0 - prev_p, 0.0)


def h2h_rows(H: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per row, over the player's strictly earlier PLAYED meetings with this opponent: (n, wins, sum of y - p_elo)."""
    played = H["played"].to_numpy(bool)
    y = H["won"].astype(bool).to_numpy().astype(float)
    e = M.elo_rows(H)
    mid = H["match_id"].to_numpy()
    opp = pd.Series(e, index=pd.MultiIndex.from_arrays([mid, H["side"].map({"A": "B", "B": "A"}).to_numpy()]))
    own = pd.Series(e, index=pd.MultiIndex.from_arrays([mid, H["side"].to_numpy()]))
    e_opp = own[~own.index.duplicated()].reindex(opp.index).to_numpy(float)
    p_elo = 1.0 / (1.0 + np.exp(-M.LN10_400 * (e - e_opp)))
    res = np.where(played & np.isfinite(p_elo), y - p_elo, 0.0)
    keys = [H["pc"].to_numpy(), H["opponent_id"].astype(str).to_numpy()]
    out = []
    for v in (played.astype(float), np.where(played, y, 0.0), res):
        out.append(pd.Series(v).groupby(keys).cumsum().to_numpy() - v)
    return out[0], out[1], out[2]


def prepare_overreact(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = M.hist(L, P)
    la, lb, _ = M.cached("luck", (H, P), lambda: luck_by_season(H, P))
    out = {"luck_a": la, "luck_b": lb}
    out["sur_a"], out["sur_b"] = M.at_model(H, P, surprise_rows(H))
    n, w, r = h2h_rows(H)
    out["h2hn_a"], out["h2hn_b"] = M.at_model(H, P, n)
    out["h2hw_a"], out["h2hw_b"] = M.at_model(H, P, w)
    out["h2hres_a"], out["h2hres_b"] = M.at_model(H, P, r)
    return out


def drift(P: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(r, F, s): r = z - F, F = the fit-free Elo forecast (SD-matched on 2014-2018, MKT-R4), s = 1[sign r != sign F]."""
    z, F = M.zmkt(P), M.elo_forecast(P)
    r = z - F
    s = (np.sign(r) != np.sign(F)).astype(float)
    s[~(np.isfinite(r) & np.isfinite(F))] = np.nan
    return r, F, s


def combine_boverreact(P: pd.DataFrame) -> dict:
    m25 = M.num(P, "luck_a") - M.num(P, "luck_b")
    r, F, s85 = drift(P)
    m85 = np.abs(r) * np.sign(F)                       # r 1[sign r != sign F] = r/2 - |r| sign(F)/2: with r held, sign +
    sa, sb = M.pair(P, "sur")
    late = (M.num(P, "in_round") >= 15).astype(float)
    ds = sa - sb
    m86 = np.where(late > 0, ds, 0.0)                  # Delta s x 1[round >= QF]; missing only where late and unpriced
    n = M.num(P, "h2hn_a")
    raw = (M.num(P, "h2hw_a") - M.num(P, "h2hw_b")) / (n + 1.0)
    res = (M.num(P, "h2hres_a") - M.num(P, "h2hres_b")) / (2.0 * (n + H2H_K))
    n3 = (n >= 3).astype(float)
    m91 = raw * n3
    x = M.signed_sum([(m25, "-"), (m85, "+"), (m86, "-"), (m91, "-")], P, symmetric=False)
    Cs, names = M.std_controls(P, x, force=("elo_games", "elo_overall", "adjperf_tpw_2w", "points_52w"))
    ctrl, cn = M.stack([(r, "r = z - F"), (np.nan_to_num(ds), "Delta surprise"), (M.miss_diff(sa, sb), "price missing, A - B"),
                        (res, "head-to-head Elo residual")] + ([(Cs, names)] if names else []))
    miss = (~(np.isfinite(sa) & np.isfinite(sb))).astype(float)
    E, en = M.stack([(M.centre(s85, P), "I-085 disagreement"), (M.centre(late, P), "round >= QF"),
                     (M.centre(miss, P), "previous price missing"), (M.centre(n3, P), "n >= 3 meetings")])
    return {"x": x, "m_set": True, "controls": ctrl, "control_names": cn, "eta_mod_controls": E, "eta_mod_names": en,
            "members": {"I-025": m25, "I-085": m85, "I-086": m86, "I-091": m91},
            "tabpfn": {"luck_13w": (m25, "diff", None), "surprise_late": (m86, "diff", None),
                       "h2h_raw_n3": (m91, "diff", None)}}


HYPOTHESES = [
    {"hid": "B-OVERREACT", "master": "I-025+I-085+I-086+I-091", "kind": "W", "sign": "+", "weight": 0.5,
     "trait": "none", "deployment": "TabPFN diff columns or nudge", "anchor": "I", "prepare": prepare_overreact,
     "combine": combine_boverreact},
]


# ------------------------------------------------------------------------------------------------ diagnostics (__main__)

def split_half(H: pd.DataFrame) -> dict:
    """MEC-08's kill test, feature-only: does e carry over between split halves (r > 0.2 means skill, reframe)? Each
    player's completed box-score matches of 2010-2018 by own-order parity, beta_f fitted on the same rows."""
    ok, y, u = luck_rows(H)
    yr = pd.to_datetime(H["tournament_date"]).dt.year.to_numpy()
    m = ok & (yr <= M.TUNE[1])
    tour, bo = H["tour"].astype(str).to_numpy(), H["best_of"].to_numpy(float)
    beta = {(t, b): fit_beta(y[m & (tour == t) & (bo == b)], u[m & (tour == t) & (bo == b)])
            if (m & (tour == t) & (bo == b)).sum() >= MIN_ROWS else np.nan for t in C.TOURS for b in (3.0, 5.0)}
    for t in C.TOURS:
        if not np.isfinite(beta[(t, 5.0)]):
            beta[(t, 5.0)] = beta[(t, 3.0)]
    five = bo == 5.0
    bk = np.select([(tour == "atp") & five, tour == "atp", (tour == "wta") & five],
                   [beta[("atp", 5.0)], beta[("atp", 3.0)], beta[("wta", 5.0)]], beta[("wta", 3.0)])
    e = y - 1.0 / (1.0 + np.exp(-bk * u))
    d = pd.DataFrame({"p": H["pc"].to_numpy()[m], "e": e[m]})
    d["half"] = d.groupby("p").cumcount() % 2
    g = d.groupby(["p", "half"])["e"].agg(["mean", "size"]).unstack()
    g = g[(g[("size", 0)] >= 30) & (g[("size", 1)] >= 30)]
    return {"players": int(len(g)), "r_split_half": float(np.corrcoef(g[("mean", 0)], g[("mean", 1)])[0, 1]),
            "beta_2010_2018": {f"{t}_bo{int(b)}": round(v, 2) for (t, b), v in beta.items()}}


def probe(H: pd.DataFrame, P: pd.DataFrame, cuts=("2016-06-15", "2019-08-28", "2022-09-07"), atol=1e-9) -> dict:
    """No Lambda of a match that surely finished by the cut moves when every later result is reversed or removed."""
    from src.eda.feature_interactions.features.f11_retirement import reverse_after
    la, lb, _ = luck_by_season(H, P)
    lf = M.num(P, "lf")
    res = {}
    for cut in cuts:
        day = float((pd.Timestamp(cut) - pd.Timestamp("1970-01-01")).days)
        for remove in (False, True):
            M.clear_memo()
            H2 = reverse_after(H, day, remove)
            H2["pc"] = pd.factorize(H2["player_id"])[0]
            a2, b2, _ = luck_by_season(H2, P)
            chk = lf <= day
            later = ~chk & np.isfinite(la)
            res[f"{cut}|{'removed' if remove else 'reversed'}"] = {
                "checked": int(chk.sum()),
                "max_abs_change_earlier": float(max(np.nanmax(np.abs(a2[chk] - la[chk])), np.nanmax(np.abs(b2[chk] - lb[chk])))),
                "share_later_moved": None if remove else float(np.nanmean(np.abs(a2[later] - la[later]) > 1e-12))}
    res["pass"] = all(v["max_abs_change_earlier"] <= atol for v in res.values() if isinstance(v, dict))
    res["atol"] = atol
    return res


def main() -> int:
    import warnings
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=C.REPLICATION[-1]).drop(columns=["a_won"])
    H = M.hist(long_table(), P)
    _, _, used = luck_by_season(H, P)
    out = {"beta_f_by_target_season": used, "split_half": split_half(H)}
    C.log(f"split half {out['split_half']}")
    out["probe"] = probe(H, P)
    C.log(f"probe pass {out['probe']['pass']}")
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(OUT / "b_overreact.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
