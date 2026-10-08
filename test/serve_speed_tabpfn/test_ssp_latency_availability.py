"""Tests of src/eda/serve_speed_tabpfn/latency/availability.py (the latency follow-up's release days). They read the
built file: run
    ./python.sh src/eda/serve_speed_tabpfn/latency/availability.py
first. No test reads a match result.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import panel as P  # noqa: E402
from src.eda.serve_speed_tabpfn.latency import availability as AV  # noqa: E402

EVID = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "latency" / "evidence"


@pytest.fixture(scope="module")
def av() -> pd.DataFrame:
    assert AV.AVAIL.exists(), "build first: ./python.sh src/eda/serve_speed_tabpfn/latency/availability.py"
    return AV.load()


def test_one_row_per_stage0_player_match_and_every_panel_row(av):
    assert not av.duplicated(["match_id", "side"]).any()
    s0 = pd.read_parquet(P.S0, columns=["match_id"])
    assert len(av) == 2 * len(s0)
    pan = P.load_panel(use_only=False)[["match_id", "side", "use"]]
    j = pan.merge(av[["match_id", "side", "in_panel", "use"]], on=["match_id", "side"], how="left",
                  suffixes=("", "_av"))
    assert j["in_panel"].all() and (j["use"] == j["use_av"]).all()
    assert int(av["in_panel"].sum()) == len(pan)


def test_simple_scenarios(av):
    lf = av["lf"].astype(np.int64)
    assert (av["release_A"] == lf + 1).all()
    assert (av["box_release"] == lf + 1).all()
    for k in (1, 3, 7, 14):
        assert (av[f"release_L{k}"] == lf + 1 + k).all()


def test_b_never_before_a(av):
    """No row may enter a feature before its match surely finished."""
    assert (av["release_B"] >= av["release_A"]).all()


def test_weekly_rule(av):
    """Non-Slam rows: release - 1 is the first Sunday on or after lf + 2."""
    w = av[av["level"].ne("GS")]
    assert (w["rule_B"] == "mantd_weekly_sunday").all()
    s = w["release_B"].astype(np.int64) - 1
    assert (AV.weekday(s.to_numpy()) == 6).all()                 # a Sunday
    lf = w["lf"].astype(np.int64)
    assert ((s >= lf + 2) & (s <= lf + 8)).all()                  # the first such Sunday
    # worked examples: Fri 2 Oct 2026, Sat 3 Oct, Sun 4 Oct, Mon 5 Oct
    days = np.array([pd.Timestamp(d).value // 86_400_000_000_000 for d in
                     ("2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05")])
    rel = AV.weekly_release(days)
    assert [str(pd.Timestamp(int(r), unit="D").date()) for r in rel] == ["2026-10-05", "2026-10-12", "2026-10-12",
                                                                        "2026-10-12"]


def test_slam_rule(av):
    """Slam rows (main draw and qualifying, both tours): the Slam-year's last main-draw day + 3, one day per edition."""
    s = av[av["level"].eq("GS")]
    assert (s["rule_B"] == "slam_after_event").all()
    assert s["slam_last_main_day"].notna().all()
    assert (s["release_B"] == np.maximum(s["slam_last_main_day"].astype(np.int64) + 3, s["lf"] + 1)).all()
    per = s.groupby(["year", "slam"])["release_B"].nunique()
    assert (per == 1).all()
    main = s[~s["qualifying"].astype(bool)]
    last = main.groupby(["year", "slam"])["lf"].max()
    assert (s.groupby(["year", "slam"])["slam_last_main_day"].first().astype(np.int64) == last).all()


def test_rule_matches_observed_publication():
    """The weekly rule reproduces the commit that first carried each match's speed (10 weekly diffs) on >= 90%."""
    o = json.loads((EVID / "mantd_publication.json").read_text(encoding="utf-8"))
    r = o["release_rules_scored"]["first_sunday_on_or_after_lf_plus_2"]
    assert r["matches"] >= 600 and r["exact"] >= 0.90
    assert o["of_those_in_that_sundays_commit"] == 0 and o["matches_played_on_a_commit_sunday"] >= 20
    m = pd.read_csv(EVID / "mantd_publication_matches.csv")
    m = m[m["lf"].notna()]
    pred = AV.weekly_release(m["lf"].to_numpy(np.int64)) - 1
    act = pd.to_datetime(m["commit_day"]).to_numpy().astype("datetime64[D]").astype(np.int64)
    window = pred <= act.max()
    assert float((pred[window] == act[window]).mean()) >= 0.90


def test_scenarios_d_and_e(av):
    """D: a daily tour collector (non-Slam rows at lf + 2), Slams as B. E: weekly tour data as B, live Slam feeds (Slam
    rows at lf + 2). Neither releases a row before A."""
    lf = av["lf"].astype(np.int64)
    slam = av["level"].eq("GS")
    assert (av.loc[~slam, "release_D"] == lf[~slam] + 2).all()
    assert (av.loc[slam, "release_D"] == av.loc[slam, "release_B"]).all()
    assert (av.loc[~slam, "release_E"] == av.loc[~slam, "release_B"]).all()
    assert (av.loc[slam, "release_E"] == lf[slam] + 2).all()
    for c in ("release_D", "release_E"):
        assert (av[c] >= av["release_A"]).all()
    assert set(av.loc[~slam, "rule_D"]) == {"daily_collector"} and set(av.loc[slam, "rule_D"]) == {"slam_after_event"}
    assert set(av.loc[~slam, "rule_E"]) == {"mantd_weekly_sunday"} and set(av.loc[slam, "rule_E"]) == {"slam_live_feed"}


def test_existing_columns_unchanged_by_the_d_e_rewrite(av):
    """Every column that existed before D and E were added hashes as it did before the rewrite."""
    import hashlib
    chk = json.loads((AV.OUT / "availability_rewrite_check.json").read_text(encoding="utf-8"))
    assert chk["existing_columns_identical"] and chk["rows_before"] == len(av)
    for c, h in chk["sha256_before"].items():
        now = hashlib.sha256(pd.util.hash_pandas_object(av[c], index=False).to_numpy().tobytes()).hexdigest()
        assert now == h, c


def test_pending_and_watermarks():
    # the comparison: pending while the match day is later than the watermark
    assert AV.pending(20001, 20000) is True
    assert AV.pending(20000, 20000) is False and AV.pending(19999, 20000) is False
    assert AV.pending(20001, float("nan")) is True                  # nothing delivered yet
    assert AV.pending(20001, 20000, covered=False) is False         # an event with no speed source is never pending
    got = AV.pending(np.array([19999, 20000, 20001]), np.array([20000, 20000, 20000]),
                     covered=np.array([True, True, False]))
    assert got.tolist() == [False, False, False]
    assert AV.pending(pd.Timestamp("2026-10-03"), pd.Timestamp("2026-10-02")) is True
    # ManTennisData: the Friday before the latest Sunday commit (a Sunday commit -> that week's Friday)
    sun = pd.Timestamp("2026-10-04").value // 86_400_000_000_000
    assert AV.weekday(sun) == 6
    assert AV.mantd_watermark(sun) == sun - 2 and AV.weekday(AV.mantd_watermark(sun)) == 4
    for k in range(7):                                              # any commit day maps to a Friday at least 2 back
        w = AV.mantd_watermark(sun + k)
        assert AV.weekday(w) == 4 and sun + k - 8 <= w <= sun + k - 2
    # daily collector: yesterday; Slam feed: the last collected day
    assert AV.daily_watermark(20010) == 20009
    assert AV.slam_feed_watermark(pd.Timestamp("2026-07-12")) == pd.Timestamp("2026-07-12").value // 86_400_000_000_000


def test_watermark_logic_reproduces_release_b():
    """Live logic at day granularity: on day t the latest usable Sunday commit is the last Sunday <= t - 1, and a match
    is in hand once its lf is not later than that commit's watermark. The first such day is exactly release_B."""
    start = pd.Timestamp("2025-01-06").value // 86_400_000_000_000
    for lf in range(start, start + 70):
        t = lf + 1
        while True:
            last_sunday = (t - 1) - (AV.weekday(t - 1) - 6) % 7
            if not AV.pending(lf, AV.mantd_watermark(last_sunday)):
                break
            t += 1
        assert t == int(AV.weekly_release(np.array([lf]))[0]), lf


def test_panel_with_release(av):
    for sc in ("A", "B", "L7"):
        p = AV.panel_with_release(sc)
        assert len(p) == len(P.load_panel())
        assert (p["release"] >= p["lf"] + 1).all()
    # the as-of offsets accept the scenario's release column
    p = AV.panel_with_release("B")
    eo = P.EditionOffsets(p, "atp", cache=False, release="release")
    day = int(p.loc[p["tour"].eq("atp") & p["year"].eq(2025), "es"].median())
    s = eo.at(day)
    assert np.isfinite(s.to_numpy()).all() and len(s) == p.loc[p["tour"].eq("atp"), "edition"].nunique()
