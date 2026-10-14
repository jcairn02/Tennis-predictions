"""The harm checks of the level layer and of the men's 2026 Challenger data (docs/studies/level_layer_adoption/), with
the level-evidence study's own pairing (src/eda/lower_level_evidence/system_pairs.py: load_models, paired, populations;
compare.py's recipe: seeds 0-3, the per-tour calibration and stage 2's b fitted walk-forward on 2019 .. Y - 1, debut
seasons out, four-week blocks plus the seeds' variance, paired by seed).

    --layer       ON (the template with the layer) against OFF (the template without it), on the same tables:
                  seasons 2020-2024 (fits 2019-2024). The decision reading: men, both stages. Also reported (not
                  deciding): both tours, women, stage 1 alone, each season, the study's strata
    --candidate   NEW (the template with the layer on C0_men26) against ON: season 2026 (fits 2019-2026), the only
                  season the additions reach. The decision reading: men, both stages. Also: women (must be 0: the
                  additions are men's), stage 1 alone
    --holdback    the new instance (template_2026-10-10: the layer, the 2026 data, the indoor fill, the 57-input list)
                  against the holdback's control, the Pinnacle-first instance of 9 Oct (errata E1 of the adoption
                  decision; CLAUDE.md: "after each batch of adoptions"): seasons 2020-2024 (fits 2019-2024), so the 2026
                  data is not seen. The reading: both tours, both stages (adoption_read's primary). Rule
                  (adoption_read, kind "holdback"): keep the adopted changes unless harm, then bisect them; below
                  resolution (the plausible effect 0.10 smaller than the 95% half-width) and spanning 0, the control
                  cannot see the batch

The owner's rule for a repair or more data of a kind already used (9 Oct 2026): adopt unless the change shows harm,
i.e. worse by more than 0.10 mLL per match with the whole 95% interval below 0. Readings: "better"/"worse" when the
interval clears 0, else "unresolved" with P(better) (Phi of estimate / se). POSITIVE = THE FIRST-NAMED MODEL BETTER.
No edge credit. Writes data/studies/level_layer_adoption/results/<check>.csv and .json.
Run: ./python.sh src/eda/level_layer_adoption/harm.py --layer | --candidate | --holdback
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

from src.eda.level_layer_adoption import verify as V  # noqa: E402
from src.eda.lower_level_evidence import system_pairs as SP  # noqa: E402

OUT = V.STUDY / "results"
HARM = -0.10
INSTANCES = ROOT / "data" / "studies" / "current_best_model"
TEMPLATE = INSTANCES / "template_2026-10-10"
CONTROL = INSTANCES / "pinnacle_first_2026-10-09"          # the holdback's control (errata E1)
PLAUSIBLE_HOLDBACK = 0.10                                   # adoption_read.KINDS["holdback"]


def harm(r: dict) -> bool:
    return bool(np.isfinite(r["estimate"]) and r["estimate"] < HARM and r["hi"] < 0)


def holdback_decision(r: dict) -> dict:
    """adoption_read's holdback rule on one reading."""
    half = (r["hi"] - r["lo"]) / 2
    below = PLAUSIBLE_HOLDBACK < half
    blind = bool(below and r["lo"] <= 0 <= r["hi"])
    decision = ("bisect the adopted changes" if harm(r) else
                "below resolution: the control cannot see this batch" if blind else "keep the adopted changes")
    return {"half_width": half, "plausible": PLAUSIBLE_HOLDBACK, "below_resolution": bool(below), "blind": blind,
            "decision": decision}


def reading_rows(info, models, first: str, second: str, test, strata: bool, seasons: bool) -> pd.DataFrame:
    rows = []
    for tour, pop, mask in SP.populations(info, test, strata=strata, seasons=seasons):
        ids = info.index[mask]
        if not len(ids):
            continue
        for stage, label in (("s2", "both stages"), ("s1", "stage 1 alone")):
            if stage == "s1" and pop != "all":
                continue
            r = SP.paired(info, ids, SP.fc(models, second, stage, info, ids), SP.fc(models, first, stage, info, ids))
            rows.append(SP.row("2020-2024" if max(test) <= 2024 else "-".join(map(str, (min(test), max(test)))),
                               "harm check", first, second, label, tour, pop, r))
    return pd.DataFrame(rows)


def run(check: str) -> dict:
    if check == "layer":
        arms = {"ON": V.ON, "OFF": V.OFF}
        through, fits, test, first, second = 2024, tuple(range(2019, 2025)), tuple(range(2020, 2025)), "ON", "OFF"
    elif check == "holdback":
        arms = {"TEMPLATE": TEMPLATE, "CONTROL": CONTROL}
        through, fits, test = 2024, tuple(range(2019, 2025)), tuple(range(2020, 2025))
        first, second = "TEMPLATE", "CONTROL"
    else:
        arms = {"NEW": V.NEW, "ON": V.ON}
        through, fits, test, first, second = 2026, tuple(range(2019, 2027)), (2026,), "NEW", "ON"
    info, models = SP.load_models(arms, through, fits, test, speed_rule="zero", strict_price=False)
    t = reading_rows(info, models, first, second, test, strata=(check == "layer"), seasons=(check != "candidate"))
    OUT.mkdir(parents=True, exist_ok=True)
    t.to_csv(OUT / f"{check}.csv", index=False)
    tour = "both tours" if check == "holdback" else "men"
    prim = t[(t["tour"] == tour) & (t["population"] == "all") & (t["stage"] == "both stages")].iloc[0].to_dict()
    if check == "holdback":
        rule = holdback_decision(prim)
        decision = rule.pop("decision")
    else:
        rule, decision = {}, "adopt (no harm)" if not harm(prim) else "harm: not adopted"
    out = {"check": check, "first": first, "second": second, "positive": f"{first} better",
           "test_seasons": list(test), "fit_seasons": list(fits),
           f"primary_{tour.replace(' ', '_')}_both_stages": prim,
           "harm_rule": "worse by more than 0.10 mLL with the whole 95% interval below 0",
           "harm": harm(prim), **rule, "decision_by_the_rule": decision,
           "speed": models["_speed"],
           "price_differs_on": {k: v.get("price_differs_on", 0) for k, v in models.items() if not k.startswith("_")},
           "others": t[(t["population"] == "all")][["tour", "stage", "matches", "estimate", "lo", "hi", "p_better",
                                                    "reading"]].to_dict("records")}
    (OUT / f"{check}.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("check", f"primary_{tour.replace(' ', '_')}_both_stages", "harm",
                                          "decision_by_the_rule")}, indent=1, default=str))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--layer", action="store_true")
    g.add_argument("--candidate", action="store_true")
    g.add_argument("--holdback", action="store_true")
    a = ap.parse_args()
    run("layer" if a.layer else "holdback" if a.holdback else "candidate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
