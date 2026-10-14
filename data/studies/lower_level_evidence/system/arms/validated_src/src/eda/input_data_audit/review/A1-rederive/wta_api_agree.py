"""Per-event agreement of Sackmann with the WTA API (from wta_api_link.py output), with each disagreeing match classed:
'equal' (all 18 counts), 'exchanged' (all 18 equal once the two players' boxes are exchanged), 'other'.
Writes wta_api_agree_<tag>_events.csv and wta_api_agree_<tag>_matches.csv."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

tag = sys.argv[1] if len(sys.argv) > 1 else "2021_2022"
d = pd.read_parquet(R.OUT / f"wta_api_links_{tag}.parquet")
d = d[d["has_box"]].copy()


def eq_all(d, swap=False, skip=()):
    ok = np.ones(len(d), dtype=bool)
    for side in ("w", "l"):
        other = {"w": "l", "l": "w"}[side] if swap else side
        for b in R.BOX:
            if b in skip:
                continue
            ok &= d[f"s_{side}_{b}"].eq(d[f"a_{other}_{b}"]).to_numpy()
    return ok


d["equal"] = eq_all(d)
d["exchanged"] = eq_all(d, swap=True)
d["equal16"] = eq_all(d, skip=("sv_gms",))
d["n_diff"] = sum((~d[f"s_{s}_{b}"].eq(d[f"a_{s}_{b}"])).astype(int) for s in ("w", "l") for b in R.BOX)
d["cls"] = np.select([d["equal"], d["exchanged"]], ["equal", "exchanged"], "other")
d["ev"] = d["tdate"].dt.strftime("%Y-%m-%d") + " " + d["tourney_name"] + " (" + d["tourney_id"] + ")"
ev = d.groupby("ev").agg(matches=("cls", "size"), equal=("equal", "sum"), exchanged=("exchanged", "sum"),
                         other=("cls", lambda c: int((c == "other").sum())),
                         api_winner_differs=("api_winner_is_sack_winner", lambda v: int((v == False).sum())))  # noqa: E712
ev["equal_share"] = ev["equal"] / ev["matches"]
ev.to_csv(R.OUT / f"wta_api_agree_{tag}_events.csv")
d.to_csv(R.OUT / f"wta_api_agree_{tag}_matches.csv", index=False)
pd.set_option("display.width", 250)
print(ev[ev["equal_share"] < 0.97].sort_values("equal_share").to_string())
print("events:", len(ev), " matches:", len(d), " equal:", int(d["equal"].sum()), " exchanged:", int(d["exchanged"].sum()),
      " other:", int((d["cls"] == "other").sum()), " api winner differs:", int((d["api_winner_is_sack_winner"] == False).sum()))  # noqa: E712
print("n_diff of 'other' rows:", d.loc[d["cls"].eq("other"), "n_diff"].value_counts().sort_index().to_dict())
