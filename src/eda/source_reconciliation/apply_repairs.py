"""The source reconciliation's repairs the owner approved on 22 Oct 2026, written into the decided correction tables
(docs/decisions/2026-10-22-source-reconciliation-repairs.md; the evidence: docs/studies/source_reconciliation/).

Every Stage 0 build applies the decided tables (stage0_build.py), so a repair written here reaches the next build of
the shared tables (the notebook's B6), every prediction run's own Stage 0, and the next retrain's training rows.

    SRS1   exchange_svgms   122 Slam matches whose two service-game counts are the point record's exchanged
                            (box/slam_svgms_candidates.csv; README § 2.3, S1)
    SRO1   replace_box      71 matches whose tour's own box and point record agree with each other and not with
                            Stage 0 (box/official_candidates.csv without the 3 that differ only on the first-serve
                            split; README § 2.3, O1)
    SRRET  mark_retired     8 frame matches filed as completed that every source and the WTA's own record call
                            retirements (context/results_contradicted.csv; README § 3.1)
    SRLVL  set_level        15 editions at the wrong level (context/level_main_tour_verdicts.csv; README § 3.2)
    SRSRF  set_surface      WTA Paris 2010-14 filed as carpet, hard by the WTA, tennis-data and Flashscore
                            (context/surface_events.csv; README § 3.2: 2013-14 in the frame)
The first three go into row_corrections.csv (named by source row, guarded by what the row writes), the last two into
event_corrections.csv (named by event, guarded by the value they replace).

Before writing, every repair is checked against today's sources: each row named exactly once in its staged file with
the guards the table gives; the raw row still reads what the repair replaces (S1: the service games exchanged against
the point record's; O1: Stage 0's counts; the statuses: the score without a marker); no row already carries a
correction of the same kind; each event exists in the live Stage 0 with the name, season and value replaced.

    ./python.sh src/eda/source_reconciliation/apply_repairs.py --check      re-check only, write nothing
    ./python.sh src/eda/source_reconciliation/apply_repairs.py --write      the checks, then the tables (copies of
                                                                            the tables they replace kept first)
Writes data/studies/source_reconciliation/applied/: repairs.csv (every repair with its evidence pointer),
applied.json (counts, the checks, the tables' SHA-256 before and after), row_corrections_before.csv and, when the event
table existed, event_corrections_before.csv.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.input_data_audit import corrections as COR  # noqa: E402
from src.eda.source_reconciliation import common as C  # noqa: E402

APPLIED = C.OUT / "applied"
CTX = C.OUT / "context"
BOX = C.OUT / "box"
LIVE_S0 = C.STUDIES / "predictability_diagnostic" / "stage0_matches.parquet"
FIX = {"s1": "SRS1", "o1": "SRO1", "ret": "SRRET", "level": "SRLVL", "surface": "SRSRF"}
DECISION = "docs/decisions/2026-10-22-source-reconciliation-repairs.md"
SACK = list(COR.COUNTS)
ROW_COLS = ["fix", "action", "match_id", "source_file", "source_row", "tourney_id", "round", "winner_name",
            "loser_name", "side", "value"] + [f"{s}_{c}" for s in ("w", "l") for c in SACK]
EVENT_COLS = ["fix", "action", "source", "tour", "tournament_id", "tourney_name", "year", "old_value", "value",
              "frame_matches", "basis"]
PARIS_YEARS = (2010, 2011, 2012, 2013, 2014)


def staged_rows(files: set[str]) -> pd.DataFrame:
    """The staged copies of the named Sackmann files: guards, score, counts, keyed '<source file>#<row>'."""
    parts = []
    for f in sorted(files):
        if "sackmann_archive" not in f:
            raise SystemExit(f"{f}: not a Sackmann file (the repairs name Sackmann rows only)")
        tour = "atp" if "/atp/" in f else "wta"
        staged = C.DUMP / "matches" / "sackmann_archive" / tour / (Path(f).stem + ".parquet")
        cols = ["tourney_id", "tourney_name", "round", "winner_name", "loser_name", "score", "_source_file", "_row"] + \
            [f"{s}_{c}" for s in ("w", "l") for c in SACK]
        parts.append(pd.read_parquet(staged, columns=cols))
    raw = pd.concat(parts, ignore_index=True)
    raw["key"] = COR._row_key(raw["_source_file"], raw["_row"])
    if raw["key"].duplicated().any():
        raise SystemExit("a staged file names one row twice")
    return raw.set_index("key")


def located(table: pd.DataFrame, raw: pd.DataFrame, what: str) -> pd.DataFrame:
    """The raw row of each table row, guards checked: every row named exactly once, reading the table's guards."""
    key = COR._row_key(table["source_file"], table["source_row"])
    missing = key[~key.isin(raw.index)]
    if len(missing):
        raise SystemExit(f"{what}: {len(missing)} rows name no staged row (first: {missing.iloc[0]})")
    r = raw.loc[key.to_numpy()].reset_index(drop=True)
    for g in COR.ROW_GUARDS:
        bad = COR._text(r[g]).to_numpy() != COR._text(table[g]).to_numpy()
        if bad.any():
            i = int(np.flatnonzero(bad)[0])
            raise SystemExit(f"{what}: {key.iloc[i]} expects {g} {table[g].iloc[i]!r}, the row has {r[g].iloc[i]!r}")
    return r


def num(s: pd.Series) -> np.ndarray:
    return pd.to_numeric(COR._text(s).replace("", np.nan), errors="coerce").to_numpy(dtype="float64")


def same(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    return (a == b) | (np.isnan(a) & np.isnan(b))


def s1_rows() -> tuple[pd.DataFrame, dict]:
    t = pd.read_csv(BOX / "slam_svgms_candidates.csv", dtype=str, keep_default_na=False)
    raw = located(t, staged_rows(set(t["source_file"])), "S1")
    reads = same(num(raw["w_SvGms"]), num(t["x_recount_l_svgms"])) & same(num(raw["l_SvGms"]),
                                                                           num(t["x_recount_w_svgms"]))
    if not reads.all():
        raise SystemExit(f"S1: {int((~reads).sum())} raw rows no longer read the point record's service games "
                         "exchanged; rebuild the candidates")
    if not t["action"].eq("exchange_svgms").all():
        raise SystemExit("S1: an action other than exchange_svgms")
    out = t.assign(fix=FIX["s1"], side="", value="")
    for c in [f"{s}_{k}" for s in ("w", "l") for k in SACK]:
        out[c] = ""
    ev = t[["match_id"]].assign(fix=FIX["s1"], action="exchange_svgms", evidence="box/slam_svgms_candidates.csv",
                                note="the recount's service games: w " + t["x_recount_w_svgms"] + ", l "
                                + t["x_recount_l_svgms"], tour=t["x_tour"], year=t["x_year"],
                                event=t["x_tournament"])
    return out[ROW_COLS], {"rows": int(len(out)), "raw_reads_the_exchange": int(reads.sum()), "evidence": ev}


def o1_rows() -> tuple[pd.DataFrame, dict]:
    t = pd.read_csv(BOX / "official_candidates.csv", dtype=str, keep_default_na=False)
    split_only = t["x_split_only"].str.lower().eq("true")
    t = t[~split_only].reset_index(drop=True)
    raw = located(t, staged_rows(set(t["source_file"])), "O1")
    # the raw row must still read Stage 0's counts; a count Stage 0 left blank (its own checks blanked service games
    # that do not fit the score, box_scores) is not compared, as in lead_official_corrections.py
    reads = np.ones(len(t), dtype=bool)
    blanked = np.zeros(len(t), dtype=bool)
    for s in ("w", "l"):
        for c in SACK:
            x = num(t[f"x_stage0_{s}_{c}"])
            reads &= same(num(raw[f"{s}_{c}"]), x) | np.isnan(x)
            blanked |= np.isnan(x) & ~np.isnan(num(raw[f"{s}_{c}"]))
    if not reads.all():
        raise SystemExit(f"O1: {int((~reads).sum())} raw rows no longer read the counts the replacement replaces")
    new = np.column_stack([num(t[f"{s}_{c}"]) for s in ("w", "l") for c in SACK])
    if np.isnan(new).any():
        raise SystemExit("O1: a replacement lacks a count")
    out = t.assign(fix=FIX["o1"], action="replace_box", side="", value="")
    ev = t[["match_id"]].assign(fix=FIX["o1"], action="replace_box", evidence="box/official_candidates.csv (" +
                                t["x_evidence"] + ", trio " + t["x_trio"] + ")",
                                note="counts differing: " + t["x_counts_differing"], tour=t["x_tour"],
                                year=t["x_year"], event=t["x_tournament"])
    return out[ROW_COLS], {"rows": int(len(out)), "left_out_split_only": int(split_only.sum()),
                           "raw_reads_stage0": int(reads.sum()), "stage0_had_blanked_a_count": int(blanked.sum()),
                           "by_trio": t["x_trio"].value_counts().to_dict(), "evidence": ev}


def status_rows(s0: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    from src.eda.predictability_diagnostic import stage0_build as B
    rc = pd.read_csv(CTX / "results_contradicted.csv", dtype=str, keep_default_na=False)
    rc = rc[rc["field"].eq("status") & rc["stage0_value"].eq("completed")
            & rc["in_model_frame"].str.lower().eq("true")].reset_index(drop=True)
    m = s0.set_index("match_id").loc[rc["match_id"]].reset_index()
    if not m["source"].eq("sackmann").all():
        raise SystemExit("statuses: a match not from Sackmann's files")
    if not (m["status"].eq("completed").all() and (m["score"].to_numpy() == rc["stage0_score"].to_numpy()).all()):
        raise SystemExit("statuses: Stage 0 no longer reads these matches as completed with the study's score")
    t = pd.DataFrame({"source_file": m["source_file"].astype(str), "source_row": m["source_row"].astype(int).astype(str)})
    raw = staged_rows(set(t["source_file"]))
    key = COR._row_key(t["source_file"], t["source_row"])
    r = raw.loc[key.to_numpy()].reset_index(drop=True)
    score = COR._text(r["score"]).str.split().str.join(" ")
    if not (score.to_numpy() == m["score"].to_numpy()).all():
        raise SystemExit("statuses: a raw score differs from Stage 0's")
    marked = [B.status_of(*B.tokens_of(f"{s} {COR.RETIRED_MARK}")) for s in score]
    if set(marked) != {"retired"}:
        raise SystemExit(f"statuses: a marked score would not read as retired ({marked})")
    out = pd.DataFrame({"fix": FIX["ret"], "action": "mark_retired", "match_id": m["match_id"],
                        "source_file": t["source_file"], "source_row": t["source_row"],
                        "tourney_id": COR._text(r["tourney_id"]), "round": COR._text(r["round"]),
                        "winner_name": COR._text(r["winner_name"]), "loser_name": COR._text(r["loser_name"]),
                        "side": "", "value": score})
    for c in [f"{s}_{k}" for s in ("w", "l") for k in SACK]:
        out[c] = ""
    ev = rc[["match_id"]].assign(fix=FIX["ret"], action="mark_retired", evidence="context/results_contradicted.csv",
                                 note="against: " + rc["competing_values"], tour=rc["tour"], year=rc["year"],
                                 event=rc["tournament_name"] + " " + rc["round"])
    return out[ROW_COLS], {"rows": int(len(out)), "evidence": ev}


def event_rows(s0: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    lv = pd.read_csv(CTX / "level_main_tour_verdicts.csv", dtype=str, keep_default_na=False)
    lv = lv[lv["verdict"].eq("stage0_wrong")].reset_index(drop=True)
    sf = pd.read_csv(CTX / "surface_events.csv", dtype=str, keep_default_na=False)
    sf = sf[sf["tour"].eq("wta") & sf["name"].eq("Paris") & sf["s0"].eq("Carpet")
            & sf["year"].astype(int).isin(PARIS_YEARS)].reset_index(drop=True)
    if len(sf) != len(PARIS_YEARS) or set(sf["majority_without_lta"]) != {"Hard"} or set(sf["wta_official"]) != {"Hard"}:
        raise SystemExit("surface: the study's Paris rows are not the five carpet editions the WTA calls hard")
    rows, notes = [], []
    for kind, t, old_col, new_col, field in (("level", lv, "stage0_level", "right_level", "level"),
                                            ("surface", sf, "s0", "majority_without_lta", "surface")):
        for r in t.itertuples():
            tour, tid = r.ev.split("|")[:2]
            ev = s0[s0["tour"].eq(tour) & s0["tournament_id"].eq(tid)]
            if ev.empty:
                raise SystemExit(f"{kind}: {r.ev} has no matches in the live Stage 0")
            src, names, years, have = (set(ev["source"]), set(ev["tournament_name"]), set(ev["year"].astype(int)),
                                       set(ev[field].astype(str)))
            old, new = getattr(r, old_col), getattr(r, new_col)
            if src != {"sackmann"} or len(names) != 1 or years != {int(r.year)} or have != {old}:
                raise SystemExit(f"{kind}: {r.ev} reads sources {src}, names {names}, seasons {years}, {field} {have}; "
                                 f"the study expects one Sackmann edition of {r.year} at {old}")
            frame = int(r.frame_matches) if str(r.frame_matches).strip() else 0
            basis = getattr(r, "basis", "") if kind == "level" else (
                "the WTA's own record, tennis-data and Flashscore give Hard; Tennis My Life copies Sackmann's Carpet")
            rows.append({"fix": FIX[kind], "action": f"set_{kind}", "source": "sackmann", "tour": tour,
                         "tournament_id": tid, "tourney_name": names.pop(), "year": str(int(r.year)), "old_value": old,
                         "value": new, "frame_matches": str(frame), "basis": basis})
            notes.append({"match_id": "", "fix": FIX[kind], "action": f"set_{kind}",
                          "evidence": "context/level_main_tour_verdicts.csv" if kind == "level"
                          else "context/surface_events.csv", "note": f"{old} -> {new}; {basis}", "tour": tour,
                          "year": str(int(r.year)), "event": f"{rows[-1]['tourney_name']} ({tid})"})
    out = pd.DataFrame(rows, columns=EVENT_COLS)
    return out, {"levels": int(out["action"].eq("set_level").sum()), "surfaces": int(out["action"].eq("set_surface").sum()),
                 "evidence": pd.DataFrame(notes)}


def conflicts(current: pd.DataFrame, new: pd.DataFrame) -> list[str]:
    """Rows the decided table already corrects in the same family (a box correction, a score correction)."""
    fam = lambda t: np.where(t["action"].eq("mark_retired"), "score",  # noqa: E731
                             np.where(t["action"].eq("set_age"), "age", "box"))
    have = set(COR._row_key(current["source_file"], current["source_row"]) + "|" + fam(current))
    want = COR._row_key(new["source_file"], new["source_row"]) + "|" + fam(new)
    dup_new = want[want.duplicated()].tolist()
    return sorted(set(want[want.isin(have)]) | set(dup_new))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="re-check every repair, write nothing")
    g.add_argument("--write", action="store_true", help="the checks, then the decided tables")
    g.add_argument("--dry-run-dir", help="the checks, then a copy of the decided folder with the repairs, written "
                                         "here (for stage0_build.py --corrections-dir); the decided tables untouched")
    a = ap.parse_args()
    s0 = pd.read_parquet(LIVE_S0, columns=["match_id", "tour", "year", "source", "source_file", "source_row", "status",
                                           "score", "tournament_id", "tournament_name", "level", "surface"])
    s1, i1 = s1_rows()
    o1, i2 = o1_rows()
    st, i3 = status_rows(s0)
    ev, i4 = event_rows(s0)
    rows = pd.concat([s1, o1, st], ignore_index=True)
    current = pd.read_csv(COR.ROW_CORRECTIONS, dtype=str, keep_default_na=False)
    ours = current["fix"].isin(set(FIX.values()))
    if ours.any():
        raise SystemExit(f"row_corrections.csv already holds {int(ours.sum())} rows of these repairs: nothing written")
    clash = conflicts(current, rows)
    if clash:
        raise SystemExit(f"{len(clash)} rows already carry a correction of the same kind (first: {clash[:3]})")
    overlap = set(s1["match_id"]) & set(o1["match_id"])
    if overlap:
        raise SystemExit(f"S1 and O1 name the same matches: {sorted(overlap)[:3]}")
    summary = {"decision": DECISION, "s1": {k: v for k, v in i1.items() if k != "evidence"},
               "o1": {k: v for k, v in i2.items() if k != "evidence"},
               "statuses": {k: v for k, v in i3.items() if k != "evidence"},
               "events": {k: v for k, v in i4.items() if k != "evidence"},
               "row_corrections": {"rows_before": int(len(current)), "rows_added": int(len(rows)),
                                   "sha256_before": C.sha256(COR.ROW_CORRECTIONS)}}
    print({k: v for k, v in summary.items() if k != "row_corrections"} | {"rows_added": int(len(rows))})
    if a.check:
        print("checked: nothing written")
        return 0
    if a.dry_run_dir:
        d = Path(a.dry_run_dir)
        if d.resolve() == COR.FIXES.resolve():
            raise SystemExit("--dry-run-dir must not be the decided folder")
        d.mkdir(parents=True, exist_ok=True)
        for f in COR.FIXES.glob("*.csv"):
            shutil.copyfile(f, d / f.name)
        pd.concat([current, rows[current.columns]], ignore_index=True).to_csv(d / COR.ROW_CORRECTIONS.name, index=False)
        ev.to_csv(d / COR.EVENT_CORRECTIONS.name, index=False)
        print(f"dry run: the decided folder with the repairs copied to {d}")
        return 0
    APPLIED.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(COR.ROW_CORRECTIONS, APPLIED / "row_corrections_before.csv")
    if COR.EVENT_CORRECTIONS.exists():
        shutil.copyfile(COR.EVENT_CORRECTIONS, APPLIED / "event_corrections_before.csv")
        summary["event_corrections_sha256_before"] = C.sha256(COR.EVENT_CORRECTIONS)
    out = pd.concat([current, rows[current.columns]], ignore_index=True)
    out.to_csv(COR.ROW_CORRECTIONS, index=False)
    ev.to_csv(COR.EVENT_CORRECTIONS, index=False)
    back = pd.read_csv(COR.ROW_CORRECTIONS, dtype=str, keep_default_na=False)
    if not back.iloc[:len(current)].equals(current):
        raise SystemExit("row_corrections.csv: the rows kept do not read back unchanged")
    summary["row_corrections"]["sha256_after"] = C.sha256(COR.ROW_CORRECTIONS)
    summary["row_corrections"]["rows_after"] = int(len(back))
    summary["event_corrections"] = {"rows": int(len(ev)), "sha256": C.sha256(COR.EVENT_CORRECTIONS)}
    evidence = pd.concat([i1["evidence"], i2["evidence"], i3["evidence"], i4["evidence"]], ignore_index=True)
    evidence.to_csv(APPLIED / "repairs.csv", index=False)
    summary["written_at"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
    C.write_json(APPLIED / "applied.json", summary)
    print(f"written: {len(rows)} rows into {COR.ROW_CORRECTIONS.name} ({len(current)} -> {len(back)}), "
          f"{len(ev)} events into {COR.EVENT_CORRECTIONS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
