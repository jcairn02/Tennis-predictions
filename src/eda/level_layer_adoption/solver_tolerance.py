"""Are the candidate's tiny IOS differences before its first addition the solver's convergence tolerance, or information?

C0_men26's build (NEW) and the template build (ON) hold the same history up to 5 Jan 2026, yet NEW's men's IOS inputs
of earlier matches differ from ON's by up to 8e-9 (holds), 5e-12 (aces) and less elsewhere (checks/candidate.json).
The surface solver's PCG stops at a relative residual of 1e-8 (surface_ios/ios_surface.py RTOL), and the players whose
first box score is one of the 2026 additions sit in the solver's system from its first snapshot (with no released row
they rate 0 and are decoupled from the rest), so the iterates take another path to a solution that is the same to
within that tolerance. If so, solving again with a far tighter tolerance must make the two builds agree to rounding.

This script solves men's holds (pooled, "current": the solve with a level effect, as lane 2 runs it, the layer on with
each build's own resolved config) on each sandbox's own lane-2 cache, released history up to 31 Dec 2025 (until_day),
at the decided tolerance and at 1e-13, and compares O_eff and D_eff on the rows both caches hold (the same rows at the
same positions before the first addition, checked). Inputs only; no result is read.
ON's sandbox (tnr_lyr_on) was deleted on 14 Oct 2026: its cache and its build config are read from byte-for-byte
copies in data/studies/level_layer_adoption/sandbox_extracts/tnr_lyr_on/ (the config relocated: its strength table's
path into the copies, no record folder; README and manifest.json there).
Writes data/studies/level_layer_adoption/checks/solver_tolerance.json.
Run: ./python.sh src/eda/level_layer_adoption/solver_tolerance.py
"""
from __future__ import annotations

import functools
import json
import os
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import level_layer as L  # noqa: E402
from src.eda.lower_level_evidence import level_layer_ios as LI  # noqa: E402
from src.eda.surface_ios import ios_surface as IS  # noqa: E402

BOXES = {"ON": ROOT / "data" / "studies" / "level_layer_adoption" / "sandbox_extracts" / "tnr_lyr_on",
         "NEW": Path("C:/Users/zerom/tnr_lyr_new")}
CUT = int((np.datetime64("2025-12-31") - np.datetime64("1970-01-01")).astype(int))
OUT = ROOT / "data" / "studies" / "level_layer_adoption" / "checks" / "solver_tolerance.json"


def solve(box: Path, rtol: float | None, kind: str) -> dict:
    """Men's holds on the sandbox's cache, the layer on: kind "current" (pooled) or "surface" (the decided surface
    variant, as build_features.main sets its h and kappa_s)."""
    from src.eda.ios_constants import registry as IC
    from src.eda.surface_ios import common as SC
    os.environ[L.ENV] = str(box / "data" / "studies" / "current_best_model" / "level_layer" / "this_build" /
                            "build_config.json")
    L._CFG.clear()
    L._TABLES.clear()
    td = LI._load_cache_tour(box, "atp")
    chosen, typ = SC.ios_constants()
    c = chosen[("atp", "hold")]
    if kind == "current":
        h, ks = c["h"], np.inf
    else:
        ch = IC.surface_choice()["atp|hold"]
        h = c["h"] * ch["h_mult"]
        ks = (c["kappa"] * ch["ks_mult"] if ch["variant"] == "shared" else
              tuple(c["kappa"] * (np.inf if v is None else v) for v in (ch["kE_mult"], ch["kF_mult"])))
    orig = IS.pcg_block
    if rtol is not None:
        IS.pcg_block = functools.partial(orig, rtol=rtol, max_iter=100000)
    try:
        t0 = time.time()
        r = LI.run_surface(td, "hold", h, c["kappa"], ks, c["tau"], typ[("hold", "atp")], until_day=CUT)
    finally:
        IS.pcg_block = orig
    return {"td": td, "res": r, "seconds": round(time.time() - t0, 1)}


def compare_kind(kind: str, out: dict) -> dict:
    res = {}
    for label, rtol in (("decided", None), ("tight", 1e-13)):
        for name, box in BOXES.items():
            res[(label, name)] = solve(box, rtol, kind)
            out["runs"][f"{kind}|{label}|{name}"] = {
                "seconds": res[(label, name)]["seconds"],
                "solver": {k: v for k, v in res[(label, name)]["res"]["solver"].items() if k != "lle_layer_beta_2024"}}
            print(kind, label, name, res[(label, name)]["seconds"], flush=True)
    on, new = res[("decided", "ON")]["td"], res[("decided", "NEW")]["td"]
    # the rows before the first addition: the same rows, in the same positions, in both caches
    k = int(np.argmax(on["day"] > CUT)) if (on["day"] > CUT).any() else len(on["day"])
    same = all(np.array_equal(on[f][:k], new[f][:k]) for f in ("day", "ev", "pid", "es", "lf", "round_order"))
    same &= all(np.array_equal(on["stats"]["hold"][f][:k], new["stats"]["hold"][f][:k], equal_nan=True)
                for f in ("ok", "x", "d", "y"))
    o = {"prefix_rows": k, "prefix_identical_in_both_caches": bool(same)}
    for label in ("decided", "tight"):
        a, b = res[(label, "ON")]["res"], res[(label, "NEW")]["res"]
        d = {}
        for f in ("O_eff", "D_eff"):
            x, y = a[f][:k], b[f][:k]
            both = np.isfinite(x) & np.isfinite(y)
            d[f] = {"largest_difference": float(np.max(np.abs(x[both] - y[both]))) if both.any() else 0.0,
                    "rows_differing": int(((x != y) & both).sum()), "rows": int(both.sum())}
        o[f"ON_vs_NEW_{label}"] = d
    for name in BOXES:
        a, b = res[("decided", name)]["res"], res[("tight", name)]["res"]
        o[f"{name}_decided_vs_tight"] = {f: float(np.nanmax(np.abs(a[f][:k] - b[f][:k]))) for f in ("O_eff", "D_eff")}
    dec = max(v["largest_difference"] for v in o["ON_vs_NEW_decided"].values())
    tight = max(v["largest_difference"] for v in o["ON_vs_NEW_tight"].values())
    o["reading"] = (f"ON against NEW: {dec:.1e} at the decided tolerance, {tight:.1e} at 1e-13; each build's decided "
                    f"solve is {max(o['ON_decided_vs_tight'].values()):.1e} from its tight one")
    return o


def main() -> int:
    out = {"what": __doc__.split("\n")[0], "cut_day": "2025-12-31", "runs": {}}
    for kind in ("current", "surface"):
        out[kind] = compare_kind(kind, out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "runs"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
