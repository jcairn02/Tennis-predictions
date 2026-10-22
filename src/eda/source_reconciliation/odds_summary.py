"""Part F, step 6: the headline numbers of the part in one file, read from the other steps' outputs (no new reading).

Writes data/studies/source_reconciliation/odds/summary.json.
Run (after odds_coverage, odds_psx, odds_proxy, odds_score, odds_checks): ./python.sh src/eda/source_reconciliation/odds_summary.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import odds_common as O  # noqa: E402


def read(name: str):
    return json.loads((O.OUT / name).read_text(encoding="utf-8"))


def pick(r: dict | None) -> dict | None:
    if not r or r.get("est") is None:
        return None
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()
            if k in ("est", "lo", "hi", "n", "blocks", "p_neg", "ll_a", "ll_b")}


def main() -> int:
    cnt, cov, psx, prx, sc, hc = (read(n) for n in ("template_counts.json", "coverage.json", "psx.json", "proxy.json",
                                                    "scores.json", "hand_checks.json"))
    man = json.loads((C.SNAP / "manifest.json").read_text(encoding="utf-8"))
    live_ok = {f["source"]: C.sha256(C.ROOT / f["source"]) == f["sha256"] for f in man["files"][:3]}
    out = {
        "sign": "mLL differences are candidate minus base; + = the candidate worse (higher log loss). p_neg = "
                "P(candidate better), t on blocks - 1 degrees of freedom",
        "template_frame": {k: cnt[k] for k in ("frame_rows", "betonline_rows", "neither_pinnacle_nor_betonline_rows",
                                               "standin_rows_from_2025_08", "standin_rows_before_2025_08",
                                               "rebuilt_with_construct_differ_rows")},
        "gap_coverage_before_seal": {k: v for k, v in cov["totals"]["before_seal"].items()},
        "primary_minus_betonline": {k: pick(sc["A"].get(k)) for k in sc["A"]},
        "primary_minus_betonline_recalibrated": {k: pick(sc["A_recalibrated"].get(k)) for k in sc["A_recalibrated"]},
        "full_coverage_rules_minus_today": {k: pick(v) for k, v in sc["D"].items()},
        "full_coverage_rules_by_part": {p: {k: pick(v) for k, v in r.items()} for p, r in sc["D_by_part"].items()},
        "holm_survivors": [k for k, v in sc["holm_declared_family"]["readings"].items() if v["survives"]],
        "where_pinnacle_known": {p: {"minus_pinnacle": {k: pick(v) for k, v in r["minus_pinnacle"].items()}}
                                 for p, r in sc["H"].items()},
        "distance_to_pinnacle_post_change_window": {k: {"kl_mll": v.get("kl_mll"), "n": v.get("n"),
                                                        "kl_minus_bol": pick(v.get("kl_minus_bol"))}
                                                    for k, v in prx["window"].items()},
        "psx_identity_by_month": {m: {"n": r["n"], "overround_median": r["ps_overround_median"],
                                      "same_as_pinnacle_last": (r.get("pin_last_ot20") or {}).get("same_price"),
                                      "same_as_pinnacle_open": (r.get("pin_open_ot20o") or {}).get("same_price")}
                                  for m, r in psx["identity"].items()},
        "psx_timing_slope_vs_betonline_move": {m: r["against_betonline_open_to_last"]["ps"].get("slope")
                                               for m, r in psx["timing"].items()},
        "psx_timing_slope_vs_pinnacle_move": {m: r["against_pinnacle_open_to_last"]["ps"].get("slope")
                                              for m, r in psx["timing"].items()},
        "hand_checks": hc,
        "live_stage0_equals_manifest": live_ok,
        "inputs_sha256": O.sha_inputs(),
    }
    O.write_json(O.OUT / "summary.json", out)
    print(json.dumps({k: out[k] for k in ("template_frame", "holm_survivors", "live_stage0_equals_manifest")},
                     indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
