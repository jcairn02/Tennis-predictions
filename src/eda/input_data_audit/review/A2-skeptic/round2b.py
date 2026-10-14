"""Round 2, follow-up checks (A2-skeptic).

  * F2x: the API record of Acapulco 2020 Xiyu Wang - Yafan Wang (Sackmann's id M004 is not the WTA's) found by season,
    date and full names; raw Sackmann rows against the API for the matches whose Stage 0 box lacks service games or
    whose API box fails its own identity (Bondar-Pieri, Rakhimova-Danilovic, Kenin-Yang, Kenin-Flipkens).
  * F2y: break points faced and saved per server in the AO 2022 ball-tracking points (2022_MS146).
  * F4x: every Match Charting Project chart and every raw row of Li Na - Ksenia Pervak in 2011-2013.
  * F1x, F1y: the raw rows; Stage 0's B0-B9 and the games identity as recorded and with svpt + df; the 16-count box
    searched in every Sackmann raw row (a copy of another match?); MCP where charted.
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/round2b.py
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

import _common as K

RAW16 = ["w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "w_bpSaved", "w_bpFaced",
         "l_ace", "l_df", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_bpSaved", "l_bpFaced"]


def b_checks(w: dict, l_: dict, score: str, retired: bool) -> str:
    sets = re.findall(r"(\d+)-(\d+)(?:\((\d+)\))?", str(score))
    games = sum(int(a) + int(b) for a, b, _ in sets)
    tb = sum(1 for a, b, t in sets if t or {int(a), int(b)} == {6, 7})
    fails = []
    for tag, f in (("w", w), ("l", l_)):
        if f["first_in"] > f["svpt"]:
            fails.append("B1" + tag)
        if f["first_won"] > f["first_in"]:
            fails.append("B2" + tag)
        if f["second_won"] > f["svpt"] - f["first_in"]:
            fails.append("B3" + tag)
        if f["bp_saved"] > f["bp_faced"]:
            fails.append("B4" + tag)
        if f["df"] > f["svpt"] - f["first_in"]:
            fails.append("B6" + tag)
        if f["ace"] > f["first_won"] + f["second_won"]:
            fails.append("B7" + tag)
        if pd.notna(f["sv_gms"]) and f["bp_faced"] - f["bp_saved"] > f["sv_gms"]:
            fails.append("B8" + tag)
        if (f["second_won"] + f["df"]) > (f["svpt"] - f["first_in"]):
            fails.append("DEF" + tag)
    sv = w["sv_gms"] + l_["sv_gms"]
    if pd.notna(sv) and abs(sv - (games - tb)) > 1 and abs(sv - games) > 1:
        fails.append("B5")
    played = (games - tb) - (1 if retired else 0)
    if w["svpt"] + l_["svpt"] < 4.5 * played:
        fails.append("B9")
    return ",".join(fails) if fails else "pass"


def raw_box(r, side):
    return {c: r[f"{side}_{K.RAW[c]}"] for c in K.BOX}


def main() -> None:
    pd.set_option("display.width", 320)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_colwidth", 80)
    cand = pd.read_csv(K.ROOT / "data/studies/input_data_audit/fixes/round2_A_candidates.csv")

    # ---- F2x follow-ups
    api = K.wta_api(range(2019, 2027))
    a20 = api[api["year"].astype(str).eq("2020") & api["name_a"].str.contains("Wang") & api["name_b"].str.contains("Wang")]
    print("API 2020 Wang-Wang matches:")
    print(a20[["key", "ResultString", "Winner", "name_a", "name_b"] + [f"{s}_{c}" for s in "ab" for c in ("svpt", "first_in", "sv_gms")]].to_string())
    raws = K.sackmann("wta", "*202[01]")
    r20 = raws[(raws["_row"].eq(396)) & raws["_source_file"].str.endswith("wta_matches_2020.csv")]
    print("Sackmann Acapulco 2020 row:")
    print(r20[["tourney_name", "round", "winner_name", "loser_name", "score"] + [f"{s}_{c}" for s in "wl" for c in ("svpt", "1stIn", "SvGms", "ace", "df")]].to_string())
    for key in ("2028/2021/RS013", "2027/2021/RS012", "2028/2021/LS032", "2028/2021/LS016"):
        a = api[api["key"].eq(key)].iloc[0]
        print("==", key, a["ResultString"], "| A:", a["name_a"], "| B:", a["name_b"], "| winner side", a["winner_side"])
        print("   API A:", {c: a[f"a_{c}"] for c in K.BOX})
        print("   API B:", {c: a[f"b_{c}"] for c in K.BOX})
    for src, row in (("wta_matches_qual_itf_2021.csv", 22855), ("wta_matches_qual_itf_2021.csv", 22990),
                     ("wta_matches_2021.csv", 31), ("wta_matches_2021.csv", 15)):
        r = raws[raws["_source_file"].str.endswith(src) & raws["_row"].eq(row)].iloc[0]
        print("   Sackmann", src, row, r["winner_name"], "d.", r["loser_name"], r["score"])
        print("      w:", raw_box(r, "w"))
        print("      l:", raw_box(r, "l"))

    # ---- F2y: break points per server in ball tracking
    p = pd.read_parquet(K.ROOT / "data/dump/points/slam_ball_tracking/points/AO_2022.parquet")
    q = p[p["match_id"].astype(str).eq("2022_MS146")].drop_duplicates(["set_num", "game_num", "point_num"])
    bp = q[q["is_break_point"].astype(str).str.upper().isin(["TRUE", "1"])]
    conv = bp[bp["is_break_point_converted"].astype(str).str.upper().isin(["TRUE", "1"])]
    print("F2y break points faced by server:", bp.groupby("server_id").size().to_dict(), "converted against server:",
          conv.groupby("server_id").size().to_dict())
    games = q.drop_duplicates(["set_num", "game_num"])
    # breaks: games won by the returner
    last = q.sort_values(["set_num", "game_num", "point_num"]).groupby(["set_num", "game_num"]).tail(1)
    last = last.assign(broken=last["point_winner_id"] != last["server_id"])
    print("F2y breaks per server (game's last point won by the returner):", last[last["broken"]].groupby("server_id").size().to_dict())

    # ---- F4x
    mc = pd.concat([K.mcp("w")])
    li = mc[(mc["pk"].str.contains("pervak") & mc["ok"].str.contains("li na|na li", regex=True)) |
            (mc["ok"].str.contains("pervak") & mc["pk"].str.contains("li na|na li", regex=True))]
    print("MCP Li Na - Pervak charts:")
    print(li[["match_id", "player", "serve_pts", "aces", "dfs", "first_in", "first_won", "second_won", "bk_pts", "bp_saved"]].to_string())
    allw = K.sackmann("wta", "*201[123]")
    pr = allw[(allw["winner_name"].str.contains("Pervak") | allw["loser_name"].str.contains("Pervak"))
              & (allw["winner_name"].isin(["Na Li", "Li Na"]) | allw["loser_name"].isin(["Na Li", "Li Na"]))]
    print("Sackmann Li - Pervak rows 2011-2013:")
    print(pr[["tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score", "_source_file", "_row"] + RAW16].to_string())
    li_ao = allw[allw["tourney_name"].eq("Australian Open") & allw["tourney_date"].astype(str).str.startswith("2012")
                 & (allw["winner_name"].isin(["Na Li"]) | allw["loser_name"].isin(["Na Li"]))]
    li_w = allw[allw["tourney_name"].eq("Wimbledon") & allw["tourney_date"].astype(str).str.startswith("2012")
                & (allw["winner_name"].isin(["Na Li"]) | allw["loser_name"].isin(["Na Li"]))]
    print("Li Na at AO 2012:")
    print(li_ao[["round", "winner_name", "loser_name", "score", "w_svpt", "l_svpt"]].to_string())
    print("Li Na at Wimbledon 2012:")
    print(li_w[["round", "winner_name", "loser_name", "score", "w_svpt", "l_svpt"]].to_string())
    pv = allw[allw["tourney_date"].astype(str).str.startswith("2012") & allw["tourney_name"].isin(["Australian Open", "Wimbledon"])
              & (allw["winner_name"].eq("Ksenia Pervak") | allw["loser_name"].eq("Ksenia Pervak"))]
    print("Pervak at AO and Wimbledon 2012 (all rounds incl. qualifying):")
    print(pv[["tourney_name", "round", "winner_name", "loser_name", "score"]].to_string())
    s0 = pd.read_parquet(K.S0 / "stage0_matches.parquet", columns=["match_id", "source_file", "source_row", "has_box", "box_status", "status"])
    print(s0[s0["match_id"].isin(cand.loc[cand["cand"].eq("F4x"), "match_id"])].to_string())
    print(s0[(s0["source_file"].str.endswith("wta_matches_2012.csv")) & s0["source_row"].isin([2342, 2605])].to_string())

    # ---- F1x and F1y rows
    all_raw = []
    for tour in ("atp", "wta"):
        r = K.sackmann(tour)
        r["tour"] = tour
        all_raw.append(r)
    all_raw = pd.concat(all_raw, ignore_index=True)
    for c in RAW16:
        all_raw[c] = pd.to_numeric(all_raw[c], errors="coerce")
    all_raw["key"] = all_raw[RAW16].fillna(-1).astype(int).astype(str).agg("|".join, axis=1)
    all_raw["key_x"] = all_raw[RAW16[8:] + RAW16[:8]].fillna(-1).astype(int).astype(str).agg("|".join, axis=1)
    mcw = K.mcp("w")
    mcw = mcw[mcw["date"].dt.year.eq(2015)]
    s0m = pd.read_parquet(K.S0 / "stage0_matches.parquet", columns=["match_id", "source_file", "source_row", "has_box", "box_status", "status", "score"])
    for c in cand[cand["cand"].isin(["F1x", "F1y"])].itertuples():
        r = all_raw[all_raw["_source_file"].eq(c.source_file) & all_raw["_row"].eq(c.source_row)].iloc[0]
        w, l_ = raw_box(r, "w"), raw_box(r, "l")
        retired = bool(re.search("RET", str(r["score"])))
        wc, lc = dict(w), dict(l_)
        wc["svpt"], lc["svpt"] = w["svpt"] + w["df"], l_["svpt"] + l_["df"]
        dup = all_raw[(all_raw["key"].eq(r["key"]) | all_raw["key_x"].eq(r["key"])) & ~(
            all_raw["_source_file"].eq(c.source_file) & all_raw["_row"].eq(c.source_row))]
        sm = s0m[s0m["source_file"].eq(c.source_file) & s0m["source_row"].eq(c.source_row)]
        print(f"== {c.cand} {r['tourney_name']} {r['round']} {r['winner_name']} d. {r['loser_name']} {r['score']} | Stage 0:",
              sm[["match_id", "has_box", "box_status", "status"]].to_dict("records"))
        print("   w:", w)
        print("   l:", l_)
        print("   checks as recorded:", b_checks(w, l_, r["score"], retired), "| with svpt + df:", b_checks(wc, lc, r["score"], retired))
        sets = re.findall(r"(\d+)-(\d+)(?:\((\d+)\))?", str(r["score"]))
        gw = sum(int(a) for a, b, _ in sets)
        gl = sum(int(b) for a, b, _ in sets)
        tbw = sum(1 for a, b, t in sets if (t or {int(a), int(b)} == {6, 7}) and int(a) > int(b))
        if not retired and pd.notna(w["sv_gms"]):
            bw, bl = w["bp_faced"] - w["bp_saved"], l_["bp_faced"] - l_["bp_saved"]
            print("   identity (tiebreaks credited): winner", w["sv_gms"] - bw + bl + tbw, "vs", gw,
                  "| exchanged", l_["sv_gms"] - bl + bw + tbw, "| loser", l_["sv_gms"] - bl + bw + (sum(1 for a, b, t in sets if (t or {int(a), int(b)} == {6, 7}) and int(b) > int(a))), "vs", gl)
        pw = w["first_won"] + w["second_won"] + l_["svpt"] - l_["first_won"] - l_["second_won"]
        pl = l_["first_won"] + l_["second_won"] + w["svpt"] - w["first_won"] - w["second_won"]
        pwc = w["first_won"] + w["second_won"] + lc["svpt"] - l_["first_won"] - l_["second_won"]
        plc = l_["first_won"] + l_["second_won"] + wc["svpt"] - w["first_won"] - w["second_won"]
        print(f"   points won as recorded {pw:g}-{pl:g}, with +df {pwc:g}-{plc:g}; games {gw}-{gl}; points per game +df "
              f"{(wc['svpt'] + lc['svpt']) / max(gw + gl, 1):.2f}")
        print("   same 16-count box elsewhere in Sackmann:", dup[["tourney_name", "tourney_date", "round", "winner_name", "loser_name", "score"]].to_dict("records"))
        for side, nm in (("w", r["winner_name"]), ("l", r["loser_name"])):
            other = r["loser_name"] if side == "w" else r["winner_name"]
            hit = mcw[(mcw["pk"] == K.name_key(nm)) & (mcw["ok"] == K.name_key(other))]
            if len(hit):
                h = hit.iloc[0]
                print(f"   MCP {h['match_id']}: {nm} serve_pts {h['serve_pts']} dfs {h['dfs']} first_in {h['first_in']} "
                      f"first_won {h['first_won']} second_won {h['second_won']}")


if __name__ == "__main__":
    main()
