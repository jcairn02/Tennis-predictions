"""R5 report check (auditor): the scale of the R2 gate's coefficients. auditor_gate2.py reported pp per SD of a single
player's f_hat over the regression rows; the README calls it "per unit" (one unit of spd_f = 2.224 km/h of the A - B
difference). This prints that SD (km/h) on the same rows (men 2022-2023, seasons <= 2023 only), so the report can state
the unit. Values only: the row set needs the box-score controls to exist (statistic histories <= 2023), and no target
or result is related to anything here.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_r5_gate_sd.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import auditor_lib as AL  # noqa: E402
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402


def main() -> None:
    from src.eda.serve_speed_tabpfn.design import modeller_gate as MG
    p = AL.panel("ks_first")
    tour = "atp"
    snaps = {tour: AL.Snapshots(p[p["tour"] == tour].reset_index(drop=True))}
    b = MG.box_history((2013, 2023), tour)
    tg = b[b["year"].between(2022, 2023) & b["level"].isin(("GS", "T1000", "T500", "T250", "FIN", "CH"))]
    for s, (n, d) in MG.STATS.items():
        tg = tg[tg[d] > 0]
    tg = tg.reset_index(drop=True)
    tg["tour"] = tour
    tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es"])
    tg = tg.merge(tm, on="match_id", how="left")
    tg = tg[tg["es"].notna()].reset_index(drop=True)
    h = AL.histories(p, tg)
    Z = AL.centred_values(p, tg, h, "asof", snaps=snaps)
    kf = AL.kalman_batch(Z, AL.noise(p, h, AL.MEN), AL.days_matrix(p, h), tg["es"].to_numpy(float), dict(AL.MEN))
    orates = MG.own_rates(b, tg)
    tg = tg.join(orates)
    opp_cols = [c for c in tg.columns if c.startswith("c52_")]
    oppv = tg[["match_id", "player_id"] + opp_cols].rename(columns={"player_id": "opponent_id"})
    tg = tg.merge(oppv, on=["match_id", "opponent_id"], how="left", suffixes=("", "_opp"))
    for s, (n, d) in MG.STATS.items():
        r52 = (tg[f"s52_{n}"] / tg[f"s52_{d}"]).to_numpy(float)
        rew = (tg[f"ew_{n}"] / tg[f"ew_{d}"]).to_numpy(float)
        oc = (tg[f"c52_{n}_opp"] / tg[f"c52_{d}_opp"]).to_numpy(float)
        ok = np.isfinite(r52) & np.isfinite(rew) & np.isfinite(oc) & np.isfinite(kf["L_hat"])
        print(f"{s}: rows {int(ok.sum())}, SD of a player's f_hat {float(np.std(kf['f_hat'][ok])):.3f} km/h")


if __name__ == "__main__":
    main()
