"""Audit of Stage 0, check 4: the level mapping, every source code and what it became.

Every staged singles row the build reads (Sackmann and Tennis My Life, files of 2010 on) is
followed to the table by its source file and row. Rows that are matches in the table give their
level directly; TML rows that were linked to a Sackmann match are followed to that match through
the same tournament id, round and pair of names. The result is one line per source x tour x code
x level, with counts and the tournament names behind them.

The levels are then read against what the tours' calendars say (inferred from tennis knowledge,
listed per year so it can be checked by eye): the events counted as 1000s and 500s each season,
events whose level changes between seasons, and events given two levels in one season.

Writes audit0/levels_by_code.csv, audit0/levels_events_by_year.csv and audit0/levels.json.
Run: ./python.sh src/eda/predictability_diagnostic/audit0_levels.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.predictability_diagnostic import audit0_common as A  # noqa: E402

GROUP = [("sackmann_archive/atp/atp_matches_qual_chall", "Sackmann ATP qualifying + Challengers"),
         ("sackmann_archive/atp/atp_matches_futures", "Sackmann ATP Futures / ITF"),
         ("sackmann_archive/atp/atp_matches_", "Sackmann ATP main tour"),
         ("sackmann_archive/wta/wta_matches_qual_itf", "Sackmann WTA qualifying + ITF"),
         ("sackmann_archive/wta/wta_matches_", "Sackmann WTA main tour"),
         ("tennis_my_life/ongoing", "TML ongoing"), ("tennis_my_life/atp_quali", "TML ATP qualifying"),
         ("_challenger", "TML ATP Challengers"), ("_wta", "TML WTA"), ("tennis_my_life/", "TML ATP main tour")]


def group_of(path: str) -> str:
    for pat, name in GROUP:
        if pat in path:
            return name
    return "?"


def norm_tid(s: pd.Series) -> pd.Series:
    return s.fillna("").astype(str).str.strip().str.replace(r"-0+(\d)", r"-\1", regex=True)


# Events whose level in the table disagrees with the tour's calendar as the audit knows it
# (inferred, not measured: to be confirmed against the ATP's and WTA's own calendars):
# (tour, season, tournament name, the level the calendar gives)
SUSPECT = [("atp", 2014, "Vienna", "T250"), ("atp", 2014, "Valencia", "T500"),
           ("wta", 2017, "Brisbane", "T500"), ("wta", 2017, "Sydney", "T500"), ("wta", 2017, "Moscow", "T500"),
           ("wta", 2019, "Moscow", "T500"), ("wta", 2023, "Guadalajara", "T1000")]


def suspects(st: pd.DataFrame, m: pd.DataFrame) -> list:
    out = []
    for tour, year, name, cal in SUSPECT:
        s = st[(st["tour"] == tour) & (st["file_season"] == year) & st["tourney_name"].fillna("").str.strip().eq(name)]
        t = m[(m["tour"] == tour) & (m["year"] == year) & m["tournament_name"].str.strip().eq(name)]
        out.append({"tour": tour, "season": year, "event": name,
                    "codes": {src: sorted(g["code"].unique()) for src, g in s.groupby("source")},
                    "table_level": sorted(t["level"].unique()), "calendar_level_inferred": cal,
                    "matches": int(len(t)), "evaluation_matches": int(t["evaluation"].sum())})
    return out


def main() -> int:
    st = A.load_staged(["tourney_id", "tourney_name", "tourney_level", "tourney_date", "round", "winner_name",
                        "loser_name"], first_season=2010)
    st["code"] = st["tourney_level"].fillna("").astype(str).str.strip()
    st["group"] = st["_source_file"].map(group_of)
    st["season"] = st["file_season"]
    m = A.load_matches(["match_id", "tour", "level", "qualifying", "year", "tournament_id", "tournament_name", "round",
                        "source", "source_file", "source_row", "evaluation"])
    names = A.names_by_side()
    m = m.join(names[["winner_name", "loser_name"]], on="match_id")

    # rows that are matches of the table
    j = st.merge(m[["source_file", "source_row", "match_id", "level", "qualifying", "year", "evaluation"]],
                 left_on=["_source_file", "_row"], right_on=["source_file", "source_row"], how="left")
    j["fate"] = np.where(j["match_id"].notna(), "a match of the table", "")
    # TML rows linked to a Sackmann match: same tournament id and round, same two names
    t_left = j["fate"].eq("") & j["source"].eq("tml")
    sk = m[m["source"].eq("sackmann")].copy()
    sk["pair"] = A.pair_key(sk["winner_name"], sk["loser_name"])
    tl = j[t_left].copy()
    tl["pair"] = A.pair_key(tl["winner_name"].fillna(""), tl["loser_name"].fillna(""))
    tl["tid"], tl["rnd"] = norm_tid(tl["tourney_id"]), tl["round"].fillna("").str.strip().str.upper()
    hit = tl.reset_index().merge(sk[["tour", "tournament_id", "round", "pair", "level", "qualifying", "year", "match_id"]]
                                 .rename(columns={"tournament_id": "tid", "round": "rnd"}), on=["tour", "tid", "rnd", "pair"],
                                 how="inner", suffixes=("", "_s")).drop_duplicates("index").set_index("index")
    for c in ("level", "qualifying", "year", "match_id"):
        j.loc[hit.index, c] = hit[f"{c}_s"]
    j.loc[hit.index, "fate"] = "TML row of a Sackmann match (followed by tournament id, round and names)"
    j["fate"] = j["fate"].replace("", "not followed (dropped, linked under other names, or outside the table)")
    j["q"] = j["round"].fillna("").str.strip().str.upper().str.fullmatch(r"Q\d")

    by_code = (j.groupby(["source", "tour", "code", "fate", "level", "q"], dropna=False)
               .agg(rows=("_row", "size"), first_season=("season", "min"), last_season=("season", "max"),
                    examples=("tourney_name", lambda s: "; ".join(s.value_counts().index[:5])))
               .reset_index().rename(columns={"q": "qualifying_round"}))
    by_code.to_csv(A.out_dir() / "levels_by_code.csv", index=False)

    # what each code became, in one line per source x tour x code
    lines = []
    for (src, tour, code), g in j.groupby(["source", "tour", "code"], dropna=False):
        lv = g[g["level"].notna()]["level"].value_counts()
        lines.append({"source": src, "tour": tour, "code": code, "staged_rows": int(len(g)),
                      "followed": int(g["level"].notna().sum()),
                      "became": ", ".join(f"{k} {v}" for k, v in lv.items()),
                      "seasons": f"{int(g['season'].min())}-{int(g['season'].max())}"})
    lines = pd.DataFrame(lines)

    # the events of each level and season (main draws), as the table has them
    ev = m[~m["qualifying"]].groupby(["tour", "year", "level", "tournament_name"]).size().rename("matches").reset_index()
    ev.to_csv(A.out_dir() / "levels_events_by_year.csv", index=False)
    per_year = ev.groupby(["tour", "level", "year"])["tournament_name"].agg(lambda s: "; ".join(sorted(s))).reset_index()
    counts = ev.groupby(["tour", "level", "year"]).size().rename("events").reset_index()

    # an event name at two levels in one season (main draws), and names whose level changes between seasons
    base = ev.assign(name=ev["tournament_name"].str.replace(r"\s+(CH|Masters|125)$", "", regex=True).str.strip())
    two = base[base["level"].isin(["T1000", "T500", "T250", "GS", "FIN"])].groupby(["tour", "year", "name"])["level"] \
        .agg(lambda s: ", ".join(sorted(set(s)))).reset_index()
    two = two[two["level"].str.contains(",")]
    tour_lv = base[base["level"].isin(["T1000", "T500", "T250"])]
    changes = tour_lv.groupby(["tour", "name"])[["year", "level"]].apply(
        lambda g: " ".join(f"{y}:{l}" for y, l in zip(g.sort_values("year")["year"], g.sort_values("year")["level"])))
    changes = changes[tour_lv.groupby(["tour", "name"])["level"].nunique() > 1].rename("history").reset_index()

    summary = {
        "staged_rows_2010_on": int(len(j)),
        "fates": j["fate"].value_counts().to_dict(),
        "codes": lines.to_dict(orient="records"),
        "events_per_level_year": {f"{t} {lv}": dict(zip(g["year"].astype(str), g["events"]))
                                  for (t, lv), g in counts[counts["level"].isin(["GS", "FIN", "T1000", "T500"])]
                                  .groupby(["tour", "level"])},
        "t1000_and_t500_events_by_year": per_year[per_year["level"].isin(["T1000", "T500"])].to_dict(orient="records"),
        "one_name_two_levels_in_a_season": two.to_dict(orient="records"),
        "tour_level_changes_between_seasons": changes.to_dict(orient="records"),
        "suspect_events": suspects(st, m),
        "sackmann_2017_wta_tour_events_tml_lacks": sorted(set(
            st.loc[(st["source"] == "sackmann") & (st["tour"] == "wta") & (st["file_season"] == 2017)
                   & st["code"].isin(["I", "P", "W", "PM"]), "tourney_name"].str.strip())
            - set(st.loc[(st["source"] == "tml") & (st["tour"] == "wta") & (st["file_season"] == 2017), "tourney_name"]
                  .str.strip())),
    }
    A.write_json("levels.json", summary)
    print(lines.to_string())
    print(summary["fates"])
    for k, v in summary["events_per_level_year"].items():
        print(k, v)
    print(two.to_string())
    print(changes.to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
