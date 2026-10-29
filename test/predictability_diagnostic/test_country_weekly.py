"""The weekly check of the event-country table (src/eda/predictability_diagnostic/stage4_country_weekly.py) on toy
tables: which names it adds, which it leaves for a person, and that adding rows never changes the existing ones."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.predictability_diagnostic import stage4_country_weekly as W  # noqa: E402


def _miss(rows):
    return pd.DataFrame([{"match_id": m, "tour": t, "event_key": k, "tournament_name": n, "tournament_id": i,
                          "tournament_date": pd.Timestamp("2026-10-05"), "year": 2026} for m, t, k, n, i in rows])


def test_atp_ids_are_read_by_their_first_two_parts_and_french_territories_as_france():
    miss = _miss([("m1", "atp", "shanghai", "Shanghai", "2026-5014-20261007"),
                  ("m2", "atp", "noumea open", "Noumea Open", "2026-2205"),
                  ("m3", "atp", "itf thing", "ITF Thing", "2026-M-ITF-FRA-01")])
    atp = pd.DataFrame({"id": ["2026-5014", "2026-2205"], "location": ["Shanghai", "Noumea"],
                        "country_code": ["CHN", "CAL"]})
    r = W.atp_readings(miss, atp).set_index("match_id")["country"].to_dict()
    assert r == {"m1": "CHN", "m2": "FRA"}


def test_one_country_is_added_and_two_or_none_go_to_a_person():
    miss = _miss([("a1", "atp", "agree", "Agree Open", "2026-1"), ("a2", "atp", "agree", "Agree Open", "2026-1"),
                  ("b1", "atp", "split", "Split Open", "2026-2"), ("b2", "atp", "split", "Split Open", "2026-3"),
                  ("c1", "atp", "unknown", "Unknown Open", "2026-4")])
    readings = pd.DataFrame([
        {"match_id": "a1", "source": "the ATP's tournament list", "country": "ESP", "place": "Villena"},
        {"match_id": "a2", "source": "tennis-data's Location", "country": "ESP", "place": "Villena"},
        {"match_id": "b1", "source": "the ATP's tournament list", "country": "ITA", "place": "Rome"},
        {"match_id": "b2", "source": "the ATP's tournament list", "country": "FRA", "place": "Paris"}])
    d = W.decide(miss, readings).set_index("event_key")
    assert d.loc["agree", "decision"] == "add" and d.loc["agree", "country"] == "ESP"
    assert d.loc["split", "decision"] == "person" and "2 countries" in d.loc["split", "why"]
    assert d.loc["unknown", "decision"] == "person" and d.loc["unknown", "why"] == "no source places it"


def test_adding_rows_keeps_every_existing_row_and_the_order(tmp_path):
    p = tmp_path / "table.csv"
    old = ("tour,event_key,from_year,to_year,tournament_id,country,basis\n"
           "atp,alpha,,,,ITA,city in the name\n"
           "atp,gamma,2013,2015,,FRA,\"a basis, with a comma\"\n"
           "atp,gamma,,,2014-9,ESP,one id\n"
           "wta,alpha,,,,ITA,city in the name\n")
    p.write_bytes(old.encode("utf-8"))
    got = W.add_rows(p, [["atp", "beta", "", "", "", "POR", "new"], ["atp", "alpha", "", "", "", "XXX", "dup"],
                         ["wta", "zeta", "", "", "", "CHN", "new, too"]])
    assert got == [("atp", "beta"), ("wta", "zeta")]
    text = p.read_bytes().decode("utf-8")
    assert "\r" not in text
    lines = text.split("\n")
    assert lines[:2] == old.split("\n")[:2] and lines[2] == "atp,beta,,,,POR,new"
    assert lines[3:6] == old.split("\n")[2:5] and lines[6] == "wta,zeta,,,,CHN,\"new, too\""
    assert W.add_rows(p, [["atp", "beta", "", "", "", "POR", "again"]]) == []
    assert p.read_bytes().decode("utf-8") == text
