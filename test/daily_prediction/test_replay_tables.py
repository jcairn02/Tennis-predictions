"""An exact replay's tables are the instance's own (dp_common.replay_tables, dp_tables.replay_steps / trim_timeline,
additions.py --accepted-json; 16 Oct 2026). Fast: small files in tmp_path; the real replay is the process log's proof.
The bug: a replay built Stage 0 on the 8 Oct dump view whatever the instance, merged today's accepted.json, and met the
repository's newer timeline at the merge, so since 14 Oct every exact replay failed ("the merge made duplicate ...").
Run: ./python.sh -m pytest test/daily_prediction/test_replay_tables.py -q
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

import dp_common as DC
import dp_tables as TB

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import additions as AD  # noqa: E402


def view(path: Path, freeze: str = "2026-10-14 04:12:16+00:00") -> Path:
    path.mkdir(parents=True)
    (path / "freeze_dump.json").write_text(json.dumps({"freeze": freeze}), encoding="utf-8")
    return path


def package(accepted: Path, name: str) -> Path:
    p = accepted / name
    p.mkdir(parents=True)
    (p / "matches.parquet").write_bytes(b"x")
    h = hashlib.sha256(b"x").hexdigest()
    (p / "manifest.json").write_text(json.dumps({"files": {"matches.parquet": h}}), encoding="utf-8")
    return p


@pytest.fixture
def world(tmp_path):
    acc = tmp_path / "accepted_additions"
    for n in ("men_2026_ch_chq", "lower_level_feed/20261013c", "men_lower_level_fill", "lower_level_feed/20261014"):
        package(acc, n)
    inst = tmp_path / "template_2026-10-14"
    inst.mkdir()
    reg = tmp_path / "replay_views.json"
    return {"acc": acc, "inst": inst, "reg": reg, "tmp": tmp_path}


def write_reg(w, entry: dict) -> None:
    w["reg"].write_text(json.dumps({"_about": "test", w["inst"].name: entry}), encoding="utf-8")


def test_view_from_the_registry_and_additions_from_the_instance_build(world):
    v = view(world["tmp"] / "freeze_1014")
    write_reg(world, {"dump_view": str(v)})
    (world["inst"] / "chain_additions.json").write_text(json.dumps({"applied": {"packages": [
        {"package": str(world["acc"]).upper().replace("/", "\\") + "\\lower_level_feed\\20261013c"}]}}),
        encoding="utf-8")
    rt = DC.replay_tables(world["inst"], None, world["reg"], world["acc"])
    assert rt["dump_view"] == str(v) and rt["freeze"] == "2026-10-14 04:12:16+00:00"
    assert rt["additions"] == {"packages": ["lower_level_feed/20261013c"], "feeds": {}}
    assert rt["additions_from"].endswith("chain_additions.json")


def test_accepted_at_build_wins_and_an_explicit_view_overrides(world):
    write_reg(world, {"dump_view": str(view(world["tmp"] / "other"))})
    (world["inst"] / "accepted_at_build.json").write_text(json.dumps(
        {"packages": ["men_lower_level_fill"], "feeds": {"lower_level_feed": "20261014"}, "retired": {}}),
        encoding="utf-8")
    (world["inst"] / "chain_additions.json").write_text(json.dumps({"applied": {"packages": []}}), encoding="utf-8")
    v = view(world["tmp"] / "freeze_1016", "2026-10-14 21:19:58+00:00")
    rt = DC.replay_tables(world["inst"], v, world["reg"], world["acc"])
    assert rt["dump_view"] == str(v) and rt["view_from"] == "DP_FREEZE_DUMP"
    assert rt["additions"] == {"packages": ["men_lower_level_fill"], "feeds": {"lower_level_feed": "20261014"}}


def test_registry_additions_for_an_instance_that_records_none(world):
    write_reg(world, {"dump_view": str(view(world["tmp"] / "freeze_0810")),
                      "additions": {"packages": ["men_2026_ch_chq"], "feeds": {}}})
    assert DC.replay_tables(world["inst"], None, world["reg"], world["acc"])["additions"]["packages"] == \
        ["men_2026_ch_chq"]


def test_refusals(world):
    with pytest.raises(SystemExit, match="no dump view"):                      # the 8 Oct view is no default
        DC.replay_tables(world["inst"], None, world["reg"], world["acc"])
    write_reg(world, {"dump_view": str(world["tmp"] / "not_a_view")})
    with pytest.raises(SystemExit, match="not a dump view"):
        DC.replay_tables(world["inst"], None, world["reg"], world["acc"])
    write_reg(world, {"dump_view": str(view(world["tmp"] / "v"))})
    with pytest.raises(SystemExit, match="no record of the additions"):         # never today's accepted.json
        DC.replay_tables(world["inst"], None, world["reg"], world["acc"])
    (world["inst"] / "accepted_at_build.json").write_text(json.dumps({"packages": ["gone"]}), encoding="utf-8")
    with pytest.raises(SystemExit, match="no longer holds"):
        DC.replay_tables(world["inst"], None, world["reg"], world["acc"])


def test_the_merge_lists_the_given_list_not_accepted_json(world):
    (world["acc"] / "accepted.json").write_text(json.dumps(
        {"packages": ["men_lower_level_fill"], "feeds": {"lower_level_feed": "20261014"}}), encoding="utf-8")
    lst = world["tmp"] / "accepted_for_replay.json"
    lst.write_text(json.dumps({"packages": ["lower_level_feed/20261013c"], "feeds": {}}), encoding="utf-8")
    assert [p.relative_to(world["acc"]).as_posix() for p in AD.listed(world["acc"], lst)] == \
        ["lower_level_feed/20261013c"]
    assert [p.relative_to(world["acc"]).as_posix() for p in AD.listed(world["acc"])] == \
        ["men_lower_level_fill", "lower_level_feed/20261014"]
    with pytest.raises(SystemExit, match="no such list"):
        AD.listed(world["acc"], world["tmp"] / "missing.json")


def test_replay_steps_merge_the_instances_list():
    steps = [("stage0", "s.py", ["--live-rows", "x"]), ("additions", "a.py", ["--apply"]), ("odds", "o.py", []),
             ("additions_window", "a.py", ["--pin-timing"])]
    out = TB.replay_steps(steps, Path("run/accepted_for_replay.json"))
    lst = str(Path("run/accepted_for_replay.json"))
    assert out[1][2] == ["--apply", "--accepted-json", lst] and out[3][2] == ["--pin-timing", "--accepted-json", lst]
    assert out[0] == steps[0] and out[2] == steps[2]


def test_trim_timeline_drops_matches_the_tree_lacks(tmp_path):
    (tmp_path / DC.PD).mkdir(parents=True)
    (tmp_path / DC.MT).mkdir(parents=True)
    pd.DataFrame({"match_id": ["m1", "m2"]}).to_parquet(tmp_path / DC.PD / "stage0_matches.parquet", index=False)
    pd.DataFrame({"match_id": ["m1", "m2", "tml_newer"], "es": [1.0, 2.0, 3.0]}).to_parquet(
        tmp_path / DC.MT / "timing.parquet", index=False)
    rec = TB.trim_timeline(tmp_path)
    assert rec["rows"] == 2 and rec["dropped"] == 1
    assert pd.read_parquet(tmp_path / DC.MT / "timing.parquet")["match_id"].tolist() == ["m1", "m2"]
