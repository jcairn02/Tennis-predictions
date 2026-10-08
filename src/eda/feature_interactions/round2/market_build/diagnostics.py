"""Result-free diagnostics of the MARKET analyst's hypotheses (src/eda/feature_interactions/features/f10-f19), beside the
batch's own (swap tests, novelty R^2 of x, coverage): for price-slope ideas the novelty of s * eta (the candidate the
screen tests), the three nearest inputs, distributions, each block member's coverage, novelty and correlations, and the
cards' feature-only prechecks. The panel's result column is dropped on load; nothing is related to a result.

Writes data/studies/feature_interactions/round2/market/diagnostics.json.
Run: ./python.sh src/eda/feature_interactions/round2/market_build/diagnostics.py
"""
from __future__ import annotations

import importlib
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions.features import mkt_common as M  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402
from src.eda.feature_interactions.panel import panel  # noqa: E402

MODULES = ("f10_price_slopes", "f11_retirement", "f12_salience", "f13_uncertainty", "f14_anchor", "f15_recal",
           "f16_repute", "f17_info", "f18_overreact", "f19_motiv")
OUT = C.OUT / "round2" / "market"


def r2(X: np.ndarray, v: np.ndarray, rows: np.ndarray) -> float:
    ok = rows & np.isfinite(v)
    if ok.sum() < 200 or np.var(v[ok]) == 0:
        return float("nan")
    Z = np.column_stack([np.ones(ok.sum()), np.nan_to_num(X[ok])])
    beta, *_ = np.linalg.lstsq(Z, v[ok], rcond=None)
    return float(1 - np.var(v[ok] - Z @ beta) / np.var(v[ok]))


def coverage(P: pd.DataFrame, v: np.ndarray) -> dict:
    v = np.asarray(v, float).reshape(len(P), -1)
    out = {}
    for tour in C.TOURS:
        for win, seas in (("2014_21", C.DISCOVERY), ("2022_24", C.REPLICATION)):
            m = (P["tour"] == tour).to_numpy() & P["season"].isin(seas).to_numpy()
            out[f"{tour}_{win}"] = round(float(np.isfinite(v[m]).all(axis=1).mean()), 4)
    return out


def column_report(P, v, X58, Xm, disc) -> dict:
    v = np.asarray(v, float)
    return {"coverage": coverage(P, v), "r2_on_58": r2(X58, v, disc), "r2_on_58_and_mset": r2(Xm, v, disc),
            "nearest": [(n, round(c, 3)) for n, c in M.nearest(P, v, 3)], "distribution": M.describe(v, P)}


def prechecks(Q: dict, P: pd.DataFrame, disc: np.ndarray) -> dict:
    """The cards' feature-only checks, from the prepared panels of the modules (no result)."""
    out = {}
    eta, z = M.eta(P), M.zmkt(P)
    q = Q["B6"]
    F13 = importlib.import_module("src.eda.feature_interactions.features.f13_uncertainty").flux_pair(q)
    dform = M.num(q, "in_adjperf_tpw_2w")
    beta = {}
    implied = np.full(len(P), np.nan)
    for tr in C.TOURS:
        m = M.tours(P) == tr
        ok = m & M.tune(P) & np.isfinite(z) & np.isfinite(dform)
        beta[tr] = float(np.sum(z[ok] * dform[ok]) / np.sum(dform[ok] ** 2))
        implied[m] = beta[tr] ** 2 * F13[m]
    out["I-033 flux gate"] = {"beta_price_on_form": beta,
                              "share_implied_flux_var_gt_0.03": float(np.nanmean(implied[disc] > 0.03)),
                              "rule": ">= 5% passes (MAT-U4's feature-only gate)"}
    out["I-055 favourite"] = {"share_sign_price_ne_sign_eta": float(np.nanmean((np.sign(z) != np.sign(eta))[disc]))}
    q = Q["B-ANCHOR"]
    f14 = importlib.import_module("src.eda.feature_interactions.features.f14_anchor")
    a, k, bad = f14.odds_parts(q)
    dF = M.num(q, "fame_a") - M.num(q, "fame_b")
    out["B-ANCHOR"] = {"share_arbitrage_positive": float(np.nanmean(a[disc] > 0)), "share_incoherent": float(bad[disc].mean()),
                       "share_equal_fame": float(np.nanmean(dF[disc] == 0)),
                       "share_contrast_nonzero": float(np.nanmean((np.abs(k) * np.abs(np.sign(dF)))[disc] > 0))}
    q = Q["B-OVERREACT"]
    f18 = importlib.import_module("src.eda.feature_interactions.features.f18_overreact")
    r, F85, s85 = f18.drift(q)
    sa, sb = M.pair(q, "sur")
    late = M.num(q, "in_round") >= 15
    out["I-085 drift"] = {"share_disagreement": float(np.nanmean(s85[disc])), "coverage_r": float(np.isfinite(r[disc]).mean()),
                          "sd_r": float(np.nanstd(r[disc])), "corr_F_with_price": float(pd.Series(F85[disc]).corr(pd.Series(z[disc])))}
    out["I-086 surprise"] = {"coverage_both_defined": float((np.isfinite(sa) & np.isfinite(sb))[disc].mean()),
                             "share_late": float(late[disc].mean()),
                             "coverage_late_rows": float((np.isfinite(sa) & np.isfinite(sb))[disc & late].mean()),
                             "share_nonzero_surprise": float(np.nanmean((np.abs(sa - sb) > 0)[disc]))}
    n = M.num(q, "h2hn_a")
    out["I-091 head to head"] = {"share_n_ge_3": float(np.mean(n[disc] >= 3)), "a_b_counts_agree":
                                 bool(np.allclose(np.nan_to_num(n), np.nan_to_num(M.num(q, "h2hn_b"))))}
    q = Q["I-082"]
    hl = np.r_[M.num(q, "hasL_a")[disc], M.num(q, "hasL_b")[disc]]
    tt = np.r_[M.tours(P)[disc], M.tours(P)[disc]]
    out["I-082 lower-level evidence"] = {t: float(np.nanmean(hl[tt == t])) for t in C.TOURS}
    q = Q["B-MOTIV"]
    f19 = importlib.import_module("src.eda.feature_interactions.features.f19_motiv")
    s = f19.pre_slam(q)
    out["B-MOTIV"] = {"share_pre_slam_rows": float(s[disc].mean()),
                      "share_post_nonzero": float(np.nanmean((M.num(q, "post_a") != M.num(q, "post_b"))[disc]))}
    ps = M.num(P, "p_ps_a")
    out["Pinnacle coverage by season"] = {int(y): round(float(np.isfinite(ps[P["season"].to_numpy() == y]).mean()), 4)
                                          for y in sorted(P["season"].unique())}
    return out


def main() -> int:
    warnings.simplefilter("ignore")
    P = panel(max_season=C.REPLICATION[-1]).drop(columns=["a_won"])
    L = long_table()
    disc = M.disc(P)
    X58 = P[[c for c in P.columns if c.startswith("in_")]].to_numpy(float)
    eta = M.eta(P)
    tour_atp = (P["tour"] == "atp").to_numpy()
    mset = np.column_stack([np.where(tour_atp, e, 0.0) for e in (eta, eta ** 3, eta * np.abs(eta))]
                           + [np.where(~tour_atp, e, 0.0) for e in (eta, eta ** 3, eta * np.abs(eta))])
    Xm = np.column_stack([X58, mset])
    rep, Q = {}, {}
    for name in MODULES:
        mod = importlib.import_module(f"src.eda.feature_interactions.features.{name}")
        for spec in mod.HYPOTHESES:
            new = spec["prepare"](P, L) if spec.get("prepare") else {}
            q = P.assign(**new) if new else P
            Q[spec["hid"]] = q
            r = spec["combine"](q)
            x = np.asarray(r["x"], float)
            cand = x * eta if r.get("x_times_eta") else x
            rec = {"module": name, "x_times_eta": bool(r.get("x_times_eta", False)), "controls": r.get("control_names"),
                   "eta_mod_controls": r.get("eta_mod_names", [])}
            if cand.ndim == 1:
                rec["candidate"] = column_report(P, cand, X58, Xm, disc)
                rec["candidate"]["corr_with_odds_logit"] = float(pd.Series(cand[disc]).corr(pd.Series(M.zmkt(P)[disc])))
            else:
                rec["candidate_columns"] = [column_report(P, cand[:, j], X58, Xm, disc) for j in range(cand.shape[1])]
            if "x_market" in r:
                xm = np.asarray(r["x_market"], float)
                ok = disc & np.isfinite(x) & np.isfinite(xm)
                rec["corr_x_with_x_market"] = float(np.corrcoef(x[ok], xm[ok])[0, 1])
            mem = r.get("members", {})
            if mem:
                cols = {k: (M.centre(np.asarray(v, float), P) * eta if r.get("x_times_eta") else np.asarray(v, float))
                        for k, v in mem.items()}                 # a symmetric member is centred per tour before x eta
                rec["members"] = {k: column_report(P, v, X58, Xm, disc) for k, v in cols.items()}
                D = pd.DataFrame({k: v[disc] for k, v in cols.items()})
                rec["member_corr"] = D.corr().round(3).to_dict()
            rep[spec["hid"]] = rec
            C.log(f"{spec['hid']}: done")
    a = Q["I-036"]
    f10 = importlib.import_module("src.eda.feature_interactions.features.f10_price_slopes")
    o, t, e, sf = f10.obscurity(a), f10.prominence(a), f10.early(a), f10.sum_fat(a)
    rep["pairs"] = {"corr I-036 x eta, I-084 x eta": float(pd.Series((o * eta)[disc]).corr(pd.Series((t * eta)[disc]))),
                    "corr I-036 s, I-084 s": float(pd.Series(o[disc]).corr(pd.Series(t[disc]))),
                    "corr I-049 x eta, I-054 x eta": float(pd.Series((e * eta)[disc]).corr(pd.Series((sf * eta)[disc])))}
    rep["prechecks"] = prechecks(Q, P, disc)
    f13 = importlib.import_module("src.eda.feature_interactions.features.f13_uncertainty")
    rep["prechecks"]["I-028 gate"] = f13.i028_gate(L)
    C.log(f"I-028 gate {rep['prechecks']['I-028 gate']['pooled_split_half_r']:.3f}")
    q16 = Q["B-REPUTE"]
    m83 = importlib.import_module("src.eda.feature_interactions.features.f16_repute").repute_parts(q16)["m83"]
    lit2 = np.abs(eta) * (M.num(q16, "fame_a") - M.num(q16, "fame_b"))
    flb = importlib.import_module("src.eda.feature_interactions.features.f10_price_slopes")
    qf = Q["B-FLB"]
    lr, hp = flb.later_round(qf) - flb.later_round(qf)[disc].mean(), flb.high_profile(qf) - flb.high_profile(qf)[disc].mean()
    bo5 = (M.num(qf, "best_of") == 5).astype(float)
    rep["pairs"].update({
        "corr LIT-2, I-083": float(pd.Series(lit2[disc]).corr(pd.Series(m83[disc]))),
        "corr HP x eta, bo5 x eta": float(pd.Series((hp * eta)[disc]).corr(pd.Series(((bo5 - bo5[disc].mean()) * eta)[disc]))),
        "corr L x eta, I-036 x eta": float(pd.Series((lr * eta)[disc]).corr(pd.Series((o * eta)[disc]))),
        "corr L x eta, HP x eta": float(pd.Series((lr * eta)[disc]).corr(pd.Series((hp * eta)[disc])))})
    OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(OUT / "diagnostics.json", rep)
    C.log("diagnostics written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
