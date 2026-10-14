"""F2 review (A2-skeptic): look for every one of the 88 matches in every held independent source.

Sources searched by both players' surnames and the season: WTA API (matches/<year>), SofaScore (three collections),
TDI, tennislive, sirgenkii's ATP results, the Wimbledon and US Open feeds, Infosys (AO 2025), the AO feed, and the
Match Charting Project. Prints the hits; f2_verdicts.py reads the counts from the ones that hold statistics.
Run: ./python.sh src/eda/input_data_audit/review/A2-skeptic/f2_search_sources.py
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

import _common as K


def toks(s) -> set:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return {t for t in re.findall(r"[a-z]+", s) if len(t) >= 3}


def surname(s) -> str:
    t = re.findall(r"[a-z]+", unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower())
    return t[-1] if t else ""


def token_cols(frame: pd.DataFrame, cols: list[str]) -> list[set]:
    vals = [[("" if pd.isna(v) else str(v)) for v in frame[c].tolist()] for c in cols]
    return [toks(" ".join(parts)) for parts in zip(*vals)]


def search(frame: pd.DataFrame, ta: list[set], tb: list[set], s1: str, s2: str) -> pd.DataFrame:
    hit = [(s1 in a and s2 in b) or (s2 in a and s1 in b) for a, b in zip(ta, tb)]
    return frame[hit]


def main() -> None:
    x = pd.read_csv(K.OUT / "f2_detail.csv", parse_dates=["tournament_date"])
    pd.set_option("display.width", 300)
    pd.set_option("display.max_columns", 30)
    pd.set_option("display.max_colwidth", 70)
    src = {}
    for c in ("sofascore", "sofascore_editions", "sofascore_tournaments"):
        e = pd.read_parquet(K.ROOT / "data/dump/points" / c / "events.parquet",
                            columns=["event_id", "start_utc", "tournament_name", "home_name", "away_name", "winner_code",
                                     "stats_status", "doubles"])
        src[c] = (e, ["home_name"], ["away_name"])
    t = pd.read_parquet(K.ROOT / "data/dump/points/tdi/matches.parquet",
                        columns=["match_id", "tournament", "completed_on", "draw_type", "team_a_names", "team_b_names",
                                 "team_a_scores", "team_b_scores", "stats_rows"])
    src["tdi"] = (t, ["team_a_names"], ["team_b_names"])
    tl = pd.read_parquet(K.ROOT / "data/dump/points/tennislive/matches.parquet",
                         columns=["url", "tournament_name", "player1_name", "player2_name", "score", "winner_id",
                                  "player1_id", "stats_available", "stats_rows", "reference_utc"])
    src["tennislive"] = (tl, ["player1_name"], ["player2_name"])
    sg = pd.read_parquet(K.ROOT / "data/dump/points/sirgenkii_infotennis/atp_results.parquet")
    src["sirgenkii"] = (sg, ["player1_name"], ["player2_name"])
    for site in ("wimbledon", "usopen"):
        m = pd.read_parquet(K.ROOT / "data/dump/points" / site / "matches.parquet")
        a = [c for c in m.columns if c.startswith("entry.team1.") and ("lastName" in c or "displayName" in c)]
        b = [c for c in m.columns if c.startswith("entry.team2.") and ("lastName" in c or "displayName" in c)]
        src[site] = (m[["year", "event", "match_id", "entry.winner", "stats_outcome"] + a + b], a, b)
    ao = pd.read_parquet(K.ROOT / "data/dump/points/ausopen/matches.parquet",
                         columns=["year", "event_name", "match_id", "round_name", "winner_team", "team1_names",
                                  "team2_names", "stats_rows"])
    src["ausopen"] = (ao, ["team1_names"], ["team2_names"])
    inf = pd.read_parquet(K.INFOSYS / "matches.parquet",
                          columns=["slam", "year", "match_id", "draw", "round_from_code", "match_winner", "p1_name",
                                   "p2_name", "keystats_sets", "points"])
    src["infosys"] = (inf, ["p1_name"], ["p2_name"])
    wm = []
    for y in range(2019, 2027):
        wm.append(K._dedup(K.WTA / "matches" / f"{y}.parquet")[["tournament_id", "year", "match_id", "DrawMatchType",
                                                                  "ResultString", "Winner", "PlayerNameFirstA",
                                                                  "PlayerNameLastA", "PlayerNameFirstB",
                                                                  "PlayerNameLastB", "stats_status"]])
    wm = pd.concat(wm, ignore_index=True)
    src["wta_api"] = (wm[wm["DrawMatchType"].eq("S")], ["PlayerNameFirstA", "PlayerNameLastA"],
                      ["PlayerNameFirstB", "PlayerNameLastB"])
    mc = pd.concat([K.mcp("m"), K.mcp("w")])
    mc = mc.drop_duplicates("match_id")[["match_id", "Player 1", "Player 2", "date", "Tournament", "Round"]]
    src["mcp"] = (mc, ["Player 1"], ["Player 2"])

    rows = []
    pre = {name: (frame.reset_index(drop=True), token_cols(frame, ca), token_cols(frame, cb))
           for name, (frame, ca, cb) in src.items()}
    for r in x.itertuples():
        s1, s2 = surname(r.winner_name), surname(r.loser_name)
        for name, (frame, ta, tb) in pre.items():
            h = search(frame, ta, tb, s1, s2)
            if h.empty:
                continue
            for _, hh in h.iterrows():
                txt = " | ".join(f"{k}={v}" for k, v in hh.items() if pd.notna(v) and str(v) != "")
                if str(r.year) not in txt and name not in ("mcp",):
                    # keep same-season hits only (dates/years are in the text for every source)
                    if not re.search(str(r.year), txt):
                        continue
                rows.append({"match_id": r.match_id, "source": name, "hit": txt[:400]})
    out = pd.DataFrame(rows)
    out.to_csv(K.OUT / "f2_source_hits.csv", index=False)
    cl = x["match_id"].str.contains(r"2021-2028|2021-2027")
    for mid in x.loc[~cl, "match_id"]:
        h = out[out["match_id"].eq(mid)] if len(out) else out
        print("==", mid, "|", x.loc[x["match_id"].eq(mid), "winner_name"].iloc[0], "d.",
              x.loc[x["match_id"].eq(mid), "loser_name"].iloc[0], x.loc[x["match_id"].eq(mid), "score"].iloc[0])
        for _, hh in h.iterrows():
            print("   ", hh["source"], ":", hh["hit"][:260])


if __name__ == "__main__":
    main()
