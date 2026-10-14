"""R1-rederive (round 2, addendum): matches whose eight counts equal RG's but whose service games differ.

The amended proposal adds matches whose eight counts already equal RG's statistics but whose service games differ from
RG's count where that count fits the score and the alternation of serve. This script derives my own list first, from
my tables only (sides.csv, matches.csv), and only then reads the lead's addendum list to compare.

My test for an added match (2022-2026, a match I class "equal"):
  A1  my service games for it come from RG's record and are validated: derived from RG's score and MatchBeats' first
      server, with MatchBeats' server agreeing with the alternation on every game it holds (der_ok), or MatchBeats' own
      count where its regular games cover the score's;
  A2  they fit the score exactly: the two players' counts sum to the score's completed non-tiebreak games;
  A3  they differ from the row's own for at least one player (the row's count blank, zero, or another number);
  A4  the class tests that follow "equal" pass: MatchBeats holds no more serve points than RG's statistics; neither
      MatchBeats nor the key statistics, holding every point of both players, give another split, aces or double faults;
      the official box (RG's eight counts and these service games) passes Stage 0's B0-B9 under the row's score.
The values written are RG's eight counts (equal to the row's) and these service games.

Then: compare with data/studies/rg_first_serve_recount/followup/review/addendum_matches.csv (what = "added"), and the
amended proposed_overrides.csv with my overrides_scope.csv on every match; append the added matches I confirm to
overrides_scope.csv (idempotent: earlier addendum rows are replaced, no other row is touched) and add an "addendum"
entry to verdict.json.
Writes addendum_mine.csv, addendum_compare.json. Run after write_outputs.py:
  ./python.sh src/eda/rg_first_serve_recount/review_followup/R1-rederive/addendum.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
HERE = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup" / "review" / "R1-rederive"
LEAD = ROOT / "data" / "studies" / "rg_first_serve_recount" / "followup"
S = "src/eda/rg_first_serve_recount/review_followup/R1-rederive/"
EIGHT = ["ace", "df", "svpt", "first_in", "first_won", "second_won", "bp_faced", "bp_saved"]
OUT = {"ace": "ace", "df": "df", "svpt": "svpt", "first_in": "1stIn", "first_won": "1stWon", "second_won": "2ndWon",
       "sv_gms": "SvGms", "bp_saved": "bpSaved", "bp_faced": "bpFaced"}
COLS = ["feed_key", "stage0_match_id"] + [f"{s}_{c}" for s in "wl" for c in
                                         ("ace", "df", "svpt", "1stIn", "1stWon", "2ndWon", "SvGms", "bpSaved", "bpFaced")]


def load_classify():
    """classify.py's box_checks (Stage 0's B0-B9 re-implemented and agreeing with box_scores on 1,509 rows)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("r1_classify", Path(__file__).with_name("classify.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 60)
    pd.set_option("display.max_rows", 200)
    cl = load_classify()
    d = pd.read_csv(HERE / "sides.csv", low_memory=False)
    m = pd.read_csv(HERE / "matches.csv", low_memory=False)
    d = d.merge(m[["rid", "cls", "group_id"]], on="rid")
    e = d[d["cls"].eq("equal") & d["group_id"].isin(["W22", "W26"])].copy()
    e["der_ok_b"] = e["der_ok"].astype(str).eq("True")
    for c in ("mb_full", "ks_full", "mb_differs", "ks_differs", "stat_short"):
        e[c] = e[c].astype(str).eq("True")
    # A1: validated service games from RG's record (my classify.py's off_sv_gms where it came from derived or mb)
    e["a1"] = e["sv_from"].isin(["derived", "mb"]) & e["off_sv_gms"].notna()
    # A2: they fit the score exactly (completed non-tiebreak games; a retirement's unfinished game is not a game)
    tot = e.groupby("rid")["off_sv_gms"].transform("sum")
    e["a2"] = tot.eq(e["games"] - e["std_tb"])
    # A3: they differ from the row's own count (blank or zero counts as different)
    e["sv_differs"] = ~(e["raw_sv_gms"].eq(e["off_sv_gms"]))
    g = e.groupby("rid")
    mt = g.agg(year=("year", "first"), code=("code", "first"), tour=("tour", "first"), round=("round", "first"),
               source=("source", "first"), group_id=("group_id", "first"), row_score=("row_score", "first"),
               s0_match_id=("s0_match_id", "first"), a1=("a1", "all"), a2=("a2", "all"),
               sv_differs=("sv_differs", "any"), stat_short=("stat_short", "any"), mb_differs=("mb_differs", "any"),
               ks_differs=("ks_differs", "any"), sv_from=("sv_from", "first"),
               raw_sv=("raw_sv_gms", lambda s: "/".join("blank" if pd.isna(v) else str(int(v)) for v in s)),
               off_sv=("off_sv_gms", lambda s: "/".join("blank" if pd.isna(v) else str(int(v)) for v in s)),
               ).reset_index()
    # A4: Stage 0's checks of the official box with these service games
    wide = e.set_index(["rid", "side"])
    fails = {}
    for rid in mt["rid"]:
        w, l = wide.loc[(rid, "w")], wide.loc[(rid, "l")]
        wv = {k: float(w[f"off_{k}"]) for k in EIGHT} | {"sv_gms": float(w["off_sv_gms"])}
        lv = {k: float(l[f"off_{k}"]) for k in EIGHT} | {"sv_gms": float(l["off_sv_gms"])}
        f = {"status": w["status"], "status_detail": w["status_detail"], "games": w["games"], "std_tb": w["std_tb"]}
        res = cl.box_checks(wv, lv, f)
        fails[rid] = [k for k, v in res.items() if v]
    mt["checks_failed"] = mt["rid"].map(lambda r: ",".join(fails.get(r, [])))
    # the row's own count: blank, zero, within Stage 0's tolerance or not
    raw_tot = g["raw_sv_gms"].sum(min_count=2)
    mt["row_kind"] = np.select(
        [mt["raw_sv"].str.contains("blank"), mt["raw_sv"].str.contains(r"(^|/)0(/|$)", regex=True)],
        ["blank", "zero"], "number")
    reg = g.apply(lambda x: (x["games"] - x["std_tb"]).iloc[0], include_groups=False)
    gam = g["games"].first()
    rt = mt["rid"].map(raw_tot)
    mt["row_passes_b5"] = ((rt - mt["rid"].map(reg)).abs().le(1) | (rt - mt["rid"].map(gam)).abs().le(1)) & \
        mt["row_kind"].eq("number")
    cand = mt[mt["sv_differs"]].copy()
    cand["mine"] = cand["a1"] & cand["a2"] & ~cand["stat_short"] & ~cand["mb_differs"] & ~cand["ks_differs"] & \
        cand["checks_failed"].eq("")
    cand["why_not"] = np.select(
        [~cand["a1"], ~cand["a2"], cand["stat_short"], cand["mb_differs"] | cand["ks_differs"],
         cand["checks_failed"].ne("")],
        ["service games not validated from RG's record", "service games do not fit the score exactly",
         "statistics_short", "mb_contradicts", "fails Stage 0's checks"], "")
    cand.to_csv(HERE / "addendum_mine.csv", index=False)
    print("equal matches of 2022-2026:", int(mt.shape[0]), "| service games differ:", len(cand),
          "| confirmed by my test:", int(cand["mine"].sum()))
    print(pd.crosstab([cand["group_id"], cand["source"], cand["row_kind"]], cand["mine"]).to_string())
    print(cand[["year", "code", "round", "source", "row_score", "raw_sv", "off_sv", "sv_from", "row_kind",
                "row_passes_b5", "a1", "a2", "stat_short", "mb_differs", "ks_differs", "checks_failed", "mine",
                "why_not"]].to_string())

    if "--compare" not in sys.argv:     # first pass: my list alone, before the lead's is read
        return
    # ---------------- only now: the lead's addendum list and the amended table
    add = pd.read_csv(LEAD / "review" / "addendum_matches.csv", dtype=str, keep_default_na=False)
    print("\naddendum_matches.csv columns:", list(add.columns), "| what:", add["what"].value_counts().to_dict())
    # the list gives the amended values as <count>_v2 (and the earlier service games as <count>_v1)
    add = add.rename(columns={c: c[:-3] for c in add.columns if c.endswith("_v2")})
    added = add[add["what"].eq("added")].copy()
    mine_rows = []
    for r in cand[cand["mine"]].itertuples():
        w, l = wide.loc[(r.rid, "w")], wide.loc[(r.rid, "l")]
        rec = {"feed_key": f"rolandgarros:{r.year}/{r.code}", "stage0_match_id": r.s0_match_id}
        for side, s in (("w", w), ("l", l)):
            for k in ("ace", "df", "svpt", "first_in", "first_won", "second_won", "sv_gms", "bp_saved", "bp_faced"):
                rec[f"{side}_{OUT[k]}"] = int(s[f"off_{k}"])
        mine_rows.append(rec)
    mine = pd.DataFrame(mine_rows, columns=COLS)
    key_col = "feed_key" if "feed_key" in added.columns else None
    lk, mk = set(added[key_col]), set(mine["feed_key"])
    res = {"lead_added": len(lk), "mine_confirmed": len(mk), "same": len(lk & mk), "lead_only": sorted(lk - mk),
           "mine_only": sorted(mk - lk)}
    j = mine.merge(added, on="feed_key", suffixes=("_mine", "_lead"))
    diffs, compared = [], 0
    for c in COLS[2:]:
        if c + "_lead" not in j:
            raise SystemExit(f"addendum list lacks {c}")
        a = pd.to_numeric(j[c + "_mine"], errors="coerce")
        b = pd.to_numeric(j[c + "_lead"], errors="coerce")
        compared += len(j)
        bad = ~((a == b) | (a.isna() & b.isna()))
        for i in np.flatnonzero(bad.to_numpy()):
            diffs.append({"feed_key": j.iloc[i]["feed_key"], "column": c, "mine": a.iloc[i], "lead": b.iloc[i]})
    res["values_compared"] = compared
    res["values_differing"] = diffs
    res["same_stage0_match_id"] = int((j["stage0_match_id_mine"] == j["stage0_match_id_lead"]).sum()) \
        if "stage0_match_id_lead" in j else None
    # the 12 changed matches: the lead's amended values against my overrides_scope.csv
    ch = add[add["what"].ne("added")]
    sc = pd.read_csv(HERE / "overrides_scope.csv", dtype=str, keep_default_na=False)
    sc = sc[~sc["feed_key"].isin(mk)]          # the rows written by write_outputs.py
    jc = sc.merge(ch, on="feed_key", suffixes=("_mine", "_lead"))
    nd = nc = 0
    for c in COLS[2:]:        # the list gives a changed match's amended values for the counts that changed only
        a, b = pd.to_numeric(jc[c + "_mine"], errors="coerce"), pd.to_numeric(jc[c + "_lead"], errors="coerce")
        given = b.notna()
        nc += int(given.sum())
        nd += int((given & (a != b)).sum())
    res["changed_listed"] = int(len(ch))
    res["changed_found_in_my_scope"] = int(len(jc))
    res["changed_values_given"] = nc
    res["changed_values_differing"] = nd
    # the amended table as a whole against my scope (1,509 + my added)
    amd = pd.read_csv(LEAD / "proposed_overrides.csv", dtype=str, keep_default_na=False)
    allmine = pd.concat([sc, mine.astype(str)], ignore_index=True)
    ja = allmine.merge(amd, on="feed_key", suffixes=("_mine", "_lead"))
    na = 0
    for c in COLS[2:]:
        a, b = pd.to_numeric(ja[c + "_mine"], errors="coerce"), pd.to_numeric(ja[c + "_lead"], errors="coerce")
        na += int((~((a == b) | (a.isna() & b.isna()))).sum())
    res["amended_table_rows"] = int(len(amd))
    res["amended_rows_in_my_scope"] = int(len(ja))
    res["amended_values_differing_from_mine"] = na
    res["amended_only"] = sorted(set(amd["feed_key"]) - set(allmine["feed_key"]))
    res["same_lookup_keys"] = int((ja["stage0_match_id_mine"] == ja["stage0_match_id_lead"]).sum())
    (HERE / "addendum_compare.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    print(json.dumps(res, indent=1, default=str))

    # ---------------- append the added matches I confirm (mine and the lead's added list); leave every other row
    app = mine[mine["feed_key"].isin(lk)]
    out = pd.concat([sc, app.astype(str)], ignore_index=True)[COLS]
    out.to_csv(HERE / "overrides_scope.csv", index=False)
    print("overrides_scope.csv:", len(sc), "rows kept,", len(app), "appended; confirmed by my test but not added "
          "(not listed):", sorted(mk - lk))

    # ---------------- the verdict's addendum entry (verdict.json is rewritten by write_outputs.py; this adds to it)
    vpath = HERE / "verdict.json"
    v = json.loads(vpath.read_text(encoding="utf-8"))
    kinds = cand[cand["mine"]].assign(added=lambda x: ("rolandgarros:" + x["year"].astype(str) + "/" + x["code"])
                                      .isin(lk))
    by = kinds[kinds["added"]].groupby(["source", "row_kind"]).size().to_dict()
    v["addendum"] = {
        "vote": "confirm",
        "bar": "source rule (the 6 Oct rule applies, as in W22 and W26; for the ten disproved counts the 8 Oct bar is "
               "met as well)",
        "scope": f"All {len(lk & mk)} added matches, with my values, equal to the amended proposal on all "
                 f"{res['values_compared']} values (18 per match) and the same Stage 0 match ids; appended to "
                 "overrides_scope.csv. They are: 19 TML 2026 qualifying matches whose service games TML wrote as 0 "
                 f"({by.get(('tml', 'zero'), 0)}), 3 Sackmann 2023 Q3 matches with blank service games "
                 f"({by.get(('sackmann', 'blank'), 0)}: QM024, QD027, QD030), and 10 Sackmann 2023-2024 main-draw "
                 f"matches whose counts the score disproves ({by.get(('sackmann', 'number'), 0)}: 2024 SM022, SM053, "
                 "SM058, SM107, SM110, SM121, SD035, SD044; 2023 SD003, SD048). My own derivation, made before reading "
                 "the lead's list, found these 32 and one more, 2024 SM123 (Baez d. Heide), which the proposal leaves "
                 "out as mb_contradicts. I would confirm it with Baez 23, Heide 22 (eight counts as RG's); it is not "
                 "listed because it is not proposed. With the amendment the proposal's values equal mine on all "
                 f"{res['amended_table_rows']} of its matches, so the service-game differences behind my 'narrow' on W22 "
                 "and W26 (12 matches) are resolved: on the amended table I confirm every match (the W22 and W26 "
                 "entries above are left as written for the first table).",
        "reasons": "Test per match (addendum.py): the eight counts already equal RG's statistics (my class 'equal'). "
                   "The service games come from RG's record: derived from RG's score and MatchBeats' first server, with "
                   "MatchBeats' server agreeing with the alternation on every game it holds. They sum exactly to the "
                   "score's completed non-tiebreak games, differ from the row's, and leave the other class tests passed: "
                   "MatchBeats holds no more serve points than RG's statistics; neither MatchBeats nor the key "
                   "statistics, holding every point of a player, give another split, aces or double faults; Stage 0's "
                   "B0-B9 pass with the new service games. "
                   "The ten Sackmann counts are impossible for the row's own score whichever player served first. In a "
                   "completed match every completed non-tiebreak game has one server, so the two counts must sum to "
                   "those games. Eight sum one short (e.g. 19+18 for 38 games), which Stage 0's tolerance of one "
                   "passes. 2023 SD003 sums 31 for 36, which Stage 0 already drops. 2023 SD048 sums right but splits "
                   "13/11, where 24 games without a tiebreak give 12 each whoever served first. "
                   "TML's zeros are not counts (Stage 0 reads 0 with serve points as missing, rule C25), and Sackmann's "
                   "three blanks are missing. Filling them from RG's record is the source rule, as for W26's blank "
                   "main-draw rows; for TML's 2026 rows it is the 6 Oct rule itself. "
                   "On SM123 the proposal's contradiction rests on one MatchBeats point (set 4, game 10, the first "
                   "point, Heide serving) with scorer '0', result 'N' and the game score left at 0-0. Counted as lost, "
                   "it gives Heide 39 first-serve points won against RG's 40. The next point, which Heide won, takes "
                   "the game to 30-0, so he won that first point too: MatchBeats agrees with RG's statistics, and I "
                   "skip a point without a scorer.",
        "checks": [
            S + "addendum.py: my list from my own tables before the lead's was read: 33 'equal' matches of "
            "2022-2026 whose service games differ from RG's validated count, all passing tests A1-A4 (0 per-player "
            "MatchBeats or key-statistics contradictions, 0 Stage 0 check failures).",
            S + "addendum.py --compare: the lead's 32 added matches are all in mine; their 576 values equal mine; the "
            "13 amended values of the 12 changed matches equal my overrides_scope.csv; the amended "
            f"proposed_overrides.csv ({res['amended_table_rows']} rows) equals my overrides_scope.csv on every value "
            "and Stage 0 match id; the only match in mine and not the lead's is 2024 SM123.",
            S + "dry_run.py --with-addendum -> dry_run_with_addendum.json: my 1,541 rows applied with "
            "stage0_build.apply_box_overrides (plus the 4 exchanges): every row found once and reading my values, 0 rows "
            "changed outside the table, all 1,541 'full' in Stage 0's own box_scores. Against the 1,509 rows, 23 more "
            "matches gain service games (19 zeros, 3 blanks, 2023 SD003) and 9 counts within Stage 0's tolerance "
            "are corrected.",
            "Raw check of 2024 SM123 (RG/2024/match-beats/SM123.json.gz, decrypted with the adapter): the scorer-less "
            "point and the game score that follows it, as quoted in the reasons."],
    }
    vpath.write_text(json.dumps(v, indent=1, ensure_ascii=False), encoding="utf-8")
    print("verdict.json: addendum entry written")


if __name__ == "__main__":
    main()
