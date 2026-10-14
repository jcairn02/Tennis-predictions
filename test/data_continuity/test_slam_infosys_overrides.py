"""slam_infosys_overrides.keystat_rows: the two Slams' key statistics, named differently, read into the same counts."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.eda.data_continuity import slam_infosys_overrides as SIO  # noqa: E402


def doc(names: dict) -> dict:
    """A key-statistics document whose match ("set0") holds these statistics as (player1, player2)."""
    return {"setStats": {"set0": [{"name": n, "player1": a, "player2": b} for n, (a, b) in names.items()]}}


AO = {"Aces": ("9", "4"), "Double Faults": ("2", "2"), "1st Serve In": ("66/101 (65%)", "85/123 (69%)"),
      "Win 1st Serve": ("51/66 (77%)", "56/85 (66%)"), "Win 2nd Serve": ("20/35 (57%)", "20/38 (53%)"),
      "Break Points Won": ("5/16 (31%)", "2/6 (33%)")}
RG = {"Aces": ("9", "4"), "Double Faults": ("2", "2"), "First Serve": ("66/101 (65%)", "85/123 (69%)"),
      "Win On 1st Serve": ("51/66 (77%)", "56/85 (66%)"), "Win On 2nd Serve": ("20/35 (57%)", "20/38 (53%)"),
      "Break Points Won": ("5/16 (31%)", "2/6 (33%)")}


def test_both_naming_schemes_give_the_same_counts():
    a, r = SIO.keystat_rows("MS701", doc(AO)), SIO.keystat_rows("SM001", doc(RG))
    strip = [{k: v for k, v in x.items() if k != "code"} for x in a], [{k: v for k, v in x.items() if k != "code"}
                                                                      for x in r]
    assert strip[0] == strip[1]
    one, two = a
    assert (one["ks_svpt"], one["ks_first_in"], one["ks_first_won"], one["ks_second_won"]) == (101, 66, 51, 20)
    # break points faced and saved come from the opponent's "break points won": player 2 won 2 of 6 on player 1's serve
    assert (one["ks_bp_faced"], one["ks_bp_saved"]) == (6, 4) and (two["ks_bp_faced"], two["ks_bp_saved"]) == (16, 11)


def test_a_document_without_first_serves_gives_no_rows():
    assert SIO.keystat_rows("MS701", doc({"Aces": ("9", "4")})) == []
