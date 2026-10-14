"""Role D's supplementary scoring for the level-evidence system: the pre-registered pairs of the arms OUTSIDE the
selection set, on dev and on the holdout, run apart from the main runs and never touching the selection. The lead's
ruling of 10 Oct 2026 (option 2 of D's checkpoint-2 note), adopted in addition 5: the men's primary is not held while
these arms are built, and they are read when they are fitted, before or after the unlock.

Scope (anything else is refused):
    RES_ONLY           dev, holdout   RES_ONLY against REF (overall, strata, seasons); SYS against RES_ONLY (addition 3,
                                      section 3)
    SYS_BOTH           dev, holdout   SYS_BOTH against REF (overall, strata, seasons: "every arm against REF")
    SYS_ITFASIS        holdout        SYS against SYS_ITFASIS (addition 1); on dev too only where its inputs differ from
                                      SYS's before 2025 (addition 2, section 2: the fit queue did not copy its dev fits)
    SYS_BOTH_ITFASIS   holdout        SYS_BOTH against SYS_BOTH_ITFASIS; on dev likewise
    NEW_ASIS, NEW_SYS_BOTH, NEW_ASIS_PRE   dev, holdout (+ pooled 2020-2026, as the main holdout reports them):
                       addition 1's pairs (NEW_ASIS against REF, NEW_SYS_BOTH against SYS_BOTH and against NEW_ASIS,
                       NEW_ASIS_PRE against REF, NEW_ASIS against NEW_ASIS_PRE), on the matches the frames of the
                       group, SYS_BOTH's and the reference's all hold; and addition 4's rule-test verdict, from
                       system_decide.rule_test run on these readings: dev decides C0_now's additions of 2018-2024, the
                       holdout those of 2025-2026.
The six selection arms (SYS, SYS_w0, SYS_w50, SYS_w100, SEP_ALL, SYS_NOCLASS) are never targets: their readings, the
selection and the primary belong to the main runs (system_pairs.py, system_decide.py), which stay exactly as built. SYS
and SYS_BOTH enter only as the comparators the pairs name.

Rules
    * It never reads or writes results/selection.json. It computes only rows that name a supplementary arm; no row of
      a selection arm against REF, no selection, no primary, no reading against a close but the targets' own.
    * It may run after the unlock, for dev and holdout seasons alike. Holdout seasons need the unlock (the scorer's
      loader checks it before any read); dev seasons read results of seasons <= 2024 only, as the main dev run.
    * The freeze: every file the scorer requires (additions 3, 4b, 4c) and this file's own SHA-256 must be written in
      verified dated additions (addition 5). A target whose fits are missing or foreign refuses (system_pairs.gather).
    * Measurements are the scorer's own functions, unchanged: load_models, readings, pair_rows (compare.py's recipe).
      Holdout: the 2026 speed rule as the main run's ("zero"; the 909-match drop as a sensitivity, written beside).
    * Writes results/supplementary/<dev|holdout>/: <ARM>_pairs.csv and <ARM>.json per target, rule_test.json; on the
      holdout also the *_drop909 versions. A re-run of the same target rewrites its own files only.
Run: ./python.sh src/eda/lower_level_evidence/system_supplementary.py --period dev|holdout --arms RES_ONLY[,SYS_BOTH,...]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import system_decide as SD  # noqa: E402
from src.eda.lower_level_evidence import system_fits as SF  # noqa: E402
from src.eda.lower_level_evidence import system_pairs as SP  # noqa: E402

THIS = Path(__file__).resolve()
SELECTION_SET = ("SYS", "SYS_w0", "SYS_w50", "SYS_w100", "SEP_ALL", "SYS_NOCLASS")
SUPPLEMENTARY = ("RES_ONLY", "SYS_BOTH", "SYS_ITFASIS", "SYS_BOTH_ITFASIS", "NEW_ASIS", "NEW_SYS_BOTH", "NEW_ASIS_PRE")
NEW = ("NEW_ASIS", "NEW_SYS_BOTH", "NEW_ASIS_PRE")
DEV = "dev 2020-2024"


def out_dir(period: str) -> Path:
    return SP.RESULTS / "supplementary" / period


# ------------------------------------------------------------------------------------------------
# The plan: which pairs a target may have (pure)

def plan(arms, period: str) -> list[dict]:
    """One entry per target: its group ("main": the reference's matches; "c0": a candidate Stage 0's), the pairs it
    owns, whether it gets the full "against REF" table (strata, seasons), and the periods read. Refuses a selection arm
    or any arm outside the scope."""
    if period not in ("dev", "holdout"):
        raise SystemExit("period: dev or holdout")
    arms = [a for a in arms if a]
    bad = [a for a in arms if a in SELECTION_SET]
    if bad:
        raise SystemExit(f"{bad}: selection arms are never scored here (their readings are the main runs')")
    unknown = [a for a in arms if a not in SUPPLEMENTARY]
    if unknown:
        raise SystemExit(f"{unknown}: not a supplementary arm (scope: {', '.join(SUPPLEMENTARY)})")
    if not arms:
        raise SystemExit("no arm named")
    periods = [(DEV, SP.DEV_TEST)] if period == "dev" else [(SP.H, SP.HOLDOUT)]
    out = []
    for a in arms:
        if a == "RES_ONLY":
            out.append({"arm": a, "group": "main", "vs_ref_full": True, "sys_vs": ["RES_ONLY"], "pairs": [],
                        "periods": periods})
        elif a == "SYS_BOTH":
            out.append({"arm": a, "group": "main", "vs_ref_full": True, "sys_vs": [], "pairs": [], "periods": periods})
        elif a in ("SYS_ITFASIS", "SYS_BOTH_ITFASIS"):
            base = "SYS" if a == "SYS_ITFASIS" else "SYS_BOTH"
            if period == "dev" and not SP.dev_differs_before_2025(a):
                out.append({"arm": a, "group": "main", "vs_ref_full": False, "sys_vs": [], "pairs": [],
                            "periods": [], "note": "dev not read: its inputs equal its comparator's before 2025 "
                                                   "(addition 1: holdout only; addition 2, section 2)"})
                continue
            out.append({"arm": a, "group": "main", "vs_ref_full": False, "sys_vs": [], "pairs": [(base, a)],
                        "periods": periods})
        else:
            pairs = [p for p in SP.ADD1_NEW if a in p]
            per = periods if period == "dev" else periods + [(SP.PD, SP.POOLED)]
            out.append({"arm": a, "group": "c0", "vs_ref_full": False, "sys_vs": [], "pairs": pairs, "periods": per})
    return out


def comparators(entry: dict) -> list[str]:
    names = {x for p in entry["pairs"] for x in p} | ({"SYS"} if entry["sys_vs"] else set())
    return sorted(n for n in names if n not in ("REF", entry["arm"]))


# ------------------------------------------------------------------------------------------------
# The measurement: the scorer's own functions, on the rows the plan names

def compute(entries: list[dict], period: str, speed_rule: str, allow_missing=()) -> pd.DataFrame:
    """Rows of the plan's pairs only. Main-group targets share one load (REF, the targets and their comparators, on the
    matches all those frames hold); the C0 targets are loaded with SYS_BOTH and REF apart, as the main scorer does."""
    through, fits, test = (SP.DEV_LAST, SP.DEV_FITS, SP.DEV_TEST) if period == "dev" else \
        (2026, SP.ALL_FITS, SP.POOLED)
    parts = []
    main = [e for e in entries if e["group"] == "main" and e["periods"]]
    if main:
        names = sorted({e["arm"] for e in main} | {c for e in main for c in comparators(e)})
        usable, _ = SP.gather(names, fits, required=tuple(names), allow_missing=allow_missing)
        info, models = SP.load_models(usable, through, fits, test, speed_rule=speed_rule)
        for name, seasons in main[0]["periods"]:
            vs_ref = [e["arm"] for e in main if e["vs_ref_full"]]
            sys_vs = [b for e in main for b in e["sys_vs"]]
            extra = [p for e in main for p in e["pairs"]]
            t = SP.readings(info, models, seasons, name, vs_ref, sys_vs, extra_pairs=extra, closes=False)
            parts.append(t)
            for a in vs_ref:                                   # each target against its own calibrated close
                for tour, pop, mask in SP.populations(info, seasons, strata=False, seasons=False):
                    ids = info.index[mask]
                    r = SP.paired(info, ids, SP.CMP.close_forecast(info, "p_ref", seasons, ids),
                                  SP.fc(models, a, "s2", info, ids), matched=False)
                    parts.append(pd.DataFrame([SP.row(name, "vs close", a, "its calibrated close", "both stages",
                                                      tour, pop, r)]))
    c0 = [e for e in entries if e["group"] == "c0"]
    if c0:
        names = sorted({"SYS_BOTH"} | {e["arm"] for e in c0} | {c for e in c0 for c in comparators(e)})
        usable, _ = SP.gather(names, fits, required=tuple(names), allow_missing=allow_missing)
        info, models = SP.load_models(usable, through, fits, test, speed_rule=speed_rule, strict_price=False)
        pairs = sorted({p for e in c0 for p in e["pairs"]})
        for name, seasons in c0[0]["periods"]:
            parts.append(SP.pair_rows(info, models, seasons, name, pairs, "supplementary"))
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


# ------------------------------------------------------------------------------------------------
# Guards, the rule test and the run

def guards(period: str) -> dict:
    """The pre-registration and its additions verified; the freeze (the scorer's required files and this file)."""
    pre = SP.verify_prereg()
    freeze = SP.cp1_addition(required={**SP.cp1_files(SP.SYSTEM), "system_supplementary.py": THIS})
    if freeze["file"] is None:
        raise SystemExit("no verified addition holds the SHA-256, as on disk now, of: " + ", ".join(freeze["missing"])
                         + " (addition 5 freezes this module); refusing")
    out = {"preregistration": pre, "freeze": freeze}
    if period == "holdout":
        out["lock"] = {k: v for k, v in SP.verify_unlock().items() if k not in ("held", "unlock")}
    return out


def men_recommendation() -> str | None:
    """The main holdout decision's men's recommendation (system_decide.py --holdout), for the rule test's RES_ONLY flag;
    None before it exists. Read for reporting; nothing here decides a selection."""
    p = SP.RESULTS / "holdout" / "decision.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return ((d.get("primary_speed_rule") or {}).get("recommendation") or {}).get("recommend")


def rule_tests(t: pd.DataFrame, entries: list[dict]) -> dict:
    """Addition 4's rule test (system_decide.rule_test, unchanged) on the supplementary readings, per period."""
    if not any(e["group"] == "c0" for e in entries) or not len(t):
        return {}
    rec = men_recommendation()
    out = {}
    for name, _ in next(e for e in entries if e["group"] == "c0")["periods"]:
        out[name] = SD.rule_test(lambda a, b, tour: SP.get(t, a, b, tour, period=name), name, rec)
        out[name]["decides"] = ("C0_now's additions of 2018-2024" if name == DEV else
                                "C0_now's additions of 2025-2026" if name == SP.H else "reported only (pooled)")
    out["men_recommendation_read"] = rec
    return out


def run(period: str, arms, compute_fn=compute, allow_missing=()) -> dict:
    g = guards(period)
    entries = plan(arms, period)
    folder = out_dir(period)
    folder.mkdir(parents=True, exist_ok=True)
    rules = ["zero"] if period == "dev" else ["zero", "drop909"]
    summary = {"what": "supplementary readings (addition 5): pre-registered pairs of arms outside the selection set; "
                       "never the selection, the primary or a selection arm's reading", "period": period,
               "plan": [{k: (v if k != "periods" else [p for p, _ in v]) for k, v in e.items()} for e in entries],
               **g, "generated_at": SF.now()}
    for rule in rules:
        suffix = "" if rule == "zero" else "_drop909"
        t = compute_fn(entries, period, rule, allow_missing)
        for e in entries:
            mine = t[(t["first"] == e["arm"]) | (t["second"] == e["arm"])] if len(t) else t
            mine.to_csv(folder / f"{e['arm']}_pairs{suffix}.csv", index=False)
            SF.write_json(folder / f"{e['arm']}{suffix}.json",
                          {**{k: v for k, v in summary.items() if k != "plan"}, "arm": e["arm"], "speed_rule": rule,
                           "rows": int(len(mine)), "note": e.get("note")})
        rt = rule_tests(t, entries)
        if rt:
            SF.write_json(folder / f"rule_test{suffix}.json", {**{k: v for k, v in summary.items() if k != "plan"},
                                                                "speed_rule": rule, "rule_test": rt})
        summary[f"rows_{rule}"] = int(len(t))
    SF.write_json(folder / "last_run.json", summary)
    print(json.dumps({k: summary[k] for k in summary if k.startswith("rows_")} | {"period": period,
                                                                                  "arms": [e["arm"] for e in entries]}))
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--period", required=True, choices=("dev", "holdout"))
    ap.add_argument("--arms", required=True, help="comma list of supplementary arms")
    ap.add_argument("--allow-missing", default="", help="the lead's word only: a comparator waived (recorded)")
    a = ap.parse_args()
    run(a.period, a.arms.split(","), allow_missing=tuple(x for x in a.allow_missing.split(",") if x))
    return 0


if __name__ == "__main__":
    sys.exit(main())
