"""stage0_build.apply_box_overrides with the optional source column (the Roland-Garros candidate of 9 Oct 2026)."""
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
