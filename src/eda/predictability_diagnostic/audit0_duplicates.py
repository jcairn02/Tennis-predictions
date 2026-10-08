"""Audit of Stage 0, check 2: duplicates (the same players, event and round appearing twice).

The match id (tour, tournament id, round and the two sorted player ids) is unique by construction,
so a duplicate can only hide behind a difference in one of its parts. Searched here:

    D-a  the match id itself repeated;
    D-b  the same tournament id and round, the same two players by name (their ids differ);
    D-c  the same two players (ids, else names) twice in one event (tournament id), in rounds where
         a pair cannot meet twice: knockout rounds of one draw, or identical set scores anywhere;
    D-d  the same two players in two events of the same fortnight with identical set scores;
    D-e  a player twice in one round of one event outside round robins and team events.

Candidates are read, not assumed: identical set scores and the same winner make a repeat certain;
round robins that end in a knockout final can hold a real rematch.
Writes audit0/duplicates.csv and audit0/duplicates.json.
Run: ./python.sh src/eda/predictability_diagnostic/audit0_duplicates.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.predictability_diagnostic import audit0_common as A  # noqa: E402

KO = ["Q1", "Q2", "Q3", "Q4", "R128", "R64", "R32", "R16", "QF", "SF", "F", "BR"]
QUAL = ["Q1", "Q2", "Q3", "Q4"]


def set_key(score: str) -> str:
    """The set scores alone, from the winner's side, sorted pairs kept in order ('6-4 7-6')."""
    sets, _ = A.parse_score(score)
    return " ".join(f"{a}-{b}" + ("m" if mtb else "") for a, b, _, mtb in sets)


def load() -> pd.DataFrame:
    m = A.load_matches(["match_id", "tour", "tournament_id", "tournament_name", "tournament_date", "level", "qualifying",
                        "round", "status", "score", "score_flag", "source", "tml_link", "year", "evaluation"])
    names = A.names_by_side()
    m = m.join(names, on="match_id")
    m["id_pair"] = np.where(m["winner_id"] < m["loser_id"], m["winner_id"] + "|" + m["loser_id"],
                            m["loser_id"] + "|" + m["winner_id"])
    m["name_pair"] = A.pair_key(m["winner_name"], m["loser_name"])
    m["sets"] = m["score"].map(set_key)
    m["winner_key"] = m["winner_name"].map(A.full_key)
    return m


def pairs_within(m: pd.DataFrame, key: str, days: int) -> pd.DataFrame:
    """Every two matches of the same tour and pair (by ``key``) whose tournament dates are at most
    ``days`` apart (each unordered pair once)."""
    cols = ["match_id", "tour", key, "tournament_id", "tournament_name", "tournament_date", "round", "level", "sets",
            "winner_key", "source", "status", "evaluation"]
    g = m[cols]
    many = g[g.duplicated(["tour", key], keep=False)]
    j = many.merge(many, on=["tour", key], suffixes=("_1", "_2"))
    j = j[j["match_id_1"] < j["match_id_2"]]
    gap = (j["tournament_date_2"] - j["tournament_date_1"]).dt.days.abs()
    return j[gap <= days].assign(days=gap[gap <= days])


def classify(j: pd.DataFrame) -> pd.DataFrame:
    j = j.copy()
    j["same_event"] = j["tournament_id_1"].eq(j["tournament_id_2"])
    j["same_round"] = j["round_1"].eq(j["round_2"])
    j["same_sets"] = j["sets_1"].eq(j["sets_2"]) & j["sets_1"].ne("")
    j["same_winner"] = j["winner_key_1"].eq(j["winner_key_2"])
    both_ko = j["round_1"].isin(KO) & j["round_2"].isin(KO)
    q_vs_main = j["round_1"].isin(QUAL) ^ j["round_2"].isin(QUAL)
    j["kind"] = np.select(
        [j["same_event"] & j["same_round"],
         j["same_event"] & j["same_sets"],
         j["same_event"] & both_ko & ~q_vs_main,
         j["same_event"],
         j["same_sets"] & j["same_winner"] & (j["days"] <= 7),
         j["same_sets"] & j["same_winner"]],
        ["same event and round",
         "same event, other round, identical set scores",
         "same event, two knockout rounds of one draw",
         "same event, round robin or qualifying and main draw (a rematch is possible)",
         "other event within 7 days, identical set scores and winner",
         "other event 8-14 days apart, identical set scores and winner"],
        "other event, different scores (distinct matches)")
    return j


def appended_repeats(m: pd.DataFrame) -> dict:
    """The appended Tennis My Life rows that repeat a Sackmann match (found in audit0_linking.py):
    for each, its Sackmann twin (same players by name, same score, same tournament id or within a
    week), and which part of the match id differs, so the repeat escaped the id-based rules."""
    path = A.AUDIT / "linking.json"
    if not path.exists():
        return {"note": "run audit0_linking.py first"}
    rows = pd.DataFrame(json.loads(path.read_text(encoding="utf-8"))["appended"]["sackmann_holds_it_rows"])
    t = rows[["match_id"]].merge(m, on="match_id")
    sk = m[m["source"].eq("sackmann")]
    out = []
    for r in t.itertuples():
        c = sk[(sk["tour"] == r.tour) & (((sk["tournament_date"] - r.tournament_date).dt.days.abs() <= 7)
                                         | (sk["tournament_id"] == r.tournament_id)) & sk["score"].eq(r.score)]
        c = c[[A.same_person(a, r.winner_name) and A.same_person(b, r.loser_name) for a, b in zip(c["winner_name"], c["loser_name"])]]
        kind = "Billie Jean King Cup" if "BJK" in r.tournament_name else (
            "Davis Cup" if "Davis Cup" in r.tournament_name else r.tournament_name)
        if c.empty:
            out.append({"kind": kind, "twin": "not found by this rule"})
            continue
        x = c.iloc[0]
        coded = any(str(i).startswith("atpcode:") or ":name:" in str(i) for i in (r.winner_id, r.loser_id))
        out.append({"kind": kind, "twin": "found", "days_to_twin": int((x["tournament_date"] - r.tournament_date).days),
                    "same_tournament_id": bool(x["tournament_id"] == r.tournament_id), "same_round": bool(x["round"] == r.round),
                    "both_player_ids_same": bool(x["winner_id"] == r.winner_id and x["loser_id"] == r.loser_id),
                    "a_player_under_a_code_or_name_id": coded})
    o = pd.DataFrame(out)
    return {"rows": int(len(o)),
            "by_kind": o.groupby(["kind", "twin"]).size().rename("rows").reset_index().to_dict(orient="records"),
            "days_to_twin": o.groupby(["kind", "days_to_twin"]).size().rename("rows").reset_index().to_dict(orient="records"),
            "what_differs": o[o["twin"].eq("found")].groupby(["kind", "same_tournament_id", "same_round",
                                                               "both_player_ids_same", "a_player_under_a_code_or_name_id"])
            .size().rename("rows").reset_index().to_dict(orient="records"),
            "sackmann_davis_cup_rounds": m.loc[m["source"].eq("sackmann") & m["tournament_name"].str.contains("Davis Cup"),
                                               "round"].value_counts().to_dict()}


def main() -> int:
    m = load()
    out = {"matches": int(len(m)), "D_a_match_id_repeated": int(m["match_id"].duplicated().sum())}

    # D-b: same tournament id and round, same two names, different ids
    k = m.groupby(["tour", "tournament_id", "round", "name_pair"])["match_id"].transform("size") > 1
    out["D_b_same_event_round_names_other_ids"] = int(k.sum())
    out["D_b_rows"] = m.loc[k, ["match_id", "winner_name", "loser_name", "score", "source"]].to_dict(orient="records")

    # D-c and D-d, by ids and by names
    by_id = classify(pairs_within(m, "id_pair", 14))
    by_name = classify(pairs_within(m, "name_pair", 14))
    by_name = by_name[~by_name.set_index(["match_id_1", "match_id_2"]).index.isin(
        by_id.set_index(["match_id_1", "match_id_2"]).index)]
    allp = pd.concat([by_id.assign(found_by="ids"), by_name.assign(found_by="names only")], ignore_index=True)
    dup_kinds = ["same event and round", "same event, other round, identical set scores",
                 "same event, two knockout rounds of one draw", "other event within 7 days, identical set scores and winner"]
    cand = allp[allp["kind"].isin(dup_kinds + ["same event, round robin or qualifying and main draw (a rematch is possible)",
                                               "other event 8-14 days apart, identical set scores and winner"])]
    cand.to_csv(A.out_dir() / "duplicates.csv", index=False)
    # a control for chance: among pairs who met in two different events 7 days apart, and 14 days
    # apart, how often are the set scores and the winner identical?
    other = by_id[~by_id["same_event"]]
    control = {}
    for d in (7, 14):
        g = other[other["days"].eq(d)]
        control[str(d)] = {"pairs": int(len(g)), "identical_scores_and_winner": int((g["same_sets"] & g["same_winner"]).sum()),
                           "share_pct": round(100 * float((g["same_sets"] & g["same_winner"]).mean()), 2) if len(g) else None}
    out["chance_control_other_events"] = control
    out["pairs_by_kind"] = allp.groupby(["found_by", "kind"]).size().rename("pairs").reset_index().to_dict(orient="records")
    sure = allp[allp["kind"].isin(dup_kinds)]
    out["probable_repeats"] = {
        "pairs": int(len(sure)),
        "by_kind_level_source": sure.groupby(["kind", "level_1", "source_1", "source_2"]).size().rename("pairs")
        .reset_index().to_dict(orient="records"),
        "evaluation_matches_involved": int(len(set(sure.loc[sure["evaluation_1"], "match_id_1"]) |
                                              set(sure.loc[sure["evaluation_2"], "match_id_2"]))),
        "events": sure.groupby(["tour", "tournament_name_1", "tournament_name_2"]).size().rename("pairs")
        .reset_index().sort_values("pairs", ascending=False).head(40).to_dict(orient="records"),
    }

    # D-e: a player twice in one round of one event (knockout rounds, not team events)
    ko = m[m["round"].isin(KO) & m["level"].ne("TEAM")]
    rows = pd.concat([ko[["match_id", "tour", "tournament_id", "round", "winner_id"]].rename(columns={"winner_id": "player"}),
                      ko[["match_id", "tour", "tournament_id", "round", "loser_id"]].rename(columns={"loser_id": "player"})])
    twice = rows[rows.duplicated(["tour", "tournament_id", "round", "player"], keep=False)]
    tm = m[m["match_id"].isin(twice["match_id"])]
    out["D_e_player_twice_in_one_knockout_round"] = {
        "player_rows": int(len(twice)), "matches": int(twice["match_id"].nunique()),
        "events": int(twice[["tour", "tournament_id"]].drop_duplicates().shape[0]),
        "by_source_level_qualifying": tm.groupby(["source", "tour", "level", "qualifying"]).size().rename("matches")
        .reset_index().to_dict(orient="records"),
        "by_year": tm.groupby("year").size().to_dict(),
        "evaluation_matches": int(tm["evaluation"].sum()),
        "same_score_twice": int(tm.duplicated(["tour", "tournament_id", "round", "sets", "winner_key"], keep=False).sum()),
        "examples": m[m["match_id"].isin(twice["match_id"])].sort_values(["tournament_id", "round"])
        [["match_id", "winner_name", "loser_name", "score", "source", "level"]].head(30).to_dict(orient="records")}

    out["appended_repeats"] = appended_repeats(m)
    A.write_json("duplicates.json", out)
    print("appended repeats", {k: v for k, v in out["appended_repeats"].items()})
    print({k: v for k, v in out.items() if k not in ("D_b_rows", "pairs_by_kind", "probable_repeats",
                                                     "D_e_player_twice_in_one_knockout_round")})
    print(pd.DataFrame(out["pairs_by_kind"]).to_string())
    print("probable repeats", out["probable_repeats"]["pairs"], "evaluation matches involved",
          out["probable_repeats"]["evaluation_matches_involved"])
    print(pd.DataFrame(out["probable_repeats"]["by_kind_level_source"]).to_string())
    print(pd.DataFrame(out["probable_repeats"]["events"]).to_string())
    print("D-e", {k: v for k, v in out["D_e_player_twice_in_one_knockout_round"].items() if k != "examples"})
    for e in out["D_e_player_twice_in_one_knockout_round"]["examples"][:30]:
        print("  ", e)
    return 0


if __name__ == "__main__":
    sys.exit(main())
