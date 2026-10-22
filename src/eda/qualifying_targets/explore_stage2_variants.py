"""Part 2, EXPLORATORY (22 Oct 2026, 10:40, after top_edges.py's readings): why does the live instance's own stage 2
(its slopes and speed coefficient, fitted on main draws) return more on qualifying than stage 2 fitted on qualifying?

For today's model (M0) on Part 1's scored qualifying matches, with each of the two stage-2 versions:
    accuracy   paired log loss against the calibrated close (compare.paired, unmatched; positive = the model better),
               and the two versions against each other (matched seeds)
    bets       at each book's close: the bets each version makes, how many they share, and the ROI of the shared bets
               and of each version's own, by favourites (odds below 2) and underdogs
Nothing here is a verdict. Writes data/studies/qualifying_targets/exploratory_stage2_variants.json.
Run: ./python.sh src/eda/qualifying_targets/explore_stage2_variants.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.qualifying_targets import common as C  # noqa: E402
from src.eda.qualifying_targets import score as S  # noqa: E402
from src.eda.qualifying_targets import top_edges as TE  # noqa: E402


def main() -> int:
    info, z = S.qual_info()
    m0 = S.model(S.seed_table("M0", "qual"), info, z)
    keep = ~info["debut"].to_numpy() & info["season"].isin(S.TEST).to_numpy()
    ids = info.index[keep]
    minfo, mz = S.main_info()
    mm = S.model(S.seed_table("M0", "main"), minfo, mz)
    fq = S.fc(m0, "s2", info, ids)                                   # (mean, per seed): stage 2 fitted on qualifying
    fm = CMP.forecasts(m0["p"], info, mm["s2"], z, ids)              # the instance's stage 2 (main draws)
    close = CMP.close_forecast(info, "p_close", S.TEST, ids)
    out = {"accuracy": [S.row(info, ids, close, fq, False, comparison="qualifying stage 2 vs calibrated close"),
                        S.row(info, ids, close, fm, False, comparison="main-draw stage 2 vs calibrated close"),
                        S.row(info, ids, fq, fm, True, comparison="main-draw stage 2 vs qualifying stage 2")],
           "bets": []}
    for venue in TE.VENUES:
        a, b = TE.candidates(info, ids, fq[0], venue), TE.candidates(info, ids, fm[0], venue)
        # the same side? (a match where both bet but on opposite sides counts as not shared)
        side_a = np.sign(np.where(a["bet"], a["odds"], 0))
        same = a["bet"].to_numpy() & b["bet"].to_numpy() & (np.isclose(a["odds"].fillna(0), b["odds"].fillna(0)))
        for name, df, mask in (("shared bets", a, same), ("qualifying stage 2 only", a, a["bet"].to_numpy() & ~same),
                               ("main-draw stage 2 only", b, b["bet"].to_numpy() & ~same)):
            fav = (df["odds"] < 2.0).to_numpy()
            for part, m in (("all", mask), ("favourites", mask & fav), ("underdogs", mask & ~fav)):
                out["bets"].append({"venue": venue, "set": name, "part": part, **TE.roi(df, m)})
        out["bets"].append({"venue": venue, "set": "opposite sides", "part": "count",
                            "bets": int((a["bet"].to_numpy() & b["bet"].to_numpy() & ~same).sum())})
        _ = side_a
    C.write_json(C.OUT / "exploratory_stage2_variants.json", {"note": "exploratory, after the readings", **out})
    acc = pd.DataFrame(out["accuracy"])
    print(acc[["comparison", "matches", "estimate", "lo", "hi", "p_better", "reading"]].to_string(index=False))
    t = pd.DataFrame(out["bets"])
    t["roi_ci"] = t.apply(lambda r: (f"{100 * r['roi']:+.1f}% [{100 * r['roi_lo']:+.1f}, {100 * r['roi_hi']:+.1f}] "
                                     f"n={int(r['bets'])}") if pd.notna(r.get("roi")) else f"n={r.get('bets')}",
                          axis=1)
    pd.set_option("display.width", 250)
    print(t.pivot_table(index=["set", "part"], columns="venue", values="roi_ci", aggfunc="first").to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
