"""Step 2: what the I-084 lead is, on the development seasons 2014-2024 only (2025-2026 never loaded).

Every fit: logit P(A wins) = slope per tour x season on eta + cubic per tour + eta|eta| per tour (the screen's nuisance
and M-set) + sum_k b_k (s_k * eta) [+ controls], no intercept; z from the largest of the four-week-block, shared-player
and union clustered variances; z for 2014-2021 and 2022-2024 separately, joint z combined as the screen does. No
widening (the screen's sqrt(1.25) for slow traits would divide every z by 1.118).

Sign key: b < 0 = the forecast should be FLATTER (closer to 50%) where the modulator is high.

    ./python.sh src/eda/pair_strength/explore.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.eda.pair_strength import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402


def summarise(res: dict, keys: list[str] | None = None) -> dict:
    keys = keys or list(res["joint_z"])
    out = {}
    for k in keys:
        a, b = res["2014-2021"]["terms"][k], res["2022-2024"]["terms"][k]
        out[k] = {"b1": a["b"], "se1": a["se"], "z1": a["z"], "b2": b["b"], "se2": b["se"], "z2": b["z"],
                  "joint_z": res["joint_z"][k]}
    return out


def pooled(F, eta, mods, controls=None, rows=None, **kw) -> dict:
    """One fit on all of 2014-2024 (per tour x season slopes), for coefficients with one interval."""
    rows = np.ones(len(F), bool) if rows is None else rows
    r = C.slope_fit(F, rows, eta, mods, controls, **kw)
    return {k: {"b": v["b"], "se": v["se"], "z": v["z"], "lo": v["b"] - 1.96 * v["se"], "hi": v["b"] + 1.96 * v["se"]}
            for k, v in r["terms"].items()} | {"_n": r["n"]}


def binned_slopes(F, eta, s, n_bins=5, rows=None) -> list[dict]:
    """Per tour and pair-strength quintile (cut per tour on 2014-2021 rows): the slope of the result on eta (one slope
    per bin, pooled over seasons) with a four-week-block/player clustered SE."""
    rows = np.ones(len(F), bool) if rows is None else rows
    out = []
    t = F["tour"].to_numpy()
    for tour in C.TOURS:
        m = (t == tour) & rows & np.isfinite(s)
        edges = np.quantile(s[m & C.disc_mask(F)], np.linspace(0, 1, n_bins + 1))
        edges[0], edges[-1] = -np.inf, np.inf
        q = np.digitize(s, edges[1:-1])
        for b in range(n_bins):
            k = m & (q == b)
            Z = eta[k][:, None]
            y = F["a_won"].to_numpy(float)[k]
            beta, p, H = S.fit(Z, y)
            a = np.linalg.solve(H, np.eye(1)[0])
            u = (y - p) * (Z @ a)
            v = S.clustered_variances(u, F["block"].to_numpy()[k], F["player_a_id"].to_numpy(str)[k],
                                      F["player_b_id"].to_numpy(str)[k])
            se = float(np.sqrt(max(v.values())))
            out.append({"tour": tour, "bin": b + 1, "n": int(k.sum()), "s_mean": float(np.mean(s[k])),
                        "slope": float(beta[0]), "se": se, "lo": float(beta[0] - 1.96 * se),
                        "hi": float(beta[0] + 1.96 * se)})
    return out


def power_devig(oa: np.ndarray, ob: np.ndarray) -> np.ndarray:
    """Power de-vig of two decimal odds: p_i = (1/o_i)^k with k solving p_A + p_B = 1; returns logit p_A."""
    qa, qb = 1.0 / oa, 1.0 / ob
    lo, hi = np.full(len(qa), 0.5), np.full(len(qa), 3.0)
    for _ in range(60):
        k = (lo + hi) / 2
        f = qa ** k + qb ** k - 1.0
        hi = np.where(f < 0, k, hi)          # sum below 1: k too large
        lo = np.where(f < 0, lo, k)
    k = (lo + hi) / 2
    pa = qa ** k
    return C.lg(pa / (pa + qb ** k))


def main() -> int:
    warnings.simplefilter("ignore")
    F = C.dev_frame()
    C.log(f"development frame: {len(F)} matches, seasons {F['season'].min()}-{F['season'].max()}")
    eta_m = F["z_model"].to_numpy(float)
    eta_p = F["z_market"].to_numpy(float)
    s = F["s_elo_sum"].to_numpy(float)
    R: dict = {"n": int(len(F)), "coverage_elo_sum": float(np.isfinite(F["pr_elo_sum"]).mean())}

    # E1: pair strength alone (no competing modulators, no Std controls)
    for base, e in (("model", eta_m), ("market", eta_p)):
        R[f"E1_alone_{base}"] = summarise(C.by_window(F, e, {"elo_sum": s}))
        R[f"E1_alone_{base}_pooled"] = pooled(F, e, {"elo_sum": s})
        R[f"E1_alone_{base}_no_mset"] = summarise(C.by_window(F, e, {"elo_sum": s}, mset=False))
    C.log(f"E1 alone: model joint z {R['E1_alone_model']['elo_sum']['joint_z']:+.2f}, market "
          f"{R['E1_alone_market']['elo_sum']['joint_z']:+.2f}")

    # E2: calibration slope by pair-strength quintile (the picture)
    R["E2_bins_model"] = binned_slopes(F, eta_m, F["pr_elo_sum"].to_numpy(float))
    R["E2_bins_market"] = binned_slopes(F, eta_p, F["pr_elo_sum"].to_numpy(float))
    # relative multipliers with the full nuisance: quintile dummies x eta (middle quintile the reference)
    mods = {}
    t = F["tour"].to_numpy()
    q = np.full(len(F), -1)
    for tour in C.TOURS:
        m = t == tour
        ed = np.quantile(F["pr_elo_sum"].to_numpy(float)[m & C.disc_mask(F)], [0.2, 0.4, 0.6, 0.8])
        q[m] = np.digitize(F["pr_elo_sum"].to_numpy(float)[m], ed)
    for b in (0, 1, 3, 4):
        mods[f"q{b + 1}"] = (q == b).astype(float)
    R["E2_quintile_dummies_model"] = pooled(F, eta_m, mods)
    R["E2_quintile_dummies_market"] = pooled(F, eta_p, mods)

    # E3: decompositions (model and market bases)
    specs = {
        "fav_dog": {"elo_fav": F["s_elo_fav"].to_numpy(float), "elo_dog": F["s_elo_dog"].to_numpy(float)},
        "max_min": {"elo_max": F["s_elo_max"].to_numpy(float), "elo_min": F["s_elo_min"].to_numpy(float)},
        "sum_and_obscurity": {"elo_sum": s, "lrank_max": F["s_lrank_max"].to_numpy(float)},
        "obscurity_alone": {"lrank_max": F["s_lrank_max"].to_numpy(float)},
        "lrank_sum_alone": {"lrank_sum": F["s_lrank_sum"].to_numpy(float)},
        "ttt_sum_alone": {"ttt_sum": F["s_ttt_sum"].to_numpy(float)},
        "sum_and_ttt": {"elo_sum": s, "ttt_sum": F["s_ttt_sum"].to_numpy(float)},
        "sum_and_overround": {"elo_sum": s, "overround": F["s_overround"].to_numpy(float)},
        "overround_alone": {"overround": F["s_overround"].to_numpy(float)},
        "sum_and_absdiff": {"elo_sum": s, "elo_absdiff": F["s_elo_absdiff"].to_numpy(float)},
        "sum_and_experience": {"elo_sum": s, "log_n_min": F["s_log_n_min"].to_numpy(float)},
        "sum_and_age": {"elo_sum": s, "age_sum": F["s_age_sum"].to_numpy(float)},
    }
    lv = F["level"].astype(str).to_numpy()
    ctx = {f"lvl_{k}": C.zsym((lv == k).astype(float), F) for k in ("GS", "FIN", "T1000", "T500")}
    ctx["bo5"] = C.zsym((pd.to_numeric(F["best_of"], errors="coerce").to_numpy(float) == 5).astype(float), F)
    from src.eda.feature_interactions.features.mkt_common import round_depth
    ctx["round_depth"] = C.zsym(round_depth(F.assign(in_round=F["in_round"])), F)
    specs["sum_and_context"] = {"elo_sum": s, **ctx}
    specs["sum_ctx_overround_obscurity"] = {"elo_sum": s, **ctx, "overround": F["s_overround"].to_numpy(float),
                                             "lrank_max": F["s_lrank_max"].to_numpy(float)}
    for name, mods in specs.items():
        for base, e in (("model", eta_m), ("market", eta_p)):
            R[f"E3_{name}_{base}"] = summarise(C.by_window(F, e, mods))
        C.log(f"E3 {name}: model " + ", ".join(f"{k} {v['joint_z']:+.2f}" for k, v in R[f'E3_{name}_model'].items()))

    # E3e: other price bases: Pinnacle (de-vigged, as the panel's p_ps_a) and a power de-vig of the average
    ps = pd.to_numeric(F["p_ps_a"], errors="coerce").to_numpy(float)
    has_ps = np.isfinite(ps)
    eta_ps = C.lg(np.where(has_ps, ps, 0.5))
    oa, ob = pd.to_numeric(F["avg_a"], errors="coerce").to_numpy(float), pd.to_numeric(F["avg_b"], errors="coerce").to_numpy(float)
    has_avg = np.isfinite(oa) & np.isfinite(ob) & (oa > 1) & (ob > 1)
    eta_pow = np.where(has_avg, power_devig(np.where(has_avg, oa, 2.0), np.where(has_avg, ob, 2.0)), 0.0)
    R["coverage_pinnacle"] = float(has_ps.mean())
    R["coverage_avg_odds"] = float(has_avg.mean())
    R["E3e_pinnacle"] = summarise(C.by_window(F, eta_ps, {"elo_sum": s}, rows=has_ps))
    R["E3e_market_on_pinnacle_rows"] = summarise(C.by_window(F, eta_p, {"elo_sum": s}, rows=has_ps))
    R["E3e_power_devig_avg"] = summarise(C.by_window(F, eta_pow, {"elo_sum": s}, rows=has_avg))
    R["E3e_pinnacle_overround"] = summarise(C.by_window(F, eta_ps, {"elo_sum": s,
                                                              "overround": F["s_overround"].to_numpy(float)},
                                                         rows=has_ps))
    C.log(f"E3e Pinnacle base: elo_sum joint z {R['E3e_pinnacle']['elo_sum']['joint_z']:+.2f}; power de-vig "
          f"{R['E3e_power_devig_avg']['elo_sum']['joint_z']:+.2f}")

    # E3f: the model's eta split into the price and the model's adjustment (adj = eta - price), each with its own
    # slope (per tour) and its own pair-strength modulation
    adj = eta_m - eta_p
    atp = (F["tour"] == "atp").to_numpy()
    tests = {"adj atp": np.where(atp, adj, 0.0), "adj wta": np.where(~atp, adj, 0.0), "adj x elo_sum": adj * s}
    R["E3f_price_plus_adjustment"] = summarise(C.by_window(F, eta_p, {"elo_sum_x_price": s}, tests=tests))

    # E3g: by tour, by level, by season (model base, pair strength alone)
    for tour in C.TOURS:
        R[f"E3g_tour_{tour}"] = summarise(C.by_window(F, eta_m, {"elo_sum": s}, rows=(F["tour"] == tour).to_numpy()))
        R[f"E3g_tour_{tour}_market"] = summarise(C.by_window(F, eta_p, {"elo_sum": s},
                                                             rows=(F["tour"] == tour).to_numpy()))
    lvl_groups = {"GS": lv == "GS", "T1000": lv == "T1000", "T500": lv == "T500", "T250": lv == "T250"}
    for name, m in lvl_groups.items():
        R[f"E3g_level_{name}"] = pooled(F, eta_m, {"elo_sum": s}, rows=m)
    seasons = sorted(F["season"].unique())
    R["E3g_by_season"] = {int(y): pooled(F, eta_m, {"elo_sum": s}, rows=(F["season"] == y).to_numpy())["elo_sum"]
                          for y in seasons}
    R["E3g_by_season_market"] = {int(y): pooled(F, eta_p, {"elo_sum": s},
                                                rows=(F["season"] == y).to_numpy())["elo_sum"] for y in seasons}

    # E4: functional form: a linear plus a quadratic term, and the binned version above
    s2 = C.zsym(s ** 2, F)
    for base, e in (("model", eta_m), ("market", eta_p)):
        R[f"E4_quadratic_{base}"] = summarise(C.by_window(F, e, {"elo_sum": s, "elo_sum_sq": s2}))

    # E5: the size in probability terms, from the simplest form: logit P = a_tour eta + b (s * eta) on 2014-2024
    # (no cubic, no M-set), for a match the plain calibration puts at 70% for the favourite
    simple = C.slope_fit(F, np.ones(len(F), bool), eta_m, {"elo_sum": s}, per_season=False, mset=False, cubic=False)
    R["E5_simple_fit"] = {"b": simple["terms"]["elo_sum"], "slopes": simple["base_slopes"]}
    atp = (F["tour"] == "atp").to_numpy()
    a_plain, _, _ = S.fit(np.column_stack([np.where(atp, eta_m, 0.0), np.where(~atp, eta_m, 0.0)]),
                          F["a_won"].to_numpy(float))
    R["E5_plain_slopes"] = {"atp": float(a_plain[0]), "wta": float(a_plain[1])}
    tab = {}
    for tour in C.TOURS:
        a0 = R["E5_plain_slopes"][tour]
        a1 = simple["base_slopes"][f"slope {tour}"]
        b = simple["terms"]["elo_sum"]["b"]
        z70 = C.lg(0.7) / a0                      # the raw eta that the plain calibration maps to 70%
        tab[tour] = {f"{sd:+.1f} SD": float(expit((a1 + b * sd) * z70)) for sd in (-2, -1.5, -1, 0, 1, 1.5, 2)}
    R["E5_probability_terms"] = tab
    C.write_json(C.OUT / "explore.json", R)
    C.log("written explore.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
