"""The Flashscore link check's verdicts and player order, P6's surname test and the refused links (offline,
synthetic)."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_downloads import verify_flashscore as VF  # noqa: E402


def test_the_record_is_put_in_the_targets_order():
    assert VF.target_order("Andreea Prisacariu", "Prisacariu A.") is True
    assert VF.target_order("Andreea Prisacariu", "Pfeifer L.") is False
    parsed = {"sets": [{"score": (0, 6)}, {"score": (4, 6)}]}
    assert VF.record_sets(parsed, home_is_name1=False) == [(6, 0), (6, 4)]


def test_the_record_is_put_in_order_by_both_players_surnames():
    # "O'Connell C." splits to "connell", which the first-word rule did not find in "Christopher Oconnell"
    assert VF.target_order("Christopher Oconnell", "O'Connell C.") is False
    assert VF.home_is_name1("Christopher Oconnell", "Yosuke Watanuki", "O'Connell C.", "Watanuki Y.") is True
    # both target players have "Ribeiro": the other player decides
    assert VF.home_is_name1("Igor Ribeiro Marcondes", "Eduardo Ribeiro", "Ribeiro E.", "Marcondes I.") is False
    # no surname matches either way: the first-word rule
    assert VF.home_is_name1("Alexander Sarkissian", "Bradley Mousley", "Klahn B.", "Zverev A.") is False


def test_verdicts():
    assert VF.compare([(6, 4), (7, 6)], "6-4 7-6(5)") == "agrees"
    assert VF.compare([(6, 4), (5, 4)], "6-4 6-4") == "winner agrees, score differs"
    assert VF.compare([(4, 6), (3, 6)], "6-4 6-3") == "winner differs"
    assert VF.compare([], "6-4 6-4") == "no record"
    # a retirement before the next set: the official score writes the set never started as 0-0
    assert VF.compare([(6, 0)], "6-0 0-0") == "agrees"
    assert VF.compare([(5, 7), (6, 4)], "5-7 6-4 0-0 RET") == "agrees"
    # a retirement inside a set: all but the unfinished set must agree
    assert VF.compare([(6, 3), (2, 1)], "6-3 2-0 RET") == "agrees"


def test_p6s_surname_test_on_flashscore_names():
    assert VF.surnames_agree("Marcel Granollers", "Daniel Evans", "Granollers M.", "Evans D.")
    assert VF.surnames_agree("Daniel Evans", "Marcel Granollers", "Granollers M.", "Evans D.")      # either order
    # a borrowed link of the trial: both first names shared, no surname (Alexander, Bradley)
    assert not VF.surnames_agree("Alexander Sarkissian", "Bradley Mousley", "Klahn B.", "Zverev A.")
    assert VF.surnames_agree("Elmer Moeller", "Alex de Minaur", "Møller E.", "De Minaur A.")         # spelling; particle
    # one surname, two players: the test cannot tell Darian King from Evan King
    assert VF.surnames_agree("Martin Klizan", "Darian King", "King E.", "Klizan M.")


def test_a_link_the_official_result_contradicts_is_refused():
    assert VF.refused("winner differs") and VF.refused("winner agrees, score differs")
    assert not any(VF.refused(v) for v in ("agrees", "no official row", "no record", "not fetched", "not linked"))
    # the rule first declared refuses only when the surnames differ too
    assert VF.both_tests_fail(False, "winner differs") and not VF.both_tests_fail(True, "winner differs")
    assert not VF.both_tests_fail(False, "no official row")


def test_check_table_reads_p6s_table_and_marks_the_refused_links(monkeypatch):
    # P6's per-target table: no edition column; one feed linked to two targets (a borrowed link)
    t = pd.DataFrame([
        {"gap": "atp_points_2018_2020", "uid": "1", "tour": "M", "level": "TQ", "draw": "qual", "d": "2019-04-22",
         "tname": "Barcelona", "name1": "Marcel Granollers", "name2": "Daniel Evans", "creator": "tml",
         "fs_id": "AAA", "fs_home": "Granollers M.", "fs_away": "Evans D."},
        {"gap": "challenger_points_2018_2021", "uid": "2", "tour": "M", "level": "CH", "draw": "main",
         "d": "2019-04-07", "tname": "Monterrey", "name1": "Marcel Granollers", "name2": "Daniel Elahi Galan",
         "creator": "sackmann", "fs_id": "AAA", "fs_home": "Granollers M.", "fs_away": "Evans D."},
        {"gap": "challenger_points_2018_2021", "uid": "3", "tour": "M", "level": "CH", "draw": "main",
         "d": "2018-02-26", "tname": "Indian Wells", "name1": "Martin Klizan", "name2": "Darian King",
         "creator": "sackmann", "fs_id": "BBB", "fs_home": "King E.", "fs_away": "Klizan M."},
        {"gap": "tour_points_rest", "uid": "4", "tour": "M", "level": "T250", "draw": "main", "d": "2022-01-30",
         "tname": "Pune", "name1": "A. Celikbilek", "name2": "S. K. Mukund", "creator": "api_tennis",
         "fs_id": "CCC", "fs_home": "Celikbilek A.", "fs_away": "Sasikumar M."},
        {"gap": "tour_points_rest", "uid": "5", "tour": "M", "level": "T250", "draw": "main", "d": "2022-01-30",
         "tname": "Pune", "name1": "Ann Other", "name2": "Some One", "creator": "tml", "fs_id": "",
         "fs_home": "", "fs_away": ""}])
    official = pd.DataFrame([("Barcelona", "2019-04-22", "Marcel Granollers", "Daniel Evans", "qual", "6-4 6-4", "tml"),
                             ("Monterrey", "2019-04-07", "Marcel Granollers", "Daniel Elahi Galan", "main", "7-5 6-1",
                              "sackmann"),
                             ("Indian Wells", "2018-02-26", "Martin Klizan", "Darian King", "main", "6-3 6-3",
                              "sackmann")],
                            columns=VF.V.KEY + ["score", "official"])
    sets = {"AAA": [(6, 4), (6, 4)], "BBB": [(6, 4), (6, 4)], "CCC": [(6, 3), (6, 3)]}   # home first
    monkeypatch.setattr(VF.V, "official_rows", lambda tnames: official)
    monkeypatch.setattr(VF.P, "receipts_for", lambda source: None)
    monkeypatch.setattr(VF.F, "feed_status", lambda receipts, fs_id: 200)
    monkeypatch.setattr(VF.F, "read_feed", lambda receipts, fs_id: fs_id)
    monkeypatch.setattr(VF.F, "parse_feed", lambda text: {"sets": [{"score": s} for s in sets[text]]})
    frame, summary = VF.check_table(t, "p6")
    got = frame.set_index("uid")
    assert got["verdict"].to_dict() == {"1": "agrees", "2": "winner agrees, score differs", "3": "winner differs",
                                        "4": "no official row", "5": "not linked"}
    assert got["link_refused"].to_dict() == {"1": False, "2": True, "3": True, "4": False, "5": False}
    assert got["both_tests_fail"].to_dict() == {"1": False, "2": True, "3": False, "4": False, "5": False}
    assert got.loc["3", "fs_sets"] == "4-6 4-6"          # King E. is home: put in the target's order, Klizan first
    assert (summary["link_refused"], summary["both_tests_fail"]) == (2, 1)
    assert summary["verdict_by_surnames"]["False"] == {"winner agrees, score differs": 1, "no official row": 1}
