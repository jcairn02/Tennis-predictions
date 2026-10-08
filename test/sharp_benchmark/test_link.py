"""Offline tests for linking Polymarket markets to tennis-data rows and orienting them (no network, no staged data)."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.merge_feasibility import scan as S  # noqa: E402
from src.eda.sharp_benchmark import build as B  # noqa: E402


def td_rows(rows):
    td = pd.DataFrame(rows, columns=["td_id", "tour", "date", "winner", "loser"])
    td["date"] = pd.to_datetime(td.date)
    td["wk"], td["lk"] = td.winner.map(S.td_key), td.loser.map(S.td_key)
    return td


def pm_rows(rows):
    pm = pd.DataFrame(rows, columns=["condition_id", "tour", "day", "name_a", "name_b", "has_close", "volume"])
    pm["day"] = pd.to_datetime(pm.day)
    return pm


def test_multiword_and_hyphenated_surnames_link_in_either_title_order():
    td = td_rows([("r1", "atp", "2026-01-10", "De Minaur A.", "Auger-Aliassime F."),
                  ("r2", "atp", "2026-01-11", "Mpetshi Perricard G.", "Struff J.L."),
                  ("r3", "wta", "2026-01-12", "Haddad Maia B.", "Andreeva M.")])
    pm = pm_rows([("m1", "atp", "2026-01-11", "Felix Auger-Aliassime", "Alex de Minaur", True, 10.0),
                  ("m2", "atp", "2026-01-11", "Giovanni Mpetshi Perricard", "Jan-Lennard Struff", True, 10.0),
                  ("m3", "wta", "2026-01-12", "Mirra Andreeva", "Beatriz Haddad Maia", True, 10.0)])
    out = B.link(td, pm).set_index("td_id")
    assert out.condition_id.to_dict() == {"r1": "m1", "r2": "m2", "r3": "m3"}
    assert out.a_won.to_dict() == {"r1": False, "r2": True, "r3": False}
    assert out.loc["r1", "gap"] == 1


def test_window_tour_and_duplicate_listings():
    td = td_rows([("r1", "atp", "2026-03-10", "Sinner J.", "Alcaraz C."),
                  ("r2", "atp", "2026-03-10", "Fritz T.", "Paul T."),
                  ("r3", "wta", "2026-03-10", "Gauff C.", "Pegula J.")])
    pm = pm_rows([("dup_unpriced", "atp", "2026-03-10", "Jannik Sinner", "Carlos Alcaraz", False, 900.0),
                  ("dup_priced", "atp", "2026-03-10", "Jannik Sinner", "Carlos Alcaraz", True, 100.0),
                  ("too_late", "atp", "2026-03-13", "Taylor Fritz", "Tommy Paul", True, 10.0),
                  ("wrong_tour", "atp", "2026-03-10", "Coco Gauff", "Jessica Pegula", True, 10.0)])
    out = B.link(td, pm)
    assert out.td_id.tolist() == ["r1"] and out.condition_id.tolist() == ["dup_priced"]


def test_a_market_takes_the_nearest_of_two_rows_and_a_tie_takes_neither():
    td = td_rows([("near", "atp", "2026-05-02", "Ruud C.", "Rune H."),
                  ("far", "atp", "2026-05-04", "Ruud C.", "Rune H."),
                  ("tie_a", "wta", "2026-05-01", "Swiatek I.", "Rybakina E."),
                  ("tie_b", "wta", "2026-05-03", "Swiatek I.", "Rybakina E.")])
    pm = pm_rows([("m", "atp", "2026-05-02", "Casper Ruud", "Holger Rune", True, 1.0),
                  ("t", None, "2026-05-02", "Iga Swiatek", "Elena Rybakina", True, 1.0)])
    out = B.link(td, pm)
    assert out.td_id.tolist() == ["near"]


def test_players_with_the_same_surname_and_initial_are_not_linked():
    td = td_rows([("r", "wta", "2026-02-01", "Pliskova Ka.", "Pliskova Kr.")])
    pm = pm_rows([("m", "wta", "2026-02-01", "Karolina Pliskova", "Kristyna Pliskova", True, 1.0)])
    assert B.link(td, pm).empty


def test_outcome_labels_orient_the_market():
    assert B.first_player_outcome("Felix Auger-Aliassime", "Alex de Minaur", ["Auger-Aliassime", "de Minaur"]) == \
        (0, "both labels")
    assert B.first_player_outcome("Felix Auger-Aliassime", "Alex de Minaur", ["de Minaur", "Auger-Aliassime"]) == \
        (1, "both labels")
    assert B.first_player_outcome("Jan-Lennard Struff", "Lorenzo Sonego", ["Struff", "Player Two"]) == \
        (0, "first label")
    assert B.first_player_outcome("Jan-Lennard Struff", "Lorenzo Sonego", ["Yes", "No"]) == (0, "title order")


def test_odds_cleaning_and_season_redating():
    td = pd.DataFrame({"PSW": ["1.50", "0", "1.0", "5.05", None], "PSL": ["2.60", "2.0", "3.0", "17.0", "2.0"],
                       "BFEW": ["1.52", "1.52", "1.52", "1.52", "1.52"], "BFEL": ["2.80", "2.80", "2.80", "2.80", "2.80"],
                       "B365W": [None] * 5, "B365L": [None] * 5, "AvgW": [None] * 5, "AvgL": [None] * 5})
    td = B.clean_odds(td)
    assert td.ok_ps.tolist() == [True, False, False, False, False]      # 0 and 1.00 missing; 5.05/17.0 incoherent
    assert td.ok_bfe.all() and not td.ok_avg.any()
    dates = pd.to_datetime(pd.Series(["2029-07-20", "2025-12-29", "2026-08-03"]))
    assert B.outside_season(dates, pd.Series([2026, 2026, 2026])).tolist() == [True, False, False]
    assert B.outside_season(pd.to_datetime(pd.Series(["2024-12-29"])), pd.Series([2025])).tolist() == [False]
