"""Regressions for identity, score anatomy and dependent box-score cleanup."""
import numpy as np
import pandas as pd
import pytest

from src.eda.feature_alpha_audit import repair_data as D
from src.eda.predictability_diagnostic import common as C
from src.eda.predictability_diagnostic import stage0_build as B


def tables(specs=(("sackmann", "atp:1", "Player One", "atp:2", "Player Two"),)):
    matches, players = [], []
    for i, (source, aid, aname, bid, bname) in enumerate(specs):
        mid = f"m{i}"
        matches.append(dict(match_id=mid, tour="atp", source=source, tournament_date=pd.Timestamp("2025-06-01"),
                            score="6-4 6-4", score_flag="", level="T250", status="completed", format="standard",
                            nonstandard_format=False, minutes=90., has_box=True, box_status="full",
                            player_a_id=aid, player_b_id=bid))
        for side, pid, name, won in [("A", aid, aname, True), ("B", bid, bname, False)]:
            p = dict(match_id=mid, side=side, player_id=pid, player_name=name, country="USA", age=25., won=won,
                     opponent_id=bid if side == "A" else aid, has_box=True)
            p.update(dict(ace=4., df=2., svpt=60., first_in=40., first_won=30., second_won=12.,
                          sv_gms=10., bp_saved=2., bp_faced=3.))
            for s in C.RATES:
                p[s + "_n"], p[s + "_d"] = 2., 5.
            p["hold_n"], p["hold_d"] = 9., 10.
            p["brk_n"], p["brk_d"] = 1., 10.
            players.append(p)
    return pd.DataFrame(matches), pd.DataFrame(players)


@pytest.mark.parametrize("score", ["6-4 3-6 10-8", "6-4 3-6 12-10", "6-4 3-6 16-14",
                                   "6-4 3-6 9-7", "6-4 6-3 10-4", "6-4 3-6 11-6"])
def test_long_advantage_or_inconsistent_sets_are_never_inferred_to_be_match_tiebreaks(score):
    assert D.plain_match_tiebreak(score, "ITF") == score
    assert D.plain_match_tiebreak(score, "GS") == score


def test_unambiguous_tiebreak_corrects_aggregates_but_retains_score_and_orientation():
    m, p = tables()
    m.loc[0, "score"] = "6-4 3-6 10-4"
    out, rows, meta = D.repair_tables(m, p)
    assert out.loc[0, "score"] == m.loc[0, "score"]
    assert out.loc[0, "format"] == "match_tiebreak"
    np.testing.assert_array_equal(rows.games_won_n, [9, 10])
    np.testing.assert_array_equal(rows.games_won_d, [19, 19])
    np.testing.assert_array_equal(rows.sets_won_n, [2, 1])
    np.testing.assert_array_equal(rows.tb_won_n, [1, 0])
    assert meta["historical_plain_match_tiebreaks_corrected"] == 1
    pd.testing.assert_series_equal(rows.side, p.side)
    assert D.plain_match_tiebreak(m.loc[0, "score"], "ITF", status="retired") == m.loc[0, "score"]
    assert D.plain_match_tiebreak(m.loc[0, "score"], "ITF", short=True) == m.loc[0, "score"]


def test_reversed_score_winner_orientation_and_stage0_parser_use_same_rule():
    m, p = tables()
    m.loc[0, ["score", "score_flag"]] = ["4-6 6-3 4-10", "read_reversed"]
    _, rows, _ = D.repair_tables(m, p)
    np.testing.assert_array_equal(rows.games_won_n, [9, 10])
    np.testing.assert_array_equal(rows.sets_won_n, [2, 1])
    scores = pd.DataFrame(dict(score=["6-4 3-6 10-4", "6-4 3-6 10-8"],
                               level=["ITF"] * 2, status=["completed"] * 2, short_event=[False] * 2))
    got = B.score_columns(scores)
    np.testing.assert_array_equal(got.games_w + got.games_l, [19, 37])
    np.testing.assert_array_equal(got.has_bracket, [True, False])


def test_unambiguous_identity_alias_preserves_match_handles_and_updates_opponent():
    m, p = tables((("sackmann", "atp:1", "Björn Example", "atp:2", "Opponent"),
                   ("tml", "atpcode:AB1", "Bjorn Example", "atp:2", "Opponent")))
    out, rows, meta = D.repair_tables(m, p)
    assert rows.loc[2, "player_id"] == "atp:1"
    assert rows.loc[3, "opponent_id"] == "atp:1"
    assert out.loc[1, "player_a_id"] == "atp:1"
    assert meta["identity_player_rows_changed"] == 1
    assert meta["identity_aliases"][0]["rows"] == 1
    pd.testing.assert_series_equal(out.match_id, m.match_id)
    pd.testing.assert_series_equal(rows.side, p.side)
    for missing in [None, np.nan, pd.NA, ""]:
        assert D.name_key(missing) == ""


@pytest.mark.parametrize("conflict", ["age", "country", "multiple_ids", "missing_name"])
def test_ambiguous_or_conflicting_identity_is_not_rewritten(conflict):
    specs = [("sackmann", "atp:1", "Same Name", "atp:2", "Other"),
             ("tml", "atpcode:X", "Same Name", "atp:2", "Other")]
    if conflict == "multiple_ids":
        specs.append(("sackmann", "atp:3", "Same Name", "atp:2", "Other"))
    m, p = tables(specs)
    if conflict == "age":
        p.loc[2, "age"] = 45.
    if conflict == "country":
        p.loc[2, "country"] = "ESP"
    if conflict == "missing_name":
        p.loc[[0, 2], "player_name"] = None
    _, got, meta = D.repair_tables(m, p)
    assert got.loc[2, "player_id"] == "atpcode:X"
    assert meta["identity_player_rows_changed"] == 0
    assert not meta["identity_aliases"]


def test_source_code_collision_is_resolved_per_named_person_never_globally():
    m, p = tables((("sackmann", "atp:1", "Person A", "atp:2", "Person B"),
                   ("tml", "atpcode:BAD", "Person A", "atp:2", "Person B"),
                   ("tml", "atpcode:BAD", "Unmatched Person", "atp:2", "Person B")))
    _, got, _ = D.repair_tables(m, p)
    assert got.loc[2, "player_id"] == "atp:1"
    assert got.loc[4, "player_id"] == "atpcode:BAD"


def test_opponent_collapse_reverts_alias_and_does_not_report_success():
    m, p = tables((("sackmann", "atp:1", "Same Name", "atp:2", "Other"),
                   ("tml", "atp:1", "Same Name", "atpcode:X", "Same Name")))
    _, got, meta = D.repair_tables(m, p)
    pd.testing.assert_series_equal(got.player_id, p.player_id)
    assert not meta["identity_aliases"]
    assert any(c["reason"] == "would collapse opponents; reverted" for c in meta["identity_conflicts_left_unresolved"])


def test_negative_primitive_drops_both_boxes_and_plausible_hold_break_derivatives():
    m, p = tables()
    p.loc[0, ["bp_saved", "bp_faced", "hold_n"]] = [-1., 1., 8.]
    p.loc[1, "brk_n"] = 2.  # apparently plausible 2/10 despite invalid opponent primitive
    out, rows, meta = D.repair_tables(m, p)
    assert not out.has_box.any() and not rows.has_box.any()
    assert rows[list(C.BOX)].isna().all().all()
    assert rows[["hold_n", "hold_d", "brk_n", "brk_d", "bp_saved_n", "bp_conv_n", "spw_n", "rpw_n"]].isna().all().all()
    pd.testing.assert_series_equal(rows.games_won_n, p.games_won_n)
    assert meta["negative_primitive_box_matches_masked"] == 1


@pytest.mark.parametrize("negative", ["bpSaved", "SvGms"])
def test_raw_stage0_rejects_negative_before_service_game_cleanup_can_hide_it(negative):
    box = {"ace": "4", "df": "2", "svpt": "60", "1stIn": "40", "1stWon": "30", "2ndWon": "12",
           "SvGms": "10", "bpSaved": "2", "bpFaced": "3"}
    row = dict(rid=0, score="6-4 6-4", status="completed", status_detail="completed", games_w=12, games_l=8, std_tb=0)
    row.update({side + "_" + k: v for side in ["w", "l"] for k, v in box.items()})
    row["w_" + negative] = "-1"
    got = B.box_scores(pd.DataFrame([row]))
    assert got.box_status.iloc[0] == "failed_check"
    assert not got.has_box.iloc[0]
    assert got[["w_bp_saved", "l_bp_saved", "w_svpt", "l_svpt"]].isna().all().all()


def test_bad_rates_missing_denominators_infinities_and_minutes_are_masked():
    m, p = tables((("sackmann", "atp:1", "A", "atp:2", "B"),
                   ("sackmann", "atp:1", "A", "atp:2", "B")))
    p.loc[0, ["first_won_n", "first_won_d"]] = [-1., np.nan]
    p.loc[1, "second_won_n"] = np.inf
    p.loc[2, "bp_faced_pg_n"] = 20.  # count/game may legitimately exceed 1
    m["minutes"] = [1., 5000.]
    out, rows, meta = D.repair_tables(m, p)
    assert rows.loc[0, ["first_won_n", "first_won_d"]].isna().all()
    assert rows.loc[1, ["second_won_n", "second_won_d"]].isna().all()
    assert rows.loc[2, "bp_faced_pg_n"] == 20.
    assert out.minutes.isna().all() and meta["implausible_minutes_masked"] == 2


def test_blank_source_ids_use_unambiguous_names_not_majority_votes():
    known = pd.DataFrame({"tour": ["atp"] * 5, "key": ["same", "same", "same", "unique", ""],
                          "pid": ["atp:1", "atp:1", "atp:2", "atp:3", "atp:4"]})
    found = B.unambiguous_name_ids(known)
    assert found.to_dict() == {("atp", "unique"): "atp:3"}


def test_repair_is_idempotent_and_rejects_unpaired_or_duplicate_records():
    m, p = tables()
    m1, p1, _ = D.repair_tables(m, p)
    m2, p2, _ = D.repair_tables(m1, p1)
    pd.testing.assert_frame_equal(m1, m2)
    pd.testing.assert_frame_equal(p1, p2)
    with pytest.raises(ValueError, match="unique matches"):
        D.repair_tables(pd.concat([m, m]), p)
    with pytest.raises(ValueError, match="exactly A and B"):
        D.repair_tables(m, p.iloc[:1])
