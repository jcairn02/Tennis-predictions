"""R4 test verifier, part 7: seed sets and the empirical seed variance of score.py (synthetic outcomes).

    calls        every Bank.per_seed call of a full score.evaluate() in verifier_signs.full_world is recorded with the
                 endpoint that made it. For each paired comparison: the scored seasons read ONE seed set for both arms
                 (the comparison's), and every calibration read is seeds 0-3 over 2019 .. Y - 1. The other endpoints
                 (S0, S6 moves, S9, S10, S12, S13) are listed with their seed sets.
    tamper       a Bank that returns one seed fewer for the arm must make paired() refuse ("unequal seed sets").
    seed_var     P2's v_seed_base / v_seed_arm (16 seeds) and S8_A2's (8 seeds) equal surface_ios.score.seed_var on the
                 same per-seed calibrated forecasts (PL.SEEDS widened in memory to the comparison's seeds; the synthetic
                 outcomes are passed in a column that seed_var calls a_won).
    convention   surface_ios recalibrated each seed with its OWN slope; score.py calibrates each seed with the arm's
                 seed-mean slope (the audit's C6 wording). The base's seed variance under both, for scale.

Writes data/studies/serve_speed_tabpfn/design/verifier_seedsets.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_seedsets.py
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402
from src.eda.serve_speed_tabpfn.design import verifier_signs as VS  # noqa: E402
from src.eda.serve_speed_tabpfn.design import verifier_worlds as V  # noqa: E402
from src.eda.surface_ios import plan as SIPL  # noqa: E402
from src.eda.surface_ios import score as SI  # noqa: E402

OUT = C.OUT / "design" / "verifier_seedsets.json"


def record_calls(bank, info, y) -> tuple[dict, dict]:
    calls = defaultdict(list)
    current = {"tag": "?"}
    real = bank.per_seed

    def spy(arm, seeds, seasons, block="td"):
        calls[current["tag"]].append({"arm": arm, "seeds": list(seeds), "seasons": list(seasons), "block": block})
        return real(arm, seeds, seasons, block)
    bank.per_seed = spy
    originals = {n: getattr(S, n) for n in ("information", "capture", "moves", "nudge", "close_edge")}

    def wrap(name, fn):
        def inner(*a, **kw):
            prev = current["tag"]
            current["tag"] = name if name != "information" else f"information:{a[1]}"
            try:
                return fn(*a, **kw)
            finally:
                current["tag"] = prev
        return inner
    paired_real = S.Scorer.paired

    def paired(self, cmp, ids=None):
        prev = current["tag"]
        current["tag"] = cmp.cid
        try:
            return paired_real(self, cmp, ids)
        finally:
            current["tag"] = prev
    try:
        for n, fn in originals.items():
            setattr(S, n, wrap(n, fn))
        S.Scorer.paired = paired
        res = S.evaluate(S.Scorer(bank, info, y))
    finally:
        for n, fn in originals.items():
            setattr(S, n, fn)
        S.Scorer.paired = paired_real
        bank.per_seed = real
    return dict(calls), res


def paired_calls(bank, info, y) -> dict:
    """Each paired comparison in a FRESH Scorer (the slope cache would hide calibration reads), its per_seed reads."""
    out = {}
    real = bank.per_seed
    for cmp in S.COMPARISONS + [S.S14]:
        cl = []

        def spy(arm, seeds, seasons, block="td", cl=cl):
            cl.append({"arm": arm, "seeds": list(seeds), "seasons": list(seasons), "block": block})
            return real(arm, seeds, seasons, block)
        bank.per_seed = spy
        try:
            S.Scorer(bank, info, y).paired(cmp)
        finally:
            bank.per_seed = real
        out[cmp.cid] = cl
    return out


def check_paired(calls: dict) -> list[dict]:
    out = []
    for cmp in S.COMPARISONS + [S.S14]:
        cl = calls.get(cmp.cid, [])
        scored = [c for c in cl if tuple(c["seasons"]) == tuple(cmp.seasons)]
        cal = [c for c in cl if tuple(c["seasons"]) != tuple(cmp.seasons)]
        arms_seeds = {(c["arm"], tuple(c["seeds"])) for c in scored}
        ok_scored = arms_seeds == {(cmp.base, tuple(cmp.seeds)), (cmp.arm, tuple(cmp.seeds))}
        want_windows = {tuple(range(2019, Y)) for Y in cmp.seasons} if cmp.metric == "calibrated" else set()
        ok_cal = all(tuple(c["seeds"]) == C.CAL_SEEDS and c["block"] == "td" for c in cal) and \
            {tuple(c["seasons"]) for c in cal} == want_windows
        out.append({"cid": cmp.cid, "base": cmp.base, "arm": cmp.arm, "seeds": [min(cmp.seeds), max(cmp.seeds)],
                    "scored_reads": sorted(f"{a}:{min(s)}-{max(s)}" for a, s in arms_seeds),
                    "calibration_windows": sorted(f"{min(c['seasons'])}-{max(c['seasons'])} seeds "
                                                  f"{min(c['seeds'])}-{max(c['seeds'])} {c['arm']}" for c in cal),
                    "one_seed_set_both_arms": ok_scored, "calibration_seeds_0_3_windows_before_Y": ok_cal})
    return out


def other_endpoints(calls: dict) -> dict:
    out = {}
    for tag, cl in calls.items():
        if tag in {c.cid for c in S.COMPARISONS + [S.S14]}:
            continue
        out[tag] = sorted({f"{c['arm']} seeds {min(c['seeds'])}-{max(c['seeds'])} seasons {min(c['seasons'])}-"
                           f"{max(c['seasons'])} {c['block']}" for c in cl})
    return out


class ShortBank(S.Bank):
    """Returns one seed fewer for arm 'spd' (a tampered bank)."""

    def per_seed(self, arm, seeds, seasons, block="td"):
        out = super().per_seed(arm, seeds, seasons, block)
        return out.iloc[:, :-1] if arm == "spd" else out


def seed_var_equality(sc: S.Scorer, info, y) -> list[dict]:
    out = []
    for cmp in (S.PRIMARY, next(c for c in S.COMPARISONS if c.cid == "S8_A2")):
        ids = S.population_ids(info, cmp.population, cmp.seasons)
        r = sc.paired(cmp)
        _, qbk = sc.forecast(cmp.base, cmp.seeds, cmp.seasons, "td", "calibrated", ids)
        _, qak = sc.forecast(cmp.arm, cmp.seeds, cmp.seasons, "td", "calibrated", ids)
        g = pd.DataFrame({"a_won": y.reindex(ids).to_numpy()})        # SYNTHETIC outcomes (seed_var's column name)
        for k in cmp.seeds:
            g[f"q_{cmp.base}_s{k}"] = qbk[:, k]
            g[f"q_{cmp.arm}_s{k}"] = qak[:, k]
        saved = SIPL.SEEDS
        SIPL.SEEDS = tuple(cmp.seeds)
        try:
            vb, va = SI.seed_var(g, "q", cmp.base), SI.seed_var(g, "q", cmp.arm)
        finally:
            SIPL.SEEDS = saved
        out.append({"cid": cmp.cid, "seeds": len(cmp.seeds), "scorer_v_base": r["v_seed_base"],
                    "surface_ios_v_base": vb, "scorer_v_arm": r["v_seed_arm"], "surface_ios_v_arm": va,
                    "equal": bool(np.isclose(vb, r["v_seed_base"], rtol=1e-10, atol=0)
                                  and np.isclose(va, r["v_seed_arm"], rtol=1e-10, atol=0))})
    return out


def own_slope_variance(sc: S.Scorer, info, y) -> dict:
    """The base's seed variance on P2's rows with each seed calibrated by its own slope (surface_ios style; possible for
    the base, which has 16 seeds in 2019-2023) against the seed-mean slope (score.py)."""
    ids = S.population_ids(info, "men", S.TEST)
    yy = y.reindex(ids).to_numpy()
    per = sc.bank.per_seed("model", S.SEEDS16, S.TEST, "td").reindex(ids)
    inf = info.loc[ids]
    own = np.empty((len(ids), 16))
    for k in S.SEEDS16:
        for Y in S.TEST:
            hist = tuple(range(C.CALIB_FROM, Y))
            p = sc.bank.per_seed("model", (k,), hist, "td")
            hi = info.reindex(p.index)
            m = (~hi["debut"].to_numpy(bool)) & (hi["tour"].to_numpy() == "atp")
            beta, _ = C.fit_logistic(C.lg(p.to_numpy()[m, 0])[:, None], y.reindex(p.index[m]).to_numpy())
            rows = (inf["season"] == Y).to_numpy()
            own[rows, k] = expit(beta[0] * C.lg(per.to_numpy()[rows, k]))
    _, mean_slope = sc.forecast("model", S.SEEDS16, S.TEST, "td", "calibrated", ids)
    v_own = float(np.var(1000 * C.ll(own, yy[:, None]).mean(axis=0), ddof=1) / 16)
    v_mean = float(np.var(1000 * C.ll(mean_slope, yy[:, None]).mean(axis=0), ddof=1) / 16)
    return {"v_seed_base_own_slope": v_own, "v_seed_base_seed_mean_slope": v_mean, "ratio_own_to_mean": v_own / v_mean}


def main() -> int:
    W = V.World()
    rng = np.random.default_rng(707)
    bank, info, y, _ = VS.full_world(W, rng, reverse_test=False)
    calls, res = record_calls(bank, info, y)
    paired = check_paired(paired_calls(bank, info, y))
    sc = S.Scorer(bank, info, y)
    tb = ShortBank(W.P, W.fx, require_checks=False)
    tb.injected = bank.injected
    try:
        S.Scorer(tb, info, y).paired(S.PRIMARY)
        tamper = "NOT refused"
    except RuntimeError as e:
        tamper = f"refused: {e}"
    report = {"what": "seed sets of every comparison, the tamper refusal and the seed variance against "
                      "surface_ios.seed_var (synthetic outcomes)",
              "paired": paired, "other_endpoints": other_endpoints(calls), "tamper": tamper,
              "seed_var_equality": seed_var_equality(sc, info, y), "own_slope_convention": own_slope_variance(sc, info, y),
              "cal_seeds": list(C.CAL_SEEDS)}
    report["passed"] = (all(p["one_seed_set_both_arms"] and p["calibration_seeds_0_3_windows_before_Y"] for p in paired)
                        and tamper.startswith("refused") and all(r["equal"] for r in report["seed_var_equality"]))
    C.write_json(OUT, report)
    for p in paired:
        print(f"{p['cid']:<26} one set {p['one_seed_set_both_arms']}  cal 0-3 < Y {p['calibration_seeds_0_3_windows_before_Y']}"
              f"  {p['scored_reads']}")
    print(json.dumps(report["other_endpoints"], indent=1))
    print("tamper:", tamper)
    print(json.dumps(report["seed_var_equality"], indent=1))
    print(report["own_slope_convention"])
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
