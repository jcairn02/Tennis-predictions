"""Rebuild the live Stage 0 tables and the shared tables built on them, in one coordinated run.

Why: the Slam box-score decision (docs/decisions/2026-10-06-slam-box-scores.md) applies its overrides at a rebuild
coordinated with the studies that read Stage 0. Stage 0's code also changed on 2 October (the feature_alpha_audit
repairs), so the tables a rebuild replaces cannot be rebuilt from today's code: they are kept first.

Steps (each must succeed, or the run stops; the kept copies restore what was there):
    keep      copy every file the run replaces into data/studies/data_continuity/rebuilds/<stamp>/replaced/, under
              the same relative paths, with a SHA-256 manifest
    build     predictability_diagnostic/stage0_build.py (the decided box-score overrides apply by default), then
              stage0_checks.py
    expect    with --expect <folder>: the new Stage 0 tables must equal that folder's (a dry run's override build)
    odds      predictability_diagnostic/stage1_odds.py: tennis-data.co.uk's closing odds re-linked to the new ids
    remap     the frozen sources' link files (match_timing/links/*.parquet that refresh.py does not rebuild) follow
              every match id that changed. Old and new ids are paired by tour, tournament id, round and the two
              players' name keys, one partner each; an id without one is left as it was and listed
    refresh   match_timing/refresh.py --skip-ios: re-links the updating sources, rebuilds and checks the timeline
    features  match_timing/rebuild.py (per-player, IOS and merged inputs), then match_timing/ttt_timed.py
Writes data/studies/data_continuity/rebuilds/<stamp>/: rebuild.json (steps, seconds, counts, hashes), id_map.csv and
the kept files under replaced/.

Run: ./python.sh src/eda/data_continuity/rebuild_stage0.py [--expect <folder>] [--skip-ttt]
     ./python.sh src/eda/data_continuity/rebuild_stage0.py --restore <stamp>   # put back what that rebuild replaced
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from src.eda.data_continuity import common as K  # noqa: E402

PD = ROOT / "data" / "studies" / "predictability_diagnostic"
MT = ROOT / "data" / "studies" / "match_timing"
LINKS = MT / "links"
REBUILDS = K.OUT / "rebuilds"
TML_LOCK = ROOT / "data" / "raw" / "public_dump" / "tennis_my_life" / ".lock"
# link files that match_timing/link_sources_c.py rewrites at every refresh; every other links/*.parquet is frozen
UPDATING = {"tennis_data", "wta_api", "sofascore", "slam_feeds", "tdi", "sirgenkii"}
PD_KEEP = ["stage0_matches.parquet", "stage0_match_players.parquet", "stage0_summary.json", "stage0_cleaning_log.csv",
           "stage0_level_applied.csv", "stage0_cells.csv", "stage0_checks.json", "stage0_check_counts.csv",
           "stage0_check_box.csv", "stage1_odds.parquet", "stage1_odds_unlinked.parquet", "stage1_odds_summary.json"]
MT_KEEP = ["timing.parquet", "timing_summary.json", "timing_classes.csv", "source_calibration.csv",
           "undated_matches.parquet", "undated_matches.csv.gz", "undated_summary.csv", "timing_check.json",
           "timing_check_classes.csv", "timing_check_siblings.csv", "perplayer_features.parquet",
           "perplayer_features_summary.json", "ios_features.parquet", "ios_features_summary.json",
           "leakproof_features.parquet", "leakproof_features_summary.json", "ttt_timed.parquet",
           "ttt_timed_results.csv", "ttt_timed_summary.json"]


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def keep(dest: Path) -> list[dict]:
    """Copy every file the run replaces (and the whole links folder) under dest, keeping relative paths."""
    files = [PD / n for n in PD_KEEP] + [MT / n for n in MT_KEEP] + sorted(p for p in LINKS.rglob("*") if p.is_file())
    manifest = []
    for src in files:
        if not src.exists():
            continue
        rel = src.relative_to(ROOT)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        digest = sha(src)
        if sha(out) != digest:
            raise SystemExit(f"keep: the copy of {rel} does not match its source")
        manifest.append({"path": rel.as_posix(), "bytes": src.stat().st_size, "sha256": digest})
    return manifest


def restore(run: Path) -> int:
    """Copy every kept file of a rebuild back to its place (each checked against the manifest first)."""
    kept = run / "replaced"
    manifest = json.loads((kept / "manifest.json").read_text(encoding="utf-8"))
    for m in manifest:
        if sha(kept / m["path"]) != m["sha256"]:
            raise SystemExit(f"restore: the kept copy of {m['path']} does not match its manifest; nothing restored")
    for m in manifest:
        dest = ROOT / m["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        shutil.copy2(kept / m["path"], part)
        os.replace(part, dest)
    return len(manifest)


def step(name: str, args: list[str], log: list[dict]) -> None:
    t0 = time.time()
    print(f"--> [{name}] {' '.join(args)}", flush=True)
    done = subprocess.run([sys.executable, *args], cwd=ROOT)
    log.append({"step": name, "command": " ".join(args), "exit": done.returncode,
                "seconds": round(time.time() - t0, 1)})
    if done.returncode != 0:
        raise SystemExit(f"stopped at {name}: {' '.join(args)} exited {done.returncode}")


def frames(folder: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    return (pd.read_parquet(folder / "stage0_matches.parquet"), pd.read_parquet(folder / "stage0_match_players.parquet"))


def same_tables(a: Path, b: Path) -> dict:
    (ma, pa), (mb, pb) = frames(a), frames(b)
    def equal(x: pd.DataFrame, y: pd.DataFrame, keys: list[str]) -> bool:
        if list(x.columns) != list(y.columns) or len(x) != len(y):
            return False
        x = x.sort_values(keys).reset_index(drop=True)
        y = y.sort_values(keys).reset_index(drop=True)
        return bool(x.equals(y))
    return {"matches_equal": equal(ma, mb, ["match_id"]),
            "players_equal": equal(pa, pb, ["match_id", "player_id"]),
            "same_bytes": all(sha(a / n) == sha(b / n) for n in ("stage0_matches.parquet",
                                                                  "stage0_match_players.parquet"))}


def id_map(old: Path, new: Path) -> tuple[pd.DataFrame, list[str]]:
    """Pair every match id that left Stage 0 with the one that replaced it: same tour, tournament id and round, and
    the same two players by name key. Only one-to-one pairs count."""
    (mo, po), (mn, pn) = frames(old), frames(new)
    gone = set(mo["match_id"]) - set(mn["match_id"])
    fresh = set(mn["match_id"]) - set(mo["match_id"])

    def keyed(m: pd.DataFrame, p: pd.DataFrame, ids: set) -> pd.DataFrame:
        x = m.loc[m["match_id"].isin(ids), ["match_id", "tour", "tournament_id", "round"]].copy()
        names = (p[p["match_id"].isin(ids)].assign(k=lambda d: K.norm_name(d["player_name"]))
                 .groupby("match_id")["k"].agg(lambda s: "|".join(sorted(s))))
        # names as text even when no id changed: the empty name map is numeric, and text + number fails (14 Oct 2026)
        x["key"] = (x["tour"].astype(str) + "#" + x["tournament_id"].astype(str) + "#" + x["round"].astype(str)
                    + "#" + x["match_id"].map(names).fillna("").astype(str))
        return x[~x["key"].duplicated(keep=False)]

    pairs = keyed(mo, po, gone).merge(keyed(mn, pn, fresh), on="key", suffixes=("_old", "_new"))
    pairs = pairs[["match_id_old", "match_id_new", "tour_old", "tournament_id_old", "round_old", "key"]]
    pairs.columns = ["old_match_id", "new_match_id", "tour", "tournament_id", "round", "key"]
    return pairs, sorted(gone - set(pairs["old_match_id"]))


def remap_frozen(pairs: pd.DataFrame) -> dict:
    """Rewrite match_id in the frozen link files through the old -> new pairs (written whole, then renamed)."""
    to_new = dict(zip(pairs["old_match_id"], pairs["new_match_id"]))
    counts = {}
    for path in sorted(LINKS.glob("*.parquet")):
        if path.stem in UPDATING:
            continue
        d = pd.read_parquet(path)
        if "match_id" not in d.columns:
            continue
        hit = d["match_id"].isin(to_new)
        counts[path.name] = int(hit.sum())
        if hit.any():
            d.loc[hit, "match_id"] = d.loc[hit, "match_id"].map(to_new)
            part = path.with_name(path.name + ".part")
            d.to_parquet(part, index=False)
            os.replace(part, path)
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--expect", help="a folder whose Stage 0 tables the new ones must equal (a dry run's build)")
    ap.add_argument("--skip-ttt", action="store_true", help="leave ttt_timed.py (about 30 minutes) for later")
    ap.add_argument("--restore", metavar="STAMP", help="put back the files the rebuild <STAMP> replaced, and stop")
    a = ap.parse_args()
    if a.restore:
        print(f"restored {restore(REBUILDS / a.restore)} files from {REBUILDS / a.restore / 'replaced'}")
        return 0
    if TML_LOCK.exists():
        raise SystemExit(f"a Tennis My Life run holds {TML_LOCK}; wait for it")
    stamp = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%dT%H%MZ")
    run = REBUILDS / stamp
    lock = REBUILDS / ".lock"
    REBUILDS.mkdir(parents=True, exist_ok=True)
    try:
        handle = open(lock, "x")
    except FileExistsError:
        raise SystemExit(f"another rebuild holds {lock}")
    log: list[dict] = []
    result: dict = {"started_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"), "steps": log}
    try:
        handle.write(stamp)
        handle.close()
        t0 = time.time()
        manifest = keep(run / "replaced")
        K.write_json(run / "replaced" / "manifest.json", manifest)
        log.append({"step": "keep", "files": len(manifest), "bytes": sum(m["bytes"] for m in manifest),
                    "seconds": round(time.time() - t0, 1)})
        old = run / "replaced" / PD.relative_to(ROOT)

        step("build", ["src/eda/predictability_diagnostic/stage0_build.py"], log)
        step("checks", ["src/eda/predictability_diagnostic/stage0_checks.py"], log)
        if a.expect:
            result["expect"] = {"folder": a.expect, **same_tables(PD, Path(a.expect))}
            if not (result["expect"]["matches_equal"] and result["expect"]["players_equal"]):
                raise SystemExit(f"the new Stage 0 tables differ from {a.expect}")
        step("odds", ["src/eda/predictability_diagnostic/stage1_odds.py"], log)

        pairs, unpaired = id_map(old, PD)
        pairs.to_csv(run / "id_map.csv", index=False)
        result["ids"] = {"changed": int(len(pairs)), "left_without_partner": unpaired[:100],
                         "left_without_partner_count": len(unpaired)}
        result["remapped_rows"] = remap_frozen(pairs)
        log.append({"step": "remap", "pairs": int(len(pairs)), "rows": sum(result["remapped_rows"].values())})

        step("refresh", ["src/eda/match_timing/refresh.py", "--skip-ios"], log)
        step("features", ["src/eda/match_timing/rebuild.py"], log)
        if not a.skip_ttt:
            step("ttt", ["src/eda/match_timing/ttt_timed.py"], log)

        (mo, _), (mn, _) = frames(old), frames(PD)
        result["matches"] = {"before": int(len(mo)), "after": int(len(mn))}
        result["sha256_after"] = {n: sha(PD / n) for n in ("stage0_matches.parquet", "stage0_match_players.parquet")}
        result["stage0_summary_overrides"] = json.loads((PD / "stage0_summary.json").read_text(encoding="utf-8")).get(
            "box_overrides")
        result["timing_check"] = {k: v for k, v in json.loads((MT / "timing_check.json").read_text(encoding="utf-8"))
                                  .items() if not isinstance(v, (list, dict))}
        result["finished_at"] = pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")
        result["ok"] = True
        return 0
    finally:
        result.setdefault("ok", False)
        run.mkdir(parents=True, exist_ok=True)
        K.write_json(run / "rebuild.json", result)
        lock.unlink(missing_ok=True)
        print(json.dumps({k: result.get(k) for k in ("ok", "matches", "ids", "remapped_rows", "expect")}, default=str))


if __name__ == "__main__":
    sys.exit(main())
