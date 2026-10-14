"""Size of the confirmed bad rows: replace their p_mkt by the independent books' de-vigged median (or the flipped value
for the mis-oriented winner_swapped row) and measure the market's log loss on train and test.
Output: out/a12_impact.json
"""
import json

import numpy as np
import pandas as pd

from _common import OUTD

D = pd.read_parquet(OUTD / "a03_joined.parquet")
fl = pd.read_csv(OUTD / "a07_avg_vs_books.csv").set_index("match_id")
confirmed_reversed = ["atp|2013-891|SF|atp:104386|atp:105379", "atp|2016-540|F|atp:104918|atp:105683",
                      "wta|2022-2030|R32|wta:201603|wta:216146", "wta|2025-822|F|wta:210722|wta:211817"]
winner_swapped_reversed = ["wta|2017-1080|F|wta:202427|wta:202499"]
garbled = ["atp|2022-421|R64|atp:105138|atp:106218", "wta|2024-2050|R32|wta:211713|wta:215453", "wta|2024-1003|R64|wta:203354|wta:215713",
           "atp|2022-520|R128|atp:105967|atp:124079", "atp|2013-560|R128|atp:104297|atp:105577"]
inferred_late = ["wta|2026-1038|R32|wta:211768|wta:211843"]
p_new = D.set_index("match_id")["p_mkt"].copy()
for m in confirmed_reversed + garbled:
    p_new[m] = fl.loc[m, "p_ref_median"]
for m in winner_swapped_reversed:
    p_new[m] = 1 - p_new[m]
D["p_fix"] = D["match_id"].map(p_new)
y = D["a_won"].astype(float)
out = {"rows_changed": {s: int(((D["p_fix"] != D["p_mkt"]) & (D["tabpfn_split"] == s)).sum()) for s in ("train", "test")}}
for s in ("train", "test"):
    g = D[D["tabpfn_split"] == s]
    yy = g["a_won"].astype(float)
    ll = lambda p: float(-(yy * np.log(p) + (1 - yy) * np.log(1 - p)).mean())  # noqa: E731
    out[s] = {"logloss_as_is": round(ll(g["p_mkt"]), 6), "logloss_fixed": round(ll(g["p_fix"]), 6)}
    out[s]["delta"] = round(out[s]["logloss_fixed"] - out[s]["logloss_as_is"], 6)
rows = D[D["match_id"].isin(confirmed_reversed + winner_swapped_reversed + garbled + inferred_late)]
out["rows"] = rows[["match_id", "tabpfn_split", "a_won", "p_mkt", "p_fix", "p_elo"]].round(4).to_dict("records")
(OUTD / "a12_impact.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
