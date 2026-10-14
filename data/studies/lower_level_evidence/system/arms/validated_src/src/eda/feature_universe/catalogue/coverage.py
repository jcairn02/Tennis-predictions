"""Coverage of the feature universe's candidates on the frozen model population, by tour and period (feature universe).

Population: the 63,737 rows of the 58-input model frame (2013-2026), read as match_id, tour and season only. No result
column is read anywhere (the store has none; for source tables the columns are named explicitly). Coverage relates no
feature to any outcome, so 2025-2026 is included (the coordinator's rule: row counts and coverage are fine).
Periods: p1 = 2013-2021, p2 = 2022-2024, p3 = 2025-2026. Exists = the value is finite; for a per-player pair
(<x>_a, <x>_b) a key <x>_ab is added: both players have it.

Writes data/studies/feature_universe/build/coverage_keys.csv (key, n and share per tour x period):
    store:<column>       every column of data/studies/feature_universe/store.parquet (the coordinator's store, read only)
    <label>:<column>     source tables of built features that are not in the store (SOURCES below)
    sl3:<stat|side|form> shot-level histories: both players have real data (the |has flags; values are prior-filled)
    ps:<field>           point-sequence coverage, from point_sequence/coverage_model.csv (its own table)
Run: ./python.sh src/eda/feature_universe/catalogue/coverage.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[4]
S = ROOT / "data" / "studies"
OUT = S / "feature_universe" / "build"
OLD =S / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced" / "data" / "studies"
STORE = S / "feature_universe" / "store.parquet"
NEVER = {"a_won", "won", "winner", "y", "result"}
SKIP = NEVER | {"match_id", "tour", "year", "season", "group", "evaluation", "status", "order", "tournament_date",
                "tournament_name", "tournament_id", "level", "round", "surface", "main", "format_supported", "updates"}
SOURCES = [   # (label, path, column filter or None = every numeric column)
    ("b1", S / "predictability_diagnostic" / "stage1_baselines.parquet", None),
    ("s4", S / "predictability_diagnostic" / "stage4_features.parquet", None),
    ("ra", S / "rating_systems" / "stageA_ratings.parquet", None),
    ("tt", OLD / "match_timing" / "ttt_timed.parquet", None),
    ("bt", S / "ufc_ideas" / "stageA_bt.parquet", None),
    ("mesr", S / "ufc_ideas" / "stageA_mesr.parquet", None),
    ("adj", S / "ufc_ideas" / "stageB_adj_features.parquet", None),
    ("split", S / "ufc_ideas" / "stageB_split_features.parquet", None),
    ("iosw", S / "ufc_ideas" / "stageB_ios_features.parquet", None),
    ("sos", S / "ufc_ideas" / "stageC_sos_part.parquet", None),
    ("fat", S / "ufc_ideas" / "stageC_fatigue_part.parquet", None),
    ("ss", S / "market_anchoring" / "surface_stat_features.parquet", None),
    ("pf", S / "predictive_frontier" / "frontier_features.parquet", None),
    ("pc", S / "surface_elo_pieces" / "pieces.parquet", lambda c: c.startswith(("S_", "XA_", "DG_"))),
    ("sl2", S / "shot_level" / "stage2_features.parquet", None),
]


def population() -> pd.DataFrame:
    mf = pd.read_parquet(STORE, columns=["match_id", "tour", "season"])
    mf["match_id"] = mf["match_id"].astype(str)
    mf["period"] = np.select([mf["season"] <= 2021, mf["season"] <= 2024], ["p1", "p2"], "p3")
    return mf


def cells(mf: pd.DataFrame) -> list[tuple[str, str, np.ndarray]]:
    t, p = mf["tour"].astype(str).to_numpy(), mf["period"].to_numpy()
    return [(tt, pp, (t == tt) & (p == pp)) for tt in ("atp", "wta") for pp in ("p1", "p2", "p3")]


def row(key: str, ok: np.ndarray, C) -> dict:
    r = {"key": key}
    for t, p, m in C:
        r[f"n_{t}_{p}"] = int(m.sum())
        r[f"cov_{t}_{p}"] = round(float(ok[m].mean()), 4) if m.any() else np.nan
    return r


def finite(x) -> np.ndarray:
    return np.isfinite(pd.to_numeric(pd.Series(x), errors="coerce").to_numpy(dtype="float64"))


def frame_rows(d: pd.DataFrame, cols: list[str], prefix: str, C) -> list[dict]:
    out, ok = [], {c: finite(d[c]) for c in cols}
    for c in cols:
        out.append(row(f"{prefix}:{c}", ok[c], C))
        if c.endswith("_a") and c[:-2] + "_b" in ok:
            out.append(row(f"{prefix}:{c[:-2]}_ab", ok[c] & ok[c[:-2] + "_b"], C))
    return out


def on_model(path: Path, ids: pd.Series, cols: list[str]) -> pd.DataFrame:
    d = pd.read_parquet(path, columns=["match_id"] + cols)
    d["match_id"] = d["match_id"].astype(str)
    d = d.drop_duplicates("match_id")
    return ids.to_frame().merge(d, on="match_id", how="left")


def main() -> int:
    mf = population()
    C = cells(mf)
    rows = []
    names = [c for c in pq.read_schema(STORE).names if "__" in c]
    st = pd.read_parquet(STORE, columns=["match_id"] + names)
    assert (st["match_id"].astype(str).to_numpy() == mf["match_id"].to_numpy()).all()
    rows += frame_rows(st, names, "store", C)
    del st
    for label, path, keep in SOURCES:
        cols = [c for c in pq.read_schema(path).names if c not in SKIP and (keep is None or keep(c))]
        d = on_model(path, mf["match_id"], cols)
        num = [c for c in cols if pd.api.types.is_numeric_dtype(d[c]) or pd.api.types.is_bool_dtype(d[c])]
        rows += frame_rows(d, num, label, C)
    # shot-level histories: real data for both players (the plain values are prior-filled)
    p3 = S / "shot_level" / "stage3_sides.parquet"
    has = [c for c in pq.read_schema(p3).names if c.startswith("A|") and c.endswith("|has")]
    d = on_model(p3, mf["match_id"], has + ["B" + c[1:] for c in has])
    for c in has:
        ok = (pd.to_numeric(d[c], errors="coerce") > 0).to_numpy() & (pd.to_numeric(d["B" + c[1:]], errors="coerce") > 0).to_numpy()
        rows.append(row("sl3:" + c[2:-4], ok, C))
    out = pd.DataFrame(rows)
    # point sequences: the point-sequence study's own per-season table, weighted by matches
    pc = pd.read_csv(S / "point_sequence" / "coverage_model.csv")
    pc = pc[pc["year"].astype(str) != "all"].assign(year=lambda x: x["year"].astype(int))
    pc["period"] = np.select([pc["year"] <= 2021, pc["year"] <= 2024], ["p1", "p2"], "p3")
    for f in ("own_sequence", "both_ge20", "both_ge5"):
        r = {"key": f"ps:{f}"}
        for (t, p), g in pc.groupby(["tour", "period"]):
            r[f"n_{t}_{p}"] = int(g["matches"].sum())
            r[f"cov_{t}_{p}"] = round(float((g[f] * g["matches"]).sum() / g["matches"].sum()), 4)
        out = pd.concat([out, pd.DataFrame([r])], ignore_index=True)
    out.to_csv(OUT / "coverage_keys.csv", index=False)
    print(f"{len(out)} keys -> {OUT / 'coverage_keys.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
