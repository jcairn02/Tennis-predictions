"""Read compare.py's scores by kind of change: what the comparison can see, and what decides.

The owner's decision of 9 Oct 2026 (docs/decisions/2026-10-09-adoption-by-change-class.md, with its errata; the
adoption framework, docs/studies/adoption_framework/README.md, sections 0, 4, 10 and 11). compare.py says what a reading
is; this says what the reading can decide. compare.py itself is unchanged: the level-evidence study's scorer imports
its recipe.

For one row of a compare.py scores.csv (default: both stages, both tours):
    * THE RESOLUTION: the 95% interval's half-width (compare.py's t interval). A true effect that size is detected about
      half the time; effect_80 = 2.8 x SE is detected 80% of the time.
    * BELOW RESOLUTION when the kind's plausible effect is smaller than the resolution. BLIND when, in addition, the
      reading itself is unresolved (its interval spans 0): the comparison saw nothing it could see.
    * HARM: worse by more than --tolerance (0.10 mLL) with the whole 95% interval below 0. A SMALL HARM: worse, with the
      interval below 0, but inside the tolerance.
    * THE KIND'S DECISION:
        repair       adopt unless harm (then check the fix for a bug). A small harm is reported, not a veto: a correct
                     fix is not vetoed by its outcome.
        expansion    needs --route-supported: the data enters by a route its statistic-level evidence supports.
        accretion    Then adopt unless harm; on a small harm, re-examine the route before adopting.
        holdback     the template with every adopted change against the latest frozen instance carrying every
                     structural change (errata E1): keep the adopted changes unless harm (then bisect them). Blind, it
                     says the control cannot see the batch.
        feature      admit to the pool as a lead, recording the seasons read (section 11); on harm, check for a bug or
                     leak first. Only a feature whose reading is not blind and that clears the arithmetic is adopted
                     alone.
        tuning       needs --k >= 2 (the variants it was picked from). Blind: keep the default. Otherwise the
                     arithmetic, after the winner's luck; a variant that does not clear keeps the default.
        structural   blind: undecided (decide on mechanism, cost and the realisation gate). Otherwise the arithmetic.
      THE ARITHMETIC: adopt when B*(est - sel) + (1 - B)*mu0 > cost, with B = tau^2 / (tau^2 + se^2) and
      sel = se * m_K * sqrt(1 - rho). A harm-checked kind given a cost above 0 (a new live feed) is weighed by it too:
      a costly change pays for itself (errata E6).
    * INPUT FLAGS: compare.py's summary.json beside scores.csv lists the inputs it flagged. Where any exist, a
      harm-checked kind's "adopt" or "keep" waits on reading them against the dose.
The kinds' defaults are the framework's starting values (section 0); each can be overridden. Positive = the candidate
better, compare.py's sign. The kind is declared before the reading is read (section 0).

Writes <scores folder>/adoption_read.json unless --out is given.
Run: ./python.sh src/eda/current_best_model/adoption_read.py --scores <folder>/scores.csv --kind <kind>
         [--route-supported] [--population "both tours"] [--comparison "both stages: candidate vs reference"]
         [--plausible X] [--mu0 X] [--tau X] [--cost X] [--k K] [--rho R] [--tolerance X] [--out <json>]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import pandas as pd
from scipy import integrate
from scipy.stats import norm

TOLERANCE = 0.10          # mLL: the harm rule's tolerance (the form of the owner's Roland Garros rule)
EFFECT_80 = 2.8           # SEs: the true effect detected 80% of the time at the 95% level

# mode, plausible effect (mLL), mu0, tau, cost: the adoption framework's starting values (README section 0)
KINDS = {
    "accretion": dict(mode="harm", plausible=0.005, mu0=None, tau=None, cost=0.0),
    "repair": dict(mode="harm", plausible=0.02, mu0=None, tau=None, cost=0.0),
    "expansion": dict(mode="harm", plausible=0.03, mu0=None, tau=None, cost=0.0),
    "holdback": dict(mode="harm", plausible=0.1, mu0=None, tau=None, cost=0.0),
    "feature": dict(mode="pool", plausible=0.01, mu0=-0.028, tau=0.03, cost=0.01),
    "structural": dict(mode="evidence", plausible=0.2, mu0=0.0, tau=0.2, cost=0.0),
    "tuning": dict(mode="evidence", plausible=0.03, mu0=0.0, tau=0.03, cost=0.0),
}
PRIMARY = ("both tours", "both stages: candidate vs reference")


def m_k(k: int) -> float:
    """The expected maximum of k independent standard normals (the winner's luck, in SEs). m_1 = 0."""
    if k < 1:
        raise ValueError("k must be at least 1")
    if k == 1:
        return 0.0
    value, _ = integrate.quad(lambda x: x * k * norm.pdf(x) * norm.cdf(x) ** (k - 1), -math.inf, math.inf)
    return float(value)


def is_harm(estimate: float, hi: float, tolerance: float = TOLERANCE) -> bool:
    """Worse by more than the tolerance, with the whole 95% interval below 0."""
    return bool(estimate < -tolerance and hi < 0)


def arithmetic(estimate: float, se: float, mu0: float, tau: float, cost: float, k: int = 1, rho: float = 0.0) -> dict:
    """B*(est - sel) + (1 - B)*mu0 against the cost (the framework's section 4)."""
    b = tau ** 2 / (tau ** 2 + se ** 2) if tau > 0 else 0.0
    sel = se * m_k(k) * math.sqrt(max(0.0, 1.0 - rho))
    posterior = b * (estimate - sel) + (1.0 - b) * mu0
    return {"B": b, "m_K": m_k(k), "k": k, "rho": rho, "sel": sel, "mu0": mu0, "tau": tau, "cost": cost,
            "posterior": posterior, "clears_cost": bool(posterior > cost)}


def _harm_kind(out: dict, kind: str, d: dict, cost: float, mu0, tau, route_supported: bool,
               input_flags: list[str]) -> dict:
    est, se, harm, small, blind = out["estimate"], out["se"], out["harm"], out["small_harm"], out["blind"]
    if kind == "expansion" and not route_supported:
        out["decision"] = "undecided: name the route first"
        out["reason"] = ("an expansion is adopted on its route: say how the data enters and which statistic-level "
                         "evidence supports it, then pass --route-supported")
        return out
    if kind == "holdback":
        if harm:
            out["decision"], out["reason"] = "bisect the adopted changes", "the batch shows harm"
        elif blind:
            out["decision"] = "below resolution: the control cannot see this batch"
            out["reason"] = ("compare with the latest frozen instance carrying every structural change (errata E1), "
                             "or wait for a larger batch")
        else:
            out["decision"], out["reason"] = "keep the adopted changes", "the batch shows no harm"
        if input_flags and not harm:
            out["decision"] += ", pending the input check"
        return out
    if cost > 0:
        a = arithmetic(est, se, 0.0 if mu0 is None else mu0, d["plausible"] if tau is None else tau, cost)
        out["arithmetic"] = a
        if harm or not a["clears_cost"]:
            out["decision"] = "do not adopt: harm" if harm else "do not adopt: does not pay for its cost"
            out["reason"] = "a costly change pays for itself (errata E6)"
            return out
    if harm:
        out["decision"] = "do not adopt: harm"
        out["reason"] = "worse by more than the tolerance, with the whole 95% interval below 0"
        if kind == "repair":
            out["reason"] += "; check the fix for a bug"
    elif small and kind in ("expansion", "accretion"):
        out["decision"] = "re-examine the route before adopting"
        out["reason"] = ("a small harm is visible (worse, inside the tolerance): ignore, down-weight or transform the "
                         "data and compare again (errata E4)")
    else:
        out["decision"] = "adopt"
        out["reason"] = "decided by the kind's direction; the reading shows no harm"
        if small:
            out["reason"] += "; a small harm is visible and reported, but a correct fix is not vetoed by its outcome"
    if input_flags and out["decision"] == "adopt":
        out["decision"] = "adopt, pending the input check"
        out["reason"] += f"; read the {len(input_flags)} flagged inputs against the dose"
    return out


def read(row: dict, kind: str, plausible: float | None = None, mu0: float | None = None, tau: float | None = None,
         cost: float | None = None, k: int | None = None, rho: float = 0.0, tolerance: float = TOLERANCE,
         route_supported: bool = False, input_flags: list[str] | None = None) -> dict:
    """The reading of one compare.py row, by kind. row needs estimate, lo, hi and se."""
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {', '.join(KINDS)}")
    d = KINDS[kind]
    est, lo, hi, se = (float(row[c]) for c in ("estimate", "lo", "hi", "se"))
    if any(math.isnan(v) for v in (est, lo, hi, se)):
        raise ValueError("the row has no estimate or interval")
    if kind == "tuning" and (k is None or k < 2):
        raise ValueError("tuning needs --k >= 2: the number of variants the candidate was picked from")
    k = 1 if k is None else k
    plausible = d["plausible"] if plausible is None else plausible
    cost = d["cost"] if cost is None else cost
    resolution = (hi - lo) / 2.0
    below = bool(plausible < resolution)
    flags = list(input_flags or [])
    out = {"kind": kind, "mode": d["mode"], "estimate": est, "lo": lo, "hi": hi, "se": se,
           "reading": row.get("reading"), "p_better": row.get("p_better"),
           "resolution": resolution, "effect_80": EFFECT_80 * se, "plausible": plausible,
           "below_resolution": below, "blind": bool(below and lo <= 0 <= hi), "tolerance": tolerance,
           "harm": is_harm(est, hi, tolerance), "small_harm": bool(hi < 0 and not is_harm(est, hi, tolerance)),
           "input_flags": flags}
    if d["mode"] == "harm":
        return _harm_kind(out, kind, d, cost, mu0, tau, route_supported, flags)
    a = arithmetic(est, se, d["mu0"] if mu0 is None else mu0, d["tau"] if tau is None else tau, cost, k, rho)
    out["arithmetic"] = a
    if d["mode"] == "pool":
        if out["harm"]:
            out["decision"] = "check for a bug or leak first; then admit to the pool as a lead"
            out["reason"] = "a single feature that harms beyond the tolerance is more often a bug than a signal"
        elif not out["blind"] and a["clears_cost"]:
            out["decision"] = "adopt (a feature big enough to test alone)"
            out["reason"] = "visible, and B*(est - sel) + (1 - B)*mu0 exceeds the cost (section 11's exception)"
        else:
            out["decision"] = "admit to the pool as a lead"
            out["reason"] = ("it has read results: record the seasons it read; a selection round decides "
                             "(section 11)" + ("; the reading is blind" if out["blind"] else ""))
        return out
    if out["blind"]:
        if kind == "tuning":
            out["decision"], out["reason"] = "keep the default", "blind: the reading cannot choose among the variants"
        else:
            out["decision"] = "undecided: below resolution"
            out["reason"] = "the reading cannot see the plausible effect; decide on mechanism, cost and the realisation gate"
        return out
    if a["clears_cost"]:
        out["decision"] = "adopt the variant" if kind == "tuning" else "adopt"
        out["reason"] = "B*(est - sel) + (1 - B)*mu0 exceeds the cost"
    else:
        out["decision"] = "keep the default" if kind == "tuning" else "do not adopt"
        out["reason"] = "B*(est - sel) + (1 - B)*mu0 does not exceed the cost"
    return out


def pick(scores: pd.DataFrame, population: str, comparison: str) -> dict:
    hit = scores[(scores["population"] == population) & (scores["comparison"] == comparison)]
    if len(hit) != 1:
        raise SystemExit(f"{len(hit)} rows for population {population!r} and comparison {comparison!r}")
    return hit.iloc[0].to_dict()


def flagged_inputs(scores_path: Path) -> list[str]:
    """The inputs compare.py flagged ('uneven' or 'every season'), from summary.json beside scores.csv, if present."""
    summary = scores_path.with_name("summary.json")
    if not summary.exists():
        return []
    rows = json.loads(summary.read_text(encoding="utf-8")).get("inputs_flagged") or []
    return [f"{r.get('input')} ({r.get('flag')})" for r in rows]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scores", required=True, help="compare.py's scores.csv")
    ap.add_argument("--kind", required=True, choices=sorted(KINDS))
    ap.add_argument("--route-supported", action="store_true",
                    help="expansion: the data enters by a route its statistic-level evidence supports")
    ap.add_argument("--population", default=PRIMARY[0])
    ap.add_argument("--comparison", default=PRIMARY[1])
    ap.add_argument("--plausible", type=float, help="the change's plausible effect, mLL (default: the kind's)")
    ap.add_argument("--mu0", type=float)
    ap.add_argument("--tau", type=float)
    ap.add_argument("--cost", type=float)
    ap.add_argument("--k", type=int, help="the variants the candidate was picked from (tuning: required, >= 2)")
    ap.add_argument("--rho", type=float, default=0.0, help="how much the variants' noise overlaps (0 to 1)")
    ap.add_argument("--tolerance", type=float, default=TOLERANCE)
    ap.add_argument("--out", help="the JSON written (default: adoption_read.json beside scores.csv)")
    a = ap.parse_args(argv)
    path = Path(a.scores)
    row = pick(pd.read_csv(path), a.population, a.comparison)
    res = read(row, a.kind, a.plausible, a.mu0, a.tau, a.cost, a.k, a.rho, a.tolerance, a.route_supported,
               flagged_inputs(path))
    res.update({"scores": str(path), "population": a.population, "comparison": a.comparison})
    out = Path(a.out) if a.out else path.with_name("adoption_read.json")
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"{a.comparison}, {a.population} (mLL, + = the candidate better): {res['estimate']:+.3f} "
          f"[{res['lo']:+.3f}, {res['hi']:+.3f}], {res['reading']}")
    print(f"resolution ±{res['resolution']:.3f} (80% power at {res['effect_80']:.3f}); the {a.kind} kind's plausible "
          f"effect {res['plausible']:.3f}: " + ("blind" if res["blind"] else "below resolution" if
                                                res["below_resolution"] else "visible"))
    if "arithmetic" in res:
        x = res["arithmetic"]
        print(f"B {x['B']:.2f}, sel {x['sel']:.3f}, mu0 {x['mu0']:+.3f}: B*(est - sel) + (1 - B)*mu0 = "
              f"{x['posterior']:+.4f} against a cost of {x['cost']:.3f}")
    print(f"harm (worse by more than {res['tolerance']:.2f}, interval below 0): {'yes' if res['harm'] else 'no'}"
          + ("; a small harm is visible" if res["small_harm"] else ""))
    if res["input_flags"]:
        print("inputs flagged by compare.py: " + ", ".join(res["input_flags"]))
    print(f"decision: {res['decision']} ({res['reason']})")
    print(f"written: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
