"""The reviewers' consensus on the proposed Roland-Garros and Olympic first-serve corrections (checklist item 6, step 2).

As on 8 Oct 2026 (docs/decisions/2026-10-08-corrupt-data-fixes.md), a correction is kept only where all three
independent reviewers confirmed it: the same raw row, the same side and the same three values. Each reviewer writes,
in data/studies/rg_first_serve_recount/review/<reviewer>/,
    verdict.json   {"reviewer", "lens", "classes": {"A": {"vote", ...}, "B": {...}}, ...}
    scope.csv      the sides the reviewer confirms: source_file, source_row, side (w/l), first_in, first_won,
                   second_won, with the values the reviewer derived

Writes, in data/studies/rg_first_serve_recount/:
    confirmed/confirmed_corrections.csv   the confirmed sides as replace_split rows (row_corrections.csv's columns);
                                          a side not confirmed is left blank, a row with none is left out
    confirmed/consensus.json              votes, counts by class and edition, what was dropped and why, the dry run
    confirmed/candidate_corrections/      a corrections folder for a candidate Stage 0 build: the decided tables
                                          of 8 Oct (row_corrections.csv, id_aliases.csv) with the confirmed rows
                                          appended to row_corrections.csv (stage0_build.py --corrections-dir)
Usage: ./python.sh src/eda/rg_first_serve_recount/consensus.py
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.input_data_audit import corrections as K  # noqa: E402
from src.eda.rg_first_serve_recount import propose as PR  # noqa: E402
from src.eda.rg_first_serve_recount import sources as S  # noqa: E402

REVIEW = S.STUDY / "review"
OUT = S.STUDY / "confirmed"
REVIEWERS = ("R1-rederive", "R2-skeptic", "R3-referee")
KEY = ["source_file", "source_row", "side"]
VALUES = ["first_in", "first_won", "second_won"]
SPLIT_RAW = dict(zip(VALUES, K.SPLIT_COUNTS))


def proposed_sides(table: pd.DataFrame) -> pd.DataFrame:
    """The proposed table as one row per side: source_file, source_row, side, fix and the three values."""
    out = []
    for r in table.itertuples(index=False):
        d = r._asdict()
        for s in ("w", "l"):
            if pd.notna(d[f"{s}_1stIn"]) and str(d[f"{s}_1stIn"]) != "":
                out.append({"source_file": d["source_file"], "source_row": int(d["source_row"]), "side": s,
                            "fix": d["fix"], **{v: int(float(d[f"{s}_{c}"])) for v, c in SPLIT_RAW.items()}})
    return pd.DataFrame(out)


def scope_of(reviewer: str) -> pd.DataFrame:
    f = pd.read_csv(REVIEW / reviewer / "scope.csv")
    f["source_row"] = pd.to_numeric(f["source_row"]).astype(int)
    for v in VALUES:
        f[v] = pd.to_numeric(f[v]).astype(int)
    f["side"] = f["side"].astype(str).str.strip().str.lower()
    if f.duplicated(KEY).any():
        raise SystemExit(f"{reviewer}: a side named twice in scope.csv")
    return f[KEY + VALUES]


def main() -> int:
    table = pd.read_csv(S.STUDY / "proposed_corrections.csv")
    prop = proposed_sides(table)
    verdicts, scopes = {}, {}
    for r in REVIEWERS:
        verdicts[r] = json.loads((REVIEW / r / "verdict.json").read_text(encoding="utf-8"))
        scopes[r] = scope_of(r)
    agreed = prop.copy()
    report = {"proposed_sides": int(len(prop)), "per_reviewer": {}}
    for r, f in scopes.items():
        m = prop.merge(f, on=KEY, how="left", suffixes=("", f"_{r}"))       # each reviewer against the proposal
        same = np.all([m[v].eq(m[f"{v}_{r}"]) for v in VALUES], axis=0)
        named = m[f"first_in_{r}"].notna()
        report["per_reviewer"][r] = {
            "classes": {c: v.get("vote") for c, v in (verdicts[r].get("classes") or {}).items()},
            "sides_confirmed": int(len(f)), "of_proposed_with_the_same_values": int(same.sum()),
            "by_fix": m[same]["fix"].value_counts().to_dict(),
            "named_with_other_values": int((named & ~same).sum()),
            "outside_the_proposal": int(len(f.merge(prop[KEY], on=KEY, how="left", indicator=True)
                                             .query("_merge == 'left_only'")))}
        agreed = agreed.merge(m.loc[same, KEY], on=KEY)                     # the running intersection
    report["confirmed_sides"] = int(len(agreed))
    report["confirmed_by_fix"] = agreed["fix"].value_counts().to_dict()
    dropped = prop.merge(agreed[KEY], on=KEY, how="left", indicator=True).query("_merge == 'left_only'")
    report["dropped_by_fix"] = dropped["fix"].value_counts().to_dict()

    # the confirmed table: the proposed rows, with only the confirmed sides kept
    keep = agreed.set_index(["source_file", "source_row", "side"]).index
    out = table.copy()
    for s in ("w", "l"):
        named = [(sf, int(sr), s) in keep for sf, sr in zip(out["source_file"], out["source_row"])]
        blank = ~np.array(named)
        for c in ("svpt", "ace", "df") + tuple(K.SPLIT_COUNTS):
            out.loc[blank, f"{s}_{c}"] = np.nan
    out = out[out[[f"{s}_1stIn" for s in ("w", "l")]].notna().any(axis=1)].reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT / "confirmed_corrections.csv", index=False)
    report["confirmed_match_rows"] = int(len(out))
    report["dry_run"] = PR.dry_run(out) if len(out) else None

    # a corrections folder for the candidate build: the decided tables plus the confirmed rows
    cand = OUT / "candidate_corrections"
    cand.mkdir(parents=True, exist_ok=True)
    decided = pd.read_csv(K.ROW_CORRECTIONS, dtype=str, keep_default_na=False)
    both = pd.concat([decided, out.astype(object).where(out.notna(), "").astype(str)
                      .replace(r"\.0$", "", regex=True)], ignore_index=True)
    both.to_csv(cand / "row_corrections.csv", index=False)
    shutil.copy2(K.ID_ALIASES, cand / "id_aliases.csv")
    report["candidate_corrections"] = {
        "folder": (cand.relative_to(ROOT) if cand.is_relative_to(ROOT) else cand).as_posix(),
        "decided_rows": int(len(decided)), "added_rows": int(len(out)),
        "decided_row_corrections_sha256": hashlib.sha256(K.ROW_CORRECTIONS.read_bytes()).hexdigest(),
        "id_aliases_sha256": hashlib.sha256(K.ID_ALIASES.read_bytes()).hexdigest()}
    (OUT / "consensus.json").write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
