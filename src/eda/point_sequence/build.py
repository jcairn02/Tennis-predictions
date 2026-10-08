"""Build the unified point-sequence table from every point source, linked to Stage 0 and checked.

Run:  ./python.sh src/eda/point_sequence/build.py [--refresh SOURCES] [--workers 6]
      (--refresh all|wta,sofascore,...: rerun those adapters; their outputs are reused otherwise)

Steps
1. Adapters (adapters.py) for the new sources write points_<source>.parquet and matches_<source>.parquet; the WTA
   adapter also the umpire logs' non-point records. The shot-level study's eight sources are read as they are
   (data/studies/shot_level/stage1_points_<source>.parquet and stage0_source_matches.parquet).
2. Linking. New sources are linked with the shot-level study's Stage0Linker (same tour, both surname keys, date within
   -10..+21 days of Stage 0's tournament date, -40 for Slam qualifying; then one surname and a loose test of the other
   name; then the same round and week), against the current Stage 0. Stage 0 was rebuilt on 6 Oct 2026 at 17:07 and
   42 WTA 2026 match ids changed (data/studies/data_continuity/rebuilds/2026-10-07T0005Z/id_map.csv); every link is
   expressed in the pre-rebuild ids, the ones the model frame uses: a link to a new id is mapped to its old id, and,
   where the old match has its sides A and B the other way round (21 of the 42), the orientation is flipped. The
   shot-level study's links are already in pre-rebuild ids. Within a source, two records linked to one Stage 0 match
   are both kept in seq_matches, and only the better one competes for the choice.
3. Replay (replay.py) of every source match, under the rules Stage 0's context allows (best_of and format; the Slam's
   deciding-set rule by year), or, for an unlinked match, under any. Each match gets:
       replay status     complete / partial / overlong / unknown (a point's winner is not recorded)
       label mismatches  points where the source's own game (set) partition and the replay's disagree
       server agreement  share of points whose source server is the rules' server (first server chosen by majority)
       field conflicts   SofaScore and marcosjn2: regular games whose own per-game server field names the player the
                         alternation does not (their point tables carry the alternation's server)
       status            complete (replays to the end, labels agree), partial (consistent but unfinished: a retirement
                         or a truncated record), inconsistent (points after the end, an unknown winner, labels that
                         disagree with the rules, or a field conflict)
4. Score check against Stage 0's official result (score, status, winner): exact (tie-break points compared where Stage 0
   gives them) / tb_points_differ / sets_differ / winner_differs / prefix_of_official (a partial replay whose sets
   begin Stage 0's) / official_walkover (Stage 0 says no ball was struck) / no_official (no set scores; the winner is
   still checked).
5. Cross-source agreement on Stage 0 matches held by two or more sources: aligned point by point (by order in the
   match, players turned to Stage 0's sides), the share of points with the same winner and the same server; and the
   share of games with the same winner (aligned by set and game number of the replay), which a missing point does not
   shift.
6. One sequence per Stage 0 match: quality tier first (0 complete, matching the official score and not contradicted by
   another source; 1 the same but contradicted; 2 partial, a retirement whose official score it reproduces; 3 a
   truncated record; 4 complete but differing from the official score; 5 partial and differing; 6 inconsistent:
   TIERS), then source priority (common.PRIORITY), then length. ``usable`` = tier 0-2. The shot-level AO table
   (common.DEFECTIVE) is never chosen.
   Then an independent check of the chosen sequences against Stage 0's box score: each player's serve points and serve
   points won counted from the sequence (box_check). ``strict`` = usable and, where a box score exists, the same
   serve points (a box score with its players' serve statistics exchanged is accepted when another source agrees).
7. Coverage of the model frame (data/studies/surface_rating_race/model/model_frame.parquet) and of Stage 0: own
   sequence held; both players with at least 5 / 10 / 20 earlier usable sequenced matches; and depth, the median
   number of earlier sequenced matches, games and points per player at match time; the same for strict sequences.
   "Earlier" is the predictability diagnostic's own-history rule (common.asof_sums: earlier tournament dates, and
   earlier rounds of the same event).

Outputs (data/studies/point_sequence/)
    points_<source>.parquet     new sources' point tables (adapters.py documents the columns)
    matches_<source>.parquet    new sources' match tables with their links
    sequences.parquet           the chosen sequence of every linked Stage 0 match: match_id (model-frame ids), source,
                                key, a1, tier, usable, seq, set_no, game_no, game_idx, pt_no, is_tb (from the replay),
                                server (the rules' server, first server chosen to agree best with the source) and
                                winner in Stage 0's orientation (1 = side A, 2 = side B, 0 unknown or beyond the
                                replay), server_src (the source's own server, same orientation), serve_no, end, ender
                                (oriented like server), t_utc. Use usable rows (tiers 0-2) unless studying the others
    seq_matches.parquet         one row per source match: links, replay, checks, agreement, tier, chosen
    wta_events.parquet          the WTA umpire logs' records that are not points, with times and links
    agreement.csv               one row per pair of sources
    coverage_model.csv          model frame by tour x season
    coverage_stage0.csv         Stage 0 by tour x level x year
    build_summary.json          counts, replay outcomes, link rates, score checks, timings, inputs
    cache/                      intermediate replay results (rebuilt on every run)
"""
from __future__ import annotations

import argparse
import itertools
import json
import re
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.point_sequence import common as C  # noqa: E402
from src.eda.point_sequence import replay as R  # noqa: E402

CACHE = C.OUT / "cache"
REBUILD = ROOT / "data" / "studies" / "data_continuity" / "rebuilds" / "2026-10-07T0005Z"
ID_MAP = REBUILD / "id_map.csv"
OLD_S0 = REBUILD / "replaced" / "data" / "studies" / "predictability_diagnostic"
S0 = ROOT / "data" / "studies" / "predictability_diagnostic"
MODEL_FRAME = ROOT / "data" / "studies" / "surface_rating_race" / "model" / "model_frame.parquet"
S0_COLS = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "best_of", "format",
           "tournament_name", "tournament_id", "tournament_date", "status", "score", "a_won", "map_level",
           "player_a_id", "player_b_id"]
TIMINGS: dict[str, float] = {}


def timed(name):
    def deco(fn):
        def run(*a, **k):
            t = time.time()
            out = fn(*a, **k)
            TIMINGS[name] = round(TIMINGS.get(name, 0) + time.time() - t, 1)
            return out
        return run
    return deco


# ------------------------------------------------------------------------------------------------
# 1. Adapters

@timed("adapters")
def run_adapters(refresh: set[str], workers: int) -> dict:
    from src.eda.point_sequence import adapters as A
    C.OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    audits = {}
    for src in C.NEW:
        pth, mth = C.OUT / f"points_{src}.parquet", C.OUT / f"matches_{src}.parquet"
        apath = CACHE / f"adapter_{src}.json"
        if pth.exists() and mth.exists() and src not in refresh and "all" not in refresh:
            audits[src] = json.loads(apath.read_text(encoding="utf-8")) if apath.exists() else {}
            C.log(f"adapter {src}: reused {pth.name}")
            continue
        t = time.time()
        C.log(f"adapter {src}")
        audit = {}
        if src == "marcosjn2":
            pts, m = A.marcosjn2()
            audit = {"tiebreak_trailing_points_dropped": int(m["tb_trailing_dropped"].sum()),
                     "matches_server_field_agrees_fully": int((m["server_field_agree"] == 1).sum()),
                     "regular_game_server_field_agreement_mean": float(m["server_field_agree"].mean()),
                     "tiebreak_server_field_is_first_server_mean": float(m["tb_field_is_first_server"].mean())}
        elif src == "sofascore":
            pts, m, audit = A.sofascore()
        elif src == "wta":
            pts, m, ev = A.wta(workers)
            ev.to_parquet(CACHE / "wta_events_raw.parquet", index=False)
            audit = {"logs": m["log"].value_counts().to_dict(),
                     "matches_with_unknown_winners": int((m["unknown_winners"].fillna(0) > 0).sum()),
                     "points_unknown_winner": int(m["unknown_winners"].fillna(0).sum()),
                     "tiebreak_last_points_filled": int(m["tb_last_point_filled"].fillna(0).sum()),
                     "serve_no_attribute_points": int(m["serve_no_attr_points"].fillna(0).sum()),
                     "serve_no_attribute_agrees_with_fault_rule": int(m["serve_no_attr_agree"].fillna(0).sum()),
                     "non_point_records": int(len(ev))}
        elif src == "wta_pbp":
            pts, m = A.wta_pbp(workers)
            audit = {"points_unknown_winner": int((pts["winner"] == 0).sum()),
                     "matches_with_unknown_winners": int((m["unknown_winners"] > 0).sum()),
                     "points_without_time": int(pts["t_utc"].isna().sum()),
                     "point_winner_field_disagrees_points": int(m["point_winner_field_disagrees"].sum())}
        elif src == "ausopen_mc":
            pts, m = A.ausopen_mc()
            audit = {"matches": int(len(m)), "matches_with_points": int((m["n_points"] > 0).sum()),
                     "points": int(len(pts)), "by_year": {int(k): int(v) for k, v in
                                                          m[m["n_points"] > 0]["year"].value_counts().items()}}
            m = m[m["n_points"] > 0].reset_index(drop=True)
        elif src == "sackmann_pbp":
            pts, m = A.sackmann_pbp()
            audit = {"rows_read": int(m.attrs.get("rows_read", 0)), "parse_notes": m["parse_note"].value_counts().to_dict(),
                     "matches_by_year": {int(k): int(v) for k, v in m["year"].value_counts().sort_index().items()}}
        pts.to_parquet(pth, index=False)
        m.to_parquet(mth, index=False)
        audit["seconds"] = round(time.time() - t, 1)
        C.write_json(apath, audit)
        audits[src] = audit
        C.log(f"  {src}: {len(pts):,} points, {len(m):,} matches ({audit['seconds']} s)")
    return audits


# ------------------------------------------------------------------------------------------------
# 2. Stage 0 view (pre-rebuild ids) and linking

def id_map() -> pd.DataFrame:
    """The 42 rebuilt ids: new -> old, and whether the old match has its sides the other way round."""
    idm = pd.read_csv(ID_MAP)
    names = []
    for folder, col in ((OLD_S0, "old_match_id"), (S0, "new_match_id")):
        mp = pd.read_parquet(folder / "stage0_match_players.parquet", columns=["match_id", "side", "player_name"])
        mp = mp[mp["match_id"].isin(set(idm[col]))]
        a = mp[mp["side"].eq("A")].set_index("match_id")["player_name"]
        names.append(idm[col].map(a))
    from src.eda.data_map import measure as M
    idm["flip"] = [M.surname_key(o) != M.surname_key(n) for o, n in zip(names[0], names[1])]
    return idm


def stage0_view(idm: pd.DataFrame) -> pd.DataFrame:
    """Stage 0 as the model frame knows it: the current table, with the 42 rebuilt matches' rows taken from the
    pre-rebuild copy (their old ids, sides and result)."""
    cur = pd.read_parquet(S0 / "stage0_matches.parquet", columns=S0_COLS)
    old = pd.read_parquet(OLD_S0 / "stage0_matches.parquet", columns=S0_COLS)
    v = pd.concat([cur[~cur["match_id"].isin(set(idm["new_match_id"]))],
                   old[old["match_id"].isin(set(idm["old_match_id"]))]], ignore_index=True)
    v["slam"] = np.where(v["level"].eq("GS"), v["tournament_name"].map(C.slam_of), None)
    return v


def _bool_or_none(x):
    if x is None or (isinstance(x, float) and np.isnan(x)) or x is pd.NA:
        return None
    return bool(x)


def map_links(mid: pd.Series, a1: pd.Series, new2old: dict, flip: dict) -> tuple[pd.Series, pd.Series, pd.Series,
                                                                                  pd.Series]:
    """Links to the current Stage 0 expressed in pre-rebuild ids: (match_id, a1, mapped, flipped). A rebuilt id is
    replaced by its old id, and where the old match has its sides the other way round the orientation is flipped."""
    mid = mid.astype(object).where(mid.notna(), None)
    a1 = a1.astype(object).map(_bool_or_none)
    mapped = mid.map(lambda x: x in new2old if isinstance(x, str) else False).astype(bool)
    flipped = mapped & mid.map(lambda x: bool(flip.get(x, False)) if isinstance(x, str) else False).astype(bool)
    a1 = pd.Series([(None if v is None else (not v)) if f else v for v, f in zip(a1, flipped)], index=a1.index,
                   dtype=object)
    out = mid.map(lambda x: new2old.get(x, x) if isinstance(x, str) else None).astype(object)
    out = pd.Series([v if isinstance(v, str) else None for v in out], index=mid.index, dtype=object)
    return out, a1, mapped, flipped


@timed("link")
def link_new(idm: pd.DataFrame) -> dict:
    from src.eda.shot_level import common as S
    C.log("linking: Stage 0 universe")
    linker = S.Stage0Linker()
    new2old = dict(zip(idm["new_match_id"], idm["old_match_id"]))
    flip = dict(zip(idm["new_match_id"], idm["flip"]))
    report = {}
    for src in C.NEW:
        mth = C.OUT / f"matches_{src}.parquet"
        m = pd.read_parquet(mth)
        rows = m[["tour", "d", "name1", "name2", "round", "level", "draw"]].copy()
        rows["d"] = pd.to_datetime(rows["d"], errors="coerce")
        lk = linker.link(rows)
        mid, a1, mapped, flipped = map_links(lk["match_id"], lk["a1"], new2old, flip)
        m["match_id"], m["a1"] = mid.to_numpy(), a1.to_numpy()
        m["link_mapped"] = mapped.to_numpy()
        m["a1_flipped"] = flipped.to_numpy()
        m.to_parquet(mth, index=False)
        report[src] = {"matches": int(len(m)), "linked": int(m["match_id"].notna().sum()),
                       "oriented": int(m["a1"].notna().sum()), "links_needing_id_map": int(mapped.sum()),
                       "of_which_side_flipped": int(flipped.sum())}
        C.log(f"  {src}: linked {report[src]['linked']:,} of {len(m):,}; mapped {int(mapped.sum())}")
    return report


def load_matches(src: str) -> pd.DataFrame:
    """A source's match table with its Stage 0 link (match_id in pre-rebuild ids, a1)."""
    if src in C.NEW:
        m = pd.read_parquet(C.OUT / f"matches_{src}.parquet")
        m["linked_by"] = "stage0_linker"
        return m
    s = pd.read_parquet(C.SHOT / "stage0_source_matches.parquet",
                        columns=["source", "key", "tour", "year", "d", "name1", "name2", "round", "draw", "level",
                                 "match_id", "a1"])
    s = s[s["source"].eq(src)].drop_duplicates("key").copy()
    s["a1"] = s["a1"].astype(object).map(lambda x: None if x is None or pd.isna(x) else bool(x))
    s["link_mapped"] = False
    s["a1_flipped"] = False
    s["linked_by"] = "shot_level_stage0_sources"
    s["has_time"] = False
    s["slam"] = np.where(s["level"].isin(["GS", "GSQ"]), None, None)
    s["best_of_hint"] = 3
    return s


def points_path(src: str) -> Path:
    return C.OUT / f"points_{src}.parquet" if src in C.NEW else C.SHOT / f"stage1_points_{src}.parquet"


# ------------------------------------------------------------------------------------------------
# 3. Replay

def _replay_chunk(args) -> tuple[dict, list]:
    winners, servers, gkeys, setnos, offsets, ctxs = args
    n = len(winners)
    out = {k: np.full(n, -1, np.int16) for k in ("d_set", "d_game", "d_gidx", "d_pt")}
    out["d_tb"] = np.zeros(n, np.int8)
    out["srv_rule"] = np.zeros(n, np.int8)
    rows = []
    for j, ctx in enumerate(ctxs):
        a, b = offsets[j], offsets[j + 1]
        w = winners[a:b]
        r = R.replay_match(w, ctx)
        sl = slice(a, b)
        out["d_set"][sl], out["d_game"][sl], out["d_gidx"][sl], out["d_pt"][sl] = r.set_no, r.game_no, r.game_idx, r.pt_no
        out["d_tb"][sl] = r.is_tb
        src_srv = servers[a:b]
        s0, agree = R.best_first_server(r.game_idx, r.pt_no, r.is_tb, src_srv)
        out["srv_rule"][sl] = R.rule_servers(r.game_idx, r.pt_no, r.is_tb, s0)
        stop = r.stop
        lab = R.boundary_mismatches(r.game_idx, gkeys[a:b], stop)
        slab = R.boundary_mismatches(r.set_no, setnos[a:b], stop)
        gi = r.game_idx[:stop]
        rows.append({"replay": r.status, "stop": int(stop), "rule": r.rule.name, "rule_primary": bool(r.primary),
                     "rules_tried": int(r.tried), "replay_winner": int(r.winner),
                     "sets_p1": R.score_text(r.sets, r.games, 1, partial=r.status != "complete"),
                     "sets_json": json.dumps([list(s) for s in r.sets]), "cur_games": f"{r.games[0]}-{r.games[1]}",
                     "cur_points": f"{r.points[0]}-{r.points[1]}", "n_sets_done": len(r.sets),
                     "n_games": int(gi.max() + 1) if stop else 0, "n_tb_points": int(r.is_tb[:stop].sum()),
                     "label_mismatch": lab, "set_label_mismatch": slab, "s0": int(s0),
                     "server_agree": agree, "n_unknown": int(((w != 1) & (w != 2)).sum()), "n_points": int(b - a)})
    return out, rows


def context(m: pd.DataFrame, view: pd.DataFrame) -> list[dict]:
    """Replay context per match: Stage 0's (best_of certain) where linked, else the source's."""
    v = view.set_index("match_id")[["best_of", "format", "slam", "qualifying", "year", "level"]]
    j = m[["match_id"]].join(v, on="match_id")
    ctxs = []
    for r, (bo, fmt, slam, q, y, lv) in zip(m.itertuples(index=False), j[["best_of", "format", "slam", "qualifying",
                                                                            "year", "level"]].itertuples(index=False)):
        if isinstance(r.match_id, str) and pd.notna(bo):
            ctxs.append({"best_of": int(bo), "best_of_certain": True, "format": fmt,
                         "slam": slam if isinstance(slam, str) else None, "qual": bool(q), "year": int(y),
                         "level": lv})
        else:
            yr = getattr(r, "year", None)
            ctxs.append({"best_of": int(getattr(r, "best_of_hint", 3) or 3), "best_of_certain": False,
                         "format": None, "slam": getattr(r, "slam", None) if isinstance(getattr(r, "slam", None), str) else None,
                         "qual": getattr(r, "draw", "") == "qual",
                         "year": int(yr) if yr is not None and pd.notna(yr) else 0, "level": getattr(r, "level", None)})
    return ctxs


FIELD_SERVER_SOURCES = ("sofascore", "marcosjn2")


def field_conflicts(src: str) -> pd.Series:
    """For the sources whose server is one field per game (SofaScore, marcosjn2; the point table's server is derived
    from the alternation): per match, the regular games whose field names the other player. In the SofaScore records
    the ace and double-fault codes of such games fit the field, not the alternation (build_summary.json, adapter
    audit), so the game order or the serving order of those records is suspect and the match is marked inconsistent.
    Tie-breaks are left out: there the field is no better than chance."""
    if src not in FIELD_SERVER_SOURCES:
        return pd.Series(dtype="int64")
    p = pd.read_parquet(points_path(src), columns=["key", "game_key", "is_tb", "server", "server_src"])
    g = p.drop_duplicates(["key", "game_key"])
    bad = g[(g["is_tb"] == 0) & g["server_src"].isin([1, 2]) & (g["server_src"] != g["server"])]
    return bad.groupby("key").size()


@timed("replay")
def replay_source(src: str, view: pd.DataFrame, workers: int) -> pd.DataFrame:
    m = load_matches(src)
    p = pd.read_parquet(points_path(src), columns=["key", "seq", "set_no", "game_key", "server", "winner"])
    p = p[p["key"].isin(set(m["key"]))]
    p = p.sort_values(["key", "seq"], kind="mergesort").reset_index(drop=True)
    keys = p["key"].to_numpy(dtype=object)
    starts = np.flatnonzero(np.r_[True, keys[1:] != keys[:-1]])
    order_keys = keys[starts]
    offsets = np.r_[starts, len(p)].astype(np.int64)
    m = m.drop_duplicates("key").set_index("key").loc[order_keys].reset_index()
    ctxs = context(m, view)
    win = p["winner"].to_numpy(np.int8)
    srv = p["server"].to_numpy(np.int8)
    gk = p["game_key"].to_numpy(np.int32)
    sn = p["set_no"].to_numpy(np.int8)
    nchunk = max(1, min(48, len(m) // 500 + 1))
    bounds = np.linspace(0, len(m), nchunk + 1).astype(int)
    tasks = []
    for c0, c1 in zip(bounds[:-1], bounds[1:]):
        if c1 <= c0:
            continue
        a, b = offsets[c0], offsets[c1]
        tasks.append((win[a:b], srv[a:b], gk[a:b], sn[a:b], offsets[c0:c1 + 1] - a, ctxs[c0:c1]))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        res = list(ex.map(_replay_chunk, tasks))
    der = {k: np.concatenate([r[0][k] for r in res]) for k in res[0][0]}
    rows = [x for r in res for x in r[1]]
    d = pd.DataFrame({"key": p["key"], "seq": p["seq"].astype("int32"), **der})
    d.to_parquet(CACHE / f"replay_points_{src}.parquet", index=False)
    rm = pd.DataFrame(rows)
    rm.insert(0, "key", order_keys)
    # the replay's columns replace any of the same name in the match table (the adapters' own n_points among them)
    m = m.drop(columns=[c for c in rm.columns if c in m.columns and c != "key"])
    out = m.merge(rm, on="key", how="left")
    out["source"] = src
    out["field_conflicts"] = out["key"].map(field_conflicts(src)).fillna(0).astype(int)
    # status from the replay, the labels and (SofaScore, marcosjn2) the per-game server field
    issues = []
    for r in out.itertuples(index=False):
        it = []
        if r.replay == "overlong":
            it.append("points_after_end")
        if r.replay == "unknown":
            it.append("unknown_winner")
        if r.label_mismatch > 0:
            it.append("game_labels")
        if r.set_label_mismatch > 0:
            it.append("set_labels")
        if r.field_conflicts > 0:
            it.append("server_field_conflict")
        issues.append(";".join(it))
    out["issues"] = issues
    ok_labels = (out["label_mismatch"] == 0) & (out["set_label_mismatch"] == 0) & (out["field_conflicts"] == 0)
    out["status"] = np.select([out["replay"].eq("complete") & ok_labels, out["replay"].eq("partial") & ok_labels],
                              ["complete", "partial"], "inconsistent")
    C.log(f"replay {src}: " + ", ".join(f"{k} {v}" for k, v in out["status"].value_counts().items()))
    return out


# ------------------------------------------------------------------------------------------------
# 4. Score check

_SET = re.compile(r"^\[?(\d+)-(\d+)\]?(?:\((\d+)\))?$")
EARLY = ("RET", "W/O", "DEF", "ABD", "DEF.", "RET.", "WALKOVER", "DEFAULT", "ABANDONED", "UNK", "RE")


def parse_official(score: str, fmt: str | None) -> tuple[list, bool]:
    """Stage 0's score (winner first) -> ([(w, l, tb_loser or None, mtb)], ended_early)."""
    out, early = [], False
    toks = str(score or "").replace("&nbsp;", " ").split()
    for i, t in enumerate(toks):
        m = _SET.match(t)
        if m:
            w, l = int(m.group(1)), int(m.group(2))
            tb = int(m.group(3)) if m.group(3) else None
            mtb = t.startswith("[") or (fmt == "match_tiebreak" and max(w, l) >= 10)
            out.append((w, l, tb, mtb))
        elif t.upper().strip(".") in EARLY or t.upper().startswith("RET") or t.upper().startswith("DEF"):
            early = True
    return out, early


def score_check(seqm: pd.DataFrame, view: pd.DataFrame) -> pd.DataFrame:
    v = view.set_index("match_id")[["score", "status", "a_won", "format"]]
    j = seqm[["match_id", "a1", "replay", "replay_winner", "sets_json", "cur_games", "status"]].join(
        v.rename(columns={"status": "s0_status"}), on="match_id")
    res = []
    for r in j.itertuples(index=False):
        if not isinstance(r.match_id, str):
            res.append("not_linked")
            continue
        if r.a1 is None or pd.isna(r.a_won):
            res.append("not_oriented")
            continue
        if r.s0_status == "walkover":
            # no ball was struck in Stage 0's match: the points belong to another meeting of the pair (or Stage 0 errs)
            res.append("official_walkover")
            continue
        off, early = parse_official(r.score, r.format)
        p1_wins = bool(r.a1) == bool(r.a_won)
        if not off:
            # no set scores (a blank Stage 0 score): the winner can still be checked
            wrong = r.replay == "complete" and r.replay_winner in (1, 2) and (r.replay_winner == 1) != p1_wins
            res.append("winner_differs" if wrong and not early else "no_official")
            continue
        sets = json.loads(r.sets_json) if isinstance(r.sets_json, str) else []
        done = []                                   # completed sets, the official winner's games first
        for g1, g2, t1, t2 in sets:
            w, l, tw, tl = (g1, g2, t1, t2) if p1_wins else (g2, g1, t2, t1)
            if g1 + g2 == 1 and t1 is not None:       # a match tie-break, compared by its points
                done.append((tw, tl, None))
            else:
                done.append((w, l, min(tw, tl) if tw is not None else None))
        cur = None
        if r.replay != "complete":
            cg = [int(x) for x in str(r.cur_games).split("-")] if isinstance(r.cur_games, str) else [0, 0]
            if cg != [0, 0]:
                cur = (cg[0], cg[1]) if p1_wins else (cg[1], cg[0])
        offs = [(a, b, t) for a, b, t, _ in off]
        while offs and offs[-1][:2] == (0, 0):     # '6-2 0-0 RET'
            offs.pop()
        mine = done + ([(cur[0], cur[1], None)] if cur else [])
        if r.replay == "complete" and r.replay_winner in (1, 2) and not early and (r.replay_winner == 1) != p1_wins:
            res.append("winner_differs")
        elif [(a, b) for a, b, _ in mine] == [(a, b) for a, b, _ in offs]:
            # tie-break points are compared where Stage 0 gives them ('7-6' without the loser's points does not)
            same_tb = all(to is None or tm == to for (_, _, tm), (_, _, to) in zip(mine, offs))
            res.append("exact" if same_tb else "tb_points_differ")
        elif r.replay != "complete" and len(done) < len(offs) and \
                [(a, b) for a, b, _ in done] == [(a, b) for a, b, _ in offs[:len(done)]] and \
                (cur is None or (cur[0] <= offs[len(done)][0] and cur[1] <= offs[len(done)][1])):
            res.append("prefix_of_official")         # a truncated record (or a retirement Stage 0 calls complete)
        else:
            res.append("sets_differ")
    seqm = seqm.copy()
    seqm["score_check"] = res
    seqm["official_score"] = j["score"].to_numpy()
    seqm["official_status"] = j["s0_status"].to_numpy()
    return seqm


# ------------------------------------------------------------------------------------------------
# 5. Agreement

def oriented_points(src: str, keys: pd.DataFrame) -> pd.DataFrame:
    """Points of the given (key, match_id, a1) with winner and server turned to Stage 0's sides, plus the replay's set
    and game numbers."""
    p = pd.read_parquet(points_path(src), columns=["key", "seq", "server", "winner"])
    p = p[p["key"].isin(set(keys["key"]))]
    d = pd.read_parquet(CACHE / f"replay_points_{src}.parquet", columns=["key", "seq", "d_set", "d_game"])
    d = d[d["key"].isin(set(keys["key"]))]
    p = p.merge(d, on=["key", "seq"], how="left").merge(keys[["key", "match_id", "a1"]], on="key")
    a1 = p["a1"].astype(bool).to_numpy()
    for c in ("server", "winner"):
        v = p[c].to_numpy()
        p[c] = np.where((v == 1) | (v == 2), np.where(a1, v, 3 - v), 0).astype("int8")
    return p.drop(columns=["a1"])


@timed("agreement")
def agreement(seqm: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Pairwise agreement on multi-source matches, and per (source, match) whether it agrees with another source."""
    best = seqm[seqm["primary_in_source"] & seqm["match_id"].notna() & seqm["a1"].notna()]
    nsrc = best.groupby("match_id")["source"].nunique()
    multi = best[best["match_id"].isin(nsrc[nsrc >= 2].index)]
    pts = {s: oriented_points(s, g[["key", "match_id", "a1"]]) for s, g in multi.groupby("source")}
    games = {}
    for s, p in pts.items():
        last = p[p["d_set"] >= 1].sort_values(["match_id", "seq"]).groupby(["match_id", "d_set", "d_game"]).tail(1)
        games[s] = last[["match_id", "d_set", "d_game", "winner"]]
    rows, per = [], []
    for sa, sb in itertools.combinations(sorted(pts, key=lambda s: C.RANK.get(s, 99)), 2):
        pa, pb = pts[sa], pts[sb]
        both = np.intersect1d(pa["match_id"].unique(), pb["match_id"].unique())
        if len(both) == 0:
            continue
        x = pa[pa["match_id"].isin(both)].merge(pb[pb["match_id"].isin(both)], on=["match_id", "seq"],
                                                suffixes=("_a", "_b"))
        known = (x["winner_a"] > 0) & (x["winner_b"] > 0)
        x["w_eq"] = (x["winner_a"] == x["winner_b"]) & known
        x["w_known"] = known
        sk = (x["server_a"] > 0) & (x["server_b"] > 0)
        x["s_eq"] = (x["server_a"] == x["server_b"]) & sk
        x["s_known"] = sk
        g = x.groupby("match_id").agg(n=("seq", "size"), w_eq=("w_eq", "sum"), w_known=("w_known", "sum"),
                                      s_eq=("s_eq", "sum"), s_known=("s_known", "sum"))
        na = pa[pa["match_id"].isin(both)].groupby("match_id").size()
        nb = pb[pb["match_id"].isin(both)].groupby("match_id").size()
        g["n_a"], g["n_b"] = na.reindex(g.index).to_numpy(), nb.reindex(g.index).to_numpy()
        g["w_share"] = g["w_eq"] / g["w_known"].where(g["w_known"] > 0)
        g["s_share"] = g["s_eq"] / g["s_known"].where(g["s_known"] > 0)
        g["agree"] = (g["w_share"] >= 0.98) & (g["s_share"] >= 0.98) & (g["n"] >= 20)
        ga, gb = games[sa], games[sb]
        gg = ga[ga["match_id"].isin(both)].merge(gb[gb["match_id"].isin(both)], on=["match_id", "d_set", "d_game"])
        ggk = gg[(gg["winner_x"] > 0) & (gg["winner_y"] > 0)]
        game_share = ggk.assign(eq=ggk["winner_x"] == ggk["winner_y"]).groupby("match_id")["eq"].mean()
        rows.append({"pair": f"{sa} | {sb}", "a": sa, "b": sb, "matches_both": int(len(both)),
                     "same_point_count": float((g["n_a"] == g["n_b"]).mean()),
                     "points_compared": int(g["w_known"].sum()),
                     "point_winner_agree": float(g["w_eq"].sum() / max(g["w_known"].sum(), 1)),
                     "point_server_agree": float(g["s_eq"].sum() / max(g["s_known"].sum(), 1)),
                     "matches_winner_agree_ge98": float((g["w_share"] >= 0.98).mean()),
                     "matches_server_agree_ge98": float((g["s_share"] >= 0.98).mean()),
                     "matches_agree_both_ge98": float(g["agree"].mean()),
                     "matches_identical": float(((g["w_share"] == 1) & (g["s_share"] == 1) &
                                                 (g["n_a"] == g["n_b"])).mean()),
                     "median_match_winner_agree": float(g["w_share"].median()),
                     "games_compared": int(len(ggk)),
                     "game_winner_agree": float((ggk["winner_x"] == ggk["winner_y"]).mean()) if len(ggk) else None,
                     "matches_all_games_agree": float((game_share == 1).mean()) if len(game_share) else None})
        for side, s in (("a", sa), ("b", sb)):
            per.append(pd.DataFrame({"source": s, "match_id": g.index, "other": sb if side == "a" else sa,
                                     "agree": g["agree"].to_numpy(), "w_share": g["w_share"].to_numpy(),
                                     "s_share": g["s_share"].to_numpy()}))
        C.log(f"  {sa} | {sb}: {len(both)} matches, winners {rows[-1]['point_winner_agree']:.4f}, "
              f"servers {rows[-1]['point_server_agree']:.4f}")
    per = pd.concat(per, ignore_index=True) if per else pd.DataFrame(columns=["source", "match_id", "other", "agree"])
    return pd.DataFrame(rows), per


# ------------------------------------------------------------------------------------------------
# 6. Choice

TIERS = {0: "complete, official score reproduced (or none to check, under the first-candidate rule), not contradicted "
             "by another source",
         1: "as 0, but every other source holding the match disagrees with it point by point",
         2: "partial: the match ended early (retirement, default) and the replay reproduces the official score",
         3: "partial: a truncated record, its sets the beginning of the official score",
         4: "complete, but the official score differs (or a fallback rule could not be checked against it)",
         5: "partial, not matching the official score",
         6: "inconsistent: points after the end, an unknown point winner, game/set labels that break the rules, or "
            "(SofaScore, marcosjn2) a regular game whose own server field breaks the alternation"}


def tiers(seqm: pd.DataFrame) -> pd.Series:
    """Quality tier of each linked source match (TIERS); NaN when not linked to Stage 0. A tie-break whose points differ
    from Stage 0's counts as reproducing the official score only when another source agrees with the sequence."""
    sc = seqm["score_check"]
    agrees = seqm["agrees_with_other"].fillna(False).astype(bool)
    score_ok = sc.eq("exact") | (sc.eq("tb_points_differ") & agrees)
    score_unknown = sc.isin(["no_official", "not_oriented"])
    contradicted = seqm["n_other_sources"].gt(0) & ~agrees
    complete, partial = seqm["status"].eq("complete"), seqm["status"].eq("partial")
    trusted_rule = seqm["rule_primary"].fillna(False).astype(bool) | score_ok
    t = np.select([complete & (score_ok | score_unknown) & trusted_rule & ~contradicted,
                   complete & (score_ok | score_unknown) & trusted_rule,
                   partial & score_ok,
                   partial & sc.eq("prefix_of_official"),
                   complete,
                   partial],
                  [0, 1, 2, 3, 4, 5], 6).astype("float64")
    linked = seqm["match_id"].notna() & seqm["a1"].notna()
    t[~linked.to_numpy()] = np.nan
    return pd.Series(t, index=seqm.index)


def wta_feeds(seqm: pd.DataFrame, per: pd.DataFrame) -> dict:
    """The evidence for ranking the WTA point-by-point feed after marcosjn2: point counts of the two WTA feeds where
    both reproduce the official score, and, on matches all three hold, which source the umpire log sides with."""
    one = seqm[seqm["primary_in_source"] & seqm["match_id"].notna()]
    w = one[one["source"].eq("wta")].set_index("match_id")
    p = one[one["source"].eq("wta_pbp")].set_index("match_id")
    both = w.index.intersection(p.index)
    ok = both[(w.loc[both, "status"].eq("complete") & w.loc[both, "score_check"].eq("exact") &
               p.loc[both, "status"].eq("complete") & p.loc[both, "score_check"].eq("exact")).to_numpy()]
    diff = (w.loc[ok, "stop"] - p.loc[ok, "stop"])
    ag = per.set_index(["source", "other", "match_id"])["agree"].sort_index()

    def pair(a, b):
        return ag.xs((a, b), level=["source", "other"]) if (a, b) in ag.index.droplevel(2) else pd.Series(dtype=bool)

    lp, lm, pm = pair("wta", "wta_pbp"), pair("wta", "marcosjn2"), pair("wta_pbp", "marcosjn2")
    tri = lp.index.intersection(lm.index).intersection(pm.index)
    lp, lm, pm = lp.loc[tri], lm.loc[tri], pm.loc[tri]
    return {"both_wta_feeds_reproduce_official_score": int(len(ok)),
            "point_by_point_has_fewer_points": int((diff > 0).sum()), "point_by_point_has_more_points": int((diff < 0).sum()),
            "difference_log_minus_pbp_median_where_unequal": float(diff[diff != 0].median()) if (diff != 0).any() else None,
            "matches_held_by_log_pbp_and_marcosjn2": int(len(tri)),
            "pbp_and_marcosjn2_disagree": int((~pm).sum()),
            "of_which_log_agrees_with_marcosjn2_only": int((~pm & lm & ~lp).sum()),
            "of_which_log_agrees_with_pbp_only": int((~pm & lp & ~lm).sum()),
            "of_which_log_agrees_with_neither": int((~pm & ~lp & ~lm).sum()),
            "log_and_marcosjn2_disagree": int((~lm).sum()),
            "of_which_pbp_agrees_with_log_only": int((~lm & lp & ~pm).sum()),
            "of_which_pbp_agrees_with_marcosjn2_only": int((~lm & pm & ~lp).sum()),
            "agree_means": "both winners and servers equal on at least 98% of the points the two hold in common "
                           "(at least 20)"}


@timed("sequences")
def write_sequences(seqm: pd.DataFrame) -> pd.DataFrame:
    ch = seqm[seqm["chosen"]]
    parts = []
    for src, g in ch.groupby("source"):
        keys = g[["key", "match_id", "a1", "tier", "usable"]]
        p = pd.read_parquet(points_path(src), columns=["key", "seq", "server", "winner", "serve_no", "end", "ender"] +
                            (["t_utc"] if src in C.NEW else []))
        p = p[p["key"].isin(set(keys["key"]))]
        if "t_utc" not in p:
            p["t_utc"] = np.nan
        d = pd.read_parquet(CACHE / f"replay_points_{src}.parquet")
        d = d[d["key"].isin(set(keys["key"]))]
        p = p.merge(d, on=["key", "seq"], how="left").merge(keys, on="key")
        # the server is the rules' (the first server chosen to agree best with the source); the source's own is kept
        p = p.rename(columns={"server": "server_src"})
        p["server"] = p["srv_rule"]
        a1 = p["a1"].astype(bool).to_numpy()
        for c in ("server", "server_src", "winner", "ender"):
            v = p[c].to_numpy()
            p[c] = np.where((v == 1) | (v == 2), np.where(a1, v, 3 - v), 0).astype("int8")
        p["source"] = src
        parts.append(p)
    s = pd.concat(parts, ignore_index=True)
    s = s.rename(columns={"d_set": "set_no", "d_game": "game_no", "d_gidx": "game_idx", "d_pt": "pt_no",
                          "d_tb": "is_tb"})
    s = s.sort_values(["match_id", "seq"], kind="mergesort").reset_index(drop=True)
    cols = ["match_id", "source", "key", "a1", "tier", "usable", "seq", "set_no", "game_no", "game_idx", "pt_no",
            "is_tb", "server", "winner", "server_src", "serve_no", "end", "ender", "t_utc"]
    s = s[cols]
    for c in ("set_no", "game_no", "game_idx", "pt_no"):
        s[c] = s[c].astype("int16")
    for c in ("is_tb", "tier", "serve_no", "end"):
        s[c] = s[c].astype("int8")
    s["a1"] = s["a1"].astype(bool)
    s["match_id"] = s["match_id"].astype("category")
    s["source"] = s["source"].astype("category")
    s.to_parquet(C.OUT / "sequences.parquet", index=False)
    return s


# ------------------------------------------------------------------------------------------------
# 7. Coverage

def match_players(idm: pd.DataFrame, extra: list[str] | None = None) -> pd.DataFrame:
    """Stage 0's player rows in pre-rebuild ids (the 42 rebuilt matches' rows from the pre-rebuild copy)."""
    cols = ["match_id", "player_id", "side"] + list(extra or [])
    cur = pd.read_parquet(S0 / "stage0_match_players.parquet", columns=cols)
    old = pd.read_parquet(OLD_S0 / "stage0_match_players.parquet", columns=cols)
    mp = pd.concat([cur[~cur["match_id"].isin(set(idm["new_match_id"]))],
                    old[old["match_id"].isin(set(idm["old_match_id"]))]], ignore_index=True)
    return mp


@timed("box_check")
def box_check(seq: pd.DataFrame, seqm: pd.DataFrame, idm: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """An independent check of the chosen sequences: each player's serve points and serve points won, counted from the
    sequence, against Stage 0's box score (svpt; first_won + second_won) where it has one. A match whose two players'
    counts are the box score's the other way round is 'mirrored' (with the official score reproduced, that is a box
    score with its players' serve statistics exchanged, or a sequence whose servers are all exchanged; agreement with
    another source tells which)."""
    s = seq.loc[seq["usable"], ["match_id", "server", "winner"]]
    s = s.assign(match_id=s["match_id"].astype(str))
    sa, sb = s["server"].eq(1), s["server"].eq(2)
    agg = pd.DataFrame({"svpt_a": sa, "svpt_b": sb, "spw_a": sa & s["winner"].eq(1),
                        "spw_b": sb & s["winner"].eq(2)}).groupby(s["match_id"]).sum()
    mp = match_players(idm, ["svpt", "first_won", "second_won", "has_box"])
    mp = mp[mp["has_box"].fillna(False).astype(bool)]
    a, b = mp[mp["side"].eq("A")].set_index("match_id"), mp[mp["side"].eq("B")].set_index("match_id")
    box = pd.DataFrame({"bsvpt_a": a["svpt"], "bsvpt_b": b["svpt"], "bspw_a": a["first_won"] + a["second_won"],
                        "bspw_b": b["first_won"] + b["second_won"]}).dropna()
    j = agg.join(box, how="inner")
    out = pd.DataFrame(index=j.index)
    out["box_svpt_diff"] = (j["svpt_a"] - j["bsvpt_a"]).abs() + (j["svpt_b"] - j["bsvpt_b"]).abs()
    out["box_spw_diff"] = (j["spw_a"] - j["bspw_a"]).abs() + (j["spw_b"] - j["bspw_b"]).abs()
    out["box_mirrored"] = (out["box_svpt_diff"] > 0) & (j["svpt_a"] == j["bsvpt_b"]) & (j["svpt_b"] == j["bsvpt_a"])
    ch = seqm[seqm["chosen"]].set_index("match_id")
    out["source"] = ch["source"].reindex(out.index)
    out["year"] = ch["year"].reindex(out.index)
    out["agrees_with_other"] = ch["agrees_with_other"].reindex(out.index).fillna(False).astype(bool)
    g = out.groupby("source")
    by_src = pd.DataFrame({"matches": g.size(), "svpt_exact": g["box_svpt_diff"].apply(lambda x: (x == 0).mean()),
                           "spw_exact": g["box_spw_diff"].apply(lambda x: (x == 0).mean()),
                           "svpt_within_2": g["box_svpt_diff"].apply(lambda x: (x <= 2).mean()),
                           "mirrored": g["box_mirrored"].sum()})
    by_sy = out.groupby(["source", "year"])["box_svpt_diff"].agg(lambda x: round(float((x == 0).mean()), 4))
    mir = out[out["box_mirrored"]]
    tid = mir.index.str.split("|").str[1]
    allt = out.index.str.split("|").str[1]
    clusters = []
    for t, n in tid.value_counts().head(10).items():
        clusters.append({"tournament_id": t, "mirrored": int(n), "checked_in_event": int((allt == t).sum()),
                         "mirrored_agreeing_with_another_source": int(mir[tid == t]["agrees_with_other"].sum())})
    summary = {"matches_checked": int(len(out)),
               "serve_points_exact": float((out["box_svpt_diff"] == 0).mean()),
               "serve_points_won_exact": float((out["box_spw_diff"] == 0).mean()),
               "serve_points_within_2": float((out["box_svpt_diff"] <= 2).mean()),
               "mirrored": int(out["box_mirrored"].sum()),
               "mirrored_agreeing_with_another_source": int(mir["agrees_with_other"].sum()),
               "mirrored_clusters": clusters,
               "by_source": by_src.round(4).reset_index().to_dict("records"),
               "svpt_exact_by_source_year": {f"{s}|{int(y)}": v for (s, y), v in by_sy.items() if pd.notna(y)}}
    return out[["box_svpt_diff", "box_spw_diff", "box_mirrored"]], summary


@timed("coverage")
def coverage(seqm: pd.DataFrame, view: pd.DataFrame, idm: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    from src.eda.predictability_diagnostic import common as PD
    ch = seqm[seqm["chosen"]].set_index("match_id")
    mp = match_players(idm)
    order = view[["match_id", "tournament_date", "tournament_id", "round_order", "tour", "year", "map_level"]]
    mp = mp.merge(order, on="match_id", how="left")
    usable = ch["usable"].reindex(mp["match_id"]).fillna(False).astype(bool).to_numpy()
    strict = ch["strict"].reindex(mp["match_id"]).fillna(False).astype(bool).to_numpy()
    complete = ch["status"].reindex(mp["match_id"]).eq("complete").to_numpy(dtype=bool) & usable
    n_games = ch["n_games"].reindex(mp["match_id"]).fillna(0).to_numpy()
    games = np.where(usable, n_games, 0)
    games_strict = np.where(strict, n_games, 0)
    points = np.where(usable, ch["stop"].reindex(mp["match_id"]).fillna(0).to_numpy(), 0)
    tmp = mp[["player_id", "tournament_date", "tournament_id", "round_order"]].copy()
    tmp["_m"], tmp["_c"], tmp["_g"], tmp["_p"] = usable.astype(float), complete.astype(float), games, points
    tmp["_s"], tmp["_sg"] = strict.astype(float), games_strict
    prev = PD.asof_sums(tmp, ["_m", "_c", "_g", "_p", "_s", "_sg"])
    mp["prev_matches"], mp["prev_complete"] = prev["_m"].to_numpy(), prev["_c"].to_numpy()
    mp["prev_games"], mp["prev_points"] = prev["_g"].to_numpy(), prev["_p"].to_numpy()
    mp["prev_strict"], mp["prev_games_strict"] = prev["_s"].to_numpy(), prev["_sg"].to_numpy()
    mp["own"] = usable
    mp["own_complete"] = complete
    mp["own_strict"] = strict
    per_match = mp.groupby("match_id").agg(own=("own", "max"), own_complete=("own_complete", "max"),
                                           own_strict=("own_strict", "max"), min_prev=("prev_matches", "min"),
                                           min_prev_strict=("prev_strict", "min"))

    def summarise(rows: pd.DataFrame, by: list[str]) -> pd.DataFrame:
        """rows: one per match (match_id + the grouping columns); per group, the match shares and the depth of its
        players' history (each player-match row counted once)."""
        rows = rows.drop_duplicates("match_id")
        pm = rows.join(per_match, on="match_id")
        for k in (5, 10, 20):
            pm[f"ge{k}"] = pm["min_prev"] >= k
            pm[f"ge{k}s"] = pm["min_prev_strict"] >= k
        a = pm.groupby(by, dropna=False).agg(matches=("match_id", "size"), own_sequence=("own", "mean"),
                                             own_complete=("own_complete", "mean"), both_ge5=("ge5", "mean"),
                                             both_ge10=("ge10", "mean"), both_ge20=("ge20", "mean"),
                                             own_strict=("own_strict", "mean"), both_ge5_strict=("ge5s", "mean"),
                                             both_ge10_strict=("ge10s", "mean"), both_ge20_strict=("ge20s", "mean"))
        pr = mp[["match_id", "prev_matches", "prev_complete", "prev_games", "prev_points", "prev_strict",
                 "prev_games_strict"]].merge(rows[["match_id"] + by], on="match_id")
        pr["none"] = pr["prev_matches"] == 0
        g = pr.groupby(by, dropna=False)
        b = pd.DataFrame({"player_rows": g.size(),
                          "median_prev_matches": g["prev_matches"].median(),
                          "p25_prev_matches": g["prev_matches"].quantile(0.25),
                          "median_prev_complete": g["prev_complete"].median(),
                          "median_prev_games": g["prev_games"].median(),
                          "p25_prev_games": g["prev_games"].quantile(0.25),
                          "median_prev_points": g["prev_points"].median(),
                          "players_with_no_prev": g["none"].mean(),
                          "median_prev_matches_strict": g["prev_strict"].median(),
                          "median_prev_games_strict": g["prev_games_strict"].median()})
        return a.join(b).reset_index()

    mf = pd.read_parquet(MODEL_FRAME, columns=["match_id", "tour", "season"])
    base = pd.read_parquet(C.BASE_FRAME, columns=["match_id"])
    info = {"model_frame": C.rel(MODEL_FRAME), "model_frame_matches": int(len(mf)),
            "model_frame_ids_equal_base_frame_ids": bool(set(mf["match_id"]) == set(base["match_id"])),
            "model_frame_ids_in_stage0_view": int(mf["match_id"].isin(set(view["match_id"])).sum())}
    cov_m = summarise(mf.rename(columns={"season": "year"}), ["tour", "year"])
    tot = summarise(mf.rename(columns={"season": "year"}).assign(all="all"), ["tour", "all"]).rename(
        columns={"all": "year"})
    cov_m = pd.concat([cov_m, tot], ignore_index=True)
    s0 = view[["match_id", "tour", "map_level", "year"]].rename(columns={"map_level": "level"})
    cov_s = summarise(s0, ["tour", "level", "year"])
    return cov_m, cov_s, info


# ------------------------------------------------------------------------------------------------
# main

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", default="", help="adapters to rerun: all, or a comma list of new sources")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()
    workers = max(1, min(6, args.workers))
    refresh = {x for x in args.refresh.split(",") if x}
    t_start = time.time()
    C.OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    audits = run_adapters(refresh, workers)
    idm = id_map()
    view = stage0_view(idm)
    links = link_new(idm)

    frames = []
    for src in C.EXISTING + C.NEW:
        frames.append(replay_source(src, view, workers))
    seqm = pd.concat(frames, ignore_index=True)
    seqm = score_check(seqm, view)

    # within a source, the best record per Stage 0 match competes for the choice
    pre_tier = tiers(seqm.assign(n_other_sources=0, agrees_with_other=False))
    seqm["_pre"] = pre_tier
    seqm["_rank"] = seqm["source"].map(C.RANK)
    seqm = seqm.sort_values(["_pre", "_rank", "n_points"], ascending=[True, True, False], kind="mergesort")
    linked = seqm["match_id"].notna() & seqm["a1"].notna()
    seqm["primary_in_source"] = linked & ~seqm.duplicated(["source", "match_id"]) | (~linked)
    seqm["dup_within_source"] = linked & seqm.duplicated(["source", "match_id"], keep=False)

    agree_tab, per = agreement(seqm)
    agrees = per.groupby(["source", "match_id"])["agree"].any()
    others = seqm[seqm["primary_in_source"] & linked].groupby("match_id")["source"].nunique() - 1
    seqm["n_other_sources"] = seqm["match_id"].map(others).fillna(0).astype(int)
    seqm["agrees_with_other"] = [agrees.get((s, m), False) if isinstance(m, str) else False
                                 for s, m in zip(seqm["source"], seqm["match_id"])]
    seqm["tier"] = tiers(seqm)
    sc = seqm["score_check"]
    seqm["partial_kind"] = np.select([seqm["status"].eq("partial") & sc.eq("exact"),
                                      seqm["status"].eq("partial") & sc.eq("prefix_of_official"),
                                      seqm["status"].eq("partial")], ["retired", "truncated", "other"], "")
    seqm = seqm.sort_values(["tier", "_rank", "n_points"], ascending=[True, True, False], kind="mergesort")
    cand = seqm["primary_in_source"] & linked & ~seqm["source"].isin(list(C.DEFECTIVE))
    seqm["chosen"] = cand & ~seqm["match_id"].where(cand).duplicated()
    seqm.loc[~cand, "chosen"] = False
    seqm["usable"] = seqm["tier"].le(2).fillna(False).astype(bool)
    seqm = seqm.drop(columns=["_pre", "_rank"]).sort_values(["source", "key"]).reset_index(drop=True)
    wfeeds = wta_feeds(seqm, per)

    seq = write_sequences(seqm)
    C.log(f"wrote sequences.parquet ({len(seq):,} points, {seq['match_id'].nunique():,} matches)")
    box, box_summary = box_check(seq, seqm, idm)
    ch_ids = seqm["match_id"].where(seqm["chosen"])
    for c in box.columns:
        seqm[c] = ch_ids.map(box[c])
    box_bad = seqm["box_svpt_diff"].gt(0) & ~(seqm["box_mirrored"].fillna(False).astype(bool) &
                                              seqm["agrees_with_other"].astype(bool))
    seqm["strict"] = seqm["usable"] & ~box_bad

    keep_first = ["source", "key", "match_id", "a1", "link_mapped", "a1_flipped", "linked_by", "tour", "year", "d",
                  "name1", "name2", "round", "draw", "level", "status", "partial_kind", "issues", "replay", "rule",
                  "rule_primary",
                  "rules_tried", "n_points", "stop", "n_games", "n_sets_done", "n_tb_points", "n_unknown", "sets_p1",
                  "replay_winner", "cur_games", "cur_points", "label_mismatch", "set_label_mismatch",
                  "field_conflicts", "s0",
                  "server_agree", "has_time", "score_check", "official_score", "official_status",
                  "dup_within_source", "primary_in_source", "n_other_sources", "agrees_with_other", "tier", "usable",
                  "chosen", "box_svpt_diff", "box_spw_diff", "box_mirrored", "strict", "src_winner", "src_score",
                  "src_status", "sets_json"]
    out = seqm[[c for c in keep_first if c in seqm] + [c for c in seqm.columns if c not in keep_first and c in
                                                        ("event_id", "scrape", "tname", "slam", "best_of_hint",
                                                         "server_field_agree", "tb_trailing_dropped", "log",
                                                         "unknown_winners", "tb_last_point_filled", "copy",
                                                         "parse_note", "start_utc", "MatchTimeStamp")]].copy()
    out["d"] = pd.to_datetime(out["d"], errors="coerce")
    out["year"] = pd.to_numeric(out["year"], errors="coerce").astype("Int64")
    out["a1"] = out["a1"].astype("boolean")
    flags = ["link_mapped", "a1_flipped", "rule_primary", "has_time", "dup_within_source", "primary_in_source",
             "agrees_with_other", "usable", "chosen", "strict"]
    out["box_mirrored"] = out["box_mirrored"].astype("boolean")
    for c in flags:
        out[c] = out[c].fillna(False).astype(bool)
    for c in out.columns:
        if out[c].dtype == object and c not in flags + ["a1"]:
            out[c] = out[c].map(lambda v: None if v is None or (isinstance(v, float) and np.isnan(v)) else str(v))
    out.to_parquet(C.OUT / "seq_matches.parquet", index=False)
    agree_tab.to_csv(C.OUT / "agreement.csv", index=False)
    C.log(f"wrote seq_matches.parquet ({len(out):,} rows) and agreement.csv ({len(agree_tab)} pairs)")

    # the WTA umpire logs' non-point records, with links
    ev = pd.read_parquet(CACHE / "wta_events_raw.parquet")
    wm = seqm[seqm["source"].eq("wta")][["key", "match_id", "a1"]]
    ev = ev.merge(wm, on="key", how="left")
    mt = pd.read_parquet(C.OUT / "matches_wta.parquet", columns=["key", "PlayerIDA", "PlayerIDB"])
    ev = ev.merge(mt, on="key", how="left")
    side = np.select([ev["player"].astype(str).eq(ev["PlayerIDA"].astype(str)),
                      ev["player"].astype(str).eq(ev["PlayerIDB"].astype(str))], [1, 2], 0)
    ev["player_side"] = side.astype("int8")
    a1 = ev["a1"].astype("boolean")
    ev["player_side_ab"] = np.where(side == 0, 0, np.where(a1.fillna(True).to_numpy(dtype=bool), side, 3 - side)).astype("int8")
    ev.loc[a1.isna().to_numpy(), "player_side_ab"] = 0
    ev = ev.drop(columns=["PlayerIDA", "PlayerIDB"])
    ev["a1"] = a1
    for c in ("index",):
        ev[c] = pd.to_numeric(ev[c], errors="coerce").astype("Int64")
    ev.to_parquet(C.OUT / "wta_events.parquet", index=False)
    C.log(f"wrote wta_events.parquet ({len(ev):,} records)")

    cov_m, cov_s, cov_info = coverage(seqm, view, idm)
    cov_m.to_csv(C.OUT / "coverage_model.csv", index=False)
    cov_s.to_csv(C.OUT / "coverage_stage0.csv", index=False)
    C.log("wrote coverage_model.csv and coverage_stage0.csv")

    summary = summarise_build(seqm, seq, agree_tab, audits, links, cov_m, cov_info, idm, ev)
    summary["wta_feeds"] = wfeeds
    summary["box_score_check"] = box_summary
    summary["strict_means"] = ("usable, and where Stage 0 has a box score, each player's serve points counted from the "
                               "sequence equal the box score's (a box score with the players' serve statistics the "
                               "other way round is accepted when another source agrees with the sequence)")
    summary["tiers"] = TIERS
    summary["defective_reused_tables"] = C.DEFECTIVE
    summary["timings_seconds"] = {**TIMINGS, "total": round(time.time() - t_start, 1)}
    C.write_json(C.OUT / "build_summary.json", summary)
    C.log("wrote build_summary.json")
    return 0


def summarise_build(seqm, seq, agree_tab, audits, links, cov_m, cov_info, idm, ev) -> dict:
    linked = seqm["match_id"].notna()
    by_src = {}
    for src, g in seqm.groupby("source"):
        gl = g[g["match_id"].notna()]
        by_src[src] = {
            "matches": int(len(g)), "points": int(g["n_points"].sum()),
            "linked": int(g["match_id"].notna().sum()), "oriented": int(g["a1"].notna().sum()),
            "status": g["status"].value_counts().to_dict(), "replay": g["replay"].value_counts().to_dict(),
            "issues": pd.Series([i for x in g["issues"] for i in str(x).split(";") if i]).value_counts().to_dict(),
            "rule_fallback_used": int((~g["rule_primary"].astype(bool)).sum()),
            "server_agree_median": float(g["server_agree"].median()),
            "server_agree_ge_98": float((g["server_agree"] >= 0.98).mean()),
            "score_check_linked": gl["score_check"].value_counts().to_dict(),
            "score_check_complete_linked": gl[gl["status"].eq("complete")]["score_check"].value_counts().to_dict(),
            "dup_within_source_rows": int(g["dup_within_source"].sum()),
            "partial_kind": g.loc[g["partial_kind"].ne(""), "partial_kind"].value_counts().to_dict(),
            "tiers_linked": {int(k): int(v) for k, v in g["tier"].dropna().value_counts().sort_index().items()},
            "chosen": int(g["chosen"].sum()),
            "chosen_usable": int((g["chosen"] & g["usable"]).sum()),
            "years": [int(g["year"].min()), int(g["year"].max())] if g["year"].notna().any() else None,
            "has_time": C.RAW_TIMES.get(src, "no time per point")}
    ch = seqm[seqm["chosen"]]
    inputs = [C.SHOT / "stage0_source_matches.parquet"] + [C.SHOT / f"stage1_points_{s}.parquet" for s in C.EXISTING] + \
        [C.RAW / "gap_sources" / "marcosjn2" / f for f in ("atp-matches.jsonl", "wta-matches.jsonl")] + \
        [C.DUMP / "points" / d / f for d in ("sofascore", "sofascore_editions", "sofascore_tournaments")
         for f in ("points.parquet", "events.parquet")] + \
        sorted((C.DUMP / "points" / "wta" / "events").glob("*.parquet")) + \
        sorted((C.DUMP / "points" / "wta" / "points").glob("*.parquet")) + \
        sorted((C.DUMP / "points" / "wta" / "matches").glob("*.parquet")) + \
        sorted((C.RAW / "point_shot_sources" / "pbp_copy_2015").glob("*.csv")) + \
        sorted((C.RAW / "point_shot_sources" / "pbp_copy_2018").glob("*.csv")) + \
        [S0 / "stage0_matches.parquet", S0 / "stage0_match_players.parquet", OLD_S0 / "stage0_matches.parquet",
         OLD_S0 / "stage0_match_players.parquet", ID_MAP, MODEL_FRAME, C.BASE_FRAME]
    return {
        "built_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
        "sources": by_src,
        "source_priority": C.PRIORITY,
        "linking": {"new_sources": links, "id_map": {"pairs": int(len(idm)), "side_flipped_pairs": int(idm["flip"].sum()),
                                                     "file": C.rel(ID_MAP)},
                    "links_needing_id_map_all_sources": int(seqm["link_mapped"].fillna(False).astype(bool).sum())},
        "adapter_audits": audits,
        "choice": {"stage0_matches_with_a_sequence": int(ch["match_id"].nunique()),
                   "usable": int(ch["usable"].sum()),
                   "by_source": ch.groupby("source").size().to_dict(),
                   "usable_by_source": ch[ch["usable"]].groupby("source").size().to_dict(),
                   "by_tier": {int(k): int(v) for k, v in ch["tier"].value_counts().sort_index().items()},
                   "matches_with_2plus_sources": int((ch["n_other_sources"] > 0).sum()),
                   "sequences_points": int(len(seq))},
        "agreement_pairs": agree_tab.to_dict("records"),
        "coverage_model_frame_all_years": cov_m[cov_m["year"].astype(str).eq("all")].to_dict("records"),
        "coverage_info": cov_info,
        "wta_events": {"records": int(len(ev)), "by_name": ev["name"].value_counts().to_dict(),
                       "linked_records": int(ev["match_id"].notna().sum())},
        "inputs": [C.file_sig(p) for p in inputs],
    }


if __name__ == "__main__":
    raise SystemExit(main())
