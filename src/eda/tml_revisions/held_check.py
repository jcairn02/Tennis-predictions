"""The check before a held Tennis My Life season file is accepted (docs/decisions/2026-10-13-tml-lower-level-revisions.md).

The download gate (docs/decisions/2026-10-06-tml-file-versions.md) holds a season file in which rows of the current copy
are gone; it cannot tell a damaged file from a cleanup (an event given its proper id, a duplicate removed). This check
builds Stage 0 twice in a scratch tree, with the same code and the same files but the held ones: A on the current copies,
B with the held versions staged in their place. It then lists every match that differs, the players they touch, the
history check of each build, and the rows of the 2026 fit's training seasons those players play after their first change.

Nothing shared is written. The tree is outside the repository. The repository's raw folder and every staged folder but
the ones holding a checked file are linked read-only (junctions). The decided tables Stage 0 reads are copied, and so are
Tennis My Life's staged folders that hold a checked file. Only the report goes to data/studies/tml_revisions/held_check/.

    ./python.sh src/eda/tml_revisions/held_check.py setup [--names 2022_challenger.csv ...]   # default: every held file
    ./python.sh src/eda/tml_revisions/held_check.py validate   # the adapter's staging of the current copies = the staged tables
    ./python.sh src/eda/tml_revisions/held_check.py build A    # Stage 0 on the current copies (about 2 minutes)
    ./python.sh src/eda/tml_revisions/held_check.py stage      # the held versions staged in place of the current copies
    ./python.sh src/eda/tml_revisions/held_check.py build B    # Stage 0 with them
    ./python.sh src/eda/tml_revisions/held_check.py compare    # the differences -> data/studies/tml_revisions/held_check/
    ./python.sh src/eda/tml_revisions/held_check.py cleanup    # the junctions first (the link only), then the tree

TML_CHECK_TREE moves the tree (default C:/Users/zerom/tnr_tmlcheck: short, for Windows' path limit).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.current_best_model import history as H  # noqa: E402
from src.ingest.public_dump import common as PD  # noqa: E402
from src.ingest.public_dump import tennis_my_life as TML  # noqa: E402

TREE = Path(os.environ.get("TML_CHECK_TREE", "C:/Users/zerom/tnr_tmlcheck"))
MARKER = ".tml_held_check_tree"
RAW_TML = ROOT / "data" / "raw" / "public_dump" / "tennis_my_life"
HELD = RAW_TML / "held"
STAGED_TML = ROOT / "data" / "dump" / "matches" / "tennis_my_life"
# what Stage 0 reads from data/studies (stage0_build: LEVEL_RULES, DECIDED_OVERRIDES, DECIDED_CORRECTIONS)
STUDY_INPUTS = ["data/studies/predictability_diagnostic/stage0_level_rules.csv",
                "data/studies/data_continuity/slam_box_overrides.csv",
                "data/studies/input_data_audit/fixes"]
REPORT = ROOT / "data" / "studies" / "tml_revisions" / "held_check"
TEMPLATE_FRAME = ROOT / "data" / "studies" / "current_best_model" / "template_2026-10-10" / "model_frame_chain.parquet"
TRAIN_SEASONS = (2013, 2025)        # the 2026 fit's training seasons (season Y trained on 2013 .. Y - 1)


def log(msg: str) -> None:
    print(msg, flush=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def subdir_of(name: str) -> str:
    """Tennis My Life's staged folder for a catalog file (tennis_my_life.RULES)."""
    for regex, _branch, subdir, _validator, _has_year, _always in TML.RULES:
        if re.match(regex, name):
            return subdir
    raise SystemExit(f"{name}: no Tennis My Life rule stages it")


def held_files(names: list[str] | None = None) -> list[dict]:
    """The held versions (held/<stem>.<sha12>.csv and its .meta.json): name, path, sha256, reason, held_at."""
    out = []
    for meta_path in sorted(HELD.rglob("*.csv.meta.json")):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if names and meta["name"] not in names:
            continue
        path = meta_path.with_name(meta_path.name[: -len(".meta.json")])
        out.append({"name": meta["name"], "path": path, "sha256": meta["sha256"], "reason": meta.get("reason"),
                    "held_at": meta.get("held_at"), "subdir": subdir_of(meta["name"])})
    if names and len(out) != len(set(names)):
        raise SystemExit(f"held versions found for {[h['name'] for h in out]} of {names}")
    return out


def staged_path(root: Path, name: str) -> Path:
    return root / "data" / "dump" / "matches" / "tennis_my_life" / subdir_of(name) / (Path(name).stem + ".parquet")


def marker() -> dict:
    p = TREE / MARKER
    if not p.exists():
        raise SystemExit(f"{TREE} is not a check tree (no {MARKER}): run setup first")
    return json.loads(p.read_text(encoding="utf-8"))


def write_marker(state: dict) -> None:
    (TREE / MARKER).write_text(json.dumps(state, indent=1), encoding="utf-8")


# ------------------------------------------------------------------------------------------------
# The tree

def robocopy(src: Path, dst: Path, exclude_dirs: tuple[str, ...] = ()) -> None:
    cmd = ["robocopy", str(src), str(dst), "/E", "/MT:16", "/NFL", "/NDL", "/NJH", "/NP", "/R:0", "/W:0"]
    if exclude_dirs:
        cmd += ["/XD", *exclude_dirs]
    if subprocess.run(cmd, stdout=subprocess.DEVNULL).returncode >= 8:      # robocopy: 0-7 success, 8+ failures
        raise SystemExit(f"robocopy {src} failed")


def junction(link: Path, target: Path) -> None:
    subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], check=True, stdout=subprocess.DEVNULL)


def mirror(src: Path, dst: Path, copy: set[str]) -> None:
    """dst as a folder whose children link to src's, except the children named in copy (copied)."""
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        if child.is_dir() and child.name in copy:
            shutil.copytree(child, dst / child.name)
        elif child.is_dir():
            junction(dst / child.name, child)
        else:
            shutil.copy2(child, dst / child.name)


def setup(names: list[str] | None) -> dict:
    held = held_files(names)
    if not held:
        raise SystemExit("no held Tennis My Life file to check")
    if TREE.exists():
        raise SystemExit(f"{TREE} exists; run cleanup first")
    if TREE.resolve().is_relative_to(ROOT.resolve()):
        raise SystemExit("the check tree must be outside the repository")
    t0 = time.time()
    (TREE / "data").mkdir(parents=True)
    robocopy(ROOT / "src", TREE / "src", ("__pycache__",))
    for rel in STUDY_INPUTS:
        src, dst = ROOT / rel, TREE / rel
        if src.is_dir():
            shutil.copytree(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    junction(TREE / "data" / "raw", ROOT / "data" / "raw")
    mirror(ROOT / "data" / "dump", TREE / "data" / "dump", set())        # replaced below for matches/
    subprocess.run(["cmd", "/c", "rmdir", str(TREE / "data" / "dump" / "matches")], check=True)
    mirror(ROOT / "data" / "dump" / "matches", TREE / "data" / "dump" / "matches", set())
    subprocess.run(["cmd", "/c", "rmdir", str(TREE / "data" / "dump" / "matches" / "tennis_my_life")], check=True)
    mirror(STAGED_TML, TREE / "data" / "dump" / "matches" / "tennis_my_life", {h["subdir"] for h in held})
    state = {"created_at": PD.utc_now_iso(), "repository": str(ROOT), "by": "src/eda/tml_revisions/held_check.py",
             "names": [h["name"] for h in held], "held_staged": False, "seconds": round(time.time() - t0, 1)}
    write_marker(state)
    return state


def links() -> list[str]:
    ps = (f"Get-ChildItem -Path '{TREE}' -Recurse -Force -Attributes ReparsePoint -ErrorAction SilentlyContinue "
          "| ForEach-Object { $_.FullName }")
    out = subprocess.run(["powershell.exe", "-NoProfile", "-Command", ps], capture_output=True, text=True).stdout
    return [x for x in out.splitlines() if x.strip()]


def cleanup() -> dict:
    """The junctions first (rmdir removes the link, never its target), a check that none is left, then the tree."""
    if not TREE.exists():
        return {"deleted": False, "why": "no tree"}
    marker()
    for link in sorted(links(), key=len, reverse=True):
        subprocess.run(["cmd", "/c", "rmdir", link], check=True)
    left = links()
    if left:
        raise SystemExit(f"links left in the tree, nothing deleted: {left[:5]}")
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(TREE)], check=True)
    return {"deleted": not TREE.exists()}


# ------------------------------------------------------------------------------------------------
# Staging, as the adapter does it

def stage(src: Path, dest: Path, source_file: str, sha: str, retrieved_at: str | None) -> dict:
    """tennis_my_life's staging (common.stage_csv_file) with the provenance the adapter would write: the source file is
    the raw copy's own path, whatever path the bytes are read from."""
    prov = PD.Provenance(TML.SOURCE, source_file, sha, retrieved_at)
    stats = PD.stage_delimited(src, dest, prov)
    return stats


def validate() -> dict:
    """The current copies, staged here, must equal the repository's staged tables (provenance columns included)."""
    state = marker()
    out = {}
    for name in state["names"]:
        raw = RAW_TML / name
        repo_staged = staged_path(ROOT, name)
        meta = json.loads(Path(str(repo_staged) + ".meta.json").read_text(encoding="utf-8"))
        test = TREE / "validate" / (Path(name).stem + ".parquet")
        test.parent.mkdir(parents=True, exist_ok=True)
        stage(raw, test, meta["source_path"], meta["sha256"], meta["retrieved_at"])
        a, b = pd.read_parquet(test), pd.read_parquet(repo_staged)
        out[name] = {"raw_sha256_equals_staged_meta": sha256(raw) == meta["sha256"], "rows": int(len(b)),
                     "equal": bool(a.equals(b))}
        log(f"{name}: {out[name]}")
    if not all(v["equal"] and v["raw_sha256_equals_staged_meta"] for v in out.values()):
        raise SystemExit("validation failed: the staging here does not reproduce the repository's staged tables")
    state["validated"] = out
    write_marker(state)
    return out


def stage_held() -> dict:
    state = marker()
    if not (TREE / "out" / "A" / "stage0_matches.parquet").exists():
        raise SystemExit("build A first: it reads the current copies the held versions replace")
    out = {}
    for h in held_files(state["names"]):
        dest = staged_path(TREE, h["name"])
        if not dest.resolve().is_relative_to(TREE.resolve()) or dest.is_symlink():
            raise SystemExit(f"{dest} is not the tree's own copy; refusing to write it")
        stats = stage(h["path"], dest, PD.rel(RAW_TML / h["name"]), h["sha256"], h["held_at"])
        PD.write_meta(dest, {"branch": "matches", "source": TML.SOURCE, "dest": PD.rel(dest), "rows": stats["rows"],
                             "source_path": PD.rel(RAW_TML / h["name"]), "sha256": h["sha256"],
                             "retrieved_at": h["held_at"], "catalog_name": h["name"], "held_version_of_check": True})
        out[h["name"]] = {"sha256": h["sha256"], "rows": stats["rows"]}
        log(f"staged the held {h['name']} ({h['sha256'][:12]}): {stats['rows']:,} rows")
    state["held_staged"] = True
    state["staged"] = out
    write_marker(state)
    return out


def build(which: str) -> dict:
    state = marker()
    if which == "A" and state.get("held_staged"):
        raise SystemExit("the held versions are staged: A must be built on the current copies (setup again)")
    if which == "B" and not state.get("held_staged"):
        raise SystemExit("stage the held versions first")
    out = TREE / "out" / which
    logf = TREE / "logs" / f"build_{which}.log"
    logf.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    with logf.open("w", encoding="utf-8") as handle:
        rc = subprocess.run([sys.executable, str(TREE / "src" / "eda" / "predictability_diagnostic" / "stage0_build.py"),
                             "--out-dir", str(out)], cwd=TREE, stdout=handle, stderr=subprocess.STDOUT).returncode
    res = {"exit": rc, "seconds": round(time.time() - t0, 1), "log": str(logf), "out": str(out)}
    state[f"build_{which}"] = res
    write_marker(state)
    if rc:
        raise SystemExit(f"build {which} failed (exit {rc}): {logf}")
    return res


# ------------------------------------------------------------------------------------------------
# The comparison

def _ids(m: pd.DataFrame) -> pd.Series:
    return m["player_a_id"].astype(str) + "|" + m["player_b_id"].astype(str)


def explain(new: pd.DataFrame, gone: pd.DataFrame) -> pd.DataFrame:
    """Pairs of a dropped and a new match that are one match under a new key: same tour, tournament date, round and
    score, and one player in common (the players' id columns, after Stage 0's id aliases). 'key' when the event and both
    players are the same (the key was built from an id resolved later in one build: the sides may swap), 'event' when
    only the tournament id changed, 'player' when a player's id did."""
    if new.empty or gone.empty:
        return pd.DataFrame(columns=["old_id", "new_id", "kind"])
    key = ["tour", "tournament_date", "round", "score"]
    j = gone.merge(new, on=key, suffixes=("_old", "_new"))
    pa_old, pb_old = j["player_a_id_old"].astype(str), j["player_b_id_old"].astype(str)
    pa_new, pb_new = j["player_a_id_new"].astype(str), j["player_b_id_new"].astype(str)
    common = ((pa_old == pa_new) | (pa_old == pb_new) | (pb_old == pa_new) | (pb_old == pb_new))
    same_pair = (((pa_old == pa_new) & (pb_old == pb_new)) | ((pa_old == pb_new) & (pb_old == pa_new)))
    same_event = j["tournament_id_old"].astype(str) == j["tournament_id_new"].astype(str)
    kind = np.select([same_pair & same_event, same_pair], ["key", "event"], "player")
    j = j.assign(kind=kind)[common.to_numpy()].copy()
    j = j.drop_duplicates("match_id_old").drop_duplicates("match_id_new")
    return j.rename(columns={"match_id_old": "old_id", "match_id_new": "new_id"})[["old_id", "new_id", "kind"]]


def fact_changes(ma: pd.DataFrame, mb: pd.DataFrame, pa: pd.DataFrame, pb: pd.DataFrame, ids) -> pd.Series:
    """For each revised match, the facts that differ (match facts by name; player facts as 'player.<fact>')."""
    a = ma.set_index("match_id").loc[ids, H.MATCH_FACTS].astype(str)
    b = mb.set_index("match_id").loc[ids, H.MATCH_FACTS].astype(str)
    out = {i: [c for c in H.MATCH_FACTS if a.at[i, c] != b.at[i, c]] for i in ids}
    key = ["match_id", "side"]
    qa = pa[pa["match_id"].isin(ids)].astype({c: str for c in H.PLAYER_FACTS}).set_index(key).sort_index()
    qb = pb[pb["match_id"].isin(ids)].astype({c: str for c in H.PLAYER_FACTS}).set_index(key).sort_index()
    both = qa.index.intersection(qb.index)
    diff = qa.loc[both, H.PLAYER_FACTS[1:]] != qb.loc[both, H.PLAYER_FACTS[1:]]
    for (mid, _side), row in diff.iterrows():
        out[mid] += [f"player.{c}" for c in row.index[row.to_numpy()] if f"player.{c}" not in out[mid]]
    return pd.Series({k: ";".join(v) for k, v in out.items()})


def reach(changed: pd.DataFrame, players_long: pd.DataFrame) -> dict:
    """Rows of the 2026 fit's training seasons (the template's frame) in which a touched player plays: any, and those
    dated after the player's first changed match (only these can have different inputs)."""
    if not TEMPLATE_FRAME.exists() or changed.empty:
        return {"frame": str(TEMPLATE_FRAME), "available": TEMPLATE_FRAME.exists()}
    first = (players_long.assign(d=pd.to_datetime(players_long["tournament_date"], errors="coerce"))
             .groupby("player_id")["d"].min())
    fr = pd.read_parquet(TEMPLATE_FRAME, columns=["match_id", "season", "tournament_date"]).astype({"match_id": str})
    fr = fr[fr["season"].between(*TRAIN_SEASONS)]
    ref_p = pd.read_parquet(H.REF_STAGE0 / "stage0_match_players.parquet", columns=["match_id", "player_id"])
    ref_p = ref_p.astype({"match_id": str, "player_id": str})
    rp = ref_p[ref_p["match_id"].isin(set(fr["match_id"])) & ref_p["player_id"].isin(set(first.index))]
    rp = rp.merge(fr, on="match_id")
    rp["after"] = pd.to_datetime(rp["tournament_date"], errors="coerce") > rp["player_id"].map(first)
    by_season = rp[rp["after"]].drop_duplicates("match_id").groupby("season").size()
    return {"frame": H.R.rel(TEMPLATE_FRAME) if hasattr(H.R, "rel") else str(TEMPLATE_FRAME),
            "training_rows": int(len(fr)), "touched_players": int(first.size),
            "touched_players_in_training_rows": int(rp["player_id"].nunique()),
            "rows_with_a_touched_player": int(rp["match_id"].nunique()),
            "rows_after_the_players_first_change": int(rp.loc[rp["after"], "match_id"].nunique()),
            "rows_after_by_season": {int(k): int(v) for k, v in by_season.items()}}


def cleaning_rules(folder: Path) -> pd.Series:
    """The rows each cleaning rule touched, by rule, tour, level, qualifying and year (the log's own cells)."""
    p = folder / "stage0_cleaning_log.csv"
    if not p.exists():
        return pd.Series(dtype="int64")
    t = pd.read_csv(p)
    return t.groupby(["rule_id", "tour", "level", "qualifying", "year"])["count"].sum()


def compare() -> dict:
    state = marker()
    a_dir, b_dir = TREE / "out" / "A", TREE / "out" / "B"
    ma, pa = H.load(a_dir)
    mb, pb = H.load(b_dir)
    ia, ib = pd.Index(ma["match_id"]), pd.Index(mb["match_id"])
    new, gone = mb[~ib.isin(ia)].copy(), ma[~ia.isin(ib)].copy()
    both = ia.intersection(ib)
    ha = H.content_hash(ma[ma["match_id"].isin(both)], pa[pa["match_id"].isin(both)])
    hb = H.content_hash(mb[mb["match_id"].isin(both)], pb[pb["match_id"].isin(both)])
    rev_ids = both[ha.reindex(both).to_numpy() != hb.reindex(both).to_numpy()]
    revised = mb[mb["match_id"].isin(rev_ids)].copy()
    revised["changed"] = revised["match_id"].map(fact_changes(ma, mb, pa, pb, list(rev_ids)))
    pairs = explain(new, gone)
    new["kind"], gone["kind"], revised["kind"] = "new", "dropped", "revised"
    new["paired_with"] = new["match_id"].map(pairs.set_index("new_id")["old_id"])
    gone["paired_with"] = gone["match_id"].map(pairs.set_index("old_id")["new_id"])
    new["pair_kind"] = new["match_id"].map(pairs.set_index("new_id")["kind"])
    gone["pair_kind"] = gone["match_id"].map(pairs.set_index("old_id")["kind"])
    cols = ["kind", "match_id", "source", "tour", "map_level", "qualifying", "year", "tournament_id", "tournament_date",
            "round", "player_a_id", "player_b_id", "score", "has_box", "paired_with", "pair_kind", "changed"]
    changes = pd.concat([gone, new, revised], ignore_index=True).reindex(columns=cols)
    changes["lower_level"] = H.lower_level(changes)
    REPORT.mkdir(parents=True, exist_ok=True)
    changes.to_csv(REPORT / "changes.csv", index=False)

    ids = set(changes["match_id"]) | set(changes["paired_with"].dropna())
    touched = pd.concat([pa[pa["match_id"].isin(ids)], pb[pb["match_id"].isin(ids)]])[["match_id", "player_id"]]
    touched = touched.astype(str).drop_duplicates()
    dates = pd.concat([ma, mb])[["match_id", "tournament_date"]].astype({"match_id": str}).drop_duplicates("match_id")
    touched = touched.merge(dates, on="match_id", how="left")
    players = (touched.groupby("player_id").agg(matches=("match_id", "nunique"), first=("tournament_date", "min"),
                                               last=("tournament_date", "max")).reset_index())
    players.to_csv(REPORT / "players_touched.csv", index=False)

    rules = pd.DataFrame({"A": cleaning_rules(a_dir), "B": cleaning_rules(b_dir)}).fillna(0).astype("int64")
    rules = rules[rules["A"] != rules["B"]]
    rules.to_csv(REPORT / "cleaning_rules_changed.csv")

    hist = {}
    for which, folder in (("A", a_dir), ("B", b_dir)):
        res = H.check(folder, H.LIVE_TIMING)
        hist[which] = {"line": H.summary_line(res), "gated": res["gated"], "allowed_main_tour": res["allowed_main_tour"],
                       "template_ok": res["template_ok"]}
    (REPORT / "history_A_B.json").write_text(json.dumps(hist, indent=1, default=str), encoding="utf-8")

    def tally(t: pd.DataFrame) -> list[dict]:
        if t.empty:
            return []
        g = t.groupby(["kind", "source", "tour", "map_level", "year"], dropna=False).size().rename("matches")
        return g.reset_index().to_dict("records")

    main_tour = changes[~changes["lower_level"]]
    summary = {
        "checked": state["names"], "staged": state.get("staged"), "validated": state.get("validated"),
        "builds": {k: state.get(f"build_{k}") for k in ("A", "B")},
        "matches": {"A": int(len(ma)), "B": int(len(mb))},
        "dropped": int(len(gone)), "new": int(len(new)), "revised": int(len(revised)),
        "paired": {k: int((pairs["kind"] == k).sum()) for k in ("key", "event", "player")},
        "dropped_unpaired": int(gone["paired_with"].isna().sum()), "new_unpaired": int(new["paired_with"].isna().sum()),
        "main_tour_changes": int(len(main_tour)), "main_tour_examples": main_tour["match_id"].head(10).tolist(),
        "by": tally(changes),
        "revised_facts": (revised["changed"].str.split(";").explode().value_counts().to_dict() if len(revised) else {}),
        "players_touched": int(len(players)),
        "reach": reach(changes, touched),
        "cleaning_rules_changed": {"|".join(map(str, r)): {"A": int(v["A"]), "B": int(v["B"])}
                                   for r, v in rules.iterrows()},
        "history": {k: v["line"] for k, v in hist.items()},
        "written": PD.utc_now_iso(),
    }
    (REPORT / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("step", choices=["setup", "validate", "build", "stage", "compare", "cleanup"])
    ap.add_argument("which", nargs="?", choices=["A", "B"], help="build: A (current copies) or B (held versions)")
    ap.add_argument("--names", nargs="*", help="setup: the held files to check (default: every held file)")
    a = ap.parse_args()
    if a.step == "setup":
        res = setup(a.names)
    elif a.step == "validate":
        res = validate()
    elif a.step == "build":
        if not a.which:
            ap.error("build needs A or B")
        res = build(a.which)
    elif a.step == "stage":
        res = stage_held()
    elif a.step == "compare":
        res = compare()
    else:
        res = cleanup()
    print(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
