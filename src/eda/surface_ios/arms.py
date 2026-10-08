"""Build every arm's input frame for the surface-IOS TabPFN test (plan.ARMS): the base frame's rows, with inputs taken
from the base frame or derived from the surface IOS (surface_features.parquet, build_features.py).

First a mapping check: today's 21 IOS profile inputs (iosO, iosD, prod on seven statistics) rebuilt from the "current"
full-history runs must equal the base frame's, value for value; otherwise the per-match surface inputs could sit on the
wrong rows. Then each arm's columns are written as in_<name> beside the base frame's match identifiers.

Input recipes (A - B differences; prod as in Stage D: A's offence times B's lack of defence minus the reverse):
    iosO_<s>, iosD_<s>, prod_<s>      today's (current) or the surface model's effective values on the match's surface
    sdevO_<s>, sdevD_<s>              the surface model's deviations on the match's surface: E_A - E_B, F_A - F_B
    iosOall_<s>, iosDall_<s>          the surface model's all-surface parts: O_A - O_B, D_A - D_B

Writes data/studies/surface_ios/arms/<arm>.parquet and arms/checks.json.
Run: ./python.sh src/eda/surface_ios/arms.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.surface_ios import common as C  # noqa: E402
from src.eda.surface_ios import plan as PL  # noqa: E402

META = ["match_id", "tour", "year", "tournament_date", "a_won", "group", "surface_code", "p_mkt", "split"]


def recipe(name: str, sf: pd.DataFrame) -> np.ndarray:
    """The value of input ``name`` for every row of ``sf`` (surface features merged onto the base frame's rows)."""
    kind, stat = name.split("_", 1)
    a = lambda c: sf[f"{c}_a"].to_numpy(dtype="float64")   # noqa: E731
    b = lambda c: sf[f"{c}_b"].to_numpy(dtype="float64")   # noqa: E731
    if kind in ("iosO", "iosD", "prod", "curO", "curD", "curprod"):
        src = "srf" if kind in ("iosO", "iosD", "prod") else "cur"
        o = f"{src}_O_eff_{stat}" if src == "srf" else f"cur_O_{stat}"
        d = f"{src}_D_eff_{stat}" if src == "srf" else f"cur_D_{stat}"
        if kind.endswith("O"):
            return a(o) - b(o)
        if kind.endswith("D"):
            return a(d) - b(d)
        return a(o) * (-b(d)) - b(o) * (-a(d))
    if kind == "sdevO":
        return a(f"srf_E_{stat}") - b(f"srf_E_{stat}")
    if kind == "sdevD":
        return a(f"srf_F_{stat}") - b(f"srf_F_{stat}")
    if kind == "iosOall":
        return a(f"srf_O_{stat}") - b(f"srf_O_{stat}")
    if kind == "iosDall":
        return a(f"srf_D_{stat}") - b(f"srf_D_{stat}")
    if kind == "dnet":           # the change in A's net (serve + return) advantage: surface-effective minus today's
        eff = (a(f"srf_O_eff_{stat}") - b(f"srf_O_eff_{stat}")) + (a(f"srf_D_eff_{stat}") - b(f"srf_D_eff_{stat}"))
        cur = (a(f"cur_O_{stat}") - b(f"cur_O_{stat}")) + (a(f"cur_D_{stat}") - b(f"cur_D_{stat}"))
        return eff - cur
    if kind == "dnetperm":       # the placebo: dnet permuted within tour x surface x season (fixed seed)
        v = recipe(f"dnet_{stat}", sf)
        out = v.copy()
        rng = np.random.default_rng(20261006)
        keys = sf[["tour", "surface_code", "year"]].astype(str).agg("|".join, axis=1).to_numpy()
        for k in np.unique(keys):
            idx = np.flatnonzero(keys == k)
            out[idx] = v[rng.permutation(idx)]
        return out
    raise KeyError(name)


def main() -> int:
    base = pd.read_parquet(C.OUT / "base_frame.parquet")
    checks = {}
    if "--base-only" in sys.argv:                            # the base arm needs no surface input (pipeline checks)
        spec = PL.ARMS["base"]
        frame = pd.concat([base[META], base[[f"in_{n}" for n in spec["columns"]]]], axis=1)
        (C.OUT / "arms").mkdir(parents=True, exist_ok=True)
        frame.to_parquet(PL.arm_path("base"), index=False)
        C.log(f"base: {len(spec['columns'])} inputs")
        return 0
    sf = pd.read_parquet(C.OUT / "surface_features.parquet")
    sf = base[["match_id", "tour", "surface_code", "year"]].merge(sf, on="match_id", how="left", validate="one_to_one")
    for s in C.PROFILE_IOS:                                   # the mapping check against today's inputs
        for kind, model in (("curO", "iosO"), ("curD", "iosD"), ("curprod", "prod")):
            got = recipe(f"{kind}_{s}", sf)
            want = base[f"in_{model}_{s}"].to_numpy(dtype="float64")
            gap = float(np.nanmax(np.abs(got - want)))
            same_nan = bool(np.array_equal(np.isnan(got), np.isnan(want)))
            checks[f"{model}_{s}"] = {"max_abs_gap": gap, "same_missing": same_nan}
            if gap > 1e-12 or not same_nan:
                raise RuntimeError(f"{model}_{s}: rebuilt current input differs from the base frame ({gap})")
    out_dir = C.OUT / "arms"
    out_dir.mkdir(parents=True, exist_ok=True)
    for arm, spec in PL.ARMS.items():
        cols = {}
        for n in spec["columns"]:
            src = spec.get("sources", {}).get(n)
            cols[f"in_{n}"] = base[f"in_{n}"].to_numpy(dtype="float64") if src is None else recipe(src, sf)
        frame = pd.concat([base[META].reset_index(drop=True), pd.DataFrame(cols)], axis=1)
        frame.to_parquet(PL.arm_path(arm), index=False)
        changed = [n for n in spec["columns"] if spec.get("sources", {}).get(n)]
        checks[f"arm:{arm}"] = {"columns": len(spec["columns"]), "derived": changed,
                                "missing_share": {n: float(np.isnan(cols[f"in_{n}"]).mean()) for n in changed}}
        C.log(f"{arm}: {len(spec['columns'])} inputs, {len(changed)} from the surface IOS")
    C.jdump(checks, out_dir / "checks.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
