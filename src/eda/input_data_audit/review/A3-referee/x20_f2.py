"""F2 (box scores exchanged between winner and loser): every one of the 88 matches refereed and simulated.

For each match of data/studies/input_data_audit/box_swapped_oct07.csv:
    * Stage 0's row (live, 7 Oct) and Sackmann's raw row (_source_file, _row);
    * every independent record of the same match found (WTA API, MCP, Sackmann's Slam point-by-point, US Open /
      Wimbledon official statistics, Sofascore, Tennislive, TDI, RG Infosys key statistics, ATP Infosys key
      statistics 2025) and Tennis My Life's copy; per player, exact agreement of the record with the box as
      recorded and as exchanged;
    * internal checks as recorded and exchanged: B0-B9 (replica and stage0_build.box_scores), the games identity
      on BOTH players, service games, points won, and the minimum-points rule (a player who won G games won at
      least 4G points, 7 per tiebreak);
    * B = difference of the two players' breaks conceded, D = difference of their service games: with B = 0 an
      exchange of the service games alone fits the identity as well as the whole exchange; with D = 0 an exchange
      of the break-point counts alone does;
    * progression: does the recorded winner (or loser) play a later round of the event.
Writes f2_matches.csv (88 rows: verdict, referee, reason) and f2_referee_rows.csv (every referee row used).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402
import refs  # noqa: E402

INDEPENDENT = ["wta_api", "mcp", "slam_pbp", "usopen", "wimbledon", "sofascore", "tennislive", "tdi", "infosys"]
SLAM_OF = {"Australian Open": "ausopen", "Roland Garros": "frenchopen", "Wimbledon": "wimbledon", "US Open": "usopen",
           "Us Open": "usopen"}


def agreement(ref_box: pd.Series, ours: pd.Series) -> tuple[int, int]:
    avail = [b for b in rc.BOX if pd.notna(ref_box.get(b)) and pd.notna(ours.get(b))]
    return sum(int(ref_box[b] == ours[b]) for b in avail), len(avail)


def compatible(c: pd.DataFrame, row: pd.Series) -> pd.Series:
    """Referee rows that can be this match: same Slam and year for the Slam feeds; the same WTA tournament number
    for the WTA API where Sackmann's id carries it; otherwise a date 10 days before to 25 days after the event."""
    yr, tname = int(row["year"]), str(row["tournament_name"])
    slam = SLAM_OF.get(tname)
    ok = pd.Series(True, index=c.index)
    for ref in ("slam_pbp", "usopen", "wimbledon", "infosys"):
        s = c["ref"].eq(ref)
        if not s.any():
            continue
        if not slam:
            ok[s] = False
            continue
        ev = c.loc[s, "event"].astype(str)
        if ref == "slam_pbp":
            good = (c.loc[s, "year"] == yr) & ev.str.startswith(slam)
        elif ref == "infosys":
            good = (c.loc[s, "year"] == yr) & ev.str.startswith("RG") & (slam == "frenchopen")
        else:
            good = (c.loc[s, "year"] == yr) & (slam == ref)
        ok[s] = good.to_numpy()
    s = c["ref"].eq("wta_api")
    if s.any():
        m = re.match(r"^\d{4}-(\d+)$", str(row["tournament_id"]))
        if m:
            ok[s] = (c.loc[s, "event"].astype(str).str.split("|").str[0] == m.group(1)) & (c.loc[s, "year"] == yr)
        else:
            ok[s] = (c.loc[s, "date"] - pd.Timestamp(row["tournament_date"])).dt.days.between(-10, 25)
    other = ~c["ref"].isin(["slam_pbp", "usopen", "wimbledon", "infosys", "wta_api"])
    td = pd.Timestamp(row["tournament_date"])
    ok[other] = (c.loc[other, "date"] - td).dt.days.between(-10, 25).fillna(False)
    return ok


def find_refs(R: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    wk, lk = rc.name_key(row["w_player_name"]), rc.name_key(row["l_player_name"])
    ws, ls = refs.surname(row["w_player_name"]), refs.surname(row["l_player_name"])
    yr = int(row["year"])
    near = R[(R["year"] - yr).abs() <= 1]
    full = near[((near["pk"] == wk) & (near["ok"] == lk)) | ((near["pk"] == lk) & (near["ok"] == wk))]
    full = full.assign(name_match="full", is_w=full["pk"].eq(wk))
    if not full.empty:
        full = full[compatible(full, row)]
    sur = near[((near["sn"] == ws) & (near["osn"] == ls)) | ((near["sn"] == ls) & (near["osn"] == ws))]
    sur = sur[~sur["ref"].isin(full["ref"])]       # a referee found by full names is not searched by surnames
    sur = sur.assign(name_match="surname", is_w=sur["sn"].eq(ws))
    if not sur.empty:
        sur = sur[compatible(sur, row)]
    return pd.concat([full, sur])


def atp_keystats_bergs_rublev() -> dict:
    """ATP Infosys key statistics (sirgenkii_infotennis), Miami 2025 ms047 Bergs d. Rublev: Bergs's row, as fractions."""
    k = rc.rd(rc.PTS / "sirgenkii_infotennis" / "atp_key_stats.parquet")
    x = k[(k["match_id"] == "ms047") & (k["tournament_id"].astype(str) == "403") & (k["set_n"].astype(str) == "0")]
    x = x[x["player_id"] == "BU13"].iloc[0]
    return {c: float(x[c]) for c in ["aces", "double_faults", "serve1", "serve1_pts_won", "serve2_pts_won",
                                     "break_points_saved", "break_points_faced", "service_games_played",
                                     "service_points_won", "total_points_won"]}


def main() -> int:
    sw = pd.read_csv(rc.AUD / "box_swapped_oct07.csv")
    m, p = rc.stage0()
    W = rc.wide(m[m["match_id"].isin(sw["match_id"])], p[p["match_id"].isin(sw["match_id"])])
    W = W.set_index("match_id").loc[sw["match_id"]].reset_index()
    print("matches:", len(W), "with a Stage 0 box:", int(W["has_box"].sum()))
    wb = W[[f"w_{b}" for b in rc.BOX]].set_axis(rc.BOX, axis=1).astype(float)
    lb = W[[f"l_{b}" for b in rc.BOX]].set_axis(rc.BOX, axis=1).astype(float)
    short = W["format"].eq("short_sets")
    chk_rec = rc.box_checks(wb, lb, W["score"], W["status"], W["status_detail"], short)
    chk_exc = rc.box_checks(lb, wb, W["score"], W["status"], W["status_detail"], short)
    assert (chk_exc["has_box"] == chk_exc["has_box_stage0"]).all(), "replica disagrees with stage0_build"
    gw, gl = W["w_games_won_n"].astype(float), W["l_games_won_n"].astype(float)
    tbw, tbl = W["w_tb_won_n"].astype(float).fillna(0), W["l_tb_won_n"].astype(float).fillna(0)
    id_rec = rc.games_identity(gw, gl, wb, lb, tbw, tbl)
    id_exc = rc.games_identity(gw, gl, lb, wb, tbw, tbl)
    pw_r, pl_r = rc.points_won(wb, lb)
    need_w = 4 * (gw - tbw) + 7 * tbw - np.where(W["status"].eq("completed"), 0, 4)
    need_l = 4 * (gl - tbl) + 7 * tbl - np.where(W["status"].eq("completed"), 0, 4)
    feas_rec = (pw_r >= need_w) & (pl_r >= need_l)
    feas_exc = (pl_r >= need_w) & (pw_r >= need_l)
    B = (wb["bp_faced"] - wb["bp_saved"]) - (lb["bp_faced"] - lb["bp_saved"])
    D = wb["sv_gms"] - lb["sv_gms"]
    prog = rc.progression(m, p, W["match_id"].tolist()).set_index("match_id").loc[W["match_id"]].reset_index()

    print("loading referees ...")
    R = refs.load_all(INDEPENDENT)
    T = refs.ref_tml()
    print(f"  ref tml: {len(T):,} player-matches")
    R = pd.concat([R, T], ignore_index=True)
    R["sn"], R["osn"] = R["name"].map(refs.surname), R["oname"].map(refs.surname)
    atp = atp_keystats_bergs_rublev()

    out, used = [], []
    for i, row in W.iterrows():
        rec = {"match_id": row["match_id"], "tour": row["tour"], "year": int(row["year"]), "level": row["level"],
               "qualifying": bool(row["qualifying"]), "tournament": row["tournament_name"], "round": row["round"],
               "score": row["score"], "status": row["status"], "winner": row["w_player_name"],
               "winner_id": row["w_player_id"], "loser": row["l_player_name"], "loser_id": row["l_player_id"],
               "source": row["source"], "_source_file": row["source_file"], "_row": row["source_row"],
               "rec_identity_both": bool(id_rec.loc[i, "both_fit"]),
               "exch_identity_both": bool(id_exc.loc[i, "both_fit"]),
               "exch_identity_winner": bool(id_exc.loc[i, "w_fits"]), "exch_identity_loser": bool(id_exc.loc[i, "l_fits"]),
               "B_breaks_diff": B[i], "D_svgms_diff": D[i],
               "rec_passes_B0_B9": bool(chk_rec.loc[i, "has_box"]), "exch_passes_B0_B9": bool(chk_exc.loc[i, "has_box"]),
               "exch_failed_checks": ",".join(k for k in ["B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"]
                                              if chk_exc.loc[i, k]),
               "winner_pts_rec": pw_r[i], "loser_pts_rec": pl_r[i],
               "min_points_feasible_rec": bool(feas_rec[i]), "min_points_feasible_exch": bool(feas_exc[i]),
               "winner_plays_later": bool(prog.loc[i, "winner_plays_later"]),
               "loser_plays_later": bool(prog.loc[i, "loser_plays_later"]),
               "winner_next_rounds": prog.loc[i, "winner_next"]}
        c = find_refs(R, row)
        votes = []
        for _, r in c.iterrows():
            mine_rec = wb.loc[i] if r["is_w"] else lb.loc[i]
            mine_exc = lb.loc[i] if r["is_w"] else wb.loc[i]
            e_r, n = agreement(r, mine_rec)
            e_x, _ = agreement(r, mine_exc)
            used.append({"match_id": row["match_id"], "ref": r["ref"], "ref_event": r["event"], "ref_round": r["round"],
                         "ref_date": r["date"], "ref_name": r["name"], "ref_oname": r["oname"],
                         "about": "winner" if r["is_w"] else "loser", "name_match": r["name_match"],
                         "eq_as_recorded": e_r, "eq_exchanged": e_x, "counts_compared": n,
                         **{f"ref_{b}": r[b] for b in rc.BOX}, **{f"rec_{b}": mine_rec[b] for b in rc.BOX}})
            votes.append((r["ref"], bool(r["is_w"]), e_r, e_x, n))
        v = pd.DataFrame(votes, columns=["ref", "is_w", "e_r", "e_x", "n"])
        says = {}
        for ref, x in v.groupby("ref"):
            er, ex, n, sides = int(x["e_r"].sum()), int(x["e_x"].sum()), int(x["n"].sum()), x["is_w"].nunique()
            if n == 0:
                continue
            if ex >= 0.6 * n and ex >= er + 0.3 * n:
                verdict = "exchange"
            elif er >= 0.6 * n and er >= ex + 0.3 * n:
                verdict = "as_recorded"
            else:
                verdict = "unclear"
            says[ref] = (verdict, er, ex, n, sides)
        rec["tml"] = "" if "tml" not in says else "{0} (rec {1}/{3}, exch {2}/{3})".format(*says["tml"])
        ind = {k: v_ for k, v_ in says.items() if k != "tml"}
        if row["tournament_name"] == "Miami Masters" and int(row["year"]) == 2025 and "Bergs" in row["w_player_name"]:
            # ATP Infosys key statistics hold Bergs's row only, as fractions: compare with both boxes
            def fr(bx):
                return {"aces": bx["ace"], "double_faults": bx["df"], "serve1": bx["first_in"] / bx["svpt"],
                        "serve1_pts_won": bx["first_won"] / bx["first_in"],
                        "serve2_pts_won": bx["second_won"] / (bx["svpt"] - bx["first_in"]),
                        "break_points_saved": bx["bp_saved"] / bx["bp_faced"], "service_games_played": bx["sv_gms"]}
            e_r = sum(abs(fr(wb.loc[i])[k] - atp[k]) < 0.005 for k in fr(wb.loc[i]))
            e_x = sum(abs(fr(lb.loc[i])[k] - atp[k]) < 0.005 for k in fr(lb.loc[i]))
            ind["atp_keystats"] = ("exchange" if e_x >= 6 and e_r <= 2 else "unclear", e_r, e_x, 7, 1)
            used.append({"match_id": row["match_id"], "ref": "atp_keystats", "ref_event": "Miami 2025 ms047",
                         "ref_name": "Zizou Bergs", "about": "winner", "eq_as_recorded": e_r, "eq_exchanged": e_x,
                         "counts_compared": 7, "note": str(atp)})
        rec["referees"] = ";".join(f"{k}:{v_[0]} (rec {v_[1]}/{v_[3]}, exch {v_[2]}/{v_[3]}, players {v_[4]})"
                                   for k, v_ in sorted(ind.items()))
        rec["referee_verdicts"] = ";".join(sorted({v_[0] for v_ in ind.values()}))
        out.append(rec)
    o = pd.DataFrame(out)
    pd.DataFrame(used).to_csv(rc.OUT / "f2_referee_rows.csv", index=False)
    o.to_csv(rc.OUT / "f2_matches_raw.csv", index=False)
    pd.set_option("display.max_rows", 200)
    print(o[["tournament", "year", "round", "winner", "loser", "referees", "exch_identity_both", "B_breaks_diff",
             "D_svgms_diff", "min_points_feasible_rec", "min_points_feasible_exch", "winner_pts_rec", "loser_pts_rec",
             "winner_plays_later", "tml"]].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
