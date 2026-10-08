"""Offline tests of the live linker (live/link.py) on held 2026 rows. No match result is read."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.live import link as LK  # noqa: E402
from src.eda.serve_speed_tabpfn.live import staging as ST  # noqa: E402

MANTD_2026 = ROOT / "data" / "raw" / "public_dump" / "mantennisdata" / "atp" / "matches_2026.csv"
HIDDEN = {"2026-329", "2026-747", "2026-7581", "2026-4713"}        # Tokyo, Beijing, Chengdu, Hangzhou


@pytest.fixture(scope="module")
def staged() -> pd.DataFrame:
    m = pd.read_csv(MANTD_2026, dtype=str, keep_default_na=False)
    v1 = pd.to_numeric(m["win_average_first_serves_kmh"], errors="coerce")
    v2 = pd.to_numeric(m["los_average_first_serves_kmh"], errors="coerce")
    return ST.to_frame(ST.mantd_rows(m[(v1 > 40) & (v2 > 40)], collected_on="2026-10-07"))


@pytest.fixture(scope="module")
def xw() -> pd.Series:
    return LK.crosswalk()


def test_links_agree_with_the_acquisition(staged, xw):
    lk = LK.link(staged, xw=xw)
    sp = pd.read_parquet(LK.SPEEDS, columns=["source", "source_key", "player_source_id", "match_id", "side"])
    sp = sp[sp["source"].eq("mantennisdata")]
    a = lk[["mantd_id", "p1_atp_id", "match_id", "side_p1"]].rename(columns={"mantd_id": "source_key"})
    a["player_source_id"] = a["p1_atp_id"].str.lower()
    j = a.merge(sp.rename(columns={"match_id": "mid_acq", "side": "side_acq"}), on=["source_key", "player_source_id"])
    both = j[j["mid_acq"].notna() & j["match_id"].notna()]
    assert len(both) > 2000
    assert (both["match_id"] == both["mid_acq"]).mean() >= 0.99
    assert (both["side_p1"] == both["side_acq"]).mean() >= 0.99
    assert int((j["mid_acq"].notna() & j["match_id"].isna()).sum()) <= 5


def test_matches_newer_than_stage0_link_through_tennis_my_life(staged, xw):
    """Hide four events from Stage 0: the Tennis My Life path builds the same match ids and sides Stage 0 has."""
    st = staged[(staged["year"].astype(str) + "-" + staged["event_id"].astype(str)).isin(HIDDEN)]
    s0 = pd.read_parquet(LK.S0, columns=LK.S0_COLS)
    truth = LK.link(st, s0=s0, xw=xw)
    lk = LK.link(st, s0=s0[~s0["tournament_id"].isin(HIDDEN)], xw=xw)
    assert (lk["link_method"] == "tml").mean() >= 0.95
    j = lk[["match_id", "side_p1", "es", "lf", "obs"]].join(truth[["match_id", "side_p1"]], rsuffix="_t")
    ok = j["match_id"].notna() & j["match_id_t"].notna()
    assert (j.loc[ok, "match_id"] == j.loc[ok, "match_id_t"]).mean() >= 0.95
    assert (j.loc[ok, "side_p1"] == j.loc[ok, "side_p1_t"]).mean() >= 0.98
    assert (j.loc[ok, "es"] <= j.loc[ok, "obs"]).all() and (j.loc[ok, "obs"] <= j.loc[ok, "lf"]).all()


def test_crosswalk_and_unknown_codes(xw):
    assert xw.get("W0BH") == "atp:209409" and xw.get("HB64") == "atp:111460"
    assert LK.project_id("zz99", xw) == "atpcode:ZZ99"
    assert LK.project_id(None, xw) is None


def test_tennis_my_life_is_read_without_results():
    assert not {"score", "w_ace", "l_ace", "w_svpt", "minutes"} & set(LK.TML_COLS)
    t = LK.tml_table((2026,))
    assert not {"winner_id", "loser_id", "winner_name", "loser_name"} & set(t.columns)
    assert (t["c_lo"].fillna("") <= t["c_hi"].fillna("")).all()
