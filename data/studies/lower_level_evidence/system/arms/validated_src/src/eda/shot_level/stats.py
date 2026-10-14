"""Per-player, per-match statistics built from the common point table (src/eda/shot_level/points.py).

Every statistic is a numerator over a denominator for one player in one match, so it can be summed over a history,
shrunk and opponent-adjusted like the box-score statistics. The points must already be turned to Stage 0's sides (player
1 = side A, 2 = side B). Definitions, for player P against opponent O ('rally' counts the serve as shot 1 and an
erring shot; a point's return is 'in play' when the point lasted 3 shots or more, or ended on shot 2 with a return
winner; return errors, aces and double faults are not in play):

  rally length (a match carries the family when 90% of its points that are not double faults have a rally length)
    srv_quick     P's serve points in play won within 4 shots / P's serve points in play
    ret_quick     P's return points in play won within 4 shots / P's return points in play
    rally5        points of 5 or more shots won by P / points of 5 or more shots
    rally9        points of 9 or more shots won by P / points of 9 or more shots
    ret_inplay    P's returns in play / O's serve points that were neither aces nor double faults
    long_share    points of 5 or more shots / points with a rally length (not double faults): the match's length of
                  rallies, the same for both players (a style; used in an interaction)
  how points end (90% of points classified)
    winner_rate   P's winners (aces excluded) / classified points
    error_rate    P's errors, forced and unforced (double faults excluded) / classified points
    ue_share      P's unforced errors / both players' unforced errors (a within-match share: the sources disagree on
                  forced versus unforced, by a level that cancels within a match)
    w_ratio       P's winners / (P's winners + P's errors)
  serve speed (half of the player's first serves timed)
    spd1          the mean speed of P's first serves in, km/h (numerator: the sum of speeds)
    spd2          the mean speed of P's second serves in (double faults excluded)
  net play (net flags recorded on 90% of points)
    net_rate      points at which P came to the net / points with net flags
    net_won       net points won by P / P's net points
  serve placement (half of P's first serves in placed)
    t_share       P's first serves in to the T / P's first serves in with a placement
    wide_share    P's first serves in out wide / the same
  return depth (half of P's returns in play with a depth)
    deep_ret      P's returns in play landing deep / P's returns in play with a depth
  wing (half of the classified rally endings with a wing)
    bh_ue_share   P's unforced errors on the backhand / P's unforced errors with a wing
    fh_win_share  P's winners on the forehand / P's winners with a wing
  point sequence (a complete sequence: see sequence_ok)
    consolidate   P's service games held right after P broke serve / such games (same set, no tiebreaks)
    break_back    P's return games won right after P was broken / such games
    serve_set     P's service games held when winning the game wins the set / such games
    pressure_srv  on P's serve points at 30-30, deuce or break point: won minus P's serve-point rate in the match
                  (an excess; denominator: such points)
    first_in_pressure   on the same points: first serves in minus P's first-serve-in rate in the match
    after_loss    on P's serve points that follow a lost serve point in the same game: won minus P's serve-point rate
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.eda.shot_level.points import END

STATS = {
    "rally": ["srv_quick", "ret_quick", "rally5", "rally9", "ret_inplay", "long_share"],
    "ending": ["winner_rate", "error_rate", "ue_share", "w_ratio"],
    "speed": ["spd1", "spd2"],
    "net": ["net_rate", "net_won"],
    "placement": ["t_share", "wide_share"],
    "return": ["deep_ret"],
    "stroke": ["bh_ue_share", "fh_win_share"],
    "sequence": ["consolidate", "break_back", "serve_set", "pressure_srv", "first_in_pressure", "after_loss"],
}
FAMILY_OF = {s: f for f, ss in STATS.items() for s in ss}
ALL_STATS = [s for ss in STATS.values() for s in ss]
LEVEL = {"spd1", "spd2"}                         # means of a measurement, not shares
EXCESS = {"pressure_srv", "first_in_pressure", "after_loss"}   # differences from the player's own match rate
SAME_FOR_BOTH = {"long_share"}
GATE = 0.9
GATE_HALF = 0.5


def _sum(mask: np.ndarray, groups: np.ndarray, n: int) -> np.ndarray:
    return np.bincount(groups, weights=mask.astype("float64"), minlength=n)


def match_stats(p: pd.DataFrame) -> pd.DataFrame:
    """One row per (match_id, side) for the points of one source, oriented to Stage 0's sides: <stat>_n and <stat>_d
    for every statistic except the sequence family, and per-family gates already applied (a failing match has d = 0)."""
    key = p["match_id"].to_numpy()
    codes, uniq = pd.factorize(key)
    n = len(uniq)
    srv, win = p["server"].to_numpy(), p["winner"].to_numpy()
    rally, end, ender = p["rally"].to_numpy(), p["end"].to_numpy(), p["ender"].to_numpy()
    sn, speed, place = p["serve_no"].to_numpy(), p["speed"].to_numpy(dtype="float64"), p["place"].to_numpy()
    net1, net2, rdeep, wing = p["net1"].to_numpy(), p["net2"].to_numpy(), p["ret_deep"].to_numpy(), p["wing"].to_numpy()
    is_df, is_ace = end == END["df"], end == END["ace"]
    is_err = np.isin(end, [END["forced"], END["unforced"]])
    known_r = rally >= 0
    in_play = known_r & ((rally >= 3) | ((rally == 2) & (win != srv)))
    # gates (per match, the same for both sides)
    nondf = ~is_df
    g_rally = _sum(known_r & nondf, codes, n) / np.maximum(_sum(nondf, codes, n), 1) >= GATE
    classified = end > 0
    g_end = _sum(classified, codes, n) / np.maximum(_sum(np.ones(len(p), bool), codes, n), 1) >= GATE
    g_net = _sum(net1 >= 0, codes, n) / np.maximum(_sum(np.ones(len(p), bool), codes, n), 1) >= GATE
    rows = {}
    for side in (1, 2):
        opp = 3 - side
        S, R = srv == side, srv == opp
        won = win == side
        out = {}
        # rally length
        out["srv_quick"] = (_sum(S & in_play & won & (rally <= 4), codes, n), _sum(S & in_play, codes, n), g_rally)
        out["ret_quick"] = (_sum(R & in_play & won & (rally <= 4), codes, n), _sum(R & in_play, codes, n), g_rally)
        out["rally5"] = (_sum(known_r & (rally >= 5) & won, codes, n), _sum(known_r & (rally >= 5), codes, n), g_rally)
        out["rally9"] = (_sum(known_r & (rally >= 9) & won, codes, n), _sum(known_r & (rally >= 9), codes, n), g_rally)
        out["ret_inplay"] = (_sum(R & in_play, codes, n), _sum(R & known_r & ~is_ace & ~is_df, codes, n), g_rally)
        out["long_share"] = (_sum(known_r & (rally >= 5), codes, n), _sum(known_r & nondf & (rally >= 1), codes, n), g_rally)
        # endings
        mine = ender == side
        w_p = _sum(classified & (end == END["winner"]) & mine, codes, n)
        e_p = _sum(classified & is_err & mine, codes, n)
        ue_p = _sum((end == END["unforced"]) & mine, codes, n)
        ue_o = _sum((end == END["unforced"]) & (ender == opp), codes, n)
        cls = _sum(classified, codes, n)
        out["winner_rate"] = (w_p, cls, g_end)
        out["error_rate"] = (e_p, cls, g_end)
        out["ue_share"] = (ue_p, ue_p + ue_o, g_end)
        out["w_ratio"] = (w_p, w_p + e_p, g_end)
        # speed (first serves in: serve_no 1 on a point that is not a double fault)
        f1 = S & (sn == 1) & ~is_df
        f2 = S & (sn == 2) & ~is_df
        t1, t2 = f1 & np.isfinite(speed), f2 & np.isfinite(speed)
        sp = np.nan_to_num(speed)
        g_sp1 = _sum(t1, codes, n) / np.maximum(_sum(f1, codes, n), 1) >= GATE_HALF
        g_sp2 = _sum(t2, codes, n) / np.maximum(_sum(f2, codes, n), 1) >= GATE_HALF
        out["spd1"] = (np.bincount(codes, weights=np.where(t1, sp, 0.0), minlength=n), _sum(t1, codes, n), g_sp1)
        out["spd2"] = (np.bincount(codes, weights=np.where(t2, sp, 0.0), minlength=n), _sum(t2, codes, n), g_sp2)
        out["spd1_sq"] = (np.bincount(codes, weights=np.where(t1, sp * sp, 0.0), minlength=n), _sum(t1, codes, n), g_sp1)
        out["spd2_sq"] = (np.bincount(codes, weights=np.where(t2, sp * sp, 0.0), minlength=n), _sum(t2, codes, n), g_sp2)
        # net
        netp = net1 if side == 1 else net2
        nk = netp >= 0
        out["net_rate"] = (_sum(nk & (netp == 1), codes, n), _sum(nk, codes, n), g_net)
        out["net_won"] = (_sum(nk & (netp == 1) & won, codes, n), _sum(nk & (netp == 1), codes, n), g_net)
        # placement (first serves in)
        pk = f1 & (place > 0)
        g_pl = _sum(pk, codes, n) / np.maximum(_sum(f1, codes, n), 1) >= GATE_HALF
        out["t_share"] = (_sum(pk & (place == 1), codes, n), _sum(pk, codes, n), g_pl)
        out["wide_share"] = (_sum(pk & (place == 3), codes, n), _sum(pk, codes, n), g_pl)
        # return depth (P's returns in play)
        rk = R & in_play & (rdeep >= 0)
        g_rd = _sum(rk, codes, n) / np.maximum(_sum(R & in_play, codes, n), 1) >= GATE_HALF
        out["deep_ret"] = (_sum(rk & (rdeep == 1), codes, n), _sum(rk, codes, n), g_rd)
        # wing
        ue_m = (end == END["unforced"]) & mine
        wn_m = (end == END["winner"]) & mine
        wk_ue, wk_wn = ue_m & (wing > 0), wn_m & (wing > 0)
        rally_end = classified & np.isin(end, [END["winner"], END["forced"], END["unforced"]])
        g_wing = _sum(rally_end & (wing > 0), codes, n) / np.maximum(_sum(rally_end, codes, n), 1) >= GATE_HALF
        out["bh_ue_share"] = (_sum(wk_ue & (wing == 2), codes, n), _sum(wk_ue, codes, n), g_wing)
        out["fh_win_share"] = (_sum(wk_wn & (wing == 1), codes, n), _sum(wk_wn, codes, n), g_wing)
        rec = {}
        for s, (num_, den_, gate) in out.items():
            rec[f"{s}_n"] = np.where(gate, num_, 0.0)
            rec[f"{s}_d"] = np.where(gate, den_, 0.0)
        rows[side] = pd.DataFrame(rec)
        rows[side].insert(0, "side", "A" if side == 1 else "B")
        rows[side].insert(0, "match_id", uniq)
    return pd.concat([rows[1], rows[2]], ignore_index=True)


# ------------------------------------------------------------------------------------------------
# The point sequence: games, sets, breaks, pressure

def game_frame(p: pd.DataFrame) -> pd.DataFrame:
    """One row per game of every match: server (the side that served its points; 0 for a tiebreak, where both serve),
    winner (the winner of its last point), set_no, the games each side had won in the set before it, and whether the
    game could have won its server the set. Points must be in match order (seq) within match_id."""
    g = p.groupby(["match_id", "game_key"], sort=True)
    gf = pd.DataFrame({"set_no": g["set_no"].first(), "srv_min": g["server"].min(), "srv_max": g["server"].max(),
                       "winner": g["winner"].last(), "points": g.size()}).reset_index()
    gf["tb"] = gf["srv_min"] != gf["srv_max"]
    gf["server"] = np.where(gf["tb"], 0, gf["srv_min"])
    gf = gf.sort_values(["match_id", "game_key"]).reset_index(drop=True)
    a_won = (gf["winner"] == 1).astype(int)
    b_won = (gf["winner"] == 2).astype(int)
    key = [gf["match_id"], gf["set_no"]]
    gf["a_games"] = a_won.groupby(key).cumsum() - a_won
    gf["b_games"] = b_won.groupby(key).cumsum() - b_won
    srv_games = np.where(gf["server"] == 1, gf["a_games"], gf["b_games"])
    ret_games = np.where(gf["server"] == 1, gf["b_games"], gf["a_games"])
    gf["for_set"] = (~gf["tb"]) & (srv_games + 1 >= 6) & (srv_games + 1 - ret_games >= 2)
    gf["break"] = (~gf["tb"]) & (gf["winner"] != gf["server"])
    return gf


def sequence_ok(gf: pd.DataFrame) -> pd.Series:
    """Per match: whether the reconstructed sets look like tennis. Every set but the last ends with its winner on 6 games
    or more, ahead by 2, or 7-6 (a tiebreak). A match with points missing fails, and the sequence family is not built
    from it."""
    last = gf.groupby(["match_id", "set_no"]).tail(1)
    fin_a = last["a_games"] + (last["winner"] == 1).astype(int)
    fin_b = last["b_games"] + (last["winner"] == 2).astype(int)
    hi, lo = np.maximum(fin_a, fin_b), np.minimum(fin_a, fin_b)
    ok_set = ((hi >= 6) & (hi - lo >= 2)) | ((hi == 7) & (lo == 6)) | (last["tb"] & (hi - lo == 1))
    # the last set of a retired match may be unfinished
    is_last = last.groupby("match_id")["set_no"].transform("max") == last["set_no"]
    ok = (ok_set | is_last).groupby(last["match_id"]).all()
    n_sets = last.groupby("match_id").size()
    return ok & (n_sets >= 2)


def sequence_stats(p: pd.DataFrame) -> pd.DataFrame:
    """The sequence family per (match_id, side): <stat>_n and <stat>_d, zero for matches whose sequence fails
    sequence_ok."""
    p = p.sort_values(["match_id", "seq"], kind="mergesort").reset_index(drop=True)
    gf = game_frame(p)
    ok = sequence_ok(gf)
    gf = gf[gf["match_id"].map(ok).fillna(False).astype(bool)].reset_index(drop=True)
    good = set(gf["match_id"])
    p = p[p["match_id"].isin(good)].reset_index(drop=True)
    uniq = np.array(sorted(good))
    idx = {m: i for i, m in enumerate(uniq)}
    n = len(uniq)
    # previous game in the same set (no tiebreaks either side)
    prev_same = gf["match_id"].eq(gf["match_id"].shift()) & gf["set_no"].eq(gf["set_no"].shift())
    prev_break = gf["break"].shift(fill_value=False).astype(bool) & prev_same
    prev_srv = gf["server"].shift(fill_value=0)
    prev_tb = gf["tb"].shift(fill_value=False).astype(bool)
    gi = gf["match_id"].map(idx).to_numpy()
    # point level: score in the game before the point
    pt = p.merge(gf[["match_id", "game_key", "tb", "server"]].rename(columns={"server": "g_server"}),
                 on=["match_id", "game_key"], how="left")
    srv_won = (pt["winner"] == pt["server"]).astype(int)
    grp = [pt["match_id"], pt["game_key"]]
    s_before = srv_won.groupby(grp).cumsum() - srv_won
    r_before = (1 - srv_won).groupby(grp).cumsum() - (1 - srv_won)
    normal = ~pt["tb"].astype(bool)
    pressure = normal & (((s_before == r_before) & (s_before >= 2)) | ((r_before >= 3) & (r_before > s_before)))
    prev_pt_lost = (srv_won.groupby(grp).shift(1) == 0) & normal
    pi = pt["match_id"].map(idx).to_numpy()
    rows = {}
    for side in (1, 2):
        rec = {}
        held = (gf["winner"] == side).to_numpy()
        mine_srv = (gf["server"] == side).to_numpy() & ~gf["tb"].to_numpy()
        # consolidate: my service game right after I broke (the previous game was the opponent's, broken by me)
        cons = mine_srv & prev_break.to_numpy() & (prev_srv.to_numpy() == 3 - side) & ~prev_tb.to_numpy()
        rec["consolidate_n"] = np.bincount(gi, weights=(cons & held).astype(float), minlength=n)
        rec["consolidate_d"] = np.bincount(gi, weights=cons.astype(float), minlength=n)
        # break back: the opponent's service game right after I was broken
        theirs = (gf["server"] == 3 - side).to_numpy() & ~gf["tb"].to_numpy()
        bb = theirs & prev_break.to_numpy() & (prev_srv.to_numpy() == side) & ~prev_tb.to_numpy()
        rec["break_back_n"] = np.bincount(gi, weights=(bb & held).astype(float), minlength=n)
        rec["break_back_d"] = np.bincount(gi, weights=bb.astype(float), minlength=n)
        # serving for the set
        fs = mine_srv & gf["for_set"].to_numpy()
        rec["serve_set_n"] = np.bincount(gi, weights=(fs & held).astype(float), minlength=n)
        rec["serve_set_d"] = np.bincount(gi, weights=fs.astype(float), minlength=n)
        # point excesses on my serve
        S = (pt["server"] == side).to_numpy() & normal.to_numpy()
        won = (pt["winner"] == side).to_numpy()
        rate = np.bincount(pi, weights=(S & won).astype(float), minlength=n) / np.maximum(np.bincount(pi, weights=S.astype(float), minlength=n), 1)
        sn = pt["serve_no"].to_numpy()
        snk = S & (sn > 0)
        rate_in = np.bincount(pi, weights=(snk & (sn == 1)).astype(float), minlength=n) / np.maximum(np.bincount(pi, weights=snk.astype(float), minlength=n), 1)
        pr = S & pressure.to_numpy()
        rec["pressure_srv_n"] = np.bincount(pi, weights=np.where(pr, won - rate[pi], 0.0), minlength=n)
        rec["pressure_srv_d"] = np.bincount(pi, weights=pr.astype(float), minlength=n)
        prk = pr & (sn > 0)
        rec["first_in_pressure_n"] = np.bincount(pi, weights=np.where(prk, (sn == 1) - rate_in[pi], 0.0), minlength=n)
        rec["first_in_pressure_d"] = np.bincount(pi, weights=prk.astype(float), minlength=n)
        al = S & prev_pt_lost.to_numpy()
        rec["after_loss_n"] = np.bincount(pi, weights=np.where(al, won - rate[pi], 0.0), minlength=n)
        rec["after_loss_d"] = np.bincount(pi, weights=al.astype(float), minlength=n)
        df = pd.DataFrame(rec)
        df.insert(0, "side", "A" if side == 1 else "B")
        df.insert(0, "match_id", uniq)
        rows[side] = df
    return pd.concat([rows[1], rows[2]], ignore_index=True)
