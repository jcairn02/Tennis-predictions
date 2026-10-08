"""R4 test verifier, part 5: the sign and definition of every endpoint of score.py (P2, S0-S14), on SYNTHETIC outcomes.

A full world is injected into score.py's Bank: every arm the scorer reads (model, spd, spd_raw, spd_all, spd_noodds,
model_noodds; seeds 0-15 in every season 2019-2026, independent seed noise of the measured structure), the early-price
blocks of model and spd in 2025-2026, and SYNTHETIC Polymarket prices (p_early_a, p_close_a) on the real priced rows.
No real price is related to any feature: the early forecasts and both prices are built here.

Truth (log-odds): a_tour mu + BETA spd_f + GAMMA spd_raw0 for men (spd_raw0 = spd_raw with NaN -> 0), a_tour mu +
BETA spd_f_all for women; mu = the base's real 16-seed log-odds.
    improve   that truth in every season: each arm captures part of the term its own column carries, so every gain the
              pre-registration signs "positive = the arm better" must read positive
    harm      the same arms and the same truth up to 2023, the speed terms REVERSED in 2024-2026: every such gain must
              read negative (S10, the direction TabPFN moved, stays positive; S13 stays positive)
Arms (center log-odds; seed noise added per seed):
    model         mu                                       spd (A1)       mu + c1 / a (BETA spd_f)
    spd_raw (A2)  mu + c2 / a (GAMMA spd_raw0)                spd_all (A3)   mu + c3 / a (BETA spd_f_all), c3 > c1
    model_noodds  0.85 mu                                  spd_noodds     0.85 mu + c1 / a (BETA spd_f)
    early (2025-26, priced rows): model mu + d, spd mu + d + c1 / a (BETA spd_f), d ~ N(0, 0.1^2) per match
Synthetic prices (priced rows): logit p_early = truth - LAMBDA BETA spd_f + N(0, 0.15^2); logit p_close = truth +
N(0, 0.05^2): the 30-minute price moves toward the speed term (S6's move must then read positive where A1 is right).

S13 is also checked against synthetic closes: a perfect close (p_mkt = the truth: S13 must be negative), an
over-confident perfect close (logit p_mkt = 1.25 truth: the decided recalibration must recover it, S13 negative) and the
real close in a world whose truth is the base (S13 positive).

Writes data/studies/serve_speed_tabpfn/design/verifier_signs.json (verifier_signs_<tag>.json with --tag <tag>).
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_signs.py [--tag reverify]
"""
from __future__ import annotations

import json
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

OUT = C.OUT / "design" / "verifier_signs.json"
BETA, GAMMA, LAMBDA = 0.5, 0.25, 0.5
C1, C2, C3 = 0.5, 0.5, 0.8
ARMS = ("model", "spd", "spd_raw", "spd_all", "model_noodds", "spd_noodds")


def columns(W: V.World) -> dict:
    info = W.info
    raw0 = info["spd_raw"].fillna(0.0).to_numpy(float)
    return {"z": W.z, "z_all": info["spd_f_all"].to_numpy(float), "raw0": np.where(W.atp, raw0, 0.0)}


def truth_logit(W: V.World, cols: dict, reverse_test: bool) -> np.ndarray:
    term = np.where(W.atp, BETA * cols["z"] + GAMMA * cols["raw0"], BETA * cols["z_all"])
    if reverse_test:
        term = np.where(np.isin(W.season, S.TEST), -term, term)
    return W.a_row * W.mu + term


def full_world(W: V.World, rng, reverse_test: bool):
    """(bank with every arm injected, info with synthetic prices, y, truth) for one world."""
    cols = columns(W)
    a = V.A_TOUR["atp"]
    truth = truth_logit(W, cols, reverse_test)
    y = pd.Series((rng.random(len(W.info)) < expit(truth)).astype(float), index=W.info.index)
    centers = {"model": W.mu, "spd": W.mu + C1 / a * BETA * cols["z"],
               "spd_raw": W.mu + C2 / a * GAMMA * cols["raw0"],
               "spd_all": W.mu + C3 * BETA * cols["z_all"] / W.a_row,
               "model_noodds": 0.85 * W.mu, "spd_noodds": 0.85 * W.mu + C1 / a * BETA * cols["z"]}
    d = rng.normal(0, 0.1, len(W.info))
    early_centers = {"model": W.mu + d, "spd": W.mu + d + C1 / a * BETA * cols["z"]}
    info = W.info.copy()
    priced = (info["has_early"].to_numpy(bool) & np.isfinite(info["p_early_a"].to_numpy(float))
              & np.isfinite(info["p_close_a"].to_numpy(float)))
    early_logit = truth - LAMBDA * BETA * cols["z"] * np.where(np.isin(W.season, S.TEST) & reverse_test, -1, 1) \
        + rng.normal(0, 0.15, len(info))
    close_logit = truth + rng.normal(0, 0.05, len(info))
    info.loc[priced, "p_early_a"] = expit(early_logit[priced])
    info.loc[priced, "p_close_a"] = expit(close_logit[priced])
    bank = S.Bank(W.P, W.fx, require_checks=False)
    for arm in ARMS:
        for (s, k), ser in V.synth_seeds(W, rng, centers[arm]).items():
            bank.injected[(arm, s, k)] = {"td": ser}
    for arm in ("model", "spd"):
        for (s, k), ser in V.synth_seeds(W, rng, early_centers[arm]).items():
            if s in C.PRICE_SEASONS:
                rows = priced[W.rows[s]]
                bank.injected[(arm, s, k)]["early"] = ser[rows]
    return bank, info, y, truth


EXPECT = {  # cid -> (sign in the improve world, sign in the harm world); 0 = no planted information (expected ~0)
    "P2": (1, -1), "S0": (1, -1), "S1_2024": (1, -1), "S1_2025": (1, -1), "S1_2026": (1, -1), "S2": (1, -1),
    "S3_both": (1, -1), "S3_one": (1, -1), "S3_neither": (1, -1), "S4_A1_women": (0, 0), "S4_A1_both": (1, -1),
    "S4_A3_women": (1, -1), "S4_A3_women_no_conflict": (1, -1), "S5": (1, -1), "S6_early_all": (1, -1),
    "S6_early_clean": (1, -1), "S6_move_odds_all": (1, -1), "S6_move_odds_clean": (1, -1),
    "S6_move_noodds_all": (1, -1), "S6_move_noodds_clean": (1, -1), "S7": (1, -1), "S8_A2": (1, -1),
    "S8_A3": (1, -1), "S8_A1_vs_A2": (1, -1), "S8_A3_vs_A1": (1, -1), "S9_shrunk": (1, -1), "S9_mle": (1, -1),
    "S10": (1, 1), "S11_block_only": (1, -1), "S11_week": (1, -1), "S12": (1, -1), "S13": (1, 1), "S14": (1, -1)}


def flatten(res: dict) -> dict:
    rows = {r["cid"]: r for r in [res["P2"]] + S.secondary_rows(res)}
    s10 = res["S10"]
    rows["S10"] = {"cid": "S10", "estimate": s10["applied_slope_a"], "direction": s10["direction"],
                   "unit": s10["unit"]}
    return rows


def judge(rows: dict, world: int) -> list[dict]:
    out = []
    for cid, (e_imp, e_harm) in EXPECT.items():
        e = (e_imp, e_harm)[world]
        r = rows.get(cid)
        if r is None:
            out.append({"cid": cid, "present": False, "pass": False})
            continue
        est, lo, hi = r["estimate"], r.get("lo"), r.get("hi")
        if e == 0:
            ok = lo is not None and lo <= 0 <= hi                      # no planted information: a tie
        else:
            ok = np.sign(est) == e                                     # the sign check (part 5's question)
        excl = None if lo is None else bool(lo > 0 or hi < 0)
        out.append({"cid": cid, "present": True, "expected_sign": e, "estimate": est, "lo": lo, "hi": hi,
                    "interval_excludes_0": excl, "unit": r.get("unit"), "direction": r.get("direction"),
                    "matches": r.get("matches"), "pass": bool(ok)})
    return out


def s13_worlds(W: V.World, rng, p2: dict) -> list[dict]:
    """S13 against closes in worlds without any speed term (nothing here involves z):
        A  truth = a mu (the base is right), the real close            -> the base better: S13 > 0
        B  truth = a mu + d, d ~ N(0, 0.3^2) known to the close only;  p_mkt = expit(truth)      -> S13 < 0
        C  as B with an over-confident close, logit p_mkt = 1.25 truth  -> after the decided recalibration S13 < 0"""
    d = rng.normal(0, 0.3, len(W.info))
    bank = S.Bank(W.P, W.fx, require_checks=False)
    for (s, k), ser in V.synth_seeds(W, rng, W.mu).items():
        bank.injected[("model", s, k)] = {"td": ser}
    out = []
    for name, truth, p_mkt, expect in (
            ("A: real close, truth = the base", W.a_row * W.mu, W.info["p_mkt"].to_numpy(float), 1),
            ("B: close knows d (p_mkt = truth)", W.a_row * W.mu + d, expit(W.a_row * W.mu + d), -1),
            ("C: over-confident close knows d (logit p_mkt = 1.25 truth)", W.a_row * W.mu + d,
             expit(1.25 * (W.a_row * W.mu + d)), -1)):
        y = pd.Series((rng.random(len(W.info)) < expit(truth)).astype(float), index=W.info.index)
        info = W.info.assign(p_mkt=p_mkt)
        sc = S.Scorer(bank, info, y)
        r = S.close_edge(sc, p2)
        ids = S.population_ids(info, "men", S.TEST)
        yy = y.reindex(ids).to_numpy()
        qb, _ = sc.forecast("model", S.SEEDS16, S.TEST, "td", "calibrated", ids)
        raw_close = 1000 * float(np.mean(C.ll(info.loc[ids, "p_mkt"].to_numpy(float), yy) - C.ll(qb, yy)))
        slopes = {s: sc.price_slopes(s) for s in S.TEST}
        ok = (r["lo"] > 0) if expect > 0 else (r["hi"] < 0)
        out.append({"world": name, "S13": r["estimate"], "lo": r["lo"], "hi": r["hi"], "expected_sign": expect,
                    "pass": bool(ok), "uncalibrated_close_minus_base_mLL": raw_close,
                    "close_slopes_atp": {str(s): v["atp"] for s, v in slopes.items()},
                    "ratio_P2_to_S13": r["ratio_P2_to_S13"], "direction": r["direction"]})
    return out


def main() -> int:
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else None
    out_path = OUT.with_name(f"verifier_signs_{tag}.json") if tag else OUT
    W = V.World()
    rng = np.random.default_rng(20261007)
    report = {"what": "signs of every endpoint on synthetic outcomes (planted improvement and planted reversal); no "
                      "match result read; prices synthetic", "beta": BETA, "gamma": GAMMA, "capture": [C1, C2, C3],
              "lambda": LAMBDA, "scorer_code_sha256": C.code_hash(), "tag": tag, "worlds": {}}
    p2_keep = None
    for world, name in ((0, "improve"), (1, "harm")):
        bank, info, y, _ = full_world(W, rng, reverse_test=bool(world))
        res = S.evaluate(S.Scorer(bank, info, y))
        rows = flatten(res)
        judged = judge(rows, world)
        if world == 0:
            p2_keep = res["P2"]
        report["worlds"][name] = {"decision": res["decision"], "multiplicity": res["multiplicity"],
                                  "S9_parameters": res["S9_parameters"], "endpoints": judged,
                                  "unavailable": [r for r in res.get("paired_secondaries", []) if not r.get("available", True)],
                                  "all_pass": all(j["pass"] for j in judged)}
    report["S13_closes"] = s13_worlds(W, rng, p2_keep)
    report["passed"] = (all(w["all_pass"] for w in report["worlds"].values())
                        and all(r["pass"] for r in report["S13_closes"])
                        and report["worlds"]["improve"]["decision"]["row"] == 1
                        and report["worlds"]["harm"]["decision"]["row"] == 2)
    C.write_json(out_path, report)
    for name, w in report["worlds"].items():
        print(f"== {name}: decision row {w['decision']['row']}; unavailable {len(w['unavailable'])}")
        for j in w["endpoints"]:
            if j["present"]:
                lo = "" if j["lo"] is None else f"[{j['lo']:+.3f}, {j['hi']:+.3f}]"
                tie = " (tie)" if j["interval_excludes_0"] is False else ""
                print(f"  {'ok ' if j['pass'] else 'BAD'} {j['cid']:<26} expect {j['expected_sign']:+d}  "
                      f"{j['estimate']:+.4f} {lo}{tie}  {j['unit']}")
            else:
                print(f"  BAD {j['cid']} missing")
    for r in report["S13_closes"]:
        print(f"  {'ok ' if r['pass'] else 'BAD'} S13 {r['world']}: {r['S13']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}] "
              f"(uncalibrated close minus base {r['uncalibrated_close_minus_base_mLL']:+.2f}); slopes {r['close_slopes_atp']}")
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
