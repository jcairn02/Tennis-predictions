"""Role E (red team), CP2: re-derive dev readings from the fits with compare.py's own functions, and decompose the
intervals into their block and seed parts.

Readings (men, dev 2020-2024, both stages and stage 1, seed term paired by seed):
  SYS against REF; SYS_w100 against SYS (one challenger pair); the first run's FP against REF (for the width's yardstick)
For each: the estimate and SE as compare.py builds them, the block SE, the seed term (variance over seeds of the
per-seed loss difference / 4), and each seed's own difference. Results of seasons <= 2024 only (compare.outcomes'
filtered read). Writes audit/cp2/rederive.json.
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

OUT = Path(__file__).resolve().parents[1] / "cp2"
OUT.mkdir(exist_ok=True)
ARMS = ROOT / "data/studies/lower_level_evidence/system/arms"
FP = ROOT / "data/studies/lower_level_evidence/candidates/FP"
THROUGH = 2024
test = tuple(range(CMP.SCORE_FROM, THROUGH + 1))
seasons = tuple(range(CMP.FIT_FROM, THROUGH + 1))


def model(folder):
    name, P, _ = CMP.candidate(str(folder))
    return name, P


def load(P_ref, P_c):
    ref, cand = CMP.inputs_frame(P_ref), CMP.inputs_frame(P_c)
    info = CMP.scoring_info(ref, cand, CMP.outcomes(P_ref, THROUGH), CMP.outcomes(P_c, THROUGH), THROUGH)
    assert info["season"].max() <= THROUGH
    p_ref = CMP.seed_table(P_ref, ref, seasons).reindex(info.index)
    p_c = CMP.seed_table(P_c, cand, seasons).reindex(info.index)
    return info, p_ref, p_c


def fc(p, info, z, ids, stage2=True):
    eta = pd.Series(CMP.C.lg(p.mean(axis=1).to_numpy()), index=p.index)
    par = CMP.walk_forward(eta, info, z if stage2 else None, test)
    return CMP.forecasts(p, info, par, z if stage2 else None, ids)


def reading(info, ids, base, arm):
    y = info.loc[ids, "y"].to_numpy(float)
    (qb, qbk), (qa, qak) = base, arm
    sb, sa = S.seed_loss(qbk, y), S.seed_loss(qak, y)
    r = S.paired_stats(CMP.C.ll(qb, y), CMP.C.ll(qa, y), sb, sa, info.loc[ids, "block"].to_numpy(),
                       info.loc[ids, "week"].to_numpy(), matched_seeds=True)
    per_seed = (sb - sa).tolist()            # each seed's own gain (1000 x mean loss difference), + = arm better
    d = 1000 * (CMP.C.ll(qb, y) - CMP.C.ll(qa, y))
    return {"estimate": r["estimate"], "lo": r["lo"], "hi": r["hi"], "se": r["se"], "se_block": r["se_block"],
            "seed_sd_of_mean": float(np.sqrt(r["v_seed"])), "blocks": r["blocks"], "per_seed_gain": per_seed,
            "per_match_sd": float(d.std()), "mean_abs_forecast_change": float(np.mean(np.abs(qa - qb))),
            "seed_spread_base": float(np.std(sb, ddof=1)), "seed_spread_arm": float(np.std(sa, ddof=1))}


res = {}
P_ref = R.paths("reference")
z_ref = R.speed_column("reference")
for label, folder, base_folder in (("SYS vs REF", ARMS / "SYS", None), ("FP vs REF (first run)", FP, None),
                                   ("SYS_w100 vs SYS", ARMS / "SYS_w100", ARMS / "SYS")):
    _, P_c = model(folder)
    if base_folder is None:
        info, p_b, p_a = load(P_ref, P_c)
    else:
        _, P_b = model(base_folder)
        info, p_b, p_a = load(P_b, P_c)
    men = info.index[~info["debut"].to_numpy() & info["season"].isin(test).to_numpy() & (info["tour"] == "atp").to_numpy()]
    out = {}
    for stage, s2 in (("both stages", True), ("stage 1", False)):
        out[stage] = reading(info, men, fc(p_b, info, z_ref, men, s2), fc(p_a, info, z_ref, men, s2))
    out["matches"] = int(len(men))
    res[label] = out
    print(label, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in out["both stages"].items()}))
(OUT / "rederive.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
