"""Dry run of the Slam box-score overrides (docs/decisions/2026-10-06-slam-box-scores.md), away from the live tables.

Builds Stage 0 twice into a scratch folder, each in its own process: once without overrides (the baseline,
--no-box-overrides) and once with slam_box_overrides.csv. Then:
    overrides against baseline   only the override matches may change; their counts must equal the feed's, and
                                 the pooled first-serve-in rates of Wimbledon and the US Open 2026 return to the feed's
    baseline against live        what a rebuild would change anyway: stage0_build.py and repair_data.py changed after
                                 the live tables were written (code drift), reported apart from the overrides
The live tables' SHA-256 is checked before and after: they must not change.

Writes data/studies/data_continuity/stage0_dry_run.json and stage0_dry_run_changes.csv (--name changes the stem, so an
earlier run's evidence is kept).
Run: ./python.sh src/eda/data_continuity/stage0_dry_run.py --scratch <folder outside data/studies/predictability_diagnostic>
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_continuity import common as K  # noqa: E402

BUILD = "src/eda/predictability_diagnostic/stage0_build.py"
LIVE = [K.STAGE0 / "stage0_matches.parquet", K.STAGE0 / "stage0_match_players.parquet"]
OVERRIDES = K.OUT / "slam_box_overrides.csv"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build(out: Path, overrides: Path | None) -> float:
    t0 = time.time()
    cmd = [sys.executable, BUILD, "--out-dir", str(out)] + (["--box-overrides", str(overrides)] if overrides
                                                             else ["--no-box-overrides"])
    print("-->", " ".join(cmd), flush=True)
    done = subprocess.run(cmd, cwd=K.ROOT)
    if done.returncode != 0:
        raise SystemExit(f"build failed: {' '.join(cmd)}")
    return round(time.time() - t0, 1)


def changed_rows(a: pd.DataFrame, b: pd.DataFrame, keys: list[str]) -> tuple[pd.DataFrame, pd.Series]:
    """Rows present in both whose values differ (NaN equals NaN), and how many rows each column changes."""
    cols = [c for c in a.columns if c in b.columns and c not in keys]
    j = a.merge(b, on=keys, suffixes=("_a", "_b"))
    diff = pd.DataFrame({c: ~((j[f"{c}_a"] == j[f"{c}_b"]) | (j[f"{c}_a"].isna() & j[f"{c}_b"].isna()))
                         for c in cols})
    return j[diff.any(axis=1)], diff.sum().loc[lambda s: s > 0].sort_values(ascending=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scratch", required=True, help="folder for the two builds (not the live Stage 0 folder)")
    ap.add_argument("--name", default="stage0_dry_run", help="stem of the two output files")
    a = ap.parse_args()
    scratch = Path(a.scratch).resolve()
    if scratch == K.STAGE0.resolve() or K.STAGE0.resolve() in scratch.parents:
        raise SystemExit("the scratch folder must be outside the live Stage 0 folder")
    live_before = {p.name: sha(p) for p in LIVE}
    base, over = scratch / "baseline", scratch / "overrides"
    seconds = {"baseline": build(base, None), "overrides": build(over, OVERRIDES)}
    live_after = {p.name: sha(p) for p in LIVE}

    ov = pd.read_csv(OVERRIDES, dtype=str, keep_default_na=False)
    mb, pb = pd.read_parquet(base / "stage0_matches.parquet"), pd.read_parquet(base / "stage0_match_players.parquet")
    mo, po = pd.read_parquet(over / "stage0_matches.parquet"), pd.read_parquet(over / "stage0_match_players.parquet")
    targets = set(ov["stage0_match_id"])

    same_ids = set(mb["match_id"]) == set(mo["match_id"])
    m_rows, m_cols = changed_rows(mb, mo, ["match_id"])
    p_rows, p_cols = changed_rows(pb, po, ["match_id", "player_id"])
    touched = set(m_rows["match_id"]) | set(p_rows["match_id"])
    outside = sorted(touched - targets)

    # after the overrides, Stage 0's counts against the feed's (oriented by Stage 0's winner)
    won = po[po["match_id"].isin(targets)].merge(mo[["match_id", "tour", "tournament_name"]], on="match_id")
    feed_rows = []
    for side, flag in (("w", True), ("l", False)):
        f = ov[["stage0_match_id"] + [f"{side}_{c}" for c in K.SACKMANN_NAMES.values()]].copy()
        f.columns = ["match_id"] + list(K.SACKMANN_NAMES)
        feed_rows.append(f.assign(won=flag))
    feed = pd.concat(feed_rows)
    for c in K.SACKMANN_NAMES:
        feed[c] = pd.to_numeric(feed[c], errors="coerce")
    cmp = won.merge(feed, on=["match_id", "won"], suffixes=("", "_feed"))
    equal = {c: round(float(((cmp[c] == cmp[f"{c}_feed"]) | (cmp[c].isna() & cmp[f"{c}_feed"].isna())).mean()), 4)
             for c in K.SACKMANN_NAMES}

    def first_in_pct(mp: pd.DataFrame, m: pd.DataFrame) -> dict:
        x = mp[mp["match_id"].isin(targets)].merge(m[["match_id", "tour", "tournament_name", "qualifying"]], on="match_id")
        g = x.groupby(["tournament_name", "tour", "qualifying"])[["first_in", "svpt"]].sum()
        return {f"{t}|{tour}|{'Q' if q else 'main'}": round(100 * r.first_in / r.svpt, 2)
                for (t, tour, q), r in g.iterrows() if r.svpt > 0}

    # what changed per override match (the counts that moved, before and after)
    rows = []
    for mid, g in p_rows[p_rows["match_id"].isin(targets)].groupby("match_id"):
        for r in g.itertuples():
            rows.append({"match_id": mid, "player_id": r.player_id,
                         **{f"{c}_before": getattr(r, f"{c}_a") for c in K.COUNTS},
                         **{f"{c}_after": getattr(r, f"{c}_b") for c in K.COUNTS}})
    pd.DataFrame(rows).to_csv(K.OUT / f"{a.name}_changes.csv", index=False)

    # code drift: the baseline build against the live tables
    ml, pl = pd.read_parquet(LIVE[0]), pd.read_parquet(LIVE[1])
    d_rows, d_cols = changed_rows(ml, mb, ["match_id"])
    dp_rows, dp_cols = changed_rows(pl, pb, ["match_id", "player_id"])
    drift = {"live_matches": int(len(ml)), "baseline_matches": int(len(mb)),
             "only_in_live": int(len(set(ml["match_id"]) - set(mb["match_id"]))),
             "only_in_baseline": int(len(set(mb["match_id"]) - set(ml["match_id"]))),
             "matches_changed": int(len(d_rows)), "match_columns_changed": d_cols.head(15).astype(int).to_dict(),
             "player_rows_changed": int(len(dp_rows)), "player_columns_changed": dp_cols.head(15).astype(int).to_dict(),
             "changed_by_year": d_rows.groupby("year_a").size().astype(int).to_dict() if "year_a" in d_rows else {}}

    result = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "build_seconds": seconds,
        "live_tables_unchanged": live_before == live_after, "live_sha256": live_after,
        "overrides": int(len(ov)), "override_matches_in_stage0": int(len(targets & set(mo["match_id"]))),
        "same_match_ids": same_ids,
        "matches_changed": int(len(m_rows)), "match_columns_changed": m_cols.astype(int).to_dict(),
        "player_rows_changed": int(len(p_rows)), "player_columns_changed": p_cols.head(25).astype(int).to_dict(),
        "changed_outside_overrides": outside[:50], "changed_outside_overrides_count": len(outside),
        "stage0_equals_feed_after_overrides": equal,
        "first_in_pct_baseline": first_in_pct(pb, mb), "first_in_pct_overrides": first_in_pct(po, mo),
        "box_status_after": mo[mo["match_id"].isin(targets)]["box_status"].value_counts().to_dict(),
        "box_status_before": mb[mb["match_id"].isin(targets)]["box_status"].value_counts().to_dict(),
        "scores_after": mo[mo["match_id"].isin(targets) & ~mo["match_id"].map(
            mb.set_index("match_id")["score"]).eq(mo["score"])][["match_id", "score", "status", "minutes"]]
        .to_dict("records"),
        "code_drift_baseline_vs_live": drift,
        "pass": bool(live_before == live_after and same_ids and not outside and min(equal.values()) >= 0.99),
    }
    K.write_json(K.OUT / f"{a.name}.json", result)
    print({k: result[k] for k in ("live_tables_unchanged", "same_match_ids", "matches_changed", "player_rows_changed",
                                  "changed_outside_overrides_count", "pass")})
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
