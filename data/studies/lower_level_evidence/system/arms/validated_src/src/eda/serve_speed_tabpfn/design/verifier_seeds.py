"""R4 test verifier: the structure of the base model's seed noise, from saved forecasts only (no match result is read).

Why. The synthetic worlds that test score.py need seed noise "of a realistic size". The scorer's own --synthetic mode
gives the new arm i.i.d. per-match noise and keeps the base's real seeds, so the base's seed noise never enters the
paired difference. This script measures the real noise of the 58-input base ("model", seeds 0-15, 2019-2026) so the
verifier's two-sided world (verifier_worlds.py) can give BOTH arms independent noise with the same structure:

    d_k = eta_k - eta_bar                     per match, seed k's symmetrised log-odds minus the 16-seed mean's
    temperature  tau_k = sum(d_k eta_bar) / sum(eta_bar^2) per (season, tour, seed): a seed-level scale change
    residual     r_k = d_k - tau_k eta_bar
    block share  the variance of four-week-block means of r_k against its i.i.d. value var(r) / n_block (design
                 effect; 1 = no within-block correlation)

Only forecasts (probabilities and ids) and the frame's tour / season / tournament_date are read.
Writes data/studies/serve_speed_tabpfn/design/verifier_seeds.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/verifier_seeds.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

OUT = C.OUT / "design" / "verifier_seeds.json"


def main() -> int:
    P = C.DEFAULT
    info = S.population(P)                                   # no outcome (explicit columns; see verifier_noread.py)
    bank = S.Bank(P, S.frame_index(P), require_checks=True)  # the reuse checks have passed (checks/*.json)
    rows, design = [], []
    for s in S.HIST:
        p = bank.per_seed("model", S.SEEDS16, (s,), "td")
        eta = C.lg(p.to_numpy())                             # per-seed log-odds
        bar = C.lg(p.mean(axis=1).to_numpy())                # the 16-seed mean's log-odds (scorer's eta)
        inf = info.reindex(p.index)
        for t in C.TOURS:
            m = (inf["tour"] == t).to_numpy()
            d = eta[m] - bar[m][:, None]
            e = bar[m]
            tau = (d * e[:, None]).sum(axis=0) / (e ** 2).sum()
            r = d - np.outer(e, tau)
            blk = inf["block"].to_numpy()[m]
            ub, ix = np.unique(blk, return_inverse=True)
            cnt = np.bincount(ix)
            de = []
            for k in range(r.shape[1]):
                means = np.bincount(ix, weights=r[:, k]) / cnt
                expect = np.var(r[:, k]) / cnt
                de.append(float(np.mean((means - r[:, k].mean()) ** 2) / np.mean(expect)))
            rows.append({"season": s, "tour": t, "matches": int(m.sum()),
                         "sd_across_seeds_rms": float(np.sqrt(np.mean(np.var(d, axis=1, ddof=1)))),
                         "tau_sd": float(np.std(tau, ddof=1)), "tau_mean": float(np.mean(tau)),
                         "share_var_temperature": float(1 - np.var(r) / np.var(d)),
                         "resid_rms": float(np.sqrt(np.mean(r ** 2))),
                         "block_design_effect_mean": float(np.mean(de)),
                         "mean_abs_eta": float(np.mean(np.abs(e))), "sd_eta": float(np.std(e))})
            # heteroscedasticity: residual RMS by |eta| tercile
            q = np.quantile(np.abs(e), [1 / 3, 2 / 3])
            band = np.digitize(np.abs(e), q)
            design.append({"season": s, "tour": t, **{f"resid_rms_abs_eta_tercile_{b}": float(np.sqrt(np.mean(r[band == b] ** 2)))
                                                      for b in range(3)}})
    t = pd.DataFrame(rows)
    out = {"what": "structure of the base model's seed noise (forecasts only; no match result read)",
           "by_season_tour": rows, "heteroscedasticity": design,
           "summary": {"sd_across_seeds_rms": float(np.sqrt(np.mean(t["sd_across_seeds_rms"] ** 2))),
                       "tau_sd_mean": float(t["tau_sd"].mean()),
                       "share_var_temperature_mean": float(t["share_var_temperature"].mean()),
                       "resid_rms": float(np.sqrt(np.mean(t["resid_rms"] ** 2))),
                       "block_design_effect_mean": float(t["block_design_effect_mean"].mean())}}
    C.write_json(OUT, out)
    with pd.option_context("display.width", 200):
        print(t.round(4).to_string(index=False))
        print(pd.DataFrame(design).round(4).to_string(index=False))
    print(out["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
