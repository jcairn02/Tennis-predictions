"""The feed's rule verdicts (src/eda/data_gaps_2026/feed.py) on a candidate whose builder wrote empty identity samples."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.data_gaps_2026 import feed as FD  # noqa: E402


def test_rule_verdicts_read_links_and_skip_the_empty_samples_of_a_box_only_candidate(tmp_path):
    """A box-only source's candidate (14 Oct 2026, the TennisLive box-score package) adds no player: the builder writes
    empty player, new-id and repair-move samples, and the links are judged alone."""
    pd.DataFrame({"source": "tennislive_pages", "sid": ["s1", "s2"], "src_p1": ["Taro Daniel", "Jiri Lehecka"],
                  "src_p2": ["Daniel Munoz-De La Nava", "Alexander Shevchenko"], "src_day": ["2019-09-18", "2021-07-31"],
                  "src_event": ["Biella Challenger", "Poznan Challenger"], "src_round": [None, "SF"],
                  "match_id": ["m1", "m2"], "s0_a": ["Daniel Munoz de la Nava", "Jiri Lehecka"],
                  "s0_b": ["Taro Daniel", "Alexander Shevchenko"], "s0_date": ["2019-09-16", "2021-07-26"],
                  "s0_event": ["Biella CH", "Poznan CH"], "s0_round": ["R32", "QF"], "name_grade": [6, 6]}).to_csv(
        tmp_path / "identity_sample_links.csv", index=False)
    for f in ("identity_sample_players.csv", "identity_sample_new_ids.csv", "identity_sample_repair_moves.csv"):
        pd.DataFrame().to_csv(tmp_path / f, index=False)                # what the builder writes with no rows
    v = FD.auto_verdicts(tmp_path)
    assert v["kind"].tolist() == ["links", "links"]
    assert v["verdict"].tolist() == ["right", "unsure"]                  # the second's rounds differ (SF and QF)
    assert FD.screen(v)["pass"]                                          # under SCREEN_MIN rows: not judged
