"""Link the result sources no match-timing link file covers to the study's frozen Stage 0: TennisLive's event listings,
the WTA website's records (the Kaggle copy v29 and the WTA API's player-matches results of 2026) and the ITF's live data.

The loaders are the lower-level package's (src/eda/lower_level_evidence/candidate_stage0.py: load_wta_site,
load_itf_live), read-only; TennisLive's is the same loader with walkovers kept (status 'walkover', no sets) and its
event category, seeds and round kept. The linking is that package's too: srcc_common.link per tour and season (both
names in the window, confirmed by identical set scores or by the same round on a plausible day; a third pass by the
source's own player ids), then its event map and weekly-venue filter (a link into another tournament than the source
event's mapped one stands only with identical set scores). It runs against the snapshot's Stage 0, not the frozen
reference the package used.

Writes data/studies/source_reconciliation/context/work/selflink_<source>.parquet (one row per linked Stage 0 match:
match_id, sid, p1_side, sc, rd, pass, gap) and work/selfrows_<source>.parquet (the source rows: sid, names, ids, winner,
sets, status, event fields), and context/selflink_summary.json (rows read, linked, why the rest are not).

Run: ./python.sh src/eda/source_reconciliation/ctx_selflink.py [--sources tennislive,wta_site,itf_live]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import candidate_stage0 as CS  # noqa: E402
from src.eda.match_timing import srcc_common as K  # noqa: E402
from src.eda.predictability_diagnostic import common as PC  # noqa: E402
from src.eda.source_reconciliation import ctx_common as X  # noqa: E402

TL = CS.TL


def link_frame() -> pd.DataFrame:
    """srcc_common.stage0()'s frame on the snapshot: names, winner-first sets, early-round numbers, qualifying depth
    (no event country: the linker does not read it)."""
    m = X.stage0_matches()
    f = m[["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
           "tournament_name", "tournament_date", "status", "score", "player_a_id", "player_b_id", "a_won", "map_level",
           "name_a", "name_b"]].copy()
    f["tdate"] = pd.to_datetime(f["tournament_date"]).astype("datetime64[ns]")
    f["sets_w"] = f["score"].map(K.s0_sets)
    f["country"] = None
    return CS.add_event_columns(f.reset_index(drop=True))


def load_tennislive() -> tuple[pd.DataFrame, dict]:
    """candidate_stage0.load_tennislive with walkovers kept and the event's category, seeds, round and draw kept."""
    li = pd.read_parquet(TL / "listed.parquet",
                         columns=["event_key", "event_name", "event_kind", "event_rank", "tour", "discipline", "junior",
                                  "played", "match_id", "player1_id", "player1_name", "player1_flag", "player2_id",
                                  "player2_name", "player2_flag", "winner_side", "score", "player1_sets",
                                  "player2_sets", "end_reason", "start_utc", "draw", "round", "player1_seed",
                                  "player2_seed", "state"])
    li = li[li["discipline"].eq("singles") & ~li["junior"].eq("TRUE")].drop_duplicates(["event_key", "match_id"])
    stats = {"singles_listed": int(len(li))}
    walk = li["end_reason"].eq("walkover") & li["winner_side"].isin(["1", "2"])
    ok = (li["played"].eq("TRUE") & ~li["end_reason"].eq("walkover") & li["winner_side"].isin(["1", "2"])) | walk
    stats.update(walkovers_kept=int(walk.sum()), unplayed_or_no_winner=int((~ok).sum()))
    li = li[ok].copy()
    ev = pd.read_parquet(TL / "events.parquet", columns=["key", "first_week", "surface_code", "surface", "country",
                                                         "rank", "kind", "name"]).drop_duplicates("key").set_index("key")
    evk = ev.reindex(li["event_key"])
    w = li["winner_side"].astype(int).to_numpy()
    s1, s2 = li["player1_sets"].map(CS.tl_sets), li["player2_sets"].map(CS.tl_sets)
    pairs, sets4 = [], []
    for a, b, wk in zip(s1, s2, li["end_reason"].eq("walkover")):
        if wk:
            pairs.append(())
            sets4.append([])
            continue
        pairs.append(tuple((x[0], y[0]) for x, y in zip(a, b)))
        sets4.append([(x[0], y[0], x[1], y[1]) for x, y in zip(a, b)])
    kind = li["event_kind"].astype(str)
    level = kind.map(CS.TL_KIND_LEVEL).fillna(li["event_rank"].astype(str).map(CS.TL_RANK_LEVEL))
    played = pd.to_datetime(li["start_utc"].str[:10], format="%Y-%m-%d", errors="coerce")
    monday = pd.to_datetime(evk["first_week"].to_numpy(), format="%Y-%m-%d", errors="coerce")
    played_monday = played - pd.to_timedelta(played.dt.weekday, unit="D")
    ev_date = pd.Series(monday, index=li.index).where(~(played_monday > pd.Series(monday, index=li.index)), played_monday)
    ev_date = ev_date.fillna(played_monday)
    er = li["end_reason"].fillna("")
    rows = pd.DataFrame({
        "sid": "tennislive:" + li["event_key"].astype(str) + ":" + li["match_id"].astype(str),
        "tour": li["tour"].map({"atp": "atp", "wta": "wta"}).to_numpy(), "season": ev_date.dt.year.to_numpy(),
        "ev_key": "tennislive:" + li["event_key"].astype(str), "ev_name": li["event_name"].to_numpy(),
        "ev_date": ev_date.to_numpy(), "ev_surface": [CS.surface_of(s) for s in evk["surface_code"].to_numpy()],
        "ev_indoor": None, "ev_country": [CS.ioc(c) for c in evk["country"].to_numpy()], "ev_level": level.to_numpy(),
        "ev_draw": None, "qual": li["draw"].eq("qualifying").to_numpy(),
        "rnd": li["round"].where(li["round"].isin(list(PC.ROUND_ORDER)), None).to_numpy(),
        "day": played.to_numpy(), "date_basis": "utc_date",
        "p1": li["player1_name"].to_numpy(), "p2": li["player2_name"].to_numpy(),
        "id1": li["player1_id"].to_numpy(), "id2": li["player2_id"].to_numpy(),
        "c1": [CS.ioc(c) for c in li["player1_flag"]], "c2": [CS.ioc(c) for c in li["player2_flag"]],
        "winner": w, "status_hint": np.select([er.eq("walkover"), er.eq("retired"), er.eq("disqualified")],
                                              ["walkover", "retired", "defaulted"], "completed"),
        "score": li["score"].to_numpy(), "sets": pairs})
    rows = CS.finish(rows, "tennislive")
    extra = pd.DataFrame({"sid": "tennislive:" + li["event_key"].astype(str) + ":" + li["match_id"].astype(str),
                          "sets4": sets4, "ev_kind": kind.to_numpy(), "ev_rank": li["event_rank"].astype(str).to_numpy(),
                          "ev_surface_raw": evk["surface"].to_numpy(), "seed1": li["player1_seed"].to_numpy(),
                          "seed2": li["player2_seed"].to_numpy(), "round_raw": li["round"].to_numpy(),
                          "draw_raw": li["draw"].to_numpy(), "end_reason": er.to_numpy()})
    rows = rows.merge(extra, on="sid", how="left")
    stats["rows"] = int(len(rows))
    return rows, stats


def load(source: str) -> tuple[pd.DataFrame, dict]:
    if source == "tennislive":
        return load_tennislive()
    if source == "wta_site":
        r, s = CS.load_wta_site()
        r["sets4"] = [[(a, b, None, None) for a, b in t] for t in r["sets"]]
        return r, s
    if source == "itf_live":
        r, s = CS.load_itf_live()
        r["sets4"] = [[(a, b, None, None) for a, b in t] for t in r["sets"]]
        return r, s
    raise SystemExit(f"unknown source {source}")


def run(source: str, S: pd.DataFrame) -> dict:
    X.log(f"[{source}] loading")
    R, stats = load(source)
    R = R[R["tour"].isin(["atp", "wta"])].reset_index(drop=True)
    lo, hi = S["tdate"].min() - pd.Timedelta(days=30), S["tdate"].max() + pd.Timedelta(days=30)
    day = R["day"].where(R["day"].notna(), R["ev_date"])
    inside = day.between(lo, hi)
    stats["outside_stage0_dates"] = int((~inside).sum())
    R = R[inside].reset_index(drop=True)
    X.log(f"[{source}] {len(R):,} rows to link")
    lk, reason, amb = CS.link_rows(R, S)
    stats["linked_identity"] = int(len(lk))
    evmap = CS.event_map(R, lk, S)
    lk2, dropped = CS.weekly_venue_filter(R, lk, evmap, S)
    stats["dropped_by_weekly_venue_filter"] = int(len(dropped))
    stats["linked"] = int(len(lk2))
    stats["linked_by_pass"] = lk2["pass"].value_counts().to_dict()
    stats["linked_identical_sets"] = int(lk2["sc"].sum())
    stats["ambiguous_rows"] = int(len(amb))
    reason = reason[~reason.index.duplicated()]
    stats["row_outcomes"] = reason.value_counts().to_dict()
    X.WORK.mkdir(parents=True, exist_ok=True)
    keep = ["match_id", "sid", "p1_side", "sc", "rd", "pass", "gap"]
    lk2[keep].to_parquet(X.WORK / f"selflink_{source}.parquet", index=False)
    cols = [c for c in ["sid", "tour", "season", "ev_key", "ev_name", "ev_date", "ev_surface", "ev_indoor", "ev_level",
                        "ev_draw", "ev_country", "qual", "rnd", "day", "p1", "p2", "id1", "id2", "winner",
                        "status_hint", "score", "sets4", "ev_kind", "ev_rank", "ev_surface_raw", "seed1", "seed2",
                        "round_raw", "draw_raw", "end_reason"] if c in R.columns]
    R[R["sid"].isin(set(lk2["sid"]))][cols].to_parquet(X.WORK / f"selfrows_{source}.parquet", index=False)
    X.log(f"[{source}] linked {len(lk2):,}")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sources", default="tennislive,wta_site,itf_live")
    args = ap.parse_args()
    S = link_frame()
    X.log(f"Stage 0 link frame: {len(S):,} matches")
    path = X.OUT / "selflink_summary.json"
    import json
    old = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    for s in [x.strip() for x in args.sources.split(",") if x.strip()]:
        old[s] = run(s, S)
        X.write_json(path, old)
    return 0


if __name__ == "__main__":
    sys.exit(main())
