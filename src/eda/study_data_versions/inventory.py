"""Step 1 of the study data-version plan (owner, 22 Oct 2026: "start step 1 and draft the rule";
docs/studies/study_data_versions/process_log.md, section 3): a read-only inventory of which history each table under
data/studies was built on, who reads it, which code mixes versions, whether it can be recreated, and its size; and
the build folders on this machine.

    histories   every Stage 0 on disk: the repository's; the copies the shared rebuilds saved (each the history in use
                before that rebuild); the frozen reference's; each build folder's (C:/Users/zerom/tnr_*). Fingerprints:
                the file's sha256 and the match ids' (sorted, hashed), the match count, the newest tournament date
    tables      every parquet under data/studies with a match_id column, except the saved histories' folders and the
                frozen reference (each listed whole): its match ids against every history. "equals" one history's ids;
                else "inside" every history that holds all its ids (the newest and the oldest named); else "outside"
                (it holds ids no kept history has). "older" when it equals a history that is not the repository's, or
                holds ids the repository's history has since dropped
    readers     each src/ file that names a table (its stem, plus its folder's name when the stem is shared by several
                tables): static, by name, so a first pass, not proof
    mixing      a src/ file that names an older table and a live base table (Stage 0, the timeline, the odds link)
                and no saved history: flagged for reading by hand
    folders     every C:/Users/zerom/tnr_* folder: its size, whether it holds a history and its own code, and the
                documents and code that name it

Recreatable: a history or table can be rebuilt exactly only if the code that built it is kept. The repository keeps no
code version for its tables (the owner commits by hand); a build folder keeps a copy of the code it ran, and the
frozen reference keeps its code and environment. So "recreatable" is yes only for those.

Writes data/studies/study_data_versions/{histories,tables,readers,mixing,folders}.csv and summary.json, and
docs/studies/study_data_versions/index.md. Reads only: changes no table, code or study file.
Run: ./python.sh src/eda/study_data_versions/inventory.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
STUDIES = ROOT / "data" / "studies"
REBUILDS = STUDIES / "data_continuity" / "rebuilds"
REFERENCE = STUDIES / "current_best_model" / "reference_2026-10-08"
HOME = Path("C:/Users/zerom")
OUT = STUDIES / "study_data_versions"
INDEX = ROOT / "docs" / "studies" / "study_data_versions" / "index.md"
S0 = Path("data") / "studies" / "predictability_diagnostic" / "stage0_matches.parquet"
LIVE_BASE = ("stage0_matches", "stage0_match_players", "load_matches", "STAGE0", "timing.parquet", "TIMING",
             "stage1_odds")
SAVED = ("rebuilds", "replaced", "reference_2026-10-08", "frozen", "OLD")
# the model chain's builders (run_chain.py's lanes) and the daily engine: they read and write one tree's tables
# together (a build sandbox or the engine's work tree), so naming both kinds of table there is not mixing
CHAIN_ENGINE = {"predictability_diagnostic", "match_timing", "ufc_ideas", "ios_constants", "tabpfn_thinking",
                "tabpfn_leakproof", "surface_elo_pieces", "surface_ios", "surface_rating_race", "model_rebuild",
                "current_best_model", "level_layer_adoption", "daily_prediction", "prediction_pipeline",
                "prediction_run", "data_continuity"}
# the folders holding the chain's tables in the repository: the snapshot of the 7 Oct history and its neighbours
CHAIN_TABLES = {"predictability_diagnostic", "surface_ios", "surface_elo_pieces", "tabpfn_thinking",
                "tabpfn_leakproof", "ufc_ideas", "surface_rating_race"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def id_hashes(ids: pd.Series) -> np.ndarray:
    return np.unique(pd.util.hash_pandas_object(ids.astype(str), index=False).to_numpy())


def is_link(path: str) -> bool:
    """A junction or symbolic link (a build folder links data/dump and data/raw to the repository's: not its size)."""
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return bool(getattr(st, "st_file_attributes", 0) & 0x400) or os.path.islink(path)


def folder_size(p: Path) -> int:
    """The folder's own files, links not followed (Python 3.11's os.walk would descend into junctions)."""
    total = 0
    for dirpath, dirs, files in os.walk(p):
        dirs[:] = [d for d in dirs if not is_link(os.path.join(dirpath, d))]
        for f in files:
            fp = os.path.join(dirpath, f)
            if not is_link(fp):
                try:
                    total += os.path.getsize(fp)
                except OSError:
                    pass
    return total


# ------------------------------------------------------------------------------------------------ histories
def history_paths() -> list[tuple[str, str, Path]]:
    out = [("repository", "the repository's history (the shared tables)", ROOT / S0)]
    for d in sorted(REBUILDS.iterdir()) if REBUILDS.exists() else []:
        p = d / "replaced" / S0
        if p.exists():
            out.append((f"before {d.name}", f"saved by the shared rebuild of {d.name}: the history in use before it", p))
    p = REFERENCE / "frozen" / "tables" / S0
    if p.exists():
        out.append(("frozen reference", "the frozen reference of 8 Oct (kept by decision, with its code)", p))
    for d in sorted(HOME.glob("tnr_*")):
        p = d / S0
        if p.exists():
            out.append((f"folder {d.name}", f"the build folder {d.name}", p))
    return out


def load_histories() -> tuple[pd.DataFrame, dict, pd.Series]:
    rows, ids, dates = [], {}, []
    for name, what, p in history_paths():
        m = pd.read_parquet(p, columns=["match_id", "tournament_date"])
        h = pd.util.hash_pandas_object(m["match_id"].astype(str), index=False).to_numpy()
        ids[name] = np.unique(h)
        dates.append(pd.Series(pd.to_datetime(m["tournament_date"]).to_numpy(), index=h))
        rows.append({"history": name, "what": what, "path": str(p), "matches": int(len(m)),
                     "newest": str(pd.to_datetime(m["tournament_date"]).max().date()),
                     "written": dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="minutes"),
                     "file_sha256": sha256(p)[:12],
                     "ids_sha256": hashlib.sha256(ids[name].tobytes()).hexdigest()[:12]})
    h = pd.DataFrame(rows)
    same = h.groupby("ids_sha256")["history"].agg(list)
    h["same_ids_as"] = [", ".join(x for x in same[s] if x != n) for n, s in zip(h["history"], h["ids_sha256"])]
    d = pd.concat(dates)
    d = d[~d.index.duplicated(keep="first")]
    return h, ids, d


# ------------------------------------------------------------------------------------------------ tables
def table_paths() -> list[Path]:
    skip = (REBUILDS, REFERENCE)
    out = []
    for p in STUDIES.rglob("*.parquet"):
        if any(s in p.parents for s in skip):
            continue
        out.append(p)
    return sorted(out)


def held(t: np.ndarray, h: np.ndarray) -> np.ndarray:
    """Which of the sorted unique hashes t the sorted unique hashes h hold."""
    i = np.searchsorted(h, t)
    return (i < len(h)) & (h[np.minimum(i, len(h) - 1)] == t)


def classify(t: np.ndarray, hist: pd.DataFrame, ids: dict) -> dict:
    order = list(hist.sort_values("written")["history"])           # oldest first
    counts = {n: int(held(t, ids[n]).sum()) for n in order}
    equal = [n for n in order if counts[n] == len(t) == len(ids[n])]
    inside = [n for n in order if counts[n] == len(t)]
    dropped = len(t) - counts["repository"]
    if equal:
        verdict, version = "equals", equal[0]
    elif inside:
        verdict, version = "inside", f"{inside[0]} .. {inside[-1]}" if len(inside) > 1 else inside[0]
    else:
        best = max(order, key=lambda n: counts[n])
        verdict, version = "outside", f"closest {best}"
    older = (verdict == "equals" and "repository" not in equal) or (verdict != "outside" and dropped > 0)
    return {"verdict": verdict, "version": version, "equals": ", ".join(equal), "inside_n": len(inside),
            "not_in_repository": dropped, "older": bool(older)}


def scan_tables(hist: pd.DataFrame, ids: dict, dates: pd.Series) -> pd.DataFrame:
    rows = []
    for p in table_paths():
        rel = p.relative_to(ROOT).as_posix()
        base = {"table": rel, "study": p.relative_to(STUDIES).parts[0], "bytes": p.stat().st_size,
                "written": dt.datetime.fromtimestamp(p.stat().st_mtime).isoformat(timespec="minutes")}
        try:
            pf = pq.ParquetFile(p)
            names = pf.schema_arrow.names
            base["rows"] = int(pf.metadata.num_rows)
        except Exception as exc:  # noqa: BLE001 - recorded, the scan goes on
            rows.append({**base, "verdict": "unreadable", "note": f"{type(exc).__name__}: {exc}"[:200]})
            continue
        if "match_id" not in names:
            rows.append({**base, "verdict": "no match ids"})
            continue
        s = pq.read_table(p, columns=["match_id"]).column(0).to_pandas()
        t = id_hashes(s.dropna())
        if not len(t):
            rows.append({**base, "verdict": "no match ids"})
            continue
        c = classify(t, hist, ids)
        known = dates.reindex(t)
        rows.append({**base, **c, "matches": int(len(t)),
                     "newest": str(known.max().date()) if known.notna().any() else ""})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ readers and mixing
def scan_code(tables: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    files = sorted((ROOT / "src").rglob("*.py"))
    text = {f: f.read_text(encoding="utf-8", errors="ignore") for f in files}
    t = tables[tables["verdict"].isin(["equals", "inside", "outside"])].copy()
    t["stem"] = t["table"].map(lambda s: Path(s).stem)
    t["folder"] = t["table"].map(lambda s: Path(s).parent.name)
    shared = t["stem"].value_counts()
    items = [(r.stem, r.folder, shared[r.stem] > 1, r.table, r.study, r.version, bool(r.older))
             for r in t.itertuples(index=False)]
    rows = []
    for f, body in text.items():
        rel = f.relative_to(ROOT).as_posix()
        parts = f.relative_to(ROOT / "src").parts
        study = parts[1] if len(parts) > 2 else ""
        for stem, folder, is_shared, table, tstudy, version, older in items:
            if stem not in body or (is_shared and folder not in body):
                continue
            rows.append({"code": rel, "code_study": study, "table": table, "table_study": tstudy,
                         "table_version": version, "table_older": older})
    readers = pd.DataFrame(rows, columns=["code", "code_study", "table", "table_study", "table_version",
                                          "table_older"])
    mix = []
    for code, g in readers.groupby("code"):
        body = text[ROOT / code]
        older = g[g["table_older"].astype(bool)]
        live = [k for k in LIVE_BASE if re.search(rf"\b{re.escape(k)}", body)]
        saved = [k for k in SAVED if k in body]
        if len(older) and live and not saved:
            chain = older[older["table_study"].isin(CHAIN_TABLES)]
            likely = bool(len(chain)) and g["code_study"].iloc[0] not in CHAIN_ENGINE
            note = ""
            if likely:      # a second static signal: the table's file named (not only its module), a model folder named
                if re.search(r"tnr_|base_tree|BASE_TREE|selected_instance", body):
                    note = "names a model folder: probably consistent (a static guess)"
                elif any(Path(t).name in body for t in chain["table"]):
                    note = "names a snapshot table's file and a live base table: a candidate"
                else:
                    note = "names the module only: probably not reading the table"
            mix.append({"code": code, "strength": "likely" if likely else "weak",
                        "older_tables": "; ".join(sorted(set((chain if likely else older)["table"])))[:400],
                        "older_versions": "; ".join(sorted(set(older["table_version"]))),
                        "live_base_named": ", ".join(live),
                        "verdict": "not read" if likely else "weak: not read", "note": note})
    return readers, pd.DataFrame(mix, columns=["code", "strength", "older_tables", "older_versions",
                                               "live_base_named", "verdict", "note"])


# ------------------------------------------------------------------------------------------------ folders
def scan_folders(hist: pd.DataFrame) -> pd.DataFrame:
    docs = [p for p in (ROOT / "docs").rglob("*.md")] + [p for p in (ROOT / "src").rglob("*.py")]
    doc_text = {p: p.read_text(encoding="utf-8", errors="ignore") for p in docs}
    sel = json.loads((STUDIES / "master_pipeline" / "selected_instance.json").read_text(encoding="utf-8"))
    rv = STUDIES / "daily_prediction" / "replay_views.json"
    replay = rv.read_text(encoding="utf-8") if rv.exists() else ""
    rows = []
    for d in sorted(HOME.glob("tnr_*")):
        named = [p.relative_to(ROOT).as_posix() for p, b in doc_text.items() if d.name in b]
        h = hist[hist["history"] == f"folder {d.name}"]
        rows.append({"folder": str(d), "bytes": folder_size(d), "holds_history": bool(len(h)),
                     "history_matches": int(h["matches"].iloc[0]) if len(h) else None,
                     "holds_code": (d / "src").exists(), "selected_instance": sel.get("tree", "").rstrip("/").endswith(d.name),
                     "in_replay_registry": d.name in replay, "named_by": len(named),
                     "named_by_examples": "; ".join(named[:6])})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ the index page
def gb(n) -> str:
    return f"{n / 1e9:.1f} GB" if n >= 1e8 else f"{n / 1e6:.0f} MB"


def write_index(hist, tables, readers, mix, folders, when) -> str:
    t = tables[tables["verdict"].isin(["equals", "inside", "outside"])]
    per = t.groupby(["verdict", "version"]).agg(tables=("table", "size"), bytes=("bytes", "sum")).reset_index()
    per = per.sort_values("bytes", ascending=False)
    lines = [
        "# Which data each table was built on: the index",
        "",
        f"Generated {when} by `src/eda/study_data_versions/inventory.py` (read-only). Do not edit by hand: run the script.",
        "Owner's request and the plan: [process log](process_log.md); the rule it supports: [draft](rule_draft.md).",
        "",
        "## The histories on disk",
        "",
        "| History | What it is | Matches | Newest match | Written | Same matches as | Recreatable from a recipe |",
        "|---|---|---:|---|---|---|---|"]
    for _, r in hist.iterrows():
        rec = ("only while the folder exists: its code is inside it" if r["history"].startswith("folder ")
               else "yes: kept with its code and environment" if r["history"] == "frozen reference"
               else "no: the code that built it is not kept")
        lines.append(f"| {r['history']} | {r['what']} | {r['matches']:,} | {r['newest']} | {r['written']} | "
                     f"{r['same_ids_as'] or '–'} | {rec} |")
    n_old = int(t["older"].astype(bool).sum())
    lines += ["", "## The tables under data/studies", "",
              f"{len(tables):,} parquet tables scanned; {len(t):,} hold match ids. **{n_old:,} are on an older history** "
              "than the repository's (they equal an older one, or hold matches it has since dropped).", "",
              "| Verdict | History | Tables | Size |", "|---|---|---:|---:|"]
    for _, r in per.head(25).iterrows():
        lines.append(f"| {r['verdict']} | {r['version']} | {r['tables']:,} | {gb(r['bytes'])} |")
    lines += ["", "\"equals\": the table holds exactly that history's matches. \"inside\": every history from the first "
              "to the last named holds all its matches (a main-tour table sits inside many). \"outside\": it holds "
              "matches no kept history has (candidate builds, live rows); the closest history is named.", "",
              "### By study folder (tables on an older history)", "",
              "| Study folder | Tables | On an older history | Size |", "|---|---:|---:|---:|"]
    s = t.groupby("study").agg(tables=("table", "size"), older=("older", "sum"), bytes=("bytes", "sum"))
    for st, r in s.sort_values("bytes", ascending=False).head(30).iterrows():
        lines.append(f"| {st} | {int(r['tables']):,} | {int(r['older']):,} | {gb(r['bytes'])} |")
    likely = mix[mix["strength"] == "likely"]
    weak = mix[mix["strength"] == "weak"]
    lines += ["", "## Code that may mix versions", "",
              f"A static first pass by file names. **{len(likely)} file(s) are likely:** outside the model chain and "
              "the daily engine, they name one of the snapshot's chain tables together with a live base table "
              "(Stage 0, the timeline or the odds link) and no saved history. Each is read by hand.", "",
              "| Code | Snapshot tables it names | Verdict |", "|---|---|---|"]
    for _, r in likely.iterrows():
        note = r["note"] if isinstance(r["note"], str) and r["note"] else ""
        lines.append(f"| `{r['code']}` | {r['older_tables'][:160]} | {r['verdict']}{(': ' + note) if note else ''} |")
    by = weak["code"].str.split("/").str[2].value_counts()
    lines += ["", f"**{len(weak)} weak flags, not read:** files that name some table built on an older history and a "
              "live base table, inside the chain or the engine, or naming only a study's own older outputs. By code "
              "folder: " + ", ".join(f"{k} {v}" for k, v in by.items()) + "."]
    lines += ["", "## Build folders on this machine", "",
              "| Folder | Size | History | Own code | In use | Replay registry | Named by |",
              "|---|---:|---:|---|---|---|---:|"]
    for _, r in folders.iterrows():
        lines.append(f"| `{Path(r['folder']).name}` | {gb(r['bytes'])} | "
                     f"{'' if pd.isna(r['history_matches']) else format(int(r['history_matches']), ',')} | "
                     f"{'yes' if r['holds_code'] else 'no'} | {'**yes**' if r['selected_instance'] else ''} | "
                     f"{'yes' if r['in_replay_registry'] else ''} | {r['named_by']} |")
    lines += ["", "## Files", "", "`data/studies/study_data_versions/`: `histories.csv`, `tables.csv`, `readers.csv`, "
              "`mixing.csv`, `folders.csv`, `summary.json`.", ""]
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    INDEX.write_bytes("\n".join(lines).encode("utf-8"))
    return str(INDEX)


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--reuse-tables", action="store_true",
                    help="read histories.csv and tables.csv from the last run instead of scanning (about 15 minutes)")
    a = ap.parse_args()
    when = dt.datetime.now().isoformat(timespec="minutes")
    OUT.mkdir(parents=True, exist_ok=True)
    if a.reuse_tables:
        hist = pd.read_csv(OUT / "histories.csv", dtype={"same_ids_as": str}).fillna({"same_ids_as": ""})
        tables = pd.read_csv(OUT / "tables.csv", low_memory=False)
        tables["older"] = tables["older"].fillna(False).astype(bool)
    else:
        hist, ids, dates = load_histories()
        tables = scan_tables(hist, ids, dates)
    readers, mix = scan_code(tables)
    reviewed = OUT / "mixing_reviewed.csv"                      # the hand reading, kept across runs
    if reviewed.exists():
        rv = pd.read_csv(reviewed, dtype=str).set_index("code")
        for i, r in mix.iterrows():
            if r["code"] in rv.index:
                mix.loc[i, "verdict"] = rv.loc[r["code"], "verdict"]
                mix.loc[i, "note"] = rv.loc[r["code"], "note"] if isinstance(rv.loc[r["code"], "note"], str) else ""
        missed = [c for c in rv.index if c not in set(mix["code"])]     # confirmed by reading, unseen by the pass
        if missed:
            mix = pd.concat([mix, pd.DataFrame([{"code": c, "strength": "likely", "older_tables": "",
                                                 "older_versions": "", "live_base_named": "",
                                                 "verdict": rv.loc[c, "verdict"] + " (missed by the static pass)",
                                                 "note": rv.loc[c, "note"]} for c in missed])], ignore_index=True)
    folders = scan_folders(hist)
    for name, df in (("histories", hist), ("tables", tables), ("readers", readers), ("mixing", mix),
                     ("folders", folders)):
        df.to_csv(OUT / f"{name}.csv", index=False, lineterminator="\n")
    t = tables[tables["verdict"].isin(["equals", "inside", "outside"])]
    summary = {"generated": when, "histories": len(hist), "tables_scanned": int(len(tables)),
               "tables_with_match_ids": int(len(t)), "tables_on_an_older_history": int(t["older"].astype(bool).sum()),
               "bytes_on_an_older_history": int(t.loc[t["older"].astype(bool), "bytes"].sum()),
               "code_flagged_for_mixing": int(len(mix)), "folders": int(len(folders)),
               "folders_bytes": int(folders["bytes"].sum())}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    print("index:", write_index(hist, tables, readers, mix, folders, when))
    return 0


if __name__ == "__main__":
    sys.exit(main())
