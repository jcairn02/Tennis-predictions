"""Outcome-free check (13 Oct 2026, synthesis 2): correlations among the provisional groups' scores and their members'
orthogonal parts on the frame's matches of seasons <= 2024 (no result column is read: the frame is loaded without it).
Pool members from the feature store (stand-ins until the rebuilt values exist). Writes lead_checks/group_corr.csv.
Run: ./python.sh src/eda/unpriced_leads/group_corr.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import screen as H  # noqa: E402

C = H.OUT / "candidates"
STORE = ROOT / "data" / "studies" / "feature_universe" / "store.parquet"
GROUPS = {
    "G1 luck": [("luck", "PS03_net", -1), ("luck", "PS06_close", -1), ("luck", "PS04_flat", -1)],
    "G2 letdown": [("store", "fi__B-MOTIV__post_slam", -1)],
    "G3 venue x serve": [("store", "fi__B-VENUE__x", +1)],
    "G4 status": [("store", "el__low_share_diff", +1), ("store", "fp__f12_salience__hasL_a-b", +1),
                  ("store", "pp__seeded_a-b", -1), ("store", "fp__f14_anchor__fame_a-b", -1)],
    "G5 rhythm": [("rhythm", "rb01_d7_else", +1), ("rhythm", "rb14_cold28", +1), ("rhythm", "rb03_lt20", -1),
                  ("store", "fi__B-STATE__x", +1)],
}


def main() -> int:
    names = [d["name"] for d in __import__("json").loads((H.INSTANCE / "model_inputs.json").read_text())["inputs"]]
    f = pd.read_parquet(H.FRAME, columns=["match_id", "tour", "season", "debut_season"] + [f"in_{n}" for n in names],
                        filters=[("season", "<=", 2024)])
    f = f[~f["debut_season"].astype(bool)].reset_index(drop=True)
    f["match_id"] = f["match_id"].astype(str)
    for k, (a, b) in H.PAIRS.items():
        f[f"in_{k}"] = f[f"in_{a}"] - f[f"in_{b}"]
    store_cols = sorted({c for g in GROUPS.values() for src, c, _ in g if src == "store"})
    need = set()
    for c in store_cols:
        need |= {c[:-4] + "_a", c[:-4] + "_b"} if c.endswith("_a-b") else {c}
    st = pd.read_parquet(STORE, columns=["match_id"] + sorted(need)).astype({"match_id": str})
    st = st.drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
    cache = {}
    scores, members = {}, {}
    for g, mem in GROUPS.items():
        parts = []
        for src, col, sign in mem:
            if src == "store":
                x = (st[col[:-4] + "_a"] - st[col[:-4] + "_b"]).to_numpy(float) if col.endswith("_a-b") \
                    else st[col].to_numpy(float)
            else:
                if src not in cache:
                    cache[src] = pd.read_parquet(C / src / "values.parquet").astype({"match_id": str}) \
                        .drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
                x = cache[src][col].to_numpy(float)
            xo, _ = H.orthogonal_part(f, x)
            sc = np.ones(len(f))
            for t in ("atp", "wta"):
                m = (f["tour"] == t).to_numpy()
                sc[m] = np.sqrt(np.nanmean(xo[m] ** 2))
            z = np.where(np.isfinite(xo), sign * xo / sc, 0.0)
            members[f"{g}: {col}"] = z
            parts.append(z)
        scores[g] = np.mean(np.column_stack(parts), axis=1)
    S = pd.DataFrame(scores)
    print("group scores, Pearson r (seasons <= 2024, outcome-free):")
    print(S.corr().round(3).to_string())
    M = pd.DataFrame(members)
    big = M.corr().where(lambda d: (d.abs() > 0.3) & (d.abs() < 0.999)).stack()
    print("member pairs with |r| > 0.3:")
    print(big.round(3).to_string() if len(big) else "none")
    (H.OUT / "lead_checks").mkdir(parents=True, exist_ok=True)
    S.corr().to_csv(H.OUT / "lead_checks" / "group_corr.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
