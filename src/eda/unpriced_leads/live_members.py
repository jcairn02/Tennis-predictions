"""Live values of the registered members (the unpriced-leads single check, step 3; rules:
docs/studies/unpriced_leads/check_now_rules.md).

The registered values were built for the template frame's matches by rebuild_pool.py (variant V1) and build_rhythm.py.
Here the same builder functions, imported unchanged and called as those scripts call them, compute the members for any
set of matches, live rows included, on the tables of the tree this file sits in. Run it from a work tree's copy, as the
daily engine runs its steps, and every path resolves to that tree's Stage 0, clock, Stage 1 odds, match-timing links,
TennisLive dump and the instance's frozen extracts.
    pool       G2 post-Slam letdown (f19_motiv), G3 venue pace x ace offence (f09_venue, the leak-proof clock), G4 seeded
               (Stage 0's seed), G4 fame (f14_anchor), G5 past fatigue (f28_state on f20_fatigue's history). Run on
               rebuild_pool's own long table, panel and Patched sources, with the instance's surface-IOS extract
    rhythm     G5 doubles at other events in days d-7..d-1 (TennisLive; every level, as the registered run's ITF rule
               decided: candidates/rhythm/build.json) and G5 rest under 20 hours (start times from the timing links,
               Flashscore's end times), on build_rhythm's own long table
    not built  G1's three luck members and G4's two lower-level members. While their data supply stays collapsed (box
               scores, lower levels; the check of 13 Oct 2026), the live gate switches them off for every live match.
               They are returned missing; turning them on needs this module extended and the parity proof re-run.
Each value is A - B for Stage 0's side A, as in the registered files.

Run (inside a tree): <python> <tree>/src/eda/unpriced_leads/live_members.py --ids <file of match ids> --out <parquet>
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


def tree_tables(stage0_dir: Path | None = None) -> RP.Tables:
    """The tree's tables; stage0_dir: another Stage 0 folder (the parity proof's restored Stage 0), which the rhythm
    builders then read too (screen's module paths are pointed at it)."""
    s = ROOT / "data" / "studies"
    d = Path(stage0_dir) if stage0_dir else s / RP.PD
    if stage0_dir:
        H.STAGE0_M, H.STAGE0_P = d / "stage0_matches.parquet", d / "stage0_match_players.parquet"
    return RP.Tables("live", f"the tables of {ROOT}", str(d / "stage0_matches.parquet"),
                     str(d / "stage0_match_players.parquet"), str(s / "match_timing" / "timing.parquet"),
                     str(s / RP.PD / "stage1_odds.parquet"), "instance", "instance", "current")


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


def pool_members(T: RP.Tables, keys: pd.DataFrame) -> dict[str, np.ndarray]:
    """The five pool members at the keys' matches, exactly as rebuild_pool.build computes them."""
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
        seeded = P["seed_a"].notna().astype(float).to_numpy() - P["seed_b"].notna().astype(float).to_numpy()
        fame = RP.F14.prepare_fame(P, L)
        fame_d = np.asarray(fame["fame_a"], float) - np.asarray(fame["fame_b"], float)
        Hh = RP.F20.history(P, L)
        pfa, pfb = RP.F20.at_model(P, Hh, RP.F28.past_fat(Hh))
        RP.clear_caches()
    if (P["match_id"].astype(str).to_numpy() != keys["match_id"].astype(str).to_numpy()).any():
        raise RuntimeError("the panel's order differs from the keys'")
    return {"rb__fi__B-MOTIV__post_slam": post, "rb__fi__B-VENUE__f09_venue_pace_x_ace": x72,
            "rb__pp__seeded_a-b": seeded, "rb__fp__f14_anchor__fame_a-b": fame_d,
            "rb__fp__f28_state__bdst_pastfat_a-b": np.asarray(pfa, float) - np.asarray(pfb, float)}


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


def live_values(ids, stage0_dir: Path | None = None) -> pd.DataFrame:
    T = tree_tables(stage0_dir)
    keys = keys_for(T, ids)
    vals = {"match_id": keys["match_id"].astype(str).to_numpy()}
    vals.update(pool_members(T, keys))
    vals.update(rhythm_members(keys))
    for c in NOT_BUILT:
        vals[c] = np.full(len(keys), np.nan)
    return pd.DataFrame(vals)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", required=True, help="a text file with one match id per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--stage0", default=None, help="another Stage 0 folder (the parity proof's restored Stage 0)")
    a = ap.parse_args()
    ids = [x.strip() for x in Path(a.ids).read_text(encoding="utf-8").splitlines() if x.strip()]
    df = live_values(ids, a.stage0)
    for c in ("a_won", "y", "won", "winner"):
        if c in df.columns:
            raise RuntimeError("a result column would be written")
    df.to_parquet(a.out, index=False)
    print(json.dumps({"tree": str(ROOT), "matches": int(len(df)),
                      "present": {c: int(np.isfinite(df[c]).sum()) for c in df.columns if c != "match_id"}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
