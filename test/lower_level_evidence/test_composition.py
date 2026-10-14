"""Tests of the evidence-dose and exposure counts (src/eda/lower_level_evidence/composition.py).

Synthetic Stage 0 tables only: the window counting (no future leakage, boundary days, the same event's earlier rounds,
same-week other events, buckets, channels, both sides, tours), the effective (decayed) counts, the brute-force agreement
on a random history, the bins, the heterogeneity test, the holdout guard of part 5, the clock check's classes, and an
end-to-end run on a candidate-style Stage 0 folder (the renewable path).

Run: ./python.sh -m pytest test/lower_level_evidence/test_composition.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as CM  # noqa: E402
from src.eda.lower_level_evidence import composition as K  # noqa: E402

D0 = pd.Timestamp("2019-06-03")          # a Monday


def stage0(rows: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Matches and player rows from short dicts: id, tour, lv (map_level), ev, day (offset from D0), rnd, a, b, and
    optional status, box, rank_a, rank_b."""
    m = pd.DataFrame([{"match_id": r["id"], "tour": r.get("tour", "atp"), "map_level": r["lv"],
                       "tournament_id": r["ev"], "tournament_date": D0 + pd.Timedelta(days=r["day"]),
                       "round_order": r["rnd"], "status": r.get("status", "completed"), "has_box": r.get("box", True),
                       "player_a_id": r["a"], "player_b_id": r["b"]} for r in rows])
    m["bucket"] = CM.bucket(m["map_level"])
    p = pd.DataFrame([{"match_id": r["id"], "player_id": pid, "side": side, "rank": r.get(f"rank_{side.lower()}", 50.0)}
                      for r in rows for side, pid in (("A", r["a"]), ("B", r["b"]))])
    return m, p


def counts_for(rows: list[dict], match_id: str, side: str = "A") -> dict[str, dict]:
    m, p = stage0(rows)
    hist, _ = K.history_table(m, p)
    ix = K.Index(hist)
    r = hist[(hist["match_id"] == match_id) & (hist["side"] == side)].iloc[0]
    res = ix.counts([r["pcode"]], [r["t"]], [r["ev"]], [r["rnd"]])
    return {w: {f"{c}_{b}": float(res[w][0, k]) for k, (c, b) in enumerate(ix.cols)} for w in K.WINDOW_NAMES}


# ------------------------------------------------------------------------------------------------
# The window rule

def test_window_boundaries_are_inclusive_at_w_and_exclusive_after():
    rows = [{"id": "T", "lv": "T250", "ev": "E0", "day": 0, "rnd": 13, "a": "x", "b": "y"}]
    for k, gap in enumerate((14, 15, 28, 29, 91, 92, 365, 366, 1000)):
        rows.append({"id": f"h{gap}", "lv": "CH", "ev": f"H{k}", "day": -gap, "rnd": 13, "a": "x", "b": f"o{k}"})
    c = counts_for(rows, "T")
    assert c["14d"]["res_CH"] == 1          # 14 in, 15 out
    assert c["28d"]["res_CH"] == 3          # 14, 15, 28
    assert c["91d"]["res_CH"] == 5          # .. 29, 91
    assert c["365d"]["res_CH"] == 7         # .. 92, 365
    assert c["career"]["res_CH"] == 9


def test_same_event_earlier_rounds_count_later_rounds_and_the_match_itself_do_not():
    rows = [{"id": "q1", "lv": "TQ", "ev": "E", "day": 0, "rnd": 1, "a": "x", "b": "o1"},
            {"id": "q2", "lv": "TQ", "ev": "E", "day": 0, "rnd": 2, "a": "x", "b": "o2"},
            {"id": "r32", "lv": "T250", "ev": "E", "day": 0, "rnd": 13, "a": "x", "b": "o3"},
            {"id": "T", "lv": "T250", "ev": "E", "day": 0, "rnd": 14, "a": "x", "b": "o4"},
            {"id": "qf", "lv": "T250", "ev": "E", "day": 0, "rnd": 15, "a": "x", "b": "o5"},
            {"id": "next", "lv": "CH", "ev": "F", "day": 7, "rnd": 13, "a": "x", "b": "o6"}]
    c = counts_for(rows, "T")
    for w in ("14d", "career", "h2w"):
        assert c[w]["res_TQ"] == 2 and c[w]["res_MAIN"] == 1 and c[w]["res_CH"] == 0
    assert c["h2w"]["res_TQ"] == pytest.approx(2.0)      # same event: age 0, weight 1


def test_round_robin_same_round_and_same_week_other_events_never_count():
    rows = [{"id": "rr1", "lv": "FIN", "ev": "F", "day": 0, "rnd": 10, "a": "x", "b": "o1"},
            {"id": "T", "lv": "FIN", "ev": "F", "day": 0, "rnd": 10, "a": "x", "b": "o2"},
            {"id": "other_week_event", "lv": "CH", "ev": "G", "day": 0, "rnd": 1, "a": "x", "b": "o3"},
            {"id": "last_week", "lv": "CH", "ev": "H", "day": -7, "rnd": 17, "a": "x", "b": "o4"}]
    c = counts_for(rows, "T")
    assert c["career"]["res_MAIN"] == 0      # the other round-robin match of the same round
    assert c["career"]["res_CH"] == 1        # last week's only; this week's other event left out


def test_channels_and_statuses():
    rows = [{"id": "T", "lv": "T500", "ev": "E", "day": 0, "rnd": 13, "a": "x", "b": "y"},
            {"id": "c_box", "lv": "ITF", "ev": "A1", "day": -7, "rnd": 13, "a": "x", "b": "o1", "box": True},
            {"id": "c_nobox", "lv": "ITF", "ev": "A2", "day": -14, "rnd": 13, "a": "x", "b": "o2", "box": False},
            {"id": "ret", "lv": "ITF", "ev": "A3", "day": -21, "rnd": 13, "a": "x", "b": "o3", "status": "retired",
             "box": False},
            {"id": "wo", "lv": "ITF", "ev": "A4", "day": -28, "rnd": 13, "a": "x", "b": "o4", "status": "walkover"},
            {"id": "oth", "lv": "ITF", "ev": "A5", "day": -35, "rnd": 13, "a": "x", "b": "o5", "status": "other"}]
    c = counts_for(rows, "T")
    assert c["career"]["res_ITF"] == 3 and c["career"]["box_ITF"] == 1


def test_both_sides_count_their_own_player_and_tours_are_separate_players():
    rows = [{"id": "T", "lv": "GS", "ev": "E", "day": 0, "rnd": 11, "a": "x", "b": "y"},
            {"id": "x1", "lv": "CH", "ev": "A", "day": -7, "rnd": 13, "a": "x", "b": "o1"},
            {"id": "y1", "lv": "ITF", "ev": "B", "day": -7, "rnd": 13, "a": "y", "b": "o2"},
            {"id": "y2", "lv": "ITF", "ev": "C", "day": -14, "rnd": 13, "a": "o3", "b": "y"},
            {"id": "wta_x", "tour": "wta", "lv": "ITF", "ev": "W", "day": -7, "rnd": 13, "a": "x", "b": "o4"}]
    a, b = counts_for(rows, "T", "A"), counts_for(rows, "T", "B")
    assert a["career"]["res_CH"] == 1 and a["career"]["res_ITF"] == 0      # the WTA "x" is another player
    assert b["career"]["res_ITF"] == 2 and b["career"]["res_CH"] == 0


def test_effective_counts_follow_the_half_life():
    rows = [{"id": "T", "lv": "T250", "ev": "E", "day": 0, "rnd": 13, "a": "x", "b": "y"},
            {"id": "h1", "lv": "CH", "ev": "A", "day": -14, "rnd": 13, "a": "x", "b": "o1"},
            {"id": "h2", "lv": "CH", "ev": "B", "day": -28, "rnd": 13, "a": "x", "b": "o2"},
            {"id": "h3", "lv": "CH", "ev": "C", "day": -364, "rnd": 13, "a": "x", "b": "o3"}]
    c = counts_for(rows, "T")
    for h in K.HALF_LIVES:
        want = sum(2.0 ** (-age / (7.0 * h)) for age in (14, 28, 364))
        assert c[f"h{h}w"]["res_CH"] == pytest.approx(want, rel=1e-12)
    assert c["h2w"]["res_CH"] == pytest.approx(0.5 + 0.25 + 2.0 ** -26, rel=1e-12)


# ------------------------------------------------------------------------------------------------
# Random histories: brute force and leakage

def random_stage0(seed: int = 0, n_weeks: int = 80, players: int = 30) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    lvls = ["GS", "T250", "T1000", "TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ", "TEAM"]
    rows, k = [], 0
    for w in range(n_weeks):
        for e in range(3):
            lv = lvls[rng.integers(len(lvls))]
            tour = "atp" if rng.random() < 0.6 else "wta"
            day = 7 * w - (1 if rng.random() < 0.1 else 0)        # some events start on a Sunday
            for _ in range(rng.integers(2, 8)):
                a, b = rng.choice(players, size=2, replace=False)
                rows.append({"id": f"m{k}", "tour": tour, "lv": lv, "ev": f"e{w}_{e}", "day": day,
                             "rnd": int(rng.choice([1, 2, 10, 11, 12, 13, 14, 15, 16, 17])), "a": f"p{a}",
                             "b": f"p{b}", "status": rng.choice(["completed", "retired", "walkover", "other"],
                                                                p=[0.85, 0.05, 0.05, 0.05]),
                             "box": bool(rng.random() < 0.7), "rank_a": float(rng.integers(1, 400)),
                             "rank_b": float(rng.integers(1, 400))})
                k += 1
    return stage0(rows)


def test_fast_counts_equal_brute_force_on_a_random_history():
    m, p = random_stage0()
    hist, _ = K.history_table(m, p)
    ix = K.Index(hist)
    res = ix.counts(hist["pcode"], hist["t"], hist["ev"], hist["rnd"])
    for i in np.random.default_rng(1).choice(len(hist), size=150, replace=False):
        r = hist.iloc[i]
        slow = K.count_slow(hist, int(r["pcode"]), int(r["t"]), int(r["ev"]), int(r["rnd"]))
        for w, rec in slow.items():
            for k, cb in enumerate(ix.cols):
                assert res[w][i, k] == pytest.approx(rec[cb], rel=1e-9, abs=1e-12), (w, cb)


def test_nothing_after_a_cut_reaches_a_count_before_it():
    m, p = random_stage0(seed=3)
    hist, _ = K.history_table(m, p)
    base = K.Index(hist).counts(hist["pcode"], hist["t"], hist["ev"], hist["rnd"])
    cut = int(np.quantile(hist["t"], 0.5))
    rng = np.random.default_rng(5)
    late = hist["t"].to_numpy() > cut
    pert = hist.copy()
    pert.loc[late, "bucket"] = rng.choice(list(K.BUCKETS), size=int(late.sum()))
    pert.loc[late, "res"] = rng.random(int(late.sum())) < 0.5
    pert.loc[late, "box"] = pert.loc[late, "res"] & (rng.random(int(late.sum())) < 0.5)
    got = K.Index(pert).counts(pert["pcode"], pert["t"], pert["ev"], pert["rnd"])
    early = ~late
    for w in K.WINDOW_NAMES:
        assert np.allclose(got[w][early], base[w][early], rtol=0, atol=1e-9), w
    assert any(not np.allclose(got[w][late], base[w][late]) for w in K.WINDOW_NAMES)   # the probe can see change


def test_later_rounds_of_the_same_event_never_reach_an_earlier_round():
    rows = [{"id": "r32", "lv": "T250", "ev": "E", "day": 0, "rnd": 13, "a": "x", "b": "o1"},
            {"id": "T", "lv": "T250", "ev": "E", "day": 0, "rnd": 14, "a": "x", "b": "o2"},
            {"id": "qf", "lv": "T250", "ev": "E", "day": 0, "rnd": 15, "a": "x", "b": "o3"}]
    c1 = counts_for(rows, "T")
    rows[2]["lv"], rows[2]["status"] = "ITF", "retired"
    assert counts_for(rows, "T") == c1


# ------------------------------------------------------------------------------------------------
# Targets, bins, shares

def test_targets_table_maps_both_sides_bands_and_missing_matches():
    m, p = stage0([{"id": "T1", "lv": "T250", "ev": "E", "day": 0, "rnd": 13, "a": "x", "b": "y", "rank_a": 15,
                    "rank_b": 250},
                   {"id": "c", "lv": "CH", "ev": "F", "day": -7, "rnd": 13, "a": "x", "b": "z"}])
    hist, _ = K.history_table(m, p)
    frame = pd.DataFrame({"match_id": ["T1", "T_missing"], "tour": ["atp", "atp"], "season": [2019, 2019],
                          "tournament_date": [D0, D0], "debut_season": [False, False], "in_level": [4.0, 4.0]})
    tg, info = K.targets_table(hist, frame, p)
    assert info["frame_matches_missing_from_stage0"] == 1 and info["sides_per_match_not_two"] == 0
    assert list(tg["side"]) == ["A", "B"] and list(tg["band"]) == ["1-20", "201+"]
    assert set(tg["level"]) == {"250s"}


def test_bins():
    assert list(K.band_of([1, 20, 21, 50, 51, 100, 101, 200, 201, np.nan])) == \
        ["1-20", "1-20", "21-50", "21-50", "51-100", "51-100", "101-200", "101-200", "201+", "unranked"]
    assert list(K.exposure_bin([0, 1, 4, 5, 9, 10, 19, 20, 300, np.nan])) == \
        ["0", "1-4", "1-4", "5-9", "5-9", "10-19", "10-19", "20+", "20+", "none"]
    assert list(K.bin_of([0.0, 0.2499, 0.25, 0.5, 0.75, 1.0, np.nan], K.SHARE_BINS, "no evidence")) == \
        ["0-25%", "0-25%", "25-50%", "50-75%", "75-100%", "75-100%", "no evidence"]


def test_shares_pool_counts_and_flag_domination():
    zeros = {K.col(c, w, b): [0, 0, 0] for c in K.CHANNELS for w in K.WINDOW_NAMES for b in K.BUCKETS}
    sides = pd.DataFrame({"tour": ["atp", "atp", "atp"], **zeros})
    sides[K.col("res", "365d", "MAIN")] = [3, 1, 0]
    sides[K.col("res", "365d", "CH")] = [1, 3, 0]
    s = K.shares(sides, ["tour"], windows=("365d",))
    r = s[s["channel"] == "res"].iloc[0]
    assert r["share_lower"] == pytest.approx(0.5) and r["share_CH"] == pytest.approx(0.5)
    assert r["no_evidence"] == pytest.approx(1 / 3) and r["lower_dominates"] == pytest.approx(0.5)


def test_p7_scenario_boxes_only_itf_main_draws_of_2018_2024():
    # D0 is 3 Jun 2019: an ITF result 7 days before (2019), one in 2017 (outside P7), an ITFQ one (not P7's target)
    rows = [{"id": "T", "lv": "T250", "ev": "E", "day": 0, "rnd": 13, "a": "x", "b": "y"},
            {"id": "itf19", "lv": "ITF", "ev": "A", "day": -7, "rnd": 13, "a": "x", "b": "o1", "box": False},
            {"id": "itf17", "lv": "ITF", "ev": "B", "day": -600, "rnd": 13, "a": "x", "b": "o2", "box": False},
            {"id": "itfq19", "lv": "ITFQ", "ev": "C", "day": -14, "rnd": 1, "a": "x", "b": "o3", "box": False},
            {"id": "ch19", "lv": "T250", "ev": "D", "day": -21, "rnd": 13, "a": "x", "b": "o4", "box": True}]
    m, p = stage0(rows)
    hist, _ = K.history_table(m, p)
    tg = hist[hist["match_id"] == "T"].sort_values("side").reset_index(drop=True)
    tg = tg.assign(season=2019, tour="atp")
    ix = K.Index(hist)
    res = ix.counts(tg["pcode"], tg["t"], tg["ev"], tg["rnd"])
    counts = {K.col(c, w, b): res[w][:, k] for w in K.WINDOW_NAMES for k, (c, b) in enumerate(ix.cols)}
    sides = pd.concat([tg[["tour", "season"]], pd.DataFrame(counts)], axis=1)
    sc = K.p7_scenario(hist, tg, sides)
    assert sc.attrs["flipped_rows"] == 2                                 # both players' rows of itf19
    r = sc[(sc["window"] == "365d")].iloc[0]
    assert r["box_evidence_today"] == 1 and r["box_evidence_p7"] == 2      # side A gains itf19 only
    assert r["box_lower_share_today"] == 0 and r["box_lower_share_p7"] == pytest.approx(0.5)


# ------------------------------------------------------------------------------------------------
# Part 5's helpers

def test_heterogeneity_separates_a_planted_difference_from_none():
    rng = np.random.default_rng(0)
    n = 6000
    blocks = rng.integers(0, 60, n)
    lab = rng.choice(["a", "b", "c"], n)
    same = rng.normal(0, 30, n)
    assert K.heterogeneity(same, lab, blocks)["p_value"] > 0.001
    planted = same + np.where(lab == "c", 8.0, 0.0)
    assert K.heterogeneity(planted, lab, blocks)["p_value"] < 1e-4


def test_outcomes_are_refused_when_a_season_2024_row_falls_in_the_holdout(tmp_path):
    f = pd.DataFrame({"match_id": ["a", "b"], "season": [2024, 2024],
                      "tournament_date": [pd.Timestamp("2024-06-03"), pd.Timestamp("2024-12-30")],
                      "a_won": [True, False]})
    path = tmp_path / "frame.parquet"
    f.to_parquet(path)
    with pytest.raises(AssertionError):
        K.outcomes_through_2024(path)
    f.loc[1, "tournament_date"] = pd.Timestamp("2024-11-25")
    f.to_parquet(path)
    y = K.outcomes_through_2024(path)
    assert list(y.index) == ["a", "b"]


def test_clock_check_classes():
    rows = [{"id": "r32", "lv": "T250", "ev": "E", "day": 0, "rnd": 13, "a": "x", "b": "o1"},
            {"id": "T", "lv": "T250", "ev": "E", "day": 0, "rnd": 14, "a": "x", "b": "o2"},
            {"id": "lastw", "lv": "CH", "ev": "F", "day": -7, "rnd": 17, "a": "x", "b": "o3"},
            {"id": "sameweek", "lv": "CH", "ev": "G", "day": 0, "rnd": 1, "a": "x", "b": "o4"}]
    m, p = stage0(rows)
    hist, origin = K.history_table(m, p)
    ix = K.Index(hist)
    tg = hist[(hist["match_id"] == "T") & (hist["side"] == "A")].reset_index(drop=True)
    day = lambda d: float((D0 - pd.Timestamp("1970-01-01")).days + d)       # noqa: E731
    timing = pd.DataFrame({"match_id": ["r32", "T", "lastw", "sameweek"],
                           "es": [day(0), day(1), day(-2), day(-1)],          # r32's window overlaps T's start
                           "lf": [day(2), day(3), day(-1), day(-1)]})         # the same-week match surely finished
    cc, s = K.clock_check(ix, hist, tg, timing)
    allr = cc[cc["bucket"] == "all"].iloc[0]
    assert allr["counted_365d"] == 2 and allr["counted_same_event"] == 1
    assert allr["counted_not_placed_first_by_clock"] == 1 and allr["of_which_same_event"] == 1
    assert allr["left_out_other_event_same_week"] == 1 and allr["left_out_but_clock_says_first"] == 1
    assert allr["counted_but_clock_says_after"] == 0


# ------------------------------------------------------------------------------------------------
# The renewable path: a whole run on a candidate-style Stage 0 folder

def test_run_end_to_end_on_a_synthetic_stage0_folder(tmp_path):
    m, p = random_stage0(seed=11, n_weeks=120)
    m = m.copy()
    shift = pd.Timestamp("2018-01-01") - m["tournament_date"].min()
    m["tournament_date"] = m["tournament_date"] + shift                      # 2018 .. 2020
    d0 = tmp_path / "stage0"
    d0.mkdir()
    m.drop(columns="bucket").to_parquet(d0 / "stage0_matches.parquet")
    p.to_parquet(d0 / "stage0_match_players.parquet")
    main = m[m["bucket"] == "MAIN"]
    lvl = {"GS": 0.0, "FIN": 1.0, "T1000": 2.0, "T500": 3.0, "T250": 4.0}
    frame = pd.DataFrame({"match_id": main["match_id"], "tour": main["tour"],
                          "season": main["tournament_date"].dt.year, "tournament_date": main["tournament_date"],
                          "debut_season": False, "in_level": main["map_level"].map(lvl)})
    frame.to_parquet(tmp_path / "frame.parquet")
    out = tmp_path / "out"
    summ = K.run(d0, tmp_path / "frame.parquet", "synthetic", out, timing_path=None, with_scores=False, spot=40)
    assert summ["spot_check"]["passed"]
    assert summ["targets"]["frame_matches_missing_from_stage0"] == 0
    sides = pd.read_parquet(out / "sides.parquet")
    assert len(sides) == 2 * len(frame)
    for name in ("shares.csv", "shares_full.csv.gz", "inputs_dose.csv", "itf_regime.csv", "itf_any.csv",
                 "itf_preview.csv", "itf_p7_scenario.csv", "exposure.csv", "exposure_cross.csv", "summary.json"):
        assert (out / name).exists(), name
