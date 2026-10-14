"""Red team: the README's process is "discover over many seasons, CONFIRM on the most recent closes". advice.py's
"both" rule is that confirm step (decade |z| >= 2 AND the same sign in 2023-24). Paired: both against decade, 2025-26.
Run: ./python.sh data/studies/edge_anatomy/team/red_team/rt_advice_confirm.py"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rt_common as R  # noqa: E402
import rt_residual as RS  # noqa: E402
import rt_advice as AD  # noqa: E402

f, xs = RS.frame()
sel = pd.read_csv(R.OUT / "rt_advice_selection.csv")
dec = {t: sel[(sel.tour == t) & (sel.z_2013_24.abs() >= 2)]["input"].tolist() for t in ("atp", "wta")}
both = {t: sel[(sel.tour == t) & (sel.z_2013_24.abs() >= 2) & (np.sign(sel.z_2013_24) == np.sign(sel.z_2023_24))]
        ["input"].tolist() for t in ("atp", "wta")}
print("decade", dec)
print("both  ", both)
a = R.load_analysis().set_index("match_id")
P = a[a["season"].isin((2025, 2026)) & ~a["debut"]][["season", "tour", "y", "block", "q_close", "q_full"]].copy()
P["decade"] = AD.predict(f, dec).reindex(P.index)
P["both"] = AD.predict(f, both).reindex(P.index)
for tour in ("both", "atp", "wta"):
    g = P if tour == "both" else P[P["tour"] == tour]
    for x, ybase in (("both", "q_close"), ("decade", "q_close"), ("both", "decade")):
        d = R.gain(g[ybase], g[x], g["y"].to_numpy(), g["block"].to_numpy())
        print(f"{tour:5s} {x:7s} vs {ybase:8s} {R.fmt(d)}")
