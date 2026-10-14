"""R1-rederive (group SVS): service games set from the score where the row's are blank, zero or wrong without being
an exchange. My derivation first; the lead's proposed_sets.csv only with --compare.

Inputs (mine): svx_checked.csv (RG 2019-2026, AO 2025), svx_checked_add.csv (AO 2018-2024 and 2026, RG 2013-2015),
svx_checked_add2.csv (RG 2016-2018), svx_tolerant.csv (the glitch-tolerant reading); Stage 0's raw rows of those
editions (work/stage0_*rows*.parquet, read with stage0_build.normalise(load_raw())) for the serve points and the other
counts; my overrides_scope.csv, exchanges_scope.csv, round 1's confirmed split rows and the decided row corrections.

A row is a set I confirm when all hold:
  S1  the first server is proven: my strict proof (svx_truth.prove: P1-P4), or the glitch-tolerant reading with the
      break identity agreeing (svx_tolerant.py);
  S2  serve points played and break points recorded for both players (another blank count is reported: the box
      then stays partial until it is filled too);
  S3  the row's service games are missing, or 0 with serve points played ("fill"), or numbers that differ from the
      truth without being the truth exchanged ("other"); an "other" row whose counts are the truth with the tiebreaks
      counted as service games (the convention Stage 0's B5 also accepts) is listed apart, as a convention, not an error;
  S4  the consistency test: each player's non-tiebreak games won = the truth's service games - breaks conceded + breaks
      made, breaks from the row's own break points (the break identity of svx_checks.py);
  S5  no other table of the candidate changes the row (my confirmed overrides, the RGX exchanges, round 1's split rows,
      the decided row corrections, the swaps);
  S6  Stage 0's B5 and B8 pass with the new counts.
The values: the truth (both players).
Writes svs_rows.csv (every candidate with each test) and svs_mine.csv. Run:
  ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/svs.py [--compare]
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
WORK = HERE / "work"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "service_games" / "proposed_sets.csv"
S = "src/eda/rg_first_serve_recount/review_followup/R1-rederive/"
EIGHT = ["ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "bpSaved", "bpFaced"]


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"r1_{name}", Path(__file__).with_name(f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = load("svx_truth")


def tb_turns(score: str, first_is_w: bool) -> tuple[int, int]:
    """Tiebreak turns of the row's winner and loser in the alternation (who serves first in each tiebreak)."""
    sets, _ = T.sets_of(score)
    pos, tw, tl = 0, 0, 0
    for a, b in sets:
        n = a + b
        tb = max(a, b) == 7 and min(a, b) == 6
        pos += n
        if tb:
            w_turn = (pos % 2 == 1) == first_is_w
            tw, tl = tw + w_turn, tl + (not w_turn)
    return tw, tl


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_rows", 400)
    parts = []
    for f in ("svx_checked.csv", "svx_checked_add.csv", "svx_checked_add2.csv"):
        p = pd.read_csv(HERE / f, low_memory=False)
        p["table"] = f
        parts.append(p)
    x = pd.concat(parts, ignore_index=True)
    x["key"] = x["source_file"].astype(str) + "#" + x["source_row"].astype("Int64").astype(str)
    # the tolerant reading: its proven rows take its truth
    tol = pd.read_csv(HERE / "svx_tolerant.csv", low_memory=False)
    tol = tol[tol["tolerant_proof"].astype(bool) & tol["t4_break_identity"].astype(str).eq("True")]
    tol["key"] = tol["source_file"] + "#" + tol["source_row"].astype(int).astype(str)
    x["tolerant"] = x["key"].isin(set(tol["key"])) & x["proof"].ne("proven")
    tt = tol.set_index("key")
    for c in ("t_w", "t_l"):
        x.loc[x["tolerant"], c] = x.loc[x["tolerant"], "key"].map(tt[c])
    x["s1_proven"] = x["proof"].eq("proven") | x["tolerant"]
    # the rows' other counts (serve points etc.), from Stage 0's raw rows
    raws = []
    for f in ("stage0_rg_rows.parquet", "stage0_ao_rows.parquet", "stage0_old_rows.parquet",
              "stage0_old_rows_rg1618.parquet"):
        r = pd.read_parquet(WORK / f, columns=["rid"] + [f"{s}_{c}" for s in "wl" for c in EIGHT])
        raws.append(r)
    raw = pd.concat(raws, ignore_index=True).drop_duplicates("rid")
    x = x.merge(raw, on="rid", how="left", suffixes=("", "_raw"))
    # S2: serve points played and break points recorded for both players (the fill's premise and the consistency
    # test's inputs); a row with another count blank as well (RG 2013-2014: double faults) is kept and reported, its
    # box staying partial (Stage 0 drops it, C23) until that count is filled too
    x["s2_complete"] = x[["w_svpt", "l_svpt", "w_bpFaced", "w_bpSaved", "l_bpFaced", "l_bpSaved"]].notna().all(axis=1) & \
        x["w_svpt"].gt(0) & x["l_svpt"].gt(0)
    x["box_partial_after"] = ~x[[f"{s}_{c}" for s in "wl" for c in EIGHT]].notna().all(axis=1)
    # S3: the kind of the row's service games
    rw, rl = x["w_SvGms"], x["l_SvGms"]
    missing = rw.isna() | rl.isna() | ((rw == 0) & x["w_svpt"].gt(0)) | ((rl == 0) & x["l_svpt"].gt(0))
    equal = rw.eq(x["t_w"]) & rl.eq(x["t_l"])
    swapped = rw.eq(x["t_l"]) & rl.eq(x["t_w"]) & x["t_w"].ne(x["t_l"])
    fs_w = x["first_server"].astype(str).str.replace(".0", "", regex=False).eq(
        x["mb_w_team"].astype(str).str.replace(".0", "", regex=False))
    turns = [tb_turns(s, bool(f)) for s, f in zip(x["score"].fillna(""), fs_w)]
    x["tb_w"], x["tb_l"] = [t[0] for t in turns], [t[1] for t in turns]
    incl_tb = rw.eq(x["t_w"] + x["tb_w"]) & rl.eq(x["t_l"] + x["tb_l"]) & (x["tb_w"] + x["tb_l"]).gt(0)
    x["kind"] = np.select([x["t_w"].isna(), missing, equal, swapped, incl_tb],
                          ["no_truth", "fill", "equal", "swapped", "tiebreaks_counted"], "other")
    # S4: the consistency test
    x["s4_consistent"] = x["bp_sv_w"].eq(x["t_w"]) & x["bp_sv_l"].eq(x["t_l"])
    x["row_consistent"] = x["bp_sv_w"].eq(rw) & x["bp_sv_l"].eq(rl)
    # S5: other tables
    ovs = pd.read_csv(HERE / "overrides_scope.csv", dtype=str, keep_default_na=False)
    rgx = pd.read_csv(HERE / "exchanges_scope.csv", dtype=str, keep_default_na=False)
    r1 = pd.read_csv(ROOT / "data" / "studies" / "rg_first_serve_recount" / "confirmed" / "confirmed_corrections.csv",
                     dtype=str, keep_default_na=False)
    rc = pd.read_csv(ROOT / "data" / "studies" / "input_data_audit" / "fixes" / "row_corrections.csv", dtype=str,
                     keep_default_na=False)
    sws = pd.read_csv(HERE / "swaps_scope.csv", dtype=str, keep_default_na=False)
    x["in_override"] = x["s0_match_id"].isin(set(ovs["stage0_match_id"])) & x["slam"].eq("RG")
    x["in_rgx"] = x["key"].isin(set(rgx["source_file"] + "#" + rgx["source_row"]))
    x["in_round1_split"] = x["key"].isin(set(r1["source_file"] + "#" + r1["source_row"]))
    x["in_decided"] = x["key"].isin(set(rc["source_file"] + "#" + rc["source_row"]))
    x["in_swaps"] = x["key"].isin(set(sws["source_file"] + "#" + sws["source_row"]))
    x["s5_free"] = ~x[["in_override", "in_rgx", "in_round1_split", "in_decided", "in_swaps"]].any(axis=1)
    # S6: B5 (the total fits the score) and B8 with the new counts
    reg = [sum(a + b - (1 if max(a, b) == 7 and min(a, b) == 6 else 0) for a, b in T.sets_of(s)[0])
           for s in x["score"].fillna("")]
    x["reg_games"] = reg
    x["s6_b5"] = (x["t_w"] + x["t_l"]).eq(x["reg_games"])
    x["s6_b8"] = ((x["w_bpFaced"] - x["w_bpSaved"]) <= x["t_w"]) & ((x["l_bpFaced"] - x["l_bpSaved"]) <= x["t_l"])
    cand = x[x["kind"].isin(["fill", "other", "tiebreaks_counted"])].copy()
    cand["confirm"] = cand["s1_proven"] & cand["s2_complete"] & cand["kind"].isin(["fill", "other"]) & \
        cand["s4_consistent"] & cand["s5_free"] & cand["s6_b5"] & cand["s6_b8"]
    cand["why_not"] = np.select(
        [~cand["s1_proven"], ~cand["s2_complete"], cand["kind"].eq("tiebreaks_counted"), ~cand["s4_consistent"],
         cand["in_override"], cand["in_decided"], ~cand["s5_free"], ~cand["s6_b5"] | ~cand["s6_b8"]],
        ["first server not proven", "box incomplete", "tiebreaks counted (a convention)", "fails the consistency test",
         "RG override", "decided correction", "another table", "Stage 0 check"], "")
    cand.to_csv(HERE / "svs_rows.csv", index=False)
    mine = cand[cand["confirm"]]
    mine[["source_file", "source_row", "t_w", "t_l", "slam", "year", "code", "kind", "w_SvGms", "l_SvGms", "score",
          "s0_match_id"]].to_csv(HERE / "svs_mine.csv", index=False)
    print("candidates (proven or not):", len(cand), "| by kind:", cand["kind"].value_counts().to_dict())
    print("confirmed:", len(mine), "| by kind:", mine["kind"].value_counts().to_dict())
    print(pd.crosstab([mine["slam"], mine["year"]], mine["kind"], margins=True).to_string())
    print("\nnot confirmed, by reason:\n", cand[~cand["confirm"]].groupby(["why_not", "kind"]).size().to_string())
    print("\nfills: the row's service games as recorded:",
          mine[mine["kind"].eq("fill")].assign(r=lambda d: d["w_SvGms"].astype(str) + "/" + d["l_SvGms"].astype(str))
          ["r"].value_counts().head(8).to_dict())
    oth = mine[mine["kind"].eq("other")]
    d = (oth["w_SvGms"] + oth["l_SvGms"]) - (oth["t_w"] + oth["t_l"])
    print("'other' rows: total minus the truth's:", d.value_counts().sort_index().to_dict())
    print("'other' rows whose recorded counts are consistent with their own break points:",
          int(oth["row_consistent"].sum()))
    print(cand[cand["kind"].eq("tiebreaks_counted")][["slam", "year", "code", "score", "w_SvGms", "l_SvGms", "t_w",
                                                       "t_l", "tb_w", "tb_l"]].head(20).to_string())
    if "--compare" in sys.argv:
        compare(cand, mine)


def compare(cand: pd.DataFrame, mine: pd.DataFrame) -> None:
    lead = pd.read_csv(LEAD, dtype=str, keep_default_na=False)
    lead["key"] = lead["source_file"] + "#" + lead["source_row"]
    mine = mine.copy()
    mine["key"] = mine["source_file"] + "#" + mine["source_row"].astype(int).astype(str)
    lk, mk = set(lead["key"]), set(mine["key"])
    j = mine.merge(lead, on="key", suffixes=("_m", "_l"))
    same = (pd.to_numeric(j["w_SvGms_l"]) == j["t_w"]) & (pd.to_numeric(j["l_SvGms_l"]) == j["t_l"])
    res = {"lead": len(lk), "mine": len(mk), "both": len(lk & mk), "same_values": int(same.sum()),
           "lead_only": sorted(lk - mk), "mine_only": sorted(mk - lk)}
    cand = cand.copy()
    cand["key"] = cand["source_file"] + "#" + cand["source_row"].astype("Int64").astype(str)
    res["lead_only_detail"] = cand[cand["key"].isin(lk - mk)][["slam", "year", "code", "score", "kind", "w_SvGms",
                                                                "l_SvGms", "t_w", "t_l", "bp_sv_w", "bp_sv_l",
                                                                "why_not", "proof"]].to_dict("records")
    res["lead_only_not_in_my_candidates"] = sorted((lk - mk) - set(cand["key"]))
    res["mine_only_detail"] = mine[mine["key"].isin(mk - lk)][["slam", "year", "code", "score", "kind", "w_SvGms",
                                                               "l_SvGms", "t_w", "t_l"]].to_dict("records")
    res["value_differences"] = j[~same][["key", "w_SvGms_l", "l_SvGms_l", "t_w", "t_l"]].to_dict("records")
    (HERE / "svs_compare.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, list) or len(v) < 30 else f"{len(v)} items") for k, v in res.items()},
                     indent=1, default=str))
    write_outputs(cand, mine, res)


def write_outputs(cand: pd.DataFrame, mine: pd.DataFrame, res: dict) -> None:
    """sets_scope.csv (my values) and the "SVS" entry of verdict.json."""
    out = mine.assign(source_row=mine["source_row"].astype(int), w_SvGms=mine["t_w"].astype(int),
                      l_SvGms=mine["t_l"].astype(int))[["source_file", "source_row", "w_SvGms", "l_SvGms"]]
    out.sort_values(["source_file", "source_row"]).to_csv(HERE / "sets_scope.csv", index=False)
    fills, oth = mine[mine["kind"].eq("fill")], mine[mine["kind"].eq("other")]
    by = mine.groupby(["slam", "year"]).size()
    partial = mine[mine["box_partial_after"].astype(bool)]
    z = oth[(oth["w_SvGms"] + oth["l_SvGms"]).eq(oth["t_w"] + oth["t_l"])]
    fail = cand[cand["why_not"].eq("fails the consistency test") & ~cand["in_override"].astype(bool)]
    v = json.loads((HERE / "verdict.json").read_text(encoding="utf-8"))
    v["SVS"] = {
        "vote": "confirm" if res["both"] == res["lead"] and res["same_values"] == res["lead"] else "narrow",
        "corrupt_beyond_doubt": True, "fix_clear_and_correct": True,
        "scope": f"{res['both']} of the {res['lead']} proposed sets, every one with the proposal's values "
                 f"({res['same_values']} of {res['both']}), in sets_scope.csv with the values I derived: {len(fills)} "
                 f"fills and {len(oth)} 'other' ("
                 + "; ".join(f"{s} {y} {n}" for (s, y), n in by.items()) + "). My derivation, made before reading "
                 "the proposal, found the same rows and values; none added, none dropped. "
                 f"{int((~mine['tolerant'].astype(bool)).sum())} rest on the strict proof; "
                 + ", ".join(f"{r.slam} {r.year} {r.code}" for r in mine[mine["tolerant"].astype(bool)].itertuples())
                 + " on the glitch-tolerant reading (a local glitch of at most three records in one set, every other "
                   "game on the alternation), its truth agreeing with the break identity. Of the fills, "
                 f"{len(partial)} (RG 2013-2014: " + ", ".join(f"{r.year} {r.code}" for r in partial.itertuples()) +
                 ") have double faults blank too, so their box stays partial and Stage 0 still drops it (C23) "
                 "until those are filled; the fill is correct and harmless, but completes nothing.",
        "reasons": "Each set rests on the same proven first server as SVX (my own decryption and recount; the "
                   "opening of the match shown by the set score after game 1 or by its first point, every game on "
                   "the alternation, sets checked by the games' winners). The truth is the score's alternation, a "
                   "tiebreak taking its turn uncounted, a retirement's finished games only. Every set passes the "
                   "consistency test: each player's non-tiebreak games won equal the truth's service games, less "
                   "breaks conceded, plus breaks made, from the row's own break points. That makes the new counts the "
                   "only ones the row's own score and break points allow, independently of the point record. "
                   f"Fills ({len(fills)}): the counts are blank (RG 2013-2014, Sackmann's rows with serve points and "
                   "no service games) or 0 and 0 with serve points played (RG 2017, which Stage 0 already reads as "
                   "missing); serve points and break points are present. "
                   f"'Other' ({len(oth)}): the recorded counts are wrong and not an exchange. {len(z)} have the right "
                   f"total with the split off ({int((z['w_SvGms'].eq(z['l_SvGms']) & z['t_w'].ne(z['t_l'])).sum())} "
                   "equal counts where the score forces unequal ones), and two fall short: RG 2023 SM040, 9/9 for 27 "
                   "games; RG 2024 SM123, 22/22 for 45, the match the overrides leave out for a scorer-less "
                   "MatchBeats point, here 23/22 as I derived it then. None is a tiebreak counted the other way: no "
                   "row equals the truth with tiebreak turns added. None of the recorded counts is consistent with "
                   f"its own break points ({int(oth['row_consistent'].astype(bool).sum())} of {len(oth)}), and every "
                   "truth is. B5 (the total fits the score) and B8 pass on every set. No set touches a row another "
                   "table changes: my confirmed overrides, the RGX exchanges, round 1's split rows, the decided "
                   "corrections or the swaps. "
                   f"Left out, as the proposal does: the RG override matches, and the consistency failures outside "
                   f"them ({', '.join(f'{r.slam} {r.year} {r.code}' for r in fail.itertuples())}).",
        "checks": [
            S + "svx_truth.py, svx_addendum.py (--tag add2), svx_tolerant.py: the proof and the truth for every "
            "edition held. The opening check now accepts either the set score after game 1 or its first point; the "
            "swap lists are unchanged by it (swaps_scope.csv byte-identical to the 810 confirmed).",
            S + "svs.py: candidates from my own tables; tests S1-S6 per row (svs_rows.csv); values = the truth.",
            S + "svs.py --compare: " + f"{res['both']} of {res['lead']} equal, {res['same_values']} with the same "
            f"values, {len(res['mine_only'])} of mine outside the proposal, {len(res['lead_only'])} of it outside "
            "mine."],
        "notes_for_the_lead": "The brief says Stosur d. Halep was kept out of SVX, but the swap table (the 810, "
                              "byte-identical) holds it (RG 2016 SD014), and I confirmed it there with the reasons "
                              "given in SVX_addendum2. If the consistency test is meant to apply to the swaps too, "
                              "that row is the one it would remove.",
    }
    (HERE / "verdict.json").write_text(json.dumps(v, indent=1, ensure_ascii=False), encoding="utf-8")
    print("sets_scope.csv:", len(out), "rows | verdict.json: SVS entry written")


if __name__ == "__main__":
    main()
