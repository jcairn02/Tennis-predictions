"""The commit check of 22 Oct 2026: its three "delete now" groups, deleted at the owner's word (22 Oct 2026, pasting
the three rows: "Delete these 3 suggested delete now repository/files"). The check, the readers and why each item can
go: docs/studies/cleanup_inventory/process_log.md § 9; the report: README.md.

The items, in the order deleted:
    solver caches   the daily engine's temporary IOS caches that three live runs of 14 Oct left when they were cut
                    short (runs/live_2026-10-14_{123349,125827,135305}/_ios_cache_<stamp>.npz). dp_state.py:243 writes
                    one per states step under a new stamp and deletes it when the step ends, so nothing reads a
                    leftover. The runs' records stay.
    TabPFN caches   state/template_2026-10-21/tabpfn/: the training caches of the first retrain's morning instance,
                    replaced at 16:39 the same day by template_2026-10-21b. dp_tabcache.py builds a missing seed by
                    itself (about 45 s a seed). The instance's checkpoints (state/template_2026-10-21/<day>/) stay.
    work trees      five daily work trees of 13-16 Oct kept "for review": tnr_daily_patterns, tnr_daily_patterns_live,
                    tnr_daily_fastcourt, tnr_daily_fastcourt_live, tnr_daily_replayfix. No code reads them.
--part 2: the build trees of the 13 and 14 Oct instances, deleted at the owner's word the same afternoon (quoting the
recommendation to delete both and to repoint the one script that named one: "Do this, update studies that refernce them
that we've deleted it , so models who review the study know it was built with an older version and may have to be
updated"; process log § 9d):
    build trees     C:/Users/zerom/tnr_gaps (template_2026-10-13, live 13 Oct 20:41 - 14 Oct 07:43) and
                    C:/Users/zerom/tnr_tpl1014 (template_2026-10-14, live 14 Oct 07:43 - 16 Oct 17:58). Their caches
                    went on 21 Oct; neither is a rollback. feature_universe/form_evidence.py, which defaulted to
                    tnr_gaps, now defaults to the master notebook's selection.
                    Re-checked: run_chain's shape (its code inside; exactly the links data/raw and data/dump into the
                    repository); the instance's README names the tree; not the selected instance or tree; no rollback
                    command in current_best_model/README.md or in_season_retrain/README.md names it; no run made
                    since the instance was replaced has it as base tree; no process names it; quiet; readable.

Safety, as in delete_now.py (11 Oct) and lyr_sandboxes.py (14 Oct), whose walk and removal this reuses:
    re-checked just before the run: a cache file's size as found; for the TabPFN caches, that their instance is not
    the selected one and that no run made since the switch names it; for a work tree, its dp_worktree.py marker, that
    it is not the selected build tree, and that no running process names it; nothing in an item written in the last
    QUIET_HOURS hours; nothing unreadable;
    links are found by a walk that never enters one and removed as links (cmd /c rmdir, never the target); a second
    walk must find none before rmdir /s /q (delete_now.remove_tree);
    the kept trees (every link's target, the daily engine's state, current_best_model, the three runs, the selected
    and the rollback build trees) are listed file by file before the run and after each item. Files that other jobs
    remove meanwhile (temporary and partial files, by name: VOLATILE) are reported; any other lost file stops the run.
An item already gone is recorded and skipped, so a stopped run can be resumed (its kept trees listed afresh).
--dry-run lists the plan, deleting nothing; before the run it also records the plan.
The record: data/studies/cleanup_inventory/deletions_2026-10-22.json (part 2 under "part2").
Run: ./python.sh src/eda/cleanup_inventory/delete_2026_10_22.py [--part 2] --dry-run, then without it.
"""
from __future__ import annotations

import argparse
import fnmatch
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
RECORD = STUDIES / "cleanup_inventory" / "deletions_2026-10-22.json"
SELECTED = STUDIES / "master_pipeline" / "selected_instance.json"
SOLVER_CACHES = {   # the file -> its size in bytes when the check found it (22 Oct, 11:36)
    DPS / "runs" / "live_2026-10-14_123349" / "_ios_cache_2026-10-14T194634Z.npz": 2_494_003_914,
    DPS / "runs" / "live_2026-10-14_125827" / "_ios_cache_2026-10-14T201041Z.npz": 1_873_705_026,
    DPS / "runs" / "live_2026-10-14_135305" / "_ios_cache_2026-10-14T210507Z.npz": 1_873_710_330}
INSTANCE = "template_2026-10-21"
SWITCH = "2026-10-21T233900Z"      # template_2026-10-21b live from 16:39 PDT (in_season_retrain/README.md)
TABPFN = DPS / "state" / INSTANCE / "tabpfn"
WORK_TREES = [HOME / n for n in ("tnr_daily_patterns", "tnr_daily_patterns_live", "tnr_daily_fastcourt",
                                 "tnr_daily_fastcourt_live", "tnr_daily_replayfix")]
MARKER = ".prediction_run_sandbox"   # dp_worktree.MARKER
QUIET_HOURS = 2
KEPT = ([ROOT / "data" / "raw", ROOT / "data" / "dump", HOME / "tnr_dump_freeze", HOME / "tnr_dump_freeze_1014",
         DPS / "state", STUDIES / "current_best_model", HOME / "tnr_tpl1021", HOME / "tnr_tpl1016"]
        + sorted({p.parent for p in SOLVER_CACHES}))
VOLATILE = ("_ios_cache_*.npz", "_cache_tmp.npz", "*.tmp", "*.part", "*.partial", "*.crdownload", "*.lock")
BUILD_TREES = {   # part 2: the build tree -> its instance, and when the next instance went live (UTC, as run.json writes)
    HOME / "tnr_gaps": ("template_2026-10-13", "2026-10-14T144300Z"),      # replaced 14 Oct 07:43 PDT
    HOME / "tnr_tpl1014": ("template_2026-10-14", "2026-10-17T005800Z")}   # replaced 16 Oct 17:58 PDT
ROLLBACK_DOCS = [STUDIES / "current_best_model" / "README.md", ROOT / "docs" / "studies" / "in_season_retrain" / "README.md"]
LINKED = ("raw", "dump")             # run_chain.LINKED: a chain sandbox's two links, data/raw and data/dump


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def load_record() -> dict:
    return json.loads(RECORD.read_text(encoding="utf-8")) if RECORD.exists() else {}


def save_record(rec: dict) -> None:
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")


def free_gb() -> float:
    return round(shutil.disk_usage("C:/").free / 1e9, 1)


def norm(s: str) -> str:
    return str(s).replace("\\", "/").lower()


def quiet(files) -> tuple[bool, str | None]:
    """No file written in the last QUIET_HOURS hours; and the newest file's time."""
    t = max((os.lstat(f).st_mtime for f, _ in files), default=0.0)
    return t < time.time() - QUIET_HOURS * 3600, (datetime.fromtimestamp(t).isoformat(timespec="seconds") if t else None)


def processes() -> list[str]:
    ps = "Get-CimInstance Win32_Process | ForEach-Object { $_.CommandLine }"
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return [norm(x) for x in out.splitlines() if x.strip()]


def runs_naming(instance: str, since: str) -> list[str]:
    """Run folders made at or after `since` whose run.json names the instance."""
    hits = []
    for rj in sorted((DPS / "runs").glob("*/run.json")):
        try:
            r = json.loads(rj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(r.get("created_at", "")) >= since and Path(str(r.get("instance", ""))).name == instance:
            hits.append(rj.parent.name)
    return hits


def runs_on_tree(tree: Path, since: str) -> list[str]:
    """Run folders anywhere in data/studies made at or after `since` whose run.json has the tree as its base tree."""
    hits = []
    for rj in sorted(STUDIES.rglob("run.json")):
        try:
            r = json.loads(rj.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(r, dict) and str(r.get("created_at", "")) >= since and norm(r.get("base_tree", "")) == norm(tree):
            hits.append(rj.parent.relative_to(STUDIES).as_posix())
    return hits


def rollback_trees() -> list[str]:
    """The trees the documented rollback commands name (tree="...")."""
    out = set()
    for doc in ROLLBACK_DOCS:
        out |= {norm(x) for x in re.findall(r'tree="([^"]+)"', doc.read_text(encoding="utf-8"))}
    return sorted(out)


def volatile(rel: str) -> bool:
    name = Path(rel).name.lower()
    return any(fnmatch.fnmatch(name, p) for p in VOLATILE)


# ------------------------------------------------------------------------------------------------
# The plan, with each item's checks

def plan(part: int) -> list[dict]:
    return plan_part1() if part == 1 else plan_part2()


def plan_part2() -> list[dict]:
    sel = json.loads(SELECTED.read_text(encoding="utf-8"))
    procs = processes()
    rollbacks = rollback_trees()
    recent = time.strftime("%Y-%m-%dT%H%M%SZ", time.gmtime(time.time() - 3 * 86400))
    items = []
    for t, (instance, replaced) in BUILD_TREES.items():
        it = {"group": "build trees", "path": str(t), "kind": "folder", "exists": t.exists(), "instance": instance,
              "replaced_utc": replaced}
        if it["exists"]:
            files, links, bad = D.walk(t)
            ok, newest = quiet(files)
            pairs = [[str(x), D.target(x)] for x in links]
            want = {(f"data/{n}", norm(ROOT / "data" / n)) for n in LINKED}
            got = {(Path(x).relative_to(t).as_posix(), norm(tgt)) for x, tgt in pairs}
            readme = STUDIES / "current_best_model" / instance / "README.md"
            named = readme.exists() and norm(t) in norm(readme.read_text(encoding="utf-8"))
            forms = [norm(t), "/c/" + norm(t)[3:]]
            pats = [re.compile(re.escape(x) + r"(?![a-z0-9_])") for x in forms]
            named_by = [p[:200] for p in procs if any(q.search(p) for q in pats)]
            since_replaced, last_3_days = runs_on_tree(t, replaced), runs_on_tree(t, recent)
            it.update(files=len(files), bytes=sum(s for _, s in files), newest=newest, links=pairs,
                      unreadable=bad[:3], selected=sel, rollback_trees=rollbacks,
                      runs_on_it_since_replaced=since_replaced, runs_on_it_last_3_days=last_3_days,
                      processes_naming_it=named_by)
            it["checks"] = {"chain_sandbox_code": (t / "src" / "eda" / "model_rebuild" / "run_chain.py").exists(),
                            "only_the_chain_links": got == want, "instance_readme_names_it": named,
                            "not_selected": sel.get("instance") != instance and norm(sel.get("tree", "")) != norm(t),
                            "not_a_rollback": norm(t) not in rollbacks, "no_run_in_3_days": not last_3_days,
                            "no_process_names_it": not named_by, "readable": not bad, "quiet": ok}
        items.append(it)
    return items


def plan_part1() -> list[dict]:
    sel = json.loads(SELECTED.read_text(encoding="utf-8"))
    procs = processes()
    items = []
    for f, size in SOLVER_CACHES.items():
        st = D.lstat(f)
        it = {"group": "solver caches", "path": str(f), "kind": "file", "exists": st is not None}
        if st is not None:
            it.update(files=1, bytes=st.st_size,
                      modified=datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"))
            it["checks"] = {"size_as_found": st.st_size == size, "not_a_link": not D.is_reparse(st),
                            "quiet": st.st_mtime < time.time() - QUIET_HOURS * 3600}
        items.append(it)

    it = {"group": "TabPFN caches", "path": str(TABPFN), "kind": "folder", "exists": TABPFN.exists()}
    if it["exists"]:
        files, links, bad = D.walk(TABPFN)
        ok, newest = quiet(files)
        keys = {}
        for k in sorted(TABPFN.glob("season*/seed*/key.json")):
            try:
                keys[k.relative_to(TABPFN).as_posix()] = json.loads(k.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                keys[k.relative_to(TABPFN).as_posix()] = f"<unreadable: {e}>"
        recent = runs_naming(INSTANCE, SWITCH)
        it.update(files=len(files), bytes=sum(s for _, s in files), newest=newest,
                  listing=[[f.relative_to(TABPFN).as_posix(), s] for f, s in sorted(files)],
                  links=[str(x) for x in links], unreadable=bad[:3], keys=keys, selected=sel.get("instance"),
                  runs_naming_it_since_switch=recent,
                  kept_beside=sorted(p.name for p in TABPFN.parent.iterdir() if p.name != "tabpfn"))
        it["checks"] = {"not_selected": sel.get("instance") != INSTANCE, "no_run_since_switch": not recent,
                        "no_links": not links, "readable": not bad, "quiet": ok}
    items.append(it)

    base = norm(sel.get("tree", ""))
    for t in WORK_TREES:
        it = {"group": "work trees", "path": str(t), "kind": "folder", "exists": t.exists()}
        if it["exists"]:
            files, links, bad = D.walk(t)
            ok, newest = quiet(files)
            try:
                marker = json.loads((t / MARKER).read_text(encoding="utf-8"))
            except (OSError, ValueError):
                marker = None
            forms = [norm(t), "/c/" + norm(t)[3:]]                     # C:/Users/... and Git Bash's /c/Users/...
            pats = [re.compile(re.escape(x) + r"(?![a-z0-9_])") for x in forms]
            named_by = [p[:200] for p in procs if any(q.search(p) for q in pats)]
            it.update(files=len(files), bytes=sum(s for _, s in files), newest=newest,
                      links=[[str(x), D.target(x)] for x in links], unreadable=bad[:3], marker=marker,
                      processes_naming_it=named_by)
            it["checks"] = {"dp_worktree_marker": bool(marker) and marker.get("by") == "daily_prediction/dp_worktree.py",
                            "not_the_selected_tree": norm(t) != base, "no_process_names_it": not named_by,
                            "readable": not bad, "quiet": ok}
        items.append(it)
    return items


def kept_roots(items: list[dict]) -> list[Path]:
    """KEPT, plus any tree link's target that no kept root holds."""
    roots = list(KEPT)
    for it in items:
        if it["group"] not in ("work trees", "build trees"):
            continue
        for _, tgt in it.get("links", []):
            if not any(norm(tgt) == norm(r) or norm(tgt).startswith(norm(r) + "/") for r in roots):
                roots.append(Path(tgt))
    return roots


def show(items: list[dict], roots: list[Path]) -> None:
    for it in items:
        if not it["exists"]:
            print(f"{it['path']}: already gone")
            continue
        failed = [k for k, v in it["checks"].items() if not v]
        print(f"{it['path']}: {it['files']:,} files, {it['bytes'] / 1e9:.2f} GB, newest "
              f"{it.get('newest') or it.get('modified')}; checks {'pass' if not failed else 'FAIL: ' + ', '.join(failed)}")
        if it["group"] in ("work trees", "build trees"):
            for x, tgt in it["links"]:
                print(f"    link {Path(x).relative_to(it['path'])} -> {tgt}")
        if it["group"] == "build trees":
            print(f"    instance {it['instance']} (selected: {it['selected'].get('instance')}); runs on it since it was "
                  f"replaced: {it['runs_on_it_since_replaced'] or 'none'}; in the last 3 days: "
                  f"{it['runs_on_it_last_3_days'] or 'none'}; rollback trees: {', '.join(it['rollback_trees'])}")
        if it["group"] == "TabPFN caches":
            print(f"    selected {it['selected']}; runs naming {INSTANCE} since the switch: "
                  f"{it['runs_naming_it_since_switch'] or 'none'}; kept beside: {', '.join(it['kept_beside'])}")
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


def run(dry: bool, part: int = 1) -> int:
    rec = load_record()
    box = rec if part == 1 else rec.setdefault("part2", {})     # part 1's keys sit at the top (written first)
    items = plan(part)
    roots = kept_roots(items)
    show(items, roots)
    if dry:
        if "runs" not in box:                        # after the run a dry run only prints: the plan stays as recorded
            box["dry_run"] = {"at": now(), "free_gb": free_gb(), "kept_roots": [str(r) for r in roots], "items": items}
            save_record(rec)
        return 0
    failed = [[it["path"], k] for it in items if it["exists"] for k, v in it["checks"].items() if not v]
    if failed:
        print("checks failed, nothing deleted:", failed)
        box.setdefault("refused", []).append({"at": now(), "failed": failed})
        save_record(rec)
        return 1
    entry = {"at": now(), "free_gb_before": free_gb(), "kept_roots": [str(r) for r in roots], "items": []}
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
        p = Path(it["path"])
        for f, _ in D.walk(p)[0]:                     # this item's files inside a kept root may go; nothing else
            for r in roots:
                try:
                    expected[str(r)].add(str(f.relative_to(r)))
                except ValueError:
                    pass
        t1 = time.time()
        try:
            e["result"] = D.remove_file(p) if it["kind"] == "file" else D.remove_tree(p)
            e["deleted"] = D.lstat(p) is None
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
        entry["items"].append(e)
        n_lost = sum(len(v) for v in e["kept_lost"].values())
        n_tmp = sum(len(v) for v in e["kept_lost_temporary"].values())
        print(f"{now()} {it['path']}: deleted {e['deleted']}, {it['bytes'] / 1e9:.2f} GB, {e['seconds']} s; kept trees "
              f"lost {n_lost} files (temporary files gone meanwhile: {n_tmp})", flush=True)
        if n_lost or not e["deleted"]:
            stopped = True
            print("STOPPED:", e.get("error") or e["kept_lost"], flush=True)
            break
    final = D.fingerprint(roots)
    entry.update(kept_files_after={k: len(v) for k, v in final.items()}, stopped=stopped,
                 deleted_bytes=sum(e.get("bytes", 0) for e in entry["items"] if e.get("deleted")),
                 free_gb_after=free_gb(), seconds=round(time.time() - t0, 1), git_after=git_checks())
    box.setdefault("runs", []).append(entry)
    save_record(rec)
    print(f"{now()} deleted {entry['deleted_bytes'] / 1e9:.2f} GB in {entry['seconds']} s; C: free "
          f"{entry['free_gb_before']} -> {entry['free_gb_after']} GB; git: tracked files missing "
          f"{entry['git_after']['tracked_deleted']}, untracked over 50 MB {entry['git_after']['untracked_over_50_mb']}")
    return 1 if stopped else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--part", type=int, choices=(1, 2), default=1)
    a = ap.parse_args()
    return run(a.dry_run, a.part)


if __name__ == "__main__":
    sys.exit(main())
