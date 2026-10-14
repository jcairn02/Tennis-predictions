"""Checks of the level layer in the current best model (docs/studies/level_layer_adoption/; docs/decisions/
2026-10-10-level-evidence-layer.md), on the builds of 10 Oct 2026. Inputs only: no result is read.

The builds (build_template.sh; the live tables equal the frozen reference's, so all are on the reference's tables):
    OFF   the template without the layer (LLE_LAYER unset): data/studies/level_layer_adoption/template_off/
    ON    the template with the official config: data/studies/current_best_model/level_layer_2026-10-10/
    NEW   ON's recipe on C0_men26 (the men's 2026 Challenger and Challenger-qualifying additions):
          data/studies/level_layer_adoption/candidate_men26/
Each folder keeps the chain's own frame (model_frame_chain.parquet: the books' average odds input, all 58 columns)
beside the template's (model_frame.parquet after odds_input.py --apply and template_inputs.py --apply).

    --identity    OFF's chain frame against the frozen reference's frame: every input exactly, but `indoor`, which
                  carries the decided fill (it must differ only where the reference's is missing); then OFF's template
                  frame against the current template's inputs on these tables (the indoor-fill study's arm: the
                  Pinnacle-first odds, the fill, 57 inputs): every column exactly
    --fidelity    ON's chain frame against the study's SYS frame: every input exactly, but `indoor` (the fill, as
                  above) and `ios_points_short` (switched off: it must equal the reference's); the 21 surface-solver
                  inputs within 1e-12 (the study's documented rounding; the bit-exact count kept)
    --gates       the study's own gates on ON against OFF (system_gates: G2 invariance, G3 direction with the ENV
                  rule, G5 the builders' probes in ON's sandbox), the tuned constants and the Stage B pin. The OFF and
                  ON sandboxes were deleted on 14 Oct 2026; the 7 files --gates reads from them are byte-for-byte copies
                  in data/studies/level_layer_adoption/sandbox_extracts/ (same layout; its README and manifest.json)
    --candidate   NEW against ON: every input exact on matches the additions cannot reach (women; men before the
                  first addition counts on the match clock); the men's 2026 changes by input
Writes data/studies/level_layer_adoption/checks/<check>.json (and .csv).
Run: ./python.sh src/eda/level_layer_adoption/verify.py --identity | --fidelity | --gates | --candidate
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

from src.eda.lower_level_evidence import common as LC  # noqa: E402
from src.eda.lower_level_evidence import level_layer as L  # noqa: E402
from src.eda.lower_level_evidence import system_gates as G  # noqa: E402

STUDY = ROOT / "data" / "studies" / "level_layer_adoption"
OFF = STUDY / "template_off"
ON = ROOT / "data" / "studies" / "current_best_model" / "level_layer_2026-10-10"
NEW = STUDY / "candidate_men26"
EXTRACTS = STUDY / "sandbox_extracts"        # OFF's and ON's sandboxes (tnr_lyr_off, tnr_lyr_on), deleted 14 Oct 2026
SANDBOX = {"OFF": EXTRACTS / "tnr_lyr_off", "ON": EXTRACTS / "tnr_lyr_on",
           "NEW": Path("C:/Users/zerom/tnr_lyr_new")}
SYS = ROOT / "data" / "studies" / "lower_level_evidence" / "system" / "arms" / "SYS" / "model_frame.parquet"
TEMPLATE_NOW = ROOT / "data" / "studies" / "indoor_fill" / "arm" / "model_frame.parquet"
C0 = STUDY / "stage0" / "C0_men26"
CHECKS = STUDY / "checks"
CHAIN = "model_frame_chain.parquet"
SOLVER_TOL = 1e-7          # the joint solves' convergence noise between two builds (solver_tolerance.py; candidate())
ID_COLS = ["match_id", "tour", "season", "tournament_date", "tabpfn_split", "debut_season"]


def write(name: str, out: dict, table: pd.DataFrame | None = None) -> dict:
    CHECKS.mkdir(parents=True, exist_ok=True)
    G.write_json(CHECKS / f"{name}.json", out)
    if table is not None and len(table):
        table.to_csv(CHECKS / f"{name}.csv", index=False)
    print(json.dumps({k: v for k, v in out.items() if k not in ("inputs_table",)}, indent=1, default=str)[:6000])
    return out


def frames(a: Path, b: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    x, y = G.inputs_of(a), G.inputs_of(b)
    if not (len(x) == len(y) and (x["match_id"].to_numpy() == y["match_id"].to_numpy()).all()):
        raise SystemExit(f"{a} and {b}: not the same matches in the same order")
    return x, y


def identifiers(x: pd.DataFrame, y: pd.DataFrame) -> dict:
    out = {}
    for c in ID_COLS:
        if c in x and c in y:
            out[c] = bool(x[c].astype(str).equals(y[c].astype(str)))
    return out


def compare(x: pd.DataFrame, y: pd.DataFrame, names=None, tol: dict | None = None) -> pd.DataFrame:
    """Per input: G.diff_stats of x against y (exact = largest difference 0 and the same missing cells), and within
    the input's tolerance where one is given (the bit-exact verdict kept)."""
    names = names or [n for n in G.input_names(x) if f"in_{n}" in y]
    rows = []
    for n in names:
        st = G.diff_stats(x[f"in_{n}"], y[f"in_{n}"])
        st["bit_exact"] = st["exact"]
        if tol and n in tol:
            st["tolerance"] = tol[n]
            st["exact"] = bool(st["same_missing"] and st["largest_difference"] <= tol[n])
        rows.append({"input": n, **st})
    return pd.DataFrame(rows)


def indoor_check(chain: pd.DataFrame, before: pd.DataFrame) -> dict:
    """The decided fill: equal wherever the earlier frame had a value; the rest is what the rule filled."""
    a = chain["in_indoor"].to_numpy(float)
    b = before["in_indoor"].to_numpy(float)
    had = np.isfinite(b)
    return {"equal_where_it_had_a_value": bool(np.array_equal(a[had], b[had])),
            "filled": int((~had & np.isfinite(a)).sum()), "still_missing": int((~np.isfinite(a)).sum()),
            "filled_by_tour": {t: int((~had & np.isfinite(a) & (chain["tour"].to_numpy() == t)).sum())
                               for t in ("atp", "wta")}}


# ------------------------------------------------------------------------------------------------

def identity() -> dict:
    ref, off = frames(LC.FRAME, OFF / CHAIN)
    t = compare(ref, off)
    t_other = t[t["input"] != "indoor"]
    part1 = {"what": "OFF's chain frame (layer unset) against the frozen reference's frame",
             "matches": int(len(ref)), "identifiers_equal": identifiers(ref, off),
             "inputs": int(len(t)), "inputs_exact_but_indoor": int(t_other["exact"].sum()),
             "not_exact": t.loc[~t["exact"], ["input", "rows_changed", "largest_difference"]].to_dict("records"),
             "indoor": indoor_check(off, ref)}
    part1["pass"] = bool(all(part1["identifiers_equal"].values()) and t_other["exact"].all()
                         and part1["indoor"]["equal_where_it_had_a_value"] and part1["indoor"]["still_missing"] == 0)
    now, tmpl = frames(TEMPLATE_NOW, OFF / "model_frame.parquet")
    names = [n for n in G.input_names(now)]
    t2 = compare(now, tmpl, names)
    extra = {}
    for c in ("p_mkt", "odds_input", "p_mkt_avg"):
        if c in now and c in tmpl:
            extra[c] = bool(now[c].astype(str).equals(tmpl[c].astype(str)))
    li = json.loads((TEMPLATE_NOW.parent / "model_inputs.json").read_text(encoding="utf-8"))
    lo = json.loads((OFF / "model_inputs.json").read_text(encoding="utf-8"))
    part2 = {"what": "OFF's template frame (Pinnacle-first odds, 57 inputs) against the current template's inputs on "
                     "these tables (data/studies/indoor_fill/arm/: the Pinnacle-first instance's frame with the indoor "
                     "fill, A2's 57-input list)",
             "identifiers_equal": identifiers(now, tmpl), "columns_in_both": int(len(t2)),
             "exact": int(t2["exact"].sum()),
             "not_exact": t2.loc[~t2["exact"], ["input", "rows_changed", "largest_difference"]].to_dict("records"),
             "price_columns_equal": extra,
             "input_lists_equal": [d["name"] for d in li["inputs"]] == [d["name"] for d in lo["inputs"]],
             "inputs_listed": len(lo["inputs"])}
    part2["pass"] = bool(all(part2["identifiers_equal"].values()) and t2["exact"].all() and all(extra.values())
                         and part2["input_lists_equal"])
    out = {"check": "identity", "chain_vs_reference": part1, "template_vs_current_template": part2,
           "pass": bool(part1["pass"] and part2["pass"])}
    return write("identity", out, pd.concat([t.assign(against="reference"), t2.assign(against="current template")]))


def fidelity() -> dict:
    sys_, on = frames(SYS, ON / CHAIN)
    ref = G.inputs_of(LC.FRAME)
    tol = {n: G.SURFACE_TOL for n in G.SURFACE_SOLVER}
    t = compare(sys_, on, tol=tol)
    skip = {"indoor", "ios_points_short"}
    rest = t[~t["input"].isin(skip)]
    ips = G.diff_stats(ref["in_ios_points_short"], on["in_ios_points_short"])
    out = {"check": "fidelity", "what": "ON's chain frame (the official config) against the study's SYS frame, on the "
                                       "frozen reference's tables",
           "matches": int(len(on)), "identifiers_equal": identifiers(sys_, on),
           "inputs_compared": int(len(rest)), "exact": int(rest["exact"].sum()),
           "bit_exact": int(rest["bit_exact"].sum()),
           "within_tolerance_only": rest.loc[rest["exact"] & ~rest["bit_exact"],
                                             ["input", "rows_changed", "largest_difference"]].to_dict("records"),
           "not_exact": rest.loc[~rest["exact"], ["input", "rows_changed", "largest_difference"]].to_dict("records"),
           "indoor": indoor_check(on, sys_),
           "ios_points_short_switched_off_equals_reference": ips,
           "ios_points_short_vs_sys": G.diff_stats(sys_["in_ios_points_short"], on["in_ios_points_short"])}
    out["pass"] = bool(all(out["identifiers_equal"].values()) and rest["exact"].all()
                       and out["indoor"]["equal_where_it_had_a_value"] and ips["exact"])
    return write("fidelity", out, t)


def gates() -> dict:
    cfg_path = ON / "level_layer" / "build_config.json"
    cfg = L.load_config(cfg_path)
    off, on = frames(OFF / CHAIN, ON / CHAIN)
    g2, t2 = G.g2("ON", off, on, cfg)
    g3, t3 = G.g3("ON", off, on, cfg)
    g5 = G.g5("ON", SANDBOX["ON"])
    rc = json.loads(L.Path(G.SA.REF_CONSTANTS).read_text(encoding="utf-8"))
    const = {}
    for name, folder in (("OFF", OFF), ("ON", ON)):
        s1 = json.loads((folder / "chain_outputs" / "stage1_baselines_summary.json").read_text(encoding="utf-8"))
        pm = json.loads((folder / "chain_outputs" / "surface_elo_pieces_pieces_meta.json").read_text(encoding="utf-8"))
        sb = SANDBOX[name] / "data" / "studies"
        s3 = json.loads((sb / "predictability_diagnostic" / "stage3_ratings_summary.json").read_text(encoding="utf-8"))
        ref3 = {t: json.loads(v.replace("'", '"')) for t, v in rc["stage3_chosen"].items()}
        sbj = json.loads((sb / "ufc_ideas" / "stageB_adj_summary.json").read_text(encoding="utf-8"))
        got = {f"{c['tour']}|{c['stat']}": {k: float(c[k]) if k != "tau" else int(c[k])
                                            for k in ("h1", "K1", "tau", "h3", "K3")} for c in sbj["chosen"]}
        const[name] = {"stage1_chosen_equal": s1["chosen"] == rc["stage1_chosen"],
                       "offset_constants_equal": pm["offset_constants"] == rc["offset_constants"],
                       "stage3_chosen_equal": all({k: float(x) for k, x in s3["chosen"][t].items()}
                                                  == {k: float(x) for k, x in ref3[t].items()} for t in s3["chosen"]),
                       "stageB_constants_used_equal_reference": got == rc["stageB_chosen"]}
    calls = ON / "level_layer" / "layer_calls" / "layer_calls.jsonl"
    recs = [json.loads(x) for x in calls.read_text(encoding="utf-8").splitlines()] if calls.exists() else []
    pins = [r for r in recs if r.get("hook") == "pin"]
    hooks = sorted({r.get("hook") for r in recs})
    pin = {"pin_records": len(pins), "tuned_equals_reference_in_this_build": pins[-1]["tuned_equals_reference"]
           if pins else None, "hooks_recorded": hooks,
           "layer_sha256_in_records": sorted({r.get("layer_sha256") for r in recs})}
    out = {"check": "gates", "config": str(cfg_path), "G2": g2, "G3": g3, "G5": g5, "constants": const, "pin": pin}
    out["pass"] = bool(g2["pass"] and g3["pass"] and g5["pass"] and all(all(v.values()) for v in const.values())
                       and pins)
    write("gates", out, None)
    t2.to_csv(CHECKS / "gates_G2.csv", index=False)
    t3.to_csv(CHECKS / "gates_G3.csv", index=False)
    return out


def candidate() -> dict:
    on, new = frames(ON / CHAIN, NEW / CHAIN)
    m = pd.read_parquet(C0 / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_date"])
    ref_ids = set(pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet", columns=["match_id"])["match_id"])
    added = m[~m["match_id"].isin(ref_ids)]
    lay = pd.read_parquet(C0 / "box_layers.parquet") if (C0 / "box_layers.parquet").exists() else pd.DataFrame()
    completed = set(lay.loc[lay["applied"].astype(bool), "match_id"]) if len(lay) else set()
    touched = pd.concat([added[["match_id", "tour"]], m[m["match_id"].isin(completed)][["match_id", "tour"]]])
    tm = pd.read_parquet(C0 / "timing.parquet", columns=["match_id", "es", "lf"]).set_index("match_id")
    first_count = (tm["lf"].reindex(touched["match_id"]).to_numpy(float) + 1.0)
    first = pd.Series(first_count, index=touched["tour"].to_numpy()).groupby(level=0).min()
    es = tm["es"].reindex(on["match_id"]).to_numpy(float)
    fc = first.reindex(on["tour"].to_numpy()).to_numpy(float)
    unreachable = np.where(np.isnan(fc), True, es < fc)       # women: no addition at all
    tol = {n: G.SURFACE_TOL for n in G.SURFACE_SOLVER}
    t_un = compare(on[unreachable], new[unreachable], tol=tol)
    women = on["tour"].to_numpy() == "wta"
    t_w = compare(on[women], new[women], tol=tol)
    men26 = (on["tour"].to_numpy() == "atp") & ~unreachable
    t_m = compare(on[men26], new[men26])
    # added after the first run of this check (10 Oct 2026, 14:13 PDT), on the evidence of solver_tolerance.py: the
    # surface solver's PCG stops at a relative residual of 1e-8, and the two builds' solves of the same rows differ by up
    # to 4.2e-8 at it and 8.2e-12 at 1e-13. So the joint-solve inputs are also judged within SOLVER_TOL; the strict
    # verdict is kept beside it
    solver_tol = {n: SOLVER_TOL for n in tuple(G.SURFACE_SOLVER) + ("ios_points_short",)}
    t_un_tol = compare(on[unreachable], new[unreachable], tol=solver_tol)
    out = {"check": "candidate", "what": "NEW (C0_men26, the layer) against ON (the reference's tables, the layer)",
           "additions": int(len(added)), "completions": int(len(completed)),
           "first_addition_counts_from": {t: str(np.datetime64(int(v), "D")) for t, v in first.items()},
           "unreachable_matches": int(unreachable.sum()),
           "unreachable_exact": bool(t_un["exact"].all()),
           "unreachable_not_exact": t_un.loc[~t_un["exact"], ["input", "rows_changed", "largest_difference"]]
           .to_dict("records"),
           "unreachable_exact_but_joint_solves_within_solver_tolerance": bool(t_un_tol["exact"].all()),
           "solver_tolerance": SOLVER_TOL, "solver_tolerance_evidence": "checks/solver_tolerance.json",
           "unreachable_non_joint_solve_inputs_bit_exact": bool(t_un.loc[~t_un["input"].isin(list(solver_tol)),
                                                                         "bit_exact"].all()),
           "women_matches": int(women.sum()), "women_exact": bool(t_w["exact"].all()),
           "men_reachable_matches": int(men26.sum()),
           "men_reachable_changed_by_input": t_m.set_index("input")["rows_changed"].astype(int).to_dict()}
    out["pass_strict"] = bool(out["unreachable_exact"] and out["women_exact"])
    out["pass"] = bool(out["unreachable_exact_but_joint_solves_within_solver_tolerance"] and out["women_exact"]
                       and out["unreachable_non_joint_solve_inputs_bit_exact"])
    return write("candidate", out, t_m)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    for k in ("identity", "fidelity", "gates", "candidate"):
        g.add_argument(f"--{k}", action="store_true")
    a = ap.parse_args()
    fn = {"identity": identity, "fidelity": fidelity, "gates": gates, "candidate": candidate}
    res = next(fn[k]() for k in fn if getattr(a, k))
    return 0 if res.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
