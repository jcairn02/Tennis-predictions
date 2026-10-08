"""Offline tests of the input-data audit's detectors on synthetic matches: exchanged box scores, serve points that
leave out double faults, a whole edition read high for the same players, and name keys."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.input_data_audit import common as C  # noqa: E402

# A wins 6-4 6-3: 12 games to 7, no tiebreak. A serves 10 games and is broken once; B serves 9 and is broken 3 times.
A = {"ace": 5, "df": 2, "svpt": 60, "first_in": 36, "first_won": 30, "second_won": 10, "sv_gms": 10, "bp_saved": 1, "bp_faced": 2}
B = {"ace": 2, "df": 4, "svpt": 58, "first_in": 35, "first_won": 25, "second_won": 8, "sv_gms": 9, "bp_saved": 2, "bp_faced": 5}


def match(a: dict, b: dict, won: bool = True, games: int = 12, tiebreaks: int = 0, status: str = "completed") -> pd.DataFrame:
    row = {**a, **{f"o_{k}": v for k, v in b.items()}, "won": won, "games_won_n": games, "tb_won_d": tiebreaks,
           "status": status}
    return pd.DataFrame([row])


def test_a_consistent_match_raises_no_flag():
    f = C.identity_flags(match(A, B)).iloc[0]
    assert f["identity_testable"]
    assert not f["games_identity_fails"] and not f["swapped_box_fits"]
    assert not f["winner_fewer_points"] and not f["svg_not_alternating"]


def test_box_scores_exchanged_between_winner_and_loser_are_caught():
    f = C.identity_flags(match(B, A)).iloc[0]          # the winner carries the loser's counts
    assert f["games_identity_fails"] and f["swapped_box_fits"]
    assert f["winner_fewer_points"]


def test_identity_is_not_tested_through_a_tiebreak_or_an_unfinished_match():
    assert not C.identity_flags(match(B, A, tiebreaks=1)).iloc[0]["identity_testable"]
    assert not C.identity_flags(match(B, A, status="retired")).iloc[0]["identity_testable"]


def test_service_games_that_cannot_alternate_are_flagged():
    assert C.identity_flags(match({**A, "sv_gms": 12}, B)).iloc[0]["svg_not_alternating"]


def test_serve_points_without_double_faults_make_a_row_impossible():
    # 24 second-serve points (20 in, 4 double faults), 18 won: possible as recorded with double faults included ...
    full = pd.DataFrame([{"svpt": 60, "first_in": 36, "second_won": 18, "df": 4}])
    assert not C.serve_points_exclude_dfs(full).iloc[0]
    # ... impossible once serve points leave the 4 double faults out
    short = full.assign(svpt=56)
    assert C.serve_points_exclude_dfs(short).iloc[0]


def test_pooled_second_serve_share_recovers_when_double_faults_are_added_back():
    rows = pd.DataFrame([{"g": 1, "svpt": 56, "first_in": 36, "first_won": 24, "second_won": 11, "ace": 3, "df": 4,
                          "bp_saved": 1, "bp_faced": 2}])
    r = C.pooled_rates(rows, ["g"]).iloc[0]
    assert np.isclose(r["second_won_pct"], 100 * 11 / 20)
    assert np.isclose(r["second_won_pct_if_svpt_plus_df"], 100 * 11 / 24)


def test_edition_effects_find_one_edition_read_high_for_the_same_players():
    rng = np.random.default_rng(0)
    rows = []
    for p in range(40):
        level = 0.55 + 0.05 * rng.standard_normal()
        for e, shift in (("ev2024", 0.0), ("ev2025", 0.05), ("other", 0.0)):
            rows.append({"player": f"p{p}|2025", "edition": e, "rate": level + shift, "den": 80.0})
    x = pd.DataFrame(rows)
    out = C.edition_effects(x["rate"] * x["den"], x["den"], x["player"], x["edition"], min_den=20)
    assert np.isclose(out.loc["ev2025", "delta"] - out.loc["ev2024", "delta"], 0.05, atol=1e-6)
    assert np.isclose(out.loc["other", "delta"], out.loc["ev2024", "delta"], atol=1e-6)


def test_name_key_ignores_order_accents_and_punctuation():
    assert C.name_key("Sorribes Tormo, Sara") == C.name_key("Sara Sorribes Tormo")
    assert C.name_key("Linda Nosková") == C.name_key("NOSKOVA Linda")
    assert C.event_key("Adelaide 2 2022") == C.event_key("adelaide 2")
