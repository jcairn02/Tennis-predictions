"""The WTA website records' mislabelled tournaments (P6 data issues, 14 Oct 2026): read-only investigation.

The WTA website's match records (Kaggle bwandowando/womens-tennis-association-matches-1975-present, version 29 of
24 Sep 2026, data/raw/gap_sources/bwandowando/) join each match to its edition by `pseudo_tournament_id`. The data map
showed 55 matches of September 2026 under six WTA 125 titles whose fields SofaScore did not list. This script:

  1. lists every singles match the copy files under its last ten editions (those starting 7-14 Sep 2026), and finds
     each one's real event in independent data on disk:
        api        the WTA API's player-matches results (work package P2(b), fetched 11-14 Oct 2026), which carry the
                   tournament number on every row: joined on the copy's own row fields (listing player, both names,
                   draw, round, score, round index, winner)
        tl         TennisLive's event listings (P4): same pair of players (surname keys, loosely), any event 28 Aug -
                   27 Sep 2026; the score compared
        wta_list   the WTA API's live-scoring match lists of the WTA 125 and tour events (data/raw/point_sources/wta/
                   tournaments/<group>_<year>/matches.json): same pair of WTA ids
        itf_live   the ITF live-data API (events from 13 Sep 2026 on: only rematches can show here)
     and joins the data map's rows (data/studies/data_map/matches.parquet), the accepted lower-level feed snapshot
     (accepted.json "feeds") and the repository's Stage 0 to those matches;
  2. measures how widespread the problem is over the whole file 2018-2026: every 2026 row against the P2(b) rows;
     every edition with a WTA API list against that list (2019-2026); every match against Sackmann's files (2018 - June
     2026); and the file against itself (one match under two editions).

Nothing outside data/studies/p6_data_issues/wta_site/ is written. No network access. Outputs there:
    map_55_true_events.csv          the 55 map rows under the six WTA 125 titles: real event, level, round, day, scores
    sep2026_matches.csv             every match (187) the ten editions of 7-14 Sep 2026 hold, with all evidence
    sep2026_listings.csv            every listing (raw row, 339) of those editions, right or wrong
    map_copies.csv, feed_copies.csv, stage0_copies.csv   each copy of those matches and its proposed correction
    editions_2026_vs_wta_api.csv    every 2026 edition against the WTA API's player matches
    editions_vs_wta_lists.csv       every edition with a WTA live-scoring list (2019-2026) against it
    edition_purity_tennislive.csv, edition_purity_sackmann.csv   every edition 2018-2026: one real event or several
    sackmann_status_by_year.csv, sackmann_disagreements.csv     match-level comparison with Sackmann's files
    internal_two_editions.csv       one match under two editions, checked against TennisLive and Sackmann
    summary.json
(feed_rows.csv, map_rows_ten_editions.csv, stage0_rows.csv: superseded outputs of a first pass; matched on the pair
only, so they include rematches. Not read by anything.)

Run:  ./python.sh src/eda/p6_data_issues/wta_site_mislabels.py           (about 2 minutes)
      ./python.sh src/eda/p6_data_issues/wta_site_mislabels.py --part1   (the September editions only)
"""
from __future__ import annotations

import difflib
import json
import re
import sys
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.data_map.measure import surname_key  # noqa: E402  (the map's own name key, so the map's rows match)

RAW = ROOT / "data" / "raw"
DUMP = ROOT / "data" / "dump"
KAGGLE = RAW / "gap_sources" / "bwandowando"
P2B_RAW = DUMP / "points" / "wta" / "player_matches" / "2026.parquet"
WTA_LISTS = RAW / "point_sources" / "wta" / "tournaments"
TL_LISTED = DUMP / "points" / "tennislive" / "listed.parquet"
TL_EVENTS = DUMP / "points" / "tennislive" / "events.parquet"
ITF_LIVE = DUMP / "points" / "itf_live" / "matches.parquet"
SOFA = DUMP / "points" / "sofascore_editions" / "events.parquet"
SACKMANN = DUMP / "matches" / "sackmann_archive" / "wta"
MAP = ROOT / "data" / "studies" / "data_map" / "matches.parquet"
ACCEPTED = ROOT / "data" / "studies" / "current_best_model" / "accepted_additions" / "accepted.json"
FEED_DIR = ROOT / "data" / "studies" / "current_best_model" / "accepted_additions"
FEED_CAND = ROOT / "data" / "studies" / "data_gaps_2026" / "feed" / "candidates"
STAGE0 = ROOT / "data" / "studies" / "predictability_diagnostic"
OUT = ROOT / "data" / "studies" / "p6_data_issues" / "wta_site"

SEP_FIRST = "2026-09-07"            # the first of the ten editions the copy scrambles (found by part 2 (a))
SIX_TITLES = ["BBVA Open Internacional de Valencia", "Caldas da Rainha Ladies Open", "Zavarovalnica Triglav Ljubljana",
              "ATIK Antalya Open", "Kia Open - Barranquilla", "Montreux Nestl"]
LEVEL = {"ITF": "ITF", "WTA 125": "CH", "125K": "CH", "WTA 250": "T250", "International": "T250", "WTA 500": "T500",
         "Premier": "T500", "WTA 1000": "T1000", "Premier 5": "T1000", "Premier Mandatory": "T1000",
         "Grand Slam": "GS", "Finals": "FIN"}
QUAL = {"ITF": "ITFQ", "CH": "CHQ", "T250": "TQ", "T500": "TQ", "T1000": "TQ", "GS": "GSQ", "FIN": "TQ"}
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


# --------------------------------------------------------------------------------------------------------------------
# names and scores

def jn(values, sep: str = ";") -> str:
    """The distinct non-missing values, as text, sorted and joined."""
    return sep.join(sorted({str(v) for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))
                            and v is not pd.NA and str(v) != ""}))


def ascii_lower(s) -> str:
    s = "" if s is None or (isinstance(s, float) and np.isnan(s)) else str(s)
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()


def kaggle_name(s) -> str:
    """'SURNAME,  FIRST  CTY' -> 'FIRST SURNAME' (the site's form; the map's wta_site_name)."""
    s = "" if s is None or (isinstance(s, float) and np.isnan(s)) else str(s)
    if "," not in s:
        return s.strip()
    last, rest = s.split(",", 1)
    parts = rest.split()
    if len(parts) > 1 and len(parts[-1]) == 3 and parts[-1].isupper():
        parts = parts[:-1]
    return " ".join(parts + [last.strip()])


@lru_cache(maxsize=None)
def close(a: str, b: str) -> bool:
    """Two surname keys that may name one player: equal, one a 4+-letter prefix of the other, or similar spellings
    ('khamutsianskaya' / 'khomutsianskaya', 'lacinova' / 'lachinova')."""
    if not a or not b:
        return False
    if a == b:
        return True
    if min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.8


def same_pair(a1: str, a2: str, b1: str, b2: str) -> bool:
    return (close(a1, b1) and close(a2, b2)) or (close(a1, b2) and close(a2, b1))


_SET = re.compile(r"(\d+)-(\d+)(?:\((\d+)\))?")


def sets_of(text) -> list[tuple[int, int]]:
    return [(int(a), int(b)) for a, b, _ in _SET.findall(str(text or ""))]


def canon(sets: list[tuple[int, int]]) -> str:
    """Sets turned to the side that won more of them (a retirement with sets level keeps the listed side)."""
    first = sum(a > b for a, b in sets)
    second = sum(b > a for a, b in sets)
    if second > first:
        sets = [(b, a) for a, b in sets]
    return " ".join(f"{a}-{b}" for a, b in sets)


def canon_text(text) -> str:
    return canon(sets_of(text))


def full_canon(text) -> str:
    """The canonical score with each tiebreak's loser points kept ('6-4 6-7(9) 6-4'), oriented like canon()."""
    toks = _SET.findall(str(text or ""))
    sets = [(int(a), int(b), t) for a, b, t in toks]
    if sum(b > a for a, b, _ in sets) > sum(a > b for a, b, _ in sets):
        sets = [(b, a, t) for a, b, t in sets]
    return " ".join(f"{a}-{b}" + (f"({t})" if t else "") for a, b, t in sets)


def tl_canon(p1_sets, p2_sets) -> str:
    """TennisLive's per-set games ('7(7) 3 6' / '6(4) 6 1') -> canonical score."""
    g1 = [int(x) for x in re.findall(r"(\d+)(?:\(\d+\))?", str(p1_sets or ""))]
    g2 = [int(x) for x in re.findall(r"(\d+)(?:\(\d+\))?", str(p2_sets or ""))]
    return canon(list(zip(g1, g2)))


_GENERIC = {"wta", "wtt", "itf", "open", "ladies", "international", "internacional", "tennis", "championships", "cup",
            "presented", "presentado", "por", "by", "the", "de", "di", "da", "del", "la", "le", "of", "tennis",
            "europe", "usta", "trophy", "challenger", "women", "womens", "s", "and", "powered", "grand", "prix",
            "tournament", "classic", "atp", "series", "nestle", "kia", "atik", "bbva", "bnp", "paribas", "copa",
            "w", "k", "usa", "new"}


_TEAM = re.compile(r"united cup|atp cup|laver cup|davis cup|billie jean king|bjk cup|fed cup|olympic|hopman", re.I)


def slam_of(text) -> str | None:
    t = ascii_lower(text)
    for word, code in (("australian", "ao"), ("roland", "rg"), ("garros", "rg"), ("championnats internationaux", "rg"),
                       ("wimbledon", "w"), ("us open", "uso")):
        if word in t:
            return code
    return None


def place_tokens(text) -> set:
    """Words of an event's name that can identify its place: 3+ letters, generic and sponsor words dropped, German
    umlaut spellings folded ('Poertschach' / 'Portschach'), a trailing country code (', TUR') dropped."""
    t = re.sub(r",\s*[A-Z]{3}\s*$", "", "" if text is None or (isinstance(text, float) and np.isnan(text)) else str(text))
    t = ascii_lower(t).replace("ae", "a").replace("oe", "o").replace("ue", "u")
    words = re.split(r"[^a-z]+", t)
    return {w for w in words if len(w) >= 3 and w not in _GENERIC and not re.match(r"^w?\d", w)}


def same_place(a, b) -> bool:
    sa, sb = slam_of(a), slam_of(b)
    if sa or sb:
        return sa == sb
    ta, tb = place_tokens(a), place_tokens(b)
    if not ta or not tb:
        return False
    if ta & tb:
        return True
    return any(x.startswith(y) or y.startswith(x) for x in ta for y in tb if min(len(x), len(y)) >= 5)


# --------------------------------------------------------------------------------------------------------------------
# the Kaggle copy

def load_editions() -> pd.DataFrame:
    t = pd.read_csv(KAGGLE / "tournaments.csv", low_memory=False)
    t["start"] = pd.to_datetime(t["startDate"], errors="coerce")
    t["group"] = pd.to_numeric(t["tournamentGroupId"], errors="coerce").astype("Int64")
    t["map_level"] = t["level"].map(LEVEL)
    return t


def load_kaggle(t: pd.DataFrame, since: str = "2017-12-01") -> pd.DataFrame:
    """Singles rows of editions starting on or after `since`, with their edition's fields and name keys."""
    m = pd.read_csv(KAGGLE / "matches.csv", low_memory=False)
    m = m.merge(t[["pseudo_tournament_id", "year", "title", "startDate", "start", "level", "map_level", "group", "city",
                   "country", "surface"]], on="pseudo_tournament_id", how="left")
    m = m[(m["start"] >= since) & m["player_3"].isna() & m["player_4"].isna()].copy()
    for c in ("player_1", "player_2"):
        m[c] = pd.to_numeric(m[c], errors="coerce").astype("Int64")
    m["n1"], m["n2"] = m["team_name_1"].map(kaggle_name), m["team_name_2"].map(kaggle_name)
    m["k1"], m["k2"] = m["n1"].map(surname_key), m["n2"].map(surname_key)
    m["pair"] = [("|".join(sorted((a, b)))) if a and b and a != b else None for a, b in zip(m["k1"], m["k2"])]
    m["score_c"] = m["scores"].map(canon_text)
    m["played"] = m["reason_code"].isin(["W", "R"])
    return m


def match_key(m: pd.DataFrame) -> pd.Series:
    """One match whichever player's page listed it: pair of surname keys, draw, round, canonical score."""
    return m["pair"].astype(str) + "#" + m["qpm_flag"].astype(str) + "#" + m["round_name"].astype(str) + "#" + \
        m["score_c"].astype(str)


# --------------------------------------------------------------------------------------------------------------------
# independent sources

def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def row_key(df: pd.DataFrame) -> list:
    num = lambda c: pd.to_numeric(df[c], errors="coerce").astype("Int64").astype(str)  # noqa: E731
    return list(zip(num("player_1"), df["team_name_1"].map(_norm), df["team_name_2"].map(_norm), df["qpm_flag"],
                    df["round_name"].astype(str), df["scores"].map(_norm), num("tourn_round"), num("winner")))


def load_p2b() -> pd.DataFrame:
    a = pd.read_parquet(P2B_RAW)
    a = a[a["s_d_flag"].eq("S")].copy()
    a["tourn_nbr"] = a["tourn_nbr"].astype(str).str.strip()
    a["key"] = row_key(a)
    return a


def p2b_truth(k: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    """Each Kaggle row's event in the WTA API's player-matches results (exact row fields)."""
    g = a.groupby("key").agg(api_group=("tourn_nbr", lambda s: jn(s, ";")),
                             api_start=("StartDate", lambda s: jn(s.astype(str).str[:10], ";")),
                             api_title=("tournament_title", "first"), api_level=("tournament_level", "first"),
                             api_round=("round_name", "first"), api_scores=("scores", "first"),
                             api_surface=("Surface", "first"), api_io=("tournament_in_outdoor", "first"))
    k = k.copy()
    k["key"] = row_key(k)
    return k.merge(g, left_on="key", right_index=True, how="left")


def load_wta_lists(years: set | None = None) -> pd.DataFrame:
    rows = []
    for d in sorted(WTA_LISTS.iterdir()):
        if not d.is_dir() or not (d / "matches.json").exists():
            continue
        try:
            group, year = d.name.split("_")
        except ValueError:
            continue
        if years and int(year) not in years:
            continue
        j = json.loads((d / "matches.json").read_text(encoding="utf-8"))
        title = (j.get("tournament") or {}).get("title") if isinstance(j.get("tournament"), dict) else None
        for x in j.get("matches") or []:
            if x.get("DrawMatchType") != "S":
                continue
            rows.append({"list_group": int(group), "list_year": int(year), "list_title": title,
                         "draw": x.get("DrawLevelType"), "round_id": x.get("RoundID"), "match_id": x.get("MatchID"),
                         "ida": str(x.get("PlayerIDA") or ""), "idb": str(x.get("PlayerIDB") or ""),
                         "na": f"{x.get('PlayerNameFirstA') or ''} {x.get('PlayerNameLastA') or ''}".strip(),
                         "nb": f"{x.get('PlayerNameFirstB') or ''} {x.get('PlayerNameLastB') or ''}".strip(),
                         "score": x.get("ScoreString"), "state": x.get("MatchState"),
                         "when": x.get("MatchTimeStamp")})
    w = pd.DataFrame(rows)
    w["id_pair"] = ["|".join(sorted((a, b))) if a and b else None for a, b in zip(w["ida"], w["idb"])]
    w["pair"] = ["|".join(sorted((surname_key(a), surname_key(b)))) for a, b in zip(w["na"], w["nb"])]
    w["score_c"] = w["score"].map(canon_text)
    return w


def load_tl(lo: str, hi: str) -> pd.DataFrame:
    cols = ["event_key", "event_id", "event_name", "event_kind", "tour", "stage", "round", "draw", "discipline",
            "junior", "match_id", "state", "score", "winner_side", "player1_name", "player2_name", "player1_sets",
            "player2_sets", "start_utc"]
    li = pd.read_parquet(TL_LISTED, columns=cols)
    li = li[(li["tour"] == "wta") & (li["discipline"] == "singles") & (li["start_utc"].astype(str) >= lo)
            & (li["start_utc"].astype(str) <= hi)].copy()
    li["tk1"], li["tk2"] = li["player1_name"].map(surname_key), li["player2_name"].map(surname_key)
    li["score_c"] = [tl_canon(a, b) for a, b in zip(li["player1_sets"], li["player2_sets"])]
    ev = pd.read_parquet(TL_EVENTS, columns=["tl_id", "first_week", "kind", "name"])
    li = li.merge(ev.rename(columns={"tl_id": "event_id", "first_week": "tl_week"})[["event_id", "tl_week"]],
                  on="event_id", how="left")
    return li


def itf_games(text) -> list[int]:
    """ITF live's per-set games, '1:6/0 2:7/5' (set:games/tiebreak points) -> [6, 7]."""
    return [int(g) for _, g, _ in re.findall(r"(\d+):(\d+)/(\d+)", str(text or ""))]


def load_itf_live() -> pd.DataFrame:
    x = pd.read_parquet(ITF_LIVE)
    x = x[x["discipline"].astype(str).eq("Women Singles")].copy()
    x = x.sort_values("latest", ascending=False).drop_duplicates(["event_key", "match_id"])
    x["n1"] = x["side1_players"].astype(str)
    x["n2"] = x["side2_players"].astype(str)
    x["tk1"], x["tk2"] = x["n1"].map(surname_key), x["n2"].map(surname_key)
    x["score_c"] = [canon(list(zip(itf_games(a), itf_games(b)))) for a, b in zip(x["side1_sets"], x["side2_sets"])]
    return x


# --------------------------------------------------------------------------------------------------------------------
# part 1: the editions of 7-14 Sep 2026

def part1(t: pd.DataFrame, k: pd.DataFrame, a: pd.DataFrame) -> dict:
    log("part 1: the ten editions of 7-14 Sep 2026")
    eds = t[t["start"] >= SEP_FIRST].copy()
    s = k[k["pseudo_tournament_id"].isin(set(eds["pseudo_tournament_id"]))].copy()
    s = p2b_truth(s, a)
    s["mkey"] = match_key(s)
    s.to_csv(OUT / "sep2026_raw_rows.csv", index=False, columns=[
        "match_row_id", "pseudo_match_id", "pseudo_tournament_id", "title", "startDate", "level", "group",
        "TournamentType", "perspective_player_id", "player_1", "player_2", "team_name_1", "team_name_2", "qpm_flag",
        "reason_code", "round_name", "tourn_round", "scores", "winner", "api_group", "api_start", "api_title",
        "api_level", "api_round", "api_scores", "mkey"])

    # one row per match (both players' listings, any edition)
    def first(sr):
        sr = sr.dropna()
        return sr.iloc[0] if len(sr) else None

    g = s.groupby("mkey")
    mt = pd.DataFrame({
        "n_rows": g.size(),
        "played": g["played"].any(),
        "reason": g["reason_code"].agg(lambda x: jn(x, ";")),
        "name_a": g["n1"].agg(first), "name_b": g["n2"].agg(first),
        "k_a": g["k1"].agg(first), "k_b": g["k2"].agg(first),
        "ids": g.apply(lambda d: ";".join(sorted({str(v) for v in pd.concat([d["player_1"], d["player_2"]]).dropna()})),
                       include_groups=False),
        "qpm_flag": g["qpm_flag"].agg(first), "round_name": g["round_name"].agg(first),
        "tourn_round": g["tourn_round"].agg(lambda x: jn(x, ";")),
        "site_score": g["scores"].agg(first), "score_c": g["score_c"].agg(first),
        "site_editions": g["title"].agg(lambda x: jn(x, " | ")),
        "site_edition_ids": g["pseudo_tournament_id"].agg(lambda x: ";".join(sorted({str(v) for v in x}))),
        "site_groups": g["group"].agg(lambda x: ";".join(sorted({str(v) for v in x.dropna()}))),
        "site_starts": g["startDate"].agg(lambda x: jn(x, ";")),
        "pseudo_match_ids": g["pseudo_match_id"].agg(lambda x: ";".join(sorted({str(v) for v in x}))),
        "n_editions": g["pseudo_tournament_id"].nunique(),
        "api_group": g["api_group"].agg(lambda x: ";".join(sorted(set(";".join(x.dropna()).split(";")) - {""}))),
        "api_title": g["api_title"].agg(first), "api_start": g["api_start"].agg(first),
        "api_level": g["api_level"].agg(first), "api_round": g["api_round"].agg(first),
        "api_scores": g["api_scores"].agg(first), "true_surface": g["api_surface"].agg(first),
        "true_in_outdoor": g["api_io"].agg(first),
    }).reset_index()

    # fall back to the API by id pair, draw, round and score where no row of the match joined exactly
    a2 = a.copy()
    a2["id_pair"] = ["|".join(sorted((str(x), str(y)))) for x, y in
                     zip(pd.to_numeric(a2["player_1"], errors="coerce").astype("Int64"),
                         pd.to_numeric(a2["player_2"], errors="coerce").astype("Int64"))]
    a2["score_c"] = a2["scores"].map(canon_text)
    mt["api_note"] = np.where(mt["api_group"].ne(""), "row fields", "not found")
    for i, r in mt[mt["api_group"].eq("")].iterrows():
        ids = r["ids"].split(";") if r["ids"] else []
        if len(ids) == 2:
            hit = a2[(a2["id_pair"] == "|".join(sorted(ids))) & (a2["score_c"] == r["score_c"])
                     & (a2["qpm_flag"] == r["qpm_flag"])]
            if len(hit):
                mt.loc[i, ["api_group", "api_title", "api_start", "api_level", "api_round", "api_scores",
                           "true_surface", "true_in_outdoor"]] = [
                    jn(hit["tourn_nbr"], ";"), hit["tournament_title"].iloc[0],
                    str(hit["StartDate"].iloc[0])[:10], hit["tournament_level"].iloc[0], hit["round_name"].iloc[0],
                    hit["scores"].iloc[0], hit["Surface"].iloc[0], hit["tournament_in_outdoor"].iloc[0]]
                mt.loc[i, "api_note"] = "id pair + score"

    # TennisLive: same pair (loose surname keys), any event 28 Aug - 27 Sep 2026
    tl = load_tl("2026-08-28", "2026-09-28")
    tl = tl[tl["junior"].astype(str).str.lower().isin(["false", "0", "none", "nan", ""])]
    tl["score_full"] = tl["score"].map(full_canon)
    rec = []
    for i, r in mt.iterrows():
        cand = tl[[same_pair(r["k_a"], r["k_b"], x, y) for x, y in zip(tl["tk1"], tl["tk2"])]]
        same = cand[cand["score_c"] == r["score_c"]]
        exact = same[same["score_full"] == full_canon(r["site_score"])]
        if len(exact):                     # a same-score rematch in another week: keep the one with equal tiebreaks
            same = exact
        pick = same if len(same) else cand
        rec.append({
            "tl_n_pair": len(cand), "tl_n_same_score": len(same),
            "tl_event": jn(pick["event_name"], " | ") if len(pick) else None,
            "tl_event_id": jn(pick["event_id"], ";") if len(pick) else None,
            "tl_kind": jn(pick["event_kind"], ";") if len(pick) else None,
            "tl_round": jn(pick["round"], ";") if len(pick) else None,
            "tl_day": jn(pick["start_utc"].astype(str).str[:10], ";") if len(pick) else None,
            "tl_score": jn(pick["score"], ";") if len(pick) else None,
            "tl_other_events": jn(set(cand["event_name"].dropna()) - set(same["event_name"].dropna()), " | ") or None})
    mt = pd.concat([mt, pd.DataFrame(rec, index=mt.index)], axis=1)

    # the WTA API's live-scoring lists of the 2026 events of these weeks (WTA 125 and tour)
    wl = load_wta_lists({2026})
    groups_here = {int(x) for x in eds["group"].dropna()} | {1112, 1173, 2093}
    wl = wl[wl["list_group"].isin(groups_here)]
    rec = []
    for i, r in mt.iterrows():
        ids = r["ids"].split(";") if r["ids"] else []
        if len(ids) == 2:
            hit = wl[wl["id_pair"] == "|".join(sorted(ids))]
        else:
            hit = wl[[same_pair(r["k_a"], r["k_b"], *p.split("|")) for p in wl["pair"]]]
        rec.append({"wta_list_groups": ";".join(str(v) for v in sorted(set(hit["list_group"]))) or None,
                    "wta_list_draw": jn(hit["draw"], ";") or None,
                    "wta_list_score": jn(hit["score"], ";") or None,
                    "wta_list_score_c_equal": bool((hit["score_c"] == r["score_c"]).any()) if len(hit) else None})
    mt = pd.concat([mt, pd.DataFrame(rec, index=mt.index)], axis=1)
    # did the claimed edition's own WTA list (where it has one) hold the pair?
    have_list = set(wl["list_group"])
    mt["claimed_has_list"] = mt["site_groups"].map(
        lambda s: any(int(g) in have_list for g in s.split(";") if g) if s else False)
    mt["claimed_list_holds_pair"] = [
        any(g and r_g and g in r_g.split(";") for g in str(sg).split(";"))
        for sg, r_g in zip(mt["site_groups"], mt["wta_list_groups"].fillna(""))]

    # ITF live (13 Sep on): only rematches of these pairs can show
    il = load_itf_live()
    rec = []
    for i, r in mt.iterrows():
        cand = il[[same_pair(r["k_a"], r["k_b"], x, y) for x, y in zip(il["tk1"], il["tk2"])]]
        rec.append({"itf_live_events": jn(cand["event_name"], " | ") or None,
                    "itf_live_score_equal": bool((cand["score_c"] == r["score_c"]).any()) if len(cand) else None})
    mt = pd.concat([mt, pd.DataFrame(rec, index=mt.index)], axis=1)

    # verdict: the true event is the WTA API's; TennisLive and the WTA's live-scoring list confirm it independently
    def verdict(r):
        api_g = [g for g in str(r["api_group"]).split(";") if g]
        true_title = r["api_title"] if api_g else None
        tl_agrees = bool(r["tl_event"]) and r["tl_n_same_score"] > 0 and true_title is not None and \
            same_place(true_title, r["tl_event"])
        list_agrees = bool(r["wta_list_groups"]) and api_g and \
            set(api_g) & set(str(r["wta_list_groups"]).split(";")) and bool(r["wta_list_score_c_equal"])
        claimed = set(str(r["site_groups"]).split(";"))
        right = bool(api_g) and set(api_g) <= claimed and len(claimed) == 1
        n_ind = int(tl_agrees) + int(bool(list_agrees))
        return pd.Series({
            "true_group": ";".join(api_g) or None, "true_event": true_title,
            "true_start": r["api_start"] if api_g else None,
            "true_level": LEVEL.get(str(r["api_level"]), r["api_level"]) if api_g else None,
            "true_map_level": (QUAL.get(LEVEL.get(str(r["api_level"]), ""), None) if r["qpm_flag"] == "Q"
                               else LEVEL.get(str(r["api_level"]))) if api_g else None,
            "site_label_right": right,
            "tl_agrees_with_api": tl_agrees, "wta_list_agrees_with_api": bool(list_agrees),
            "independent_confirmations": n_ind,
            "score_equal_api": canon_text(r["api_scores"]) == r["score_c"] if api_g else None,
            "score_equal_tl": r["tl_n_same_score"] > 0,
        })
    mt = pd.concat([mt, mt.apply(verdict, axis=1)], axis=1)
    mt["indisputable"] = (~mt["site_label_right"]) & mt["true_group"].notna() & (mt["independent_confirmations"] >= 1) \
        & mt["score_equal_api"].fillna(False)
    return {"eds": eds, "rows": s, "matches": mt}


# --------------------------------------------------------------------------------------------------------------------
# the data map, the feed, Stage 0

def score_same(a, b) -> bool:
    """Two canonical scores of one match: equal once empty sets ('0-0', a retirement's unplayed set) are dropped."""
    strip = lambda s: " ".join(x for x in str(s or "").split() if x != "0-0")  # noqa: E731
    return strip(a) != "" and strip(a) == strip(b)


def true_week(r) -> tuple[pd.Timestamp, pd.Timestamp]:
    """The true event's days: its qualifying weekend to the Sunday of its week (a match the next week is another)."""
    start = pd.Timestamp(str(r["true_start"]).split(";")[0])
    return start - pd.Timedelta(days=3), start + pd.Timedelta(days=7) - pd.Timedelta(seconds=1)


def resolve(copies: pd.DataFrame, right_col: str = "right") -> pd.Series:
    """The correction of each copy of one match: keep a right copy; else re-attribute one wrong copy (the first) and
    drop the rest as duplicates."""
    act = pd.Series("drop: duplicate of the right copy", index=copies.index)
    right = copies[right_col]
    if right.any():
        act[right] = "keep"
        keep_first = right[right].index[1:]
        act[keep_first] = "drop: second right copy"
    else:
        act.iloc[0] = "re-attribute to the true event and level"
        act.iloc[1:] = "drop: duplicate of the re-attributed copy"
    return act


def map_rows(mt: pd.DataFrame, eds: pd.DataFrame) -> pd.DataFrame:
    """Every map row that holds one of the matches: a wta_site row under one of the ten editions' titles (same pair and
    draw: a pair meets once per draw, and the five true events share one week), or another source's row of the same
    pair and draw in the true event's week (the WTA lists' rows carry no title)."""
    mp = pd.read_parquet(MAP)
    mp = mp[(mp["tour"] == "W") & (mp["d"] >= "2026-08-24") & (mp["d"] <= "2026-09-28")].copy()
    mp["k1"], mp["k2"] = mp["name1"].map(surname_key), mp["name2"].map(surname_key)
    site_titles = set(eds["title"])
    mp["from_ten_editions"] = mp["creator"].eq("wta_site") & mp["tname"].isin(site_titles)
    mp["six_titles"] = mp["from_ten_editions"] & mp["tname"].fillna("").str.contains("|".join(SIX_TITLES), regex=True)
    rows = []
    for _, r in mt[mt["played"]].iterrows():
        lo, hi = true_week(r)
        draw = "qual" if r["qpm_flag"] == "Q" else "main"
        pair = np.array([same_pair(r["k_a"], r["k_b"], x, y) for x, y in zip(mp["k1"], mp["k2"])], dtype=bool)
        c = mp[pair & (mp["draw"] == draw)]
        c = c[c["from_ten_editions"] | (~c["creator"].eq("wta_site") & c["d"].between(lo, hi)
                                         & (c["tname"].isna() | c["tname"].map(lambda x: same_place(x, r["true_event"]))))]
        for _, x in c.iterrows():
            right = (same_place(x["tname"], r["true_event"]) if pd.notna(x["tname"]) else True) and \
                x["level"] == r["true_map_level"]
            rows.append({"mkey": r["mkey"], "uid": x["uid"], "creator": x["creator"], "tname": x["tname"],
                         "level": x["level"], "draw": x["draw"], "d": x["d"], "name1": x["name1"], "name2": x["name2"],
                         "sources": x["sources"], "six_titles": x["six_titles"], "right": right,
                         "true_event": r["true_event"], "true_map_level": r["true_map_level"],
                         "true_start": r["true_start"], "true_round": r["api_round"], "score": r["site_score"]})
    res = pd.DataFrame(rows)
    res["n_copies"] = res.groupby("mkey")["uid"].transform("nunique")
    res = res.sort_values(["mkey", "right", "uid"], ascending=[True, False, True])
    res["correction"] = res.groupby("mkey", group_keys=False)[["right"]].apply(lambda d: resolve(d))
    # map rows of the ten editions this left unexplained (should be none)
    unexplained = mp[mp["from_ten_editions"] & ~mp["uid"].isin(set(res["uid"]))]
    if len(unexplained):
        log(f"map rows of the ten editions not tied to a match: {len(unexplained)}")
        unexplained.to_csv(OUT / "map_rows_unexplained.csv", index=False)
    return res


def table_copies(m: pd.DataFrame, mt: pd.DataFrame, name_cols: tuple[str, str], tag: str) -> pd.DataFrame:
    """Rows of a Stage 0-schema table (the feed snapshot, Stage 0) that hold one of the matches: same pair (loosely),
    same score, tournament dated from a week before the true event to two weeks after."""
    m = m.copy()
    m["fk1"], m["fk2"] = m[name_cols[0]].map(surname_key), m[name_cols[1]].map(surname_key)
    m["score_c"] = m["score"].map(canon_text)
    rows = []
    for _, r in mt[mt["played"]].iterrows():
        start = pd.Timestamp(str(r["true_start"]).split(";")[0])
        w = m[(m["tournament_date"] >= start - pd.Timedelta(days=7)) & (m["tournament_date"] <= start + pd.Timedelta(days=14))]
        c = w[[same_pair(r["k_a"], r["k_b"], x, y) and score_same(s, r["score_c"])
               for x, y, s in zip(w["fk1"], w["fk2"], w["score_c"])]]
        pmids = set(str(r["pseudo_match_ids"]).split(";"))
        for _, x in c.iterrows():
            sf = str(x.get("source_file", ""))
            origin = ("WTA website copy (this match's listing)" if sf.split(":", 1)[-1] in pmids else
                      "WTA API player matches (P2(b))" if sf.startswith("wta_site:api:") else
                      "WTA website copy (other listing)" if sf.startswith("wta_site:") else str(x["source"]))
            right = same_place(x["tournament_name"], r["true_event"]) and x["map_level"] == r["true_map_level"]
            rows.append({"mkey": r["mkey"], f"{tag}_match_id": x["match_id"], "source": x["source"],
                         "source_file": sf, "origin": origin, "tournament_id": x["tournament_id"],
                         "tournament": x["tournament_name"], "date": x["tournament_date"], "level": x["level"],
                         "map_level": x["map_level"], "round": x["round"], "score": x["score"], "right": right,
                         "surface": x.get("surface"), "indoor": x.get("indoor"),
                         "true_event": r["true_event"], "true_map_level": r["true_map_level"],
                         "true_start": r["true_start"], "true_round": r["api_round"], "tl_round": r["tl_round"],
                         "tl_day": r["tl_day"], "true_surface": r["true_surface"],
                         "true_indoor": {"I": True, "O": False}.get(str(r["true_in_outdoor"]).strip())})
    res = pd.DataFrame(rows)
    if len(res):
        res["surface_right"] = res["surface"].astype(str).str.lower() == res["true_surface"].astype(str).str.lower()
        res["n_copies"] = res.groupby("mkey")[f"{tag}_match_id"].transform("nunique")
        res = res.sort_values(["mkey", "right", f"{tag}_match_id"], ascending=[True, False, True])
        res["correction"] = res.groupby("mkey", group_keys=False)[["right"]].apply(lambda d: resolve(d))
    return res


def with_names(m: pd.DataFrame, p: pd.DataFrame) -> pd.DataFrame:
    p = p[p["match_id"].isin(set(m["match_id"]))]
    names = p.pivot_table(index="match_id", columns="side", values="player_name", aggfunc="first")
    return m.merge(names.rename(columns={"A": "name_a", "B": "name_b"}), left_on="match_id", right_index=True,
                   how="left")


def feed_copies(mt: pd.DataFrame) -> tuple[pd.DataFrame, str, pd.DataFrame]:
    acc = json.loads(ACCEPTED.read_text(encoding="utf-8"))
    snap = acc["feeds"]["lower_level_feed"]
    d = FEED_DIR / "lower_level_feed" / snap
    m = pd.read_parquet(d / "matches.parquet")
    m = m[(m["tour"] == "wta") & (m["tournament_date"] >= "2026-08-24") & (m["tournament_date"] <= "2026-09-28")]
    m = with_names(m, pd.read_parquet(d / "match_players.parquet", columns=["match_id", "side", "player_name"]))
    res = table_copies(m, mt, ("name_a", "name_b"), "feed")
    if len(res):
        # each copy's leak-proof window (es / lf as dates): a copy filed a week late counts its result a week late
        tm = pd.read_parquet(d / "timing.parquet", columns=["match_id", "es", "lf", "window_basis"])
        tm["es_day"] = pd.to_datetime(tm["es"], unit="D", errors="coerce").dt.date
        tm["lf_day"] = pd.to_datetime(tm["lf"], unit="D", errors="coerce").dt.date
        res = res.merge(tm[["match_id", "es_day", "lf_day", "window_basis"]], left_on="feed_match_id",
                        right_on="match_id", how="left").drop(columns=["match_id"])
        # the feed's own tournament id for each true event (from the right copies), for the re-attributions
        ids = res[res["right"]].groupby("true_event")[["tournament_id", "tournament"]].first()
        res["target_tournament_id"] = res["true_event"].map(ids["tournament_id"])
        res["target_tournament"] = res["true_event"].map(ids["tournament"])
    return res, snap


def stage0_copies(mt: pd.DataFrame) -> pd.DataFrame:
    m = pd.read_parquet(STAGE0 / "stage0_matches.parquet")
    m = m[(m["tour"] == "wta") & (m["tournament_date"] >= "2026-08-24") & (m["tournament_date"] <= "2026-09-28")]
    m = with_names(m, pd.read_parquet(STAGE0 / "stage0_match_players.parquet",
                                      columns=["match_id", "side", "player_name"]))
    return table_copies(m, mt, ("name_a", "name_b"), "s0")


# --------------------------------------------------------------------------------------------------------------------
# part 2: how widespread

def part2_p2b(k: pd.DataFrame, a: pd.DataFrame) -> pd.DataFrame:
    """(a) Every 2026 row against the P2(b) rows: per edition, rows found and rows in the same edition."""
    s = p2b_truth(k[k["year"] == 2026], a)
    s["found"] = s["api_group"].notna()
    s["kg"] = s["group"].astype(str)
    s["agree"] = s["found"] & np.array([str(g) in str(ag).split(";") for g, ag in zip(s["kg"], s["api_group"])], dtype=bool)
    s["agree_exactly"] = s["found"] & (s["kg"] == s["api_group"])
    e = s.groupby(["pseudo_tournament_id", "title", "startDate", "level", "kg"]).agg(
        rows=("key", "size"), found=("found", "sum"), same_edition=("agree", "sum"),
        api_events=("api_group", lambda x: x.dropna().nunique())).reset_index()
    e["other_edition"] = e["found"] - e["same_edition"]
    return e.sort_values("startDate")


def part2_lists(k: pd.DataFrame) -> pd.DataFrame:
    """(b) Every edition with a WTA API live-scoring list (2019-2026): share of its played singles matches listed."""
    wl = load_wta_lists()
    held = wl.groupby(["list_group", "list_year"])["id_pair"].agg(set).to_dict()
    held_names = wl.groupby(["list_group", "list_year"])["pair"].agg(set).to_dict()
    s = k[k["played"] & k["group"].notna()].drop_duplicates("pseudo_match_id").copy()
    s["year_ed"] = s["start"].dt.year
    rows = []
    for (pid, grp, title, sd, lvl, yr), d in s.groupby(["pseudo_tournament_id", "group", "title", "startDate", "level",
                                                        "year"]):
        key = (int(grp), int(yr))
        if key not in held:
            continue
        ids = ["|".join(sorted((str(a), str(b)))) if pd.notna(a) and pd.notna(b) else None
               for a, b in zip(d["player_1"], d["player_2"])]
        inl = [(x in held[key]) if x else (p in held_names[key]) for x, p in zip(ids, d["pair"])]
        rows.append({"pseudo_tournament_id": pid, "group": int(grp), "year": int(yr), "title": title, "start": sd,
                     "level": lvl, "matches": len(d), "in_list": int(sum(inl)), "not_in_list": int(len(d) - sum(inl))})
    r = pd.DataFrame(rows)
    r["share_in_list"] = r["in_list"] / r["matches"]
    return r.sort_values("start")


def load_sackmann(years: range) -> pd.DataFrame:
    fr = []
    for y in years:
        for f in (f"wta_matches_{y}.parquet", f"wta_matches_qual_itf_{y}.parquet"):
            p = SACKMANN / f
            if p.exists():
                fr.append(pd.read_parquet(p, columns=["tourney_id", "tourney_name", "tourney_level", "tourney_date",
                                                      "winner_name", "loser_name", "score", "round"]))
    s = pd.concat(fr, ignore_index=True)
    s["sd"] = pd.to_datetime(s["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    s["wk"], s["lk"] = s["winner_name"].map(surname_key), s["loser_name"].map(surname_key)
    s["pair"] = ["|".join(sorted((a, b))) if a and b and a != b else None for a, b in zip(s["wk"], s["lk"])]
    s["score_c"] = s["score"].map(canon_text)
    s["s_group"] = s["tourney_id"].astype(str).str.extract(r"^\d{4}-(\d+)$")[0]
    return s.dropna(subset=["pair"])


def part2_sackmann(k: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(c) Every played match against Sackmann's files: same pair and score within 45 days; is it the same week, and
    the same event (WTA group id where Sackmann gives one, else the place in the name)?"""
    s = load_sackmann(range(2018, 2027))
    km = k[k["played"] & k["pair"].notna()].drop_duplicates("pseudo_match_id").copy()
    km["mkey"] = match_key(km)
    km = km.drop_duplicates(["pseudo_tournament_id", "mkey"])
    j = km[["pseudo_tournament_id", "pseudo_match_id", "title", "start", "level", "group", "year", "pair", "score_c",
            "qpm_flag", "round_name", "mkey"]].merge(
        s[["pair", "score_c", "sd", "tourney_name", "tourney_level", "s_group", "round"]], on=["pair", "score_c"])
    j["dd"] = (j["sd"] - j["start"]).dt.days
    j = j[j["dd"].abs() <= 45].copy()
    j["same_week"] = j["dd"].abs() <= 6
    j["same_event"] = [(pd.notna(sg) and pd.notna(g) and str(int(g)) == sg) or same_place(t_, n_)
                       for g, sg, t_, n_ in zip(j["group"], j["s_group"], j["title"], j["tourney_name"])]
    # per Kaggle match: consistent if any Sackmann candidate is the same week and event
    best = j.assign(ok=j["same_week"] & j["same_event"]).groupby(["pseudo_tournament_id", "mkey"]).agg(
        ok=("ok", "any"), any_same_week=("same_week", "any"), any_same_event=("same_event", "any"),
        sack=("tourney_name", lambda x: jn(x, " | ")), sack_ids=("s_group", lambda x: jn(x, ";")),
        dd=("dd", lambda x: ";".join(map(str, sorted(set(x))))))
    km = km.merge(best, left_on=["pseudo_tournament_id", "mkey"], right_index=True, how="left")
    km["found"] = km["ok"].notna()
    km = km[km["start"] <= s["sd"].max() + pd.Timedelta(days=6)]
    team = km["title"].fillna("").str.contains(_TEAM)
    km["status"] = np.where(team, "team event (not compared)",
                            np.where(~km["found"], "not in Sackmann",
                                     np.where(km["ok"].fillna(False), "same week and event",
                                              np.where(km["any_same_week"].fillna(False), "same week, other event",
                                                       np.where(km["any_same_event"].fillna(False),
                                                                "same event, other week", "other week, other event")))))
    by = km.groupby(["year", "status"]).size().unstack(fill_value=0)
    cols = ["year", "pseudo_tournament_id", "pseudo_match_id", "title", "startDate", "level", "group", "qpm_flag",
            "round_name", "n1", "n2", "scores", "score_c", "sack", "sack_ids", "dd", "status"]
    return by, km.loc[km["status"].isin(["same week, other event", "same event, other week",
                                         "other week, other event"]), cols]


def kaggle_matches(k: pd.DataFrame) -> pd.DataFrame:
    km = k[k["played"] & k["pair"].notna()].copy()
    km["mkey"] = match_key(km)
    return km.drop_duplicates(["pseudo_tournament_id", "mkey"])


def purity(km: pd.DataFrame, ref: pd.DataFrame, lo: int = -7, hi: int = 21) -> pd.DataFrame:
    """Naming-free test of each edition: its matches found in an independent source (same pair of surname keys, same
    canonical score, the source's day from `lo` to `hi` days after the edition's start), and how many of them sit in
    the source's most common event for that edition. A real edition maps to one event (purity ~1); a scrambled one
    to several. ref needs: pair, score_c, day, ev, ev_name."""
    j = km[["pseudo_tournament_id", "title", "startDate", "start", "level", "year", "pair", "score_c", "mkey"]].merge(
        ref[["pair", "score_c", "day", "ev", "ev_name"]], on=["pair", "score_c"])
    j["dd"] = (j["day"] - j["start"]).dt.days
    j = j[j["dd"].between(lo, hi)]
    # one source event per match: the nearest in time
    j = j.assign(add=j["dd"].abs()).sort_values("add").drop_duplicates(["pseudo_tournament_id", "mkey"])
    n_all = km.groupby("pseudo_tournament_id").size().rename("matches")
    g = j.groupby(["pseudo_tournament_id", "ev"]).size().rename("n").reset_index()
    top = g.sort_values("n", ascending=False).drop_duplicates("pseudo_tournament_id").set_index("pseudo_tournament_id")
    found = g.groupby("pseudo_tournament_id")["n"].sum().rename("found")
    out = km.drop_duplicates("pseudo_tournament_id").set_index("pseudo_tournament_id")[
        ["title", "startDate", "level", "year"]].join(n_all).join(found).join(top[["ev", "n"]])
    out["found"] = out["found"].fillna(0).astype(int)
    out["in_top_event"] = out["n"].fillna(0).astype(int)
    out["source_events"] = g.groupby("pseudo_tournament_id")["ev"].nunique().reindex(out.index).fillna(0).astype(int)
    out["top_event_name"] = out["ev"].map(ref.drop_duplicates("ev").set_index("ev")["ev_name"])
    out["purity"] = out["in_top_event"] / out["found"].where(out["found"] > 0)
    return out.drop(columns=["n"]).reset_index().sort_values("startDate")


def ref_sackmann() -> pd.DataFrame:
    s = load_sackmann(range(2018, 2027))
    return pd.DataFrame({"pair": s["pair"], "score_c": s["score_c"], "day": s["sd"], "ev": s["tourney_id"].astype(str),
                         "ev_name": s["tourney_name"]})


def ref_tennislive() -> pd.DataFrame:
    tl = load_tl("2017-12-01", "2026-12-31")
    tl = tl[tl["junior"].astype(str).str.lower().isin(["false", "0", "none", "nan", ""])]
    tl = tl[tl["state"].astype(str).str.lower().eq("finished") | tl["state"].isna()]
    pair = ["|".join(sorted((a, b))) if a and b and a != b else None for a, b in zip(tl["tk1"], tl["tk2"])]
    return pd.DataFrame({"pair": pair, "score_c": tl["score_c"].to_numpy(),
                         "day": pd.to_datetime(tl["start_utc"].astype(str).str[:10], errors="coerce").to_numpy(),
                         "ev": tl["event_id"].astype(str).to_numpy(), "ev_name": tl["event_name"].to_numpy()}
                        ).dropna(subset=["pair"])


def part2_internal(k: pd.DataFrame) -> pd.DataFrame:
    """(d) The file against itself: one match (pair, draw, round, score) under two editions within 30 days."""
    km = k[k["played"] & k["pair"].notna()].copy()
    km["mkey"] = match_key(km)
    g = km.groupby("mkey").agg(n_ed=("pseudo_tournament_id", "nunique"), starts=("start", lambda x: sorted(set(x))),
                               titles=("title", lambda x: jn(x, " | ")),
                               years=("year", "max"))
    g = g[g["n_ed"] > 1].copy()
    g["span_days"] = g["starts"].map(lambda x: (max(x) - min(x)).days)
    g = g[g["span_days"] <= 30]
    g["first_start"] = g["starts"].map(min)
    return g.drop(columns=["starts"]).sort_values("first_start")


# --------------------------------------------------------------------------------------------------------------------

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    t = load_editions()
    log("reading the Kaggle copy")
    k = load_kaggle(t)
    log(f"{len(k):,} singles rows from editions since Dec 2017")
    a = load_p2b()
    log(f"P2(b) singles rows: {len(a):,}")

    # part 2 (a) first: it locates the scrambled editions
    e26 = part2_p2b(k, a)
    e26.to_csv(OUT / "editions_2026_vs_wta_api.csv", index=False)
    log("2026 editions vs the WTA API's player matches written")

    p1 = part1(t, k, a)
    mt = p1["matches"]

    # each listing (raw row): its edition against the true one
    rows = p1["rows"].merge(mt[["mkey", "true_group", "true_event", "true_map_level"]], on="mkey", how="left")
    rows["listing_right"] = rows["group"].astype(str) == rows["true_group"].astype(str)
    rows.to_csv(OUT / "sep2026_listings.csv", index=False, columns=[
        "match_row_id", "pseudo_match_id", "pseudo_tournament_id", "title", "startDate", "level", "group",
        "TournamentType", "perspective_player_id", "player_1", "player_2", "team_name_1", "team_name_2", "qpm_flag",
        "reason_code", "round_name", "tourn_round", "scores", "winner", "api_group", "api_title", "api_round",
        "api_scores", "mkey", "true_group", "true_event", "true_map_level", "listing_right"])

    def describe(c: pd.DataFrame, cols) -> pd.DataFrame:
        if not len(c):
            return pd.DataFrame(index=pd.Index([], name="mkey"))
        g = c.groupby("mkey")
        return pd.DataFrame({
            "copies": g.size(), "right_copies": g["right"].sum(),
            "entries": g.apply(lambda d: " | ".join(" ".join(str(getattr(r, x)) for x in cols) + f" [{r.correction}]"
                                                    for r in d.itertuples()), include_groups=False)})

    mp = map_rows(mt, p1["eds"])
    fc, snap = feed_copies(mt)
    s0 = stage0_copies(mt)
    mt = mt.merge(describe(mp, ["uid", "tname", "level"]).add_prefix("map_"), left_on="mkey", right_index=True,
                  how="left")
    mt = mt.merge(describe(fc, ["tournament", "map_level", "round", "origin"]).add_prefix("feed_"), left_on="mkey",
                  right_index=True, how="left")
    mt = mt.merge(describe(s0, ["tournament", "level", "source"]).add_prefix("stage0_"), left_on="mkey",
                  right_index=True, how="left")
    for c in ("map_copies", "map_right_copies", "feed_copies", "feed_right_copies", "stage0_copies",
              "stage0_right_copies"):
        if c in mt:
            mt[c] = mt[c].fillna(0).astype(int)
    mt.to_csv(OUT / "sep2026_matches.csv", index=False)
    mp.to_csv(OUT / "map_copies.csv", index=False)
    fc.to_csv(OUT / "feed_copies.csv", index=False)
    s0.to_csv(OUT / "stage0_copies.csv", index=False)
    six = mp[mp["six_titles"]].merge(
        mt[["mkey", "name_a", "name_b", "qpm_flag", "round_name", "site_score", "api_title", "api_round",
            "api_scores", "tl_event", "tl_round", "tl_day", "tl_score", "wta_list_groups", "wta_list_score",
            "independent_confirmations", "indisputable", "feed_copies", "feed_entries"]], on="mkey", how="left")
    six.to_csv(OUT / "map_55_six_titles.csv", index=False)
    # the deliverable: one line per map row of the six WTA 125 titles, with its real event
    fcm = fc.assign(e=fc["tournament"] + " [" + fc["map_level"] + ", " + fc["correction"] + "]").groupby("mkey")["e"] \
        .agg(lambda x: " | ".join(x)) if len(fc) else pd.Series(dtype=str)
    clean = pd.DataFrame({
        "map_uid": six["uid"], "site_title": six["tname"], "site_level": six["level"], "site_date": six["d"],
        "player_1": six["name1"], "player_2": six["name2"], "site_round": six["round_name"],
        "site_draw": six["qpm_flag"].map({"Q": "qualifying", "M": "main"}), "site_score": six["site_score"],
        "true_event": six["true_event"], "true_level": six["true_map_level"], "true_week": six["true_start"],
        "true_round": six["tl_round"], "true_day": six["tl_day"],
        "wta_api_score": six["api_scores"], "tennislive_event": six["tl_event"], "tennislive_score": six["tl_score"],
        "score_equal": six["mkey"].map(mt.set_index("mkey")["score_equal_api"]) &
        six["mkey"].map(mt.set_index("mkey")["score_equal_tl"]),
        "confirmed_by": np.where(six["mkey"].map(mt.set_index("mkey")["tl_agrees_with_api"]),
                                 "WTA API player matches + TennisLive", "WTA API player matches"),
        "map_correction": six["correction"], "map_copies_of_match": six["n_copies"],
        "feed_copies": six["mkey"].map(fcm)})
    clean.sort_values(["site_title", "map_uid"]).to_csv(OUT / "map_55_true_events.csv", index=False)
    log("part 1 written")

    if "--part1" in sys.argv:
        return
    lists = part2_lists(k)
    lists.to_csv(OUT / "editions_vs_wta_lists.csv", index=False)
    log("editions vs WTA lists written")
    by, dis = part2_sackmann(k)
    by.to_csv(OUT / "sackmann_status_by_year.csv")
    dis.to_csv(OUT / "sackmann_disagreements.csv", index=False)
    log("Sackmann comparison written")
    internal = part2_internal(k)
    internal.to_csv(OUT / "internal_two_editions.csv")
    log("internal duplicates written")
    km = kaggle_matches(k)
    rs, rt = ref_sackmann(), ref_tennislive()
    pur_s = purity(km, rs)
    pur_s.to_csv(OUT / "edition_purity_sackmann.csv", index=False)
    log("edition purity vs Sackmann written")
    pur_t = purity(km, rt)
    pur_t.to_csv(OUT / "edition_purity_tennislive.csv", index=False)
    log("edition purity vs TennisLive written")
    # a match under two editions: does an independent source hold two meetings (a real rematch) or one?
    internal = internal.reset_index()
    internal["pair"] = internal["mkey"].str.split("#").str[0]
    internal["score_c"] = internal["mkey"].str.split("#").str[3]
    for name, ref in (("tennislive", rt), ("sackmann", rs)):
        ev, nm = [], []
        for _, r in internal.iterrows():
            st = pd.Timestamp(r["first_start"])
            c = ref[(ref["pair"] == r["pair"]) & (ref["score_c"] == r["score_c"])
                    & ref["day"].between(st - pd.Timedelta(days=10), st + pd.Timedelta(days=40))]
            ev.append(c["ev"].nunique())
            nm.append(jn(c["ev_name"], " | "))
        internal[f"{name}_events"], internal[f"{name}_event_names"] = ev, nm
    internal.to_csv(OUT / "internal_two_editions.csv", index=False)
    log("two-edition matches checked against TennisLive and Sackmann")

    def low(p: pd.DataFrame) -> pd.DataFrame:
        return p[(p["found"] >= 5) & (p["purity"] < 0.8)]

    summary = {
        "kaggle_version": "29 (24 Sep 2026)", "feed_snapshot": snap,
        "ten_editions": p1["eds"][["pseudo_tournament_id", "title", "startDate", "level", "tournamentGroupId"]]
        .astype(str).to_dict("records"),
        "raw_singles_rows_ten_editions": int(len(rows)), "listings_right": int(rows["listing_right"].sum()),
        "matches_ten_editions": int(len(mt)), "played": int(mt["played"].sum()),
        "label_right": int(mt["site_label_right"].sum()),
        "true_event_found_api": int(mt["true_group"].notna().sum()),
        "true_events": mt["true_event"].value_counts().to_dict(),
        "indisputable": int(mt["indisputable"].sum()),
        "map_rows_six_titles": int(len(six)), "map_copies": mp["correction"].value_counts().to_dict(),
        "feed_copies": fc["correction"].value_counts().to_dict() if len(fc) else {},
        "feed_wrong_copies_wrong_surface": int((~fc["right"] & ~fc["surface_right"]).sum()) if len(fc) else 0,
        "feed_wrong_copies_by_title": {f"{a} {b}": int(n) for (a, b), n in
                                       fc[~fc["right"]].groupby(["tournament", "map_level"]).size().items()}
        if len(fc) else {},
        "feed_copies_by_level": {f"{a} right={b}": int(n) for (a, b), n in
                                 fc.groupby(["map_level", "right"]).size().items()} if len(fc) else {},
        "stage0_copies": s0["correction"].value_counts().to_dict() if len(s0) else {},
        "p2b_2026_rows_found": int(e26["found"].sum()), "p2b_2026_other_edition": int(e26["other_edition"].sum()),
        "p2b_2026_other_edition_before_sep7": int(e26.loc[e26["startDate"] < SEP_FIRST, "other_edition"].sum()),
        "wta_lists_editions": int(len(lists)),
        "wta_lists_matches": int(lists["matches"].sum()), "wta_lists_not_in_list": int(lists["not_in_list"].sum()),
        "sackmann_by_year": by.to_dict(orient="index"),
        "purity_sackmann": {"editions_with_5_found": int((pur_s["found"] >= 5).sum()),
                            "below_0.8": low(pur_s)[["title", "startDate", "found", "in_top_event", "purity"]]
                            .astype(str).to_dict("records")},
        "purity_tennislive": {"editions_with_5_found": int((pur_t["found"] >= 5).sum()),
                              "below_0.8": low(pur_t)[["title", "startDate", "found", "in_top_event", "purity"]]
                              .astype(str).to_dict("records")},
        "internal_two_editions_by_year": internal.groupby("years").size().to_dict(),
        "internal_two_editions_before_sep7_2026": {
            "matches": int((internal["first_start"] < pd.Timestamp(SEP_FIRST)).sum()),
            "tennislive_two_meetings": int(((internal["first_start"] < pd.Timestamp(SEP_FIRST))
                                            & (internal["tennislive_events"] >= 2)).sum()),
            "tennislive_one_event": int(((internal["first_start"] < pd.Timestamp(SEP_FIRST))
                                         & (internal["tennislive_events"] == 1)).sum())},
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    log("done")


if __name__ == "__main__":
    main()
