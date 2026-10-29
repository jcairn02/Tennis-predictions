"""A2's name check reads the shared Stage 0 with the decided id aliases applied (28 Oct 2026, the owner: "fix mensik"):
a player's second id merged after the shared tables' build no longer makes his name ambiguous."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.input_data_audit import corrections as X  # noqa: E402
from src.pipeline import live as L  # noqa: E402

NO_TML = pd.DataFrame(columns=["winner_name", "loser_name", "_wk", "_lk"])


def shared_stage0(tmp_path: Path) -> Path:
    rows = [("atp|2023-1|Q1|atp:1|atp:210084", "atp:210084", "Jakub Mensik"),
            ("atp|2026-2|R32|atp:2|atp:210150", "atp:210150", "Jakub Mensik"),
            ("atp|2026-2|R32|atp:2|atp:210150", "atp:2", "Other Player"),
            ("wta|2026-3|R32|wta:9|wta:210084", "wta:210084", "Jakub Mensik")]
    pd.DataFrame(rows, columns=["match_id", "player_id", "player_name"]).to_parquet(
        tmp_path / "stage0_match_players.parquet", index=False)
    return tmp_path


def test_a_merged_second_id_names_its_player_once(tmp_path, monkeypatch):
    monkeypatch.setattr(L.CFG, "STAGE0", shared_stage0(tmp_path))
    table = tmp_path / "id_aliases.csv"
    monkeypatch.setattr(X, "ID_ALIASES", table)
    pd.DataFrame(columns=["tour", "from_id", "to_id", "name_key"]).to_csv(table, index=False)
    assert "names 2 Stage 0 players" in L._player("Jakub Mensik", "atp", L._stage0_keys("atp"), NO_TML, {})[2]
    pd.DataFrame([{"tour": "atp", "from_id": "atp:210084", "to_id": "atp:210150", "name_key": "jakub mensik"}]).to_csv(
        table, index=False)
    assert L._player("Jakub Mensik", "atp", L._stage0_keys("atp"), NO_TML, {}) == ("Jakub Mensik", "atp:210150", "stage0")
    assert set(L._stage0_keys("wta")["player_id"]) == {"wta:210084"}          # an alias holds for its own tour only


def test_no_table_leaves_the_ids_as_they_are(tmp_path, monkeypatch):
    monkeypatch.setattr(L.CFG, "STAGE0", shared_stage0(tmp_path))
    monkeypatch.setattr(X, "ID_ALIASES", tmp_path / "missing.csv")
    assert set(L._stage0_keys("atp")["player_id"]) == {"atp:210084", "atp:210150", "atp:2"}
