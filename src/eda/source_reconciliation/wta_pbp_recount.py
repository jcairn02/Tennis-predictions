"""Readers wta_pbp_recount and wta_events_tbfill_recount.

wta_pbp_recount: serve points, serve points won, service games and break points recounted from the WTA API's
point-by-point feed (batch B8: data/dump/points/wta/points/<year>.parquet, from mid-March 2022; none served October 2025
to March 2026, patchy in mid-2025 and September 2026). A second record of the same scoring system as the event log.

    * each point carries the game score after it in A/B order (0/15/30/40/A/G; tiebreak points as numbers, the last one
      included); its winner is read from the change of score, never from pointWinner (wrong on some points:
      official_point_feeds README). The server is the feed's (blank on tiebreak points, where it is the first server
      and then every two points the other player);
    * the points are replayed under WTA singles rules (wta_eventlog's state machine); a point whose score follows from
      neither winner is skipped and counted;
    * no serve number, aces or double faults: ace, df, first_in, first_won, second_won are NaN; sv_gms counts regular
      service games started (completed + the one in progress at a retirement), as wta_eventlog.counts;
    * complete: points numbered 1..n without gaps, no point skipped, a known winner for every point, and the replay's
      sets (tiebreak points included) equal Stage 0's score, finished for a completed match, unfinished for a
      retirement.

wta_events_tbfill_recount: the event-log recount (wta_events_recount.parquet, read back) with the winners of its
unwritten tiebreak points taken from the point-by-point feed, where the feed has the same tiebreak with the same number
of points and every winner, and the event log's known winners (aces, double faults) agree. first_won, second_won and
sv_won are then recomputed (the event log's serve numbers, the feed's winners); every other column is the event-log
recount's. Rows of matches with nothing to fill are copied unchanged (x_tb_filled False). Not independent of either
record: both come from the umpire's device.

Run (after wta_events_recount.py): ./python.sh src/eda/source_reconciliation/wta_pbp_recount.py
"""
from __future__ import annotations

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
from src.eda.source_reconciliation import wta_events_recount as ER  # noqa: E402

READER = "wta_pbp_recount"
FILL_READER = "wta_events_tbfill_recount"
YEARS = [2022, 2023, 2024, 2025, 2026]
P_COLS = ["tournament_id", "match_id", "match_status", "point_number", "set", "game", "server", "point_winner",
          "game_score_a", "game_score_b"]
LADDER_AB = ("0", "15", "30", "40")


def render_regular_ab(pa: int, pb: int, ended_by: str | None) -> tuple[str, str]:
    """The feed's game score after a point, A/B order."""
    if ended_by == "A":
        return "G", LADDER_AB[min(pb, 3)]
    if ended_by == "B":
        return LADDER_AB[min(pa, 3)], "G"
    if pa >= 3 and pb >= 3:
        return ("40", "40") if pa == pb else ("A", "40") if pa > pb else ("40", "A")
    return LADDER_AB[pa], LADDER_AB[pb]


def replay_pbp(points: list[tuple]) -> dict:
    """points: (number, server or "", score_a, score_b) in feed order. Returns the replay with per-point records."""
    st = E.St()
    pts, skipped, srv_mismatch = [], 0, 0
    tb_points: dict[int, list] = {}
    for num, server, sa, sb in points:
        if st.over:
            skipped += 1
            continue
        sa, sb = str(sa or "").strip().upper(), str(sb or "").strip().upper()
        if st.tb:
            exp = E.tb_server(st.srv, st.tbn)
            srv = exp
            fits = []
            for w in ("A", "B"):
                a = sum(1 for p in tb_points.get(len(st.sets), []) if p["win"] == "A") + (w == "A")
                b = sum(1 for p in tb_points.get(len(st.sets), []) if p["win"] == "B") + (w == "B")
                if (sa, sb) == (str(a), str(b)):
                    fits.append((w, a, b))
            if len(fits) != 1:
                skipped += 1
                continue
            w, a, b = fits[0]
            rec = {"srv": srv, "win": w, "tb": True, "bp": False, "set_no": len(st.sets) + 1, "num": num}
            tb_points.setdefault(len(st.sets), []).append(rec)
            pts.append(rec)
            if max(a, b) >= 7 and abs(a - b) >= 2:
                st = E.close_tiebreak(E.St(st.sets, st.ga, st.gb, 0, 0, st.srv, True, st.tbn + 1, False),
                                      "A" if a > b else "B", min(a, b))
            else:
                st = E.St(st.sets, st.ga, st.gb, 0, 0, st.srv, True, st.tbn + 1, False)
            continue
        srv = st.srv or (server if server in ("A", "B") else None)
        if srv is None:
            skipped += 1
            continue
        if server in ("A", "B") and server != srv:
            srv_mismatch += 1
        sp, rp = (st.pa, st.pb) if srv == "A" else (st.pb, st.pa)
        fits = []
        for w in ("A", "B"):
            pa, pb = st.pa + (w == "A"), st.pb + (w == "B")
            ended = ("A" if pa > pb else "B") if (pa >= 4 or pb >= 4) and abs(pa - pb) >= 2 else None
            if render_regular_ab(pa, pb, ended) == (sa, sb):
                fits.append((w, pa, pb, ended))
        if len(fits) != 1:
            skipped += 1
            continue
        w, pa, pb, ended = fits[0]
        pts.append({"srv": srv, "win": w, "tb": False, "bp": rp >= 3 and rp > sp, "set_no": len(st.sets) + 1,
                    "num": num, "ends_game": ended is not None})
        base = E.St(st.sets, st.ga, st.gb, st.pa, st.pb, srv, False, 0, False)
        st = E.end_game(base, ended) if ended else E.St(st.sets, st.ga, st.gb, pa, pb, srv, False, 0, False)
    return {"st": st, "pts": pts, "skipped": skipped, "srv_mismatch": srv_mismatch, "tb_points": tb_points}


def pbp_counts(res: dict) -> dict:
    out = {s: {"svpt": 0, "sv_won": 0, "sv_gms": 0, "bp_faced": 0, "bp_saved": 0} for s in ("A", "B")}
    for p in res["pts"]:
        c = out[p["srv"]]
        c["svpt"] += 1
        c["sv_won"] += p["win"] == p["srv"]
        if p.get("ends_game"):
            c["sv_gms"] += 1
        if p["bp"]:
            c["bp_faced"] += 1
            c["bp_saved"] += p["win"] == p["srv"]
    st = res["st"]
    # Sackmann's service games: the regular game in progress at a retirement counts too (see wta_eventlog.counts)
    if not st.over and not st.tb and (st.pa or st.pb) and st.srv in ("A", "B"):
        out[st.srv]["sv_gms"] += 1
    return out


def final_sets(st: E.St) -> list[tuple]:
    sets = [tuple(s) for s in st.sets]
    if not st.over and (st.ga or st.gb or st.pa or st.pb or st.tb):
        sets.append((st.ga, st.gb, None))
    return sets


def run() -> int:
    t0 = time.time()
    lst = WC.listing()
    lst_s = lst[lst["draw"].isin(["main_singles", "qual_singles"])].copy()
    s0m, s0p = WC.stage0_women()
    lk, info_link = WC.link(lst_s, s0m, s0p)
    rows, tb_by_key = [], {}
    per_year, forms = {}, {}
    for y in YEARS:
        path = WC.WTA / "points" / f"{y}.parquet"
        t = pq.read_table(path, columns=P_COLS).to_pandas()
        t = t[t["match_id"].str.startswith(("LS", "RS"))]
        t["num"] = pd.to_numeric(t["point_number"], errors="coerce")
        n = 0
        for (tid, mid), g in t.groupby(["tournament_id", "match_id"], sort=False):
            key = WC.wta_key(tid, y, mid)
            g = g.sort_values("num")
            nums = g["num"].tolist()
            whole = nums == list(range(1, len(nums) + 1))
            res = replay_pbp(list(zip(g["num"], g["server"].fillna(""), g["game_score_a"], g["game_score_b"])))
            cnt = pbp_counts(res)
            n += 1
            sets = final_sets(res["st"])
            base = {"source_key": key, "x_api_year": y, "x_points": len(res["pts"]), "x_rows": len(g),
                    "x_numbering_whole": whole, "x_skipped": res["skipped"], "x_server_mismatch": res["srv_mismatch"],
                    "x_over": res["st"].over, "x_match_status": g["match_status"].iloc[0],
                    "x_sets_api": " ".join(f"{a}-{b}" + (f"({t_})" if t_ is not None else "") for a, b, t_ in sets)}
            tb_by_key[key] = {sn: "".join(p["win"] for p in ps) for sn, ps in res["tb_points"].items()}
            for side in ("A", "B"):
                row = dict(base, x_api_side=side, _sets=sets)
                for f in C.FIELDS:
                    row[f] = cnt[side].get(f, np.nan)
                rows.append(row)
        per_year[y] = n
        WC.log(f"[{READER}] {y}: {n:,} singles documents, {time.time() - t0:.0f}s")
    rc = pd.DataFrame(rows)
    pl = WC.players_of(lk, s0p)
    out = pl.merge(rc.rename(columns={"x_api_side": "api_side"}), on=["source_key", "api_side"], how="inner")
    meta = lk[["source_key", "tier", "draw", "how", "x_winner_agrees", "x_ids_agree", "x_orient_one_name",
               "link_method", "level_group", "s0_year", "map_level", "status", "score", "a_won", "wta_a_is_s0"]]
    out = out.merge(meta, on="source_key", how="left")
    s0_winner_api = np.where(out["a_won"].astype(bool) == out["wta_a_is_s0"].eq("A"), "A", "B")
    eq, sets_w = [], []
    for sets, wside, score, status, over in zip(out["_sets"], s0_winner_api, out["score"], out["status"], out["x_over"]):
        mine = [(a, b, t_) if wside == "A" else (b, a, t_) for a, b, t_ in sets]
        theirs, _ = ER.s0_sets(score)
        ok = ER.sets_match(mine, theirs)
        ok = ok and (bool(over) if status == "completed" else (not bool(over)) if status == "retired" else False)
        eq.append(ok)
        sets_w.append(" ".join(f"{a}-{b}" + (f"({t_})" if t_ is not None else "") for a, b, t_ in mine))
    out["x_sets_recount"] = sets_w
    out["x_sets_equal_s0"] = eq
    out["complete"] = out["x_sets_equal_s0"] & out["x_numbering_whole"] & out["x_skipped"].eq(0)
    out = out.drop(columns=["_sets", "score", "a_won", "wta_a_is_s0"])
    out = out.rename(columns={"tier": "x_tier", "draw": "x_draw", "how": "x_how", "level_group": "x_level_group",
                              "s0_year": "x_s0_year", "map_level": "x_map_level", "status": "x_s0_status",
                              "api_side": "x_api_side", "s0_side": "x_s0_side", "won": "x_s0_won"})
    frame = WC.finish_reader(out, READER, "recount")
    done = frame.drop_duplicates("match_id")
    eq_c = WC.equality_with_stage0(frame, s0p, only=frame["complete"])
    eq_y = WC.equality_with_stage0(frame, s0p, by=["x_s0_year"], only=frame["complete"])
    summary = {
        "source": "WTA API point-by-point (batch B8), data/dump/points/wta/points/<year>.parquet, 2022-2026",
        "records_read": {"singles_documents_by_year": per_year, "recounted": int(rc["source_key"].nunique())},
        "link": info_link,
        "linked_recounts": int(frame["source_key"].nunique()),
        "dropped": {"recounted_but_not_linked_to_stage0": int(rc["source_key"].nunique() - frame["source_key"].nunique())},
        "complete": {"matches": int(done["complete"].sum()), "of": int(len(done)),
                     "why_not": {"numbering_not_whole": int((~done["x_numbering_whole"]).sum()),
                                 "points_skipped": int((done["x_skipped"] > 0).sum()),
                                 "sets_differ_from_stage0": int((~done["x_sets_equal_s0"]).sum())}},
        "server_field_disagrees_with_rotation_matches": int((done["x_server_mismatch"] > 0).sum()),
        "by_level_group_complete": done.groupby("x_level_group")["complete"].agg(["sum", "size"]).astype(int)
                                       .rename(columns={"sum": "complete", "size": "linked"}).to_dict("index"),
        "by_s0_year_complete": done.groupby("x_s0_year")["complete"].agg(["sum", "size"]).astype(int)
                                   .rename(columns={"sum": "complete", "size": "linked"}).to_dict("index"),
        "sanity_equality_with_stage0_complete_rows": WC.agreement_records(eq_c),
        "sanity_equality_with_stage0_complete_rows_by_year": WC.agreement_records(eq_y),
        "hand_checks": "see wta_handcheck.json",
        "seconds": round(time.time() - t0, 1),
    }
    WC.write_reader(frame, READER, summary)
    tbfill(tb_by_key, frame, s0p)
    return 0


def tbfill(tb_by_key: dict, pbp_frame: pd.DataFrame, s0p: pd.DataFrame) -> None:
    """The event-log recount with its unwritten tiebreak winners from the point-by-point feed."""
    ev = pd.read_parquet(WC.READERS / "wta_events_recount.parquet")
    ev = ev.copy()
    ev["reader"] = FILL_READER
    ev["x_tb_filled"] = False
    ev["x_tb_fill_reason"] = np.where(ev["x_tb_unwritten"] > 0, "", "nothing to fill")
    reasons = {}
    for key, g in ev[ev["x_tb_unwritten"] > 0].groupby("source_key"):
        tbs = str(g["x_tb_detail"].iloc[0] or "")
        feed = tb_by_key.get(key)
        why = None
        if feed is None:
            why = "no point-by-point document"
        elif not bool(g["x_serve_number_recorded"].iloc[0]):
            why = "serve numbers not recorded"
        add = {"A": [0, 0, 0], "B": [0, 0, 0]}   # first_won, second_won, sv_won from the tiebreaks
        if why is None:
            for part in tbs.split(";"):
                if not part:
                    continue
                set_no, srvs, serve_no, kinds, wins = part.split("|")
                fw = feed.get(int(set_no) - 1)
                if fw is None or len(fw) != len(srvs):
                    why = "feed tiebreak missing or of another length"
                    break
                if any(w != "?" and w != f for w, f in zip(wins, fw)):
                    why = "feed winners contradict the log's aces or double faults"
                    break
                for s, n_, f, w in zip(srvs, serve_no, fw, wins):
                    if w == "?" and f == s:     # points of known winner (aces, double faults) are counted already
                        add[s][2] += 1
                        add[s][0 if n_ == "1" else 1] += 1
        if why is not None:
            reasons[why] = reasons.get(why, 0) + 1
            ev.loc[g.index, "x_tb_fill_reason"] = why
            continue
        reasons["filled"] = reasons.get("filled", 0) + 1
        for i in g.index:
            s = ev.at[i, "x_api_side"]
            ev.at[i, "first_won"] = ev.at[i, "x_first_won_known"] + add[s][0]
            ev.at[i, "second_won"] = ev.at[i, "x_second_won_known"] + add[s][1]
            ev.at[i, "sv_won"] = ev.at[i, "x_sv_won_known"] + add[s][2]
            ev.at[i, "x_tb_filled"] = True
            ev.at[i, "x_tb_fill_reason"] = "filled"
    frame = WC.finish_reader(ev.drop(columns=["reader", "family", "kind"]), FILL_READER, "recount")
    filled = frame[frame["x_tb_filled"]]
    eq_f = WC.equality_with_stage0(frame, s0p, only=frame["complete"] & frame["x_tb_filled"])
    summary = {
        "source": "wta_events_recount.parquet with unwritten tiebreak winners from the WTA point-by-point feed (B8)",
        "rule": "fill only when the feed's tiebreak in the same set has the same number of points and the log's known "
                "winners (aces, double faults) agree; the event log's servers and serve numbers are kept",
        "matches_with_unwritten_tiebreaks": int(ev.loc[ev["x_tb_unwritten"] > 0, "match_id"].nunique()),
        "fill_outcomes_matches": reasons,
        "filled_matches": int(filled["match_id"].nunique()),
        "filled_complete_matches": int(filled.loc[filled["complete"], "match_id"].nunique()),
        "sanity_equality_with_stage0_filled_complete_rows": WC.agreement_records(eq_f),
        "independence": "not independent of the event log or of the point-by-point feed: both are the umpire device's",
        "hand_checks": "see wta_handcheck.json",
    }
    WC.write_reader(frame, FILL_READER, summary)


if __name__ == "__main__":
    sys.exit(run())
