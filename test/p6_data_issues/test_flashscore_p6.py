"""The Flashscore fetch for P6's targets: one collector per host, the seeded trial, the copy's record of each feed for
staging, and the links the link check refused (offline)."""
import os
import sys
import time
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import flashscore_p6 as FP  # noqa: E402


def test_it_waits_while_another_collector_writes_flashscores_receipts(tmp_path, monkeypatch):
    monkeypatch.setattr(P, "RAW_ROOT", tmp_path)
    assert FP.host_busy() is None                                   # no receipts at all
    receipts = tmp_path / "flashscore_points" / "_receipts.jsonl"
    receipts.parent.mkdir(parents=True)
    receipts.write_text("{}\n")
    assert "in use" in FP.host_busy()                               # written just now
    old = time.time() - 20 * 60
    os.utime(receipts, (old, old))
    assert FP.host_busy() is None                                   # idle for 20 minutes


def test_the_trial_spreads_over_gaps_and_years_and_skips_records_without_the_point_tab(tmp_path, monkeypatch):
    rows = [{"gap": g, "year": y, "fs_id": f"{g[:3]}{y}{i}", "fs_mh": i < 3, "fs_date": f"{y}-05-0{i + 1}",
             "fs_score": "6-4 6-4"} for g in ("atp_points_2018_2020", "challenger_points_2018_2021")
            for y in (2019, 2020) for i in range(5)]
    path = tmp_path / "targets.csv.gz"
    pd.DataFrame(rows).to_csv(path, index=False, compression="gzip")
    monkeypatch.setattr(FP, "TARGETS", path)
    assert len(FP.load_targets()) == 12                             # 3 with the tab in each of 4 cells
    trial = FP.load_targets(trial=4)
    assert len(trial) == 4 and trial.groupby(["gap", "year"]).size().eq(1).all()


def test_the_copys_record_of_each_feed_is_staged_in_flashscore_points_columns():
    from src.ingest.point_sources import flashscore_points as F
    base = {"tour": "M", "fs_category": "atp-singles", "fs_tournament": "Sydney", "fs_home": "De Minaur A.",
            "fs_away": "Opelka R."}
    t = pd.DataFrame([{**base, "uid": 1, "fs_id": "AAA", "fs_date": "2019-01-09", "fs_score": "6-4 7-6",
                       "fs_duration": "1:31"},
                      {**base, "uid": 2, "fs_id": "AAA", "fs_date": "2019-01-09", "fs_score": "6-4 7-6",
                       "fs_duration": "1:31"},                      # the same match twice on the map: one record
                      {**base, "uid": 3, "fs_id": "BBB", "fs_date": "2023-05-01", "fs_score": float("nan"),
                       "fs_duration": float("nan"), "fs_category": "challenger-men-singles"}])
    rows = [dict(zip(F.HANDOFF_COLUMNS, r)) for r in FP.info_rows(t)]
    assert [r["fs_id"] for r in rows] == ["AAA", "BBB"]
    assert (rows[0]["fs_date"], rows[0]["grade"], rows[0]["fs_duration"]) == ("20190109", "atp-singles", "1:31")
    assert rows[1]["fs_score"] is None and rows[1]["fs_status"] is None and rows[1]["grade"] == "challenger-men-singles"


def test_the_links_the_link_check_refused_are_marked(tmp_path, monkeypatch):
    monkeypatch.setattr(FP, "VETOES", tmp_path / "link_vetoes.csv")
    t = pd.DataFrame({"uid": [1, 2], "fs_id": ["AAA", "AAA"]})       # one feed, two targets
    assert FP.load_vetoes() == set() and not FP.refused(t, FP.load_vetoes()).any()   # before the check has run
    pd.DataFrame({"uid": ["2"], "fs_id": ["AAA"], "verdict": ["winner differs"]}).to_csv(FP.VETOES, index=False)
    assert FP.refused(t, FP.load_vetoes()).tolist() == [False, True]
