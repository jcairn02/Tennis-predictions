"""Compare a candidate build of the current best model with the frozen reference of 8 Oct 2026, both stages.

The owner's rule (8 Oct 2026; docs/decisions/2026-10-08-current-best-model.md, amendment): new data, new features and
rebuilds are compared against the frozen reference (reference.py) before they change the current best model. If they
harm it, the data is ignored, down-weighted or transformed, and compared again.

The candidate. A built instance in the layout run_chain.py --collect and model_rebuild/fits.py write: a folder with
model_frame.parquet, model_inputs.json and fits/model__<Y>__seed<k>.npz for seasons 2019 .. --through and seeds 0-3, and
optionally speed_columns.parquet (match_id, spd_L_B: its own stage-2 column; without it the reference's column is used,
which is right when only the tables under stage 1 changed). Or by name: "previous" (the frozen 30 Sep model) or
"reference" (the reference itself: every difference must come out exactly 0).

Part 1, the inputs. No result is read. On the matches both frames hold, all seasons 2013-2026, per input, tour and
season:
    * the share of rows changed, the correlation, and the median and 99th-percentile change in reference SDs;
    * the SCALE RATIO: the candidate's SD over the reference's, that tour and season;
    * the LEVEL SHIFT: the change of the mean, in reference SDs.
A tour-season is flagged when its scale ratio is off 1 by more than 10% or its level moves by more than 0.10 SD. An
input is "uneven" when some of its tour-seasons are flagged and others not. That is the shape of the input-data audit's
finding #6, where ITF box scores widened the IOS products in 2025-2026 only. Also written: each frame's own season
profile (each tour-season's SD and mean against its 2013-2021 training seasons), and the matches one frame holds and the
other lacks.

Part 2, the scores. Results of seasons <= --through only. The default 2024 keeps 2025-2026 out: they are the proposed
clean holdout (docs/studies/clean_holdout_rebuild/). Each model goes through the decided recipe on its own forecasts:
    * the seed mean of seeds 0-3;
    * the per-tour calibration slopes and stage 2's b, fitted walk-forward on 2019 .. Y - 1, debut seasons out, b
      shrunk with tau 0.05 (serve_speed_tabpfn/score.nudge_parameters' fit, as model_rebuild/compare.py runs it);
    * scored on 2020 .. --through, on the matches both frames hold.
Paired log loss in milli-log-loss per match. POSITIVE = THE CANDIDATE HAS THE LOWER LOG LOSS (better). Intervals:
serve_speed_tabpfn/score.paired_stats, 4-week blocks plus the seeds' variance (t on blocks - 1). Both models use seeds
0-3, so their seed term is paired by seed: the variance over seeds of the per-seed difference, over 4 (matched_seeds,
since 9 Oct 2026). A model compared with itself gets exactly 0 with a zero-width interval. The rows against a closing
price keep the unpaired term (the price has no seeds). The unpaired interval, as read before 9 Oct 2026, is kept as
se_unpaired, lo_unpaired and hi_unpaired. Reading: "better" if the interval lies above 0, "worse" if below, otherwise
"unresolved", with p_better = P(better), the t CDF of estimate / se on blocks - 1 degrees of freedom: the flat-prior
reading of this one test, undefined for identical forecasts (docs/studies/adoption_framework/README.md, section 7).
    primary   both stages: both tours, men, women
    also      stage 1 alone; both stages by level and by season; each model against its own calibrated close

Writes <out>/inputs.csv, inputs_by_season.csv, season_profile.csv, coverage.csv, scores.csv and summary.json. <out>
defaults to <candidate>/vs_reference_2026-10-08 (a named candidate: the reference's comparisons/<name>/).
Run: ./python.sh src/eda/current_best_model/compare.py --candidate <folder>|previous|reference [--speed <parquet>]
                                                        [--through 2024] [--out <folder>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.special import expit
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.serve_speed_tabpfn import score as S  # noqa: E402

SEEDS = (0, 1, 2, 3)
FIT_FROM = C.CALIB_FROM          # 2019: the first season the walk-forward fits read
SCORE_FROM = 2020
THROUGH = 2024                   # the last season whose results are read, by default
TRAIN_END = 2021                 # the season profile's yardstick: the frame's 2013-2021 seasons
LEVELS = {0.0: "Slams", 1.0: "Finals", 2.0: "1000s", 3.0: "500s", 4.0: "250s"}
SCALE_TOL = 0.10
LEVEL_TOL = 0.10
CHANGED = 1e-9


# ------------------------------------------------------------------------------------------------
# The two models

def candidate(arg: str) -> tuple[str, C.Paths, Path | None]:
    """(name, paths, folder) of the candidate: a built folder, or "previous" / "reference" (frozen)."""
    if arg in ("reference", "previous"):
        return arg, R.paths(arg), None
    folder = Path(arg) if Path(arg).is_absolute() else ROOT / arg
    if not (folder / "model_frame.parquet").exists():
        raise SystemExit(f"{folder}: no model_frame.parquet")
    P = C.DEFAULT.with_(model_frame=folder / "model_frame.parquet", model_inputs=folder / "model_inputs.json",
                        local=folder / "fits", fi_local=folder / "no_fits_here", race_local=folder / "no_fits_here",
                        checks=folder / "no_checks_here")
    return folder.name, P, folder


def inputs_frame(P: C.Paths) -> pd.DataFrame:
    """The frame without its result column, by match id, in the file's order."""
    cols = [c for c in pq.read_schema(P.model_frame).names if c != "a_won"]
    f = pd.read_parquet(P.model_frame, columns=cols)
    f["match_id"] = f["match_id"].astype(str)
    return f.set_index("match_id")


def outcomes(P: C.Paths, through: int) -> pd.Series:
    """a_won of seasons <= through only: later seasons' rows are filtered out before the column is read."""
    f = pd.read_parquet(P.model_frame, columns=["match_id", "season", "a_won"], filters=[("season", "<=", through)])
    if len(f) and f["season"].max() > through:
        raise RuntimeError("a result after --through was read")
    return pd.Series(f["a_won"].astype(float).to_numpy(), index=f["match_id"].astype(str).to_numpy())


def seed_table(P: C.Paths, frame: pd.DataFrame, seasons) -> pd.DataFrame:
    """Symmetrised P(A wins) by match id, one column per seed, from the model's stored fits (checked against its
    frame: ids in order, the expanding window's training size, the input list)."""
    fx = F.FrameIndex(frame.reset_index()[["match_id", "season"]])
    table, _ = F.seed_table("model", seasons, SEEDS, fx, P, "td", require_checks=True)
    return table


# ------------------------------------------------------------------------------------------------
# Part 1: the inputs (no result read)

def _stats(a: np.ndarray, b: np.ndarray, sd_all: float) -> dict:
    fa, fb = np.isfinite(a), np.isfinite(b)
    both = fa & fb
    changed = (fa != fb) | (both & (np.abs(a - b) > CHANGED))
    d = np.abs(a[both] - b[both]) / sd_all
    sa = float(np.std(a[fa])) if fa.any() else np.nan
    sb = float(np.std(b[fb])) if fb.any() else np.nan
    if fa.any() and fb.any():
        ratio = sb / sa if sa > 0 else (1.0 if sb == 0 else np.inf)
        shift = (float(np.mean(b[fb])) - float(np.mean(a[fa]))) / sd_all
    else:
        ratio, shift = (1.0, 0.0) if fa.sum() == fb.sum() == 0 else (np.nan, np.nan)
    corr = (float(np.corrcoef(a[both], b[both])[0, 1]) if both.sum() > 2 and np.std(a[both]) > 0
            and np.std(b[both]) > 0 else np.nan)
    flag = (not np.isfinite(ratio) or not np.isfinite(shift) or abs(ratio - 1) > SCALE_TOL
            or abs(shift) > LEVEL_TOL)
    return {"rows": int(len(a)), "changed_share": float(changed.mean()) if len(a) else 0.0, "correlation": corr,
            "median_abs_change_sd": float(np.median(d)) if len(d) else np.nan,
            "p99_abs_change_sd": float(np.quantile(d, 0.99)) if len(d) else np.nan,
            "scale_ratio": ratio, "level_shift_sd": shift, "missing_reference": int((~fa).sum()),
            "missing_candidate": int((~fb).sum()), "flagged": bool(flag)}


def input_drift(ref: pd.DataFrame, cand: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(per input, tour and season; per input) on the matches both frames hold. No result is read."""
    ids = ref.index.intersection(cand.index)
    a_all, b_all = ref.loc[ids], cand.loc[ids]
    keys = a_all[["tour", "season"]].astype({"season": int})
    cells = sorted(set(map(tuple, keys.to_numpy().tolist())))
    shared = [c for c in ref.columns if c.startswith("in_") and c in cand.columns]
    rows, per = [], []
    for c in shared:
        a, b = a_all[c].to_numpy(float), b_all[c].to_numpy(float)
        sd_all = float(np.nanstd(a)) or 1.0
        flagged = []
        for tour, season in cells:
            m = (keys["tour"].to_numpy() == tour) & (keys["season"].to_numpy() == season)
            st = _stats(a[m], b[m], sd_all)
            rows.append({"input": c[3:], "tour": tour, "season": season, **st})
            if st["flagged"]:
                flagged.append(f"{tour} {season}")
        whole = _stats(a, b, sd_all)
        shape = "none" if not flagged else ("every season" if len(flagged) == len(cells) else "uneven")
        per.append({"input": c[3:], "rows": whole["rows"], "changed_share": whole["changed_share"],
                    "correlation": whole["correlation"], "median_abs_change_sd": whole["median_abs_change_sd"],
                    "p99_abs_change_sd": whole["p99_abs_change_sd"], "flag": shape,
                    "flagged_tour_seasons": len(flagged), "flagged": "; ".join(flagged)})
    extra = ([{"input": c[3:], "flag": "only in the reference"} for c in ref.columns
              if c.startswith("in_") and c not in cand.columns]
             + [{"input": c[3:], "flag": "only in the candidate"} for c in cand.columns
                if c.startswith("in_") and c not in ref.columns])
    return pd.DataFrame(rows), pd.concat([pd.DataFrame(per), pd.DataFrame(extra)], ignore_index=True)


def season_profile(frame: pd.DataFrame, label: str) -> pd.DataFrame:
    """Each input's SD and mean by tour and season against its own 2013-2021 values (no result read): how evenly an
    input is scaled across the eras the model trains on. Finding #6 shows here as products' SD ratios well above 1
    in 2025-2026."""
    s, t = frame["season"].to_numpy(), frame["tour"].to_numpy()
    rows = []
    for c in [c for c in frame.columns if c.startswith("in_")]:
        x = frame[c].to_numpy(float)
        for tour in sorted(set(t)):
            base = x[(t == tour) & (s >= C.TRAIN_FROM) & (s <= TRAIN_END) & np.isfinite(x)]
            sd0 = float(np.std(base)) if len(base) else np.nan
            mu0 = float(np.mean(base)) if len(base) else np.nan
            for season in sorted(set(s[t == tour])):
                m = (t == tour) & (s == season)
                xs = x[m & np.isfinite(x)]
                ok = len(xs) > 0 and np.isfinite(sd0) and sd0 > 0
                rows.append({"frame": label, "input": c[3:], "tour": tour, "season": int(season), "rows": int(m.sum()),
                             "missing_share": float(1 - len(xs) / m.sum()),
                             "sd_ratio_to_2013_21": float(np.std(xs) / sd0) if ok else np.nan,
                             "mean_shift_sd": float((np.mean(xs) - mu0) / sd0) if ok else np.nan})
    return pd.DataFrame(rows)


def coverage(ref: pd.DataFrame, cand: pd.DataFrame) -> pd.DataFrame:
    """Matches by tour and season: in both frames, in the reference only, in the candidate only."""
    both = ref.index.intersection(cand.index)
    parts = [ref.loc[both, ["tour", "season"]].assign(where="both"),
             ref.loc[ref.index.difference(cand.index), ["tour", "season"]].assign(where="reference only"),
             cand.loc[cand.index.difference(ref.index), ["tour", "season"]].assign(where="candidate only")]
    t = pd.concat(parts)
    return t.groupby(["tour", "season", "where"]).size().unstack("where", fill_value=0).reset_index()


# ------------------------------------------------------------------------------------------------
# Part 2: the scores (results of seasons <= through)

def scoring_info(ref: pd.DataFrame, cand: pd.DataFrame, y_ref: pd.Series, y_cand: pd.Series, through: int,
                 base: str = "reference") -> pd.DataFrame:
    """The matches both frames hold, 2019 .. through, with what scoring needs. The match facts (tour, season, date,
    debut, level) come from the reference's frame (base="candidate": from the candidate's, as model_rebuild/compare.py
    took them from the model it compared against); each model's closing price from its own frame."""
    src = ref if base == "reference" else cand
    ids = ref.index.intersection(cand.index)
    ids = ids[src.loc[ids, "season"].between(FIT_FROM, through).to_numpy()]
    y1, y2 = y_ref.reindex(ids), y_cand.reindex(ids)
    if y1.isna().any() or y2.isna().any() or not np.array_equal(y1.to_numpy(), y2.to_numpy()):
        raise SystemExit("the two frames disagree on a result, or lack one")
    info = src.loc[ids, ["tour", "season", "tournament_date", "debut_season", "in_level"]].copy()
    info["debut"] = info["debut_season"].astype(bool)
    info["y"] = y1.to_numpy(float)
    info["block"] = C.blocks(info["tournament_date"].to_numpy(), 28)
    info["week"] = C.blocks(info["tournament_date"].to_numpy(), 7)
    info["level"] = info["in_level"].map(LEVELS)
    info["p_ref"] = ref.loc[ids, "p_mkt"].to_numpy(float)
    info["p_cand"] = cand.loc[ids, "p_mkt"].to_numpy(float)
    return info


def walk_forward(eta: pd.Series, info: pd.DataFrame, z: pd.Series | None, test) -> dict:
    """{Y: (s_atp, s_wta, b_shrunk, b, se_b)} for Y in test, each fitted on 2019 .. Y - 1, debut seasons out (z None:
    the calibration slopes alone, b = 0). model_rebuild/compare.walk_forward with the test seasons as an argument."""
    out = {}
    for Y in test:
        hist = info.index[(info["season"] < Y) & ~info["debut"]]
        e = eta.reindex(hist).to_numpy()
        atp = (info.loc[hist, "tour"] == "atp").to_numpy()
        y = info.loc[hist, "y"].to_numpy(float)
        X = [np.where(atp, e, 0.0), np.where(~atp, e, 0.0)]
        if z is not None:
            zz = z.reindex(hist).to_numpy(float)
            if not np.isfinite(zz).all():
                raise SystemExit(f"the speed column lacks {int((~np.isfinite(zz)).sum())} matches of 2019 .. {Y - 1}")
            X.append(zz)
        beta, se = C.fit_logistic(np.column_stack(X), y)
        b = 0.0
        if z is not None:
            b = float(beta[2]) * C.TAU_NUDGE ** 2 / (C.TAU_NUDGE ** 2 + float(se[2]) ** 2)
        out[int(Y)] = (float(beta[0]), float(beta[1]), b, float(beta[2]) if z is not None else 0.0,
                       float(se[2]) if z is not None else 0.0)
    return out


def walk_forward_on(eta: pd.Series, info: pd.DataFrame, z: pd.Series | None, hist: pd.Index) -> tuple:
    """(s_atp, s_wta, b_shrunk, b, se_b) fitted on the named history (debut seasons already left out): walk_forward's
    fit with its rows given, for stage 2 grown at a retrain (2019 .. Y - 1 plus the season-Y matches it admits; the
    owner, 20 Oct 2026). On hist = the seasons before Y it equals walk_forward(...)[Y] (test_training_rows.py)."""
    e = eta.reindex(hist).to_numpy()
    atp = (info.loc[hist, "tour"] == "atp").to_numpy()
    y = info.loc[hist, "y"].to_numpy(float)
    X = [np.where(atp, e, 0.0), np.where(~atp, e, 0.0)]
    if z is not None:
        zz = z.reindex(hist).to_numpy(float)
        if not np.isfinite(zz).all():
            raise SystemExit(f"the speed column lacks {int((~np.isfinite(zz)).sum())} history matches")
        X.append(zz)
    beta, se = C.fit_logistic(np.column_stack(X), y)
    b = 0.0
    if z is not None:
        b = float(beta[2]) * C.TAU_NUDGE ** 2 / (C.TAU_NUDGE ** 2 + float(se[2]) ** 2)
    return (float(beta[0]), float(beta[1]), b, float(beta[2]) if z is not None else 0.0,
            float(se[2]) if z is not None else 0.0)


def forecasts(p: pd.DataFrame, info: pd.DataFrame, params: dict, z: pd.Series | None, ids: pd.Index):
    """(the seed mean's forecast, the per-seed forecasts) on ids, with each season's s and b; women's column is 0."""
    lp = C.lg(p.reindex(ids).to_numpy())
    lm = C.lg(p.reindex(ids).mean(axis=1).to_numpy())
    inf = info.loc[ids]
    s = np.array([params[int(Y)][0] if t == "atp" else params[int(Y)][1] for Y, t in zip(inf["season"], inf["tour"])])
    b = np.array([params[int(Y)][2] for Y in inf["season"]])
    zz = np.zeros(len(ids)) if z is None else np.where(inf["tour"].to_numpy() == "wta", 0.0,
                                                       z.reindex(ids).to_numpy(float))
    return expit(s * lm + b * zz), expit(s[:, None] * lp + (b * zz)[:, None])


def close_forecast(info: pd.DataFrame, col: str, test, ids: pd.Index):
    """A frame's closing price, recalibrated with one slope per tour fitted on 2019 .. Y - 1 (debut seasons out)."""
    par = {}
    for Y in test:
        hist = info.index[(info["season"] < Y) & ~info["debut"] & np.isfinite(info[col])]
        atp = (info.loc[hist, "tour"] == "atp").to_numpy()
        e = C.lg(info.loc[hist, col].to_numpy())
        beta, _ = C.fit_logistic(np.column_stack([np.where(atp, e, 0.0), np.where(~atp, e, 0.0)]),
                                 info.loc[hist, "y"].to_numpy(float))
        par[int(Y)] = (float(beta[0]), float(beta[1]))
    inf = info.loc[ids]
    s = np.array([par[int(Y)][0] if t == "atp" else par[int(Y)][1] for Y, t in zip(inf["season"], inf["tour"])])
    q = expit(s * C.lg(inf[col].to_numpy()))
    return q, q[:, None]


def reading(lo: float, hi: float) -> str:
    return "better" if lo > 0 else "worse" if hi < 0 else "unresolved"


def p_better(estimate: float, se: float, blocks: int) -> float:
    """P(better): the t CDF of estimate / se on blocks - 1 degrees of freedom. Not the chance that the change helps next
    season. NaN when the forecasts are identical (estimate 0, se 0)."""
    if se > 0:
        return float(student_t.cdf(estimate / se, blocks - 1))
    return 1.0 if estimate > 0 else 0.0 if estimate < 0 else np.nan


def paired(info: pd.DataFrame, ids: pd.Index, base, arm, matched: bool = True) -> dict:
    """1000 x mean(LL(base) - LL(arm)): positive = the arm (the candidate) better; score.paired_stats' interval, its seed
    term paired by seed when both forecasts come from seeds 0-3 (matched; a price has no seeds: matched=False)."""
    y = info.loc[ids, "y"].to_numpy(float)
    (qb, qbk), (qa, qak) = base, arm
    r = S.paired_stats(C.ll(qb, y), C.ll(qa, y), S.seed_loss(qbk, y), S.seed_loss(qak, y),
                       info.loc[ids, "block"].to_numpy(), info.loc[ids, "week"].to_numpy(), matched_seeds=matched)
    out = {k: r[k] for k in ("matches", "estimate", "lo", "hi", "se")}
    out["p_better"] = p_better(r["estimate"], r["se"], r["blocks"])
    out["reading"] = reading(r["lo"], r["hi"])
    out.update({k: r[k] for k in ("lo_week", "hi_week", "blocks", "seed_term", "se_unpaired", "lo_unpaired",
                                  "hi_unpaired", "lo_week_unpaired", "hi_week_unpaired")})
    return out


def populations(info: pd.DataFrame, test) -> list[tuple[str, str, np.ndarray]]:
    """(group, name, mask): the primary three, each level, each season; debut seasons out throughout."""
    keep = ~info["debut"].to_numpy() & info["season"].isin(list(test)).to_numpy()
    tour = info["tour"].to_numpy()
    out = [("primary", "both tours", keep), ("primary", "men", keep & (tour == "atp")),
           ("primary", "women", keep & (tour == "wta"))]
    out += [("level", L, keep & (info["level"].to_numpy() == L)) for L in ("Slams", "1000s", "500s", "250s", "Finals")]
    out += [("season", str(Y), ~info["debut"].to_numpy() & (info["season"].to_numpy() == Y)) for Y in test]
    return out


def score(info: pd.DataFrame, p_ref: pd.DataFrame, p_cand: pd.DataFrame, z_ref: pd.Series, z_cand: pd.Series,
          test) -> tuple[pd.DataFrame, dict]:
    eta_ref = pd.Series(C.lg(p_ref.mean(axis=1).to_numpy()), index=p_ref.index)
    eta_cand = pd.Series(C.lg(p_cand.mean(axis=1).to_numpy()), index=p_cand.index)
    models = {"reference stage 1": (p_ref, walk_forward(eta_ref, info, None, test), None),
              "candidate stage 1": (p_cand, walk_forward(eta_cand, info, None, test), None),
              "reference": (p_ref, walk_forward(eta_ref, info, z_ref, test), z_ref),
              "candidate": (p_cand, walk_forward(eta_cand, info, z_cand, test), z_cand)}
    rows = []
    for group, name, mask in populations(info, test):
        ids = info.index[mask]
        if len(ids) == 0:
            continue
        fc = {m: forecasts(p, info, par, z, ids) for m, (p, par, z) in models.items()}
        rows.append({"group": group, "population": name, "comparison": "both stages: candidate vs reference",
                     **paired(info, ids, fc["reference"], fc["candidate"])})
        rows.append({"group": group, "population": name, "comparison": "stage 1: candidate vs reference",
                     **paired(info, ids, fc["reference stage 1"], fc["candidate stage 1"])})
        if group == "primary":
            rows.append({"group": group, "population": name,
                         "comparison": "for scale: reference vs its calibrated close",
                         **paired(info, ids, close_forecast(info, "p_ref", test, ids), fc["reference"], matched=False)})
            rows.append({"group": group, "population": name,
                         "comparison": "for scale: candidate vs its calibrated close",
                         **paired(info, ids, close_forecast(info, "p_cand", test, ids), fc["candidate"], matched=False)})
    coef = {m: {str(Y): v for Y, v in par.items()} for m, (_, par, _) in models.items()}
    return pd.DataFrame(rows), coef


# ------------------------------------------------------------------------------------------------

def compare(cand_arg: str, speed: str | None = None, through: int = THROUGH, out: str | None = None) -> dict:
    name, P_cand, folder = candidate(cand_arg)
    P_ref = R.paths("reference")
    if not R.MANIFEST.exists():
        raise SystemExit("the reference is not frozen yet: ./python.sh src/eda/current_best_model/reference.py --freeze")
    if folder is None:
        out_dir = R.REF / "comparisons" / name
    else:
        out_dir = folder / f"vs_reference_{R.REF_ID}"
    out_dir = Path(out) if out else out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    test = tuple(range(SCORE_FROM, through + 1))
    if through > THROUGH:
        C.log(f"--through {through} reads 2025-2026 results: the proposed clean holdout "
              "(docs/studies/clean_holdout_rebuild/); record this look")
    ref, cand = inputs_frame(P_ref), inputs_frame(P_cand)
    C.log(f"reference {len(ref):,} matches, candidate {name} {len(cand):,}, both {len(ref.index.intersection(cand.index)):,}")
    # Part 1 (no result read)
    by_season, per_input = input_drift(ref, cand)
    profile = pd.concat([season_profile(ref, "reference"), season_profile(cand, "candidate")], ignore_index=True)
    cov = coverage(ref, cand)
    by_season.to_csv(out_dir / "inputs_by_season.csv", index=False)
    per_input.to_csv(out_dir / "inputs.csv", index=False)
    profile.to_csv(out_dir / "season_profile.csv", index=False)
    cov.to_csv(out_dir / "coverage.csv", index=False)
    # Part 2 (results of seasons <= through)
    info = scoring_info(ref, cand, outcomes(P_ref, through), outcomes(P_cand, through), through)
    seasons = tuple(range(FIT_FROM, through + 1))
    p_ref = seed_table(P_ref, ref, seasons).reindex(info.index)
    p_cand = seed_table(P_cand, cand, seasons).reindex(info.index)
    if p_ref.isna().any().any() or p_cand.isna().any().any():
        raise SystemExit("forecasts missing on matches both frames hold")
    z_ref = R.speed_column("reference")
    if speed:
        z_src = Path(speed) if Path(speed).is_absolute() else ROOT / speed
    elif cand_arg == "previous":
        z_src = "the previous model's column (frozen speed/columns.parquet)"
    elif folder is not None and (folder / "speed_columns.parquet").exists():
        z_src = folder / "speed_columns.parquet"
    else:
        z_src = None
    if isinstance(z_src, Path):
        z_cand = pd.read_parquet(z_src, columns=["match_id", "spd_L_B"]).astype({"match_id": str}) \
            .set_index("match_id")["spd_L_B"]
    elif cand_arg == "previous":
        z_cand = R.speed_column("previous")
    else:
        z_cand = z_ref
    scores, coef = score(info, p_ref, p_cand, z_ref, z_cand, test)
    scores.to_csv(out_dir / "scores.csv", index=False)
    primary = scores[(scores["group"] == "primary")]
    summary = {
        "generated_at": R.now(), "reference": R.REF_ID, "candidate": name,
        "candidate_frame": R.rel(P_cand.model_frame), "candidate_frame_sha256": C.sha256_file(P_cand.model_frame),
        "speed_column": "the reference's" if z_src is None else (z_src if isinstance(z_src, str) else R.rel(z_src)),
        "results_read_through": through, "scored_seasons": [test[0], test[-1]],
        "unit": "mLL per match; positive = the candidate has the lower log loss (better); reading 'better' or 'worse' "
                "when the 95% interval clears 0, otherwise 'unresolved'; p_better = the t CDF of estimate / se on "
                "blocks - 1 df (flat prior, this one test; null for identical forecasts); model against model: seed "
                "term paired by seed (seeds 0-3), against a close: unpaired; *_unpaired = the interval as read before "
                "9 Oct 2026",
        "primary": [{k: None if isinstance(v, float) and not np.isfinite(v) else v for k, v in r.items()}
                    for r in primary.to_dict("records")],
        "inputs_flagged": per_input.loc[per_input["flag"].isin(["uneven", "every season"]),
                                        ["input", "flag", "flagged_tour_seasons", "flagged"]].to_dict("records"),
        "inputs_changed": int((per_input["changed_share"].fillna(0) > 0).sum()),
        "inputs_only_in_one": per_input.loc[per_input["flag"].astype(str).str.startswith("only"),
                                            ["input", "flag"]].to_dict("records"),
        "coverage": {"both": int(cov.get("both", pd.Series(dtype=int)).sum()),
                     "reference only": int(cov.get("reference only", pd.Series(dtype=int)).sum()),
                     "candidate only": int(cov.get("candidate only", pd.Series(dtype=int)).sum())},
        "coefficients_last_season": {m: v[str(test[-1])] for m, v in coef.items()},
    }
    C.write_json(out_dir / "summary.json", summary)
    pd.set_option("display.width", 220)
    print(primary[["population", "comparison", "matches", "estimate", "lo", "hi", "p_better", "reading"]].round(3)
          .to_string(index=False))
    flagged = summary["inputs_flagged"]
    print(f"inputs changed: {summary['inputs_changed']} of {len(per_input)}; flagged: "
          + (", ".join(f"{r['input']} ({r['flag']}, {r['flagged_tour_seasons']})" for r in flagged) or "none"))
    print(f"written: {R.rel(out_dir)}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--candidate", required=True, help="a built folder, or previous / reference")
    ap.add_argument("--speed", help="the candidate's stage-2 column (parquet: match_id, spd_L_B)")
    ap.add_argument("--through", type=int, default=THROUGH, help="the last season whose results are read")
    ap.add_argument("--out", help="the output folder")
    a = ap.parse_args()
    compare(a.candidate, a.speed, a.through, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
