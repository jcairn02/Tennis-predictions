"""Role E (red team), CP3: re-derive the holdout's headline readings from the fits with compare.py's own functions, after
the unlock (holdout_unlock.json 56864fed..., 08:36:26 UTC), and probe the placebo's "better".

Readings (both stages, seeds paired; the 2026 speed rule "zero": a scored match without a speed value gets no stage-2
nudge, as system_pairs.py applies it):
  primary   SYS against REF, men, 2025-2026
  pooled    SYS_w0 against REF, men, 2020-2026 (and SYS against REF pooled)
  placebo   SYS_PLACEBO against REF, men and both tours, 2025-2026; and on dev 2020-2024 for contrast
For each: estimate, interval, SE, block SE, seed term, per-seed gains, per-season gains, the per-match SD, and for the
placebo the calibration of REF's forecasts on 2025-2026 (slope of y on REF's logit) and how much the placebo shrinks
REF's logits. Writes audit/cp3/rederive.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "cp3"
OUT.mkdir(exist_ok=True)
ARMS = ROOT / "data/studies/lower_level_evidence/system/arms"
D_ARMS = ROOT / "data/studies/lower_level_evidence/system/results/arms"
THROUGH = 2026
seasons = tuple(range(CMP.FIT_FROM, THROUGH + 1))
P_ref = R.paths("reference")
z_raw = R.speed_column("reference")


def load(folder):
    _, P_c, _ = CMP.candidate(str(folder))
    ref, cand = CMP.inputs_frame(P_ref), CMP.inputs_frame(P_c)
    info = CMP.scoring_info(ref, cand, CMP.outcomes(P_ref, THROUGH), CMP.outcomes(P_c, THROUGH), THROUGH)
    p_ref = CMP.seed_table(P_ref, ref, seasons).reindex(info.index)
    p_c = CMP.seed_table(P_c, cand, seasons).reindex(info.index)
    assert not p_ref.isna().any().any() and not p_c.isna().any().any()
    return info, p_ref, p_c


def fc(p, info, z, ids, test):
    eta = pd.Series(CMP.C.lg(p.mean(axis=1).to_numpy()), index=p.index)
    par = CMP.walk_forward(eta, info, z, test)
    return CMP.forecasts(p, info, par, z, ids)


def reading(info, ids, base, arm):
    y = info.loc[ids, "y"].to_numpy(float)
    (qb, qbk), (qa, qak) = base, arm
    sb, sa = S.seed_loss(qbk, y), S.seed_loss(qak, y)
    r = S.paired_stats(CMP.C.ll(qb, y), CMP.C.ll(qa, y), sb, sa, info.loc[ids, "block"].to_numpy(),
                       info.loc[ids, "week"].to_numpy(), matched_seeds=True)
    d = 1000 * (CMP.C.ll(qb, y) - CMP.C.ll(qa, y))
    seas = info.loc[ids, "season"].to_numpy()
    by_season = {int(s): float(d[seas == s].mean()) for s in np.unique(seas)}
    lb, la = CMP.C.lg(qb), CMP.C.lg(qa)
    # calibration of each forecast on these matches: slope of y on its logit (1 = calibrated; < 1 = overconfident)
    cal = {}
    for name, l in (("base", lb), ("arm", la)):
        beta, _ = CMP.C.fit_logistic(l[:, None], y)
        cal[name] = float(beta[0])
    shrink = float(np.polyfit(lb, la, 1)[0])          # slope of the arm's logit on the base's
    return {"matches": int(len(ids)), "estimate": r["estimate"], "lo": r["lo"], "hi": r["hi"], "se": r["se"],
            "se_block": r["se_block"], "seed_sd_of_mean": float(np.sqrt(r["v_seed"])), "blocks": r["blocks"],
            "per_seed_gain": (sb - sa).tolist(), "by_season": by_season, "per_match_sd": float(d.std()),
            "mean_abs_logit_base": float(np.abs(lb).mean()), "mean_abs_logit_arm": float(np.abs(la).mean()),
            "calibration_slope": cal, "arm_logit_on_base_logit": shrink}


res = {}
jobs = (("SYS", ARMS / "SYS"), ("SYS_w0", ARMS / "SYS_w0"), ("SYS_PLACEBO", D_ARMS / "SYS_PLACEBO"))
for name, folder in jobs:
    info, p_ref, p_c = load(folder)
    z = z_raw.reindex(info.index).fillna(0.0)        # the 2026 speed rule "zero" (no gap before 2026)
    keep = ~info["debut"].to_numpy()
    men = (info["tour"] == "atp").to_numpy()
    sea = info["season"].to_numpy()
    out = {}
    for label, test, mask in (("holdout men", (2025, 2026), keep & men & np.isin(sea, [2025, 2026])),
                              ("holdout both tours", (2025, 2026), keep & np.isin(sea, [2025, 2026])),
                              ("pooled men 2020-2026", tuple(range(2020, 2027)), keep & men & (sea >= 2020)),
                              ("dev men 2020-2024", tuple(range(2020, 2025)), keep & men & (sea >= 2020) & (sea <= 2024))):
        ids = info.index[mask]
        out[label] = reading(info, ids, fc(p_ref, info, z, ids, test), fc(p_c, info, z, ids, test))
    res[f"{name} vs REF"] = out
    print(name, {k: (round(v["estimate"], 4), round(v["lo"], 4), round(v["hi"], 4), round(v["se"], 4),
                     round(v["se_block"], 4), round(v["seed_sd_of_mean"], 4)) for k, v in out.items()}, flush=True)
(OUT / "rederive.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
