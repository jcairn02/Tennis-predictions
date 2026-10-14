"""Audit B of Stage 4, check 5 (the null band), two details beyond the reproduction in audit4_scoring.py.

    links           the plan says the shared keys make every copy "shuffle every feature the same way", so the copies
                    keep the rows' links to one another. A copy's permutation is drawn over the matches where the row
                    exists, so it is the same for two rows only when they exist on the same matches. Measured: for the
                    five forms of each statistic, the correlation over the 20 copies of the improvement given Elo, for
                    pairs of forms on the same matches (career with decayed, with adjusted) and on different matches
                    (career with 52 weeks, with surface), beside the correlation of the features themselves
    line drivers    each family-wide line is the largest of 20 copy maxima: which row and copy set it, how far it stands
                    above the other copies' maxima, and what the line would be without that row

Writes data/studies/predictability_diagnostic/audit4/band.json.

Run: ./python.sh src/eda/predictability_diagnostic/audit4_band.py   (under a minute)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import audit4_common as A  # noqa: E402

C = [f"copy_{i}" for i in range(1, 21)]


def loo_z(M: np.ndarray) -> np.ndarray:
    z = np.empty_like(M)
    for c in range(M.shape[1]):
        o = np.delete(M, c, axis=1)
        z[:, c] = (M[:, c] - o.mean(axis=1)) / o.std(axis=1, ddof=1)
    return z


def main() -> int:
    nc = pd.read_csv(A.OUT / "stage4_null_copies.csv")
    f = pd.read_parquet(A.OUT / "stage4_features.parquet")
    cand = pd.read_csv(A.OUT / "stage4_candidates.csv")
    stats = cand[cand["forms"].str.count(";") == 4]["id"].tolist()
    pairs = []
    for t in ("atp", "wta"):
        ft = f[f["tour"].eq(t)]
        for s in stats:
            g = nc[nc["tour"].eq(t) & nc["id"].eq(s) & nc["score"].eq("elo")].set_index("form")
            if len(g) < 5:
                continue
            for a, b in (("career", "decayed"), ("career", "adjusted"), ("career", "52 weeks"), ("career", "surface")):
                xa, xb = ft[f"{s}|{a}"].to_numpy("float64"), ft[f"{s}|{b}"].to_numpy("float64")
                ok = np.isfinite(xa) & np.isfinite(xb)
                pairs.append({"tour": t, "stat": s, "pair": f"{a} / {b}",
                              "same_matches": bool((np.isfinite(xa) == np.isfinite(xb)).all()),
                              "copy_corr": float(np.corrcoef(g.loc[a, C].astype(float), g.loc[b, C].astype(float))[0, 1]),
                              "feature_corr": float(np.corrcoef(xa[ok], xb[ok])[0, 1])})
    P = pd.DataFrame(pairs)
    links = (P.groupby("same_matches")[["copy_corr", "feature_corr"]].agg(["median", "min", "max", "count"]).round(3))
    links = {str(k): {f"{a}_{b}": float(v) for (a, b), v in row.items()} for k, row in links.iterrows()}

    drivers = {}
    for t in ("atp", "wta"):
        for s in ("alone", "elo", "market"):
            g = nc[nc["tour"].eq(t) & nc["score"].eq(s)].reset_index(drop=True)
            M = g[C].to_numpy("float64")
            keep = M.std(axis=1, ddof=1) > 0
            g, M = g[keep].reset_index(drop=True), M[keep]
            z = loo_z(M)
            mx = z.max(axis=0)
            c = int(mx.argmax())
            r = int(z[:, c].argmax())
            without = np.delete(z, r, axis=0).max()
            rk = pd.read_csv(A.OUT / "stage4_ranking.csv")
            zr = pd.to_numeric(rk.loc[rk["tour"].eq(t), f"{s}_z"], errors="coerce")
            second = float(np.sort(mx)[-2])
            drivers[f"{t}|{s}"] = {"line": float(mx.max()), "set_by": f"{g.at[r, 'id']}|{g.at[r, 'form']}", "copy": c + 1,
                                   "rows_between_second_maximum_and_line": int(((zr > second) & (zr <= mx.max())).sum()),
                                   "rows_above_line": int((zr > mx.max()).sum()),
                                   "copy_maxima_sorted": [round(float(v), 3) for v in np.sort(mx)[::-1]],
                                   "line_without_that_row": float(without),
                                   "rows_setting_a_copy_maximum": g.loc[z.argmax(axis=0), ["id", "form"]].astype(str)
                                   .agg("|".join, axis=1).value_counts().to_dict()}
    out = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "links": links, "pairs": pairs,
           "line_drivers": drivers}
    A.save_json(out, "band.json")
    print(json.dumps(links, indent=1))
    for k, v in drivers.items():
        print(k, round(v["line"], 2), v["set_by"], "copy", v["copy"], "| without:", round(v["line_without_that_row"], 2),
              "| maxima:", v["copy_maxima_sorted"][:4], "| setters:", v["rows_setting_a_copy_maximum"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
