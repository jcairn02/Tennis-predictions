"""Audit of Stage 0, check 6: the box-score consistency checks, re-run independently.

The nine counts per player are read from the staged source row of every match (source_file,
source_row), parsed here, and put through the checks stage0.md describes (B1-B9), with the score
read by the audit's own parser. The result is compared with Stage 0's box_status and has_box
match by match, with the counts in the cleaning log (C31-C39), and with the counts Stage 0 kept in
stage0_match_players. Three checks Stage 0 does not make are added (A1-A3).

Writes audit0/box_crosstab.csv, audit0/box_disagreements.csv and audit0/box.json.
Run: ./python.sh src/eda/predictability_diagnostic/audit0_box.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.predictability_diagnostic import audit0_common as A  # noqa: E402

NAMES = {"ace": "ace", "df": "df", "svpt": "svpt", "1stIn": "first_in", "1stWon": "first_won", "2ndWon": "second_won",
         "SvGms": "sv_gms", "bpSaved": "bp_saved", "bpFaced": "bp_faced"}
FLOOR = 4.5
STAGE0_RULE = {"B1": "C31", "B2": "C32", "B3": "C33", "B4": "C34", "B5": "C35", "B6": "C36", "B7": "C37",
               "B8": "C38", "B9": "C39"}


def side_counts(staged: pd.DataFrame, side: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(values, filled) for one side: values as floats, filled = the source cell is not blank."""
    raw = pd.DataFrame({NAMES[c]: staged[f"{side}_{c}"].fillna("").astype(str).str.strip() for c in A.BOX_COLS})
    filled = raw.ne("")
    vals = raw.apply(lambda s: pd.to_numeric(s.replace("", np.nan), errors="coerce"))
    return vals, filled


def side_kind(vals: pd.DataFrame, filled: pd.DataFrame) -> pd.Series:
    n = filled.sum(axis=1)
    nonzero = (vals.fillna(0) != 0).sum(axis=1)
    return pd.Series(np.select([n.eq(0), nonzero.eq(0), n.eq(8) & ~filled["sv_gms"], n.lt(9)],
                               ["blank", "all_zero", "no_svgms", "partial"], "full"), index=vals.index)


def score_games(score: str, flag: str, fmt: str, status: str) -> tuple:
    """Games in the score by player (first-written winner unless read reversed), standard tiebreaks,
    and the same with a deciding match tiebreak written as a set taken out."""
    short = fmt == "short_sets"
    gw, gl, tb = A.games_in_score(score, short)
    if flag == "read_reversed":
        gw, gl = gl, gw
    sets, marks = A.parse_score(score)
    plain = 0
    if len(sets) >= 3 and not marks:
        a, b, t, mtb = sets[-1]
        ww = sum(1 for x in sets[:-1] if x[0] > x[1])
        ll = sum(1 for x in sets[:-1] if x[1] > x[0])
        if not mtb and max(a, b) >= 10 and ww == ll and abs(a - b) != 2 and (max(a, b), min(a, b)) != (13, 12):
            plain = a + b
    return gw, gl, tb, plain


def main() -> int:
    m = A.load_matches(["match_id", "tour", "level", "year", "qualifying", "status", "status_detail", "score",
                        "score_flag", "format", "box_status", "has_box", "sv_gms_incl_tb", "evaluation", "source",
                        "source_file", "source_row"])
    cols = ["winner_name", "loser_name"] + [f"{s}_{c}" for s in ("w", "l") for c in A.BOX_COLS]
    staged = A.load_staged(cols)
    j = m.merge(staged[["_source_file", "_row"] + cols], left_on=["source_file", "source_row"],
                right_on=["_source_file", "_row"], how="left", validate="one_to_one")
    wv, wf = side_counts(j, "w")
    lv, lf = side_counts(j, "l")
    kw, kl = side_kind(wv, wf), side_kind(lv, lf)

    # the match's box status, as stage0.md describes it
    both_blank = kw.eq("blank") & kl.eq("blank")
    any_zero = (kw.eq("all_zero") | kl.eq("all_zero")) & ~both_blank
    one_side = (kw.eq("blank") | kl.eq("blank")) & ~both_blank & ~any_zero
    partial = (kw.eq("partial") | kl.eq("partial")) & ~both_blank & ~any_zero & ~one_side
    status = pd.Series(np.select([both_blank, any_zero, one_side, partial], ["blank", "all_zero", "one_side", "partial"],
                                 "full"), index=j.index)
    usable = status.eq("full")
    no_sv = usable & (kw.eq("no_svgms") | kl.eq("no_svgms"))
    zero_sv = usable & ((wv["sv_gms"].eq(0) & wv["svpt"].gt(0)) | (lv["sv_gms"].eq(0) & lv["svpt"].gt(0)))
    sv_missing = no_sv | zero_sv
    status[sv_missing] = "no_svgms"
    for v in (wv, lv):
        v.loc[sv_missing, "sv_gms"] = np.nan

    g = pd.DataFrame([score_games(s, f, fm, st) for s, f, fm, st in
                      zip(j["score"], j["score_flag"].fillna(""), j["format"], j["status"])],
                     columns=["gw", "gl", "tb", "plain_mtb"], index=j.index)
    games = g["gw"] + g["gl"]
    scored = j["status_detail"].ne("unknown") & j["score"].ne("") & ~j["status"].eq("walkover")

    def run_checks(games: pd.Series, label: str) -> dict:
        sv = wv["sv_gms"] + lv["sv_gms"]
        b5 = usable & scored & sv.notna() & ((sv - (games - g["tb"])).abs() > 1) & ((sv - games).abs() > 1)
        fails = {"B5": b5}
        per = {}
        for side, v in (("w", wv), ("l", lv)):
            svg = v["sv_gms"].where(~b5)
            per[side] = {
                "B1": v["first_in"] > v["svpt"],
                "B2": v["first_won"] > v["first_in"],
                "B3": v["second_won"] > v["svpt"] - v["first_in"],
                "B4": v["bp_saved"] > v["bp_faced"],
                "B6": v["df"] > v["svpt"] - v["first_in"],
                "B7": v["ace"] > v["first_won"] + v["second_won"],
                "B8": (v["bp_faced"] - v["bp_saved"]) > svg,
            }
        for k in per["w"]:
            fails[k] = usable & (per["w"][k].fillna(False) | per["l"][k].fillna(False))
        played = (games - g["tb"]) - np.where(j["status"].eq("completed"), 0, 1)
        fails["B9"] = usable & scored & ((wv["svpt"] + lv["svpt"]) < FLOOR * played).fillna(False)
        return fails

    fails = run_checks(games, "as Stage 0 reads the score")
    fails_fixed = run_checks(games - g["plain_mtb"], "match tiebreaks written as sets taken out")
    dropped = pd.Series(False, index=j.index)
    for k, v in fails.items():
        if k != "B5":
            dropped |= v
    audit_status = status.copy()
    audit_status[fails["B5"] & ~dropped & audit_status.eq("full")] = "no_svgms"
    audit_status[dropped] = "failed_check"
    audit_has = audit_status.isin(["full", "no_svgms"])

    # compare with Stage 0
    agree = audit_status.eq(j["box_status"]) & audit_has.eq(j["has_box"])
    cross = pd.crosstab(audit_status.rename("audit"), j["box_status"].rename("stage0"))
    cross.to_csv(A.out_dir() / "box_crosstab.csv")
    dis = j.loc[~agree, ["match_id", "tour", "level", "year", "score", "status", "box_status"]].assign(
        audit_status=audit_status[~agree],
        audit_fails=[",".join(k for k in fails if fails[k].iat[i]) for i in np.flatnonzero(~agree.to_numpy())])
    dis.to_csv(A.out_dir() / "box_disagreements.csv", index=False)

    log = pd.read_csv(A.STUDY / "stage0_cleaning_log.csv")
    log_tot = log.groupby("rule_id")["count"].sum()
    per_check = {k: {"audit": int(v.sum()), "stage0_log": int(log_tot.get(STAGE0_RULE[k], 0)),
                     "audit_with_match_tiebreaks_fixed": int(fails_fixed[k].sum())} for k, v in fails.items()}

    # the counts Stage 0 kept, against the staged row (player by player, by name)
    mp = A.load_players(["match_id", "won", "player_name"] + list(NAMES.values()))
    w = mp[mp["won"]].set_index("match_id")
    kept = j[j["has_box"]].set_index("match_id")
    swapped = w.reindex(kept.index)["player_name"].ne(kept["winner_name"].fillna("").str.strip())
    diffs = {}
    for c in NAMES.values():
        if c == "sv_gms":
            continue
        src_w = pd.to_numeric(kept[f"w_{[k for k, v in NAMES.items() if v == c][0]}"], errors="coerce")
        src_l = pd.to_numeric(kept[f"l_{[k for k, v in NAMES.items() if v == c][0]}"], errors="coerce")
        mine = np.where(swapped, src_l, src_w)
        diffs[c] = int((~np.isclose(w.reindex(kept.index)[c].to_numpy(), mine, equal_nan=True)).sum())

    # checks Stage 0 does not make, on the box scores it keeps
    keep = j["has_box"]
    for v in (wv, lv):   # service games as Stage 0 keeps them (dropped where B5 fails)
        v.loc[fails["B5"], "sv_gms"] = np.nan
    wbrk, lbrk = wv["bp_faced"] - wv["bp_saved"], lv["bp_faced"] - lv["bp_saved"]
    split = (wv["sv_gms"] - lv["sv_gms"]).abs()
    a1 = keep & (split > 1 + g["tb"])
    # A2: with no tiebreak in a completed match, the games each player won are their holds plus
    # the opponent's breaks conceded, exactly
    no_tb = keep & j["status"].eq("completed") & g["tb"].eq(0) & g["plain_mtb"].eq(0) & ~j["format"].eq("match_tiebreak")
    ident_w = (wv["sv_gms"] - wbrk) + lbrk
    ident_l = (lv["sv_gms"] - lbrk) + wbrk
    # which player served which count: the staged winner's counts sit in w_ even where Stage 0
    # swapped the sides, and the score is the staged winner's unless read reversed (handled above)
    dw, dl = ident_w - g["gw"], ident_l - g["gl"]
    gap = np.maximum(dw.abs(), dl.abs())
    a2_tested = no_tb & wv["sv_gms"].notna() & lv["sv_gms"].notna()
    a2 = a2_tested & (gap > 0)
    a2_big = a2_tested & (gap > 1)
    pattern = pd.crosstab(dw[a2].clip(-3, 3).rename("winner_games_box_minus_score"),
                          dl[a2].clip(-3, 3).rename("loser_games_box_minus_score"))
    # A3: a player's serve points below four per service game (a game has at least four points)
    a3 = keep & (((wv["svpt"] < 4 * (wv["sv_gms"] - 1 - g["tb"])) | (lv["svpt"] < 4 * (lv["sv_gms"] - 1 - g["tb"]))))
    added = {
        "A1_service_game_split_exceeds_one_plus_tiebreaks": int(a1.sum()),
        "A2_tested_completed_no_tiebreak": int(a2_tested.sum()),
        "A2_games_not_holds_plus_breaks": int(a2.sum()),
        "A2_off_by_more_than_one_game": int(a2_big.sum()),
        "A2_by_tour_level": j[a2_big].groupby(["tour", "level"]).size().rename("matches").reset_index()
        .to_dict(orient="records"),
        "A2_evaluation_off_by_more_than_one_pct": {
            t: round(100 * float(a2_big[j["evaluation"] & j["tour"].eq(t)].sum()) /
                     max(1, int(a2_tested[j["evaluation"] & j["tour"].eq(t)].sum())), 2) for t in ("atp", "wta")},
        "A2_evaluation_off_by_one_or_more": {
            t: {"off": int(a2[j["evaluation"] & j["tour"].eq(t)].sum()),
                "tested": int(a2_tested[j["evaluation"] & j["tour"].eq(t)].sum())} for t in ("atp", "wta")},
        "A2_off_by_one_or_more_by_tour_level": j[a2].groupby(["tour", "level"]).size().rename("matches").reset_index()
        .to_dict(orient="records"),
        "A2_off_by_one_or_more_by_source": j[a2].groupby("source").size().to_dict(),
        "A2_pattern_winner_by_loser": {str(k): {str(c): int(v) for c, v in row.items()} for k, row in pattern.iterrows()},
        "A2_box_games_minus_score_games": (wv["sv_gms"] + lv["sv_gms"] - g["gw"] - g["gl"])[a2].value_counts()
        .sort_index().to_dict(),
        "A2_examples": j.loc[a2_big, ["match_id", "score"]].assign(
            gap=gap[a2_big], w=wv.loc[a2_big, ["sv_gms", "bp_faced", "bp_saved"]].to_numpy().tolist(),
            l=lv.loc[a2_big, ["sv_gms", "bp_faced", "bp_saved"]].to_numpy().tolist()).head(10).to_dict(orient="records"),
        "A3_serve_points_below_four_per_service_game": int(a3.sum()),
        "A3_examples": j.loc[a3, ["match_id", "score"]].assign(
            w=wv.loc[a3, ["svpt", "sv_gms"]].to_numpy().tolist(), l=lv.loc[a3, ["svpt", "sv_gms"]].to_numpy().tolist())
        .head(8).to_dict(orient="records"),
    }
    ev = j["evaluation"]
    plain = g["plain_mtb"].gt(0)
    summary = {
        "matches": int(len(j)), "staged_row_found": int(j["_row"].notna().sum()),
        "status_and_has_box_agree": int(agree.sum()), "disagree": int((~agree).sum()),
        "crosstab_audit_by_stage0": cross.to_dict(),
        "per_check_failures": per_check,
        "kept_boxes": int(j["has_box"].sum()),
        "kept_counts_differing_from_staged_row": diffs,
        "kept_boxes_failing_any_audit_check": int((j["has_box"] & (dropped | fails["B5"] & j["box_status"].eq("full"))).sum()),
        "evaluation_box_pct": {t: round(100 * float(j.loc[ev & j["tour"].eq(t), "has_box"].mean()), 1) for t in ("atp", "wta")},
        "match_tiebreak_written_as_set": {
            "with_usable_box": int((plain & usable).sum()),
            "B5_fail_as_read": int((plain & fails["B5"]).sum()), "B5_fail_fixed": int((plain & fails_fixed["B5"]).sum()),
            "B9_fail_as_read": int((plain & fails["B9"]).sum()), "B9_fail_fixed": int((plain & fails_fixed["B9"]).sum()),
            "box_dropped_by_stage0": int((plain & j["box_status"].eq("failed_check")).sum()),
            "box_dropped_only_because_of_B9_as_read": int((plain & fails["B9"] & ~fails_fixed["B9"]).sum()),
            "service_games_dropped_only_because_of_B5_as_read": int((plain & fails["B5"] & ~fails_fixed["B5"]).sum()),
        },
        "added_checks": added,
    }
    A.write_json("box.json", summary)
    print(cross.to_string())
    for k in ("matches", "staged_row_found", "status_and_has_box_agree", "disagree", "kept_boxes",
              "kept_boxes_failing_any_audit_check", "evaluation_box_pct"):
        print(k, summary[k])
    print("per check", per_check)
    print("kept counts vs staged", diffs)
    print("plain MTB", summary["match_tiebreak_written_as_set"])
    print("added", {k: v for k, v in added.items() if "examples" not in k})
    print(dis.head(20).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
