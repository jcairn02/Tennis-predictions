"""The decision layer of the level-evidence system (role D): the owner's decision of 9 October 2026, applied mechanically
to the frozen scorer's readings. It measures nothing: every number it uses was written by system_pairs.py.

Sources (read before any score of this run existed):
    docs/decisions/2026-10-09-adoption-by-change-class.md (the owner: "I accept your adoptation logic, implement it");
    data/studies/lower_level_evidence/system/owner_decision_2026-10-09.md, sections 1-5 (it governs where texts differ);
    data/studies/lower_level_evidence/system/preregistration_addition_4.md, which adopts them as this study's decision
    layer, replacing the pre-registration's selection steps 1-2 and recommendation and addition 1's interpretation.

The rules
    1. Harm. A reading shows harm when the named model is worse by MORE than 0.10 mLL (estimate < -0.10) with its WHOLE
       95% interval below 0 (hi < 0): the scorer's interval, compare.py's (t on blocks - 1). An estimate of exactly
       -0.10, or an interval touching 0, is not harm. An input flag shows harm only when F's hashed expected unevenness,
       read against the tour-season's dose (SPEC section 8), does not explain it: that is a reading of the input
       checks, written in D's report; the flags are listed here, never decided here (the owner's file, section 7).
    2. Selection (men, dev 2020-2024, both stages). SYS is selected unless a challenger (SYS_w0, SYS_w50, SYS_w100,
       SEP_ALL, SYS_NOCLASS: erratum 1 to the owner's file) reads "better" than SYS: its 95% interval against SYS
       clears 0. Of several, the largest point gain (a tie: the first in that order). The winner's estimate is also
       reported after the winner's luck: gain - 1.35 x SE, the owner's file's figure, with the number of challengers
       (five) recorded beside it. R_S2 and SYS_S2 (the two share inputs, a new feature found on 2020-2024) are not
       challengers: they are fitted, scored and reported against REF and against SYS, as registered, as lead evidence
       for the feature pool (the owner's decision, point 6), never selected on their discovery seasons.
    3. REF instead (no change) only if the selected arm shows harm against REF for men on dev.
    4. Recommendation (men). SELECTED unless the holdout primary (SELECTED against REF, men, 2025-2026) shows harm, or
       any of addition 2's eight Holm-corrected readings reads "worse" after Holm (the scorer's holm family). Then REF,
       with what drove it. No edge credit: the edge that sizes stakes comes only from untouched matches at the venue's
       price. Applied to the primary speed rule (no stage-2 nudge without a speed memory) and, reported beside it, to
       the 909-match drop sensitivity.
    5. The rule test. C0_now's additions are recommended for entry by the system's route (NEW_SYS_BOTH: B's translation
       and weights for every new box score, its w_results for every new result, w = 0 for ITF and ITFQ box scores
       until P7) for each tour whose treatment is the system's, unless NEW_SYS_BOTH against SYS_BOTH shows harm for
       that tour: on dev for the additions of 2018-2024, on the holdout for those of 2025-2026. That is men now; women's
       treatment waits for P7, and their readings (with REF_noITF against REF, the 2025-26 ITF box scores already in
       the reference) are reported as its harm evidence. NEW_ASIS and NEW_ASIS_PRE are reported, never decisive. If REF
       is recommended for men, the flag "register RES_ONLY on C0_now next" is raised.
    The registered rules' outcomes (system_pairs.py's: selection_registered.json, with its own seven challengers; the
    registered recommendation in holdout/readings.json; addition 1's interpretation) are written beside every decision,
    for the record.

Modes
    --dev       after system_pairs.py --dev: reads results/dev/pairs.csv, dev/addition1_pairs.csv and
                selection_registered.json; writes results/selection.json (the selection in force, marked
                system_pairs.DECISION_LAYER, which the holdout requires) and results/dev/decision.json. Refuses once
                system/holdout_unlock.json exists, and without the freeze (this file's SHA-256 in a verified addition).
    --holdout   after system_pairs.py --holdout: reads results/holdout/readings.json, pairs.csv and pairs_drop909.csv;
                writes results/holdout/decision.json. Needs the unlock (as the readings it reads do).
Run: ./python.sh src/eda/lower_level_evidence/system_decide.py --dev | --holdout
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import system_fits as SF  # noqa: E402
from src.eda.lower_level_evidence import system_pairs as SP  # noqa: E402

HARM_MLL = 0.10                 # the owner's file, section 1: may not be loosened once a score it governs exists
WINNERS_LUCK = 1.35             # section 2: the owner's file's figure, kept as stated (erratum 1 does not change it)
# Erratum 1 (owner_decision_2026-10-09_erratum_1.md, section 1): the challengers of the amended selection
CHALLENGERS = ("SYS_w0", "SYS_w50", "SYS_w100", "SEP_ALL", "SYS_NOCLASS")
POOL_LEADS = ("R_S2", "SYS_S2")  # reported, never selected: the share inputs are a new feature found on 2020-2024
POOL_LABEL = "lead evidence for the pool, seasons 2020-2024 (2025-2026 on the holdout)"
DEV = "dev 2020-2024"
SOURCES = {"decision": "docs/decisions/2026-10-09-adoption-by-change-class.md",
           "applied": "data/studies/lower_level_evidence/system/owner_decision_2026-10-09.md (sections 1-5)",
           "erratum": "data/studies/lower_level_evidence/system/owner_decision_2026-10-09_erratum_1.md (section 1: the "
                      "challengers; R_S2 and SYS_S2 report-only)",
           "adopted": "data/studies/lower_level_evidence/system/preregistration_addition_4.md (code: 4b, 4c)"}
NO_EDGE_CREDIT = ("no edge credit: a change adopted on these rules adds nothing to the edge used for stakes, which comes "
                  "only from untouched matches at the venue's price")


# ------------------------------------------------------------------------------------------------
# The rules (pure: tested on synthetic readings)

def finite(x) -> bool:
    try:
        return x is not None and bool(np.isfinite(float(x)))
    except (TypeError, ValueError):
        return False


def harm(r: dict | None) -> bool:
    """Section 1: the named (first) model worse by more than 0.10 mLL with the whole 95% interval below 0."""
    if r is None or not finite(r.get("estimate")) or not finite(r.get("hi")):
        return False
    return float(r["estimate"]) < -HARM_MLL and float(r["hi"]) < 0


def cell(r: dict | None) -> dict | None:
    if r is None:
        return None
    return {k: r.get(k) for k in ("comparison", "tour", "population", "stage", "matches", "estimate", "lo", "hi", "se",
                                  "p_better", "reading")}


def select_amended(sys_vs: dict, vs_ref: dict) -> dict:
    """Sections 2-3 with erratum 1. sys_vs[C] = the reading "SYS vs C" (+ = SYS better), men, dev, both stages;
    vs_ref[A] = "A vs REF". A challenger (CHALLENGERS: five) qualifies when it reads better than SYS: SYS vs C has
    hi < 0 (its interval against SYS clears 0). Readings of R_S2 and SYS_S2, if passed, are ignored here."""
    rows, missing = [], []
    for c in CHALLENGERS:
        r = sys_vs.get(c)
        if r is None:
            missing.append(c)
            rows.append({"challenger": c, "scored": False})
            continue
        gain, se = -float(r["estimate"]), float(r["se"])
        rows.append({"challenger": c, "scored": True, "gain_over_SYS_mLL": gain, "lo": -float(r["hi"]),
                     "hi": -float(r["lo"]), "se": se, "reads_better_than_SYS": bool(float(r["hi"]) < 0),
                     "gain_after_winners_luck": gain - WINNERS_LUCK * se})
    qual = [r for r in rows if r.get("reads_better_than_SYS")]
    step1 = max(qual, key=lambda r: r["gain_over_SYS_mLL"])["challenger"] if qual else "SYS"
    ref_r = vs_ref.get(step1)
    ok = not missing and vs_ref.get("SYS") is not None and ref_r is not None
    shows_harm = harm(ref_r)
    selected = ("REF" if shows_harm else step1) if ok else None
    winner = next((r for r in rows if r["challenger"] == step1), None) if step1 != "SYS" else None
    return {"status": "final" if ok else "incomplete", "selected": selected, "step1_arm": step1,
            "qualifying": [r["challenger"] for r in qual], "missing_challengers": missing, "challengers": rows,
            "step1_vs_REF_men_dev": cell(ref_r), "step1_shows_harm_against_REF": shows_harm,
            "winner_after_winners_luck": ({"challenger": step1, "gain_over_SYS_mLL": winner["gain_over_SYS_mLL"],
                                           "after_winners_luck_mLL": winner["gain_after_winners_luck"],
                                           "figure": WINNERS_LUCK, "challengers": len(CHALLENGERS),
                                           "rule": f"gain - {WINNERS_LUCK} x SE (the owner's file's figure; "
                                                   f"{len(CHALLENGERS)} challengers)"} if winner else None),
            "challenger_list": list(CHALLENGERS), "not_challengers": {a: POOL_LABEL for a in POOL_LEADS},
            "rules": "the owner's decision of 9 Oct 2026 (sections 2-3) with erratum 1: SYS unless one of five "
                     "challengers reads better than SYS (men, dev, both stages); of several, the largest gain; REF only "
                     "if that arm shows harm against REF (worse by more than 0.10 mLL, whole 95% interval below 0); "
                     "R_S2 and SYS_S2 reported, not challengers"}


def pool_leads(get_reading, seasons: str) -> dict:
    """Erratum 1: R_S2's and SYS_S2's registered readings, against REF and against SYS, labelled as lead evidence for
    the feature pool with their seasons; never decisive. get_reading(first, second, tour)."""
    out = {"label": POOL_LABEL, "seasons_read": seasons, "decides": "nothing (the owner's decision, point 6: a selection "
                                                                    "round outside the discovery seasons decides)"}
    for tour in SP.TOURS:
        out[tour] = {f"{a} vs {b}": cell(get_reading(a, b, tour)) for a, b in (
            ("R_S2", "REF"), ("SYS_S2", "REF"), ("SYS", "R_S2"), ("SYS", "SYS_S2"), ("SYS_S2", "SYS"))}
    return out


def recommend_amended(primary: dict | None, holm: dict | None, selected: str) -> dict:
    """Section 4. A missing primary or an incomplete Holm family refuses: never a silent fall back."""
    if selected == "REF":
        return {"recommend": "REF (no change)", "drivers": ["REF was selected on dev: the selected arm showed harm "
                                                            "against REF for men on dev"], "edge": NO_EDGE_CREDIT}
    if primary is None:
        raise SystemExit(f"the holdout primary ({selected} vs REF, men) is missing: refusing (never a fall back to REF)")
    if holm is None or not holm.get("complete"):
        raise SystemExit("addition 2's eight Holm readings are incomplete: the recommendation cannot be applied; "
                         "refusing")
    drivers = []
    if harm(primary):
        drivers.append(f"the holdout primary shows harm: {selected} vs REF, men, {primary['estimate']:+.3f} "
                       f"[{primary['lo']:+.3f}, {primary['hi']:+.3f}] mLL")
    for name in holm.get("worse_after_holm", []):
        drivers.append(f"worse after Holm: {name}")
    return {"recommend": "REF" if drivers else selected, "drivers": drivers, "primary": cell(primary),
            "primary_shows_harm": harm(primary), "worse_after_holm": list(holm.get("worse_after_holm", [])),
            "raw_worse_of_the_eight": list(holm.get("raw_worse", [])), "edge": NO_EDGE_CREDIT,
            "rules": "the owner's decision of 9 Oct 2026 (section 4): SELECTED unless the holdout primary shows harm or "
                     "any of addition 2's eight readings is worse after Holm"}


def rule_test(get_reading, period: str, men_recommended: str | None) -> dict:
    """Section 5, one period: the dev period decides C0_now's 2018-2024 additions, the holdout its 2025-2026 ones.
    get_reading(first, second, tour) returns the reading or None."""
    out = {"period": period, "tours": {}}
    for tour in SP.TOURS:
        r = get_reading("NEW_SYS_BOTH", "SYS_BOTH", tour)
        if tour == "men":
            if r is None:
                verdict = "not scored: NEW_SYS_BOTH or SYS_BOTH has no reading (the default cannot be applied yet)"
            elif harm(r):
                verdict = "not recommended: NEW_SYS_BOTH shows harm against SYS_BOTH for men"
            else:
                verdict = "recommended for entry by the system's route (NEW_SYS_BOTH): no harm against SYS_BOTH"
        elif tour == "women":
            verdict = ("waits for P7: women's treatment is decided then by the same rule; this reading and REF_noITF "
                       "against REF are its harm evidence")
        else:
            verdict = "reported (the rule is per tour)"
        out["tours"][tour] = {"verdict": verdict, "NEW_SYS_BOTH vs SYS_BOTH": cell(r), "shows_harm": harm(r),
                              "reported_not_decisive": {f"{a} vs {b}": cell(get_reading(a, b, tour)) for a, b in (
                                  ("NEW_ASIS", "REF"), ("NEW_ASIS_PRE", "REF"), ("NEW_ASIS", "NEW_ASIS_PRE"),
                                  ("NEW_SYS_BOTH", "NEW_ASIS"), ("REF_noITF", "REF"))}}
    out["register_RES_ONLY_on_C0_now_next"] = bool(men_recommended is not None
                                                   and str(men_recommended).startswith("REF"))
    if out["register_RES_ONLY_on_C0_now_next"]:
        out["flag"] = ("REF is recommended for men: register RES_ONLY on C0_now next (the men's results keep a "
                       "supported route: B's w_results)")
    return out


# ------------------------------------------------------------------------------------------------
# Inputs and guards

def guards(mode: str) -> dict:
    pre = SP.verify_prereg()
    cp1 = SP.require_cp1(False)
    if mode == "dev" and SP.UNLOCK.exists():
        raise SystemExit("the holdout unlock exists: the selection was written down before it; not re-decided")
    return {"preregistration": pre, "freeze": cp1}


def reader(paths: list[Path]):
    t = pd.concat([pd.read_csv(p) for p in paths if p.exists()], ignore_index=True)
    return t, (lambda first, second, tour, period, pop="all", stage="both stages":
               SP.get(t, first, second, tour, pop, stage, period=period))


def input_flags(arms) -> dict:
    """The input checks' flags (compare.py part 1, no result) of the arms that bear on the rule test: listed for the
    reading of section 1's input-flag harm (D's report), never decided here."""
    out = {}
    for a in arms:
        p = SF.arm_dir(a) / SF.CMP_DIR / "part1_summary.json"
        if p.exists():
            d = json.loads(p.read_text(encoding="utf-8"))
            out[a] = {"inputs_changed": d.get("inputs_changed"), "inputs_flagged": d.get("inputs_flagged")}
    return out


# ------------------------------------------------------------------------------------------------
# Modes

def dev() -> dict:
    g = guards("dev")
    reg_path, pairs = SP.SELECTION_REGISTERED, SP.RESULTS / "dev" / "pairs.csv"
    if not reg_path.exists() or not pairs.exists():
        raise SystemExit("run system_pairs.py --dev first (no selection_registered.json or dev/pairs.csv)")
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    t, get = reader([pairs, SP.RESULTS / "dev" / "addition1_pairs.csv"])
    sys_vs = {c: get("SYS", c, "men", DEV) for c in CHALLENGERS}
    vs_ref = {a: get(a, "REF", "men", DEV) for a in ("SYS",) + CHALLENGERS}
    sel = select_amended(sys_vs, vs_ref)
    sel.update({"decision_layer": SP.DECISION_LAYER, "sources": SOURCES, "period": DEV,
                "registered_rules_outcome": {k: reg.get(k) for k in ("status", "selected", "step1_arm", "qualifying",
                                                                     "step1_p_better_than_REF", "t_cdf_check")},
                "agrees_with_registered_rules": sel["selected"] == reg.get("selected"),
                "sides_parquet_sha256": reg.get("sides_parquet_sha256"), "arms_scored": reg.get("arms_scored"),
                "arms_record": reg.get("arms_record"), "selection_registered_sha256": SF.sha256(reg_path),
                "dev_pairs_sha256": SF.sha256(pairs), **g, "generated_at": SF.now()})
    SF.write_json(SP.SELECTION, sel)
    dec = {"decision_layer": SP.DECISION_LAYER, "sources": SOURCES, "selection": {k: sel[k] for k in (
               "status", "selected", "step1_arm", "qualifying", "challenger_list", "winner_after_winners_luck",
               "step1_shows_harm_against_REF", "agrees_with_registered_rules")},
           "rule_test_2018_2024": rule_test(lambda a, b, tour: get(a, b, tour, DEV), DEV,
                                            "REF" if sel["selected"] == "REF" else None),
           "results_channel": {f"{a} vs {b}, {tour}": cell(get(a, b, tour, DEV))
                               for a, b in (("RES_ONLY", "REF"), ("SYS", "RES_ONLY")) for tour in SP.TOURS},
           "pool_lead_evidence": pool_leads(lambda a, b, tour: get(a, b, tour, DEV), "2020-2024 (dev)"),
           "input_flags_for_the_harm_reading": input_flags(("SYS", "NEW_ASIS", "NEW_SYS_BOTH", "NEW_ASIS_PRE",
                                                            "REF_noITF")),
           "registered_rule_test_interpretation": "results/dev/addition1.json (addition 1's, kept for the record)",
           "generated_at": SF.now()}
    SF.write_json(SP.RESULTS / "dev" / "decision.json", dec)
    print(json.dumps(dec["selection"], indent=1, default=str))
    print(f"selection.json sha256 {SF.sha256(SP.SELECTION)} (the unlock must hold it)")
    return dec


def holdout() -> dict:
    g = guards("holdout")
    SP.verify_unlock()
    out = SP.RESULTS / "holdout"
    rd = out / "readings.json"
    if not rd.exists():
        raise SystemExit("run system_pairs.py --holdout first (no holdout/readings.json)")
    readings = json.loads(rd.read_text(encoding="utf-8"))
    sel = json.loads(SP.SELECTION.read_text(encoding="utf-8"))
    if sel.get("decision_layer") != SP.DECISION_LAYER or sel.get("selected") != readings.get("selected_on_dev"):
        raise SystemExit("the holdout readings were not made with the decision layer's selection; refusing")
    selected = sel["selected"]
    dec = {"decision_layer": SP.DECISION_LAYER, "sources": SOURCES, "selected_on_dev": selected, **g,
           "readings_sha256": SF.sha256(rd)}
    for key, res, pairs in (("primary_speed_rule", readings, out / "pairs.csv"),
                            ("sensitivity_drop909", readings.get("sensitivity_drop909", {}), out / "pairs_drop909.csv")):
        t, get = reader([pairs])
        rec = recommend_amended(res.get("primary"), res.get("holm"), selected)
        dec[key] = {"recommendation": rec,
                    "registered_rules_recommendation": res.get("recommendation"),
                    "rule_test_2025_2026": rule_test(lambda a, b, tour: get(a, b, tour, SP.H), SP.H, rec["recommend"]),
                    "rule_test_pooled_2020_2026_reported": rule_test(lambda a, b, tour: get(a, b, tour, SP.PD), SP.PD,
                                                                     rec["recommend"]),
                    "pool_lead_evidence": pool_leads(lambda a, b, tour: get(a, b, tour, SP.H), "2025-2026 (holdout)"),
                    "registered_rule_test_interpretation": (res.get("addition1") or {}).get("interpretation")}
    dec["generated_at"] = SF.now()
    SF.write_json(out / "decision.json", dec)
    print(json.dumps({k: dec[k]["recommendation"]["recommend"] for k in ("primary_speed_rule", "sensitivity_drop909")},
                     indent=1))
    return dec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dev", action="store_true")
    g.add_argument("--holdout", action="store_true")
    a = ap.parse_args()
    if a.dev:
        dev()
    else:
        holdout()
    return 0


if __name__ == "__main__":
    sys.exit(main())
