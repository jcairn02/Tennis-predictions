"""Round 2 (A1-rederive): per-row checks of round2_A_candidates.csv.

F2x: each match is linked afresh to the WTA API by searching every API singles match of that year for the two players
(surname keys, either order, draw Q/M from the round), preferring the API event equal to Sackmann's tourney id suffix.
Stage 0's box under each player is compared with the API's counts for that player (all nine), as recorded and
exchanged; the API's winner is compared with Stage 0's winner; Stage 0's counts are compared with the raw row.
F1x: Stage 0 / raw counts against MCP's Overview totals (serve points with double faults).
F2y: AO 2022 ball tracking (2022_MS146): games served, games won on serve, the first server, per player.
F4x: AO 2012 Li-Pervak against MCP and Sackmann's AO 2012 / Wimbledon 2012 point-by-point.
Writes round2_checks.csv and prints everything.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rd_common as R  # noqa: E402

pd.set_option("display.width", 280)
pd.set_option("display.max_colwidth", 80)
pd.set_option("display.max_rows", 200)
C = pd.read_csv(R.AUDIT / "fixes" / "round2_A_candidates.csv")
m, p = R.stage0()
mi = m.set_index("match_id")

# raw rows
raw_cache = {}


def raw_row(src_file, row):
    f = Path(src_file).name.replace(".csv", ".parquet")
    tour = "atp" if f.startswith("atp") else "wta"
    if f not in raw_cache:
        raw_cache[f] = R.sack(tour, f).set_index("_row")
    return raw_cache[f].loc[row]


def surname_ok(full, last):
    t = R.nkey(full).split()
    lk = R.nkey(last).split()
    return bool(lk) and all(x in t for x in lk)


api_cache = {}


def api_year(y):
    if y not in api_cache:
        a = R.wta_api(y)
        for c in ("lkA", "lkB"):
            a[c] = a[c].str.replace("sanders", "hunter", regex=False)
        api_cache[y] = a
    return api_cache[y]


out = []
for r in C.to_dict("records"):
    mid = r["match_id"]
    mr = mi.loc[mid]
    pr = p[p["match_id"].eq(mid)]
    W, L = pr[pr["won"]].iloc[0], pr[~pr["won"]].iloc[0]
    raw = raw_row(r["source_file"], r["source_row"])
    raw_w_is_W = f"{mr['tour']}:{raw['winner_id']}" == W["player_id"]
    side_W, side_L = ("w", "l") if raw_w_is_W else ("l", "w")
    s0_eq_raw = all((W[b] == raw[f"{side_W}_{b}"] or (pd.isna(W[b]) and pd.isna(raw[f"{side_W}_{b}"])))
                    and (L[b] == raw[f"{side_L}_{b}"] or (pd.isna(L[b]) and pd.isna(raw[f"{side_L}_{b}"]))) for b in R.BOX)
    rec = {"cand": r["cand"], "match_id": mid, "event": r["tournament_name"], "date": r["tournament_date"], "round": r["round"],
           "score": mr["score"], "status": mr["status"], "s0_has_box": bool(mr["has_box"]), "winner": W["player_name"],
           "loser": L["player_name"], "s0_equals_raw": s0_eq_raw, "raw_winner_is_s0_winner": raw_w_is_W}
    for b in R.BOX:
        rec[f"W_{b}"], rec[f"L_{b}"] = W[b], L[b]
    if r["cand"] == "F2x":
        y = int(str(r["tournament_date"])[:4])
        a = api_year(y)
        q = str(r["round"]).upper().startswith("Q") and str(r["round"])[1:].isdigit()
        a = a[a["draw"].eq("Q" if q else "M")]
        ev = str(raw["tourney_id"]).split("-")[-1]
        hits = []
        wk, lk = R.nkey(W["player_name"]), R.nkey(L["player_name"])

        def first_ok(full, api_full):
            # first name must agree when given (Kristyna vs Karolina, Xiyu vs Yafan, Veronika vs Polina ...)
            f1, f2 = R.nkey(full).split()[:1], R.nkey(api_full).split()[:1]
            return bool(f1) and bool(f2) and (f1[0] == f2[0] or f1[0].startswith(f2[0]) or f2[0].startswith(f1[0]))
        for x in a.to_dict("records"):
            ab = surname_ok(W["player_name"], x["lkA"]) and surname_ok(L["player_name"], x["lkB"])                 and first_ok(W["player_name"], x["nameA"]) and first_ok(L["player_name"], x["nameB"])
            ba = surname_ok(W["player_name"], x["lkB"]) and surname_ok(L["player_name"], x["lkA"])                 and first_ok(W["player_name"], x["nameB"]) and first_ok(L["player_name"], x["nameA"])
            if ab and not ba:
                hits.append((x, "A", "B"))
            elif ba and not ab:
                hits.append((x, "B", "A"))
            elif ab and ba:
                hits.append((x, "?", "?"))
        same_ev = [h for h in hits if h[0]["event"] == ev]
        use = same_ev if same_ev else hits
        rec["api_candidates"] = len(hits)
        rec["api_same_event"] = len(same_ev)
        rec["api_orientation_ambiguous"] = any(h[1] == "?" for h in use)
        same_surname = R.nkey(W["player_name"]).split()[-1] == R.nkey(L["player_name"]).split()[-1] or             surname_ok(W["player_name"], R.nkey(L["player_name"]).split()[-1]) or surname_ok(L["player_name"], R.nkey(W["player_name"]).split()[-1])
        rec["same_surname_pair"] = same_surname
        # my own games identity (orientation-free: uses Stage 0's boxes and score only)
        gw, gl, tw, tl, ntb, ret_ = R.games_of(mr["score"])
        def bg(a_, b_):
            return a_["sv_gms"] - (a_["bp_faced"] - a_["bp_saved"]) + (b_["bp_faced"] - b_["bp_saved"])
        rec["games_score"] = f"{gw - tw}-{gl - tl} (+tb {tw}-{tl})"
        rec["box_games_recorded"] = f"{bg(W, L):.0f}-{bg(L, W):.0f}"
        rec["pts_W_recorded"] = W["first_won"] + W["second_won"] + L["svpt"] - L["first_won"] - L["second_won"]
        rec["pts_L_recorded"] = L["first_won"] + L["second_won"] + W["svpt"] - W["first_won"] - W["second_won"]
        if len(use) == 1 and use[0][1] != "?":
            x, ws, ls = use[0]
            aW = {b: x[f"{ws}_{b}"] for b in R.BOX}
            aL = {b: x[f"{ls}_{b}"] for b in R.BOX}
            n_rec = sum(W[b] == aW[b] for b in R.BOX) + sum(L[b] == aL[b] for b in R.BOX)
            n_exc = sum(W[b] == aL[b] for b in R.BOX) + sum(L[b] == aW[b] for b in R.BOX)
            win_code = {"2": "A", "3": "B", "4": "A", "5": "B", "6": "A", "7": "B"}.get(x["winner_code"], "?")
            rec.update({"api_event": x["event"], "api_match": x["wmid"], "api_result": x["result"],
                        "api_winner_is_recorded_winner": win_code == ws, "api_match_recorded_of18": n_rec,
                        "api_match_exchanged_of18": n_exc})
            for b in R.BOX:
                rec[f"apiW_{b}"], rec[f"apiL_{b}"] = aW[b], aL[b]
    out.append(rec)
X = pd.DataFrame(out)
X.to_csv(R.OUT / "round2_checks.csv", index=False)
f2 = X[X["cand"].eq("F2x")]
print(f2[["event", "round", "score", "winner", "loser", "s0_equals_raw", "same_surname_pair", "api_orientation_ambiguous",
          "api_match", "api_result", "api_winner_is_recorded_winner", "api_match_recorded_of18", "api_match_exchanged_of18",
          "games_score", "box_games_recorded", "pts_W_recorded", "pts_L_recorded"]].to_string())

# ---------------- F1x: MCP
mcp = R.mcp_overview("w")
for r in X[X["cand"].eq("F1x")].to_dict("records"):
    print("\nF1x", r["match_id"], r["score"], "| Stage 0 has box:", r["s0_has_box"], "| equals raw:", r["s0_equals_raw"])
    for who in ("W", "L"):
        nm = r["winner"] if who == "W" else r["loser"]
        o = mcp[(mcp["mdate"].dt.year == 2015) & (mcp["tournament"].astype(str).str.contains("Doha")) & mcp["pkey"].eq(R.nkey(nm))
                & mcp["round"].astype(str).str.upper().eq(r["round"])]
        if len(o) != 1:
            print("   ", nm, "MCP rows:", len(o))
            continue
        o = o.iloc[0]
        print(f"    {nm}: Stage0 svpt {r[who + '_svpt']:.0f} df {r[who + '_df']:.0f} -> svpt+df {r[who + '_svpt'] + r[who + '_df']:.0f} | MCP "
              f"serve_pts {o['serve_pts']:.0f} dfs {o['dfs']:.0f} | first_in {r[who + '_first_in']:.0f}/{o['first_in']:.0f} "
              f"first_won {r[who + '_first_won']:.0f}/{o['first_won']:.0f} second_won {r[who + '_second_won']:.0f}/{o['second_won']:.0f} "
              f"ace {r[who + '_ace']:.0f}/{o['aces']:.0f} | definition test after fix: "
              f"{r[who + '_second_won'] + r[who + '_df'] <= r[who + '_svpt'] + r[who + '_df'] - r[who + '_first_in']}")

# ---------------- F2y: ball tracking AO 2022 Paire-Monteiro
bt = pd.read_parquet(R.DUMP / "points" / "slam_ball_tracking" / "points" / "AO_2022.parquet")
x = bt[bt["match_id"].eq("2022_MS146")].drop_duplicates("point_ID")
pts = x[x["point_end_type"] != "Faulty Serve"].copy()
for c in ("set_num", "game_num", "point_num"):
    pts[c] = pd.to_numeric(pts[c], errors="coerce")
pts = pts.sort_values(["set_num", "game_num", "point_num"])
games = pts.groupby(["set_num", "game_num"]).agg(server=("server_id", "first"), n_servers=("server_id", "nunique"),
                                                   last_winner=("point_winner_id", "last")).reset_index()
print("\nF2y ball tracking 2022_MS146: games", len(games), " games with two servers:", int((games["n_servers"] > 1).sum()))
print("   first game server:", games.iloc[0]["server"], " (ATPPD31 = Paire, ATPMJ08 = Monteiro)")
for pid, nm in (("ATPPD31", "Paire"), ("ATPMJ08", "Monteiro")):
    g = games[games["server"].eq(pid)]
    holds = int((g["last_winner"] == pid).sum())
    print(f"   {nm}: games served {len(g)}, held {holds}, broken {len(g) - holds}; games won overall "
          f"{int((games['last_winner'] == pid).sum())}")
r = X[X["cand"].eq("F2y")].iloc[0]
print(f"   Stage 0: Paire (W) sv_gms {r['W_sv_gms']:.0f}, bp {r['W_bp_saved']:.0f}/{r['W_bp_faced']:.0f} -> broken "
      f"{r['W_bp_faced'] - r['W_bp_saved']:.0f}; Monteiro (L) sv_gms {r['L_sv_gms']:.0f}, bp {r['L_bp_saved']:.0f}/{r['L_bp_faced']:.0f} -> broken "
      f"{r['L_bp_faced'] - r['L_bp_saved']:.0f}; score {r['score']}")
gw, gl, tw, tl, ntb, ret = R.games_of(r["score"])
for label, sw, sl in (("as recorded", r["W_sv_gms"], r["L_sv_gms"]), ("sv_gms exchanged", r["L_sv_gms"], r["W_sv_gms"])):
    bw = sw - (r["W_bp_faced"] - r["W_bp_saved"]) + (r["L_bp_faced"] - r["L_bp_saved"])
    bl = sl - (r["L_bp_faced"] - r["L_bp_saved"]) + (r["W_bp_faced"] - r["W_bp_saved"])
    print(f"   games from the box {label}: Paire {bw:.0f}, Monteiro {bl:.0f}  (score: {gw}-{gl})")

# ---------------- F4x: AO 2012 Li-Pervak
r = X[X["cand"].eq("F4x")].iloc[0]
print("\nF4x", r["match_id"], r["score"], "| Stage 0 has box:", r["s0_has_box"], "| equals raw:", r["s0_equals_raw"])
print(f"   Stage 0 box: Li svpt {r['W_svpt']:.0f} ace {r['W_ace']:.0f} df {r['W_df']:.0f} first_in {r['W_first_in']:.0f} won "
      f"{r['W_first_won'] + r['W_second_won']:.0f}; Pervak svpt {r['L_svpt']:.0f} ace {r['L_ace']:.0f} df {r['L_df']:.0f} "
      f"first_in {r['L_first_in']:.0f} won {r['L_first_won'] + r['L_second_won']:.0f}")
o = mcp[mcp["match_id"].astype(str).str.startswith("20120116-W-Australian_Open-R128-Na_Li")]
print(o[["match_id", "player", "serve_pts", "aces", "dfs", "first_in", "first_won", "second_won"]].to_string())
for yr, slam in ((2012, "ausopen"), (2012, "wimbledon")):
    base = R.DUMP / "points" / "sackmann_archive" / "slam_pointbypoint"
    mt = pd.read_parquet(base / f"{yr}-{slam}-matches.parquet")
    pt = pd.read_parquet(base / f"{yr}-{slam}-points.parquet")
    hit = mt[mt["player1"].astype(str).str.contains("Li$|Na Li", regex=True) & mt["player2"].astype(str).str.contains("Pervak")
             | mt["player2"].astype(str).str.contains("Li$|Na Li", regex=True) & mt["player1"].astype(str).str.contains("Pervak")]
    for h in hit.to_dict("records"):
        q = pt[pt["match_id"].eq(h["match_id"])].copy()
        for c in ("PointServer", "PointWinner", "P1Ace", "P2Ace", "P1DoubleFault", "P2DoubleFault"):
            q[c] = pd.to_numeric(q[c], errors="coerce")
        q = q[q["PointServer"].isin([1, 2])]
        li = 1 if "Li" in h["player1"] and "Pervak" not in h["player1"] else 2
        pv = 3 - li
        print(f"   {yr} {slam} {h['match_id']} ({h['player1']} v {h['player2']}): Li svpt {(q['PointServer'] == li).sum()} won "
              f"{((q['PointServer'] == li) & (q['PointWinner'] == li)).sum()} aces {int(q[f'P{li}Ace'].sum())} dfs {int(q[f'P{li}DoubleFault'].sum())}"
              f" | Pervak svpt {(q['PointServer'] == pv).sum()} won {((q['PointServer'] == pv) & (q['PointWinner'] == pv)).sum()} "
              f"aces {int(q[f'P{pv}Ace'].sum())} dfs {int(q[f'P{pv}DoubleFault'].sum())}")
