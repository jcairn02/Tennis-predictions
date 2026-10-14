"""Stage 1, part 4: which shot-level statistics are traits of a player, by split-half reliability.

For each statistic and tour: the players with at least MIN_MATCHES matches carrying the statistic (any year); each
player's matches split alternately into two halves in chronological order; the correlation, across players, of the two
halves' rates (sum of numerators over sum of denominators). A chance band comes from the same correlation with the
second halves shuffled across players (200 permutations, 2.5% and 97.5% points). This is the predictability diagnostic's
Stage 3 question (does a statistic repeat?) asked of the new statistics; no result of a match is read.

Run:  ./python.sh src/eda/shot_level/stage1_reliability.py   (under a minute)
Writes data/studies/shot_level/stage1_reliability.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import stats as T  # noqa: E402

MIN_MATCHES = 30
PERMUTATIONS = 200


def main() -> int:
    st = pd.read_parquet(S.OUT / "stage1_match_stats.parquet")
    order = C.load_matches(["match_id", "order"]).set_index("match_id")["order"]
    st["order"] = st["match_id"].map(order)
    st = st.sort_values(["player_id", "order"])
    rng = np.random.default_rng(20261002)
    rows = []
    for s in T.ALL_STATS:
        for t in C.TOURS:
            g = st[(st["tour"] == t) & (st[f"{s}_d"] > 0)][["player_id", f"{s}_n", f"{s}_d"]].copy()
            g["half"] = g.groupby("player_id").cumcount() % 2
            cnt = g.groupby("player_id").size()
            a = g.groupby(["player_id", "half"])[[f"{s}_n", f"{s}_d"]].sum().unstack()
            a = a[(cnt.reindex(a.index) >= MIN_MATCHES).to_numpy()]
            a = a[(a[(f"{s}_d", 0)] > 0) & (a[(f"{s}_d", 1)] > 0)]
            rec = {"statistic": s, "family": T.FAMILY_OF[s], "tour": t, "players": int(len(a))}
            if len(a) >= 30:
                r0 = (a[(f"{s}_n", 0)] / a[(f"{s}_d", 0)]).to_numpy()
                r1 = (a[(f"{s}_n", 1)] / a[(f"{s}_d", 1)]).to_numpy()
                r = float(np.corrcoef(r0, r1)[0, 1])
                perm = np.array([np.corrcoef(r0, rng.permutation(r1))[0, 1] for _ in range(PERMUTATIONS)])
                rec.update({"split_half_r": r, "chance_lo": float(np.quantile(perm, 0.025)),
                            "chance_hi": float(np.quantile(perm, 0.975)),
                            "above_chance": bool(r > np.quantile(perm, 0.975)),
                            "half_units": float(np.concatenate([a[(f"{s}_d", 0)], a[(f"{s}_d", 1)]]).mean())})
            rows.append(rec)
    out = pd.DataFrame(rows)
    out.to_csv(S.OUT / "stage1_reliability.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_rows", 80):
        print(out.round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
