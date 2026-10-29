"""Offline tests of the id-alias check of the retrain register (verify_aliases.py): an alias is in a Stage 0 when no
player row of its tour carries the second id and the established id has rows."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.input_data_audit import verify_aliases as V  # noqa: E402

ALIAS = pd.DataFrame([{"tour": "atp", "from_id": "atp:210084", "to_id": "atp:210150", "name_key": "jakub mensik"}])


def stage0(tmp_path: Path, ids: list[tuple[str, str]]) -> Path:
    rows = [{"match_id": f"{t}|2023-1|R32|{i}|x{n}", "player_id": i} for n, (t, i) in enumerate(ids)]
    pd.DataFrame(rows).to_parquet(tmp_path / "stage0_match_players.parquet", index=False)
    return tmp_path


def test_an_alias_is_in_a_stage0_built_with_it(tmp_path):
    got = V.check(stage0(tmp_path, [("atp", "atp:210150"), ("atp", "atp:210150"), ("atp", "atp:1")]), ALIAS)
    assert got["ok"] and got["aliases"]["atp:210084"]["rows_established_id"] == 2


def test_an_alias_is_not_in_a_stage0_that_still_holds_the_second_id(tmp_path):
    got = V.check(stage0(tmp_path, [("atp", "atp:210084"), ("atp", "atp:210150")]), ALIAS)
    assert not got["ok"] and got["aliases"]["atp:210084"]["rows_second_id"] == 1


def test_the_established_id_must_have_rows_of_its_tour(tmp_path):
    assert not V.check(stage0(tmp_path, [("wta", "atp:210150"), ("atp", "atp:1")]), ALIAS)["ok"]


def test_the_command_exits_1_until_the_alias_is_in(tmp_path, capsys):
    table = tmp_path / "aliases.csv"
    ALIAS.to_csv(table, index=False)
    folder = stage0(tmp_path, [("atp", "atp:210084"), ("atp", "atp:210150")])
    assert V.main(["--stage0", str(folder), "--aliases", str(table)]) == 1
    assert '"atp:210084"' in capsys.readouterr().out
    stage0(tmp_path, [("atp", "atp:210150")])
    assert V.main(["--stage0", str(folder), "--aliases", str(table), "--instance", "x"]) == 0
    with pytest.raises(SystemExit):
        V.main(["--stage0", str(folder), "--aliases", str(table), "--only", "atp:999"])
