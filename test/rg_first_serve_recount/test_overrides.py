"""stage0_build.apply_box_overrides with the optional source column (the Roland-Garros candidate of 9 Oct 2026), and
with a name its source re-spelled since the table was built (28 Oct 2026; master pipeline process log, Part 21)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402


def frame() -> pd.DataFrame:
    """Two raw rows of one match, as normalise() keys them: Sackmann's (blank box) and TML's (a box)."""
    base = {"tour": "atp", "tid": "2026-520", "round": "R128", "wkey": "sinner", "lkey": "doe", "score": "6-1 6-1 6-1",
            "minutes": ""}
    rows = [dict(base, source="sackmann", rid=0, **{c: "" for c in B.OVERRIDE_COUNTS}),
            dict(base, source="tml", rid=1, **{c: "1" for c in B.OVERRIDE_COUNTS})]
    return pd.DataFrame(rows)


def table(source: str | None = None, lkey: str = "doe") -> pd.DataFrame:
    row = {"tour": "atp", "tid": "2026-520", "round": "R128", "winner_key": "sinner", "loser_key": lkey,
           "score": "", "minutes": "", **{c: "7" for c in B.OVERRIDE_COUNTS}}
    if source is not None:
        row["source"] = source
    return pd.DataFrame([row])


def test_a_table_without_source_names_tml_rows_only():
    out = B.apply_box_overrides(frame(), table(), "t.csv", {})
    assert (out.loc[1, B.OVERRIDE_COUNTS] == "7").all()
    assert (out.loc[0, B.OVERRIDE_COUNTS] == "").all()


def test_a_blank_source_means_tml():
    out = B.apply_box_overrides(frame(), table(""), "t.csv", {})
    assert (out.loc[1, B.OVERRIDE_COUNTS] == "7").all() and (out.loc[0, B.OVERRIDE_COUNTS] == "").all()


def test_source_sackmann_names_the_sackmann_row():
    summary = {}
    out = B.apply_box_overrides(frame(), table("sackmann"), "t.csv", summary)
    assert (out.loc[0, B.OVERRIDE_COUNTS] == "7").all()
    assert (out.loc[1, B.OVERRIDE_COUNTS] == "1").all()
    assert summary["box_overrides"]["rows"] == 1


def test_an_override_that_names_no_row_stops_the_build():
    with pytest.raises(SystemExit):
        B.apply_box_overrides(frame(), table("sackmann", lkey="roe"), "t.csv", {})


def test_an_override_that_names_two_rows_stops_the_build():
    f = pd.concat([frame(), frame().iloc[[0]].assign(rid=2)], ignore_index=True)
    with pytest.raises(SystemExit):
        B.apply_box_overrides(f, table("sackmann"), "t.csv", {})


def test_an_unknown_source_stops_the_build():
    with pytest.raises(SystemExit):
        B.apply_box_overrides(frame(), table("wta_api"), "t.csv", {})


def test_a_table_without_score_or_minutes_replaces_only_the_counts():
    out = B.apply_box_overrides(frame(), table("sackmann").drop(columns=["score", "minutes"]), "t.csv", {})
    assert (out.loc[0, B.OVERRIDE_COUNTS] == "7").all() and out.loc[0, "score"] == "6-1 6-1 6-1"


def named_frame() -> pd.DataFrame:
    """Two TML rows of one round with their names, as Tennis My Life wrote them on 26 Oct 2026."""
    base = {"source": "tml", "tour": "wta", "tid": "2026-905", "round": "R128", "minutes": "",
            **{c: "1" for c in B.OVERRIDE_COUNTS}}
    rows = [("Xin Yu Wang", "Emiliana Arango", "6-4 6-2"), ("Eva Lys", "Gabriela Andrea Knutson", "6-3 6-3")]
    return pd.DataFrame([dict(base, rid=i, winner_name=w, loser_name=l, wkey=B.S.name_key(w), lkey=B.S.name_key(l),
                              score=s) for i, (w, l, s) in enumerate(rows)])


def named_table(winner: str = "Xinyu Wang", loser: str = "Emiliana Arango", tml_score: str = "6-4 6-2") -> pd.DataFrame:
    """One override as the table recorded it, before the re-spelling (by default the first row's)."""
    return pd.DataFrame([{"tour": "wta", "tid": "2026-905", "round": "R128", "winner_key": B.S.name_key(winner),
                          "loser_key": B.S.name_key(loser), "winner_name": winner, "loser_name": loser,
                          "tml_score": tml_score, "score": "", "minutes": "", **{c: "7" for c in B.OVERRIDE_COUNTS}}])


@pytest.mark.parametrize("old, new, same", [
    ("Xinyu Wang", "Xin Yu Wang", True), ("Alexander Shevchenko", "Aleksandr Shevchenko", True),
    ("Gabriela Knutson", "Gabriela Andrea Knutson", True), ("Wang Xinyu", "Xinyu Wang", True),
    ("Anna Blinkova", "Anna Kalinskaya", False), ("", "Xin Yu Wang", False)])
def test_respelled(old, new, same):
    assert B.respelled(old, new) is same


def test_a_respelled_winner_finds_its_row_and_is_listed():
    summary = {}
    out = B.apply_box_overrides(named_frame(), named_table(), "t.csv", summary)
    assert (out.loc[0, B.OVERRIDE_COUNTS] == "7").all() and (out.loc[1, B.OVERRIDE_COUNTS] == "1").all()
    assert summary["box_overrides"]["respelled"] == [{"override": "tml|wta|2026-905|R128|wang xinyu|arango emiliana",
                                                      "table": "Xinyu Wang d. Emiliana Arango",
                                                      "source_now": "Xin Yu Wang d. Emiliana Arango"}]


def test_a_respelled_loser_finds_its_row():
    out = B.apply_box_overrides(named_frame(), named_table("Eva Lys", "Gabriela Knutson", "6-3 6-3"), "t.csv", {})
    assert (out.loc[1, B.OVERRIDE_COUNTS] == "7").all() and (out.loc[0, B.OVERRIDE_COUNTS] == "1").all()


def test_both_players_respelled_find_their_row():
    out = B.apply_box_overrides(named_frame(), named_table("Xinyu Wang", "Emilia Arango"), "t.csv", {})
    assert (out.loc[0, B.OVERRIDE_COUNTS] == "7").all()


def test_a_row_found_by_its_names_is_not_listed():
    summary = {}
    B.apply_box_overrides(named_frame(), named_table("Xin Yu Wang"), "t.csv", summary)
    assert summary["box_overrides"]["respelled"] == []


def test_another_score_still_stops_the_build():
    with pytest.raises(SystemExit):
        B.apply_box_overrides(named_frame(), named_table(tml_score="6-4 6-3"), "t.csv", {})


def test_another_player_sharing_only_a_first_name_still_stops_the_build():
    with pytest.raises(SystemExit):
        B.apply_box_overrides(named_frame(), named_table(loser="Emiliana Smith"), "t.csv", {})


def test_winner_and_loser_exchanged_still_stop_the_build():
    with pytest.raises(SystemExit):
        B.apply_box_overrides(named_frame(), named_table("Emiliana Arango", "Xinyu Wang"), "t.csv", {})


def test_two_respelled_candidates_still_stop_the_build():
    f = pd.concat([named_frame(), named_frame().iloc[[0]].assign(rid=2, winner_name="Xin-Yu Wang")], ignore_index=True)
    with pytest.raises(SystemExit):
        B.apply_box_overrides(f, named_table(), "t.csv", {})


def test_one_row_named_twice_still_stops_the_build():
    ov = pd.concat([named_table("Xin Yu Wang"), named_table()], ignore_index=True)
    with pytest.raises(SystemExit):
        B.apply_box_overrides(named_frame(), ov, "t.csv", {})
