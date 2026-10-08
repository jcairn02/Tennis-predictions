"""Audit of Stage 0, check 1: match counts by tour x level x year against the data map.

Stage 0's matches (2018 on, walkovers and blank scores left out as the map leaves them out) are
counted in the map's cells (tour M/W, the map's level codes, year) and compared with
data/studies/data_map/coverage_cells.csv as it stands now, and with the map's own matches first
listed by the two result files (creator Tennis My Life or Sackmann, from its matches.parquet).

Every difference is then taken apart exactly: the map's own first two steps (src/eda/data_map/
measure.py: Tennis My Life, then Sackmann) are run again here, read-only, with each staged row's
provenance carried along in memory, so every Stage 0 match can be followed to the map match its
staged row became. A cell's difference is then the sum of: Stage 0 matches the map merges into
another match; matches the two file in different cells; map matches with no Stage 0 match; and
Stage 0 matches whose staged row the map does not place.

Writes audit0/counts_cells.csv, audit0/counts_reconciliation.csv and audit0/counts.json.
Run: ./python.sh src/eda/predictability_diagnostic/audit0_counts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from src.eda.data_map import measure as M  # noqa: E402  (the map's own code, run read-only)
from src.eda.predictability_diagnostic import audit0_common as A  # noqa: E402

QUAL_OF = {"GS": "GSQ", "T1000": "TQ", "T500": "TQ", "T250": "TQ", "FIN": "TQ", "CH": "CHQ", "ITF": "ITFQ"}
RESULT = {"sackmann", "tml"}
MAP_END = pd.Timestamp("2026-09-27")        # the map's window end (build_report.json)
BIG_PCT, BIG_N = 1.0, 10
KEY = ["tour", "level", "year"]


def sets_of(score) -> str:
    sets, _ = A.parse_score(score)
    return " ".join(f"{a}-{b}" for a, b, _, _ in sets)


def stage0_played() -> pd.DataFrame:
    m = A.load_matches(["match_id", "tour", "level", "qualifying", "year", "tournament_date", "tournament_name",
                        "round", "score", "status", "source", "map_level", "source_file", "source_row"])
    names = A.names_by_side()
    m = m.join(names[["winner_name", "loser_name"]], on="match_id")
    # the map's rule: a score containing W/O or 'walkover', or a blank score, is not a played match
    s = m["score"].fillna("").astype(str)
    wo = s.str.contains(r"W/O|walkover", case=False, regex=True) | s.str.strip().eq("")
    m = m[~wo & (m["year"] >= 2018)].copy()
    m["mtour"] = m["tour"].map({"atp": "M", "wta": "W"})
    m["mlevel"] = np.where(m["qualifying"], m["level"].map(QUAL_OF).fillna(m["level"]), m["level"])
    m["pair"] = M.pair_key(m["winner_name"].map(M.surname_key), m["loser_name"].map(M.surname_key))
    return m


def rerun_map() -> tuple[pd.DataFrame, pd.DataFrame]:
    """The map's Tennis My Life and Sackmann steps, with staged provenance carried in memory.
    Returns the map's result-file matches and every placed staged row (with its uid)."""
    orig_rows, orig_cols = M._match_rows, M.MATCH_COLS

    def with_provenance(frame, tour, level_fn):
        out = orig_rows(frame, tour, level_fn)
        out["_source_file"] = frame.loc[out.index, "_source_file"].to_numpy()
        out["_row"] = pd.to_numeric(frame.loc[out.index, "_row"]).to_numpy()
        return out

    M._match_rows, M.MATCH_COLS = with_provenance, orig_cols + ["_source_file", "_row"]
    try:
        u = M.Universe(MAP_END)
        tml = M.load_tml()
        placed_tml = u.add("tml", tml)
        tml_levels = {}                      # as measure.build() makes it
        for tour, year, name, level, draw in zip(tml["tour"], tml["year"], tml["tname"].str.lower().str.strip(),
                                                 tml["level"], tml["draw"]):
            if draw == "main":
                tml_levels.setdefault((tour, year, name), level)
        placed_sack = u.add("sackmann", M.load_sackmann(tml_levels))
    finally:
        M._match_rows, M.MATCH_COLS = orig_rows, orig_cols
    placed = pd.concat([placed_tml.assign(src="tml"), placed_sack.assign(src="sackmann")], ignore_index=True)
    return u.matches.copy(), placed


def main() -> int:
    s0 = stage0_played()
    mm = pd.read_parquet(A.MAP_DIR / "matches.parquet", columns=["uid", "tour", "level", "draw", "year", "d", "name1",
                                                                 "name2", "tname", "creator"])
    cells = pd.read_csv(A.MAP_DIR / "coverage_cells.csv")

    # ------------------------------------------------------------ the cell comparison
    ours = s0.groupby(["mtour", "mlevel", "year"]).size().rename("stage0")
    ours.index.names = KEY
    rf = mm[mm["creator"].isin(RESULT)].groupby(KEY).size().rename("map_result_files")
    out = cells.set_index(KEY)[["matches"]].rename(columns={"matches": "map_all_sources"}) \
        .join(rf, how="left").join(mm.groupby(KEY).size().rename("map_matches_parquet"), how="left") \
        .join(ours, how="outer").fillna(0).astype(int).reset_index()
    out = out[out["year"] >= 2018]
    out["diff"] = out["stage0"] - out["map_result_files"]
    out["diff_pct"] = (100 * out["diff"] / out["map_result_files"].where(out["map_result_files"] > 0)).round(2)
    big = out[((out["diff_pct"].abs() > BIG_PCT) & (out["diff"].abs() >= BIG_N))
              | (out["map_result_files"].eq(0) & out["stage0"].ge(BIG_N))]
    old = pd.read_csv(A.STUDY / "stage0_check_counts.csv").set_index(KEY)
    joined = out.set_index(KEY).join(old[["stage0", "map_result_files", "map_all_sources"]], rsuffix="_stage0_check")
    changed = joined[(joined["map_result_files"] != joined["map_result_files_stage0_check"])
                     | (joined["map_all_sources"] != joined["map_all_sources_stage0_check"])]
    parquet_vs_cells = out[out["map_all_sources"] != out["map_matches_parquet"]]

    # ------------------------------------------------------------ the map re-run and the decomposition
    umatches, placed = rerun_map()
    rerun_cells = umatches[umatches["year"] >= 2018].groupby(KEY).size().rename("rerun")
    reproduced = out.set_index(KEY)[["map_result_files"]].join(rerun_cells, how="outer").fillna(0)
    uid_of = placed.dropna(subset=["uid"]).drop_duplicates(["_source_file", "_row"]).set_index(["_source_file", "_row"])["uid"]
    s0["uid"] = pd.Series(list(zip(s0["source_file"], s0["source_row"])), index=s0.index).map(uid_of)
    um = umatches.set_index("uid")
    s0["map_cell"] = s0["uid"].map(um["level"]) + " " + s0["uid"].map(um["year"]).astype("Int64").astype(str)
    s0["cell"] = s0["mlevel"] + " " + s0["year"].astype(str)
    s0 = s0.sort_values(["uid", "source", "tournament_date", "match_id"])   # Sackmann first, as the map adds it... after TML
    s0["rank_in_uid"] = s0.groupby("uid").cumcount()
    s0["kind"] = np.select(
        [s0["uid"].isna(), s0["rank_in_uid"] > 0, s0["map_cell"].ne(s0["cell"])],
        ["staged row not placed by the map", "merged by the map into another Stage 0 match's map match",
         "in the map in another cell"], "same map match, same cell")
    first = s0[s0["uid"].notna() & s0["rank_in_uid"].eq(0)]
    moved_in = first[first["map_cell"].ne(first["cell"])]
    held = set(s0["uid"].dropna().astype("int64"))
    only = umatches[(umatches["year"] >= 2018) & ~umatches["uid"].isin(held)].copy()
    creator_row = placed.dropna(subset=["uid"]).sort_values("src", ascending=False)   # 'tml' before 'sackmann'
    creator_row = creator_row[creator_row["uid"].isin(only["uid"])].drop_duplicates("uid").set_index("uid")
    only["row_src"] = only["uid"].map(creator_row["src"])
    only["round"] = only["uid"].map(creator_row["round"])
    # a map-only match from TML: does Stage 0 hold the pair in the same event, on another date?
    s0_by_pair = s0[s0["uid"].notna()][["mtour", "pair", "tournament_date", "tournament_name", "round"]]
    cand = only[["uid", "tour", "d", "tname", "name1", "name2"]].assign(
        pair=lambda f: M.pair_key(f["name1"].map(M.surname_key), f["name2"].map(M.surname_key))).merge(
        s0_by_pair.rename(columns={"mtour": "tour"}), on=["tour", "pair"])
    cand = cand[((cand["d"] - cand["tournament_date"]).dt.days.abs() <= 400).to_numpy()
                & np.array([bool(A.event_words(a) & A.event_words(b))
                            for a, b in zip(cand["tname"], cand["tournament_name"])], dtype=bool)]
    only["kind"] = np.where(only["uid"].isin(cand["uid"]),
                            "Stage 0 holds the pair in the same event on another date (one match, two copies in the map)",
                            np.where(only["row_src"].eq("tml"), "a Tennis My Life row Stage 0 does not keep",
                                     "a Sackmann row Stage 0 does not keep"))

    rec = []
    for (t, lv, y), g in out.set_index(KEY).iterrows():
        c = f"{lv} {y}"
        sc = s0[(s0["mtour"] == t) & (s0["cell"] == c)]
        rec.append({"tour": t, "level": lv, "year": int(y), "stage0": int(g["stage0"]),
                    "map_result_files": int(g["map_result_files"]), "diff": int(g["diff"]),
                    "merged_by_the_map": int(sc["kind"].str.startswith("merged").sum()),
                    "stage0_row_not_placed_by_the_map": int(sc["kind"].str.startswith("staged row").sum()),
                    "map_files_elsewhere": int(sc["kind"].eq("in the map in another cell").sum()),
                    "map_files_here_stage0_elsewhere": int(((moved_in["mtour"] == t) & (moved_in["map_cell"] == c)).sum()),
                    "map_only": int(((only["tour"] == t) & (only["level"] == lv) & (only["year"] == y)).sum())})
    rec = pd.DataFrame(rec)
    rec["identity_residual"] = (rec["merged_by_the_map"] + rec["stage0_row_not_placed_by_the_map"] + rec["map_files_elsewhere"]
                                - rec["map_files_here_stage0_elsewhere"] - rec["map_only"]) - rec["diff"]
    rec.to_csv(A.out_dir() / "counts_reconciliation.csv", index=False)
    out.to_csv(A.out_dir() / "counts_cells.csv", index=False)

    def top(frame: pd.DataFrame, cols: list[str], n: int = 6) -> list:
        return frame.groupby(cols, dropna=False).size().rename("matches").reset_index() \
            .sort_values("matches", ascending=False).head(n).to_dict(orient="records")

    # why the map merges two Stage 0 matches: what the merged pair looks like
    merged = s0[s0["kind"].str.startswith("merged")].merge(
        s0[s0["rank_in_uid"].eq(0)][["uid", "tournament_name", "mlevel", "round", "pair", "tournament_date", "source",
                                     "score"]]
        .rename(columns={"tournament_name": "kept_tname", "mlevel": "kept_level", "round": "kept_round", "pair": "kept_pair",
                         "tournament_date": "kept_date", "source": "kept_source", "score": "kept_score"}), on="uid")
    merged["same_pair"] = merged["pair"].eq(merged["kept_pair"])
    merged["same_event"] = [bool(A.event_words(a) & A.event_words(b)) for a, b in zip(merged["tournament_name"], merged["kept_tname"])]
    merged["same_sets"] = [sets_of(a) == sets_of(b) and sets_of(a) != "" for a, b in zip(merged["score"], merged["kept_score"])]
    merged["days"] = (merged["tournament_date"] - merged["kept_date"]).dt.days
    merged["how"] = np.select(
        [merged["same_pair"] & merged["same_event"] & merged["same_sets"],
         merged["same_pair"] & merged["same_event"] & merged["round"].eq(merged["kept_round"]),
         merged["same_pair"] & ~merged["same_event"],
         merged["same_pair"],
         ~merged["same_pair"]],
        ["one match twice in Stage 0 (same surname pair, event and set scores)",
         "two matches of one event and round whose surname pairs coincide (brothers, common surnames)",
         "same surname pair, another event within the map's window (two real matches made one)",
         "same surname pair, same event, another round (two real matches made one)",
         "one shared surname (the map's fallback passes)"], "")

    explain = []
    for r in big.itertuples():
        c = f"{r.level} {r.year}"
        sc = s0[(s0["mtour"] == r.tour) & (s0["cell"] == c)]
        mi = moved_in[(moved_in["mtour"] == r.tour) & (moved_in["map_cell"] == c)]
        oc = only[(only["tour"] == r.tour) & (only["level"] == r.level) & (only["year"] == r.year)]
        mg = merged[(merged["mtour"] == r.tour) & (merged["cell"] == c)]
        away = sc[sc["kind"].eq("in the map in another cell")]
        explain.append({
            "tour": r.tour, "level": r.level, "year": int(r.year), "stage0": int(r.stage0),
            "map_result_files": int(r.map_result_files), "diff": int(r.diff),
            "merged_by_the_map": {"matches": int(len(mg)), "how": mg["how"].value_counts().to_dict(),
                                  "top": top(mg, ["tournament_name", "kept_tname"])},
            "stage0_row_not_placed_by_the_map": {"matches": int(sc["kind"].str.startswith("staged row").sum()),
                                                 "top": top(sc[sc["kind"].str.startswith("staged row")], ["tournament_name"])},
            "map_files_elsewhere": {"matches": int(len(away)), "top": top(away, ["tournament_name", "map_cell"])},
            "map_files_here": {"matches": int(len(mi)), "top": top(mi, ["tournament_name", "cell"])},
            "map_only": {"matches": int(len(oc)), "kind": oc["kind"].value_counts().to_dict(),
                         "top": top(oc, ["tname", "row_src"])},
        })

    unplaced = s0[s0["uid"].isna()].copy()
    k1, k2 = unplaced["winner_name"].map(M.surname_key), unplaced["loser_name"].map(M.surname_key)
    unplaced["why"] = np.select([k1.eq("") | k2.eq(""), k1.eq(k2)],
                                ["a name with no Latin letters", "both players share a surname key (the map drops the match)"],
                                "outside the map's dates")
    summary = {
        "map_files_modified": {
            "coverage_cells": pd.Timestamp((A.MAP_DIR / "coverage_cells.csv").stat().st_mtime, unit="s").isoformat(),
            "stage0_check_counts": pd.Timestamp((A.STUDY / "stage0_check_counts.csv").stat().st_mtime, unit="s").isoformat()},
        "cells_where_the_map_changed_since_stage0_checks": int(len(changed)),
        "stage0_map_level_column_agrees": int((s0["mlevel"] == s0["map_level"]).sum()), "stage0_rows_2018_on": int(len(s0)),
        "cells": int(len(out)), "cells_with_map_result_files": int(out["map_result_files"].gt(0).sum()),
        "cells_within_1pct": int(out["diff_pct"].abs().le(1).sum()), "large_cells": int(len(big)),
        "totals": out.groupby("tour")[["stage0", "map_result_files", "map_all_sources", "map_matches_parquet"]].sum()
        .reset_index().to_dict(orient="records"),
        "coverage_cells_differs_from_matches_parquet": parquet_vs_cells[KEY + ["map_all_sources", "map_matches_parquet"]]
        .to_dict(orient="records"),
        "rerun_reproduces_map_result_file_cells": int((reproduced["map_result_files"] == reproduced["rerun"]).sum()),
        "rerun_cells": int(len(reproduced)),
        "stage0_rows_followed_into_the_map": int(s0["uid"].notna().sum()),
        "kinds": s0["kind"].value_counts().to_dict(),
        "kinds_by_tour_level": s0[~s0["kind"].str.startswith("same map match")].groupby(["mtour", "mlevel", "kind"]).size()
        .rename("matches").reset_index().to_dict(orient="records"),
        "merged_how": merged.groupby(["mtour", "how"]).size().rename("matches").reset_index().to_dict(orient="records"),
        "merged_same_pair_other_event_days": merged.loc[merged["how"].str.startswith("same surname pair, another event"), "days"]
        .abs().value_counts().sort_index().to_dict(),
        "unplaced_why": unplaced.groupby(["mtour", "why"]).size().rename("matches").reset_index().to_dict(orient="records"),
        "unplaced_examples": unplaced[["match_id", "winner_name", "loser_name", "tournament_date", "why"]].head(10)
        .to_dict(orient="records"),
        "map_only_kinds": only.groupby(["tour", "kind"]).size().rename("matches").reset_index().to_dict(orient="records"),
        "reconciliation_identity_holds_in_cells": int(rec["identity_residual"].eq(0).sum()),
        "totals_decomposition": {t: {"stage0_minus_map_result_files": int(out.loc[out["tour"] == t, "diff"].sum()),
                                     "merged_by_the_map": merged[merged["mtour"] == t]["how"].value_counts().to_dict(),
                                     "stage0_rows_the_map_does_not_place": unplaced[unplaced["mtour"] == t]["why"]
                                     .value_counts().to_dict(),
                                     "map_only": only[only["tour"] == t]["kind"].value_counts().to_dict()}
                                 for t in ("M", "W")},
        "large_differences": explain,
    }
    A.write_json("counts.json", summary)
    print({k: v for k, v in summary.items() if k not in ("large_differences", "kinds_by_tour_level", "unplaced_examples")})
    print(rec[rec.set_index(KEY).index.isin(big.set_index(KEY).index)].to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
