"""Diagnostics of the surface-IOS inputs on the model's own rows (main tour with closing odds, 2013-2026), all before any
TabPFN fit and none on the test seasons' results:

    movement     how far the surface model's effective inputs (iosO, iosD, prod on the match's surface) move from today's:
                 correlation and the SD of the change in units of the input's SD, by tour and surface
    deviations   the size of the surface deviations (E_A - E_B, F_A - F_B) by tour and surface, and their correlation
                 with the odds, Elo and today's IOS inputs
    priced?      given the closing price, do the surface terms predict the winner? Logistic fits per tour on 2013-2018
                 only (2019-2021 are kept untouched for the TabPFN validation that chooses the representation): the
                 price's log-odds plus a block of surface inputs, cluster-robust z by four-week block, and the
                 in-sample log-loss gain; and the same fitted on 2013-2016 and scored on 2017-2018 (milli-log-loss,
                 positive = the block helps). The men's 2018 season has no odds.

Writes data/studies/surface_ios/diagnostics.json and diagnostics_*.csv.
Run: ./python.sh src/eda/surface_ios/diagnostics.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit, logit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios.arms import recipe  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

SURF = {0: "Hard", 1: "Clay", 2: "Grass", 3: "Carpet"}      # the frame's surface code (in_surface)
RETURN_FIRST = ("spw", "hold", "first_won", "ace", "second_won", "bp_saved", "df", "first_in")


def cluster_z(Z: np.ndarray, y: np.ndarray, beta: np.ndarray, blocks: np.ndarray) -> np.ndarray:
    p = expit(Z @ beta)
    H = (Z.T * (p * (1 - p))) @ Z
    Hinv = np.linalg.pinv(H)
    s = Z * (y - p)[:, None]
    labels, ix = np.unique(blocks, return_inverse=True)
    S = np.zeros((len(labels), Z.shape[1]))
    np.add.at(S, ix, s)
    V = Hinv @ (S.T @ S) @ Hinv
    return beta / np.sqrt(np.maximum(np.diag(V), 1e-300))


def main() -> int:
    base = pd.read_parquet(C.OUT / "base_frame.parquet")
    sf = pd.read_parquet(C.OUT / "surface_features.parquet")
    sf = base[["match_id"]].merge(sf, on="match_id", how="left", validate="one_to_one")
    surf = base["in_surface"].map(SURF).to_numpy()
    tour = base["tour"].to_numpy()
    out = {"movement": [], "deviations": [], "priced": []}

    for s in C.PROFILE_IOS:
        for kind, cur in (("iosO", "curO"), ("iosD", "curD"), ("prod", "curprod")):
            new, old = recipe(f"{kind}_{s}", sf), recipe(f"{cur}_{s}", sf)
            for t in ("atp", "wta"):
                for sname in ("Hard", "Clay", "Grass"):
                    m = (tour == t) & (surf == sname) & np.isfinite(new) & np.isfinite(old)
                    if m.sum() < 100:
                        continue
                    sd = np.std(old[m])
                    out["movement"].append({"input": f"{kind}_{s}", "tour": t, "surface": sname, "rows": int(m.sum()),
                                            "corr": float(np.corrcoef(new[m], old[m])[0, 1]),
                                            "sd_change_over_sd": float(np.std(new[m] - old[m]) / sd) if sd else np.nan})
    others = {"odds_logit": base["in_odds_logit"].to_numpy(), "elo_logit": base["in_elo_logit"].to_numpy()}
    for s in C.STATS:
        for kind in ("sdevO", "sdevD"):
            v = recipe(f"{kind}_{s}", sf)
            for t in ("atp", "wta"):
                for sname in ("Hard", "Clay", "Grass"):
                    m = (tour == t) & (surf == sname) & np.isfinite(v)
                    if m.sum() < 100:
                        continue
                    rec = {"input": f"{kind}_{s}", "tour": t, "surface": sname, "rows": int(m.sum()),
                           "sd": float(np.std(v[m]))}
                    if s in C.PROFILE_IOS:
                        lvl = recipe(f"{'curO' if kind == 'sdevO' else 'curD'}_{s}", sf)
                        rec["sd_today_input"] = float(np.std(lvl[m]))
                        rec["corr_today_input"] = float(np.corrcoef(v[m], lvl[m])[0, 1])
                    for k, o in others.items():
                        mm = m & np.isfinite(o)
                        rec[f"corr_{k}"] = float(np.corrcoef(v[mm], o[mm])[0, 1])
                    out["deviations"].append(rec)

    # priced? the closing price plus a block of surface inputs, per tour, training seasons only
    blocks4 = T.blocks(base["tournament_date"].to_numpy(), 28)
    z_mkt = logit(np.clip(base["p_mkt"].to_numpy(dtype=float), T.EPS, 1 - T.EPS))
    y_all = base["a_won"].to_numpy().astype(float)
    year = base["year"].to_numpy()
    sets = {"return deviations (sdevD: spw, hold, first_won, ace)": [f"sdevD_{s}" for s in ("spw", "hold", "first_won", "ace")],
            "all deviations (sdevO, sdevD: 8 statistics)": [f"{k}_{s}" for s in C.STATS for k in ("sdevO", "sdevD")],
            "effective minus today (21 IOS inputs)": [f"{k}_{s}" for s in C.PROFILE_IOS for k in ("iosO", "iosD", "prod")]}
    for label, names in sets.items():
        X = np.column_stack([recipe(n, sf) - (recipe(n.replace("ios", "cur").replace("prod_", "curprod_"), sf)
                                              if label.startswith("effective") else 0.0) for n in names])
        for t in ("atp", "wta"):
            for fit_years, score_years in (((2013, 2018), (2013, 2018)), ((2013, 2016), (2017, 2018))):
                fit = (tour == t) & (year >= fit_years[0]) & (year <= fit_years[1]) & np.isfinite(z_mkt)
                sc = (tour == t) & (year >= score_years[0]) & (year <= score_years[1]) & np.isfinite(z_mkt)
                Xf = np.nan_to_num(X)
                sd = Xf[fit].std(axis=0)
                sd[sd == 0] = 1.0
                Z = np.column_stack([z_mkt, Xf / sd])
                b0, _ = T.fit_logistic(z_mkt[fit][:, None], y_all[fit])
                b1, _ = T.fit_logistic(Z[fit], y_all[fit])
                ll0 = T.ll(expit(b0[0] * z_mkt[sc]), y_all[sc])
                ll1 = T.ll(expit(Z[sc] @ b1), y_all[sc])
                c = T.compare(ll0, ll1, base["tournament_date"].to_numpy()[sc])
                rec = {"block": label, "tour": t, "fit": f"{fit_years[0]}-{fit_years[1]}",
                       "scored": f"{score_years[0]}-{score_years[1]}", "matches": c["n"], "gain": c["gain"],
                       "lo": c["lo"], "hi": c["hi"]}
                if fit_years == score_years:
                    zs = cluster_z(Z[fit], y_all[fit], b1, blocks4[fit])
                    rec["max_abs_z"] = float(np.max(np.abs(zs[1:])))
                    rec["z"] = {n: float(v) for n, v in zip(names, zs[1:])}
                out["priced"].append(rec)
    C.jdump(out, C.OUT / "diagnostics.json")
    for k in ("movement", "deviations"):
        pd.DataFrame(out[k]).to_csv(C.OUT / f"diagnostics_{k}.csv", index=False)
    pr = pd.DataFrame([{k: v for k, v in r.items() if k != "z"} for r in out["priced"]])
    pr.to_csv(C.OUT / "diagnostics_priced.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_rows", 400):
        mv = pd.DataFrame(out["movement"])
        print(mv.pivot_table(index=["input"], columns=["tour", "surface"], values="corr").round(3).to_string())
        print(pd.DataFrame(out["deviations"]).round(3).to_string(index=False))
        print(pr.round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
