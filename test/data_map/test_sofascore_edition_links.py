"""The map places the by-edition SofaScore rows on the matches its adapter linked them to (offline, synthetic)."""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.data_map import measure as M  # noqa: E402


def test_adapter_links_beat_a_meeting_the_week_before(tmp_path):
    links = tmp_path / "sofascore_atp_points_2025_matches.csv"
    pd.DataFrame({"tour": "M", "tname": ["Mallorca", "Mallorca", "Halle", "Rotterdam", "Rotterdam"],
                  "d": ["2026-06-24", "2026-06-25", "2026-06-19", "2026-02-09", "2026-02-13"],
                  "name1": ["Ann Bee", "Cid Dee", "Eve Eff", "Ugo Humbert", "Ugo Humbert"],
                  "name2": ["Gus Hay", "Ivo Jay", "Kim Ell", "Chris Oconnell", "Chris O'Connell"],
                  "creator": ["tml", "tml", "tml", "sackmann", "tml"],
                  "event_id": ["11", None, "33", "55", "55"]}).to_csv(links, index=False)
    # 2026 matches are dated by the day played: the pair also met at Eastbourne five days earlier, which the
    # generic link would prefer (|5 - 3| < |0 - 3|); Halle's key names two matches, so it places neither;
    # Rotterdam's match is in the map twice (two spellings), and Tennis My Life's row takes the event
    matches = pd.DataFrame({"uid": [1, 2, 3, 4, 5, 6, 7], "tour": "M",
                            "tname": ["Mallorca", "Mallorca", "Eastbourne", "Halle", "Halle", "Rotterdam", "Rotterdam"],
                            "d": pd.to_datetime(["2026-06-24", "2026-06-25", "2026-06-19", "2026-06-19", "2026-06-19",
                                                 "2026-02-09", "2026-02-13"]),
                            "name1": ["Ann Bee", "Cid Dee", "Ann Bee", "Eve Eff", "Eve Eff", "Ugo Humbert",
                                      "Ugo Humbert"],
                            "name2": ["Gus Hay", "Ivo Jay", "Gus Hay", "Kim Ell", "Kim Ell", "Chris Oconnell",
                                      "Chris O'Connell"]})
    rows = pd.DataFrame({"event_id": ["11", "22", "33", "44", "55"]})
    got = M.sofascore_edition_uids(rows, matches, paths=[links])
    assert got.iloc[0] == 1 and got.iloc[1:4].isna().all() and got.iloc[4] == 7
    assert M.sofascore_edition_uids(rows, matches, paths=[]).isna().all()
