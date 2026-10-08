"""Offline tests of the live pipeline's staging format (src/eda/serve_speed_tabpfn/live/staging.py). The parser is
tested only on the held, already-decrypted handoff copies (not our decryption). No match result is read."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.live import staging as ST  # noqa: E402

HANDOFF_FILE = ROOT / "data" / "raw" / "public_dump" / "atp_pipeline_handoff" / "infosys_deep" / "2023_data.jsonl.gz"
PANEL_HANDOFF_CACHE = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "handoff_keystats.parquet"


def _same(a, b) -> bool:
    return (np.isnan(a) and np.isnan(b)) or a == b


@pytest.mark.skipif(not HANDOFF_FILE.exists(), reason="the handoff copy is not on this machine")
def test_parser_equals_the_panel_build_on_held_decrypted_records():
    """Staged values of 40 held handoff records equal what panel.py's own parser cached for the same records."""
    rows = ST.handoff_rows(HANDOFF_FILE, limit=40)
    assert len(rows) == 40
    df = ST.to_frame(rows)
    assert list(df.columns[:len(ST.STAGING_COLS)]) == ST.STAGING_COLS
    cache = pd.read_parquet(PANEL_HANDOFF_CACHE).set_index(["k_year", "k_tid", "k_code", "player_no"])
    checked = 0
    for r in df.itertuples(index=False):
        for no, pre in ((1, "p1"), (2, "p2")):
            key = (str(r.year), str(r.event_id), str(r.match_code), no)
            if key not in cache.index:
                continue
            c = cache.loc[key]
            c = c.iloc[0] if isinstance(c, pd.DataFrame) else c
            assert _same(getattr(r, f"{pre}_spd1"), c["v1"])
            assert _same(getattr(r, f"{pre}_spd2"), c["v2"])
            assert _same(getattr(r, f"{pre}_max"), c["vmax"])
            assert _same(getattr(r, f"{pre}_first_in"), c["first_in"])
            assert _same(getattr(r, f"{pre}_first_total"), c["first_total"])
            checked += 1
    assert checked >= 60
    assert (df["source"] == "handoff_keystats").all()
    assert df["p1_atp_id"].str.fullmatch(r"[A-Z0-9]{4}").all()


def test_path_b_hook_gives_the_same_row_as_the_decrypted_file():
    ks = {"matchCompleted": True,
          "players": [{"player1Id": "b0cd", "player1Name": "J. BROOKSBY"}, {"player1Id": "N771", "player1Name": "C. NORRIE"}],
          "setStats": {"set0": [{"name": "1st Serve Average Speed", "player1": "180", "player2": "184"},
                                {"name": "2nd Serve Average Speed", "player1": "142", "player2": "147"},
                                {"name": "Max Speed", "player1": "191", "player2": "202"},
                                {"name": "1st Serve", "player1": "51/78 (65%)", "player2": "35/63 (56%)"}]}}
    a = ST.parse_keystats(ks, year=2026, event_id=747, match_code="MS003")
    b = ST.from_rendered({"1st Serve Average Speed": ("180 km/h", "184 km/h"), "2nd Serve Average Speed": ("142 km/h", "147 km/h"),
                          "Max Speed": ("191 km/h", "202 km/h"), "1st Serve": ("51/78 (65%)", "35/63 (56%)")},
                         year=2026, event_id=747, match_code="MS003", p1=("B0CD", "J. BROOKSBY"), p2=("N771", "C. NORRIE"))
    for k in ("p1_spd1", "p2_spd1", "p1_spd2", "p2_spd2", "p1_max", "p2_max", "p1_first_in", "p1_first_total",
              "p2_first_in", "p2_first_total", "p1_atp_id", "p2_atp_id", "round"):
        assert a[k] == b[k], k
    assert a["p1_spd1"] == 180.0 and a["p1_first_in"] == 51 and a["p2_first_total"] == 63 and a["round"] == "SF"
    assert a["source"] == "infosys_atp_daily" and b["source"] == "atp_page"


def test_round_from_code_and_plausibility():
    cases = {"MS001": "F", "MS002": "SF", "MS003": "SF", "MS004": "QF", "MS007": "QF", "MS008": "R16", "MS015": "R16",
             "MS016": "R32", "MS031": "R32", "MS032": "R64", "MS063": "R64", "MS064": "R128", "MS127": "R128"}
    for code, rnd in cases.items():
        assert ST.round_from_code(code) == rnd, code
    assert ST.round_from_code("QS010") is None and ST.round_from_code("XX") is None
    ks = {"setStats": {"set0": [{"name": "1st Serve Average Speed", "player1": "0", "player2": "271"}]}}
    r = ST.parse_keystats(ks, year=2026, event_id=1, match_code="MS001")
    assert np.isnan(r["p1_spd1"]) and np.isnan(r["p2_spd1"])
    assert ST.parse_keystats({"setStats": {"set0": []}}, year=2026, event_id=1, match_code="MS001") is None


def test_mantd_rows_drop_the_winner_order():
    """ManTennisData's rows are winner / loser; staging puts the pair in ATP-code order, so p1 says nothing of a result."""
    base = {"id": "2026-747-zz99-aa11-R32", "tournament_id": "2026-747", "stadie_id": "R32",
            "stats_url": "https://www.atptour.com/en/scores/match-stats/archive/2026/747/ms020",
            "winner_code": "zz99", "winner_name": "Zed Zed", "loser_code": "aa11", "loser_name": "Al Al"}
    for pre, (spd, fin, tot) in (("win", ("201", "40", "60")), ("los", ("185", "30", "50"))):
        base.update({f"{pre}_average_first_serves_kmh": spd, f"{pre}_average_second_serve_kmh": "150",
                     f"{pre}_fastest_first_serves_kmh": "215", f"{pre}_first_serves_in": fin,
                     f"{pre}_first_serves_total": tot})
    r = ST.mantd_rows(pd.DataFrame([base]), collected_on="2026-10-08")[0]
    assert r["p1_atp_id"] == "AA11" and r["p1_spd1"] == 185.0 and r["p2_atp_id"] == "ZZ99" and r["p2_spd1"] == 201.0
    assert r["round"] == "R32" and r["match_code"] == "MS020" and r["event_id"] == "747" and r["year"] == 2026
