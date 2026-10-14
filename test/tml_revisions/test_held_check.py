"""Tests of the held-file check (src/eda/tml_revisions/held_check.py; docs/decisions/2026-10-13-tml-lower-level-revisions.md):
the pairing that explains a dropped and a new match as one match under a new key, the held versions it finds, and the
folder each file stages to. The builds themselves are run by hand (they take minutes and a scratch tree).

Run: ./python.sh -m pytest test/tml_revisions -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.tml_revisions import held_check as HC  # noqa: E402


def row(mid, tid="2026-1", a="p1", b="p2", score="6-4 6-4", day="2026-06-08", rnd="R32"):
    return {"match_id": mid, "tour": "atp", "tournament_id": tid, "tournament_date": pd.Timestamp(day), "round": rnd,
            "score": score, "player_a_id": a, "player_b_id": b}


def test_explain_names_a_rebuilt_key_a_new_event_id_and_a_new_player():
    gone = pd.DataFrame([row("k_old", b="code:X"), row("e_old", tid="Rome", score="6-1 6-1"),
                         row("p_old", a="p3", b="p4", score="7-5 7-5"), row("lost", score="6-0 6-0")])
    gone.loc[0, "player_b_id"] = "p2"                    # the id columns after Stage 0's aliases: the same players
    new = pd.DataFrame([row("k_new", a="p2", b="p1"),    # same event, same players, sides swapped
                        row("e_new", tid="2026-2781", score="6-1 6-1"),
                        row("p_new", a="p3", b="p9", score="7-5 7-5")])
    pairs = HC.explain(new, gone).set_index("old_id")
    assert pairs.loc["k_old", "new_id"] == "k_new" and pairs.loc["k_old", "kind"] == "key"
    assert pairs.loc["e_old", "new_id"] == "e_new" and pairs.loc["e_old", "kind"] == "event"
    assert pairs.loc["p_old", "new_id"] == "p_new" and pairs.loc["p_old", "kind"] == "player"
    assert "lost" not in pairs.index                      # nothing new shares its round, date and score


def test_explain_needs_a_player_in_common():
    gone = pd.DataFrame([row("a", a="p1", b="p2")])
    new = pd.DataFrame([row("b", a="p7", b="p8")])        # same round, date and score, other players
    assert HC.explain(new, gone).empty


def test_held_files_reads_the_gates_records(tmp_path, monkeypatch):
    held = tmp_path / "held"
    held.mkdir()
    (held / "2024_challenger.ca3a597f1a97.csv").write_text("tourney_id\n", encoding="utf-8")
    (held / "2024_challenger.ca3a597f1a97.csv.meta.json").write_text(json.dumps(
        {"sha256": "ca3a597f1a97" + "0" * 52, "name": "2024_challenger.csv", "reason": "127 rows of the current copy "
         "are gone (more than 5)", "held_at": "2026-10-13T23:53:19+00:00"}), encoding="utf-8")
    monkeypatch.setattr(HC, "HELD", held)
    got = HC.held_files()
    assert len(got) == 1 and got[0]["name"] == "2024_challenger.csv" and got[0]["subdir"] == "atp_challenger"
    assert got[0]["path"] == held / "2024_challenger.ca3a597f1a97.csv"
    with pytest.raises(SystemExit):
        HC.held_files(["2023_challenger.csv"])             # asked for a file that is not held


@pytest.mark.parametrize("name, subdir", [("2025_challenger.csv", "atp_challenger"), ("2025.csv", "atp_main"),
                                          ("2025_wta.csv", "wta_main"),
                                          ("atp_quali/2011_atp_quali.csv", "atp_qualifying")])
def test_each_season_file_stages_to_the_adapters_folder(name, subdir):
    assert HC.subdir_of(name) == subdir
    assert HC.staged_path(Path("X"), name).parent.name == subdir


def test_the_tree_must_be_outside_the_repository(monkeypatch):
    monkeypatch.setattr(HC, "TREE", ROOT / "data" / "scratch_tree_test")
    monkeypatch.setattr(HC, "held_files", lambda names=None: [{"name": "2024_challenger.csv",
                                                               "subdir": "atp_challenger"}])
    with pytest.raises(SystemExit, match="outside the repository"):
        HC.setup(None)
    assert not (ROOT / "data" / "scratch_tree_test").exists()
