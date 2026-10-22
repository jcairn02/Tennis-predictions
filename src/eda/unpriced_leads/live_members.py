"""Live values of the registered members (the unpriced-leads single check, step 3; rules:
docs/studies/unpriced_leads/check_now_rules.md).

The registered values were built for the template frame's matches by rebuild_pool.py (variant V1) and build_rhythm.py.
Here the same builder functions, imported unchanged and called as those scripts call them, compute the members for any
set of matches, live rows included, on the tables of the tree this file sits in. Run it from a work tree's copy, as the
daily engine runs its steps, and every path resolves to that tree's Stage 0, clock, Stage 1 odds, match-timing links
and TennisLive dump.
    pool       G2 post-Slam letdown (f19_motiv), G3 venue pace x ace offence (f09_venue, the leak-proof clock), G4 seeded
               (Stage 0's seed), G4 fame (f14_anchor), G5 past fatigue (f28_state on f20_fatigue's history). Run on
               rebuild_pool's own long table, panel and Patched sources, with the run's surface IOS (below)
    rhythm     G5 doubles at other events in days d-7..d-1 (TennisLive; every level, as the registered run's ITF rule
               decided: candidates/rhythm/build.json) and G5 rest under 20 hours (start times from the timing links,
               Flashscore's end times), on build_rhythm's own long table
    not built  G1's three luck members and G4's two lower-level members. While their data supply stays collapsed (box
               scores, lower levels; the check of 13 Oct 2026), the live gate switches them off for every live match.
               They are returned missing; turning them on needs this module extended and the parity proof re-run.
Each value is A - B for Stage 0's side A, as in the registered files.

The surface IOS (G3, 16 Oct 2026). Until then this module read the registered build's extract (pinned to the 10 Oct
instance's table), which holds no match played after its tables, so G3 was missing for every live match and the venue
pace lacked each event's newest days. Now (ios_table): the instance's own table (--ios-table, its build tree's) with
the ace ratings the run's states step solved on today's tables laid over it (--ace-rows: the live rows themselves and
the history since the checkpoint). The live match's ace gap is then the model's own input in_iosO_ace (--frame checks
it), as in the registered build, where it was the frame's input bit for bit. live_members.json records the table and
counts the venue history rows the pace should read but cannot (no rating in either source).

Run (inside a tree): <python> <tree>/src/eda/unpriced_leads/live_members.py --ids <file of match ids> --out <parquet>
                     --ios-table <instance build tree's surface_features.parquet> --ace-rows <run>/ios_ace_recent.parquet
                     --ios-out <scratch parquet> [--frame <run>/live_frame.parquet]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.unpriced_leads import build_rhythm as BR  # noqa: E402
from src.eda.unpriced_leads import rebuild_pool as RP  # noqa: E402
from src.eda.unpriced_leads import screen as H  # noqa: E402

POOL = {"rb__fi__B-MOTIV__post_slam": "post_slam", "rb__fi__B-VENUE__f09_venue_pace_x_ace": "venue_x_ace",
        "rb__pp__seeded_a-b": "seeded", "rb__fp__f14_anchor__fame_a-b": "fame",
        "rb__fp__f28_state__bdst_pastfat_a-b": "pastfat"}
RHYTHM = ["rb01_d7_else", "rb03_lt20"]
NOT_BUILT = ["PS03_net", "PS06_close", "PS04_flat", "rb__el__low_share_diff", "rb__fp__f12_salience__hasL_a-b"]
RHYTHM_PRIMARY = None          # every doubles level: the registered run's ITF rule (build.json, "all levels")
VENUE = "rb__fi__B-VENUE__f09_venue_pace_x_ace"
ACE = ["srf_O_eff_ace", "srf_D_eff_ace"]
ACE_COLS = [f"{c}_{s}" for c in ACE for s in "ab"]
GAP_TOL = 1e-12                # the panel's ace gap against the run's own input: the same numbers


def ios_table(instance_table: Path, ace_rows: Path | None, out: Path) -> dict:
    """The run's surface IOS for the pool members: the instance's own table (every match its build reached), with the
    ace ratings the run's states step solved on today's tables laid over it (dp_state.write_ace_rows: the live rows
    and the history since the checkpoint); today's ratings win where both hold a match. Only the ace columns are laid
    over: the serve-point columns feed f09's indoor deviations, which no registered member uses. Writes `out`."""
    t = pd.read_parquet(instance_table, columns=RP.INSTANCE["ios"]["cols"])
    t["match_id"] = t["match_id"].astype(str)
    t = t.drop_duplicates("match_id").set_index("match_id")
    rec = {"instance_table": str(instance_table), "instance_sha256": RP.sha256(Path(instance_table)),
           "instance_matches": int(len(t)), "ace_rows": None if ace_rows is None else str(ace_rows)}
    if ace_rows is not None:
        r = pd.read_parquet(ace_rows)
        r["match_id"] = r["match_id"].astype(str)
        if r.duplicated(["match_id", "side"]).any() or not set(r["side"]) <= {"A", "B"}:
            raise RuntimeError(f"{ace_rows}: one row per match and side A or B expected")
        new = pd.DataFrame(index=pd.Index(r["match_id"].unique(), name="match_id"))
        for c in ACE:
            for side, tag in (("A", "a"), ("B", "b")):
                new[f"{c}_{tag}"] = r[r["side"] == side].set_index("match_id")[c].reindex(new.index).to_numpy(float)
        over, add = new.index.intersection(t.index), new.index.difference(t.index)
        cur, nv = t.loc[over, ACE_COLS].to_numpy(float), new.loc[over, ACE_COLS].to_numpy(float)
        upd = np.isfinite(nv)                          # a side the run has no rating for keeps the instance's
        moved = np.abs(np.where(upd & np.isfinite(cur), nv - cur, np.nan))
        if len(over):
            t.loc[over, ACE_COLS] = np.where(upd, nv, cur)
        t = pd.concat([t, new.loc[add, ACE_COLS]])
        rec.update({"ace_rows_sha256": RP.sha256(Path(ace_rows)), "run_matches": int(len(new)),
                    "replaced": int(len(over)), "added": int(len(add)),
                    "replaced_max_abs_change": float(np.nanmax(moved)) if np.isfinite(moved).any() else 0.0})
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    t.rename_axis("match_id").reset_index().to_parquet(out, index=False)
    rec.update({"table": str(out), "matches": int(len(t))})
    return rec


def tree_tables(stage0_dir: Path | None = None, ios: Path | None = None) -> RP.Tables:
    """The tree's tables; stage0_dir: another Stage 0 folder (the parity proof's restored Stage 0), which the rhythm
    builders then read too (screen's module paths are pointed at it); ios: the run's surface IOS (ios_table's)."""
    s = ROOT / "data" / "studies"
    d = Path(stage0_dir) if stage0_dir else s / RP.PD
    if stage0_dir:
        H.STAGE0_M, H.STAGE0_P = d / "stage0_matches.parquet", d / "stage0_match_players.parquet"
    return RP.Tables("live", f"the tables of {ROOT}", str(d / "stage0_matches.parquet"),
                     str(d / "stage0_match_players.parquet"), str(s / "match_timing" / "timing.parquet"),
                     str(s / RP.PD / "stage1_odds.parquet"), str(ios) if ios else "instance", "instance", "current")


def keys_for(T: RP.Tables, ids) -> pd.DataFrame:
    """The population's keys from the tree's Stage 0 (never a result): match_id, tour, season (the tournament date's
    year, from 20 Dec the next, f20's rule), tournament_date, debut_season False, and the sides."""
    m = pd.read_parquet(T.stage0_m, columns=["match_id", "tour", "tournament_date", "player_a_id", "player_b_id"])
    m["match_id"] = m["match_id"].astype(str)
    want = pd.Index(pd.Series(list(ids), dtype=str).unique())
    m = m.drop_duplicates("match_id").set_index("match_id")
    missing = want.difference(m.index)
    if len(missing):
        raise RuntimeError(f"{len(missing)} requested matches are not in the tree's Stage 0 (first: {list(missing[:3])})")
    m = m.loc[want].rename_axis("match_id").reset_index()
    d = pd.to_datetime(m["tournament_date"])
    m["season"] = d.dt.year + ((d.dt.month == 12) & (d.dt.day >= 20)).astype(int)
    m["debut_season"] = False
    return m


def venue_coverage(P: pd.DataFrame, L: pd.DataFrame) -> list[dict]:
    """Per match, the venue history rows its pace should read (released by its earliest start, completed or retired,
    20+ serve points with an ace count: f09.serve_rows' own conditions) and how many of them have no surface-IOS ace
    rating (the server's offence or the returner's defence), so add nothing. Run inside Patched (the run's table)."""
    S = RP.S1
    Lc = S.cut_history(L, P)
    vk = RP.F09.venue_key(Lc["tour"], Lc["tournament_name"], Lc["surface"])
    pk = RP.F09.venue_key(P["tour"], P["tournament_name"], P["surface"])
    sel = np.isin(vk, pk)
    Lv, vk = Lc[sel].reset_index(drop=True), vk[sel]
    Hh = S.history_ios(Lv, ACE)
    a, n = S.history_stat(Lv, "ace")
    good = Lv["status"].astype(str).isin(["completed", "retired"]).to_numpy() & (n >= 20) & np.isfinite(a)
    rated = np.isfinite(Hh[("own", "srf_O_eff_ace")]) & np.isfinite(Hh[("opp", "srf_D_eff_ace")])
    rel, es = S.num(Lv, "lf") + 1.0, S.num(P, "es")
    out = []
    for i in range(len(P)):
        m = good & (vk == pk[i]) & (rel <= es[i])
        out.append({"match_id": str(P["match_id"].iloc[i]), "venue": str(pk[i]), "rows": int(m.sum()),
                    "without_rating": int((m & ~rated).sum())})
    return out


def pool_members(T: RP.Tables, keys: pd.DataFrame) -> tuple[dict[str, np.ndarray], dict]:
    """The five pool members at the keys' matches, exactly as rebuild_pool.build computes them, and what G3 read: the
    panel's ace gap (A - B, from T's surface IOS) and the venue history it could not rate (venue_coverage)."""
    k = keys[RP.KEYS].copy()
    with RP.Patched(T):
        L, _ = RP.long_table(T)
        P = RP.panel(T, k)
        RP.clear_caches()
        mot = RP.F19.prepare_motiv(P, L)
        bm = RP.F19.combine_bmotiv(P.assign(**mot))
        post = np.asarray(bm["tabpfn"]["post_slam"][0], float)
        ven = RP.F09.prepare_venue(P, L)
        x72 = np.asarray(RP.F09.x_i072(P.assign(**ven)), float)
        cover = venue_coverage(P, L)
        seeded = P["seed_a"].notna().astype(float).to_numpy() - P["seed_b"].notna().astype(float).to_numpy()
        fame = RP.F14.prepare_fame(P, L)
        fame_d = np.asarray(fame["fame_a"], float) - np.asarray(fame["fame_b"], float)
        Hh = RP.F20.history(P, L)
        pfa, pfb = RP.F20.at_model(P, Hh, RP.F28.past_fat(Hh))
        RP.clear_caches()
    if (P["match_id"].astype(str).to_numpy() != keys["match_id"].astype(str).to_numpy()).any():
        raise RuntimeError("the panel's order differs from the keys'")
    seen = {"ace_gap": P["ios_srfO_ace_a"].to_numpy(float) - P["ios_srfO_ace_b"].to_numpy(float), "venue": cover}
    return {"rb__fi__B-MOTIV__post_slam": post, VENUE: x72,
            "rb__pp__seeded_a-b": seeded, "rb__fp__f14_anchor__fame_a-b": fame_d,
            "rb__fp__f28_state__bdst_pastfat_a-b": np.asarray(pfa, float) - np.asarray(pfb, float)}, seen


def rhythm_members(keys: pd.DataFrame) -> dict[str, np.ndarray]:
    """The two rhythm members at the keys' matches, exactly as build_rhythm's run_builders and assemble compute them."""
    reg = json.loads((BR.OUT / "build.json").read_text(encoding="utf-8"))
    kinds = reg.get("rb01_itf_shift", reg.get("facts", {}).get("rb01_itf_shift", {})).get("primary_kinds", "")
    if kinds and not kinds.startswith("all"):
        raise RuntimeError(f"the registered run's doubles levels are '{kinds}', not every level")
    L = BR.load_long()
    ids = set(keys["match_id"].astype(str))
    Q = BR.frame_queries(L, ids)
    if Q["obs"].isna().any():
        raise RuntimeError("a requested player-row has no clock day")
    s0m = pd.read_parquet(H.STAGE0_M, columns=["match_id", "tournament_id", "tournament_date", "player_a_id",
                                               "player_b_id", "surface"])
    s0m["match_id"] = s0m["match_id"].astype(str)
    s0m = s0m.merge(pd.read_parquet(H.TIMING, columns=["match_id", "obs"]).astype({"match_id": str}), on="match_id")
    id2s0, name2s0 = BR.tl_name_map()
    ev2tid, _ = BR.tl_event_map(id2s0, s0m)
    D, _ = BR.tl_doubles(name2s0, ev2tid)
    V = Q[["match_id", "player_id"]].copy()
    rest = BR.build_rest(BR.lsub(L, BR.BUILD_READS["rest"]))
    rest = rest[rest["match_id"].isin(ids)].drop_duplicates(["match_id", "player_id"])
    V = V.merge(rest, on=["match_id", "player_id"], how="left", validate="one_to_one")
    V = V.merge(BR.build_rb01(Q, D, RHYTHM_PRIMARY), on=["match_id", "player_id"], how="left", validate="one_to_one")
    out = {}
    for col in RHYTHM:
        a, b = H.at_frame(V, col, keys)
        out[col] = a - b
    return out


def live_values(ids, stage0_dir: Path | None = None, ios: Path | None = None) -> tuple[pd.DataFrame, dict]:
    """The members of the matches `ids`, and what G3 read (pool_members)."""
    T = tree_tables(stage0_dir, ios)
    keys = keys_for(T, ids)
    vals = {"match_id": keys["match_id"].astype(str).to_numpy()}
    pool, seen = pool_members(T, keys)
    vals.update(pool)
    vals.update(rhythm_members(keys))
    for c in NOT_BUILT:
        vals[c] = np.full(len(keys), np.nan)
    return pd.DataFrame(vals), seen


def frame_check(frame: Path, ids: np.ndarray, gap: np.ndarray) -> dict:
    """The panel's ace gap against the run's own input in_iosO_ace (the model's live input: the same ratings, so the
    same numbers). Refuses a match where they differ, or where the input exists and the gap does not."""
    f = pd.read_parquet(frame, columns=["match_id", "in_iosO_ace"]).astype({"match_id": str})
    want = f.drop_duplicates("match_id").set_index("match_id")["in_iosO_ace"].reindex(ids).to_numpy(float)
    bad = np.isfinite(want) & ~(np.abs(gap - want) <= GAP_TOL)
    if bad.any():
        raise RuntimeError(f"{int(bad.sum())} matches: the venue member's ace gap differs from the run's in_iosO_ace "
                           f"(first: {list(ids[bad][:3])}); the surface IOS read is not the run's")
    fin = np.isfinite(want) & np.isfinite(gap)
    return {"frame": str(frame), "matches": int(len(ids)), "equal": int(fin.sum()),
            "input_missing": int((~np.isfinite(want)).sum()),
            "max_abs_diff": float(np.abs(gap[fin] - want[fin]).max()) if fin.any() else 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True, help="a text file with one match id per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage0", default=None, help="another Stage 0 folder (the parity proof's restored Stage 0)")
    ap.add_argument("--ios-table", required=True,
                    help="the instance's own surface IOS table (its build tree's surface_ios/surface_features.parquet)")
    ap.add_argument("--ace-rows", default=None,
                    help="the run's ace ratings (dp_state.write_ace_rows), laid over the table; without them no live "
                         "match has a rating")
    ap.add_argument("--ios-out", required=True, help="where the run's surface IOS table is written (scratch)")
    ap.add_argument("--frame", default=None, help="the run's live_frame.parquet: the ace gap is checked against it")
    a = ap.parse_args()
    ids = [x.strip() for x in Path(a.ids).read_text(encoding="utf-8").splitlines() if x.strip()]
    rec = {"tree": str(ROOT)}
    rec["ios"] = ios_table(Path(a.ios_table), Path(a.ace_rows) if a.ace_rows else None, Path(a.ios_out))
    df, seen = live_values(ids, a.stage0, Path(a.ios_out))
    for c in ("a_won", "y", "won", "winner"):
        if c in df.columns:
            raise RuntimeError("a result column would be written")
    if a.frame:
        rec["frame_check"] = frame_check(Path(a.frame), df["match_id"].to_numpy(str), seen["ace_gap"])
    df.to_parquet(a.out, index=False)
    cover = seen["venue"]
    rec.update({"matches": int(len(df)),
                "present": {c: int(np.isfinite(df[c]).sum()) for c in df.columns if c != "match_id"},
                "venue_rows": int(sum(c["rows"] for c in cover)),
                "venue_rows_without_rating": int(sum(c["without_rating"] for c in cover)), "venue_by_match": cover})
    Path(a.out).with_suffix(".json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in rec.items() if k != "venue_by_match"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
