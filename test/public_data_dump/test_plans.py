"""Offline tests for each adapter's file planning and route logic (no network)."""
import datetime as dt
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.ingest.public_dump import common as C  # noqa: E402
from src.ingest.public_dump import match_charting, open_tennis_data, sackmann_archive, tennis_data_couk, tennis_my_life  # noqa: E402


def test_sackmann_plan_filters_years_decades_docs_and_skips():
    tree = ["README.md", "atp/atp_matches_1999.csv", "atp/atp_matches_2000.csv", "atp/atp_matches_2026.csv",
            "atp/atp_matches_qual_chall_2025.csv", "atp/atp_matches_futures_2025.csv", "atp/atp_matches_doubles_2020.csv",
            "atp/atp_matches_amateur.csv", "atp/atp_players.csv", "atp/atp_rankings_90s.csv", "atp/atp_rankings_00s.csv",
            "atp/atp_rankings_current.csv", "atp/matches_data_dictionary.txt", "wta/wta_matches_qual_itf_2026.csv",
            "slam_pointbypoint/2024-usopen-points.csv", "slam_pointbypoint/2019-wimbledon-matches-doubles.csv",
            "slam_pointbypoint/data_dictionary.txt", "weird/file.csv"]
    selected, skipped = sackmann_archive.plan(tree, 2000, 2026)
    paths = {p for _, _, p, _ in selected}
    assert "atp/atp_matches_2000.csv" in paths and "atp/atp_matches_1999.csv" not in paths
    assert "atp/atp_rankings_00s.csv" in paths and "atp/atp_rankings_90s.csv" not in paths
    assert "atp/atp_rankings_current.csv" in paths and "README.md" in paths
    assert "slam_pointbypoint/2024-usopen-points.csv" in paths and "slam_pointbypoint/2019-wimbledon-matches-doubles.csv" in paths
    reasons = {s["path"]: s["reason"] for s in skipped}
    assert "amateur" in reasons["atp/atp_matches_amateur.csv"]
    assert "no rule" in reasons["weird/file.csv"]
    branches = {p: b for b, _, p, _ in selected}
    assert branches["atp/atp_players.csv"] == "players" and branches["wta/wta_matches_qual_itf_2026.csv"] == "matches"
    selected_no, skipped_no = sackmann_archive.plan(tree, 2000, 2026, include_slam=False, include_doubles=False)
    assert not any("slam_pointbypoint" in p for _, _, p, _ in selected_no if p.endswith(".csv"))
    assert any("doubles excluded" in s["reason"] for s in skipped_no)


def test_tml_plan_skips_backups_and_amateur_and_filters_years():
    catalog = [{"name": "1999.csv", "url": "u"}, {"name": "2026.csv", "url": "u"}, {"name": "2026_wta.csv", "url": "u"},
               {"name": "2026_challenger.csv", "url": "u"}, {"name": "atp_quali/2026_atp_quali.csv", "url": "u"},
               {"name": "ongoing_tourneys.csv", "url": "u"}, {"name": "ATP_Database.csv", "url": "u"},
               {"name": "atp_rankings_2026-08-31.csv", "url": "u"}, {"name": "backup_ll_audit_20260906_044746/2026.csv", "url": "u"},
               {"name": "atp_matches_amateur.csv", "url": "u"}, {"name": "mystery.txt", "url": "u"}]
    selected, skipped = tennis_my_life.plan(catalog, 2000, 2026)
    names = {item["name"]: (branch, subdir, always) for branch, subdir, item, _, always in selected}
    assert names["2026.csv"] == ("matches", "atp_main", False)
    assert names["ongoing_tourneys.csv"] == ("matches", "ongoing", True)
    assert names["ATP_Database.csv"][0] == "players" and names["atp_rankings_2026-08-31.csv"][0] == "rankings"
    assert "1999.csv" not in names
    reasons = {s["path"]: s["reason"] for s in skipped}
    assert "duplicate" in reasons["backup_ll_audit_20260906_044746/2026.csv"]
    assert "amateur" in reasons["atp_matches_amateur.csv"] and "no rule" in reasons["mystery.txt"]


def test_mcp_plan_respects_era_flag():
    tree = ["README.md", "data_dictionary.txt", "MatchChart 0.3.2.xlsm", "charting-m-matches.csv",
            "charting-m-points-2020s.csv", "charting-w-points-to-2009.csv", "charting-w-stats-Overview.csv"]
    selected, skipped = match_charting.plan(tree, all_eras=False)
    assert ("points", "charting-w-points-to-2009.csv") not in selected
    assert ("stats", "charting-w-stats-Overview.csv") in selected and ("docs", "README.md") in selected
    assert any("xlsm" in s["path"] for s in skipped)
    selected_all, _ = match_charting.plan(tree, all_eras=True)
    assert ("points", "charting-w-points-to-2009.csv") in selected_all


def test_open_tennis_data_helpers():
    releases = [{"tag_name": "b", "draft": False}, {"tag_name": "a", "draft": False}, {"tag_name": "d", "draft": True}]
    assert open_tennis_data.pick_release(releases, None)["tag_name"] == "b"
    assert open_tennis_data.pick_release(releases, "a")["tag_name"] == "a"
    assert open_tennis_data.parse_sha256sums("abc  x.parquet\ndef *y.parquet\n") == {"x.parquet": "abc", "y.parquet": "def"}


def test_tennis_data_urls():
    assert tennis_data_couk.live_url("atp", 2012) == "https://www.tennis-data.co.uk/2012/2012.xls"
    assert tennis_data_couk.live_url("wta", 2026) == "https://www.tennis-data.co.uk/2026w/2026.xlsx"
    assert tennis_data_couk.wayback_url("20260803192930", "https://x/y.xlsx") == "https://web.archive.org/web/20260803192930id_/https://x/y.xlsx"


class CdxSession:
    def get(self, url, params=None, timeout=None):
        class R:
            status_code = 200
            text = json.dumps([["timestamp", "statuscode", "length", "digest"], ["20230509143122", "200", "1", "A"],
                               ["20260402190834", "200", "2", "B"]])

            def raise_for_status(self):
                pass

            def json(self):
                return json.loads(self.text)
        return R()


def test_wayback_captures_are_newest_first():
    captures = tennis_data_couk.wayback_captures("https://x", sess=CdxSession())
    assert [c["timestamp"] for c in captures] == ["20260402190834", "20230509143122"]


def test_acquire_local_route_and_partitioned_staging(tmp_path, monkeypatch):
    import openpyxl

    monkeypatch.setattr(C, "RAW_ROOT", tmp_path / "raw")
    monkeypatch.setattr(C, "DUMP_ROOT", tmp_path / "dump")
    monkeypatch.setattr(C, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(tennis_data_couk, "LEGACY_ROOT", tmp_path / "legacy")
    book = openpyxl.Workbook()
    sheet = book.active
    sheet.append(["ATP", "Location", "Date", "Series", "Winner", "B365W"])
    sheet.append([1, "Brisbane", dt.datetime(2026, 1, 5), "ATP250", "A", 1.5])
    sheet.append([2, "Melbourne", dt.datetime(2026, 1, 18), "Grand Slam", "B", 2.0])
    sheet.append([3, "Melbourne", dt.datetime(2026, 1, 19), "Grand Slam", "C", None])
    for _ in range(400):  # keep the workbook above the plausibility size floor
        sheet.append([9, "Pad", dt.datetime(2026, 2, 1), "ATP250", "Z", 1.0])
    legacy = tmp_path / "legacy" / "atp"
    legacy.mkdir(parents=True)
    book.save(legacy / "2026.xlsx")
    receipts = C.Receipts("tennis_data_couk")
    receipt = tennis_data_couk.acquire("atp", 2026, receipts, refresh=False, routes=("local",))
    assert receipt["route"] == "local_snapshot" and receipt.get("error") is None
    metas = tennis_data_couk.stage_workbook("atp", 2026, receipt)
    partitions = {m["partition_value"]: m["rows"] for m in metas}
    assert partitions == {"ATP250": 401, "Grand Slam": 2}
    table = pq.read_table(tmp_path / "dump" / "odds" / "tennis_data_couk" / "atp" / "grand_slam" / "2026.parquet")
    assert table.column("Date").to_pylist() == ["2026-01-18", "2026-01-19"]
    assert table.column("_partition_column").to_pylist() == ["Series", "Series"]
    assert table.column("_route").to_pylist() == ["local_snapshot"] * 2
    assert table.column("B365W").to_pylist() == ["2", None]
    again = tennis_data_couk.acquire("atp", 2026, receipts, refresh=False, routes=("local",))
    assert again.get("skipped") is True
    missing = tennis_data_couk.acquire("wta", 2026, receipts, refresh=False, routes=("local",))
    assert missing.get("error")
