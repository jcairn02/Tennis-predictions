"""Stage 4: each event's country, for the candidate "playing in the home country".

No file on disk gives every tournament's country (candidates.md, section 4.6), so the plan named a hand-made table,
data/studies/predictability_diagnostic/stage4_event_country.csv, built at the start of Stage 4 and tracked by git. It
gives each evaluation event's country as an IOC code from the city in the event's name (the event names are keyed as
the plan's coverage script keys them: normalised, digits removed). A row may be limited to a span of seasons (an event
that moved, such as the ATP Finals) or to one tournament id (a name two events share). A blank country is an event the
name cannot place; its matches have no home-country value.

The table is checked, never corrected, against three sources on disk:
    tennis-data.co.uk's Location   the city of each main-tour match linked by Stage 1, read as a country (CITY below)
    the WTA's tournament ids       Sackmann's WTA ids of 2013-2015 carry a three-letter country code
    the WTA's calendar             data/dump/points/wta/editions.parquet (2016 and 2018-2026), linked by the WTA's
                                   tournament number; its countries are written as names and codes (WTA_NAMES)
Every disagreement is listed in stage4_event_country_check.csv; none is resolved silently.

Players' countries are Stage 0's ``country`` (the nation the player represents). A handful of rows write an ISO code
where the rest use the IOC's (PRT for POR, SVN for SLO ...); PLAYER_ALIASES reads them as the IOC code.

Writes, in data/studies/predictability_diagnostic/:
    stage4_event_country_check.csv   one row per tour x event name x season x tournament id: the table's country, each
                                     source's reading, the matches, and whether a source disagrees or is unreadable
    stage4_event_country_summary.json  the counts quoted in stage4.md

Run: ./python.sh src/eda/predictability_diagnostic/stage4_country.py   (under a minute)
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

TABLE = C.OUT / "stage4_event_country.csv"
CHECK = C.OUT / "stage4_event_country_check.csv"
SUMMARY = C.OUT / "stage4_event_country_summary.json"
ODDS = C.OUT / "stage1_odds.parquet"
WTA_EDITIONS = C.DUMP / "points" / "wta" / "editions.parquet"

# ISO codes some Stage 0 rows use for a player's nation, read as the IOC code the rest use; and two French territories
# whose players represent France
PLAYER_ALIASES = {"PRT": "POR", "URY": "URU", "SVN": "SLO", "VNM": "VIE", "PRY": "PAR", "BHR": "BRN", "BWA": "BOT",
                  "SAU": "KSA", "GTM": "GUA", "CHL": "CHI", "PRI": "PUR", "COG": "CGO", "LIB": "LBN", "NCL": "FRA",
                  "GUD": "FRA"}
# the three-letter codes in the WTA's 2013-2015 tournament ids that differ from the IOC's
WTA_ID_CODES = {"SIN": "SGP"}

# tennis-data.co.uk's Location (a city) as a country, for the check
CITY = {
    "'s-Hertogenbosch": "NED", "Abu Dhabi": "UAE", "Acapulco": "MEX", "Adelaide": "AUS", "Almaty": "KAZ", "Antalya": "TUR",
    "Antwerp": "BEL", "Athens": "GRE", "Atlanta": "USA", "Auckland": "NZL", "Austin": "USA", "Bad Gastein": "AUT",
    "Bad Homburg": "GER", "Baku": "AZE", "Bali": "INA", "Bangkok": "THA", "Banja Luka": "BIH", "Barcelona": "ESP",
    "Basel": "SUI", "Bastad": "SWE", "Beijing": "CHN", "Belgrade": "SRB", "Berlin": "GER", "Biel": "SUI",
    "Birmingham": "GBR", "Bogota": "COL", "Brisbane": "AUS", "Brussels": "BEL", "Bucharest": "ROU", "Budapest": "HUN",
    "Buenos Aires": "ARG", "Cagliari": "ITA", "Cancun": "MEX", "Carlsbad": "USA", "Casablanca": "MAR",
    "Charleston": "USA", "Chengdu": "CHN", "Chennai": "IND", "Chicago": "USA", "Cincinnati": "USA", "Cleveland": "USA",
    "Cluj-Napoca": "ROU", "College Park": "USA", "Cologne": "GER", "Copenhagen": "DEN", "Cordoba": "ARG",
    "Costa Do Sauipe": "BRA", "Courmayeur": "ITA", "Dallas": "USA", "Delray Beach": "USA", "Doha": "QAT",
    "Dubai": "UAE", "Dusseldorf": "GER", "Eastbourne": "GBR", "Estoril": "POR", "Fes": "MAR", "Florence": "ITA",
    "Florianopolis": "BRA", "Fort Worth": "USA", "Gdynia": "POL", "Geneva": "SUI", "Gijon": "ESP", "Granby": "CAN",
    "Gstaad": "SUI", "Guadalajara": "MEX", "Guangzhou": "CHN", "Halle": "GER", "Hamburg": "GER", "Hangzhou": "CHN",
    "Hiroshima": "JPN", "Hobart": "AUS", "Hong Kong": "HKG", "Houston": "USA", "Hua Hin": "THA", "Iasi": "ROU",
    "Indian Wells": "USA", "Istanbul": "TUR", "Jiujiang": "CHN", "Johannesburg": "RSA", "Jurmala": "LAT",
    "Kaohsiung": "TPE", "Katowice": "POL", "Kitzbuhel": "AUT", "Kuala Lumpur": "MAS", "Lausanne": "SUI",
    "Lexington": "USA", "Linz": "AUT", "London": "GBR", "Los Angeles": "USA", "Los Cabos": "MEX", "Lugano": "SUI",
    "Luxembourg": "LUX", "Lyon": "FRA", "Madrid": "ESP", "Mallorca": "ESP", "Marbella": "ESP", "Marrakech": "MAR",
    "Marrakesh": "MAR", "Marseille": "FRA", "Melbourne": "AUS", "Memphis": "USA", "Merida": "MEX", "Metz": "FRA",
    "Miami": "USA", "Monastir": "TUN", "Monte Carlo": "MON", "Monterrey": "MEX", "Montpellier": "FRA",
    "Montreal": "CAN", "Moscow": "RUS", "Munich": "GER", "Nanchang": "CHN", "Napoli": "ITA", "New Haven": "USA",
    "New York": "USA", "Newport": "USA", "Nice": "FRA", "Ningbo": "CHN", "Nottingham": "GBR", "Nur-Sultan": "KAZ",
    "Nurnberg": "GER", "Oeiras": "POR", "Osaka": "JPN", "Ostrava": "CZE", "Palermo": "ITA", "Paris": "FRA",
    "Parma": "ITA", "Pattaya": "THA", "Ponte Vedra Beach": "USA", "Portoroz": "SLO", "Prague": "CZE", "Pune": "IND",
    "Quebec": "CAN", "Queens Club": "GBR", "Quito": "ECU", "Rabat": "MAR", "Rio de Janeiro": "BRA", "Riyadh": "KSA",
    "Rome": "ITA", "Rotterdam": "NED", "Rouen": "FRA", "San Diego": "USA", "San Jose": "USA", "Santiago": "CHI",
    "Sao Paulo": "BRA", "Sardinia": "ITA", "Seoul": "KOR", "Shanghai": "CHN", "Shenzhen": "CHN", "Singapore": "SGP",
    "Sofia": "BUL", "St. Petersburg": "RUS", "Stanford": "USA", "Stockholm": "SWE", "Strasbourg": "FRA",
    "Stuttgart": "GER", "Sydney": "AUS", "Taipei": "TPE", "Tallinn": "EST", "Tashkent": "UZB", "Tel Aviv": "ISR",
    "Tenerife": "ESP", "Tianjin": "CHN", "Tokyo": "JPN", "Toronto": "CAN", "Turin": "ITA", "Umag": "CRO",
    "Valencia": "ESP", "Vienna": "AUT", "Vina del Mar": "CHI", "Warsaw": "POL", "Washington": "USA",
    "Winston-Salem": "USA", "Wuhan": "CHN", "Zagreb": "CRO", "Zhengzhou": "CHN", "Zhuhai": "CHN"}

# the WTA calendar's countries (names, codes and "STATE, UNITED STATES" forms) as IOC codes
WTA_NAMES = {
    "ANDORRA": "AND", "ARG": "ARG", "ARGENTINA": "ARG", "AUS": "AUS", "AUSTRALIA": "AUS", "AUSTRIA": "AUT", "AUT": "AUT",
    "BOLIVIA": "BOL", "BRA": "BRA", "BRAZIL": "BRA", "CAN": "CAN", "CANADA": "CAN", "CHI": "CHI", "CHILE": "CHI",
    "CHINA": "CHN", "CHINESE TAIPEI": "TPE", "CHN": "CHN", "COL": "COL", "COLOMBIA": "COL", "CRO": "CRO",
    "CROATIA": "CRO", "CZE": "CZE", "CZECH REPUBLIC": "CZE", "ECU": "ECU", "ESP": "ESP", "ESTONIA": "EST", "FRA": "FRA",
    "FRANCE": "FRA", "GBR": "GBR", "GER": "GER", "GERMANY": "GER", "GRE": "GRE", "GREAT BRITAIN": "GBR", "HKG": "HKG",
    "HONG-KONG, CHINA": "HKG", "HUNGARY": "HUN", "IND": "IND", "INDIA": "IND", "ITA": "ITA", "ITALY": "ITA",
    "JAPAN": "JPN", "JPN": "JPN", "KAZAKHSTAN": "KAZ", "KOR": "KOR", "KOREA": "KOR", "KSA": "KSA", "LATVIA": "LAT",
    "LUXEMBOURG": "LUX", "MALAYSIA": "MAS", "MAR": "MAR", "MEX": "MEX", "MEXICO": "MEX", "MOROCCO": "MAR", "NED": "NED",
    "NETHERLANDS": "NED", "NEW ZEALAND": "NZL", "NZL": "NZL", "PHI": "PHI", "POL": "POL", "POLAND": "POL", "POR": "POR",
    "PORTUGAL": "POR", "QAT": "QAT", "QATAR": "QAT", "ROMANIA": "ROU", "ROU": "ROU", "RUSSIA": "RUS", "SERBIA": "SRB",
    "SGP": "SGP", "SLO": "SLO", "SLOVENIA": "SLO", "SPAIN": "ESP", "SUI": "SUI", "SWE": "SWE", "SWEDEN": "SWE",
    "SWITZERLAND": "SUI", "THAILAND": "THA", "TUNISIA": "TUN", "TUR": "TUR", "TURKEY": "TUR", "UAE": "UAE",
    "UNITED ARAB EMIRATES": "UAE", "URUGUAY": "URU", "UZBEKISTAN": "UZB"}


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z ]", " ", s.replace("-", " ")).split())


def event_key(name) -> str:
    """The plan's key for an event name (stage4_candidates.py): normalised, digits removed."""
    return re.sub(r"\d+", "", norm_name(name)).strip()


def ascii_fold(s: str) -> str:
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().strip()


def wta_country(s) -> str | None:
    """A WTA calendar country as an IOC code; None when it cannot be read."""
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return None
    t = str(s).strip().upper()
    if "UNITED STATES" in t or t == "USA" or t.startswith("USA,"):
        return "USA"
    return WTA_NAMES.get(t)


def player_country(code: pd.Series) -> pd.Series:
    """Stage 0's player country with the ISO codes read as IOC codes."""
    return code.astype("object").map(lambda c: PLAYER_ALIASES.get(c, c) if isinstance(c, str) else None)


def load_table() -> pd.DataFrame:
    t = pd.read_csv(TABLE, dtype={"tournament_id": "string", "country": "string"})
    assert not t.duplicated(["tour", "event_key", "from_year", "to_year", "tournament_id"]).any()
    return t


def event_country(matches: pd.DataFrame, table: pd.DataFrame | None = None) -> pd.Series:
    """Each match's event country (IOC code) from the hand-made table, or missing. ``matches`` needs tour, year,
    tournament_id and tournament_name. A row naming a tournament id beats a row with a span of seasons, which beats a
    row for the whole name."""
    t = load_table() if table is None else table
    key = matches["tournament_name"].map(event_key)
    out = pd.Series(pd.NA, index=matches.index, dtype="string")
    rank = pd.Series(-1, index=matches.index)
    tours, years, tids = matches["tour"].to_numpy(), matches["year"].to_numpy(), matches["tournament_id"].astype(str).to_numpy()
    keys = key.to_numpy()
    for r in t.itertuples(index=False):
        hit = (tours == r.tour) & (keys == r.event_key)
        level = 0
        if pd.notna(r.from_year):
            hit &= (years >= int(r.from_year)) & (years <= int(r.to_year))
            level = 1
        if pd.notna(r.tournament_id):
            hit &= tids == str(r.tournament_id)
            level = 2
        take = hit & (rank.to_numpy() < level)
        out[take] = r.country if pd.notna(r.country) else pd.NA
        rank[take] = level
    return out


# ------------------------------------------------------------------------------------------------

def check() -> tuple[pd.DataFrame, dict]:
    m = C.load_matches(["match_id", "tour", "year", "level", "qualifying", "evaluation", "tournament_id", "tournament_name"])
    ev = m[m["evaluation"]].copy()
    ev["event_key"] = ev["tournament_name"].map(event_key)
    table = load_table()
    ev["country"] = event_country(ev, table)
    known_keys = set(zip(table["tour"], table["event_key"]))
    ev["in_table"] = [(t, k) in known_keys for t, k in zip(ev["tour"], ev["event_key"])]

    # tennis-data.co.uk's Location through Stage 1's link
    o = pd.read_parquet(ODDS, columns=["match_id", "td_file", "td_row"])
    o = o[o["td_file"].notna()]
    parts = []
    for f, g in o.groupby("td_file"):
        loc = pd.read_parquet(ROOT / f, columns=["Location"])["Location"].to_numpy()
        parts.append(pd.DataFrame({"match_id": g["match_id"].to_numpy(), "td_location": loc[g["td_row"].astype(int).to_numpy()]}))
    loc = pd.concat(parts, ignore_index=True)
    loc["td_location"] = loc["td_location"].map(lambda s: ascii_fold(s) if isinstance(s, str) else None)
    loc["td_country"] = loc["td_location"].map(CITY)
    ev = ev.merge(loc, on="match_id", how="left")

    # the WTA's ids of 2013-2015 and its calendar (2016 on)
    code = ev["tournament_id"].astype(str).str.extract(r"^\d{4}-W-[A-Z0-9]+-([A-Z]{3})-")[0]
    ev["wta_id_country"] = np.where(ev["tour"].eq("wta"), code.map(lambda c: WTA_ID_CODES.get(c, c) if isinstance(c, str) else None), None)
    wed = pd.read_parquet(WTA_EDITIONS, columns=["tournament_id", "year", "country"])
    wed = wed.assign(tid=wed["tournament_id"].astype(str).str.lstrip("0"), year=wed["year"].astype(int))
    wed = wed.drop_duplicates(["tid", "year"])
    num = ev["tournament_id"].astype(str).str.extract(r"^\d{4}-[A-Z]?0*(\d+)$")[0]
    ev["tid"] = np.where(ev["tour"].eq("wta"), num, None)
    ev = ev.merge(wed[["tid", "year", "country"]].rename(columns={"country": "wta_calendar_raw"}), on=["tid", "year"], how="left")
    ev["wta_calendar_country"] = ev["wta_calendar_raw"].map(wta_country)

    def join(s):
        v = sorted({str(x) for x in s.dropna()})
        return "; ".join(v)

    g = ev.groupby(["tour", "event_key", "year", "tournament_id"], dropna=False).agg(
        level=("level", "first"), names=("tournament_name", join), matches=("match_id", "size"),
        in_table=("in_table", "first"), country=("country", "first"),
        td_matches=("td_location", "count"), td_location=("td_location", join), td_country=("td_country", join),
        td_agree=("td_country", lambda s: int(0)), wta_id_country=("wta_id_country", join),
        wta_calendar_raw=("wta_calendar_raw", join), wta_calendar_country=("wta_calendar_country", join)).reset_index()
    # match-level agreement with tennis-data (an event can be linked to rows of more than one Location)
    ev["td_disagrees"] = ev["td_country"].notna() & ev["country"].notna() & (ev["td_country"] != ev["country"])
    ev["td_unread"] = ev["td_location"].notna() & ev["td_country"].isna()
    per = ev.groupby(["tour", "event_key", "year", "tournament_id"], dropna=False).agg(
        td_disagree_matches=("td_disagrees", "sum"), td_unread_matches=("td_unread", "sum")).reset_index()
    g = g.drop(columns="td_agree").merge(per, on=["tour", "event_key", "year", "tournament_id"], how="left")

    def disagrees(table_c, src):
        return [bool(isinstance(c, str) and s and c not in s.split("; ")) for c, s in zip(table_c, src)]
    g["wta_id_disagrees"] = disagrees(g["country"], g["wta_id_country"])
    g["wta_calendar_disagrees"] = disagrees(g["country"], g["wta_calendar_country"])
    g["wta_calendar_unread"] = [bool(r and not c) for r, c in zip(g["wta_calendar_raw"], g["wta_calendar_country"])]
    g["no_country"] = g["country"].isna()
    g["flag"] = (g["td_disagree_matches"].gt(0) | g["td_unread_matches"].gt(0) | g["wta_id_disagrees"]
                 | g["wta_calendar_disagrees"] | g["wta_calendar_unread"] | g["no_country"] | ~g["in_table"])
    g = g.sort_values(["tour", "event_key", "year", "tournament_id"]).reset_index(drop=True)

    mp = C.load_match_players(["match_id", "country"], with_order=False)
    mp = mp[mp["match_id"].isin(ev["match_id"])]
    pc = player_country(mp["country"])
    both = pc.notna().groupby(mp["match_id"]).all()
    ev_c = ev.set_index("match_id")["country"]
    summ = {
        "table_rows": int(len(table)), "event_keys": {t: int(table.loc[table["tour"].eq(t), "event_key"].nunique()) for t in C.TOURS},
        "evaluation_keys": {t: int(ev.loc[ev["tour"].eq(t), "event_key"].nunique()) for t in C.TOURS},
        "keys_missing_from_table": sorted({f"{t}|{k}" for t, k, i in zip(ev["tour"], ev["event_key"], ev["in_table"]) if not i}),
        "matches_with_country": {t: int(ev.loc[ev["tour"].eq(t), "country"].notna().sum()) for t in C.TOURS},
        "matches_without_country": {t: int(ev.loc[ev["tour"].eq(t), "country"].isna().sum()) for t in C.TOURS},
        "unresolved_rows": table.loc[table["country"].isna(), ["tour", "event_key", "basis"]].to_dict(orient="records"),
        "tennis_data": {"linked_matches": int(ev["td_location"].notna().sum()),
                        "agree": int((ev["td_country"].notna() & (ev["td_country"] == ev["country"])).sum()),
                        "disagree": int(ev["td_disagrees"].sum()), "location_unread": int(ev["td_unread"].sum()),
                        "disagreeing_events": g.loc[g["td_disagree_matches"].gt(0), ["tour", "event_key", "year", "country", "td_location", "td_disagree_matches"]].to_dict(orient="records")},
        "wta_ids": {"events": int(g["wta_id_country"].ne("").sum()), "agree": int((g["wta_id_country"].ne("") & ~g["wta_id_disagrees"]).sum()),
                    "disagree": g.loc[g["wta_id_disagrees"], ["event_key", "year", "country", "wta_id_country"]].to_dict(orient="records")},
        "wta_calendar": {"events": int(g["wta_calendar_raw"].ne("").sum()),
                         "agree": int((g["wta_calendar_country"].ne("") & ~g["wta_calendar_disagrees"]).sum()),
                         "disagree": g.loc[g["wta_calendar_disagrees"], ["event_key", "year", "country", "wta_calendar_raw"]].to_dict(orient="records"),
                         "unread": g.loc[g["wta_calendar_unread"], ["event_key", "year", "country", "wta_calendar_raw"]].to_dict(orient="records")},
        "player_aliases": PLAYER_ALIASES,
        "player_rows_aliased": {k: int((mp["country"] == k).sum()) for k in PLAYER_ALIASES if (mp["country"] == k).any()},
        "matches_both_players_with_country": {t: int(both.reindex(ev.loc[ev["tour"].eq(t), "match_id"]).sum()) for t in C.TOURS},
        "matches_home_defined": {t: int((both.reindex(ev.loc[ev["tour"].eq(t), "match_id"]).fillna(False).to_numpy()
                                         & ev_c.reindex(ev.loc[ev["tour"].eq(t), "match_id"]).notna().to_numpy()).sum()) for t in C.TOURS},
        "evaluation_matches": {t: int(ev["tour"].eq(t).sum()) for t in C.TOURS}}
    return g, summ


def main() -> int:
    g, summ = check()
    g.to_csv(CHECK, index=False)
    SUMMARY.write_text(json.dumps(summ, indent=1, default=str), encoding="utf-8")
    print(f"wrote {CHECK.name} ({len(g):,} event-seasons, {int(g['flag'].sum())} flagged) and {SUMMARY.name}")
    print(json.dumps({k: summ[k] for k in ("keys_missing_from_table", "matches_without_country")}, default=str))
    print("tennis-data:", {k: v for k, v in summ["tennis_data"].items() if k != "disagreeing_events"})
    print("WTA ids:", {k: (v if not isinstance(v, list) else len(v)) for k, v in summ["wta_ids"].items()})
    print("WTA calendar:", {k: (v if not isinstance(v, list) else len(v)) for k, v in summ["wta_calendar"].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
