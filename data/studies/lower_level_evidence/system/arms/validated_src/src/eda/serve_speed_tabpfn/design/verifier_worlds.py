"""R4 test verifier: score.py on SYNTHETIC outcomes built from the REAL base forecasts and the REAL spd_f.

No match result is read: outcomes are drawn here; the frame is read through score.population (explicit columns, no
a_won; verifier_noread.py proves it). The base forecasts are the real fits of arm "model", seeds 0-15, 2019-2026.

Worlds (truth for every frame match of 2019-2026, calibration seasons included; z = spd_f, 0 for women):

  w1   the scorer's own machinery, score.synthetic(): y ~ Bernoulli(expit(s eta_B + beta z)), s = 0.9 for both tours,
       eta_B the base's real 16-seed log-odds; A1's seed k = eta_B + capture (beta / s) z + N(0, 0.019^2) per match;
       the base keeps its real seeds.
       Its blind spot: the base's own seed noise is already inside the truth, so only A1's noise reaches the paired
       difference, while the seed term counts both arms.
  w2   the verifier's two-sided world (score.py's functions, forecasts injected): truth = a_tour mu + beta z with
       mu the base's real 16-seed log-odds and a = 0.92 (men) / 0.87 (women) (assumed; real slopes need outcomes).
       BOTH arms are synthetic with independent seed noise of the measured structure (verifier_seeds.json):
       seed k = mu (+ capture (beta / a_atp) z for A1) + tau_k mu + e_k, tau_k ~ N(0, 0.0028^2) per season, tour and
       seed, e_k ~ N(0, sd_i^2 - tau_sd^2 mu_i^2), sd_i the real per-match SD across the 16 seeds.
  w2s  w2 plus a structural column perturbation u_i ~ N(0, 0.02^2) in A1 only, fixed across seeds (the
       "adding a column moves the fit" effect of strategist_noise.json), which costs A1 a little log loss.
  w3   real seed noise only: each replicate partitions the 16 real seeds at random into a truth set (6), a base set
       (5) and an A1 set (5); truth = a_tour lg(mean of the truth set) + beta z; base = the base set; A1 = the A1
       set shifted by capture (beta / a_atp) z. Scored by score.py's paired() with ONE 5-seed set on both sides
       (calibration on each arm's first four). Arms are exchangeable at beta = 0, so the null is exact.

Per replicate: P2 (estimate, interval, block-only interval, SE parts), the exact expected gain given the replicate's
calibrated forecasts (as score.synthetic computes it), S0, S10, S13, S14 and the decision row (w1, w2, w2s use
score.evaluate(core_only=True); w3 computes P2 only). G_star: the ideal gain of capturing a share `capture` of the
planted term with perfect calibration and no seed noise.

Writes data/studies/serve_speed_tabpfn/design/verifier_worlds/<world>_b<beta>_c<capture>_s<seed>.json
(w1 also writes score.synthetic's own file under verifier_worlds/synthetic/).
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_worlds.py --world w2 --beta 0 --capture 0.5 --reps 500 --seed 1
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

OUT = C.OUT / "design" / "verifier_worlds"
A_TOUR = {"atp": 0.92, "wta": 0.87}       # assumed calibration slopes of the truth (w2, w2s, w3)
S_TRUE_W1 = 0.9                          # score.synthetic's default
TAU_SD = 0.0028                          # seed-level temperature SD (verifier_seeds.json: 0.0028)
STRUCT_SD = 0.02                         # w2s: A1's structural perturbation (log-odds)
SEEDS5 = (0, 1, 2, 3, 4)


class World:
    """The real inputs, loaded once: population (no outcome), the base's per-seed forecasts, mu, sd_i, z."""

    def __init__(self):
        self.P = C.DEFAULT
        self.info = S.population(self.P)
        self.fx = S.frame_index(self.P)
        self.real = S.Bank(self.P, self.fx, require_checks=True)
        per = {s: self.real.per_seed("model", S.SEEDS16, (s,), "td") for s in S.HIST}
        self.per = per
        self.mu = pd.concat([pd.Series(C.lg(per[s].mean(axis=1).to_numpy()), index=per[s].index)
                             for s in S.HIST]).reindex(self.info.index).to_numpy()
        self.sd_i = pd.concat([pd.Series(np.std(C.lg(per[s].to_numpy()), axis=1, ddof=1), index=per[s].index)
                               for s in S.HIST]).reindex(self.info.index).to_numpy()
        if not (np.isfinite(self.mu).all() and np.isfinite(self.sd_i).all()):
            raise RuntimeError("base forecasts missing for some 2019-2026 frame matches")
        self.z = self.info["spd_f"].to_numpy(float)
        self.atp = (self.info["tour"] == "atp").to_numpy()
        self.a_row = np.where(self.atp, A_TOUR["atp"], A_TOUR["wta"])
        self.season = self.info["season"].to_numpy()
        self.rows = {s: np.flatnonzero(self.season == s) for s in S.HIST}
        self.ids_p2 = S.population_ids(self.info, "men", S.TEST)
        self.pos_p2 = pd.Series(np.arange(len(self.info)), index=self.info.index).reindex(self.ids_p2).to_numpy()
        self.resid_sd = np.sqrt(np.maximum(self.sd_i ** 2 - TAU_SD ** 2 * self.mu ** 2, 0.0))


def ideal_gain(pt: np.ndarray, eta_b_cal: np.ndarray, shift_cal: np.ndarray) -> float:
    """1000 x E[LL(base) - LL(arm)] for calibrated log-odds eta_b_cal and eta_b_cal + shift_cal under truth pt."""
    qb, qa = expit(eta_b_cal), expit(eta_b_cal + shift_cal)
    return 1000 * float(np.mean(pt * (np.log(qa) - np.log(qb)) + (1 - pt) * (np.log1p(-qa) - np.log1p(-qb))))


def expected_gain(pt: np.ndarray, qa: np.ndarray, qb: np.ndarray) -> float:
    """score.synthetic's formula: P2's exact expectation given the replicate's calibrated forecasts."""
    return 1000 * float(np.mean(pt * (np.log(qa) - np.log(qb)) + (1 - pt) * (np.log1p(-qa) - np.log1p(-qb))))


def synth_seeds(W: World, rng, center: np.ndarray, struct: np.ndarray | None = None) -> dict:
    """{(season, seed): pd.Series of P(A wins)}: center + tau_k mu + e_k (+ struct), per season and seed."""
    out = {}
    for s, r in W.rows.items():
        idx = W.info.index[r]
        for k in S.SEEDS16:
            tau = np.where(W.atp[r], rng.normal(0, TAU_SD), rng.normal(0, TAU_SD))
            eta = center[r] + tau * W.mu[r] + rng.normal(0, 1, len(r)) * W.resid_sd[r]
            if struct is not None:
                eta = eta + struct[r]
            out[(s, k)] = pd.Series(expit(eta), index=idx)
    return out


def summarise_rep(res: dict, exp_gain: float) -> dict:
    p2, s0, s13, s14 = res["P2"], res["S0"], res["S13"], res["S14"]
    return {"P2": p2["estimate"], "P2_lo": p2["lo"], "P2_hi": p2["hi"], "P2_se": p2["se"],
            "P2_se_block": p2["se_block"], "P2_v_seed_base": p2["v_seed_base"], "P2_v_seed_arm": p2["v_seed_arm"],
            "P2_lo_block_only": p2["lo_block_only"], "P2_hi_block_only": p2["hi_block_only"],
            "P2_lo_week": p2["lo_week"], "P2_hi_week": p2["hi_week"], "expected_gain": exp_gain,
            "S0_b": s0["estimate"], "S0_se": s0["se"], "S0_lo": s0["lo"], "S0_hi": s0["hi"],
            "S10_a": res["S10"]["applied_slope_a"], "S13": s13["estimate"], "S13_lo": s13["lo"], "S13_hi": s13["hi"],
            "S14": s14["estimate"], "S14_lo": s14["lo"], "S14_hi": s14["hi"],
            "excluding_0": res["multiplicity"]["excluding_0"], "decision_row": res["decision"]["row"]}


def run_two_sided(W: World, beta: float, capture: float, reps: int, seed: int, struct_sd: float = 0.0) -> list[dict]:
    rng = np.random.default_rng(seed)
    truth = W.a_row * W.mu + beta * W.z
    pt_all = expit(truth)
    shift = capture * (beta / A_TOUR["atp"]) * W.z            # z = 0 for women
    rows = []
    for r in range(reps):
        y = pd.Series((rng.random(len(W.info)) < pt_all).astype(float), index=W.info.index)
        bank = S.Bank(W.P, W.fx, require_checks=False)
        struct = rng.normal(0, struct_sd, len(W.info)) if struct_sd > 0 else None
        for (s, k), ser in synth_seeds(W, rng, W.mu).items():
            bank.injected[("model", s, k)] = {"td": ser}
        for (s, k), ser in synth_seeds(W, rng, W.mu + shift, struct).items():
            bank.injected[("spd", s, k)] = {"td": ser}
        sc = S.Scorer(bank, W.info, y)
        res = S.evaluate(sc, core_only=True)
        qb, _ = sc.forecast("model", S.SEEDS16, S.TEST, "td", "calibrated", W.ids_p2)
        qa, _ = sc.forecast("spd", S.SEEDS16, S.TEST, "td", "calibrated", W.ids_p2)
        out = summarise_rep(res, expected_gain(pt_all[W.pos_p2], qa, qb))
        out["slope_model_2024_atp"] = sc.slopes("model", 2024)["atp"]
        out["slope_spd_2024_atp"] = sc.slopes("spd", 2024)["atp"]
        rows.append({"rep": r, **out})
    return rows


def run_w3(W: World, beta: float, capture: float, reps: int, seed: int) -> list[dict]:
    rng = np.random.default_rng(seed)
    cmp = S.Comparison("P2_w3", "model", "spd", SEEDS5, "men", S.TEST)
    shift = capture * (beta / A_TOUR["atp"]) * W.z
    lg_seed = {s: C.lg(W.per[s].reindex(W.info.index[r]).to_numpy()) for s, r in W.rows.items()}   # (n_s, 16)
    rows = []
    for r in range(reps):
        perm = rng.permutation(16)
        T_, B_, A_ = perm[:6], perm[6:11], perm[11:]
        mu_t = np.empty(len(W.info))
        bank = S.Bank(W.P, W.fx, require_checks=False)
        for s, rr in W.rows.items():
            idx = W.info.index[rr]
            p = expit(lg_seed[s])
            mu_t[rr] = C.lg(p[:, T_].mean(axis=1))
            for j in range(5):
                bank.injected[("model", s, j)] = {"td": pd.Series(p[:, B_[j]], index=idx)}
                bank.injected[("spd", s, j)] = {"td": pd.Series(expit(lg_seed[s][:, A_[j]] + shift[rr]), index=idx)}
        pt_all = expit(W.a_row * mu_t + beta * W.z)
        y = pd.Series((rng.random(len(W.info)) < pt_all).astype(float), index=W.info.index)
        sc = S.Scorer(bank, W.info, y)
        p2 = sc.paired(cmp)
        qb, _ = sc.forecast("model", SEEDS5, S.TEST, "td", "calibrated", W.ids_p2)
        qa, _ = sc.forecast("spd", SEEDS5, S.TEST, "td", "calibrated", W.ids_p2)
        rows.append({"rep": r, "P2": p2["estimate"], "P2_lo": p2["lo"], "P2_hi": p2["hi"], "P2_se": p2["se"],
                     "P2_se_block": p2["se_block"], "P2_v_seed_base": p2["v_seed_base"],
                     "P2_v_seed_arm": p2["v_seed_arm"], "P2_lo_block_only": p2["lo_block_only"],
                     "P2_hi_block_only": p2["hi_block_only"], "P2_lo_week": p2["lo_week"], "P2_hi_week": p2["hi_week"],
                     "expected_gain": expected_gain(pt_all[W.pos_p2], qa, qb)})
    return rows


def run_w1(W: World, beta: float, capture: float, reps: int, seed: int) -> list[dict]:
    P = W.P.with_(out=OUT)
    tag = f"w1_b{beta:g}_c{capture:g}_s{seed}"
    out = S.synthetic(P, beta=beta, capture_share=capture, reps=reps, seed=seed, arms="synthetic", s_true=S_TRUE_W1,
                      seed_sd=0.019, tag=tag)
    return out["replicates"]


def g_star(W: World, world: str, beta: float, capture: float) -> float:
    if world == "w1":
        eta_b = S.Bank(W.P, W.fx, require_checks=True).eta("model", S.SEEDS16, S.HIST, "td").reindex(W.info.index)
        a = np.full(len(W.info), S_TRUE_W1)
        mu = eta_b.to_numpy()
    else:
        a, mu = W.a_row, W.mu
    pt = expit(a * mu + beta * W.z)[W.pos_p2]
    return ideal_gain(pt, (a * mu)[W.pos_p2], (capture * beta * W.z)[W.pos_p2])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--world", choices=("w1", "w2", "w2s", "w3"), required=True)
    ap.add_argument("--beta", type=float, default=0.0)
    ap.add_argument("--capture", type=float, default=0.5)
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    t0 = time.time()
    W = World()
    if a.world == "w1":
        rows = run_w1(W, a.beta, a.capture, a.reps, a.seed)
    elif a.world == "w3":
        rows = run_w3(W, a.beta, a.capture, a.reps, a.seed)
    else:
        rows = run_two_sided(W, a.beta, a.capture, a.reps, a.seed, STRUCT_SD if a.world == "w2s" else 0.0)
    tq = float(student_t.ppf(0.975, 32))
    out = {"what": "synthetic outcomes drawn from a planted model on the real base forecasts and the real spd_f; no "
                   "match result read", "world": a.world, "beta": a.beta, "capture": a.capture, "reps": a.reps,
           "seed": a.seed, "a_tour": A_TOUR if a.world != "w1" else {"atp": S_TRUE_W1, "wta": S_TRUE_W1},
           "tau_sd": TAU_SD, "struct_sd": STRUCT_SD if a.world == "w2s" else 0.0,
           "G_star": g_star(W, a.world if a.world != "w3" else "w2", a.beta, a.capture),
           "t_975_32": tq, "seconds": round(time.time() - t0, 1), "replicates": rows}
    C.write_json(OUT / f"{a.world}_b{a.beta:g}_c{a.capture:g}_s{a.seed}.json", out)
    print(f"{a.world} beta {a.beta} capture {a.capture} reps {a.reps} seed {a.seed}: {out['seconds']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
