"""The pre-registered readings of the role-08 candidate (lower-level evidence): every arm against the frozen reference
and the paired arm-against-arm readings, both stages, 2020-2024, with compare.py's own functions.

The plan: data/studies/lower_level_evidence/candidates/preregistration.md. This scorer refuses to run if that file's
SHA-256 (CRLF normalised to LF) differs from preregistration.sha256.

What it does (compare.py's recipe, unchanged: src/eda/current_best_model/compare.py):
    * each model's seeds 0-3 forecasts (seed_table, with its file checks), the seed mean;
    * per model, the per-tour calibration slopes and stage 2's b, fitted walk-forward on 2019 .. Y - 1, debut seasons out,
      b shrunk with tau 0.05 (walk_forward), on the reference's speed column for every arm (stage 1 is all that changes);
    * forecasts on a population (forecasts), paired log loss (paired: four-week blocks plus the seeds' variance, paired
      by seed between two models; unpaired against a closing price);
    * the matches every frame holds, scored on 2020-2024, debut seasons out. Results of seasons <= 2024 only.
POSITIVE = THE NAMED CANDIDATE HAS THE LOWER LOG LOSS (better), in mLL per match. "better" / "worse" when the 95%
interval clears 0, otherwise "unresolved" with P(better) (the owner's decision of 9 Oct 2026; the pre-registration's
"tie"). The dated addition of 9 Oct (written before any score): the R_S2 control and the reading FP vs R_S2.

Populations (sides.parquet of role 02, counts only): both tours, men, women; exposure (the less-exposed side's
main-tour results in 365 days under 10, 10 or more); share gap (|A's - B's 365-day lower-level box-score share| at least
0.5, under 0.5; matches where a side has no box score in the window are left out); the falsification stratum (both
sides 20+ main-tour results and a share under 0.10); each season.

Harness check: this scorer's FP-vs-reference primary row must equal compare.py's (FP/vs_reference_2026-10-08/scores.csv).
Writes candidates/results/pairs.csv, results.json (the verdict by the pre-registered rule), stratum_inputs.csv.
Run: ./python.sh src/eda/lower_level_evidence/candidate_pairs.py [--arms FP,F,P,FP_placebo,R_L,FP_L,FP_half]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import compare as CMP  # noqa: E402
from src.eda.current_best_model import reference as R  # noqa: E402
from src.eda.lower_level_evidence import candidate_arms as CA  # noqa: E402

CAND = CA.CAND
RESULTS = CAND / "results"
PREREG = CAND / "preregistration.md"
PREREG_SHA = CAND / "preregistration.sha256"
PREREG_ADD_SHA = CAND / "preregistration_addition.sha256"
ADDITION = b"\n## Addition of 9 Oct 2026"
ARMS = ("FP", "F", "P", "FP_placebo", "R_L", "FP_L", "FP_half", "R_S2")
LOWER = CA.LOWER
ALL = CA.ALL_BUCKETS
TEST = tuple(range(CMP.SCORE_FROM, CMP.THROUGH + 1))           # 2020-2024
SEASONS = tuple(range(CMP.FIT_FROM, CMP.THROUGH + 1))          # 2019-2024


def verify_prereg() -> dict:
    """The original pre-registration (the text before the dated addition) and the file with the addition must both
    equal the hashes recorded before any score was read."""
    full = PREREG.read_bytes().replace(b"\r\n", b"\n")
    cut = full.find(ADDITION)
    original = full[:cut] if cut >= 0 else full
    got = {"original": hashlib.sha256(original).hexdigest(), "with_addition": hashlib.sha256(full).hexdigest()}
    want = {"original": PREREG_SHA.read_text(encoding="utf-8").strip(),
            "with_addition": PREREG_ADD_SHA.read_text(encoding="utf-8").strip() if PREREG_ADD_SHA.exists() else None}
    if got["original"] != want["original"] or (want["with_addition"] and got["with_addition"] != want["with_addition"]):
        raise SystemExit(f"the pre-registration changed after it was hashed ({got} != {want}); refusing to score")
    return got


def reading(r: dict) -> str:
    """compare.py's reading: "better" or "worse" when the 95% interval clears 0, otherwise "unresolved" (the owner's
    decision of 9 Oct 2026: no comparison is called a tie; the pre-registration's "tie" reads as "unresolved")."""
    return r["reading"]


def strata(info: pd.DataFrame) -> dict[str, np.ndarray]:
    """Pre-registered strata of the scored matches (debut seasons out, 2020-2024), from sides.parquet (counts only)."""
    cols = ["match_id", "side", "res_365d_MAIN"] + [f"box_365d_{b}" for b in ALL]
    s = pd.read_parquet(CA.SIDES, columns=cols)
    tot = s[[f"box_365d_{b}" for b in ALL]].sum(axis=1).to_numpy(float)
    low = s[[f"box_365d_{b}" for b in LOWER]].sum(axis=1).to_numpy(float)
    s["share"] = np.where(tot > 0, low / np.where(tot > 0, tot, 1.0), np.nan)
    a = s[s["side"] == "A"].set_index("match_id").reindex(info.index)
    b = s[s["side"] == "B"].set_index("match_id").reindex(info.index)
    keep = ~info["debut"].to_numpy() & info["season"].isin(list(TEST)).to_numpy()
    expo = np.minimum(a["res_365d_MAIN"].to_numpy(float), b["res_365d_MAIN"].to_numpy(float))
    gap = np.abs(a["share"].to_numpy() - b["share"].to_numpy())
    known = np.isfinite(gap)
    fals = ((a["res_365d_MAIN"].to_numpy(float) >= 20) & (b["res_365d_MAIN"].to_numpy(float) >= 20)
            & (a["share"].to_numpy() < 0.10) & (b["share"].to_numpy() < 0.10))
    tour = info["tour"].to_numpy()
    out = {"both tours": keep, "men": keep & (tour == "atp"), "women": keep & (tour == "wta"),
           "exposure < 10": keep & (expo < 10), "exposure >= 10": keep & (expo >= 10),
           "share gap >= 0.5": keep & known & (gap >= 0.5), "share gap < 0.5": keep & known & (gap < 0.5),
           "share gap unknown (left out)": keep & ~known,
           "falsification: both 20+ main-tour, share < 0.10": keep & fals}
    for Y in TEST:
        out[f"season {Y}"] = ~info["debut"].to_numpy() & (info["season"].to_numpy() == Y)
    return out


def load_models(arms) -> tuple[pd.DataFrame, dict]:
    """info (the reference's match facts on the matches every frame holds, 2019-2024) and, per model, its seed table,
    stage-1 and both-stage walk-forward parameters."""
    P_ref = R.paths("reference")
    ref = CMP.inputs_frame(P_ref)
    frames = {"reference": (P_ref, ref)}
    for arm in arms:
        _, P, folder = CMP.candidate(str(CAND / arm))
        frames[arm] = (P, CMP.inputs_frame(P))
    ids = ref.index
    for _, (P, f) in frames.items():
        ids = ids.intersection(f.index)
    y_ref = CMP.outcomes(P_ref, CMP.THROUGH)
    info = CMP.scoring_info(ref.loc[ids], ref.loc[ids], y_ref, y_ref, CMP.THROUGH)
    for arm in arms:
        y = CMP.outcomes(frames[arm][0], CMP.THROUGH).reindex(info.index)
        if not np.array_equal(y.to_numpy(float), info["y"].to_numpy(float)):
            raise SystemExit(f"{arm}: its results differ from the reference's")
        if not np.allclose(frames[arm][1].loc[info.index, "p_mkt"].to_numpy(float), info["p_ref"].to_numpy(float),
                           rtol=0, atol=0, equal_nan=True):
            raise SystemExit(f"{arm}: its closing price differs from the reference's")
    z = R.speed_column("reference")
    models = {}
    for name, (P, f) in frames.items():
        p = CMP.seed_table(P, f, SEASONS).reindex(info.index)
        if p.isna().any().any():
            raise SystemExit(f"{name}: forecasts missing on scored matches")
        eta = pd.Series(CMP.C.lg(p.mean(axis=1).to_numpy()), index=p.index)
        models[name] = {"p": p, "s1": CMP.walk_forward(eta, info, None, TEST), "s2": CMP.walk_forward(eta, info, z, TEST)}
    models["_z"] = z
    return info, models


def fc(models: dict, name: str, stage: str, info: pd.DataFrame, ids: pd.Index):
    m = models[name]
    return CMP.forecasts(m["p"], info, m[stage], models["_z"] if stage == "s2" else None, ids)


def row(group: str, population: str, comparison: str, stage: str, r: dict) -> dict:
    return {"group": group, "population": population, "comparison": comparison, "stage": stage,
            **{k: r[k] for k in ("matches", "estimate", "lo", "hi", "se", "p_better", "blocks")},
            "reading": reading(r)}


def stratum_inputs(info: pd.DataFrame, pops: dict) -> pd.DataFrame:
    """How far FP moved the 18 inputs in each population: the median |change| in the reference's SD (no result)."""
    ref = CA.inputs_of(CA.REF_FRAME).set_index("match_id").loc[info.index]
    fp = CA.inputs_of(CAND / "FP" / "model_frame.parquet").set_index("match_id").loc[info.index]
    rows = []
    for pop, mask in pops.items():
        rec = {"population": pop, "matches": int(mask.sum())}
        meds, shares = [], []
        for n in CA.TRANSLATED:
            a, b = ref[f"in_{n}"].to_numpy(float), fp[f"in_{n}"].to_numpy(float)
            sd = np.nanstd(a)
            d = np.abs(a - b)[mask & np.isfinite(a) & np.isfinite(b)] / sd
            meds.append(float(np.median(d)) if len(d) else np.nan)
            shares.append(float((d > 0).mean()) if len(d) else np.nan)
        rec["median_abs_change_sd_mean_over_18"] = float(np.nanmean(meds))
        rec["share_of_input_values_changed"] = float(np.nanmean(shares))
        rows.append(rec)
    return pd.DataFrame(rows)


def unexpected_uneven(info_all: pd.DataFrame | None = None) -> dict:
    """The pre-registered 'unexpected uneven input' test on FP's compare.py part 1 (no result read)."""
    src = CAND / "FP" / "vs_reference_2026-10-08" / "inputs.csv"
    if not src.exists():
        return {"flags": [], "unexpected": [], "any_unexpected": None, "note": f"{src} missing: run compare.py first"}
    per = pd.read_csv(src)
    out = {"flags": per.loc[per["flag"].isin(["uneven", "every season"]), ["input", "flag", "flagged"]].to_dict("records"),
           "unexpected": []}
    ref = CA.inputs_of(CA.REF_FRAME)
    sh = {"h2w": CA.side_shares("h2w").reindex(ref["match_id"]), "365d": CA.side_shares("365d").reindex(ref["match_id"])}
    for r in out["flags"]:
        name = r["input"]
        if name not in CA.TRANSLATED:
            out["unexpected"].append({**r, "why": "not a translated input"})
            continue
        if r["flag"] != "uneven":
            continue
        win = "365d" if name == "points_52w" else "h2w"
        g = pd.DataFrame({"tour": ref["tour"].to_numpy(), "season": ref["season"].to_numpy(),
                          "gap": np.abs(sh[win]["share_a"].to_numpy() - sh[win]["share_b"].to_numpy())})
        g = g[g["season"].between(2013, 2026)].groupby(["tour", "season"])["gap"].mean()
        for cell in str(r["flagged"]).split("; "):
            tour, season = cell.split()
            med = float(g.loc[tour].median())
            val = float(g.loc[(tour, int(season))])
            if val < med:
                out["unexpected"].append({**r, "cell": cell, "mean_abs_share_gap": val, "tour_median": med,
                                          "why": "flagged tour-season below the tour's median share gap"})
    out["any_unexpected"] = bool(out["unexpected"])
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--cand-dir", default=None, help="another candidates folder (the harness dry run); default the "
                                                    "study's")
    a = ap.parse_args()
    sha = verify_prereg()
    global CAND, RESULTS
    if a.cand_dir:
        CAND = Path(a.cand_dir)
        RESULTS = CAND / "results"
    arms = [x for x in a.arms.split(",") if x and (CAND / x / "fits").exists()]
    missing = [x for x in a.arms.split(",") if x and x not in arms]
    if "FP" not in arms:
        raise SystemExit("FP has no fits yet")
    info, models = load_models(arms)
    pops = strata(info)
    rows = []
    # every arm against the reference
    for arm in arms:
        groups = pops if arm == "FP" else {k: pops[k] for k in ("both tours", "men", "women")}
        for pop, mask in groups.items():
            ids = info.index[mask]
            if len(ids) == 0:
                continue
            for stage in ("s2", "s1"):
                if stage == "s1" and arm != "FP" and pop != "both tours":
                    continue
                r = CMP.paired(info, ids, fc(models, "reference", stage, info, ids), fc(models, arm, stage, info, ids))
                rows.append(row("vs reference", pop, f"{arm} vs reference",
                                "both stages" if stage == "s2" else "stage 1", r))
    # arm against arm
    for cand, base in (("FP", "FP_placebo"), ("FP_L", "R_L"), ("FP", "R_S2")):
        if cand in arms and base in arms:
            for pop in ("both tours", "men", "women"):
                ids = info.index[pops[pop]]
                r = CMP.paired(info, ids, fc(models, base, "s2", info, ids), fc(models, cand, "s2", info, ids))
                rows.append(row("arm vs arm", pop, f"{cand} vs {base}", "both stages", r))
    # each model against its calibrated close (the close is the same in every frame)
    for name in ["reference"] + arms:
        ids = info.index[pops["both tours"]]
        r = CMP.paired(info, ids, CMP.close_forecast(info, "p_ref", TEST, ids), fc(models, name, "s2", info, ids),
                       matched=False)
        rows.append(row("vs close", "both tours", f"{name} vs its calibrated close", "both stages", r))
    t = pd.DataFrame(rows)
    RESULTS.mkdir(parents=True, exist_ok=True)
    t.to_csv(RESULTS / "pairs.csv", index=False)
    si = stratum_inputs(info, {k: v for k, v in pops.items() if not k.startswith("season")})
    si.to_csv(RESULTS / "stratum_inputs.csv", index=False)
    # harness check against compare.py's own primary row
    harness = {}
    cs = CAND / "FP" / "vs_reference_2026-10-08" / "scores.csv"
    if cs.exists():
        c = pd.read_csv(cs)
        c = c[(c["group"] == "primary") & (c["population"] == "both tours")
              & (c["comparison"] == "both stages: candidate vs reference")].iloc[0]
        mine = t[(t["comparison"] == "FP vs reference") & (t["population"] == "both tours")
                 & (t["stage"] == "both stages")].iloc[0]
        harness = {"compare_py": {k: float(c[k]) for k in ("estimate", "lo", "hi")},
                   "this_scorer": {k: float(mine[k]) for k in ("estimate", "lo", "hi")},
                   "equal": bool(all(abs(float(c[k]) - float(mine[k])) < 1e-9 for k in ("estimate", "lo", "hi")))}

    def get(comp, pop="both tours", stage="both stages"):
        s = t[(t["comparison"] == comp) & (t["population"] == pop) & (t["stage"] == stage)]
        return s.iloc[0].to_dict() if len(s) else None
    prim = get("FP vs reference")
    plac = get("FP vs FP_placebo")
    expo = get("FP_L vs R_L")
    uneven = unexpected_uneven()
    secondaries = {"F vs reference": get("F vs reference"), "P vs reference": get("P vs reference"),
                   "FP vs reference, men": get("FP vs reference", "men"),
                   "FP vs reference, women": get("FP vs reference", "women"),
                   **{f"FP vs reference, {k}": get("FP vs reference", k) for k in
                      ("exposure < 10", "exposure >= 10", "share gap >= 0.5", "share gap < 0.5")},
                   "FP_L vs R_L": expo}
    # the falsification stratum is "reported without a decision rule" (pre-registration): read, never decisive
    falsification = get("FP vs reference", "falsification: both 20+ main-tour, share < 0.10")
    worse = [k for k, v in secondaries.items() if v is not None and v["reading"] == "worse"]
    absent = [k for k, v in secondaries.items() if v is None]
    if prim["reading"] == "better":
        conds = {"FP beats FP_placebo": bool(plac and plac["reading"] == "better"),
                 "FP_L not worse than R_L": bool(expo and expo["reading"] != "worse")}
        verdict = "Better" if all(conds.values()) else "primary better, but " + ", ".join(k for k, v in conds.items()
                                                                                          if not v) + " failed"
    elif prim["reading"] == "unresolved":
        conds = {"no unexpected uneven input": not uneven["any_unexpected"],
                 "no secondary worse": not worse, "every secondary scored": not absent}
        verdict = ("Unresolved (the pre-registration's 'tie'), recommend on mechanism" if all(conds.values())
                   else "Unresolved (the pre-registration's 'tie'), not recommended on mechanism: "
                   + ", ".join(k for k, v in conds.items() if not v))
    else:
        conds = {}
        verdict = "Worse"
    res = {"preregistration_sha256": sha, "scored_seasons": [TEST[0], TEST[-1]], "results_read_through": CMP.THROUGH,
           "arms_scored": arms, "arms_missing": missing, "unit": "mLL per match; positive = the named candidate better",
           "primary": prim, "fp_vs_placebo": plac, "fpl_vs_rl": expo, "secondaries": secondaries,
           "secondaries_worse": worse, "falsification_stratum": falsification, "uneven_check": uneven,
           "fp_vs_r_s2": get("FP vs R_S2"), "r_s2_vs_reference": get("R_S2 vs reference"),
           "conditions": conds, "verdict": verdict,
           "harness_check": harness,
           "coefficients_2024": {n: {"stage1": models[n]["s1"][2024], "both": models[n]["s2"][2024]}
                                 for n in ["reference"] + arms},
           "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    CA.write_json(RESULTS / "results.json", res)
    with pd.option_context("display.width", 230, "display.max_rows", 200):
        print(t[["population", "comparison", "stage", "matches", "estimate", "lo", "hi", "p_better", "reading"]].round(3)
              .to_string(index=False))
    print("harness", harness)
    print("verdict:", verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
