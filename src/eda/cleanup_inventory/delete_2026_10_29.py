"""The commit check of 29 Oct 2026: its three items, deleted at the owner's word (29 Oct 2026: "Delete this", pasting the
check's section "Study files you can delete (rebuildable, nothing in production reads them)"). The check, the readers
and why each item can go: docs/studies/cleanup_inventory/process_log.md § 10; the report: README.md.

The items, in the order deleted:
    work trees   the seven daily work trees of 24-25 Oct that the master pipeline's process log kept "for review"
                 (Parts 14 and 17): tnr_daily_earlier and tnr_daily_earlier2 (the qualifying earlier-rounds replays),
                 tnr_daily_main, tnr_daily_main_w and tnr_daily_main2 (the main-draw ones), tnr_daily_datefix_off and
                 tnr_daily_datefix_on (the main-draw date check). Their run folders stay; no code reads a tree.
    bytecode     the __pycache__ folders a test run wrote on 28 Oct 09:03 into the frozen reference's code copy
                 (current_best_model/reference_2026-10-08/frozen/code/). None is a frozen file: frozen/files.csv.gz lists
                 1,581 files, no .pyc, and reference.verify reads only those.
    P9 tables    the nine git-ignored .parquet tables of the P9 point-details study (p9_point_details/build/ and
                 harness/). Only the study's own scripts read them; its README § 8 rebuilds them, with slightly different
                 numbers. Its JSON and CSV outputs stay.

Safety, as in delete_2026_10_22.py, whose walk, link removal and listings (delete_now.py) this reuses:
    no bet-day step in flight: no master_pipeline/predict.lock, no runner marker, no process running the daily engine;
    re-checked just before the run: a work tree's dp_worktree.py marker naming its own run (whose folder stays), each of
    its links pointing where dp_worktree.setup points it, not the selected build tree nor a live work tree, no running
    process naming it; the bytecode's files .pyc only, directly inside __pycache__ folders, none listed in files.csv.gz,
    no link in the code copy; a table's size as found and git's ignore; for each item, nothing written in the last
    QUIET_HOURS hours and nothing unreadable;
    links are found by a walk that never enters one and removed as links (cmd /c rmdir, never the target); a second walk
    must find none before rmdir /s /q (delete_now.remove_tree);
    the kept trees (every link's target, the Tennis My Life freezes, the daily engine's state and runs,
    current_best_model, the P9 study's folder, the selected and the rollback build trees) are listed file by file before
    the run and after each item. Files that other jobs remove meanwhile (temporary and partial files, by name: VOLATILE)
    are reported; any other lost file stops the run;
    the frozen reference is verified before the run and right after the bytecode goes (reference.verify with
    write=False, so its tracked verify.json is left as it is): the same files present and equal, or the run stops.
An item already gone is recorded and skipped, so a stopped run can be resumed (its kept trees listed afresh).
--dry-run lists the plan, deleting nothing; before the run it also records the plan.
The record: data/studies/cleanup_inventory/deletions_2026-10-29.json.
Run: ./python.sh src/eda/cleanup_inventory/delete_2026_10_29.py --dry-run, then without it.
"""
from __future__ import annotations

import argparse
import csv
import fnmatch
import gzip
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.cleanup_inventory import delete_now as D  # noqa: E402

HOME = Path("C:/Users/zerom")
STUDIES = ROOT / "data" / "studies"
DPS = STUDIES / "daily_prediction"
MP = STUDIES / "master_pipeline"
RECORD = STUDIES / "cleanup_inventory" / "deletions_2026-10-29.json"
SELECTED = MP / "selected_instance.json"
MARKER = ".prediction_run_sandbox"   # dp_worktree.MARKER
WORK_TREES = {   # the tree -> the run its marker names (a folder of daily_prediction/runs, which stays)
    HOME / "tnr_daily_earlier": "replay_2026-10-19_Q2_earlier_tennislive",
    HOME / "tnr_daily_earlier2": "replay_2026-10-19_Q2_earlier_tennislive_v2",
    HOME / "tnr_daily_main": "replay_2026-10-05_R128_main_earlier",
    HOME / "tnr_daily_main_w": "replay_2026-09-28_R128_main_earlier_wta",
    HOME / "tnr_daily_main2": "replay_2026-10-05_R128_main_earlier_v3",
    HOME / "tnr_daily_datefix_off": "check_maindate_off_finals",
    HOME / "tnr_daily_datefix_on": "check_maindate_on_finals"}
LIVE_TREES = ("tnr_daily", "tnr_daily_nb")   # dp_common.WORK_TREE's default and the notebook's (pipeline/predict.py)
FROZEN = STUDIES / "current_best_model" / "reference_2026-10-08" / "frozen"
P9 = STUDIES / "p9_point_details"
P9_TABLES = {   # the table -> its size in bytes when the check found it (29 Oct)
    P9 / "build" / "atoms.parquet": 1_659_784,
    P9 / "build" / "crosswalk.parquet": 40_730,
    P9 / "build" / "depth_rows.parquet": 733_863,
    P9 / "build" / "links.parquet": 2_559_100,
    P9 / "build" / "match_sources.parquet": 1_501_327,
    P9 / "build" / "rally_points.parquet": 15_083_863,
    P9 / "harness" / "challenger_link.parquet": 462_148,
    P9 / "harness" / "model_inputs.parquet": 2_963_930,
    P9 / "harness" / "population.parquet": 1_075_710}
QUIET_HOURS = 2
KEPT = [ROOT / "data" / "raw", ROOT / "data" / "dump", HOME / "tnr_dump_freeze_10211347", HOME / "tnr_dump_freeze",
        HOME / "tnr_dump_freeze_1014", HOME / "tnr_dump_freeze_1016", DPS / "state", DPS / "runs",
        STUDIES / "current_best_model", P9, HOME / "tnr_tpl1021", HOME / "tnr_tpl1016"]
VOLATILE = ("_ios_cache_*.npz", "_cache_tmp.npz", "*.tmp", "*.part", "*.partial", "*.crdownload", "*.lock")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}


def save_record(rec: dict) -> None:
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")


def free_gb() -> float:
    return round(shutil.disk_usage("C:/").free / 1e9, 1)


def norm(s) -> str:
    return str(s).replace("\\", "/").lower()


def quiet(files) -> tuple[bool, str | None]:
    """No file written in the last QUIET_HOURS hours; and the newest file's time."""
    t = max((os.lstat(f).st_mtime for f, _ in files), default=0.0)
    return t < time.time() - QUIET_HOURS * 3600, (datetime.fromtimestamp(t).isoformat(timespec="seconds") if t else None)


def processes() -> list[str]:
    ps = "Get-CimInstance Win32_Process | ForEach-Object { $_.CommandLine }"
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return [norm(x) for x in out.splitlines() if x.strip()]


def naming(procs: list[str], path: Path) -> list[str]:
    """The command lines that name path, as C:/Users/... or Git Bash's /c/Users/... (not a longer name)."""
    forms = [norm(path), "/c/" + norm(path)[3:]]
    pats = [re.compile(re.escape(x) + r"(?![a-z0-9_])") for x in forms]
    return [p[:200] for p in procs if any(q.search(p) for q in pats)]


def bet_day(procs: list[str]) -> list[str]:
    """What shows a bet-day step in flight: the notebook's lock, a runner marker, a process running the daily engine."""
    hits = [str(MP / "predict.lock")] if (MP / "predict.lock").exists() else []
    hits += [str(m) for m in sorted((MP / "running").glob("*.json"))] if (MP / "running").is_dir() else []
    return hits + [p[:200] for p in procs if "daily_prediction/dp.py" in p]


def volatile(rel: str) -> bool:
    name = Path(rel).name.lower()
    return any(fnmatch.fnmatch(name, p) for p in VOLATILE)


def ignored(paths) -> set[str]:
    """Which of the paths git ignores, as repository-relative paths."""
    rel = [Path(p).relative_to(ROOT).as_posix() for p in paths]
    r = subprocess.run(["git", "-C", str(ROOT), "check-ignore", "--no-index", *rel], capture_output=True, text=True)
    return {x.strip() for x in r.stdout.splitlines() if x.strip()}  # as arguments: text-mode stdin would add \r


def frozen_listed() -> set[str]:
    """Every frozen file of the reference, as files.csv.gz names it (relative to frozen/)."""
    with gzip.open(FROZEN / "files.csv.gz", "rt", encoding="utf-8", newline="") as f:
        return {norm(r["frozen"]) for r in csv.DictReader(f)}


def reference() -> dict:
    """The frozen reference's own check, its verify.json left as it is."""
    from src.eda.current_best_model import reference as R
    v = R.verify(write=False)
    return {k: v[k] for k in ("ok", "files", "missing", "differ", "inventory_intact")}


def expected_target(rel: str, view: str | None) -> str:
    """Where dp_worktree.setup points a tree's link at rel: the repository's same path, but a replay's Tennis My Life at
    its instance's dump view."""
    if view and rel == "data/dump/matches/tennis_my_life":
        return norm(Path(view) / "matches" / "tennis_my_life")
    return norm(ROOT / rel)


# ------------------------------------------------------------------------------------------------
# The plan, with each item's checks

def plan() -> tuple[list[dict], dict]:
    sel = json.loads(SELECTED.read_text(encoding="utf-8"))
    procs = processes()
    kept = {norm(k) for k in KEPT}
    items = []
    for t, run in WORK_TREES.items():
        it = {"group": "work trees", "path": str(t), "kind": "folder", "paths": [str(t)], "exists": t.exists(),
              "run": run}
        if it["exists"]:
            files, links, bad = D.walk(t)
            ok, newest = quiet(files)
            try:
                marker = json.loads((t / MARKER).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                marker = None
            view = (marker or {}).get("dump_view")
            pairs = [[str(x), D.target(x)] for x in links]
            rels = {Path(x).relative_to(t).as_posix(): tgt for x, tgt in pairs}
            named_by = naming(procs, t)
            it.update(files=len(files), bytes=sum(s for _, s in files), newest=newest, links=pairs, unreadable=bad[:3],
                      marker=marker, processes_naming_it=named_by)
            it["checks"] = {"dp_worktree_marker": bool(marker) and marker.get("by") == "daily_prediction/dp_worktree.py",
                            "marker_names_its_run": bool(marker) and norm(marker.get("owner", "")) == norm(DPS / "runs" / run),
                            "its_run_folder_stays": (DPS / "runs" / run).is_dir(),
                            "links_as_setup_made_them": "data/raw" in rels and all(
                                norm(tgt) == expected_target(rel, view) for rel, tgt in rels.items()),
                            "dump_view_kept": not view or norm(view) in kept,
                            "not_the_selected_tree": norm(t) != norm(sel.get("tree", "")),
                            "not_a_live_tree": t.name not in LIVE_TREES, "no_process_names_it": not named_by,
                            "readable": not bad, "quiet": ok}
        items.append(it)

    code = FROZEN / "code"
    files, links, bad = D.walk(code)
    inside = [(f, s) for f, s in files if "__pycache__" in f.relative_to(code).parts]
    dirs = sorted({f.parent for f, _ in inside})
    it = {"group": "bytecode", "path": str(code), "kind": "folders", "paths": [str(d) for d in dirs], "exists": bool(dirs)}
    if dirs:
        ok, newest = quiet(inside)
        hit = sorted({norm(f.relative_to(FROZEN).as_posix()) for f, _ in inside} & frozen_listed())
        it.update(folders=len(dirs), files=len(inside), bytes=sum(s for _, s in inside), newest=newest,
                  listed_in_files_csv=hit[:20], links_in_code_copy=[str(x) for x in links][:20], unreadable=bad[:3])
        it["checks"] = {"pyc_directly_in_pycache_only": all(f.suffix == ".pyc" and f.parent.name == "__pycache__"
                                                            for f, _ in inside),
                        "no_frozen_file_among_them": not hit, "no_link_in_the_code_copy": not links,
                        "readable": not bad, "quiet": ok}
    items.append(it)

    present = {p: D.lstat(p) for p in P9_TABLES}
    here = [p for p, st in present.items() if st is not None]
    it = {"group": "P9 tables", "path": str(P9), "kind": "files", "paths": [str(p) for p in here], "exists": bool(here)}
    if here:
        ok, newest = quiet([(p, present[p].st_size) for p in here])
        ign = ignored(here)
        it.update(files=len(here), bytes=sum(present[p].st_size for p in here), newest=newest,
                  already_gone=[str(p) for p, st in present.items() if st is None])
        it["checks"] = {"sizes_as_found": all(present[p].st_size == P9_TABLES[p] for p in here),
                        "no_links": not any(D.is_reparse(present[p]) for p in here),
                        "ignored_by_git": all(p.relative_to(ROOT).as_posix() in ign for p in here), "quiet": ok}
    items.append(it)
    return items, {"selected": sel, "bet_day_in_flight": bet_day(procs)}


def kept_roots(items: list[dict]) -> list[Path]:
    """KEPT, plus any tree link's target that no kept root holds."""
    roots = list(KEPT)
    for it in items:
        for _, tgt in it.get("links", []):
            if not any(norm(tgt) == norm(r) or norm(tgt).startswith(norm(r) + "/") for r in roots):
                roots.append(Path(tgt))
    return roots


def show(items: list[dict], context: dict, roots: list[Path], ref: dict) -> None:
    for it in items:
        if not it["exists"]:
            print(f"{it['group']}: {it['path']}: already gone")
            continue
        failed = [k for k, v in it["checks"].items() if not v]
        folders = f"{it['folders']} folders, " if it["group"] == "bytecode" else ""
        print(f"{it['group']}: {it['path']}: {folders}{it['files']:,} files, {it['bytes'] / 1e9:.3f} GB, newest "
              f"{it['newest']}; checks {'pass' if not failed else 'FAIL: ' + ', '.join(failed)}")
        if it["group"] == "work trees":
            print(f"    marker names {Path(str((it['marker'] or {}).get('owner', ''))).name}; {len(it['links'])} links:")
            for x, tgt in it["links"]:
                print(f"    link {Path(x).relative_to(it['path'])} -> {tgt}")
    print(f"selected: {context['selected'].get('instance')} on {context['selected'].get('tree')}")
    print(f"bet-day step in flight: {context['bet_day_in_flight'] or 'none'}")
    print(f"frozen reference: {ref}")
    print("kept trees listed:", *[str(r) for r in roots], sep="\n    ")
    print(f"total {sum(i.get('bytes', 0) for i in items if i['exists']) / 1e9:.2f} GB; C: free {free_gb()} GB")


# ------------------------------------------------------------------------------------------------
# The run

def git_checks() -> dict:
    """Read-only: tracked files missing from disk, and untracked files a commit would add that are over 50 MB."""
    def ls(*args):
        r = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", *args], capture_output=True, text=True,
                           encoding="utf-8")
        return [x for x in r.stdout.split("\0") if x]
    big = []
    for x in ls("--others", "--exclude-standard"):
        st = D.lstat(ROOT / x)
        if st is not None and st.st_size > 50_000_000:
            big.append([x, st.st_size])
    return {"tracked_deleted": ls("-d"), "untracked_over_50_mb": big}


def run(dry: bool) -> int:
    rec = load_record()
    items, context = plan()
    roots = kept_roots(items)
    ref = reference()
    show(items, context, roots, ref)
    if dry:
        if "runs" not in rec:                        # after the run a dry run only prints: the plan stays as recorded
            rec["dry_run"] = {"at": now(), "free_gb": free_gb(), "kept_roots": [str(r) for r in roots],
                              "context": context, "reference": ref, "git": git_checks(), "items": items}
            save_record(rec)
        return 0
    failed = [[it["path"], k] for it in items if it["exists"] for k, v in it["checks"].items() if not v]
    if context["bet_day_in_flight"]:
        failed.append(["bet day", "a step in flight: " + "; ".join(context["bet_day_in_flight"])[:300]])
    if not ref["ok"]:
        failed.append([str(FROZEN), "the reference does not verify before the run"])
    if failed:
        print("checks failed, nothing deleted:", failed)
        rec.setdefault("refused", []).append({"at": now(), "failed": failed})
        save_record(rec)
        return 1
    entry = {"at": now(), "free_gb_before": free_gb(), "kept_roots": [str(r) for r in roots], "reference_before": ref,
             "git_before": git_checks(), "items": []}
    t0 = time.time()
    before = D.fingerprint(roots)
    entry["kept_files_before"] = {k: len(v) for k, v in before.items()}
    print(f"{now()} kept trees listed: {sum(len(v) for v in before.values()):,} files", flush=True)
    expected = {str(r): set() for r in roots}
    stopped = False
    for it in items:
        e = dict(it)
        if not it["exists"]:
            e["result"] = "already gone"
            entry["items"].append(e)
            continue
        paths = [Path(x) for x in it["paths"]]
        for p in paths:                              # this item's files inside a kept root may go; nothing else
            for f, _ in D.walk(p)[0]:
                for r in roots:
                    try:
                        expected[str(r)].add(str(f.relative_to(r)))
                    except ValueError:
                        pass
        t1 = time.time()
        try:
            if it["kind"] == "folder":
                e["result"] = D.remove_tree(paths[0])
            else:
                done = [D.remove_tree(p) if it["kind"] == "folders" else D.remove_file(p) for p in paths]
                e["result"] = {"removed": len(done), "files": sum(d.get("files", 1) for d in done),
                               "bytes": sum(d.get("bytes", 0) for d in done)}
            e["deleted"] = all(D.lstat(p) is None for p in paths)
        except Exception as ex:                       # noqa: BLE001  (recorded, then the run stops)
            e["deleted"] = False
            e["error"] = f"{type(ex).__name__}: {ex}"[:500]
        e["seconds"] = round(time.time() - t1, 1)
        after = D.fingerprint(roots)
        lost = {k: before[k] - after.get(k, set()) - expected[k] for k in before}
        e["kept_lost"] = {k: sorted(x for x in v if not volatile(x))[:20] for k, v in lost.items()
                          if any(not volatile(x) for x in v)}
        e["kept_lost_temporary"] = {k: sorted(x for x in v if volatile(x))[:20] for k, v in lost.items()
                                    if any(volatile(x) for x in v)}
        e["expected_gone_still_present"] = sum(1 for k in expected for x in expected[k] if x in after.get(k, set()))
        moved = False
        if it["group"] == "bytecode":
            e["reference_after"] = reference()
            moved = e["reference_after"] != ref
        entry["items"].append(e)
        n_lost = sum(len(v) for v in e["kept_lost"].values())
        n_tmp = sum(len(v) for v in e["kept_lost_temporary"].values())
        print(f"{now()} {it['path']}: deleted {e['deleted']}, {it['bytes'] / 1e9:.3f} GB, {e['seconds']} s; kept trees "
              f"lost {n_lost} files (temporary files gone meanwhile: {n_tmp})"
              + (f"; reference {e['reference_after']}" if it["group"] == "bytecode" else ""), flush=True)
        if n_lost or not e["deleted"] or moved:
            stopped = True
            print("STOPPED:", e.get("error") or e["kept_lost"] or e.get("reference_after"), flush=True)
            break
    final = D.fingerprint(roots)
    entry.update(kept_files_after={k: len(v) for k, v in final.items()}, stopped=stopped,
                 deleted_bytes=sum(e.get("bytes", 0) for e in entry["items"] if e.get("deleted")),
                 free_gb_after=free_gb(), seconds=round(time.time() - t0, 1), git_after=git_checks())
    rec.setdefault("runs", []).append(entry)
    save_record(rec)
    print(f"{now()} deleted {entry['deleted_bytes'] / 1e9:.2f} GB in {entry['seconds']} s; C: free "
          f"{entry['free_gb_before']} -> {entry['free_gb_after']} GB; git: tracked files missing "
          f"{len(entry['git_before']['tracked_deleted'])} before, {len(entry['git_after']['tracked_deleted'])} after; "
          f"untracked over 50 MB {entry['git_after']['untracked_over_50_mb']}")
    return 1 if stopped else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    return run(a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
