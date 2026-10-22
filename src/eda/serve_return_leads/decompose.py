"""Cleaner serve/return versions, and what carries "serving over-rated, returning under-rated" (seen matches only).

Candidates (men, A - B, each oriented before reading; + = the registered direction holds):
    SP    point-level serving: the surface-effective IOS offence on serve points won (srf_O_eff_spw), (-)
          [the model has no serve-points-won input: it has first in, first won, second won separately]
    RP    point-level returning: the surface-effective IOS defence on serve points won (srf_D_eff_spw), (+)
    ST    the balance: (O_spw - D_spw)_A - (O_spw - D_spw)_B = SP - RP, (-): "serving per se is over-rated"
    TOT   point-level strength SP + RP, read two-sided (a control: the close should price it)
    HX    the hold rating's excess over point-level serving: iosO_hold minus its least-squares projection on SP (by
          tour, no intercept, fitted on the window's rows: outcome-free), (-): the game-level part of serving
    BX    the same for iosO_bp_saved, (-)
    RX    the return-hold excess: iosD_hold minus its projection on RP, (+)
    luck  unpriced leads' luck builder (break points and holds beyond the match's own point rates, 91-day half-life,
          and the 365-day half-life variants): PS03_hold (-), PS03_save (-), PS03_break (-), PS03_conv (-),
          PS03_net (-); PS03_hold_h365 (-), PS03_save_h365 (-)
Readings through readings.read (raw and orth; beyond the close and beyond the model; eras, 2013-24, 2020-24, 2025-26).
Joint fits (beyond the close): [SP, HX, BX, RP, RX, T2] and [SP, RP, PS03_hold, PS03_save] in 2025-26 and 2013-24.
The surface features come from data/studies/surface_ios/surface_features.parquet (older tables than the 10 Oct
instance; their A - B equal the frame's IOS inputs to r 0.996-0.999), so this is a diagnostic, not the registered build.

Writes data/studies/serve_return_leads/decompose_single.csv, decompose_joint.csv, decompose_corr.csv.
Run: ./python.sh src/eda/serve_return_leads/decompose.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_return_leads import common as C  # noqa: E402
from src.eda.serve_return_leads import readings as R  # noqa: E402

SURF = ROOT / "data" / "studies" / "surface_ios" / "surface_features.parquet"
LUCK = ROOT / "data" / "studies" / "unpriced_leads" / "candidates" / "luck" / "values.parquet"
LUCK_COLS = {"PS03_hold": -1, "PS03_save": -1, "PS03_break": -1, "PS03_conv": -1, "PS03_net": -1,
             "PS03_hold_h365": -1, "PS03_save_h365": -1}


def resid_on(y: np.ndarray, x: np.ndarray, frame: pd.DataFrame) -> np.ndarray:
    """y minus its projection on x, by window-agnostic tour fit on all rows given (outcome-free)."""
    y, x = np.nan_to_num(y), np.nan_to_num(x)
    b = float(np.dot(x, y) / np.dot(x, x)) if np.dot(x, x) > 0 else 0.0
    return y - b * x


def candidates(f: pd.DataFrame) -> tuple[dict, dict]:
    s = pd.read_parquet(SURF, columns=["match_id", "srf_O_eff_spw_a", "srf_O_eff_spw_b", "srf_D_eff_spw_a",
                                       "srf_D_eff_spw_b"]).astype({"match_id": str})
    s = s.drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
    SP = s["srf_O_eff_spw_a"].to_numpy(float) - s["srf_O_eff_spw_b"].to_numpy(float)
    RP = s["srf_D_eff_spw_a"].to_numpy(float) - s["srf_D_eff_spw_b"].to_numpy(float)
    c = {"SP": SP, "RP": RP, "ST": SP - RP, "TOT": SP + RP}
    sign = {"SP": -1, "RP": +1, "ST": -1, "TOT": +1}
    # the excesses: residualised within each window by read()? No: one projection over all seen men's rows here
    # (outcome-free); read()'s orth form re-projects on the model's inputs anyway
    c["HX"] = resid_on(f["in_iosO_hold"].to_numpy(float), SP, f)
    c["BX"] = resid_on(f["in_iosO_bp_saved"].to_numpy(float), SP, f)
    c["RX"] = resid_on(f["in_iosD_hold"].to_numpy(float), RP, f)
    sign.update({"HX": -1, "BX": -1, "RX": +1})
    lk = pd.read_parquet(LUCK, columns=["match_id"] + list(LUCK_COLS)).astype({"match_id": str})
    lk = lk.drop_duplicates("match_id").set_index("match_id").reindex(f["match_id"])
    for k, sg in LUCK_COLS.items():
        c[k] = lk[k].to_numpy(float)
        sign[k] = sg
    return c, sign


def main() -> int:
    f = R.seen_frame("atp")
    sc = C.scales(f)
    sco = C.scores(f, sc)
    c, sign = candidates(f)
    # outcome-free: coverage and correlations with the locked traits (A - B, men, all seen rows)
    corr = {}
    for k, v in c.items():
        ok = np.isfinite(v)
        corr[k] = {"present": float(np.mean(ok & (np.nan_to_num(v) != 0)))}
        for t in ("T1", "T2", "T3", "R0"):
            corr[k][t] = float(np.corrcoef(np.nan_to_num(v)[ok], sco[t][ok])[0, 1]) * sign[k]
        for col in ("iosO_hold", "iosO_bp_saved", "form_bp_saved", "iosD_first_won", "iosD_hold"):
            x = f[f"in_{col}"].to_numpy(float)
            m = ok & np.isfinite(x)
            corr[k][col] = float(np.corrcoef(np.nan_to_num(v)[m], x[m])[0, 1])
    pd.DataFrame(corr).T.to_csv(C.OUT / "decompose_corr.csv")
    rows = [R.read(f, sco[t], t, +1) for t in ("R0", "T1", "T2", "T3")]
    for k, v in c.items():
        rows.append(R.read(f, v, k, sign[k]))
    single = pd.concat(rows, ignore_index=True)
    single.to_csv(C.OUT / "decompose_single.csv", index=False)
    joint = []
    sets = {"serving split": ["SP", "HX", "BX", "RP", "RX"],
            "points vs luck": ["SP", "RP", "PS03_hold", "PS03_save"],
            "balance vs strength": ["ST", "TOT"],
            "locked traits": ["T1", "T2", "T3"]}
    for wname, (a, b) in {"2025-26": (2025, 2026), "2013-24": (2013, 2024), "2020-24": (2020, 2024)}.items():
        m = f["season"].between(a, b).to_numpy()
        g = f[m].reset_index(drop=True)
        for sname, names in sets.items():
            cols = []
            for n in names:
                v = sco[n] if n in sco else c[n] * sign[n]
                cols.append(np.asarray(v, float)[m])
            for base in ("L", "L_model"):
                if not np.isfinite(g[base].to_numpy(float)).any():
                    continue
                j = R.fit_joint(g, np.column_stack(cols), base=base, names=names)
                j["set"], j["window"], j["base"] = sname, wname, base
                joint.append(j)
    joint = pd.concat(joint, ignore_index=True)
    joint.to_csv(C.OUT / "decompose_joint.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_rows", 400)
    print(pd.DataFrame(corr).T.round(2).to_string())
    piv = single[(single["form"] == "raw")].pivot_table(index=["candidate", "base"], columns="window", values="z")
    print(piv[["2013-16", "2017-19", "2020-22", "2023-24", "2013-24", "2020-24", "2025-26"]].round(2).to_string())
    piv = single[(single["form"] == "orth") & (single["base"] == "L")].pivot_table(index="candidate", columns="window",
                                                                                 values="z")
    print("orth, beyond the close")
    print(piv[["2013-16", "2017-19", "2020-22", "2023-24", "2013-24", "2020-24", "2025-26"]].round(2).to_string())
    print(joint[["window", "set", "base", "score", "beta", "z"]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
