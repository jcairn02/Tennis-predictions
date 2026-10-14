"""Tests of adoption_read.py: compare.py's scores read by kind of change (the owner's decision of 9 Oct 2026,
docs/decisions/2026-10-09-adoption-by-change-class.md, with its errata; the adoption framework's sections 0, 4, 10, 11).

Offline and synthetic, plus one read of a published compare.py output (the speed backfill's seed check), skipped if
absent:
    * the winner's luck m_K equals the framework's table (K = 2, 3, 4, 6, 10) and is 0 for one test;
    * the harm rule needs both: worse by more than the tolerance and the whole interval below 0; a small harm is worse
      with the interval below 0, inside the tolerance;
    * "below resolution" compares the kind's plausible effect with the 95% half-width; "blind" adds an unresolved reading;
    * the arithmetic tends to mu0 when the comparison is blind and to est - sel when sharp;
    * repair: adopt unless harm, and a small harm is no veto;
    * expansion: needs a supported route; a small harm sends it back to its route; a cost makes it pay for itself;
    * the holdback keeps, bisects, or says its control cannot see the batch;
    * a new feature goes to the pool as a lead (a harm first checks for a bug or leak), unless visible and clearing;
    * tuning needs k >= 2 and keeps the default when blind (the review's case: +0.01 [-0.07, +0.09]);
    * structural is undecided when blind, and decided by the arithmetic when the reading is resolved;
    * input flags in summary.json make an adoption wait on the input check;
    * a row of NaNs is refused; identical forecasts do not divide by zero;
    * the command line picks the declared row, refuses a missing one, and writes its JSON.

Run: ./python.sh -m pytest test/current_best_model -q
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import adoption_read as A  # noqa: E402

PRIMARY = {"population": "both tours", "comparison": "both stages: candidate vs reference"}


def row(estimate, lo, hi, se, reading="unresolved", p_better=0.5):
    return {"estimate": estimate, "lo": lo, "hi": hi, "se": se, "reading": reading, "p_better": p_better}


def test_winners_luck_matches_the_framework_table():
    table = {2: 0.56, 3: 0.85, 4: 1.03, 6: 1.27, 10: 1.54}
    for k, want in table.items():
        assert A.m_k(k) == pytest.approx(want, abs=0.006)
    assert A.m_k(1) == 0.0
    assert A.m_k(7) == pytest.approx(1.352, abs=0.002)  # the level-evidence amendment's 1.35
    with pytest.raises(ValueError):
        A.m_k(0)


def test_harm_needs_size_and_a_whole_interval_below_zero():
    assert A.is_harm(-0.15, -0.02)
    assert not A.is_harm(-0.15, +0.01)       # interval spans 0
    assert not A.is_harm(-0.05, -0.01)       # inside the tolerance: a small harm
    assert not A.is_harm(-0.10, -0.01)       # exactly at the tolerance is not beyond it
    assert A.is_harm(-0.06, -0.01, tolerance=0.05)
    small = A.read(row(-0.05, -0.09, -0.01, 0.02), "repair")
    assert small["small_harm"] and not small["harm"]


def test_below_resolution_and_blind():
    r = row(0.02, -0.058, 0.098, 0.04)       # half-width 0.078, unresolved
    out = A.read(r, "repair", plausible=0.01)
    assert out["below_resolution"] and out["blind"]
    assert not A.read(r, "repair", plausible=0.2)["below_resolution"]
    assert out["resolution"] == pytest.approx(0.078)
    assert out["effect_80"] == pytest.approx(0.112)
    resolved = A.read(row(0.5, 0.2, 0.8, 0.15), "structural")
    assert resolved["below_resolution"] and not resolved["blind"]   # wide, but it saw something


def test_arithmetic_tends_to_the_prior_when_blind_and_to_the_reading_when_sharp():
    blind = A.arithmetic(estimate=0.5, se=10.0, mu0=-0.028, tau=0.03, cost=0.01)
    assert blind["posterior"] == pytest.approx(-0.028, abs=1e-4)
    sharp = A.arithmetic(estimate=0.5, se=1e-6, mu0=-0.028, tau=0.03, cost=0.01)
    assert sharp["posterior"] == pytest.approx(0.5, abs=1e-4)
    a = A.arithmetic(estimate=0.1, se=0.04, mu0=0.0, tau=0.03, cost=0.0, k=3, rho=0.5)
    b = 0.03 ** 2 / (0.03 ** 2 + 0.04 ** 2)
    sel = 0.04 * A.m_k(3) * math.sqrt(0.5)
    assert a["B"] == pytest.approx(b)
    assert a["sel"] == pytest.approx(sel)
    assert a["posterior"] == pytest.approx(b * (0.1 - sel))


def test_repair_adopts_unless_harm_and_a_small_harm_is_no_veto():
    for est, lo, hi in ((0.014, -0.006, 0.035), (-0.014, -0.035, 0.006)):
        assert A.read(row(est, lo, hi, 0.0105), "repair")["decision"] == "adopt"
    small = A.read(row(-0.08, -0.15, -0.01, 0.036), "repair")
    assert small["decision"] == "adopt" and "not vetoed" in small["reason"]
    harmful = A.read(row(-0.2, -0.3, -0.1, 0.05), "repair")
    assert harmful["decision"] == "do not adopt: harm" and "bug" in harmful["reason"]


def test_expansion_needs_a_route_and_a_small_harm_sends_it_back():
    r = row(0.014, -0.006, 0.035, 0.0105)
    assert A.read(r, "expansion")["decision"] == "undecided: name the route first"
    assert A.read(r, "expansion", route_supported=True)["decision"] == "adopt"
    assert A.read(r, "accretion")["decision"] == "adopt"
    small = A.read(row(-0.08, -0.15, -0.01, 0.036), "expansion", route_supported=True)
    assert small["decision"] == "re-examine the route before adopting"
    harmful = A.read(row(-0.2, -0.3, -0.1, 0.05), "expansion", route_supported=True)
    assert harmful["decision"] == "do not adopt: harm" and "arithmetic" not in harmful


def test_a_costly_expansion_pays_for_itself():
    cheap = A.read(row(0.014, -0.006, 0.035, 0.0105), "expansion", route_supported=True)
    assert cheap["decision"] == "adopt"
    feed = A.read(row(0.014, -0.006, 0.035, 0.0105), "expansion", route_supported=True, cost=0.05)
    assert feed["decision"] == "do not adopt: does not pay for its cost"
    paying = A.read(row(0.30, 0.15, 0.45, 0.075), "expansion", route_supported=True, cost=0.05, tau=0.3)
    assert paying["decision"] == "adopt"


def test_the_holdback_keeps_bisects_or_cannot_see():
    assert A.read(row(-0.05, -0.12, 0.02, 0.035), "holdback")["decision"] == "keep the adopted changes"
    assert A.read(row(-0.3, -0.5, -0.1, 0.1), "holdback")["decision"] == "bisect the adopted changes"
    # across the odds change the control resolves about +-0.3: blind for a batch of small changes (errata E1)
    blind = A.read(row(0.007, -0.306, 0.320, 0.16), "holdback")
    assert blind["blind"] and blind["decision"].startswith("below resolution")


def test_a_new_feature_goes_to_the_pool_as_a_lead():
    small = A.read(row(0.06, -0.10, 0.23, 0.084), "feature")
    assert small["blind"] and small["decision"] == "admit to the pool as a lead"
    weak = A.read(row(0.0, -0.05, 0.05, 0.0255), "feature", plausible=0.3)
    assert not weak["below_resolution"] and weak["decision"] == "admit to the pool as a lead"
    harmful = A.read(row(-0.3, -0.5, -0.1, 0.1), "feature")
    assert harmful["decision"].startswith("check for a bug or leak first")
    strong = A.read(row(0.78, 0.03, 1.54, 0.385), "feature", plausible=0.8, tau=0.5)
    assert strong["decision"] == "adopt (a feature big enough to test alone)"


def test_tuning_needs_k_and_keeps_the_default_when_blind():
    with pytest.raises(ValueError):
        A.read(row(0.01, -0.07, 0.09, 0.04), "tuning")
    with pytest.raises(ValueError):
        A.read(row(0.01, -0.07, 0.09, 0.04), "tuning", k=1)
    tie = A.read(row(0.01, -0.07, 0.09, 0.04), "tuning", k=4)       # the review's case
    assert tie["blind"] and tie["decision"] == "keep the default"
    visible = A.read(row(0.20, 0.12, 0.28, 0.04), "tuning", k=2, plausible=0.1)
    assert visible["decision"] == "adopt the variant"
    # a resolved reading (2.1 SE) picked as the best of 50 variants: their luck (m_50 = 2.25 SE) eats it
    lucky = A.read(row(0.042, 0.0028, 0.0812, 0.02), "tuning", k=50, plausible=0.05)
    assert not lucky["blind"] and lucky["decision"] == "keep the default"


def test_structural_is_undecided_when_blind_and_decided_when_resolved():
    blind = A.read(row(0.01, -0.29, 0.31, 0.153), "structural")         # Pinnacle first against the reference
    assert blind["decision"] == "undecided: below resolution"
    rows_ = A.read(row(-0.48, -1.09, 0.14, 0.31), "structural")         # Challenger rows
    assert rows_["decision"] == "undecided: below resolution"
    assert A.read(row(0.5, 0.2, 0.8, 0.15), "structural")["decision"] == "adopt"
    assert A.read(row(-0.5, -0.8, -0.2, 0.15), "structural")["decision"] == "do not adopt"


def test_input_flags_make_an_adoption_wait():
    out = A.read(row(0.014, -0.006, 0.035, 0.0105), "repair", input_flags=["points_52w (uneven)"])
    assert out["decision"] == "adopt, pending the input check"
    hb = A.read(row(0.0, -0.05, 0.05, 0.025), "holdback", input_flags=["indoor (uneven)"])
    assert hb["decision"] == "keep the adopted changes, pending the input check"


def test_nan_rows_are_refused_and_identical_forecasts_do_not_divide_by_zero():
    with pytest.raises(ValueError):
        A.read(row(float("nan"), float("nan"), float("nan"), float("nan")), "repair")
    for kind in A.KINDS:
        out = A.read(row(0.0, 0.0, 0.0, 0.0), kind, k=2 if kind == "tuning" else None, route_supported=True)
        assert out["resolution"] == 0.0 and not out["harm"]
    assert A.read(row(0.0, 0.0, 0.0, 0.0), "repair")["decision"] == "adopt"


def test_unknown_kind_is_refused():
    with pytest.raises(ValueError):
        A.read(row(0, -1, 1, 0.5), "rebuild")


def test_command_line_picks_the_declared_row_and_writes_json(tmp_path, capsys):
    scores = pd.DataFrame([
        {**PRIMARY, "group": "primary", "estimate": 0.014, "lo": -0.006, "hi": 0.035, "se": 0.0105,
         "p_better": 0.92, "reading": "unresolved"},
        {"group": "primary", "population": "men", "comparison": PRIMARY["comparison"], "estimate": -0.3,
         "lo": -0.5, "hi": -0.1, "se": 0.1, "p_better": 0.01, "reading": "worse"},
    ])
    path = tmp_path / "scores.csv"
    scores.to_csv(path, index=False)
    assert A.main(["--scores", str(path), "--kind", "expansion", "--route-supported"]) == 0
    res = json.loads((tmp_path / "adoption_read.json").read_text(encoding="utf-8"))
    assert res["decision"] == "adopt" and res["population"] == "both tours"
    assert A.main(["--scores", str(path), "--kind", "expansion", "--route-supported", "--population", "men",
                   "--out", str(tmp_path / "men.json")]) == 0
    assert json.loads((tmp_path / "men.json").read_text(encoding="utf-8"))["decision"] == "do not adopt: harm"
    (tmp_path / "summary.json").write_text(json.dumps({"inputs_flagged": [{"input": "indoor", "flag": "uneven"}]}),
                                           encoding="utf-8")
    assert A.main(["--scores", str(path), "--kind", "repair", "--out", str(tmp_path / "flag.json")]) == 0
    assert json.loads((tmp_path / "flag.json").read_text(encoding="utf-8"))["input_flags"] == ["indoor (uneven)"]
    with pytest.raises(SystemExit):
        A.main(["--scores", str(path), "--kind", "repair", "--population", "women"])
    assert "decision:" in capsys.readouterr().out


SEED_FIX = ROOT / "data" / "studies" / "adoption_framework" / "seed_fix_check" / "scores.csv"


@pytest.mark.skipif(not SEED_FIX.exists(), reason="the backfill's seed check is not on disk")
def test_the_published_backfill_reads_as_an_adoption():
    """The speed backfill (an expansion of data already used, in its own format): +0.014 [-0.006, +0.035], both
    tours. No harm -> adopt (pending its input check, if its summary.json lists flags)."""
    r = A.pick(pd.read_csv(SEED_FIX), *A.PRIMARY)
    out = A.read(r, "expansion", route_supported=True, input_flags=A.flagged_inputs(SEED_FIX))
    assert out["estimate"] == pytest.approx(0.014, abs=0.001)
    assert not out["harm"] and out["decision"].startswith("adopt")
    assert out["resolution"] == pytest.approx(0.0205, abs=0.002)
