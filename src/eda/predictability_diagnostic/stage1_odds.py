"""Stage 1 of the predictability diagnostic, part 1: closing odds from tennis-data.co.uk, linked to Stage 0.

tennis-data.co.uk publishes tour-level main-draw results with bookmakers' odds, one workbook per tour and
season (ATP 2010-2017 and 2019-2026: there is no ATP 2018 file; WTA 2010-2026; both to 3 August 2026).
Its notes say the odds "generally represent the most recent before play starts" (a provider claim).
Names are "Surname I." only, so rows are linked to Stage 0 matches by the method of
src/eda/merge_feasibility/scan.py: every "surname span + first initial" form of the Stage 0 names, as an
ordered winner > loser pair, same tour, the match day 7 days before to 20 days after the tournament's
Monday. scan.py then takes the nearest tournament week; that is run here as it stands, for the record.

What Stage 1 changes, and why (measured in stage1_odds_summary.json, "scan_py_method"):
    * scan.py's nearest week misreads a pair who met at events a week apart: a Sunday final is one day
      before the next event's Monday and six after its own, so it links to the next week's match.
      Here a candidate with identical set scores comes first, then one whose round agrees, then the
      nearest week (pick()). Equal best candidates leave the row ambiguous, and each Stage 0 match
      takes at most one row (scan.py lets two rows share one match).
    * A candidate needs identical set scores or an agreeing round; the nearest week alone is not enough.
    * Two passes of our own follow for the rows left: one identical player on the same side with
      identical set scores (the one-player anchor of scan.py's Tennis My Life pass, which names that
      differ between the sources need: "Zahlavova Strycova B." is Sackmann's "Barbora Strycova"); and
      the same pair with winner and loser exchanged, which scan.py counts but does not link.

Two corrections to tennis-data's rows, each counted in the summary: a row dated outside its file's
season (more than a month before 1 January, or after 31 December) takes the file's year, which re-dates
the ATP 2013 file's China Open and Japan Open (written as October 2012) and one WTA row written as 2029;
and odds of 0 or 1.00 are not quotes and are treated as missing. A pair of quotes whose overround (the
sum of the two implied probabilities, 1/odds) lies outside 1.00-1.20 is not a coherent quote either:
the median pair's is 1.058, and outside that range sit swapped or garbled values (Djokovic v Ruud,
Rome 2020: average odds 5.05 and 17.00 where Pinnacle had 1.19 and 5.49). Such a pair gives no
probability. The market-average close (AvgW/AvgL, OddsPortal's average) is normalised to sum to one;
Pinnacle (PSW/PSL) is kept as a check.

Writes, in data/studies/predictability_diagnostic/:
    stage1_odds.parquet            one row per Stage 0 main-draw match at the levels tennis-data covers
                                   (keyed by match_id): the link, the tennis-data row, odds for A and B,
                                   and the normalised market probability that A wins; unlinked matches
                                   are kept with the odds missing
    stage1_odds_unlinked.parquet   every tennis-data row of 2010 on that no Stage 0 match took, with why
    stage1_odds_summary.json       link counts by pass, tour and season; scan.py's method on the same rows;
                                   coverage of evaluation matches; quotes, overrounds and Pinnacle's end

Run: ./python.sh src/eda/predictability_diagnostic/stage1_odds.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.merge_feasibility import scan as S  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

TD = C.DUMP / "odds" / "tennis_data_couk"
ODDS = C.OUT / "stage1_odds.parquet"
UNLINKED = C.OUT / "stage1_odds_unlinked.parquet"
SUMMARY = C.OUT / "stage1_odds_summary.json"
LINK_LEVELS = ("GS", "FIN", "T1000", "T500", "T250", "TEAM")   # scan.py's slam, tour and team tiers, main draw
WINDOW = (-7, 20)                                             # scan.py's window for tennis-data, in days
BOOKS = {"avg": ("AvgW", "AvgL"), "ps": ("PSW", "PSL"), "max": ("MaxW", "MaxL"), "b365": ("B365W", "B365L")}
TD_ROUNDS = {"1st Round": 1, "2nd Round": 2, "3rd Round": 3, "4th Round": 4, "Quarterfinals": "QF",
             "Semifinals": "SF", "The Final": "F", "Round Robin": "RR", "Third Place": "BR"}
OVERROUND_OK = (1.0, 1.2)                                     # a coherent pair of quotes
EARLY_ROUNDS = ("R128", "R64", "R32", "R16")                  # the numbered rounds, in playing order
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.1f}s] {msg}", flush=True)


# ------------------------------------------------------------------------------------------------
# The two sides

def load_td() -> pd.DataFrame:
    """Every tennis-data row of the 2010-on files, with its provenance, names keyed as scan.py keys them,
    set scores, and the odds as numbers (0 and 1.00, which are not quotes, as missing)."""
    sets = [f"{s}{k}" for k in range(1, 6) for s in "WL"]
    books = [c for pair in BOOKS.values() for c in pair]
    need = ["Date", "Tournament", "Series", "Tier", "Round", "Surface", "Best of", "Winner", "Loser", "Comment",
            "WRank", "LRank"]
    frames = []
    for f in sorted(TD.glob("*/*/*.parquet")):
        season = int(f.stem)
        if season < C.FIRST_YEAR:
            continue
        df = pd.read_parquet(f).reindex(columns=need + books + sets)   # the WTA files have no 4th or 5th set
        frames.append(pd.DataFrame({
            "td_file": f.relative_to(ROOT).as_posix(), "td_row": np.arange(len(df)), "tour": f.parts[-3],
            "td_season": season, "td_date_text": df["Date"], "td_tournament": df["Tournament"],
            "td_series": df["Series"].fillna(df["Tier"]), "td_round": df["Round"], "td_surface": df["Surface"],
            "td_best_of": df["Best of"], "td_winner": df["Winner"], "td_loser": df["Loser"],
            "td_comment": df["Comment"], "td_wrank": pd.to_numeric(df["WRank"], errors="coerce"),
            "td_lrank": pd.to_numeric(df["LRank"], errors="coerce"), **{c: df[c] for c in books + sets}}))
    td = pd.concat(frames, ignore_index=True)
    td["td_date"] = pd.to_datetime(td["td_date_text"], errors="coerce")
    td["td_date_as_published"] = td["td_date"]
    td["td_redated"] = outside_season(td["td_date"], td["td_season"])
    td.loc[td["td_redated"], "td_date"] = [d.replace(year=int(y)) for d, y in
                                           zip(td.loc[td["td_redated"], "td_date"], td.loc[td["td_redated"], "td_season"])]
    for pair in BOOKS.values():
        for c in pair:
            v = pd.to_numeric(td[c], errors="coerce")
            td[c] = v.where(v > 1.0)
    td["wk"], td["lk"] = td["td_winner"].map(S.td_key), td["td_loser"].map(S.td_key)
    td["pair"] = (td["wk"] + ">" + td["lk"]).where((td["wk"] != "") & (td["lk"] != ""), "")
    td["sets"] = td_sets(td)
    td["td_round_key"] = td["td_round"].map(TD_ROUNDS)
    return td


def outside_season(date: pd.Series, season: pd.Series) -> pd.Series:
    """A date more than a month before its file's season starts, or after it ends. Events of the first
    week can start in late December, so dates from 1 December of the year before are the season's."""
    start = pd.to_datetime(season.astype(str) + "-01-01") - pd.Timedelta(days=31)
    end = pd.to_datetime(season.astype(str) + "-12-31")
    return (date < start) | (date > end)


def coherent(odds_a: pd.Series, odds_b: pd.Series) -> pd.Series:
    """Both quotes present and their overround inside OVERROUND_OK."""
    s = 1.0 / odds_a + 1.0 / odds_b
    return s.between(*OVERROUND_OK) & odds_a.notna() & odds_b.notna()


def td_sets(td: pd.DataFrame) -> list:
    """Each row's set scores, (winner's games, loser's games) per set, up to the first blank set."""
    arr = np.stack([pd.to_numeric(td[f"{s}{k}"], errors="coerce").to_numpy(dtype="float64")
                    for k in range(1, 6) for s in "WL"], axis=1)
    out = []
    for row in arr:
        sets = []
        for k in range(5):
            w, l = row[2 * k], row[2 * k + 1]
            if np.isnan(w) or np.isnan(l):
                break
            sets.append((int(w), int(l)))
        out.append(tuple(sets))
    return out


def stage0_side() -> pd.DataFrame:
    """Stage 0's main-draw matches at the levels tennis-data could hold (scan.py's slam, tour and team
    tiers), every status, with the two names, the set scores and each early round's number."""
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "evaluation", "round", "round_order",
                        "tournament_id", "tournament_name", "tournament_date", "status", "score",
                        "player_a_id", "player_b_id", "a_won"])
    m = m[m["level"].isin(LINK_LEVELS) & ~m["qualifying"]].copy()
    mp = pd.read_parquet(C.MATCH_PLAYERS, columns=["match_id", "side", "won", "player_name", "rank"])
    mp = mp[mp["match_id"].isin(m["match_id"])]
    m["winner_name"] = m["match_id"].map(mp[mp["won"]].set_index("match_id")["player_name"])
    m["loser_name"] = m["match_id"].map(mp[~mp["won"]].set_index("match_id")["player_name"])
    m["rank_a"] = m["match_id"].map(mp[mp["side"].eq("A")].set_index("match_id")["rank"])
    m["rank_b"] = m["match_id"].map(mp[mp["side"].eq("B")].set_index("match_id")["rank"])
    m["sets"] = m["score"].map(lambda s: tuple((a, b) for a, b, br in B.set_scores(s) if not br))
    # each event's early rounds, numbered from its first ("1st Round" of a 32 draw is R32, of a 128 draw R128)
    ev = m[m["round"].isin(EARLY_ROUNDS)].groupby(["tour", "tournament_date", "tournament_id"])["round_order"]
    first = ev.transform("min")
    m["round_no"] = pd.Series(np.nan, index=m.index)
    m.loc[first.index, "round_no"] = (m.loc[first.index, "round_order"] - first + 1).astype("float64")
    return m.reset_index(drop=True)


# ------------------------------------------------------------------------------------------------
# Candidates and choice

def variants(m: pd.DataFrame) -> pd.DataFrame:
    """scan.py's left side: every 'surname span + first initial' form of each Stage 0 winner and loser."""
    ex = pd.DataFrame({"idx": m.index, "tour": m["tour"], "tdate": m["tournament_date"],
                       "wv": m["winner_name"].map(S.td_variants), "lv": m["loser_name"].map(S.td_variants)})
    return ex.explode("wv").explode("lv").set_index("idx")


def pair_candidates(ex: pd.DataFrame, td: pd.DataFrame, swapped: bool = False) -> pd.DataFrame:
    """Candidate (ri, li, gap): the ordered name pair as scan.py builds it (td winner > td loser, or the
    other way round when ``swapped``), same tour, inside scan.py's window."""
    left = ex.assign(pair=ex["wv"] + ">" + ex["lv"])[["tour", "tdate", "pair"]]
    right = td[td["pair"] != ""]
    if swapped:
        right = right.assign(pair=right["lk"] + ">" + right["wk"])
    c = S.link(left, right.rename(columns={"td_date": "date"}), ["tour", "pair"])
    return c[(c["gap"] >= WINDOW[0]) & (c["gap"] <= WINDOW[1])].drop_duplicates(["ri", "li"])


def anchor_candidates(ex: pd.DataFrame, td: pd.DataFrame) -> pd.DataFrame:
    """One identical player on the same side (td winner a form of the Stage 0 winner, or td loser a form
    of the Stage 0 loser), same tour, inside the window."""
    out = []
    for side, key in (("wv", "wk"), ("lv", "lk")):
        left = ex[["tour", "tdate", side]].rename(columns={side: "k"})
        left = left.reset_index().drop_duplicates().set_index("idx")    # one row per match and name form
        right = td[td[key] != ""][["tour", "td_date", key]].rename(columns={key: "k", "td_date": "date"})
        out.append(S.link(left, right, ["tour", "k"]))
    c = pd.concat(out, ignore_index=True)
    return c[(c["gap"] >= WINDOW[0]) & (c["gap"] <= WINDOW[1])].drop_duplicates(["ri", "li"])


def round_agrees(td_key, s0_round: str, s0_no) -> int:
    """2 when the rounds agree, 0 when they do not, 1 when tennis-data gives no round we can read."""
    if td_key is None or (isinstance(td_key, float) and np.isnan(td_key)):
        return 1
    if isinstance(td_key, (int, np.integer)):
        return 2 if (s0_round in EARLY_ROUNDS and s0_no == td_key) else 0
    return 2 if td_key == s0_round else 0


def score(c: pd.DataFrame, td: pd.DataFrame, m: pd.DataFrame, swapped: bool = False) -> pd.DataFrame:
    """Add to candidates: identical set scores (sc), round agreement (rd), distance in days (dist)."""
    c = c.copy()
    ts, ss = td.loc[c["ri"], "sets"].to_numpy(), m.loc[c["li"], "sets"].to_numpy()
    if swapped:
        ts = np.array([tuple((b, a) for a, b in s) for s in ts], dtype=object)
    c["sc"] = np.array([len(a) > 0 and a == b for a, b in zip(ts, ss)])
    c["rd"] = [round_agrees(k, r, n) for k, r, n in zip(td.loc[c["ri"], "td_round_key"].to_numpy(),
                                                          m.loc[c["li"], "round"].to_numpy(),
                                                          m.loc[c["li"], "round_no"].to_numpy())]
    c["dist"] = c["gap"].abs()
    return c


def pick(c: pd.DataFrame) -> tuple[pd.DataFrame, pd.Index, pd.Index]:
    """One Stage 0 match per tennis-data row and one row per match, as Stage 0's pick() does for TML.

    Candidates rank by identical set scores, then round agreement, then the nearest date. Equal best
    candidates leave the row ambiguous. When two rows claim one match, the better-ranked keeps it and the
    other stays unlinked. Returns the kept links, the ambiguous rows and the rows that lost a match."""
    cols = ["ri", "li", "gap", "sc", "rd", "dist"]
    if c.empty:
        return pd.DataFrame(columns=cols), pd.Index([]), pd.Index([])
    key = ["sc", "rd", "dist"]
    c = c.sort_values(["ri"] + key + ["li"], ascending=[True, False, False, True, True])
    top = c.drop_duplicates("ri")
    ties = c.merge(top[["ri"] + key], on=["ri"] + key).groupby("ri")["li"].nunique()
    ambiguous = ties.index[ties > 1]
    top = top[~top["ri"].isin(ambiguous)].sort_values(["li"] + key + ["ri"], ascending=[True, False, False, True, True])
    kept = top.drop_duplicates("li")
    lost = pd.Index(top.loc[~top.index.isin(kept.index), "ri"])
    return kept[cols], ambiguous, lost


# ------------------------------------------------------------------------------------------------
# Linking

def scan_py_method(td: pd.DataFrame, ex: pd.DataFrame, m: pd.DataFrame) -> dict:
    """scan.py's measure_tennis_data() on the same rows, as it stands: dates as published, nearest week,
    ties ambiguous."""
    right = td[td["pair"] != ""].drop(columns="td_date").rename(columns={"td_date_as_published": "date"})
    left = ex.assign(pair=ex["wv"] + ">" + ex["lv"])[["tour", "tdate", "pair"]]
    n, unique = S.resolve(S.link(left, right, ["tour", "pair"]), window=WINDOW)
    status = S.statuses(right.index, n)
    shared = unique[unique.duplicated("li", keep=False)]
    sc = score(unique, td, m)
    return {"rows": int(len(td)), "rows_with_two_names": int(len(right)),
            "linked": int((status == "linked").sum()), "ambiguous": int((status == "ambiguous").sum()),
            "unlinked": int((status == "unlinked").sum()),
            "linked_pct_of_all_rows": round(100 * float((status == "linked").sum()) / len(td), 2),
            "matches_taken_by_two_rows": int(shared["li"].nunique()), "rows_sharing_a_match": int(len(shared)),
            "links_with_identical_set_scores": int(sc["sc"].sum()),
            "links_with_neither_scores_nor_round_agreeing": int((~sc["sc"] & (sc["rd"] != 2)).sum()),
            "_links": unique}


def link_all(td: pd.DataFrame, m: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, dict]:
    """Three passes; returns the links (ri, li, gap, sc, rd, pass), a reason per unlinked td row, counts."""
    ex = variants(m)
    reason = pd.Series("no name pair in the window", index=td.index, dtype=object)
    reason[td["td_date"].isna()] = "no date"
    reason[td["pair"] == ""] = "a name missing"
    counts = {}

    c1 = score(pair_candidates(ex, td), td, m)
    ok = c1["sc"] | (c1["rd"] == 2)
    unverified = pd.Index(c1.loc[~ok, "ri"].unique()).difference(c1.loc[ok, "ri"])
    reason[unverified] = "name pair in the window, but neither set scores nor round agree"
    k1, amb1, lost1 = pick(c1[ok])
    reason[amb1] = "ambiguous: two equally good matches"
    reason[lost1] = "its match was taken by a better-ranked row"
    links = [k1.assign(link="name_pair")]
    counts["name_pair"] = {"candidates": int(len(c1)), "rows_with_a_candidate": int(c1["ri"].nunique()),
                           "linked": int(len(k1)), "ambiguous": int(len(amb1)), "lost_to_another_row": int(len(lost1)),
                           "unverified_rows": int(len(unverified)),
                           "linked_with_identical_set_scores": int(k1["sc"].sum()),
                           "linked_by_round_alone": int((~k1["sc"]).sum())}

    taken_r, taken_l = set(k1["ri"]), set(k1["li"])
    open_r = td.index[~td.index.isin(list(taken_r)) & ~td.index.isin(amb1)]
    c2 = anchor_candidates(ex, td.loc[open_r])
    c2 = c2[~c2["li"].isin(list(taken_l))]
    c2 = score(c2, td, m)
    c2 = c2[c2["sc"] & (c2["rd"] >= 1)]
    one = c2.groupby("ri")["li"].transform("nunique").eq(1) & c2.groupby("li")["ri"].transform("nunique").eq(1)
    k2 = c2[one]
    reason[k2["ri"]] = "linked"
    links.append(k2.assign(link="one_player_anchor"))
    counts["one_player_anchor"] = {"candidates_with_identical_scores": int(len(c2)), "linked": int(len(k2)),
                                   "not_unique": int(c2.loc[~one, "ri"].nunique())}

    taken_r |= set(k2["ri"])
    taken_l |= set(k2["li"])
    open_r = td.index[~td.index.isin(list(taken_r)) & ~td.index.isin(amb1)]
    c3 = score(pair_candidates(ex, td.loc[open_r], swapped=True), td, m, swapped=True)
    c3 = c3[~c3["li"].isin(list(taken_l)) & (c3["sc"] | (c3["rd"] == 2))]
    k3, amb3, lost3 = pick(c3)
    links.append(k3.assign(link="winner_swapped"))
    counts["winner_swapped"] = {"linked": int(len(k3)), "ambiguous": int(len(amb3)),
                                "with_identical_set_scores_read_the_other_way": int(k3["sc"].sum())}

    out = pd.concat(links, ignore_index=True)
    reason[out["ri"]] = "linked"
    return out, reason, counts


# ------------------------------------------------------------------------------------------------
# Tables

CAPTURE_WEEKS_FROM = pd.Timestamp("2026-07-27")   # events from this week on are missing or partial in the capture


def ranks_agree(a: pd.Series, b: pd.Series) -> pd.Series:
    """Two sources' rankings of one player agree: within 3 places or 10%, where both are known."""
    both = a.notna() & b.notna()
    return ((a - b).abs() <= np.maximum(3.0, 0.1 * b)).where(both).astype("boolean")


def odds_table(m: pd.DataFrame, td: pd.DataFrame, links: pd.DataFrame) -> pd.DataFrame:
    """One row per Stage 0 candidate match: its link, the tennis-data row, and the odds of A and B."""
    l = links.set_index("li")
    o = m[["match_id", "tour", "year", "level", "round", "tournament_date", "evaluation", "status", "a_won"]].copy()
    o["link"] = l["link"].reindex(o.index).fillna("none")
    ri = l["ri"].reindex(o.index)
    has = ri.notna().to_numpy()
    pos = np.flatnonzero(has)
    r = td.loc[ri[has].astype("int64")]
    for c in ("td_file", "td_tournament", "td_round", "td_comment", "td_winner", "td_loser"):
        v = np.full(len(o), None, dtype=object)
        v[pos] = r[c].to_numpy(dtype=object)
        o[c] = pd.array(v, dtype="string")
    row = np.full(len(o), -1, dtype="int64")
    row[pos] = r["td_row"].to_numpy(dtype="int64")
    o["td_row"] = pd.array(row, dtype="Int64")
    o.loc[~has, "td_row"] = pd.NA
    d = np.full(len(o), np.datetime64("NaT"), dtype="datetime64[ns]")
    d[pos] = r["td_date"].to_numpy(dtype="datetime64[ns]")
    o["td_date"] = d
    red = np.zeros(len(o), dtype=bool)
    red[pos] = r["td_redated"].to_numpy(dtype=bool)
    o["td_redated"] = red
    o["days_from_monday"] = l["gap"].reindex(o.index).astype("float64")
    o["same_set_scores"] = l["sc"].reindex(o.index).astype("boolean")
    o["round_agrees"] = l["rd"].reindex(o.index).map({2: "yes", 0: "no", 1: "unknown"})
    # tennis-data's winner is Stage 0's winner, except in the swapped pass
    a_won = o["a_won"].to_numpy(dtype=bool)
    a_is_td_winner = np.where(o["link"].eq("winner_swapped").to_numpy(), ~a_won, a_won)

    def per_side(wc, lc):
        w, lo = np.full(len(o), np.nan), np.full(len(o), np.nan)
        w[pos], lo[pos] = r[wc].to_numpy(dtype="float64"), r[lc].to_numpy(dtype="float64")
        return np.where(a_is_td_winner, w, lo), np.where(a_is_td_winner, lo, w)

    ta, tb = per_side("td_wrank", "td_lrank")
    o["rank_agrees_a"] = ranks_agree(pd.Series(ta, index=o.index), m["rank_a"])
    o["rank_agrees_b"] = ranks_agree(pd.Series(tb, index=o.index), m["rank_b"])
    for book, (wc, lc) in BOOKS.items():
        o[f"{book}_a"], o[f"{book}_b"] = per_side(wc, lc)
    for book in ("avg", "ps"):
        a, b = o[f"{book}_a"], o[f"{book}_b"]
        o[f"overround_{book}"] = 1.0 / a + 1.0 / b
        o[f"{book}_coherent"] = coherent(a, b)
        o[f"p_{book}_a"] = ((1.0 / a) / (1.0 / a + 1.0 / b)).where(o[f"{book}_coherent"])   # normalised to sum to one
    return o.drop(columns=["a_won"])


def records(frame: pd.DataFrame) -> list:
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def raw_not_quotes() -> dict:
    """How many published odds values are 0 or 1.00 (or below), which are not quotes, per column."""
    out = {}
    for f in sorted(TD.glob("*/*/*.parquet")):
        if int(f.stem) < C.FIRST_YEAR:
            continue
        df = pd.read_parquet(f)
        for pair in BOOKS.values():
            for c in pair:
                if c in df.columns:
                    v = pd.to_numeric(df[c], errors="coerce")
                    out[c] = out.get(c, 0) + int((v <= 1.0).sum())
    return out


def summary_of(o: pd.DataFrame, td: pd.DataFrame, reason: pd.Series, counts: dict, scan: dict) -> dict:
    lk = o[o["link"].ne("none")]
    s = {"generated_at": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds"),
         "window_days": list(WINDOW), "link_levels": list(LINK_LEVELS), "overround_ok": list(OVERROUND_OK),
         "td_rows_2010_on": int(len(td)), "td_rows_by_tour": td.groupby("tour").size().to_dict(),
         "td_seasons_by_tour": {t: sorted(int(x) for x in g.unique()) for t, g in td.groupby("tour")["td_season"]},
         "td_last_date_by_tour": td.groupby("tour")["td_date"].max().dt.strftime("%Y-%m-%d").to_dict(),
         "td_redated": records(td[td["td_redated"]].groupby(["tour", "td_season", "td_tournament"])
                               .agg(rows=("td_row", "size"), published_first=("td_date_as_published", "min"),
                                    published_last=("td_date_as_published", "max")).reset_index()),
         "scan_py_method": {k: v for k, v in scan.items() if not k.startswith("_")},
         "passes": counts,
         "td_rows_by_outcome": reason.value_counts().to_dict(),
         "td_rows_linked": int((reason == "linked").sum()),
         "td_rows_linked_pct": round(100 * float((reason == "linked").mean()), 2),
         "stage0_candidate_matches": int(len(o)),
         "stage0_candidates_by_level_and_link": records(pd.crosstab([o["tour"], o["level"]], o["link"]).reset_index()),
         "linked_by_tour_season": records(pd.crosstab([td["tour"], td["td_season"]], reason.eq("linked"))
                                          .rename(columns={True: "linked", False: "not_linked"}).reset_index())}
    both_known = lk["rank_agrees_a"].notna() & lk["rank_agrees_b"].notna()
    both_agree = lk["rank_agrees_a"].fillna(False) & lk["rank_agrees_b"].fillna(False)
    ver = lk.assign(sc=lk["same_set_scores"].fillna(False).astype(bool), rd=lk["round_agrees"].eq("yes"),
                    rk=both_known, ra=both_agree)
    ver = ver.groupby("link").agg(links=("match_id", "size"), same_set_scores=("sc", "sum"), round_agrees=("rd", "sum"),
                                  both_ranks_known=("rk", "sum"), both_ranks_agree=("ra", "sum"))
    s["verification_by_pass"] = records(ver.reset_index())
    s["values_not_quotes"] = raw_not_quotes()
    q = {}
    for book in ("avg", "ps"):
        both = lk[f"{book}_a"].notna() & lk[f"{book}_b"].notna()
        orr = lk.loc[both, f"overround_{book}"]
        q[book] = {"linked_rows_with_both_quotes": int(both.sum()), "coherent": int(lk[f"{book}_coherent"].sum()),
                   "overround_below_1": int((orr < OVERROUND_OK[0]).sum()),
                   "overround_above_1_2": int((orr > OVERROUND_OK[1]).sum()),
                   "overround_quantiles": {str(k): round(float(v), 4)
                                           for k, v in orr.quantile([0, .001, .01, .5, .99, .999, 1]).items()}}
    s["quotes"] = q
    # coverage of evaluation matches: odds exist only for tour-level main draws
    ev = o[o["evaluation"]].copy()
    ev["with_odds"] = ev["p_avg_a"].notna()
    cov = ev.groupby(["tour", "level", "year"]).agg(matches=("with_odds", "size"), with_odds=("with_odds", "sum")).reset_index()
    cov["pct"] = (100 * cov["with_odds"] / cov["matches"]).round(1)
    s["evaluation_coverage_by_tour_level_year"] = records(cov)
    tl = ev[ev["level"].isin(("GS", "FIN", "T1000", "T500", "T250"))]
    inside = tl[~((tl["tour"] == "atp") & (tl["year"] == 2018)) & (tl["tournament_date"] < CAPTURE_WEEKS_FROM)]

    def share(g):
        return {"matches": int(len(g)), "with_odds": int(g["with_odds"].sum()), "pct": round(100 * float(g["with_odds"].mean()), 1)}

    s["capture_weeks_from"] = CAPTURE_WEEKS_FROM.strftime("%Y-%m-%d")
    s["evaluation_tour_level_with_market"] = {t: share(g) for t, g in tl.groupby("tour")}
    s["evaluation_tour_level_with_market_inside_coverage"] = {t: share(g) for t, g in inside.groupby("tour")}
    s["evaluation_tour_level_after_capture"] = {t: int(len(g)) for t, g in
                                                tl[tl["tournament_date"] >= CAPTURE_WEEKS_FROM].groupby("tour")}
    s["evaluation_atp_2018_tour_level"] = int(((tl["tour"] == "atp") & (tl["year"] == 2018)).sum())
    names = pd.read_parquet(C.MATCHES, columns=["match_id", "tournament_id", "tournament_name"])
    e = inside.merge(names, on="match_id").groupby(["tour", "level", "year", "tournament_id", "tournament_name"]).agg(
        matches=("with_odds", "size"), with_odds=("with_odds", "sum")).reset_index()
    s["evaluation_events_without_any_odds"] = records(e[e["with_odds"] == 0].drop(columns="with_odds"))
    part = e[(e["with_odds"] > 0) & (e["with_odds"] < e["matches"])]
    s["evaluation_matches_without_odds_in_events_with_odds"] = int((part["matches"] - part["with_odds"]).sum())
    # Pinnacle, and its last months
    lkm = lk.assign(month=lk["td_date"].dt.strftime("%Y-%m"))
    by = lkm[lkm["month"] >= "2025-01"].groupby(["tour", "month"]).agg(
        linked=("match_id", "size"), with_pinnacle=("p_ps_a", lambda x: int(x.notna().sum())))
    s["pinnacle"] = {"linked_with_avg": int(lk["p_avg_a"].notna().sum()), "linked_with_ps": int(lk["p_ps_a"].notna().sum()),
                     "linked_with_both": int((lk["p_avg_a"].notna() & lk["p_ps_a"].notna()).sum()),
                     "last_month_by_tour": lkm[lkm["p_ps_a"].notna()].groupby("tour")["month"].max().to_dict(),
                     "by_month_2025_on": records(by.reset_index())}
    return s


def main() -> int:
    td = load_td()
    log(f"tennis-data rows 2010 on: {len(td):,} ({int(td['td_redated'].sum())} re-dated to their file's season)")
    m = stage0_side()
    log(f"Stage 0 main-draw matches at the linked levels: {len(m):,}")
    scan = scan_py_method(td, variants(m), m)
    log(f"scan.py's method: {scan['linked']:,} linked ({scan['linked_pct_of_all_rows']}%), "
        f"{scan['matches_taken_by_two_rows']} matches taken by two rows")
    links, reason, counts = link_all(td, m)
    log(f"linked: {len(links):,} ({100 * len(links) / len(td):.2f}%)")
    o = odds_table(m, td, links)
    un = td.loc[reason.ne("linked"), ["td_file", "td_row", "tour", "td_season", "td_date", "td_redated", "td_tournament",
                                      "td_series", "td_round", "td_winner", "td_loser", "td_comment", "AvgW", "AvgL",
                                      "PSW", "PSL"]]
    un = un.assign(reason=reason[un.index].astype(str))
    summary = summary_of(o, td, reason, counts, scan)
    o.to_parquet(ODDS, index=False)
    un.to_parquet(UNLINKED, index=False)
    SUMMARY.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log(f"wrote {ODDS.name} ({len(o):,} rows), {UNLINKED.name} ({len(un):,} rows), {SUMMARY.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


