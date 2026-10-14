"""Role D's scorer for the level-evidence system: every arm's pre-registered readings, both stages, with compare.py's own
functions; the selection rule applied mechanically; the 2025-2026 holdout behind its lock.

The plan, every file checked against its recorded SHA-256 before anything is read (a mismatch refuses):
    data/studies/lower_level_evidence/system/preregistration.md (cc65bcd5...) and its dated additions beside it
    (preregistration_addition_1.md: the rule of 8 October; _2: the evaluator's four questions; the checkpoint-1
    addition, which freezes SYS's internals and this scorer); docs/studies/lower_level_evidence/system/SPEC.md 7-8.

The decision layer (addition 4, the owner's decision of 9 Oct 2026, written before any score): the rules that turn
readings into a selection, a recommendation or the rule test's verdict live in system_decide.py. This scorer measures
and, for the record, still applies the registered rules: its dev run writes their selection to
results/selection_registered.json (not selection.json), and its holdout run writes their recommendation into
holdout/readings.json. The selection in force, results/selection.json, is written by system_decide.py --dev; the
holdout reads SELECTED from it only when it carries DECISION_LAYER. Changed for addition 4 (nothing that measures):
the registered selection's file name, that marker check, the freeze's file list (system_decide.py added) and the
freeze's matching (each hash in any verified addition, so addition 4b may list only what changed).

Modes
    --dev       seasons 2020-2024 scored, fits 2019-2024, results of seasons <= 2024 only (compare.py's filtered read).
                It never reads, computes or prints a number of a season after 2024. It refuses to run:
                  * until the freeze is on disk: the SHA-256, as on disk now, of every file in cp1_files (the classes,
                    the parameters, relationship.py, level_layer.py, level_layer_ios.py: addition 2 section 5; this
                    scorer and the fit queue: E's checkpoint 1, M4; system_decide.py: addition 4) written in verified
                    dated additions (3, and 4b for what changed). Any of them changed since: refused again;
                  * once system/holdout_unlock.json exists (the dev readings are written down before the unlock);
                  * unless every pre-registered arm is built and every one of its fits passes the provenance check
                    (REQUIRED_DEV; the lead may waive one with --allow-missing ARM, recorded in the outputs).
    --holdout   refuses to read any season after 2024 unless system/holdout_unlock.json exists and holds the SHA-256 of
                every pre-registration file on disk (each equal to the file and its recorded hash) and of the written
                dev selection (results/selection.json, the decision layer's); and it runs once: it refuses if
                results/holdout/readings.json exists. It also needs the freeze, a final selection carrying
                DECISION_LAYER, the same sides.parquet as dev (the strata), and every pre-registered arm with all 32
                fits passing the provenance check: a selected or compared arm with a missing fit fails loudly, never a
                fall back to REF.
    --harness   the first run's FP and R_S2 (candidates/, read only) through this scorer's code, against compare.py's
                scores.csv, the first run's pairs.csv and the published readings. No arm of this run is read.
    --run-compare   with --dev: also run compare.py itself on every main arm (its vs_reference_2026-10-08/) and check that
                its primary rows equal this scorer's. Not on the holdout: compare.py has no rule for addition 2's speed gap.

compare.py's recipe, unchanged (src/eda/current_best_model/compare.py): each model's seeds 0-3 forecasts (seed_table,
with its file checks: ids in order, training window, input list); the per-tour calibration slopes and stage 2's b,
fitted walk-forward on 2019 .. Y - 1, debut seasons out, b shrunk with tau 0.05 (walk_forward), on the reference's
speed column unless an arm's folder holds its own speed_columns.parquet; forecasts; paired log loss (paired: four-week
blocks plus the seeds' variance, paired by seed between two models; unpaired against a closing price); the matches every
frame of a group holds; the reference's match facts; debut seasons out.
Units: mLL per match. POSITIVE = THE FIRST-NAMED MODEL HAS THE LOWER LOG LOSS (better). "X vs Y" names X first.
Readings: "better" or "worse" when the 95% interval (compare.py's: t on blocks - 1) clears 0, otherwise "unresolved".
P(better) = Phi(estimate / se) (the pre-registration; addition 2 section 4); compare.py's t value is kept as p_better_t,
and a selection or recommendation step on which the two would disagree is flagged.

Fit provenance at scoring (E's checkpoint 1, S8): every fit file of a scored model must record the SHA-256 of the
model's own frame, or be a copy registered by the fit queue (system_fits.copied_registry) whose bytes still have the
recorded hash. Anything else refuses (a fit left from before a rebuild is never scored).

The 2026 speed rule (addition 2 section 1; the lead's message of 10 Oct): the reference's stage-2 speed memory is missing
for 909 matches of 2026 (416 men's). In every reading, a match without one gets no stage-2 nudge (b * spd_L = 0, the
forecast s_tour * eta), identically in every arm. The sensitivity, written beside the primary under separate files and
keys: the same readings with those 909 matches (both tours) left out.

The pre-registered readings (dev; the holdout adds its own below), each for both tours, men and women:
    every arm against REF (both stages; stage 1 alone overall), overall, in the strata and in each season; SYS against
    each challenger (SYS_w0, SYS_w50, SYS_w100, SEP_ALL, SYS_NOCLASS, SYS_S2, R_S2), SYS_PLACEBO and RES_ONLY (and the
    optional SYS_w25, SYS_w75), overall and by season; SYS_S2 against SYS; the dose curve (SYS_w0, [SYS_w25], SYS_w50,
    [SYS_w75], SYS_w100, SYS: each against REF and against SYS); each model against its calibrated close (scale).
    RES_ONLY (the checkpoint-1 addition; E's M3): RES_ONLY against REF (the Elo weighting alone) and SYS against
    RES_ONLY (the box-score layer beyond it); neither enters the selection.
    The strata (sides.parquet of role 02, counts only; the first run's definitions): the less-exposed side's main-tour
    results in 365 days under 10 / 10 or more; the 365-day lower-level box-score share gap 0.5 or more / under 0.5 /
    unknown (left out); falsification: both sides 20+ main-tour results and both shares under 0.10.
The selection rule (pre-registration "Dev"), men, both stages, dev: SYS unless a challenger has P(better than SYS) >= 0.90;
    of several, the largest point gain over SYS (a tie: the first in CHALLENGERS' order); then REF if that arm's
    P(better than REF) < 0.50. Women: no selection.
The holdout: the primary (SELECTED against REF, men); the decomposition, both tours and each tour: SELECTED against
    REF_noITF = everything the system changes except the ITF box-score exclusion, Elo weights included (the lead's
    relabelling of 10 Oct; not "the Challenger and qualifying part"), and REF_noITF against REF = the ITF box scores as-is;
    every secondary; the pooled 2020-2026 primary and dose curve; and the recommendation, applied mechanically, where "no
    secondary is worse" means (addition 2 section 3): none of eight men's holdout readings of SELECTED against REF (both
    stages: seasons 2025 and 2026, the six strata but "unknown"; and stage 1 alone overall) is worse after a Holm
    correction at a family-wise 5%: estimate < 0 and Holm-adjusted p < 0.05, p two-sided normal,
    2 (1 - Phi(|estimate| / se)) (the lead's ruling of 10 Oct). The raw labels are reported too.
Addition 1 (the rule of 8 October), apart from the selection, the Holm family and the recommendation: REF_noITF against
    REF; SYS against SYS_ITFASIS and SYS_BOTH against SYS_BOTH_ITFASIS (holdout; on dev too where their inputs differ
    before 2025: addition 2 section 2); NEW_ASIS against REF, NEW_SYS_BOTH against SYS_BOTH and against NEW_ASIS, and
    the optional NEW_ASIS_PRE against REF and NEW_ASIS against NEW_ASIS_PRE (dev, holdout, pooled; the candidate-Stage-0
    arms on the matches their frames, SYS_BOTH's and the reference's all hold); with the addition's guiding reading per
    data set (protective / holding back / mixed / unresolved).
Writes system/results/: selection_registered.json; dev/; holdout/ (primary files and *_drop909 sensitivity files);
harness/. (selection.json and the decisions: system_decide.py.)
Run: ./python.sh src/eda/lower_level_evidence/system_pairs.py --harness | --dev [--run-compare] | --holdout
                                                               [--allow-missing ARM,ARM]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.lower_level_evidence import system_fits as SF  # noqa: E402

SYSTEM = SF.SYSTEM
RESULTS = SF.RESULTS
PREREG = SYSTEM / "preregistration.md"
PREREG_SHA = SYSTEM / "preregistration.sha256"
UNLOCK = SYSTEM / "holdout_unlock.json"
SELECTION = RESULTS / "selection.json"                      # the decision layer's (system_decide.py --dev)
SELECTION_REGISTERED = RESULTS / "selection_registered.json"  # this scorer's dev run: the registered rules' outcome
# The owner's decision of 9 Oct (addition 4) replaced the decision layer: selection.json is written by system_decide.py,
# and the holdout reads SELECTED from it only when it carries this marker
DECISION_LAYER = "owner decision 2026-10-09 (adoption by change class), addition 4"

DEV_LAST = 2024
DEV_TEST = tuple(range(CMP.SCORE_FROM, DEV_LAST + 1))          # 2020-2024
DEV_FITS = tuple(range(CMP.FIT_FROM, DEV_LAST + 1))            # 2019-2024
HOLDOUT = (2025, 2026)
POOLED = tuple(range(CMP.SCORE_FROM, 2027))                    # 2020-2026
ALL_FITS = tuple(range(CMP.FIT_FROM, 2027))                    # 2019-2026
H, PD = "holdout 2025-2026", "pooled 2020-2026"

CHALLENGERS = ("SYS_w0", "SYS_w50", "SYS_w100", "SEP_ALL", "SYS_NOCLASS", "SYS_S2", "R_S2")
ARMS = ("SYS",) + CHALLENGERS + ("SYS_PLACEBO", "SYS_BOTH", "REF_noITF", "RES_ONLY", "SYS_w25", "SYS_w75")
OPTIONAL = ("SYS_w25", "SYS_w75", "NEW_ASIS_PRE")
DEV_ARMS = tuple(a for a in ARMS if a != "REF_noITF")         # "every arm except REF_noITF"
REQUIRED_DEV = ("SYS",) + CHALLENGERS + ("SYS_PLACEBO", "SYS_BOTH", "RES_ONLY")
REQUIRED_HOLDOUT = REQUIRED_DEV + ("REF_noITF",)
SYS_VS = CHALLENGERS + ("SYS_PLACEBO", "RES_ONLY", "SYS_w25", "SYS_w75")
DOSE = (("SYS_w0", "0"), ("SYS_w25", "0.25"), ("SYS_w50", "0.5"), ("SYS_w75", "0.75"), ("SYS_w100", "1"),
        ("SYS", "fitted (role B)"))
DOSE_PREREG = ("SYS_w0", "SYS_w50", "SYS", "SYS_w100")
P_CHALLENGER = 0.90
P_REF_FLOOR = 0.50
P_RECOMMEND = 0.80
HOLM_ALPHA = 0.05
TOURS = {"both tours": None, "men": "atp", "women": "wta"}
STRATA = ("exposure < 10", "exposure >= 10", "share gap >= 0.5", "share gap < 0.5", "share gap unknown (left out)",
          "falsification: both 20+ main-tour, share < 0.10")
# Addition 2 section 3: the eight men's holdout readings of SELECTED against REF in the Holm family
HOLM_FAMILY = (("season 2025", "both stages"), ("season 2026", "both stages"), ("exposure < 10", "both stages"),
               ("exposure >= 10", "both stages"), ("share gap >= 0.5", "both stages"),
               ("share gap < 0.5", "both stages"), ("falsification: both 20+ main-tour, share < 0.10", "both stages"),
               ("all", "stage 1"))
# Addition 1 (the rule of 8 October) and the optional C0_pre arm: none of these enters the selection
ITFASIS = ("SYS_ITFASIS", "SYS_BOTH_ITFASIS")
NEW = ("NEW_ASIS", "NEW_SYS_BOTH", "NEW_ASIS_PRE")
ADD1_MAIN = (("REF_noITF", "REF"), ("SYS", "SYS_ITFASIS"), ("SYS_BOTH", "SYS_BOTH_ITFASIS"))
ADD1_NEW = (("NEW_ASIS", "REF"), ("NEW_SYS_BOTH", "SYS_BOTH"), ("NEW_SYS_BOTH", "NEW_ASIS"), ("NEW_ASIS_PRE", "REF"),
            ("NEW_ASIS", "NEW_ASIS_PRE"))
P_PROTECTIVE = 0.20
# What the checkpoint-1 addition must record, as on disk now (addition 2 section 5; E's checkpoint 1, M4); the
# recommended ones are reported when absent but do not refuse
LLE_SRC = ROOT / "src" / "eda" / "lower_level_evidence"
CP1_DATA = ("classes/classes.csv", "relationship/params.parquet")                  # under the system folder
CP1_CODE = {"relationship.py": LLE_SRC / "relationship.py", "level_layer.py": LLE_SRC / "level_layer.py",
            "level_layer_ios.py": LLE_SRC / "level_layer_ios.py", "system_pairs.py": LLE_SRC / "system_pairs.py",
            "system_fits.py": LLE_SRC / "system_fits.py", "system_decide.py": LLE_SRC / "system_decide.py"}
CP1_RECOMMENDED_DATA = ("relationship/params_noclass.parquet",)
CP1_RECOMMENDED_CODE = {"system_arms.py": LLE_SRC / "system_arms.py",
                        "system_sandbox.py": LLE_SRC / "system_sandbox.py",
                        "compare.py": ROOT / "src" / "eda" / "current_best_model" / "compare.py"}


def cp1_files(system: Path, recommended: bool = False) -> dict[str, Path]:
    data, code = (CP1_RECOMMENDED_DATA, CP1_RECOMMENDED_CODE) if recommended else (CP1_DATA, CP1_CODE)
    return {**{k: Path(system) / k for k in data}, **code}


class HoldoutLocked(SystemExit):
    """Raised before any read of a season after 2024 when the holdout is not unlocked."""


# ------------------------------------------------------------------------------------------------
# The pre-registration, the checkpoint-1 freeze and the lock

def hashes_of(path: Path) -> tuple[str, str]:
    """(SHA-256 of the raw bytes, SHA-256 with CRLF normalised to LF)."""
    b = Path(path).read_bytes()
    return hashlib.sha256(b).hexdigest(), hashlib.sha256(b.replace(b"\r\n", b"\n")).hexdigest()


def recorded(sha_file: Path) -> str:
    """The first token of a sha256 file ('<hex>  *name' or '<hex>')."""
    return Path(sha_file).read_text(encoding="utf-8").split()[0].strip().lower()


def addition_files(system: Path | None = None) -> list[Path]:
    system = Path(system or SYSTEM)
    found = set(system.glob("preregistration*.md")) | set(system.glob("*addition*.md"))
    return sorted(p for p in found if p.name != "preregistration.md")


def sha_file_of(path: Path) -> Path:
    """<stem>.sha256 or <name>.sha256 beside the file (the first that exists; else the first)."""
    options = [path.with_suffix(".sha256"), path.with_name(path.name + ".sha256")]
    return next((p for p in options if p.exists()), options[0])


def verify_prereg(system: Path | None = None) -> dict:
    """The pre-registration and every dated addition beside it must equal their recorded hashes; else refuse."""
    system = Path(system or SYSTEM)
    out = {}
    for path in [system / "preregistration.md"] + addition_files(system):
        sha_file = sha_file_of(path)
        if not sha_file.exists():
            raise SystemExit(f"{path.name}: no {sha_file.name} beside it; refusing to score")
        want = recorded(sha_file)
        raw, lf = hashes_of(path)
        if want not in (raw, lf):
            raise SystemExit(f"{path.name} changed after it was hashed ({raw} != {want}); refusing to score")
        out[path.name] = want
    return out


def _hex_values(obj) -> set[str]:
    """Every 64-hex string anywhere in a JSON value, or in a text (lower case)."""
    out = set()
    if isinstance(obj, dict):
        for v in obj.values():
            out |= _hex_values(v)
    elif isinstance(obj, list):
        for v in obj:
            out |= _hex_values(v)
    elif isinstance(obj, str):
        s = obj.strip().lower()
        if len(s) == 64 and all(c in "0123456789abcdef" for c in s):
            out.add(s)
    return out


def verify_unlock(system: Path | None = None) -> dict:
    """The holdout's lock. holdout_unlock.json must exist and hold the SHA-256 of every pre-registration file on disk
    (preregistration.md and each dated addition), each equal to the file on disk and to its recorded hash; the main
    file's hash is expected under "preregistration_sha256", the others under any key. Raises HoldoutLocked otherwise,
    before anything after 2024 is read."""
    system = Path(system or SYSTEM)
    unlock, prereg = system / "holdout_unlock.json", system / "preregistration.md"
    if not unlock.exists():
        raise HoldoutLocked(f"the holdout is locked: {unlock} does not exist (the lead writes it after checkpoint 2)")
    try:
        d = json.loads(unlock.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise HoldoutLocked(f"the holdout is locked: {unlock.name} is not readable JSON ({e})")
    held = _hex_values(d)
    if not held:
        raise HoldoutLocked(f"the holdout is locked: {unlock.name} holds no SHA-256 (expected 'preregistration_sha256')")
    checked = {}
    for path in [prereg] + addition_files(system):
        raw, lf = hashes_of(path)
        sha_file = sha_file_of(path)
        rec = recorded(sha_file) if sha_file.exists() else None
        got = raw if raw in held else lf if lf in held else None
        if got is None:
            raise HoldoutLocked(f"the holdout is locked: {unlock.name} does not hold the hash of {path.name} as it is "
                                f"on disk ({raw})")
        if got != rec:
            raise HoldoutLocked(f"the holdout is locked: {path.name}'s hash {got} is not its recorded hash {rec}")
        checked[path.name] = got
    return {"unlock_file": SF.rel(unlock), "files": checked, "preregistration_sha256": checked[prereg.name],
            "held": sorted(held), "unlock": d}


def cp1_addition(system: Path | None = None, required: dict | None = None) -> dict:
    """The freeze, recognised by content: every file of cp1_files (the classes and parameters under the system folder;
    relationship.py, level_layer.py, level_layer_ios.py, this scorer, the fit queue and the decision module) must have
    its SHA-256, as on disk now, written in a dated addition beside the pre-registration (checkpoint 1's addition 3;
    the later addition 4b for files changed or added since). Each hash may sit in any addition; the callers verify every
    addition against its own hash file first (verify_prereg). Returns {"file": the additions that hold them, joined by
    " + ", or None, "held_in": {file: addition}, "missing": [...], "recommended_missing": [...], "hashes": {...}}; file
    is None when a hash is in no addition (or the file moved on since)."""
    system = Path(system or SYSTEM)
    required = cp1_files(system) if required is None else required
    want, absent = {}, []
    for name, p in required.items():
        if Path(p).exists():
            want[name] = hashes_of(Path(p))[0]
        else:
            absent.append(name)
    rec = {k: hashes_of(Path(p))[0] for k, p in cp1_files(system, recommended=True).items() if Path(p).exists()}
    texts = {p.name: p.read_text(encoding="utf-8", errors="replace").lower() for p in addition_files(system)}
    held_in = {k: next((n for n, t in texts.items() if h in t), None) for k, h in want.items()}
    missing = sorted(set(absent) | {k for k, n in held_in.items() if n is None})
    recommended_missing = sorted(k for k, h in rec.items() if not any(h in t for t in texts.values()))
    used = sorted({n for n in held_in.values() if n is not None})
    return {"file": " + ".join(used) if not missing and used else None, "held_in": held_in, "missing": missing,
            "recommended_missing": recommended_missing, "hashes": want}


def require_cp1(without_addition: bool) -> dict:
    cp1 = cp1_addition()
    if cp1["file"] is None and not without_addition:
        raise SystemExit("no checkpoint-1 addition (3, or a later one such as 4b) holds the SHA-256, as on disk now, of: "
                         + ", ".join(cp1["missing"]) + ". The additions freeze SYS's internals, this scorer and the "
                         "decision module before any score is read (--without-addition only on the lead's word)")
    return cp1


# ------------------------------------------------------------------------------------------------
# Arms, fits and models

def arm_folders(names, base: dict | None = None) -> dict[str, Path]:
    """{arm: folder} for the arms whose frame exists (system/arms/ or D's system/results/arms/)."""
    base = base or {}
    out = {}
    for a in names:
        d = base.get(a, SF.arm_dir(a))
        if (Path(d) / "model_frame.parquet").exists():
            out[a] = Path(d)
    return out


def complete(folder: Path, seasons) -> bool:
    return all((folder / "fits" / f"model__{s}__seed{k}.npz").exists() for s in seasons for k in CMP.SEEDS)


def fit_problems(folder: Path, seasons, registry: dict | None = None) -> list[str]:
    """Provenance at scoring: every (season, seed 0-3) fit exists and records the SHA-256 of the folder's own frame, or
    is a copy registered by the fit queue whose bytes still have the recorded hash."""
    registry = SF.copied_registry() if registry is None else registry
    frame_sha = SF._sha_cached(Path(folder) / "model_frame.parquet")
    out = []
    for s in seasons:
        for k in CMP.SEEDS:
            p = Path(folder) / "fits" / f"model__{s}__seed{k}.npz"
            if not p.exists():
                out.append(f"{p.name}: missing")
                continue
            with np.load(p, allow_pickle=False) as z:
                meta = json.loads(str(z["meta"]))
            if meta.get("model_frame_sha256") == frame_sha:
                continue
            key = str(p.resolve())
            if key not in registry:
                out.append(f"{p.name}: fitted on another frame ({str(meta.get('model_frame_sha256'))[:12]}) and not a "
                           f"registered copy")
            elif SF.sha256(p) != registry[key]:
                out.append(f"{p.name}: a registered copy whose bytes changed")
    return out


def gather(names, seasons, required=(), allow_missing=()) -> tuple[dict[str, Path], dict]:
    """The arms to score, loudly: a required arm without a frame refuses; an arm whose frame exists refuses unless all
    its fits of `seasons` pass the provenance check (an optional arm, or one the lead waived, is then skipped and
    recorded). Never a silent drop, never a fall back."""
    usable, rec = {}, {"absent": [], "skipped": {}, "waived": sorted(allow_missing)}
    for a in names:
        d = SF.arm_dir(a)
        if not (d / "model_frame.parquet").exists():
            if a in required and a not in allow_missing:
                raise SystemExit(f"{a}: a pre-registered arm with no frame; refusing (--allow-missing {a} only on the "
                                 f"lead's word)")
            rec["absent"].append(a)
            continue
        problems = fit_problems(d, seasons)
        if problems:
            if a in OPTIONAL or a in allow_missing:
                rec["skipped"][a] = problems[:5]
                continue
            raise SystemExit(f"{a}: {len(problems)} fit problems for seasons {seasons[0]}-{seasons[-1]}: "
                             f"{problems[:4]}; refusing (a compared arm never falls back)")
        usable[a] = d
    return usable, rec


def speed_of(folder: Path | None, z_ref: pd.Series) -> tuple[pd.Series, str]:
    if folder is not None and (folder / "speed_columns.parquet").exists():
        z = pd.read_parquet(folder / "speed_columns.parquet", columns=["match_id", "spd_L_B"])
        return z.astype({"match_id": str}).set_index("match_id")["spd_L_B"], SF.rel(folder / "speed_columns.parquet")
    return z_ref, "the reference's"


def speed_gap_ids(info: pd.DataFrame, z_ref: pd.Series, test) -> pd.Index:
    """The matches of the test seasons (both tours, debut or not) without a reference speed memory: addition 2's 909
    matches of 2026 (416 men's) when the test seasons include 2026; none in 2019-2025."""
    m = info["season"].isin(list(test)).to_numpy()
    v = z_ref.reindex(info.index).to_numpy(float)
    return info.index[m & ~np.isfinite(v)]


def apply_speed_rule(info: pd.DataFrame, z: pd.Series, gap: pd.Index, rule: str) -> pd.Series:
    """The model's stage-2 column on info's matches: rule "zero" sets the gap matches to 0 (no nudge, every arm alike);
    rule "drop909" expects them already left out of info."""
    zz = z.reindex(info.index).astype(float)
    if rule == "zero":
        zz.loc[zz.index.intersection(gap)] = 0.0
    return zz


def load_models(arms: dict[str, Path], through: int, fit_seasons, test_seasons, speed_rule: str = "zero",
                strict_price: bool = True) -> tuple[pd.DataFrame, dict]:
    """info (the reference's match facts on the matches every frame holds, seasons 2019 .. through) and, per model
    (REF and each arm), its seed table and walk-forward parameters for test_seasons (stage 1 alone and both stages).
    Results are read for seasons <= through only (compare.outcomes' filtered read). Any season after 2024 (results,
    fits or scores) needs the unlock: verify_unlock runs here, before the first read.
    speed_rule: "zero" (addition 2 section 1: the gap matches get no stage-2 nudge) or "drop909" (the sensitivity: they
    are left out, both tours). A scored men's match still without a speed value after the rule refuses.
    strict_price: every arm's closing price must equal the reference's on the scored matches (False for the candidate-
    Stage-0 arms: the differences are counted; the price enters only the rows against the close)."""
    if max(through, max(fit_seasons), max(test_seasons)) > DEV_LAST:
        verify_unlock()
    if max(fit_seasons) > through or max(test_seasons) > through:
        raise RuntimeError("a season after --through was asked for")
    if speed_rule not in ("zero", "drop909"):
        raise ValueError("speed_rule: zero or drop909")
    P_ref = R.paths("reference")
    ref = CMP.inputs_frame(P_ref)
    frames = {"REF": (P_ref, ref, None)}
    for a, d in arms.items():
        _, P, folder = CMP.candidate(str(d))
        frames[a] = (P, CMP.inputs_frame(P), folder)
    ids = ref.index
    for _, (_, f, _) in frames.items():
        ids = ids.intersection(f.index)
    y_ref = CMP.outcomes(P_ref, through)
    info = CMP.scoring_info(ref.loc[ids], ref.loc[ids], y_ref, y_ref, through)
    if int(info["season"].max()) > through:
        raise RuntimeError("a season after --through reached the scored matches")
    price_diff = {}
    for a in arms:
        y = CMP.outcomes(frames[a][0], through).reindex(info.index)
        if not np.array_equal(y.to_numpy(float), info["y"].to_numpy(float)):
            raise SystemExit(f"{a}: its results differ from the reference's")
        pa_, pr_ = frames[a][1].loc[info.index, "p_mkt"].to_numpy(float), info["p_ref"].to_numpy(float)
        same = (pa_ == pr_) | (np.isnan(pa_) & np.isnan(pr_))
        if not same.all():
            if strict_price:
                raise SystemExit(f"{a}: its closing price differs from the reference's")
            price_diff[a] = int((~same).sum())
    z_ref = R.speed_column("reference")
    gap = speed_gap_ids(info, z_ref, test_seasons)
    if speed_rule == "drop909":
        info = info.drop(index=gap)
    models = {}
    for name, (P, f, folder) in frames.items():
        p = CMP.seed_table(P, f, fit_seasons).reindex(info.index)
        if p.isna().any().any():
            raise SystemExit(f"{name}: forecasts missing on scored matches")
        z_raw, z_src = speed_of(folder, z_ref)
        z = apply_speed_rule(info, z_raw, gap, speed_rule)
        scored_men = (info["season"].isin(list(test_seasons)) & (info["tour"] == "atp")).to_numpy()
        if not np.isfinite(z.to_numpy()[scored_men]).all():
            raise SystemExit(f"{name}: scored men's matches without a speed value outside addition 2's gap")
        eta = pd.Series(CMP.C.lg(p.mean(axis=1).to_numpy()), index=p.index)
        models[name] = {"p": p, "z": z, "speed": z_src, "folder": SF.rel(folder) if folder else "frozen reference",
                        "price_differs_on": price_diff.get(name, 0), "matches_in_frame": int(len(f)),
                        "matches_scored_pool": int(len(info)),
                        "s1": CMP.walk_forward(eta, info, None, test_seasons),
                        "s2": CMP.walk_forward(eta, info, z, test_seasons)}
    models["_speed"] = {"rule": speed_rule, "gap_matches": int(len(gap)),
                        "gap_men": int((info.reindex(gap)["tour"] == "atp").sum()) if speed_rule == "zero" else None}
    return info, models


def fc(models: dict, name: str, stage: str, info: pd.DataFrame, ids: pd.Index):
    m = models[name]
    return CMP.forecasts(m["p"], info, m[stage], m["z"] if stage == "s2" else None, ids)


def p_better(estimate: float, se: float) -> float:
    """The pre-registration's P(better) = Phi(estimate / se); NaN for identical forecasts."""
    if se > 0:
        return float(norm.cdf(estimate / se))
    return 1.0 if estimate > 0 else 0.0 if estimate < 0 else float("nan")


def p_two_sided(estimate: float, se: float) -> float:
    """The lead's Holm p-value (10 Oct): two-sided normal, 2 (1 - Phi(|estimate| / se)), consistent with Phi's
    P(better). NaN for identical forecasts."""
    if se is None or not np.isfinite(se) or se <= 0 or not np.isfinite(estimate):
        return float("nan")
    return float(2 * norm.sf(abs(estimate) / se))


def paired(info, ids, base_fc, arm_fc, matched: bool = True) -> dict:
    """compare.paired (positive = arm better) with P(better) as pre-registered (Phi) and compare.py's t CDF kept. A
    population inside fewer than two four-week blocks (or weeks) has no clustered interval: it gets a row of NaN read
    "too few blocks" (compare.py would divide by blocks - 1 = 0)."""
    if min(info.loc[ids, "block"].nunique(), info.loc[ids, "week"].nunique()) < 2:
        nan = float("nan")
        return {"matches": int(len(ids)), "estimate": nan, "lo": nan, "hi": nan, "se": nan, "p_better": nan,
                "p_better_t": nan, "p_two_sided": nan, "blocks": int(info.loc[ids, "block"].nunique()),
                "reading": "too few blocks"}
    r = CMP.paired(info, ids, base_fc, arm_fc, matched=matched)
    r["p_better_t"] = r["p_better"]
    r["p_better"] = p_better(r["estimate"], r["se"])
    r["p_two_sided"] = p_two_sided(r["estimate"], r["se"])
    r["reading"] = CMP.reading(r["lo"], r["hi"])
    return r


# ------------------------------------------------------------------------------------------------
# Populations

def side_counts(index: pd.Index) -> pd.DataFrame:
    """Per scored match (counts only, sides.parquet of role 02): each side's main-tour results in 365 days and lower-level
    share of 365-day box-score evidence (lower = TQ, GSQ, CH, CHQ, ITF, ITFQ of all 8 buckets; NaN without box scores)."""
    from src.eda.lower_level_evidence import candidate_arms as CA
    cols = ["match_id", "side", "res_365d_MAIN"] + [f"box_365d_{b}" for b in CA.ALL_BUCKETS]
    s = pd.read_parquet(CA.SIDES, columns=cols)
    s["match_id"] = s["match_id"].astype(str)
    tot = s[[f"box_365d_{b}" for b in CA.ALL_BUCKETS]].sum(axis=1).to_numpy(float)
    low = s[[f"box_365d_{b}" for b in CA.LOWER]].sum(axis=1).to_numpy(float)
    s["share"] = np.where(tot > 0, low / np.where(tot > 0, tot, 1.0), np.nan)
    a = s[s["side"] == "A"].set_index("match_id").reindex(index)
    b = s[s["side"] == "B"].set_index("match_id").reindex(index)
    return pd.DataFrame({"res_a": a["res_365d_MAIN"].to_numpy(float), "res_b": b["res_365d_MAIN"].to_numpy(float),
                         "share_a": a["share"].to_numpy(float), "share_b": b["share"].to_numpy(float)}, index=index)


def sides_sha256() -> str:
    from src.eda.lower_level_evidence import candidate_arms as CA
    return SF.sha256(CA.SIDES)


def strata_masks(sc: pd.DataFrame) -> dict[str, np.ndarray]:
    """The pre-registered strata (the first run's definitions, candidate_pairs.strata), without the season filter."""
    expo = np.minimum(sc["res_a"].to_numpy(), sc["res_b"].to_numpy())
    gap = np.abs(sc["share_a"].to_numpy() - sc["share_b"].to_numpy())
    known = np.isfinite(gap)
    fals = ((sc["res_a"].to_numpy() >= 20) & (sc["res_b"].to_numpy() >= 20)
            & (sc["share_a"].to_numpy() < 0.10) & (sc["share_b"].to_numpy() < 0.10))
    return {"exposure < 10": expo < 10, "exposure >= 10": expo >= 10,
            "share gap >= 0.5": known & (gap >= 0.5), "share gap < 0.5": known & (gap < 0.5),
            "share gap unknown (left out)": ~known,
            "falsification: both 20+ main-tour, share < 0.10": fals}


def populations(info: pd.DataFrame, test, strata: bool = True, seasons: bool = True) -> list[tuple[str, str, np.ndarray]]:
    """(tour, population, mask) on the scored matches of `test`, debut seasons out: overall, each stratum, each season;
    each for both tours, men and women."""
    keep = ~info["debut"].to_numpy() & info["season"].isin(list(test)).to_numpy()
    tour = info["tour"].to_numpy()
    sm = strata_masks(side_counts(info.index)) if strata else {}
    out = []
    for tname, t in TOURS.items():
        tm = keep if t is None else keep & (tour == t)
        out.append((tname, "all", tm))
        for k, m in sm.items():
            out.append((tname, k, tm & m))
        if seasons:
            for Y in test:
                out.append((tname, f"season {Y}", tm & (info["season"].to_numpy() == Y)))
    return out


# ------------------------------------------------------------------------------------------------
# The readings

def row(period: str, group: str, first: str, second: str, stage: str, tour: str, pop: str, r: dict) -> dict:
    return {"period": period, "group": group, "comparison": f"{first} vs {second}", "first": first, "second": second,
            "stage": stage, "tour": tour, "population": pop,
            **{k: r[k] for k in ("matches", "estimate", "lo", "hi", "se", "p_better", "p_better_t", "p_two_sided",
                                 "blocks", "reading")}}


def readings(info: pd.DataFrame, models: dict, test, period: str, vs_ref_arms, sys_vs, extra_pairs=(),
             strata: bool = True, closes: bool = True) -> pd.DataFrame:
    """The rows of one period: every arm against REF (both stages; stage 1 alone overall), SYS against the listed arms,
    the extra (first, second) pairs, each against its calibrated close."""
    pops = populations(info, test, strata=strata)
    rows = []
    for a in vs_ref_arms:
        if a not in models:
            continue
        for tour, pop, mask in pops:
            ids = info.index[mask]
            if len(ids) == 0:
                continue
            r = paired(info, ids, fc(models, "REF", "s2", info, ids), fc(models, a, "s2", info, ids))
            rows.append(row(period, "vs REF", a, "REF", "both stages", tour, pop, r))
            if pop == "all":
                r = paired(info, ids, fc(models, "REF", "s1", info, ids), fc(models, a, "s1", info, ids))
                rows.append(row(period, "vs REF", a, "REF", "stage 1", tour, pop, r))
    pairs = [("SYS", b) for b in sys_vs if b in models and "SYS" in models] + \
            [(x, y) for x, y in extra_pairs if x in models and y in models]
    for first, second in pairs:
        for tour, pop, mask in pops:
            if pop != "all" and not pop.startswith("season"):
                continue
            ids = info.index[mask]
            if len(ids) == 0:
                continue
            r = paired(info, ids, fc(models, second, "s2", info, ids), fc(models, first, "s2", info, ids))
            rows.append(row(period, "arm vs arm", first, second, "both stages", tour, pop, r))
    if closes:
        for name in [k for k in models if not k.startswith("_")]:
            for tour, pop, mask in pops:
                if pop != "all":
                    continue
                ids = info.index[mask]
                r = paired(info, ids, CMP.close_forecast(info, "p_ref", test, ids), fc(models, name, "s2", info, ids),
                           matched=False)
                rows.append(row(period, "vs close", name, "its calibrated close", "both stages", tour, pop, r))
    return pd.DataFrame(rows)


def get(t: pd.DataFrame, first: str, second: str, tour: str = "men", pop: str = "all", stage: str = "both stages",
        period: str | None = None) -> dict | None:
    if t is None or not len(t):
        return None
    s = t[(t["first"] == first) & (t["second"] == second) & (t["tour"] == tour) & (t["population"] == pop)
          & (t["stage"] == stage)]
    if period is not None:
        s = s[s["period"] == period]
    return s.iloc[0].to_dict() if len(s) else None


def dose_curve(t: pd.DataFrame, period: str) -> pd.DataFrame:
    rows = []
    for arm, w in DOSE:
        for tour in TOURS:
            vr = get(t, arm, "REF", tour, period=period)
            vs = get(t, "SYS", arm, tour, period=period) if arm != "SYS" else None
            if vr is None:
                continue
            rows.append({"period": period, "arm": arm, "w": w, "pre_registered": arm in DOSE_PREREG, "tour": tour,
                         "vs_REF_estimate": vr["estimate"], "vs_REF_lo": vr["lo"], "vs_REF_hi": vr["hi"],
                         "vs_REF_p_better": vr["p_better"], "vs_REF_reading": vr["reading"],
                         "SYS_vs_arm_estimate": vs["estimate"] if vs else np.nan,
                         "SYS_vs_arm_p_better": vs["p_better"] if vs else np.nan,
                         "SYS_vs_arm_reading": vs["reading"] if vs else ""})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# The selection rule and the recommendation (pure: tested on synthetic readings)

def select(sys_vs: dict, vs_ref: dict, p_key: str = "p_better") -> dict:
    """The pre-registered selection, men, dev, both stages.
    sys_vs[C]: the reading "SYS vs C" (estimate, se, lo, hi, p_better; + = SYS better), or None when C is unscored.
    vs_ref[A]: the reading "A vs REF" (+ = A better), or None.
    A challenger qualifies when P(it is better than SYS) = Phi(-estimate / se) >= 0.90 (with p_key="p_better_t", the t
    CDF's 1 - p_better_t); of several, the one with the largest point gain over SYS (-estimate) is the step-1 arm (a tie:
    the first in CHALLENGERS' order); REF is selected when the step-1 arm's P(better than REF) < 0.50."""
    rows, missing = [], []
    for c in CHALLENGERS:
        r = sys_vs.get(c)
        if r is None:
            missing.append(c)
            rows.append({"challenger": c, "scored": False})
            continue
        gain = -float(r["estimate"])
        if p_key == "p_better":
            p_c = p_better(gain, float(r["se"]))
        else:
            p_c = 1.0 - float(r[p_key]) if np.isfinite(r[p_key]) else float("nan")
        rows.append({"challenger": c, "scored": True, "gain_over_SYS_mLL": gain, "lo": -float(r["hi"]),
                     "hi": -float(r["lo"]), "se": float(r["se"]), "p_better_than_SYS": p_c,
                     "reading_vs_SYS": {"better": "worse", "worse": "better"}.get(r["reading"], "unresolved"),
                     "qualifies": bool(np.isfinite(p_c) and p_c >= P_CHALLENGER)})
    qual = [r for r in rows if r.get("qualifies")]
    step1 = max(qual, key=lambda r: r["gain_over_SYS_mLL"])["challenger"] if qual else "SYS"
    ref_r = vs_ref.get(step1)
    p_ref = None
    if ref_r is not None:
        p_ref = p_better(float(ref_r["estimate"]), float(ref_r["se"])) if p_key == "p_better" else float(ref_r[p_key])
    sys_scored = vs_ref.get("SYS") is not None
    ok = (not missing) and sys_scored and p_ref is not None and np.isfinite(p_ref)
    selected = ("REF" if p_ref < P_REF_FLOOR else step1) if ok else None
    return {"status": "final" if ok else "incomplete", "missing_challengers": missing,
            "challengers": rows, "qualifying": [r["challenger"] for r in qual], "step1_arm": step1,
            "step1_p_better_than_REF": p_ref, "selected": selected,
            "rule": "SYS unless a challenger has P(better than SYS) >= 0.90 for men on dev (both stages); of several, "
                    "the largest point gain over SYS; then REF if that arm's P(better than REF) < 0.50; women: no "
                    "selection"}


def selection_from(t: pd.DataFrame, period: str) -> dict:
    sys_vs = {c: get(t, "SYS", c, "men", period=period) for c in CHALLENGERS}
    vs_ref = {a: get(t, a, "REF", "men", period=period) for a in ("SYS",) + CHALLENGERS}
    res = select(sys_vs, vs_ref)
    alt = select(sys_vs, vs_ref, p_key="p_better_t")
    res["t_cdf_check"] = {"selected_with_t_cdf": alt["selected"], "qualifying_with_t_cdf": alt["qualifying"],
                          "agrees": alt["selected"] == res["selected"] and alt["qualifying"] == res["qualifying"]}
    return res


def holm_adjust(p: list[float]) -> list[float]:
    """Holm's step-down adjusted p-values (a NaN p counts as 1)."""
    q = [1.0 if (v is None or not np.isfinite(v)) else float(v) for v in p]
    m = len(q)
    order = sorted(range(m), key=lambda i: q[i])
    adj, running = [float("nan")] * m, 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * q[i]))
        adj[i] = running
    return adj


def holm_family(t: pd.DataFrame, selected: str, period: str = H) -> dict:
    """Addition 2 section 3: the eight men's holdout readings of SELECTED against REF; "worse after Holm" = estimate < 0
    and Holm-adjusted two-sided normal p < 0.05 (family-wise 5% across the eight). Raw labels kept."""
    rows = []
    for pop, stage in HOLM_FAMILY:
        r = get(t, selected, "REF", "men", pop, stage, period=period)
        rows.append({"population": pop, "stage": stage, "present": r is not None,
                     **({k: r[k] for k in ("matches", "estimate", "lo", "hi", "se", "p_two_sided", "reading")}
                        if r is not None else {})})
    adj = holm_adjust([r.get("p_two_sided", float("nan")) for r in rows])
    for r, a in zip(rows, adj):
        r["p_holm"] = a
        r["raw_reading"] = r.pop("reading", None)
        r["worse_after_holm"] = bool(r["present"] and np.isfinite(r.get("estimate", np.nan)) and r["estimate"] < 0
                                     and a < HOLM_ALPHA)
    return {"what": "addition 2 section 3: men's holdout readings of SELECTED against REF; worse after Holm = estimate "
                    "< 0 and Holm-adjusted p < 0.05; p = 2 (1 - Phi(|estimate| / se))",
            "complete": all(r["present"] for r in rows), "readings": rows,
            "worse_after_holm": [r["population"] + " / " + r["stage"] for r in rows if r["worse_after_holm"]],
            "raw_worse": [r["population"] + " / " + r["stage"] for r in rows if r.get("raw_reading") == "worse"]}


def recommend(primary: dict | None, pooled: dict | None, holm: dict | None, selected: str) -> dict:
    """The pre-registered recommendation (guiding; the owner decides), applied mechanically, with addition 2 section 3's
    "no secondary is worse" (the Holm family). A missing primary of a selected arm other than REF refuses."""
    if selected == "REF":
        return {"recommend": "REF (no change)", "why": "REF was selected on dev"}
    if primary is None:
        raise SystemExit(f"the holdout primary ({selected} vs REF, men) is missing: refusing (never a fall back to REF)")

    def branch(p_key: str) -> dict:
        if primary["reading"] == "better":
            return {"recommend": selected, "why": "the holdout primary is better"}
        if primary["reading"] == "worse":
            return {"recommend": "REF", "why": "the holdout primary is worse"}
        cond = {"p_better_at_least_0.80": bool(np.isfinite(primary[p_key]) and primary[p_key] >= P_RECOMMEND),
                "pooled_2020_2026_better": bool(pooled is not None and pooled["reading"] == "better"),
                "no_secondary_worse_after_holm": bool(holm is not None and holm["complete"]
                                                      and not holm["worse_after_holm"])}
        if all(cond.values()):
            return {"recommend": selected, "why": "unresolved with P(better) >= 0.80, the pooled 2020-2026 primary "
                                                  "better, and none of the eight worse after Holm", "conditions": cond}
        return {"recommend": "unresolved", "p_better": primary[p_key], "conditions": cond,
                "why": "unresolved: report P(better)"}
    out = branch("p_better")
    alt = branch("p_better_t")
    out["t_cdf_check"] = {"recommend_with_t_cdf": alt["recommend"], "agrees": alt["recommend"] == out["recommend"]}
    return out


# ------------------------------------------------------------------------------------------------
# How far an arm moved its inputs in each population (no result read)

def stratum_inputs(arm: str, folder: Path, info: pd.DataFrame, test) -> pd.DataFrame:
    from src.eda.lower_level_evidence import candidate_arms as CA
    ref = CA.inputs_of(SF.REF_FRAME).set_index("match_id").loc[info.index]
    a = CA.inputs_of(folder / "model_frame.parquet").set_index("match_id").loc[info.index]
    names = [c[3:] for c in ref.columns if c.startswith("in_") and c in a.columns]
    moved = [n for n in names if not np.array_equal(ref[f"in_{n}"].to_numpy(float), a[f"in_{n}"].to_numpy(float),
                                                    equal_nan=True)]
    rows = []
    for tour, pop, mask in populations(info, test):
        rec = {"arm": arm, "tour": tour, "population": pop, "matches": int(mask.sum()), "inputs_moved": len(moved)}
        meds, shares = [], []
        for n in moved:
            x, y = ref[f"in_{n}"].to_numpy(float), a[f"in_{n}"].to_numpy(float)
            sd = np.nanstd(x)
            d = np.abs(x - y)[mask & np.isfinite(x) & np.isfinite(y)] / (sd if sd > 0 else 1.0)
            meds.append(float(np.median(d)) if len(d) else np.nan)
            shares.append(float((d > 0).mean()) if len(d) else np.nan)
        rec["median_abs_change_sd_mean_over_moved"] = float(np.nanmean(meds)) if meds else 0.0
        rec["share_of_values_changed"] = float(np.nanmean(shares)) if shares else 0.0
        rows.append(rec)
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------
# compare.py itself, per arm (dev)

def run_compare(arms: dict[str, Path], through: int) -> pd.DataFrame:
    rows = []
    for a, d in arms.items():
        out = d / "vs_reference_2026-10-08"
        s = CMP.compare(str(d), None, through, str(out))
        for r in s["primary"]:
            rows.append({"arm": a, "through": through, **{k: r.get(k) for k in ("population", "comparison", "matches",
                                                                                "estimate", "lo", "hi", "p_better",
                                                                                "reading")}})
        SF.log_line(RESULTS / "compare_runs.log", f"compare {a} through {through} -> {SF.rel(out)}")
    return pd.DataFrame(rows)


def check_against_compare(t: pd.DataFrame, cmp_rows: pd.DataFrame, period: str) -> dict:
    """This scorer's '<arm> vs REF' rows against compare.py's own primary rows (both stages and stage 1, three tours)."""
    names = {"both stages: candidate vs reference": "both stages", "stage 1: candidate vs reference": "stage 1"}
    worst, n = 0.0, 0
    for _, c in cmp_rows.iterrows():
        stage = names.get(c["comparison"])
        if stage is None:
            continue
        mine = get(t, c["arm"], "REF", c["population"], "all", stage, period=period)
        if mine is None:
            continue
        for k in ("estimate", "lo", "hi"):
            worst = max(worst, abs(float(mine[k]) - float(c[k])))
        n += 1
    return {"rows_compared": n, "largest_difference": worst, "equal": bool(n > 0 and worst < 1e-9)}


# ------------------------------------------------------------------------------------------------
# Addition 1: the rule of 8 October. None of it enters the selection, the Holm family or the recommendation.

def pair_rows(info: pd.DataFrame, models: dict, test, period: str, pairs, group: str) -> pd.DataFrame:
    """(first, second) pairs present in models: both stages overall and by season, stage 1 overall; three tours."""
    rows = []
    for first, second in pairs:
        if first not in models or second not in models:
            continue
        for tour, pop, mask in populations(info, test, strata=False):
            ids = info.index[mask]
            if len(ids) == 0:
                continue
            r = paired(info, ids, fc(models, second, "s2", info, ids), fc(models, first, "s2", info, ids))
            rows.append(row(period, group, first, second, "both stages", tour, pop, r))
            if pop == "all":
                r = paired(info, ids, fc(models, second, "s1", info, ids), fc(models, first, "s1", info, ids))
                rows.append(row(period, group, first, second, "stage 1", tour, pop, r))
    return pd.DataFrame(rows)


def flip(r: dict | None) -> dict | None:
    """The same reading named the other way round: '+ = the other model better'."""
    if r is None:
        return None
    swap = {"better": "worse", "worse": "better"}
    out = dict(r)
    out.update({"comparison": f"{r['second']} vs {r['first']}", "first": r["second"], "second": r["first"],
                "estimate": -r["estimate"], "lo": -r["hi"], "hi": -r["lo"],
                "p_better": 1 - r["p_better"] if np.isfinite(r["p_better"]) else r["p_better"],
                "p_better_t": 1 - r["p_better_t"] if np.isfinite(r["p_better_t"]) else r["p_better_t"],
                "reading": swap.get(r["reading"], r["reading"])})
    return out


def rule_reading(as_is: dict, through_system: dict) -> dict:
    """Addition 1's interpretation (guiding; the owner decides), for one data set, period and tour. Each reading is
    oriented '+ = adding the data is better'. Protective: adding as-is reads worse than leaving it out ('worse', or
    'unresolved' with P(better) <= 0.20). Holding the model back: adding reads better, as-is or through the system.
    Otherwise unresolved (the rule costs nothing to keep). Both at once is reported as mixed."""
    a = {k: v for k, v in as_is.items() if v is not None}
    s = {k: v for k, v in through_system.items() if v is not None}
    protective = [k for k, v in a.items() if v["reading"] == "worse"
                  or (v["reading"] == "unresolved" and np.isfinite(v["p_better"]) and v["p_better"] <= P_PROTECTIVE)]
    holding = [k for k, v in {**a, **s}.items() if v["reading"] == "better"]
    if not a and not s:
        label = "not scored"
    elif protective and holding:
        label = "mixed: protective as-is, and better " + ("through the system" if set(holding) <= set(s) else "as-is")
    elif holding:
        label = "the rule holds the model back"
    elif protective:
        label = "the rule is protective"
    else:
        label = "unresolved: the default stays (new data is a candidate)"
    cells = {k: {x: v[x] for x in ("comparison", "matches", "estimate", "lo", "hi", "p_better", "reading")}
             for k, v in {**a, **s}.items()}
    return {"reading": label, "protective_by": protective, "holding_back_by": holding, "readings": cells}


def addition1_interpretation(t: pd.DataFrame, periods) -> list[dict]:
    """Per data set, period and tour: the 2025-26 ITF box scores (as-is in REF against REF_noITF, in SYS_ITFASIS against
    SYS, in SYS_BOTH_ITFASIS against SYS_BOTH), C0_now's additions (NEW_ASIS against REF as-is; NEW_SYS_BOTH against
    SYS_BOTH through the system) and, when built, C0_pre's (NEW_ASIS_PRE against REF as-is)."""
    out = []
    for period in periods:
        for tour in TOURS:
            g = lambda f, s: get(t, f, s, tour, period=period)    # noqa: E731
            itf = rule_reading({"REF (ITF as-is) vs REF_noITF": flip(g("REF_noITF", "REF")),
                                "SYS_ITFASIS vs SYS": flip(g("SYS", "SYS_ITFASIS")),
                                "SYS_BOTH_ITFASIS vs SYS_BOTH": flip(g("SYS_BOTH", "SYS_BOTH_ITFASIS"))}, {})
            new = rule_reading({"NEW_ASIS vs REF": g("NEW_ASIS", "REF")},
                               {"NEW_SYS_BOTH vs SYS_BOTH": g("NEW_SYS_BOTH", "SYS_BOTH")})
            pre = rule_reading({"NEW_ASIS_PRE vs REF": g("NEW_ASIS_PRE", "REF")}, {})
            out.append({"data_set": "the 2025-26 ITF box scores", "period": period, "tour": tour, **itf})
            out.append({"data_set": "C0_now's additions", "period": period, "tour": tour, **new})
            out.append({"data_set": "C0_pre's additions (to 2024-12-29; optional arm)", "period": period, "tour": tour,
                        **pre})
    return out


def dev_differs_before_2025(arm: str) -> bool:
    """Addition 2 section 2: an ITFASIS arm is read on dev only where its inputs differ from its comparator's before
    2025, i.e. when the fit queue did not copy its dev fits (results/checks/<ARM>_reuse.json)."""
    rec = SF.CHECKS / f"{arm}_reuse.json"
    if not rec.exists():
        return True
    return not json.loads(rec.read_text(encoding="utf-8")).get("identical_to_2024", False)


def addition1(main_info: pd.DataFrame, main_models: dict, mode: str, speed_rule: str = "zero",
              allow_missing=()) -> tuple[pd.DataFrame, dict]:
    """Addition 1's pairs and interpretation for one mode and speed rule. The candidate-Stage-0 arms are loaded apart,
    with SYS_BOTH and the reference, on the matches all their frames hold."""
    if mode == "dev":
        main_pairs = [p for p in ADD1_MAIN if p[1] not in ITFASIS or dev_differs_before_2025(p[1])]
        parts = [pair_rows(main_info, main_models, DEV_TEST, "dev 2020-2024", main_pairs, "addition 1")]
        through, fits, test, periods = DEV_LAST, DEV_FITS, DEV_TEST, [("dev 2020-2024", DEV_TEST)]
    else:
        parts = [pair_rows(main_info, main_models, HOLDOUT, H, ADD1_MAIN, "addition 1")]
        through, fits, test, periods = 2026, ALL_FITS, POOLED, [(H, HOLDOUT), (PD, POOLED)]
    group, rec = gather(("SYS_BOTH",) + NEW, fits, required=(), allow_missing=allow_missing)
    new_info = {}
    if any(a in group for a in NEW):
        info2, models2 = load_models(group, through, fits, test, speed_rule=speed_rule, strict_price=False)
        for name, seasons in periods:
            parts.append(pair_rows(info2, models2, seasons, name, ADD1_NEW, "addition 1"))
        new_info = {k: {x: m[x] for x in ("folder", "price_differs_on", "matches_in_frame", "matches_scored_pool")}
                    for k, m in models2.items() if not k.startswith("_")}
    parts = [p for p in parts if len(p)]
    t = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    res = {"what": "addition 1 (preregistration_addition_1.md): the rule of 8 October; none of it enters the selection, "
                   "the Holm family or the recommendation", "mode": mode, "speed_rule": speed_rule,
           "candidate_stage0_group": new_info, "arms_record": rec,
           "pairs_scored": sorted(set(t["comparison"])) if len(t) else [],
           "interpretation": addition1_interpretation(t, [p for p, _ in periods]) if len(t) else [],
           "generated_at": SF.now()}
    return t, res


# ------------------------------------------------------------------------------------------------
# Modes

def dev(run_cmp: bool = False, without_addition: bool = False, allow_missing=()) -> dict:
    pre = verify_prereg()
    cp1 = require_cp1(without_addition)
    if UNLOCK.exists():
        raise SystemExit("the holdout unlock exists: the dev readings and the selection were written down before it; "
                         "dev is not re-run")
    ref_problems = fit_problems(SF.REF_DIR, DEV_FITS)
    if ref_problems:
        raise SystemExit(f"REF: {ref_problems[:4]}")
    names = DEV_ARMS + ("REF_noITF",) + ITFASIS                 # REF_noITF, ITFASIS: addition 1's dev pairs only
    usable, rec = gather(names, DEV_FITS, required=REQUIRED_DEV, allow_missing=allow_missing)
    gather(("SYS_BOTH",) + NEW, DEV_FITS, required=(), allow_missing=allow_missing)   # refuses before anything is read
    info, models = load_models(usable, DEV_LAST, DEV_FITS, DEV_TEST)
    if models["_speed"]["gap_matches"]:
        raise SystemExit("a dev season lacks the stage-2 speed value: not expected (addition 2 names 2026 only)")
    period = "dev 2020-2024"
    t = readings(info, models, DEV_TEST, period, [a for a in usable if a in DEV_ARMS], SYS_VS,
                 extra_pairs=[("SYS_S2", "SYS")])
    out = RESULTS / "dev"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "pairs.csv", index=False)
    dose_curve(t, period).to_csv(out / "dose_curve.csv", index=False)
    a1, a1res = addition1(info, models, "dev", allow_missing=allow_missing)
    a1.to_csv(out / "addition1_pairs.csv", index=False)
    SF.write_json(out / "addition1.json", a1res)
    sel = selection_from(t, period)
    sel.update({"preregistration": pre, "checkpoint_1": cp1, "period": period, "arms_scored": list(usable),
                "arms_record": rec, "sides_parquet_sha256": sides_sha256(), "generated_at": SF.now(),
                "rules": "registered (pre-registration 'Dev'), kept for the record; the selection in force is "
                         "system_decide.py's results/selection.json (addition 4)"})
    SF.write_json(SELECTION_REGISTERED, sel)
    si = [stratum_inputs(a, usable[a], info, DEV_TEST) for a in ("SYS", sel.get("selected"))
          if a is not None and a in usable]
    if si:
        pd.concat(si, ignore_index=True).drop_duplicates().to_csv(out / "stratum_inputs.csv", index=False)
    res = {"period": period, "results_read_through": DEV_LAST, "scored_seasons": [DEV_TEST[0], DEV_TEST[-1]],
           "unit": "mLL per match; positive = the first-named model better; P(better) = Phi(estimate/se)",
           "preregistration": pre, "checkpoint_1": cp1, "without_addition": without_addition,
           "arms_scored": list(usable), "arms_record": rec, "speed": models["_speed"],
           "models": {k: {"folder": m["folder"], "speed_column": m["speed"]} for k, m in models.items()
                      if not k.startswith("_")},
           "coefficients_2024": {k: {"stage1": m["s1"][DEV_LAST], "both": m["s2"][DEV_LAST]} for k, m in models.items()
                                 if not k.startswith("_")},
           "selection_registered_rules": {k: sel[k] for k in ("status", "selected", "step1_arm", "qualifying")},
           "selection_registered_sha256": SF.sha256(SELECTION_REGISTERED),
           "sides_parquet_sha256": sel["sides_parquet_sha256"],
           "addition1": {"pairs_scored": a1res["pairs_scored"], "file": "results/dev/addition1.json"},
           "generated_at": SF.now()}
    if run_cmp:
        c = run_compare({a: d for a, d in usable.items() if a in DEV_ARMS}, DEV_LAST)
        c.to_csv(out / "compare_py_primary.csv", index=False)
        res["compare_py_check"] = check_against_compare(t, c, period)
    SF.write_json(out / "results.json", res)
    show(t, period)
    print("registered rules' selection (for the record):",
          json.dumps({k: sel[k] for k in ("status", "selected", "step1_arm", "qualifying", "missing_challengers",
                                          "t_cdf_check")}, default=str))
    print("the selection in force is written by system_decide.py --dev (results/selection.json; the unlock must hold "
          "its SHA-256)")
    return res


def holdout_readings(selected: str, usable: dict, rule: str, allow_missing=()) -> tuple[pd.DataFrame, dict]:
    """Every holdout reading under one speed rule ("zero": the primary; "drop909": the sensitivity)."""
    info, models = load_models(usable, 2026, ALL_FITS, POOLED, speed_rule=rule)
    t_h = readings(info, models, HOLDOUT, H, [a for a in usable if a in ARMS], SYS_VS,
                   extra_pairs=[("SYS_S2", "SYS"), (selected, "REF_noITF"), ("REF_noITF", "REF")])
    pooled_arms = [a for a in DOSE_PREREG + (selected,) if a in usable and a != "REF"]
    t_p = readings(info, models, POOLED, PD, pooled_arms, (), strata=False, closes=False)
    t = pd.concat([t_h, t_p], ignore_index=True)
    primary = get(t, selected, "REF", "men", period=H) if selected != "REF" else None
    pooled = get(t, selected, "REF", "men", period=PD) if selected != "REF" else None
    if selected != "REF" and (primary is None or pooled is None):
        raise SystemExit(f"the holdout primary ({selected} vs REF) could not be read: refusing (never a fall back)")
    holm = holm_family(t, selected) if selected != "REF" else None
    decomposition = {
        "meaning": {f"{selected} vs REF_noITF": "everything the system changes except the ITF box-score exclusion, "
                                                "Elo weights included (the lead's relabelling of 10 Oct)",
                    "REF_noITF vs REF": "the ITF and ITFQ box scores as the reference has them (as-is) against left "
                                        "out"},
        f"{selected} vs REF_noITF": {tr: get(t, selected, "REF_noITF", tr, period=H) for tr in TOURS},
        "REF_noITF vs REF": {tr: get(t, "REF_noITF", "REF", tr, period=H) for tr in TOURS}}
    a1, a1res = addition1(info, models, "holdout", speed_rule=rule, allow_missing=allow_missing)
    res = {"speed_rule": rule, "speed": models["_speed"], "primary": primary, "pooled_primary": pooled,
           "decomposition": decomposition, "holm": holm, "recommendation": recommend(primary, pooled, holm, selected),
           "results_and_elo": {f"RES_ONLY vs REF, {tr}": get(t, "RES_ONLY", "REF", tr, period=H) for tr in TOURS}
           | {f"SYS vs RES_ONLY, {tr}": get(t, "SYS", "RES_ONLY", tr, period=H) for tr in TOURS},
           "addition1": a1res}
    return pd.concat([t, a1], ignore_index=True) if len(a1) else t, res


def holdout(allow_missing=(), without_addition: bool = False) -> dict:
    pre = verify_prereg()
    lock = verify_unlock()                                       # raises HoldoutLocked before any later season is read
    out = RESULTS / "holdout"
    if (out / "readings.json").exists():
        raise SystemExit("the holdout was opened already (results/holdout/readings.json exists): it is opened once")
    cp1 = require_cp1(without_addition)
    sel = json.loads(SELECTION.read_text(encoding="utf-8")) if SELECTION.exists() else {}
    if sel.get("status") != "final" or not sel.get("selected"):
        raise SystemExit("the dev selection is not written down as final (results/selection.json); refusing")
    if sel.get("decision_layer") != DECISION_LAYER:
        raise SystemExit("results/selection.json is not the decision layer's (addition 4): run system_decide.py --dev "
                         "after the dev readings; refusing")
    sel_sha = SF.sha256(SELECTION)
    if sel_sha not in set(lock["held"]):
        raise HoldoutLocked(f"the holdout is locked: the unlock does not hold selection.json's SHA-256 ({sel_sha}); the "
                            f"selection must be the one written down before the unlock")
    if sel.get("sides_parquet_sha256") != sides_sha256():
        raise SystemExit("sides.parquet (the strata) changed since the dev readings; refusing")
    selected = sel["selected"]
    ref_problems = fit_problems(SF.REF_DIR, ALL_FITS)
    if ref_problems:
        raise SystemExit(f"REF: {ref_problems[:4]}")
    required = REQUIRED_HOLDOUT + ((selected,) if selected != "REF" else ())
    usable, rec = gather(ARMS + ITFASIS, ALL_FITS, required=required, allow_missing=allow_missing)
    gather(("SYS_BOTH",) + NEW, ALL_FITS, required=(), allow_missing=allow_missing)   # refuses before anything is read
    if selected != "REF" and selected not in usable:
        raise SystemExit(f"the selected arm {selected} cannot be scored: refusing (never a fall back to REF)")
    t, res = holdout_readings(selected, usable, "zero", allow_missing)
    t_s, res_s = holdout_readings(selected, usable, "drop909", allow_missing)
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "pairs.csv", index=False)
    t_s.to_csv(out / "pairs_drop909.csv", index=False)
    dose_curve(t, H).to_csv(out / "dose_curve.csv", index=False)
    dose_curve(t_s, H).to_csv(out / "dose_curve_drop909.csv", index=False)
    readings_json = {"lock": {k: v for k, v in lock.items() if k != "held"}, "preregistration": pre,
                     "checkpoint_1": cp1, "selected_on_dev": selected, "selection_sha256": sel_sha,
                     "arms_scored": list(usable), "arms_record": rec, "results_read_through": 2026,
                     "unit": "mLL per match; positive = the first-named model better; P(better) = Phi(estimate/se)",
                     "primary_speed_rule": "zero: no stage-2 nudge without a speed memory (addition 2 section 1)",
                     **res, "sensitivity_drop909": res_s,
                     "compare_py_cross_check": "not applicable: compare.py has no rule for addition 2's speed gap",
                     "generated_at": SF.now()}
    SF.write_json(out / "readings.json", readings_json)     # written last: its presence means the holdout was opened
    show(t, H)
    print("recommendation:", json.dumps(res["recommendation"], default=str))
    print("sensitivity (909 dropped):", json.dumps(res_s["recommendation"], default=str))
    return readings_json


# ------------------------------------------------------------------------------------------------
# The harness check: the first run's FP and R_S2 through this scorer

PUBLISHED = {("FP", "both tours"): (0.024, -0.047, 0.096), ("FP", "men"): (0.083, 0.002, 0.164),
             ("FP", "women"): (-0.040, -0.154, 0.073)}


def harness() -> dict:
    cand = SF.LLE / "candidates"
    arms = {"FP": cand / "FP", "R_S2": cand / "R_S2"}
    for name, d in list(arms.items()) + [("REF", SF.REF_DIR)]:
        problems = fit_problems(d, DEV_FITS)
        if problems:
            raise SystemExit(f"{name}: {problems[:4]}")
    info, models = load_models(arms, DEV_LAST, DEV_FITS, DEV_TEST)
    period = "dev 2020-2024"
    t = readings(info, models, DEV_TEST, period, ["FP", "R_S2"], (), extra_pairs=[("FP", "R_S2")])
    out = RESULTS / "harness"
    out.mkdir(parents=True, exist_ok=True)
    t.to_csv(out / "pairs.csv", index=False)
    res = {"what": "the first run's FP and R_S2 (candidates/, read only) through system_pairs.py, against compare.py's "
                   "FP scores.csv, the first run's pairs.csv (candidate_pairs.py) and the published readings",
           "generated_at": SF.now()}
    cs = pd.read_csv(cand / "FP" / "vs_reference_2026-10-08" / "scores.csv")
    cs = cs[cs["group"] == "primary"].assign(arm="FP")
    res["vs_compare_py"] = check_against_compare(t, cs, period)
    fr = pd.read_csv(cand / "results" / "pairs.csv")
    worst, n, worst_p = 0.0, 0, 0.0
    for _, r in fr.iterrows():
        comp = str(r["comparison"])
        if comp.endswith("vs its calibrated close"):
            first, second = comp.split(" vs ")[0], "its calibrated close"
        else:
            first, second = comp.split(" vs ")
        first = "REF" if first == "reference" else first
        second = "REF" if second == "reference" else second
        pop = str(r["population"])
        tour, popn = (pop, "all") if pop in TOURS else ("both tours", pop)
        stage = "stage 1" if r["stage"] == "stage 1" else "both stages"
        mine = get(t, first, second, tour, popn, stage, period=period)
        if mine is None:
            continue
        n += 1
        for k in ("estimate", "lo", "hi", "se"):
            worst = max(worst, abs(float(mine[k]) - float(r[k])))
        if np.isfinite(r["p_better"]):
            worst_p = max(worst_p, abs(float(mine["p_better_t"]) - float(r["p_better"])))
    res["vs_first_run_pairs"] = {"rows_compared": n, "rows_in_file": int(len(fr)), "largest_difference": worst,
                                 "largest_difference_p_better_t": worst_p, "equal": bool(n > 0 and worst < 1e-9)}
    pub = {}
    for (arm, tour), (e, lo, hi) in PUBLISHED.items():
        mine = get(t, arm, "REF", tour, period=period)
        got = (round(mine["estimate"], 3), round(mine["lo"], 3), round(mine["hi"], 3))
        pub[f"{arm} vs REF, {tour}"] = {"published": [e, lo, hi], "this_scorer": list(got),
                                        "exact": [mine["estimate"], mine["lo"], mine["hi"]],
                                        "p_better": mine["p_better"], "p_better_t": mine["p_better_t"],
                                        "reading": mine["reading"], "equal": got == (e, lo, hi)}
    res["vs_published"] = pub
    res["pass"] = bool(res["vs_compare_py"]["equal"] and res["vs_first_run_pairs"]["equal"]
                       and all(v["equal"] for v in pub.values()))
    SF.write_json(out / "harness.json", res)
    print(json.dumps({k: v for k, v in res.items() if k != "what"}, indent=1, default=str))
    return res


def show(t: pd.DataFrame, period: str) -> None:
    s = t[(t["period"] == period) & (t["population"] == "all") & (t["stage"] == "both stages")]
    with pd.option_context("display.width", 230, "display.max_rows", 400):
        print(s[["comparison", "tour", "matches", "estimate", "lo", "hi", "p_better", "reading"]].round(3)
              .to_string(index=False))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dev", action="store_true")
    g.add_argument("--holdout", action="store_true")
    g.add_argument("--harness", action="store_true")
    ap.add_argument("--run-compare", action="store_true")
    ap.add_argument("--without-addition", action="store_true", help="the lead's word only: score without the "
                                                                     "checkpoint-1 addition")
    ap.add_argument("--allow-missing", default="", help="the lead's word only: pre-registered arms waived, comma list "
                                                        "(recorded in the outputs)")
    a = ap.parse_args()
    allow = tuple(x for x in a.allow_missing.split(",") if x)
    if a.harness:
        verify_prereg()
        return 0 if harness()["pass"] else 1
    if a.dev:
        dev(a.run_compare, a.without_addition, allow)
        return 0
    holdout(allow, a.without_addition)
    return 0


if __name__ == "__main__":
    sys.exit(main())
