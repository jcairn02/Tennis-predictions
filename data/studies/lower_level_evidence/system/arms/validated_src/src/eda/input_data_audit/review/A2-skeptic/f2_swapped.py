"""F2 review (A2-skeptic): box scores exchanged between winner and loser (88 matches of box_swapped_oct07.csv).

Per match:
  * the identity as recorded and exchanged (recomputed on the live Stage 0), the error k an exchanged fit needs,
    the points each player won, the games each won;
  * who advanced: the recorded winner / loser in the next round of the same event (Stage 0), the last qualifying
    round's winner in the main draw (entry Q / LL), finals and round robins have no next round;
  * independent records: the WTA API (2019-2026: winner, and whose box is whose; the API's own box fits its own
    score), the Match Charting Project (serve points, first serves in, aces, double faults per player), Infosys
    AO 2025 key statistics, official Slam feeds where held;
  * the raw Sackmann row (file, row), and Stage 0's D5 relabel (the recorded loser advanced: winner exchanged).
And for the whole population: how many exchanged fits coincidence would produce among the matches that fail the
identity for other reasons (permutation of the recorded error over failing matches), and how often the winner
wins fewer points in clean matches with the same games margin.
Writes data/studies/input_data_audit/fixes/A2-skeptic/f2_*.csv
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/f2_swapped.py
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import _common as K

NEXT = {"Q1": "Q2", "Q2": "Q3", "Q3": "Q4", "R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF", "QF": "SF",
        "SF": "F"}


def side_a(d: pd.DataFrame) -> pd.DataFrame:
    b = d[d["side"].eq("A")].copy()
    brk_a, brk_b = b["bp_faced"] - b["bp_saved"], b["o_bp_faced"] - b["o_bp_saved"]
    b["rec"] = b["sv_gms"] - brk_a + brk_b
    b["exch"] = b["o_sv_gms"] - brk_b + brk_a
    b["e"] = b["rec"] - b["games_won_n"]
    b["k"] = b["rec"] - b["exch"]
    b["pts_a"] = b["first_won"] + b["second_won"] + (b["o_svpt"] - b["o_first_won"] - b["o_second_won"])
    b["pts_b"] = b["o_first_won"] + b["o_second_won"] + (b["svpt"] - b["first_won"] - b["second_won"])
    won = b["won"].astype(bool)
    b["winner_pts"] = b["pts_a"].where(won, b["pts_b"])
    b["loser_pts"] = b["pts_b"].where(won, b["pts_a"])
    b["winner_games"] = b["games_won_n"].where(won, b["games_won_d"] - b["games_won_n"])
    b["loser_games"] = b["games_won_d"] - b["winner_games"]
    b["testable"] = (b["status"].eq("completed") & b["sv_gms"].notna() & b["o_sv_gms"].notna()
                     & b["tb_won_d"].fillna(-1).eq(0) & b["games_won_n"].notna())
    b["fails"] = b["testable"] & (b["rec"] != b["games_won_n"])
    b["swap_fit"] = b["fails"] & (b["exch"] == b["games_won_n"])
    return b


def coincidence(b: pd.DataFrame, cluster: set) -> dict:
    """Expected exchanged fits by coincidence among failing matches, by permuting the recorded error e over the
    failing matches that are not exchanged fits (their e is the 'other reasons' error), against each failing match's
    required k. Also stratified by |k|."""
    f = b[b["fails"]]
    other = f[~f["swap_fit"]]
    pe = other["e"].value_counts(normalize=True)
    f = f.assign(p_coinc=f["k"].map(pe).fillna(0.0))
    out = {"failing": int(len(f)), "failing_not_fit": int(len(other)), "swap_fits": int(f["swap_fit"].sum()),
           "expected_coincidental_fits_all_failing": float(f["p_coinc"].sum()),
           "expected_coincidental_fits_outside_clusters": float(f.loc[~f["match_id"].isin(cluster), "p_coinc"].sum()),
           "e_distribution_other": {int(k): round(float(v), 4) for k, v in pe.sort_index().items() if v >= 0.002}}
    return out, f


def main() -> None:
    d = K.stage0()
    m = pd.read_parquet(K.S0 / "stage0_matches.parquet")
    sw = pd.read_csv(K.AUDIT / "box_swapped_oct07.csv")
    b = side_a(d[d["has_box"]])
    cluster_ids = set(sw.loc[sw["edition"].str.contains("Abu Dhabi\\|2021|Phillip Island Trophy\\|2021"), "match_id"])

    # ---- coincidence estimate
    co, f = coincidence(b, cluster_ids)
    print({k: v for k, v in co.items() if k != "e_distribution_other"})
    print("e distribution among failing non-fits:", co["e_distribution_other"])
    # stratify by margin: how often the winner wins fewer points in clean testable matches, by games margin
    clean = b[b["testable"] & ~b["fails"]].copy()
    clean["margin"] = clean["winner_games"] - clean["loser_games"]
    clean["wfp"] = clean["winner_pts"] < clean["loser_pts"]
    wfp_by_margin = clean.groupby(clean["margin"].clip(-3, 8))["wfp"].agg(["mean", "size"])
    print("winner fewer points in clean matches, by games margin (winner - loser):")
    print(wfp_by_margin.to_string())

    # ---- the 88
    x = b[b["match_id"].isin(sw["match_id"])].copy()
    assert len(x) == 88, len(x)
    x = x.merge(f[["match_id", "p_coinc"]], on="match_id", how="left")
    x["margin"] = x["winner_games"] - x["loser_games"]
    x["p_wfp_if_box_right"] = x["margin"].clip(-3, 8).map(wfp_by_margin["mean"])
    x["p_coinc_fit"] = x["p_coinc"]

    # winner/loser ids
    x["winner_id"] = np.where(x["won"].astype(bool), x["player_id"], x["o_player_id"])
    x["loser_id"] = np.where(x["won"].astype(bool), x["o_player_id"], x["player_id"])
    x["winner_name"] = np.where(x["won"].astype(bool), x["player_name"], x["o_player_name"])
    x["loser_name"] = np.where(x["won"].astype(bool), x["o_player_name"], x["player_name"])

    # ---- progression in Stage 0
    allm = d[["match_id", "tour", "tournament_id", "round", "player_id", "entry", "qualifying"]]
    seen = set(zip(allm["tour"], allm["tournament_id"], allm["round"], allm["player_id"]))
    main_entry = allm[~allm["qualifying"]].groupby(["tour", "tournament_id", "player_id"])["entry"].first()
    in_main = set(zip(allm.loc[~allm["qualifying"], "tour"], allm.loc[~allm["qualifying"], "tournament_id"],
                      allm.loc[~allm["qualifying"], "player_id"]))
    rounds_held = set(zip(allm["tour"], allm["tournament_id"], allm["round"]))
    prog, note = [], []
    for r in x.itertuples():
        nxt = NEXT.get(r.round)
        if r.round == "RR" or r.level == "TEAM":
            prog.append("no next round (team tie / round robin)")
            note.append("")
            continue
        if r.round == "F":
            prog.append("final")
            note.append("")
            continue
        if nxt and (r.tour, r.tournament_id, nxt) in rounds_held:
            w_on = (r.tour, r.tournament_id, nxt, r.winner_id) in seen
            l_on = (r.tour, r.tournament_id, nxt, r.loser_id) in seen
            prog.append({(True, False): "winner advanced", (False, True): "LOSER advanced",
                         (True, True): "both in next round", (False, False): "neither in next round"}[(w_on, l_on)])
            note.append("")
            continue
        if r.qualifying:
            w_in = (r.tour, r.tournament_id, r.winner_id) in in_main
            l_in = (r.tour, r.tournament_id, r.loser_id) in in_main
            we = main_entry.get((r.tour, r.tournament_id, r.winner_id), None)
            le = main_entry.get((r.tour, r.tournament_id, r.loser_id), None)
            prog.append({(True, False): "winner in main draw", (False, True): "LOSER in main draw",
                         (True, True): "both in main draw", (False, False): "neither in main draw"}[(w_in, l_in)])
            note.append(f"winner entry {we}, loser entry {le}")
            continue
        prog.append("next round not held")
        note.append("")
    x["progression"], x["progression_note"] = prog, note

    # ---- raw row and D5
    mm = m.set_index("match_id")
    x["source_file"] = x["match_id"].map(mm["source_file"])
    x["source_row"] = x["match_id"].map(mm["source_row"])
    raws = {}
    for tour in ("atp", "wta"):
        r = K.sackmann(tour)
        raws[tour] = r.set_index(["_source_file", "_row"])
    raw_w, raw_l, raw_score = [], [], []
    for r in x.itertuples():
        try:
            rr = raws[r.tour].loc[(r.source_file, int(r.source_row))]
            if isinstance(rr, pd.DataFrame):
                rr = rr.iloc[0]
            raw_w.append(rr["winner_name"]), raw_l.append(rr["loser_name"]), raw_score.append(rr["score"])
        except KeyError:
            raw_w.append(None), raw_l.append(None), raw_score.append(None)
    x["raw_winner"], x["raw_loser"], x["raw_score"] = raw_w, raw_l, raw_score
    x["d5_relabelled"] = [K.name_key(a) != K.name_key(b) if a is not None else None
                          for a, b in zip(x["raw_winner"], x["winner_name"])]

    # ---- WTA API
    api = K.wta_api()
    api["pair"] = [frozenset((a, b)) for a, b in zip(api["ka"], api["kb"])]
    x["kw"], x["kl"] = x["winner_name"].map(K.name_key), x["loser_name"].map(K.name_key)
    res = []
    for r in x.itertuples():
        if r.tour != "wta":
            res.append({})
            continue
        cand = api[(api["year"].astype(str) == str(r.year)) & (api["pair"] == frozenset((r.kw, r.kl)))]
        tid = str(r.tournament_id).split("-")[-1]
        if len(cand) > 1:
            c2 = cand[cand["tournament_id"].astype(str) == tid]
            cand = c2 if len(c2) else cand
        if len(cand) != 1:
            res.append({"api_found": len(cand)})
            continue
        a = cand.iloc[0]
        w_side = "a" if a["ka"] == r.kw else "b"
        l_side = "b" if w_side == "a" else "a"
        api_winner_is_recorded = a["winner_side"] == w_side
        # Stage 0 boxes of recorded winner / loser
        if r.won:
            sw_box = [getattr(r, c) for c in K.BOX]
            sl_box = [getattr(r, f"o_{c}") for c in K.BOX]
        else:
            sl_box = [getattr(r, c) for c in K.BOX]
            sw_box = [getattr(r, f"o_{c}") for c in K.BOX]
        aw = [a[f"{w_side}_{c}"] for c in K.BOX]
        al = [a[f"{l_side}_{c}"] for c in K.BOX]
        same = sum(float(p) == float(q) for p, q in zip(sw_box, aw)) + sum(float(p) == float(q) for p, q in zip(sl_box, al))
        cross = sum(float(p) == float(q) for p, q in zip(sw_box, al)) + sum(float(p) == float(q) for p, q in zip(sl_box, aw))
        # the API's own identity for its own winner side
        g_w = a[f"games_{w_side}"]
        id_w = a[f"{w_side}_sv_gms"] - (a[f"{w_side}_bp_faced"] - a[f"{w_side}_bp_saved"]) + (a[f"{l_side}_bp_faced"] - a[f"{l_side}_bp_saved"])
        res.append({"api_found": 1, "api_key": a["key"], "api_result": a["ResultString"],
                    "api_winner_is_recorded_winner": bool(api_winner_is_recorded),
                    "api_counts_equal_as_recorded_of18": int(same), "api_counts_equal_exchanged_of18": int(cross),
                    "api_own_identity_holds": bool(id_w == g_w) if not a["any_tb"] else None,
                    "api_winner_pts_more": None})
    x = pd.concat([x.reset_index(drop=True), pd.DataFrame(res)], axis=1)

    # ---- MCP
    rows = []
    for g, tour in (("m", "atp"), ("w", "wta")):
        mc = K.mcp(g)
        mc = mc[mc["date"].dt.year.between(2009, 2026)]
        xs = x[x["tour"].eq(tour)]
        for r in xs.itertuples():
            c = mc[(mc["pk"] == r.kw) & (mc["ok"] == r.kl)]
            c = c[(c["date"] - r.tournament_date).dt.days.between(-1, 16)]
            if c.empty:
                continue
            wrow = c.iloc[0]
            lrow = mc[(mc["match_id"] == wrow["match_id"]) & (mc["pk"] == r.kl)]
            if lrow.empty:
                continue
            lrow = lrow.iloc[0]
            if r.won:
                swb = {c_: getattr(r, c_) for c_ in K.BOX}
                slb = {c_: getattr(r, f"o_{c_}") for c_ in K.BOX}
            else:
                slb = {c_: getattr(r, c_) for c_ in K.BOX}
                swb = {c_: getattr(r, f"o_{c_}") for c_ in K.BOX}
            pairs = [("svpt", "serve_pts"), ("first_in", "first_in"), ("ace", "aces"), ("df", "dfs")]
            rec = sum(abs(swb[a] - wrow[b_]) + abs(slb[a] - lrow[b_]) for a, b_ in pairs)
            exc = sum(abs(swb[a] - lrow[b_]) + abs(slb[a] - wrow[b_]) for a, b_ in pairs)
            rows.append({"match_id": r.match_id, "mcp_match": wrow["match_id"], "mcp_abs_diff_as_recorded": rec,
                         "mcp_abs_diff_exchanged": exc})
    mcpd = pd.DataFrame(rows)
    if len(mcpd):
        x = x.merge(mcpd, on="match_id", how="left")
    else:
        x["mcp_match"] = None

    x.to_csv(K.OUT / "f2_detail.csv", index=False)
    show = ["match_id", "round", "score", "winner_name", "loser_name", "winner_games", "loser_games", "winner_pts",
            "loser_pts", "e", "k", "p_coinc_fit", "p_wfp_if_box_right", "progression", "progression_note",
            "d5_relabelled", "api_found", "api_winner_is_recorded_winner", "api_counts_equal_as_recorded_of18",
            "api_counts_equal_exchanged_of18", "api_own_identity_holds", "mcp_abs_diff_as_recorded",
            "mcp_abs_diff_exchanged"]
    pd.set_option("display.width", 400)
    pd.set_option("display.max_colwidth", 60)
    print(x[[c for c in show if c in x]].to_string())


if __name__ == "__main__":
    main()
