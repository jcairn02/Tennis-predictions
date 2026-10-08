"""Offline tests: the coordinated Stage 0 rebuild's id pairing and link remap, the build's override guard, and the
scheduled downloads' alert rules."""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.data_continuity import rebuild_stage0 as R  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402
from src.ingest import scheduled as S  # noqa: E402


def stage0(folder: Path, matches: list[tuple], players: list[tuple]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(matches, columns=["match_id", "tour", "tournament_id", "round"]).to_parquet(
        folder / "stage0_matches.parquet", index=False)
    pd.DataFrame(players, columns=["match_id", "player_id", "player_name"]).to_parquet(
        folder / "stage0_match_players.parquet", index=False)


def test_id_map_pairs_by_event_round_and_names(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    stage0(old, [("wta|t1|R32|wta:1|wta:9", "wta", "t1", "R32"), ("wta|t1|R16|wta:1|wta:2", "wta", "t1", "R16"),
                 ("wta|t2|F|wta:5|wta:6", "wta", "t2", "F")],
           [("wta|t1|R32|wta:1|wta:9", "wta:1", "Emma Navarro"), ("wta|t1|R32|wta:1|wta:9", "wta:9", "Eva Lys"),
            ("wta|t1|R16|wta:1|wta:2", "wta:1", "Emma Navarro"), ("wta|t1|R16|wta:1|wta:2", "wta:2", "Ann Li"),
            ("wta|t2|F|wta:5|wta:6", "wta:5", "A B"), ("wta|t2|F|wta:5|wta:6", "wta:6", "C D")])
    # R32: Eva Lys's id changes; R16 unchanged; the t2 final disappears; a new match appears
    stage0(new, [("wta|t1|R32|wta:1|wta:name:eva lys", "wta", "t1", "R32"), ("wta|t1|R16|wta:1|wta:2", "wta", "t1", "R16"),
                 ("wta|t3|F|wta:7|wta:8", "wta", "t3", "F")],
           [("wta|t1|R32|wta:1|wta:name:eva lys", "wta:1", "Emma Navarro"),
            ("wta|t1|R32|wta:1|wta:name:eva lys", "wta:44", "Lys Eva"),
            ("wta|t1|R16|wta:1|wta:2", "wta:1", "Emma Navarro"), ("wta|t1|R16|wta:1|wta:2", "wta:2", "Ann Li"),
            ("wta|t3|F|wta:7|wta:8", "wta:7", "E F"), ("wta|t3|F|wta:7|wta:8", "wta:8", "G H")])
    pairs, unpaired = R.id_map(old, new)
    assert pairs[["old_match_id", "new_match_id"]].values.tolist() == [
        ["wta|t1|R32|wta:1|wta:9", "wta|t1|R32|wta:1|wta:name:eva lys"]]   # name keys ignore token order
    assert unpaired == ["wta|t2|F|wta:5|wta:6"]


def test_id_map_leaves_ambiguous_pairs_alone(tmp_path):
    old, new = tmp_path / "old", tmp_path / "new"
    rows = lambda mid, a, b: [(mid, a, "Same Name"), (mid, b, "Other Name")]  # noqa: E731
    stage0(old, [("m_old", "atp", "t", "R1")], rows("m_old", "atp:1", "atp:2"))
    stage0(new, [("m_new1", "atp", "t", "R1"), ("m_new2", "atp", "t", "R1")],
           rows("m_new1", "atp:3", "atp:4") + rows("m_new2", "atp:5", "atp:6"))
    pairs, unpaired = R.id_map(old, new)
    assert pairs.empty and unpaired == ["m_old"]


def test_remap_rewrites_frozen_links_only(tmp_path, monkeypatch):
    links = tmp_path / "links"
    links.mkdir()
    pd.DataFrame({"match_id": ["a", "b"], "source_key": ["1", "2"]}).to_parquet(links / "live_tennis_api.parquet")
    pd.DataFrame({"match_id": ["a"], "source_key": ["9"]}).to_parquet(links / "wta_api.parquet")   # rebuilt by refresh
    pd.DataFrame({"other": [1]}).to_parquet(links / "flashscore_records.parquet")                  # no match_id
    monkeypatch.setattr(R, "LINKS", links)
    counts = R.remap_frozen(pd.DataFrame({"old_match_id": ["a"], "new_match_id": ["A"]}))
    assert counts == {"live_tennis_api.parquet": 1}
    assert pd.read_parquet(links / "live_tennis_api.parquet")["match_id"].tolist() == ["A", "b"]
    assert pd.read_parquet(links / "wta_api.parquet")["match_id"].tolist() == ["a"]
    assert not list(links.glob("*.part"))


def test_restore_puts_back_only_verified_copies(tmp_path, monkeypatch):
    monkeypatch.setattr(R, "ROOT", tmp_path)
    live = tmp_path / "data" / "t.parquet"
    live.parent.mkdir(parents=True)
    live.write_bytes(b"new")
    kept = tmp_path / "run" / "replaced" / "data" / "t.parquet"
    kept.parent.mkdir(parents=True)
    kept.write_bytes(b"old")
    manifest = [{"path": "data/t.parquet", "bytes": 3, "sha256": R.sha(kept)}]
    (tmp_path / "run" / "replaced" / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    assert R.restore(tmp_path / "run") == 1 and live.read_bytes() == b"old"
    kept.write_bytes(b"tampered")
    live.write_bytes(b"new")
    with pytest.raises(SystemExit, match="does not match"):
        R.restore(tmp_path / "run")
    assert live.read_bytes() == b"new"


def test_build_guards_other_override_tables(tmp_path, monkeypatch):
    def no_build():
        raise AssertionError("the guard did not stop the build")
    monkeypatch.setattr(B, "load_raw", no_build)    # never reach the live tables, whatever happens
    other = tmp_path / "other.csv"
    other.write_text("tour\n", encoding="utf-8")
    with pytest.raises(SystemExit, match="confirm-live-overrides"):
        B.build(None, other)                        # another table into the live folder, unconfirmed
    with pytest.raises(SystemExit, match="missing"):
        B.build(tmp_path / "out", tmp_path / "nope.csv")


def test_decided_override_table_is_the_default():
    assert B.build.__defaults__[1] == B.DECIDED_OVERRIDES
    assert B.DECIDED_OVERRIDES.name == "slam_box_overrides.csv"


def test_canary_flags_compare_first_word(tmp_path, monkeypatch):
    latest = tmp_path / "canary_latest.json"
    latest.write_text(json.dumps({"flags": {"tml": ["STALE (12 days)"], "repo": ["GONE"]}}), encoding="utf-8")
    monkeypatch.setattr(S, "CANARY_LATEST", latest)
    assert S.canary_flags() == {"tml:STALE", "repo:GONE"}


def test_slam_reminder_once_a_week(monkeypatch):
    monkeypatch.setattr(S, "slam_held", lambda folder, year: folder != "wimbledon")
    state: dict = {}
    _, alerts = S.job_slams(state, dt.date(2027, 7, 20))
    assert len(alerts) == 1 and "Wimbledon 2027" in alerts[0]
    assert S.job_slams(state, dt.date(2027, 7, 23))[1] == []          # reminded three days ago
    assert len(S.job_slams(state, dt.date(2027, 7, 27))[1]) == 1      # a week later, again
    assert S.job_slams({}, dt.date(2027, 7, 1))[1] == []              # not finished yet


def test_tml_alerts_on_repeat_hold_and_errors(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "ROOT", tmp_path)
    def fake(text):
        def child(name, args, timeout):
            (tmp_path / "t.log").write_text("=== x\n" + text, encoding="utf-8")
            return {"exit": 1, "seconds": 0.1, "log": "t.log"}
        return child
    held = "[tennis_my_life] held 2026.csv: ragged\n[tennis_my_life] done: 9 staged files, 1 rows, 0 download errors, 1 held\n"
    monkeypatch.setattr(S, "child", fake(held))
    state: dict = {}
    assert S.job_tml(state)[1] == [] and state["tml_held"] == ["2026.csv"]       # first hold: no alert
    assert "held two runs in a row" in S.job_tml(state)[1][0]
    monkeypatch.setattr(S, "child", fake("[tennis_my_life] done: 3 staged files, 1 rows, 2 download errors, 0 held\n"))
    out, alerts = S.job_tml(state)
    assert out["errors"] == 2 and alerts == [] and state["tml_held"] == []      # one failure: the PC may be offline
    monkeypatch.setattr(S, "child", fake("Traceback: manifest unavailable\n"))     # no summary line at all
    assert "two runs in a row" in S.job_tml(state)[1][0]
    monkeypatch.setattr(S, "child", fake("[tennis_my_life] done: 9 staged files, 1 rows, 0 download errors, 0 held\n"))
    assert S.job_tml(state)[1] == [] and state["tml_failed"] is False


def test_offline_canary_raises_nothing(tmp_path, monkeypatch):
    latest = tmp_path / "canary_latest.json"
    monkeypatch.setattr(S, "CANARY_LATEST", latest)
    monkeypatch.setattr(S, "child", lambda name, args, timeout: {"exit": 0, "seconds": 0.1, "log": "c.log"})
    latest.write_text(json.dumps({"flags": {"a": ["GONE"], "b": ["GONE"], "c": ["GONE"]},
                                  "items": [{"item": x, "status": None} for x in "abc"]}), encoding="utf-8")
    state = {"canary_flags": ["x:GONE"]}
    out, alerts = S.job_canary(state)
    assert out["offline"] and alerts == [] and state["canary_flags"] == ["x:GONE"]
    latest.write_text(json.dumps({"flags": {"a": ["GONE"]}, "items": [{"item": "a", "status": 404},
                                                                     {"item": "b", "status": 200}]}), encoding="utf-8")
    out, alerts = S.job_canary(state)
    assert out["new_flags"] == ["a:GONE"] and "new flag" in alerts[0]
