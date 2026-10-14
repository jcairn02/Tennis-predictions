"""Step 2's test run on 2020-2024: the combined-pattern term added to the current best model's stage 2, scored with
the project's paired comparison (current_best_model/compare.paired: block intervals, seed term paired by seed), and the
term's overlap with the serve-speed term.

These seasons were used to find the patterns, so any gain here proves nothing. This is a code check and a harm check
only (the adoption framework's default harm line: worse by more than 0.10 mLL with the whole interval below 0).
    term     logit q_new = logit q_full + b z, applied to the seed mean and to each seed alike
    z        the registered combined score with the registered gate, in-window parameters on 2020-24 (as the check
             fits them on its own window), capped at +-3.5 (check_now.score_params / score_from_params)
    b        the prior size of the rules: 0.45 x the registered discovery beta per SD, per unit of z
    base     the instance's 16 seeds, recalibrated walk-forward with the speed term (build_forecasts' recipe), checked
             against check_now/forecasts.parquet
Overlap with speed: the correlation of z with the speed column among men's matches, and the decision reading beyond
both stages against beyond stage 1 alone.

Reads results of seasons <= 2024 only. Writes data/studies/unpriced_leads/stage2_test/ (scores.csv in compare.py's
columns, summary.json).
Run: ./python.sh src/eda/unpriced_leads/stage2_test.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.edge_anatomy import common as E  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.unpriced_leads import check_now as CN  # noqa: E402
from src.eda.unpriced_leads import look as LK  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

C = CMP.C
TEST = tuple(range(2020, 2025))
OUT = H.OUT / "stage2_test"


def main() -> int:
    reg = json.loads(CN.REGISTRY.read_text(encoding="utf-8"))
    paths = LK.instance_paths(reg)
    frame = LK.load_window(paths, 2020, 2024, "2025-01-01", allow_post_2024=False)
    frame = LK.add_bases(frame, paths)
    frame = CN.add_model_bases(frame)
    LK._load_frame_months(paths)
    groups = reg["groups"]
    gates, _ = CN.registered_gates(groups, frame)
    P = CN.score_params(groups, frame, gates)
    z = CN.score_from_params(groups, frame, P, gates)
    s = LK.omnibus_score(groups, frame, "window", gates)
    if np.max(np.abs(CN.score_from_params(groups, frame, P, gates, capped=False) - s / P["omnibus_rms"])) > 1e-9:
        raise RuntimeError("the frozen parameters do not reproduce the registered score")
    disc = H.load_frame()
    bd = LK.fit(disc, LK.omnibus_score(groups, disc, "window"))["beta"]
    b_per_z = CN.PRIOR_K * bd / CN._rms(z)
    # the base, per seed (build_forecasts' recipe on seasons 2019-2024)
    _, Pi, _ = CMP.candidate(str(E.INSTANCE))
    fr = CMP.inputs_frame(Pi)
    yy = pd.read_parquet(Pi.model_frame, columns=["match_id", "season", "a_won"], filters=[("season", "<=", 2024)])
    if yy["season"].max() > 2024:
        raise RuntimeError("a result after 2024 was read")
    y = pd.Series(yy["a_won"].astype(float).to_numpy(), index=yy["match_id"].astype(str).to_numpy())
    sp = pd.read_parquet(E.SPEED, columns=["match_id", "spd_L_B"]).astype({"match_id": str})
    zs = sp.drop_duplicates("match_id").set_index("match_id")["spd_L_B"]
    ids = fr.index[fr["season"].between(2019, 2024).to_numpy()]
    info = fr.loc[ids, ["tour", "season", "tournament_date", "debut_season", "in_level"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = y.reindex(ids).to_numpy(float)
    info["block"] = C.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = C.blocks(info["tournament_date"].to_numpy(), 7)
    p16, _ = F.seed_table("model", tuple(range(2019, 2025)), tuple(range(16)),
                          F.FrameIndex(fr.reset_index()[["match_id", "season"]]), Pi, "td", require_checks=True)
    p16 = p16.reindex(ids)
    eta4 = pd.Series(C.lg(p16[[0, 1, 2, 3]].mean(axis=1).to_numpy()), index=ids)
    par = CMP.walk_forward(eta4, info, zs, TEST)
    # scored: the frame window's matches (debut seasons out), with their z
    zser = pd.Series(z, index=frame["match_id"].to_numpy())
    test = info.index[info["season"].isin(TEST).to_numpy() & ~info["debut"].to_numpy()]
    test = test.intersection(zser.index, sort=False)
    q, qk = CMP.forecasts(p16, info, par, zs, test)
    chk = pd.read_parquet(CN.FORECASTS, columns=["match_id", "q_full"]).astype({"match_id": str}).set_index("match_id")
    d = float(np.max(np.abs(q - chk["q_full"].reindex(test).to_numpy(float))))
    if d > 1e-9:
        raise RuntimeError(f"the base differs from check_now/forecasts.parquet (max {d:.2e})")
    off = b_per_z * zser.reindex(test).to_numpy(float)
    qn, qkn = expit(C.lg(q) + off), expit(C.lg(qk) + off[:, None])
    rows = []
    tour = info.loc[test, "tour"].to_numpy()
    pops = [("primary", "both tours", np.ones(len(test), bool)), ("primary", "men", tour == "atp"),
            ("primary", "women", tour == "wta")]
    pops += [("season", str(Y), info.loc[test, "season"].to_numpy() == Y) for Y in TEST]
    for group, name, m in pops:
        sub = test[m]
        base = (q[m], qk[m])
        arm = (qn[m], qkn[m])
        rows.append({"group": group, "population": name,
                     "comparison": "both stages: with the pattern term vs without (2020-24, in-sample)",
                     **CMP.paired(info, sub, base, arm)})
    scores = pd.DataFrame(rows)
    # overlap with speed
    men = (frame["tour"] == "atp").to_numpy()
    spd = zs.reindex(frame["match_id"]).to_numpy(float)
    okm = men & np.isfinite(spd)
    corr = float(np.corrcoef(z[okm], spd[okm])[0, 1])
    g3 = LK.group_score(next(g for g in groups if g["id"] == "G3"), frame, "window", gates)
    corr_g3 = float(np.corrcoef(g3[okm], spd[okm])[0, 1])
    r_full = LK.fit(frame, z, base="L_full")
    r_s1 = LK.fit(frame, z, base="L_s1")
    summary = {"seasons": list(TEST), "matches_scored": int(len(test)), "b_per_unit_z": b_per_z,
               "b_per_sd_prior": CN.PRIOR_K * bd, "largest_adjustment_log_odds": b_per_z * CN.CAP,
               "share_at_limit": float(np.mean(np.abs(CN.score_from_params(groups, frame, P, gates, capped=False))
                                               > CN.CAP)),
               "base_check_max_abs": d,
               "overlap_with_speed": {"corr_z_spd_men": corr, "corr_G3_spd_men": corr_g3,
                                      "beyond_both_stages": {k: r_full[k] for k in ("beta", "se", "z", "n")},
                                      "beyond_stage_1": {k: r_s1[k] for k in ("beta", "se", "z", "n")}},
               "note": "in-sample: the patterns were chosen on these seasons; a code and harm check only"}
    OUT.mkdir(parents=True, exist_ok=True)
    scores.to_csv(OUT / "scores.csv", index=False)
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8")
    pd.set_option("display.width", 200)
    print(scores[["group", "population", "matches", "estimate", "lo", "hi", "p_better", "reading"]].to_string(index=False))
    print(json.dumps(summary["overlap_with_speed"], indent=1, default=float))
    print(f"b per unit z {b_per_z:.4f}; largest adjustment {b_per_z * CN.CAP:.3f} log-odds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
