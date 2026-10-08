"""Serve-speed sources: the parsers of Flashscore's and Infosys's speed fields, the Slam labels, the power formula, and
the presence-only feature window, on synthetic data.

Run: ./python.sh -m pytest test/serve_speed_sources
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_sources import coverage as C  # noqa: E402
from src.eda.serve_speed_sources import flashscore_crawl as F  # noqa: E402

STATS = json.dumps([{"SE": "Match"}, {"SF": "Service"}, {"SG": "Aces", "SH": "14", "SI": "8"},
                    {"SG": "Average 1st serve speed", "SH": "198 km/h", "SI": "203 km/h"},
                    {"SG": "Average 2nd serve speed", "SH": "165 km/h", "SI": "169 km/h"},
                    {"SE": "1st set"}, {"SG": "Average 1st serve speed", "SH": "190 km/h", "SI": "0 km/h"}])


def test_flashscore_statistics_block_is_read_for_the_match_period_only():
    assert C.fs_both(STATS)
    one_side = STATS.replace('"SI": "203 km/h"', '"SI": "0 km/h"')
    assert not C.fs_both(one_side)
    assert not C.fs_both("[]")


def test_flashscore_speeds_from_flat_fields_or_the_block():
    assert F.speeds({"home_average_1st_serve_speed": "154 km/h", "away_average_1st_serve_speed": "155 km/h"}) \
        == (154.0, 155.0)
    assert F.speeds({"stats_detail_json": STATS}) == (198.0, 203.0)
    h, a = F.speeds({"stats_detail_json": "[]"})
    assert np.isnan(h) and np.isnan(a)


def test_zero_kmh_placeholders_are_missing():
    # most 2024 Flashscore records print "0 km/h" for both players where no speed was measured
    flat = {"home_average_1st_serve_speed": "0 km/h", "away_average_1st_serve_speed": "0 km/h"}
    assert not C.fs_record_timed(flat)
    h, a = F.speeds(flat)
    assert np.isnan(h) and np.isnan(a)
    zeros = STATS.replace("198 km/h", "0 km/h").replace("203 km/h", "0 km/h")
    assert not C.fs_both(zeros)
    assert C.fs_record_timed({"home_average_1st_serve_speed": "154 km/h", "away_average_1st_serve_speed": "155 km/h"})
    assert not C.plausible("0") and not C.plausible("12 km/h") and C.plausible("182") and not C.plausible("999")


def test_numbers_inside_strings():
    assert C.num("182 KMH") == 182.0
    assert C.num(None) == 0.0
    assert F.kmh("203 km/h") == 203.0
    assert np.isnan(F.kmh("136 mph"))   # miles per hour are not read as km/h


def test_slam_labels_only_at_grand_slams():
    lv = pd.Series(["GS", "GS", "GS", "GS", "T250"])
    nm = pd.Series(["Australian Open", "Roland Garros", "Wimbledon", "US Open", "Australian Open warm-up"])
    assert C.slam_of(lv, nm).tolist() == ["AO", "RG", "W", "USO", ""]


def test_power_grows_with_matches_and_matches_the_registration():
    p = [C.power_one_sided(n) for n in (500, 2000, 8000)]
    assert p[0] < p[1] < p[2]
    # speed_prereg.md section 8: n = 3,534 gives SE about 0.038 per SD
    se = 1.0 / np.sqrt(3534 * 0.19 * 1.06)
    assert abs(se - 0.038) < 0.001
    assert C.power_one_sided(0) == 0.0


def test_presence_window_counts_only_earlier_timed_matches_within_14_days():
    # one player, four matches; timed history matters, the target itself does not
    rows = pd.DataFrame({"tour": "atp", "player_id": "p1", "round_order": [1, 1, 2, 1],
                         "tdate": [0, 30, 30, 40], "tournament_id": ["a", "b", "b", "c"],
                         "obs": [0.0, 30.0, 32.0, 50.0]})
    timed = np.array([True, False, True, False])
    got = C.feature_presence(rows, timed, np.array([1, 2, 3]))
    # match 1 (day 30): its only earlier timed match is 30 days old -> absent
    # match 2 (day 32, a later round of the same event): match 1 is untimed, match 0 too old -> absent
    # match 3 (day 50): match 2 (day 32) is timed and 18 days old -> absent; within 14 days it would count
    assert got.tolist() == [False, False, False]
    rows.loc[3, "obs"] = 40.0
    assert C.feature_presence(rows, timed, np.array([3])).tolist() == [True]
