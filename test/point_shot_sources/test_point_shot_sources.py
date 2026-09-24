"""Parsing and linking rules of the point/shot sources study (offline)."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "point_shot_sources"))

import fill_matrix as F  # noqa: E402
import link_sofascore as L  # noqa: E402
import pbp_checks as C  # noqa: E402

LISTING = """# player: Test Player | sofascore_id: 42 | how verified: test
# page 0 | COUNT=2 TRUNCATED=yes HASNEXT=absent
103 | 1700600000 | Somewhere, Spain | Challenger | Round of 16 | Test Player | Ann Other | 1 | false | 1 | finished | 2 | 0
104|1700700000|Somewhere, Spain|Challenger|Quarterfinals|Bob Smith|Test Player|1|false|absent|finished|2|1
# page 1 | COUNT=2 TRUNCATED=yes HASNEXT=absent
101 | 1700000000 | M15 Place | ITF Men | Round of 32 | Test Player | Carl Jones | 1 | false | 2 | finished | 2 | 1
102 | 1700100000 | M15 Place, Doubles | ITF Men | Round of 16 | Player T / Partner P | X / Y | 2 | false | absent | finished | 0 | 2
"""


def test_sofascore_round_labels_become_atp_codes():
    assert L.sofa_round("Round of 32") == "R32"
    assert L.sofa_round("Quarterfinals") == "QF"
    assert L.sofa_round("Qualification round 2") == "Q2"
    assert L.sofa_round("Qual Final") == "Q"
    assert L.round_agrees("R32", "R32") == 2
    assert L.round_agrees("Q2", "Q") == 1
    assert L.round_agrees("QF", "Q") == 0


def test_opponent_names_with_and_without_spaces_agree():
    assert L.opp_score("Theo", "Vandeweghe", "T. Van de Weghe") == 1
    assert L.opp_score("Theo", "Van de Weghe", "Theo Vandeweghe") >= 1
    assert L.opp_score("Ann", "Other", "Ann Other") == 3
    assert L.opp_score("Theo", "Vandeweghe", "Carl Weghe") == 0


def test_play_windows_follow_the_draw_calendar():
    assert L.play_window("GS", "Tour qualifying", "Q1") == (-10, -1)
    assert L.play_window("GS", "Tour main draw", "QF") == (-1, 14)
    assert L.play_window("CH", "Challenger qualifying", "Q2") == (-3, 2)
    assert L.play_window("1000", "Tour main draw", "R64") == (-2, 13)
    assert L.play_window("FU", "ITF main draw", "R32") == (-2, 8)


def test_listing_parser_reads_both_separator_styles(tmp_path):
    f = tmp_path / "TST1.txt"
    f.write_text(LISTING, encoding="utf-8")
    ev, pages, head = L.parse_listing(f)
    assert head["sofascore_id"] == "42"
    assert list(ev["sofa_id"]) == ["103", "104", "101", "102"]
    assert list(ev["page"]) == [0, 0, 1, 1]
    assert ev.loc[ev["sofa_id"] == "104", "first_to_serve"].item() == "absent"
    assert len(pages) == 2 and set(pages["truncated"]) == {"yes"}
    assert not L.list_complete(pages)
    f.write_text(LISTING + "# page 2 | HTTP 404 Not Found (end of list; paging stopped)\n", encoding="utf-8")
    assert L.list_complete(L.parse_listing(f)[1])


def test_unseen_spans_are_the_cut_page_tails():
    ev = pd.DataFrame({"page": [0, 0, 1, 1], "ts": [1700600000, 1700700000, 1700000000, 1700100000]})
    spans = L.unseen_spans(ev, now_ts=1800000000, list_complete=False)
    assert (1700100000, 1700600000) in spans      # tail of page 1, cut by the reading tool
    assert (1700700000, 1800000000) in spans      # tail of page 0 up to the reading date
    assert (0, 1700000000) in spans               # older than anything read
    assert (0, 1700000000) not in L.unseen_spans(ev, 1800000000, list_complete=True)


def test_a_miscopied_timestamp_is_flagged_and_bridged():
    day = 86400
    ev = pd.DataFrame({"page": [4, 4, 4, 4, 5, 5], "ts": [100 * day, 102 * day, 104 * day, 10 * day, 50 * day, 60 * day]})
    ev["ts_suspect"] = L.suspect_timestamps(ev)
    assert list(ev["ts_suspect"]) == [False, False, False, True, False, False]
    assert L.link_timestamps(ev).iloc[3] == 104 * day       # the last line takes its only neighbour's date
    assert (60 * day, 100 * day) in L.unseen_spans(ev, 200 * day, list_complete=True)


def test_doubles_and_player_side():
    row = {"home": "Player T / Partner P", "away": "X / Y", "tournament": "M15 Place"}
    assert L.is_doubles(row)
    assert not L.is_doubles({"home": "Test Player", "away": "Carl Jones", "tournament": "M15 Place"})
    assert L.player_side("Test Player", "Test Player", "Carl Jones") == "home"
    assert L.player_side("Test Player", "Bob Smith", "Test Player") == "away"


def _ref(rows):
    ref = pd.DataFrame(rows)
    ref["day0"] = (pd.to_datetime(ref["event_date"]) - pd.Timestamp("1970-01-01")).dt.days
    ref[["win_lo", "win_hi"]] = pd.DataFrame([L.play_window(t, lv, r) for t, lv, r in
                                             zip(ref["event_type"], ref["level"], ref["round"])], index=ref.index)
    return ref


def _events(rows):
    ev = pd.DataFrame(rows)
    ev["days"] = ev["ts"] // 86400
    ev["round_code"] = ev["sofa_round"].map(L.sofa_round)
    for c, default in (("tournament", "Somewhere, Spain"), ("category", ""), ("first_to_serve", ""),
                       ("final_result_only", ""), ("status", "finished")):
        if c not in ev:
            ev[c] = default
    return ev


def test_link_prefers_name_then_round_and_reports_unseen():
    ref = _ref([
        {"ref_id": "a", "code": "T", "event_type": "CH", "level": "Challenger main draw", "round": "R16",
         "event_name": "Somewhere", "event_date": "2023-11-20", "opp_first": "Ann", "opp_last": "Other", "seen": True},
        {"ref_id": "b", "code": "T", "event_type": "CH", "level": "Challenger main draw", "round": "QF",
         "event_name": "Somewhere", "event_date": "2023-11-20", "opp_first": "Dan", "opp_last": "Nobody", "seen": True},
        {"ref_id": "c", "code": "T", "event_type": "FU", "level": "ITF main draw", "round": "R32",
         "event_name": "M15 Place", "event_date": "2023-11-13", "opp_first": "Eve", "opp_last": "Hidden", "seen": False},
    ])
    ev = _events([
        {"sofa_id": "103", "code": "T", "ts": 1700600000, "sofa_round": "Round of 16", "opponent": "Ann Other"},
        {"sofa_id": "105", "code": "T", "ts": 1700600000, "sofa_round": "Round of 32", "opponent": "A. Other"},
    ])
    out = L.link(ref, ev).set_index("ref_id")
    assert out.loc["a", "sofa_status"] == "linked" and out.loc["a", "sofa_id"] == "103"
    assert out.loc["b", "sofa_status"] == "absent"
    assert out.loc["c", "sofa_status"] == "unobserved"


def test_same_opponent_in_consecutive_weeks_goes_to_the_named_tournament():
    ref = _ref([
        {"ref_id": "corr", "code": "T", "event_type": "CH", "level": "Challenger main draw", "round": "R32",
         "event_name": "Corrientes", "event_date": "2022-06-13", "opp_first": "Fermin", "opp_last": "Tenti", "seen": True},
        {"ref_id": "ba", "code": "T", "event_type": "CH", "level": "Challenger main draw", "round": "R32",
         "event_name": "Buenos Aires (Argentino)", "event_date": "2022-06-20", "opp_first": "Fermin",
         "opp_last": "Tenti", "seen": True},
    ])
    ev = _events([{"sofa_id": "1", "code": "T", "ts": 1655820000, "sofa_round": "Round of 32",
                   "opponent": "Fermin Tenti", "tournament": "Buenos Aires, Argentina"},
                  {"sofa_id": "2", "code": "T", "ts": 1655820000, "sofa_round": "Round of 32",
                   "opponent": "Fermin Tenti", "tournament": "Buenos Aires, Argentina"}])
    ev.loc[1, "status"] = "canceled"   # a cancelled duplicate of the same pairing
    out = L.link(ref, ev).set_index("ref_id")
    assert out.loc["ba", "sofa_id"] == "1" and out.loc["ba", "sofa_status"] == "linked"
    assert L.place_agrees("M25 Santo Domingo", "Santo Domingo, Singles M-ITF-DOM-01A") == 1
    assert L.place_agrees("Germany F9", "Germany F10, Singles") == 1
    assert L.place_agrees("Corrientes", "Buenos Aires, Argentina") == 0


def test_claims_map_level_year_and_share_onto_matches():
    ref = pd.DataFrame({"level": ["Challenger main draw", "Challenger main draw", "Tour main draw", "Tour main draw",
                                  "ITF main draw"],
                        "event_type": ["CH", "CH", "GS", "250", "FU"], "year": [2018, 2024, 2019, 2019, 2024]})
    claims = pd.DataFrame([
        {"source_id": "arch", "level": "Challenger main draw", "event_types": "", "year_from": "2013",
         "year_to": "2022", "share": "0.553"},
        {"source_id": "arch", "level": "Tour main draw", "event_types": "GS", "year_from": "2013",
         "year_to": "2022", "share": "0.98"},
        {"source_id": "feed", "level": "Challenger main draw", "event_types": "", "year_from": "2024",
         "year_to": "2026", "share": ""},
    ])
    out = F.claimed(ref, claims)
    assert list(out["arch"]) == [0.553, 0.0, 0.98, 0.0, 0.0]   # the 250 main draw is outside the GS-only claim
    assert list(out["feed"]) == [0.0, 1.0, 0.0, 0.0, 0.0]       # an unstated share counts as an upper bound of 1


def test_itf_recent_window():
    ref = pd.DataFrame({"level": ["ITF main draw", "ITF main draw", "ITF qualifying", "Challenger main draw"],
                        "year": [2024, 2025, 2026, 2025]})
    assert list(F.itf_recent(ref)) == [False, True, True, False]


def test_wilson_interval_brackets_the_share():
    lo, hi = C.wilson(6, 20)
    assert 0.14 < lo < 0.15 and 0.51 < hi < 0.53
    assert C.wilson(0, 0) == (0.0, 0.0)


def test_official_games_count_a_tiebreak_as_one_game():
    assert C.official_games("6-3 6-7(4) 7-5") == [9, 13, 12]
    assert C.official_games("7-6(5) 6-0") == [13, 6]
    assert C.era(2018) == "2012-18" and C.era(2025) == "2025-26"
