"""The rebuilt model (corrected data) against the current best model, both stages, on the same matches.

Both models are the decided recipe (docs/decisions/2026-10-07-speed-nudge.md): the local TabPFN-3.5 on 58 inputs, season Y
trained on 2013 .. Y - 1, symmetrised, then the serve-speed adjustment logit q = s_tour,Y eta + b_Y spd_L, s and b fitted
on 2019 .. Y - 1 (seeds 0-3 mean, debut seasons out, b shrunk with tau 0.05: serve_speed_tabpfn/score.nudge_parameters'
fit, here on each model's own forecasts). They differ only in their data:
    current   model_frame.parquet built on the tables of 30 Sep; its fits (rating race seeds 0-2, feature interactions
              seed 3); spd_L_B as the adjustment uses it (adaptive/columns.parquet, the study's frozen speed panel)
    rebuilt   the frame rebuilt on the corrected tables of 8 Oct (src/eda/model_rebuild/run_chain.py; fits.py, seeds
              0-3), with the same spd_L_B, and with spd_L_B recomputed on the corrected speed history
              (speed_columns.py)

The matches: every match both frames hold, 2019-2026, by match id (a match whose id changed between the tables is left
out; the rebuilt frame's extra matches, the restored men's 2018 included, are training rows only). Debut seasons out, as
the adjustment's fit and evaluation. Scored on 2022-2026 (the TabPFN test seasons), both tours and by tour and season,
and on men 2024-2026 (the speed study's test). Log loss in milli-log-loss per match; positive = the rebuilt model has the
lower log loss (better). Intervals: serve_speed_tabpfn/score.paired_stats (4-week blocks plus the seeds' variance; the
calendar-week version too). Since 9 Oct 2026 the seed term between two models is paired by seed (both use seeds 0-3, the
same TabPFN random states), and unpaired against the close; the unpaired intervals, as published, are kept as
lo_unpaired / hi_unpaired. For scale, each model against the calibrated close. Stage 1 also at Polymarket's price 24
hours before the start (2025-2026, the matches both models priced), with each model's close-based calibration.

Writes data/studies/model_rebuild/comparison.json and comparison.csv.
Run: ./python.sh src/eda/model_rebuild/compare.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402
from src.eda.serve_speed_tabpfn.adaptive import columns as CO  # noqa: E402

OUT = ROOT / "data" / "studies" / "model_rebuild"
NONE = OUT / "no_fits_here"                 # the rebuilt model never falls back to the current model's fit folders
P_CUR = C.DEFAULT
P_NEW = C.DEFAULT.with_(model_frame=OUT / "model_frame.parquet", model_inputs=OUT / "model_inputs.json",
                        local=OUT / "fits", fi_local=NONE, race_local=NONE)
SEASONS = tuple(range(2019, 2027))
TEST = tuple(range(2022, 2027))
SEEDS = (0, 1, 2, 3)


def frame(P: C.Paths) -> pd.DataFrame:
    f = pd.read_parquet(P.model_frame, columns=["match_id", "tour", "season", "tournament_date", "debut_season",
                                                "a_won", "p_mkt"])
    f["match_id"] = f["match_id"].astype(str)
    return f.set_index("match_id")


def seed_table(P: C.Paths, require_checks: bool) -> pd.DataFrame:
    fx = F.FrameIndex(frame(P).reset_index()[["match_id", "season"]])
    t, _ = F.seed_table("model", SEASONS, SEEDS, fx, P, "td", require_checks)
    return t


def early_table(P: C.Paths, require_checks: bool) -> pd.DataFrame:
    fx = F.FrameIndex(frame(P).reset_index()[["match_id", "season"]])
    t, _ = F.seed_table("model", (2025, 2026), SEEDS, fx, P, "early", require_checks)
    return t


def walk_forward(eta: pd.Series, info: pd.DataFrame, z: pd.Series | None) -> dict:
    """{Y: (s_atp, s_wta, b_shrunk)} for Y in TEST from 2019 .. Y - 1, debut out (score.nudge_parameters' fit; z None
    gives the calibration slopes alone, b = 0)."""
    out = {}
    for Y in TEST:
        hist = info.index[(info["season"] < Y) & ~info["debut"]]
        e = eta.reindex(hist).to_numpy()
        atp = (info.loc[hist, "tour"] == "atp").to_numpy()
        y = info.loc[hist, "y"].to_numpy(float)
        X = [np.where(atp, e, 0.0), np.where(~atp, e, 0.0)]
        if z is not None:
            X.append(z.reindex(hist).to_numpy(float))
        beta, se = C.fit_logistic(np.column_stack(X), y)
        b = 0.0
        if z is not None:
            b = float(beta[2]) * C.TAU_NUDGE ** 2 / (C.TAU_NUDGE ** 2 + float(se[2]) ** 2)
        out[Y] = (float(beta[0]), float(beta[1]), b, float(beta[2]) if z is not None else 0.0,
                  float(se[2]) if z is not None else 0.0)
    return out


def forecasts(p: pd.DataFrame, info: pd.DataFrame, params: dict, z: pd.Series | None, ids: pd.Index):
    """The seed-mean forecast and the per-seed forecasts on ids, with each season's s and b."""
    lp = C.lg(p.reindex(ids).to_numpy())                     # per-seed log-odds
    lm = C.lg(p.reindex(ids).mean(axis=1).to_numpy())        # the seed mean's log-odds (the model's eta)
    inf = info.loc[ids]
    s = np.array([params[int(Y)][0] if t == "atp" else params[int(Y)][1] for Y, t in zip(inf["season"], inf["tour"])])
    b = np.array([params[int(Y)][2] for Y in inf["season"]])
    zz = np.zeros(len(ids)) if z is None else np.where(inf["tour"].to_numpy() == "wta", 0.0,
                                                       z.reindex(ids).to_numpy(float))
    return expit(s * lm + b * zz), expit(s[:, None] * lp + (b * zz)[:, None])


def paired(info, ids, base, arm, matched: bool = True) -> dict:
    """matched: both forecasts from seeds 0-3, the seed term paired by seed; False against a price (it has no seeds)."""
    y = info.loc[ids, "y"].to_numpy(float)
    (qb, qbk), (qa, qak) = base, arm
    r = S.paired_stats(C.ll(qb, y), C.ll(qa, y), S.seed_loss(qbk, y), S.seed_loss(qak, y),
                       info.loc[ids, "block"].to_numpy(), info.loc[ids, "week"].to_numpy(), matched_seeds=matched)
    return {k: r[k] for k in ("matches", "estimate", "lo", "hi", "lo_week", "hi_week", "seed_term", "lo_unpaired",
                              "hi_unpaired", "lo_week_unpaired", "hi_week_unpaired")}


def main() -> int:
    cur, new = frame(P_CUR), frame(P_NEW)
    common = cur.index.intersection(new.index)
    both = common[cur.loc[common, "season"].between(2019, 2026).to_numpy()]
    if not (cur.loc[both, "a_won"].to_numpy() == new.loc[both, "a_won"].to_numpy()).all():
        raise SystemExit("the two frames disagree on a result")
    info = cur.loc[both, ["tour", "season", "tournament_date", "debut_season", "p_mkt"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = cur.loc[both, "a_won"].astype(float)
    info["block"] = C.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = C.blocks(info["tournament_date"].to_numpy(), 7)
    info["p_mkt_new"] = new.loc[both, "p_mkt"]
    p_cur = seed_table(P_CUR, require_checks=True).reindex(both)
    p_new = seed_table(P_NEW, require_checks=False).reindex(both)
    if p_cur.isna().any().any() or p_new.isna().any().any():
        raise SystemExit("forecasts missing on common matches")
    z_cur = pd.read_parquet(CO.COLUMNS, columns=["match_id", "spd_L_B"]).astype({"match_id": str}) \
        .set_index("match_id")["spd_L_B"]
    z_fix = pd.read_parquet(OUT / "speed_columns_corrected.parquet", columns=["match_id", "spd_L_B"]) \
        .astype({"match_id": str}).set_index("match_id")["spd_L_B"]
    eta_cur = pd.Series(C.lg(p_cur.mean(axis=1).to_numpy()), index=both)
    eta_new = pd.Series(C.lg(p_new.mean(axis=1).to_numpy()), index=both)
    models = {
        "current_base": (p_cur, walk_forward(eta_cur, info, None), None),
        "rebuilt_base": (p_new, walk_forward(eta_new, info, None), None),
        "current_full": (p_cur, walk_forward(eta_cur, info, z_cur), z_cur),
        "rebuilt_full": (p_new, walk_forward(eta_new, info, z_cur), z_cur),
        "rebuilt_full_corrected_speed": (p_new, walk_forward(eta_new, info, z_fix), z_fix),
    }
    pops = {"both_2022_26": (info["season"].between(2022, 2026)), "men_2022_26": (info["tour"] == "atp")
            & info["season"].between(2022, 2026), "women_2022_26": (info["tour"] == "wta")
            & info["season"].between(2022, 2026), "men_2024_26": (info["tour"] == "atp")
            & info["season"].between(2024, 2026)}
    pops.update({f"both_{Y}": info["season"] == Y for Y in TEST})
    rows = []
    comparisons = [("stage 1 (calibrated base)", "current_base", "rebuilt_base"),
                   ("both stages, the adjustment's speed column as used today", "current_full", "rebuilt_full"),
                   ("both stages, rebuilt model with the corrected speed history", "current_full",
                    "rebuilt_full_corrected_speed"),
                   ("speed history alone (rebuilt model, corrected against today's speed column)", "rebuilt_full",
                    "rebuilt_full_corrected_speed")]
    for name, pmask in pops.items():
        ids = info.index[pmask.to_numpy() & ~info["debut"].to_numpy()]
        fc = {m: forecasts(p, info, par, z, ids) for m, (p, par, z) in models.items()}
        for label, a, b in comparisons:
            rows.append({"population": name, "comparison": label, "base": a, "arm": b, **paired(info, ids, fc[a], fc[b])})
        # for scale: each model's both stages against the calibrated close
        close = {}
        for col in ("p_mkt", "p_mkt_new"):
            pm = info[col]
            par = {}
            for Y in TEST:
                hist = info.index[(info["season"] < Y) & ~info["debut"] & np.isfinite(pm)]
                atp = (info.loc[hist, "tour"] == "atp").to_numpy()
                e = C.lg(pm.loc[hist].to_numpy())
                beta, _ = C.fit_logistic(np.column_stack([np.where(atp, e, 0.0), np.where(~atp, e, 0.0)]),
                                         info.loc[hist, "y"].to_numpy(float))
                par[Y] = (float(beta[0]), float(beta[1]))
            inf = info.loc[ids]
            s = np.array([par[int(Y)][0] if t == "atp" else par[int(Y)][1] for Y, t in zip(inf["season"], inf["tour"])])
            q = expit(s * C.lg(inf[col].to_numpy()))
            close[col] = (q, q[:, None])
        rows.append({"population": name, "comparison": "for scale: current model against the calibrated close",
                     "base": "close", "arm": "current_full",
                     **paired(info, ids, close["p_mkt"], fc["current_full"], matched=False)})
        rows.append({"population": name, "comparison": "for scale: rebuilt model against the calibrated close "
                     "(its own corrected odds)", "base": "close", "arm": "rebuilt_full_corrected_speed",
                     **paired(info, ids, close["p_mkt_new"], fc["rebuilt_full_corrected_speed"], matched=False)})
    # stage 1 at Polymarket's price 24 hours before the listed start (the "early" query block: odds_logit replaced by
    # that price), 2025-2026, the matches both models priced; calibrated with each model's own close-based slopes
    early_cur = early_table(P_CUR, True)
    early_new = early_table(P_NEW, False)
    eids = early_cur.index.intersection(early_new.index).intersection(info.index[~info["debut"].to_numpy()])
    for name, m in (("both_2025_26_early_price", np.ones(len(eids), bool)),
                    ("men_2025_26_early_price", (info.loc[eids, "tour"] == "atp").to_numpy())):
        ids = eids[m]
        fc_c = forecasts(early_cur, info, models["current_base"][1], None, ids)
        fc_n = forecasts(early_new, info, models["rebuilt_base"][1], None, ids)
        rows.append({"population": name, "comparison": "stage 1 at the price 24 hours before the start",
                     "base": "current_base", "arm": "rebuilt_base", **paired(info, ids, fc_c, fc_n)})
    table = pd.DataFrame(rows)
    table.to_csv(OUT / "comparison.csv", index=False)
    meta = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
            "matches_both_frames_2019_26": int(len(both)), "current_frame_2019_26": int(cur["season"].between(2019, 2026).sum()),
            "rebuilt_frame_2019_26": int(new["season"].between(2019, 2026).sum()),
            "odds_changed_on_common_matches": int((info["p_mkt"] != info["p_mkt_new"]).sum()),
            "coefficients": {m: {str(Y): v for Y, v in par.items()} for m, (_, par, _) in models.items()},
            "unit": "mLL per match; positive = the arm (second model) has the lower log loss",
            "rows": rows}
    (OUT / "comparison.json").write_text(json.dumps(meta, indent=1, default=float), encoding="utf-8")
    print(table[table["population"].isin(["both_2022_26", "men_2024_26"])].to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
