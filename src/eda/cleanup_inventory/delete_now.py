"""The cleanup inventory's "highly recommended: delete now" items, deleted at the owner's word (11 Oct 2026, about
17:30 PDT: "Delete all the highly recommended delete now files. The ones you are very confident about it").
docs/studies/cleanup_inventory/README.md lists them; the items held back after a recheck are in its process log, § 6.

Safety, for every folder deleted:
    every reparse point inside it (a junction or a link) is found by a walk that never follows one, removed with
    `cmd /c rmdir` (a directory link: the link only, never its target) or os.unlink (a file link), a second walk must
    find none, and only then is the folder deleted with `cmd /c rmdir /s /q`.
The trees that are kept (data/raw, data/dump, tnr_dump_freeze, tnr_lyr_new, current_best_model) and every link's
target are listed file by file before the run, after each sandbox and at the end: a file missing stops the run.
The leftover processes are stopped only while their command line is still the one the inventory found.
Session scratchpads go only when neither the folder nor the session's transcript was written in the last 24 hours.
--dry-run deletes nothing: it lists every item and its size, the links and their targets, what stays beside the
files deleted, which items git tracks, and where code or docs name an item.
The record: data/studies/cleanup_inventory/deletions_2026-10-11.json.
Run: ./python.sh src/eda/cleanup_inventory/delete_now.py --dry-run, then without it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path("C:/Users/zerom/Documents/Tennis-predictions")
S = REPO / "data" / "studies"
HOME = Path("C:/Users/zerom")
TEMP = HOME / "AppData" / "Local" / "Temp"
SCRATCH = TEMP / "claude" / "c--Users-zerom-Documents-Tennis-predictions"
TRANSCRIPTS = HOME / ".claude" / "projects" / "c--Users-zerom-Documents-Tennis-predictions"
RECORD = S / "cleanup_inventory" / "deletions_2026-10-11.json"
READERS = S / "cleanup_inventory" / "deletions_2026-10-11_readers.txt"
KEPT = REPO / "docs" / "studies" / "cleanup_inventory" / "kept"
REPARSE = stat.FILE_ATTRIBUTE_REPARSE_POINT
DIRECTORY = stat.FILE_ATTRIBUTE_DIRECTORY
THIS_SESSION = "d2d2331e"
CITED_SCRATCH = ("1407378e", "1de31848", "9fe8e537")            # docs cite files inside them: held back
# repository records name a folder inside them (a rebuild's expected output, a verifier's inputs, a download): held back
NAMED_SCRATCH = ("6a2c00c2", "46524484", "48421609", "5ba10243")
RECENT_HOURS = 24
PROTECTED = [REPO / "data" / "raw", REPO / "data" / "dump", HOME / "tnr_dump_freeze", HOME / "tnr_lyr_new",
             S / "current_best_model"]
SANDBOXES = ("tnr_live", "tnr_live2", "tnr_live3", "tnr_sys1", "tnr_sys2", "tnr_sys3", "tnr_sys5", "tnr_sys_ios",
             "tnr_lyr_rp")                                        # tnr_sys4 held back (§ 6)
# pid -> a part of the command line the inventory found; a pid running anything else is left alone
PROCESSES = {53808: "tnr_lle/logs/lane", 41588: "tnr_lle/logs/lane",
             24472: "d061329f-0568-4169-b891-1a461e96dc2d/tasks/b7rrpey33.output",
             37948: "d061329f-0568-4169-b891-1a461e96dc2d/tasks/b7rrpey33.output"}


def lstat(p: Path):
    try:
        return os.lstat(p)
    except OSError:
        return None


def is_reparse(st) -> bool:
    return st is not None and bool(getattr(st, "st_file_attributes", 0) & REPARSE)


def walk(root: Path):
    """(files, reparse points, unreadable) under root, never entering a reparse point."""
    files, links, bad = [], [], []
    st = lstat(root)
    if st is None:
        return files, links, bad
    if is_reparse(st):
        return files, [root], bad
    if not stat.S_ISDIR(st.st_mode):
        return [(root, st.st_size)], links, bad
    stack = [root]
    while stack:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                entries = list(it)
        except OSError as e:
            bad.append((str(d), str(e)))
            continue
        for e in entries:
            try:
                st = e.stat(follow_symlinks=False)
            except OSError as ex:
                bad.append((e.path, str(ex)))
                continue
            if is_reparse(st):
                links.append(Path(e.path))
            elif stat.S_ISDIR(st.st_mode):
                stack.append(Path(e.path))
            else:
                files.append((Path(e.path), st.st_size))
    return files, links, bad


def size_of(p: Path) -> int:
    return sum(s for _, s in walk(p)[0])


def target(link: Path) -> str:
    try:
        t = os.readlink(link)
    except OSError as e:
        return f"<unreadable: {e}>"
    return t[4:] if t.startswith("\\\\?\\") else t


def long_path(p: Path) -> str:
    return "\\\\?\\" + os.path.abspath(p).replace("/", "\\")


def remove_tree(p: Path) -> dict:
    files, links, bad = walk(p)
    if bad:
        raise RuntimeError(f"{p}: unreadable entries, nothing deleted: {bad[:3]}")
    removed = []
    for link in sorted(links, key=lambda x: len(str(x)), reverse=True):
        st = lstat(link)
        if st is None:
            continue
        removed.append({"link": str(link), "target": target(link)})
        if stat.S_ISDIR(st.st_mode) or st.st_file_attributes & DIRECTORY:
            r = subprocess.run(["cmd", "/c", "rmdir", str(link)], capture_output=True, text=True)
            if r.returncode != 0 or lstat(link) is not None:
                raise RuntimeError(f"{link}: rmdir of the link failed: {r.stderr.strip()}")
        else:
            os.unlink(link)
    left = walk(p)[1]
    if left:
        raise RuntimeError(f"{p}: links left after removal, nothing deleted: {left[:3]}")
    r = subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", long_path(p)], capture_output=True, text=True)
    if lstat(p) is not None:
        raise RuntimeError(f"{p}: still exists after rmdir /s /q: {r.stderr.strip()[:300]}")
    return {"links_removed": removed, "files": len(files), "bytes": sum(s for _, s in files)}


def remove_file(p: Path) -> dict:
    st = lstat(p)
    if st is None:
        return {"missing": True}
    if stat.S_ISDIR(st.st_mode) and not is_reparse(st):
        raise RuntimeError(f"{p}: a folder given as a file")
    size = 0 if is_reparse(st) else st.st_size
    os.unlink(p)
    if lstat(p) is not None:
        raise RuntimeError(f"{p}: still exists")
    return {"bytes": size}


# ------------------------------------------------------------------------------------------------
# The items (README "Highly recommended: delete now", less what was held back)

def scratchpads() -> tuple[list[tuple[Path, str]], list[tuple[str, str]]]:
    """(to delete with a note, held back with the reason)."""
    recent = time.time() - RECENT_HOURS * 3600
    go, held = [], []
    for d in sorted(SCRATCH.iterdir()):
        if not d.is_dir():
            continue
        if d.name.startswith(THIS_SESSION):
            held.append((d.name, "this session"))
            continue
        if d.name.startswith(CITED_SCRATCH):
            held.append((d.name, "docs cite files inside it"))
            continue
        if d.name.startswith(NAMED_SCRATCH):
            held.append((d.name, "a repository record names a folder inside it"))
            continue
        tr = TRANSCRIPTS / f"{d.name}.jsonl"
        if tr.exists() and tr.stat().st_mtime >= recent:
            held.append((d.name, f"transcript written {datetime.fromtimestamp(tr.stat().st_mtime):%m-%d %H:%M}"))
            continue
        files, links, bad = walk(d)
        newest = max([d.stat().st_mtime] + [lstat(f).st_mtime for f, _ in files if lstat(f) is not None])
        if newest >= recent or bad:
            held.append((d.name, f"newest file {datetime.fromtimestamp(newest):%m-%d %H:%M}" if not bad
                         else f"unreadable entries {bad[:1]}"))
            continue
        go.append((d, f"newest {datetime.fromtimestamp(newest):%Y-%m-%d %H:%M}, {len(files)} files"))
    return go, held


def items() -> tuple[list[dict], list]:
    out: list[dict] = []

    def add(group, path, kind="tree", why=""):
        out.append({"group": group, "path": Path(path), "kind": kind, "why": why})

    # A. build sandboxes (results copied out; nothing reads them)
    for name in SANDBOXES:
        add("A sandboxes", HOME / name)
    # B. the 8 Oct backup's local zips (identical MD5 in the bucket, checked 17:21)
    for n in ("studies", "raw", "dump"):
        add("B backup zips", REPO / "data" / "backups" / "2026-10-08" / f"tennis_data_{n}_2026-10-08.zip", "file")
    # C. session scratchpads
    go, held = scratchpads()
    for d, note in go:
        add("C session scratchpads", d, "tree", note)
    # D. study leftovers
    for slot in sorted((S / "surface_ios" / "uploads").iterdir()):
        if slot.is_dir():
            for f in ("X_train.parquet", "X_query.parquet", "y_train.npy"):
                if (slot / f).exists():
                    add("D surface_ios uploads", slot / f, "file")
    for t in ("wallet_markets", "scored_positions", "prematch_positions", "prematch_positions_buffer30", "maker_cells"):
        add("D polymarket_sharp_money", S / "polymarket_sharp_money" / f"{t}.parquet", "file")
    for f in sorted((S / "surface_ios" / "full_runs").glob("*_current.*")):
        add("D surface_ios full_runs current", f, "file")
    # surface_ios/arms/ held back: surface_rating_race/arms.py and model_frame.py (the previous model's frame) read
    # arms/sprof.parquet, and it cannot be rebuilt on the tables it was built on
    ps = S / "point_sequence"
    for f in sorted(ps.glob("points_*.parquet")) + sorted(ps.glob("matches_*.parquet")):
        add("D point_sequence", f, "file")
    for t in ("trait_player_matches_variants", "lev_player_matches", "wta_events", "med_pairs", "trait_player_matches",
              "trait_matches", "carry_triples", "tempo_player_matches", "trait_population"):
        add("D point_sequence", ps / f"{t}.parquet", "file")
    add("D point_sequence", ps / "cache")
    tp = S / "tour_pooling"
    for f in sorted((tp / "fits").iterdir()):
        if not f.name.startswith("split__"):
            add("D tour_pooling fits", f, "tree" if f.is_dir() else "file")
    add("D tour_pooling", tp / "segments" / "standin")
    add("D shot_level", S / "shot_level" / "stage2_frame.parquet", "file")
    for st_ in ("training_window", "meta_stack", "pair_strength"):
        add("D rejected studies' fits", S / st_ / "local")
    add("D match_timing", S / "match_timing" / "undated_matches.csv", "file")
    add("D match_timing", S / "match_timing" / "probe_smoke.log", "file")
    add("D tabpfn_thinking", S / "tabpfn_thinking" / "tabicl")
    for prof in ("chrome_desktop_profile", "edge_desktop_profile"):
        add("D predictive_frontier_tabpfn", S / "predictive_frontier_tabpfn" / "report_qa" / prof)
    add("D surface_elo_pieces", S / "surface_elo_pieces" / "local")
    add("D surface_elo_pieces", S / "surface_elo_pieces" / "audit_scratch" / "fake_tabpfn")
    add("D surface_elo_pieces", S / "surface_elo_pieces" / "audit_scratch" / "pytest")
    add("D surface_elo_pieces", S / "surface_elo_pieces" / "pytest_tmp")
    add("D predictability_diagnostic", S / "predictability_diagnostic" / "summary_number_check.csv", "file")
    for f in ("_check_frame.parquet", "_check_null_copies.csv", "_check_ranking.csv", "_check_results.csv",
              "_check_results.json"):
        add("D ufc_ideas", S / "ufc_ideas" / f, "file")
    pf = S / "predictive_frontier"
    add("D predictive_frontier", pf / "matplotlib_cache")
    add("D predictive_frontier", pf / "explanation_check")
    for f in ("report_desktop.png", "report_mobile.png"):
        add("D predictive_frontier", pf / f, "file")
    for f in ("results_partial.csv", "results_partial.json", "moves_partial.csv", "features_first_run.log"):
        add("D surface_rating_race", S / "surface_rating_race" / f, "file")
    sst = S / "serve_speed_tabpfn"
    for f in ("first_live_run.log", "first_live_run2.log", "first_live_run3.log", "first_live_run4.log"):
        add("D serve_speed_tabpfn", sst / "live" / f, "file")
    add("D serve_speed_tabpfn", sst / "features" / "standin_build.log", "file")
    for f in ("verifier_worlds/w1_b0.09_c0.5_s999.json", "verifier_worlds/w2_b0.09_c0.5_s999.json",
              "verifier_worlds/w3_b0.09_c0.5_s999.json", "verifier_worlds/synthetic/w1_b0.09_c0.5_s999.json",
              "verifier_multiplicity/null_s999.json"):
        add("D serve_speed_tabpfn", sst / "design" / f, "file")
    bt = S / "bet_timing"
    for d in ("local", "local_lines", "local_consensus"):
        add("D bet_timing", bt / d)
    for f in sorted((bt / "local_cons_trained").glob("pb__*.npz")) + sorted((bt / "local_cons_trained").glob("bo__*.npz")):
        add("D bet_timing", f, "file")
    for f in ("results_2024_2026.json", "results_decomposition_2024_2026.csv"):
        add("D bet_timing", bt / f, "file")
    add("D data_continuity", S / "data_continuity" / "pytest_tmp")
    for f in ("_scratch_left.parquet", "_scratch_right.parquet"):
        add("D data_continuity", S / "data_continuity" / f, "file")
    add("D data_map", S / "data_map" / "_logs")
    ev = S / "event_levels"
    add("D event_levels", ev / "local" / "A")
    add("D event_levels", ev / "local" / "B")
    for r in ("4B", "A14", "A_GS", "A_T1000", "A_T500", "A", "C"):
        for ext in ("csv", "json"):
            add("D event_levels", ev / f"results_{r}.{ext}", "file")
    fa = S / "feature_alpha_audit"
    for f in ("repair_date_audit.parquet", "repair_matches.parquet", "repair_rows.parquet", "repair_date_coverage.csv",
              "repair_history_summary.json"):
        add("D feature_alpha_audit", fa / f, "file")
    fi = S / "feature_interactions"
    for f in sorted((fi / "local").glob("binj__*.npz")) + sorted((fi / "local").glob("levels__*.npz")):
        add("D feature_interactions", f, "file")
    add("D feature_interactions", fi / "features" / "levels.parquet", "file")
    for f in ("frozen_binj_2024.parquet", "redo_binj_2024.parquet"):
        add("D feature_interactions", fi / "redteam" / f, "file")
    for f in ("cols.parquet", "p2_HEIGHT_smoke.parquet", "p2_UFIX_smoke.parquet", "planted_smoke.parquet",
              "planted_smoke2.parquet", "sizes_check.parquet"):
        add("D feature_interactions", fi / "verify" / f, "file")
    add("D infosys_atp_backfill", S / "infosys_atp_backfill" / "speed_panel_augmented.parquet", "file")
    add("D ios_product_centring", S / "ios_product_centring" / "local" / "repro")
    for arm in ("A1", "A3", "P0", "P2"):
        add("D lean_review", S / "lean_review" / "arms" / arm)
    ls_ = S / "line_sharpening"
    for t in ("takers", "prices", "markets", "book_minutes", "checkpoints_ext", "checkpoints", "early_onsets",
              "book_onsets", "timing_frame"):
        add("D line_sharpening", ls_ / f"{t}.parquet", "file")
    add("D line_sharpening", ls_ / "local")
    le = S / "lower_level_evidence"
    add("D lower_level_evidence", le / "snapshots" / "dryrun_p7_scenario_vs_reference_2026-10-08.md", "file")
    # R_S2 (here) and system/results/arms/SYS_S2 held back: they carry the two share inputs the feature universe
    # README lists as a lead to admit (docs/studies/feature_universe/README.md, "the lower-level study's R_S2")
    for c in ("F", "FP", "FP_half", "FP_L", "FP_placebo", "P", "R_L"):
        add("D lower_level_evidence candidates", le / "candidates" / c / "fits")
        add("D lower_level_evidence candidates", le / "candidates" / c / "model_frame.parquet", "file")
    add("D lower_level_evidence", le / "candidates" / "offsets" / "forms_z_untranslated.parquet", "file")
    for arm in ("SYS_w0", "SYS_w50", "SYS_w100", "SYS_NOCLASS", "SEP_ALL", "RES_ONLY", "SYS_ITFASIS", "SYS_BOTH_ITFASIS",
                "IDENTITY", "NEW_SYS_BOTH_optA_unread", "REF_noITF_C1DRY", "SEP_ALL_C1DRY"):
        add("D lower_level_evidence system arms", le / "system" / "arms" / arm)
    add("D lower_level_evidence", le / "system" / "arms" / "g5" / "work")
    add("D lower_level_evidence", le / "system" / "audit" / "g5_realparams" / "work")
    add("D lower_level_evidence", le / "system" / "results" / "arms" / "SYS_PLACEBO")
    for v in ("old", "old2", "new"):
        for w in ("default", "live"):
            d = S / "daily_prediction" / "stage0_speed" / f"{v}_{w}"
            for f in ("stage0_matches.parquet", "stage0_match_players.parquet", "stage0_cleaning_log.csv",
                      "stage0_level_applied.csv", "stage0_cells.csv"):
                add("D daily_prediction stage0_speed", d / f, "file")
    # E. temporary and test folders, caches, strays, dead scratch code
    for d in sorted(TEMP.glob("ssp_verifier_*")):
        add("E ssp_verifier temp", d)
    add("E pytest temp", TEMP / "pytest-of-zerom")
    add("E home stray", HOME / "skrub_data")
    for f in ("explore1.csv", "explore2.csv", "explore3.csv", "explore4.csv", "explore5.csv", "panel_noresult.parquet",
              "controls_full.json", "nearest_final.json"):
        add("E root strays", REPO / f, "file")
    add("E repository caches", REPO / ".pytest_cache")
    if (REPO / "__pycache__").is_dir():
        add("E repository caches", REPO / "__pycache__")
    for top in ("src", "test", "scripts", "docs", "data/studies"):
        for dirpath, dirnames, _ in os.walk(REPO / top):
            for dn in list(dirnames):
                full = Path(dirpath) / dn
                if is_reparse(lstat(full)):
                    dirnames.remove(dn)
                elif dn == "__pycache__":
                    add("E repository caches", full)
                    dirnames.remove(dn)
    for f in ("src/eda/feature_interactions/round1/math_audit/apply_checkpoint1.py",
              "src/eda/feature_interactions/round0/body/check_tables.py"):
        add("E dead scratch code", REPO / f, "file")
    return out, held


# ------------------------------------------------------------------------------------------------
# Checks

def fingerprint(roots) -> dict:
    return {str(p): {str(f.relative_to(p)) for f, _ in walk(p)[0]} for p in roots}


def lost_files(before: dict, after: dict) -> dict:
    return {k: sorted(before[k] - after.get(k, set()))[:20] for k in before if before[k] - after.get(k, set())}


def tracked() -> set[str]:
    r = subprocess.run(["git", "-C", str(REPO), "ls-files", "-z"], capture_output=True, text=True, encoding="utf-8")
    return set(x for x in r.stdout.split("\0") if x)


def rel(p: Path) -> str | None:
    try:
        return p.relative_to(REPO).as_posix()
    except ValueError:
        return None


TEXT = {".py", ".md", ".txt", ".yaml", ".yml", ".json", ".sh", ".ipynb", ".toml", ".cfg", ".ini", ".html", ".ps1"}
GENERIC = {"local", "cache", "fits", "arms", "work", "pytest", "pytest_tmp", "_logs", "standin", "repro", "__pycache__",
           ".pytest_cache"}


def reader_hits(todo: list[dict]) -> dict:
    """Where code or docs name a group D or E item: by file basename, quoted stem, or folder's last two parts."""
    tokens: dict[str, set] = defaultdict(set)
    for i, it in enumerate(todo):
        if not it["group"].startswith(("D", "E dead", "E root")):
            continue
        p = it["path"]
        if it["kind"] == "file":
            tokens[p.name].add(i)
            if "_" in p.stem and len(p.stem) >= 6:
                tokens[f'"{p.stem}"'].add(i)
                tokens[f"'{p.stem}'"].add(i)
        else:
            tokens[f"{p.parent.name}/{p.name}"].add(i)
            tokens[f"{p.parent.name}\\{p.name}"].add(i)
            if p.name not in GENERIC and len(p.name) >= 5:
                tokens[f'"{p.name}"'].add(i)
    pat = re.compile("|".join(re.escape(t) for t in sorted(tokens, key=len, reverse=True)))
    skip = (REPO / "docs" / "studies" / "cleanup_inventory", REPO / "src" / "eda" / "cleanup_inventory")
    hits: dict[int, list] = defaultdict(list)
    roots = [REPO / "src", REPO / "test", REPO / "scripts", REPO / "docs"]
    loose = [f for f in REPO.iterdir() if f.is_file() and f.suffix in TEXT] + \
            [f for f in (REPO / "data").iterdir() if f.is_file() and f.suffix in TEXT]
    files = list(loose)
    for r in roots:
        for f, _ in walk(r)[0]:
            if f.suffix in TEXT and not any(str(f).startswith(str(s)) for s in skip) and "__pycache__" not in f.parts:
                files.append(f)
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in pat.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            for i in tokens[m.group(0)]:
                hits[i].append(f"{rel(f)}:{line}")
    return hits


def stop_processes(dry: bool) -> list[dict]:
    rec = []
    for pid, expect in PROCESSES.items():
        r = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                            f"(Get-CimInstance Win32_Process -Filter 'ProcessId={pid}').CommandLine"],
                           capture_output=True, text=True)
        cmd = r.stdout.strip()
        if not cmd:
            rec.append({"pid": pid, "running": False})
            continue
        if expect not in cmd:
            rec.append({"pid": pid, "running": True, "left_alone": "a different command line", "cmd": cmd[:200]})
            continue
        if dry:
            rec.append({"pid": pid, "running": True, "would_stop": True, "cmd": cmd[:160]})
            continue
        k = subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, text=True)
        rec.append({"pid": pid, "cmd": cmd[:200], "stopped": k.returncode == 0, "out": k.stdout.strip()[:300]})
    return rec


# ------------------------------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    rec: dict = {"started": datetime.now().isoformat(timespec="seconds"), "dry_run": a.dry_run}
    rec["processes"] = stop_processes(a.dry_run)
    todo, held = items()
    rec["scratchpads_held"] = held
    in_git = tracked()
    for it in todo:
        st = lstat(it["path"])
        it["exists"] = st is not None
        it["bytes"] = (size_of(it["path"]) if it["kind"] == "tree" else st.st_size) if st else 0
        r = rel(it["path"])
        if r is None:
            it["tracked"] = 0
        elif it["kind"] == "file":
            it["tracked"] = int(r in in_git)
        else:
            it["tracked"] = sum(1 for x in in_git if x.startswith(r + "/"))
    links = {}
    for it in todo:
        if it["kind"] == "tree" and it["exists"]:
            ls = walk(it["path"])[1]
            if ls:
                links[str(it["path"])] = [(str(x), target(x)) for x in ls]
    targets = sorted({t for v in links.values() for _, t in v})

    def under(t: str, p: Path) -> bool:
        a, b = t.lower().rstrip("\\"), str(p).replace("/", "\\").lower().rstrip("\\")
        return a == b or a.startswith(b + "\\")

    trees = [it["path"] for it in todo if it["kind"] == "tree"]
    roots = list(PROTECTED)                  # plus any link target outside the kept trees and the trees deleted
    inside = []                              # targets inside a tree being deleted (pytest's "current" links)
    for t in targets:
        if any(under(t, p) for p in PROTECTED):
            continue
        if any(under(t, p) for p in trees):
            inside.append(t)
        else:
            roots.append(Path(t))
    rec["link_targets_inside_deleted_trees"] = len(inside)
    by_group: dict = {}
    for it in todo:
        g = by_group.setdefault(it["group"], {"items": 0, "bytes": 0, "missing": 0, "tracked": 0})
        g["items"] += 1
        g["bytes"] += it["bytes"]
        g["missing"] += 0 if it["exists"] else 1
        g["tracked"] += it["tracked"]
    rec["by_group"] = by_group
    rec["total_bytes"] = sum(it["bytes"] for it in todo)
    rec["link_targets"] = targets
    rec["fingerprint_roots"] = [str(p) for p in roots]
    if a.dry_run:
        for g, v in by_group.items():
            print(f"{g:40s} {v['items']:5d} items {v['bytes'] / 1e9:9.3f} GB  missing {v['missing']:3d}"
                  f"  tracked {v['tracked']}")
        print(f"{'total':40s} {len(todo):5d} items {rec['total_bytes'] / 1e9:9.3f} GB")
        print("\nsandboxes and other trees with links:")
        for it in todo:
            if it["group"].startswith("A"):
                print(f"   {it['path']}  {it['bytes'] / 1e9:.3f} GB  links {len(links.get(str(it['path']), []))}")
        for k, v in links.items():
            if not k.startswith(str(HOME / "tnr_")):
                print(f"   (links outside the sandboxes) {k}: {len(v)} links, all pointing inside it:",
                      all(under(t, Path(k)) for _, t in v))
        for k, v in links.items():
            if k.startswith(str(HOME / "tnr_")):
                print(f"   {k}:", *[f"{Path(x).relative_to(k)} -> {t}" for x, t in v], sep="\n      ")
        print(f"link targets outside the kept trees and the deleted trees: "
              f"{[str(r) for r in roots[len(PROTECTED):]]}; inside deleted trees: {len(inside)}")
        print("fingerprint roots:", *rec["fingerprint_roots"], sep="\n   ")
        print("\nmissing items:", *[str(it["path"]) for it in todo if not it["exists"]], sep="\n   ")
        print("\ntracked items:", *[f"{it['path']} ({it['tracked']})" for it in todo if it["tracked"]], sep="\n   ")
        print("\nscratchpads: deleting", sum(1 for it in todo if it["group"].startswith("C")), "; held:")
        for n, why in held:
            print(f"   {n}  {why}")
        # what stays beside the files deleted, by folder
        deleted = {str(it["path"]) for it in todo}
        parents = defaultdict(set)
        for it in todo:
            if it["kind"] == "file" and it["group"].startswith("D"):
                parents[(it["group"], it["path"].parent)].add(it["path"].name)
        print("\nwhat stays beside the files deleted (folders sharing a set counted together):")
        stays = defaultdict(Counter)
        for (g, par), _ in parents.items():
            names = []
            for e in sorted(os.scandir(par), key=lambda e: e.name) if par.exists() else []:
                if str(Path(e.path)) not in deleted:
                    names.append(e.name + ("/" if e.is_dir() else ""))
            key = tuple(re.sub(r"\d+", "#", n) for n in names) if g == "D surface_ios uploads" else tuple(names)
            stays[g][(str(par) if g != "D surface_ios uploads" else "<slot>", key)] += 1
        for g, c in stays.items():
            for (par, names), n in c.items():
                shown = ", ".join(names[:12]) + (f" … ({len(names)} in all)" if len(names) > 12 else "")
                print(f"   {g}: {Path(par).relative_to(S) if par != '<slot>' else par} x{n}: {shown or '(nothing)'}")
        hits = reader_hits(todo)
        lines = []
        for i, it in enumerate(todo):
            if hits.get(i):
                lines.append(f"{rel(it['path'])}:\n    " + "\n    ".join(sorted(set(hits[i]))))
        READERS.parent.mkdir(parents=True, exist_ok=True)
        READERS.write_text("\n".join(lines) + "\n", encoding="utf-8")
        code = sum(1 for i in hits if any(h.startswith(("src/", "test/", "scripts/")) for h in hits[i]))
        print(f"\nnamed in code or docs: {len(hits)} items ({code} in code); listing: {READERS}")
        print("processes:", *[json.dumps(p) for p in rec["processes"]], sep="\n   ")
        t1 = time.time()
        fp = fingerprint(roots)
        print(f"one listing of the kept trees: {time.time() - t1:.0f} s;",
              ", ".join(f"{Path(k).name} {len(v)}" for k, v in fp.items()))
        print(f"\n{time.time() - t0:.0f} s")
        return 0

    # the real run
    KEPT.mkdir(parents=True, exist_ok=True)
    rec["kept_copies"] = []
    for f in SCRATCH.glob("7d6b3770*/scratchpad/tennis_model_anatomy.html"):
        dst = KEPT / f.name
        dst.write_bytes(f.read_bytes())
        rec["kept_copies"].append({"from": str(f), "to": str(dst), "bytes": dst.stat().st_size})
    before = fingerprint(roots)
    rec["protected_files_before"] = {k: len(v) for k, v in before.items()}
    done = []
    rec["items"] = done

    def save():
        rec["deleted_bytes"] = sum(e["bytes"] for e in done if e.get("deleted"))
        rec["failed"] = [e for e in done if e.get("deleted") is False]
        rec["seconds"] = round(time.time() - t0, 1)
        RECORD.write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")

    for it in todo:
        entry = {"group": it["group"], "path": str(it["path"]), "kind": it["kind"], "bytes": it["bytes"],
                 "tracked": it["tracked"]}
        if it["why"]:
            entry["why"] = it["why"]
        done.append(entry)
        if not it["exists"]:
            entry["result"] = "not present"
            continue
        try:
            entry["result"] = remove_tree(it["path"]) if it["kind"] == "tree" else remove_file(it["path"])
            entry["deleted"] = True
        except Exception as e:                              # recorded; the run goes on with the next item
            entry["deleted"] = False
            entry["error"] = f"{type(e).__name__}: {e}"[:500]
        if it["group"].startswith("A"):                     # the kept trees checked after every sandbox
            lost = lost_files(before, fingerprint(roots))
            entry["protected_lost_after"] = lost
            print(f"{datetime.now():%H:%M:%S} {it['path']}: deleted {entry.get('deleted')}, kept trees lost "
                  f"{sum(len(v) for v in lost.values())} files", flush=True)
            if lost:
                rec["stopped"] = f"files missing from a kept tree after {it['path']}"
                save()
                print(json.dumps(lost, indent=1))
                return 1
        save()
    after = fingerprint(roots)
    rec["protected_files_after"] = {k: len(v) for k, v in after.items()}
    rec["protected_files_lost"] = lost_files(before, after)
    rec["finished"] = datetime.now().isoformat(timespec="seconds")
    save()
    print(json.dumps({k: rec[k] for k in ("deleted_bytes", "seconds", "protected_files_before",
                                         "protected_files_after", "protected_files_lost")}, indent=1))
    print("failed:", json.dumps(rec["failed"], indent=1)[:3000])
    return 1 if rec["protected_files_lost"] else 0


if __name__ == "__main__":
    sys.exit(main())
