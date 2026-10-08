"""Design R2 (auditor): f_hat against the registered window statistic on the result-free mechanism gate, like for like.
Men 2022-2023 (tour + Challengers + Slams), women Slams 2016-2023; statistic targets of one player per row (aces per
serve point, first-serve points won per first serve in, serve points won per serve point); never an A - B difference
and never a match result. As-of edition centring (the auditor's ruling), the modeller's constants.

Features (standardised on the regression rows):
    f_hat      Kalman posterior mean of the fast state (0 without history)
    x_win      registered window on as-of-centred speeds: 14-day mean - 364-day mean (0 where no 14-day row, plus a
               missing flag)
    x_raw      the same on raw speeds (the registered x_raw, plus a missing flag)
Rows: all; and the rows where the window exists (k14 >= 1), where both features are informative.
Controls: the modeller's (own 364-day and two-week box-score rate, L_hat, the opponent's conceded rate) with target-
edition fixed effects; 95% intervals clustered by 28-day blocks. Joint fits put f_hat and x_win in one regression.

Run: ./python.sh src/eda/serve_speed_tabpfn/design/auditor_gate2.py
Writes data/studies/serve_speed_tabpfn/design/auditor_gate2.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn.design import auditor_centring as AC  # noqa: E402
from src.eda.serve_speed_tabpfn.design import auditor_lib as AL  # noqa: E402
from src.eda.serve_speed_tabpfn.design import engineer_common as EC  # noqa: E402

OUT = AL.OUT / "auditor_gate2.json"
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


def main() -> None:
    from src.eda.serve_speed_tabpfn.design import modeller_gate as MG
    p = AL.panel("ks_first")
    res = {"reads_results": False}
    for tour in ("atp", "wta"):
        snaps = {tour: AL.Snapshots(p[p["tour"] == tour].reset_index(drop=True))}
        years, levels = ((2022, 2023), ("GS", "T1000", "T500", "T250", "FIN", "CH")) if tour == "atp" else \
            ((2016, 2023), ("GS",))
        b = MG.box_history((2013, 2023), tour)
        tg = b[b["year"].between(*years) & b["level"].isin(levels)].reset_index(drop=True)
        for s, (n, d) in MG.STATS.items():
            tg = tg[tg[d] > 0]
        tg = tg.reset_index(drop=True)
        tg["tour"] = tour
        tm = pd.read_parquet(EC.TIMING, columns=["match_id", "es"])
        tg = tg.merge(tm, on="match_id", how="left")
        tg = tg[tg["es"].notna()].reset_index(drop=True)
        h = AL.histories(p, tg)
        tday = tg["es"].to_numpy(float)
        base = AL.MEN if tour == "atp" else AL.WOMEN_MENDYN
        R, D = AL.noise(p, h, base), AL.days_matrix(p, h)
        Za = AL.centred_values(p, tg, h, "asof", snaps=snaps)
        Zr = AL.centred_values(p, tg, h, "raw")
        kf = AL.kalman_batch(Za, R, D, tday, dict(base))
        wa, wr = AL.window_means(Za, h, p, tday), AL.window_means(Zr, h, p, tday)
        feats = {"f_hat": kf["f_hat"], "x_win": wa["x"], "x_raw": wr["x"]}
        L_hat = kf["L_hat"]
        orates = MG.own_rates(b, tg)
        tg = tg.join(orates)
        opp_cols = [c for c in tg.columns if c.startswith("c52_")]
        oppv = tg[["match_id", "player_id"] + opp_cols].rename(columns={"player_id": "opponent_id"})
        tg = tg.merge(oppv, on=["match_id", "opponent_id"], how="left", suffixes=("", "_opp"))
        tg["block"] = (tg["obs"] // 28).astype(int)
        tg["edition"] = tg["tournament_id"].astype(str) + "|" + tg["qualifying"].astype(str)
        out = {}
        for s, (n, d) in MG.STATS.items():
            yv = (tg[n] / tg[d]).to_numpy(float)
            r52 = (tg[f"s52_{n}"] / tg[f"s52_{d}"]).to_numpy(float)
            rew = (tg[f"ew_{n}"] / tg[f"ew_{d}"]).to_numpy(float)
            oc = (tg[f"c52_{n}_opp"] / tg[f"c52_{d}_opp"]).to_numpy(float)
            w = tg[d].to_numpy(float)
            ok = np.isfinite(r52) & np.isfinite(rew) & np.isfinite(oc) & np.isfinite(L_hat) & np.isfinite(yv)
            for subset, m in (("all", ok), ("window_exists", ok & (h["k14"] >= 1)),
                              ("window_exists_earlier_events_only", ok & (h["k14"] >= 1) & ~h["same_event"])):
                g = np.flatnonzero(m)
                ctrl = np.column_stack([r52[g], rew[g], oc[g], L_hat[g]])
                row = {"rows": int(len(g))}
                for fname in ("f_hat", "x_win", "x_raw"):
                    F = np.nan_to_num(feats[fname][g])
                    miss = np.isnan(feats[fname][g]).astype(float)
                    X = np.column_stack([F / F.std(), ctrl] + ([miss] if miss.std() > 0 else []))
                    beta, se = AC.wls_fe(yv[g], X, w[g], tg.loc[g, "edition"].to_numpy(), tg.loc[g, "block"].to_numpy(),
                                         True)
                    row[fname] = {"pp_per_sd": 100 * beta[0], "lo": 100 * (beta[0] - 1.96 * se[0]),
                                  "hi": 100 * (beta[0] + 1.96 * se[0])}
                F1 = feats["f_hat"][g]
                F2 = np.nan_to_num(feats["x_win"][g])
                miss = np.isnan(feats["x_win"][g]).astype(float)
                X = np.column_stack([F1 / F1.std(), F2 / F2.std(), ctrl] + ([miss] if miss.std() > 0 else []))
                beta, se = AC.wls_fe(yv[g], X, w[g], tg.loc[g, "edition"].to_numpy(), tg.loc[g, "block"].to_numpy(), True)
                row["joint"] = {"f_hat": {"pp_per_sd": 100 * beta[0], "lo": 100 * (beta[0] - 1.96 * se[0]),
                                          "hi": 100 * (beta[0] + 1.96 * se[0])},
                                "x_win": {"pp_per_sd": 100 * beta[1], "lo": 100 * (beta[1] - 1.96 * se[1]),
                                          "hi": 100 * (beta[1] + 1.96 * se[1])}}
                row["corr_f_x_win"] = float(np.corrcoef(F1, F2)[0, 1])
                out[f"{s}|{subset}"] = row
                log(f"{tour} {s} {subset}: rows {len(g)}; " + "; ".join(
                    f"{k} {row[k]['pp_per_sd']:+.2f} [{row[k]['lo']:+.2f}, {row[k]['hi']:+.2f}]"
                    for k in ("f_hat", "x_win", "x_raw")) + f"; joint f {row['joint']['f_hat']['pp_per_sd']:+.2f} "
                    f"[{row['joint']['f_hat']['lo']:+.2f}, {row['joint']['f_hat']['hi']:+.2f}] x "
                    f"{row['joint']['x_win']['pp_per_sd']:+.2f} [{row['joint']['x_win']['lo']:+.2f}, "
                    f"{row['joint']['x_win']['hi']:+.2f}]")
        res[tour] = out
    res["key"] = ("pp of the rate per SD of the feature, beyond the controls and target-edition fixed effects; positive"
                  " = a player serving faster than his norm serves better; 95% intervals clustered by 28-day blocks; "
                  "a tie when the interval spans 0")
    OUT.write_text(json.dumps(AC.jsonable(res), indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
