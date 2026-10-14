"""M2, step 1 (plan.md, "Fixed at M1"): build an eligible member's frozen TabPFN deployment columns for every model-frame
season, 2013-2026, and register them for the TabPFN arms.

Reads no result. The 2025-2026 rows are built with the same frozen code; before registering, the build must reproduce,
exactly, the frozen screen column x and every deployment column on the 2013-2024 rows (the meta-auditor's checkpoint 1,
section 6.3, item 3: no constant moved).

Run: ./python.sh src/eda/feature_interactions/g5_build.py --hid B-INJ
"""
from __future__ import annotations

import importlib
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.feature_interactions import common as C  # noqa: E402
from src.eda.feature_interactions import screen_batch as B  # noqa: E402
from src.eda.feature_interactions.history import long_table  # noqa: E402
from src.eda.feature_interactions.panel import panel  # noqa: E402
from src.eda.feature_interactions.registry import register  # noqa: E402


def spec_of(hid: str) -> dict:
    for path in sorted(B.FEATURE_DIR.glob(B.FAMILY)):
        mod = importlib.import_module(f"src.eda.feature_interactions.features.{path.stem}")
        for spec in mod.HYPOTHESES:
            if spec["hid"] == hid:
                return spec
    raise KeyError(hid)


def same(a, b) -> bool:
    return bool(np.array_equal(np.asarray(a, float), np.asarray(b, float), equal_nan=True))


def main() -> int:
    warnings.simplefilter("ignore")
    hid = sys.argv[sys.argv.index("--hid") + 1]
    spec = spec_of(hid)
    L = long_table()
    P24 = panel(max_season=2024).drop(columns=["a_won"])
    P26 = panel(max_season=2026).drop(columns=["a_won"])
    r24 = B.evaluate(spec, P24.assign(**(spec["prepare"](P24, L) if spec.get("prepare") else {})))
    new26 = spec["prepare"](P26, L) if spec.get("prepare") else {}
    r26 = B.evaluate(spec, P26.assign(**new26))
    pos = pd.Series(np.arange(len(P26)), index=P26["match_id"].astype(str)).reindex(P24["match_id"].astype(str))
    pos = pos.to_numpy().astype(int)
    frozen = pd.read_csv(B.HYP / "hypothesis_table.csv").set_index("hid").loc[hid, "x_sha256"]
    checks = {"x_2024_build_matches_frozen_hash": B.sha_array(r24["x"]) == frozen,
              "x_2026_build_equals_2024_build_on_2013_2024": same(np.asarray(r26["x"], float)[pos], r24["x"])}
    for name, (arr, kind, partner) in r26["tabpfn"].items():
        checks[f"{name}_2026_equals_2024"] = same(np.asarray(arr, float)[pos], np.asarray(r24["tabpfn"][name][0], float))
    C.log(f"{hid}: checks {checks}")
    if not all(checks.values()):
        raise SystemExit(f"{hid}: the 2026 build does not reproduce the frozen 2013-2024 columns")
    frame = pd.DataFrame({"match_id": P26["match_id"].astype(str).to_numpy()})
    specs = {}
    for name, (arr, kind, partner) in r26["tabpfn"].items():
        frame[name] = np.asarray(arr, float)
        specs[name] = {"kind": kind, "desc": f"{hid} deployment column (frozen builder)"} | (
            {"partner": partner} if partner else {})
    family = hid.lower().replace("-", "")
    register(family, frame, specs)
    cov = {n: {int(s): round(float(np.isfinite(frame.loc[P26["season"].to_numpy() == s, n]).mean()), 3)
               for s in (2016, 2020, 2024, 2025, 2026)} for n in specs}
    C.write_json(C.OUT / "g5" / f"{family}_build.json", {"hid": hid, "columns": list(specs), "checks": checks,
                                                         "coverage_by_season": cov, "rows": int(len(frame))})
    C.log(f"registered {list(specs)} as family {family}; coverage {cov}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
