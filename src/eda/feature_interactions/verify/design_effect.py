"""Harness verifier, task 3: the design effect re-measured against the current best (critique 1.3; plan M1, M4).

REAL results (a_won, 2014-2024) against the current best's out-of-sample log-odds, with RANDOM features only, through
screen.run (per tour x season slopes, the odd cubic, no controls): the spread of b over draws (the true null spread)
against the estimators' variances. No candidate and no real feature is related to the results here.

    iid             N(0, 1) per match
    player_fixed    u_A - u_B, u ~ N(0, 1) per player (like height, hand, country)
    player_season   u_A,s - u_B,s, one u per player and season
    tourn_x_eta     t x eta, t ~ N(0, 1) per tournament edition (tournament id x season): a context modulation
    block_x_eta     t x eta, t per four-week block

Run: ./python.sh src/eda/feature_interactions/verify/design_effect.py [--draws 300]
Writes data/studies/feature_interactions/verify/design_effect_draws.parquet and design_effect.json
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402

TYPES = ("iid", "player_fixed", "player_season", "tourn_x_eta", "block_x_eta")


def per_key(keys: np.ndarray, rng) -> np.ndarray:
    _, ix = np.unique(keys, return_inverse=True)
    return rng.normal(size=ix.max() + 1)[ix]


def feature(F: pd.DataFrame, kind: str, rng) -> np.ndarray:
    pa, pb = F["player_a_id"].astype(str).to_numpy(), F["player_b_id"].astype(str).to_numpy()
    if kind == "iid":
        return rng.normal(size=len(F))
    if kind in ("player_fixed", "player_season"):
        tag = "" if kind == "player_fixed" else F["season"].astype(str).to_numpy()
        u = per_key(np.r_[np.char.add(pa, tag), np.char.add(pb, tag)], rng)
        return u[:len(F)] - u[len(F):]
    eta = F["z_model"].to_numpy(float)
    keys = F["tedition"].to_numpy() if kind == "tourn_x_eta" else F["block"].astype(str).to_numpy()
    return per_key(keys, rng) * eta


def summarise(D: pd.DataFrame) -> list[dict]:
    out = []
    for kind, g in D.groupby("type", sort=False):
        for w in ("1", "2"):
            mv = (g[f"se_model{w}"] ** 2).mean()
            row = {"type": kind, "window": "2014-2021" if w == "1" else "2022-2024", "draws": len(g),
                   "true_var": g[f"b{w}"].var(ddof=1) / mv}
            for est in ("block", "player", "union"):
                row[f"{est}_est"] = (g[f"se_{est}{w}"] ** 2).mean() / mv
            row["harness_est"] = (g[f"se{w}"] ** 2).mean() / mv
            row["true_over_harness"] = row["true_var"] / row["harness_est"]
            row["sd_z"] = g[f"z{w}"].std(ddof=1)
            row["fpr_two_sided_5"] = float((g[f"z{w}"].abs() > 1.96).mean())
            out.append(row)
        out.append({"type": kind, "window": "joint z", "draws": len(g), "sd_z": g["z_joint"].std(ddof=1),
                    "fpr_two_sided_5": float((g["z_joint"].abs() > 1.96).mean()),
                    "corr_z1_z2": float(np.corrcoef(g["z1"], g["z2"])[0, 1])})
    return out


def main() -> int:
    warnings.simplefilter("ignore")
    draws = int(sys.argv[sys.argv.index("--draws") + 1]) if "--draws" in sys.argv else 300
    F = S.load(with_model=True)
    s0 = pd.read_parquet(S.PRE_REBUILD_STAGE0, columns=["match_id", "tournament_id"])
    s0["match_id"] = s0["match_id"].astype(str)
    F = F.merge(s0, on="match_id", how="left", validate="one_to_one")
    F["tedition"] = F["tournament_id"].astype(str) + "|" + F["season"].astype(str)
    rng = np.random.default_rng(20261006)
    keep = ("b1", "se1", "se_model1", "se_block1", "se_player1", "se_union1", "z1",
            "b2", "se2", "se_model2", "se_block2", "se_player2", "se_union2", "z2", "z_joint")
    rows = []
    for kind in TYPES:
        for d in range(draws):
            r = S.run(F, S.Hypothesis(kind, feature(F, kind, rng)), n_p1=0, sizes=False)
            rows.append({"type": kind, "draw": d, **{k: r[k] for k in keep}})
        C.log(f"{kind}: {draws} draws")
        pd.DataFrame(rows).to_parquet(C.OUT / "verify" / "design_effect_draws.parquet", index=False)
    D = pd.DataFrame(rows)
    C.write_json(C.OUT / "verify" / "design_effect.json", {"draws": draws, "editions": int(F["tedition"].nunique()),
                                                           "table": summarise(D)})
    C.log("written design_effect.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
