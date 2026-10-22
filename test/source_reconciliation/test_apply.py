"""Offline tests of the 22 Oct 2026 repairs' machinery (docs/decisions/2026-10-22-source-reconciliation-repairs.md):
the score-marker row action, the per-event corrections Stage 0's builder applies, the history check's acceptance of
their matches, an id alias the source itself now satisfies, and the register of revisions pending at a retrain."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.eda.current_best_model import history as H  # noqa: E402
from src.eda.current_best_model import pending as PEND  # noqa: E402
from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402


def raw(scores=("2-6 6-2", "6-4 6-3")) -> pd.DataFrame:
    rows = []
    for i, s in enumerate(scores):
        rows.append({"_source_file": "f.csv", "_row": i + 1, "tourney_id": "2023-1", "round": "R32",
                     "winner_name": f"Win {i}", "loser_name": f"Lose {i}", "score": s,
                     **{f"{side}_{k}": "5" for side in "wl" for k in K.COUNTS}})
    return pd.DataFrame(rows, index=[10, 11][:len(scores)])


def table(action: str, row: int = 1, **extra) -> pd.DataFrame:
    g = {"tourney_id": "2023-1", "round": "R32", "winner_name": f"Win {row - 1}", "loser_name": f"Lose {row - 1}"}
    return pd.DataFrame([{"action": action, "source_file": "f.csv", "source_row": row, **{**g, **extra}}])


def test_a_retirement_takes_its_marker_and_reads_as_retired():
    df, done = K.apply_row_corrections(raw(), table("mark_retired", value="2-6 6-2"))
    assert df.loc[10, "score"] == "2-6 6-2 RET" and df.loc[11, "score"] == "6-4 6-3"
    assert list(done["mark_retired"]) == [10]
    assert B.status_of(*B.tokens_of(df.loc[10, "score"])) == "retired"


def test_a_score_the_source_already_marked_is_left_alone():
    df, done = K.apply_row_corrections(raw(("2-6 6-2 RET",)), table("mark_retired", value="2-6 6-2"))
    assert df.loc[10, "score"] == "2-6 6-2 RET" and done["mark_retired"].empty


def test_another_score_stops_the_build():
    with pytest.raises(SystemExit, match="mark_retired expects"):
        K.apply_row_corrections(raw(("2-6 6-3",)), table("mark_retired", value="2-6 6-2"))


def test_a_score_fix_and_a_box_fix_can_share_a_row():
    t = pd.concat([table("mark_retired", value="2-6 6-2"), table("exchange_svgms")], ignore_index=True)
    df, done = K.apply_row_corrections(raw(), t)
    assert df.loc[10, "score"].endswith("RET") and list(done["exchange_svgms"]) == [10]


def frames() -> pd.DataFrame:
    return pd.DataFrame({"source": ["sackmann"] * 4, "tour": ["wta"] * 4,
                         "tid": ["2017-M020", "2017-M020", "2018-M020", "2017-1090"],
                         "tourney_name": ["Brisbane", "Brisbane", "Brisbane", "Bol"],
                         "season": pd.array([2017, 2017, 2018, 2017], dtype="Int64"),
                         "level": ["T250", "T250", "T250", "T250"], "surface": ["Hard"] * 3 + ["Clay"]})


def events(**over) -> pd.DataFrame:
    row = {"fix": "SRLVL", "action": "set_level", "source": "sackmann", "tour": "wta", "tournament_id": "2017-M020",
           "tourney_name": "Brisbane", "year": "2017", "old_value": "T250", "value": "T500"}
    return pd.DataFrame([{**row, **over}])


def test_one_edition_takes_its_level_and_no_other_edition_moves():
    df, rep = K.apply_event_corrections(frames(), events(), "set_level")
    assert list(df["level"]) == ["T500", "T500", "T250", "T250"]
    assert rep["applied"] == ["sackmann|wta|2017-M020"] and list(rep["rows"]) == [0, 1]
    same, rep2 = K.apply_event_corrections(frames(), events(), "set_surface")     # the other action: nothing
    assert same.equals(frames()) and not rep2["applied"]


def test_an_edition_already_at_the_value_is_reported_not_changed():
    f = frames()
    f.loc[[0, 1], "level"] = "T500"
    df, rep = K.apply_event_corrections(f, events(), "set_level")
    assert rep["already"] == ["sackmann|wta|2017-M020"] and not rep["applied"]


@pytest.mark.parametrize("over", [{"old_value": "T1000"}, {"tourney_name": "Sydney"}, {"year": "2016"},
                                  {"tournament_id": "2019-M020"}])
def test_an_event_that_reads_otherwise_stops_the_build(over):
    with pytest.raises(SystemExit, match="event corrections"):
        K.apply_event_corrections(frames(), events(**over), "set_level")


def test_the_history_check_accepts_every_match_of_a_corrected_event(tmp_path):
    p = tmp_path / "event_corrections.csv"
    events().to_csv(p, index=False)
    rows = pd.DataFrame({"tour": ["wta", "wta", "atp"], "tournament_id": ["2017-M020", "2018-M020", "2017-M020"]})
    assert list(H.in_decided_events(rows, H.decided_events(p))) == [True, False, False]


def alias_tables(tmp_path, ids_of_ann):
    m = pd.DataFrame({"match_id": ["a", "b"], "tour": ["wta", "wta"], "player_a_id": ["", ""], "player_b_id": ["", ""]})
    mp = pd.DataFrame({"match_id": ["a", "a", "b", "b"], "side": ["A", "B", "A", "B"],
                       "player_id": [ids_of_ann[0], "wta:5", ids_of_ann[1], "wta:6"], "opponent_id": "",
                       "player_name": ["Ann Bee", "Cy Dee", "Ann Bee", "Ed Fay"]})
    pd.DataFrame([{"tour": "wta", "from_id": "wta:9", "to_id": "wta:1", "name_key": "ann bee"}]).to_csv(
        tmp_path / "id_aliases.csv", index=False)
    return m, mp


def test_an_alias_the_source_now_writes_itself_does_not_stop_the_build(tmp_path):
    m, mp = alias_tables(tmp_path, ("wta:1", "wta:1"))
    summary: dict = {}
    m2, mp2 = B.apply_id_aliases(m, mp, tmp_path, summary)
    assert summary["id_aliases"]["fixed_by_source"] == ["wta:9"] and summary["id_aliases"]["applied"] == []


def test_an_alias_whose_player_carries_another_id_still_stops_the_build(tmp_path):
    m, mp = alias_tables(tmp_path, ("wta:1", "wta:7"))
    with pytest.raises(SystemExit, match="id aliases"):
        B.apply_id_aliases(m, mp, tmp_path, {})


def test_the_register_checks_each_pending_revision_and_marks_it_applied(tmp_path, monkeypatch):
    ok = [sys.executable, "-c", "import sys; sys.exit(0 if sys.argv[1].endswith('good') else 1)", "{stage0}"]
    reg = {"revisions": [{"id": "r1", "decision": "d", "status": "pending", "what": ["x"], "check_stage0": ok[1:],
                          "check_instance": ok[1:]},
                         {"id": "r0", "decision": "d", "status": "applied", "what": ["y"], "check_stage0": ["-c", "0"]}]}
    path = tmp_path / "pending.json"
    path.write_text(json.dumps(reg), encoding="utf-8")
    assert [r["id"] for r in PEND.pending(path)] == ["r1"]
    assert PEND.check(tmp_path / "good", path=path)["ok"]
    assert not PEND.check(tmp_path / "bad", path=path)["ok"]
    inst = tmp_path / "inst"
    inst.mkdir()
    (inst / PEND.AT_BUILD).write_text(json.dumps(PEND.check(tmp_path / "good", inst, path)), encoding="utf-8")
    monkeypatch.setattr(PEND, "INSTANCES", tmp_path)
    assert PEND.mark_applied("inst", path) == ["r1"]
    after = json.loads(path.read_text(encoding="utf-8"))["revisions"][0]
    assert after["status"] == "applied" and after["applied_in"] == "inst"


def test_the_decided_register_names_the_repairs_and_its_checks():
    r = [x for x in PEND.register()["revisions"] if x["id"] == "2026-10-22-source-reconciliation"]
    assert len(r) == 1 and (ROOT / r[0]["decision"]).exists()
    assert r[0]["check_stage0"][0] == "src/eda/source_reconciliation/verify_applied.py"


def test_the_repaired_speed_history_differs_from_the_backfilled_one_in_y_on_576_rows():
    from src.eda.serve_speed_tabpfn.live import live_panel as LP
    if not LP.REPAIRED.exists():
        pytest.skip("the repaired speed history is not built here")
    old, new = LP.frozen_panel(repaired=False), LP.frozen_panel()
    assert list(old.columns) == list(new.columns) and len(old) == len(new)
    pd.testing.assert_frame_equal(old.drop(columns="y"), new.drop(columns="y"))
    assert int((np.abs(new["y"].to_numpy() - old["y"].to_numpy()) > 1e-9).sum()) == 576
    assert LP.decided_column() == LP.COLUMN_REPAIRED
