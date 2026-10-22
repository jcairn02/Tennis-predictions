"""The ATP Stats Centre backfill (offline, on small synthetic inputs): the staging of decrypted files, the double-fault
codes in the speed tables, the panel's new sources and subset build, the live feed's backfilled history and its guards,
and the study's parsers and season statistics. Nothing here reads the real staged tables or writes the live folder."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.infosys_atp_backfill import checks as CK  # noqa: E402
from src.eda.infosys_atp_backfill import compare as CMP  # noqa: E402
from src.eda.serve_speed_acquisition import speeds as SP  # noqa: E402
from src.eda.serve_speed_tabpfn import panel as PN  # noqa: E402
from src.eda.serve_speed_tabpfn.live import live_panel as LP  # noqa: E402
from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import infosys_atp_stage as ST  # noqa: E402


# ----------------------------------------------------------------------------------- staging
@pytest.mark.parametrize("event, mid, rnd", [
    ("418", "MS001", "F"), ("418", "MS003", "SF"), ("418", "MS007", "QF"), ("418", "MS008", "R16"),
    ("404", "MS064", "R128"), ("404", "MS127", "R128"), ("418", "QS012", None),
    ("605", "MS001", None), ("7696", "MS004", None), ("9210", "MS012", None),       # round robins: not a bracket
])
def test_round_from_code(event, mid, rnd):
    assert ST.round_from_code(event, mid) == rnd


@pytest.mark.parametrize("value, speed", [("194.38 KPH", 194.38), ("201", 201.0), ("NA", None), ("0 KPH", None),
                                          (None, None), ("", None)])
def test_court_vision_speed(value, speed):
    assert ST.cv_speed(value) == speed


def point(pid, server, serve, speed, result, scorer):
    return {"pointId": pid, "point": 1, "server": server, "serve": serve, "serveSpeed": speed, "faultSrvSpd": 0.0,
            "scorer": scorer, "result": result}


def matchbeats(points):
    return {"eventId": 418, "matchId": "MS001", "matchWinner": 2, "matchStatus": "C", "isMatchComplete": True,
            "setsComplete": 1, "playerData": {"tm1Ply1Id": "MK66", "tm1Ply1Name": "M. MCDONALD",
                                              "tm1Ply1FirstName": "Mackenzie", "tm1Ply1LastName": "MCDONALD",
                                              "tm2Ply1Id": "S0AG", "tm2Ply1Name": "J. SINNER",
                                              "tm2Ply1FirstName": "Jannik", "tm2Ply1LastName": "SINNER"},
            "setData": [{"set": 1, "gameData": [{"game": 1, "pointData": points}]}]}


def test_stage_writes_the_five_tables_from_decrypted_files(tmp_path, monkeypatch):
    dec = tmp_path / "decrypted" / "2021" / "418"
    (dec / "match-beats").mkdir(parents=True)
    (dec / "keystats").mkdir(parents=True)
    pts = [point("1_1_1_1", "1", 1, 200.0, "A", "1"), point("1_1_2_2", "1", 2, 160.0, "P", "2"),
           point("1_1_3_1", "1", 1, 0.0, "N", "1")]
    (dec / "match-beats" / "MS001.json").write_text(json.dumps(matchbeats(pts)), encoding="utf-8")
    ks = {"players": [{"player1Id": "MK66"}, {"player1Id": "S0AG"}], "setStats": {"set0": [
        {"order": 1, "name": "1st Serve Average Speed", "player1": "200", "player2": "0"}]}}
    (dec / "keystats" / "MS001.json").write_text(json.dumps(ks), encoding="utf-8")
    written = {}

    def fake_stage_table(source, dest, header, rows, **kw):
        written[Path(dest).name] = pd.DataFrame(rows, columns=header)
        return {"rows": len(rows), "bytes": 0}

    monkeypatch.setattr(ST, "DECRYPTED", tmp_path / "decrypted")
    monkeypatch.setattr(ST, "INVENTORY", tmp_path / "none.csv")
    monkeypatch.setattr(ST, "DECRYPTION", tmp_path / "none.csv")
    monkeypatch.setattr(ST.P, "stage_table", fake_stage_table)
    out = ST.stage()
    assert set(written) == {"matches.parquet", "points.parquet", "keystats.parquet", "rally.parquet",
                            "court_vision.parquet"}
    m = written["matches.parquet"].iloc[0]
    assert (m["year"], m["event_id"], m["match_id"], m["round_from_code"]) == ("2021", "418", "MS001", "F")
    assert (m["p1_id"], m["p2_id"], m["match_winner"]) == ("MK66", "S0AG", "2")
    assert (m["points"], m["points_timed"], m["first_serve_points_timed"], m["points_classified"]) == ("3", "2", "1", "2")
    assert m["keystats_speed"] == "TRUE"
    assert len(written["points.parquet"]) == 3 and out["by_year"]["2021"]["with_timed_points"] == 1


# ----------------------------------------------------------------------------------- speeds: double faults
def test_atp_point_speeds_leave_both_double_fault_codes_out_of_the_second_serve(tmp_path, monkeypatch):
    rows = [("2021", "418", "MS001", "1", "1", "200", "0", "A"), ("2021", "418", "MS001", "1", "2", "150", "0", "W"),
            ("2021", "418", "MS001", "1", "2", "170", "0", "P"), ("2021", "418", "MS001", "1", "2", "171", "0", "DF"),
            ("2021", "418", "MS001", "2", "1", "0", "0", "N")]
    cols = ["year", "event_id", "match_id", "server", "serve", "serveSpeed", "faultSrvSpd", "result"]
    (tmp_path / "pts").mkdir()
    pd.DataFrame(rows, columns=cols).to_parquet(tmp_path / "pts" / "points.parquet")
    monkeypatch.setattr(SP, "ATP", tmp_path / "pts")
    out = SP.atp_point_speeds().set_index("player_no")
    assert out.loc["1", "spd1_mean"] == 200.0 and out.loc["1", "spd1_n"] == 1
    assert out.loc["1", "spd2_mean"] == 150.0 and out.loc["1", "spd2_n"] == 1      # "P" and "DF" are faults
    assert out.loc["1", "service_points"] == 4
    assert np.isnan(out.loc["2", "spd1_mean"])                                      # 0 is "not timed"


def test_panel_atp_records_leave_both_double_fault_codes_out(tmp_path, monkeypatch):
    rows = [("2021", "418", "MS001", "1", "1", "200", "0", "A"), ("2021", "418", "MS001", "1", "1", "190", "0", "W"),
            ("2021", "418", "MS001", "1", "2", "150", "0", "W"), ("2021", "418", "MS001", "1", "2", "170", "0", "P"),
            ("2021", "418", "MS001", "1", "2", "171", "0", "DF")]
    pd.DataFrame(rows, columns=PN.INFO_ATP_COLS).to_parquet(tmp_path / "points.parquet")
    monkeypatch.setattr(PN, "INFO_ATP_POINTS", tmp_path / "points.parquet")
    sp = pd.DataFrame({"source": ["infosys_atp"], "source_key": ["2021_418_MS001"], "player_no": [1],
                       "match_id": ["atp|2021-418|F|a|b"], "side": ["B"], "round": ["F"]})
    r = PN._infosys_atp_records(sp).iloc[0]
    assert (r["f1"], r["n1"], r["s1"]) == (2, 2, 390.0)
    assert (r["f2"], r["n2"], r["s2"]) == (1, 1, 150.0)
    assert (r["match_id"], r["side"], r["round_src"], r["source"]) == ("atp|2021-418|F|a|b", "B", "F", "infosys_atp")


def test_panel_ks_ranks_and_source_names():
    assert PN.KS_RANK == {"mantennisdata": 0, "handoff_ks": 1, "infosys_atp_ks": 2}
    order = PN.PTS_PRIORITY
    assert order.index("infosys_slams") < order.index("sirgenkii") < order.index("infosys") < order.index("slam_pbp")
    assert {"infosys_atp", "infosys_atp_ks"} <= PN.TOUR_ONLY
    with pytest.raises(ValueError):
        PN.build_records({"no_such_source"})


# ----------------------------------------------------------------------------------- the live history
def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def live_files(tmp_path, monkeypatch):
    frozen = tmp_path / "speed_panel.parquet"
    pd.DataFrame({"match_id": ["m1"], "side": ["A"], "y": [200.0]}).to_parquet(frozen)
    corrected = tmp_path / "corrected.parquet"
    pd.DataFrame({"match_id": ["m1"], "side": ["A"], "y": [201.0]}).to_parquet(corrected)
    meta = tmp_path / "corrected.json"
    meta.write_text(json.dumps({"frozen_panel_sha256": sha(frozen), "corrected_sha256": sha(corrected)}))
    backfilled = tmp_path / "backfilled.parquet"
    pd.DataFrame({"match_id": ["m1", "m2"], "side": ["A", "B"], "y": [201.0, 210.0]}).to_parquet(backfilled)
    bmeta = tmp_path / "backfilled.json"
    bmeta.write_text(json.dumps({"corrected_sha256": sha(corrected), "backfilled_sha256": sha(backfilled)}))
    monkeypatch.setattr(PN, "PANEL", frozen)
    monkeypatch.setattr(LP, "CORRECTED", corrected)
    monkeypatch.setattr(LP, "CORRECTED_META", meta)
    monkeypatch.setattr(LP, "BACKFILLED", backfilled)
    monkeypatch.setattr(LP, "BACKFILLED_META", bmeta)
    # the repaired layer above the backfill (since 22 Oct 2026, source_reconciliation/apply_speed.py): absent here, so
    # the backfill is the top layer these tests read
    monkeypatch.setattr(LP, "REPAIRED", tmp_path / "repaired.parquet")
    monkeypatch.setattr(LP, "REPAIRED_META", tmp_path / "repaired.json")
    return {"corrected": corrected, "backfilled": backfilled, "bmeta": bmeta}


def test_live_history_reads_the_backfill_when_its_record_holds(live_files):
    assert LP.frozen_panel()["match_id"].tolist() == ["m1", "m2"]


def test_live_history_falls_back_to_the_corrected_copy_without_the_backfill(live_files):
    live_files["backfilled"].unlink()
    assert LP.frozen_panel()["match_id"].tolist() == ["m1"]


def test_live_history_stops_when_the_corrected_copy_moved(live_files):
    rec = json.loads(live_files["bmeta"].read_text())
    rec["corrected_sha256"] = "0" * 64
    live_files["bmeta"].write_text(json.dumps(rec))
    with pytest.raises(SystemExit):
        LP.frozen_panel()


def test_live_history_stops_when_the_backfill_was_altered(live_files):
    pd.DataFrame({"match_id": ["m9"], "side": ["A"], "y": [1.0]}).to_parquet(live_files["backfilled"])
    with pytest.raises(SystemExit):
        LP.frozen_panel()


# ----------------------------------------------------------------------------------- the study's helpers
@pytest.mark.parametrize("text, value", [("34/57 (60%)", (34.0, 57.0)), ("5", 5.0), ("", None), (None, None),
                                         (float("nan"), None), ("NA", None)])
def test_key_statistic_values(text, value):
    assert CK.ks_value(text) == value


@pytest.mark.parametrize("score, sets", [("64 76(5)", [(6, 4), (7, 6)]), ("60 63", [(6, 0), (6, 3)]),
                                         ("64 RET", None), ("", None)])
def test_score_sets(score, sets):
    assert CK.score_sets(score) == sets


def test_season_heterogeneity_on_equal_and_on_scattered_seasons():
    same = [{"seasons": str(y), "estimate": 0.05, "se": 0.04} for y in range(2019, 2025)]
    h = CMP.heterogeneity(same)
    assert h["Q"] == pytest.approx(0.0) and h["tau_between_seasons"] == 0.0
    assert h["random_effects_mean"] == pytest.approx(0.05)
    spread = [{"seasons": str(y), "estimate": b, "se": 0.02} for y, b in zip(range(2019, 2025),
                                                                         (0.2, -0.1, 0.15, -0.05, 0.1, 0.0))]
    h = CMP.heterogeneity(spread)
    assert h["p_heterogeneity"] < 0.001 and h["tau_between_seasons"] > 0.05
    lo, hi = h["prediction_interval_next_season"]
    assert lo < h["random_effects_mean"] < hi
