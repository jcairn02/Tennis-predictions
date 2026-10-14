"""Tests of the lean review's T2 code (src/eda/lean_review/): the arms, the opening-line filter, the pre-declared
decision rule and the realisation regression. No result is read; the rule is tested on made-up readings."""
import json

import numpy as np
import pytest

from src.eda.lean_review import common as L
from src.eda.lean_review import score as SC


def instance_inputs():
    meta = json.loads(L.INPUTS.read_text(encoding="utf-8"))
    return [d["name"] for d in meta["inputs"]], {d["name"]: d["kind"] for d in meta["inputs"]}


def test_arms_drop_exactly_the_profile_and_the_short_memory():
    names, kinds = instance_inputs()
    assert len(names) == 58
    assert len(L.PROFILE) == 21 and len(set(L.PROFILE)) == 21
    assert set(L.PROFILE) <= set(names) and set(L.SHORT) <= set(names)
    assert L.ARMS["A0"] == [] and L.ARMS["A3"] == L.PROFILE + L.SHORT
    for arm, drop in L.ARMS.items():
        assert all(kinds[d] == "diff" for d in drop), f"{arm} would break a pair or drop context"
    assert {n for n in names if n.startswith(("iosO_", "iosD_", "prod_"))} == set(L.PROFILE)


def test_reasons_keeps_only_coherent_pre_start_lines_outside_the_2021_us_open():
    p = np.array([0.6, np.nan, 0.6, 0.6, 0.6, 0.6, 0.6])
    after = np.array([-60.0, -60.0, np.nan, 5.0, -60.0, -60.0, 0.0])
    date = np.array(["2022-05-01", "2022-05-01", "2022-05-01", "2022-05-01", "2021-08-30", "2021-08-30", "2022-05-01"])
    level = np.array([2.0, 2.0, 2.0, 2.0, 0.0, 3.0, 2.0])
    why = L.reasons(p, after, date, level)
    assert why.tolist() == ["kept", "no coherent opening line", "no stamp", "stamped after the listed start",
                            "2021 US Open (recording failed)", "kept", "kept"]


def reading(est, se, p):
    return {"estimate": est, "se": se, "p_better": p}


def test_decide_prefers_both_when_it_qualifies():
    o = {"both": reading(-0.05, 0.08, 0.27), "profile": reading(-0.04, 0.08, 0.31), "short": reading(0.0, 0.03, 0.5)}
    c = {k: reading(0.0, 0.05, 0.5) for k in o}
    d = SC.decide(o, c)
    assert d["removals"]["both"]["eligible"]
    assert d["proposal"] == "both"


def test_decide_picks_the_single_removal_with_the_larger_score():
    o = {"both": reading(-0.20, 0.08, 0.01), "profile": reading(-0.20, 0.08, 0.01), "short": reading(0.01, 0.03, 0.6)}
    c = {k: reading(0.0, 0.05, 0.5) for k in o}
    d = SC.decide(o, c)
    assert not d["removals"]["both"]["qualifies"] and not d["removals"]["profile"]["qualifies"]
    assert d["removals"]["short"]["qualifies"]
    assert d["proposal"] == "short"


def test_decide_veto_and_neither():
    o = {"both": reading(0.10, 0.08, 0.9), "profile": reading(-0.30, 0.08, 0.0), "short": reading(-0.10, 0.03, 0.0)}
    c = {"both": reading(-0.15, 0.04, 0.0), "profile": reading(0.0, 0.05, 0.5), "short": reading(0.0, 0.05, 0.5)}
    d = SC.decide(o, c)
    assert d["removals"]["both"]["qualifies"] and d["removals"]["both"]["vetoed"]
    assert not d["removals"]["profile"]["qualifies"] and not d["removals"]["short"]["qualifies"]
    assert d["proposal"] == "neither"


def test_decide_bar_matches_the_plan():
    # the profile at SE 0.08 (tau 0.1, c 0.05): remove iff est > -0.082 (arith_r2.out)
    for est, expect in ((-0.080, True), (-0.085, False)):
        o = {"both": reading(-1.0, 0.08, 0.0), "profile": reading(est, 0.08, 0.2), "short": reading(-1.0, 0.03, 0.0)}
        c = {k: reading(0.0, 0.05, 0.5) for k in o}
        assert SC.decide(o, c)["removals"]["profile"]["qualifies"] is expect


def test_t3_rule():
    from src.eda.lean_review import t3

    def rows(both, men, women, close):
        return {("O", "both tours"): reading(*both), ("O", "men"): reading(*men), ("O", "women"): reading(*women),
                ("C", "both tours"): reading(*close)}
    # unresolved everywhere: switch to pooled
    d = t3.decide(rows((0.02, 0.06, 0.6), (0.03, 0.09, 0.6), (0.01, 0.08, 0.5), (0.0, 0.05, 0.5)))
    assert d["proposal"] == "switch to pooled" and not d["clears_both"]
    # per surface clearly better at (O): B 0.41 at SE 0.06, so est 0.10 gives 0.041 > 0.01
    d = t3.decide(rows((0.10, 0.06, 0.95), (0.10, 0.09, 0.87), (0.10, 0.08, 0.9), (0.0, 0.05, 0.5)))
    assert d["proposal"] == "stay per surface"
    # men clear, women's per-surface reading worse with P <= 0.2: split
    d = t3.decide(rows((0.02, 0.06, 0.6), (0.20, 0.09, 0.99), (-0.10, 0.08, 0.1), (0.0, 0.05, 0.5)))
    assert d["split"] == {"atp": "per surface", "wta": "pooled"}
    # pooled worse at the close by more than 0.1: veto
    d = t3.decide(rows((0.0, 0.06, 0.5), (0.0, 0.09, 0.5), (0.0, 0.08, 0.5), (0.12, 0.05, 0.99)))
    assert d["veto"] and d["proposal"].startswith("stay per surface")


def test_realisation_recovers_a_known_slope():
    rng = np.random.default_rng(0)
    n = 40000
    lp = rng.normal(0, 1.2, n)
    d = rng.normal(0, 0.3, n)
    lam = 0.7
    y = (rng.random(n) < 1 / (1 + np.exp(-(lp + lam * d)))).astype(float)
    p, q = 1 / (1 + np.exp(-lp)), 1 / (1 + np.exp(-(lp + d)))
    r = SC.realisation(q, p, y, np.arange(n) // 400)
    assert r["lo"] < lam < r["hi"]
    assert r["price_slope"] == pytest.approx(1.0, abs=0.05)
