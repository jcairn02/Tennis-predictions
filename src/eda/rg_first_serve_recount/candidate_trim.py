"""Trim a candidate Stage 0 built in the sandbox to the live Stage 0 plus the candidate's own changes, for the harm check
of the Roland Garros candidate (decision of 9 Oct 2026: docs/decisions/2026-10-09-roland-garros-box-scores.md, point 2).

A sandbox Stage 0 build reads today's source files, so besides the candidate's tables it brings matches played since the
live build (and newer box scores of recent ones). The frozen timeline has no entry for those, and rebuilding it would
re-link match days from source folders that changed since the freeze. So the build is trimmed: matches the live Stage 0
lacks are dropped, and any match whose rows changed although no candidate table names it is restored from the live
tables. What is left differs from the live Stage 0 only in the matches the candidate's tables name.

Writes the sandbox's stage0_matches.parquet and stage0_match_players.parquet in place, and <out>/candidate_trim.json:
the matches dropped and restored, the matches the tables name and those that changed, and the SHA-256 before and after.
Usage: ./python.sh src/eda/rg_first_serve_recount/candidate_trim.py --sandbox C:/Users/zerom/tnr_sb --out <folder>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
LIVE = ROOT / "data" / "studies" / "predictability_diagnostic"
CANDIDATE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "confirmed" / "candidate"
TABLES = ("stage0_matches.parquet", "stage0_match_players.parquet")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def named_matches() -> set[str]:
    """The Stage 0 matches the candidate's tables name: the override rows and the correction rows."""
    ov = pd.read_csv(CANDIDATE / "slam_box_overrides.csv", dtype=str, keep_default_na=False)
    rc = pd.read_csv(CANDIDATE / "corrections" / "row_corrections.csv", dtype=str, keep_default_na=False)
    return set(ov["stage0_match_id"]) | set(rc["match_id"])


def changed(live: pd.DataFrame, cand: pd.DataFrame, key: list[str]) -> set[str]:
    """Match ids whose rows differ between two versions of a table (rows of both, compared column by column)."""
    j = live.merge(cand, on=key, suffixes=("_l", "_c"))
    diff = np.zeros(len(j), dtype=bool)
    for c in [c for c in live.columns if c not in key]:
        a, b = j[f"{c}_l"], j[f"{c}_c"]
        same = (a == b).astype("boolean").fillna(False).to_numpy(dtype=bool) | (a.isna() & b.isna()).to_numpy()
        diff |= ~same
    return set(j.loc[diff, "match_id"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sandbox", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    sb = Path(a.sandbox) / "data" / "studies" / "predictability_diagnostic"
    if sb.resolve() == LIVE.resolve():
        raise SystemExit("the sandbox must not be the repository")
    named = named_matches()
    record: dict = {"sha256_before": {t: sha(sb / t) for t in TABLES}}
    lm, lp = (pd.read_parquet(LIVE / t) for t in TABLES)
    cm, cp = (pd.read_parquet(sb / t) for t in TABLES)
    new = set(cm["match_id"]) - set(lm["match_id"])
    if set(lm["match_id"]) - set(cm["match_id"]):
        raise SystemExit("the candidate lacks matches of the live Stage 0; it is not a trim case")
    cm, cp = cm[~cm["match_id"].isin(new)], cp[~cp["match_id"].isin(new)]
    moved = changed(lm, cm, ["match_id"]) | changed(lp, cp, ["match_id", "player_id"])
    restore = sorted(moved - named)
    cm = pd.concat([cm[~cm["match_id"].isin(restore)], lm[lm["match_id"].isin(restore)]])
    cp = pd.concat([cp[~cp["match_id"].isin(restore)], lp[lp["match_id"].isin(restore)]])
    order_m = pd.Series(np.arange(len(lm)), index=lm["match_id"])                # the live tables' row order
    cm = cm.iloc[np.argsort(order_m.loc[cm["match_id"]].to_numpy(), kind="stable")]
    lp_key = lp["match_id"] + "|" + lp["player_id"].astype(str)
    order_p = pd.Series(np.arange(len(lp)), index=lp_key)
    cp = cp.iloc[np.argsort(order_p.loc[cp["match_id"] + "|" + cp["player_id"].astype(str)].to_numpy(), kind="stable")]
    for t, df, ref in (("stage0_matches.parquet", cm, lm), ("stage0_match_players.parquet", cp, lp)):
        df = df.reset_index(drop=True).astype(ref.dtypes.to_dict())
        df.to_parquet(sb / t, index=False)
    after = changed(lm, cm, ["match_id"]) | changed(lp, cp, ["match_id", "player_id"])
    record.update({
        "dropped_new_matches": sorted(new), "restored_from_live": restore,
        "matches_named_by_the_tables": len(named), "matches_changed_after_the_trim": len(after),
        "changed_matches_not_named": sorted(after - named),
        "sha256_after": {t: sha(sb / t) for t in TABLES}})
    out = Path(a.out) if Path(a.out).is_absolute() else ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    (out / "candidate_trim.json").write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 12 else f"{len(v)} items") for k, v in record.items()},
                     indent=1))
    return 1 if record["changed_matches_not_named"] else 0


if __name__ == "__main__":
    sys.exit(main())
