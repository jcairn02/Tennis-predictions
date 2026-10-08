"""Stage 1, part 2: do the sources agree on the matches two of them hold?

For every pair of point-level sources, the matches both hold (the same Stage 0 match) are aligned point by point by their
order in the match, and kept where the two sequences agree on the server and the point winner on at least 98% of
points (a check that the alignment is right). On those points the script measures, for every field of the common point
table, how often the two sources agree: rally length (after the conversion to one counting convention), how the point
ended and who hit the last shot, the serve number, the serve speed (within 2 km/h), the placement, net play, the return
depth and the wing. It also gives per-source level ratios for the ending counts (winners, forced and unforced errors per
point), which the statistics' definitions take into account (stage1_stats.py).

Nothing here reads who won a match beyond the point winners used to align the sequences.

Run:  ./python.sh src/eda/shot_level/stage1_agreement.py
Writes data/studies/shot_level/stage1_agreement.csv (one row per pair) and stage1_agreement.json.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.shot_level import common as S  # noqa: E402
from src.eda.shot_level import points as P  # noqa: E402

SOURCES = list(P.ADAPTERS)


def oriented(name: str, links: pd.DataFrame) -> pd.DataFrame:
    """A source's points with the Stage 0 match and the players turned to Stage 0's sides (1 = side A)."""
    p = pd.read_parquet(S.OUT / f"stage1_points_{name}.parquet")
    lk = links[links["source"].eq(name) & links["match_id"].notna() & links["a1"].notna()][["key", "match_id", "a1"]]
    p = p.merge(lk, on="key", how="inner")
    a1 = p["a1"].astype(bool).to_numpy()
    for c in ("server", "winner", "ender"):
        v = p[c].to_numpy()
        p[c] = np.where(v == 0, 0, np.where(a1, v, 3 - v)).astype("int8")
    n1, n2 = p["net1"].to_numpy(), p["net2"].to_numpy()
    p["net1"], p["net2"] = np.where(a1, n1, n2), np.where(a1, n2, n1)
    return p.drop(columns=["a1"])


def compare(a: pd.DataFrame, b: pd.DataFrame, na: str, nb: str) -> dict | None:
    both = np.intersect1d(a["match_id"].unique(), b["match_id"].unique())
    if len(both) == 0:
        return None
    m = a[a["match_id"].isin(both)].merge(b[b["match_id"].isin(both)], on=["match_id", "seq"], suffixes=("_a", "_b"))
    agree = (m["server_a"] == m["server_b"]) & (m["winner_a"] == m["winner_b"])
    ok = agree.groupby(m["match_id"]).mean()
    good = ok[ok >= 0.98].index
    m = m[m["match_id"].isin(good)]
    out = {"pair": f"{na} | {nb}", "a": na, "b": nb, "matches_both": int(len(both)), "matches_aligned": int(len(good)),
           "points": int(len(m))}
    if len(m) == 0:
        return out
    r = m[(m["rally_a"] >= 0) & (m["rally_b"] >= 0)]
    out["rally_points"] = int(len(r))
    if len(r):
        diff = (r["rally_a"] - r["rally_b"])
        out["rally_equal"] = float((diff == 0).mean())
        out["rally_within_1"] = float((diff.abs() <= 1).mean())
        out["rally_mean_diff"] = float(diff.mean())
        # the bins the statistics use: within 4 shots, 5 or more, 9 or more
        for lo, name in ((5, "5plus"), (9, "9plus")):
            out[f"rally_{name}_agree"] = float(((r["rally_a"] >= lo) == (r["rally_b"] >= lo)).mean())
    e = m[(m["end_a"] > 0) & (m["end_b"] > 0)]
    out["end_points"] = int(len(e))
    if len(e):
        out["end_equal"] = float((e["end_a"] == e["end_b"]).mean())
        err_a = e["end_a"].isin([P.END["forced"], P.END["unforced"]])
        err_b = e["end_b"].isin([P.END["forced"], P.END["unforced"]])
        out["error_vs_winner_equal"] = float(((err_a == err_b) & ~(e["end_a"].isin([1, 2]) ^ e["end_b"].isin([1, 2]))).mean())
        both_err = e[err_a & err_b]
        out["forced_unforced_equal"] = float((both_err["end_a"] == both_err["end_b"]).mean()) if len(both_err) else None
        same = e[e["end_a"] == e["end_b"]]
        out["ender_equal"] = float((same["ender_a"] == same["ender_b"]).mean()) if len(same) else None
        # level ratios: counts per point of each kind, source a over source b, on the same points
        for k in ("winner", "forced", "unforced"):
            ca, cb = (e["end_a"] == P.END[k]).sum(), (e["end_b"] == P.END[k]).sum()
            out[f"ratio_{k}"] = float(ca / cb) if cb else None
        ca = e["end_a"].isin([P.END["forced"], P.END["unforced"]]).sum()
        cb = e["end_b"].isin([P.END["forced"], P.END["unforced"]]).sum()
        out["ratio_errors"] = float(ca / cb) if cb else None
    sn = m[(m["serve_no_a"] > 0) & (m["serve_no_b"] > 0)]
    out["serve_no_equal"] = float((sn["serve_no_a"] == sn["serve_no_b"]).mean()) if len(sn) else None
    sp = m[m["speed_a"].notna() & m["speed_b"].notna()]
    out["speed_points"] = int(len(sp))
    out["speed_within_2"] = float(((sp["speed_a"] - sp["speed_b"]).abs() <= 2).mean()) if len(sp) else None
    pl = m[(m["place_a"] > 0) & (m["place_b"] > 0)]
    out["place_points"] = int(len(pl))
    out["place_equal"] = float((pl["place_a"] == pl["place_b"]).mean()) if len(pl) else None
    nt = m[(m["net1_a"] >= 0) & (m["net1_b"] >= 0)]
    out["net_points"] = int(len(nt))
    out["net_equal"] = float(((nt["net1_a"] == nt["net1_b"]) & (nt["net2_a"] == nt["net2_b"])).mean()) if len(nt) else None
    rd = m[(m["ret_deep_a"] >= 0) & (m["ret_deep_b"] >= 0)]
    out["ret_deep_points"] = int(len(rd))
    out["ret_deep_equal"] = float((rd["ret_deep_a"] == rd["ret_deep_b"]).mean()) if len(rd) else None
    wg = m[(m["wing_a"] > 0) & (m["wing_b"] > 0)]
    out["wing_points"] = int(len(wg))
    out["wing_equal"] = float((wg["wing_a"] == wg["wing_b"]).mean()) if len(wg) else None
    return out


def main() -> int:
    links = pd.read_parquet(S.OUT / "stage0_source_matches.parquet", columns=["source", "key", "match_id", "a1"])
    pts = {n: oriented(n, links) for n in SOURCES if (S.OUT / f"stage1_points_{n}.parquet").exists()}
    rows = []
    for na, nb in itertools.combinations(pts, 2):
        r = compare(pts[na], pts[nb], na, nb)
        if r and r.get("matches_aligned", 0) > 0:
            rows.append(r)
            S.log(f"{na} | {nb}: {r['matches_aligned']} matches aligned, {r['points']} points")
    t = pd.DataFrame(rows)
    t.to_csv(S.OUT / "stage1_agreement.csv", index=False)
    (S.OUT / "stage1_agreement.json").write_text(json.dumps(rows, indent=1, default=float), encoding="utf-8")
    cols = ["pair", "matches_aligned", "points", "rally_equal", "rally_within_1", "rally_mean_diff", "rally_5plus_agree",
            "rally_9plus_agree", "end_equal", "error_vs_winner_equal", "forced_unforced_equal", "ender_equal",
            "ratio_winner", "ratio_errors", "ratio_unforced", "serve_no_equal", "speed_within_2", "place_equal",
            "net_equal", "ret_deep_equal", "wing_equal"]
    with pd.option_context("display.width", 320, "display.max_columns", 40):
        print(t[[c for c in cols if c in t]].round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
