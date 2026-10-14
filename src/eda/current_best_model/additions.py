"""Lower-level data the owner accepted into the current best model's training history beyond the reference's feeds
(since 10 Oct 2026; docs/decisions/2026-10-10-men-2026-challenger-data.md): packages in ACCEPTED/<name>/, listed in
ACCEPTED/accepted.json, merged into a build's Stage 0 and timeline inside its sandbox. The repository's live tables are
never changed (other sessions read them; the decided rebuild is data_continuity/rebuild_stage0.py's).

A package (--package, from a READY candidate Stage 0 of role F's builder and the decision that accepted it):
    matches.parquet         the added matches' Stage 0 rows (stage0_matches' columns, the candidate's values)
    match_players.parquet   their two player rows each
    timing.parquet          their timeline rows (the candidate's clock: the sources' days and windows)
    completions.parquet     box scores completing matches Stage 0 holds as results only: per (match, side) the match's
                            box columns and the player row's box columns, as the candidate applied them
    manifest.json           counts, every file's sha256, the candidate and its manifest's sha256, the decision
--apply [--tree T]: every listed package merged into T's (default this tree's) stage0_matches, stage0_match_players and
    timing.parquet:
      * an added match whose id T already holds is skipped (its feed published it since), and so is one whose two
        players already meet in the same tournament and round under another id (the feed's row wins);
      * a completion applies only to a match T still holds without a box score, with the same players;
      * Stage 0 is re-sorted by its own rule (predictability_diagnostic.common.chrono_sort, ties broken by match id, so
        the result does not depend on where the rows were added) and `order` renumbered; the player rows follow;
      * the timeline gets the package's rows for the matches added.
    A record goes to T/data/studies/current_best_model/accepted_additions_applied.json.
--pin-timing [--tree T]: after a timeline rebuild (a prediction run's timing.py), the added matches' rows set back to the
    package's, the windows training used.
--check-against <candidate folder>: on the frozen reference's tables, the merge must give the candidate's own Stage 0
    and timeline (every row, every column), so a build on the candidate is a build of the template's recipe.
--register <name>: list a written package in accepted.json (the adoption; its decision record says so).

Feeds (since 13 Oct 2026, docs/studies/data_gaps_2026/; the owner: "Make sure our pipeline is set up to automatically
integrate this so this doesnt happen again"): a feed is a package refreshed from the newest downloads, kept as dated
snapshots ACCEPTED/<feed>/<snapshot>/ (each written once, as a package is) and named in accepted.json's "feeds"
({feed: snapshot}). Every listed package is merged first, then each feed's current snapshot. A feed that covers a
package supersedes it: --retire moves the package to accepted.json's "retired", refused unless every match the package
adds is in the feed's current snapshot.
    --package <candidate> --name <feed>/<snapshot> --decision <record>   writes a snapshot (data_gaps_2026/feed.py)
    --set-feed <feed>/<snapshot>                                          points accepted.json at it
    --retire <name> --reason <text>
The merge also skips (since 13 Oct 2026) an added match when the table holds one of the same tour, round and pair, by
player ids or by both players' name keys, with tournament dates at most 3 days apart: a feed's row of a match another
feed has published since under its own tournament id.
Run: ./python.sh src/eda/current_best_model/additions.py --package <candidate> --name <name> --decision <record>
     ./python.sh src/eda/current_best_model/additions.py --register <name>
     ./python.sh src/eda/current_best_model/additions.py --check-against <candidate> [--only <name>[,<name>]]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ACCEPTED = Path("C:/Users/zerom/Documents/Tennis-predictions/data/studies/current_best_model/accepted_additions")
PD = Path("data") / "studies" / "predictability_diagnostic"
MT = Path("data") / "studies" / "match_timing"
RECORD = Path("data") / "studies" / "current_best_model" / "accepted_additions_applied.json"
BOX_MATCH = ["has_box", "box_status", "sv_gms_incl_tb"]


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def log(msg: str) -> None:
    print(f"[additions] {msg}", flush=True)


def index(accepted: Path = ACCEPTED) -> dict:
    idx = Path(accepted) / "accepted.json"
    cur = json.loads(idx.read_text(encoding="utf-8")) if idx.exists() else {}
    cur.setdefault("packages", [])
    return cur


def write_index(cur: dict, accepted: Path = ACCEPTED) -> None:
    idx = Path(accepted) / "accepted.json"
    part = idx.with_name(idx.name + ".part")
    part.write_text(json.dumps(cur, indent=1), encoding="utf-8")
    part.replace(idx)


def listed(accepted: Path = ACCEPTED) -> list[Path]:
    """The accepted packages, then each feed's current snapshot, each hash-checked against its manifest."""
    idx = Path(accepted) / "accepted.json"
    if not idx.exists():
        return []
    cur = index(accepted)
    names = list(cur["packages"]) + [f"{feed}/{snap}" for feed, snap in sorted(cur.get("feeds", {}).items())]
    out = []
    for name in names:
        p = Path(accepted) / name
        man = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
        for f, h in man["files"].items():
            if sha256(p / f) != h:
                raise SystemExit(f"{p / f}: its sha256 differs from the package's manifest")
        out.append(p)
    return out


def accepted_ids(accepted: Path = ACCEPTED) -> tuple[set, set]:
    """(the added matches' ids, the completed matches' ids) of every accepted package (history.py's 'accepted')."""
    added, completed = set(), set()
    for p in listed(accepted):
        added |= set(pd.read_parquet(p / "matches.parquet", columns=["match_id"])["match_id"].astype(str))
        c = pd.read_parquet(p / "completions.parquet", columns=["match_id"])
        completed |= set(c["match_id"].astype(str))
    return added, completed


# ------------------------------------------------------------------------------------------------
# A package from a candidate

def package(candidate: Path, name: str, decision: str, accepted: Path = ACCEPTED) -> Path:
    """The candidate's additions and completions against the frozen reference's Stage 0, as a package (refuses one that
    exists). The candidate must be READY (role F's checks)."""
    from src.eda.lower_level_evidence import candidate_stage0 as F
    candidate = Path(candidate)
    if not (candidate / "READY.txt").exists():
        raise SystemExit(f"{candidate}: not READY")
    out = Path(accepted) / name
    if out.exists():
        raise SystemExit(f"{out} exists: a package is written once")
    m_ref, mp_ref = F.load_reference()
    m = pd.read_parquet(candidate / "stage0_matches.parquet")
    mp = pd.read_parquet(candidate / "stage0_match_players.parquet")
    t = pd.read_parquet(candidate / "timing.parquet")
    ref_ids = set(m_ref["match_id"].astype(str))
    new_ids = set(m.loc[~m["match_id"].astype(str).isin(ref_ids), "match_id"].astype(str))
    lay = pd.read_parquet(candidate / "box_layers.parquet") if (candidate / "box_layers.parquet").exists() else None
    comp_ids = set(lay.loc[lay["applied"].astype(bool) & lay["match_id"].astype(str).isin(ref_ids), "match_id"]
                   .astype(str)) if lay is not None and len(lay) else set()
    out.mkdir(parents=True)
    am = m[m["match_id"].astype(str).isin(new_ids)].drop(columns=["order"])
    am.to_parquet(out / "matches.parquet", index=False)
    mp[mp["match_id"].astype(str).isin(new_ids)].to_parquet(out / "match_players.parquet", index=False)
    t[t["match_id"].astype(str).isin(new_ids)].to_parquet(out / "timing.parquet", index=False)
    pc = [c for c in mp.columns if c not in ("match_id", "player_id", "opponent_id", "side", "won")]
    mbox = m.loc[m["match_id"].astype(str).isin(comp_ids), ["match_id"] + BOX_MATCH].rename(
        columns={c: f"match_{c}" for c in BOX_MATCH})
    comp = mp[mp["match_id"].astype(str).isin(comp_ids)].merge(mbox, on="match_id", how="left")
    comp[["match_id", "player_id", "side"] + [f"match_{c}" for c in BOX_MATCH] + pc].to_parquet(
        out / "completions.parquet", index=False)
    files = {f: sha256(out / f) for f in ("matches.parquet", "match_players.parquet", "timing.parquet",
                                          "completions.parquet")}
    man = {"name": name, "decision": decision, "candidate": str(candidate),
           "candidate_manifest_sha256": sha256(candidate / "manifest.json"),
           "added_matches": int(len(am)), "completed_matches": int(len(comp_ids)),
           "by_tour_level_year": am.groupby(["tour", "map_level", "year"]).size().rename("matches").reset_index()
           .to_dict("records"), "files": files,
           "written_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    (out / "manifest.json").write_text(json.dumps(man, indent=1, default=str), encoding="utf-8")
    log(f"package {name}: {len(am):,} added matches, {len(comp_ids)} completions")
    return out


def register(name: str, accepted: Path = ACCEPTED) -> None:
    cur = index(accepted)
    if name not in cur["packages"]:
        cur["packages"].append(name)
    write_index(cur, accepted)


def set_feed(target: str, accepted: Path = ACCEPTED) -> dict:
    """Point accepted.json's feed at a written snapshot ('<feed>/<snapshot>'); the snapshot is hash-checked first. The
    previous snapshot stays on disk (its folder is the record of what earlier builds merged)."""
    feed, _, snap = target.partition("/")
    if not (feed and snap):
        raise SystemExit("--set-feed takes <feed>/<snapshot>")
    p = Path(accepted) / feed / snap
    if not (p / "manifest.json").exists():
        raise SystemExit(f"{p}: no snapshot")
    man = json.loads((p / "manifest.json").read_text(encoding="utf-8"))
    for f, h in man["files"].items():
        if sha256(p / f) != h:
            raise SystemExit(f"{p / f}: its sha256 differs from the snapshot's manifest")
    cur = index(accepted)
    before = cur.setdefault("feeds", {}).get(feed)
    cur["feeds"][feed] = snap
    cur.setdefault("feed_history", []).append({"feed": feed, "snapshot": snap, "previous": before,
                                                "at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")})
    write_index(cur, accepted)
    return {"feed": feed, "snapshot": snap, "previous": before}


def retire(name: str, reason: str, accepted: Path = ACCEPTED) -> dict:
    """Move a package from accepted.json's packages to "retired", once a feed's current snapshot holds every match it
    adds (by id, or by tour, tournament, round and pair) and every match it completes."""
    cur = index(accepted)
    if name not in cur["packages"]:
        raise SystemExit(f"{name}: not a listed package")
    feeds = [Path(accepted) / f / s for f, s in cur.get("feeds", {}).items()]
    if not feeds:
        raise SystemExit("no feed is listed: nothing supersedes the package")
    pm = pd.read_parquet(Path(accepted) / name / "matches.parquet")
    fm = pd.concat([pd.read_parquet(p / "matches.parquet") for p in feeds], ignore_index=True)
    held = pm["match_id"].astype(str).isin(set(fm["match_id"].astype(str))) | key(pm).isin(set(key(fm)))
    if not held.all():
        # the same meeting under other ids, as the merge skips it (week_duplicates: tour, round and pair by ids or by
        # both name keys, tournament dates at most 3 days apart): a player new to Stage 0 takes a different minted id
        # from each source (13 Oct 2026: Misolic d. Esculcas, Braga Q1, 'atp:sofa:1292322' in the package and
        # 'atp:tl:132674' in the feed)
        pmp = pd.read_parquet(Path(accepted) / name / "match_players.parquet")
        fmp = pd.concat([pd.read_parquet(p / "match_players.parquet") for p in feeds], ignore_index=True)
        rest = pm[~held.to_numpy()]
        hit = week_duplicates(fm, fmp, rest.reset_index(drop=True),
                              pmp[pmp["match_id"].isin(set(rest["match_id"]))])
        held.loc[rest.index[hit]] = True
    pc = set(pd.read_parquet(Path(accepted) / name / "completions.parquet", columns=["match_id"])["match_id"].astype(str))
    fc = set()
    for p in feeds:
        fc |= set(pd.read_parquet(p / "completions.parquet", columns=["match_id"])["match_id"].astype(str))
    if not held.all() or not pc <= fc:
        raise SystemExit(f"{name}: the feeds hold {int(held.sum())} of its {len(pm)} added matches and "
                         f"{len(pc & fc)} of its {len(pc)} completions: not retired")
    cur["packages"] = [n for n in cur["packages"] if n != name]
    cur.setdefault("retired", {})[name] = {"reason": reason, "superseded_by": [f"{p.parent.name}/{p.name}" for p in feeds],
                                           "at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    write_index(cur, accepted)
    return cur["retired"][name]


# ------------------------------------------------------------------------------------------------
# The merge

def key(f: pd.DataFrame) -> pd.Series:
    """A meeting: tour, tournament, round and the two players (in either order)."""
    a = f["player_a_id"].astype(str).to_numpy(dtype=object)
    b = f["player_b_id"].astype(str).to_numpy(dtype=object)
    lo, hi = np.where(a <= b, a, b), np.where(a <= b, b, a)
    return pd.Series([f"{t}|{i}|{r}|{x}|{y}" for t, i, r, x, y in zip(
        f["tour"].astype(str), f["tournament_id"].astype(str), f["round"].astype(str), lo, hi)], index=f.index,
        dtype=object)


def name_key(value) -> str:
    """candidate_stage0.name_key (repair_data.name_key): accents folded, lower case, letters and digits only."""
    import re
    import unicodedata
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def pairs(f: pd.DataFrame, fp: pd.DataFrame) -> pd.DataFrame:
    """Per match: tour, round, date, and the pair as sorted player ids and as sorted name keys (none without names)."""
    out = pd.DataFrame({"i": np.arange(len(f)), "tour": f["tour"].astype(str).to_numpy(),
                        "round": f["round"].astype(str).to_numpy(),
                        "d": pd.to_datetime(f["tournament_date"]).to_numpy()})
    a, b = f["player_a_id"].astype(str).to_numpy(dtype=object), f["player_b_id"].astype(str).to_numpy(dtype=object)
    out["ids"] = [f"{x}|{y}" if x <= y else f"{y}|{x}" for x, y in zip(a, b)]
    out["names"] = None
    if "player_name" in fp.columns and len(fp):
        cache: dict = {}
        k = fp["player_name"].map(lambda v: cache.setdefault(v, name_key(v)) if isinstance(v, str) else "")
        nk = pd.DataFrame({"match_id": fp["match_id"].astype(str).to_numpy(), "side": fp["side"].astype(str).to_numpy(),
                           "k": k.to_numpy()}).pivot_table(index="match_id", columns="side", values="k", aggfunc="first")
        ka = f["match_id"].astype(str).map(nk["A"]) if "A" in nk else pd.Series("", index=f.index)
        kb = f["match_id"].astype(str).map(nk["B"]) if "B" in nk else pd.Series("", index=f.index)
        out["names"] = [f"{x}|{y}" if x <= y else f"{y}|{x}" if (x and y) else None
                        for x, y in zip(ka.fillna("").astype(str), kb.fillna("").astype(str))]
    return out


def week_duplicates(m: pd.DataFrame, mp: pd.DataFrame, am: pd.DataFrame, amp: pd.DataFrame) -> np.ndarray:
    """For each added match, whether the table holds one of the same tour, round and pair (ids, or both name keys) whose
    tournament date is at most 3 days away: the same meeting under another feed's tournament id."""
    if not len(am):
        return np.zeros(0, bool)
    lo = pd.to_datetime(am["tournament_date"]).min() - pd.Timedelta(days=7)
    hi = pd.to_datetime(am["tournament_date"]).max() + pd.Timedelta(days=7)
    d = pd.to_datetime(m["tournament_date"])
    near = m[(d >= lo) & (d <= hi)]
    if not len(near):
        return np.zeros(len(am), bool)
    A = pairs(am, amp)
    N = pairs(near, mp[mp["match_id"].isin(set(near["match_id"]))])
    hit = np.zeros(len(am), bool)
    for col in ("ids", "names"):
        j = A.dropna(subset=[col]).merge(N.dropna(subset=[col]), on=["tour", "round", col], suffixes=("", "_n"))
        j = j[(j["d"] - j["d_n"]).abs() <= pd.Timedelta(days=3)]
        hit[j["i"].to_numpy()] = True
    return hit


def merge(m: pd.DataFrame, mp: pd.DataFrame, t: pd.DataFrame, packages: list[Path]) -> tuple:
    """(matches, players, timing, record): the packages merged into the given Stage 0 and timeline (module docstring)."""
    from src.eda.predictability_diagnostic import common as C
    rec = {"packages": []}
    m, mp, t = m.copy(), mp.copy(), t.copy()
    for p in packages:
        am = pd.read_parquet(p / "matches.parquet")
        amp = pd.read_parquet(p / "match_players.parquet")
        at = pd.read_parquet(p / "timing.parquet")
        comp = pd.read_parquet(p / "completions.parquet")
        have = set(m["match_id"].astype(str))
        same_id = am["match_id"].astype(str).isin(have)
        same_meeting = key(am).isin(set(key(m))) & ~same_id
        same_week = pd.Series(week_duplicates(m, mp, am, amp), index=am.index) & ~same_id & ~same_meeting
        add = am[~same_id & ~same_meeting & ~same_week]
        ids = set(add["match_id"].astype(str))
        m = pd.concat([m, add.assign(order=-1)], ignore_index=True)
        mp = pd.concat([mp, amp[amp["match_id"].astype(str).isin(ids)]], ignore_index=True)
        t = pd.concat([t, at[at["match_id"].astype(str).isin(ids)]], ignore_index=True)
        # completions: only where the match is still without a box score, with the same players
        applied = 0
        for mid, g in comp.groupby("match_id"):
            sel = m["match_id"].astype(str) == str(mid)
            if not sel.any() or bool(m.loc[sel, "has_box"].iloc[0]):
                continue
            rows = mp["match_id"].astype(str) == str(mid)
            if set(mp.loc[rows, "player_id"].astype(str)) != set(g["player_id"].astype(str)):
                continue
            for c in BOX_MATCH:
                m.loc[sel, c] = g[f"match_{c}"].iloc[0]
            gi = g.set_index("player_id")
            for c in [c for c in g.columns if c not in ("match_id", "player_id", "side")
                      and not c.startswith("match_")]:
                mp.loc[rows, c] = mp.loc[rows, "player_id"].map(gi[c]).astype(mp[c].dtype).to_numpy()
            applied += 1
        rec["packages"].append({"package": str(p), "added": int(len(add)), "skipped_same_id": int(same_id.sum()),
                                "skipped_same_meeting": int(same_meeting.sum()),
                                "skipped_same_pair_round_week": int(same_week.sum()),
                                "completions_applied": applied, "completions_listed": int(comp["match_id"].nunique())})
    m = C.chrono_sort(m).reset_index(drop=True)
    m["order"] = np.arange(len(m), dtype="int64")
    mp = mp.merge(m[["match_id", "order"]], on="match_id", how="left", validate="many_to_one")
    if mp["order"].isna().any():
        raise SystemExit("player rows without a match")
    mp = mp.sort_values(["order", "side"], kind="mergesort").drop(columns="order").reset_index(drop=True)
    if m["match_id"].duplicated().any() or mp.duplicated(["match_id", "side"]).any() or t["match_id"].duplicated().any():
        raise SystemExit("the merge made duplicate match ids, sides or timeline rows")
    return m, mp, t, rec


def apply(tree: Path = ROOT, accepted: Path = ACCEPTED) -> dict:
    tree = Path(tree)
    packages = listed(accepted)
    paths = {"m": tree / PD / "stage0_matches.parquet", "mp": tree / PD / "stage0_match_players.parquet",
             "t": tree / MT / "timing.parquet"}
    before = {k: sha256(p) for k, p in paths.items()}
    if not packages:
        rec = {"packages": [], "note": "no accepted package"}
    else:
        m, mp, t, rec = merge(pd.read_parquet(paths["m"]), pd.read_parquet(paths["mp"]), pd.read_parquet(paths["t"]),
                              packages)
        m.to_parquet(paths["m"], index=False)
        mp.to_parquet(paths["mp"], index=False)
        t.to_parquet(paths["t"], index=False, compression="zstd")
    rec.update({"tree": str(tree), "before_sha256": before, "after_sha256": {k: sha256(p) for k, p in paths.items()},
                "applied_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")})
    (tree / RECORD).parent.mkdir(parents=True, exist_ok=True)
    (tree / RECORD).write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    log(f"applied {len(packages)} package(s) to {tree}: {rec['packages']}")
    return rec


def pin_timing(tree: Path = ROOT, accepted: Path = ACCEPTED) -> dict:
    """The added matches' timeline rows set back to the packages' (after a prediction run rebuilt the timeline)."""
    tree = Path(tree)
    path = tree / MT / "timing.parquet"
    t = pd.read_parquet(path)
    n = 0
    for p in listed(accepted):
        at = pd.read_parquet(p / "timing.parquet")
        at = at[at["match_id"].astype(str).isin(set(t["match_id"].astype(str)))]
        idx = t.reset_index().set_index(t["match_id"].astype(str))["index"]
        pos = idx.reindex(at["match_id"].astype(str)).to_numpy()
        for c in at.columns:
            if c in t.columns:
                t.loc[pos, c] = at[c].to_numpy()
        n += len(at)
    t.to_parquet(path, index=False, compression="zstd")
    return {"rows_pinned": n}


def check_against(candidate: Path, accepted: Path = ACCEPTED, only: list[str] | None = None) -> dict:
    """On the frozen reference's tables, the merge must give the candidate's own Stage 0 and timeline. only: merge just
    these packages or snapshots (names under ACCEPTED, e.g. a feed's '<feed>/<snapshot>'), listed or not."""
    from src.eda.lower_level_evidence import candidate_stage0 as F
    from src.eda.lower_level_evidence import common as LC
    m_ref, mp_ref = F.load_reference()
    t_ref = pd.read_parquet(LC.TIMING)
    packages = [Path(accepted) / n for n in only] if only else listed(accepted)
    m, mp, t, rec = merge(m_ref, mp_ref, t_ref, packages)
    cm = pd.read_parquet(Path(candidate) / "stage0_matches.parquet")
    cmp_ = pd.read_parquet(Path(candidate) / "stage0_match_players.parquet")
    ct = pd.read_parquet(Path(candidate) / "timing.parquet")
    out = {"merge": rec,
           "matches_equal": bool(m[cm.columns].reset_index(drop=True).equals(cm.reset_index(drop=True))),
           "players_equal": bool(mp[cmp_.columns].reset_index(drop=True).equals(cmp_.reset_index(drop=True))),
           "timing_equal_by_match": bool(t.sort_values("match_id")[ct.columns].reset_index(drop=True)
                                         .equals(ct.sort_values("match_id").reset_index(drop=True)))}
    out["pass"] = all(v for k, v in out.items() if k.endswith("equal") or k.endswith("_by_match"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--apply", action="store_true")
    g.add_argument("--pin-timing", action="store_true")
    g.add_argument("--package", metavar="CANDIDATE")
    g.add_argument("--check-against", metavar="CANDIDATE")
    g.add_argument("--register", metavar="NAME", help="list a written package in accepted.json: the owner's adoption, "
                                                      "recorded in its decision")
    g.add_argument("--set-feed", metavar="FEED/SNAPSHOT", help="point accepted.json's feed at a written snapshot")
    g.add_argument("--retire", metavar="NAME", help="move a package a feed supersedes to accepted.json's retired")
    ap.add_argument("--tree", default=str(ROOT))
    ap.add_argument("--name", help="--package: the package's name, or <feed>/<snapshot> for a feed's snapshot")
    ap.add_argument("--decision", help="--package: the decision record that accepted it")
    ap.add_argument("--reason", help="--retire: why (recorded)")
    ap.add_argument("--only", help="--check-against: merge only these packages or snapshots (comma-separated names)")
    ap.add_argument("--accepted", default=str(ACCEPTED))
    a = ap.parse_args()
    acc = Path(a.accepted)
    if a.set_feed:
        print(json.dumps(set_feed(a.set_feed, acc)))
        listed(acc)
        return 0
    if a.retire:
        if not a.reason:
            raise SystemExit("--retire needs --reason")
        print(json.dumps(retire(a.retire, a.reason, acc), default=str))
        return 0
    if a.package:
        if not (a.name and a.decision):
            raise SystemExit("--package needs --name and --decision")
        print(package(Path(a.package), a.name, a.decision, acc))
        return 0
    if a.register:
        if not (acc / a.register / "manifest.json").exists():
            raise SystemExit(f"{acc / a.register}: no package")
        register(a.register, acc)
        listed(acc)                                       # every listed package hash-checked
        print(f"registered {a.register} in {acc / 'accepted.json'}")
        return 0
    if a.check_against:
        res = check_against(Path(a.check_against), acc, [x for x in (a.only or "").split(",") if x] or None)
        print(json.dumps(res, indent=1, default=str))
        return 0 if res["pass"] else 1
    if a.pin_timing:
        print(json.dumps(pin_timing(Path(a.tree), acc)))
        return 0
    print(json.dumps(apply(Path(a.tree), acc), indent=1, default=str)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
