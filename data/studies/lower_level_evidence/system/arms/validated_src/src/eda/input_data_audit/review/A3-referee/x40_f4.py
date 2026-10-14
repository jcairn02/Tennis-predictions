"""F4: box scores repeated on the same pair's other meeting, and the Dusseldorf 2012 copies; which row is the copy.

For each pair in box_raw_copies.csv with same_players True (deduplicated) and the two Dusseldorf rows:
    * both raw Sackmann rows (_source_file, _row) and their Stage 0 match ids;
    * how the shared box fits each match's score: the games identity on both players (tiebreaks either way),
      service games against the games played (B5), serve points per game (B9), the minimum-points rule,
      the points-won winner;
    * the Match Charting Project's record of either match, where held (exact agreement with the shared box);
    * verdict: the copy is the row whose score the box does not fit, when the box fits the other row and not this
      one, or when an independent record matches the box on the other row.
Writes f4_pairs.csv and f4_scope.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rc  # noqa: E402
import refs  # noqa: E402

PPG_LO, PPG_HI = 4.84, 9.19   # 0.1% and 99.9% of serve points per game, clean completed WTA tour/Slam matches 2010-16
RAWC = ["w_ace", "w_df", "w_svpt", "w_1stIn", "w_1stWon", "w_2ndWon", "w_bpSaved", "w_bpFaced",
        "l_ace", "l_df", "l_svpt", "l_1stIn", "l_1stWon", "l_2ndWon", "l_bpSaved", "l_bpFaced"]


def load_raw() -> pd.DataFrame:
    fr = []
    for tour in ("atp", "wta"):
        for f in sorted((rc.SACK / tour).glob(f"{tour}_matches_*.parquet")):
            if "doubles" in f.name:
                continue
            t = pd.read_parquet(f)
            if not set(RAWC) <= set(t.columns):
                continue
            t["tour"] = tour
            fr.append(t)
    r = pd.concat(fr, ignore_index=True)
    r["key"] = r[RAWC].apply(lambda c: rc.num(c)).fillna(-1).astype(int).astype(str).agg("|".join, axis=1)
    return r


def fit(score, status, sdet, w, l_, gw, gl, tbw, tbl):
    """How a box (w, l: dicts of the nine counts) fits a match's score."""
    W = pd.DataFrame([w])
    L = pd.DataFrame([l_])
    chk = rc.box_checks(W, L, pd.Series([score]), pd.Series([status]), pd.Series([sdet]))
    ident = rc.games_identity(pd.Series([gw]), pd.Series([gl]), W, L, pd.Series([tbw]), pd.Series([tbl]))
    pw, pl = rc.points_won(W, L)
    sp = rc.score_parts(pd.Series([score]), None, None, pd.Series([status]))
    games = int(sp["games_w"][0] + sp["games_l"][0])
    std_tb = int(sp["std_tb"][0])
    ppg = (w["svpt"] + l_["svpt"]) / max(games - std_tb, 1)
    need_w = 4 * (gw - tbw) + 7 * tbw - (0 if status == "completed" else 4)
    need_l = 4 * (gl - tbl) + 7 * tbl - (0 if status == "completed" else 4)
    # identity without service games: games_w - games_l = D - 2B (+ tiebreaks won difference), |D| <= 1
    B = (w["bp_faced"] - w["bp_saved"]) - (l_["bp_faced"] - l_["bp_saved"])
    dg, dtb = gw - gl, tbw - tbl
    approx = (abs(dg + 2 * B - dtb) <= 1) or (abs(dg + 2 * B) <= 1)
    min_ok = bool(pw[0] >= need_w and pl[0] >= need_l)
    plausible_ppg = PPG_LO <= ppg <= PPG_HI
    hard_fail = (not approx) or (not min_ok) or (not plausible_ppg) or bool(chk["B5"][0])
    return {"passes_B0_B9": bool(chk["has_box"][0]), "B5_svgms": bool(chk["B5"][0]), "B9": bool(chk["B9"][0]),
            "identity_both": bool(ident["both_fit"][0]), "approx_identity": bool(approx),
            "svg_total": w["sv_gms"] + l_["sv_gms"], "games": games, "pts_per_game": round(ppg, 2),
            "ppg_plausible": bool(plausible_ppg), "winner_more_points": bool(pw[0] > pl[0]),
            "min_points_ok": min_ok, "fits": not hard_fail}


def main() -> int:
    cp = pd.read_csv(rc.AUD / "box_raw_copies.csv")
    same = cp[cp["same_players"]].copy()
    dus = cp[cp["copy_event"].eq("Dusseldorf")].copy()
    print("same-player rows:", len(same), "distinct copy matches:", same[["copy_event", "copy_date", "copy_match"]].drop_duplicates().shape[0])
    raw = load_raw()
    m, p = rc.stage0()
    W = rc.wide(m[m["source"].eq("sackmann")], p[p["match_id"].isin(m.loc[m["source"].eq("sackmann"), "match_id"])])
    by_src = W.set_index(["source_file", "source_row"])
    mc = refs.ref_mcp()
    mc["sn"], mc["osn"] = mc["name"].map(refs.surname), mc["oname"].map(refs.surname)

    groups = []
    for _, g in pd.concat([same, dus]).groupby(["tour", "source_event", "source_date", "source_match"]):
        groups.append(g)
    rows = []
    for g in groups:
        t, sev, sdate, smatch = g.iloc[0][["tour", "source_event", "source_date", "source_match"]]
        # every raw row that carries this box
        cand = raw[(raw["tour"] == t) & (raw["tourney_name"].isin([sev] + g["copy_event"].tolist()))
                   & (raw["tourney_date"].astype(str).isin([str(sdate)] + g["copy_date"].astype(str).tolist()))]
        cand = cand.copy()
        cand["mstr"] = cand["winner_name"] + " d. " + cand["loser_name"] + " " + cand["score"].astype(str)
        members = cand[cand["mstr"].isin([smatch] + g["copy_match"].tolist())]
        keyset = members["key"].value_counts()
        k = keyset.index[0]
        members = members[members["key"] == k]
        # the box (as raw w / l of the first member)
        info = []
        for _, r in members.iterrows():
            s0 = by_src.loc[(r["_source_file"], r["_row"])] if (r["_source_file"], r["_row"]) in by_src.index else None
            def val(x):
                v = rc.num(pd.Series([x]).astype("string"))[0]
                return np.nan if pd.isna(v) else float(v)
            w = {b: val(r[f"w_{rc.SRC[b]}"]) for b in rc.BOX}
            l_ = {b: val(r[f"l_{rc.SRC[b]}"]) for b in rc.BOX}
            if s0 is None:
                info.append({"match": r["mstr"], "event": r["tourney_name"], "date": r["tourney_date"],
                             "round": r["round"], "_source_file": r["_source_file"], "_row": r["_row"],
                             "match_id": None})
                continue
            # Stage 0 winner may be the raw loser (rule D5); games from Stage 0 for the Stage 0 winner
            flip = s0["w_player_id"] != f"{t}:{r['winner_id']}"
            gw, gl = (s0["l_games_won_n"], s0["w_games_won_n"]) if flip else (s0["w_games_won_n"], s0["l_games_won_n"])
            tbw, tbl = (s0["l_tb_won_n"], s0["w_tb_won_n"]) if flip else (s0["w_tb_won_n"], s0["l_tb_won_n"])
            f = fit(s0["score"], s0["status"], s0["status_detail"], w, l_, float(gw) if pd.notna(gw) else np.nan,
                    float(gl) if pd.notna(gl) else np.nan, float(tbw) if pd.notna(tbw) else 0.0,
                    float(tbl) if pd.notna(tbl) else 0.0)
            # MCP record of this match (date within the event's window)
            ws, ls = rc.name_key(r["winner_name"]), rc.name_key(r["loser_name"])
            td = pd.to_datetime(str(r["tourney_date"]), format="%Y%m%d")
            x = mc[(((mc["pk"] == ws) & (mc["ok"] == ls)) | ((mc["pk"] == ls) & (mc["ok"] == ws)))
                   & (mc["date"] - td).dt.days.between(-1, 16)]
            mcp_eq = ""
            if len(x):
                e = n = 0
                for _, xr in x.iterrows():
                    mine = w if xr["pk"] == ws else l_
                    for b in rc.BOX:
                        if pd.notna(xr[b]) and pd.notna(mine[b]):
                            n += 1
                            e += int(xr[b] == mine[b])
                mcp_eq = f"{e}/{n}"
            info.append({"match": r["mstr"], "event": r["tourney_name"], "date": r["tourney_date"], "round": r["round"],
                         "_source_file": r["_source_file"], "_row": r["_row"], "match_id": s0.name if False else None,
                         "stage0_has_box": bool(s0["has_box"]), "mcp_agreement_with_box": mcp_eq, **f})
        # attach match ids
        for d in info:
            hit = W[(W["source_file"] == d["_source_file"]) & (W["source_row"] == d["_row"])]
            d["match_id"] = hit["match_id"].iloc[0] if len(hit) else None
        n = len(info)
        fits = [bool(d.get("fits", False)) for d in info]
        mcp = []
        for d in info:
            st = d.get("mcp_agreement_with_box", "")
            if st:
                a_, b_ = map(int, st.split("/"))
                mcp.append("agrees" if (b_ >= 8 and a_ >= 0.8 * b_) else ("contradicts" if (b_ >= 8 and a_ <= 0.25 * b_) else "mixed"))
            else:
                mcp.append("")
        genuine, why = None, ""
        agree = [i for i, v in enumerate(mcp) if v == "agrees"]
        contra = [i for i, v in enumerate(mcp) if v == "contradicts"]
        if len(agree) == 1:
            genuine, why = agree[0], "MCP's chart equals the box on this match"
        else:
            rest = [i for i in range(n) if i not in contra]
            fit_rest = [i for i in rest if fits[i]]
            if len(fit_rest) == 1 and all(not fits[i] for i in rest if i != fit_rest[0]):
                genuine = fit_rest[0]
                why = ("the box fits only this match's score (games identity without service games, minimum points, "
                       "points per game within 0.1-99.9% of clean matches, B5)"
                       + ("; MCP contradicts the box on the other match" if contra else ""))
        for i, d in enumerate(info):
            role = "genuine" if genuine == i else ("copy" if genuine is not None else "undecided")
            if genuine is None and (mcp[i] == "contradicts" or (not fits[i] and n >= 3 and sum(fits) >= 1)):
                # the box cannot be this row's own, though which other row owns it is not decided
                role = "copy"
            d.update({"group": f"{t}|{sev}|{sdate}|{smatch}", "members": n, "role": role, "mcp": mcp[i],
                      "decided_by": why if genuine is not None else
                      ("box fits " + str(sum(fits)) + " of the " + str(n) + " scores; no independent record decides")})
            rows.append(d)
    out = pd.DataFrame(rows)
    out.to_csv(rc.OUT / "f4_pairs.csv", index=False)
    pd.set_option("display.width", 300)
    pd.set_option("display.max_rows", 300)
    pd.set_option("display.max_colwidth", 70)
    print(out[["group", "match", "event", "round", "role", "fits", "approx_identity", "identity_both", "svg_total",
               "games", "pts_per_game", "min_points_ok", "winner_more_points", "mcp_agreement_with_box",
               "stage0_has_box"]].to_string())
    print(out.groupby("role").size())
    sc = out[out["role"].eq("copy")][["match_id", "match", "event", "date", "round", "_source_file", "_row",
                                      "stage0_has_box", "decided_by"]]
    sc = sc.assign(operation="blank the box score (all nine counts, both players) of this row")
    sc.to_csv(rc.OUT / "f4_scope.csv", index=False)
    print("copies decided:", len(sc))
    return 0


if __name__ == "__main__":
    sys.exit(main())
