"""Audit scratch: the frame and the registered jobs.

1. The 2022 confirm job's training set (seasons 2013-2021, frame order) against the leak-proof upload's X_train / y_train
   (the check in build_frames compares tabpfn_split == 'train' rows, which need not be the same selection).
2. Recompute every job's fingerprint from frame.parquet (what dispatch.py will send) and compare with jobs.json.
3. Columns of each job against arms.ARMS; query = season rows then their flip.
4. The frame's new inputs against pieces.parquet recomputed independently (no arms.py code).
5. Population facts: rows per season, the 2018 men's gap, carpet, unknown surfaces, players with no rating history.

Run: ./python.sh data/studies/surface_elo_pieces/audit_scratch/check_frame_jobs.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from src.eda.surface_elo_pieces import arms as A  # noqa: E402
from src.eda.surface_elo_pieces import build_frames as BF  # noqa: E402
from src.eda.surface_elo_pieces import common as C  # noqa: E402
from src.eda.tabpfn_leakproof import common as LP  # noqa: E402
from src.eda.tabpfn_thinking import common as T  # noqa: E402

OUT = Path(__file__).resolve().parent
res = {}
frame = pd.read_parquet(C.OUT / "frame.parquet")
jobs = json.loads((C.OUT / "jobs.json").read_text(encoding="utf-8"))

# 1. the 2022 fold's training set against the leak-proof upload
X_train_lp, y_train_lp, X_query_lp, ids_lp, _ = LP.load_upload()
X_tr, y_tr, X_q, ids = BF.job_data(frame, "base", 2022)
res["fold2022_train_equals_leakproof_upload"] = bool(
    X_tr.shape == X_train_lp.shape and np.array_equal(X_tr.to_numpy(), X_train_lp.to_numpy(dtype="float64"), equal_nan=True)
    and np.array_equal(y_tr, y_train_lp))
res["tabpfn_split_vs_season"] = frame.groupby(["tabpfn_split", "season"]).size().unstack(0).fillna(0).astype(int).to_dict()
res["frame_split_values"] = frame["split"].value_counts().to_dict()

# 2-3. fingerprints and columns of every job
bad_fp, bad_cols, bad_q = [], [], []
for j in jobs:
    X_tr, y_tr, X_q, ids = BF.job_data(frame, j["arm"], j["season"])
    if T.fingerprint(X_tr, y_tr, X_q) != j["fingerprint"]:
        bad_fp.append(j["job"])
    if list(X_tr.columns) != A.ARMS[j["arm"]] or j["columns"] != A.ARMS[j["arm"]]:
        bad_cols.append(j["job"])
    n = len(X_q) // 2
    tr_seasons = frame.loc[frame["season"].between(C.TRAIN_FROM, j["season"] - 1), "season"]
    if not (tr_seasons.max() == j["season"] - 1 and len(X_tr) == j["train_rows"] and len(X_q) == j["query_rows"]
            and np.allclose(A.flip(X_q.iloc[n:].reset_index(drop=True)).to_numpy(), X_q.iloc[:n].to_numpy(), equal_nan=True)):
        bad_q.append(j["job"])
res["jobs"] = len(jobs)
res["fingerprint_mismatch"] = bad_fp
res["column_mismatch"] = bad_cols
res["window_or_flip_problem"] = bad_q
res["train_rows_by_job_season"] = {str(s): int(next(j["train_rows"] for j in jobs if j["season"] == s)) for s in sorted({j["season"] for j in jobs})}

# 4. new inputs recomputed from pieces.parquet with independent code
pc = frame[["match_id"]].merge(pd.read_parquet(C.PIECES), on="match_id", how="left", validate="one_to_one")
L10 = np.log(10) / 400
chk = {
    "elo_overall": L10 * (pc["R_a"] - pc["R_b"]),
    "elo_offset": L10 * ((pc["R_a"] + pc["D_a"].fillna(0)) - (pc["R_b"] + pc["D_b"].fillna(0))),
    "elo_surface": L10 * (pc["S_a"].fillna(pc["R_a"]) - pc["S_b"].fillna(pc["R_b"])),
}
for s in ("a", "b"):
    chk[f"surf_career_{s}"] = np.log1p(pc[f"NS_{s}"])
    chk[f"surf_season_{s}"] = np.log1p(pc[f"season_n_{s}"])
    chk[f"surf_layoff_{s}"] = np.log1p(np.minimum(pc[f"days_since_{s}"].fillna(1095.0), 1095.0))
    chk[f"surf_form_prev_{s}"] = pc[f"prev_res_{s}"] / (pc[f"prev_n_{s}"] + 5.0)
res["new_inputs_max_abs_diff"] = {k: float(np.nanmax(np.abs(frame[f"x_{k}"].to_numpy() - np.asarray(v, float))))
                                  for k, v in chk.items()}
# elo_logit (base) against the blend recomputed from pieces (Stage 1 'ret', w 0.30 / 0.25)
w = np.where(frame["tour"].eq("atp"), 0.30, 0.25)
blend = L10 * (((1 - w) * pc["R_a"] + w * pc["S_a"].fillna(pc["R_a"])) - ((1 - w) * pc["R_b"] + w * pc["S_b"].fillna(pc["R_b"])))
res["elo_logit_vs_recomputed_blend_max_abs_diff"] = float(np.nanmax(np.abs(frame["x_elo_logit"].to_numpy() - blend.to_numpy())))
res["elo_logit_vs_recomputed_blend_p99_abs_diff"] = float(np.nanquantile(np.abs(frame["x_elo_logit"].to_numpy() - blend.to_numpy()), 0.99))

# 5. population facts
res["surface_counts"] = {f"{k[0]}|{k[1]}": int(v) for k, v in frame.groupby(["tour", "x_surface"]).size().items()}
res["rows_with_unknown_surface"] = int(frame["x_surface"].isna().sum())
res["NS_zero_rows_by_season"] = frame.assign(z=(pc["NS_a"].eq(0) | pc["NS_b"].eq(0)).to_numpy()).groupby("season")["z"].sum().to_dict()
res["N_overall_zero_rows_by_season"] = frame.assign(z=(pc["N_a"].eq(0) | pc["N_b"].eq(0)).to_numpy()).groupby("season")["z"].sum().to_dict()
res["corr_inputs_all_rows"] = frame[["x_odds_logit", "x_elo_logit", "x_elo_overall", "x_elo_offset", "x_elo_surface"]].corr().round(4).to_dict()
d_off = (L10 * (pc["D_a"].fillna(0) - pc["D_b"].fillna(0))).to_numpy()
res["sd_offset_difference_logit"] = float(np.std(d_off))
res["sd_elo_overall_logit"] = float(np.std(frame["x_elo_overall"]))
res["sd_elo_logit_minus_overall"] = float(np.std(frame["x_elo_logit"] - frame["x_elo_overall"]))
print(json.dumps(res, indent=1, default=str))
(OUT / "check_frame_jobs.json").write_text(json.dumps(res, indent=1, default=str))
