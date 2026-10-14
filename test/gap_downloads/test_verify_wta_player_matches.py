"""The check of the WTA API's player-matches results (src/eda/gap_downloads/verify_wta_player_matches.py), offline."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_downloads import verify_wta_player_matches as V  # noqa: E402
from src.ingest.point_sources import wta as W  # noqa: E402


def results() -> pd.DataFrame:
    r = pd.DataFrame({
        "match_key": ["k1", "k2", "k3"], "tournament_group_id": ["4826", "4826", "9999"],
        "start_date": ["2026-08-31", "2026-08-31", "2026-09-21"], "title": ["WTT W50 - LEIRIA, PORTUGAL"] * 2 +
        ["WTT W35 - YECLA, SPAIN"], "level": ["ITF"] * 3, "qpm_flag": ["M", "Q", "M"], "round_name": ["R32", "R16", "Q"],
        "winner_id": ["332174", "331077", "327137"], "loser_id": ["331077", "324673", "331077"],
        "winner_name": ["Hayu Kinoshita", "Rebecca Munk Mortensen", "Sofia Rojas"],
        "loser_name": ["Rebecca Munk Mortensen", "Maria Toma", "Rebecca Munk Mortensen"],
        "scores": ["6-0  7-5", "6-2  6-4", "4-6  6-3  2-0"], "reason_code": ["W", "W", "R"]})
    r["d"] = pd.to_datetime(r["start_date"])
    return r


def test_itf_live_sets_and_scores():
    assert V.itf_live_sets("1:5/0 2:6/0 3:6/0", "1:7/0 2:0/0 3:1/0") == "5-7 6-0 6-1"
    assert V.itf_live_sets("1:7/7 2:6/0", "1:6/5 2:3/0") == "7-6 6-3"   # tiebreak points left aside
    assert V.same_score("6-0  7-5", "6-0 7-5") and not V.same_score("6-0 7-5", "7-5 6-0")


def test_result_keys_are_symmetric_and_need_both_ids():
    r = results()
    keys = V.result_keys(r)
    assert keys[0] == "4826|2026-08-31|M|R32|331077|332174"
    swapped = r.assign(winner_id=r["loser_id"], loser_id=r["winner_id"])
    assert list(V.result_keys(swapped)) == list(keys)
    assert pd.isna(V.result_keys(r.assign(loser_id=[None, "1", "2"]))[0])


def test_results_become_official_rows_in_the_maps_round_form():
    off = V.as_official(results())
    assert list(off["round"]) == ["R32", "Q1", "QF"]          # Leiria's only qualifying row here is its first round
    assert list(off["draw"]) == ["main", "qual", "main"]
    assert off["score"].iloc[2].endswith(" RET") and list(off["official"]) == ["k1", "k2", "k3"]
    assert off["pair"].iloc[0] == "kinoshita|mortensen"


def test_listed_matches_are_found_or_not_in_the_results():
    official = V.as_official(results())
    listed = pd.DataFrame({
        "event_key": ["e1", "e2"], "event_name": ["W35 Yecla", "W35 Elsewhere"], "event_kind": ["itf", "itf"],
        "tour": ["W", "W"], "match_id": ["m1", "m2"], "draw": ["main", "main"], "round": ["QF", "R32"],
        "day": pd.to_datetime(["2026-09-24", "2026-09-22"]), "winner_side": ["2", "1"],
        "score": ["6-4 3-6 0-2", "6-1 6-1"], "player1_name": ["Rebecca Munk Mortensen", "Ana Uno"],
        "player2_name": ["Sofia Rojas", "Bea Dos"], "end_reason": ["retired", ""]})
    listed["k1"], listed["k2"] = listed["player1_name"].map(V.M.surname_key), listed["player2_name"].map(V.M.surname_key)
    listed["pair"] = V.M.pair_key(listed["k1"], listed["k2"])
    listed["year"] = 2026
    summary, out = V.against("unit", listed, official, "2026-09-07")
    assert list(out["verdict"]) == ["agrees", "not in the results"]
    assert summary["results_after_cut"] == 1 and summary["results_after_cut_confirmed"] == 1


def test_the_kaggle_copy_is_compared_by_edition_draw_round_and_ids(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "KAGGLE", tmp_path)
    pd.DataFrame({"pseudo_tournament_id": [11], "startDate": ["2026-08-31"], "level": ["ITF"],
                  "tournamentGroupId": [4826]}).to_csv(tmp_path / "tournaments.csv", index=False)
    pd.DataFrame({"pseudo_tournament_id": [11, 11, 11, 11], "player_1": [331077, 332174, 331077, 331077],
                  "player_2": ["332174", "331077", "324673", "BYE"], "winner": [2, 1, 1, 1],
                  "reason_code": ["W", "W", "W", "B"], "qpm_flag": ["M", "M", "Q", "Q"],
                  "round_name": ["R32", "R32", "R16", "R32"], "scores": ["6-0  7-5", "6-0  7-5", "6-2 6-3", ""]}
                 ).to_csv(tmp_path / "matches.csv", index=False)
    got = V.check_kaggle(results(), 2026)
    assert got["kaggle_matches"] == 2 and got["found_in_results"] == 2   # the bye is left out, the pair kept once
    assert got["same_winner"] == 2 and got["different_winner"] == 0
    assert got["same_score"] == 1                                       # 6-2 6-3 against the results' 6-2 6-4
    assert got["kaggle_matches_listed_with_two_winners"] == 0
    assert got["itf_results_not_in_kaggle"] == 1                         # Yecla, after the copy
    assert got["found_by_month"]["2026-09"] == {"kaggle": 0, "found": 0, "results_not_in_kaggle": {"M": 1}}
