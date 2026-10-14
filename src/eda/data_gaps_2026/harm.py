"""The lower-level feed's harm check (docs/studies/data_gaps_2026/; the rule fixed before any build or reading, process
log § 3 addendum of 13 Oct 2026, 16:54): FEED (the template recipe on the frozen reference's tables plus the feed's
first snapshot) against ON (the current instance, template_2026-10-10: the same recipe plus the 10 Oct package), with
the 10 Oct harm check's own scorer (src/eda/level_layer_adoption/harm.py: reading_rows, on system_pairs.load_models;
compare.py's recipe: seeds 0-3, the per-tour calibration and stage 2's b fitted walk-forward on 2019 .. Y - 1, debut
seasons out, four-week blocks plus the seeds' variance, paired by seed; the speed rule "zero").

Primary: both tours, both stages, test seasons 2025-2026 (the seasons the additions reach). Rule: harm = worse by more
than 0.10 mLL per match with the whole 95% interval below 0. Readings: "better"/"worse" when the interval clears 0,
else "unresolved" with P(better). POSITIVE = FEED BETTER. No edge credit.
Also reported (not deciding): men, women, stage 1 alone, each season.
The gate before scoring (--gate): FEED's inputs equal ON's on every match the additions cannot reach (gate()).
Writes data/studies/data_gaps_2026/harm/feed.csv and .json (and gate.json).
Run: ./python.sh src/eda/data_gaps_2026/harm.py --feed <the FEED instance folder> --gate <the derived candidate>
     ./python.sh src/eda/data_gaps_2026/harm.py --feed <the FEED instance folder>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.level_layer_adoption import harm as LH  # noqa: E402
from src.eda.lower_level_evidence import system_pairs as SP  # noqa: E402

OUT = ROOT / "data" / "studies" / "data_gaps_2026" / "harm"
ON = LH.TEMPLATE                                          # data/studies/current_best_model/template_2026-10-10
FITS = tuple(range(2019, 2027))
TEST = (2025, 2026)


def gate(feed: Path, cand: Path) -> dict:
    """Before scoring (the 10 Oct candidate check's rule, level_layer_adoption/verify.candidate): FEED's chain inputs
    equal ON's on every match the additions cannot reach, i.e. whose earliest start (es) comes before the first day any
    addition or completion of its tour counts (its lf + 1), with the joint solves' inputs within the solver's tolerance
    and every other input bit for bit. cand: the derived candidate (its Stage 0, timeline and box layers)."""
    import numpy as np
    import pandas as pd
    from src.eda.level_layer_adoption import verify as V
    from src.eda.lower_level_evidence import common as LC
    from src.eda.lower_level_evidence import system_gates as G
    on, new = V.frames(ON / V.CHAIN, Path(feed) / V.CHAIN)
    m = pd.read_parquet(cand / "stage0_matches.parquet", columns=["match_id", "tour"])
    ref_ids = set(pd.read_parquet(LC.STAGE0_DIR / "stage0_matches.parquet", columns=["match_id"])["match_id"])
    lay = pd.read_parquet(cand / "box_layers.parquet") if (cand / "box_layers.parquet").exists() else pd.DataFrame()
    completed = set(lay.loc[lay["applied"].astype(bool), "match_id"]) if len(lay) else set()
    touched = m[~m["match_id"].isin(ref_ids) | m["match_id"].isin(completed)]
    tm = pd.read_parquet(cand / "timing.parquet", columns=["match_id", "es", "lf"]).set_index("match_id")
    first = pd.Series(tm["lf"].reindex(touched["match_id"]).to_numpy(float) + 1.0,
                      index=touched["tour"].to_numpy()).groupby(level=0).min()
    es = tm["es"].reindex(on["match_id"]).to_numpy(float)
    fc = first.reindex(on["tour"].to_numpy()).to_numpy(float)
    unreachable = np.where(np.isnan(fc), True, es < fc)
    solver_tol = {n: V.SOLVER_TOL for n in tuple(G.SURFACE_SOLVER) + ("ios_points_short",)}
    t_strict = V.compare(on[unreachable], new[unreachable])
    t_tol = V.compare(on[unreachable], new[unreachable], tol=solver_tol)
    reach = V.compare(on[~unreachable], new[~unreachable])
    out = {"check": "gate", "what": "FEED against ON on the matches the additions cannot reach",
           "first_addition_counts_from": {t: str(np.datetime64(int(v), "D")) for t, v in first.items()},
           "unreachable_matches": int(unreachable.sum()), "reachable_matches": int((~unreachable).sum()),
           "unreachable_bit_exact": bool(t_strict["exact"].all()),
           "unreachable_within_solver_tolerance": bool(t_tol["exact"].all()),
           "unreachable_non_joint_solve_inputs_bit_exact": bool(t_strict.loc[~t_strict["input"].isin(list(solver_tol)),
                                                                             "bit_exact"].all()),
           "unreachable_not_exact": t_strict.loc[~t_strict["exact"], ["input", "rows_changed", "largest_difference"]]
           .to_dict("records"),
           "reachable_changed_by_input": reach.set_index("input")["rows_changed"].astype(int).to_dict()}
    out["pass"] = bool(out["unreachable_within_solver_tolerance"] and out["unreachable_non_joint_solve_inputs_bit_exact"])
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "gate.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "reachable_changed_by_input"}, indent=1, default=str))
    return out


def run(feed: Path) -> dict:
    arms = {"FEED": Path(feed), "ON": ON}
    info, models = SP.load_models(arms, 2026, FITS, TEST, speed_rule="zero", strict_price=False)
    t = LH.reading_rows(info, models, "FEED", "ON", TEST, strata=False, seasons=True)
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT / "feed.csv", index=False)
    prim = t[(t["tour"] == "both tours") & (t["population"] == "all") & (t["stage"] == "both stages")].iloc[0].to_dict()
    out = {"check": "feed", "first": "FEED", "second": "ON", "positive": "FEED better", "feed": str(feed),
           "on": str(ON), "test_seasons": list(TEST), "fit_seasons": list(FITS),
           "primary_both_tours_both_stages": prim,
           "harm_rule": "worse by more than 0.10 mLL with the whole 95% interval below 0",
           "harm": LH.harm(prim), "decision_by_the_rule": "adopt (no harm)" if not LH.harm(prim) else "harm: not adopted",
           "speed": models["_speed"],
           "price_differs_on": {k: v.get("price_differs_on", 0) for k, v in models.items() if not k.startswith("_")},
           "others": t[["period", "tour", "stage", "population", "matches", "estimate", "lo", "hi", "p_better",
                        "reading"]].to_dict("records")}
    (OUT / "feed.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("primary_both_tours_both_stages", "harm", "decision_by_the_rule")}, indent=1,
                     default=str))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--feed", required=True, help="the FEED instance folder (built, post-built, fits seeds 0-3)")
    ap.add_argument("--gate", metavar="CANDIDATE", help="only the gate before scoring, against the derived candidate")
    a = ap.parse_args()
    if a.gate:
        return 0 if gate(Path(a.feed), Path(a.gate))["pass"] else 1
    run(Path(a.feed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
