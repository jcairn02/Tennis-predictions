"""R1-rederive (SVX addendum): swapped service games at the Australian Open 2018-2024 and 2026, and Roland Garros
2013-2015, with the same proof, truth and checks as svx_truth.py / svx_checks.py (imported, not copied).

Inputs (mine): work/svx_files_add.parquet, work/svx_games_add.parquet (svx_parse.py --addendum: my decryption and
recount of the new files); work/stage0_old_rows.parquet (Stage 0's raw rows of these editions, one load of
stage0_build.normalise(load_raw())). Files are linked to Stage 0's rows by names within year, event, tour and round
(optimal assignment; RG's codes give its rounds as before, the AO's their round digit). The decided row corrections of
8 Oct are checked for rows they already change (exchanging twice would undo them; the build refuses a row named twice).

First pass (no argument): my list (svx_rows_add.csv, svx_mine_add.csv), before the lead's is read.
Second pass (--compare): the lead's list (addendum_swaps.csv, or addendum2_swaps.csv with --tag add2) against mine; the swaps of that
list I confirm appended to swaps_scope.csv (earlier addendum rows replaced, my 323 rows untouched); an "SVX_addendum"
entry added to verdict.json (SVX_addendum2 with --tag add2). Full order: write_outputs.py; addendum.py --compare;
svx_outputs.py; svx_addendum.py; svx_addendum.py --tag add2; svx_tolerant.py; svx_addendum.py --compare;
svx_addendum.py --tag add2 --compare.
Run: ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/svx_addendum.py [--compare]
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
WORK = HERE / "work"
S = "src/eda/rg_first_serve_recount/review_followup/R1-rederive/"
# which addendum: --tag add (AO 2018-2024 and 2026, RG 2013-2015; the default) or --tag add2 (RG 2016-2018)
TAG = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "add"
CFG = {"add": {"rows": "stage0_old_rows.parquet", "lead": "addendum_swaps.csv", "key": "SVX_addendum",
               "editions": "AO 2018-2024 and 2026 on the static match-beats route; RG 2013-2015 on the API route"},
       "add2": {"rows": "stage0_old_rows_rg1618.parquet", "lead": "addendum2_swaps.csv", "key": "SVX_addendum2",
                "editions": "RG 2016-2018 on the API route; 16 codes of RG 2016 have no file on either route"}}[TAG]
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / CFG["lead"]
OUTTAG = f"_{TAG}"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"r1_{name}", Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = load("svx_truth")      # prove, classify, report, toks, sim, AO_ROUND, AO_QROUND
CK = load("svx_checks")    # reg_won


def rg_round(code: str) -> str:
    fam, n = code[:2], int(code[2:])
    table = ((1, 1, "F"), (2, 2, "SF"), (4, 4, "QF"), (8, 8, "R16"), (16, 16, "R32"), (32, 32, "R64"),
             (64, 64, "R128")) if fam in ("SM", "SD") else ((16, 16, "Q3"), (32, 32, "Q2"), (64, 64, "Q1"))
    for first, k, rnd in table:
        if first <= n < first + k:
            return rnd
    return "?"


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_rows", 300)
    files = pd.read_parquet(WORK / f"svx_files{OUTTAG}.parquet")
    games = pd.read_parquet(WORK / f"svx_games{OUTTAG}.parquet")
    files = files[files["status"].eq("ok")].copy()
    gx = {k: g.sort_values("order") for k, g in games.groupby(["slam", "year", "code"])}
    rows = pd.read_parquet(WORK / CFG["rows"])
    rows = rows[rows["s0_match_id"].notna()].copy()            # the rows Stage 0 keeps
    rows["slam"] = np.where(rows["tourney_name"].str.contains("australian", case=False), "AO", "RG")
    rows["year"] = rows["season"].astype(int)
    files["tour"] = np.where(files["slam"].eq("AO"), np.where(files["code"].str[0].eq("M"), "atp", "wta"),
                             np.where(files["code"].str[:2].isin(["SM", "QM"]), "atp", "wta"))
    files["round"] = [(T.AO_QROUND if c[1] == "Q" else T.AO_ROUND)[c[2]] if s == "AO" else rg_round(c)
                      for s, c in zip(files["slam"], files["code"])]
    rec = []
    for (slam, year, tour, rnd), grp in files.groupby(["slam", "year", "tour", "round"]):
        rr = rows[rows["slam"].eq(slam) & rows["year"].eq(year) & rows["tour"].eq(tour) & rows["round"].eq(rnd)]
        if rr.empty:
            continue
        fl, rl = grp.to_dict("records"), rr.to_dict("records")
        t1 = [T.toks(f"{f['first1']} {f['last1']}") for f in fl]
        t2 = [T.toks(f"{f['first2']} {f['last2']}") for f in fl]
        tw = [T.toks(r["winner_name"]) for r in rl]
        tl = [T.toks(r["loser_name"]) for r in rl]
        sc = np.array([[max(T.sim(t1[i], tw[j]) + T.sim(t2[i], tl[j]), T.sim(t1[i], tl[j]) + T.sim(t2[i], tw[j]))
                        for j in range(len(rl))] for i in range(len(fl))])
        for i, j in zip(*linear_sum_assignment(-sc)):
            if sc[i, j] < 1.0:
                continue
            f, r = fl[i], rl[j]
            one_w = T.sim(t1[i], tw[j]) + T.sim(t2[i], tl[j]) >= T.sim(t1[i], tl[j]) + T.sim(t2[i], tw[j])
            rec.append({"slam": slam, "year": int(year), "code": f["code"], "rid": int(r["rid"]),
                        "w_pid": f["id1"] if one_w else f["id2"], "l_pid": f["id2"] if one_w else f["id1"],
                        "link_sim": min(T.sim(t1[i] if one_w else t2[i], tw[j]),
                                        T.sim(t2[i] if one_w else t1[i], tl[j])),
                        "winner_agrees": f["match_winner"] == ("1" if one_w else "2"),
                        "mb_w_name": f"{f['first1']} {f['last1']}" if one_w else f"{f['first2']} {f['last2']}",
                        "mb_l_name": f"{f['first2']} {f['last2']}" if one_w else f"{f['first1']} {f['last1']}"})
    lk = pd.DataFrame(rec)
    linked = set(lk["rid"])
    lk = lk.merge(rows[["rid", "source", "tour", "round", "season", "winner_name", "loser_name", "score", "w_SvGms",
                        "l_SvGms", "w_bpFaced", "w_bpSaved", "l_bpFaced", "l_bpSaved", "_source_file", "_row",
                        "s0_match_id", "tourney_id"]], on="rid", how="left")
    lk = lk.merge(files[["slam", "year", "code", "route", "id1", "id2", "order_ok", "games", "first_set", "first_game",
                         "first_server", "first_gs1", "first_gs2", "match_complete"]], on=["slam", "year", "code"],
                  how="left")
    lk = lk.rename(columns={"_source_file": "source_file", "_row": "source_row"})
    x = T.classify(T.prove(lk, gx))
    # the break identity (svx_checks.py), from the row's own score and break points
    rw = np.array([CK.reg_won(s) for s in x["score"].fillna("")])
    x["reg_w"], x["reg_l"] = rw[:, 0], rw[:, 1]
    bw, bl = x["w_bpFaced"] - x["w_bpSaved"], x["l_bpFaced"] - x["l_bpSaved"]
    x["bp_sv_w"], x["bp_sv_l"] = x["reg_w"] + bw - bl, x["reg_l"] + bl - bw
    x["bp_eq_truth"] = x["bp_sv_w"].eq(x["t_w"]) & x["bp_sv_l"].eq(x["t_l"])
    x["bp_eq_row"] = x["bp_sv_w"].eq(x["w_SvGms"]) & x["bp_sv_l"].eq(x["l_SvGms"])
    # rows the decided corrections of 8 Oct already change
    rc = pd.read_csv(ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "row_corrections.csv", dtype=str,
                     keep_default_na=False)
    key = x["source_file"].astype(str) + "#" + x["source_row"].astype("Int64").astype(str)
    rck = rc.assign(k=rc["source_file"] + "#" + rc["source_row"]).set_index("k")
    x["decided_action"] = key.map(lambda k: ",".join(rck.loc[[k], "fix"] + ":" + rck.loc[[k], "action"])
                                  if k in rck.index else "")
    x["excluded"] = x["decided_action"].ne("")
    T.report(x, tag=OUTTAG)
    sw = x[x["cls"].eq("swapped")]
    comp = ~sw["score"].fillna("").str.contains("RET|DEF|W/O", regex=True)
    print("\nrows Stage 0 keeps:", len(rows), "| linked to a file:", len(linked), "| rows without a file:",
          len(rows) - len(linked))
    print("swapped:", len(sw), "| excluded (decided corrections):", sw[sw["excluded"]][["slam", "year", "code",
                                                                                         "winner_name", "loser_name",
                                                                                         "decided_action"]].to_dict(
        "records"))
    print("break identity on the swaps: completed", int(sw.loc[comp, "bp_eq_truth"].sum()), "of", int(comp.sum()),
          "| retirements", int(sw.loc[~comp, "bp_eq_truth"].sum()), "of", int((~comp).sum()),
          "| equal to the row as recorded:", int(sw["bp_eq_row"].sum()))
    print(sw[~sw["bp_eq_truth"]][["slam", "year", "code", "score", "w_SvGms", "l_SvGms", "t_w", "t_l", "bp_sv_w",
                                  "bp_sv_l", "w_bpFaced", "w_bpSaved", "l_bpFaced", "l_bpSaved"]].to_string())
    print("links of the swaps: similarity < 1:", int((sw["link_sim"] < 1).sum()), "| winner disagrees:",
          int((~sw["winner_agrees"].astype(bool)).sum()))
    print(sw[sw["link_sim"] < 1][["slam", "year", "code", "winner_name", "mb_w_name", "loser_name", "mb_l_name",
                                  "link_sim"]].to_string())
    print("B8 after the exchange fails on", int((~sw["b8_after_ok"].astype(bool)).sum()), "| before:",
          int((~sw["b8_before_ok"].astype(bool)).sum()))
    pc = x[x["proof"].eq("proven") & ~x["score"].fillna("").str.contains("RET|DEF|W/O", regex=True)
           & x["w_bpFaced"].notna()]
    print("break identity on all proven completed rows: equals the truth on", int(pc["bp_eq_truth"].sum()), "of",
          len(pc), "| by edition misses:", pc[~pc["bp_eq_truth"]].groupby(["slam", "year"]).size().to_dict())
    x.to_csv(HERE / f"svx_checked{OUTTAG}.csv", index=False)
    if "--compare" not in sys.argv:
        return
    compare_and_write(x)


def compare_and_write(x: pd.DataFrame) -> None:
    lead = pd.read_csv(LEAD, dtype=str, keep_default_na=False)
    lead["key"] = lead["source_file"] + "#" + lead["source_row"]
    x = x.copy()
    x["key"] = x["source_file"].astype(str) + "#" + x["source_row"].astype("Int64").astype(str)
    # the strict proof's swaps, and those of the glitch-tolerant reading (svx_tolerant.py: a local glitch of at most
    # three records in one set, every other game on the alternation, the break identity agreeing)
    tol = pd.read_csv(HERE / "svx_tolerant.csv", low_memory=False)
    tol = tol[tol["rows"].eq(f"svx_checked{OUTTAG}.csv") & tol["tolerant_proof"].astype(bool) & tol["cls"].eq("swapped")
              & tol["t4_break_identity"].astype(str).eq("True")]
    tol_keys = set(tol["source_file"] + "#" + tol["source_row"].astype(int).astype(str))
    x["tolerant_swap"] = x["key"].isin(tol_keys) & ~x["excluded"].astype(bool)
    for k in tol_keys:          # the tolerant truth, for the verdict's tallies
        t = tol[(tol["source_file"] + "#" + tol["source_row"].astype(int).astype(str)) == k].iloc[0]
        x.loc[x["key"].eq(k), ["t_w", "t_l"]] = [t["t_w"], t["t_l"]]
    x["bp_eq_truth"] = x["bp_sv_w"].eq(x["t_w"]) & x["bp_sv_l"].eq(x["t_l"])
    x["b8_after_ok"] = ((x["w_bpFaced"] - x["w_bpSaved"]) <= x["l_SvGms"]) & \
        ((x["l_bpFaced"] - x["l_bpSaved"]) <= x["w_SvGms"])
    mine = x[(x["cls"].eq("swapped") & ~x["excluded"].astype(bool)) | x["tolerant_swap"]]
    res_tol = sorted(x.loc[x["tolerant_swap"], "slam"].astype(str) + " " + x.loc[x["tolerant_swap"], "year"].astype(str)
                     + " " + x.loc[x["tolerant_swap"], "code"].astype(str))
    lk, mk = set(lead["key"]), set(mine["key"])
    res = {"lead": len(lk), "mine": len(mk), "both": len(lk & mk), "lead_only": sorted(lk - mk),
           "mine_only": sorted(mk - lk), "by_the_tolerant_reading": res_tol}
    mid = mine.set_index("key")["s0_match_id"]
    res["match_ids_equal"] = int(sum(mid.get(k) == m for k, m in zip(lead["key"], lead["match_id"]) if k in mk))
    res["lead_by_edition"] = lead.groupby("tourney_id").size().to_dict()
    lo = x[x["key"].isin(lk - mk)]
    res["lead_only_detail"] = lo[["slam", "year", "code", "score", "w_SvGms", "l_SvGms", "t_w", "t_l", "cls", "proof",
                                  "p1_order", "p2_opens", "p3_alternation", "p4_sets", "games_off", "bp_sv_w",
                                  "bp_sv_l", "decided_action"]].to_dict("records")
    res["lead_only_not_linked"] = sorted((lk - mk) - set(x["key"]))
    mo = x[x["key"].isin(mk - lk)]
    res["mine_only_detail"] = mo[["slam", "year", "code", "score", "w_SvGms", "l_SvGms", "t_w", "t_l",
                                  "bp_sv_w", "bp_sv_l"]].to_dict("records")
    (HERE / f"svx{OUTTAG}_compare.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))
    # append the swaps of the lead's list that I confirm; every earlier row (other lists) stays as it is
    sc = pd.read_csv(HERE / "swaps_scope.csv", dtype=str, keep_default_na=False)
    sc = sc[~(sc["source_file"] + "#" + sc["source_row"]).isin(lk)]
    app = mine[mine["key"].isin(lk)].copy()
    app["source_row"] = app["source_row"].astype(int).astype(str)
    app = app.rename(columns={"s0_match_id": "match_id"})[["source_file", "source_row", "match_id"]]
    out = pd.concat([sc, app], ignore_index=True)
    out.to_csv(HERE / "swaps_scope.csv", index=False)
    print("swaps_scope.csv:", len(sc), "rows kept,", len(app), "appended")
    # the verdict entry
    sw = mine[mine["key"].isin(lk)]
    by = sw.groupby(["slam", "year"]).size()
    comp = ~sw["score"].fillna("").str.contains("RET|DEF|W/O", regex=True)
    pr = x[x["proof"].eq("proven")]
    whole = pr[pr["mb_whole"].astype(str).eq("True")]
    whole_eq = int((whole["mb_w"].eq(whole["t_w"]) & whole["mb_l"].eq(whole["t_l"])).sum())
    excl = x[x["cls"].eq("swapped") & x["excluded"].astype(bool)]
    v = json.loads((HERE / "verdict.json").read_text(encoding="utf-8"))
    ed = "; ".join(f"{s} {y} {n}" for (s, y), n in by.items())
    scope = (f"{res['both']} of the {res['lead']} added swaps ({ed}), appended to swaps_scope.csv with the same source "
             f"rows and match ids ({res['match_ids_equal']} equal). My own derivation, made before reading the list, "
             f"found {res['both'] - len(res_tol)} of them by the strict proof.")
    if len(excl):
        scope += (" It also found the swap the decided correction F2y already makes ("
                  + ", ".join(f"{r.slam} {r.year} {r.winner_name} d. {r.loser_name}" for r in excl.itertuples())
                  + "), which I leave out as the lead does: exchanging it again would undo it, and the build refuses "
                    "a row named twice.")
    if "AO 2024 MS136" in res_tol:
        scope += (" AO 2024 MS136 passes a glitch-tolerant reading of the proof (svx_tolerant.py). Set 4 of its file "
                  "repeats game 4 (one point) and its game 5 names both servers; the other 50 game records, set 1 game "
                  "1 among them, follow the alternation with Safiullin serving first. The break identity "
                  "independently gives the same truth (Griekspoor 25, Safiullin 26; the row 26/25). Applied to every "
                  "unproven file of both rounds, that reading proves no other swap.")
    elif res_tol:
        scope += (f" {'; '.join(res_tol)} pass(es) the glitch-tolerant reading (svx_tolerant.py: a local glitch of at "
                  "most three records in one set, every other game on the alternation, the break identity agreeing).")
    elif TAG == "add2":
        scope += (" The glitch-tolerant reading (svx_tolerant.py), applied to this round's unproven files, proves no "
                  "swap.")
    if not res["lead_only"] and not res["mine_only"]:
        scope += " None added, none dropped."
    v[CFG["key"]] = {
        "vote": "confirm" if res["both"] == res["lead"] else "narrow",
        "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
        "scope": scope,
        "reasons": "The same method and checks as SVX, from my own decryption and recount of the new files ("
                   + CFG["editions"] + "): the first "
                   "server is proven (games in order; the first game is set 1 game 1; every game held follows the "
                   "alternation, a tiebreak by its first point; each set held whole has the row's games by the games' "
                   "winners), and the truth comes from the row's own score (a tiebreak takes its turn uncounted, the "
                   "AO's final-set 10-point tiebreak at 6-6 from 2019 included; a retirement's finished games only). "
                   f"Where MatchBeats holds every game its own count equals the truth on {whole_eq} of {len(whole)} "
                   "proven rows. The break identity (service games = non-tiebreak games won + breaks conceded - "
                   "breaks made, from the row's own score and break points, without MatchBeats) gives the truth on "
                   f"{int(sw['bp_eq_truth'].sum())} of {len(sw)} swaps and the row as recorded on "
                   f"{int(sw['bp_eq_row'].sum())}. So each row's two counts contradict its own score and break "
                   "points as well as the point record: corrupt beyond doubt. The exchange gives exactly the truth, "
                   "keeps the total (B5), passes B8 on every row "
                   f"({int((~sw['b8_after_ok'].astype(bool)).sum())} failures after, "
                   f"{int((~sw['b8_before_ok'].astype(bool)).sum())} before), and no other decided table touches these "
                   "rows: clear, unique and correct. Links: every file paired with its Stage 0 row by names within "
                   "event, tour and round, MatchBeats' match winner equal to the row's winner on every swap"
                   f"{'' if (sw['link_sim'] >= 1).all() else '; the names short of an exact match are transliterations or married names, reviewed'}.",
        "checks": [
            (S + "stage0_old_rows.py: Stage 0's raw rows of AO 2018-2024, 2026 and RG 2013-2015 read once with "
             "stage0_build.normalise(load_raw()) (Sackmann's WTA rows of RG 2013-2015 carry another tournament id; "
             "taken by name).") if TAG == "add" else
            (S + "stage0_old_rows.py --rg2016-2018: Stage 0's raw rows of RG 2016-2018 read once with "
             "stage0_build.normalise(load_raw()) (450 Sackmann rows a year)."),
            S + f"svx_parse.py {'--addendum' if TAG == 'add' else '--addendum2'}: every file of these editions "
            "decrypted with the adapter's blocks_of/decrypt and recounted (games, servers, order, winners).",
            S + f"svx_addendum.py --tag {TAG}: links, proof and truth (svx_truth.prove/classify), the break identity, "
            "B8, the decided corrections; then the lead's list: " + f"{res['both']} of {res['lead']} equal, "
            f"{len(res['mine_only'])} of mine outside it, {len(res['lead_only'])} of it outside mine."],
    }
    e = v[CFG["key"]]
    # swaps where the break identity backs the row (not the point record), and files whose match-winner field
    # disagrees with the row: said plainly, with what settles them
    if TAG == "add2":      # no final-set tiebreak at RG before 2022: the AO's clause does not apply here
        e["reasons"] = e["reasons"].replace(", the AO's final-set 10-point tiebreak at 6-6 from 2019 included", "")
    back_row = sw[sw["bp_eq_row"].astype(bool)]
    if len(back_row):
        new = ("So the rows' two counts contradict their own score and break points as well as the point record, all "
               f"but {len(back_row)}: corrupt beyond doubt.")
        if TAG == "add2" and ((back_row["year"] == 2016) & (back_row["code"] == "SD014")).any():
            new += (" The exception is RG 2016 SD014 (Stosur d. Halep 7-6(0) 6-3). There the break identity backs the "
                    "row's 11/10, because the row's break points have Halep losing serve twice where the point "
                    "record's games show three times. The row's 11/10 needs Halep to have served first. Read that way, "
                    "the record's game winners, which reproduce the 7-6 6-3 score exactly, would put ten breaks in set "
                    "1 alone, against the row's own three in the match. Read with Stosur serving first (every one of its "
                    "22 games on the alternation, 17 of 21 service games held), they differ from the row's break "
                    "points by that one Halep break. The row's service games are the inconsistent count; I confirm the "
                    "swap.")
        e["reasons"] = e["reasons"].replace(
            "So each row's two counts contradict its own score and break points as well as the point record: corrupt "
            "beyond doubt.", new)
    wd = sw[~sw["winner_agrees"].astype(bool)]
    if len(wd):
        new = f"; on {len(wd)} swaps the file's match-winner field does not name the row's winner"
        if TAG == "add2":
            new += (" (RG 2016 SM023 and RG 2018 SM091: the field is missing, '0'; RG 2016 SD070: it names Allertova, "
                    "though Nara played the next round), while in each the game winners give the row's score from the "
                    "row winner's side")
        e["reasons"] = e["reasons"].replace(", MatchBeats' match winner equal to the row's winner on every swap", new)
    (HERE / "verdict.json").write_text(json.dumps(v, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"verdict.json: {CFG['key']} entry written")


if __name__ == "__main__":
    main()
