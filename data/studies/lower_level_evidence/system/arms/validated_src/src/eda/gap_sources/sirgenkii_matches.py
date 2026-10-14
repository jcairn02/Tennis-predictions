"""Gap sources, lane B2: what the SirGenkii/infotennis SQL dumps (decrypted ATP Stats Centre data, Jan-Apr
2025) hold per match, and which atp_points_2025 gap matches they fill.

Input: data/raw/gap_sources/sirgenkii/backup_sql/*.sql (fetch_sirgenkii.py; MySQL 8.0.41 dumps from commit
1bb7527dda, 7 Apr 2025), data/studies/data_map/matches.parquet, and Tennis My Life's 2025 season files
(data/dump/matches/tennis_my_life/atp_main/2025.parquet, atp_qualifying/2025_atp_quali.parquet) for an exact
check by ATP tournament id and player codes.

What it does:
1. Parses the INSERT statements of the six tables (results, calendars, rally_analysis, key_stats,
   stroke_analysis, court_vision) without a database.
2. One row per match of the results table: tournament, category, week (the calendar's start date), draw
   (qualifying when the match code starts with 'qs'), point rows (rally analysis), point rows whose
   `point_end_type` is a winner / forced / unforced error, rows with a serve speed, and whether key stats,
   stroke analysis and Court Vision rows exist.
3. Links each match to Tennis My Life by (tourney_id 'YYYY-<id>', both ATP player codes) and to the data
   map's matches by both surnames within -10..+21 days of `d` (the map's rule, using its name functions).

Writes:
* data/studies/gap_sources/sirgenkii_matches.csv: one row per match in the dumps, with the links.
* data/studies/gap_sources/sirgenkii_summary.json: counts by month and level, and the gap fill.

Run: ./python.sh src/eda/gap_sources/sirgenkii_matches.py
"""
from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
SQL = ROOT / "data" / "raw" / "gap_sources" / "sirgenkii" / "backup_sql"
OUT = ROOT / "data" / "studies" / "gap_sources"
MAP = ROOT / "data" / "studies" / "data_map" / "matches.parquet"
TML = ROOT / "data" / "dump" / "matches" / "tennis_my_life"

_spec = importlib.util.spec_from_file_location("measure", ROOT / "src" / "eda" / "data_map" / "measure.py")
measure = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(measure)
surname_key, pair_key, same_player = measure.surname_key, measure.pair_key, measure.same_player

GAP = {"tours": ["M"], "levels": ["FIN", "T1000", "T500", "T250", "TQ"], "years": [2025, 2026]}
OUTCOME = {"WINNER", "FORCED_ERROR", "UNFORCED_ERROR", "FORCED ERROR", "UNFORCED ERROR"}


# ---------------------------------------------------------------------------------------------
# MySQL dump reader

def _columns(text: str, table: str) -> list[str]:
    m = re.search(r"CREATE TABLE `%s` \((.*?)\n\) ENGINE" % re.escape(table), text, re.S)
    cols = []
    for line in m.group(1).splitlines():
        line = line.strip()
        if line.startswith("`"):
            cols.append(line.split("`")[1])
    return cols


def _tuples(values: str):
    """Yield tuples from a MySQL VALUES list: (1,'a\\'b',NULL,2.5),(...)."""
    i, n = 0, len(values)
    row, tok, in_str, started = [], [], False, False
    while i < n:
        c = values[i]
        if in_str:
            if c == "\\" and i + 1 < n:
                nxt = values[i + 1]
                tok.append({"n": "\n", "t": "\t", "r": "\r", "0": "\0"}.get(nxt, nxt))
                i += 2
                continue
            if c == "'":
                in_str = False
            else:
                tok.append(c)
        elif c == "'":
            in_str, started = True, True
        elif c == "(" and not row and not tok and not started:
            pass
        elif c == ",":
            row.append(_value(tok, started))
            tok, started = [], False
        elif c == ")":
            row.append(_value(tok, started))
            yield row
            row, tok, started = [], [], False
            # skip to the next '('
            j = values.find("(", i)
            if j < 0:
                return
            i = j
        else:
            tok.append(c)
        i += 1


def _value(tok, quoted):
    s = "".join(tok)
    if quoted:
        return s
    s = s.strip()
    if s == "NULL" or s == "":
        return None
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return s


def read_table(name: str) -> pd.DataFrame:
    text = (SQL / f"infotennis4_atp_{name}.sql").read_text(encoding="utf-8")
    table = f"atp_{name}"
    cols = _columns(text, table)
    rows = []
    for m in re.finditer(r"INSERT INTO `%s` VALUES (.*?);\n" % re.escape(table), text, re.S):
        body = m.group(1)
        rows.extend(_tuples(body[body.index("("):]))
    df = pd.DataFrame(rows, columns=cols)
    return df


# ---------------------------------------------------------------------------------------------

def level_of(category: str, draw: str) -> str:
    c = (category or "").lower()
    if "grand slam" in c:
        return "GSQ" if draw == "qual" else "GS"
    if c == "other":
        return "TEAM"          # the United Cup is the only 'Other' event in the dumps
    if draw == "qual":
        return "TQ"
    if "1000" in c:
        return "T1000"
    if "500" in c:
        return "T500"
    if "250" in c:
        return "T250"
    if "final" in c:
        return "FIN"
    return "OTHER"


def link_map(left: pd.DataFrame, m: pd.DataFrame, lo=-10, hi=21) -> pd.DataFrame:
    """left: lid, tour, date, name1, name2, draw -> best matches.parquet uid (pair pass, then one surname)."""
    L = left.copy()
    L["k1"], L["k2"] = L["name1"].map(surname_key), L["name2"].map(surname_key)
    L["pair"] = pair_key(L["k1"], L["k2"])
    R = m[["uid", "tour", "d", "draw", "name1", "name2"]].copy()
    R["k1"], R["k2"] = R["name1"].map(surname_key), R["name2"].map(surname_key)
    R["pair"] = pair_key(R["k1"], R["k2"])

    def best(c, tag):
        c = c.copy()
        c["delta"] = (c["date"] - c["d"]).dt.days
        c = c[(c["delta"] >= lo) & (c["delta"] <= hi)]
        mism = c["draw"] != c["draw_r"]
        c["score"] = (c["delta"] - 3).abs() + np.where(mism, 40, 0)
        c = c.sort_values(["lid", "score"]).drop_duplicates("lid")
        c["pass"] = tag
        return c[["lid", "uid", "pass", "delta"]]

    c1 = L[["lid", "tour", "pair", "date", "draw"]].dropna(subset=["pair"]).merge(
        R[["uid", "tour", "pair", "d", "draw"]].rename(columns={"draw": "draw_r"}), on=["tour", "pair"])
    f1 = best(c1, "pair")
    todo = L[~L["lid"].isin(f1["lid"])]
    keys = ["lid", "tour", "date", "draw"]
    left2 = pd.concat([todo[keys].assign(key=todo["k1"], other=todo["name2"]),
                       todo[keys].assign(key=todo["k2"], other=todo["name1"])])
    right2 = pd.concat([R[["uid", "tour", "d", "draw"]].assign(key=R["k1"], rother=R["name2"]),
                        R[["uid", "tour", "d", "draw"]].assign(key=R["k2"], rother=R["name1"])]).rename(columns={"draw": "draw_r"})
    c2 = left2[left2["key"] != ""].merge(right2, on=["tour", "key"])
    c2 = c2[((c2["date"] - c2["d"]).dt.days >= lo) & ((c2["date"] - c2["d"]).dt.days <= hi)]
    if not c2.empty:
        c2 = c2[[same_player(a, b) for a, b in zip(c2["other"], c2["rother"])]]
    f2 = best(c2, "one_surname") if not c2.empty else pd.DataFrame(columns=["lid", "uid", "pass", "delta"])
    return pd.concat([f1, f2]).set_index("lid")


def main() -> None:
    res = read_table("results")
    cal = read_table("calendars")
    rally = read_table("rally_analysis")
    keys = read_table("key_stats")
    strokes = read_table("stroke_analysis")
    cv = read_table("court_vision")
    k = ["year", "tournament_id", "match_id"]
    for d in (res, cal, rally, keys, strokes, cv):
        if "tournament_id" in d:
            d["tournament_id"] = d["tournament_id"].astype(str)
        if "match_id" in d:
            d["match_id"] = d["match_id"].astype(str).str.lower()
    raw_counts = {"results": len(res), "calendars": len(cal), "rally_analysis": len(rally), "key_stats": len(keys),
                  "stroke_analysis": len(strokes), "court_vision": len(cv)}
    pe = rally["point_end_type"].fillna("").astype(str).str.upper()
    rally["_outcome"] = pe.isin(OUTCOME)
    rally["_classified"] = pe.isin(OUTCOME | {"ACE", "DOUBLE FAULT"})
    rally["_speed"] = pd.to_numeric(rally["serve_speed"], errors="coerce").fillna(0) > 0
    pts = rally.groupby(k).agg(point_rows=("point_id", "size"), outcome_rows=("_outcome", "sum"),
                               classified_rows=("_classified", "sum"), speed_rows=("_speed", "sum")).reset_index()
    ks = keys.groupby(k).size().rename("key_stat_rows").reset_index()
    st = strokes.groupby(k).size().rename("stroke_rows").reset_index()
    cvm = cv.groupby(k).agg(court_vision_rows=("id", "size"), court_vision_points=("point_id", "nunique")).reset_index()

    cal = cal.drop_duplicates(["year", "tournament_id"])
    # date_start is a range 'YYYY.MM.DD - YYYY.MM.DD'; several first dates are month placeholders
    # (Delray Beach '2025.02.01 - 2025.02.16'), so the week is taken from the end date: end - 6 days
    cal["end"] = pd.to_datetime(cal["date_start"].str.split(" - ").str[-1], format="%Y.%m.%d", errors="coerce")
    cal["week"] = cal["end"] - pd.Timedelta(days=6)
    mt = res.drop_duplicates(k).merge(cal[["year", "tournament_id", "week", "category", "draw", "surface"]]
                                      .rename(columns={"category": "cal_category", "draw": "cal_draw"}),
                                      on=["year", "tournament_id"], how="left")
    for d in (pts, ks, st, cvm):
        mt = mt.merge(d, on=k, how="left")
    for c in ("point_rows", "outcome_rows", "classified_rows", "speed_rows", "key_stat_rows", "stroke_rows",
              "court_vision_rows", "court_vision_points"):
        mt[c] = mt[c].fillna(0).astype(int)
    mt["draw"] = np.where(mt["match_id"].str.startswith("q"), "qual", "main")
    mt["level"] = [level_of(c, d) for c, d in zip(mt["category"].fillna(mt["cal_category"]), mt["draw"])]
    mt["month"] = mt["week"].dt.strftime("%Y-%m")
    # rally rows whose match is not in the results table
    orphan = pts.merge(res[k].drop_duplicates(), on=k, how="left", indicator=True)
    orphan_n = int((orphan["_merge"] == "left_only").sum())

    # exact link to Tennis My Life: tourney_id 'YYYY-<id>' plus both ATP player codes
    tml = pd.concat([pd.read_parquet(TML / "atp_main" / "2025.parquet"),
                     pd.read_parquet(TML / "atp_qualifying" / "2025_atp_quali.parquet")], ignore_index=True)
    tml["tid"] = tml["tourney_id"].astype(str).str.split("-").str[-1].str.lstrip("0")
    tml["codes"] = [frozenset((str(a).upper(), str(b).upper())) for a, b in zip(tml["winner_id"], tml["loser_id"])]
    tml["tdate"] = pd.to_datetime(tml["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    tml_key = {(t, c): (sc, w, l, r, td) for t, c, sc, w, l, r, td in
               zip(tml["tid"], tml["codes"], tml["score"], tml["winner_name"], tml["loser_name"], tml["round"],
                   tml["tdate"])}
    mt["tid"] = mt["tournament_id"].str.lstrip("0")
    hits = [tml_key.get((t, frozenset((str(a).upper(), str(b).upper()))))
            for t, a, b in zip(mt["tid"], mt["player1_id"], mt["player2_id"])]
    mt["tml_linked"] = [h is not None for h in hits]
    mt["tml_score"] = [h[0] if h else None for h in hits]
    mt["tml_round"] = [h[3] if h else None for h in hits]
    mt["tml_tourney_date"] = [h[4] if h else pd.NaT for h in hits]
    # the week for reporting and linking: Tennis My Life's tournament date where linked, else end - 6 days
    mt["week"] = pd.to_datetime(mt["tml_tourney_date"]).fillna(mt["week"])
    mt["month"] = mt["week"].dt.strftime("%Y-%m")

    # link to the data map
    m = pd.read_parquet(MAP)
    m = m[(m["tour"] == "M") & m["year"].isin([2024, 2025, 2026])].copy()
    left = pd.DataFrame({"lid": mt.index, "tour": "M", "name1": mt["player1_name"], "name2": mt["player2_name"],
                         "draw": mt["draw"], "date": mt["week"] + pd.Timedelta(days=3)})
    lk = link_map(left, m)
    mt = mt.join(lk[["uid", "pass", "delta"]], how="left")
    mt = mt.merge(m[["uid", "level", "year", "d", "best", "tname", "name1", "name2"]]
                  .rename(columns={"level": "map_level", "year": "map_year", "d": "map_d", "best": "map_best",
                                   "tname": "map_tname", "name1": "map_name1", "name2": "map_name2"}), on="uid", how="left")
    gap_all = m[m["level"].isin(GAP["levels"]) & m["year"].isin(GAP["years"]) & m["best"].isin(["result", "stats"])]
    mt["in_gap"] = mt["uid"].isin(gap_all["uid"])
    mt["fills_gap_points"] = mt["in_gap"] & mt["point_rows"].gt(0)
    mt["fills_gap_outcomes"] = mt["in_gap"] & mt["outcome_rows"].gt(0)
    slam_gap = m[m["level"].eq("GS") & m["year"].eq(2025) & m["tname"].fillna("").str.contains("Australian")
                 & m["best"].isin(["result", "stats"])]
    mt["in_ao2025_gap"] = mt["uid"].isin(slam_gap["uid"])
    # overlap with the Kaggle marcosjn2 fills (marcosjn2_links.py), when that table exists
    mk = OUT / "marcosjn2_gap_links.csv"
    mk_uids = set(pd.read_csv(mk).query("gap == 'atp_points_2025'")["uid"]) if mk.exists() else set()
    mt["also_in_marcosjn2"] = mt["uid"].isin(mk_uids)

    cols = ["year", "tournament", "tournament_id", "category", "level", "draw", "week", "month", "match_id", "round",
            "player1_name", "player1_id", "player2_name", "player2_id", "score", "point_rows", "outcome_rows",
            "classified_rows", "speed_rows", "key_stat_rows", "stroke_rows", "court_vision_rows", "court_vision_points", "tml_linked",
            "tml_score", "tml_round", "uid", "pass", "delta", "map_level", "map_best", "map_d", "map_tname",
            "map_name1", "map_name2", "in_gap", "fills_gap_points", "fills_gap_outcomes", "in_ao2025_gap",
            "also_in_marcosjn2"]
    out = mt[cols].copy()
    out["week"] = out["week"].dt.date
    out["map_d"] = pd.to_datetime(out["map_d"]).dt.date
    out["uid"] = out["uid"].astype("Int64")
    out.sort_values(["week", "tournament_id", "match_id"]).to_csv(OUT / "sirgenkii_matches.csv", index=False, encoding="utf-8")

    def tab(df, by):
        g = df.groupby(by).agg(matches=("match_id", "size"), with_points=("point_rows", lambda s: int((s > 0).sum())),
                               with_outcomes=("outcome_rows", lambda s: int((s > 0).sum())),
                               with_serve_speed=("speed_rows", lambda s: int((s > 0).sum())),
                               with_key_stats=("key_stat_rows", lambda s: int((s > 0).sum())),
                               with_court_vision=("court_vision_rows", lambda s: int((s > 0).sum())),
                               point_rows=("point_rows", "sum"), outcome_rows=("outcome_rows", "sum"))
        return [dict(zip(by if isinstance(by, list) else [by], ix if isinstance(ix, tuple) else (ix,)), **{c: int(v) for c, v in row.items()})
                for ix, row in g.iterrows()]

    gap25 = gap_all[gap_all["d"] < "2025-05-01"]
    summary = {
        "source": {"repo": "SirGenkii/infotennis", "commit_head": "ec1b188f30e9bccc6923ed084b0db99e0e472917",
                   "backup_sql_commit": "1bb7527dda3845fc2cbe4c3d4391042f5cf97aa1", "dump": "MySQL 8.0.41, database infotennis4"},
        "table_rows": raw_counts,
        "rally_rows_without_results_row": orphan_n,
        "point_end_type_values": rally["point_end_type"].value_counts(dropna=False).to_dict(),
        "tournaments": cal[["year", "tournament", "tournament_id", "category", "date_start", "tournament_status"]].astype(str).to_dict(orient="records"),
        "matches": int(len(mt)), "years": mt["year"].value_counts().to_dict(),
        "by_month_level": tab(mt, ["month", "level"]),
        "by_level": tab(mt, ["level"]),
        "tml_linked": int(mt["tml_linked"].sum()),
        "map_linked": int(mt["uid"].notna().sum()),
        "map_linked_by_best": mt["map_best"].value_counts().to_dict(),
        "gap_fill": {
            "atp_points_2025_gap_matches": int(len(gap_all)),
            "gap_matches_with_d_before_2025_05": int(len(gap25)),
            "sirgenkii_matches_in_gap": int(mt["in_gap"].sum()),
            "fills_with_point_rows": int(mt["fills_gap_points"].sum()),
            "fills_with_outcomes": int(mt["fills_gap_outcomes"].sum()),
            "fills_by_level": mt[mt["fills_gap_points"]].groupby("map_level").size().to_dict(),
            "fills_by_month_of_d": mt[mt["fills_gap_points"]].groupby(pd.to_datetime(mt["map_d"]).dt.strftime("%Y-%m")).size().to_dict(),
            "gap_matches_by_month_of_d_to_2025_05": gap25.groupby(gap25["d"].dt.strftime("%Y-%m")).size().to_dict(),
            "fills_also_filled_by_marcosjn2": int((mt["fills_gap_points"] & mt["also_in_marcosjn2"]).sum()),
            "fills_not_in_marcosjn2": int((mt["fills_gap_points"] & ~mt["also_in_marcosjn2"]).sum()),
            "union_with_marcosjn2": int(len(mk_uids | set(mt.loc[mt["fills_gap_points"], "uid"].astype(int)))),
            "marcosjn2_fills_in_same_weeks": int(len(mk_uids & set(gap25["uid"]))),
            "ao2025_gap_matches": int(len(slam_gap)),
            "ao2025_gap_matches_with_sirgenkii_points": int((mt["in_ao2025_gap"] & mt["point_rows"].gt(0)).sum()),
            "ao2025_sirgenkii_matches_linked": int(mt["in_ao2025_gap"].sum()),
        },
        "unlinked_to_map": mt[mt["uid"].isna()][["tournament", "match_id", "player1_name", "player2_name", "point_rows"]].astype(str).to_dict(orient="records"),
    }
    (OUT / "sirgenkii_summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps({k2: v for k2, v in summary.items() if k2 != "tournaments"}, indent=1, default=str))


if __name__ == "__main__":
    main()
