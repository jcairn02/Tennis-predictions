"""The harm check of the rebuild of 16 Oct 2026 (docs/studies/men_lower_level_fill/; the rule fixed before any build or
reading, process log § 3, step 6): NEW (template_2026-10-16: the template on the day's tables with every accepted
package and the feed, the men's lower-level fill among them) against ON (template_2026-10-14, the current instance).
It covers everything that entered since ON was built: the men's fill, the two TennisLive packages, the feed's snapshot
20261014, the Tenerife date correction and the matches Tennis My Life has published since (the 14 Oct rule: "each
rebuild's harm check covers what entered since").

The scorer is the 10 Oct harm check's own, as the feed's check of 13 Oct used it (src/eda/data_gaps_2026/harm.py):
level_layer_adoption/harm.py's reading_rows on system_pairs.load_models; compare.py's recipe: seeds 0-3, the per-tour
calibration and stage 2's b fitted walk-forward on 2019 .. Y - 1, debut seasons out, four-week blocks plus the seeds'
variance, paired by seed; the speed rule "zero".

Primary: both tours, both stages, test seasons 2020-2026. Rule: harm = worse by more than 0.10 mLL per match with the
whole 95% interval below 0. Readings: "better"/"worse" when the interval clears 0, else "unresolved" with P(better).
POSITIVE = NEW BETTER. No edge credit. Also reported (not deciding): men, women, stage 1 alone, each season, and the
two periods 2020-2024 and 2025-2026.
Writes data/studies/men_lower_level_fill/harm/new_vs_on.csv and .json.
Run: ./python.sh src/eda/men_lower_level_fill/harm.py --new data/studies/current_best_model/template_2026-10-16
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

OUT = ROOT / "data" / "studies" / "men_lower_level_fill" / "harm"
ON = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-14"
FITS = tuple(range(2019, 2027))
TEST = tuple(range(2020, 2027))
PERIODS = {"2020-2024": tuple(range(2020, 2025)), "2025-2026": (2025, 2026)}


def run(new: Path) -> dict:
    arms = {"NEW": Path(new), "ON": ON}
    info, models = SP.load_models(arms, 2026, FITS, TEST, speed_rule="zero", strict_price=False)
    t = LH.reading_rows(info, models, "NEW", "ON", TEST, strata=False, seasons=True)
    parts = [t]
    for name, seasons in PERIODS.items():
        p = LH.reading_rows(info, models, "NEW", "ON", seasons, strata=False, seasons=False)
        p["period"] = name
        parts.append(p)
    import pandas as pd
    t = pd.concat(parts, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT / "new_vs_on.csv", index=False)
    full = "-".join(map(str, (min(TEST), max(TEST))))
    prim = t[(t["period"] == full) & (t["tour"] == "both tours") & (t["population"] == "all")
             & (t["stage"] == "both stages")].iloc[0].to_dict()
    out = {"check": "rebuild of 16 Oct 2026", "first": "NEW", "second": "ON", "positive": "NEW better",
           "new": str(new), "on": str(ON), "test_seasons": list(TEST), "fit_seasons": list(FITS),
           "primary_both_tours_both_stages": prim,
           "harm_rule": "worse by more than 0.10 mLL with the whole 95% interval below 0",
           "harm": LH.harm(prim),
           "decision_by_the_rule": "switch to NEW (no harm)" if not LH.harm(prim) else "harm: no switch; the owner decides",
           "speed": models["_speed"],
           "price_differs_on": {k: v.get("price_differs_on", 0) for k, v in models.items() if not k.startswith("_")},
           "others": t[["period", "tour", "stage", "population", "matches", "estimate", "lo", "hi", "p_better",
                        "reading"]].to_dict("records")}
    (OUT / "new_vs_on.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("primary_both_tours_both_stages", "harm", "decision_by_the_rule")}, indent=1,
                     default=str))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--new", required=True, help="the NEW instance folder (built, post-built, fits seeds 0-3 2019-2026)")
    a = ap.parse_args()
    run(Path(a.new))
    return 0


if __name__ == "__main__":
    sys.exit(main())
