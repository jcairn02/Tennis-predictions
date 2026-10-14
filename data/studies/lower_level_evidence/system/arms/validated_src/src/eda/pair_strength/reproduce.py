"""Step 1: reproduce the feature-interactions screen's I-084 row (a machinery check, no new information).

I-084's column and controls are rebuilt with the frozen builder's own functions (features/f10_price_slopes.py:
prominence, level dummies, I-036's obscurity, B-FLB's L and HP, the three nearest inputs as Std) and assembled as
screen_batch.screen_one does for an x_times_eta row (eta-modulator controls x eta, the M-set eta|eta| per tour), then run
through screen.run (per tour x season slopes, cubic, clustered z, the slow-trait widening sqrt(1.25), 200 P1
permutations). Target, data/studies/feature_interactions/hypotheses/screen_results.csv: model base z1 -2.6566,
z2 -2.0326 (unwidened), joint -2.9846; market base z1 -2.8481, z2 -2.0081, joint -3.1155.

    ./python.sh src/eda/pair_strength/reproduce.py
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.eda.pair_strength import common as C  # noqa: E402
from src.eda.feature_interactions import screen as S  # noqa: E402
from src.eda.feature_interactions.features import f10_price_slopes as F10  # noqa: E402
from src.eda.feature_interactions.features import mkt_common as M  # noqa: E402
from src.eda.feature_interactions.panel import panel  # noqa: E402


def i084_inputs(P: pd.DataFrame) -> dict:
    """I-084 exactly as the frozen builder returns it (x = prominence, Std controls, eta-modulator controls)."""
    return F10.combine_i084(P)


def assemble(F: pd.DataFrame, r: dict, pos: np.ndarray, e: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """screen_batch.screen_one's assembly for an x_times_eta row with the M-set."""
    xb = np.asarray(r["x"], float)[pos] * e
    parts = [np.asarray(r["controls"], float)[pos]]
    names = list(r["control_names"])
    Em = np.asarray(r["eta_mod_controls"], float).reshape(len(r["x"]), -1)[pos]
    parts.append(Em * e[:, None])
    names += [f"mod{j} x eta" for j in range(Em.shape[1])]
    atp = (F["tour"] == "atp").to_numpy()
    parts.append(np.column_stack([np.where(atp, e * np.abs(e), 0.0), np.where(~atp, e * np.abs(e), 0.0)]))
    names += ["eta|eta| atp", "eta|eta| wta"]
    miss = ~np.isfinite(xb)
    if miss.any() and not miss.all():
        parts.append(miss.astype(float)[:, None] * e[:, None])
        names += ["miss x eta"]
    return xb, np.column_stack(parts), names


def main() -> int:
    warnings.simplefilter("ignore")
    P = panel(max_season=C.REPLICATION[-1])
    F = S.load(with_model=True)
    pos = pd.Series(np.arange(len(P)), index=P["match_id"].astype(str)).reindex(F["match_id"]).to_numpy().astype(int)
    r = i084_inputs(P.drop(columns=["a_won"]))
    want = pd.read_csv(C.ROOT / "data/studies/feature_interactions/hypotheses/screen_results.csv")
    want = want[want["hid"] == "I-084"].set_index("base")
    out = {}
    for base in ("model", "market"):
        e = F[f"z_{base}"].to_numpy(float)
        xb, Cb, names = assemble(F, r, pos, e)
        h = S.Hypothesis("I-084", xb, Cb, names, "+", 0.5, "slow")
        res = S.run(F, h, base=base, n_p1=200 if base == "model" else 0, n_p2=0, sizes=True)
        keep = ["b1", "se1", "z1", "b2", "se2", "z2", "widen", "z1_adj", "z2_adj", "z_joint", "gain_disc_both",
                "lo_disc_both", "hi_disc_both", "gain_repl_both", "lo_repl_both", "hi_repl_both"]
        got = {k: float(res[k]) for k in keep if k in res}
        ref = {k: float(want.loc[base, k]) for k in keep if k in want.columns}
        out[base] = {"reproduced": got, "screen": ref, "controls": names,
                     "max_abs_diff_z": float(max(abs(got[k] - ref[k]) for k in ("z1", "z2", "z_joint")))}
        C.log(f"{base}: z1 {got['z1']:+.4f} (screen {ref['z1']:+.4f}), z2 {got['z2']:+.4f} ({ref['z2']:+.4f}), "
              f"joint {got['z_joint']:+.4f} ({ref['z_joint']:+.4f})")
    C.OUT.mkdir(parents=True, exist_ok=True)
    C.write_json(C.OUT / "reproduce.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
