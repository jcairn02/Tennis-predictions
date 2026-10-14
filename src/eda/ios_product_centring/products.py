"""The centred products of every pool match, gates G2 and G6, the centred arm's frame and the outcome-free diagnostics.

For each Stage 4 pool match and each of the model's 7 statistics: the surface-effective ratings of both sides from the
decided surface IOS's stored run (surface_ios/full_runs/<tour>_<stat>_surface.npz, which reference.py's re-solve
reproduces exactly: G1), and the reference level of the match's own snapshot (its earliest possible start) on its
surface (reference/<tour>_<stat>.npz). The product as built and the centred product (common.py).

    G2  the products as built equal the model frame's 7 in_prod_<s> inputs to 1e-12, with identical missing values, and
        every model-frame match has a finite reference level wherever its product is finite
    G6  the centred products are antisymmetric (A and B swapped negates them), the arm frame's flip is an involution, and
        the arm frame's other 51 inputs and identifiers equal the model frame's exactly

Writes data/studies/ios_product_centring/centred_products.parquet (pool matches: match_id, built_<s>, cprod_<s>, m_o_<s>,
m_d_<s>), arm_frame.parquet (the model frame with in_prod_<s> centred), checks/g2_products.json, checks/g6_symmetry.json
and diagnostics.json (the products' spread as built and centred, and the reference levels, by tour and season). Reads no
match result.
Run: ./python.sh src/eda/ios_product_centring/products.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.ios_product_centring import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import arms as SA  # noqa: E402
from src.eda.serve_speed_tabpfn import common as SC  # noqa: E402
from src.eda.surface_ios import common as SI  # noqa: E402

MODEL_FRAME = SC.DEFAULT.model_frame


def pool_products() -> pd.DataFrame:
    pool = pd.read_parquet(SI.CACHE / "pool.parquet")
    out = pd.DataFrame({"match_id": pool["match_id"].astype(str).to_numpy(), "tour": pool["tour"].to_numpy()})
    cols: dict[str, np.ndarray] = {}
    for t in C.TOURS:
        td = SI.load_tour(t)
        sel = (pool["tour"] == t).to_numpy()
        a, b = pool.loc[sel, "pos_a"].to_numpy(), pool.loc[sel, "pos_b"].to_numpy()
        q = td["es"][a]
        if not np.array_equal(q, td["es"][b], equal_nan=True) or not np.array_equal(td["surf"][a], td["surf"][b]):
            raise RuntimeError(f"{t}: the two sides of a pool match differ in start or surface")
        if not np.array_equal(td["surf"][a], pool.loc[sel, "surf"].to_numpy()):
            raise RuntimeError(f"{t}: pool surfaces differ from the cache's")
        surf = td["surf"][a].astype(np.int64)
        for s in C.STATS:
            with np.load(C.SI_RUNS / f"{t}_{s}_surface.npz") as z:
                O, D = z["O_eff"], z["D_eff"]
            with np.load(C.REF / f"{t}_{s}.npz") as r:
                days, m_o, m_d, count = r["days"], r["m_o"], r["m_d"], r["count"]
            i = np.searchsorted(days, q)
            if (i >= len(days)).any() or not np.array_equal(days[i], q):
                raise RuntimeError(f"{t} {s}: a pool match's start is not a snapshot day")
            mo, md = C.level(m_o[i, surf], count[i]), C.level(m_d[i, surf], count[i])
            for name, v in (("built", C.built_product(O[a], O[b], D[a], D[b])),
                            ("cprod", C.centred_product(O[a], O[b], D[a], D[b], mo, md)),
                            ("m_o", mo), ("m_d", md), ("ref_count", count[i].astype("float64")),
                            ("d_o", O[a] - O[b]), ("d_d", D[a] - D[b])):
                cols.setdefault(f"{name}_{s}", np.full(len(pool), np.nan))[sel] = v
    return pd.concat([out, pd.DataFrame(cols)], axis=1)


def diagnostics(f: pd.DataFrame, j: pd.DataFrame) -> dict:
    """Outcome-free: by tour and season, each product's SD as built and centred, its share explained by the two rating
    differences (the level x difference part), and the reference levels."""
    rows = []
    for (t, y), g in f.groupby(["tour", "season"]):
        idx = g.index.to_numpy()
        for s in C.STATS:
            bt, cp = j.loc[idx, f"built_{s}"].to_numpy(), j.loc[idx, f"cprod_{s}"].to_numpy()
            X = np.column_stack([j.loc[idx, f"d_o_{s}"].to_numpy(), j.loc[idx, f"d_d_{s}"].to_numpy()])
            ok = np.isfinite(bt) & np.isfinite(cp) & np.isfinite(X).all(axis=1)

            def r2(v):
                if ok.sum() < 3 or np.var(v[ok]) == 0:          # e.g. women's holds before 2015: every rating is 0
                    return float("nan")
                beta, *_ = np.linalg.lstsq(X[ok], v[ok], rcond=None)
                return float(1 - np.var(v[ok] - X[ok] @ beta) / np.var(v[ok]))
            rows.append({"tour": t, "season": int(y), "stat": s, "matches": int(ok.sum()),
                         "sd_built": float(np.std(bt[ok])), "sd_centred": float(np.std(cp[ok])),
                         "sd_offence_difference": float(np.std(X[ok, 0])),
                         "sd_defence_difference": float(np.std(X[ok, 1])),
                         "r2_built_on_differences": r2(bt), "r2_centred_on_differences": r2(cp),
                         "corr_built_centred": (float(np.corrcoef(bt[ok], cp[ok])[0, 1])
                                                if ok.sum() > 2 and np.std(bt[ok]) > 0 and np.std(cp[ok]) > 0
                                                else float("nan")),
                         "m_o_mean": float(np.nanmean(j.loc[idx, f"m_o_{s}"])),
                         "m_d_mean": float(np.nanmean(j.loc[idx, f"m_d_{s}"]))})
    return {"by_tour_season_stat": rows}


def main() -> int:
    cp = pool_products()
    cp.to_parquet(C.OUT / "centred_products.parquet", index=False)
    f = pd.read_parquet(MODEL_FRAME)
    f["match_id"] = f["match_id"].astype(str)
    j = f[["match_id"]].merge(cp, on="match_id", how="left", validate="one_to_one", indicator=True)
    missing = int((j["_merge"] != "both").sum())

    # G2: the products as built are the model's inputs
    g2 = {"model_frame_matches": int(len(f)), "missing_from_pool": missing, "by_stat": {}}
    for s in C.STATS:
        gap, same_nan = C.max_gap(j[f"built_{s}"], f[f"in_prod_{s}"])
        fin = np.isfinite(j[f"built_{s}"].to_numpy())
        ref_ok = bool(np.isfinite(j.loc[fin, f"m_o_{s}"]).all() and np.isfinite(j.loc[fin, f"m_d_{s}"]).all())
        no_ref = (j[f"ref_count_{s}"].to_numpy() == 0) & fin
        g2["by_stat"][s] = {"max_abs_gap": gap, "same_missing": same_nan, "reference_finite": ref_ok,
                            "missing_share": float(np.isnan(f[f"in_prod_{s}"].to_numpy(dtype=float)).mean()),
                            "rows_without_reference_players": {
                                f"{t}_{y}": int(n) for (t, y), n in
                                pd.Series(no_ref).groupby([f["tour"], f["season"]]).sum().items() if n}}
    g2["passed"] = missing == 0 and all(v["max_abs_gap"] <= C.EXACT and v["same_missing"] and v["reference_finite"]
                                        for v in g2["by_stat"].values())
    C.jdump({"what": "G2: the products as built equal the model frame's in_prod inputs (1e-12, same missing values); "
                     "every finite product has a finite reference level", "tolerance": C.EXACT, **g2},
            C.CHECKS / "g2_products.json")
    if not g2["passed"]:
        C.log(f"G2 FAIL: {g2}")
        return 1

    # the centred arm's frame: only the 7 products change
    arm = f.copy()
    for s in C.STATS:
        arm[f"in_prod_{s}"] = j[f"cprod_{s}"].to_numpy(dtype="float64")
    arm.to_parquet(C.OUT / "arm_frame.parquet", index=False)

    # G6: antisymmetry, the flip, everything else unchanged
    names, _, _ = SA.base_inputs(SC.DEFAULT)
    pool = pd.read_parquet(SI.CACHE / "pool.parquet")
    anti = {}
    for t in C.TOURS:
        td = SI.load_tour(t)
        sel = (pool["tour"] == t).to_numpy()
        a, b = pool.loc[sel, "pos_a"].to_numpy(), pool.loc[sel, "pos_b"].to_numpy()
        for s in C.STATS:
            with np.load(C.SI_RUNS / f"{t}_{s}_surface.npz") as z:
                O, D = z["O_eff"], z["D_eff"]
            mo, md = cp.loc[sel, f"m_o_{s}"].to_numpy(), cp.loc[sel, f"m_d_{s}"].to_numpy()
            fwd = C.centred_product(O[a], O[b], D[a], D[b], mo, md)
            rev = C.centred_product(O[b], O[a], D[b], D[a], mo, md)
            anti[f"{t}_{s}"] = C.max_gap(fwd, -rev)[0]
    other = [c for c in f.columns if c not in {f"in_prod_{s}" for s in C.STATS}]
    unchanged = all(f[c].equals(arm[c]) for c in other)
    flip_ok = SA.check_flip(arm, names, SC.DEFAULT)
    g6 = {"what": "G6: centred products antisymmetric; the arm frame's flip an involution; its other columns equal the "
                  "model frame's", "antisymmetry_max_abs_gap": anti, "flip_is_involution": flip_ok,
          "other_columns_unchanged": unchanged, "other_columns": len(other)}
    g6["passed"] = flip_ok and unchanged and max(anti.values()) <= C.EXACT
    C.jdump(g6, C.CHECKS / "g6_symmetry.json")

    diag = diagnostics(f, j)
    diag["sha256"] = {"centred_products": C.sha256(C.OUT / "centred_products.parquet"),
                      "arm_frame": C.sha256(C.OUT / "arm_frame.parquet"), "model_frame": C.sha256(MODEL_FRAME)}
    C.jdump(diag, C.OUT / "diagnostics.json")
    d = pd.DataFrame(diag["by_tour_season_stat"])
    show = d[d["stat"] == "hold"][["tour", "season", "sd_built", "sd_centred", "r2_built_on_differences",
                                   "r2_centred_on_differences", "m_o_mean", "m_d_mean"]]
    with pd.option_context("display.width", 200, "display.max_rows", 100):
        print(show.round(3).to_string(index=False))
    C.log(f"G2 PASS; G6 {'PASS' if g6['passed'] else 'FAIL'}; arm_frame.parquet written")
    return 0 if g6["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
