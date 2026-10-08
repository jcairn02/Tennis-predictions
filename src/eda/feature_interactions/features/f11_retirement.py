"""I-042, retirement hazard x price (MAT-W2 + MKT-20 + BOD-12, merged; math audit family 09).

The label is "the player who advanced", so with in-match retirement hazards h_A, h_B and a played-out probability p,
P(A advances) = (1 - h_A - h_B) p + h_B and the log-odds correction is exactly
    tau = h_B / p - h_A / (1 - p) = -Dh (1 + cosh z) - Sh sinh z          (antisymmetric; sign +)
with p = sigmoid(eta), eta the base's log-odds (the batch's x_of_eta hook evaluates it per base: the current best's
forecast, or the price). Controls (round-2 family, rulings MAT-R1a): the M-set and Std only; no Dh (with Dh free only
a third of tau's value remains) and no Sh * eta (the Sh sinh z part is the hypothesis).

Per-player hazards come from each player's own strictly earlier matches at every level (safe by construction) and, for
the parts pooled over players (the tour rate r_bar, MAT-W2's two modifiers, BOD-12's logistic), from walk-forward fits:
season Y reads only matches with lf + 1 <= the earliest start of any season-Y panel match. Estimators (one primary,
chosen on the retirement label of 2013-2018 model matches, out of sample, before M1; the others are sensitivities):
    a  MKT-20   (retirements in the last 730 days + k r_bar) / (played matches in them + k)
    b  MAT-W2   the same counting walkovers given, times walk-forward rate ratios for a retirement or walkover given in
                the last 30 days and for a layoff over 42 days, rescaled to the retirement rate
    c  BOD-12   a walk-forward logistic model (L2, C = 1) of "retires in this match" on main-tour main-draw rows: the
                logit of the 52-week shrunk rate (k = 20), a 28-day decayed retirement/walkover count (tau 14 days), age,
                age^2, Fat, the log load ratio (minutes, last 7 days vs a quarter of the last 28, + 90 min each), log(1 +
                days since the previous match), best of five, and the month as sin/cos
Weight 1 (the rulings' addendum: 2 -> 1, because 89% of tau is spanned by the 58 plus the M-set, so the precheck's
premise that all of tau is identifiable fails). Run `./python.sh src/eda/feature_interactions/features/f11_retirement.py`
for the estimator comparison, the hazard-spread precheck and the probe; results in data/studies/feature_interactions/round2/market/i042.json.
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

PRIMARY = ("a", 160.0)         # chosen on 2013-2018 (run this file): lowest pooled out-of-sample log loss
K_GRID = (5.0, 10.0, 20.0, 40.0, 80.0, 160.0, 320.0)   # extended once: the first grid chose its edge (80)
AGE_FILL = 26.0                 # a missing age (rare) is set to this constant, never to a median over all rows
W24, W52, REC_DAYS, REC_TAU, LAYOFF, LOAD_C = 730.0, 364.0, 28.0, 14.0, 42.0, 90.0
OUT = C.OUT / "round2" / "market"
ATOL = 1e-9                    # the match-timing probe's tolerance (floating-point sums over a cut table)


def row_features(H: pd.DataFrame) -> pd.DataFrame:
    """Per row of the long table, from the player's strictly earlier rows only (plus the row's own pre-match facts:
    age, best of, month, days since the previous match)."""
    def make():
        won = H["won"].astype(bool).to_numpy()
        played = H["played"].to_numpy(bool)
        ret = (H["status"].astype(str).to_numpy() == "retired") & ~won
        wo_given = H["walkover"].to_numpy(bool) & ~won
        gave = (ret | wo_given).astype(float)
        R = pd.DataFrame(index=H.index)
        R["ret24"], R["n24"] = M.window_sum(H, ret.astype(float), W24)[0], M.window_sum(H, played.astype(float), W24)[0]
        R["wo24"] = M.window_sum(H, wo_given.astype(float), W24)[0]
        R["ret52"], R["n52"] = M.window_sum(H, ret.astype(float), W52)[0], M.window_sum(H, played.astype(float), W52)[0]
        R["rec28"] = M.decayed_lag(H, gave, REC_TAU, REC_DAYS)
        R["rec30"] = (M.decayed_lag(H, gave, 1e9, 30.0) > 0).astype(float)
        gap = H["rest_days"].to_numpy(float)
        R["layoff"] = (np.nan_to_num(gap, nan=0.0) > LAYOFF).astype(float)
        R["log_gap"] = np.log1p(np.clip(np.nan_to_num(gap, nan=0.0), 0, 3650))
        f, _ = M.fat(H)
        R["fat"] = f
        mins, _ = M.minutes_filled(H)
        m7, _ = M.window_sum(H, np.nan_to_num(mins), 7.0)
        m28, _ = M.window_sum(H, np.nan_to_num(mins), 28.0)
        R["log_load"] = np.log((m7 + LOAD_C) / (m28 / 4.0 + LOAD_C))
        age = pd.to_numeric(H["age"], errors="coerce").to_numpy(float)
        R["age"] = np.where(np.isfinite(age), age, AGE_FILL)
        R["bo5"] = (H["best_of"].to_numpy(float) == 5).astype(float)
        mon = pd.to_datetime(H["tournament_date"]).dt.month.to_numpy(float)
        R["msin"], R["mcos"] = np.sin(2 * np.pi * mon / 12), np.cos(2 * np.pi * mon / 12)
        R["label"] = ret.astype(float)                      # this row's own retirement: a training label only
        R["gave"], R["played"] = gave, played.astype(float)
        R["main"] = (H["level"].isin(M.MAIN_LEVELS).to_numpy() & ~H["qualifying"].astype(bool).to_numpy()
                     & played).astype(float)
        R["lf"], R["es"] = H["lf"].to_numpy(float), H["es"].to_numpy(float)
        R["tour"] = H["tour"].astype(str).to_numpy()
        return R
    return M.cached("i042_rows", (H,), make)


def season_cutoffs(P: pd.DataFrame) -> dict[int, float]:
    """For each panel season, the earliest start (es) of its matches: a fit for that season reads only matches with
    lf + 1 <= this day."""
    es = M.num(P, "es")
    s = P["season"].astype(int).to_numpy()
    return {int(y): float(np.nanmin(es[s == y])) for y in np.unique(s)}


def _logit(p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p) - np.log1p(-p)


C_FEATS = ("lrate52", "rec28", "age", "age2", "fat", "log_load", "log_gap", "bo5", "msin", "mcos")


def _design(R: pd.DataFrame, idx: np.ndarray, rbar: dict) -> np.ndarray:
    tour = R["tour"].to_numpy()[idx]
    rb = np.where(tour == "atp", rbar["atp"], rbar["wta"])
    lrate = _logit((R["ret52"].to_numpy()[idx] + 20.0 * rb) / (R["n52"].to_numpy()[idx] + 20.0))
    age = R["age"].to_numpy()[idx]
    cols = {"lrate52": lrate, "rec28": R["rec28"].to_numpy()[idx], "age": age, "age2": (age - 27.0) ** 2,
            "fat": R["fat"].to_numpy()[idx], "log_load": R["log_load"].to_numpy()[idx],
            "log_gap": R["log_gap"].to_numpy()[idx], "bo5": R["bo5"].to_numpy()[idx],
            "msin": R["msin"].to_numpy()[idx], "mcos": R["mcos"].to_numpy()[idx]}
    return np.nan_to_num(np.column_stack([cols[c] for c in C_FEATS]))


def hazards_by_season(H: pd.DataFrame, P: pd.DataFrame, estimators: list[tuple[str, float]]) -> dict:
    """{(est, k): (h_A, h_B)} aligned to P, each season from a fit on strictly earlier matches (the match clock)."""
    from sklearn.linear_model import LogisticRegression
    R = row_features(H)
    pa, pb = M.model_pos(H, P)
    season = P["season"].astype(int).to_numpy()
    lf, label, played = R["lf"].to_numpy(), R["label"].to_numpy(), R["played"].to_numpy()
    gave, main, tour = R["gave"].to_numpy(), R["main"].to_numpy(), R["tour"].to_numpy()
    ret24, n24, wo24 = R["ret24"].to_numpy(), R["n24"].to_numpy(), R["wo24"].to_numpy()
    out = {e: (np.full(len(P), np.nan), np.full(len(P), np.nan)) for e in estimators}
    for y, cut in season_cutoffs(P).items():
        train = lf + 1 <= cut
        rows = season == y
        if not rows.any() or train.sum() < 1000:
            continue
        rbar, rbar_rw, ratios = {}, {}, {}
        for t in C.TOURS:
            m = train & (tour == t)
            rbar[t] = label[m & (played > 0)].mean()
            rbar_rw[t] = gave[m].mean()
            mp = m & (played > 0)
            ratios[t] = {c: label[mp & (R[c].to_numpy() > 0)].mean() / label[mp & (R[c].to_numpy() == 0)].mean()
                         for c in ("rec30", "layoff")}
        model = None
        for e in estimators:
            if e[0] == "c" and model is None:
                tr = np.flatnonzero(train & (main > 0))
                Xtr = _design(R, tr, rbar)
                mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-12
                model = (LogisticRegression(C=1.0, max_iter=500).fit((Xtr - mu) / sd, label[tr]), mu, sd)
        for side, pos in ((0, pa), (1, pb)):
            idx = pos[rows]
            ok = idx >= 0
            ii = idx[ok]
            if len(ii) == 0:                       # (a probe that removed this season's matches)
                continue
            tr_ = tour[ii]
            rb = np.where(tr_ == "atp", rbar["atp"], rbar["wta"])
            for e in estimators:
                kind, k = e
                if kind == "a":
                    h = (ret24[ii] + k * rb) / (n24[ii] + k)
                elif kind == "b":
                    rrw = np.where(tr_ == "atp", rbar_rw["atp"], rbar_rw["wta"])
                    base = (ret24[ii] + wo24[ii] + k * rrw) / (n24[ii] + wo24[ii] + k)
                    mr = np.array([ratios[t]["rec30"] for t in tr_]) ** R["rec30"].to_numpy()[ii]
                    ml = np.array([ratios[t]["layoff"] for t in tr_]) ** R["layoff"].to_numpy()[ii]
                    h = base * (rb / rrw) * mr * ml
                elif kind == "c":
                    mdl, mu, sd = model
                    h = mdl.predict_proba((_design(R, ii, rbar) - mu) / sd)[:, 1]
                elif kind == "rate":
                    h = rb.copy()
                else:
                    raise ValueError(kind)
                vals = np.full(rows.sum(), np.nan)
                vals[ok] = np.clip(h, 1e-4, 0.5)
                out[e][side][rows] = vals
    return out


def hazard_primary(P: pd.DataFrame, L: pd.DataFrame) -> dict:
    H = M.hist(L, P)
    ha, hb = M.cached("i042_primary", (H, P), lambda: hazards_by_season(H, P, [PRIMARY])[PRIMARY])
    return {"hz_a": ha, "hz_b": hb}


def combine_i042(P: pd.DataFrame) -> dict:
    """tau as a function of the base's eta (the batch's x_of_eta hook); x is its eta_model version (placeholder, the
    batch re-evaluates it). Controls: Std only, with the M-set (the rulings, MAT-R1a: no Dh, no Sh * eta)."""
    ha, hb = M.pair(P, "hz")

    def x_of_eta(e, rows):
        p = 1.0 / (1.0 + np.exp(-np.asarray(e, float)))
        return hb[rows] / p - ha[rows] / (1.0 - p)
    x = x_of_eta(M.eta(P), np.arange(len(P)))
    Cs, names = M.std_controls(P, x)
    return {"x": x, "x_of_eta": x_of_eta, "x_market": x_of_eta(M.zmkt(P), np.arange(len(P))), "m_set": True,
            "controls": Cs if names else None, "control_names": names,
            "tabpfn": {"hz_a": (ha, "pair", "hz_b"), "hz_b": (hb, "pair", "hz_a")}}


HYPOTHESES = [
    {"hid": "I-042", "master": "I-042", "kind": "W", "sign": "+", "weight": 1.0, "trait": "slow", "deployment": "nudge",
     "anchor": "I", "prepare": hazard_primary, "combine": combine_i042},
]


# ------------------------------------------------------------------------------------------------ diagnostics (__main__)

def _ll(y, h):
    h = np.clip(h, 1e-6, 1 - 1e-6)
    return -(y * np.log(h) + (1 - y) * np.log(1 - h))


def compare_estimators(H: pd.DataFrame, P: pd.DataFrame) -> dict:
    """Out-of-sample log loss on the retirement label (each side's own retirement) of the 2013-2018 panel matches: the
    statistic target of the math audit's ruling (a look-ledger note: reads retirements, never a_won)."""
    ests = [("rate", 0.0)] + [("a", k) for k in K_GRID] + [("b", k) for k in K_GRID] + [("c", 0.0)]
    hz = hazards_by_season(H, P, ests)
    R = row_features(H)
    pa, pb = M.model_pos(H, P)
    lab = R["label"].to_numpy()
    ya, yb = np.where(pa >= 0, lab[np.maximum(pa, 0)], np.nan), np.where(pb >= 0, lab[np.maximum(pb, 0)], np.nan)
    rows = M.seasons(P, *M.TUNE)
    t = M.tours(P)
    res = {}
    for e in ests:
        ha, hb = hz[e]
        rec = {}
        for name, m in (("both", rows), ("atp", rows & (t == "atp")), ("wta", rows & (t == "wta"))):
            ok = m & np.isfinite(ha) & np.isfinite(hb) & np.isfinite(ya) & np.isfinite(yb)
            rec[name] = {"mll": float(1000 * np.mean(np.r_[_ll(ya[ok], ha[ok]), _ll(yb[ok], hb[ok])])),
                         "rows": int(2 * ok.sum()), "events": int(np.r_[ya[ok], yb[ok]].sum())}
        res[f"{e[0]}_k{e[1]:g}"] = rec
    base = res["rate_k0"]["both"]["mll"]
    for k_, v in res.items():
        v["gain_vs_rate_mll_per_row"] = base - v["both"]["mll"]
    return res


def spread_precheck(H: pd.DataFrame) -> dict:
    """The de-noised SD of a persistent per-player in-match retirement rate (split-half, as in Stage 3): each player's
    played matches of 2010-2018 split by the parity of their own order; cov(rate_odd, rate_even) across players with at
    least 20 matches in each half estimates the persistent rate's variance (binomial noise is independent between the
    halves). Also the method of moments (variance minus mean binomial variance). Weight rule (math audit): >= 1 pp -> 2,
    0.5-1 pp -> 1, < 0.5 pp -> drop."""
    yr = pd.to_datetime(H["tournament_date"]).dt.year.to_numpy()
    won = H["won"].astype(bool).to_numpy()
    ret = ((H["status"].astype(str).to_numpy() == "retired") & ~won).astype(float)
    played = H["played"].to_numpy(bool)
    out = {}
    for scope, extra in (("all_levels", np.ones(len(H), bool)),
                         ("main_tour", H["level"].isin(M.MAIN_LEVELS).to_numpy())):
        m = played & (yr <= M.TUNE[1]) & extra
        d = pd.DataFrame({"p": H["pc"].to_numpy()[m], "r": ret[m], "tour": H["tour"].astype(str).to_numpy()[m]})
        d["half"] = d.groupby("p").cumcount() % 2
        g = d.groupby(["p", "half"])["r"].agg(["mean", "size"]).unstack()
        g = g[(g[("size", 0)] >= 20) & (g[("size", 1)] >= 20)]
        r1, r2 = g[("mean", 0)].to_numpy(), g[("mean", 1)].to_numpy()
        n = (g[("size", 0)] + g[("size", 1)]).to_numpy()
        cov = float(np.cov(r1, r2)[0, 1])
        allr = d.groupby("p")["r"].agg(["mean", "size"]).loc[g.index]
        mom = float(allr["mean"].var() - np.mean(allr["mean"] * (1 - allr["mean"]) / allr["size"]))
        out[scope] = {"players": int(len(g)), "mean_rate": float(np.mean(allr["mean"])),
                      "split_half_cov": cov, "sd_pp_split_half": float(100 * np.sqrt(max(cov, 0.0))),
                      "split_half_corr": float(np.corrcoef(r1, r2)[0, 1]),
                      "sd_pp_moments": float(100 * np.sqrt(max(mom, 0.0))), "median_matches": float(np.median(n))}
    return out


def reverse_after(H: pd.DataFrame, day: float, remove: bool) -> pd.DataFrame:
    """The long table with every match that surely started after `day` (es > day) reversed (winner flag flipped for
    both rows) or removed."""
    later = H["es"].to_numpy(float) > day
    if remove:
        return H.loc[~later].reset_index(drop=True)
    H2 = H.copy()
    H2.loc[later, "won"] = ~H2.loc[later, "won"].astype(bool)
    return H2


def probe(H: pd.DataFrame, P: pd.DataFrame, cuts=("2016-06-15", "2019-08-28", "2022-09-07")) -> dict:
    """No hazard of a match that surely finished by the cut (lf <= cut) moves when every later result is reversed or
    removed (the walk-forward pools: r_bar, MAT-W2's ratios, BOD-12's logistic)."""
    ests = [PRIMARY, ("b", PRIMARY[1]), ("c", 0.0)]
    base = hazards_by_season(H, P, ests)
    lf = M.num(P, "lf")
    res = {}
    for cut in cuts:
        day = float((pd.Timestamp(cut) - pd.Timestamp("1970-01-01")).days)
        for remove in (False, True):
            M.clear_memo()
            H2 = reverse_after(H, day, remove)
            H2["pc"] = pd.factorize(H2["player_id"])[0]
            alt = hazards_by_season(H2, P, ests)
            chk = lf <= day
            for e in ests:
                d = max(float(np.nanmax(np.abs(alt[e][s][chk] - base[e][s][chk]))) for s in (0, 1))
                later = ~chk & np.isfinite(base[e][0])
                moved = float(np.nanmean(np.abs(alt[e][0][later] - base[e][0][later]) > 1e-12)) if remove is False else None
                res[f"{cut}|{'removed' if remove else 'reversed'}|{e[0]}"] = {
                    "checked": int(chk.sum()), "max_abs_change_earlier": d, "share_later_moved": moved}
    res["pass"] = all(v["max_abs_change_earlier"] <= ATOL for k, v in res.items() if isinstance(v, dict))
    res["atol"] = ATOL
    return res


def main() -> int:
    import warnings
    warnings.simplefilter("ignore")
    from src.eda.feature_interactions.history import long_table
    from src.eda.feature_interactions.panel import panel
    P = panel(max_season=C.REPLICATION[-1]).drop(columns=["a_won"])
    L = long_table()
    H = M.hist(L, P)
    out = {"primary": list(PRIMARY), "precheck": spread_precheck(H)}
    C.log(f"precheck {out['precheck']}")
    out["comparison_2013_2018"] = compare_estimators(H, P)
    C.log("comparison done")
    hz = hazard_primary(P, L)
    hh = np.r_[hz["hz_a"], hz["hz_b"]]
    out["primary_hazard_at_model_rows"] = {"mean": float(np.nanmean(hh)), "sd_pp": float(100 * np.nanstd(hh)),
                                           "q01_q50_q99": [float(q) for q in np.nanquantile(hh, [0.01, 0.5, 0.99])]}
    out["probe"] = probe(H, P)
    C.log(f"probe pass {out['probe']['pass']}")
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(OUT / "i042.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
