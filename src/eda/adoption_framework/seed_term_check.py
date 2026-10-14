"""Review check (read-only): how much of the backfill comparison's interval is the seeds' variance, and what the
interval is when the seed term is paired by seed (both arms share the same TabPFN fits).

Mirrors src/eda/current_best_model/compare.py up to its scoring, results of seasons <= 2024 only (the proposed
holdout's outcomes are never read: compare.outcomes filters on season <= through). Writes nothing in the repo.
Run from the repo root: ./python.sh <this file>
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
SPEED = ROOT / "data/studies/infosys_atp_backfill/speed_columns_augmented.parquet"

P_ref = R.paths("reference")
ref = K.inputs_frame(P_ref)
y = K.outcomes(P_ref, THROUGH)
info = K.scoring_info(ref, ref, y, y, THROUGH)
seasons = tuple(range(K.FIT_FROM, THROUGH + 1))
test = tuple(range(K.SCORE_FROM, THROUGH + 1))
p = K.seed_table(P_ref, ref, seasons).reindex(info.index)
z_ref = R.speed_column("reference")
z_cand = pd.read_parquet(SPEED, columns=["match_id", "spd_L_B"]).astype({"match_id": str}).set_index("match_id")["spd_L_B"]
eta = pd.Series(C.lg(p.mean(axis=1).to_numpy()), index=p.index)
par_ref = K.walk_forward(eta, info, z_ref, test)
par_cand = K.walk_forward(eta, info, z_cand, test)
par_s1 = K.walk_forward(eta, info, None, test)


def decompose(ids, base, arm, label):
    yy = info.loc[ids, "y"].to_numpy(float)
    (qb, qbk), (qa, qak) = base, arm
    sb, sa = S.seed_loss(qbk, yy), S.seed_loss(qak, yy)
    r = S.paired_stats(C.ll(qb, yy), C.ll(qa, yy), sb, sa, info.loc[ids, "block"].to_numpy(), info.loc[ids, "week"].to_numpy())
    G = r["blocks"]
    tq = student_t.ppf(0.975, G - 1)
    d_seed = sb - sa                      # per-seed paired difference (both arms use the same fits)
    v_paired = float(np.var(d_seed, ddof=1) / len(d_seed))
    se_paired = np.sqrt(r["se_block"] ** 2 + v_paired)
    g = r["estimate"]
    print(f"{label:40s} n {r['matches']:6d} est {g:+.4f} | doc SE {r['se']:.4f} -> [{r['lo']:+.3f}, {r['hi']:+.3f}] "
          f"P {norm.cdf(g / r['se']):.2f} | block SE {r['se_block']:.4f}, seed terms {np.sqrt(r['v_seed_base']):.4f}/"
          f"{np.sqrt(r['v_seed_arm']):.4f}, paired seed {np.sqrt(v_paired):.5f} | paired SE {se_paired:.4f} -> "
          f"[{g - tq * se_paired:+.3f}, {g + tq * se_paired:+.3f}] P {norm.cdf(g / se_paired):.3f}  (G {G})")


for _group, name, mask in K.populations(info, test)[:3]:
    ids = info.index[mask]
    fr = K.forecasts(p, info, par_ref, z_ref, ids)
    fc = K.forecasts(p, info, par_cand, z_cand, ids)
    f1 = K.forecasts(p, info, par_s1, None, ids)
    decompose(ids, fr, fc, f"backfill: cand vs ref, {name}")
    decompose(ids, f1, f1, f"identical arms (stage 1 vs itself), {name}")
    if name == "men":
        decompose(ids, f1, fr, "stage 2 vs stage 1 (speed adj.), men")
