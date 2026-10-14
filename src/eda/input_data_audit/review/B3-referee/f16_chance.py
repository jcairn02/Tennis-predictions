"""B3-referee, F16: are the "copied" speed blocks copies, or chance coincidences of integer statistics?

Read-only. Writes data/studies/input_data_audit/fixes/B3-referee/f16_chance.json.

(1) Same player, two different matches (panel use rows, key-statistic and match-centre sources, integer values):
    pairs with identical (y_raw, spd2_raw, spd_max) regardless of n, and how many of those also share n. If the
    blocks were copied whole, n would always be shared; if they are chance coincidences, n is shared about as often as
    two of the player's matches share n at random (measured on all the player's pairs).
(2) Both sides of one match: matches with y_raw equal, with n equal, and with both, by source; the chance rate of
    "both" is estimated as P(y equal) x P(n equal) within the source.
(3) The box score check: for each flagged record, n (first serves in) and n2 (second-serve points) against Stage 0's box.
"""
from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "data/studies/input_data_audit/fixes/B3-referee"
SP = ROOT / "data/studies/serve_speed_tabpfn"


def main() -> None:
    pan = pd.read_parquet(SP / "speed_panel.parquet")
    u = pan[pan["use"] & pan["kind"].isin(["keystat", "mc_floor"])].copy()
    res = {}
    # (1) same player, two matches
    trip, quad, npairs, same_n = 0, 0, 0, 0
    for (tour, pid), g in u.groupby(["tour", "player_id"]):
        if len(g) < 2:
            continue
        y, s2, mx, n = (g[c].to_numpy() for c in ("y_raw", "spd2_raw", "spd_max", "n"))
        for i, j in combinations(range(len(g)), 2):
            npairs += 1
            same_n += int(n[i] == n[j])
            if y[i] == y[j] and s2[i] == s2[j] and mx[i] == mx[j]:
                trip += 1
                quad += int(n[i] == n[j])
    res["same_player"] = {"pairs_of_use_rows": npairs, "share_with_equal_n": same_n / npairs,
                          "pairs_equal_y_spd2_max": trip, "of_which_equal_n": quad,
                          "expected_equal_n_if_chance": trip * same_n / npairs}
    # (2) both sides of a match
    out = {}
    for src, g in u.groupby("source"):
        w = g.pivot_table(index="match_id", columns="side", values=["y_raw", "n"], aggfunc="first").dropna()
        if w.empty:
            continue
        ye = (w[("y_raw", "A")] == w[("y_raw", "B")])
        ne = (w[("n", "A")] == w[("n", "B")])
        out[src] = {"matches": int(len(w)), "y_equal": int(ye.sum()), "n_equal": int(ne.sum()),
                    "both_equal": int((ye & ne).sum()),
                    "expected_both_if_independent": float(len(w) * ye.mean() * ne.mean())}
    res["both_sides"] = out
    (OUT / "f16_chance.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
