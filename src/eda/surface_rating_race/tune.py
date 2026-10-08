"""Tune the surface offset of TrueSkill Through Time on 2013-2018 (design years only), the overall constants frozen.

Per tour, on the history up to 2018 (a pass's rows before a cut never depend on later rows: the leak-proof timeline):

    reference   the pass without offsets. Its overall forecast must equal the decided TTT's overall component
                (match_timing/ttt_timed.parquet, p_ttt_timed_overall), computed on the full history: the check that
                this study runs the decided TTT and its timeline exactly
    grid        sigma_o (the offset's prior deviation) x gamma_o (its drift per square-root year); the rule is the
                rating-systems study's: the lowest log loss on its evaluation matches of 2013-2018 (every level,
                qualifying included). Where the best lies on an edge of the grid (gamma_o = 0 is a natural bound) the
                grid is widened past it, up to three times

Also reported on the same matches, as design evidence: the best offset TTT against the decided TTT (the 30%/35% blend
of overall and surface-only chains) and against the overall chain alone, milli-log-loss with 95% intervals over
four-week blocks (positive = the offset TTT is better).

Writes data/studies/surface_rating_race/tuning.csv and tuning_choice.json.
Run: ./python.sh src/eda/surface_rating_race/tune.py [--workers 12]
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.rating_systems import common as RC  # noqa: E402
from src.eda.surface_rating_race import common as C  # noqa: E402
from src.eda.surface_rating_race import runs as RU  # noqa: E402
from src.eda.surface_rating_race import ttt_offset as TO  # noqa: E402

GRID = {"sigma_o": [0.15, 0.25, 0.35, 0.5], "gamma_o": [0.0, 0.05, 0.1, 0.2]}
MAX_WIDENINGS = 3


def job(spec: dict) -> dict:
    t0 = time.time()
    t, h = RU.load_history(spec["tour"], last_year=C.TUNE_YEARS[1])
    cfg = dict(RU.frozen_constants()[spec["tour"]], **spec.get("off", {}))
    o = RU.run_pass(h, cfg, offsets=spec["offsets"])
    mask = RC.tune_mask(h)
    out = {"tour": spec["tour"], "offsets": spec["offsets"], **spec.get("off", {}), "matches": int(mask.sum()),
           "match_id": t["match_id"].to_numpy()[mask], "dates": t["tournament_date"].to_numpy()[mask],
           "y": h["y"][mask]}
    if spec["offsets"]:
        out["p"] = TO.p_offset(o)[mask]
    else:
        p = TO.p_overall(o)
        ref = pd.read_parquet(C.TTT_TIMED).set_index("match_id").reindex(t["match_id"])
        gap = np.abs(p - ref["p_ttt_timed_overall"].to_numpy())
        early = (t["tournament_date"] < pd.Timestamp("2018-12-01")).to_numpy()
        out.update({"p": p[mask], "p_blend": ref["p_ttt_timed"].to_numpy()[mask],
                    "max_abs_gap_vs_decided_overall": float(np.nanmax(gap)),
                    "max_abs_gap_before_dec_2018": float(np.nanmax(gap[early])),
                    "rows_differing": int((gap > 1e-12).sum()), "rows": int(len(gap))})
    out["log_loss"] = RC.log_loss(out["p"], out["y"])
    out["seconds"] = round(time.time() - t0, 1)
    return out


def widen(rows: pd.DataFrame, tried: dict) -> dict:
    """New values past an edge where the best lies (gamma_o's 0 is a natural bound)."""
    best = rows.loc[rows["log_loss"].idxmin()]
    add = {}
    s = sorted(tried["sigma_o"])
    if best["sigma_o"] == s[-1]:
        add["sigma_o"] = [round(s[-1] * 1.5, 4)]
    elif best["sigma_o"] == s[0]:
        add["sigma_o"] = [round(s[0] / 1.5, 4)]
    g = sorted(tried["gamma_o"])
    if best["gamma_o"] == g[-1]:
        add["gamma_o"] = [round(g[-1] * 2.0, 4)]
    return add


def main() -> int:
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 12
    C.OUT.mkdir(parents=True, exist_ok=True)
    tried = {tour: {k: list(v) for k, v in GRID.items()} for tour in C.TOURS}
    specs = [{"tour": tour, "offsets": True, "off": {"sigma_o": s, "gamma_o": g}}
             for tour in C.TOURS for s in GRID["sigma_o"] for g in GRID["gamma_o"]]
    specs = [{"tour": tour, "offsets": False} for tour in C.TOURS] + specs
    specs.sort(key=lambda s: s["tour"] != "atp")             # the long tour first
    results, round_no = [], 0
    with ProcessPoolExecutor(max_workers=workers) as ex:
        while specs:
            futs = {ex.submit(job, s): s for s in specs}
            for f in as_completed(futs):
                r = f.result()
                results.append(r)
                extra = (f"gap vs decided overall {r['max_abs_gap_vs_decided_overall']:.2e} "
                         f"(before Dec 2018 {r['max_abs_gap_before_dec_2018']:.2e})" if not r["offsets"] else "")
                C.log(f"{r['tour']} offsets={r['offsets']} {r.get('sigma_o', '')} {r.get('gamma_o', '')}: "
                      f"log loss {r['log_loss']:.6f} ({r['seconds']:.0f} s) {extra}")
            specs = []
            if round_no >= MAX_WIDENINGS:
                break
            round_no += 1
            grid = pd.DataFrame([{k: r[k] for k in ("tour", "sigma_o", "gamma_o", "log_loss")}
                                 for r in results if r["offsets"]])
            for tour in C.TOURS:
                add = widen(grid[grid["tour"] == tour], tried[tour])
                for par, vals in add.items():
                    other = "gamma_o" if par == "sigma_o" else "sigma_o"
                    for v in vals:
                        for w in tried[tour][other]:
                            specs.append({"tour": tour, "offsets": True, "off": {par: v, other: w}})
                    tried[tour][par] += vals
                if add:
                    C.log(f"{tour}: best on an edge, widening {add}")
    grid = pd.DataFrame([{k: r.get(k) for k in ("tour", "offsets", "sigma_o", "gamma_o", "matches", "log_loss",
                                                 "seconds")} for r in results])
    grid.sort_values(["tour", "offsets", "sigma_o", "gamma_o"]).to_csv(C.OUT / "tuning.csv", index=False)
    choice = {"rule": "lowest log loss on the rating-systems study's evaluation matches of 2013-2018",
              "grid_start": GRID, "frozen_overall": RU.frozen_constants(),
              "key": "milli-log-loss; positive = the offset TTT (second named) is better; 95% intervals over "
                     "four-week blocks; spanning 0 = tie"}
    for tour in C.TOURS:
        ref = next(r for r in results if r["tour"] == tour and not r["offsets"])
        g = [r for r in results if r["tour"] == tour and r["offsets"]]
        best = min(g, key=lambda r: r["log_loss"])
        if not np.array_equal(ref["match_id"], best["match_id"]):
            raise RuntimeError("tuning rows differ between passes")
        ll_off, ll_over, ll_blend = (C.ll(p, best["y"]) for p in (best["p"], ref["p"], ref["p_blend"]))
        vs = {name: {k: float(v) for k, v in C.compare(b, ll_off, best["dates"]).items() if k in ("gain", "lo", "hi", "n")}
              for name, b in (("vs decided TTT (blend)", ll_blend), ("vs overall chain alone", ll_over))}
        s_vals, g_vals = sorted({r["sigma_o"] for r in g}), sorted({r["gamma_o"] for r in g})
        lls = np.array([r["log_loss"] for r in g])
        choice[tour] = {"sigma_o": best["sigma_o"], "gamma_o": best["gamma_o"], "log_loss": best["log_loss"],
                        "matches": best["matches"], "sigma_o_tried": s_vals, "gamma_o_tried": g_vals,
                        "on_edge": {"sigma_o": best["sigma_o"] in (s_vals[0], s_vals[-1]),
                                    "gamma_o": best["gamma_o"] == g_vals[-1]},
                        "settings_within_0_1_milli": int((lls - lls.min() < 1e-4).sum()), "settings": len(g),
                        "reference_check": {k: ref[k] for k in ("max_abs_gap_vs_decided_overall",
                                                                "max_abs_gap_before_dec_2018", "rows_differing", "rows")},
                        "log_loss_overall_alone": ref["log_loss"], "log_loss_decided_blend": float(np.mean(ll_blend)),
                        "design_evidence_2013_2018": vs}
    C.write_json(C.OUT / "tuning_choice.json", choice)
    C.log(f"chosen: { {t: (choice[t]['sigma_o'], choice[t]['gamma_o']) for t in C.TOURS} }")
    for tour in C.TOURS:
        C.log(f"{tour}: {choice[tour]['design_evidence_2013_2018']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
