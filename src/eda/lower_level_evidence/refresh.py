"""Re-run the lower-level evidence review on a Stage 0 and compare it with the first run: the renewable part of the study.

The review (docs/studies/lower_level_evidence/README.md) was first run on 9 Oct 2026 on the frozen reference of 8 Oct
(label reference_2026-10-08). When new lower-level data lands (the dossier's re-review triggers), a session builds a
candidate Stage 0 that carries it (run_chain.py --setup --candidate, lane 0) and runs this script on it with its own
label and its own timeline:

    ./python.sh src/eda/lower_level_evidence/refresh.py --label <name> \
        --stage0-dir <candidate>/data/studies/predictability_diagnostic \
        --timing <candidate>/data/studies/match_timing/timing.parquet

The scripts it calls keep their own holdout guards (no outcome of 2025-2026 is read); this script reads their outputs.

Steps (--steps, comma-separated; outputs under data/studies/lower_level_evidence/):
    incoming      incoming.py     -> incoming/<label>/      what is held at each level: counts and coverage only (~25 s)
    composition   composition.py  -> composition/<label>/   how much of each input's evidence is lower-level (~2 min;
                                                             its part 5, the scores, only with --scores)
    translation   translation.py  -> translation/<label>/   offsets, exchange rates, tier priors (~8 min with 30 draws).
                                                             With ITF box scores of 2018-2024 in the Stage 0, move its
                                                             windows (--translation-args "--fit-window 2018-2021 --tune
                                                             2019-2021 --validate 2022-2024"): a statistic-level review
                                                             only. Offsets fitted on 2018-2021 must not enter a model
                                                             candidate scored on 2020-2024 (fit walk-forward instead)
    snapshot      the three runs' headline numbers -> snapshots/<label>.json
    diff          the snapshot against --base (default: the first run) -> snapshots/<label>_vs_<base>.md and .json

Safety: --label is required; the first run's label is refused for any Stage 0 but the frozen reference's; a step whose
output folder exists is refused without --force; a candidate Stage 0 must come with its own --timing.

The diff's flags (it reads the composition and translation numbers; the incoming numbers are stored for reference):
    MISSING          a section the base run has is absent from this run: its outputs were not found (never read as
                     "nothing moved")
    UNEVEN DOSE      per tour and memory, the season-by-season change of the lower-level share of box-score evidence
                     spreads over >= 3 points (some seasons move more than others): the shape the input check calls
                     "uneven" (the input-data audit's finding #6). It lists the seasons that moved by >= 3 points
    FAMILY DOSE      an input family's lower-level share moves by >= 3 points in a tour-era
    EXPOSURE         the share of model matches whose less-exposed side has under 10 main-tour results in 365 days moves
                     by >= 2 points
    NEW LEVEL        a level reaches translation.py's threshold of box-score rows (200) in the seasons it reads (to
                     2024), so its own offset and weight are estimated
    WINDOWS CHANGED  translation.py's fit, tune or validation window differs from the base run's; DRIFT is then not read
    DRIFT            an offset or a weight leaves the base run's bootstrap 5-95% range (only the statistics that have
                     bootstrap draws: 8 of 12 in the first run)

--scenario p7 writes the flags of a construction, not of new data: the base run's own preview of the ITF box scores of
2018-2024 (composition.py's itf_p7_scenario.csv, column "p7") fed in as if it were a candidate.
"""
from __future__ import annotations

import argparse
import copy
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as C  # noqa: E402

BASE_LABEL = "reference_2026-10-08"
SNAP = C.OUT / "snapshots"
STEPS = ("incoming", "composition", "translation", "snapshot", "diff")
HEAVY = ("incoming", "composition", "translation")
SCRIPTS = {s: ROOT / "src" / "eda" / "lower_level_evidence" / f"{s}.py" for s in HEAVY}

UNEVEN_POINTS = 0.03      # in share units: 3 points of the evidence
FAMILY_POINTS = 0.03
EXPOSURE_POINTS = 0.02
BOOT_RANGE = (0.05, 0.95)


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# ------------------------------------------------------------------------------------------------
# Where each run's outputs live

def incoming_dir(label: str) -> Path:
    """The first run wrote incoming/ itself; later runs write incoming/<label>/."""
    d = C.OUT / "incoming" / label
    if not d.exists() and label == BASE_LABEL:
        return C.OUT / "incoming"
    return d


def composition_dir(label: str) -> Path:
    return C.OUT / "composition" / label


def translation_dir(label: str) -> Path:
    return C.OUT / "translation" / label


def output_dirs(label: str) -> dict[str, Path]:
    """Where each heavy step would write for this label."""
    return {"incoming": C.OUT / "incoming" / label, "composition": composition_dir(label),
            "translation": translation_dir(label)}


def is_reference(stage0_dir: Path) -> bool:
    return Path(stage0_dir).resolve() == Path(C.STAGE0_DIR).resolve()


def validate(label: str, steps: list[str], stage0_dir: Path, timing: Path | None, force: bool) -> Path | None:
    """The run's arguments checked before anything is written; returns the timeline to use."""
    unknown = set(steps) - set(STEPS)
    if unknown:
        raise SystemExit(f"unknown steps {sorted(unknown)}; choose from {STEPS}")
    heavy = [s for s in steps if s in HEAVY]
    if heavy and label == BASE_LABEL and not is_reference(stage0_dir):
        raise SystemExit(f"--label {BASE_LABEL} is the first run's: give a candidate Stage 0 its own label")
    if heavy and not force:
        taken = [f"{s}: {d}" for s, d in output_dirs(label).items() if s in heavy and d.exists()]
        if taken:
            raise SystemExit("these outputs exist and would be overwritten (use a new --label, or --force):\n  "
                             + "\n  ".join(taken))
    if timing is None:
        if heavy and not is_reference(stage0_dir):
            raise SystemExit("a candidate Stage 0 needs its own --timing (the timeline built with it)")
        timing = C.TIMING
    return timing


# ------------------------------------------------------------------------------------------------
# Running the three scripts

def step_commands(steps: list[str], stage0_dir: Path, timing: Path | None, frame: Path, label: str, scores: bool,
                  model: str, boot: int, translation_args: str = "") -> list[tuple[str, list[str]]]:
    """(step, argv) for the scripts among the steps, in order; snapshot and diff run in-process."""
    py = sys.executable
    out: list[tuple[str, list[str]]] = []
    if "incoming" in steps:
        cmd = [py, str(SCRIPTS["incoming"]), "--stage0-dir", str(stage0_dir), "--out", str(output_dirs(label)["incoming"]),
               "--skip-progress"]
        if timing:
            cmd += ["--timing", str(timing)]
        out.append(("incoming", cmd))
    if "composition" in steps:
        cmd = [py, str(SCRIPTS["composition"]), "--stage0-dir", str(stage0_dir), "--frame", str(frame),
               "--label", label, "--timing", str(timing) if timing else ""]
        cmd += ["--model", model] if scores else ["--no-scores"]
        out.append(("composition", cmd))
    if "translation" in steps:
        cmd = [py, str(SCRIPTS["translation"]), "--stage0-dir", str(stage0_dir), "--label", label, "--boot", str(boot)]
        if timing:
            cmd += ["--timing", str(timing)]
        cmd += shlex.split(translation_args)
        out.append(("translation", cmd))
    return out


def run(cmds: list[tuple[str, list[str]]]) -> dict:
    record = {}
    for name, cmd in cmds:
        t0 = time.time()
        print(f"--> {name}: {' '.join(cmd[1:])}", flush=True)
        done = subprocess.run(cmd, cwd=ROOT)
        record[name] = {"exit": done.returncode, "seconds": round(time.time() - t0, 1)}
        if done.returncode != 0:
            raise SystemExit(f"{name} failed (exit {done.returncode}); later steps not run")
    return record


# ------------------------------------------------------------------------------------------------
# The snapshot: the headline numbers of one run

def _read_csv(path: Path) -> pd.DataFrame | None:
    return pd.read_csv(path) if path.exists() else None


def _read_json(path: Path) -> dict | None:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def composition_numbers(d: Path) -> dict:
    out: dict = {}
    dose = _read_csv(d / "inputs_dose.csv")
    if dose is not None:
        g = dose[dose["grouping"] == "tour x era"]
        out["family_dose"] = {f"{r.input_family}|{r.tour}|{r.era}": float(r.share_lower) for r in g.itertuples()}
    scen = _read_csv(d / "itf_p7_scenario.csv")
    if scen is not None:
        out["box_share_by_season"] = {f"{r.tour}|{r.window}|{int(r.season)}": float(r.box_lower_share_today)
                                      for r in scen.itertuples()}
    summ = _read_json(d / "summary.json")
    if summ is not None and "exposure" in summ:
        out["exposure_under10"] = {k: float(v["less_exposed_under_10_main_365d"]) for k, v in summ["exposure"].items()
                                   if isinstance(v, dict) and "less_exposed_under_10_main_365d" in v}
    return out


def credibility_numbers(params: pd.DataFrame) -> dict:
    """Offsets and weights of the translated-and-discounted arm, with the bootstrap's 5-95% range where drawn."""
    levels = sorted(c[len("delta_"):] for c in params.columns if c.startswith("delta_"))
    main = params[params["arm"] == "translated_discounted"]
    boot = params[params["arm"].astype(str).str.startswith("boot")]
    out = {}
    for r in main.itertuples():
        for lv in levels:
            key = f"{r.tour}|{r.stat}|{lv}"
            rec = {"delta": float(getattr(r, f"delta_{lv}")), "w": float(getattr(r, f"w_{lv}"))}
            b = boot[(boot["tour"] == r.tour) & (boot["stat"] == r.stat)]
            if len(b) >= 10:
                for p in ("delta", "w"):
                    lo, hi = np.quantile(b[f"{p}_{lv}"].to_numpy(float), BOOT_RANGE)
                    rec[f"{p}_lo"], rec[f"{p}_hi"] = float(lo), float(hi)
            out[key] = rec
    return out


def translation_numbers(d: Path) -> dict:
    out: dict = {}
    summ = _read_json(d / "summary.json")
    if summ is not None:
        out["levels_with_box_scores"] = list(summ.get("levels_with_box_scores", []))
        run_ = summ.get("run", {})
        out["windows"] = {k: run_.get(k) for k in ("fit_window", "tune", "validate")}
    params = _read_csv(d / "credibility_params.csv")
    if params is not None:
        out["credibility"] = credibility_numbers(params)
    eff = _read_csv(d / "level_effects.csv")
    if eff is not None:
        e = eff[eff["variant"] == "level"]
        out["level_effects_points"] = {f"{r.tour}|{r.stat}|{r.window}|{r.cell}": float(r.delta_points)
                                       for r in e.itertuples()}
    arms = _read_csv(d / "ios_arms.csv")
    if arms is not None:
        a = arms[(arms["period"] == "validate") & (arms["group"] == "all")]
        out["ios_arms_validate_milli"] = {f"{r.tour}|{r.stat}|{r.arm}": float(r.gain_vs_ios_milli)
                                          for r in a.itertuples()}
    return out


def incoming_numbers(d: Path) -> dict:
    out: dict = {}
    dose = _read_csv(d / "dose.csv")
    if dose is not None and "mean_p7_share_365" in dose.columns:
        out["p7_share_by_season"] = {f"{r.T}|{int(r.season)}": float(r.mean_p7_share_365) for r in dose.itertuples()}
    cen = _read_csv(d / "census.csv")
    if cen is not None:
        out["box_coverage"] = {f"{r.T}|{r.bucket}|{int(r.year)}": (int(r.with_box), int(r.matches))
                               for r in cen.itertuples()}
    return out


def snapshot(label: str) -> dict:
    return {"label": label,
            "generated_at": utc_now(),
            "composition": composition_numbers(composition_dir(label)),
            "translation": translation_numbers(translation_dir(label)),
            "incoming": incoming_numbers(incoming_dir(label))}


def scenario_p7(base: dict, label: str = BASE_LABEL) -> dict:
    """A construction, not new data: the base snapshot with its box-score shares replaced by the base run's own preview
    of the ITF box scores of 2018-2024 (composition.py's itf_p7_scenario.csv, column box_lower_share_p7)."""
    scen = pd.read_csv(composition_dir(label) / "itf_p7_scenario.csv")
    cand = copy.deepcopy(base)
    cand["label"] = "scenario_p7"
    cand["generated_at"] = utc_now()
    cand["composition"]["box_share_by_season"] = {f"{r.tour}|{r.window}|{int(r.season)}": float(r.box_lower_share_p7)
                                                  for r in scen.itertuples()}
    return cand


# ------------------------------------------------------------------------------------------------
# The diff: flags and the changes behind them

SECTIONS = {"composition": ("family_dose", "box_share_by_season", "exposure_under10"),
            "translation": ("levels_with_box_scores", "credibility")}


def missing(base: dict, cand: dict) -> list[dict]:
    """A section the base run has and this run lacks: its outputs were not found, so nothing about it can be read."""
    out = []
    for part, keys in SECTIONS.items():
        for k in keys:
            if base.get(part, {}).get(k) and not cand.get(part, {}).get(k):
                out.append({"flag": "MISSING", "where": f"{part}.{k}",
                            "note": "absent from this run: rerun its step or check its output folder"})
    return out


def _changes(base: dict, cand: dict) -> pd.Series:
    keys = sorted(set(base) & set(cand))
    return pd.Series({k: cand[k] - base[k] for k in keys}, dtype=float)


def uneven_dose(base: dict, cand: dict, points: float = UNEVEN_POINTS) -> list[dict]:
    """Per tour and memory: the season-by-season change of the box-score lower-level share spreads over `points`."""
    ch = _changes(base.get("box_share_by_season", {}), cand.get("box_share_by_season", {}))
    flags = []
    if ch.empty:
        return flags
    parts = ch.index.to_series().str.rsplit("|", n=1, expand=True)
    for grp, idx in ch.groupby(parts[0]).groups.items():
        c = ch.loc[idx]
        if c.abs().max() >= points and (c.max() - c.min()) >= points:
            moved = sorted(int(k.rsplit("|", 1)[1]) for k, v in c.items() if abs(v) >= points)
            still = sorted(int(k.rsplit("|", 1)[1]) for k, v in c.items() if abs(v) < points)
            flags.append({"flag": "UNEVEN DOSE", "where": grp, "moved_seasons": moved, "unmoved_seasons": still,
                          "largest_change_points": round(100 * float(c.loc[c.abs().idxmax()]), 1)})
    return flags


def threshold_flags(name: str, base: dict, cand: dict, points: float) -> list[dict]:
    ch = _changes(base, cand)
    return [{"flag": name, "where": k, "change_points": round(100 * float(v), 1),
             "base": round(100 * float(base[k]), 1), "new": round(100 * float(cand[k]), 1)}
            for k, v in ch.items() if abs(v) >= points]


def new_levels(base: dict, cand: dict) -> list[dict]:
    b = set(base.get("levels_with_box_scores", []))
    return [{"flag": "NEW LEVEL", "where": lv, "note": "200+ box-score rows in the seasons translation.py reads: its own "
             "offset and weight are estimated (statistic level only; a model candidate fits them walk-forward)"}
            for lv in sorted(set(cand.get("levels_with_box_scores", [])) - b)]


def windows_changed(base: dict, cand: dict) -> list[dict]:
    b, c = base.get("windows"), cand.get("windows")
    if b and c and b != c:
        return [{"flag": "WINDOWS CHANGED", "where": "translation.py", "base": b, "new": c,
                 "note": "the offsets and weights are refitted on other seasons: DRIFT is not read"}]
    return []


def drift(base: dict, cand: dict) -> list[dict]:
    flags = []
    for k, b in base.get("credibility", {}).items():
        c = cand.get("credibility", {}).get(k)
        if c is None:
            continue
        for p in ("delta", "w"):
            lo, hi = b.get(f"{p}_lo"), b.get(f"{p}_hi")
            if lo is None or hi is None or not np.isfinite(c[p]):
                continue
            if not lo <= c[p] <= hi:
                flags.append({"flag": "DRIFT", "where": f"{k} {p}", "base": round(b[p], 4), "new": round(c[p], 4),
                              "base_range": [round(lo, 4), round(hi, 4)]})
    return flags


def diff(base: dict, cand: dict) -> list[dict]:
    bc, cc = base.get("composition", {}), cand.get("composition", {})
    bt, ct = base.get("translation", {}), cand.get("translation", {})
    moved = windows_changed(bt, ct)
    return (missing(base, cand)
            + uneven_dose(bc, cc)
            + threshold_flags("FAMILY DOSE", bc.get("family_dose", {}), cc.get("family_dose", {}), FAMILY_POINTS)
            + threshold_flags("EXPOSURE", bc.get("exposure_under10", {}), cc.get("exposure_under10", {}),
                              EXPOSURE_POINTS)
            + new_levels(bt, ct)
            + moved
            + ([] if moved else drift(bt, ct)))


ORDER = ("MISSING", "UNEVEN DOSE", "NEW LEVEL", "WINDOWS CHANGED", "DRIFT", "FAMILY DOSE", "EXPOSURE")


def markdown(base: dict, cand: dict, flags: list[dict], record: dict | None = None, note: str = "") -> str:
    lines = [f"# Lower-level evidence review: {cand['label']} against {base['label']}", "",
             f"Generated {cand['generated_at']} by `src/eda/lower_level_evidence/refresh.py`. Shares are in points "
             "(percentage points of the evidence that is lower-level); + = more lower-level evidence than in the base run.",
             ""]
    if note:
        lines += [note, ""]
    if record:
        lines += ["**Steps run:** " + ", ".join(f"{k} ({v['seconds']} s)" for k, v in record.items()), ""]
    if not flags:
        lines += ["**No flag.** Every section was found and nothing moved past the thresholds (`refresh.py`'s "
                  "docstring).", ""]
        return "\n".join(lines)
    lines += [f"**{len(flags)} flags.** Read MISSING, UNEVEN DOSE and NEW LEVEL first: they decide whether a candidate "
              "built on this Stage 0 needs the level-aware treatment before `compare.py`.", ""]
    for name in ORDER:
        rows = [f for f in flags if f["flag"] == name]
        if not rows:
            continue
        lines += [f"## {name} ({len(rows)})", ""]
        cols = [c for c in rows[0] if c != "flag"]
        lines += ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        lines += ["| " + " | ".join(str(r.get(c, "")).replace("|", "\\|") for c in cols) + " |" for r in rows[:60]]
        if len(rows) > 60:
            lines.append(f"| … {len(rows) - 60} more in the JSON |" + " |" * (len(cols) - 1))
        lines.append("")
    return "\n".join(lines)


def write_diff(base: dict, cand: dict, name: str, record: dict | None = None, note: str = "") -> Path:
    flags = diff(base, cand)
    (SNAP / f"{name}.json").write_text(json.dumps(flags, indent=1), encoding="utf-8")
    md = SNAP / f"{name}.md"
    md.write_text(markdown(base, cand, flags, record, note), encoding="utf-8")
    print(f"{len(flags)} flags -> {md}", flush=True)
    return md


# ------------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True, help=f"this run's name (the first run is {BASE_LABEL})")
    ap.add_argument("--stage0-dir", type=Path, default=C.STAGE0_DIR)
    ap.add_argument("--timing", type=Path, default=None,
                    help="the match timeline built with the Stage 0 (required for a candidate Stage 0)")
    ap.add_argument("--frame", type=Path, default=C.FRAME, help="the model frame naming the model's matches")
    ap.add_argument("--base", default=BASE_LABEL, help="the snapshot to compare with")
    ap.add_argument("--steps", default=",".join(STEPS))
    ap.add_argument("--force", action="store_true", help="allow a step to overwrite its existing output folder")
    ap.add_argument("--scores", action="store_true", help="also run composition's part 5 (reads 2019-2024 results)")
    ap.add_argument("--model", default="reference", help="part 5's forecasts: reference, or a built folder")
    ap.add_argument("--boot", type=int, default=30, help="translation.py's bootstrap draws (DRIFT needs them)")
    ap.add_argument("--translation-args", default="", help="extra arguments for translation.py, quoted")
    ap.add_argument("--scenario", choices=["p7"], default=None,
                    help="only write the flags of a construction against the base (see the docstring)")
    a = ap.parse_args()
    SNAP.mkdir(parents=True, exist_ok=True)
    base_path = SNAP / f"{a.base}.json"

    if a.scenario == "p7":
        if not base_path.exists():
            raise SystemExit(f"no base snapshot {base_path}: run --steps snapshot --label {a.base} first")
        base = json.loads(base_path.read_text(encoding="utf-8"))
        write_diff(base, scenario_p7(base, a.base), f"scenario_p7_vs_{a.base}",
                   note="**A construction, not new data:** the base run's own preview of the ITF box scores of "
                        "2018-2024 (`itf_p7_scenario.csv`, column `box_lower_share_p7`) fed in as a candidate's "
                        "box-score shares. It shows what the flags will read when that data is wired in.")
        return 0

    steps = [s.strip() for s in a.steps.split(",") if s.strip()]
    timing = validate(a.label, steps, a.stage0_dir, a.timing, a.force)
    record = run(step_commands(steps, a.stage0_dir, timing, a.frame, a.label, a.scores, a.model, a.boot,
                               a.translation_args))
    snap_path = SNAP / f"{a.label}.json"
    if "snapshot" in steps:
        snap = snapshot(a.label)
        snap["stage0_dir"] = str(a.stage0_dir)
        snap["timing"] = str(timing)
        snap["steps_run"] = record
        snap_path.write_text(json.dumps(snap, indent=1), encoding="utf-8")
        print(f"snapshot -> {snap_path}", flush=True)
    if "diff" in steps:
        if a.label == a.base:
            print("diff skipped: the label equals the base", flush=True)
        elif not base_path.exists():
            raise SystemExit(f"no base snapshot {base_path}: run --steps snapshot --label {a.base} first")
        elif not snap_path.exists():
            raise SystemExit(f"no snapshot {snap_path}: include the snapshot step")
        else:
            write_diff(json.loads(base_path.read_text(encoding="utf-8")),
                       json.loads(snap_path.read_text(encoding="utf-8")), f"{a.label}_vs_{a.base}", record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
