"""Tests of the level-evidence system's decision layer (src/eda/lower_level_evidence/system_decide.py): the owner's
decision of 9 Oct 2026 (owner_decision_2026-10-09.md, sections 1-5; addition 4), on synthetic readings only.

The harm rule's edges (an estimate of exactly -0.10; an interval touching 0), the switch rule (a "better" reading, not a
P(better) threshold; the largest gain; the winner's luck), REF only on harm, the recommendation (primary harm, Holm,
refusals), the rule test per tour with the RES_ONLY flag, and that the registered rules' outcome still computes beside
the amended one. No real score is read.
Run: ./python.sh -m pytest test/lower_level_evidence/test_system_decide.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import system_decide as SD  # noqa: E402
from src.eda.lower_level_evidence import system_pairs as SP  # noqa: E402


def r(est: float, lo: float, hi: float, se: float = 0.04, **kw) -> dict:
    """A reading with an explicit interval (the scorer's), named first-vs-second by the caller."""
    reading = "better" if lo > 0 else "worse" if hi < 0 else "unresolved"
    return {"estimate": est, "lo": lo, "hi": hi, "se": se, "p_better": SP.p_better(est, se),
            "p_better_t": SP.p_better(est, se), "reading": reading, **kw}


# ------------------------------------------------------------------------------------------------
# Section 1: harm

def test_harm_edges():
    assert SD.harm(r(-0.15, -0.25, -0.05))                     # worse by more than 0.10, interval below 0
    assert not SD.harm(r(-0.10, -0.20, -0.01))                 # exactly -0.10: not "more than"
    assert SD.harm(r(-0.1000001, -0.20, -0.01))
    assert not SD.harm(r(-0.20, -0.40, 0.0))                   # the interval touches 0: not wholly below
    assert SD.harm(r(-0.20, -0.40, -1e-9))
    assert not SD.harm(r(-0.20, -0.45, 0.05))                  # unresolved passes a harm check
    assert not SD.harm(r(-0.05, -0.08, -0.02))                 # resolved worse, but within the tolerance
    assert not SD.harm(None) and not SD.harm(r(float("nan"), float("nan"), float("nan")))


# ------------------------------------------------------------------------------------------------
# Sections 2-3: the selection

def sys_vs(**challengers):
    """'SYS vs C' readings (+ = SYS better); default: SYS ahead, unresolved."""
    out = {c: r(0.02, -0.05, 0.09) for c in SP.CHALLENGERS}
    out.update(challengers)
    return out


def vs_ref(**arms):
    out = {a: r(0.05, -0.02, 0.12) for a in ("SYS",) + SP.CHALLENGERS}
    out.update(arms)
    return out


def test_sys_stays_without_a_better_challenger():
    s = SD.select_amended(sys_vs(), vs_ref())
    assert s["status"] == "final" and s["selected"] == "SYS" and s["qualifying"] == []
    assert s["winner_after_winners_luck"] is None


def test_switch_needs_a_better_reading_not_a_probability():
    # SEP_ALL against SYS: gain 0.06 [-0.01, +0.13], P(better) about 0.93: the registered rule switches, the amended not
    readings = sys_vs(SEP_ALL=r(-0.06, -0.13, 0.01, se=0.04))
    amended = SD.select_amended(readings, vs_ref())
    registered = SP.select(readings, vs_ref())                 # the registered rules' outcome still computes
    assert amended["selected"] == "SYS" and amended["qualifying"] == []
    assert registered["selected"] == "SEP_ALL" and registered["qualifying"] == ["SEP_ALL"]


def test_largest_gain_among_better_readings_and_winners_luck():
    readings = sys_vs(SYS_w0=r(-0.15, -0.25, -0.05, se=0.05), SYS_NOCLASS=r(-0.30, -0.50, -0.10, se=0.10),
                      SYS_w100=r(-0.40, -0.85, 0.05, se=0.22))  # the largest gain, but not "better": out
    s = SD.select_amended(readings, vs_ref())
    assert set(s["qualifying"]) == {"SYS_w0", "SYS_NOCLASS"} and s["selected"] == "SYS_NOCLASS"
    w = s["winner_after_winners_luck"]
    assert w["challenger"] == "SYS_NOCLASS" and w["after_winners_luck_mLL"] == pytest.approx(0.30 - 1.35 * 0.10)
    assert w["figure"] == 1.35 and w["challengers"] == 5          # the owner's figure, five challengers beside it


def test_share_arms_read_better_but_sys_stays():
    """Erratum 1: R_S2 and SYS_S2 read better than SYS on dev; they are pool leads, not challengers."""
    readings = sys_vs(R_S2=r(-0.30, -0.50, -0.10, se=0.10), SYS_S2=r(-0.20, -0.35, -0.05, se=0.08))
    s = SD.select_amended(readings, vs_ref())
    assert s["selected"] == "SYS" and s["qualifying"] == [] and s["status"] == "final"
    assert set(s["not_challengers"]) == {"R_S2", "SYS_S2"}
    assert "R_S2" not in s["challenger_list"] and "SYS_S2" not in s["challenger_list"]
    registered = SP.select(readings, vs_ref())                 # its own seven challengers: it switches
    assert registered["selected"] == "R_S2" and set(registered["qualifying"]) == {"R_S2", "SYS_S2"}


def test_a_remaining_challenger_better_is_selected():
    readings = sys_vs(SYS_w100=r(-0.12, -0.20, -0.04, se=0.04), R_S2=r(-0.30, -0.50, -0.10, se=0.10))
    s = SD.select_amended(readings, vs_ref())
    assert s["qualifying"] == ["SYS_w100"] and s["selected"] == "SYS_w100"   # R_S2's larger gain does not count
    assert s["winner_after_winners_luck"]["after_winners_luck_mLL"] == pytest.approx(0.12 - 1.35 * 0.04)


def test_ref_only_on_harm():
    resolved_worse = vs_ref(SYS=r(-0.05, -0.09, -0.01))        # worse, but not harm: SYS stays
    assert SD.select_amended(sys_vs(), resolved_worse)["selected"] == "SYS"
    assert SP.select(sys_vs(), resolved_worse)["selected"] == "REF"   # the registered rule (P < 0.50) would go to REF
    harmed = vs_ref(SYS=r(-0.15, -0.25, -0.05))
    s = SD.select_amended(sys_vs(), harmed)
    assert s["selected"] == "REF" and s["step1_shows_harm_against_REF"]
    switched = SD.select_amended(sys_vs(SEP_ALL=r(-0.2, -0.3, -0.1)), vs_ref(SEP_ALL=r(-0.12, -0.2, -0.01)))
    assert switched["step1_arm"] == "SEP_ALL" and switched["selected"] == "REF"


def test_selection_incomplete_without_every_challenger():
    readings = sys_vs()
    readings["SYS_w50"] = None
    s = SD.select_amended(readings, vs_ref())
    assert s["status"] == "incomplete" and s["selected"] is None and s["missing_challengers"] == ["SYS_w50"]
    readings = sys_vs()
    readings["SYS_S2"] = None                                  # not a challenger any more: the selection stands
    assert SD.select_amended(readings, vs_ref())["status"] == "final"


# ------------------------------------------------------------------------------------------------
# Section 4: the recommendation

def holm(worse=(), complete=True):
    return {"complete": complete, "worse_after_holm": list(worse), "raw_worse": list(worse)}


def test_recommendation():
    unresolved = r(0.03, -0.09, 0.15, comparison="SYS vs REF")
    assert SD.recommend_amended(unresolved, holm(), "SYS")["recommend"] == "SYS"   # unresolved passes
    assert SD.recommend_amended(r(-0.05, -0.09, -0.01), holm(), "SYS")["recommend"] == "SYS"   # worse, within 0.10
    rec = SD.recommend_amended(r(-0.15, -0.28, -0.02), holm(), "SYS")
    assert rec["recommend"] == "REF" and rec["primary_shows_harm"] and rec["drivers"]
    rec = SD.recommend_amended(unresolved, holm(worse=["season 2026 / both stages"]), "SYS")
    assert rec["recommend"] == "REF" and rec["drivers"] == ["worse after Holm: season 2026 / both stages"]
    assert SD.recommend_amended(None, None, "REF")["recommend"] == "REF (no change)"
    with pytest.raises(SystemExit, match="never a fall back"):
        SD.recommend_amended(None, holm(), "SYS")
    with pytest.raises(SystemExit, match="incomplete"):
        SD.recommend_amended(unresolved, holm(complete=False), "SYS")


# ------------------------------------------------------------------------------------------------
# Section 5: the rule test

def getter(table: dict):
    return lambda a, b, tour: table.get((a, b, tour))


def test_rule_test_men_decide_women_wait():
    ok = {("NEW_SYS_BOTH", "SYS_BOTH", "men"): r(-0.06, -0.12, 0.0),     # unresolved: no harm
          ("NEW_SYS_BOTH", "SYS_BOTH", "women"): r(-0.30, -0.5, -0.1),   # harm, but women wait for P7
          ("NEW_ASIS", "REF", "men"): r(-0.4, -0.6, -0.2)}              # as-is harm: reported, not decisive
    t = SD.rule_test(getter(ok), SP.H, "SYS")
    assert t["tours"]["men"]["verdict"].startswith("recommended for entry")
    assert t["tours"]["women"]["verdict"].startswith("waits for P7") and t["tours"]["women"]["shows_harm"]
    assert t["tours"]["men"]["reported_not_decisive"]["NEW_ASIS vs REF"]["estimate"] == -0.4
    assert not t["register_RES_ONLY_on_C0_now_next"]
    bad = {("NEW_SYS_BOTH", "SYS_BOTH", "men"): r(-0.12, -0.2, -0.04)}
    assert SD.rule_test(getter(bad), SP.H, "SYS")["tours"]["men"]["verdict"].startswith("not recommended")
    assert SD.rule_test(getter({}), SP.H, "SYS")["tours"]["men"]["verdict"].startswith("not scored")


def test_res_only_flag_when_ref_is_recommended():
    t = SD.rule_test(getter({}), SP.H, "REF")
    assert t["register_RES_ONLY_on_C0_now_next"] and "RES_ONLY on C0_now" in t["flag"]
    assert SD.rule_test(getter({}), SP.H, "REF (no change)")["register_RES_ONLY_on_C0_now_next"]
    assert not SD.rule_test(getter({}), SP.H, None)["register_RES_ONLY_on_C0_now_next"]


# ------------------------------------------------------------------------------------------------
# The dev mode end to end on a synthetic scorer output

def scorer_rows(readings: dict) -> pd.DataFrame:
    rows = []
    for (first, second), x in readings.items():
        rows.append({"period": SD.DEV, "group": "g", "comparison": f"{first} vs {second}", "first": first,
                     "second": second, "stage": "both stages", "tour": "men", "population": "all", "matches": 100, **x})
    return pd.DataFrame(rows)


def test_dev_writes_the_selection_in_force_beside_the_registered(tmp_path, monkeypatch):
    res = tmp_path / "results"
    (res / "dev").mkdir(parents=True)
    monkeypatch.setattr(SP, "RESULTS", res)
    monkeypatch.setattr(SP, "SELECTION", res / "selection.json")
    monkeypatch.setattr(SP, "SELECTION_REGISTERED", res / "selection_registered.json")
    monkeypatch.setattr(SP, "UNLOCK", tmp_path / "holdout_unlock.json")
    monkeypatch.setattr(SD, "guards", lambda mode: {"preregistration": {}, "freeze": {}})
    readings = {("SYS", c): x for c, x in sys_vs(SEP_ALL=r(-0.06, -0.13, 0.01)).items()}
    readings.update({(a, "REF"): x for a, x in vs_ref().items()})
    scorer_rows(readings).to_csv(res / "dev" / "pairs.csv", index=False)
    reg = SP.select({c: readings[("SYS", c)] for c in SP.CHALLENGERS},
                    {a: readings[(a, "REF")] for a in ("SYS",) + SP.CHALLENGERS})
    (res / "selection_registered.json").write_text(json.dumps({**reg, "sides_parquet_sha256": "abc"}))
    SD.dev()
    sel = json.loads((res / "selection.json").read_text())
    assert sel["decision_layer"] == SP.DECISION_LAYER and sel["status"] == "final"
    assert sel["selected"] == "SYS" and sel["registered_rules_outcome"]["selected"] == "SEP_ALL"
    assert sel["agrees_with_registered_rules"] is False and sel["sides_parquet_sha256"] == "abc"
    assert sel["challenger_list"] == list(SD.CHALLENGERS)
    dec = json.loads((res / "dev" / "decision.json").read_text())
    assert dec["rule_test_2018_2024"]["tours"]["men"]["verdict"].startswith("not scored")
    lead = dec["pool_lead_evidence"]
    assert lead["label"] == SD.POOL_LABEL and lead["men"]["SYS vs R_S2"]["estimate"] == 0.02


def test_dev_refuses_once_the_unlock_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(SP, "UNLOCK", tmp_path / "holdout_unlock.json")
    (tmp_path / "holdout_unlock.json").write_text("{}")
    monkeypatch.setattr(SP, "verify_prereg", lambda *a, **k: {})
    monkeypatch.setattr(SP, "require_cp1", lambda *a, **k: {})
    with pytest.raises(SystemExit, match="unlock"):
        SD.dev()


def test_constants_are_the_owners():
    assert SD.HARM_MLL == 0.10 and SD.WINNERS_LUCK == 1.35
    assert SD.CHALLENGERS == ("SYS_w0", "SYS_w50", "SYS_w100", "SEP_ALL", "SYS_NOCLASS")      # erratum 1
    assert SD.POOL_LEADS == ("R_S2", "SYS_S2") and not set(SD.POOL_LEADS) & set(SD.CHALLENGERS)
    assert len(SP.CHALLENGERS) == 7 and set(SD.POOL_LEADS) <= set(SP.CHALLENGERS)          # the registered rules'
    assert "system_decide.py" in SP.CP1_CODE                  # the freeze covers the decision module
