"""The candidate: the current best model with the indoor input filled, on the frozen tables of 8 Oct 2026.

The base is the lean review's arm A2: the Pinnacle-first instance's frame (data/studies/current_best_model/
pinnacle_first_2026-10-09/, the reference's tables with the decided odds input) without ios_points_short, the decided 57
inputs, with fits for 2019-2024, seeds 0-3, fed the close ("td") and Pinnacle's opening line ("open"). The candidate is
that frame with in_indoor replaced by the rule (status.py) and nothing else: so the paired comparison A2 against it
measures the fill alone.

Checks before writing (no result is read):
    * every other column equals the instance's, value for value;
    * every men's value the frame had is unchanged; what the rule adds is the men's 2026 US Open (127 matches) and every
      women's match; no match is left unknown;
    * the chain's own builder (tabpfn_thinking/build_frame.indoor_codes, the code build() runs since 9 Oct 2026) gives
      the same column on these matches, and with --indoor-men-only the instance's column (--chain-check). build() itself
      cannot run on the repository's tables: its Stage 4 pool predates the Stage 0 of 8 Oct, which the chain rebuilds
      first in its sandbox.

Writes data/studies/indoor_fill/arm/model_frame.parquet, model_inputs.json (A2's list) and arm.json.
Run: ./python.sh src/eda/indoor_fill/arm.py [--chain-check]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.indoor_fill import status as ST  # noqa: E402
from src.eda.lean_review import common as L  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402

OUT = ROOT / "data" / "studies" / "indoor_fill"
ARM = OUT / "arm"
BASE_INPUTS = L.arm_dir("A2") / "model_inputs.json"


def same(a, b) -> bool:
    return bool(np.array_equal(np.asarray(a, dtype="float64"), np.asarray(b, dtype="float64"), equal_nan=True))


def chain_check(frame: pd.DataFrame, rule: np.ndarray, old: np.ndarray) -> dict:
    """The frame builder's indoor column on these matches, from the pool columns it reads (match_id, tour, group) and
    Stage 0's rows in the same order: the rule by default, the instance's column with men_only."""
    from src.eda.tabpfn_thinking import build_frame as BF
    pool = pd.DataFrame({"match_id": frame["match_id"].to_numpy(), "tour": frame["tour"].to_numpy(),
                         "group": frame["in_level"].map({0.0: "GS", 1.0: "FIN", 2.0: "T1000", 3.0: "T500",
                                                         4.0: "T250"}).to_numpy()})
    m = ST.stage0_rows(levels=None).set_index("match_id").reindex(pool["match_id"]).reset_index()
    out = {}
    for label, men_only, want in (("rule", False, rule), ("men_only", True, old)):
        got, _, info = BF.indoor_codes(pool, m, men_only)
        out[label] = {"matches": int(len(pool)), "equal": same(got, want), "info": info}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--chain-check", action="store_true")
    a = ap.parse_args()
    f = pd.read_parquet(L.FRAME)
    f["match_id"] = f["match_id"].astype(str)
    old = f["in_indoor"].to_numpy(dtype="float64")
    new, src = ST.for_matches(f["match_id"])
    men = f["tour"].eq("atp").to_numpy()
    checks = {
        "men_known_unchanged": same(new[men & np.isfinite(old)], old[men & np.isfinite(old)]),
        "women_old_all_missing": bool(np.isnan(old[~men]).all()),
        "unknown_after": int(np.isnan(new).sum()),
        "men_filled": int((men & np.isnan(old) & np.isfinite(new)).sum()),
        "women_filled": int((~men & np.isfinite(new)).sum()),
    }
    filled_men = f.loc[men & np.isnan(old), ["season", "tournament_date"]].assign(source=src.to_numpy()[men & np.isnan(old)])
    checks["men_filled_events"] = filled_men.value_counts().rename("matches").reset_index().astype(str).to_dict("records")
    cand = f.copy()
    cand["in_indoor"] = new
    others = [c for c in f.columns if c != "in_indoor"]
    checks["other_columns_equal"] = all(
        f[c].equals(cand[c]) for c in others)
    if a.chain_check:
        checks["chain_builder"] = chain_check(f, new, old)
    bad = [k for k in ("men_known_unchanged", "women_old_all_missing", "other_columns_equal") if not checks[k]]
    if checks["unknown_after"]:
        bad.append("unknown_after")
    if a.chain_check and not all(v["equal"] for v in checks["chain_builder"].values()):
        bad.append("chain_builder")
    if bad:
        raise SystemExit(f"checks failed: {bad}: {json.dumps(checks, default=str)[:2000]}")
    ARM.mkdir(parents=True, exist_ok=True)
    cand.to_parquet(ARM / "model_frame.parquet", index=False)
    meta = json.loads(BASE_INPUTS.read_text(encoding="utf-8"))
    meta["indoor_fill"] = {"from": BASE_INPUTS.relative_to(ROOT).as_posix(), "frame": "the Pinnacle-first instance's, "
                           "in_indoor replaced by src/eda/indoor_fill/status.py"}
    (ARM / "model_inputs.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    sources = pd.DataFrame({"tour": f["tour"], "source": src.to_numpy()}).value_counts().sort_index()
    record = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
              "base_frame": L.FRAME.relative_to(ROOT).as_posix(), "base_frame_sha256": SC.sha256_file(L.FRAME),
              "base_inputs": BASE_INPUTS.relative_to(ROOT).as_posix(),
              "frame_sha256": SC.sha256_file(ARM / "model_frame.parquet"),
              "inputs": len(meta["inputs"]), "checks": checks,
              "sources": {f"{t}|{s}": int(n) for (t, s), n in sources.items()},
              "indoor_share_by_tour_season": (cand.groupby(["tour", "season"])["in_indoor"].mean().round(4)
                                              .reset_index().to_dict("records"))}
    (OUT / "arm.json").write_text(json.dumps(record, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in checks.items() if k != "men_filled_events"}, indent=1, default=str))
    print(record["sources"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
