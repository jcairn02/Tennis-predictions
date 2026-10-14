"""The 2027 fix (10 Oct 2026, docs/studies/daily_update_speed/): a match of a season after 2026 passes every gate that
used to stop at 2026, and every season to 2026 is treated as before."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.match_timing import srcc_slams as SL  # noqa: E402
from src.eda.match_timing import timing as TM  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage4_features as S4  # noqa: E402
from src.eda.tabpfn_thinking import build_frame as TB  # noqa: E402

YEARS = [2009, 2010, 2012, 2013, 2021, 2022, 2026, 2027, 2031]


def test_the_evaluation_flag_has_no_last_season():
    m = pd.DataFrame({"year": YEARS, "level": "T250", "status": "completed"})
    assert C.in_evaluation(m).tolist() == [y >= 2013 for y in YEARS]
    assert not C.in_evaluation(m.assign(level="ITF")).any()
    assert not C.in_evaluation(m.assign(status="walkover")).any()


def test_the_pool_has_no_last_season():
    rows = pd.DataFrame({"year": np.repeat(YEARS, 2), "level": "T250", "status": "completed"})   # two rows a match
    assert S4.pool_mask(rows).tolist() == [y >= 2010 for y in YEARS]


def test_the_frame_split_has_no_last_season():
    year = np.array(YEARS)
    split = TB.split_of(year, np.ones(len(year), dtype=bool))
    want = ["" if y < 2013 else ("train" if y <= 2021 else "test") for y in YEARS]
    assert split.tolist() == want
    assert TB.split_of(year, np.zeros(len(year), dtype=bool)).tolist() == [""] * len(YEARS)


def test_eras_take_later_seasons_into_the_last_one_and_keep_their_labels():
    year = pd.Series(YEARS)
    assert TM.era_of(year).tolist() == ["", "2010-2018", "2010-2018", "2010-2018", "2021-2026", "2021-2026",
                                        "2021-2026", "2021-2026", "2021-2026"]
    got = C.era_of(year).tolist()
    assert got[3:] == ["2013-16", "2020-21", "2022-26", "2022-26", "2022-26", "2022-26"]
    assert all(pd.isna(v) for v in got[:3])


def test_the_odds_sources_take_every_staged_season_with_no_last_one(tmp_path, monkeypatch):
    """A 2027 tennis-data file is linked to OddsTrader like any other season, so a 2027 match gets BetOnline's close
    (the Pinnacle-first rule) instead of the books' average; the seasons held today are the lists of before."""
    from src.eda.odds_sources import common as OC
    assert OC.FRAME_SEASONS == tuple(range(2013, 2027)) and OC.OT_SEASONS == tuple(range(2018, 2027))
    for tour, level, season in (("atp", "atp250", 2017), ("atp", "atp250", 2026), ("wta", "international", 2018),
                                ("atp", "grand_slam", 2027), ("wta", "international", 2027)):
        (tmp_path / tour / level).mkdir(parents=True, exist_ok=True)
        (tmp_path / tour / level / f"{season}.parquet").write_bytes(b"")
    (tmp_path / "atp" / "atp250" / "notes.parquet").write_bytes(b"")
    monkeypatch.setattr(OC, "TD", tmp_path)
    assert OC.td_seasons(2018) == (2018, 2026, 2027)
    assert OC.td_seasons(2013) == (2017, 2018, 2026, 2027)


def test_slam_timestamps_of_a_later_season_are_plausible_and_earlier_bounds_are_unchanged():
    hi = SL.epoch_hi(pd.Series([2018, 2026, np.nan, 2027, 2030]))
    assert hi[0] == hi[1] == hi[2] == SL.EPOCH_OK[1]
    assert hi[3] == pd.Timestamp("2028-01-01", tz="UTC").timestamp()
    assert hi[4] == pd.Timestamp("2031-01-01", tz="UTC").timestamp()
