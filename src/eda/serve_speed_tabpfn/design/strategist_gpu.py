"""R1 design look of the integration strategist: the GPU cost of the proposed fits, from the logged durations of earlier
local TabPFN-3.5 runs of the same 58-input frame (feature interactions' and the rating race's runner logs). No result
is read.

Writes data/studies/serve_speed_tabpfn/design/strategist_gpu.json.
Run: ./python.sh src/eda/serve_speed_tabpfn/design/strategist_gpu.py
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = ROOT / "data" / "studies" / "serve_speed_tabpfn" / "design"
LOGS = [ROOT / "data" / "studies" / "feature_interactions" / "local_fits_model_16seeds.log",
        ROOT / "data" / "studies" / "feature_interactions" / "local_fits_binj_test.log",
        ROOT / "data" / "studies" / "surface_rating_race" / "local_fits_1.log",
        ROOT / "data" / "studies" / "surface_rating_race" / "local_fits_2.log",
        ROOT / "data" / "studies" / "surface_rating_race" / "local_fits_3.log"]
LINE = re.compile(r"\[\s*([\d.]+)s\]\s+(\w+?)__(\d{4})__seed(\d+)\.npz: (\d+) s")
OVERHEAD_S = 1.5             # wall seconds per fit beyond the fit itself (16-seed log: 29.3 wall vs 28.0 fit, per fit)
SAFETY = 1.5                 # the brief quotes 1-1.5 minutes per fit; the logs are faster: plan at 1.5 x the logs

# (arm, odds?, seasons, seeds): the proposal's fit plan (base fits with the odds are reused, never refitted)
PLAN = [("spd (A1)", True, range(2019, 2024), 4), ("spd (A1)", True, range(2024, 2027), 16),
        ("spd_raw (A2)", True, range(2019, 2024), 4), ("spd_raw (A2)", True, range(2024, 2027), 8),
        ("A3", True, range(2019, 2024), 4), ("A3", True, range(2024, 2027), 8),
        ("spd_noodds", False, range(2019, 2024), 4), ("spd_noodds", False, range(2024, 2027), 8),
        ("model_noodds seed 3", False, range(2019, 2024), 1), ("model_noodds seeds 3-7", False, range(2024, 2027), 5)]


def main() -> int:
    odds, noodds = defaultdict(list), defaultdict(list)
    for log in LOGS:
        for line in log.read_text(encoding="utf-8").splitlines():
            m = LINE.search(line)
            if m:
                arm, season, secs = m.group(2), int(m.group(3)), int(m.group(5))
                (noodds if arm.endswith("noodds") else odds)[season].append(secs)
    mean = {"odds": {s: sum(v) / len(v) for s, v in sorted(odds.items())},
            "noodds": {s: sum(v) / len(v) for s, v in sorted(noodds.items())}}
    rows, total = [], 0.0
    for arm, with_odds, seasons, seeds in PLAN:
        per = mean["odds" if with_odds else "noodds"]
        secs = seeds * sum(per[s] + OVERHEAD_S for s in seasons)
        total += secs
        rows.append({"arm": arm, "odds": with_odds, "seasons": f"{seasons[0]}-{seasons[-1]}", "seeds": seeds,
                     "fits": seeds * len(seasons), "seconds": round(secs)})
    out = {"mean_fit_seconds_by_season": {k: {s: round(v, 1) for s, v in d.items()} for k, d in mean.items()},
           "fits_logged": {"odds": sum(len(v) for v in odds.values()), "noodds": sum(len(v) for v in noodds.values())},
           "sweep_2019_2026_one_seed_seconds_odds": round(sum(mean["odds"][s] + OVERHEAD_S for s in range(2019, 2027))),
           "plan": rows, "plan_fits": sum(r["fits"] for r in rows), "plan_hours_at_logged_speed": round(total / 3600, 2),
           "plan_hours_with_safety": round(SAFETY * total / 3600, 2), "safety_factor": SAFETY}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "strategist_gpu.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
