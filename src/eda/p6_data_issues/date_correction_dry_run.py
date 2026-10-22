"""The Tenerife date correction (D1), proposed as a table and dry-run on today's sources (owner, 14 Oct 2026;
docs/decisions/2026-10-14-p6-data-issues.md, point 1).

    1. The table: the three reviewers' 31 matches (stage0_review/consensus.json), each named as the corrections module's
       date table names a match (source file, tournament id, round, both players, as Tennis My Life writes them today),
       with the date it replaces (20240121) and the true one (20240226). Written to
       data/studies/p6_data_issues/stage0_review/date_corrections.csv; every row checked against today's raw file
       (exactly one row each).
    2. The dry run: Stage 0 built twice from today's sources into scratch folders (stage0_build.py --out-dir), with the
       decided corrections and with them plus this table (--corrections-dir: a scratch copy of the decided folder and
       the table). The two must differ in exactly the 31 matches' tournament_date (and the order numbers that follow),
       every other fact equal.
Nothing in the repository's tables or the decided folder changes. Writes stage0_review/dry_run.json.

Run: ./python.sh src/eda/p6_data_issues/date_correction_dry_run.py --scratch <folder>     (two Stage 0 builds, minutes)
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "data" / "studies" / "p6_data_issues" / "stage0_review"
FIXES = ROOT / "data" / "studies" / "input_data_audit" / "fixes"
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
OLD, NEW = "20240121", "20240226"


def proposed_table() -> pd.DataFrame:
    ids = json.loads((REVIEW / "consensus.json").read_text(encoding="utf-8"))["G1"]["rows"]
    s0 = pd.read_parquet(STAGE0, columns=["match_id", "source_file", "tournament_id"])
    s0 = s0[s0["match_id"].isin(ids)]
    if len(s0) != len(ids) or s0["source_file"].nunique() != 1:
        raise SystemExit(f"Stage 0 holds {len(s0)} of the {len(ids)} matches, or in more than one file")
    src = s0["source_file"].iloc[0]
    raw = pd.read_csv(ROOT / src, dtype=str, keep_default_na=False)
    raw = raw[raw["tourney_id"].eq("2024-2847") & raw["tourney_date"].eq(OLD)]
    rows = []
    # each match by its round and the two players' Stage 0 ids' names in the raw file: link through Stage 0's players
    mp = pd.read_parquet(ROOT / "data/studies/predictability_diagnostic/stage0_match_players.parquet",
                         columns=["match_id", "player_name", "won"])
    mp = mp[mp["match_id"].isin(ids)]
    for mid, g in mp.groupby("match_id"):
        w, lo = g.loc[g["won"].astype(bool), "player_name"].iloc[0], g.loc[~g["won"].astype(bool), "player_name"].iloc[0]
        rnd = mid.split("|")[2]
        hit = raw[raw["round"].str.upper().eq(rnd) & raw["winner_name"].eq(w) & raw["loser_name"].eq(lo)]
        if len(hit) != 1:
            raise SystemExit(f"{mid}: {len(hit)} raw rows read {rnd} {w} d. {lo} on {OLD}")
        r = hit.iloc[0]
        rows.append({"fix": "D1", "action": "set_tourney_date", "match_id": mid, "source_file": src,
                     "tourney_id": r["tourney_id"], "round": r["round"], "winner_name": r["winner_name"],
                     "loser_name": r["loser_name"], "old_value": OLD, "value": NEW,
                     "evidence": "three reviewers, 14 Oct 2026: data/studies/p6_data_issues/stage0_review/consensus.json"})
    return pd.DataFrame(rows).sort_values("match_id").reset_index(drop=True)


def build(out: Path, corrections: Path | None) -> int:
    args = [sys.executable, "src/eda/predictability_diagnostic/stage0_build.py", "--out-dir", str(out)]
    if corrections is not None:
        args += ["--corrections-dir", str(corrections)]
    with (out.parent / f"{out.name}.log").open("w", encoding="utf-8") as fh:
        return subprocess.run(args, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--scratch", required=True)
    a = ap.parse_args()
    scratch = Path(a.scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    table = proposed_table()
    table.to_csv(REVIEW / "date_corrections.csv", index=False)
    fixes = scratch / "fixes_with_dates"
    if fixes.exists():
        raise SystemExit(f"{fixes} exists: give a fresh --scratch (nothing is deleted)")
    shutil.copytree(FIXES, fixes, ignore=shutil.ignore_patterns("*.parquet", "*.json"))
    table.drop(columns=["evidence"]).to_csv(fixes / "date_corrections.csv", index=False)
    rec = {"table_rows": int(len(table)), "table": str((REVIEW / "date_corrections.csv").relative_to(ROOT))}
    for name, corr in (("without", None), ("with", fixes)):
        out = scratch / name
        out.mkdir(exist_ok=True)
        rec[f"build_{name}"] = build(out, corr)
        if rec[f"build_{name}"]:
            (REVIEW / "dry_run.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
            raise SystemExit(f"the build {name} failed (log {out}.log)")
    a_, b_ = (pd.read_parquet(scratch / n / "stage0_matches.parquet").set_index("match_id").sort_index()
              for n in ("without", "with"))
    pa, pb = (pd.read_parquet(scratch / n / "stage0_match_players.parquet").sort_values(["match_id", "side"])
              .reset_index(drop=True) for n in ("without", "with"))
    other = [c for c in a_.columns if c not in ("order", "tournament_date")]
    date_diff = a_.index[(a_["tournament_date"] != b_["tournament_date"]).to_numpy()]
    rec.update(same_matches=bool(a_.index.equals(b_.index)), other_columns_equal=bool(a_[other].equals(b_[other])),
               players_equal=bool(pa.equals(pb)), dates_changed=int(len(date_diff)),
               dates_changed_are_the_31=bool(set(date_diff) == set(table["match_id"])),
               new_dates=sorted({str(d.date()) for d in b_.loc[date_diff, "tournament_date"]}),
               order_numbers_changed=int((a_["order"] != b_["order"]).sum()))
    summ = json.loads((scratch / "with" / "stage0_summary.json").read_text(encoding="utf-8"))
    rec["build_summary_date_corrections"] = summ.get("date_corrections")
    (REVIEW / "dry_run.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(json.dumps(rec, indent=1, default=str))
    ok = rec["same_matches"] and rec["other_columns_equal"] and rec["players_equal"] and rec["dates_changed_are_the_31"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
