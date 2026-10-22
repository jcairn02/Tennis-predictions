"""A retrain's harm check (the owner, 20 Oct 2026; docs/studies/in_season_retrain/): the NEW instance against ON, the
instance in use when the retrain started, by the rebuild of 16 Oct's check (src/eda/men_lower_level_fill/harm.py) with
ON a parameter instead of a fixed folder. It covers everything that entered since ON was built (the 14 Oct rule: "each
rebuild's harm check covers what entered since"). It reads the walk-forward fits (the season rule) of both, never the
production fit: the in-season rows are the guard's (in_season_retrain/check.py), not this check's.

The scorer: level_layer_adoption/harm.py's reading_rows on lower_level_evidence/system_pairs.load_models (seeds 0-3, the
per-tour calibration and stage 2's b fitted walk-forward on 2019 .. Y - 1, debut seasons out, four-week blocks plus the
seeds' variance, paired by seed; the speed rule "zero"). Primary: both tours, both stages, test seasons 2020 .. the
last. Rule: harm = worse by more than 0.10 mLL per match with the whole 95% interval below 0. POSITIVE = NEW BETTER.
No edge credit. Also reported (not deciding): men, women, stage 1, each season, 2020-2024 and 2025 on.
Writes <new>/harm_vs_<on>.csv and .json.

    ./python.sh src/eda/in_season_retrain/harm.py --new <instance> [--on <instance>] [--last 2026]
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

INSTANCES = ROOT / "data" / "studies" / "current_best_model"


def run(new: Path, on: Path, last: int) -> dict:
    import pandas as pd
    fits, test = tuple(range(2019, last + 1)), tuple(range(2020, last + 1))
    periods = {"2020-2024": tuple(range(2020, 2025)), f"2025-{last}": tuple(range(2025, last + 1))}
    info, models = SP.load_models({"NEW": new, "ON": on}, last, fits, test, speed_rule="zero", strict_price=False)
    parts = [LH.reading_rows(info, models, "NEW", "ON", test, strata=False, seasons=True)]
    for name, seasons in periods.items():
        p = LH.reading_rows(info, models, "NEW", "ON", seasons, strata=False, seasons=False)
        p["period"] = name
        parts.append(p)
    t = pd.concat(parts, ignore_index=True)
    stem = new / f"harm_vs_{on.name}"
    t.to_csv(stem.with_suffix(".csv"), index=False)
    full = f"{min(test)}-{max(test)}"
    prim = t[(t["period"] == full) & (t["tour"] == "both tours") & (t["population"] == "all")
             & (t["stage"] == "both stages")].iloc[0].to_dict()
    out = {"check": f"retrain {new.name} against {on.name}", "first": "NEW", "second": "ON", "positive": "NEW better",
           "new": str(new), "on": str(on), "test_seasons": list(test), "fit_seasons": list(fits),
           "primary_both_tours_both_stages": prim,
           "harm_rule": "worse by more than 0.10 mLL with the whole 95% interval below 0", "harm": LH.harm(prim),
           "decision_by_the_rule": "switch to NEW (no harm)" if not LH.harm(prim) else "harm: no switch; the owner decides",
           "speed": models["_speed"],
           "others": t[["period", "tour", "stage", "population", "matches", "estimate", "lo", "hi", "p_better",
                        "reading"]].to_dict("records")}
    stem.with_suffix(".json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("primary_both_tours_both_stages", "harm", "decision_by_the_rule")}, indent=1,
                     default=str))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--new", required=True, help="the NEW instance (built, post-built, fits seeds 0-3 2019 .. last)")
    ap.add_argument("--on", help="the instance compared against (default: the one the daily pipeline uses now)")
    ap.add_argument("--last", type=int, default=2026, help="the last fitted and scored season")
    a = ap.parse_args()
    new = Path(a.new) if Path(a.new).is_absolute() else ROOT / a.new
    if a.on:
        on = Path(a.on) if Path(a.on).is_absolute() else ROOT / a.on
    else:
        from src.pipeline.train import active_instance
        on = active_instance()
    if new.resolve() == on.resolve():
        raise SystemExit("NEW and ON are the same instance")
    r = run(new, on, a.last)
    return 0 if not r["harm"] else 3


if __name__ == "__main__":
    sys.exit(main())
