"""R4 test verifier: S6(b), the 24 h -> 30 min price-move regression, on synthetic prices and forecasts.

Finding from verifier_multiplicity.py: with no speed term anywhere, score.moves()'s odds version
    M = logit p30 - logit p24  on  [eta_B,early - logit p24, eta_A1,early - eta_B,early]   (no intercept, 4-week CR1)
excludes 0 far more often than 5%. Two mechanisms, both present in real fits:
    shared seeds   eta_B,early's seed noise is in both regressors with opposite signs; x1 correlates with M (the
                   24-hour price's error is in x1 and reverts in M), so the second slope gets a positive bias
    temperature    any arm-level scale difference t (A1's early log-odds = (1 + t) x the base's) makes x2 contain
                   t eta_B,early; M's residual after x1 contains -lambda (1 - a) eta_B,early (the base's raw
                   over-confidence against the price sits in x1 and M does not follow it), so the second slope is
                   driven by (1 - a) / t. Seed-level t varies by sample (SD about 0.001 for a 16-seed mean), so the
                   cluster SE misses it; a structural t of 1% gives a large spurious slope.
The world: only 2025-2026, the real priced rows, synthetic everything else (no outcome, no real price):
    logit p24 = a mu + e1, e1 ~ N(0, 0.15^2);  logit p30 = a mu + e2 + LAM BETA z (planted world only), e2 ~ N(0, 0.05^2)
    early forecasts, seed k: (mu + d)(1 + tau_k) + e_k for the base; (mu + d + c BETA z / a)(1 + t + tau_k) + e_k for
    A1; d ~ N(0, 0.1^2) per match (the price's effect on the forecast), tau_k ~ N(0, tau_sd^2), e_k as measured
The temperature now scales the WHOLE early forecast (in verifier_multiplicity's world it scaled mu only).
Variants of the regression (slope on the A1-view term):
    registered     [eta_B - lp24, eta_A - eta_B]                         (score.moves, 16 seeds each)
    control        [eta_B - lp24, eta_B, eta_A - eta_B]
    disjoint       [eta_B^{0-7} - lp24, eta_A - eta_B^{8-15}]
    control_disj   [eta_B^{0-7} - lp24, eta_B^{0-7}, eta_A - eta_B^{8-15}]
and the no-odds version as registered.

Writes data/studies/serve_speed_tabpfn/design/verifier_s6.json (verifier_s6_<tag>.json with --tag <tag>; the
re-verification of the strategist's fix uses --tag reverify, where "registered" is score.moves()'s new regression).
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_s6.py [--tag reverify]
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402
from src.eda.serve_speed_tabpfn.design import verifier_worlds as V  # noqa: E402

OUT = C.OUT / "design" / "verifier_s6.json"
REPS = 400
LAM, BETA, CAP = 0.5, 0.09, 0.5


def seed_means(W, rng, center, r, seeds, tau_sd, t_arm=0.0):
    """Per-seed early forecasts (probabilities) on rows r: center (1 + t_arm + tau_k) + e_k."""
    out = []
    for _ in range(seeds):
        tau = np.where(W.atp[r], rng.normal(0, tau_sd), rng.normal(0, tau_sd))
        out.append(expit(center[r] * (1 + t_arm + tau) + rng.normal(0, 1, len(r)) * W.resid_sd[r]))
    return np.array(out)                                   # (seeds, rows)


def one_rep(W, rng, priced, tau_sd: float, t_arm: float, planted: bool) -> dict:
    info = W.info.copy()
    beta = BETA if planted else 0.0
    a_mu = W.a_row * W.mu
    info.loc[priced, "p_early_a"] = expit((a_mu + rng.normal(0, 0.15, len(info)))[priced])
    info.loc[priced, "p_close_a"] = expit((a_mu + rng.normal(0, 0.05, len(info)) + LAM * beta * W.z)[priced])
    d = rng.normal(0, 0.1, len(info))
    shift = CAP * beta * W.z / V.A_TOUR["atp"]
    bank = S.Bank(W.P, W.fx, require_checks=False)
    per = {}
    for s in (2025, 2026):
        r = W.rows[s]
        idx = W.info.index[r]
        pr = priced[r]
        pb = seed_means(W, rng, W.mu + d, r, 16, tau_sd)
        pa = seed_means(W, rng, W.mu + d + shift, r, 16, tau_sd, t_arm)
        per[s] = (idx[pr], pb[:, pr], pa[:, pr])
        for k in range(16):
            bank.injected[("model", s, k)] = {"early": pd.Series(pb[k, pr], index=idx[pr])}
            bank.injected[("spd", s, k)] = {"early": pd.Series(pa[k, pr], index=idx[pr])}
        for arm, center in (("model_noodds", 0.85 * W.mu), ("spd_noodds", 0.85 * W.mu + shift)):
            p = seed_means(W, rng, center, r, 8, tau_sd)
            for k in range(8):
                bank.injected[(arm, s, k)] = {"td": pd.Series(p[k], index=idx)}
    sc = S.Scorer(bank, info, pd.Series(0.0, index=info.index))       # moves() reads no outcome
    out = {m["cid"].replace("S6_move_", "") + "|registered": (m["estimate"], m["lo"], m["hi"]) for m in S.moves(sc)}
    ids_all = np.concatenate([per[s][0] for s in (2025, 2026)])
    eta = {"B": C.lg(np.concatenate([per[s][1].mean(axis=0) for s in (2025, 2026)])),
           "A": C.lg(np.concatenate([per[s][2].mean(axis=0) for s in (2025, 2026)])),
           "B0_7": C.lg(np.concatenate([per[s][1][:8].mean(axis=0) for s in (2025, 2026)])),
           "B8_15": C.lg(np.concatenate([per[s][1][8:].mean(axis=0) for s in (2025, 2026)]))}
    eta = {k: pd.Series(v, index=ids_all) for k, v in eta.items()}
    for pop in ("men_early_all", "men_early_clean"):
        ids = S.population_ids(info, pop, (2025, 2026))
        inf = info.loc[ids]
        lp24 = C.lg(inf["p_early_a"])
        M = C.lg(inf["p_close_a"]) - lp24
        e = {k: v.reindex(ids).to_numpy() for k, v in eta.items()}
        tag = pop.rsplit("_", 1)[1]
        for name, X in (("control", [e["B"] - lp24, e["B"], e["A"] - e["B"]]),
                        ("disjoint", [e["B0_7"] - lp24, e["A"] - e["B8_15"]]),
                        ("control_disj", [e["B0_7"] - lp24, e["B0_7"], e["A"] - e["B8_15"]])):
            r = S.ols_cluster(M, np.column_stack(X), inf["block"].to_numpy())
            out[f"odds_{tag}|{name}"] = (r["beta"][-1], r["lo"][-1], r["hi"][-1])
    return out


def main() -> int:
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else None
    out_path = OUT.with_name(f"verifier_s6_{tag}.json") if tag else OUT
    W = V.World()
    priced = (W.info["has_early"].to_numpy(bool) & np.isfinite(W.info["p_early_a"].to_numpy(float))
              & np.isfinite(W.info["p_close_a"].to_numpy(float)))
    report = {"what": "S6(b) on synthetic prices and forecasts: the registered regression and three variants (no "
                      "outcome and no real price used)", "reps": REPS, "lambda": LAM, "beta": BETA, "capture": CAP,
              "scorer_code_sha256": C.code_hash(), "tag": tag, "worlds": []}
    worlds = [("null, measured seed temperature", V.TAU_SD, 0.0, False),
              ("null, no seed temperature", 0.0, 0.0, False),
              ("null, A1 1% more confident (no information)", V.TAU_SD, 0.01, False),
              ("planted: A1 knows half the speed term, the 30-min price moves toward it", V.TAU_SD, 0.0, True)]
    for i, (label, tau_sd, t_arm, planted) in enumerate(worlds):
        rng = np.random.default_rng(31 + i)
        reps = [one_rep(W, rng, priced, tau_sd, t_arm, planted) for _ in range(REPS)]
        rows = {}
        for cid in reps[0]:
            e = np.array([r[cid] for r in reps])
            est, lo, hi = e[:, 0], e[:, 1], e[:, 2]
            rows[cid] = {"mean": float(est.mean()), "sd": float(est.std(ddof=1)),
                         "mean_half_width": float(((hi - lo) / 2).mean()),
                         "reject_pos": float((lo > 0).mean()), "reject_neg": float((hi < 0).mean()),
                         "reject_two_sided": float(((lo > 0) | (hi < 0)).mean())}
        same = {}
        for tag_pop in ("all", "clean"):
            a = np.array([r[f"odds_{tag_pop}|registered"] for r in reps])
            b = np.array([r[f"odds_{tag_pop}|control_disj"] for r in reps])
            same[tag_pop] = float(np.abs(a - b).max())          # score.moves() against the verifier's variant
        report["worlds"].append({"world": label, "tau_sd": tau_sd, "t_arm": t_arm, "planted": planted,
                                 "endpoints": rows, "max_abs_registered_minus_control_disj": same})
        print(f"   max |registered - control_disj| (estimate, lo, hi): {same}")
        print(f"== {label}")
        for cid, v in sorted(rows.items()):
            print(f"   {cid:<28} mean {v['mean']:+.3f} sd {v['sd']:.3f} half-width {v['mean_half_width']:.3f} "
                  f"reject + {v['reject_pos']:.3f} - {v['reject_neg']:.3f} two-sided {v['reject_two_sided']:.3f}")
    C.write_json(out_path, report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
