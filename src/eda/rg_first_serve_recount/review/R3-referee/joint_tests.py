"""R3-referee, step 3b: the independent records judged on the whole split, not first serves in alone.

A side's serve points fall in four categories: first serve in and won (first_won), in and lost (first_in -
first_won), points on a second serve won (second_won) and lost (svpt - first_in - second_won). Where an independent
record (MCP, Court Vision) holds the same serve points as the official record, the number of points it would have to
reclassify to read another record's split is half the L1 distance of the two four-count vectors. Its distribution is
measured where the truth is not in dispute (rows whose official record equals Sackmann's): MCP on RG 2019-2021 (the
clean editions), MCP on the Olympics' equal rows (MCP is noisier there), Court Vision on RG 2019-2020 and RG 2022's
equal rows. On the proposed rows, k_O (moves to the official split) and k_S (moves to Sackmann's) are compared:
which is smaller, and a log-likelihood ratio from the calibrated distribution of k.

Reads mcp_rows.csv and cv_rows.csv (independent.py). Writes joint_tests.csv and joint_rows.csv.
Usage: ./python.sh src/eda/rg_first_serve_recount/review/R3-referee/joint_tests.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import r3common as C  # noqa: E402

OUT = C.OUT


def cats(sv, fi, fw, sw):
    return np.stack([fw, fi - fw, sw, sv - fi - sw], axis=-1)


def moves(d: pd.DataFrame, src: str, ref: str) -> np.ndarray:
    a = cats(d[f"{src}_svpt"].to_numpy(float), d[f"{src}_first_in"].to_numpy(float), d[f"{src}_first_won"].to_numpy(float),
             d[f"{src}_second_won"].to_numpy(float))
    b = cats(d[f"{ref}_svpt"].to_numpy(float), d[f"{ref}_first_in"].to_numpy(float), d[f"{ref}_first_won"].to_numpy(float),
             d[f"{ref}_second_won"].to_numpy(float))
    return np.abs(a - b).sum(axis=1) / 2


def pmf(k: np.ndarray, alpha: float = 1.0):
    k = np.asarray(k, dtype=float)
    lam = max(np.mean(k), 0.25)
    vals, cnt = np.unique(k, return_counts=True)
    emp = dict(zip(vals, cnt))
    n = len(k)

    def f(x):
        geo = (1 / (1 + lam)) * (lam / (1 + lam)) ** x          # a geometric tail with the same mean
        return (emp.get(x, 0) + alpha * geo) / (n + alpha)
    return f


def run(T: pd.DataFrame, src: str, cal: pd.DataFrame, sets: dict, cal_name: str) -> list[dict]:
    cal = cal[cal[f"{src}_svpt"].eq(cal["raw_svpt"])]
    kc = moves(cal, src, "raw")
    f = pmf(kc)
    out = []
    for name, d in sets.items():
        d = d[d[f"{src}_svpt"].eq(d["off_svpt"])]
        if d.empty:
            continue
        ko, ks = moves(d, src, "off"), moves(d, src, "raw")
        llr = np.array([np.log10(f(a)) - np.log10(f(b)) for a, b in zip(ko, ks)])
        out.append({"source": src, "calibration": cal_name, "calibration_rows": len(cal),
                    "calibration_k0": round(float(np.mean(kc == 0)), 3), "calibration_mean_k": round(float(np.mean(kc)), 2),
                    "set": name, "rows": len(d), "k_O_smaller": int(np.sum(ko < ks)), "k_S_smaller": int(np.sum(ks < ko)),
                    "equal_k": int(np.sum(ko == ks)), "k_O_zero": int(np.sum(ko == 0)), "k_S_zero": int(np.sum(ks == 0)),
                    "mean_k_O": round(float(np.mean(ko)), 2), "mean_k_S": round(float(np.mean(ks)), 2),
                    "log10_LR_O_vs_S": round(float(llr.sum()), 1), "rows_LR_favour_S": int(np.sum(llr < 0))})
    return out


def sets_of(D: pd.DataFrame, prefix: str, fixes: list[str]) -> dict:
    p = D[D["fix"].notna() & D["fix"].ne("")].copy()
    p["absd"] = (p["raw_first_in"] - p["off_first_in"]).abs()
    s = {f"{prefix} all proposed": p}
    for fx in fixes:
        g = p[p["fix"].eq(fx)]
        s[fx] = g
        for sg in ["+", "-", "0"]:
            s[f"{fx} {sg}"] = g[g["sign"].eq(sg)]
        s[f"{fx} |d|<=1"] = g[g["absd"].le(1)]
        s[f"{fx} |d|>=2"] = g[g["absd"].ge(2)]
    return s


def main() -> int:
    M = pd.read_csv(OUT / "mcp_rows.csv", low_memory=False)
    V = pd.read_csv(OUT / "cv_rows.csv", low_memory=False)
    rows = []
    rg, og = M[M["event"].eq("RG")], M[M["event"].eq("OG")]
    cal_rg = rg[rg["year"].between(2019, 2021) & rg["cls"].eq("equal")]
    cal_og = og[og["cls"].eq("equal")]
    rows += run(M, "mcp", cal_rg, sets_of(rg, "MCP RG", ["RGFSA", "RGFSB"]), "MCP RG 2019-2021 equal")
    rows += run(M, "mcp", cal_rg, sets_of(og, "MCP OG", ["OGFSA", "OGFSB"]), "MCP RG 2019-2021 equal")
    rows += run(M, "mcp", cal_og, sets_of(og, "MCP OG", ["OGFSA", "OGFSB"]), "MCP OG equal (noisier)")
    v22 = V[V["year"].eq(2022)]
    rows += run(V, "cv", V[V["year"].between(2019, 2020) & V["cls"].eq("equal")], sets_of(v22, "CV RG 2022", ["RGFSA", "RGFSB"]),
                "CV RG 2019-2020 equal")
    rows += run(V, "cv", v22[v22["cls"].eq("equal")], sets_of(v22, "CV RG 2022", ["RGFSA", "RGFSB"]), "CV RG 2022 equal")
    t = pd.DataFrame(rows)
    t.to_csv(OUT / "joint_tests.csv", index=False)
    # per-row detail for the Olympic rows and every row where the record sides with Sackmann
    det = []
    for src, D in (("mcp", M), ("cv", v22)):
        p = D[D["fix"].notna() & D["fix"].ne("") & D[f"{src}_svpt"].eq(D["off_svpt"])].copy()
        p["k_O"], p["k_S"] = moves(p, src, "off"), moves(p, src, "raw")
        p["source"] = src
        det.append(p[["source", "fix", "sign", "event", "year", "round", "player_name", "source_file", "source_row", "side",
                      "raw_svpt", "raw_first_in", "raw_first_won", "raw_second_won", "off_first_in", "off_first_won",
                      "off_second_won", f"{src}_first_in", f"{src}_first_won", f"{src}_second_won", "k_O", "k_S"]]
                   .rename(columns={f"{src}_first_in": "ind_first_in", f"{src}_first_won": "ind_first_won",
                                    f"{src}_second_won": "ind_second_won"}))
    det = pd.concat(det, ignore_index=True)
    det.to_csv(OUT / "joint_rows.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    print(t.to_string())
    print(det[det["k_S"] < det["k_O"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
