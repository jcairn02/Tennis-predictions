"""Snapshot the two audited studies and collect their published feature scores.

Read-only with respect to the original studies. Run through ./python.sh.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "data/studies/feature_alpha_audit"
STUDIES = ("predictability_diagnostic", "ufc_ideas")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if "--verify" in sys.argv:
        original = pd.read_csv(OUT / "input_manifest.csv")
        changed = [row.path for row in original.itertuples()
                   if not (ROOT / row.path).exists() or digest(ROOT / row.path) != row.sha256]
        result = {"checked_original_files": len(original), "changed": changed}
        (OUT / "original_unchanged.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result))
        if changed:
            raise SystemExit(1)
        return
    manifest = []
    for study in STUDIES:
        for parent in ("docs/studies", "src/eda", "data/studies", "test"):
            for path in sorted((ROOT / parent / study).rglob("*")):
                if not path.is_file() or "__pycache__" in path.parts:
                    continue
                if path.suffix not in {".py", ".md", ".html", ".csv", ".json", ".parquet"}:
                    continue
                manifest.append({"path": path.relative_to(ROOT).as_posix(),
                                 "bytes": path.stat().st_size, "sha256": digest(path)})
    pd.DataFrame(manifest).to_csv(OUT / "input_manifest.csv", index=False)
    records = []
    for study in STUDIES:
        for path in sorted((ROOT / "data/studies" / study).glob("*ranking.csv")):
            if path.name.startswith("_"):
                continue
            table = pd.read_csv(path).copy()
            table.insert(0, "study", study)
            table.insert(1, "source_table", path.name)
            records.append(table)
    rank = pd.concat(records, ignore_index=True, sort=False)
    keep = ["study", "source_table", "tour", "id", "form", "name", "inputs", "reading"]
    for prefix in ("elo", "market", "ratings"):
        keep += [f"{prefix}_{suffix}" for suffix in
                 ("imp", "lo", "hi", "2019-2026", "2022-2026", "scored", "coverage", "clears_line")]
    rank[[c for c in keep if c in rank]].to_csv(OUT / "original_scores.csv", index=False)
    selected = rank[(rank["id"].isin(["rating_matchup", "elo_games", "sets_14d", "surface_first", "age",
                                    "adjperf_tpw", "ios_matchup_points", "profile_adjperf", "everything"]))]
    selected[[c for c in keep if c in rank]].to_csv(OUT / "shortlist_original_scores.csv", index=False)
    meta = {"audit_date": "2026-10-02", "original_files": len(manifest),
            "ranking_rows_including_repeated_baseline_tests": len(rank),
            "original_files_modified": False,
            "interpretation": "All periods have previously been explored. 2019+ avoids feature-constant tuning years, but is not a new holdout.",
            "units": "milli-log-loss; +1 is a reduction of 0.001 in mean natural-log loss, not an ROI or accuracy percentage"}
    (OUT / "audit_inputs.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta))


if __name__ == "__main__":
    main()
