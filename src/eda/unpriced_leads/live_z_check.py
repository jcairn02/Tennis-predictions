"""Step 3's second proof: the combined score z for live rows equals z built from the registered values on the template
frame's inputs, with the same gates and the check's frozen parameters (rules: docs/studies/unpriced_leads/
check_now_rules.md).

On a replay run (live_members.parquet written inside its work tree by the patterns step):
    z_live   check_now.score_from_params on the live inputs (the run's live_frame.parquet) and the live member values
    z_hist   the same function on the template frame's inputs for the same matches and the registered values files
Gates: the live gate of the run's months, with the members not built for live matches (live_members.NOT_BUILT)
switched off on both sides. That is October 2026's state, where those members' data supply has collapsed; in the
replayed month (July 2026) their gate was still on, so the engine itself pauses those matches. With that one change,
both sides must agree to 1e-9.
Also written, with --write, to <run>/live_patterns.parquet: z_live, for the predict hook's test (patterns_live.for_run).
Writes data/studies/unpriced_leads/check_now/live_parity/<name>_z.json.
Run: ./python.sh src/eda/unpriced_leads/live_z_check.py --run <replay run> --tree <its work tree> --name <replay>
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

from src.eda.unpriced_leads import check_now as CN  # noqa: E402
from src.eda.unpriced_leads import live_members as LM  # noqa: E402
from src.eda.unpriced_leads import look as LK  # noqa: E402
from src.eda.unpriced_leads import patterns_live as PL  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

OUT = ROOT / "data" / "studies" / "unpriced_leads" / "check_now" / "live_parity"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--tree", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    run = Path(a.run)
    reg = json.loads(CN.REGISTRY.read_text(encoding="utf-8"))
    groups = reg["groups"]
    adj = json.loads((ROOT / "data" / "studies" / "unpriced_leads" / "check_now" / "adjustment.json")
                     .read_text(encoding="utf-8"))
    P = json.loads((ROOT / adj["params"]).read_text(encoding="utf-8"))
    names = H.diff_input_names()
    # the live side
    vals = pd.read_parquet(run / PL.MEMBERS_FILE).astype({"match_id": str}).drop_duplicates("match_id")
    lf = pd.read_parquet(run / "live_frame.parquet").astype({"match_id": str}).drop_duplicates("match_id")
    meta = pd.read_parquet(run / "live_meta.parquet").astype({"match_id": str}).drop_duplicates("match_id")
    live = lf.merge(meta[["match_id", "day"]], on="match_id", how="left", validate="one_to_one")
    for k, (x, y) in H.PAIRS.items():
        live[f"in_{k}"] = live[f"in_{x}"] - live[f"in_{y}"]
    live["month"] = pd.to_datetime(live["day"]).dt.to_period("M").astype(str)
    gates, _ = PL.live_gates(groups, live["tour"].to_numpy(), live["month"].to_numpy(), Path(a.tree))
    for c in LM.NOT_BUILT:
        gates[c] = np.zeros(len(live), bool)
    v_live = {c: vals.set_index("match_id")[c] for c in vals.columns if c != "match_id"}
    z_live = CN.score_from_params(groups, live, P, gates, values=v_live)
    # the historical side: the template frame's inputs (no result column read), the registered values
    cols = ["match_id", "tour"] + [f"in_{n}" for n in names if n not in H.PAIRS] + \
        [f"in_{x}" for k in H.PAIRS for x in H.PAIRS[k]]
    fr = pd.read_parquet(H.FRAME, columns=list(dict.fromkeys(cols))).astype({"match_id": str})
    fr = fr.drop_duplicates("match_id").set_index("match_id").reindex(live["match_id"]).reset_index()
    for k, (x, y) in H.PAIRS.items():
        fr[f"in_{k}"] = fr[f"in_{x}"] - fr[f"in_{y}"]
    members = {m["column"]: m for g in groups for m in g["members"]}
    v_hist = {}
    for c in members:
        if c in LM.NOT_BUILT:
            v_hist[c] = pd.Series(np.nan, index=live["match_id"])
            continue
        r = pd.read_parquet(ROOT / members[c]["values"], columns=["match_id", c]).astype({"match_id": str})
        LK.check_hash(ROOT / members[c]["values"], members[c].get("values_sha256"), c)
        v_hist[c] = r.drop_duplicates("match_id").set_index("match_id")[c]
    z_hist = CN.score_from_params(groups, fr, P, gates, values=v_hist)
    d_in = np.abs(live[[f"in_{n}" for n in names]].to_numpy(float) - fr[[f"in_{n}" for n in names]].to_numpy(float))
    d_z = np.abs(z_live - z_hist)
    rec = {"name": a.name, "matches": int(len(live)), "tolerance": 1e-9,
           "inputs_48_max_abs_diff": float(np.nanmax(d_in)) if np.isfinite(d_in).any() else 0.0,
           "inputs_48_nan_mismatch": int((np.isnan(live[[f"in_{n}" for n in names]].to_numpy(float)) ^
                                          np.isnan(fr[[f"in_{n}" for n in names]].to_numpy(float))).sum()),
           "z_max_abs_diff": float(np.max(d_z)), "z_live": z_live.tolist(), "z_hist": z_hist.tolist(),
           "gates_used": {c: np.asarray(v).tolist() for c, v in gates.items()},
           "proof_passed": bool(np.max(d_z) <= 1e-9)}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{a.name}_z.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    if a.write:
        pd.DataFrame({"match_id": live["match_id"], "z": z_live}).to_parquet(run / PL.LIVE_FILE, index=False)
    print(f"inputs (48) max |diff| {rec['inputs_48_max_abs_diff']:.2e}, NaN mismatches {rec['inputs_48_nan_mismatch']}")
    print(f"z: live vs historical max |diff| {rec['z_max_abs_diff']:.2e}; z range {np.min(z_live):+.2f} .. "
          f"{np.max(z_live):+.2f}")
    print(f"PROOF {'PASSED' if rec['proof_passed'] else 'FAILED'}")
    return 0 if rec["proof_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
