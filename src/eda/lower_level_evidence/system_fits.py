"""Role D's fit queue for the level-evidence system: every arm's TabPFN fits, seasons 2019-2026, seeds 0-3, one fit at a
time on the shared card. The binding plan: docs/studies/lower_level_evidence/system/SPEC.md (sections 6.4, 7 and 8) and
the frozen pre-registration data/studies/lower_level_evidence/system/preregistration.md.

Fitting reads training outcomes only: season Y trains on the arm's matches of 2013 .. Y - 1 (the model's own walk-forward,
serve_speed_tabpfn/arms.job_data). The 2025-2026 holdout forbids reading SCORES; nothing here scores a forecast, and the
only use of a 2025 result outside the fit itself is the training-label integrity check (a hash equality, below).

The runners (reused, never edited):
    58 inputs   src/eda/model_rebuild/fits.py --out <arm> --seeds 0-3 --seasons 2019-2026 --wait-memory-only
    60 inputs   src/eda/lower_level_evidence/candidate_fits.run: fits.py line for line, plus R_S2's registered pair of
                share inputs (kind diff). This file's --fit60 calls it inside the local env, because candidate_fits.py's
                own command line refuses seasons after 2024 (a guard of the first run's pre-registration; the owner has
                since agreed to fit and, once, score the holdout under SPEC section 8). --fit60 keeps candidate_fits'
                precondition: the first run's G5 check (it refitted the reference's 2019 seed 0 exactly) must have passed.
Both run through ./python_tabpfn_local.sh. Each fit waits for 12 GB free on the card (--wait-memory-only): another
session's runner (lean_review/fits.py) keeps a local-env process alive for hours and itself waits for memory only, so
waiting for every other local-env process to exit would stall this queue. One of our fits runs at a time.

Where the arms are:
    system/arms/<ARM>/           C1 builds them and writes READY.txt when built and gated; D writes only fits/ and
                                 vs_reference_2026-10-08/ inside (fit logs go to system/results/fit_logs/)
    system/results/arms/<ARM>/   D builds them: R_S2 (a hashed copy of candidates/R_S2 with its 24 fits of 2019-2024, plus
                                 2025-2026), SYS_PLACEBO and SYS_S2 (from SYS's frame, SPEC section 7)

Commands (CPU work runs in ./python.sh; the fits are launched through ./python_tabpfn_local.sh):
    --prepare-r-s2         copy candidates/R_S2 (frame, inputs, 24 fits) into results/arms/R_S2, hashes checked
    --verify ARM           the frame check (no score): 67,226 matches in the reference's ids and order, identifiers
                           equal, training labels equal (a hash), inputs per model_inputs.json, which inputs moved for
                           which tour and seasons against what the arm's definition allows
    --part1 ARM            compare.py's part 1 (the input check, no result read) into <arm>/vs_reference_2026-10-08/,
                           after the arm's expected broad change is written down (results/expected_changes.json)
    --fit ARM [--seasons 2019-2026] [--seeds 0-3]     the arm's fits, logged to results/fits_queue.log
    --queue ARM,ARM,...    --fit for each, in order
    --build-placebo        SYS_PLACEBO: SYS's per-match change (every changed input together) permuted within tour x
                           season, default_rng(20261009)
    --build-s2             SYS_S2: SYS plus R_S2's two share inputs
    --repro-ref-noitf      REF_noITF: refit season 2024 seed 0 from REF_noITF's frame; only if it equals the reference's
                           stored fit exactly (and the inputs to 2024 are the reference's) are the reference's 2019-2024
                           fits copied
    --status               each arm's fits present and missing
    --check-fits ARM       every fit file against its frame (load_fit's checks, frame hash, configuration, window)
    --fit-times            results/fit_times.csv and fit_times_by_season.csv (the lead's forecasts)
    --poll [--minutes 20]  the continuous queue: the highest-priority arm with work goes next (FIT_ORDER, the lead's
                           order of 9 Oct): verify, part 1, REF_noITF's repro or the ITFASIS reuse, fit (2019-2024 then
                           2025-2026 of the same arm), fit-file checks, fit times; one poller at a time
                           (results/poller.json); it stops after --minutes without work
Addition 1 (preregistration_addition_1.md): SYS_ITFASIS and SYS_BOTH_ITFASIS take SYS's and SYS_BOTH's 2019-2024 fits
when their input frames are identical through 2024 (results/checks/<ARM>_reuse.json), else every season is fitted;
NEW_ASIS and NEW_SYS_BOTH (on the candidate Stage 0 C0_now) may hold extra matches: their frame check reads the matches
both frames hold, and they are fitted 2019-2026 on their own frames.
Run: ./python.sh src/eda/lower_level_evidence/system_fits.py <command>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LLE = ROOT / "data" / "studies" / "lower_level_evidence"
SYSTEM = LLE / "system"
ARMS_DIR = SYSTEM / "arms"
RESULTS = SYSTEM / "results"
D_ARMS = RESULTS / "arms"
CHECKS = RESULTS / "checks"
FIT_LOGS = RESULTS / "fit_logs"
QUEUE_LOG = RESULTS / "fits_queue.log"
STATUS_LOG = SYSTEM / "status.log"
EXPECTED = RESULTS / "expected_changes.json"
REF_DIR = ROOT / "data" / "studies" / "current_best_model" / "reference_2026-10-08" / "frozen" / "instance"
REF_FRAME = REF_DIR / "model_frame.parquet"
REF_INPUTS = REF_DIR / "model_inputs.json"
CAND_R_S2 = LLE / "candidates" / "R_S2"
SHIM_GPU = ROOT / "python_tabpfn_local.sh"
N_MATCHES = 67226
SEASONS = tuple(range(2019, 2027))
SEEDS = (0, 1, 2, 3)
DEV_LAST = 2024
PLACEBO_SEED = 20261009
S2_EXTRAS = ["box_low_share_h2w_diff", "box_low_share_365d_diff"]
CMP_DIR = "vs_reference_2026-10-08"

D_BUILT = ("R_S2", "SYS_PLACEBO", "SYS_S2")
C1_ARMS = ("SYS", "SYS_w0", "SYS_w50", "SYS_w100", "SEP_ALL", "SYS_NOCLASS", "SYS_BOTH", "REF_noITF", "SYS_w25",
           "SYS_w75", "SYS_ITFASIS", "SYS_BOTH_ITFASIS", "NEW_ASIS", "NEW_SYS_BOTH", "RES_ONLY", "NEW_ASIS_PRE")
# The lead's priority (message of 10 Oct, after E's checkpoint 1): the highest-priority READY arm is fitted next, each
# arm's 2025-2026 fits right after its 2019-2024 fits (fits.py runs the seasons in order). R_S2 is done.
FIT_ORDER = ("SEP_ALL", "REF_noITF", "SYS", "SYS_w0", "SYS_w100", "RES_ONLY", "SYS_S2", "SYS_PLACEBO", "SYS_w50",
             "SYS_NOCLASS", "SYS_BOTH", "SYS_ITFASIS", "SYS_BOTH_ITFASIS", "NEW_ASIS", "NEW_SYS_BOTH", "NEW_ASIS_PRE",
             "SYS_w25", "SYS_w75", "R_S2")
# Addition 1: arms whose 2019-2024 fits are their base arm's when the input frames are identical through 2024
REUSE_BASE = {"SYS_ITFASIS": "SYS", "SYS_BOTH_ITFASIS": "SYS_BOTH"}
# Addition 1 (and the optional C0_pre arm): arms built on a candidate Stage 0, whose frames may hold matches the
# reference lacks
EXTRA_MATCHES_OK = ("NEW_ASIS", "NEW_SYS_BOTH", "NEW_ASIS_PRE")
POLL_LOCK = RESULTS / "poller.json"

# The 58 inputs by family (SPEC section 3's table); every name is classified, or family() fails.
BOX_FAMILIES = ("raw_rates", "forms", "joint_solves", "products", "ratings_iid")


def family(name: str) -> str:
    if name == "points_52w":
        return "raw_rates"
    if name == "adjperf_tpw_2w" or name.startswith("form_") or name.startswith("formdef_"):
        return "forms"
    if name.startswith("iosO_") or name.startswith("iosD_") or name == "ios_points_short":
        return "joint_solves"
    if name.startswith("prod_"):
        return "products"
    if name == "ratings_iid":
        return "ratings_iid"
    if name in ("elo_overall", "elo_surf_offset", "elo_games"):
        return "elo"
    if name in ("sets_14d", "surf_season_a", "surf_season_b", "surf_layoff_a", "surf_layoff_b", "age", "age_sq"):
        return "workload_intrinsic"
    if name in ("odds_logit", "tour", "surface", "level", "indoor", "best_of", "round"):
        return "market_context"
    if name in S2_EXTRAS:
        return "share_inputs"
    raise KeyError(f"input {name} has no family")


# What each arm's definition lets move (SPEC section 7; the layer applies to men only unless stated). Written before any
# arm exists; --verify reports any move outside it, and --part1 refuses to run before the arm's entry is on disk.
_SYS_LIKE = {"families": list(BOX_FAMILIES) + ["elo"], "tours": ["atp"], "seasons": [2013, 2026]}
EXPECT = {
    "SYS": {**_SYS_LIKE, "broad": "men's box-score inputs (points_52w, the 17 forms, the joint solves and products, "
                                  "ratings_iid) and Elo (w_results) move in every season for players with lower-level "
                                  "evidence; lower-level-heavy players' skill inputs fall towards main-tour terms; in "
                                  "2025-2026 also where ITF box scores are excluded; women's inputs identical"},
    "SYS_w0": {**_SYS_LIKE, "broad": "as SYS, larger: lower-level box scores carry no weight in any statistic, so "
                                     "players with little main-tour evidence lose most of theirs (missing values may "
                                     "appear); Elo as SYS; women identical"},
    "SYS_w50": {**_SYS_LIKE, "broad": "as SYS with w = 0.5 everywhere; between SYS_w0 and SYS_w100; women identical"},
    "SYS_w100": {**_SYS_LIKE, "broad": "as SYS with w = 1: translation only, no discount; women identical"},
    "SYS_w25": {**_SYS_LIKE, "broad": "as SYS with w = 0.25; women identical"},
    "SYS_w75": {**_SYS_LIKE, "broad": "as SYS with w = 0.75; women identical"},
    "SYS_NOCLASS": {**_SYS_LIKE, "broad": "as SYS, every statistic translated by its own gamma and delta (classes "
                                          "ignored): style statistics move too; women identical"},
    "SEP_ALL": {**_SYS_LIKE, "broad": "no lower-level observation in any box-score input or in Elo: the largest change "
                                      "of all arms, every season, men only; missing values may appear"},
    "SYS_BOTH": {"families": list(BOX_FAMILIES) + ["elo"], "tours": ["atp", "wta"], "seasons": [2013, 2026],
                 "broad": "SYS on both tours: men as SYS; women's box-score inputs and Elo move with women's parameters"},
    "REF_noITF": {"families": list(BOX_FAMILIES), "tours": ["atp", "wta"],
                  "seasons": {"atp": [2025, 2026], "wta": [2022, 2026]},
                  "broad": "ITF and ITFQ box scores out of every box-score family. Men's exist only from 30 Dec 2024, "
                           "so men's inputs to 2024 equal the reference's; women's start with 31 matches from 2 May "
                           "2022 (Stage 0 count), so women's inputs may move from 2022 (365-day and career windows "
                           "carry it on). In 2025-2026 women move far more than men (42% and 7% of model matches "
                           "reached); Elo unchanged"},
    "SYS_PLACEBO": {**_SYS_LIKE, "broad": "the inputs SYS changes, by a permuted copy of SYS's change: the same size "
                                          "per tour-season, no alignment with the players' evidence; women identical"},
    "SYS_S2": {**_SYS_LIKE, "extras": S2_EXTRAS,
               "broad": "SYS's inputs exactly, plus the two share inputs of R_S2"},
    "R_S2": {"families": [], "tours": [], "seasons": [2013, 2026], "extras": S2_EXTRAS,
             "broad": "the reference's 58 inputs exactly, plus the two share inputs"},
    # addition 1 (written 20:5x UTC on 9 Oct, before any of these arms exists)
    "SYS_ITFASIS": {**_SYS_LIKE, "broad": "as SYS against the reference, but ITF and ITFQ box scores enter as the "
                                          "reference has them: identical to SYS to 2024 (men have no ITF box score "
                                          "before 30 Dec 2024); in 2025-2026 its men's inputs sit between SYS's and the "
                                          "reference's where players have ITF box scores; women identical"},
    "SYS_BOTH_ITFASIS": {"families": list(BOX_FAMILIES) + ["elo"], "tours": ["atp", "wta"], "seasons": [2013, 2026],
                         "broad": "as SYS_BOTH with ITF box scores as-is: men identical to SYS_BOTH to 2024; women may "
                                  "differ from SYS_BOTH from 2022 (31 women's ITF box-score matches in 2022), so the "
                                  "reuse of SYS_BOTH's 2019-2024 fits may not apply"},
    "NEW_ASIS": {"families": list(BOX_FAMILIES) + ["elo", "workload_intrinsic"], "tours": ["atp", "wta"],
                 "seasons": [2013, 2026],
                 "broad": "the template on the candidate Stage 0 C0_now: the newly wired lower-level matches and box "
                          "scores enter as equivalent, so box-score inputs, Elo and workload counts move for players "
                          "with new lower-level history, both tours; market and context inputs identical on the matches "
                          "both frames hold; the frame may hold extra matches (role F writes the expected unevenness)"},
    "NEW_SYS_BOTH": {"families": list(BOX_FAMILIES) + ["elo", "workload_intrinsic"], "tours": ["atp", "wta"],
                     "seasons": [2013, 2026],
                     "broad": "the SYS_BOTH configuration on C0_now: both tours move, as SYS_BOTH plus the new data "
                              "through the layer; market and context identical on the shared matches"},
    # the lead's message of 10 Oct (E's checkpoint 1, M3 and S9), written before either arm exists
    "RES_ONLY": {"families": ["elo"], "tours": ["atp", "wta"], "seasons": [2013, 2026],
                 "broad": "the reference plus B's fitted w_results at every lower level, ITF and ITFQ included: only "
                          "elo_overall, elo_surf_offset and elo_games move, in every season, for players with "
                          "lower-level results (men's ITF x0.25-0.5 and ITF qualifying x0 in B's choices); no "
                          "box-score input moves; men's Elo inputs should equal SYS's; women's identical to the "
                          "reference's if the arm is men-only, as SYS is"},
    "NEW_ASIS_PRE": {"families": list(BOX_FAMILIES) + ["elo", "workload_intrinsic"], "tours": ["atp", "wta"],
                     "seasons": [2013, 2026],
                     "broad": "the template on C0_pre (C0_now's additions dated up to 2024-12-29 only): as NEW_ASIS "
                              "before 2025; in 2025-2026 only through history windows reaching back past the cut; "
                              "market and context identical on the shared matches; extra matches possible"},
}


def now() -> str:
    return pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def rel(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    def default(o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o) if np.isfinite(o) else None
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, np.bool_):
            return bool(o)
        return str(o)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=default), encoding="utf-8")
    tmp.replace(path)


def log_line(path: Path, msg: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(f"{now()} {msg}\n")


def status_line(msg: str) -> None:
    """One line in the team's shared status log (append only)."""
    log_line(STATUS_LOG, f"D {msg}")


def arm_dir(arm: str) -> Path:
    if arm == "REF":
        return REF_DIR
    return (D_ARMS if arm in D_BUILT else ARMS_DIR) / arm


def input_names(folder: Path) -> list[tuple[str, str]]:
    meta = json.loads((folder / "model_inputs.json").read_text(encoding="utf-8"))
    return [(d["name"], d["kind"]) for d in meta["inputs"]]


def fits_present(arm: str, seasons=SEASONS, seeds=SEEDS) -> tuple[int, list[tuple[int, int]]]:
    d = arm_dir(arm) / "fits"
    missing = [(s, k) for s in seasons for k in seeds if not (d / f"model__{s}__seed{k}.npz").exists()]
    return len(seasons) * len(seeds) - len(missing), missing


# ------------------------------------------------------------------------------------------------
# R_S2: a hashed copy (the first run's folder is read-only)

def prepare_r_s2() -> dict:
    dst = arm_dir("R_S2")
    (dst / "fits").mkdir(parents=True, exist_ok=True)
    files = [Path("model_frame.parquet"), Path("model_inputs.json")]
    files += [Path("fits") / f"model__{s}__seed{k}.npz" for s in range(2019, DEV_LAST + 1) for k in SEEDS]
    rows = []
    for f in files:
        src, out = CAND_R_S2 / f, dst / f
        want = sha256(src)
        if out.exists():
            got = sha256(out)
            if got != want:
                raise SystemExit(f"{rel(out)} exists and differs from {rel(src)}: not overwritten")
        else:
            tmp = out.with_name(out.name + ".tmp")
            shutil.copyfile(src, tmp)
            tmp.replace(out)
            got = sha256(out)
        if got != want:
            raise SystemExit(f"copy of {rel(src)} has another hash")
        rows.append({"file": f.as_posix(), "source": rel(src), "sha256": want, "bytes": out.stat().st_size})
    rec = {"what": "R_S2 (role 08's arm: the reference plus two share inputs), copied unchanged from the first run's "
                   "read-only folder so that D can add its 2025-2026 fits; every file's SHA-256 equals the source's",
           "copied_at": now(), "source": rel(CAND_R_S2), "files": rows}
    write_json(dst / "provenance_D.json", rec)
    print(f"R_S2: {len(rows)} files copied or already equal -> {rel(dst)}")
    return rec


# ------------------------------------------------------------------------------------------------
# The frame check (no score; the training labels are compared by hash only)

def labels_hash(path: Path, through: int = 2025) -> str:
    """SHA-256 of the result column of seasons <= through, in file order: the labels the walk-forward fits train on
    (2026's fit trains on 2013-2025). Only the hash leaves this function."""
    f = pd.read_parquet(path, columns=["season", "a_won"], filters=[("season", "<=", through)])
    if len(f) and int(f["season"].max()) > through:
        raise RuntimeError("a result after the training seasons was read")
    v = np.ascontiguousarray(f["a_won"].astype("int8").to_numpy())
    return hashlib.sha256(v.tobytes()).hexdigest()


def labels_equal_on(path_a: Path, path_b: Path, ids: pd.Index, through: int = 2025) -> bool:
    """The result columns of two frames, seasons <= through, on the given match ids (in that order) both frames hold:
    equal or not, compared by hash. Only the equality leaves this function."""
    def read(p):
        f = pd.read_parquet(p, columns=["match_id", "season", "a_won"], filters=[("season", "<=", through)])
        if len(f) and int(f["season"].max()) > through:
            raise RuntimeError("a result after the training seasons was read")
        return f.assign(match_id=f["match_id"].astype(str)).set_index("match_id")["a_won"]
    a, b = read(path_a), read(path_b)
    keep = ids[ids.isin(a.index) & ids.isin(b.index)]
    if not (ids.isin(a.index) == ids.isin(b.index)).all():
        return False                                          # a match's season differs between the frames
    ha = hashlib.sha256(np.ascontiguousarray(a.loc[keep].astype("int8").to_numpy()).tobytes()).hexdigest()
    hb = hashlib.sha256(np.ascontiguousarray(b.loc[keep].astype("int8").to_numpy()).tobytes()).hexdigest()
    return ha == hb


def verify_frame(arm: str, write: bool = True) -> dict:
    from src.eda.lower_level_evidence import candidate_arms as CA
    d = arm_dir(arm)
    path = d / "model_frame.parquet"
    out = {"arm": arm, "checked_at": now(), "frame": rel(path), "frame_sha256": sha256(path)}
    ref, cand = CA.inputs_of(REF_FRAME), CA.inputs_of(path)
    out["rows"] = int(len(cand))
    relaxed = arm in EXTRA_MATCHES_OK
    if relaxed:
        # addition 1's C0_now arms: other matches may be present; everything below is read on the matches both hold
        ids_ref, ids_arm = pd.Index(ref["match_id"]), pd.Index(cand["match_id"])
        common = ids_ref[ids_ref.isin(ids_arm)]
        out.update({"matches_both": int(len(common)), "only_in_arm": int((~ids_arm.isin(ids_ref)).sum()),
                    "only_in_reference": int((~ids_ref.isin(ids_arm)).sum()),
                    "duplicate_ids": int(ids_arm.duplicated().sum())})
        out["rows_ok"] = out["duplicate_ids"] == 0 and len(common) > 0
        out["same_ids_in_order"] = None
        if not out["rows_ok"]:
            out["pass"] = False
            if write:
                write_json(CHECKS / f"{arm}_frame.json", out)
            return out
        ref = ref.set_index("match_id").loc[common].reset_index()
        cand = cand.set_index("match_id").loc[common].reset_index()
    else:
        out["rows_ok"] = len(cand) == N_MATCHES and len(ref) == N_MATCHES
        out["same_ids_in_order"] = bool(len(ref) == len(cand)
                                        and (ref["match_id"].to_numpy() == cand["match_id"].to_numpy()).all())
        if not (out["rows_ok"] and out["same_ids_in_order"]):
            out["pass"] = False
            if write:
                write_json(CHECKS / f"{arm}_frame.json", out)
            return out
    ids = {}
    for c in CA.ID_COLS[1:]:
        x, y = ref[c], cand[c]
        ids[c] = bool(x.equals(y)) if x.dtype == y.dtype else bool((x.astype(str) == y.astype(str)).all())
    out["identifiers_equal"] = ids
    if relaxed:
        out["training_labels_equal_to_2025"] = labels_equal_on(REF_FRAME, path, pd.Index(ref["match_id"]))
    else:
        out["training_labels_equal_to_2025"] = labels_hash(REF_FRAME) == labels_hash(path)
    ri, ci = input_names(REF_DIR), input_names(d)
    spec = EXPECT.get(arm, {})
    extras = spec.get("extras", [])
    out["inputs"] = len(ci)
    out["base_inputs_equal"] = ci[:58] == ri
    out["extras"] = [n for n, _ in ci[58:]]
    out["extras_as_defined"] = [n for n, _ in ci[58:]] == list(extras) and all(k == "diff" for _, k in ci[58:])
    names = [n for n, _ in ci]
    in_cols = [c for c in cand.columns if c.startswith("in_")]
    out["columns_are_the_inputs"] = sorted(in_cols) == sorted(f"in_{n}" for n in names)
    tour = ref["tour"].to_numpy()
    season = ref["season"].to_numpy().astype(int)
    rows, unexpected = [], []
    allowed_fam = set(spec.get("families", []))
    allowed_tours = set(spec.get("tours", []))
    seasons_spec = spec.get("seasons", [2013, 2026])
    for n, _ in ri:
        a, b = ref[f"in_{n}"].to_numpy(float), cand[f"in_{n}"].to_numpy(float)
        na, nb = np.isnan(a), np.isnan(b)
        both = ~na & ~nb
        changed = (na != nb) | (both & (a != b))
        for t in ("atp", "wta"):
            m = changed & (tour == t)
            if not m.any():
                continue
            gap = np.abs(a - b)[m & both]
            r = {"input": n, "family": family(n), "tour": t, "rows_changed": int(m.sum()),
                 "rows_tour": int((tour == t).sum()), "first_season": int(season[m].min()),
                 "last_season": int(season[m].max()), "largest_change": float(gap.max()) if len(gap) else None,
                 "missing_reference": int((na & m).sum()), "missing_candidate": int((nb & m).sum())}
            s_lo, s_hi = seasons_spec.get(t, [2013, 2026]) if isinstance(seasons_spec, dict) else seasons_spec
            ok = (family(n) in allowed_fam and t in allowed_tours and s_lo <= r["first_season"]
                  and r["last_season"] <= s_hi)
            r["allowed"] = bool(ok)
            rows.append(r)
            if not ok:
                unexpected.append(r)
    out["moved"] = rows
    out["moved_inputs"] = sorted({r["input"] for r in rows})
    out["unexpected_moves"] = unexpected
    out["reference_inputs_to_2024_identical"] = not any(r["first_season"] <= DEV_LAST for r in rows)
    if arm == "RES_ONLY" and (arm_dir("SYS") / "model_frame.parquet").exists():
        # informational (E's M3): the Elo weighting alone should be SYS's Elo exactly
        s = CA.inputs_of(arm_dir("SYS") / "model_frame.parquet")
        if len(s) == len(cand) and (s["match_id"].to_numpy() == cand["match_id"].to_numpy()).all():
            out["elo_inputs_equal_to_SYS"] = {
                n: bool(np.array_equal(s[f"in_{n}"].to_numpy(float), cand[f"in_{n}"].to_numpy(float), equal_nan=True))
                for n in ("elo_overall", "elo_surf_offset", "elo_games")}
    ids_ok = True if relaxed else bool(out["same_ids_in_order"])      # the C0 arms: read on the shared matches
    out["pass"] = bool(out["rows_ok"] and ids_ok and all(ids.values())
                       and out["training_labels_equal_to_2025"] and out["base_inputs_equal"]
                       and out["extras_as_defined"] and out["columns_are_the_inputs"] and not unexpected)
    if write:
        write_json(CHECKS / f"{arm}_frame.json", out)
    return out


# ------------------------------------------------------------------------------------------------
# compare.py's part 1 (the input check; no result read)

def write_expectations() -> None:
    """The expected broad change of every arm, written once before any input check is read (SPEC section 8)."""
    have = json.loads(EXPECTED.read_text(encoding="utf-8")) if EXPECTED.exists() else {}
    changed = False
    for arm, spec in EXPECT.items():
        if arm not in have:
            have[arm] = {**spec, "written_at": now()}
            changed = True
    if changed:
        write_json(EXPECTED, have)


def amend_expectation(arm: str, why: str) -> None:
    """Replace an arm's written expectation with the code's current one, keeping the earlier text and the reason.
    Refused once the arm's input check has been written (an expectation is amended only before its reading)."""
    if (arm_dir(arm) / CMP_DIR / "part1_summary.json").exists():
        raise SystemExit(f"{arm}: its input check is already written; its expectation is not amended")
    have = json.loads(EXPECTED.read_text(encoding="utf-8")) if EXPECTED.exists() else {}
    earlier = have.get(arm)
    have[arm] = {**EXPECT[arm], "written_at": now(), "amended_because": why,
                 "earlier": earlier, "arm_frame_existed": (arm_dir(arm) / "model_frame.parquet").exists()}
    write_json(EXPECTED, have)


def part1(arm: str) -> dict:
    from src.eda.current_best_model import compare as CMP
    from src.eda.current_best_model import reference as R
    write_expectations()
    exp = json.loads(EXPECTED.read_text(encoding="utf-8")).get(arm)
    if not exp:
        raise SystemExit(f"{arm}: no expected change written down; refusing to read its input check")
    d = arm_dir(arm)
    out_dir = d / CMP_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    _, P_cand, _ = CMP.candidate(str(d))
    ref, cand = CMP.inputs_frame(R.paths("reference")), CMP.inputs_frame(P_cand)
    by_season, per_input = CMP.input_drift(ref, cand)
    profile = pd.concat([CMP.season_profile(ref, "reference"), CMP.season_profile(cand, "candidate")],
                        ignore_index=True)
    cov = CMP.coverage(ref, cand)
    by_season.to_csv(out_dir / "inputs_by_season.csv", index=False)
    per_input.to_csv(out_dir / "inputs.csv", index=False)
    profile.to_csv(out_dir / "season_profile.csv", index=False)
    cov.to_csv(out_dir / "coverage.csv", index=False)
    flagged = per_input.loc[per_input["flag"].isin(["uneven", "every season"]),
                            ["input", "flag", "flagged_tour_seasons", "flagged"]].to_dict("records")
    cells, summary = evidence_mix_reading(arm, by_season)
    cells.to_csv(out_dir / "changes_vs_evidence_mix.csv", index=False)
    summary.to_csv(out_dir / "changes_vs_evidence_mix_summary.csv", index=False)
    res = {"arm": arm, "written_at": now(), "what": "compare.py part 1 (input_drift, season_profile, coverage) on the "
           "arm against the frozen reference; no result read", "expected_change": exp["broad"],
           "inputs_changed": int((per_input["changed_share"].fillna(0) > 0).sum()), "inputs_flagged": flagged,
           "only_in_one": per_input.loc[per_input["flag"].astype(str).str.startswith("only"), ["input", "flag"]]
           .to_dict("records"), "coverage": {k: int(cov[k].sum()) for k in cov.columns if k not in ("tour", "season")}}
    write_json(out_dir / "part1_summary.json", res)
    print(f"{arm}: part 1 written to {rel(out_dir)}; inputs changed {res['inputs_changed']}, flagged "
          + (", ".join(f"{r['input']} ({r['flag']}, {r['flagged_tour_seasons']})" for r in flagged) or "none"))
    return res


def evidence_mix() -> pd.DataFrame:
    """Per tour and season (no result): the mean lower-level share of the two sides' box-score evidence and the mean
    absolute share gap (365 days and the two-week window), and the ITF part of the 365-day evidence (sides.parquet of
    role 02, counts only; lower = TQ, GSQ, CH, CHQ, ITF, ITFQ as the first run's strata)."""
    from src.eda.lower_level_evidence import candidate_arms as CA
    cols = ["match_id", "side", "tour", "season"] + [f"box_{w}_{b}" for w in ("365d", "h2w") for b in CA.ALL_BUCKETS]
    s = pd.read_parquet(CA.SIDES, columns=cols)
    out = {}
    for w in ("365d", "h2w"):
        tot = s[[f"box_{w}_{b}" for b in CA.ALL_BUCKETS]].sum(axis=1).to_numpy(float)
        low = s[[f"box_{w}_{b}" for b in CA.LOWER]].sum(axis=1).to_numpy(float)
        s[f"share_{w}"] = np.where(tot > 0, low / np.where(tot > 0, tot, 1.0), np.nan)
        if w == "365d":
            itf = s[[f"box_{w}_ITF", f"box_{w}_ITFQ"]].sum(axis=1).to_numpy(float)
            s["itf_share_365d"] = np.where(tot > 0, itf / np.where(tot > 0, tot, 1.0), np.nan)
    a = s[s["side"] == "A"].set_index("match_id")
    b = s[s["side"] == "B"].set_index("match_id").reindex(a.index)
    m = pd.DataFrame({"tour": a["tour"], "season": a["season"].astype(int)})
    for w in ("365d", "h2w"):
        m[f"mean_share_{w}"] = (a[f"share_{w}"] + b[f"share_{w}"]) / 2
        m[f"abs_gap_{w}"] = (a[f"share_{w}"] - b[f"share_{w}"]).abs()
    m["mean_itf_share_365d"] = (a["itf_share_365d"] + b["itf_share_365d"]) / 2
    out = m.groupby(["tour", "season"]).mean(numeric_only=True).reset_index()
    return out


def evidence_mix_reading(arm: str, by_season: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(cells, summary). Cells: each changed input's per tour-season change (scale ratio, level shift, median change,
    flag) beside that tour-season's evidence mix. Summary: per input and tour, the flagged seasons and the rank
    correlation across tour-seasons of the change's size (|scale ratio - 1| + |level shift|) with each mix measure. A
    flag is read against the tour-season's own evidence mix (SPEC section 8), not against a median split."""
    mix = evidence_mix()
    t = by_season.merge(mix, on=["tour", "season"], how="left")
    t = t[t["changed_share"].fillna(0) > 0].copy()
    t.insert(0, "arm", arm)
    t["size"] = (t["scale_ratio"] - 1).abs() + t["level_shift_sd"].abs()
    rows = []
    for (inp, tour), g in t.groupby(["input", "tour"]):
        r = {"arm": arm, "input": inp, "tour": tour, "tour_seasons_changed": int(len(g)),
             "tour_seasons_flagged": int(g["flagged"].sum()),
             "flagged_seasons": "; ".join(str(int(s)) for s in g.loc[g["flagged"], "season"])}
        for c in ("mean_share_365d", "abs_gap_365d", "mean_share_h2w", "abs_gap_h2w", "mean_itf_share_365d"):
            ok = g["size"].notna() & g[c].notna()
            r[f"spearman_size_vs_{c}"] = (float(g.loc[ok, "size"].rank().corr(g.loc[ok, c].rank()))
                                          if ok.sum() > 2 else np.nan)
        rows.append(r)
    return t, pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# The fits

def _bash() -> str:
    b = shutil.which("bash")
    if not b or "system32" in b.lower():
        raise SystemExit(f"no Git bash on PATH (found {b}): the GPU shim ./python_tabpfn_local.sh needs it")
    return b


def fit(arm: str, seasons=SEASONS, seeds=SEEDS) -> int:
    d = arm_dir(arm)
    names = input_names(d)
    have, missing = fits_present(arm, seasons, seeds)
    if not missing:
        log_line(QUEUE_LOG, f"skip {arm}: all {have} fits present")
        return 0
    if len(names) == 58:
        cmd = [_bash(), str(SHIM_GPU), "src/eda/model_rebuild/fits.py", "--out", str(d), "--seeds",
               f"{seeds[0]}-{seeds[-1]}", "--seasons", f"{seasons[0]}-{seasons[-1]}", "--wait-memory-only"]
    elif len(names) == 60 and [n for n, _ in names[58:]] == S2_EXTRAS:
        cmd = [_bash(), str(SHIM_GPU), "src/eda/lower_level_evidence/system_fits.py", "--fit60", str(d), "--seeds",
               f"{seeds[0]}-{seeds[-1]}", "--seasons", f"{seasons[0]}-{seasons[-1]}"]
    else:
        raise SystemExit(f"{arm}: {len(names)} inputs; only 58, or the 58 plus R_S2's two share inputs, are fitted")
    FIT_LOGS.mkdir(parents=True, exist_ok=True)
    logf = FIT_LOGS / f"{arm}.log"
    log_line(QUEUE_LOG, f"start {arm} seasons {seasons[0]}-{seasons[-1]} seeds {seeds[0]}-{seeds[-1]}: "
                        f"{len(missing)} to fit, {have} present ({len(names)} inputs)")
    t0 = time.monotonic()
    with open(logf, "a", encoding="utf-8") as fh:
        fh.write(f"=== {now()} {' '.join(cmd[1:])}\n")
        fh.flush()
        rc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode
    have2, missing2 = fits_present(arm, seasons, seeds)
    log_line(QUEUE_LOG, f"done {arm} exit {rc} fits {have2 - have} new, {len(missing2)} missing "
                        f"({time.monotonic() - t0:.0f} s)")
    return rc


def fit60(out: Path, seasons: list[int], seeds: list[int]) -> int:
    """Inside the local env: candidate_fits.run on a 60-input arm (R_S2's pair of extras), any season 2019-2026."""
    from src.eda.lower_level_evidence import candidate_fits as CF
    g5 = json.loads(CF.REPRO_JSON.read_text(encoding="utf-8")) if CF.REPRO_JSON.exists() else {}
    if not g5.get("pass"):
        raise SystemExit("the first run's G5 check (candidate_fits reproduces the reference's fit) has not passed")
    if [n for n, _ in input_names(out)[58:]] != S2_EXTRAS:
        raise SystemExit(f"{out}: not a 58 + share-pair arm")
    if any(s < 2019 or s > 2026 for s in seasons):
        raise SystemExit("seasons 2019-2026 only")
    CF.run(out, seasons, seeds, frame_label=f"lower_level_evidence system arm {out.name} (system_fits.py --fit60)",
           wait_memory_only=True)
    return 0


def span(text: str) -> list[int]:
    a, _, b = text.partition("-")
    return list(range(int(a), int(b or a) + 1))


def check_fits(arm: str, seasons=SEASONS, seeds=SEEDS) -> dict:
    """Every fit file of the arm against its frame, with forecasts.load_fit's own checks (stored columns = the arm's
    inputs, training shape = the expanding window's, td ids = the season's frame ids in order) plus its metadata: the
    frame's SHA-256 (a copied fit: the source frame's, recorded), the configuration and the training seasons. No
    forecast is compared with a result."""
    from src.eda.current_best_model import compare as CMP
    from src.eda.serve_speed_tabpfn import common as C
    from src.eda.serve_speed_tabpfn import forecasts as F
    d = arm_dir(arm)
    _, P, _ = CMP.candidate(str(d))
    frame = CMP.inputs_frame(P)
    fx = F.FrameIndex(frame.reset_index()[["match_id", "season"]])
    frame_sha = sha256(d / "model_frame.parquet")
    rows = []
    for s in seasons:
        for k in seeds:
            path = d / "fits" / f"model__{s}__seed{k}.npz"
            if not path.exists():
                continue
            r = {"season": s, "seed": k, "file": path.name}
            try:
                F.load_fit("model", s, k, fx, P, require_checks=True)
                r["load_fit_checks"] = True
            except Exception as e:                            # noqa: BLE001 (recorded, then the check fails)
                r["load_fit_checks"] = False
                r["error"] = str(e)
            with np.load(path, allow_pickle=False) as z:
                meta = json.loads(str(z["meta"]))
            r["frame_sha256_equal"] = meta.get("model_frame_sha256") == frame_sha
            r["config_equal"] = meta.get("config") == {**C.CONFIG, "random_state": k}
            r["train_seasons_equal"] = meta.get("train_seasons") == [C.TRAIN_FROM, s - 1]
            r["seconds"] = meta.get("seconds")
            rows.append(r)
    registered = copied_files()
    copied = [r for r in rows if not r["frame_sha256_equal"]]
    unregistered = [r["file"] for r in copied if str((d / "fits" / r["file"]).resolve()) not in registered]
    res = {"arm": arm, "checked_at": now(), "fits": len(rows), "frame_sha256": frame_sha,
           "all_load_fit_checks": all(r["load_fit_checks"] for r in rows),
           "all_config_and_window": all(r["config_equal"] and r["train_seasons_equal"] for r in rows),
           "fits_from_another_frame_file": [r["file"] for r in copied],
           "fits_from_another_frame_not_registered_copies": unregistered, "rows": rows}
    # a fit made on another frame passes only as a registered copy (REF_noITF's repro, the ITFASIS reuse, R_S2's first
    # run); anything else is a stale fit, e.g. one left from before a rebuild (E's checkpoint 1, S8)
    res["pass"] = bool(rows and res["all_load_fit_checks"] and res["all_config_and_window"] and not unregistered)
    write_json(CHECKS / f"{arm}_fits.json", res)
    return res


# ------------------------------------------------------------------------------------------------
# D-built arms from SYS (SPEC section 7)

def _require_ready(arm: str) -> Path:
    d = arm_dir(arm)
    if not (d / "READY.txt").exists():
        raise SystemExit(f"{arm} is not READY ({rel(d / 'READY.txt')} missing)")
    chk = verify_frame(arm)
    if not chk["pass"]:
        raise SystemExit(f"{arm}: the frame check failed ({rel(CHECKS / (arm + '_frame.json'))})")
    return d


def placebo_change(ref: pd.DataFrame, sys_: pd.DataFrame, names: list[str]) -> tuple[dict, np.ndarray, dict]:
    """SYS's per-match change vector over every input it changes, permuted across matches within tour x season with
    default_rng(20261009) (the first run's FP_placebo rule): a changed cell's value is the reference's plus the change of
    the permuted match; where either frame is missing the change is 0 (a missing reference value stays missing)."""
    rng = np.random.default_rng(PLACEBO_SEED)
    perm = np.arange(len(ref))
    keys = ref[["tour", "season"]].astype({"season": int}).reset_index(drop=True)
    for _, g in keys.groupby(["tour", "season"], sort=True):
        idx = g.index.to_numpy()
        perm[idx] = idx[rng.permutation(len(idx))]
    out, info = {}, {}
    for n in names:
        a, b = ref[f"in_{n}"].to_numpy(float), sys_[f"in_{n}"].to_numpy(float)
        d = np.nan_to_num(b - a, nan=0.0)
        out[n] = a + d[perm]
        info[n] = {"missing_pattern_differs": int((np.isnan(a) != np.isnan(b)).sum()),
                   "sd_change_sys": float(np.nanstd(b - a)), "sd_change_placebo": float(np.nanstd(out[n] - a)),
                   "corr_sys_placebo_change": float(pd.Series(b - a).corr(pd.Series(out[n] - a)))}
    return out, perm, info


def build_placebo() -> dict:
    from src.eda.lower_level_evidence import candidate_arms as CA
    import pyarrow.parquet as pq
    d_sys = _require_ready("SYS")
    ref, sys_ = CA.inputs_of(REF_FRAME), CA.inputs_of(d_sys / "model_frame.parquet")
    names = [n for n, _ in input_names(REF_DIR)]
    moved = [n for n in names if CA.max_gap(ref[f"in_{n}"].to_numpy(), sys_[f"in_{n}"].to_numpy())[2] > 0]
    pl, perm, size = placebo_change(ref, sys_, moved)
    t = pq.read_table(REF_FRAME)                     # the reference's table: the result column passes through unread
    for n in moved:
        t = CA.replace(t, f"in_{n}", pl[n])
    dst = arm_dir("SYS_PLACEBO")
    dst.mkdir(parents=True, exist_ok=True)
    pq.write_table(t, dst / "model_frame.parquet")
    meta = json.loads(REF_INPUTS.read_text(encoding="utf-8"))
    meta["arm"] = {"name": "SYS_PLACEBO", "built_by": "src/eda/lower_level_evidence/system_fits.py --build-placebo",
                   "what": f"the reference plus SYS's per-match change vector over its {len(moved)} changed inputs, "
                           f"permuted across matches within tour x season (default_rng({PLACEBO_SEED}))",
                   "sys_frame_sha256": sha256(d_sys / "model_frame.parquet")}
    write_json(dst / "model_inputs.json", meta)
    np.save(dst / "permutation.npy", perm)
    rec = {"arm": "SYS_PLACEBO", "built_at": now(), "inputs_permuted": moved, "size": size,
           "frame_sha256": sha256(dst / "model_frame.parquet"), "sys_frame_sha256": meta["arm"]["sys_frame_sha256"],
           "reference_frame_sha256": sha256(REF_FRAME)}
    write_json(dst / "provenance_D.json", rec)
    print(json.dumps({k: v for k, v in rec.items() if k != "size"}, indent=1))
    return rec


def build_s2() -> dict:
    from src.eda.lower_level_evidence import candidate_arms as CA
    import pyarrow.parquet as pq
    d_sys = _require_ready("SYS")
    if not (arm_dir("R_S2") / "model_frame.parquet").exists():
        prepare_r_s2()
    sys_ = CA.inputs_of(d_sys / "model_frame.parquet")
    rs2 = CA.inputs_of(arm_dir("R_S2") / "model_frame.parquet")
    if not (sys_["match_id"].to_numpy() == rs2["match_id"].to_numpy()).all():
        raise SystemExit("SYS's and R_S2's frames are not in the same order")
    t = pq.read_table(d_sys / "model_frame.parquet")
    for n in S2_EXTRAS:
        t = CA.replace(t, f"in_{n}", rs2[f"in_{n}"].to_numpy(float))
    dst = arm_dir("SYS_S2")
    dst.mkdir(parents=True, exist_ok=True)
    pq.write_table(t, dst / "model_frame.parquet")
    meta = json.loads((d_sys / "model_inputs.json").read_text(encoding="utf-8"))
    r_meta = json.loads((arm_dir("R_S2") / "model_inputs.json").read_text(encoding="utf-8"))
    meta["inputs"] = meta["inputs"][:58] + [x for x in r_meta["inputs"] if x["name"] in S2_EXTRAS]
    meta["arm"] = {"name": "SYS_S2", "built_by": "src/eda/lower_level_evidence/system_fits.py --build-s2",
                   "what": "SYS plus R_S2's two share inputs (in_box_low_share_h2w_diff, in_box_low_share_365d_diff)",
                   "sys_frame_sha256": sha256(d_sys / "model_frame.parquet"),
                   "r_s2_frame_sha256": sha256(arm_dir("R_S2") / "model_frame.parquet")}
    write_json(dst / "model_inputs.json", meta)
    rec = {"arm": "SYS_S2", "built_at": now(), "frame_sha256": sha256(dst / "model_frame.parquet"), **meta["arm"]}
    write_json(dst / "provenance_D.json", rec)
    print(json.dumps(rec, indent=1))
    return rec


# ------------------------------------------------------------------------------------------------
# REF_noITF: the reference's 2019-2024 fits, if its inputs to 2024 are the reference's and one refit reproduces

def repro_ref_noitf() -> dict:
    d = _require_ready("REF_noITF")
    chk = json.loads((CHECKS / "REF_noITF_frame.json").read_text(encoding="utf-8"))
    res = {"what": "REF_noITF: one refit (season 2024, seed 0) from its own frame against the reference's stored fit; "
                   "the reference's 2019-2024 fits are copied only when the inputs to 2024 are the reference's and the "
                   "refit equals the stored fit exactly", "checked_at": now(),
           "inputs_to_2024_identical": bool(chk.get("reference_inputs_to_2024_identical"))}
    if not res["inputs_to_2024_identical"]:
        res["pass"] = False
        write_json(CHECKS / "ref_noitf_repro.json", res)
        raise SystemExit("REF_noITF's inputs to 2024 differ from the reference's: fit all of 2019-2026 instead")
    local = CHECKS / "ref_noitf_repro"
    local.mkdir(parents=True, exist_ok=True)
    target = local / "model__2024__seed0.npz"
    if not target.exists():
        # model_rebuild/fits.py writes into <out>/fits; a scratch arm folder pointing at REF_noITF's frame keeps the
        # repro fit out of the arm's own fits/ until it has passed
        scratch = local / "arm"
        (scratch / "fits").mkdir(parents=True, exist_ok=True)
        for f in ("model_frame.parquet", "model_inputs.json"):
            if not (scratch / f).exists():
                shutil.copyfile(d / f, scratch / f)
        cmd = [_bash(), str(SHIM_GPU), "src/eda/model_rebuild/fits.py", "--out", str(scratch), "--seeds", "0",
               "--seasons", "2024", "--wait-memory-only"]
        with open(FIT_LOGS / "REF_noITF_repro.log", "a", encoding="utf-8") as fh:
            rc = subprocess.run(cmd, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode
        if rc != 0:
            raise SystemExit(f"the repro fit failed (exit {rc})")
        shutil.copyfile(scratch / "fits" / "model__2024__seed0.npz", target)
    with np.load(target, allow_pickle=False) as z:
        p_new, ids_new = z["p_td"], z["ids_td"].astype(str)
        m_new = json.loads(str(z["meta"]))
    with np.load(REF_DIR / "fits" / "model__2024__seed0.npz", allow_pickle=False) as z:
        p_old, ids_old = z["p_td"], z["ids_td"].astype(str)
        m_old = json.loads(str(z["meta"]))
    res.update({"ids_equal": bool(np.array_equal(ids_new, ids_old)),
                "largest_difference": float(np.max(np.abs(p_new - p_old))) if len(p_new) == len(p_old) else None,
                "fingerprint_equal": m_new.get("fingerprint") == m_old.get("fingerprint"),
                "columns_equal": m_new.get("columns") == m_old.get("columns"),
                "train_shape_equal": m_new.get("train_shape") == m_old.get("train_shape")})
    res["pass"] = bool(res["ids_equal"] and res["largest_difference"] == 0.0 and res["columns_equal"]
                       and res["train_shape_equal"])
    if res["pass"]:
        dst = d / "fits"
        dst.mkdir(parents=True, exist_ok=True)
        copied = []
        for s in range(2019, DEV_LAST + 1):
            for k in SEEDS:
                src = REF_DIR / "fits" / f"model__{s}__seed{k}.npz"
                out = dst / src.name
                if not out.exists():
                    shutil.copyfile(src, out)
                if sha256(out) != sha256(src):
                    raise SystemExit(f"{rel(out)} differs from the reference's fit")
                copied.append({"file": src.name, "sha256": sha256(out)})
        res["copied"] = copied
    write_json(CHECKS / "ref_noitf_repro.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "copied"}, indent=1))
    return res


# ------------------------------------------------------------------------------------------------
# Status and polling

def status() -> pd.DataFrame:
    rows = []
    for arm in FIT_ORDER:
        d = arm_dir(arm)
        have, missing = fits_present(arm)
        rows.append({"arm": arm, "folder": rel(d), "frame": (d / "model_frame.parquet").exists(),
                     "ready": (d / "READY.txt").exists() if arm not in D_BUILT else None,
                     "fits": have, "missing_dev": sum(1 for s, _ in missing if s <= DEV_LAST),
                     "missing_holdout": sum(1 for s, _ in missing if s > DEV_LAST),
                     "part1": (d / CMP_DIR / "part1_summary.json").exists()})
    return pd.DataFrame(rows)


def reuse_dev_fits(arm: str) -> str:
    """Addition 1: SYS_ITFASIS and SYS_BOTH_ITFASIS take their base arm's 2019-2024 fits when the two input frames are
    identical through 2024 (every input, exactly, NaN where NaN; the identifiers and training labels are checked against
    the reference by verify_frame). Returns "copied", "not identical" (then every season is fitted) or "waiting" (the
    base arm's 2019-2024 fits are not all on disk yet)."""
    from src.eda.lower_level_evidence import candidate_arms as CA
    base = REUSE_BASE[arm]
    if fits_present(base, range(2019, DEV_LAST + 1))[1]:
        return "waiting"
    a = CA.inputs_of(arm_dir(arm) / "model_frame.parquet")
    b = CA.inputs_of(arm_dir(base) / "model_frame.parquet")
    names = [n for n, _ in input_names(arm_dir(base))]
    same_ids = bool(len(a) == len(b) and (a["match_id"].to_numpy() == b["match_id"].to_numpy()).all())
    m = b["season"].to_numpy().astype(int) <= DEV_LAST
    differ = [] if same_ids else names
    if same_ids:
        for n in names:
            if not np.array_equal(a[f"in_{n}"].to_numpy(float)[m], b[f"in_{n}"].to_numpy(float)[m], equal_nan=True):
                differ.append(n)
    rec = {"arm": arm, "base": base, "checked_at": now(), "same_ids_in_order": same_ids,
           "inputs_differing_to_2024": differ, "identical_to_2024": not differ,
           "arm_frame_sha256": sha256(arm_dir(arm) / "model_frame.parquet"),
           "base_frame_sha256": sha256(arm_dir(base) / "model_frame.parquet")}
    if differ:
        write_json(CHECKS / f"{arm}_reuse.json", {**rec, "copied": []})
        log_line(QUEUE_LOG, f"{arm}: inputs to 2024 differ from {base}'s ({len(differ)} inputs): every season fitted")
        return "not identical"
    dst = arm_dir(arm) / "fits"
    dst.mkdir(parents=True, exist_ok=True)
    copied = []
    for s in range(2019, DEV_LAST + 1):
        for k in SEEDS:
            src = arm_dir(base) / "fits" / f"model__{s}__seed{k}.npz"
            out = dst / src.name
            if not out.exists():
                tmp = out.with_name(out.name + ".tmp")
                shutil.copyfile(src, tmp)
                tmp.replace(out)
            if sha256(out) != sha256(src):
                raise SystemExit(f"{rel(out)} differs from {rel(src)}")
            copied.append({"file": src.name, "sha256": sha256(out)})
    write_json(CHECKS / f"{arm}_reuse.json", {**rec, "copied": copied})
    log_line(QUEUE_LOG, f"{arm}: identical to {base} through 2024; its 24 fits of 2019-2024 copied (hashes equal)")
    return "copied"


def copied_registry() -> dict[str, str]:
    """{resolved path: SHA-256 recorded when copied} of the fit files D copied rather than fitted: R_S2's first-run
    fits, REF_noITF's dev fits (after the exact refit) and the ITFASIS arms' dev fits (identical inputs to 2024)."""
    out = {}
    prov = arm_dir("R_S2") / "provenance_D.json"
    if prov.exists():
        out.update({str((arm_dir("R_S2") / r["file"]).resolve()): r["sha256"]
                    for r in json.loads(prov.read_text(encoding="utf-8"))["files"] if r["file"].startswith("fits/")})
    for arm, rec in [("REF_noITF", CHECKS / "ref_noitf_repro.json")] + [(a, CHECKS / f"{a}_reuse.json")
                                                                         for a in REUSE_BASE]:
        if rec.exists():
            out.update({str((arm_dir(arm) / "fits" / r["file"]).resolve()): r["sha256"]
                        for r in json.loads(rec.read_text(encoding="utf-8")).get("copied", [])})
    return out


def copied_files() -> set[str]:
    """The fit files D copied rather than fitted (copied_registry's paths)."""
    return set(copied_registry())


def fit_times() -> pd.DataFrame:
    """Every fit on disk with its seconds (fit and prediction, the runner's metadata), training rows and time written;
    fitted_here False for copies. Writes results/fit_times.csv and fit_times_by_season.csv (the fits made here, by
    season, beside the reference's own seconds on a free card), for the lead's forecasts."""
    copied = copied_files()
    rows = []
    for arm in FIT_ORDER:
        d = arm_dir(arm) / "fits"
        if not d.exists():
            continue
        for p in sorted(d.glob("model__*__seed*.npz")):
            with np.load(p, allow_pickle=False) as z:
                meta = json.loads(str(z["meta"]))
            rows.append({"arm": arm, "season": int(meta["season"]), "seed": int(meta["seed"]),
                         "seconds": meta.get("seconds"), "train_rows": int(meta["train_shape"][0]),
                         "inputs": int(meta["train_shape"][1]), "gpu_free_gb_before": meta.get("gpu_free_gb_before"),
                         "written_utc": pd.Timestamp(p.stat().st_mtime, unit="s", tz="UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "fitted_here": str(p.resolve()) not in copied})
    t = pd.DataFrame(rows)
    if t.empty:
        return t
    t.to_csv(RESULTS / "fit_times.csv", index=False)
    ref = {}
    for p in sorted((REF_DIR / "fits").glob("model__*__seed*.npz")):
        with np.load(p, allow_pickle=False) as z:
            meta = json.loads(str(z["meta"]))
        ref.setdefault(int(meta["season"]), []).append(meta.get("seconds"))
    h = t[t["fitted_here"]]
    by = h.groupby("season")["seconds"].agg(fits="count", mean_seconds="mean", min_seconds="min",
                                           max_seconds="max").reset_index()
    by["reference_free_card_mean_seconds"] = by["season"].map({s: float(np.mean(v)) for s, v in ref.items()})
    by.to_csv(RESULTS / "fit_times_by_season.csv", index=False)
    return t


def process_arm(arm: str) -> bool | None:
    """build (D's arms) -> verify -> part 1 -> REF_noITF's repro or the ITFASIS reuse -> fit -> fit-file checks.
    True when the arm's 32 fits are on disk and pass; False when held (frame check, a failed fit); None when waiting
    (an ITFASIS arm whose base arm's 2019-2024 fits are not on disk yet)."""
    if arm == "SYS_PLACEBO" and not (arm_dir(arm) / "model_frame.parquet").exists():
        build_placebo()
    if arm == "SYS_S2" and not (arm_dir(arm) / "model_frame.parquet").exists():
        build_s2()
    chk = verify_frame(arm)
    if not chk["pass"]:
        log_line(QUEUE_LOG, f"hold {arm}: frame check failed ({rel(CHECKS / (arm + '_frame.json'))})")
        status_line(f"{arm} held: frame check failed ({rel(CHECKS / (arm + '_frame.json'))}); not fitted")
        return False
    if not (arm_dir(arm) / CMP_DIR / "part1_summary.json").exists():
        part1(arm)
    dev_missing = fits_present(arm, range(2019, DEV_LAST + 1))[1]
    if arm == "REF_noITF" and dev_missing:
        try:
            repro_ref_noitf()
        except SystemExit as e:
            log_line(QUEUE_LOG, f"REF_noITF repro: {e}; fitting every season")
    if arm in REUSE_BASE and dev_missing:
        r = reuse_dev_fits(arm)
        if r == "waiting":
            log_line(QUEUE_LOG, f"wait {arm}: {REUSE_BASE[arm]}'s 2019-2024 fits are not all on disk yet")
            return None
    rc = fit(arm)
    have, missing = fits_present(arm)
    fc = check_fits(arm)
    t = fit_times()
    if not missing:
        secs = t[(t["arm"] == arm) & t["fitted_here"]].groupby("season")["seconds"].mean().round(0).to_dict() \
            if len(t) else {}
        status_line(f"{arm} fitted: 32 fits on disk (2019-2026, seeds 0-3), fit-file checks "
                    f"{'pass' if fc['pass'] else 'FAIL'}; mean s per fit by season {secs}; input check written "
                    f"(part 1, no score)")
    elif rc != 0:
        status_line(f"{arm} held: the fit runner exited {rc} with {len(missing)} fits missing "
                    f"(results/fit_logs/{arm}.log)")
    return rc == 0 and not missing and fc["pass"]


def pick_next(ready: list[str], done: set, held: set, waiting: set) -> str | None:
    """The highest-priority arm (FIT_ORDER) that is ready, not done, not held and not waiting."""
    for a in FIT_ORDER:
        if a in ready and a not in done | held | waiting:
            return a
    return None


_SHA_CACHE: dict = {}


def _sha_cached(path: Path) -> str | None:
    if not path.exists():
        return None
    st = path.stat()
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key not in _SHA_CACHE:
        _SHA_CACHE[key] = sha256(path)
    return _SHA_CACHE[key]


def finished(arm: str) -> bool:
    """All 32 fits on disk and their fit-file checks passed on the frame that is on disk now."""
    rec = CHECKS / f"{arm}_fits.json"
    if fits_present(arm)[1] or not rec.exists():
        return False
    r = json.loads(rec.read_text(encoding="utf-8"))
    return bool(r.get("pass")) and r.get("fits") == 32 and \
        r.get("frame_sha256") == _sha_cached(arm_dir(arm) / "model_frame.parquet")


def ready_now() -> list[str]:
    """Arms with work: C1's with READY.txt; SYS_PLACEBO and SYS_S2 once SYS is READY and has passed its frame check;
    R_S2 while a fit is missing. An arm already finished on its current frame has no work."""
    sys_ok = ((arm_dir("SYS") / "READY.txt").exists() and (CHECKS / "SYS_frame.json").exists()
              and bool(json.loads((CHECKS / "SYS_frame.json").read_text(encoding="utf-8")).get("pass")))
    out = []
    for a in FIT_ORDER:
        if finished(a):
            continue
        if a == "R_S2":
            if (arm_dir(a) / "model_frame.parquet").exists() and fits_present(a)[1]:
                out.append(a)
        elif a in ("SYS_PLACEBO", "SYS_S2"):
            if sys_ok:
                out.append(a)
        elif (arm_dir(a) / "READY.txt").exists():
            out.append(a)
    return out


def _pid_alive(pid: int) -> bool:
    """Windows: is a process with this id running (tasklist; never os.kill, which terminates on Windows)?"""
    r = subprocess.run(["tasklist", "/FI", f"PID eq {int(pid)}", "/NH", "/FO", "CSV"], capture_output=True, text=True)
    return f'"{int(pid)}"' in r.stdout


def poll(minutes: float) -> int:
    """The continuous queue. Every 60 s: the highest-priority arm with work goes through process_arm; after each arm the
    list is read again, so an arm that became READY meanwhile with a higher priority goes next. Stops after `minutes`
    without work (a running fit is never interrupted). One poller at a time (results/poller.json)."""
    if POLL_LOCK.exists():
        d = json.loads(POLL_LOCK.read_text(encoding="utf-8"))
        if d.get("status") == "running" and d.get("pid") and _pid_alive(int(d["pid"])):
            raise SystemExit(f"another poller is running (pid {d['pid']}, since {d.get('started_at')}); not started")
    lock = {"pid": os.getpid(), "started_at": now(), "idle_minutes": minutes, "status": "running"}
    write_json(POLL_LOCK, lock)
    log_line(QUEUE_LOG, f"poller started (pid {os.getpid()}, stops after {minutes:.0f} idle minutes)")
    t_end = time.monotonic() + 60 * minutes
    done, held = set(), set()
    try:
        while True:
            waiting: set = set()
            worked = False
            while True:
                arm = pick_next(ready_now(), done, held, waiting)
                if arm is None:
                    break
                try:
                    ok = process_arm(arm)
                except (Exception, SystemExit) as e:             # noqa: BLE001 (held and reported, never retried blind)
                    log_line(QUEUE_LOG, f"hold {arm}: {type(e).__name__}: {e}")
                    status_line(f"{arm} held: {type(e).__name__}: {str(e)[:200]}; not fitted")
                    held.add(arm)
                    continue
                if ok is None:
                    waiting.add(arm)
                    continue
                worked = True
                (done if ok else held).add(arm)
            if worked:
                t_end = time.monotonic() + 60 * minutes
            if time.monotonic() > t_end:
                break
            time.sleep(60)
    finally:
        write_json(POLL_LOCK, {**lock, "status": "ended", "ended_at": now(), "done": sorted(done), "held": sorted(held)})
        log_line(QUEUE_LOG, f"poller ended (pid {os.getpid()}): done {sorted(done)}, held {sorted(held)}")
    print(status().to_string(index=False))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--prepare-r-s2", action="store_true")
    g.add_argument("--verify")
    g.add_argument("--part1")
    g.add_argument("--fit")
    g.add_argument("--fit60", help=argparse.SUPPRESS)
    g.add_argument("--queue")
    g.add_argument("--build-placebo", action="store_true")
    g.add_argument("--build-s2", action="store_true")
    g.add_argument("--repro-ref-noitf", action="store_true")
    g.add_argument("--status", action="store_true")
    g.add_argument("--poll", action="store_true")
    g.add_argument("--write-expectations", action="store_true")
    g.add_argument("--check-fits")
    g.add_argument("--fit-times", action="store_true")
    ap.add_argument("--seasons", default="2019-2026")
    ap.add_argument("--seeds", default="0-3")
    ap.add_argument("--minutes", type=float, default=20.0)
    a = ap.parse_args()
    seasons, seeds = tuple(span(a.seasons)), tuple(span(a.seeds))
    if a.fit60:
        return fit60(Path(a.fit60), list(seasons), list(seeds))
    if a.prepare_r_s2:
        prepare_r_s2()
        return 0
    if a.verify:
        r = verify_frame(a.verify)
        print(json.dumps({k: v for k, v in r.items() if k != "moved"}, indent=1, default=str))
        return 0 if r["pass"] else 1
    if a.part1:
        part1(a.part1)
        return 0
    if a.fit:
        return fit(a.fit, seasons, seeds)
    if a.queue:
        rc = 0
        for arm in [x for x in a.queue.split(",") if x]:
            rc |= fit(arm, seasons, seeds)
        log_line(QUEUE_LOG, f"queue finished: {a.queue}")
        return rc
    if a.build_placebo:
        build_placebo()
        return 0
    if a.build_s2:
        build_s2()
        return 0
    if a.repro_ref_noitf:
        return 0 if repro_ref_noitf()["pass"] else 1
    if a.status:
        print(status().to_string(index=False))
        return 0
    if a.write_expectations:
        write_expectations()
        print(f"written: {rel(EXPECTED)}")
        return 0
    if a.check_fits:
        r = check_fits(a.check_fits)
        print(json.dumps({k: v for k, v in r.items() if k != "rows"}, indent=1))
        return 0 if r["pass"] else 1
    if a.fit_times:
        t = fit_times()
        print(pd.read_csv(RESULTS / "fit_times_by_season.csv").round(1).to_string(index=False) if len(t) else "no fits")
        return 0
    return poll(a.minutes)


if __name__ == "__main__":
    sys.exit(main())
