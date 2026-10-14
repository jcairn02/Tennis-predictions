"""The frozen reference of the current best model: the template's build of 8 Oct 2026 and the tables it was built on,
copied, hashed and kept read-only, so that new data, new features and rebuilds are compared against a fixed point.

The owner (8 Oct 2026; docs/decisions/2026-10-08-current-best-model.md, amendment): "I want to freeze the template of
current model and its data locations as comparisons so the new data thats coming, if it harms results we will want to
make some modifications, Either to ignore data, lower its weight, or find a way to mathematically change and integrate it
so its useful. I dont want to lose sight of the current model"

What is frozen, in data/studies/current_best_model/reference_2026-10-08/frozen/ (gitignored; manifest.json is tracked):
    instance/   the current best model as built on 8 Oct: data/studies/model_rebuild/, whole. The 58-input frame
                (67,226 matches), its input list, its 32 fits (seasons 2019-2026, seeds 0-3), the stage-2 speed column on
                the corrected speed history, the chain's records and its comparison with the previous model
    speed/      stage 2's speed history (the live feed's corrected panel) and the adaptive columns and coefficients
    tables/     the tables it was built on: the files the coordinated Stage 0 rebuild of 8 Oct (18:53 UTC) wrote, at
                their repository paths (Stage 0, Stage 1's odds, the match timeline and its links, the leak-proof IOS
                and features, TrueSkill Through Time), as the instance's build read them
    tables_later/  the ones of those files a TDI refresh rewrote in place after the build had copied them (20:12-20:30
                UTC), as they stood at the freeze: not the build's versions, which no copy on disk holds
    previous/   the previous model, the 30 Sep build every study up to 8 Oct was scored on: its frame and input list,
                its fits of seeds 0-3 in their three folders, the two checks its reused fits require, and the frame of
                Polymarket's early prices. (Its tables are kept by the 7 Oct rebuild in data_continuity/rebuilds/
                2026-10-07T0005Z/replaced/; recorded in the inventory, not copied again)
    code/       src/, docs/, test/ and the root files (CLAUDE.md, the environments, the shims), and git's HEAD and status:
                much of the code is not committed
    env/        the TabPFN-3.5 checkpoint the fits used (it lives outside the repository, where a package upgrade could
                replace it) and pip freeze of both environments
    files.csv.gz       every frozen file: role, source, frozen path, bytes, SHA-256
    inventory.csv.gz   every file under data/studies at the freeze (path, bytes, mtime, SHA-256), the rebuilds' kept
                       copies and this folder excepted: what a builder could have read, for a later exact rebuild

Commands:
    --freeze   build the reference, once (it refuses if the manifest or a partial copy exists). First it checks that
               the tables are the 8 Oct rebuild's (Stage 0's SHA-256 as rebuild.json recorded it, none of the 72 files
               written since) and that every fit of the instance was fitted on its frame. Every copy is hashed against
               its source, and every copy is made read-only
    --verify   re-hash every frozen file against files.csv.gz, and report which sources have moved on since the freeze;
               writes verify.json beside the manifest. Exit 1 if a frozen file is missing or differs
Run: ./python.sh src/eda/current_best_model/reference.py --freeze | --verify
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import os
import shutil
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.serve_speed_tabpfn import common as C  # noqa: E402
from src.eda.serve_speed_tabpfn import forecasts as F  # noqa: E402

REF_ID = "2026-10-08"
STUDIES = ROOT / "data" / "studies"
REF = STUDIES / "current_best_model" / f"reference_{REF_ID}"
FROZEN = REF / "frozen"
PARTIAL = REF / "frozen.partial"
MANIFEST = REF / "manifest.json"
VERIFY = REF / "verify.json"
FILES_CSV = "files.csv.gz"
INVENTORY_CSV = "inventory.csv.gz"

REBUILD = STUDIES / "data_continuity" / "rebuilds" / "2026-10-08T1853Z"     # the tables the instance was built on
INSTANCE_SRC = STUDIES / "model_rebuild"
SPEED_SRC = (STUDIES / "serve_speed_tabpfn" / "live" / "speed_panel_frozen_corrected.parquet",
             STUDIES / "serve_speed_tabpfn" / "live" / "speed_panel_frozen_corrected.json",
             STUDIES / "serve_speed_tabpfn" / "adaptive" / "columns.parquet",
             STUDIES / "serve_speed_tabpfn" / "adaptive" / "columns_meta.json",
             STUDIES / "serve_speed_tabpfn" / "adaptive" / "coefficients.json")
PREVIOUS_TABLES = STUDIES / "data_continuity" / "rebuilds" / "2026-10-07T0005Z" / "replaced"
FIT_FOLDER = {"study": "local", "feature_interactions": "fi_local", "race": "race_local"}   # forecasts.folders' labels
SEASONS = tuple(range(2019, 2027))
SEEDS = (0, 1, 2, 3)
CODE_DIRS = ("src", "docs", "test")
CODE_FILES = ("AGENTS.md", "CLAUDE.md", "README.md", ".gitignore", "environment.yml", "environment-tabpfn.yml",
              "environment-tabpfn-local.yml", "python.sh", "python_tabpfn.sh", "python_tabpfn_local.sh")
ENVS = {"tennis": Path("C:/Users/zerom/miniforge3/envs/tennis/python.exe"),
        "tennis-tabpfn-local": Path("C:/Users/zerom/miniforge3/envs/tennis-tabpfn-local/python.exe")}
SKIP_PARTS = {"__pycache__", ".pytest_cache", "pytest_tmp"}
FIELDS = ["role", "source", "frozen", "bytes", "sha256"]
OWNER = ("I want to freeze the template of current model and its data locations as comparisons so the new data thats "
         "coming, if it harms results we will want to make some modifications, Either to ignore data, lower its "
         "weight, or find a way to mathematically change and integrate it so its useful. I dont want to lose sight of "
         "the current model")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha(path: Path) -> str:
    return C.sha256_file(path)


def rel(path: Path) -> str:
    """Repository-relative POSIX path, or the absolute path for a file outside the repository."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).resolve().as_posix()


def skipped(path: Path) -> bool:
    return bool(SKIP_PARTS & set(path.parts))


# ------------------------------------------------------------------------------------------------
# What is frozen

def instance_frame_sha() -> str:
    return sha(INSTANCE_SRC / "model_frame.parquet")


def fit_meta(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as z:
        return json.loads(str(z["meta"]))


def checkpoint() -> Path:
    """The TabPFN checkpoint the instance's fits record (all of them must name the same one)."""
    names = {fit_meta(p).get("checkpoint") for p in sorted((INSTANCE_SRC / "fits").glob("*.npz"))}
    if len(names) != 1:
        raise RuntimeError(f"the instance's fits name {len(names)} checkpoints: {names}")
    path = Path(names.pop())
    if not path.exists():
        raise FileNotFoundError(f"the checkpoint the fits used is not on disk: {path}")
    return path


def rebuild_tables() -> tuple[list[str], list[str]]:
    """The 72 files the 8 Oct rebuild wrote: (unchanged since it ended, written again after it ended). The instance's
    sandbox copied data/studies at about 20:00 UTC, so a file written again later is not the version it was built on."""
    rb = json.loads((REBUILD / "rebuild.json").read_text(encoding="utf-8"))
    end = datetime.fromisoformat(rb["finished_at"]).timestamp()
    kept = [e["path"] for e in json.loads((REBUILD / "replaced" / "manifest.json").read_text(encoding="utf-8"))]
    later = [p for p in kept if (ROOT / p).stat().st_mtime > end + 60]
    return [p for p in kept if p not in later], later


def plan() -> list[tuple[str, Path, str]]:
    """(role, source, path under frozen/) for every file to copy."""
    out = []
    for f in sorted(INSTANCE_SRC.rglob("*")):
        if f.is_file() and not skipped(f):
            out.append(("instance", f, "instance/" + f.relative_to(INSTANCE_SRC).as_posix()))
    out += [("speed", f, "speed/" + f.name) for f in SPEED_SRC]
    exact, later = rebuild_tables()
    out += [("tables", ROOT / p, "tables/" + p) for p in exact]
    out += [("tables, later version", ROOT / p, "tables_later/" + p) for p in later]
    P = C.DEFAULT
    out += [("previous", P.model_frame, "previous/" + P.model_frame.name),
            ("previous", P.model_inputs, "previous/" + P.model_inputs.name),
            ("previous", P.early, "previous/" + P.early.name)]
    out += [("previous", P.checks / n, "previous/checks/" + n) for n in ("repro_check.json", "fingerprint_check.json")]
    for s in SEASONS:
        for k in SEEDS:
            label, path = F.find_fit("model", s, k, P)
            out.append(("previous", path, f"previous/{FIT_FOLDER[label]}/{path.name}"))
    for d in CODE_DIRS:
        for f in sorted((ROOT / d).rglob("*")):
            if f.is_file() and not skipped(f):
                out.append(("code", f, "code/" + rel(f)))
    out += [("code", ROOT / n, "code/" + n) for n in CODE_FILES if (ROOT / n).exists()]
    cp = checkpoint()
    out.append(("env", cp, "env/" + cp.name))
    return out


def preconditions() -> dict:
    """Stage 0 is the 8 Oct rebuild's, and the instance's fits were fitted on its frame. Records which of the 72 tables
    were written again after the rebuild, and whether the leak-proof table and the timeline the instance's builders
    recorded are still on disk."""
    rb = json.loads((REBUILD / "rebuild.json").read_text(encoding="utf-8"))
    exact, later = rebuild_tables()
    out = {"rebuild": REBUILD.name, "rebuild_ok": bool(rb.get("ok")), "tables": len(exact) + len(later)}
    for name, want in rb["sha256_after"].items():
        out[f"{name} is the rebuild's"] = sha(STUDIES / "predictability_diagnostic" / name) == want
    out["tables written again after the rebuild ended"] = later
    built = json.loads((INSTANCE_SRC / "chain_outputs" / "tabpfn_leakproof_manifest.json").read_text(encoding="utf-8"))
    for key, path in (("leakproof_features", "match_timing/leakproof_features.parquet"),
                      ("timing", "match_timing/timing.parquet")):
        want = built["sources"][key]["sha256"]
        out[f"{key}: SHA-256 the instance's builders recorded"] = want
        out[f"{key}: on disk now"] = sha(STUDIES / path) == want
    frame_sha = instance_frame_sha()
    fits = sorted((INSTANCE_SRC / "fits").glob("*.npz"))
    out["instance frame sha256"] = frame_sha
    out["instance fits"] = len(fits)
    out["instance fits on another frame"] = [p.name for p in fits if fit_meta(p).get("model_frame_sha256") != frame_sha]
    out["ok"] = (out["rebuild_ok"] and all(v for k, v in out.items() if k.endswith("is the rebuild's"))
                 and len(fits) == len(SEASONS) * len(SEEDS) and not out["instance fits on another frame"])
    return out


# ------------------------------------------------------------------------------------------------
# Copies, the file list and the inventory

def copy_file(src: Path, dst: Path) -> tuple[int, str]:
    """Copy src to dst (metadata kept) and return (bytes, SHA-256); the copy must hash as its source."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    want = sha(src)
    shutil.copy2(src, dst)
    got = sha(dst)
    if got != want:
        raise RuntimeError(f"{src}: the copy's SHA-256 differs from the source's (changed while copying?)")
    return dst.stat().st_size, got


def write_rows(path: Path, rows: list[dict], fields: list[str]) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def read_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def generated(dst: Path, text: str) -> tuple[int, str]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8")
    return dst.stat().st_size, sha(dst)


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else f"exit {r.returncode}\n{r.stdout}\n{r.stderr}"


def inventory_rows(base: Path = STUDIES, exclude: tuple[Path, ...] = ()) -> list[dict]:
    """Every file under base (the rebuilds' kept copies, this reference and the excluded folders aside): path, bytes,
    mtime and SHA-256; an unreadable or vanished file is listed with the error instead of a hash."""
    exclude = tuple(Path(p).resolve() for p in exclude) + (REF.resolve(),)
    files = []
    for f in base.rglob("*"):
        if skipped(f) or "replaced" in f.parts and "rebuilds" in f.parts:
            continue
        r = f.resolve()
        if any(r == e or e in r.parents for e in exclude) or not f.is_file():
            continue
        files.append(f)

    def one(f: Path) -> dict:
        try:
            st = f.stat()
            return {"path": rel(f), "bytes": st.st_size,
                    "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds"),
                    "sha256": sha(f)}
        except OSError as e:
            return {"path": rel(f), "bytes": "", "mtime": "", "sha256": f"unreadable: {type(e).__name__}"}

    with ThreadPoolExecutor(8) as pool:
        rows = list(pool.map(one, sorted(files)))
    return rows


def set_read_only(folder: Path) -> int:
    n = 0
    for f in folder.rglob("*"):
        if f.is_file():
            os.chmod(f, stat.S_IREAD)
            n += 1
    return n


# ------------------------------------------------------------------------------------------------
# Freeze and verify

def freeze() -> dict:
    if MANIFEST.exists() or FROZEN.exists():
        raise SystemExit(f"the reference already exists ({REF}); it is built once")
    if PARTIAL.exists():
        raise SystemExit(f"{PARTIAL} is left from an interrupted freeze: look at it, and remove it by hand to retry")
    pre = preconditions()
    if not pre["ok"]:
        raise SystemExit(f"preconditions failed, nothing copied: {json.dumps(pre, indent=1)}")
    C.log(f"preconditions hold: {pre['tables']} tables of {pre['rebuild']}, {pre['instance fits']} fits on the frame")
    rows = []
    for role, src, dst in plan():
        size, digest = copy_file(src, PARTIAL / dst)
        rows.append({"role": role, "source": rel(src), "frozen": dst, "bytes": size, "sha256": digest})
    C.log(f"copied {len(rows):,} files, {sum(r['bytes'] for r in rows) / 1e9:.2f} GB")
    head = run(["git", "rev-parse", "HEAD"]).strip()
    status = run(["git", "status", "--porcelain"])
    for name, text, role, source in (
            ("code/git_head.txt", head + "\n", "code", "generated: git rev-parse HEAD"),
            ("code/git_status.txt", status, "code", "generated: git status --porcelain"),
            *[(f"env/pip_freeze_{env}.txt", run([str(py), "-m", "pip", "freeze"]), "env",
               f"generated: {env} pip freeze") for env, py in ENVS.items()],
            *[(f"env/python_{env}.txt", run([str(py), "-c", "import sys; print(sys.version)"]), "env",
               f"generated: {env} python version") for env, py in ENVS.items()]):
        size, digest = generated(PARTIAL / name, text)
        rows.append({"role": role, "source": source, "frozen": name, "bytes": size, "sha256": digest})
    write_rows(PARTIAL / FILES_CSV, rows, FIELDS)
    C.log("hashing the inventory of data/studies (every file, a few minutes)")
    inv = inventory_rows()
    write_rows(PARTIAL / INVENTORY_CSV, inv, ["path", "bytes", "mtime", "sha256"])
    PARTIAL.rename(FROZEN)
    n_ro = set_read_only(FROZEN)
    by_role = pd.DataFrame(rows).groupby("role")["bytes"].agg(["size", "sum"])
    key = {r["frozen"]: r for r in rows}
    comparison = json.loads((FROZEN / "instance" / "comparison.json").read_text(encoding="utf-8"))
    coef_2026 = comparison["coefficients"]["rebuilt_full_corrected_speed"]["2026"]
    frame = pd.read_parquet(FROZEN / "instance" / "model_frame.parquet", columns=["season"])
    fit0 = fit_meta(FROZEN / "instance" / "fits" / "model__2026__seed0.npz")
    manifest = {
        "reference": REF_ID,
        "created_at": now(),
        "owner": OWNER,
        "decision": "docs/decisions/2026-10-08-current-best-model.md",
        "what": "the current best model's build of 8 Oct 2026 (data/studies/model_rebuild/) and the tables of the "
                "Stage 0 rebuild 2026-10-08T1853Z it was built on, copied and hashed; frozen/ holds the copies "
                "(read-only, gitignored), frozen/files.csv.gz lists each with its SHA-256",
        "configuration": {
            "stage 1": "local TabPFN-3.5 (non-thinking) on the 58 inputs of instance/model_inputs.json; season Y "
                       "trained on 2013 .. Y - 1; config " + json.dumps(fit0["config"]) + "; each match predicted as "
                       "stored and with A and B swapped, symmetrised; eta = log-odds of the seed mean",
            "stage 2": "logit q = s_tour,Y eta + b_Y spd_L (28-day speed form; 0 for women); s and b fitted on "
                       "2019 .. Y - 1 from seeds 0-3, debut seasons out, b shrunk with tau 0.05; the speed column on "
                       "the corrected history: instance/speed_columns_corrected.parquet (spd_L_B, the weekly feed)",
            "coefficients_2026 (s_atp, s_wta, b_shrunk, b, se_b)": coef_2026,
            "versions": fit0["versions"], "checkpoint": fit0["checkpoint"], "device": fit0["device"]},
        "key_files": {k: {"source": key[k]["source"], "sha256": key[k]["sha256"], "bytes": key[k]["bytes"]}
                      for k in ("instance/model_frame.parquet", "instance/model_inputs.json",
                                "instance/speed_columns_corrected.parquet",
                                "tables/data/studies/predictability_diagnostic/stage0_matches.parquet",
                                "tables/data/studies/predictability_diagnostic/stage0_match_players.parquet",
                                "tables/data/studies/predictability_diagnostic/stage1_odds.parquet",
                                "tables/data/studies/match_timing/timing.parquet",
                                "previous/model_frame.parquet", "env/" + Path(fit0["checkpoint"]).name)
                      if k in key},
        "instance": {"matches": int(len(frame)), "seasons": [int(frame["season"].min()), int(frame["season"].max())],
                     "fits": int(sum(1 for r in rows if r["frozen"].startswith("instance/fits/"))),
                     "fit seasons": [SEASONS[0], SEASONS[-1]], "fit seeds": [SEEDS[0], SEEDS[-1]]},
        "tables": {
            "exact": int(sum(1 for r in rows if r["role"] == "tables")),
            "later version": int(sum(1 for r in rows if r["role"] == "tables, later version")),
            "note": "tables/ holds the files of the 8 Oct rebuild (2026-10-08T1853Z) as the instance's build read them, "
                    "Stage 0 and Stage 1's odds among them. The instance's sandbox copied data/studies at about 20:00 "
                    "UTC; a TDI refresh then rewrote the timeline, its TDI links and the leak-proof IOS and features "
                    "in place (20:12-20:30 UTC) without keeping the earlier files, and no backup holds them. Those "
                    "files are in tables_later/ as they stood at the freeze: NOT the versions the instance was built "
                    "on (the SHA-256 its builders recorded for the leak-proof table and the timeline are in "
                    "preconditions, and match nothing on disk). The instance's frame and fits are unaffected. The "
                    "earlier versions could be rebuilt from TDI's raw files received before 19:22 UTC (untested)"},
        "previous": {"what": "the 30 Sep build (data/studies/surface_rating_race/model/), on which every study up "
                             "to 8 Oct was scored; its fits of seeds 0-3 in their reuse folders",
                     "tables": rel(PREVIOUS_TABLES) + " (kept by the 7 Oct rebuild; hashed in the inventory)"},
        "counts": {role: {"files": int(r["size"]), "bytes": int(r["sum"])} for role, r in by_role.iterrows()},
        "read_only_files": n_ro,
        "files_csv": {"path": f"frozen/{FILES_CSV}", "rows": len(rows), "sha256": sha(FROZEN / FILES_CSV)},
        "inventory": {"path": f"frozen/{INVENTORY_CSV}", "files": len(inv),
                      "bytes": int(sum(int(r["bytes"]) for r in inv if r["bytes"] != "")),
                      "unreadable": sum(1 for r in inv if r["sha256"].startswith("unreadable")),
                      "sha256": sha(FROZEN / INVENTORY_CSV)},
        "preconditions": pre,
        "git": {"head": head, "status_lines": len([x for x in status.splitlines() if x.strip()]),
                "untracked_lines": len([x for x in status.splitlines() if x.startswith("??")])},
    }
    C.write_json(MANIFEST, manifest)
    C.log(f"reference {REF_ID} frozen: {len(rows):,} files, inventory of {len(inv):,}; manifest {rel(MANIFEST)}")
    return manifest


def check(rows: list[dict], frozen: Path, sources: bool = True) -> dict:
    """Missing, differing and writable frozen files; with sources, which sources have changed or gone since."""
    out = {"files": len(rows), "missing": [], "differ": [], "writable": 0, "sources_moved_on": [],
           "sources_gone": []}
    for r in rows:
        p = frozen / r["frozen"]
        if not p.exists():
            out["missing"].append(r["frozen"])
            continue
        if p.stat().st_size != int(r["bytes"]) or sha(p) != r["sha256"]:
            out["differ"].append(r["frozen"])
        if os.access(p, os.W_OK):
            out["writable"] += 1
        if sources and not r["source"].startswith("generated:"):
            s = Path(r["source"]) if Path(r["source"]).is_absolute() else ROOT / r["source"]
            if not s.exists():
                out["sources_gone"].append(r["source"])
            elif s.stat().st_size != int(r["bytes"]) or sha(s) != r["sha256"]:
                out["sources_moved_on"].append(r["source"])
    return out


def verify(write: bool = True) -> dict:
    m = C.read_json(MANIFEST)
    files = FROZEN / FILES_CSV
    if sha(files) != m["files_csv"]["sha256"]:
        raise SystemExit(f"{files} differs from the manifest's record; nothing else can be trusted")
    res = check(read_rows(files), FROZEN)
    res["inventory_intact"] = sha(FROZEN / INVENTORY_CSV) == m["inventory"]["sha256"]
    res["ok"] = not res["missing"] and not res["differ"] and res["inventory_intact"]
    moved = pd.Series([s.split("/")[2] if s.startswith("data/studies/") else
                       "outside the repository" if Path(s).is_absolute() else s.split("/")[0]
                       for s in res["sources_moved_on"]], dtype=object)
    summary = {"verified_at": now(), "reference": REF_ID, "ok": res["ok"], "files": res["files"],
               "missing": res["missing"], "differ": res["differ"], "writable": res["writable"],
               "inventory_intact": res["inventory_intact"],
               "sources_moved_on_since_the_freeze": {"count": len(res["sources_moved_on"]),
                                                     "by_folder": moved.value_counts().to_dict(),
                                                     "first": res["sources_moved_on"][:20]},
               "sources_gone": res["sources_gone"][:20]}
    if write:
        C.write_json(VERIFY, summary)
    return summary


# ------------------------------------------------------------------------------------------------
# Reading the reference

def paths(which: str = "reference") -> C.Paths:
    """The serve-speed harness's paths pointed at a frozen model: "reference" (the 8 Oct build) or "previous" (30 Sep).
    Every fit is read from the frozen copies; no live folder is consulted."""
    if which == "reference":
        d = FROZEN / "instance"
        return C.DEFAULT.with_(model_frame=d / "model_frame.parquet", model_inputs=d / "model_inputs.json",
                               local=d / "fits", fi_local=d / "no_fits_here", race_local=d / "no_fits_here",
                               checks=d / "no_checks_here", early=FROZEN / "previous" / C.DEFAULT.early.name)
    if which == "previous":
        d = FROZEN / "previous"
        return C.DEFAULT.with_(model_frame=d / "model_frame.parquet", model_inputs=d / "model_inputs.json",
                               local=d / "local", fi_local=d / "fi_local", race_local=d / "race_local",
                               checks=d / "checks", early=d / C.DEFAULT.early.name)
    raise ValueError("which: reference or previous")


def speed_column(which: str = "reference") -> pd.Series:
    """The model's stage-2 column spd_L_B by match id: the reference's on the corrected speed history, the previous
    model's as the adjustment used it."""
    f = FROZEN / ("instance/speed_columns_corrected.parquet" if which == "reference" else "speed/columns.parquet")
    t = pd.read_parquet(f, columns=["match_id", "spd_L_B"])
    return t.astype({"match_id": str}).set_index("match_id")["spd_L_B"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze", action="store_true")
    g.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.freeze:
        m = freeze()
        print(json.dumps({k: m[k] for k in ("counts", "files_csv", "inventory", "git")}, indent=1))
        return 0
    s = verify()
    print(json.dumps(s, indent=1))
    return 0 if s["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
