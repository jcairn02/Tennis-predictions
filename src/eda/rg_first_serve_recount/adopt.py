"""Put the adopted Roland Garros candidate's tables in place of the decided ones (decision of 9 Oct 2026,
docs/decisions/2026-10-09-roland-garros-box-scores.md, point 2; its harm check of 10 Oct found no harm).

The candidate's tables are the decided tables of 6 and 8 Oct with the confirmed rows added
(data/studies/rg_first_serve_recount/followup/confirmed/candidate/). Adopting them is a swap, not a rebuild: Stage 0
changes only when it is next built, and the live tables are rebuilt in one coordinated run
(src/eda/data_continuity/rebuild_stage0.py), together with this swap, at a time no study is building on them.

    --check    (default) whether each decided table still holds every row of the candidate's base, unchanged, so the
               swap adds the confirmed rows and nothing else; reads no result
    --apply    after a passing check: copies the decided tables into
               data/studies/rg_first_serve_recount/adoption/<stamp>/replaced/ with their SHA-256, then writes the
               candidate's tables in their place; adoption.json records both sides' hashes
    --restore <stamp>   puts back what that --apply replaced

After --apply: ./python.sh src/eda/data_continuity/rebuild_stage0.py, then ./python.sh src/eda/current_best_model/history.py
(the main-tour differences it lists must be the candidate's matches).
Usage: ./python.sh src/eda/rg_first_serve_recount/adopt.py [--check | --apply | --restore <stamp>]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
CANDIDATE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "confirmed" / "candidate"
OUT = ROOT / "data" / "studies" / "rg_first_serve_recount" / "adoption"
# decided table -> the candidate's table that replaces it
TABLES = {
    ROOT / "data" / "studies" / "data_continuity" / "slam_box_overrides.csv": CANDIDATE / "slam_box_overrides.csv",
    ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "row_corrections.csv":
        CANDIDATE / "corrections" / "row_corrections.csv",
    ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "id_aliases.csv": CANDIDATE / "corrections" / "id_aliases.csv",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def compare(decided: pd.DataFrame, candidate: pd.DataFrame) -> dict:
    """Does the candidate hold every decided row, unchanged? Rows are compared on the decided table's columns; a column
    only the candidate has (the overrides' "source") must read blank or "tml" on those rows, as the decided table
    implies."""
    missing_cols = [c for c in decided.columns if c not in candidate.columns]
    if missing_cols:
        return {"ok": False, "reason": f"the candidate lacks the decided columns {missing_cols}"}
    extra = [c for c in candidate.columns if c not in decided.columns]
    cols = list(decided.columns)
    want = decided[cols].value_counts()
    have = candidate[cols].value_counts()
    short = want.subtract(have.reindex(want.index, fill_value=0))
    lost = int(short[short > 0].sum())
    if lost:
        return {"ok": False, "reason": f"{lost} decided rows are not in the candidate unchanged",
                "decided_rows": int(len(decided)), "candidate_rows": int(len(candidate))}
    if "source" in extra:
        keyed = candidate.merge(decided[cols].drop_duplicates(), on=cols, how="inner")
        bad = sorted(set(keyed["source"]) - {"", "tml"})
        if bad:
            return {"ok": False, "reason": f"decided rows carry the source(s) {bad} in the candidate"}
    return {"ok": True, "decided_rows": int(len(decided)), "candidate_rows": int(len(candidate)),
            "rows_added": int(len(candidate) - len(decided)), "columns_added": extra}


def check(tables: dict[Path, Path] = TABLES) -> dict:
    out = {"tables": [], "ready": True}
    for decided, cand in tables.items():
        row = {"decided": rel(decided), "candidate": rel(cand), "decided_sha256": sha(decided),
               "candidate_sha256": sha(cand)}
        row["identical"] = row["decided_sha256"] == row["candidate_sha256"]
        row.update({"ok": True} if row["identical"] else compare(read(decided), read(cand)))
        out["ready"] &= row["ok"]
        out["tables"].append(row)
    return out


def apply(tables: dict[Path, Path] = TABLES, out_dir: Path = OUT) -> Path:
    res = check(tables)
    if not res["ready"]:
        raise SystemExit("not applied: " + "; ".join(f"{t['decided']}: {t.get('reason')}" for t in res["tables"]
                                                     if not t["ok"]))
    stamp = time.strftime("%Y%m%dT%H%M%S")
    folder = out_dir / stamp
    kept = folder / "replaced"
    kept.mkdir(parents=True)
    for decided, cand in tables.items():
        if sha(decided) == sha(cand):
            continue
        dst = kept / rel(decided)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(decided, dst)
        if sha(dst) != sha(decided):
            raise SystemExit(f"the kept copy of {rel(decided)} does not match it; nothing replaced")
    for decided, cand in tables.items():
        if sha(decided) != sha(cand):
            shutil.copy2(cand, decided)
    res.update({"applied_at": stamp, "kept": rel(kept),
                "after": {rel(d): sha(d) for d in tables}, "next": [
                    "./python.sh src/eda/data_continuity/rebuild_stage0.py (coordinated with the studies on Stage 0)",
                    "./python.sh src/eda/current_best_model/history.py (main-tour differences: the candidate's matches)"]})
    (folder / "adoption.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return folder


def restore(stamp: str, out_dir: Path = OUT, root: Path = ROOT) -> list[str]:
    kept = out_dir / stamp / "replaced"
    if not kept.is_dir():
        raise SystemExit(f"no kept tables at {kept}")
    done = []
    for f in sorted(p for p in kept.rglob("*") if p.is_file()):
        dst = root / f.relative_to(kept)
        shutil.copy2(f, dst)
        done.append(rel(dst))
    return done


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = ap.add_mutually_exclusive_group()
    which.add_argument("--check", action="store_true")
    which.add_argument("--apply", action="store_true")
    which.add_argument("--restore", metavar="STAMP")
    a = ap.parse_args()
    if a.restore:
        print("restored: " + ", ".join(restore(a.restore)))
        return 0
    if a.apply:
        folder = apply()
        print(f"applied; kept copies and adoption.json in {rel(folder)}")
        print("next: rebuild_stage0.py (coordinated), then history.py")
        return 0
    res = check()
    print(json.dumps(res, indent=1))
    return 0 if res["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
