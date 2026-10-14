"""Round 2, MECHANICS, part D: between-cell leverage. Per tour x surface x indoor x best-of cell, the slope of the close's
log-odds and of the iid's own log-odds on the IOS serve-point edge Delta (2013-2021; a_won never read). If the close
followed the iid's leverage across cells, the ratio a_close / a_iid would be the same in every cell.

Run: ./python.sh src/eda/feature_interactions/round2/mechanics/part_d.py
"""
from __future__ import annotations

import json

import numpy as np

from common import OUT, load, match_logit, pr


def main():
    f, _ = load()
    delta = ((f["srf_O_eff_spw_a"] - f["srf_D_eff_spw_b"]) - (f["srf_O_eff_spw_b"] - f["srf_D_eff_spw_a"])).to_numpy()
    z_iid = match_logit(pr(f, "spw", "a", "b"), pr(f, "spw", "b", "a"), f["in_best_of"].to_numpy())
    z = f["in_odds_logit"].to_numpy()
    ind = f["in_indoor"].map({0.0: "out", 1.0: "in"}).fillna("na")
    cell = f["tour"] + " " + f["surface"] + " " + ind + " bo" + f["in_best_of"].astype(int).astype(str)
    rows = []
    for c in sorted(cell.unique()):
        m = (cell == c).to_numpy() & np.isfinite(delta) & np.isfinite(z_iid)
        if m.sum() < 300:
            continue
        X = np.column_stack([delta[m], delta[m] ** 3])
        a_close = float(np.linalg.lstsq(X, z[m], rcond=None)[0][0])
        a_iid = float(np.linalg.lstsq(X, z_iid[m], rcond=None)[0][0])
        rows.append({"cell": c, "n": int(m.sum()), "a_close": round(a_close, 3), "a_iid": round(a_iid, 3),
                     "ratio": round(a_close / a_iid, 3)})
    for t in ("atp", "wta"):
        r = [x for x in rows if x["cell"].startswith(t)]
        ai, ac, n = (np.array([x[k] for x in r]) for k in ("a_iid", "a_close", "n"))
        # across cells: elasticity of the close's slope to the iid's slope (1 = follows the leverage, 0 = flat)
        slope = np.polyfit(np.log(ai), np.log(ac), 1, w=np.sqrt(n))[0]
        rows.append({"cell": f"{t}: d ln a_close / d ln a_iid across cells", "value": round(float(slope), 3)})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "part_d.json").write_text(json.dumps(rows, indent=1))
    for x in rows:
        print(x)


if __name__ == "__main__":
    main()
