"""Round 0, brainstormer MECHANICS: outcome-free arithmetic with the iid point model.

No match outcome, no odds and no season of data enter this script. Every number is a property of the iid model
(each point an independent draw at a fixed serve-point probability), evaluated on synthetic serve-point
probabilities placed at the tour averages published in docs/studies/predictability_diagnostic/stage3.md
(men: serve points won 62.0% on average, 60.4% clay to 65.5% grass; first serves in 60.8%, first-serve points won
69.8%, second-serve points won 49.9%, aces 6.6% of serve points; women 55.9%, 62.1%, 62.5%, 45.0%, 3.4%).

Parts (each writes one block of data/studies/feature_interactions/round0/mechanics/iid_mechanics.json):

  1. leverage     d logit P(match) / d(serve-point log-odds edge), as a function of serve dominance and format
  2. length       expected points, games, sets and tiebreaks per match; P(at least one tiebreak)
  3. court        how a server's hold probability splits its sensitivity between deuce-court and ad-court points
  4. composition  (a) first-serve-in exposure x the returner's second-serve return; (b) free points (aces, unreturned
                  serves) and the returner's leverage on the rest

Run: ./python.sh src/eda/feature_interactions/round0/mechanics/iid_mechanics.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import stage2_iid as I  # noqa: E402  (read-only import)

OUT = ROOT / "data" / "studies" / "feature_interactions" / "round0" / "mechanics"


def logit(p):
    p = np.asarray(p, dtype="float64")
    return np.log(p / (1 - p))


def sig(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, dtype="float64")))


# ------------------------------------------------------------------------------------------------
# 1. Leverage of a serve-point edge on the match, by serve dominance and format

FORMATS = {"bo3": (3, "TB7@6"), "bo5_tb7": (5, "TB7@6"), "bo5_tb10final": (5, "TB10@6")}


def match_logit(m, delta, fmt):
    """logit P(A wins) when logit p_A = m + delta/2 and logit p_B = m - delta/2 (serve-point log-odds)."""
    bo, final = FORMATS[fmt]
    pa, pb = sig(m + delta / 2), sig(m - delta / 2)
    return logit(I.match_win(pa, pb, bo, final))


def part_leverage():
    pbar = np.round(np.arange(0.50, 0.785, 0.02), 3)
    m = logit(pbar)
    out = {"pbar": pbar.tolist(), "formats": {}}
    for fmt in FORMATS:
        rows = {}
        for d in (0.02, 0.10, 0.20, 0.40):
            lp = match_logit(m, np.full_like(m, d), fmt)
            rows[f"delta_{d}"] = {"match_logit": lp.round(4).tolist(), "per_unit": (lp / d).round(3).tolist()}
        lev = rows["delta_0.02"]["per_unit"]
        ref = lev[list(pbar).index(0.62)] if 0.62 in list(pbar) else lev[len(lev) // 2]
        rows["leverage_relative_to_pbar_0.62"] = (np.array(lev) / ref).round(3).tolist()
        out["formats"][fmt] = rows
    # the same edge in probability units: p_A - p_B = 0.02 at several dominance levels
    prob = {}
    for fmt in FORMATS:
        bo, final = FORMATS[fmt]
        lp = logit(I.match_win(pbar + 0.01, pbar - 0.01, bo, final))
        prob[fmt] = lp.round(4).tolist()
    out["match_logit_for_prob_edge_0.02"] = prob
    return out


# ------------------------------------------------------------------------------------------------
# 2. Expected length of a match: points, games, sets, tiebreaks

def game_stats(p):
    """(P(hold), E[points]) for a service game won point by point with probability p."""
    p = np.asarray(p, dtype="float64")
    q = 1 - p
    hold = np.zeros_like(p)
    epts = np.zeros_like(p)
    layer = {(0, 0): np.ones_like(p)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if i == 3 and j == 3:
                d = p * p + q * q
                hold += r * p * p / d
                epts += r * 2 / d
                continue
            epts += r
            for ni, nj, pr in ((i + 1, j, p), (i, j + 1, q)):
                if ni == 4:
                    hold += r * pr
                elif nj == 4:
                    pass
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return hold, epts


def _tb_first(k: int) -> bool:
    return k == 0 or ((k - 1) // 2) % 2 == 1


def tb_stats(pa, pb, target=7, a_first=True):
    """(P(A wins the tiebreak), E[points])."""
    a_srv, b_srv = pa, 1 - pb
    won = np.zeros_like(pa)
    epts = np.zeros_like(pa)
    layer = {(0, 0): np.ones_like(pa)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if i == target - 1 and j == target - 1:
                s = a_srv * b_srv + (1 - a_srv) * (1 - b_srv)
                won += r * a_srv * b_srv / s
                epts += r * 2 / s
                continue
            epts += r
            w = a_srv if _tb_first(i + j) == a_first else b_srv
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1 - w)):
                if max(ni, nj) >= target and abs(ni - nj) >= 2:
                    if ni > nj:
                        won += r * pr
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return won, epts


def set_stats(pa, pb, tb_target=7, a_first=True):
    """(P(A wins the set), E[games], E[points], P(tiebreak)) for a set with a tiebreak at 6-6."""
    hold_a, ept_a = game_stats(pa)
    hold_b, ept_b = game_stats(pb)
    win = np.zeros_like(pa)
    eg = np.zeros_like(pa)
    ept = np.zeros_like(pa)
    ptb = np.zeros_like(pa)
    layer = {(0, 0): np.ones_like(pa)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if i == 6 and j == 6:
                tw, tp = tb_stats(pa, pb, tb_target, a_first=a_first)
                win += r * tw
                eg += r
                ept += r * tp
                ptb += r
                continue
            a_serves = ((i + j) % 2 == 0) == a_first
            w = hold_a if a_serves else 1 - hold_b
            eg += r
            ept += r * (ept_a if a_serves else ept_b)
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1 - w)):
                if max(ni, nj) >= 6 and abs(ni - nj) >= 2:
                    if ni > nj:
                        win += r * pr
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return win, eg, ept, ptb


def match_stats(pa, pb, best_of=3, final_target=7):
    """Expected sets, games, points and tiebreaks, P(at least one tiebreak), P(A wins); each set's first server
    averaged over both players (the win probability does not depend on it; the lengths barely do)."""
    pa, pb = np.broadcast_arrays(np.asarray(pa, dtype="float64"), np.asarray(pb, dtype="float64"))
    s1 = set_stats(pa, pb, 7, True)
    s2 = set_stats(pa, pb, 7, False)
    s = [(x + y) / 2 for x, y in zip(s1, s2)]
    if final_target == 7:
        f = s
    else:
        f1 = set_stats(pa, pb, final_target, True)
        f2 = set_stats(pa, pb, final_target, False)
        f = [(x + y) / 2 for x, y in zip(f1, f2)]
    need = (best_of + 1) // 2
    won = np.zeros_like(pa)
    esets = np.zeros_like(pa)
    egames = np.zeros_like(pa)
    epts = np.zeros_like(pa)
    etb = np.zeros_like(pa)
    p_no_tb = {(0, 0): np.ones_like(pa)}       # joint: reach probability with no tiebreak so far
    layer = {(0, 0): np.ones_like(pa)}
    p_none_total = np.zeros_like(pa)
    while layer:
        nxt: dict = {}
        nxt_none: dict = {}
        for (i, j), r in layer.items():
            st = f if (i == need - 1 and j == need - 1) else s
            w, g, pts, ptb = st
            r0 = p_no_tb[(i, j)]
            esets += r
            egames += r * g
            epts += r * pts
            etb += r * ptb
            for ni, nj, pr in ((i + 1, j, w), (i, j + 1, 1 - w)):
                # P(no tiebreak in this set and this set result): approximate the set result and the tiebreak
                # event as independent within a set only for the "no tiebreak" bookkeeping below
                if ni == need or nj == need:
                    if ni == need:
                        won += r * pr
                    p_none_total += r0 * pr * (1 - ptb)
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
                    nxt_none[(ni, nj)] = nxt_none.get((ni, nj), 0.0) + r0 * pr * (1 - ptb)
        layer = nxt
        p_no_tb = nxt_none
    return {"p_win": won, "e_sets": esets, "e_games": egames, "e_points": epts, "e_tiebreaks": etb,
            "p_any_tiebreak_approx": 1 - p_none_total}


def part_length():
    grid = [0.54, 0.58, 0.62, 0.66, 0.70, 0.74]
    out = {}
    for bo in (3, 5):
        rows = []
        for pa in grid:
            for pb in grid:
                st = match_stats(np.array([pa]), np.array([pb]), bo)
                rows.append({"pa": pa, "pb": pb, **{k: round(float(v[0]), 3) for k, v in st.items()}})
        out[f"bo{bo}"] = rows
    # equal-strength matchups along the dominance diagonal, and a fixed edge of 0.04
    diag = {}
    for bo in (3, 5):
        d = []
        for pbar in (0.52, 0.56, 0.60, 0.64, 0.68, 0.72, 0.76):
            st = match_stats(np.array([pbar + 0.02]), np.array([pbar - 0.02]), bo)
            d.append({"pbar": pbar, **{k: round(float(v[0]), 3) for k, v in st.items()}})
        diag[f"bo{bo}_edge0.04"] = d
    out["diagonal"] = diag
    return out


# ------------------------------------------------------------------------------------------------
# 3. Deuce court and ad court: where a service game's sensitivity lies

def hold_courts(pd_, pa_):
    """P(hold) when the server wins deuce-court points with pd_ and ad-court points with pa_.
    A point is on the deuce court when the points played in the game are even (0-0, 15-15, 30-0, 15-40, deuce)."""
    pd_, pa_ = np.broadcast_arrays(np.asarray(pd_, dtype="float64"), np.asarray(pa_, dtype="float64"))
    hold = np.zeros_like(pd_)
    layer = {(0, 0): np.ones_like(pd_)}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if i == 3 and j == 3:
                # deuce (deuce court); AD-in and AD-out are on the ad court
                win2 = pd_ * pa_
                lose2 = (1 - pd_) * (1 - pa_)
                hold += r * win2 / (win2 + lose2)
                continue
            p = pd_ if (i + j) % 2 == 0 else pa_
            for ni, nj, pr in ((i + 1, j, p), (i, j + 1, 1 - p)):
                if ni == 4:
                    hold += r * pr
                elif nj == 4:
                    pass
                else:
                    nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return hold


def expected_points_by_court(p):
    """Expected deuce-court and ad-court points per service game at a constant p."""
    p = float(p)
    q = 1 - p
    e = {"deuce": 0.0, "ad": 0.0, "bp_deuce": 0.0, "bp_ad": 0.0}
    layer = {(0, 0): 1.0}
    while layer:
        nxt: dict = {}
        for (i, j), r in layer.items():
            if i == 3 and j == 3:
                d = p * p + q * q
                pairs = 1 / d                       # expected visits to deuce
                e["deuce"] += r * pairs
                e["ad"] += r * pairs                # AD-in or AD-out after every deuce point
                e["bp_ad"] += r * pairs * q         # AD-out (a break point) follows a lost deuce point
                continue
            court = "deuce" if (i + j) % 2 == 0 else "ad"
            e[court] += r
            if j == 3:
                e["bp_" + court] += r
            for ni, nj, pr in ((i + 1, j, p), (i, j + 1, q)):
                if ni == 4 or nj == 4:
                    continue
                nxt[(ni, nj)] = nxt.get((ni, nj), 0.0) + r * pr
        layer = nxt
    return e


def part_court():
    out = []
    h = 1e-5
    for p in (0.50, 0.55, 0.58, 0.60, 0.62, 0.64, 0.66, 0.68, 0.70, 0.72, 0.75):
        dd = (hold_courts(p + h, p) - hold_courts(p - h, p)) / (2 * h)
        da = (hold_courts(p, p + h) - hold_courts(p, p - h)) / (2 * h)
        e = expected_points_by_court(p)
        base = float(hold_courts(p, p))
        split = {}
        for x in (0.02, 0.04):
            split[f"ad_plus_{x}"] = round(float(hold_courts(p - x, p + x)) - base, 5)
            split[f"deuce_plus_{x}"] = round(float(hold_courts(p + x, p - x)) - base, 5)
        out.append({
            "p": p, "hold": round(base, 4),
            "dH_d_deuce": round(float(dd), 4), "dH_d_ad": round(float(da), 4),
            "ad_share_of_sensitivity": round(float(da / (da + dd)), 4),
            "ad_share_of_points": round(e["ad"] / (e["ad"] + e["deuce"]), 4),
            "break_points_per_game_deuce": round(e["bp_deuce"], 4), "break_points_per_game_ad": round(e["bp_ad"], 4),
            "hold_change_from_split": split,
        })
    return out


# ------------------------------------------------------------------------------------------------
# 4. Composition

def part_composition():
    out = {}
    # (a) Two servers with the same serve points won against an average returner (men's averages), one landing
    # many first serves (H), one few (L); against returners who are better than average only on second serves
    # (R2) or only on first serves (R1), by 0.3 on the log-odds scale.
    sw = 0.499
    spw_target = 0.620
    servers = {}
    for name, fi in (("H_fi_0.68", 0.68), ("M_fi_0.608", 0.608), ("L_fi_0.54", 0.54)):
        fw = (spw_target - (1 - fi) * sw) / fi
        servers[name] = (fi, fw)
    returners = {"avg": (0.0, 0.0), "R2_second_specialist": (0.0, 0.3), "R1_first_specialist": (0.3, 0.0),
                 "both_0.15": (0.15, 0.15)}
    tab = {}
    for sname, (fi, fw) in servers.items():
        row = {"fi": round(fi, 3), "fw": round(fw, 4)}
        for rname, (d1, d2) in returners.items():
            spw = fi * sig(logit(fw) - d1) + (1 - fi) * sig(logit(sw) - d2)
            row[rname] = round(float(spw), 4)
        tab[sname] = row
    out["first_second_exposure"] = tab
    # match consequence: the H-vs-L gap against R2, turned into a match log-odds change at the men's averages
    gap = tab["H_fi_0.68"]["R2_second_specialist"] - tab["L_fi_0.54"]["R2_second_specialist"]
    m = logit(0.62)
    dl = logit(0.62 + gap) - logit(0.62)
    lev3 = float(match_logit(np.array([m]), np.array([dl]), "bo3")[0])
    out["first_second_exposure_gap_spw"] = round(float(gap), 4)
    out["first_second_exposure_gap_match_logit_bo3"] = round(lev3, 4)

    # (b) Free points. A serve point is free (ace or unreturned serve) with probability a, else a rally the server
    # wins with probability r. spw = a + (1 - a) r. The returner's rally skill moves r by t on the log-odds scale.
    # Sensitivity of logit(spw) to t, for servers with the same spw but different free-point shares.
    rows = []
    for spw in (0.60, 0.66, 0.72):
        for a in (0.10, 0.20, 0.30, 0.40, 0.50):
            if a >= spw:
                continue
            r = (spw - a) / (1 - a)
            sens = (1 - a) * r * (1 - r) / (spw * (1 - spw))
            rows.append({"spw": spw, "free_share": a, "rally_win": round(r, 4),
                         "dlogit_spw_per_unit_returner_rally_skill": round(sens, 4)})
    out["free_points_elasticity"] = rows
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    res = {"note": "outcome-free: iid-model arithmetic on synthetic probabilities; no data rows read",
           "leverage": part_leverage(), "length": part_length(), "court": part_court(),
           "composition": part_composition()}
    (OUT / "iid_mechanics.json").write_text(json.dumps(res, indent=1))
    lev = res["leverage"]
    print("pbar", lev["pbar"])
    for fmt in FORMATS:
        print(fmt, "leverage per unit logit edge (delta 0.02):", lev["formats"][fmt]["delta_0.02"]["per_unit"])
        print(fmt, "relative to pbar 0.62:", lev["formats"][fmt]["leverage_relative_to_pbar_0.62"])
        print(fmt, "per unit at delta 0.40:", lev["formats"][fmt]["delta_0.4"]["per_unit"])
    print("match logit for p_A - p_B = 0.02:", lev["match_logit_for_prob_edge_0.02"])
    print()
    for d in res["length"]["diagonal"]["bo3_edge0.04"]:
        print("bo3 edge 0.04", d)
    for d in res["length"]["diagonal"]["bo5_edge0.04"]:
        print("bo5 edge 0.04", d)
    print()
    for c in res["court"]:
        print(c)
    print()
    print(json.dumps(res["composition"], indent=1))


if __name__ == "__main__":
    main()
