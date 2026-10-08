"""Audit of Stage 0, check 5: statuses (retirements, walkovers) against the score strings.

Every match's score is read again by the audit's own parser (audit0_common.classify_score) and
compared with Stage 0's status and status_detail. The score itself is compared with the staged
source row it came from (source_file, source_row).

Writes audit0/status_crosstab.csv, audit0/status_disagreements.csv and audit0/status.json.
Run: ./python.sh src/eda/predictability_diagnostic/audit0_status.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.predictability_diagnostic import audit0_common as A  # noqa: E402

# the audit's reading -> what Stage 0 should say (status_detail, score_flag)
EXPECT = {
    "completed": ("completed", ""),
    "completed_reversed": ("completed", "read_reversed"),
    "short_of_best_of": ("completed", "short_of_best_of"),
    "inconsistent": ("completed", "inconsistent"),
    "unfinished_unmarked": ("retired_unmarked", "retirement_unmarked"),
    "retired": ("retired", ""),
    "walkover": ("walkover", ""),
    "walkover_after_play": ("walkover_after_play", ""),
    "bye": ("bye", ""),
    "defaulted": ("defaulted", ""),
    "abandoned": ("abandoned", ""),
    "blank": ("unknown", ""),
    "unreadable": ("unknown", ""),
}
STATUS_OF = {"completed": "completed", "retired": "retired", "retired_unmarked": "retired",
             "walkover_after_play": "retired", "walkover": "walkover", "bye": "walkover", "defaulted": "other",
             "abandoned": "other", "unknown": "other"}


def plain_match_tiebreak(score: str) -> str:
    """'certain' / 'probable' / '' for a deciding match tiebreak written as if it were a set.

    The last token comes after level sets, has no brackets and reaches 10. A set cannot end 10-7
    (a long set ends two games apart, a tiebreak set at 7-6 or 13-12), so a margin other than two,
    or one other than 13-12, is certainly a match tiebreak ('certain'); 10-8, 11-9 ... are a
    match tiebreak or a long set ('probable' here; the level decides, see below)."""
    sets, marks = A.parse_score(score)
    if len(sets) < 3 or marks:
        return ""
    a, b, t, mtb = sets[-1]
    hi, lo = max(a, b), min(a, b)
    if mtb or hi < 10:
        return ""
    ww = sum(1 for x in sets[:-1] if x[0] > x[1])
    ll = sum(1 for x in sets[:-1] if x[1] > x[0])
    if ww != ll:
        return ""
    if (hi, lo) == (13, 12) or (hi - lo == 1 and t is not None):
        return ""
    return "certain" if hi - lo != 2 else "probable"


def match_tiebreak_section(j: pd.DataFrame) -> dict:
    """How many match tiebreaks are written as sets, and what Stage 0 made of them."""
    kind = j["score"].map(plain_match_tiebreak)
    # at ITF events a deciding set has a tiebreak at 6-6, so a deciding token of 10 or more is a
    # match tiebreak whatever its margin; at Grand Slams and Davis Cup it can be a long set
    itf_like = j["level"].eq("ITF")
    plain = kind.eq("certain") | (kind.eq("probable") & itf_like)
    x = j[plain]
    mp = A.load_players(["match_id", "won", "games_won_n", "games_won_d", "tb_won_d"])
    w = mp[mp["won"]].set_index("match_id")
    games_d = w.reindex(x["match_id"])["games_won_d"]
    # games Stage 0 counted against the games actually played (the tiebreak's points removed)
    true_games = x["score"].map(lambda s: sum(a + b for a, b, _, mtb in A.parse_score(s)[0][:-1] if not mtb))
    extra = (games_d.to_numpy() - true_games.to_numpy())
    return {
        "certain": int(kind.eq("certain").sum()),
        "probable_all_levels": int(kind.eq("probable").sum()),
        "counted_as_match_tiebreaks": int(len(x)),
        "by_tour_level": x.groupby(["tour", "level"]).size().rename("matches").reset_index().to_dict(orient="records"),
        "by_tour_year": x.groupby(["tour", "year"]).size().rename("matches").reset_index().to_dict(orient="records"),
        "certain_outside_itf": j[kind.eq("certain") & ~itf_like][["match_id", "score", "level", "year"]]
        .to_dict(orient="records"),
        "format_flag_stage0": x["format"].value_counts().to_dict(),
        "evaluation_matches": int(x["evaluation"].sum()),
        "box_status_stage0": x["box_status"].value_counts().to_dict(),
        "games_counted_minus_games_played": {"matches_with_games": int(np.isfinite(extra).sum()),
                                             "median": float(np.nanmedian(extra)) if len(extra) else None,
                                             "total": float(np.nansum(extra))},
        "tiebreaks_counted_per_match_median": float(np.nanmedian(w.reindex(x["match_id"])["tb_won_d"])) if len(x) else None,
        "examples": x[["match_id", "score", "format"]].head(8).to_dict(orient="records"),
    }


NEXT = {"Q1": "Q2", "Q2": "Q3", "Q3": "Q4", "R128": "R64", "R64": "R32", "R32": "R16", "R16": "QF", "QF": "SF", "SF": "F"}


def reversed_scores_and_the_draw(j: pd.DataFrame) -> dict:
    """For the scores Stage 0 reads from the loser's side (rule C17): where the event holds a next
    round, does the recorded winner play it (the reading is supported) or the recorded loser?"""
    mp = A.load_players(["match_id", "player_id", "won"])
    w = mp[mp["won"]].set_index("match_id")["player_id"]
    l = mp[~mp["won"]].set_index("match_id")["player_id"]
    x = j[["match_id", "tour", "round", "score_flag", "level", "year", "tournament_name"]].copy()
    x["tid"] = x["match_id"].str.split("|").str[1]
    x["w"], x["l"] = x["match_id"].map(w), x["match_id"].map(l)
    seen = set(zip(x["tour"], x["tid"], x["round"], x["w"])) | set(zip(x["tour"], x["tid"], x["round"], x["l"]))
    held = set(zip(x["tour"], x["tid"], x["round"]))
    r = x[x["score_flag"].eq("read_reversed")].copy()
    r["next"] = r["round"].map(NEXT)
    r["has_next"] = [(a, b, c) in held for a, b, c in zip(r["tour"], r["tid"], r["next"])]
    r["winner_on"] = [(a, b, c, d) in seen for a, b, c, d in zip(r["tour"], r["tid"], r["next"], r["w"])]
    r["loser_on"] = [(a, b, c, d) in seen for a, b, c, d in zip(r["tour"], r["tid"], r["next"], r["l"])]
    r["draw_says"] = np.select([~r["has_next"], r["winner_on"] & ~r["loser_on"], r["loser_on"] & ~r["winner_on"]],
                               ["no next round (final, round robin, team rubber)", "recorded winner plays on",
                                "recorded loser plays on"], "neither or both")
    return {"matches": int(len(r)), "draw_says": r["draw_says"].value_counts().to_dict(),
            "by_level": r.groupby(["tour", "level", "draw_says"]).size().rename("matches").reset_index()
            .to_dict(orient="records")}


def main() -> int:
    m = A.load_matches(["match_id", "tour", "level", "qualifying", "year", "round", "status", "status_detail",
                        "score", "score_flag", "best_of", "format", "evaluation", "source", "source_file",
                        "source_row", "tournament_name", "box_status"])
    staged = A.load_staged(["score", "best_of"])
    key = ["_source_file", "_row"]
    dup_keys = int(staged.duplicated(key).sum())
    j = m.merge(staged[key + ["score", "best_of"]].rename(columns={"score": "staged_score", "best_of": "staged_bo"}),
                left_on=["source_file", "source_row"], right_on=key, how="left", validate="one_to_one")
    found = j["staged_score"].notna()
    same_score = j["staged_score"].fillna("").str.strip().eq(j["score"])

    short = j["format"].eq("short_sets")
    j["audit_reading"] = [A.classify_score(s, b, sh) for s, b, sh in zip(j["score"], j["best_of"].astype("float"), short)]
    exp = j["audit_reading"].map(EXPECT)
    j["expected_detail"] = exp.map(lambda t: t[0])
    j["expected_flag"] = exp.map(lambda t: t[1])
    j["expected_status"] = j["expected_detail"].map(STATUS_OF)
    j["detail_agrees"] = j["expected_detail"].eq(j["status_detail"])
    j["status_agrees"] = j["expected_status"].eq(j["status"])
    j["flag_agrees"] = j["expected_flag"].eq(j["score_flag"].fillna(""))

    cross = pd.crosstab([j["tour"], j["audit_reading"]], j["status_detail"]).reset_index()
    cross.to_csv(A.out_dir() / "status_crosstab.csv", index=False)
    bad = j[~(j["detail_agrees"] & j["flag_agrees"])]
    groups = (bad.groupby(["tour", "audit_reading", "status_detail", "score_flag"], dropna=False)
              .agg(matches=("match_id", "size"), example_scores=("score", lambda s: " | ".join(s.value_counts().index[:6])),
                   levels=("level", lambda s: ", ".join(f"{k} {v}" for k, v in s.value_counts().items())),
                   years=("year", lambda s: f"{s.min()}-{s.max()}"))
              .reset_index().sort_values("matches", ascending=False))
    groups.to_csv(A.out_dir() / "status_disagreements.csv", index=False)

    # retirements whose score already shows a finished match, and walkovers with games
    need = (j["best_of"].astype("float").fillna(3) // 2 + 1).to_numpy()
    tally = [A.set_tally(s, sh) for s, sh in zip(j["score"], short)]
    j["winner_finished"] = np.array([t[0] for t in tally]) >= need
    ret_complete = j[j["status_detail"].eq("retired") & j["winner_finished"]]
    wo_games = j[j["status_detail"].eq("walkover_after_play")]

    # the evaluation flag against status
    ev_scope = j["level"].isin(["GS", "FIN", "T1000", "T500", "T250", "CH"]) & j["year"].between(2013, 2026)
    ev_wrong = j[ev_scope & (j["evaluation"] != j["status"].isin(["completed", "retired"]))]
    ev_out_of_scope = j[~ev_scope & j["evaluation"]]

    tab = j.groupby(["tour", "status"]).size().unstack(fill_value=0)
    left_out = j[ev_scope & ~j["evaluation"]].groupby(["tour", "status"]).size().unstack(fill_value=0)
    summary = {
        "matches": int(len(j)),
        "staged_rows_with_duplicate_keys": dup_keys,
        "staged_row_found": int(found.sum()),
        "score_equal_to_staged_row": int(same_score.sum()),
        "score_differs_from_staged_row_examples": j.loc[found & ~same_score, ["match_id", "score", "staged_score"]]
        .head(10).to_dict(orient="records"),
        "status_detail_and_flag_agree": int((j["detail_agrees"] & j["flag_agrees"]).sum()),
        "status_agrees": int(j["status_agrees"].sum()),
        "disagreement_groups": groups.to_dict(orient="records"),
        "status_by_tour": tab.to_dict(orient="index"),
        "c18_unfinished_unmarked_by_tour": j[j["status_detail"].eq("retired_unmarked")].groupby("tour").size().to_dict(),
        "c18_by_level_year": j[j["status_detail"].eq("retired_unmarked")].groupby(["tour", "level", "year"]).size()
        .rename("matches").reset_index().to_dict(orient="records"),
        "walkover_after_play": wo_games[["match_id", "score", "tournament_name", "year"]].to_dict(orient="records"),
        "retired_with_a_finished_score": {"matches": int(len(ret_complete)),
                                          "by_tour": ret_complete.groupby("tour").size().to_dict(),
                                          "examples": ret_complete[["match_id", "score", "best_of", "level", "year"]]
                                          .head(12).to_dict(orient="records")},
        "evaluation_flag_disagrees_with_status_in_scope": int(len(ev_wrong)),
        "evaluation_flag_outside_scope": int(len(ev_out_of_scope)),
        "evaluation_scope_left_out_by_status": left_out.to_dict(orient="index"),
        "retired_share_of_evaluation": j[j["evaluation"]].groupby("tour")["status"]
        .apply(lambda s: round(100 * s.eq("retired").mean(), 2)).to_dict(),
        "match_tiebreaks_written_as_sets": match_tiebreak_section(j),
        "scores_read_reversed_and_the_draw": reversed_scores_and_the_draw(j),
    }
    print("C17 and the draw:", summary["scores_read_reversed_and_the_draw"]["draw_says"])
    mt = summary["match_tiebreaks_written_as_sets"]
    print("plain-written match tiebreaks:", {k: v for k, v in mt.items() if k not in ("by_tour_year", "examples")})
    A.write_json("status.json", summary)
    print(pd.crosstab(j["audit_reading"], j["status_detail"]).to_string())
    print(groups.head(30).to_string())
    for k in ("matches", "staged_row_found", "score_equal_to_staged_row", "status_detail_and_flag_agree", "status_agrees",
              "evaluation_flag_disagrees_with_status_in_scope", "evaluation_flag_outside_scope"):
        print(k, summary[k])
    print("by tour", summary["status_by_tour"])
    print("left out", summary["evaluation_scope_left_out_by_status"])
    print("C18", summary["c18_unfinished_unmarked_by_tour"])
    print("retired with finished score", summary["retired_with_a_finished_score"]["matches"],
          summary["retired_with_a_finished_score"]["by_tour"])
    for e in summary["retired_with_a_finished_score"]["examples"]:
        print("  ", e)
    print("walkover after play", summary["walkover_after_play"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
