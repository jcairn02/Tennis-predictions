"""Reader wta_events_recount: the nine counts recounted from the chair umpire's event log (batches B1/B2), on Stage
0's ids. The replay itself is wta_eventlog.py (its docstring gives the log's vocabulary and every reading rule).

Input: data/dump/points/wta/events/<year>.parquet (2019-2026; singles: match ids LS... and RS...), the match lists
(players A/B and their ids), the frozen Stage 0 and the frozen wta_api link file (wta_common.link, which orients the
API's sides on Stage 0's players by name).

Not recounted: the "bare" logs of April-May 2019 (Point/Ace/Fault records without server, score or serve number; 662
logs in every draw, 513 of them singles) and empty logs. They are counted in the JSON.

Definitions (Sackmann's, as the brief asks; how each was settled is in box/REPORT_wta.md):
    * first serves: a point is a second-serve point when a first-serve fault record stands before it (wta_eventlog
      .first_serve_in, rule "faults"); the device's own first_serve flag on the point is kept as x_first_in_flag /
      x_first_won_flag. The rule was chosen on 2024 after comparing both readings with the API's box;
    * logs that record no serve numbers (no first-serve fault at all, or most double faults with no fault before them:
      Brisbane, Canberra, Auckland 2024 and a few others): first_in, first_won, second_won NaN, x_serve_number_recorded
      False;
    * sv_gms: regular service games started (completed + the one in progress at a retirement; tiebreaks not counted).
      x_sv_gms_completed keeps the completed ones only.

complete (per match, both rows): the replay followed every record (no record skipped, no resynchronisation, every
InProgress after a correction matched, every tiebreak closed and its points' number equal to its score) and the
recount's set scores, tiebreak points included, equal Stage 0's score (oriented by names), with the match finished for
a completed match and unfinished for a retirement. Records after the match's last point (x_after_end, a tail some logs
carry) are not counted and do not make a match incomplete. first_won, second_won and sv_won are NaN when any point's
winner is unknown (unwritten tiebreak points: from 2022 nearly every tiebreak); the other counts stay, and
wta_events_tbfill_recount fills them from the point-by-point feed where it can.

Extra columns (x_): the replay's diagnostics (records, points, corrections, edits and rewinds, points removed, skips,
resyncs, ...), the recount's sets (winner first, as Stage 0 writes them) and whether they equal Stage 0's and the
listing's, tiebreaks and unwritten tiebreaks, each tiebreak's points (x_tb_detail), per player the points of unknown
winner, the partial sums over points of known winner (x_*_known), serve points and first serves in per set, an
unfinished service game at the end, tiebreaks served first, first-serve fault records and points re-entered during an
edit; the listing's tier, draw and year, Stage 0's level group, season and status.

Run: ./python.sh src/eda/source_reconciliation/wta_events_recount.py [--years 2019-2026]
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.source_reconciliation import common as C  # noqa: E402
from src.eda.source_reconciliation import wta_common as WC  # noqa: E402
from src.eda.source_reconciliation import wta_eventlog as E  # noqa: E402

READER = "wta_events_recount"
EV_COLS = ["tournament_id", "match_id", "index", "name", "type", "reason", "first_serve", "score", "server",
           "game_score", "match_score", "match_state"]
SET_TOKEN = re.compile(r"^(\d+)-(\d+)(?:\((\d+)\))?$")
FLAG_KEYS = ["skipped", "resynced", "rewinds", "rewound_points", "inprogress_rewinds", "inprogress_unmatched",
             "foot_ignored", "after_end", "server_unknown", "tb_unresolved", "tb_count_mismatch", "max_rewind",
             "episodes", "episode_rewinds", "episode_fallback", "edit_self_undo", "inprogress_rewinds_nocorr",
             "episode_commit_failed"]
BREAKING = ["skipped", "resynced", "inprogress_unmatched", "server_unknown", "tb_unresolved",
            "tb_count_mismatch"]


def s0_sets(score: str) -> tuple[list[tuple], str]:
    """Stage 0's score as [(winner's games, loser's games, loser's tiebreak points)] and its flag (RET, W/O ...)."""
    sets, flags = [], []
    for tok in str(score or "").split():
        m = SET_TOKEN.match(tok)
        if m:
            sets.append((int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None))
        else:
            flags.append(tok)
    return sets, " ".join(flags)


def recount_match(g: pd.DataFrame, side_of: dict) -> dict | None:
    g = g.sort_values("idx_num")
    recs, ff, edit = [], {"A": 0, "B": 0}, {"A": 0, "B": 0}
    scoring_named = 0
    attributed = 0
    corrections = 0
    for pos, row in enumerate(g.itertuples(index=False)):
        typ = row.type if isinstance(row.type, str) and row.type else row.name
        kind = E.record_kind(typ, row.reason, row.first_serve)
        if kind is None:
            continue
        side = side_of.get(str(row.server)) if isinstance(row.server, str) and row.server else None
        if kind in ("ace", "point", "df", "foot_df", "ff"):
            scoring_named += 1
            if side is not None or (isinstance(row.score, str) and row.score):
                attributed += 1
        if kind == "corr":
            corrections += 1
        if kind == "ff" and side:
            ff[side] += 1
        recs.append(E.Rec(pos=pos, index=int(row.idx_num), kind=kind, side=side,
                          first_serve=str(row.first_serve).upper() == "TRUE", score=E._txt(row.score),
                          game_score=E._txt(row.game_score), match_score=E._txt(row.match_score),
                          state=str(row.match_state or "")))
    if scoring_named == 0:
        return {"form": "empty"}
    if attributed == 0:
        return {"form": "bare"}
    rp = E.replay(recs)
    recorded = E.serve_number_recorded(rp, ff["A"] + ff["B"])
    cnt = E.counts(rp, "faults", recorded)
    pos_state = {r.pos: r.state for r in recs}
    for p in rp.pts:
        if pos_state.get(p.rec_pos) == "E":
            edit[p.srv] += 1
    return {"form": "full", "rp": rp, "counts": cnt, "ff": ff, "edit": edit, "corrections": corrections,
            "records": len(g), "sets": E.final_sets(rp), "over": rp.st.over, "serve_recorded": recorded}


def listing_sets(row) -> list[tuple]:
    out = []
    for k in range(1, 6):
        a, b = row.get(f"ScoreSet{k}A"), row.get(f"ScoreSet{k}B")
        if not (str(a).strip().isdigit() and str(b).strip().isdigit()):
            break
        tb = row.get(f"ScoreTbSet{k}") if k <= 4 else None
        tb = int(tb) if str(tb or "").strip().isdigit() else None
        out.append((int(a), int(b), tb))
    while out and out[-1][:2] == (0, 0):
        out.pop()
    return out


def sets_match(mine: list[tuple], theirs: list[tuple]) -> bool:
    """Set scores equal, both in the same orientation; tiebreak loser points compared where both give them; a trailing
    0-0 set (a retirement before a set began; Stage 0 writes "7-6(0) 0-0 RET") is dropped on both sides."""
    mine, theirs = list(mine), list(theirs)
    while mine and mine[-1][:2] == (0, 0):
        mine.pop()
    while theirs and theirs[-1][:2] == (0, 0):
        theirs.pop()
    if not mine or len(mine) != len(theirs):
        return False
    for m, t in zip(mine, theirs):
        if (m[0], m[1]) != (t[0], t[1]):
            return False
        if m[2] is not None and t[2] is not None and m[2] != t[2]:
            return False
    return True


def run(years: list[int]) -> int:
    t0 = time.time()
    lst = WC.listing()
    lst_s = lst[lst["draw"].isin(["main_singles", "qual_singles"])].copy()
    s0m, s0p = WC.stage0_women()
    lk, info_link = WC.link(lst_s, s0m, s0p)
    lk_by_key = lk.set_index("source_key")
    lst_by_key = lst_s.set_index("source_key")
    rows = []
    forms = {}
    per_year = {}
    for y in years:
        ev = pq.read_table(WC.WTA / "events" / f"{y}.parquet", columns=EV_COLS).to_pandas()
        ev = ev[ev["match_id"].str.startswith(("LS", "RS"))]
        ev["idx_num"] = pd.to_numeric(ev["index"], errors="coerce")
        ev = ev.drop(columns=["index"])
        n_matches = 0
        for (tid, mid), g in ev.groupby(["tournament_id", "match_id"], sort=False):
            key = WC.wta_key(tid, y, mid)
            if key not in lst_by_key.index:
                forms["not_in_listing"] = forms.get("not_in_listing", 0) + 1
                continue
            li = lst_by_key.loc[key]
            side_of = {str(li["PlayerIDA"]): "A", str(li["PlayerIDB"]): "B"}
            res = recount_match(g, side_of)
            n_matches += 1
            forms[res["form"]] = forms.get(res["form"], 0) + 1
            if res["form"] != "full":
                continue
            rp, cnt = res["rp"], res["counts"]
            flags = rp.flags
            unwritten = sum(1 for t in rp.tb_results if not t["winners_known"])
            base = {"source_key": key, "x_api_year": y, "x_records": res["records"], "x_points": len(rp.pts),
                    "x_corrections": res["corrections"], "x_tiebreaks": len(rp.tb_results),
                    "x_tb_unwritten": unwritten, "x_over": bool(res["over"]),
                    "x_serve_number_recorded": bool(res["serve_recorded"]),
                    "x_tb_detail": E.tb_detail(rp),
                    "x_sets_api": " ".join(f"{a}-{b}" + (f"({t})" if t is not None else "") for a, b, t in res["sets"]),
                    "x_listing_reproduced": sets_match(res["sets"], listing_sets(li))}
            for k in FLAG_KEYS:
                base[f"x_{k}"] = int(flags.get(k, 0))
            base["x_breaks_chain"] = any(flags[k] for k in BREAKING)
            for side in ("A", "B"):
                c = cnt[side]
                row = dict(base)
                row["x_api_side"] = side
                for f in C.FIELDS:
                    row[f] = c[f]
                row["x_first_won_known"] = c["x_first_won_known"]
                row["x_second_won_known"] = c["x_second_won_known"]
                row["x_sv_won_known"] = c["x_sv_won_known"]
                row["x_first_in_flag"] = c["x_first_in_flag"]
                row["x_first_won_flag"] = c["x_first_won_flag"]
                row["x_unknown_winner_points"] = c["x_unknown_winner_points"]
                row["x_sv_gms_unfinished"] = c["x_sv_gms_unfinished"]
                row["x_sv_gms_completed"] = c["x_sv_gms_completed"]
                row["x_tb_served_first"] = c["x_tb_served_first"]
                nsets = max((p.set_no for p in rp.pts), default=0)
                row["x_svpt_sets"] = ",".join(str(sum(1 for p in rp.pts if p.srv == side and p.set_no == k))
                                              for k in range(1, nsets + 1))
                row["x_first_in_sets"] = ",".join(str(sum(1 for p in rp.pts if p.srv == side and p.set_no == k
                                                          and E.first_serve_in(p))) for k in range(1, nsets + 1))
                row["x_first_serve_fault_records"] = res["ff"][side]
                row["x_edit_points"] = res["edit"][side]
                row["_sets"] = res["sets"]
                rows.append(row)
        per_year[y] = n_matches
        C_log = f"[{READER}] {y}: {n_matches:,} singles logs read, {time.time() - t0:.0f}s"
        WC.log(C_log)
    rc = pd.DataFrame(rows)
    # link and orient
    pl = WC.players_of(lk, s0p)
    out = pl.merge(rc.rename(columns={"x_api_side": "api_side"}), on=["source_key", "api_side"], how="inner")
    meta = lk[["source_key", "tier", "draw", "how", "x_winner_agrees", "x_ids_agree", "x_orient_one_name",
               "link_method", "level_group", "s0_year", "map_level", "status", "score", "a_won", "wta_a_is_s0"]]
    out = out.merge(meta, on="source_key", how="left")
    # the recount's sets in Stage 0's orientation, winner first, against Stage 0's score
    s0_winner_api = np.where(out["a_won"].astype(bool) == out["wta_a_is_s0"].eq("A"), "A", "B")
    sets_w, eq = [], []
    for sets, wside, score, status, over in zip(out["_sets"], s0_winner_api, out["score"], out["status"], out["x_over"]):
        mine = [(a, b, t) if wside == "A" else (b, a, t) for a, b, t in sets]
        theirs, _ = s0_sets(score)
        ok = sets_match(mine, theirs)
        if status == "completed":
            ok = ok and bool(over)
        elif status == "retired":
            ok = ok and not bool(over)
        else:
            ok = False
        sets_w.append(" ".join(f"{a}-{b}" + (f"({t})" if t is not None else "") for a, b, t in mine))
        eq.append(ok)
    out["x_sets_recount"] = sets_w
    out["x_sets_equal_s0"] = eq
    out["complete"] = out["x_sets_equal_s0"] & ~out["x_breaks_chain"]
    # the recount's winner against Stage 0's won (completed matches; at a retirement the points do not say who won)
    out["x_recount_winner_is_player"] = [None if not over else
                                         bool(sum(1 for a, b, t in sets if (a > b) == (side == "A")) >
                                              sum(1 for a, b, t in sets if (a > b) != (side == "A")))
                                         for sets, side, over in zip(out["_sets"], out["api_side"], out["x_over"])]
    out = out.drop(columns=["_sets", "score", "a_won", "wta_a_is_s0"])
    out = out.rename(columns={"tier": "x_tier", "draw": "x_draw", "how": "x_how", "level_group": "x_level_group",
                              "s0_year": "x_s0_year", "map_level": "x_map_level", "status": "x_s0_status",
                              "api_side": "x_api_side", "s0_side": "x_s0_side", "won": "x_s0_won"})
    frame = WC.finish_reader(out, READER, "recount")
    linked = frame["source_key"].nunique()
    done = frame.drop_duplicates("match_id")
    wins = frame[frame["x_recount_winner_is_player"].notna()]
    eq_complete = WC.equality_with_stage0(frame, s0p, only=frame["complete"])
    eq_year = WC.equality_with_stage0(frame, s0p, by=["x_s0_year"], only=frame["complete"])
    summary = {
        "source": "WTA chair umpire's event log (events endpoint), batches B1 (2020-2026) and B2 (2019); "
                  "data/dump/points/wta/events/<year>.parquet; replayed by wta_eventlog.py",
        "records_read": {"singles_logs_by_year": per_year, "log_forms": forms,
                         "recounted_full_logs": int(rc["source_key"].nunique()) if len(rc) else 0},
        "link": info_link,
        "linked_recounts": int(linked),
        "dropped": {"bare_logs_april_may_2019 (no server, score or serve number)": forms.get("bare", 0),
                    "empty_logs": forms.get("empty", 0),
                    "recounted_but_not_linked_to_stage0": int(rc["source_key"].nunique() - linked) if len(rc) else 0},
        "complete": {"matches": int(done["complete"].sum()), "of": int(len(done)),
                     "why_not": {
                         "replay_chain_broken": int(done["x_breaks_chain"].sum()),
                         "sets_differ_from_stage0_only": int((~done["x_sets_equal_s0"] & ~done["x_breaks_chain"]).sum()),
                         **{f"flag_{k}": int((done[f"x_{k}"] > 0).sum()) for k in BREAKING}}},
        "listing_reproduced": {"matches": int(done["x_listing_reproduced"].sum()), "of": int(len(done))},
        "serve_numbers": {"rule": "faults (a first-serve fault record standing before the point; wta_eventlog."
                                  "first_serve_in); the device's flag reading is in x_first_in_flag",
                          "linked_logs_without_serve_numbers": int((~done["x_serve_number_recorded"]).sum())},
        "sv_gms_definition": "regular service games started: completed + the game in progress at a retirement "
                             "(x_sv_gms_completed: completed only); tiebreaks not counted",
        "after_end_records": {"matches_with_any": int((done["x_after_end"] > 0).sum()),
                              "note": "records after the match's last point; not counted, not breaking"},
        "unknown_winner_points": {"matches_with_any": int((done["x_tb_unwritten"] > 0).sum()),
                                  "note": "first_won, second_won, sv_won are NaN in these matches (unwritten "
                                          "tiebreaks); the other counts stay"},
        "edits": {"correction_edits_closed_by_an_inprogress": int(done["x_episodes"].sum()),
                  "of_them_resolved_as_a_whole": int(done["x_episodes"].sum() - done["x_episode_fallback"].sum()),
                  "fell_back_to_record_by_record": int(done["x_episode_fallback"].sum()),
                  "edits_that_undid_their_own_entries": int(done["x_edit_self_undo"].sum()),
                  "silent_undos_inprogress_without_correction": int(done["x_inprogress_rewinds_nocorr"].sum()),
                  "commit_failures": int(done["x_episode_commit_failed"].sum())},
        "corrections": {"matches_with_any": int((done["x_corrections"] > 0).sum()),
                        "matches_with_points_removed": int((done["x_rewound_points"] > 0).sum()),
                        "points_removed": int(done["x_rewound_points"].sum()),
                        "max_points_removed_in_one_rewind": int(done["x_max_rewind"].max())},
        "winner_check": {"completed_matches_rows": int(len(wins)),
                         "recount_winner_differs_from_stage0_won_rows":
                             int((wins["x_recount_winner_is_player"].astype(bool) != wins["x_s0_won"].astype(bool)).sum()),
                         "of_them_in_complete_matches":
                             int(((wins["x_recount_winner_is_player"].astype(bool) != wins["x_s0_won"].astype(bool))
                                  & wins["complete"]).sum())},
        "by_level_group_complete": done.groupby("x_level_group")["complete"].agg(["sum", "size"]).astype(int)
                                       .rename(columns={"sum": "complete", "size": "linked"}).to_dict("index"),
        "by_s0_year_complete": done.groupby("x_s0_year")["complete"].agg(["sum", "size"]).astype(int)
                                   .rename(columns={"sum": "complete", "size": "linked"}).to_dict("index"),
        "sanity_equality_with_stage0_complete_rows": WC.agreement_records(eq_complete),
        "sanity_equality_with_stage0_complete_rows_by_year": WC.agreement_records(eq_year),
        "hand_checks": "see wta_handcheck.json",
        "seconds": round(time.time() - t0, 1),
    }
    WC.write_reader(frame, READER, summary)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2019-2026")
    a = ap.parse_args()
    lo, _, hi = a.years.partition("-")
    years = list(range(int(lo), int(hi or lo) + 1))
    return run(years)


if __name__ == "__main__":
    sys.exit(main())
