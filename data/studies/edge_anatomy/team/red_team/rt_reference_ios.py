"""Red team: is the men's 2025-26 serve/return lead an artefact of the 10 Oct level layer? Re-run the single-input scan
on the frozen 8 Oct reference frame (no level layer; books' average as its price) and on the current instance, men,
2025-26 and 2024. Outcomes: rows with tournament_date < 29 Jul 2026 only (filter in the read).
Run: ./python.sh data/studies/edge_anatomy/team/red_team/rt_reference_ios.py"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rt_common as R  # noqa: E402

INS = ["iosO_hold", "iosO_bp_saved", "iosD_first_won", "iosD_hold", "prod_hold", "prod_bp_saved", "form_bp_saved",
       "sets_14d", "age"]
REF = R.ROOT / "data/studies/current_best_model/reference_2026-10-08/frozen/instance/model_frame.parquet"


def load(path):
    cols = ["match_id", "tournament_date", "tour", "season", "debut_season", "p_mkt", "a_won"] + [f"in_{c}" for c in INS]
    f = pd.read_parquet(path, columns=cols, filters=[("tournament_date", "<", R.SEALED)])
    assert f["tournament_date"].max() < R.SEALED
    f = f[~f["debut_season"].astype(bool) & (f["tour"] == "atp")].copy()
    f["match_id"] = f["match_id"].astype(str)
    f["y"] = f["a_won"].astype(float)
    f["L"] = R.lg(f["p_mkt"])
    return f


def z(g, c):
    y, cl = g["y"].to_numpy(), R.blocks(g["tournament_date"], 28)
    x = R.rms_scaled(g[f"in_{c}"].to_numpy(float))[0]
    X = np.column_stack([g["L"].to_numpy(), x])
    b, Hi = R.logistic(X, y)
    V, G = R.sandwich(X, y, np.zeros(len(y)), b, Hi, cl)
    return b[1] / np.sqrt(V[1, 1])


rows = []
cur, ref = load(R.INSTANCE / "model_frame.parquet"), load(REF)
common = cur["match_id"][cur["match_id"].isin(ref["match_id"])]
for name, f in (("instance 10 Oct (level layer)", cur), ("reference 8 Oct (no layer)", ref)):
    for w, ss in (("2025-26", (2025, 2026)), ("2024", (2024,))):
        g = f[f["season"].isin(ss) & f["match_id"].isin(common)]
        for c in INS:
            rows.append({"frame": name, "window": w, "input": c, "z": z(g, c), "n": len(g)})
# input agreement between the two frames on the common matches, 2025-26
m = cur.set_index("match_id").loc[common]
r = ref.set_index("match_id").loc[common]
s = m["season"].isin((2025, 2026))
print("correlation of the inputs between frames, men 2025-26:",
      {c: round(float(np.corrcoef(np.nan_to_num(m.loc[s, f'in_{c}']), np.nan_to_num(r.loc[s, f'in_{c}']))[0, 1]), 3)
       for c in INS})
t = pd.DataFrame(rows).pivot_table(index="input", columns=["window", "frame"], values="z")
print(t.round(2).to_string())
t.to_csv(R.OUT / "rt_reference_ios.csv")
