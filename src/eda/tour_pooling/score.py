"""Scoring of the tour-pooling study (docs/studies/tour_pooling/design.md): each arm and composite against the current
instance, with current_best_model/compare.py's recipe unchanged.

The owner's questions (9 Oct 2026): would one model per tour beat the single model trained on both tours, season by
season from 2022? What is a men/women input worth? Can a tour's model borrow the other tour's matches where they help?
notour's reading answers the second only in part: it is the explicit tour flag's value, given the model still recognises
the tour (indoor is missing on every women's match; box-score scales differ) (design.md, red team B2).

The yardstick, "pooled": the current instance, data/studies/current_best_model/pinnacle_first_2026-10-09/ (one model on
both tours, `tour` among its 58 inputs), seeds 0-3, read only. The frozen reference of 8 Oct 2026 is scored too, for the
record (W2 only).

The arms: the fits in data/studies/tour_pooling/fits/<arm>__<tour>__<Y>__seed<k>.npz (common.py; tour atp or wta for
split, borrow25, borrow50, borrowsim and sizectl, both for notour and aligned). common.ARMS's "pooled" is not an arm here:
its one file (2022, seed 0) is the runner's reproduction of the instance's stored fit (runner_reproduction). sizectl is
a control: scored against pooled like the arms, never a candidate of select. An arm is scored when every file of seasons
2019-2026 and seeds 0-3 exists ("complete"); the others are listed. Every file is checked first (read_fit), and an arm
with a failing file is refused, never scored:
    * its td ids are the frame's season-Y matches of its tour, in frame order (common.query_mask);
    * its stored columns are the arm's inputs (common.inputs); its arm, tour, season, seed and settings are its name's;
    * its training shape is [common.train_mask(...).sum(), inputs], and its training rows by tour and season are the
      mask's;
    * borrowsim: its similarity cache, common.sim_path(tour, Y) (data/studies/tour_pooling/borrow_sim_v3/
      <tour>__<Y>.parquet), must exist (the scorer never builds one) and hash to the fit's draw.sim_cache_sha256;
      common.sim_inclusion refuses a cache whose record names another version, other features or another frame;
    * it was fitted on the instance's frame (model_frame_sha256);
    * its td block is the k matches as stored, then swapped: P(A wins) = (p[:k] + 1 - p[k:]) / 2.

The composites (no new fits; design.md):
    blend          per tour, logit q = a_T eta_split + c_T eta_pooled + b spd_L (0 for women): the five coefficients
                   fitted jointly without intercept on 2019 .. Y - 1 (debut seasons out), b shrunk as stage 2's b (tau
                   0.05); seed k's forecast applies the same coefficients to seed k of each model. Its stage 1 is the
                   same stack without b. Reported with w_T = a_T / (a_T + c_T), the own-tour share, and its delta-method
                   SE (red team S3: a and c are identified only along eta_split - eta_pooled). Needs split
    blend_control  the same blend with split replaced by the instance's pooled seeds 4-7: seed k is pooled seed 4 + k
                   with pooled seed k (red team S4: how much of a blend gain is plain seed averaging, 8 fits against 4)
    select         for each tour and season Y in 2021-2026, the arm among pooled, split, borrow25, borrow50, borrowsim
                   and aligned with the lowest mean both-stage log loss on that tour's scored matches of 2020 .. Y - 1
                   (debut seasons out) supplies season Y's forecasts: both stages and stage 1, each seed too (ties go to
                   the earlier-listed arm). 2020 has no earlier scored season: pooled. Scored only when all six are
                   complete (red team S9); so is the winner's luck

Post-hoc controls (the lead, 9 Oct 2026, added after the first blend reading, because blend_control's weights are
unidentified: pooled seeds 4-7 and 0-3 are near duplicates). Equal-weight and unfitted; never select candidates, never in
the winner's-luck family. Each averages eight fits in log-odds, and its pseudo-seed k, the seed term's, is the log-odds
mean of a pair (so the four pseudo-seeds average to the eight); then the decided two stages like any model
(staged_mean: compare.walk_forward on that mean, compare.forecasts on it and on the pseudo-seeds):
    pooled8            the instance's pooled seeds 0-7; pseudo-seed k = pooled seeds k and 4 + k
    avg_split_pooled   split seeds 0-3 with pooled seeds 0-3; pseudo-seed k = split seed k and pooled seed k. Needs split

The recipe: compare.py's functions, unchanged (scoring_info, walk_forward, forecasts, close_forecast, paired,
populations). Each model is the mean of its seeds 0-3; the per-tour calibration slopes and stage 2's b are fitted
walk-forward on 2019 .. Y - 1, debut seasons out, b shrunk with tau 0.05, on each model's own forecasts. Stage 2's speed
column is the template's current one, data/studies/infosys_atp_backfill/speed_columns_augmented.parquet (spd_L_B), the
same for every model. Matches without a value (40 women's matches of June 2026) are left out, as pinnacle_first/
backtest.py leaves them out.

Results. Matches from 29 Jul 2026 are the proposed sealed holdout: a_won is read with a filter on tournament_date applied
before the column is read (outcomes), and no later match enters any table. Read: 2019 .. 28 Jul 2026 (2019 feeds the
walk-forward fits only).
    W1   2022 .. 28 Jul 2026: the owner's seasons, the declared primary window
    W2   2020-2024: compare.py's default window
Paired log loss in mLL per match, 1000 x mean(LL_base - LL_candidate): POSITIVE = THE CANDIDATE HAS THE LOWER LOG LOSS
(better). 95% intervals over four-week blocks plus the seed term: paired by seed between two models (seeds 0-3), unpaired
against a price. Reading: "better" / "worse" when the interval clears 0, otherwise "unresolved" with p_better.
    each arm, control and composite   both stages and stage 1 against pooled: both tours, men, women; each level; each
                                      season
    for scale        every model against the calibrated close (the instance's Pinnacle-first price, one slope per tour
                     fitted on 2019 .. Y - 1): both tours, men, women
    for the record   every model against the frozen reference, both stages, W2 (the reference with the same speed column)
    contrasts        both stages, both windows, both tours, men, women:
                         size effect   pooled (candidate) against sizectl (base): more rows at the same mix
                         mix effect    split (candidate) against sizectl (base): own tour only, at the same size
                         each borrowing arm (borrow25, borrow50, borrowsim, aligned) against split (base): adding the
                         other tour's rows to the own-tour model (aligned: all of them, in units of each tour's spread)
                         blend (candidate) against blend_control (base): the own-tour model beyond seed averaging
    post-hoc controls   both stages, both windows, both tours, men, women; role "post-hoc control" in scores.csv:
                         pooled8 against pooled: what four more seeds alone are worth
                         avg_split_pooled against pooled8: the own-tour model's diversity at equal fit count
                         avg_split_pooled against pooled
    realisation     training_window/score.realisation: c in logit P = logit q_close + c (logit q - logit q_close), per
                     model, window and tour (1 = right-sized moves away from the close; below 1 = too far)
    winner's luck    the best of borrow25, borrow50, borrowsim, aligned, blend and select on the primary (W1, both tours,
                     both stages): sel = se x 1.27 (K = 6, adoption framework section 4), est - sel

Checks. Before anything is written (a failure stops the run): pooled against itself is exactly 0 with a zero-width
interval in every row; this scorer's own path reproduces the decided comparison (the instance against the reference, W2,
the reference's speed column: <instance>/vs_reference_2026-10-08/summary.json), all twelve primary rows within 1e-9.
Reported, not stopping the run (exit code 2 when it fails, as for a refused arm): the runner's reproduction, its
pooled__both__2022__seed0 p_td against the instance's fits/model__2022__seed0 p_td (ids equal, max |diff| within
serve_speed_tabpfn.common.REPRO_TOL, 1e-6).

Writes data/studies/tour_pooling/scores/: scores.csv, composites.csv (blend's and blend_control's coefficients by stage,
tour and season; select's choices), realisation.csv, summary.json and forecasts.parquet (one row per match of 2019 .. 28
Jul 2026 with a speed value: q_<model> both stages, q1_<model> stage 1, q_<model>_s0..s3 per seed or pseudo-seed, the
post-hoc controls included, q_close; NaN in 2019).
Run: ./python.sh src/eda/tour_pooling/score.py [--status]      (--status: which arms are complete; reads no result)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import expit

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402
from src.eda.tour_pooling import common as C  # noqa: E402
from src.eda.training_window.score import realisation  # noqa: E402

SC = C.SC
SCORES = C.OUT / "scores"
SPEED = ROOT / "data" / "studies" / "infosys_atp_backfill" / "speed_columns_augmented.parquet"
DECIDED = C.INSTANCE / "vs_reference_2026-10-08" / "summary.json"
SEALED_FROM = pd.Timestamp("2026-07-29")
FIT_SEASONS = C.SEASONS                      # 2019-2026: every model's fitted seasons
TEST = tuple(range(2020, 2027))              # the seasons with a walk-forward forecast (2019 feeds the fits only)
WINDOWS = {"W1": tuple(range(2022, 2027)), "W2": tuple(range(2020, 2025))}
PRIMARY = "W1"
ARMS = tuple(a for a in C.ARMS if a != "pooled")   # common.ARMS's "pooled" is the runner's reproduction, never an arm
CONTROLS = ("sizectl",)                      # scored against pooled; never a select candidate
POSTHOC_CONTROLS = ("pooled8", "avg_split_pooled")   # the lead's equal-weight controls: never candidates, never in LUCK
BORROWING = ("borrow25", "borrow50", "borrowsim", "aligned")     # the declared borrowing arms, also read against split
SELECT_POOL = ("pooled", "split", "borrow25", "borrow50", "borrowsim", "aligned")
SELECT_FROM = 2021
LUCK = ("borrow25", "borrow50", "borrowsim", "aligned", "blend", "select")
LUCK_M = 1.27                                # m_K for K = 6
REPRO = ("pooled", "both", 2022, 0)          # the runner's reproduction of the instance's stored fit
CONTROL_SEEDS = (4, 5, 6, 7)                 # blend_control: seed k of its first model is pooled seed 4 + k
TOL = 1e-9
FLAG = ("the explicit tour flag's value, given the model still recognises the tour (indoor is missing on every women's "
        "match; box-score scales differ)")
VS_POOLED, STAGE1 = "both stages: arm vs pooled", "stage 1: arm vs pooled"
VS_CLOSE, VS_REF = "for scale: arm vs its calibrated close", "both stages: arm vs reference"
SIZE, MIX = "size effect, both stages: pooled vs sizectl", "mix effect, both stages: split vs sizectl"
VS_SPLIT, VS_CONTROL = "both stages: arm vs split", "both stages: blend vs blend_control"
POSTHOC = "post-hoc control"                 # the role of the lead's equal-weight controls (added after the blend read)
P8 = "post-hoc control, both stages: pooled8 vs pooled"
AVG8 = "post-hoc control, both stages: avg_split_pooled vs pooled8"
AVG = "post-hoc control, both stages: avg_split_pooled vs pooled"


@dataclass
class Fc:
    """One model's forecasts on every info row, NaN where it has none: both stages (q, per seed qk) and stage 1."""
    q: np.ndarray
    qk: np.ndarray
    q1: np.ndarray
    q1k: np.ndarray

    @classmethod
    def empty(cls, n: int, k: int = len(C.SEEDS)) -> "Fc":
        return cls(np.full(n, np.nan), np.full((n, k), np.nan), np.full(n, np.nan), np.full((n, k), np.nan))

    def both(self, m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return self.q[m], self.qk[m]

    def stage1(self, m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        return self.q1[m], self.q1k[m]

    def take(self, other: "Fc", m: np.ndarray) -> None:
        self.q[m], self.qk[m], self.q1[m], self.q1k[m] = other.q[m], other.qk[m], other.q1[m], other.q1k[m]


# ------------------------------------------------------------------------------------------------
# Results, the speed column and the matches

def outcomes(path: Path) -> pd.Series:
    """a_won of the matches before SEALED_FROM only: later rows are filtered out on tournament_date before the column is
    read (pinnacle_first/backtest.outcomes)."""
    f = pd.read_parquet(path, columns=["match_id", "tournament_date", "a_won"],
                        filters=[("tournament_date", "<", SEALED_FROM)])
    if len(f) and pd.Timestamp(f["tournament_date"].max()) >= SEALED_FROM:
        raise RuntimeError("a result from the sealed holdout was read")
    return pd.Series(f["a_won"].astype(float).to_numpy(), index=f["match_id"].astype(str).to_numpy())


def speed(path: Path = SPEED) -> pd.Series:
    s = pd.read_parquet(path, columns=["match_id", "spd_L_B"])
    s["match_id"] = s["match_id"].astype(str)
    if s["match_id"].duplicated().any():
        raise RuntimeError(f"{path.name}: duplicate match ids")
    return s.set_index("match_id")["spd_L_B"]


def load_info(z: pd.Series) -> tuple[pd.DataFrame, dict, pd.DataFrame, C.SC.Paths, pd.DataFrame, C.SC.Paths]:
    """compare.scoring_info on the instance's matches of 2019 .. 28 Jul 2026 with a speed value: the facts and the close
    (p_cand) from the instance's frame; the reference's close (p_ref) is used only to reproduce the decided comparison.
    Returns (info, facts, instance frame, its paths, reference frame, its paths)."""
    _, P_inst, _ = CMP.candidate(str(C.INSTANCE))
    P_ref = R.paths("reference")
    if not R.MANIFEST.exists():
        raise SystemExit("the frozen reference is missing (current_best_model/reference.py)")
    inst, ref = CMP.inputs_frame(P_inst), CMP.inputs_frame(P_ref)
    y_inst, y_ref = outcomes(P_inst.model_frame), outcomes(P_ref.model_frame)
    season = inst["season"].to_numpy()
    span = (season >= FIT_SEASONS[0]) & (season <= FIT_SEASONS[-1]) & (inst["tournament_date"] < SEALED_FROM).to_numpy()
    has_z = np.isfinite(z.reindex(inst.index).to_numpy(float))
    keep = inst.index[span & has_z]
    if not keep.isin(ref.index).all():
        raise RuntimeError("the reference's frame lacks some of the instance's matches")
    shared = ["tour", "season", "tournament_date", "debut_season", "in_level"]
    if not ref.loc[keep, shared].equals(inst.loc[keep, shared]):
        raise RuntimeError("the instance's and the reference's frames disagree on a match's facts")
    info = CMP.scoring_info(ref.loc[keep], inst.loc[keep], y_ref, y_inst, FIT_SEASONS[-1], base="candidate")
    info.index.name = "match_id"
    if len(info) != len(keep) or pd.Timestamp(info["tournament_date"].max()) >= SEALED_FROM:
        raise RuntimeError("the scored matches are not the instance's matches of 2019 .. 28 Jul 2026")
    if not np.isfinite(info["p_cand"].to_numpy(float)).all():
        raise RuntimeError("the instance's close is missing on a scored match")
    women = (info["tour"] == "wta").to_numpy()
    if (z.reindex(info.index).to_numpy(float)[women] != 0).any():
        raise RuntimeError("the speed column is not 0 for every woman (walk_forward fits it on both tours)")
    left = inst.loc[span & ~has_z, ["tour", "season", "tournament_date"]]
    facts = {"matches": int(len(info)), "first_day": str(info["tournament_date"].min().date()),
             "last_day": str(info["tournament_date"].max().date()),
             "by_season": {str(k): int(v) for k, v in info["season"].value_counts().sort_index().items()},
             "sealed_from": str(SEALED_FROM.date()),
             "sealed_matches_not_read": int((inst["tournament_date"] >= SEALED_FROM).sum()),
             "left_out_without_speed_value": {"matches": int(len(left)),
                                              "by_tour": {k: int(v) for k, v in left["tour"].value_counts().items()},
                                              "days": sorted({str(d.date()) for d in left["tournament_date"]})}}
    return info, facts, inst, P_inst, ref, P_ref


# ------------------------------------------------------------------------------------------------
# The arms' fits

def needed(arm: str) -> list[tuple[str, int, int]]:
    return [(t, Y, k) for Y in FIT_SEASONS for k in C.SEEDS for t in C.model_tours(arm)]


def status(arm: str) -> dict:
    need = needed(arm)
    missing = [[t, Y, k] for t, Y, k in need if not C.fit_path(arm, t, Y, k).exists()]
    return {"arm": arm, "files_needed": len(need), "files_present": len(need) - len(missing), "complete": not missing,
            "first_missing": missing[:6]}


_CACHE_SHA: dict = {}


def cache_sha(path: Path) -> str:
    """SHA-256 of a similarity cache file (cached by path, size and modification time)."""
    st = path.stat()
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key not in _CACHE_SHA:
        _CACHE_SHA[key] = C.sha256_file(path)
    return _CACHE_SHA[key]


def read_fit(path: Path, frame: pd.DataFrame, arm: str, tour: str, season: int, seed: int,
             frame_sha: str) -> pd.Series:
    """Symmetrised P(A wins) by match id from one of the study's fit files, after its checks (module docstring).
    frame: common.load_frame() (no result). Raises RuntimeError on a failed check."""
    with np.load(path, allow_pickle=False) as zf:
        meta = json.loads(str(zf["meta"]))
        p = zf["p_td"].astype(float)
        ids = zf["ids_td"].astype(str)
    name, cols = path.name, C.inputs(arm)
    want = {"arm": arm, "tour": tour, "season": season, "seed": seed, "config": {**SC.CONFIG, "random_state": seed}}
    wrong = [k for k, v in want.items() if meta.get(k) != v]
    if wrong:
        raise RuntimeError(f"{name}: stored {wrong} differ from the file's arm, tour, season, seed or settings")
    if meta.get("model_frame_sha256") != frame_sha:
        raise RuntimeError(f"{name}: fitted on another frame (model_frame_sha256 {meta.get('model_frame_sha256')})")
    if list(meta.get("columns") or []) != cols:
        raise RuntimeError(f"{name}: stored columns differ from the arm's inputs")
    expected = frame.loc[C.query_mask(frame, tour, season), "match_id"].astype(str).to_numpy()
    if not np.array_equal(ids, expected):
        raise RuntimeError(f"{name}: td ids are not the frame's season-{season} matches of {tour}, in frame order")
    k = len(ids)
    if len(p) != 2 * k:
        raise RuntimeError(f"{name}: the td block is not the {k} matches as stored, then swapped ({len(p)} values)")
    if not (np.isfinite(p).all() and (p >= 0).all() and (p <= 1).all()):
        raise RuntimeError(f"{name}: probabilities outside [0, 1]")
    if arm == "borrowsim":
        cache = C.sim_path(tour, season)
        if not cache.exists():                   # checked first: common.train_mask would build a missing cache
            raise RuntimeError(f"{name}: its similarity cache {R.rel(cache)} is missing (the scorer never builds one)")
        stored = (meta.get("draw") or {}).get("sim_cache_sha256")
        if stored != cache_sha(cache):
            raise RuntimeError(f"{name}: drawn from another similarity cache (sim_cache_sha256 {stored}, the cache's "
                               f"{cache_sha(cache)})")
    tr = C.train_mask(frame, arm, tour, season, seed)         # borrowsim: sim_inclusion checks the cache's record
    if list(meta.get("train_shape", [])) != [int(tr.sum()), len(cols)]:
        raise RuntimeError(f"{name}: training shape {meta.get('train_shape')} is not the arm's "
                           f"{[int(tr.sum()), len(cols)]}")
    if "train_rows_by_tour_season" in meta:
        by = frame.loc[tr].groupby(["tour", "season"]).size()
        if meta["train_rows_by_tour_season"] != {f"{t} {int(s)}": int(v) for (t, s), v in by.items()}:
            raise RuntimeError(f"{name}: training rows by tour and season differ from the arm's")
    return pd.Series(SC.symmetrize(p[:k], p[k:]), index=pd.Index(ids, name="match_id"))


def arm_table(arm: str, frame: pd.DataFrame, frame_sha: str, seasons=FIT_SEASONS) -> pd.DataFrame:
    """Rows: every frame match of the seasons, by match id (a per-tour arm's two models joined); columns: seeds 0-3."""
    parts = []
    for Y in seasons:
        per = {k: pd.concat([read_fit(C.fit_path(arm, t, Y, k), frame, arm, t, Y, k, frame_sha)
                             for t in C.model_tours(arm)]) for k in C.SEEDS}
        parts.append(pd.DataFrame(per))
    table = pd.concat(parts)
    want = frame.loc[frame["season"].isin(list(seasons)), "match_id"].astype(str)
    if table.index.duplicated().any() or len(table) != len(want) or not table.index.isin(want).all():
        raise RuntimeError(f"{arm}: the joined forecasts are not each frame match of the seasons once")
    if list(table.columns) != list(C.SEEDS) or table.isna().to_numpy().any():
        raise RuntimeError(f"{arm}: seeds missing")
    return table


def files_sha(arm: str) -> str:
    """SHA-256 over the arm's fit files in order (which forecasts this run scored)."""
    h = hashlib.sha256(f"tour_pooling/{arm}".encode())
    for t, Y, k in needed(arm):
        path = C.fit_path(arm, t, Y, k)
        h.update(path.name.encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def runner_reproduction(frame: pd.DataFrame, frame_sha: str, instance_fits: Path = C.INSTANCE / "fits") -> dict:
    """The runner's pooled job (2022, seed 0) against the instance's stored fit: after read_fit's checks, its raw p_td
    (as stored, then swapped) against the instance's, ids equal, max |diff| within serve_speed_tabpfn's REPRO_TOL."""
    arm, tour, season, seed = REPRO
    path, inst = C.fit_path(arm, tour, season, seed), instance_fits / f"model__{season}__seed{seed}.npz"
    out = {"what": "the tour-pooling runner's pooled job (2022, seed 0) against the instance's stored fit, raw p_td",
           "file": R.rel(path), "against": R.rel(inst), "tolerance": SC.REPRO_TOL}
    if not path.exists():
        return {**out, "status": "not written yet", "passed": None}
    try:
        read_fit(path, frame, arm, tour, season, seed, frame_sha)
    except RuntimeError as e:
        return {**out, "status": f"refused: {e}", "passed": False}
    with np.load(path, allow_pickle=False) as a, np.load(inst, allow_pickle=False) as b:
        ids_equal = bool(np.array_equal(a["ids_td"].astype(str), b["ids_td"].astype(str)))
        pa, pb = a["p_td"].astype(float), b["p_td"].astype(float)
    diff = float(np.abs(pa - pb).max()) if ids_equal and pa.shape == pb.shape else float("inf")
    return {**out, "status": "compared", "ids_equal": ids_equal, "values": int(len(pa)), "max_abs_diff_p_td": diff,
            "passed": bool(ids_equal and diff <= SC.REPRO_TOL)}


# ------------------------------------------------------------------------------------------------
# Forecasts: compare.py's two stages on a seed table, the close and the composites

def staged(p: pd.DataFrame, info: pd.DataFrame, z: pd.Series) -> tuple[Fc, dict]:
    """compare.py's recipe on one model: walk_forward (both stages; stage 1 = the slopes alone) for each season of TEST,
    and forecasts on every info row of those seasons."""
    p = p.reindex(info.index)
    if p.isna().to_numpy().any():
        raise RuntimeError(f"forecasts missing for {int(p.isna().any(axis=1).sum())} scored matches")
    eta = pd.Series(SC.lg(p.mean(axis=1).to_numpy()), index=p.index)
    par2, par1 = CMP.walk_forward(eta, info, z, TEST), CMP.walk_forward(eta, info, None, TEST)
    m = info["season"].isin(TEST).to_numpy()
    ids = info.index[m]
    fc = Fc.empty(len(info))
    fc.q[m], fc.qk[m] = CMP.forecasts(p, info, par2, z, ids)
    fc.q1[m], fc.q1k[m] = CMP.forecasts(p, info, par1, None, ids)
    return fc, {"both stages": par2, "stage 1": par1}


def logodds_mean(p_a: pd.DataFrame, p_b: pd.DataFrame, index: pd.Index) -> tuple[pd.Series, pd.DataFrame]:
    """The equal-weight mean in log-odds of two four-seed tables (columns 0-3): (the mean of the eight, the pseudo-seeds
    eta_k = (logit a_k + logit b_k) / 2). The pseudo-seeds' mean is the eight's mean."""
    a, b = p_a.reindex(index), p_b.reindex(index)
    for t in (a, b):
        if list(t.columns) != list(C.SEEDS) or t.isna().to_numpy().any():
            raise RuntimeError("a post-hoc control needs both models' seeds 0-3 on every scored match")
    eta_k = pd.DataFrame((SC.lg(a.to_numpy()) + SC.lg(b.to_numpy())) / 2, index=index, columns=list(C.SEEDS))
    return eta_k.mean(axis=1), eta_k


def staged_mean(eta: pd.Series, eta_k: pd.DataFrame, info: pd.DataFrame, z: pd.Series) -> tuple[Fc, dict]:
    """compare.py's recipe on a model given in log-odds (the post-hoc controls): walk_forward on eta, unchanged, and
    compare.forecasts, unchanged, fed expit(eta) for the forecast and expit(eta_k) for the pseudo-seeds (so its logit of
    the one-column mean is eta itself)."""
    eta, eta_k = eta.reindex(info.index), eta_k.reindex(info.index)
    par2, par1 = CMP.walk_forward(eta, info, z, TEST), CMP.walk_forward(eta, info, None, TEST)
    m = info["season"].isin(TEST).to_numpy()
    ids = info.index[m]
    point = pd.DataFrame({0: expit(eta.to_numpy())}, index=info.index)
    seeds = pd.DataFrame(expit(eta_k.to_numpy()), index=info.index, columns=eta_k.columns)
    fc = Fc.empty(len(info))
    fc.q[m], fc.qk[m] = CMP.forecasts(point, info, par2, z, ids)[0], CMP.forecasts(seeds, info, par2, z, ids)[1]
    fc.q1[m], fc.q1k[m] = CMP.forecasts(point, info, par1, None, ids)[0], CMP.forecasts(seeds, info, par1, None, ids)[1]
    return fc, {"both stages": par2, "stage 1": par1}


def close(info: pd.DataFrame, col: str = "p_cand") -> Fc:
    """compare.close_forecast: the frame's close with one slope per tour fitted on 2019 .. Y - 1 (one 'seed')."""
    m = info["season"].isin(TEST).to_numpy()
    q, qk = CMP.close_forecast(info, col, TEST, info.index[m])
    fc = Fc.empty(len(info), 1)
    fc.q[m], fc.qk[m], fc.q1[m], fc.q1k[m] = q, qk, q, qk
    return fc


def shrink(b: float, se: float) -> float:
    """compare.walk_forward's shrinkage of b (prior N(0, tau^2), tau 0.05)."""
    return float(b) * SC.TAU_NUDGE ** 2 / (SC.TAU_NUDGE ** 2 + float(se) ** 2)


def control_table(p47: pd.DataFrame) -> pd.DataFrame:
    """The instance's pooled seeds 4-7 relabelled 0-3: seed k of blend_control's first model is pooled seed 4 + k."""
    if list(p47.columns) != list(CONTROL_SEEDS):
        raise RuntimeError(f"blend_control needs pooled seeds {CONTROL_SEEDS}, got {list(p47.columns)}")
    out = p47.copy()
    out.columns = list(C.SEEDS)
    return out


def blend(info: pd.DataFrame, z: pd.Series, p_first: pd.DataFrame, p_pool: pd.DataFrame, name: str = "blend",
          first: str = "split") -> tuple[Fc, list[dict]]:
    """The blend composite (module docstring) of p_first (split; blend_control: pooled seeds 4-7) with pooled seeds
    0-3, and its coefficients by stage, tour and season: a, c, their SEs, w = a / (a + c) and its delta-method SE."""
    ps, pp = p_first.reindex(info.index), p_pool.reindex(info.index)
    if ps.isna().to_numpy().any() or pp.isna().to_numpy().any():
        raise RuntimeError(f"{name}: forecasts missing")
    es, ep = SC.lg(ps.mean(axis=1).to_numpy()), SC.lg(pp.mean(axis=1).to_numpy())
    esk, epk = SC.lg(ps.to_numpy()), SC.lg(pp.to_numpy())
    atp = (info["tour"] == "atp").to_numpy()
    zz = np.where(atp, z.reindex(info.index).to_numpy(float), 0.0)
    y, season, debut = info["y"].to_numpy(float), info["season"].to_numpy(), info["debut"].to_numpy(bool)
    fc, rows = Fc.empty(len(info)), []
    for Y in TEST:
        h, r = (season < Y) & ~debut, season == Y            # info starts in 2019: h is 2019 .. Y - 1
        for stage, with_z in (("both stages", True), ("stage 1", False)):
            X = np.column_stack([np.where(atp[h], es[h], 0.0), np.where(atp[h], ep[h], 0.0),
                                 np.where(~atp[h], es[h], 0.0), np.where(~atp[h], ep[h], 0.0)]
                                + ([zz[h]] if with_z else []))
            beta, se = SC.fit_logistic(X, y[h])
            ph = expit(X @ beta)
            cov = np.linalg.pinv((X.T * (ph * (1 - ph))) @ X)  # fit_logistic's covariance, for w's delta method
            b = shrink(beta[4], se[4]) if with_z else 0.0
            a, c = np.where(atp[r], beta[0], beta[2]), np.where(atp[r], beta[1], beta[3])
            q = expit(a * es[r] + c * ep[r] + b * zz[r])
            qk = expit(a[:, None] * esk[r] + c[:, None] * epk[r] + (b * zz[r])[:, None])
            if with_z:
                fc.q[r], fc.qk[r] = q, qk
            else:
                fc.q1[r], fc.q1k[r] = q, qk
            for j, tour in ((0, "atp"), (2, "wta")):
                aj, cj = float(beta[j]), float(beta[j + 1])
                s = aj + cj
                g = np.array([cj / s ** 2, -aj / s ** 2])
                var_w = float(g @ cov[np.ix_([j, j + 1], [j, j + 1])] @ g)
                rows.append({"composite": name, "stage": stage, "tour": tour, "season": Y, "fitted_on": f"2019-{Y - 1}",
                             "rows": int((h & (atp == (tour == "atp"))).sum()), "a_model": first,
                             "c_model": "pooled seeds 0-3", "a": aj, "se_a": float(se[j]), "c": cj,
                             "se_c": float(se[j + 1]), "w": aj / s, "se_w": float(np.sqrt(max(var_w, 0.0))),
                             "a_plus_c": s, "b": b if with_z else np.nan, "b_mle": float(beta[4]) if with_z else np.nan,
                             "se_b": float(se[4]) if with_z else np.nan})
    return fc, rows


def select_missing(models: dict) -> list[str]:
    """The select candidates without a scored model: select and the winner's luck wait for all six (red team S9)."""
    return [m for m in SELECT_POOL if m not in models]


def select(info: pd.DataFrame, models: dict[str, Fc], pool: list[str]) -> tuple[Fc, list[dict], np.ndarray]:
    """The select composite (module docstring): (forecasts, the choices, the arm behind each info row)."""
    y, season = info["y"].to_numpy(float), info["season"].to_numpy()
    tour, debut = info["tour"].to_numpy(), info["debut"].to_numpy(bool)
    fc, src, rows = Fc.empty(len(info)), np.full(len(info), None, dtype=object), []
    first = season == TEST[0]
    fc.take(models["pooled"], first)
    src[first] = "pooled"
    for t in C.TOURS:
        rows.append({"composite": "select", "tour": t, "season": TEST[0], "chosen": "pooled",
                     "note": "no earlier scored season: the yardstick"})
        for Y in range(SELECT_FROM, TEST[-1] + 1):
            h = (tour == t) & (season >= TEST[0]) & (season < Y) & ~debut
            ll = {m: float(SC.ll(models[m].q[h], y[h]).mean()) for m in pool}
            best = min(pool, key=lambda m: ll[m])             # the first minimum: ties to the earlier-listed arm
            r = (tour == t) & (season == Y)
            fc.take(models[best], r)
            src[r] = best
            rows.append({"composite": "select", "tour": t, "season": Y, "chosen": best,
                         "chosen_on": f"{TEST[0]}-{Y - 1}", "rows": int(h.sum()),
                         **{f"ll_{m}": ll[m] for m in pool}})
    return fc, rows, src


# ------------------------------------------------------------------------------------------------
# Comparisons

def row(info: pd.DataFrame, mask: np.ndarray, base_fc: tuple, cand_fc: tuple, matched: bool = True, **label) -> dict:
    """compare.paired on the info rows in mask, with the row's labels (window, population, comparison, base, arm)."""
    return {**label, **CMP.paired(info, info.index[mask], base_fc, cand_fc, matched)}


def comparisons(info: pd.DataFrame, models: dict[str, Fc], close_fc: Fc, ref_fc: Fc, candidates: list[str]) -> list:
    rows = []
    for window, seasons in WINDOWS.items():
        for group, pop, mask in CMP.populations(info, seasons):
            if not mask.any():
                continue
            lab = {"window": window, "group": group, "population": pop}
            for name in candidates:
                rows.append(row(info, mask, models["pooled"].both(mask), models[name].both(mask),
                                comparison=VS_POOLED, base="pooled", arm=name, **lab))
                rows.append(row(info, mask, models["pooled"].stage1(mask), models[name].stage1(mask),
                                comparison=STAGE1, base="pooled", arm=name, **lab))
            if group != "primary":
                continue
            for name in ["pooled"] + candidates:
                rows.append(row(info, mask, close_fc.both(mask), models[name].both(mask), matched=False,
                                comparison=VS_CLOSE, base="close", arm=name, **lab))
            if window == "W2":
                for name in ["pooled"] + candidates:
                    rows.append(row(info, mask, ref_fc.both(mask), models[name].both(mask),
                                    comparison=VS_REF, base="reference", arm=name, **lab))
    return rows


def contrast_pairs(models: dict) -> list[tuple[str, str, str]]:
    """(comparison, base, candidate) of the contrasts whose models are scored (module docstring)."""
    pairs = []
    if "sizectl" in models:
        pairs.append((SIZE, "sizectl", "pooled"))
        if "split" in models:
            pairs.append((MIX, "sizectl", "split"))
    if "split" in models:
        pairs += [(VS_SPLIT, "split", a) for a in BORROWING if a in models]
    if "blend" in models and "blend_control" in models:
        pairs.append((VS_CONTROL, "blend_control", "blend"))
    return pairs


def contrasts(info: pd.DataFrame, models: dict[str, Fc]) -> list[dict]:
    rows = []
    for window, seasons in WINDOWS.items():
        for group, pop, mask in CMP.populations(info, seasons):
            if group != "primary" or not mask.any():
                continue
            for comparison, base, arm in contrast_pairs(models):
                rows.append(row(info, mask, models[base].both(mask), models[arm].both(mask), comparison=comparison,
                                base=base, arm=arm, window=window, group=group, population=pop))
    return rows


def posthoc_rows(info: pd.DataFrame, models: dict[str, Fc], posthoc: dict[str, Fc]) -> list[dict]:
    """The post-hoc controls' rows (module docstring): both stages, both windows, both tours, men, women; their seed
    term paired by k (the pseudo-seeds share seed k with pooled's seed k)."""
    pairs = [(P8, "pooled", "pooled8")] if "pooled8" in posthoc else []
    if "avg_split_pooled" in posthoc:
        pairs += [(AVG8, "pooled8", "avg_split_pooled"), (AVG, "pooled", "avg_split_pooled")]
    every = {**models, **posthoc}
    rows = []
    for window, seasons in WINDOWS.items():
        for group, pop, mask in CMP.populations(info, seasons):
            if group != "primary" or not mask.any():
                continue
            for comparison, base, arm in pairs:
                rows.append(row(info, mask, every[base].both(mask), every[arm].both(mask), comparison=comparison,
                                base=base, arm=arm, window=window, group=group, population=pop, role=POSTHOC))
    return rows


def self_check(info: pd.DataFrame, pooled: Fc) -> dict:
    """Pooled against itself: exactly 0 with a zero-width interval, every population of both windows, both stages
    and stage 1."""
    n, bad = 0, []
    for window, seasons in WINDOWS.items():
        for group, pop, mask in CMP.populations(info, seasons):
            if not mask.any():
                continue
            for kind in ("both", "stage1"):
                part = getattr(pooled, kind)(mask)
                r = CMP.paired(info, info.index[mask], part, part)
                n += 1
                if not (r["estimate"] == 0 and r["lo"] == 0 and r["hi"] == 0 and r["se"] == 0):
                    bad.append({"window": window, "population": pop, "kind": kind, "estimate": r["estimate"],
                                "lo": r["lo"], "hi": r["hi"]})
    return {"rows": n, "passed": not bad, "failures": bad}


def decided_comparison(info: pd.DataFrame, p_pool: pd.DataFrame, p_ref: pd.DataFrame) -> dict:
    """The decided comparison (the instance against the reference, W2, the reference's speed column for both) by this
    scorer's own path: every primary row of DECIDED within TOL."""
    zr = R.speed_column("reference")
    pool, _ = staged(p_pool, info, zr)
    ref, _ = staged(p_ref, info, zr)
    close_ref, close_inst = close(info, "p_ref"), close(info, "p_cand")
    got = {}
    for group, pop, mask in CMP.populations(info, WINDOWS["W2"]):
        if group != "primary":
            continue
        ids = info.index[mask]
        got[(pop, "both stages: candidate vs reference")] = CMP.paired(info, ids, ref.both(mask), pool.both(mask))
        got[(pop, "stage 1: candidate vs reference")] = CMP.paired(info, ids, ref.stage1(mask), pool.stage1(mask))
        got[(pop, "for scale: reference vs its calibrated close")] = CMP.paired(info, ids, close_ref.both(mask),
                                                                                ref.both(mask), matched=False)
        got[(pop, "for scale: candidate vs its calibrated close")] = CMP.paired(info, ids, close_inst.both(mask),
                                                                                pool.both(mask), matched=False)
    want = C.read_json(DECIDED)["primary"]
    worst, rows = 0.0, []
    for w in want:
        g = got.get((w["population"], w["comparison"]))
        if g is None or g["matches"] != w["matches"] or g["blocks"] != w["blocks"]:
            worst = np.inf
            rows.append({"population": w["population"], "comparison": w["comparison"], "problem": "missing or count"})
            continue
        d = max(abs(g[k] - w[k]) for k in ("estimate", "lo", "hi", "se"))
        worst = max(worst, d)
        rows.append({"population": w["population"], "comparison": w["comparison"], "matches": g["matches"],
                     "estimate": g["estimate"], "lo": g["lo"], "hi": g["hi"], "decided_estimate": w["estimate"],
                     "decided_lo": w["lo"], "decided_hi": w["hi"], "max_abs_diff": d})
    return {"what": f"{R.rel(DECIDED)}: the instance (candidate) against the reference (base), W2, the reference's "
                    "speed column, every primary row, by this scorer's path",
            "rows": len(want), "max_abs_diff": worst, "tolerance": TOL, "passed": bool(len(want) == 12 and worst <= TOL),
            "detail": rows}


def realisation_rows(info: pd.DataFrame, models: dict[str, Fc], close_fc: Fc) -> list[dict]:
    rows = []
    for window, seasons in WINDOWS.items():
        for group, pop, mask in CMP.populations(info, seasons):
            if group != "primary" or not mask.any():
                continue
            y, blk = info["y"].to_numpy(float)[mask], info["block"].to_numpy()[mask]
            for name, fc in models.items():
                r = realisation(fc.q[mask], close_fc.q[mask], y, blk)
                rows.append({"window": window, "population": pop, "model": name, "matches": int(mask.sum()),
                             "blocks": int(len(np.unique(blk))), **r})
    return rows


def winners_luck(scores: pd.DataFrame) -> dict:
    s = scores[(scores["window"] == PRIMARY) & (scores["population"] == "both tours")
               & (scores["comparison"] == VS_POOLED) & scores["arm"].isin(LUCK)]
    out = {"what": "the best of the declared search (borrow25, borrow50, borrowsim, aligned, blend, select) on the "
                   "primary (W1, both tours, both stages against pooled); sel = se x m_K, K = 6, m_K = 1.27",
           "K": 6, "m_K": LUCK_M, "scored": s["arm"].tolist(), "complete_search": bool(len(s) == len(LUCK))}
    if s.empty:
        return {**out, "best": None}
    best = s.loc[s["estimate"].idxmax()]
    sel = float(best["se"]) * LUCK_M
    return {**out, "best": best["arm"], "estimate": float(best["estimate"]), "se": float(best["se"]), "sel": sel,
            "estimate_minus_sel": float(best["estimate"]) - sel,
            "estimates": {a: float(e) for a, e in zip(s["arm"], s["estimate"])}}


def declared_primaries(scores: pd.DataFrame, missing_for_select: list[str]) -> dict:
    """The declared primaries (W1, both tours, both stages against pooled), question 2 labelled as red team B2 asks."""
    def pick(arm):
        r = scores[(scores["window"] == PRIMARY) & (scores["population"] == "both tours")
                   & (scores["comparison"] == VS_POOLED) & (scores["arm"] == arm)]
        return r.iloc[0][["matches", "estimate", "lo", "hi", "se", "p_better", "reading"]].to_dict() if len(r) else None

    out = {"question 1: split": pick("split") or "not scored yet"}
    nt = pick("notour")
    out["question 2: notour (+ = dropping the explicit tour flag helps)"] = nt or "not scored yet"
    out[f"question 2: {FLAG}"] = "not scored yet" if nt is None else {
        "how": "minus notour's reading (+ = the flag helps)", "matches": nt["matches"], "estimate": -nt["estimate"],
        "lo": -nt["hi"], "hi": -nt["lo"], "se": nt["se"], "p_better": 1 - nt["p_better"],
        "reading": {"better": "worse", "worse": "better"}.get(nt["reading"], nt["reading"])}
    out["question 3: blend"] = pick("blend") or "not scored yet"
    out["question 3: select"] = pick("select") or ("not scored: select needs all six candidates complete; missing: "
                                                    + ", ".join(missing_for_select))
    return out


# ------------------------------------------------------------------------------------------------
# Output

def clean(v):
    """JSON-safe: numpy scalars to Python, non-finite floats to null."""
    if isinstance(v, dict):
        return {str(k): clean(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [clean(x) for x in v]
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return float(v) if np.isfinite(v) else None
    return v


def forecast_table(info: pd.DataFrame, models: dict[str, Fc], close_fc: Fc, select_src) -> pd.DataFrame:
    out = info[["tour", "season", "tournament_date", "block", "week", "debut", "level", "y", "p_cand"]] \
        .rename(columns={"p_cand": "p_mkt"}).reset_index()
    cols = {"q_close": close_fc.q}
    for name, fc in models.items():
        cols[f"q_{name}"], cols[f"q1_{name}"] = fc.q, fc.q1
        cols.update({f"q_{name}_s{k}": fc.qk[:, j] for j, k in enumerate(C.SEEDS)})
    out = pd.concat([out, pd.DataFrame(cols)], axis=1)
    if select_src is not None:
        out["select_from"] = select_src
    return out


def fmt(r) -> str:
    if r is None:
        return "—"
    tail = r["reading"] if r["reading"] != "unresolved" else f"unresolved P {r['p_better']:.2f}"
    return f"{r['estimate']:+.3f} [{r['lo']:+.3f}, {r['hi']:+.3f}] {tail}"


def print_primary(scores: pd.DataFrame, names: list[str]) -> None:
    if not names:
        print("no arm complete: nothing to compare with pooled yet")
    for name in names:
        for window in WINDOWS:
            for pop in ("both tours", "men", "women"):
                sel = scores[(scores["window"] == window) & (scores["population"] == pop) & (scores["arm"] == name)]
                both = sel[sel["comparison"] == VS_POOLED]
                st1 = sel[sel["comparison"] == STAGE1]
                print(f"{name:13s} {window} {pop:10s} n {int(both['matches'].iloc[0]):6,d}  both stages "
                      f"{fmt(both.iloc[0])}   stage 1 {fmt(st1.iloc[0])}")
    extra = scores[scores["comparison"].isin([SIZE, MIX, VS_SPLIT, VS_CONTROL, P8, AVG8, AVG])]
    for _, r in extra.iterrows():
        kind = "post-hoc control" if r["comparison"] in (P8, AVG8, AVG) else "contrast"
        print(f"{kind:16s} {r['arm']:16s} vs {r['base']:13s} {r['window']} {r['population']:10s} {fmt(r)}")
    close_rows = scores[(scores["comparison"] == VS_CLOSE) & (scores["population"] == "both tours")]
    for _, r in close_rows.iterrows():
        print(f"for scale {r['window']} {r['arm']:13s} vs its calibrated close: {fmt(r)}")


def run() -> dict:
    z = speed()
    info, facts, inst, P_inst, ref, P_ref = load_info(z)
    C.log(f"{facts['matches']:,} matches of {facts['first_day']} .. {facts['last_day']}; "
          f"{facts['left_out_without_speed_value']['matches']} left out without a speed value")
    fx = F.FrameIndex(inst.reset_index()[["match_id", "season"]])
    p_pool, _ = F.seed_table("model", FIT_SEASONS, C.SEEDS, fx, P_inst, "td", require_checks=True)
    p_ref = CMP.seed_table(P_ref, ref, FIT_SEASONS)
    frame = C.load_frame()
    if not np.array_equal(frame["match_id"].astype(str).to_numpy(), inst.index.to_numpy()):
        raise RuntimeError("common.load_frame() is not the instance's frame in its order")
    frame_sha = C.sha256_file(C.P.model_frame)
    repro = runner_reproduction(frame, frame_sha)
    st = {arm: status(arm) for arm in ARMS}
    tables, refused = {}, {}
    for arm in ARMS:
        if not st[arm]["complete"]:
            continue
        try:
            tables[arm] = arm_table(arm, frame, frame_sha)
        except RuntimeError as e:
            refused[arm] = str(e)
            C.log(f"REFUSED {arm}: {e}")
    models, coefs = {}, {}
    models["pooled"], coefs["pooled"] = staged(p_pool, info, z)
    for arm, t in tables.items():
        models[arm], coefs[arm] = staged(t, info, z)
    composite_rows, select_src = [], None
    p47 = control_table(F.seed_table("model", FIT_SEASONS, CONTROL_SEEDS, fx, P_inst, "td", require_checks=True)[0])
    if "split" in models:
        models["blend"], rows = blend(info, z, tables["split"], p_pool)
        composite_rows += rows
        models["blend_control"], rows = blend(info, z, p47, p_pool, "blend_control", "pooled seeds 4-7")
        composite_rows += rows
    missing_for_select = select_missing(models)
    if not missing_for_select:
        models["select"], rows, select_src = select(info, models, list(SELECT_POOL))
        composite_rows += rows
    posthoc = {"pooled8": staged_mean(*logodds_mean(p_pool, p47, info.index), info, z)[0]}   # never a candidate
    if "split" in tables:
        posthoc["avg_split_pooled"] = staged_mean(*logodds_mean(tables["split"], p_pool, info.index), info, z)[0]
    candidates = [m for m in models if m != "pooled"]
    tested = info["season"].isin(TEST).to_numpy()
    for name, fc in {**models, **posthoc}.items():
        if not all(np.isfinite(v[tested]).all() for v in (fc.q, fc.qk, fc.q1, fc.q1k)):
            raise RuntimeError(f"{name}: a forecast is missing on a scored match")
    close_fc = close(info, "p_cand")
    ref_fc, _ = staged(p_ref, info, z)
    checks = {"pooled_against_itself": self_check(info, models["pooled"]),
              "decided_comparison_reproduced": decided_comparison(info, p_pool, p_ref)}
    if not all(c["passed"] for c in checks.values()):
        C.write_json(SCORES / "checks_failed.json", clean(checks))
        raise RuntimeError(f"a check failed, nothing scored: {R.rel(SCORES / 'checks_failed.json')}")
    scores = pd.DataFrame(comparisons(info, models, close_fc, ref_fc, candidates) + contrasts(info, models)
                          + posthoc_rows(info, models, posthoc))
    scores["role"] = scores["role"].fillna("") if "role" in scores else ""
    first = ["window", "group", "population", "comparison", "base", "arm", "matches", "estimate", "lo", "hi", "se",
             "p_better", "reading", "blocks", "role"]
    scores = scores[first + [c for c in scores.columns if c not in first]]
    real = pd.DataFrame(realisation_rows(info, models, close_fc))
    luck = winners_luck(scores) if "select" in models else {
        "scored": False, "reason": "the winner's luck waits for select, which needs all six candidates complete",
        "missing": missing_for_select}
    keep = ["window", "population", "comparison", "base", "arm", "matches", "estimate", "lo", "hi", "se", "p_better",
            "reading"]
    primary = scores[(scores["group"] == "primary") & scores["comparison"].isin([VS_POOLED, STAGE1])]
    summary = {
        "generated_at": R.now(), "study": "tour_pooling", "design": "docs/studies/tour_pooling/design.md",
        "yardstick": {"pooled": R.rel(C.INSTANCE), "frame_sha256": frame_sha, "seeds": list(C.SEEDS)},
        "speed_column": {"path": R.rel(SPEED), "column": "spd_L_B", "sha256": C.sha256_file(SPEED)},
        "unit": "mLL per match = 1000 x mean(LL_base - LL_candidate); positive = the candidate has the lower log loss "
                "(better); 95% intervals over four-week blocks plus the seed term (paired by seed between models, "
                "unpaired against a price); reading 'better' / 'worse' when the interval clears 0, otherwise "
                "'unresolved' with p_better (the t CDF of estimate / se on blocks - 1 df)",
        "windows": {"W1": "2022 .. 28 Jul 2026 (the declared primary)", "W2": "2020-2024"},
        "results_read": {**facts, "note": "2025 .. 28 Jul 2026 is the clean holdout's exposed part: a run of this "
                                          "scorer is a look at it (design.md: the study's report records it)"},
        "arms": st, "arms_scored": list(tables), "arms_refused": refused,
        "controls": {
            "sizectl": "declared control arm (red team N3): split's size, pooled's mix; never a select candidate",
            "blend_control": "declared composite control (red team S4): the blend with pooled seeds 4-7 for split",
            "pooled8": "post-hoc control (lead, after the first blend reading): pooled seeds 0-7, equal weights in "
                       "log-odds; pseudo-seed k = seeds k and 4 + k",
            "avg_split_pooled": ("post-hoc control (lead, after the first blend reading): split seeds 0-3 with pooled "
                                 "seeds 0-3, equal weights in log-odds; pseudo-seed k = split k and pooled k"
                                 if "avg_split_pooled" in posthoc else "not scored: needs split")},
        "arm_files_sha256": {a: files_sha(a) for a in tables},
        "runner_reproduction": repro,
        "composites": {
            "blend": "scored (split with pooled seeds 0-3)" if "blend" in models else "not scored: needs split",
            "blend_control": ("scored (pooled seeds 4-7 with pooled seeds 0-3)" if "blend_control" in models
                              else "not scored: scored with the blend"),
            "select": ({"candidates": list(SELECT_POOL)} if "select" in models else
                       "not scored: needs all six candidates complete; missing: " + ", ".join(missing_for_select))},
        "checks": checks,
        "declared_primaries": declared_primaries(scores, missing_for_select),
        "primary": primary[keep].to_dict("records"),
        "contrasts": scores.loc[scores["comparison"].isin([SIZE, MIX, VS_SPLIT, VS_CONTROL]), keep].to_dict("records"),
        "post_hoc_controls": scores.loc[scores["role"] == POSTHOC, keep].to_dict("records"),
        "winners_luck": luck,
        "select_choices": [r for r in composite_rows if r["composite"] == "select"],
        "walk_forward_last_season": {m: {k: v[TEST[-1]] for k, v in c.items()} for m, c in coefs.items()},
    }
    SCORES.mkdir(parents=True, exist_ok=True)
    scores.to_csv(SCORES / "scores.csv", index=False)
    pd.DataFrame(composite_rows).to_csv(SCORES / "composites.csv", index=False)
    real.to_csv(SCORES / "realisation.csv", index=False)
    forecast_table(info, {**models, **posthoc}, close_fc, select_src).to_parquet(SCORES / "forecasts.parquet",
                                                                                 index=False)
    C.write_json(SCORES / "summary.json", clean(summary))
    pd.set_option("display.width", 220)
    print_primary(scores, candidates)
    print(f"checks: pooled against itself {checks['pooled_against_itself']['rows']} rows exactly 0; decided comparison "
          f"reproduced, max |diff| {checks['decided_comparison_reproduced']['max_abs_diff']:.1e}")
    rp = repro.get("max_abs_diff_p_td")
    print(f"runner reproduction: {repro['status']}" + (f", max |diff| {rp:.1e} (passed {repro['passed']})"
                                                      if rp is not None else ""))
    print("arms: " + ", ".join(f"{a} {s['files_present']}/{s['files_needed']}" for a, s in st.items())
          + (f"; REFUSED: {', '.join(refused)}" if refused else ""))
    print("select and the winner's luck: " + ("scored" if "select" in models else
                                              "not scored (missing: " + ", ".join(missing_for_select) + ")"))
    if luck.get("best"):
        print(f"winner's luck: best {luck['best']} {luck['estimate']:+.3f}, sel {luck['sel']:.3f}, "
              f"est - sel {luck['estimate_minus_sel']:+.3f}")
    print(f"written: {R.rel(SCORES)}")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true", help="which arms are complete (reads no result)")
    a = ap.parse_args()
    if a.status:
        for arm in ARMS:
            s = status(arm)
            print(f"{arm:9s} {s['files_present']:2d}/{s['files_needed']} {'complete' if s['complete'] else ''}")
        print(f"reproduction file {C.fit_path(*REPRO).name}: {'present' if C.fit_path(*REPRO).exists() else 'absent'}")
        return 0
    summary = run()
    return 2 if summary["arms_refused"] or summary["runner_reproduction"]["passed"] is False else 0


if __name__ == "__main__":
    sys.exit(main())
