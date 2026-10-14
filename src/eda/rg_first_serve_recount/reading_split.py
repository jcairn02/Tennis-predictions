"""Where the Roland Garros candidate's harm-check reading sits, and how much of its uncertainty the seeds carry.

Asked by the owner after the reading ("p15% better is awful?? ... Thats highly suggestive we shouldnt do it?"). It reads
the same seasons and forecasts as compare.py's run (2020-2024; seeds 0-3), so it is no new look at new results: the
level slices are compare.py's own, and the seed term is split out of its interval.
    * per population (both tours, each level): the seed-mean estimate (compare.py's), each seed's own estimate, and the
      seed term's standard error (the SD over seeds / sqrt(4));
    * with compare.py's total SE: the seed term's share of the variance, and the SE 16 seeds would give if the seed
      term shrank as 1/sqrt(seeds) and the match term stayed.
mLL per match, + = the candidate better. Writes <out>/vs_reference_2026-10-08/reading_split.csv.
Usage: ./python.sh src/eda/rg_first_serve_recount/reading_split.py --out data/studies/current_best_model/2026-10-09_rg_box_scores
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402

POPULATIONS = ("both tours", "men", "women", "Slams", "1000s", "500s", "250s")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, help="the candidate build's records folder")
    a = ap.parse_args()
    C = CMP.C
    _, p_cand_paths, folder = CMP.candidate(a.out)
    p_ref_paths = R.paths("reference")
    ref, cand = CMP.inputs_frame(p_ref_paths), CMP.inputs_frame(p_cand_paths)
    through = CMP.THROUGH
    info = CMP.scoring_info(ref, cand, CMP.outcomes(p_ref_paths, through), CMP.outcomes(p_cand_paths, through), through)
    seasons, test = tuple(range(CMP.FIT_FROM, through + 1)), tuple(range(CMP.SCORE_FROM, through + 1))
    p_ref = CMP.seed_table(p_ref_paths, ref, seasons).reindex(info.index)
    p_cand = CMP.seed_table(p_cand_paths, cand, seasons).reindex(info.index)
    z = R.speed_column("reference")                       # the candidate has no speed column of its own
    eta_r = pd.Series(C.lg(p_ref.mean(axis=1).to_numpy()), index=p_ref.index)
    eta_c = pd.Series(C.lg(p_cand.mean(axis=1).to_numpy()), index=p_cand.index)
    par_r, par_c = CMP.walk_forward(eta_r, info, z, test), CMP.walk_forward(eta_c, info, z, test)
    scores = pd.read_csv(folder / f"vs_reference_{R.REF_ID}" / "scores.csv")
    scores = scores[scores["comparison"].eq("both stages: candidate vs reference")].set_index("population")
    rows = []
    for _, name, mask in CMP.populations(info, test):
        if name not in POPULATIONS:
            continue
        ids = info.index[mask]
        y = info.loc[ids, "y"].to_numpy(float)
        (qr, qrk), (qc, qck) = CMP.forecasts(p_ref, info, par_r, z, ids), CMP.forecasts(p_cand, info, par_c, z, ids)
        per_seed = [1000 * float(np.mean(C.ll(qrk[:, k], y) - C.ll(qck[:, k], y))) for k in range(qrk.shape[1])]
        seed_se = float(np.std(per_seed, ddof=1) / np.sqrt(len(per_seed)))
        total_se = float(scores.loc[name, "se"])
        match_var = max(total_se ** 2 - seed_se ** 2, 0.0)
        rows.append({"population": name, "matches": int(len(ids)),
                     "estimate": 1000 * float(np.mean(C.ll(qr, y) - C.ll(qc, y))),
                     **{f"seed{k}": v for k, v in enumerate(per_seed)},
                     "seeds_negative": int(sum(v < 0 for v in per_seed)), "seed_term_se": seed_se, "total_se": total_se,
                     "seed_share_of_variance": seed_se ** 2 / total_se ** 2,
                     "se_with_16_seeds": float(np.sqrt(match_var + seed_se ** 2 / 4)),
                     "p_better": float(scores.loc[name, "p_better"])})
    out = pd.DataFrame(rows)
    path = folder / f"vs_reference_{R.REF_ID}" / "reading_split.csv"
    out.to_csv(path, index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(out.round(4).to_string(index=False))
    print(f"written: {path.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
