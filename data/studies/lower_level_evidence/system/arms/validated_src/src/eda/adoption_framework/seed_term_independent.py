"""Review check (read-only): for arms with DIFFERENT fits (the frozen previous model against the reference), how much
of compare.py's interval is the seed term, and is the per-seed noise correlated across arms (same seed indices)?
Results of seasons <= 2024 only. Writes nothing in the repo. Run from the repo root: ./python.sh <this file>
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, t as student_t

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as K  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

THROUGH = 2024
P_ref, P_prev = R.paths("reference"), R.paths("previous")
ref, prev = K.inputs_frame(P_ref), K.inputs_frame(P_prev)
info = K.scoring_info(ref, prev, K.outcomes(P_ref, THROUGH), K.outcomes(P_prev, THROUGH), THROUGH)
seasons = tuple(range(K.FIT_FROM, THROUGH + 1))
test = tuple(range(K.SCORE_FROM, THROUGH + 1))
p_ref = K.seed_table(P_ref, ref, seasons).reindex(info.index)
p_prev = K.seed_table(P_prev, prev, seasons).reindex(info.index)
z_ref, z_prev = R.speed_column("reference"), R.speed_column("previous")
pr = K.walk_forward(pd.Series(C.lg(p_ref.mean(axis=1).to_numpy()), index=p_ref.index), info, z_ref, test)
pp = K.walk_forward(pd.Series(C.lg(p_prev.mean(axis=1).to_numpy()), index=p_prev.index), info, z_prev, test)

for _g, name, mask in K.populations(info, test)[:3]:
    ids = info.index[mask]
    yy = info.loc[ids, "y"].to_numpy(float)
    (qb, qbk), (qa, qak) = K.forecasts(p_ref, info, pr, z_ref, ids), K.forecasts(p_prev, info, pp, z_prev, ids)
    sb, sa = S.seed_loss(qbk, yy), S.seed_loss(qak, yy)
    r = S.paired_stats(C.ll(qb, yy), C.ll(qa, yy), sb, sa, info.loc[ids, "block"].to_numpy(), info.loc[ids, "week"].to_numpy())
    v_paired = float(np.var(sb - sa, ddof=1) / len(sb))
    corr = float(np.corrcoef(sb, sa)[0, 1])
    se_p = np.sqrt(r["se_block"] ** 2 + v_paired)
    tq = student_t.ppf(0.975, r["blocks"] - 1)
    g = r["estimate"]
    print(f"previous vs reference (+ = previous better), {name}: n {r['matches']} est {g:+.3f} doc [{r['lo']:+.3f}, {r['hi']:+.3f}] "
          f"SE {r['se']:.4f} | block SE {r['se_block']:.4f}, seed SDs {np.sqrt(r['v_seed_base']):.4f}/{np.sqrt(r['v_seed_arm']):.4f}, "
          f"per-seed loss corr across arms {corr:+.2f}, paired seed SD {np.sqrt(v_paired):.4f} -> SE {se_p:.4f} "
          f"[{g - tq * se_p:+.3f}, {g + tq * se_p:+.3f}]")
