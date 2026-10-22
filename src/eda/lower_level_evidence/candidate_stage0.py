"""Role F of the level-evidence system: the candidate Stage 0 that holds the lower-level data the owner's rule of 8 Oct
2026 keeps out (data/studies/lower_level_evidence/system/preregistration_addition_1.md; SPEC.md section 12).

What it builds. The FROZEN Stage 0 of the reference of 8 Oct 2026 (common.STAGE0_DIR), unchanged, plus:
    new matches     lower-level singles (TQ, GSQ, CH, CHQ, ITF, ITFQ) that the frozen Stage 0 lacks, from the sources on
                    disk, each player given a resolved id (the source's id mapped to Stage 0's through the matches both
                    hold, or a new id in the source's own namespace)
    completions     box scores for reference matches Stage 0 holds as results only (lower levels): an override layer,
                    on by default, that changes no fact of the match (players, date, round, score, result)
    revisions       other box scores for reference matches that already have one: counted always, applied only with
                    --revisions (a separate layer, off by default)
and the timeline that goes with it: the frozen reference's timeline row for every reference match, unchanged, and a
cautious window for every new match (match_timing's es / lf: a result counts from lf + 1, a match reads the state as of
es): the source's own day where it gives one, widened by the clock error measured against the frozen timeline's exact
days, else the frozen timeline's class window from the tournament date (timing.py's rules), never a guessed day.

The sources, in the order they are wired (a later source's rows are linked against Stage 0 plus every match an earlier
source added, so a match two sources hold is added once, by the first):
    wta_api      the WTA API's match lists and box scores (WTA tour, WTA 125, Slams 2024-26, qualifying; 2019-2026),
                 data/dump/points/wta/ (staged by src/ingest/point_sources/wta.py; batches finished 2-3 Oct 2026)
    wta_site     the WTA website's records (Kaggle bwandowando v29, 24 Sep 2026; women's results at every level, ITF and
                 qualifying included, since 1975), data/raw/gap_sources/bwandowando/
    tennislive   P4, TennisLive's event listings (every level, both tours, 2018 - 4 Oct 2026; results),
                 data/dump/points/tennislive/listed.parquet
    itf_live     P1, the ITF live-data API (ITF and ITFQ, both tours, from 15 Sep 2026; statistics), data/dump/points/itf_live/.
                 After TennisLive: its players are then identified through the matches both list (15 Sep - 4 Oct), by
                 TennisLive ids that the reference's own matches validate, rather than by name alone
    sofascore    the three SofaScore collections (P6 so far; P7 once staged): box scores, and the few matches they add
    tennislive_pages  TennisLive match pages (P5 once staged, P8): box scores only, never a new match
    tdi          TDI, the ATP's data company (weekly since 23 Jun 2026): box scores only, for men's Challenger and tour
                 matches; the first-serve split counted from its point files (added 13 Oct 2026, data_gaps_2026)
Since 13 Oct 2026 (docs/studies/data_gaps_2026/) wta_site also reads the WTA API's player-matches results (P2(b),
data/dump/points/wta/player_results/), after the Kaggle copy's rows: a match the copy holds is kept from the copy
(--no-wta-player-matches: the source as before).
Box scores of matches the candidate holds go to the box layers (one source per match: BOX_PRIORITY).

Linking: src/eda/match_timing/srcc_common.link (the timeline's identity linker: both names in the window, confirmed by
identical set scores or by the same round on a plausible day; a third pass by the source's own player ids), run per
tour and season. Then:
    event map    each source event -> the Stage 0 tournament most of its linked rows (with identical set scores) sit in
    weekly venue a link into another tournament than the row's own mapped event stands only with identical set scores
                 (Monastir and Antalya hold real rematches a week apart: a pair is never deduplicated across events)
    ids          a source id is keyed by its tour (TennisLive numbers its ATP and WTA players separately) and maps to
                 the Stage 0 id the linked matches agree on (>= 80% of a source id's links, no Stage 0 id claimed twice
                 unless the names agree: srcc_common.crosswalk's rule, over every season); else the one Stage 0 player
                 of the tour with the same exact name key (repair_data.name_key) and no contradicting country, if no
                 other source id maps to him; else a new id "<tour>:<tag>:<source id>" (tags wtaid, itf, tl, sofa),
                 which no Stage 0 id uses; a new match whose player id is of the other tour stops the build
    new          a row neither linked nor clashing: no Stage 0 match (or earlier addition) of the same resolved pair in
                 the same tournament (or, for a tournament Stage 0 lacks, within 3 days); a player never plays twice in
                 one round of one tournament; walkovers and byes are left out; retirements keep their marker
Left out, and counted (left_out.csv.gz): ambiguous rows, rows whose players or event cannot be placed, main-tour and team
matches (the rule concerns lower-level data; a new main-tour row could also enter the model frame itself), clashes,
unknown rounds.

No outcome of a 2025-2026 match is read for any choice: the rules above are fixed in this file; set scores are compared
only to confirm that two records are one match (the timeline's linker does the same).

Outputs, data/studies/lower_level_evidence/system/stage0/<label>/:
    stage0_matches.parquet, stage0_match_players.parquet   the candidate Stage 0 (Stage 0's schema; chronological order)
    timing.parquet                                         its timeline (match_timing's schema)
    additions.parquet          one row per new match: source, source key, how each player was resolved
    box_layers.parquet         completions and revisions: the reference match, the source, old and new counts, applied?
    left_out.csv.gz            every source row not wired, with why
    links_<source>.parquet, crosswalk_<source>.csv         evidence of the linking
    inventory.csv              source x kind x tour x level x year: counts, and how many touch the model's players
    checks.json, manifest.json, READY.txt (written by --ready after the checks pass)

Run:
    ./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_now
    ./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_now --checks        (checks, history.py, dose)
    ./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_now --ready         (READY.txt + manifest)
    ./python.sh src/eda/lower_level_evidence/candidate_stage0.py --label C0_pre --derive-from C0_now --until 2024-12-29
        (a READY candidate's additions dated up to a day: same ids, windows and box scores; then --checks, --ready)
Options: --sources wta_api,wta_site,tennislive,itf_live,sofascore,tennislive_pages  --revisions
         --sofascore-skip "ITF Men,ITF Women"  --out <folder>
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import time
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.lower_level_evidence import common as LC  # noqa: E402
from src.eda.match_timing import common as MT  # noqa: E402
from src.eda.match_timing import srcc_common as K  # noqa: E402
from src.eda.match_timing import srcc_tz as TZ  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402

SYSTEM = LC.OUT / "system"
STAGE0_OUT = SYSTEM / "stage0"
STATUS_LOG = SYSTEM / "status.log"
REF_TABLES = LC.STAGE0_DIR
REF_TIMING = LC.TIMING
REF_CLASSES = LC.REF / "tables_later" / "data" / "studies" / "match_timing" / "timing_classes.csv"
RULES = ROOT / "data" / "studies" / "match_timing" / "schedule_rules.csv"
DUMP = ROOT / "data" / "dump"
RAW = ROOT / "data" / "raw"
WTA = DUMP / "points" / "wta"
ITF = DUMP / "points" / "itf_live"
TL = DUMP / "points" / "tennislive"
WTA_SITE = RAW / "gap_sources" / "bwandowando"

LOWER_MAP = ("TQ", "GSQ", "CH", "CHQ", "ITF", "ITFQ")       # the levels a new match or a box layer may touch
COUNTS = list(C.BOX)                                         # Stage 0's nine counts
SRC_NAMES = dict(C.BOX_SOURCE_NAMES)                         # ... in Sackmann's column names (w_1stIn ...)
EPOCH = pd.Timestamp("1970-01-01")
FIRST_DAY = pd.Timestamp(f"{C.FIRST_YEAR - 1}-12-01")       # Stage 0 keeps matches from December 2009 (stage0_build C02)
SOURCE_ORDER = ["wta_api", "wta_site", "tennislive", "itf_live", "sofascore", "tennislive_pages", "tdi"]   # docstring
BOX_PRIORITY = ["wta_api", "itf_live", "tdi", "sofascore", "tennislive_pages"]   # one box score per match: the first
BOX_ONLY = {"tennislive_pages", "tdi"}  # sources that give box scores to matches the candidate holds, never a new match
BOX_SOURCES = {"only": None, "exclude": set()}   # --box-sources: the sources whose box scores may enter, in priority
#                                         order; --box-exclude: (source, level) pairs left out (13 Oct 2026, data_gaps_2026:
#                                         the lower-level feed leaves SofaScore's out, whose counts differ from Stage 0's,
#                                         first serves in equal in 43-54% of shared rows, and TennisLive's at ITF, which
#                                         miss points in about 15% of matches: serve points 1.8 lower on average)
TAGS = {"wta_api": "wtaid", "wta_site": "wtaid", "itf_live": "itf", "tennislive": "tl", "sofascore": "sofa",
        "tennislive_pages": "tl", "tdi": "tdi"}
PACKAGES = {"wta_api": "WTA API (B1-B9, on disk 3 Oct; P2 top-ups)",
            "itf_live": "P1", "wta_site": "WTA website records (Kaggle v29) + the WTA API's player matches (P2(b))",
            "tennislive": "P4", "sofascore": "P6 (P7 once staged) + earlier SofaScore collections",
            "tennislive_pages": "P5 (P8) + earlier TennisLive pages", "tdi": "TDI (weekly, from 23 Jun 2026)"}
XWALK_SHARE = 0.8              # srcc_common.crosswalk's rule: a source id's links agreeing on one Stage 0 id
EVENT_SHARE = 0.6              # share of an event's confirmed links that must sit in one Stage 0 tournament
NEW_EVENT_DAYS = 3             # a new event's pair clash window (days of the tournament date)
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


QUIET = {"on": False}           # a development label (starting with '_') writes nothing to the team's status log
STATUS = {"log": STATUS_LOG}    # --status-log: another study's log (a candidate built after the team closed, 10 Oct)


def status(msg: str) -> None:
    """One line of the team's status log (append only), or of the log --status-log names."""
    if QUIET["on"]:
        log(f"(status, not logged) {msg}")
        return
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    Path(STATUS["log"]).parent.mkdir(parents=True, exist_ok=True)
    with Path(STATUS["log"]).open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} F {msg}\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jdump(obj, path: Path) -> None:
    K.jdump(obj, path)


def rel(path: Path) -> str:
    """A path relative to the repository where it is inside it, else as given."""
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).as_posix()


# ------------------------------------------------------------------------------------------------ names, dates
@lru_cache(maxsize=None)
def name_key(value) -> str:
    """repair_data.name_key: accents folded, lower case, letters and digits only (the chain's identity repair uses it)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return ""
    s = unicodedata.normalize("NFKD", str(value)).casefold()
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", s).split())


def nearest_monday(d: pd.Series) -> pd.Series:
    """timing.anchor_day's rule on dates: Tue -1, Wed -2, Thu -3, Fri +3, Sat +2, Sun +1."""
    d = pd.to_datetime(d, errors="coerce").dt.normalize()
    shift = d.dt.weekday.map({0: 0, 1: -1, 2: -2, 3: -3, 4: 3, 5: 2, 6: 1})
    return (d + pd.to_timedelta(shift, unit="D")).astype("datetime64[ns]")


# ISO 3166 alpha-3 codes some feeds use (the WTA API's Slam qualifying rows) where Stage 0 (Sackmann) uses the IOC's
ISO_IOC = {"DEU": "GER", "PRT": "POR", "NLD": "NED", "CHE": "SUI", "DNK": "DEN", "HRV": "CRO", "SVN": "SLO",
           "BGR": "BUL", "GRC": "GRE", "LVA": "LAT", "IDN": "INA", "MYS": "MAS", "PHL": "PHI", "PRY": "PAR",
           "URY": "URU", "CHL": "CHI", "ZAF": "RSA", "TWN": "TPE", "ARE": "UAE", "SAU": "KSA", "IRN": "IRI",
           "VNM": "VIE", "LKA": "SRI", "GTM": "GUA", "SLV": "ESA", "CRI": "CRC", "HND": "HON", "NGA": "NGR",
           "MNG": "MGL", "BHR": "BRN", "KWT": "KUW", "OMN": "OMA", "LBN": "LIB", "ZWE": "ZIM", "MDG": "MAD",
           "TZA": "TAN", "AGO": "ANG", "BRB": "BAR", "PRI": "PUR", "VEN": "VEN"}


def ioc(text) -> str | None:
    if text is None or (isinstance(text, float) and np.isnan(text)) or str(text).strip() == "":
        return None
    s = str(text).strip()
    if len(s) == 3 and s.isupper():
        return ISO_IOC.get(s, s)
    return TZ.country_code(s.replace("-", " "))


SURFACES = {"hard": "Hard", "clay": "Clay", "grass": "Grass", "carpet": "Carpet", "antuka": "Clay", "indoor": "Hard",
            "hardcourt": "Hard", "i.hard": "Hard", "artificial grass": "Grass"}


def surface_of(text) -> str | None:
    s = str(text or "").strip().lower()
    for k, v in SURFACES.items():
        if s.startswith(k):
            return v
    return None


def score_text(pairs, tbs=None) -> str:
    """Winner-first set scores in Stage 0's form ('7-6(5) 3-6 6-2'); tbs: the tiebreak loser's points per set or None."""
    out = []
    for i, (a, b) in enumerate(pairs):
        s = f"{a}-{b}"
        tb = None if tbs is None or i >= len(tbs) else tbs[i]
        if tb is not None and abs(a - b) == 1 and max(a, b) == 7:
            s += f"({tb})"
        out.append(s)
    return " ".join(out)


# ------------------------------------------------------------------------------------------------ the reference
def load_reference(folder: Path = REF_TABLES) -> tuple[pd.DataFrame, pd.DataFrame]:
    m = pd.read_parquet(folder / "stage0_matches.parquet")
    mp = pd.read_parquet(folder / "stage0_match_players.parquet")
    return m, mp


def link_frame(m: pd.DataFrame, mp: pd.DataFrame) -> pd.DataFrame:
    """srcc_common.stage0() on the given tables (the frozen ones, plus additions): names, winner-first sets, early
    round numbers, qualifying depth, the event's country."""
    cols = ["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
            "tournament_name", "tournament_date", "status", "score", "player_a_id", "player_b_id", "a_won", "map_level"]
    f = m[cols].copy()
    for c in ("match_id", "tour", "level", "round", "tournament_id", "tournament_name", "status", "score",
              "player_a_id", "player_b_id", "map_level"):
        f[c] = f[c].astype(object)
    names = mp[["match_id", "side", "player_name"]].drop_duplicates(["match_id", "side"])
    for side in ("A", "B"):
        n = names[names["side"].eq(side)].set_index("match_id")["player_name"]
        f[f"name_{side.lower()}"] = f["match_id"].map(n).astype(object)
    f["tdate"] = pd.to_datetime(f["tournament_date"]).astype("datetime64[ns]")
    f["sets_w"] = f["score"].map(K.s0_sets)
    return add_event_columns(f.reset_index(drop=True))


def add_event_columns(f: pd.DataFrame) -> pd.DataFrame:
    ev = ["tour", "tournament_date", "tournament_id"]
    early = f["round"].isin(K.EARLY_ROUNDS)
    first = f[early].groupby(ev)["round_order"].transform("min")
    f["round_no"] = np.nan
    f.loc[first.index, "round_no"] = (f.loc[first.index, "round_order"] - first + 1).astype("float64")
    qn = f["round"].astype(str).str.extract(r"^Q(\d)$")[0].astype("float64")
    f["qmax"] = qn.groupby([f[c] for c in ev]).transform("max")
    if "country" not in f or f["country"].isna().all():
        f["country"] = K.event_countries(f)
    return f


# ------------------------------------------------------------------------------------------------ source loaders
# Each loader returns (rows, stats). rows: one per played singles match, in the common schema below; stats: counts of
# what was read and set aside (walkovers, byes, unfinished).
SCHEMA = ["sid", "source", "tour", "season", "ev_key", "ev_name", "ev_date", "ev_surface", "ev_indoor", "ev_country",
          "ev_level", "ev_draw", "qual", "rnd", "day", "date_basis", "start_utc", "end_utc", "p1", "p2", "id1", "id2", "c1", "c2",
          "winner", "status_hint", "score", "sets", "minutes", "has_src_box"] + \
         [f"p{k}_{c}" for k in (1, 2) for c in COUNTS]


def finish(rows: pd.DataFrame, source: str) -> pd.DataFrame:
    rows = rows.copy()
    rows["source"] = source
    for c in SCHEMA:
        if c not in rows:
            rows[c] = np.nan
    for k in (1, 2):
        for c in COUNTS:
            rows[f"p{k}_{c}"] = pd.to_numeric(rows[f"p{k}_{c}"], errors="coerce").astype("float64")
    rows["has_src_box"] = rows[[f"p{k}_svpt" for k in (1, 2)]].notna().all(axis=1) & \
        rows[[f"p{k}_{c}" for k in (1, 2) for c in COUNTS if c != "sv_gms"]].notna().all(axis=1)
    rows["ev_date"] = pd.to_datetime(rows["ev_date"]).astype("datetime64[ns]")
    rows["day"] = pd.to_datetime(rows["day"]).astype("datetime64[ns]")
    # a December 2009 event belongs to the 2010 season, as in Stage 0 (its first season; Sackmann files such events in 2010)
    # the season as Stage 0 labels it: an event starting in the last week of December opens the next season
    # (Sackmann files Brisbane 2019, 31 Dec 2018, under 2019), so that a match's season and its holdout date agree
    rows["season"] = (pd.to_datetime(rows["ev_date"]) + pd.Timedelta(days=7)).dt.year
    rows["season"] = pd.to_numeric(rows["season"], errors="coerce").clip(lower=C.FIRST_YEAR).astype("Int64")
    rows = rows[rows["ev_date"].notna() & (rows["ev_date"] >= FIRST_DAY) & rows["season"].notna()]
    for c in ("id1", "id2"):
        rows[c] = rows[c].astype(str).where(rows[c].notna() & rows[c].astype(str).str.strip().ne(""), None)
    if rows["sid"].duplicated().any():
        raise ValueError(f"{source}: source keys are not unique")
    return rows[SCHEMA].reset_index(drop=True)


def wta_read(table: str, year: int, cols: list[str]) -> pd.DataFrame:
    """The WTA staged per-year tables carry 'year' twice: always name the columns."""
    path = WTA / table / f"{year}.parquet"
    have = set(pq.read_schema(path).names)
    return pq.read_table(path, columns=[c for c in cols if c in have]).to_pandas()


WTA_TIER = {"1000": "T1000", "500": "T500", "250": "T250", "125": "CH", "finals": "FIN", "slam": "GS", "team": "TEAM"}
WTA_MAIN_ROUNDS = {"Q": "QF", "S": "SF", "F": "F", "G": "RR"}


def pow2(n) -> int | None:
    try:
        n = int(n)
    except (TypeError, ValueError):
        return None
    if n <= 1:
        return None
    k = 1
    while k < n:
        k *= 2
    return k


def wta_round(draw: str, rid, size) -> str | None:
    r = "" if rid is None or (isinstance(rid, float) and np.isnan(rid)) else str(rid).strip()
    if draw == "qual_singles":
        return f"Q{r}" if r in ("1", "2", "3", "4") else None
    if r in WTA_MAIN_ROUNDS:
        return WTA_MAIN_ROUNDS[r]
    p = pow2(size)
    if r.isdigit() and p:
        n = p // (2 ** (int(r) - 1))
        return {2: "F", 4: "SF", 8: "QF"}.get(n, f"R{n}" if n >= 16 else None)
    return None


def load_wta_api() -> tuple[pd.DataFrame, dict]:
    sc = [f"ScoreSet{k}{s}" for k in range(1, 6) for s in "AB"] + [f"ScoreTbSet{k}" for k in range(1, 6)]
    cols = ["tournament_id", "match_id", "tier", "draw", "walkover", "RoundID", "MatchState", "Winner", "ScoreString",
            "MatchTimeStamp", "MatchTimeTotal", "PlayerIDA", "PlayerNameFirstA", "PlayerNameLastA", "PlayerCountryA",
            "PlayerIDB", "PlayerNameFirstB", "PlayerNameLastB", "PlayerCountryB"] + sc
    frames = []
    for y in range(2019, 2027):
        if (WTA / "matches" / f"{y}.parquet").exists():
            frames.append(wta_read("matches", y, cols).assign(year=y))
    m = pd.concat(frames, ignore_index=True)
    m = m[m["draw"].isin(["main_singles", "qual_singles"])].drop_duplicates(["tournament_id", "year", "match_id"])
    stats = {"singles_listed": int(len(m))}
    win = m["Winner"].astype(str)
    walk = win.isin(["6", "7"]) | m["walkover"].astype(str).str.upper().eq("TRUE")
    played = m["MatchState"].astype(str).eq("F") & win.isin(["2", "3", "4", "5"]) & ~walk
    stats.update(walkovers=int(walk.sum()), not_played_or_unfinished=int((~played & ~walk).sum()))
    m = m[played].copy()
    ed = pq.read_table(WTA / "editions.parquet", columns=["tournament_id", "year", "tier", "title", "start_date",
                                                          "surface", "in_outdoor", "country",
                                                          "singles_draw_size"]).to_pandas()
    ed["year"] = ed["year"].astype(int)
    ed = ed.drop_duplicates(["tournament_id", "year"]).set_index(["tournament_id", "year"])
    key = pd.MultiIndex.from_arrays([m["tournament_id"].astype(str), m["year"].astype(int)])
    edk = ed.reindex(key)
    a_won = win.loc[m.index].isin(["2", "4"]).to_numpy()
    pairs, tbs = [], []
    for _, r in m.iterrows():
        g = []
        t = []
        for k in range(1, 6):
            a, b = K.int_or_none(r[f"ScoreSet{k}A"]), K.int_or_none(r[f"ScoreSet{k}B"])
            if a is None or b is None:
                break
            g.append((a, b))
            t.append(K.int_or_none(r[f"ScoreTbSet{k}"]))
        pairs.append(tuple(g))
        tbs.append(t)
    win_first = [tuple((a, b) if aw else (b, a) for a, b in g) for g, aw in zip(pairs, a_won)]
    retired = win.loc[m.index].isin(["4", "5"]).to_numpy()
    score = [score_text(g, t) + (" RET" if r else "") for g, t, r in zip(win_first, tbs, retired)]
    ts = pd.to_datetime(m["MatchTimeStamp"], utc=True, format="ISO8601", errors="coerce")
    size = edk["singles_draw_size"].to_numpy()
    rows = pd.DataFrame({
        "sid": "wta_api:" + m["tournament_id"].astype(str) + "/" + m["year"].astype(str) + "/" + m["match_id"].astype(str),
        "tour": "wta", "season": m["year"].to_numpy(),
        "ev_key": "wta_api:" + m["tournament_id"].astype(str) + "_" + m["year"].astype(str),
        "ev_name": edk["title"].fillna("").astype(str).str.split(" - ").str[-1].to_numpy(),
        "ev_date": nearest_monday(pd.Series(edk["start_date"].to_numpy())).to_numpy(),
        "ev_surface": [surface_of(s) for s in edk["surface"].to_numpy()],
        "ev_indoor": pd.Series(edk["in_outdoor"].to_numpy()).map({"I": True, "O": False}).to_numpy(),
        "ev_country": [ioc(c) for c in edk["country"].to_numpy()],
        "ev_level": pd.Series(edk["tier"].astype(str).to_numpy()).map(WTA_TIER).to_numpy(),
        "ev_draw": pd.to_numeric(pd.Series(size), errors="coerce").to_numpy(),
        "qual": m["draw"].eq("qual_singles").to_numpy(),
        "rnd": [wta_round(d, r, s) for d, r, s in zip(m["draw"], m["RoundID"], size)],
        "day": ts.dt.tz_convert(None).dt.normalize().to_numpy(), "date_basis": "utc_date",
        "start_utc": ts.to_numpy(),
        "p1": (m["PlayerNameFirstA"].fillna("") + " " + m["PlayerNameLastA"].fillna("")).str.strip().to_numpy(),
        "p2": (m["PlayerNameFirstB"].fillna("") + " " + m["PlayerNameLastB"].fillna("")).str.strip().to_numpy(),
        "id1": m["PlayerIDA"].astype(str).to_numpy(), "id2": m["PlayerIDB"].astype(str).to_numpy(),
        "c1": [ioc(c) for c in m["PlayerCountryA"]], "c2": [ioc(c) for c in m["PlayerCountryB"]],
        "winner": np.where(a_won, 1, 2), "status_hint": np.where(retired, "retired", "completed"),
        "score": score, "sets": pairs,
        "minutes": [mins(x) for x in m["MatchTimeTotal"]]})
    # box scores (setnum 0 = the whole match), mapped as data_continuity/sources.py and prediction_run/fills.py read them
    box = []
    for y in range(2019, 2027):
        if (WTA / "stats" / f"{y}.parquet").exists():
            s = wta_read("stats", y, ["tournament_id", "match_id", "setnum", "acesa", "acesb", "dblflta", "dblfltb",
                                      "ptswon1stserva", "ptswon1stservb", "ptsplayed1stserva", "ptsplayed1stservb",
                                      "ptstotwonserva", "ptstotwonservb", "totservplayeda", "totservplayedb",
                                      "breakptsconva", "breakptsconvb", "breakptsplayeda", "breakptsplayedb",
                                      "servgamesplayeda", "servgamesplayedb"]).assign(year=y)
            box.append(s[s["setnum"].astype(str).eq("0")])
    if box:
        s = pd.concat(box, ignore_index=True).drop_duplicates(["tournament_id", "year", "match_id"])
        s["sid"] = "wta_api:" + s["tournament_id"].astype(str) + "/" + s["year"].astype(str) + "/" + s["match_id"].astype(str)
        num = lambda c: pd.to_numeric(s[c], errors="coerce")  # noqa: E731
        for k, me, op in ((1, "a", "b"), (2, "b", "a")):
            s[f"p{k}_ace"], s[f"p{k}_df"] = num(f"aces{me}"), num(f"dblflt{me}")
            s[f"p{k}_svpt"], s[f"p{k}_first_in"] = num(f"totservplayed{me}"), num(f"ptsplayed1stserv{me}")
            s[f"p{k}_first_won"] = num(f"ptswon1stserv{me}")
            s[f"p{k}_second_won"] = num(f"ptstotwonserv{me}") - num(f"ptswon1stserv{me}")
            s[f"p{k}_sv_gms"] = num(f"servgamesplayed{me}")
            s[f"p{k}_bp_faced"] = num(f"breakptsplayed{op}")
            s[f"p{k}_bp_saved"] = num(f"breakptsplayed{op}") - num(f"breakptsconv{op}")
        rows = rows.merge(s[["sid"] + [f"p{k}_{c}" for k in (1, 2) for c in COUNTS]], on="sid", how="left")
    rows["rnd"] = infer_qual_rounds(rows)
    stats["played"] = int(len(rows))
    return finish(rows, "wta_api"), stats


def infer_qual_rounds(rows: pd.DataFrame) -> pd.Series:
    """Qualifying rounds the source leaves blank (the WTA API's Slam qualifying, 2024-26: only a day number), from the
    draw itself: in a knockout both players have played the same number of the event's earlier qualifying matches, so
    the round is that number plus one, taken in the order the matches started. A match whose two players disagree keeps
    no round (it is left out: an unordered round cannot be placed)."""
    out = rows["rnd"].copy()
    need = rows["qual"].astype(bool) & rows["rnd"].isna()
    for _, g in rows[rows["ev_key"].isin(set(rows.loc[need, "ev_key"])) & rows["qual"].astype(bool)].groupby("ev_key"):
        g = g.assign(_t=pd.to_datetime(g["start_utc"], utc=True)).sort_values(["_t", "sid"])
        played: dict = {}
        for i, a, b in zip(g.index, g["id1"], g["id2"]):
            na, nb = played.get(a, 0), played.get(b, 0)
            if need.loc[i]:
                out.loc[i] = f"Q{na + 1}" if na == nb and na < 4 else None
            played[a], played[b] = na + 1, nb + 1
    return out


def mins(text) -> float:
    m = re.match(r"^(\d+):(\d\d):(\d\d)", str(text or ""))
    if not m:
        return np.nan
    v = int(m.group(1)) * 60 + int(m.group(2)) + int(m.group(3)) / 60
    return float(round(v)) if v > 0 else np.nan


ITF_STATS = {"aces": "ace", "doubleFaults": "df", "servePointsPlayed": "svpt", "firstServePercentage": "first_pct",
             "firstServePointsWon": "first_won", "secondServePointsWon": "second_won", "serveGamesPlayed": "sv_gms",
             "breakPointOpportunities": "bp_opp", "breakPointsConversions": "bp_conv"}


def itf_sets(text) -> list[tuple[int, int | None]]:
    """'1:7/7 2:6/0' -> [(7, 7), (6, 0)]: games and tiebreak points per set."""
    out = []
    for _, g, t in re.findall(r"(\d+):(\d+)(?:/(\d+))?", str(text or "")):
        out.append((int(g), int(t) if t else None))
    return out


def load_itf_live() -> tuple[pd.DataFrame, dict]:
    m = pd.read_parquet(ITF / "matches.parquet")
    m = m[m["latest"].eq("TRUE") & m["match_type"].fillna("").str.lower().eq("singles")]
    stats = {"singles_listed": int(len(m))}
    st = m["status"].fillna("").str.lower()
    walk = st.isin(["walkover", "bye"])
    post = m["status_state_type"].fillna("").str.lower().eq("post")
    win = pd.to_numeric(m["winner_side_order"], errors="coerce")
    ok = post & ~walk & win.isin([1, 2]) & ~st.isin(["scoring stopped", "postponed"])
    stats.update(walkovers_or_byes=int(walk.sum()), unfinished_or_no_winner=int((~ok & ~walk).sum()))
    m = m[ok].copy()
    win = win.loc[m.index].astype(int).to_numpy()
    ev = pd.read_parquet(ITF / "events.parquet").drop_duplicates("event_key").set_index("event_key")
    evk = ev.reindex(m["event_key"])
    s1, s2 = m["side1_sets"].map(itf_sets), m["side2_sets"].map(itf_sets)
    pairs, scores = [], []
    for a, b, w, stt in zip(s1, s2, win, m["status"].fillna("").str.lower()):
        g = tuple((x[0], y[0]) for x, y in zip(a, b))
        pairs.append(g)
        wf = [((x[0], y[0]), (y[1] if x[0] > y[0] else x[1])) if w == 1 else ((y[0], x[0]), (x[1] if y[0] > x[0] else y[1]))
              for x, y in zip(a, b)]
        tb = [t if {g_[0], g_[1]} == {7, 6} else None for g_, t in wf]
        scores.append(score_text([g_ for g_, _ in wf], tb) + (" RET" if "retire" in stt else ""))
    qual = m["draw"].fillna("").str.contains("qualif", case=False).to_numpy()
    ro = pd.to_numeric(m["round_order"], errors="coerce").to_numpy()
    # qualifying: the draw's own round order (R64/R32/R16 of the qualifying draw are Q1, Q2 ...); main draw: its label
    rnd = [f"Q{int(o)}" if q and np.isfinite(o) and 1 <= o <= 4 else (None if q else K.round_code(r))
           for q, o, r in zip(qual, ro, m["round"])]
    tour = m["gender"].map({"men": "atp", "women": "wta"})
    end = pd.to_datetime(m["actual_end_date"], utc=True, errors="coerce")
    rows = pd.DataFrame({
        "sid": "itf_live:" + m["match_id"].astype(str), "tour": tour.to_numpy(),
        "season": pd.to_datetime(m["date_start_local"], errors="coerce").dt.year.to_numpy(),
        "ev_key": "itf_live:" + m["event_key"].astype(str), "ev_name": m["event_name"].to_numpy(),
        "ev_date": nearest_monday(pd.Series(pd.to_datetime(evk["start_date"].to_numpy(), utc=True).tz_convert(None))).to_numpy(),
        "ev_surface": [surface_of(s) for s in evk["surface"].to_numpy()], "ev_indoor": None,
        "ev_country": [ioc(c) for c in evk["country_iso"].to_numpy()], "ev_level": "ITF",
        "ev_draw": None, "qual": qual, "rnd": rnd,
        "day": pd.to_datetime(m["date_start_local"], errors="coerce").to_numpy(), "date_basis": "local",
        "start_utc": pd.NaT, "end_utc": end.to_numpy(),
        "p1": m["side1_players"].to_numpy(), "p2": m["side2_players"].to_numpy(),
        "id1": m["side1_player_ids"].to_numpy(), "id2": m["side2_player_ids"].to_numpy(),
        "c1": [ioc(c) for c in m["side1_countries"]], "c2": [ioc(c) for c in m["side2_countries"]],
        "winner": win, "status_hint": np.where(m["status"].fillna("").str.lower().str.contains("retire"), "retired",
                                               "completed"),
        "score": scores, "sets": pairs, "minutes": [mins(x) for x in m["duration"]]})
    # statistics (period 'match'); break points are recorded on the returner's side (as the WTA API's): a side's faced
    # break points are the opponent's opportunities, its saved ones those less the opponent's conversions (checked:
    # conversions equal the opponent's breaks in 99% of matches, opportunities minus 'saved' in 6%)
    s = pd.read_parquet(ITF / "statistics.parquet", columns=["match_id", "stat_source_name", "period", "side_order",
                                                              "value"])
    s = s[s["period"].eq("match") & s["stat_source_name"].isin(ITF_STATS)]
    w = s.pivot_table(index="match_id", columns=["side_order", "stat_source_name"], values="value", aggfunc="first")
    box = pd.DataFrame(index=w.index)
    for k, me, op in ((1, "1", "2"), (2, "2", "1")):
        g = lambda side, name: pd.to_numeric(w.get((side, name)), errors="coerce")  # noqa: E731
        svpt = g(me, "servePointsPlayed")
        fi = svpt * g(me, "firstServePercentage") / 100
        box[f"p{k}_ace"], box[f"p{k}_df"], box[f"p{k}_svpt"] = g(me, "aces"), g(me, "doubleFaults"), svpt
        box[f"p{k}_first_in"] = np.where((fi - np.round(fi)).abs() < 0.02, np.round(fi), np.nan)
        box[f"p{k}_first_won"], box[f"p{k}_second_won"] = g(me, "firstServePointsWon"), g(me, "secondServePointsWon")
        box[f"p{k}_sv_gms"] = g(me, "serveGamesPlayed")
        box[f"p{k}_bp_faced"] = g(op, "breakPointOpportunities")
        box[f"p{k}_bp_saved"] = g(op, "breakPointOpportunities") - g(op, "breakPointsConversions")
    box.index = "itf_live:" + box.index.astype(str)
    rows = rows.merge(box, left_on="sid", right_index=True, how="left")
    stats["played"] = int(len(rows))
    return finish(rows, "itf_live"), stats


WTA_SITE_LEVEL = {"ITF": "ITF", "WTA 125": "CH", "125K": "CH", "WTA 250": "T250", "International": "T250",
                  "WTA 500": "T500", "Premier": "T500", "WTA 1000": "T1000", "Premier 5": "T1000",
                  "Premier Mandatory": "T1000", "Grand Slam": "GS", "Finals": "FIN"}
_TEAM = re.compile(r"united cup|atp cup|laver cup|davis cup|billie jean king|bjk cup|fed cup|olympic|hopman", re.I)


def wta_site_name(s) -> tuple[str, str | None]:
    """'SURNAME,  FIRST  CTY' -> ('First Surname', 'CTY')."""
    s = str(s or "")
    if "," not in s:
        return s.strip(), None
    last, rest = s.split(",", 1)
    parts = rest.split()
    cc = None
    if len(parts) > 1 and len(parts[-1]) == 3 and parts[-1].isupper():
        cc = parts[-1]
        parts = parts[:-1]
    return " ".join([p.capitalize() if p.isupper() else p for p in parts]
                    + [" ".join(w.capitalize() if w.isupper() else w for w in last.strip().split())]), cc


def wta_site_rounds(m: pd.DataFrame) -> pd.Series:
    """The site's rounds in Stage 0's labels. A qualifying round is named by its place in the qualifying draw ('R32'
    opens a 32-player qualifying, 'R16' its second round): its number is the record's own round index, tourn_round
    (R64 1, R32 2, R16 3 in a 64-player qualifying; 'Q' 3 in a 32-player one). Where tourn_round is missing, the
    data map's rule (measure.wta_site_rounds): the round's place after the tournament's first qualifying round; that
    rule misnumbers a tournament listed twice when one copy lacks a round. In a main draw 'Q' and 'S' are the quarter-
    and semi-finals."""
    order = ["R128", "R64", "R32", "R16", "Q", "S", "F"]
    name = m["round_name"].fillna("").astype(str).str.strip()
    pos = name.map({r: i for i, r in enumerate(order)})
    qual = m["qpm_flag"].eq("Q")
    first = pos.where(qual).groupby(m["pseudo_tournament_id"]).transform("min")
    step = (pos - first).where(qual)
    by_place = step.map(lambda s: f"Q{int(s) + 1}" if pd.notna(s) and int(s) <= 3 else None)
    tr = pd.to_numeric(m["tourn_round"], errors="coerce") if "tourn_round" in m else pd.Series(np.nan, index=m.index)
    own = tr.map(lambda v: f"Q{int(v)}" if pd.notna(v) and 1 <= v <= 4 else None)
    q = own.where(own.notna(), by_place)
    main = name.replace({"Q": "QF", "S": "SF"}).where(name.isin(order), None)
    return pd.Series(np.where(qual, q, main), index=m.index)


def wta_site_own_names(m: pd.DataFrame) -> pd.Series:
    """Each WTA id's own name key: the name found in (nearly) every row the id appears in, either side. The site's rows
    put the ids in the listing player's order (player_1 is the player whose page listed the match) and, in later
    seasons, the names in draw order, so a row's names cannot be read off its ids' positions: 14% of rows have them the
    other way round. An id whose name is not in 90% of its rows keeps none."""
    k1 = m["team_name_1"].map(lambda s: name_key(wta_site_name(s)[0]))
    k2 = m["team_name_2"].map(lambda s: name_key(wta_site_name(s)[0]))
    long = pd.concat([pd.DataFrame({"pid": m[p_].to_numpy(), "k": k.to_numpy()})
                      for p_ in ("player_1", "player_2") for k in (k1, k2)], ignore_index=True)
    long = long[long["pid"].notna() & long["k"].ne("")]
    rows = pd.concat([m["player_1"], m["player_2"]]).dropna().value_counts()
    cnt = long.groupby(["pid", "k"]).size().rename("n").reset_index().sort_values(["pid", "n"], ascending=[True, False])
    cnt = cnt.drop_duplicates("pid")
    cnt["share"] = cnt["n"] / cnt["pid"].map(rows)
    return cnt[cnt["share"] >= 0.9].set_index("pid")["k"]


WTA_PLAYER_RESULTS = WTA / "player_results"     # P2(b): the WTA API's player-matches results (13 Oct 2026, data_gaps_2026)
WTA_SITE_API = {"on": True}                      # --no-wta-player-matches: the wta_site source as built before 13 Oct
# The copy's last ten editions (version 29, 24 Sep 2026: those starting 7-14 Sep 2026) file their 187 singles under the
# wrong editions, ITF W50s under WTA 125 titles among them: the creator's join failed for its newest week. Each match was
# placed by the WTA API's player matches (the WTA's own tournament number) and confirmed by TennisLive or the WTA's own
# draws (docs/studies/p6_data_issues/, 14 Oct 2026). Their listings are left out; the player-matches rows hold the same
# matches under their true events, and the copy held nothing of the 13-14 Sep events themselves. The same list as the
# data map's (measure.WTA_SITE_MISFILED).
WTA_SITE_MISFILED = frozenset({163248187558, 322715938447, 354561979229, 491515815086, 540307471641,   # 7 Sep
                               968402780291, 118580316990, 179051761652, 663626961107, 790501073046})  # 13-14 Sep


def orient_sets(scores, reason) -> tuple[list[tuple[int, int, str | None]], bool]:
    """A score as listed ('2-6  4-6', '7-6(5)  6-3'), turned to the winner's side: ([(winner's games, loser's games,
    tiebreak text)], flipped?). The WTA API's player-matches rows write the score from the listing player's side, who may
    be the loser; the winner is the side with more sets, and a retirement keeps the listed side where the sets tie."""
    toks = re.findall(r"(\d+)-(\d+)(\(\d+\))?", str(scores or ""))
    sets = [(int(a), int(b), t or None) for a, b, t in toks]
    first = sum(1 for a, b, _ in sets if a > b)
    second = sum(1 for a, b, _ in sets if b > a)
    flip = second > first
    return ([(b, a, t) for a, b, t in sets] if flip else sets), flip


def wta_player_rows(t: pd.DataFrame, held: set) -> tuple[pd.DataFrame, dict]:
    """The WTA API's player-matches results (src/ingest/point_sources/wta.py --player-matches, work package P2(b): one row
    per played single, winner and loser named) in load_wta_site's frame. Each row takes its Kaggle edition's pseudo id
    where the tournament group and start date find one (the data map's rule, measure.wta_site_api_rows), else its own
    'api:<group>:<start>'; a match the Kaggle copy holds (`held`: edition, draw and pair of name keys) is kept from the
    copy. Added for the 2026 gaps (docs/studies/data_gaps_2026/): the copy ends with the editions of 7 Sep 2026."""
    paths = sorted(WTA_PLAYER_RESULTS.glob("*.parquet")) if WTA_PLAYER_RESULTS.exists() else []
    if not paths:
        return pd.DataFrame(), {"files": 0}
    a = pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True)
    a["start"] = pd.to_datetime(a["start_date"], errors="coerce")
    a = a[a["start"] >= FIRST_DAY - pd.Timedelta(days=7)].copy()
    stats = {"files": len(paths), "rows": int(len(a))}
    lookup = dict(zip(zip(pd.to_numeric(t["tournamentGroupId"], errors="coerce").astype("Int64").astype(str),
                          t["start"].dt.strftime("%Y-%m-%d")), t["pseudo_tournament_id"]))
    key = list(zip(pd.to_numeric(a["tournament_group_id"], errors="coerce").astype("Int64").astype(str),
                   a["start"].dt.strftime("%Y-%m-%d")))
    a["pseudo_tournament_id"] = [lookup.get(k, f"api:{k[0]}:{k[1]}") for k in key]
    stats["in_a_kaggle_edition"] = int(sum(k in lookup for k in key))
    played = a["reason_code"].astype(str).isin(["W", "R"]) & a["winner_name"].notna() & a["loser_name"].notna()
    a = a[played].copy()
    k1, k2 = a["winner_name"].map(name_key), a["loser_name"].map(name_key)
    lo, hi = np.where(k1 < k2, k1, k2), np.where(k1 < k2, k2, k1)
    a["_key"] = list(zip(a["pseudo_tournament_id"], a["qpm_flag"], lo, hi))
    dup = a["_key"].isin(held)
    stats["held_by_the_kaggle_copy"] = int(dup.sum())
    a = a[~dup].drop_duplicates("_key").copy()
    stats["added"] = int(len(a))
    size = t.set_index("pseudo_tournament_id")["singlesDrawSize"] if "singlesDrawSize" in t else pd.Series(dtype=float)
    rnd = wta_site_rounds(a)
    sets, scores, flipped = [], [], 0
    for s, r in zip(a["scores"], a["reason_code"]):
        wf, fl = orient_sets(s, r)
        flipped += int(fl)
        sets.append(tuple((x, y) for x, y, _ in wf))
        scores.append(" ".join(f"{x}-{y}{t_ or ''}" for x, y, t_ in wf) + (" RET" if r == "R" else ""))
    stats["scores_turned_to_the_winner"] = flipped
    level = a["level"].map(WTA_SITE_LEVEL).where(~a["title"].fillna("").str.contains(_TEAM), "TEAM")
    ids = lambda s: pd.to_numeric(s, errors="coerce").astype("Int64").astype(object).map(  # noqa: E731
        lambda v: None if v is pd.NA or v is None else str(int(v)))
    rows = pd.DataFrame({
        "sid": "wta_site:api:" + a["match_key"].astype(str), "tour": "wta", "season": a["start"].dt.year.to_numpy(),
        "ev_key": "wta_site:" + a["pseudo_tournament_id"].astype(str), "ev_name": a["title"].to_numpy(),
        "ev_date": nearest_monday(a["start"]).to_numpy(), "ev_surface": [surface_of(s) for s in a["surface"]],
        "ev_indoor": a["in_outdoor"].map({"I": True, "O": False}).to_numpy(),
        "ev_country": [ioc(str(c).split(",")[0]) for c in a["country"]], "ev_level": level.to_numpy(),
        "ev_draw": pd.to_numeric(a["pseudo_tournament_id"].map(size), errors="coerce").to_numpy(),
        "qual": a["qpm_flag"].eq("Q").to_numpy(), "rnd": rnd.to_numpy(), "day": pd.NaT, "date_basis": None,
        "p1": a["winner_name"].to_numpy(), "p2": a["loser_name"].to_numpy(),
        "c1": [ioc(c) for c in a["winner_country"]], "c2": [ioc(c) for c in a["loser_country"]],
        "id1": ids(a["winner_id"]).to_numpy(), "id2": ids(a["loser_id"]).to_numpy(), "winner": 1,
        "status_hint": np.where(a["reason_code"].eq("R"), "retired", "completed"), "score": scores, "sets": sets})
    return rows, stats


def load_wta_site() -> tuple[pd.DataFrame, dict]:
    t = pd.read_csv(WTA_SITE / "tournaments.csv", low_memory=False,
                    usecols=["pseudo_tournament_id", "title", "startDate", "surface", "inOutdoor", "country", "level",
                             "singlesDrawSize", "tournamentGroupId"])
    t["start"] = pd.to_datetime(t["startDate"], errors="coerce")
    t = t[t["start"] >= FIRST_DAY - pd.Timedelta(days=7)].drop_duplicates("pseudo_tournament_id")
    allm = pd.read_csv(WTA_SITE / "matches.csv", low_memory=False,
                       usecols=["pseudo_match_id", "pseudo_tournament_id", "player_1", "player_2", "player_3",
                                "player_4", "qpm_flag", "reason_code", "round_name", "tourn_round", "scores", "team_name_1",
                                "team_name_2", "winner"])
    allm = allm[allm["player_3"].isna() & allm["player_4"].isna()].copy()
    for c in ("player_1", "player_2"):
        allm[c] = pd.to_numeric(allm[c], errors="coerce").astype("Int64")      # 'BYE' and blanks -> missing
    own = wta_site_own_names(allm)                                              # over every listing, all years
    m = allm[allm["pseudo_tournament_id"].isin(set(t["pseudo_tournament_id"]))].drop_duplicates("pseudo_match_id")
    stats = {"singles_listed": int(len(m))}
    misfiled = pd.to_numeric(m["pseudo_tournament_id"], errors="coerce").isin(WTA_SITE_MISFILED)
    stats["misfiled_editions_left_out"] = int(misfiled.sum())
    m = m[~misfiled]
    rc = m["reason_code"].fillna("").astype(str)
    walk = rc.isin(["B", "D", "UNP", "V"])
    # a player without a WTA id (a marginal ITF player with no WTA profile, 7% of rows) keeps her name only
    named = m["team_name_1"].fillna("").str.contains(",") & m["team_name_2"].fillna("").str.contains(",")
    ok = rc.isin(["W", "R"]) & m["winner"].isin([1, 2]) & named
    stats.update(byes_walkovers_unplayed=int(walk.sum()), abandoned_or_no_winner_or_name=int((~ok & ~walk).sum()))
    m = m[ok].copy()
    # the ids and the winner are in the listing player's order; the names in draw order (later seasons): align the
    # names to the ids by each id's own name; a row whose ids fit neither order is left out
    k1 = m["team_name_1"].map(lambda s: name_key(wta_site_name(s)[0]))
    k2 = m["team_name_2"].map(lambda s: name_key(wta_site_name(s)[0]))
    o1, o2 = m["player_1"].map(own), m["player_2"].map(own)
    fit_same = (o1.isna() | (o1 == k1)) & (o2.isna() | (o2 == k2)) & (o1.notna() | o2.notna())
    fit_swap = (o1.isna() | (o1 == k2)) & (o2.isna() | (o2 == k1)) & (o1.notna() | o2.notna())
    both_missing = o1.isna() & o2.isna() & m["player_1"].isna() & m["player_2"].isna()
    aligned = (fit_same & ~fit_swap) | both_missing
    swapped = fit_swap & ~fit_same
    stats.update(names_in_listing_order=int(aligned.sum()), names_in_the_other_order=int(swapped.sum()),
                 left_out_ids_and_names_do_not_fit=int((~aligned & ~swapped).sum()),
                 a_player_without_wta_id=int((m["player_1"].isna() | m["player_2"].isna()).sum()))
    m = m[aligned | swapped].copy()
    sw = swapped.loc[m.index].to_numpy()
    tn1 = np.where(sw, m["team_name_2"], m["team_name_1"])
    tn2 = np.where(sw, m["team_name_1"], m["team_name_2"])
    m["name_p1"], m["name_p2"] = tn1, tn2
    m = m.merge(t, on="pseudo_tournament_id", how="left")
    n1, n2 = m["name_p1"].map(wta_site_name), m["name_p2"].map(wta_site_name)
    # the second pseudo id of a match (12% of ITF rows; one copy may lack a player's id): kept once per tournament,
    # draw and pair of names (a pair meets once in a draw), the copy with more ids first
    q1, q2 = n1.str[0].map(name_key), n2.str[0].map(name_key)
    lo, hi = np.where(q1 < q2, q1, q2), np.where(q1 < q2, q2, q1)
    m["_ids"] = m["player_1"].notna().astype(int) + m["player_2"].notna().astype(int)
    m["_key"] = list(zip(m["pseudo_tournament_id"], m["qpm_flag"], lo, hi))
    m["_pos"] = np.arange(len(m))
    keep = m.sort_values(["_ids", "_pos"], ascending=[False, True]).drop_duplicates("_key")["_pos"]
    dup = ~np.isin(m["_pos"].to_numpy(), keep.to_numpy())
    stats["second_pseudo_id_copies"] = int(dup.sum())
    m, n1, n2 = m[~dup].drop(columns=["_ids", "_key", "_pos"]).copy(), n1[~dup], n2[~dup]
    rnd = wta_site_rounds(m)
    win = m["winner"].astype(int).to_numpy()            # 1: player_1 (the listing player) won
    sets = []
    scores = []
    for s, w, r in zip(m["scores"].fillna(""), win, m["reason_code"]):
        toks = [x for x in str(s).replace(",", " ").split() if x]
        wf = []
        for tok in toks:
            mm = re.match(r"^(\d+)-(\d+)(?:\((\d+)\))?$", tok)
            if mm:
                wf.append((int(mm.group(1)), int(mm.group(2))))
        sets.append(tuple(wf if w == 1 else [(b, a) for a, b in wf]))          # p1-first for the linker
        scores.append(" ".join(toks) + (" RET" if r == "R" and "ret" not in str(s).lower() else ""))
    level = m["level"].map(WTA_SITE_LEVEL).where(~m["title"].fillna("").str.contains(_TEAM), "TEAM")
    rows = pd.DataFrame({
        "sid": "wta_site:" + m["pseudo_match_id"].astype(str), "tour": "wta",
        "season": m["start"].dt.year.to_numpy(), "ev_key": "wta_site:" + m["pseudo_tournament_id"].astype(str),
        "ev_name": m["title"].to_numpy(), "ev_date": nearest_monday(m["start"]).to_numpy(),
        "ev_surface": [surface_of(s) for s in m["surface"]],
        "ev_indoor": m["inOutdoor"].map({"I": True, "O": False}).to_numpy(),
        "ev_country": [ioc(str(c).split(",")[0]) for c in m["country"]], "ev_level": level.to_numpy(),
        "ev_draw": pd.to_numeric(m["singlesDrawSize"], errors="coerce").to_numpy(),
        "qual": m["qpm_flag"].eq("Q").to_numpy(), "rnd": rnd.to_numpy(), "day": pd.NaT, "date_basis": None,
        "p1": [x[0] for x in n1], "p2": [x[0] for x in n2], "c1": [x[1] for x in n1], "c2": [x[1] for x in n2],
        "id1": m["player_1"].astype(object).where(m["player_1"].notna(), None).map(
            lambda v: None if v is None else str(int(v))).to_numpy(),
        "id2": m["player_2"].astype(object).where(m["player_2"].notna(), None).map(
            lambda v: None if v is None else str(int(v))).to_numpy(),
        "winner": win, "status_hint": np.where(m["reason_code"].eq("R"), "retired", "completed"),
        "score": scores, "sets": sets})
    stats["played"] = int(len(rows))
    if WTA_SITE_API["on"]:
        held = set(zip(m["pseudo_tournament_id"], m["qpm_flag"], lo[~dup], hi[~dup]))
        api, api_stats = wta_player_rows(t, held)
        stats["wta_api_player_matches"] = api_stats
        if len(api):
            rows = pd.concat([rows, api], ignore_index=True)
            stats["played"] = int(len(rows))
    return finish(rows, "wta_site"), stats


TL_KIND_LEVEL = {"itf": "ITF", "challenger": "CH", "wta125": "CH", "slam": "GS", "finals": "FIN"}
TL_RANK_LEVEL = {"2": "T250", "3": "T1000"}


def tl_sets(text) -> list[tuple[int, int | None]]:
    """'7(7) 3 2' -> [(7, 7), (3, None), (2, None)]."""
    out = []
    for g, t in re.findall(r"(\d+)(?:\((\d+)\))?", str(text or "")):
        out.append((int(g), int(t) if t else None))
    return out


def load_tennislive() -> tuple[pd.DataFrame, dict]:
    li = pd.read_parquet(TL / "listed.parquet",
                         columns=["event_key", "event_name", "event_kind", "event_rank", "tour", "discipline", "junior",
                                  "played", "match_id", "player1_id", "player1_name", "player1_flag", "player2_id",
                                  "player2_name", "player2_flag", "winner_side", "score", "player1_sets",
                                  "player2_sets", "end_reason", "start_utc", "draw", "round", "duration"])
    li = li[li["discipline"].eq("singles") & ~li["junior"].eq("TRUE")].drop_duplicates(["event_key", "match_id"])
    stats = {"singles_listed": int(len(li))}
    walk = li["end_reason"].eq("walkover")
    ok = li["played"].eq("TRUE") & ~walk & li["winner_side"].isin(["1", "2"])
    stats.update(walkovers=int(walk.sum()), unplayed_or_no_winner=int((~ok & ~walk).sum()))
    li = li[ok].copy()
    ev = pd.read_parquet(TL / "events.parquet", columns=["key", "first_week", "surface_code", "country", "rank", "kind",
                                                         "name"]).drop_duplicates("key").set_index("key")
    evk = ev.reindex(li["event_key"])
    w = li["winner_side"].astype(int).to_numpy()
    s1, s2 = li["player1_sets"].map(tl_sets), li["player2_sets"].map(tl_sets)
    pairs, scores = [], []
    for a, b, wi, er in zip(s1, s2, w, li["end_reason"].fillna("")):
        g = tuple((x[0], y[0]) for x, y in zip(a, b))
        pairs.append(g)
        wf = [((x[0], y[0]), (y[1] if x[0] > y[0] else x[1])) if wi == 1 else ((y[0], x[0]), (x[1] if y[0] > x[0] else y[1]))
              for x, y in zip(a, b)]
        tb = [t if {g_[0], g_[1]} == {7, 6} else None for g_, t in wf]
        mark = {"retired": " RET", "disqualified": " DEF"}.get(er, "")
        scores.append(score_text([g_ for g_, _ in wf], tb) + mark)
    kind = li["event_kind"].astype(str)
    level = kind.map(TL_KIND_LEVEL).fillna(li["event_rank"].astype(str).map(TL_RANK_LEVEL))
    played = pd.to_datetime(li["start_utc"].str[:10], format="%Y-%m-%d", errors="coerce")
    monday = pd.to_datetime(evk["first_week"].to_numpy(), format="%Y-%m-%d", errors="coerce")
    played_monday = played - pd.to_timedelta(played.dt.weekday, unit="D")
    # measure.load_tennislive_listed's dating: the event's first catalog week, or the Monday of the week played when
    # that is later (a Slam's or 1000's second week)
    ev_date = pd.Series(monday, index=li.index).where(~(played_monday > pd.Series(monday, index=li.index)), played_monday)
    ev_date = ev_date.fillna(played_monday)
    rows = pd.DataFrame({
        "sid": "tennislive:" + li["event_key"].astype(str) + ":" + li["match_id"].astype(str),
        "tour": li["tour"].map({"atp": "atp", "wta": "wta"}).to_numpy(), "season": ev_date.dt.year.to_numpy(),
        "ev_key": "tennislive:" + li["event_key"].astype(str), "ev_name": li["event_name"].to_numpy(),
        "ev_date": ev_date.to_numpy(), "ev_surface": [surface_of(s) for s in evk["surface_code"].to_numpy()],
        "ev_indoor": None, "ev_country": [ioc(c) for c in evk["country"].to_numpy()], "ev_level": level.to_numpy(),
        "ev_draw": None, "qual": li["draw"].eq("qualifying").to_numpy(),
        "rnd": li["round"].where(li["round"].isin(list(C.ROUND_ORDER)), None).to_numpy(),
        "day": played.to_numpy(), "date_basis": "utc_date",
        "p1": li["player1_name"].to_numpy(), "p2": li["player2_name"].to_numpy(),
        "id1": li["player1_id"].to_numpy(), "id2": li["player2_id"].to_numpy(),
        "c1": [ioc(c) for c in li["player1_flag"]], "c2": [ioc(c) for c in li["player2_flag"]],
        "winner": w, "status_hint": li["end_reason"].map({"retired": "retired", "disqualified": "other"}).fillna(
            "completed").to_numpy(),
        "score": scores, "sets": pairs})
    stats["played"] = int(len(rows))
    return finish(rows, "tennislive"), stats


TL_STATS = {"First serve": "fs", "First serve points won": "fw", "Second serve points won": "sw",
            "Break points converted": "bp", "Total points won": "tp", "Aces": "ace", "Double faults": "df"}


def frac(text) -> tuple[float, float]:
    m = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", str(text or ""))
    return (float(m.group(1)), float(m.group(2))) if m else (np.nan, np.nan)


def load_tennislive_pages() -> tuple[pd.DataFrame, dict]:
    """TennisLive match pages (P5's and P8's, and the earlier careers and samples): box scores only, for matches the
    candidate holds (the listings, P4, give the matches). Eight statistics map to Stage 0's counts: first serves in of
    serve points, first- and second-serve points won, aces, double faults, and break points from the opponent's
    'converted' line (faced = the opponent's chances, saved = those less his conversions); service games are not
    given (Stage 0 keeps such a box score as 'no_svgms'). TennisLive has swapped the two players' statistics (2 of 36
    tour matches checked): a page whose winner took under 45% of the points is not used."""
    m = pd.read_parquet(TL / "matches.parquet")
    m = m[m["doubles"].eq("FALSE") & m["state"].eq("finished") & ~m["end_reason"].fillna("").eq("walkover")]
    s = pd.read_parquet(TL / "statistics.parquet", columns=["url", "period", "name", "player1_value", "player1_detail",
                                                             "player2_value", "player2_detail"])
    s = s[s["period"].eq("match") & s["name"].isin(TL_STATS)]
    stats = {"pages": int(len(m)), "pages_with_statistics": int(s["url"].nunique())}
    w = s.assign(k=s["name"].map(TL_STATS)).drop_duplicates(["url", "k"]).set_index(["url", "k"])
    rows = m[m["url"].isin(set(s["url"]))].copy()
    out = pd.DataFrame(index=rows.index)
    for k in (1, 2):
        def det(stat, side=k):
            v = w[f"player{side}_detail"].xs(stat, level="k") if stat in w.index.get_level_values("k") else pd.Series(
                dtype=object)
            return rows["url"].map(v)

        def val(stat, side=k):
            v = w[f"player{side}_value"].xs(stat, level="k")
            return pd.to_numeric(rows["url"].map(v), errors="coerce")
        o = 2 if k == 1 else 1
        fs = det("fs").map(frac)
        out[f"p{k}_first_in"], out[f"p{k}_svpt"] = fs.str[0], fs.str[1]
        out[f"p{k}_first_won"] = det("fw").map(frac).str[0]
        out[f"p{k}_second_won"] = det("sw").map(frac).str[0]
        out[f"p{k}_ace"], out[f"p{k}_df"] = val("ace"), val("df")
        opp = det("bp", o).map(frac)
        out[f"p{k}_bp_faced"], out[f"p{k}_bp_saved"] = opp.str[1], opp.str[1] - opp.str[0]
        out[f"p{k}_sv_gms"] = np.nan
        out[f"tp{k}"] = det("tp").map(frac).str[0]
    win = np.where(rows["winner_id"].astype(str).eq(rows["player2_id"].astype(str)), 2, 1)
    tp_w = np.where(win == 1, out["tp1"], out["tp2"])
    tp_all = out["tp1"] + out["tp2"]
    swapped = (tp_w / tp_all) < 0.45
    stats["left_out_winner_under_45pct_of_points"] = int(np.nansum(swapped))
    for c in COUNTS:
        for k in (1, 2):
            out.loc[swapped, f"p{k}_{c}"] = np.nan
    sets, scores = [], []
    for st, sw_, wi, er in zip(rows["sets"].fillna(""), rows["set_winners"].fillna(""), win, rows["end_reason"].fillna("")):
        toks = re.findall(r"(\d+)-(\d+)(?:\((\d+)\))?", str(st))
        who = str(sw_).split(";")
        p1f = []
        for i, (a, b, _) in enumerate(toks):
            a, b = int(a), int(b)
            first_won_set = a > b
            p1_won_set = (who[i] == "0") if i < len(who) and who[i] in ("0", "1") else first_won_set
            p1f.append((a, b) if first_won_set == p1_won_set else (b, a))
        sets.append(tuple(p1f))
        wf = [(x, y) if wi == 1 else (y, x) for x, y in p1f]
        scores.append(score_text(wf) + (" RET" if er == "retired" else ""))
    tour = rows["url"].str.extract(r"^/(atp|wta)/", expand=False)
    day = pd.to_datetime(rows["reference_utc"].astype(str).str[:10], format="%Y-%m-%d", errors="coerce")
    rnd = rows["stage"].map(K.round_code)
    R = pd.DataFrame({
        "sid": "tennislive_pages:" + rows["url"].astype(str), "tour": tour.to_numpy(), "season": day.dt.year.to_numpy(),
        "ev_key": ("tennislive:" + tour + ":" + rows["tournament_id"].astype(str)).to_numpy(),
        "ev_name": rows["tournament_name"].to_numpy(), "ev_date": (day - pd.to_timedelta(day.dt.weekday, unit="D"))
        .to_numpy(), "ev_level": None, "qual": rows["stage"].fillna("").str.contains("qualif").to_numpy(),
        "rnd": [r if isinstance(r, str) and r in C.ROUND_ORDER else None for r in rnd], "day": day.to_numpy(),
        "date_basis": "utc_date", "p1": rows["player1_name"].to_numpy(), "p2": rows["player2_name"].to_numpy(),
        "id1": rows["player1_id"].astype(str).to_numpy(), "id2": rows["player2_id"].astype(str).to_numpy(),
        "winner": win, "status_hint": np.where(rows["end_reason"].eq("retired"), "retired", "completed"),
        "score": scores, "sets": sets})
    R = pd.concat([R.reset_index(drop=True), out.drop(columns=["tp1", "tp2"]).reset_index(drop=True)], axis=1)
    R = R[R["tour"].notna()]
    stats["played"] = int(len(R))
    return finish(R, "tennislive_pages"), stats


SOFA_LEVEL = {"Challenger": "CH", "WTA 125": "CH", "ITF Men": "ITF", "ITF Women": "ITF", "ATP": "T250", "WTA": "T250",
              "Davis Cup": "TEAM", "Billie Jean King Cup": "TEAM"}
SOFA_COLLECTIONS = ("sofascore", "sofascore_editions", "sofascore_tournaments")
SOFA_SKIP = {"categories": set()}     # --sofascore-skip: SofaScore categories left out (the P7 day's control build)


def load_sofascore() -> tuple[pd.DataFrame, dict]:
    """SofaScore events of the three collections (sofascore: ten careers; sofascore_editions: P6 and, once staged, P7;
    sofascore_tournaments), finished singles, in the common schema, with the box score where one was fetched
    (data_continuity/sources.sofascore maps it to Stage 0's nine counts). The timeline's own SofaScore linker reads the
    same events (src/eda/match_timing/srcc_sofascore.py). A main-tour SofaScore event that is not a Slam is dated and
    levelled as a 250 until its Stage 0 event says otherwise; main-tour rows are left out in any case."""
    from src.eda.data_continuity import sources as DS
    from src.eda.match_timing import srcc_sofascore as SS
    cols = ["event_id", "start_timestamp", "tournament_name", "unique_tournament_id", "unique_tournament_name",
            "season_year", "category_name", "round_name", "status_type", "status_description", "doubles",
            "winner_code", "home_id", "home_name", "home_country", "away_id", "away_name", "away_country"] + \
        [f"{s}_{x}{k}" for k in range(1, 6) for s in ("home", "away") for x in ("set", "tb")]
    frames = []
    for c in SOFA_COLLECTIONS:
        path = DUMP / "points" / c / "events.parquet"
        if path.exists():
            have = set(pq.read_schema(path).names)
            frames.append(pq.read_table(path, columns=[x for x in cols if x in have]).to_pandas().assign(collection=c))
    ev = pd.concat(frames, ignore_index=True).drop_duplicates("event_id")
    stats = {"events_listed": int(len(ev))}
    ev["tour"] = ev["category_name"].map(SS.TOUR)
    single = ev["doubles"].astype(str).str.upper().eq("FALSE") & ~ev["home_name"].astype(str).str.contains("/") \
        & ~ev["away_name"].astype(str).str.contains("/")
    walk = ev["status_description"].eq("Walkover")
    done = ev["status_description"].isin(["Ended", "Retired"]) & ev["winner_code"].astype(str).isin(["1", "2"])
    stats.update(walkovers=int((single & walk).sum()), not_singles_or_unfinished=int((~(single & done) & ~walk).sum()))
    skip = ev["category_name"].isin(SOFA_SKIP["categories"])
    stats["left_out_by_category_option"] = int((single & done & skip).sum())
    ev = ev[ev["tour"].notna() & single & done & ~skip].copy()
    ev["sid"] = "sofascore:" + ev["event_id"].astype(str)
    box = DS.sofascore()
    box = box[box["source_key"].isin(set(ev["sid"]))]
    w = {}
    for side, k in (("home", 1), ("away", 2)):
        b = box[box["side"].eq(side)].drop_duplicates("source_key").set_index("source_key")
        for c in COUNTS:
            w[f"p{k}_{c}"] = b[c]
    wb = pd.DataFrame(w)
    ts = pd.to_datetime(pd.to_numeric(ev["start_timestamp"], errors="coerce"), unit="s", utc=True)
    rnd = ev["round_name"].map(K.round_code)
    win = pd.to_numeric(ev["winner_code"], errors="coerce").astype(int).to_numpy()
    pairs, scores = [], []
    for (_, r), wi, st in zip(ev.iterrows(), win, ev["status_description"]):
        g, tb = [], []
        for k in range(1, 6):
            a, b = K.int_or_none(r.get(f"home_set{k}")), K.int_or_none(r.get(f"away_set{k}"))
            if a is None or b is None:
                break
            g.append((a, b))
            ta, tb_ = K.int_or_none(r.get(f"home_tb{k}")), K.int_or_none(r.get(f"away_tb{k}"))
            tb.append((ta, tb_))
        pairs.append(tuple(g))
        wf = [((a, b), (t[1] if a > b else t[0])) if wi == 1 else ((b, a), (t[0] if b > a else t[1]))
              for (a, b), t in zip(g, tb)]
        scores.append(score_text([x for x, _ in wf], [t for _, t in wf]) + (" RET" if st == "Retired" else ""))
    qual = np.array([bool(SS.is_qual(t, r)) for t, r in zip(ev["tournament_name"], rnd)])
    slam = ev["unique_tournament_name"].fillna("").str.contains(r"^(?:Australian Open|Roland Garros|Wimbledon|US Open)",
                                                                 regex=True).to_numpy()
    level = np.where(slam, "GS", ev["category_name"].map(SOFA_LEVEL).to_numpy())
    rows = pd.DataFrame({
        "sid": ev["sid"].to_numpy(), "tour": ev["tour"].to_numpy(), "season": ts.dt.year.to_numpy(),
        "ev_key": "sofascore:" + ev["unique_tournament_id"].astype(str) + "_" + ev["season_year"].astype(str).to_numpy(),
        "ev_name": ev["tournament_name"].to_numpy(),
        "ev_date": nearest_monday(ts.dt.tz_convert(None)).to_numpy(), "ev_level": level, "qual": qual,
        "rnd": [r if isinstance(r, str) and r in C.ROUND_ORDER else None for r in rnd],
        "day": ts.dt.tz_convert(None).dt.normalize().to_numpy(), "date_basis": "utc_date", "start_utc": ts.to_numpy(),
        "p1": ev["home_name"].to_numpy(), "p2": ev["away_name"].to_numpy(),
        "id1": ev["home_id"].astype(str).to_numpy(), "id2": ev["away_id"].astype(str).to_numpy(),
        "c1": [ioc(c) for c in ev["home_country"]] if "home_country" in ev else None,
        "c2": [ioc(c) for c in ev["away_country"]] if "away_country" in ev else None,
        "winner": win, "status_hint": np.where(ev["status_description"].eq("Retired"), "retired", "completed"),
        "score": scores, "sets": pairs})
    rows = rows.merge(wb, left_on="sid", right_index=True, how="left")
    stats["played"] = int(len(rows))
    stats["with_box"] = int(rows["sid"].isin(wb.index).sum())
    return finish(rows, "sofascore"), stats


TDI = DUMP / "points" / "tdi"
TDI_LEVEL = {"challenger": "CH", "tour": "T250"}
TDI_ROUND = {"Qualifying Round 1": "Q1", "Qualifying Round 2": "Q2", "Qualifying Round 3": "Q3", "Round of 128": "R128",
             "Round of 96": "R128", "Round of 64": "R64", "Round of 56": "R64", "Round of 48": "R64", "Round of 32": "R32",
             "Round of 28": "R32", "Round of 16": "R16", "Quarterfinal": "QF", "Semifinal": "SF", "Final": "F"}


def tdi_sets(a, b) -> tuple[tuple[int, int], ...]:
    """TDI's per-team strings ('1:6/4 2:4', '1:7/7 2:6': set number, games, the set's tiebreak points) -> games per set,
    team A first."""
    ga = {int(k): int(g) for k, g in re.findall(r"(\d+):(\d+)", str(a or ""))}
    gb = {int(k): int(g) for k, g in re.findall(r"(\d+):(\d+)", str(b or ""))}
    return tuple((ga[k], gb[k]) for k in sorted(ga) if k in gb)


def tdi_split() -> pd.DataFrame:
    """First serves in and points won on each serve, per match and serving team, counted from TDI's point files: a point
    whose serve is FIRST or ACE counts as a first serve in, SECOND as a second serve, DOUBLE FAULT as neither. TDI's ACE
    does not say which serve: an ace on a second serve is counted as a first (measured 13 Oct 2026 against Stage 0's box
    scores on 3,615 shared matches: where the point file is complete, first serves in exact in 84%, mean 0.18 a player
    too many; docs/studies/data_gaps_2026/). `pts` is the point file's serve-point count, for the completeness check."""
    p = pd.read_parquet(TDI / "points.parquet", columns=["match_id", "winner", "team_serving", "serve"])
    p["won"] = p["winner"].eq(p["team_serving"])
    first = p["serve"].isin(["FIRST", "ACE"])
    g = ["match_id", "team_serving"]
    out = pd.DataFrame({"pts": p.groupby(g).size(), "first_in": first.groupby([p[c] for c in g]).sum(),
                        "first_won": (first & p["won"]).groupby([p[c] for c in g]).sum(),
                        "second_won": (p["serve"].eq("SECOND") & p["won"]).groupby([p[c] for c in g]).sum()})
    return out.reset_index()


def load_tdi() -> tuple[pd.DataFrame, dict]:
    """TDI (results.tennisdata.com, the ATP's data company; weekly since 23 Jun 2026): box scores only, for the men's
    Challenger and tour-level matches the candidate holds (added for the 2026 gaps, 13 Oct 2026: Stage 0 has no box score
    for men's Challenger qualifying since June). The published totals give aces, double faults, service games, break
    points faced and saved, and serve points (own service points won + the opponent's return points won; 99.8-100% equal
    to Stage 0's on shared matches, data_continuity). The first-serve split is counted from the point file (tdi_split),
    and only where that file's serve points equal the published total; elsewhere the box score is incomplete and is not
    used."""
    from src.eda.data_continuity import sources as DS
    m = pd.read_parquet(TDI / "matches.parquet", columns=["match_id", "draw_type", "draw", "round", "level", "completed_on",
                                                         "tournament", "tournament_id", "team_a_atp_ids", "team_a_names",
                                                         "team_a_countries", "team_a_scores", "team_b_atp_ids",
                                                         "team_b_names", "team_b_countries", "team_b_scores"])
    m = m[m["draw_type"].eq("singles")].drop_duplicates("match_id").copy()
    stats = {"singles": int(len(m))}
    sets = [tdi_sets(a, b) for a, b in zip(m["team_a_scores"], m["team_b_scores"])]
    won_a = [sum(1 for x, y in s if x > y and x >= 6) for s in sets]
    won_b = [sum(1 for x, y in s if y > x and y >= 6) for s in sets]
    win = np.where(np.array(won_a) > np.array(won_b), 1, np.where(np.array(won_b) > np.array(won_a), 2, 0))
    m["winner"], m["sets"] = win, sets
    stats["no_winner_from_the_sets"] = int((win == 0).sum())
    m = m[m["winner"] > 0].copy()
    pub = DS.tdi()
    pub["match_id"] = pub["source_key"].str.replace("tdi:", "", regex=False)
    split = tdi_split().rename(columns={"team_serving": "team"})
    split["side"] = split["team"].map({"teamA": "team_a", "teamB": "team_b"})
    box = pub.merge(split.drop(columns="team"), on=["match_id", "side"], how="left", suffixes=("", "_pts"))
    complete = pd.to_numeric(box["pts"], errors="coerce").eq(pd.to_numeric(box["svpt"], errors="coerce"))
    for c in ("first_in", "first_won", "second_won"):
        box[c] = pd.to_numeric(box[f"{c}_pts"], errors="coerce").where(complete)
    stats["box_sides_with_a_complete_point_file"] = int(complete.sum())
    stats["box_sides_published"] = int(len(box))
    w = {}
    for side, k in (("team_a", 1), ("team_b", 2)):
        b = box[box["side"].eq(side)].drop_duplicates("match_id").set_index("match_id")
        for c in COUNTS:
            w[f"p{k}_{c}"] = pd.to_numeric(b[c], errors="coerce") if c in b else np.nan
    wb = pd.DataFrame(w)
    day = pd.to_datetime(m["completed_on"], errors="coerce", utc=True).dt.tz_convert(None).dt.normalize()
    rows = pd.DataFrame({
        "sid": "tdi:" + m["match_id"].astype(str), "tour": "atp", "season": day.dt.year.to_numpy(),
        "ev_key": "tdi:" + m["tournament_id"].astype(str).where(m["tournament_id"].notna(), m["tournament"].astype(str)),
        "ev_name": m["tournament"].to_numpy(), "ev_date": nearest_monday(day).to_numpy(),
        "ev_level": m["level"].map(TDI_LEVEL).to_numpy(), "qual": m["draw"].eq("qualifying").to_numpy(),
        "rnd": m["round"].map(TDI_ROUND).to_numpy(), "day": day.to_numpy(), "date_basis": "utc_date",
        "p1": m["team_a_names"].to_numpy(), "p2": m["team_b_names"].to_numpy(),
        "id1": m["team_a_atp_ids"].to_numpy(), "id2": m["team_b_atp_ids"].to_numpy(),
        "c1": [ioc(c) for c in m["team_a_countries"]], "c2": [ioc(c) for c in m["team_b_countries"]],
        "winner": m["winner"].to_numpy(), "status_hint": "completed",
        "score": [score_text([(x, y) if w_ == 1 else (y, x) for x, y in s]) for s, w_ in zip(m["sets"], m["winner"])],
        "sets": m["sets"].to_numpy(), "match_id_tdi": m["match_id"].to_numpy()})
    rows = rows.merge(wb, left_on="match_id_tdi", right_index=True, how="left").drop(columns="match_id_tdi")
    stats["played"] = int(len(rows))
    return finish(rows, "tdi"), stats


LOADERS = {"wta_api": load_wta_api, "itf_live": load_itf_live, "wta_site": load_wta_site, "tennislive": load_tennislive,
           "sofascore": load_sofascore, "tennislive_pages": load_tennislive_pages, "tdi": load_tdi}


# ------------------------------------------------------------------------------------------------ linking
def link_rows(R: pd.DataFrame, S: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series, dict]:
    """srcc_common.link, per tour and season, against Stage 0 (plus additions so far) within 30 days of the rows. An
    undated source row stands on its tournament date (the linker's window is -10 .. +21 days of Stage 0's)."""
    links, reasons, amb = [], [], {}
    for (tour, season), g in R.groupby(["tour", "season"], sort=True):
        day = g["day"].where(g["day"].notna(), g["ev_date"])
        src = pd.DataFrame({"sid": g["sid"].to_numpy(), "tour": tour, "day": day.to_numpy(),
                            "p1": g["p1"].to_numpy(), "p2": g["p2"].to_numpy(), "sets": g["sets"].to_numpy(),
                            "rnd": g["rnd"].to_numpy(), "qual": g["qual"].to_numpy(), "tid": None,
                            "id1": g["id1"].to_numpy(), "id2": g["id2"].to_numpy()})
        lo, hi = day.min() - pd.Timedelta(days=30), day.max() + pd.Timedelta(days=30)
        sl = S[(S["tour"] == tour) & (S["tdate"] >= lo) & (S["tdate"] <= hi)]
        res = K.link(src, sl)
        links.append(res["links"])
        reasons.append(res["reason"])
        amb.update(res["ambiguous"])
        log(f"  linked {tour} {season}: {len(g):,} rows, {len(res['links']):,} in Stage 0 "
            f"({len(sl):,} Stage 0 matches in the window)")
    lk = pd.concat(links, ignore_index=True) if links else pd.DataFrame(columns=K.LINK_COLS)
    reason = pd.concat(reasons) if reasons else pd.Series(dtype=object)
    for c in ("sc",):
        lk[c] = lk[c].astype(bool)
    return lk, reason, amb


EVENT_MIN_LINKS = 3            # confirmed links a source event needs before it is placed in a Stage 0 tournament
TIER = {"GS": "MAIN", "FIN": "MAIN", "T1000": "MAIN", "T500": "MAIN", "T250": "MAIN", "CH": "CH", "ITF": "ITF",
        "TEAM": "TEAM"}


def event_map(R: pd.DataFrame, links: pd.DataFrame, S: pd.DataFrame) -> pd.DataFrame:
    """Each source event -> the Stage 0 tournament (id and date) that holds EVENT_SHARE or more of its confirmed links
    (identical set scores, or the same round), with EVENT_MIN_LINKS of them at least, and of the same tier as the
    source says the event is (ITF, Challenger / WTA 125, main tour, team) where it says: a stray link never moves a
    whole event into another tournament."""
    conf = links[links["sc"] | (links["rd"] == 2)]
    lk = conf[["sid", "match_id"]].merge(R[["sid", "ev_key", "ev_level"]], on="sid").merge(
        S[["match_id", "tournament_id", "tournament_date", "level"]], on="match_id")
    lk = lk[lk["ev_level"].isna() | (lk["ev_level"].map(TIER) == lk["level"].map(TIER))]
    cnt = lk.groupby(["ev_key", "tournament_id", "tournament_date"]).size().rename("n").reset_index()
    cnt["tot"] = cnt.groupby("ev_key")["n"].transform("sum")
    best = cnt[(cnt["n"] >= EVENT_SHARE * cnt["tot"]) & (cnt["n"] >= EVENT_MIN_LINKS)]
    best = best.sort_values(["ev_key", "n"], ascending=[True, False])
    return best.drop_duplicates("ev_key").set_index("ev_key")


def weekly_venue_filter(R: pd.DataFrame, links: pd.DataFrame, evmap: pd.DataFrame, S: pd.DataFrame) -> tuple[
        pd.DataFrame, pd.DataFrame]:
    """A link into another tournament than the row's own mapped event stands only with identical set scores: the
    same round on a plausible day is not enough where a venue holds an event every week (a pair's rematch at the next
    week's Monastir would otherwise be read as the earlier match)."""
    lk = links.merge(R[["sid", "ev_key"]], on="sid", how="left").merge(
        S[["match_id", "tournament_id", "tournament_date"]], on="match_id", how="left")
    tid = lk["ev_key"].astype(object).map(dict(zip(evmap.index, evmap["tournament_id"])))
    tdate = pd.to_datetime(lk["ev_key"].astype(object).map(dict(zip(evmap.index, evmap["tournament_date"]))))
    other = tid.notna() & ((lk["tournament_id"] != tid) | (lk["tournament_date"] != tdate))
    drop = other & ~lk["sc"]
    return links[~drop.to_numpy()].reset_index(drop=True), lk[drop.to_numpy()]


def tour_key(tour: pd.Series, ids: pd.Series) -> pd.Series:
    """A source player id keyed by its tour: TennisLive numbers its ATP and its WTA players separately, so one number
    is two players (role E found men's rows given a woman's id when the key lacked the tour). Missing stays missing."""
    ids = pd.Series(ids, index=tour.index)
    return (tour.astype(str) + "|" + ids.astype(str)).where(ids.notna(), None)


def crosswalk(R: pd.DataFrame, links: pd.DataFrame, S: pd.DataFrame) -> tuple[pd.DataFrame, set, set]:
    """Source player id -> Stage 0 id over every season's links: the Stage 0 id at least XWALK_SHARE of a source id's
    links agree on (srcc_common.crosswalk's rule). Where several source ids claim one Stage 0 id, srcc_common drops them
    all; here a claimant is kept when its name agrees with the Stage 0 player's (name_grade 2 or 3: the WTA API lists
    one player under an old and a new id, Serena Williams 18254 and 230234), and dropped otherwise. Returns the table,
    the source ids whose links disagree (conflicting) and the Stage 0 ids a claimant was refused for (contested)."""
    lk = links[["sid", "match_id", "p1_side"]].merge(R[["sid", "tour", "id1", "id2", "p1", "p2"]], on="sid").merge(
        S[["match_id", "player_a_id", "player_b_id", "name_a", "name_b"]], on="match_id")
    for c in ("id1", "id2"):
        lk[c] = tour_key(lk["tour"], lk[c])
    a1 = lk["p1_side"].eq("A").to_numpy()
    s1 = np.where(a1, lk["player_a_id"], lk["player_b_id"])
    s2 = np.where(a1, lk["player_b_id"], lk["player_a_id"])
    n1 = np.where(a1, lk["name_a"], lk["name_b"])
    n2 = np.where(a1, lk["name_b"], lk["name_a"])
    pairs = pd.DataFrame({"src": np.r_[lk["id1"].to_numpy(), lk["id2"].to_numpy()], "s0": np.r_[s1, s2],
                          "src_name": np.r_[lk["p1"].to_numpy(), lk["p2"].to_numpy()], "s0_name": np.r_[n1, n2]})
    pairs = pairs[pairs["src"].notna()]
    cnt = pairs.groupby(["src", "s0"]).agg(n=("s0", "size"), src_name=("src_name", "first"),
                                           s0_name=("s0_name", "first")).reset_index()
    cnt["tot"] = cnt.groupby("src")["n"].transform("sum")
    best = cnt[cnt["n"] >= XWALK_SHARE * cnt["tot"]].sort_values("n", ascending=False).drop_duplicates("src")
    best["claim"] = "sole"
    # a source id whose links split between Stage 0 ids that all carry its name (Stage 0 holding one player under two
    # ids) takes the id most of its links agree on; a split between different names stays a conflict
    rest = cnt[~cnt["src"].isin(set(best["src"]))].copy()
    if len(rest):
        rest["agree"] = [K.name_grade(a, b) >= 2 for a, b in zip(rest["src_name"], rest["s0_name"])]
        ok_src = rest.groupby("src")["agree"].all()
        top = rest[rest["src"].isin(ok_src.index[ok_src])].sort_values("n", ascending=False).drop_duplicates("src")
        top = top.drop(columns="agree").assign(claim="majority of Stage 0 ids with the same name")
        best = pd.concat([best, top], ignore_index=True)
    claimed = best.groupby("s0")["src"].nunique()
    multi = best["s0"].isin(claimed.index[claimed > 1])
    agree = np.array([K.name_grade(a, b) >= 2 for a, b in zip(best["src_name"], best["s0_name"])], dtype=bool)
    keep = ~multi | agree
    best.loc[multi & agree, "claim"] = best.loc[multi & agree, "claim"] + "; shared, names agree"
    best.loc[~keep, "claim"] = "refused: shared, names differ"
    xw = best[keep].reset_index(drop=True)
    contested = set(best.loc[~keep, "s0"])
    conflicting = (set(cnt["src"]) - set(best["src"])) | set(best.loc[~keep, "src"])
    return xw, conflicting, contested


class Names:
    """Stage 0's players by tour and exact name key (repair_data.name_key), with their countries."""

    def __init__(self, m: pd.DataFrame, mp: pd.DataFrame):
        self.ids: dict = {}
        self.countries: dict = {}
        self.by_last: dict = {}
        self.add(m, mp)

    def add(self, m: pd.DataFrame, mp: pd.DataFrame) -> None:
        tour = mp["match_id"].map(m.set_index("match_id")["tour"])
        t = pd.DataFrame({"tour": tour.to_numpy(), "pid": mp["player_id"].to_numpy(),
                          "key": mp["player_name"].map(name_key).to_numpy(), "c": mp["country"].to_numpy()})
        t = t[t["key"].ne("")]
        u = t.drop_duplicates(["tour", "key", "pid"])
        for (tr, key), g in u.groupby(["tour", "key"]):
            self.ids.setdefault((tr, key), set()).update(g["pid"].tolist())
            self.by_last.setdefault((tr, key.split()[-1]), set()).update((p, key) for p in g["pid"])
        for pid, g in t.dropna(subset=["c"]).groupby("pid"):
            self.countries.setdefault(pid, set()).update(str(x).upper() for x in g["c"].unique())

    def subset(self, tour: str, name, country) -> str | None:
        """The one player of the tour with the same last name word whose name's words contain the source's or are
        contained in them ('Joelle Steur' / 'Joelle Lilly Sophie Steur'), both with two words or more, the country known
        on both sides and equal; None otherwise."""
        key = name_key(name)
        if not key or not country:
            return None
        w = set(key.split())
        if len(w) < 2:
            return None
        hits = {p for p, k in self.by_last.get((tour, key.split()[-1]), set())
                if len(set(k.split())) >= 2 and (w <= set(k.split()) or set(k.split()) <= w)}
        if len(hits) != 1:
            return None
        pid = next(iter(hits))
        return pid if str(country).upper() in self.countries.get(pid, set()) else None

    def unique(self, tour: str, name, country) -> tuple[str | None, bool]:
        """The one player of the tour with this exact name key (None if none or several, or if the countries
        contradict), and whether a country is known on both sides and agrees."""
        ids = self.ids.get((tour, name_key(name)), set())
        if len(ids) != 1:
            return None, False
        pid = next(iter(ids))
        known = self.countries.get(pid, set())
        c = str(country).upper() if country else None
        if c and known and c not in known:
            return None, False
        return pid, bool(c and known and c in known)


MULTI_ID_SOURCES = {"wta_api"}   # sources known to list one player under two id systems (the WTA API's Slam qualifying
                                 # rows carry the Slams' own player ids: 412817 for Lisa Pigato, WTA id 330xxx elsewhere)


def resolve_ids(R: pd.DataFrame, xw: pd.DataFrame, conflicting: set, contested: set, names: Names, tag: str,
                relax: bool = False) -> pd.DataFrame:
    """Each row's two players in Stage 0's id system, and how: crosswalk, name (the one Stage 0 player of the tour with
    the same exact name key and no contradicting country, that no other source id maps to; with ``relax`` (a source in
    MULTI_ID_SOURCES) also one another source id maps to, if the country is known on both sides and equal), new (an id
    in the source's own namespace), or conflict (a source id whose links disagree: its rows are left out). A source id
    never linked to Stage 0 whose name is that of a player another source id of the same source maps to is a namesake,
    not the same person (TennisLive keeps one profile per player), so it takes a new id."""
    m = dict(zip(xw["src"], xw["s0"]))
    mapped_to = set(xw["s0"])
    out = pd.DataFrame(index=R.index)
    for k in (1, 2):
        sid_, name, ctry, tour = R[f"id{k}"], R[f"p{k}"], R[f"c{k}"], R["tour"]
        x = tour_key(tour, sid_).map(m)
        route = pd.Series(np.where(x.notna(), "crosswalk", ""), index=R.index, dtype=object)
        todo = x.isna()
        conf = todo & tour_key(tour, sid_).isin(conflicting)
        route[conf] = "conflict"
        rest = todo & ~conf
        cache: dict = {}
        vals, how = [], []
        for i in R.index[rest]:
            key = (tour[i], sid_[i], name[i], ctry[i])
            if key not in cache:
                pid, same_country = names.unique(tour[i], name[i], ctry[i])
                r = "name"
                if pid is None:
                    # a fuller or shorter spelling of the same name, the country agreeing ('Joelle Steur')
                    pid, same_country, r = names.subset(tour[i], name[i], ctry[i]), True, "name_subset"
                # a source id other than the one mapped to this player is a namesake (strict rule); a row that
                # carries no id at all (the WTA site's id-less opponents) is not
                no_id = sid_[i] is None or (isinstance(sid_[i], float) and np.isnan(sid_[i]))
                if pid is not None and (pid in contested or (pid in mapped_to and not ((relax and same_country)
                                                                                      or no_id))):
                    pid = None
                cache[key] = (pid, r)
            vals.append(cache[key][0])
            how.append(cache[key][1])
        nm = pd.Series(vals, index=R.index[rest], dtype=object)
        hw = pd.Series(how, index=R.index[rest], dtype=object)
        x.loc[nm.index] = nm
        route.loc[nm.index[nm.notna()]] = hw[nm.notna()]
        new = rest & x.isna()
        newid = np.where(sid_[new].notna(), tour[new] + f":{tag}:" + sid_[new].astype(str),
                         tour[new] + f":{tag}name:" + name[new].map(name_key))
        x.loc[new] = newid
        route.loc[new] = "new"
        out[f"x{k}"], out[f"route{k}"] = x, route
    return out


def shared_id_map(xws: dict, ref_players: set) -> dict:
    """A new id one source minted ('<tour>:<tag>:<source id>') -> (the reference player, its name) that the crosswalks
    of the sources sharing its id system (TAGS) map that source id to, where they agree on one reference player.
    (13 Oct 2026, the lower-level feed's hand check: the WTA API runs before the WTA website and both name a new player
    by her WTA id, so a WTA id the API could not link but the website's records link to a Stage 0 player was two
    players: 19 ids in F20261013c.)"""
    rows = [xw[["src", "s0", "s0_name"]].assign(tag=TAGS[src]) for src, xw in xws.items() if len(xw)]
    if not rows:
        return {}
    x = pd.concat(rows, ignore_index=True)
    x = x[x["s0"].isin(ref_players)]
    x = x[x.groupby(["tag", "src"])["s0"].transform("nunique").eq(1)].drop_duplicates(["tag", "src"])
    out = {}
    for tag, k, s0, nm in zip(x["tag"], x["src"], x["s0"], x["s0_name"]):
        tour, _, sid = str(k).partition("|")
        out[f"{tour}:{tag}:{sid}"] = (s0, nm)
    return out


def unify_shared_ids(new_m: list, new_mp: list, new_rows: list, idmap: dict) -> dict:
    """Put the reference player shared_id_map names in place of a minted id, in every source's new matches (their
    tables and rows), where every name the new rows give that id shares a surname word with the reference player's
    (srcc_common.name_grade >= 1), and no match becomes one player against herself. The match ids stay, as the identity
    repair keeps them (repair_data.repair_tables). In place; returns the counts."""
    names: dict = {}
    for N in new_rows:
        for k in (1, 2):
            hit = N[f"x{k}"].isin(idmap)
            for x, p in zip(N.loc[hit, f"x{k}"], N.loc[hit, f"p{k}"]):
                names.setdefault(x, set()).add(p)
    def same_person(p, s0_name) -> bool:
        # a shared surname word, or the same letters ("Dell'Edera" / "Delledera"); in F20261013c the names that failed
        # both were other players: the WTA API lists Slam qualifying under the Slams' own ids, so one number can be two
        # players in the two sources (9 of 21, e.g. 'Vera Pursnani' / 'Gabriela Dabrowski')
        letters = [re.sub(r"[^a-z]", "", name_key(v)) for v in (p, s0_name)]
        return isinstance(p, str) and (K.name_grade(p, s0_name) >= 1 or (letters[0] != "" and letters[0] == letters[1]))
    use = {x: idmap[x][0] for x, ps in names.items() if all(same_person(p, idmap[x][1]) for p in ps)}
    counts = {"minted_ids_a_shared_crosswalk_maps": len(names), "unified_ids": len(use),
              "refused_names_differ": len(names) - len(use), "player_rows": 0, "matches_kept_apart": 0}
    for mn, mpn, N in zip(new_m, new_mp, new_rows):
        if not len(mn):
            continue
        a2, b2 = mn["player_a_id"].map(lambda v: use.get(v, v)), mn["player_b_id"].map(lambda v: use.get(v, v))
        ok = a2.ne(b2)
        counts["matches_kept_apart"] += int((~ok & (a2.ne(mn["player_a_id"]) | b2.ne(mn["player_b_id"]))).sum())
        apart = set(mn.loc[~ok, "match_id"])
        mn["player_a_id"], mn["player_b_id"] = a2.where(ok, mn["player_a_id"]), b2.where(ok, mn["player_b_id"])
        live = ~mpn["match_id"].isin(apart)
        for c in ("player_id", "opponent_id"):
            if c in mpn:
                new = mpn[c].map(lambda v: use.get(v, v))
                ch = live & new.ne(mpn[c])
                if c == "player_id":
                    counts["player_rows"] += int(ch.sum())
                mpn.loc[ch, c] = new[ch]
        rows_live = ~N["match_id"].isin(apart)
        for k in (1, 2):
            new = N[f"x{k}"].map(lambda v: use.get(v, v))
            ch = rows_live & new.ne(N[f"x{k}"])
            N.loc[ch, f"x{k}"] = new[ch]
            N.loc[ch, f"route{k}"] = "shared_crosswalk"
    return counts


# ------------------------------------------------------------------------------------------------ classification
def new_tid(source: str, ev_key: str, season: int, tour: str) -> str:
    short = re.sub(r"[^A-Za-z0-9]+", "-", str(ev_key).split(":", 1)[-1]).strip("-")
    return f"{int(season)}-{'M' if tour == 'atp' else 'W'}-{TAGS.get(source, source).upper()}-{short}"


def event_facts(S: pd.DataFrame, m: pd.DataFrame) -> pd.DataFrame:
    """Per Stage 0 tournament (id, date): name, main level, surface, indoor, draw size (the modes of its rows)."""
    f = m[["tournament_id", "tournament_date", "tournament_name", "level", "qualifying", "surface", "indoor",
           "draw_size"] + (["year"] if "year" in m else [])].copy()
    key = ["tournament_id", "tournament_date"]
    main = f[~f["qualifying"].astype(bool)]
    lv = B.mode_by(main, key, "level").combine_first(B.mode_by(f, key, "level"))
    out = pd.DataFrame({"level": lv})
    out["tournament_name"] = f.groupby(key)["tournament_name"].first()
    out["surface"] = B.mode_by(f, key, "surface")
    out["indoor"] = B.mode_by(f.assign(indoor=f["indoor"].astype("object")), key, "indoor")
    out["draw_size"] = B.mode_by(main, key, "draw_size")
    if "year" in m:
        out["year"] = B.mode_by(f.assign(year=m["year"]), key, "year")
    return out


def classify(R: pd.DataFrame, links: pd.DataFrame, amb: dict, evmap: pd.DataFrame, ids: pd.DataFrame,
             S: pd.DataFrame, facts: pd.DataFrame) -> pd.DataFrame:
    """Per source row: in_stage0 (linked), new, or left out (with why); with the tournament a new row joins."""
    out = R[["sid", "source", "tour", "season", "ev_key", "ev_name", "ev_date", "qual", "rnd"]].copy()
    out = out.join(ids)
    linked = links.drop_duplicates("sid").set_index("sid")["match_id"]
    out["match_id"] = out["sid"].map(linked)
    out["tid"] = out["ev_key"].astype(object).map(dict(zip(evmap.index, evmap["tournament_id"])))
    out["tdate"] = pd.to_datetime(out["ev_key"].astype(object).map(dict(zip(evmap.index, evmap["tournament_date"]))))
    mapped = out["tid"].notna()
    fk = pd.MultiIndex.from_arrays([out["tid"], out["tdate"]])
    lev = pd.Series(facts["level"].reindex(fk).to_numpy(), index=out.index)
    out["level"] = lev.where(mapped, R["ev_level"])
    out["map_level"] = C.map_level(out["level"].fillna("?"), out["qual"].astype(bool))
    out.loc[out["level"].isna(), "map_level"] = None
    lo = np.where(out["x1"] < out["x2"], out["x1"], out["x2"])
    hi = np.where(out["x1"] < out["x2"], out["x2"], out["x1"])
    out["pair"] = pd.Series(lo, index=out.index) + "|" + pd.Series(hi, index=out.index)
    # pair clashes with Stage 0 (and earlier additions): the same pair in the same tournament (mapped event), or
    # within NEW_EVENT_DAYS of the tournament date (an event Stage 0 lacks)
    s_lo = np.where(S["player_a_id"] < S["player_b_id"], S["player_a_id"], S["player_b_id"])
    s_hi = np.where(S["player_a_id"] < S["player_b_id"], S["player_b_id"], S["player_a_id"])
    sp = pd.DataFrame({"tour": S["tour"].to_numpy(), "pair": pd.Series(s_lo) + "|" + pd.Series(s_hi),
                       "s_tid": S["tournament_id"].to_numpy(), "s_tdate": S["tdate"].to_numpy(),
                       "s_round": S["round"].to_numpy()})
    todo = out[out["match_id"].isna() & out["x1"].notna() & out["x2"].notna()]
    j = todo[["sid", "tour", "pair", "tid", "tdate", "ev_date"]].merge(sp, on=["tour", "pair"])
    same_event = (j["tid"].notna() & (j["s_tid"] == j["tid"]) & (pd.to_datetime(j["s_tdate"]) == pd.to_datetime(j["tdate"])))
    near = j["tid"].isna() & ((pd.to_datetime(j["s_tdate"]) - pd.to_datetime(j["ev_date"])).dt.days.abs() <= NEW_EVENT_DAYS)
    pair_clash = set(j.loc[same_event | near, "sid"])
    # a player plays once per round of a tournament (outside round robins): a mapped row whose player already has a
    # Stage 0 match in that tournament's round repeats it under another opponent
    tm = todo[todo["tid"].notna()]
    round_clash: set = set()
    if len(tm):
        keys = ["pid", "s_tid", "s_day", "rnd"]
        sday = (S["tdate"] - EPOCH).dt.days.to_numpy()
        sr = pd.concat([pd.DataFrame({"pid": S["player_a_id"].to_numpy(), "s_tid": S["tournament_id"].to_numpy(),
                                      "s_day": sday, "rnd": S["round"].to_numpy()}),
                        pd.DataFrame({"pid": S["player_b_id"].to_numpy(), "s_tid": S["tournament_id"].to_numpy(),
                                      "s_day": sday, "rnd": S["round"].to_numpy()})])
        sr = sr[sr["rnd"].ne("RR") & sr["s_tid"].isin(set(tm["tid"]))].drop_duplicates()
        tday = (pd.to_datetime(tm["tdate"]) - EPOCH).dt.days.to_numpy()
        for side in ("x1", "x2"):
            q = pd.DataFrame({"sid": tm["sid"].to_numpy(), "pid": tm[side].to_numpy(), "s_tid": tm["tid"].to_numpy(),
                              "s_day": tday, "rnd": tm["rnd"].to_numpy()})
            round_clash |= set(q.merge(sr, on=keys)["sid"])
    why = pd.Series("", index=out.index, dtype=object)
    lk = out["match_id"].notna()
    why[lk] = "in_stage0"
    rest = ~lk
    why[rest & out["sid"].isin(set(amb))] = "left_out: ambiguous (equally good Stage 0 matches)"
    conf = rest & (out["route1"].eq("conflict") | out["route2"].eq("conflict"))
    why[conf & why.eq("")] = "left_out: a player's source id links to several Stage 0 players"
    why[rest & why.eq("") & out["sid"].isin(pair_clash)] = "left_out: the same pair already in Stage 0 at this event " \
                                                           "(unconfirmed duplicate)"
    why[rest & why.eq("") & out["sid"].isin(round_clash)] = "left_out: a player already plays this round of the event"
    why[rest & why.eq("") & out["map_level"].isna()] = "left_out: level unknown"
    why[rest & why.eq("") & ~out["map_level"].isin(LOWER_MAP)] = "left_out: main tour or team (not lower-level data)"
    why[rest & why.eq("") & ~out["rnd"].isin(list(C.ROUND_ORDER))] = "left_out: round unknown (cannot be ordered)"
    why[rest & why.eq("")] = "new"
    out["why"] = why
    # duplicates among the new rows themselves: one per tournament, round and pair; a player twice in one round of one
    # tournament: all such rows left out
    new = out["why"].eq("new")
    short = out["ev_key"].astype(str).str.split(":", n=1).str[-1].str.replace(r"[^A-Za-z0-9]+", "-", regex=True) \
        .str.strip("-")
    made = (out["season"].astype("int64").astype(str) + "-" + np.where(out["tour"].eq("atp"), "M", "W") + "-"
            + out["source"].map(lambda s: TAGS.get(s, s).upper()) + "-" + short)
    ev_id = out["tid"].where(mapped, made)
    ev_dt = out["tdate"].where(mapped, out["ev_date"])
    out["event_tid"], out["event_date"] = ev_id, pd.to_datetime(ev_dt)
    key = out["tour"] + "|" + out["event_tid"].astype(str) + "|" + out["event_date"].astype(str) + "|" + \
        out["rnd"].astype(str)
    dup = new & (key + "|" + out["pair"]).duplicated(keep="first")
    out.loc[dup, "why"] = "left_out: listed twice in the source (same tournament, round and pair)"
    new = out["why"].eq("new")
    pl = pd.concat([pd.DataFrame({"i": out.index[new], "k": (key + "|" + out["x1"])[new]}),
                    pd.DataFrame({"i": out.index[new], "k": (key + "|" + out["x2"])[new]})])
    twice = set(pl.loc[pl["k"].duplicated(keep=False) & ~pl["k"].str.contains(r"\|RR\|"), "i"])
    out.loc[list(twice), "why"] = "left_out: a player twice in one round of one tournament (in the source)"
    return out


# ------------------------------------------------------------------------------------------------ Stage 0 rows
def assemble_new(R: pd.DataFrame, cls: pd.DataFrame, facts: pd.DataFrame) -> pd.DataFrame:
    """The new rows with everything Stage 0 needs: the tournament they join (a Stage 0 tournament's own name, surface,
    indoor and draw size; else the source's), the level, the resolved players."""
    keep = cls["why"].eq("new").to_numpy()
    N = R[keep].copy()
    c = cls[keep]
    for col in ("x1", "x2", "route1", "route2", "level", "map_level", "event_tid", "event_date", "tid"):
        N[col] = c[col].to_numpy()
    mapped = N["tid"].notna().to_numpy()
    fk = pd.MultiIndex.from_arrays([N["event_tid"], pd.to_datetime(N["event_date"])])
    f = facts.reindex(fk)
    N["tname"] = np.where(mapped, f["tournament_name"].to_numpy(), N["ev_name"].to_numpy())
    N["surface"] = np.where(mapped & f["surface"].notna().to_numpy(), f["surface"].to_numpy(),
                            N["ev_surface"].to_numpy())
    N["indoor"] = pd.Series(f["indoor"].to_numpy(), index=N.index).where(mapped, N["ev_indoor"])
    N["draw_size"] = pd.Series(f["draw_size"].to_numpy(), index=N.index).where(mapped, N["ev_draw"])
    if "year" in f:      # a row joining a Stage 0 tournament takes that tournament's season
        yr = pd.to_numeric(pd.Series(f["year"].to_numpy(), index=N.index), errors="coerce")
        N["season"] = yr.where(mapped & yr.notna(), N["season"]).astype("int64")
    return N.reset_index(drop=True)


def fmt(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return ""
    return str(int(round(f))) if np.isfinite(f) else ""


def build_rows(N: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stage 0's two tables for new matches, through stage0_build's own steps (normalise, the score's status, format and
    counts, the box checks B0-B9, the player rows and rates), with the level and the players already resolved."""
    if N.empty:
        return pd.DataFrame(), pd.DataFrame()
    N = N.reset_index(drop=True)
    w1 = N["winner"].astype(int).eq(1).to_numpy()

    def pick(a, b):
        return np.where(w1, N[a].to_numpy(dtype=object), N[b].to_numpy(dtype=object))

    def blank(v) -> bool:
        return v is None or v is pd.NA or v is pd.NaT or (isinstance(v, float) and np.isnan(v))

    def text(v):
        return "" if blank(v) else str(v)

    def io(v):
        if blank(v):
            return ""
        return "I" if bool(v) else "O"
    raw = pd.DataFrame({
        "tourney_id": N["event_tid"].astype(str).to_numpy(), "tourney_name": N["tname"].map(text).to_numpy(),
        "surface": N["surface"].map(text).to_numpy(),
        "draw_size": N["draw_size"].map(fmt).to_numpy() if "draw_size" in N else "",
        "tourney_level": "", "tourney_date": pd.to_datetime(N["event_date"]).dt.strftime("%Y%m%d").to_numpy(),
        "match_num": "", "score": N["score"].map(text).to_numpy(),
        "best_of": N["best_of"].map(fmt).to_numpy() if "best_of" in N else "3",
        "round": N["rnd"].astype(str).to_numpy(), "minutes": N["minutes"].map(fmt).to_numpy(),
        "indoor": N["indoor"].astype(object).map(io).to_numpy(),
        "_source_file": N["sid"].to_numpy(), "_row": np.arange(len(N)),
        "winner_id": pick("x1", "x2"), "winner_name": pick("p1", "p2"), "winner_ioc": pick("c1", "c2"),
        "loser_id": pick("x2", "x1"), "loser_name": pick("p2", "p1"), "loser_ioc": pick("c2", "c1")})
    raw["best_of"] = raw["best_of"].replace("", "3")
    for b in ("seed", "entry", "hand", "ht", "age", "rank", "rank_points"):
        for side in ("winner", "loser"):
            raw[f"{side}_{b}"] = ""
    for c in COUNTS:
        src = SRC_NAMES[c]
        raw[f"w_{src}"] = pd.Series(np.where(w1, N[f"p1_{c}"], N[f"p2_{c}"])).map(fmt).to_numpy()
        raw[f"l_{src}"] = pd.Series(np.where(w1, N[f"p2_{c}"], N[f"p1_{c}"])).map(fmt).to_numpy()
    raw["source"], raw["group"], raw["tour"] = N["source"].to_numpy(), N["source"].to_numpy(), N["tour"].to_numpy()
    raw["file_season"] = N["season"].astype("int64").to_numpy()
    raw["rid"] = np.arange(len(raw), dtype="int64")
    for c in ("winner_ioc", "loser_ioc", "winner_name", "loser_name", "winner_id", "loser_id"):
        raw[c] = raw[c].map(text)
    df = B.normalise(raw)
    want = pd.Series(N["event_tid"].astype(str).to_numpy()).str.replace(r"-0+(\d)", r"-\1", regex=True)
    if not (df["tid"].to_numpy() == want.to_numpy()).all():
        raise AssertionError("tournament ids changed under normalise")
    df = B.parse_scores(df)
    df["level"] = N["level"].to_numpy()
    df["pid_w"], df["pid_l"] = df["winner_id"], df["loser_id"]
    same = df["pid_w"].eq(df["pid_l"])
    if same.any():
        raise AssertionError(f"{int(same.sum())} new rows resolve both players to one id")
    lo = np.where(df["pid_w"] < df["pid_l"], df["pid_w"], df["pid_l"])
    hi = np.where(df["pid_w"] < df["pid_l"], df["pid_l"], df["pid_w"])
    df["pid_lo"], df["pid_hi"] = lo, hi
    df["match_id"] = df["tour"] + "|" + df["tid"] + "|" + df["round"] + "|" + lo + "|" + hi
    df["year"] = df["season"].astype("int64")
    # each event's format, then the counts read from the score (stage0_build.build, unchanged)
    comp = df["status"].eq("completed")
    toks = df["score"].map(lambda s: B.tokens_of(s)[0])
    df["_short"] = toks.map(B.short_like)
    df["_bracket"] = toks.map(lambda t: any(br for *_, br in t))
    bo = B.num(df["best_of"])
    decider = comp & (toks.map(len) == bo)
    ev_key = ["tour", "tid"]
    short_share = df[comp].groupby(ev_key)["_short"].mean()
    mtb_share = df[decider].groupby(ev_key)["_bracket"].mean()
    df["short_event"] = B.lookup(short_share, df, ev_key).fillna(0).ge(0.5)
    df["mtb_event"] = B.lookup(mtb_share, df, ev_key).fillna(0).ge(0.5)
    df = B.score_columns(df)
    df["format"] = np.select([df["short_event"] | (df["short_like"] & comp), df["mtb_event"] | df["has_bracket"]],
                             ["short_sets", "match_tiebreak"], "standard")
    df["nonstandard_format"] = df["format"].ne("standard")
    need = (bo // 2 + 1).fillna(2)
    normal = comp & (df["sets_w"] >= need)
    rev = comp & ~normal & (df["sets_l"] >= need) & (df["sets_l"] > df["sets_w"])
    unmarked = comp & ~normal & ~rev & ~df["last_done"]
    bestof = comp & ~normal & ~rev & df["last_done"] & (df["sets_w"] > df["sets_l"])
    odd = comp & ~(normal | rev | unmarked | bestof)
    for a, b in (("sets_w", "sets_l"), ("games_w", "games_l"), ("tb_w", "tb_l")):
        df.loc[rev, [a, b]] = df.loc[rev, [b, a]].to_numpy()
    df.loc[unmarked, "status"], df.loc[unmarked, "status_detail"] = "retired", "retired_unmarked"
    df["score_ok"] = df["status"].isin(["completed", "retired", "other"]) & df["status_detail"].ne("unknown") & ~odd
    df["score_flag"] = np.select([rev, unmarked, bestof, odd],
                                 ["read_reversed", "retirement_unmarked", "short_of_best_of", "inconsistent"], "")
    df = B.box_scores(df)
    minutes = B.num(df["minutes"])
    df["minutes_clean"] = minutes.where(minutes > 0)
    df["round_order"] = df["round"].map(C.ROUND_ORDER).astype("int64")
    df["evaluation"] = (df["level"].isin(C.EVAL_LEVELS) & df["year"].ge(C.EVAL_YEARS[0])      # no last season
                        & df["status"].isin(C.EVAL_STATUSES))                                 # (since 10 Oct 2026)
    low_a = df["match_id"].map(C.side_is_low)
    df["player_a_id"] = np.where(low_a, df["pid_lo"], df["pid_hi"])
    df["player_b_id"] = np.where(low_a, df["pid_hi"], df["pid_lo"])
    df["a_won"] = df["player_a_id"].eq(df["pid_w"])
    m = pd.DataFrame({
        "match_id": df["match_id"], "tour": df["tour"], "year": df["year"], "era": C.era_of(df["year"]),
        "level": df["level"], "qualifying": df["qualifying"].astype(bool), "evaluation": df["evaluation"],
        "round": df["round"], "round_order": df["round_order"], "match_num": df["match_num"], "surface": df["surface"],
        "indoor": df["indoor_flag"].astype("boolean"), "best_of": B.num(df["best_of"]).astype("Int64"),
        "draw_size": B.num(df["draw_size"]).astype("Int64"), "tournament_id": df["tid"],
        "tournament_name": df["tourney_name"], "tournament_date": df["tdate"], "status": df["status"],
        "status_detail": df["status_detail"], "score": df["score"], "score_flag": df["score_flag"],
        "minutes": df["minutes_clean"], "format": df["format"], "nonstandard_format": df["nonstandard_format"],
        "has_box": df["has_box"], "box_status": df["box_status"], "sv_gms_incl_tb": df["sv_gms_incl_tb"],
        "player_a_id": df["player_a_id"], "player_b_id": df["player_b_id"], "a_won": df["a_won"],
        "source": df["source"], "tml_link": "none", "source_file": df["_source_file"],
        "source_row": df["_row"].astype("int64")})
    m["map_level"] = C.map_level(m["level"], m["qualifying"])
    mp = pd.concat([B.player_columns(df, "w", "l"), B.player_columns(df, "l", "w")], ignore_index=True)
    a_of = m.set_index("match_id")["player_a_id"]
    mp["side"] = np.where(mp["player_id"].eq(mp["match_id"].map(a_of)), "A", "B")
    first = ["match_id", "player_id", "opponent_id", "side", "won"]
    mp = mp[first + [c for c in mp.columns if c not in first]].reset_index(drop=True)
    return m.reset_index(drop=True), mp


def conform(t: pd.DataFrame, like: pd.DataFrame) -> pd.DataFrame:
    """Columns and dtypes of the frozen table."""
    t = t.reindex(columns=like.columns).copy()
    for c, d in like.dtypes.items():
        if str(t[c].dtype) == str(d):
            continue
        if str(d).startswith("datetime64"):
            t[c] = pd.to_datetime(t[c]).astype(d)
        elif str(d) in ("str", "string", "object"):
            t[c] = t[c].astype(object).where(t[c].notna(), None).astype(d)
        else:
            t[c] = t[c].astype(d)
    return t


# ------------------------------------------------------------------------------------------------ box layers
BOX_RATES = [f"{s}_{v}" for s in C.RATES if s not in ("tb_won", "sets_won", "games_won") for v in ("n", "d")]


def box_candidates(R: pd.DataFrame, links: pd.DataFrame, m: pd.DataFrame, mp: pd.DataFrame, ref_ids: set
                   ) -> pd.DataFrame:
    """Linked source rows with a box score, on reference matches of the lower levels: per match the source's counts on
    Stage 0's sides, Stage 0's own, and the kind: completion (Stage 0 holds a result only), revision (a different box
    score) or identical."""
    if links.empty or not R["has_src_box"].any():
        return pd.DataFrame()
    lk = links[links["match_id"].isin(ref_ids)][["sid", "match_id", "p1_side"]].drop_duplicates("match_id")
    lk = lk.merge(R[R["has_src_box"]][["sid", "source"] + [f"p{k}_{c}" for k in (1, 2) for c in COUNTS]], on="sid")
    mm = m.set_index("match_id")
    lk = lk[lk["match_id"].map(mm["map_level"]).isin(LOWER_MAP).to_numpy()
            & lk["match_id"].map(mm["status"]).isin(["completed", "retired"]).to_numpy()]
    if lk.empty:
        return pd.DataFrame()
    a1 = lk["p1_side"].eq("A").to_numpy()
    for c in COUNTS:
        lk[f"new_A_{c}"] = np.where(a1, lk[f"p1_{c}"], lk[f"p2_{c}"])
        lk[f"new_B_{c}"] = np.where(a1, lk[f"p2_{c}"], lk[f"p1_{c}"])
    pm = mp[mp["match_id"].isin(set(lk["match_id"]))].set_index(["match_id", "side"])
    for side in ("A", "B"):
        idx = pd.MultiIndex.from_arrays([lk["match_id"], np.repeat(side, len(lk))])
        for c in COUNTS:
            lk[f"old_{side}_{c}"] = pm[c].reindex(idx).to_numpy()
    lk["stage0_has_box"] = lk["match_id"].map(mm["has_box"]).astype(bool).to_numpy()
    new = lk[[f"new_{s}_{c}" for s in "AB" for c in COUNTS]].to_numpy(dtype=float)
    old = lk[[f"old_{s}_{c}" for s in "AB" for c in COUNTS]].to_numpy(dtype=float)
    same = np.all((new == old) | (np.isnan(new) & np.isnan(old)), axis=1)
    lk["kind"] = np.where(~lk["stage0_has_box"], "completion", np.where(same, "identical", "revision"))
    keep = ["match_id", "sid", "source", "kind", "stage0_has_box"] + [f"{a}_{s}_{c}" for a in ("old", "new")
                                                                     for s in "AB" for c in COUNTS]
    return lk[keep].reset_index(drop=True)


def box_rebuild(cand: pd.DataFrame, m: pd.DataFrame, mp: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The reference matches rebuilt through build_rows with the source's box score and Stage 0's own facts; only the
    box columns of the result are used (has_box, box_status, sv_gms_incl_tb; the nine counts and the box rates)."""
    mm = m.set_index("match_id").loc[cand["match_id"]].reset_index()
    names = mp.set_index(["match_id", "side"])["player_name"]
    ctry = mp.set_index(["match_id", "side"])["country"]
    a_won = mm["a_won"].astype(bool).to_numpy()
    wside, lside = np.where(a_won, "A", "B"), np.where(a_won, "B", "A")
    N = pd.DataFrame({
        "sid": cand["sid"].to_numpy(), "source": cand["source"].to_numpy(), "tour": mm["tour"].to_numpy(),
        "season": mm["year"].to_numpy(), "event_tid": mm["tournament_id"].to_numpy(),
        "event_date": mm["tournament_date"].to_numpy(), "tname": mm["tournament_name"].to_numpy(),
        "level": mm["level"].to_numpy(), "rnd": mm["round"].to_numpy(), "surface": mm["surface"].to_numpy(),
        "indoor": mm["indoor"].astype(object).to_numpy(), "best_of": mm["best_of"].astype(object).to_numpy(),
        "draw_size": mm["draw_size"].astype(object).to_numpy(), "score": mm["score"].to_numpy(),
        "minutes": mm["minutes"].to_numpy(), "winner": 1,
        "x1": np.where(a_won, mm["player_a_id"], mm["player_b_id"]),
        "x2": np.where(a_won, mm["player_b_id"], mm["player_a_id"]),
        "p1": names.reindex(pd.MultiIndex.from_arrays([mm["match_id"], wside])).to_numpy(),
        "p2": names.reindex(pd.MultiIndex.from_arrays([mm["match_id"], lside])).to_numpy(),
        "c1": ctry.reindex(pd.MultiIndex.from_arrays([mm["match_id"], wside])).to_numpy(),
        "c2": ctry.reindex(pd.MultiIndex.from_arrays([mm["match_id"], lside])).to_numpy()})
    for c in COUNTS:
        N[f"p1_{c}"] = np.where(a_won, cand[f"new_A_{c}"], cand[f"new_B_{c}"])
        N[f"p2_{c}"] = np.where(a_won, cand[f"new_B_{c}"], cand[f"new_A_{c}"])
    bm, bmp = build_rows(N)
    # a match id is a stable handle: about 300 reference ids keep a player id the identity repairs later changed, so
    # the rebuilt id is mapped back by position (build_rows keeps the rows' order)
    if len(bm) != len(cand):
        raise AssertionError("box rebuild: rows lost")
    back = dict(zip(bm["match_id"], cand["match_id"]))
    if len(back) != len(cand):
        raise AssertionError("box rebuild: two matches rebuilt under one id")
    bm["match_id"] = cand["match_id"].to_numpy()
    bmp["match_id"] = bmp["match_id"].map(back)
    pairs = set(zip(mp["match_id"], mp["player_id"]))
    if not all(k in pairs for k in zip(bmp["match_id"], bmp["player_id"])):
        raise AssertionError("box rebuild: player rows do not match the candidate's")
    return bm, bmp


def apply_box(m: pd.DataFrame, mp: pd.DataFrame, bm: pd.DataFrame, bmp: pd.DataFrame, ids: set) -> tuple[
        pd.DataFrame, pd.DataFrame, set]:
    """Write the rebuilt box columns of the given reference matches (those that pass Stage 0's checks) into the tables;
    every other column, the match's facts included, stays the reference's. Returns the matches written."""
    ok = bm[bm["match_id"].isin(ids) & bm["has_box"].astype(bool)]
    done = set(ok["match_id"])
    sel = m["match_id"].isin(done)
    src = ok.set_index("match_id")
    for c in ("has_box", "box_status", "sv_gms_incl_tb"):
        m.loc[sel, c] = m.loc[sel, "match_id"].map(src[c]).astype(m[c].dtype).to_numpy()
    selp = mp["match_id"].isin(done)
    sp = bmp[bmp["match_id"].isin(done)].set_index(["match_id", "player_id"])
    key = pd.MultiIndex.from_arrays([mp.loc[selp, "match_id"], mp.loc[selp, "player_id"]])
    for c in COUNTS + ["has_box"] + BOX_RATES:
        mp.loc[selp, c] = sp[c].reindex(key).astype(mp[c].dtype).to_numpy()
    return m, mp, done


# ------------------------------------------------------------------------------------------------ the timeline
CAL_COVER, CAL_DROP, CAL_MIN = 0.999, 7, 200     # timing.py's calibration constants
DEFAULT_SLACK = (1, 1)                            # timing.py's slack for a source class with no calibration


def source_clock(R: pd.DataFrame, links: pd.DataFrame, ref_timing: pd.DataFrame) -> dict:
    """A source's clock error against the frozen timeline's exact days, as timing.calibrate measures a source class:
    on the source's rows linked to exactly dated reference matches, the days to add before and after the source's day
    (UTC days count as the day before or after already) so that CAL_COVER of the reference days fall inside;
    differences beyond CAL_DROP days are mislinks. DEFAULT_SLACK where fewer than CAL_MIN rows overlap."""
    lk = links[["sid", "match_id"]].merge(R[["sid", "day", "date_basis"]], on="sid")
    lk = lk[lk["day"].notna()].merge(ref_timing[["match_id", "exact", "obs"]], on="match_id")
    lk = lk[lk["exact"].astype(bool)]
    if lk.empty:
        return {"overlaps": 0, "before": DEFAULT_SLACK[0], "after": DEFAULT_SLACK[1], "basis": "default"}
    d = MT.to_day(lk["day"])
    u = np.where(lk["date_basis"].eq("local"), 0, 1)
    diff = d - lk["obs"].to_numpy(dtype=float)
    keep = np.abs(diff) <= CAL_DROP
    if keep.sum() < CAL_MIN:
        return {"overlaps": int(keep.sum()), "before": DEFAULT_SLACK[0], "after": DEFAULT_SLACK[1], "basis": "default"}
    need_before = (diff - u)[keep]           # the true day may lie this far before the source's claimed lower bound
    need_after = (-diff - u)[keep]
    before = max(0, int(np.ceil(np.quantile(need_before, CAL_COVER))))
    after = max(0, int(np.ceil(np.quantile(need_after, CAL_COVER))))
    inside = ((need_before <= before) & (need_after <= after)).mean()
    return {"overlaps": int(keep.sum()), "before": before, "after": after, "basis": "calibrated",
            "share_same_day": float((np.abs(diff[keep]) < 0.5).mean()), "share_inside": float(inside),
            "mislinks_dropped": int((~keep).sum())}


def timeline(new_m: pd.DataFrame, R_new: pd.DataFrame, clocks: dict) -> pd.DataFrame:
    """Timeline rows for the new matches in match_timing's schema. A day the source gives (plausible: -10 .. +21 days of
    the tournament date, and within two days of the class window) is the claimed interval widened by the source's
    measured clock error; otherwise, or for a source with no day, the frozen timeline's window for the match's class
    (tour, level, phase, round, era; pooled over eras, else timing.py's default) joined with the researched schedule
    rules (timing.rule_windows), measured from the anchor Monday. No draw narrowing (it only narrows; leaving it out is
    the cautious side)."""
    from src.eda.match_timing import timing as TM
    t = new_m[["match_id", "tour", "year", "level", "qualifying", "round", "round_order", "tournament_id",
               "tournament_name", "tournament_date"]].reset_index(drop=True).copy()
    t["start"] = MT.to_day(t["tournament_date"])
    t["anchor"] = TM.anchor_day(t)
    t["phase"] = np.where(t["qualifying"].astype(bool), "qual", "main")
    t["era"] = TM.era_of(t["year"]).to_numpy()
    cls = pd.read_csv(REF_CLASSES)
    fine = cls.set_index(["tour", "level", "phase", "round", "era"])[["lo", "hi", "median", "basis"]]
    coarse = cls.groupby(["tour", "level", "phase", "round"]).agg(lo=("lo", "min"), hi=("hi", "max"),
                                                                    median=("median", "median"))
    k5 = pd.MultiIndex.from_frame(t[["tour", "level", "phase", "round", "era"]])
    k4 = pd.MultiIndex.from_frame(t[["tour", "level", "phase", "round"]])
    f, c = fine.reindex(k5), coarse.reindex(k4)
    lg = TM.level_group(t["level"]).to_numpy()
    dlo = np.array([TM.DEFAULTS[(p, g)][0] for p, g in zip(t["phase"], lg)], dtype=float)
    dhi = np.array([TM.DEFAULTS[(p, g)][1] for p, g in zip(t["phase"], lg)], dtype=float)
    lo = np.where(np.isfinite(f["lo"].to_numpy(dtype=float)), f["lo"], np.where(np.isfinite(c["lo"].to_numpy(dtype=float)), c["lo"], dlo))
    hi = np.where(np.isfinite(f["hi"].to_numpy(dtype=float)), f["hi"], np.where(np.isfinite(c["hi"].to_numpy(dtype=float)), c["hi"], dhi))
    med = np.where(np.isfinite(f["median"].to_numpy(dtype=float)), f["median"],
                   np.where(np.isfinite(c["median"].to_numpy(dtype=float)), c["median"], (dlo + dhi) / 2))
    emp = np.isfinite(f["lo"].to_numpy(dtype=float)) | np.isfinite(c["lo"].to_numpy(dtype=float))
    rlo, rhi, named = TM.rule_windows(t)
    has_rule = np.isfinite(rlo) & np.isfinite(rhi)
    lo = np.where(named & has_rule, rlo, np.where(emp, np.fmin(lo, rlo), np.where(has_rule, rlo, lo)))
    hi = np.where(named & has_rule, rhi, np.where(emp, np.fmax(hi, rhi), np.where(has_rule, rhi, hi)))
    med = np.where(named & has_rule, (rlo + rhi) / 2, med)
    basis = np.select([named & has_rule, emp & has_rule, emp, has_rule], ["named_rule", "empirical+rule", "empirical",
                                                                           "rule"], "default")
    es_c, lf_c = t["anchor"].to_numpy() + lo, t["anchor"].to_numpy() + hi
    r = R_new.set_index("match_id").reindex(t["match_id"])
    # a row that joined a Stage 0 tournament dated otherwise than the source dates its event (a weekly venue's event a
    # week apart in the two records, e.g. Antalya 14 of 2018): the class window from both dates, joined, so that the
    # true days lie inside whichever record is right
    if "ev_date" in r:
        own = t.assign(tournament_date=pd.to_datetime(r["ev_date"].to_numpy()))
        own_anchor = TM.anchor_day(own)
        differs = np.isfinite(own_anchor) & (own_anchor != t["anchor"].to_numpy())
        es_c = np.where(differs, np.fmin(es_c, own_anchor + lo), es_c)
        lf_c = np.where(differs, np.fmax(lf_c, own_anchor + hi), lf_c)
        basis = np.where(differs, basis + "+source_date", basis)
    day = MT.to_day(r["day"])
    src = r["source"].to_numpy()
    u = np.where(r["date_basis"].astype(str).eq("local").to_numpy(), 0, 1)
    before = np.array([clocks.get(s, {}).get("before", DEFAULT_SLACK[0]) for s in src], dtype=float)
    after = np.array([clocks.get(s, {}).get("after", DEFAULT_SLACK[1]) for s in src], dtype=float)
    claim_lo, claim_hi = day - u, day + u
    end = MT.to_day(pd.to_datetime(r["end_utc"], utc=True, errors="coerce").dt.tz_convert(None)) \
        if "end_utc" in r else np.full(len(t), np.nan)
    claim_hi = np.where(np.isfinite(end) & (end > claim_hi) & (end - day <= 3), end + 1, claim_hi)
    own_lo, own_hi = claim_lo - before, claim_hi + after
    starts = [t["start"].to_numpy()]
    if "ev_date" in r:
        starts.append(MT.to_day(pd.to_datetime(r["ev_date"].to_numpy())))
    plausible = np.zeros(len(t), dtype=bool)
    for st0 in starts:      # within -10 .. +21 days of the Stage 0 tournament date or of the source's own
        plausible |= np.isfinite(day) & np.isfinite(st0) & (day - st0 >= -10) & (day - st0 <= 21)
    near_class = (claim_hi >= es_c - 2) & (claim_lo <= lf_c + 2)
    exact = plausible & near_class
    demoted = plausible & ~near_class
    t["es"] = np.where(exact, own_lo, np.where(demoted, np.fmin(own_lo, es_c), es_c))
    t["lf"] = np.where(exact, own_hi, np.where(demoted, np.fmax(own_hi, lf_c), lf_c))
    centre = np.where(exact, day, t["anchor"].to_numpy() + med)
    t["obs"] = np.clip(centre, t["es"], t["lf"])
    t["width_days"] = t["lf"] - t["es"] + 1
    t["exact"] = exact
    t["window_basis"] = np.where(exact, "exact", np.where(demoted, "claimed_day+" + basis, basis))
    t["best_source"] = np.where(exact, src, None)
    t["sources"] = np.where(np.isfinite(day), src, None)
    t["n_sources"] = np.where(np.isfinite(day), 1.0, np.nan)
    t["conflict"] = np.where(np.isfinite(day), False, None)
    t["outvoted_source"] = np.where(np.isfinite(day), "", None)
    t["wide_conflict"] = np.where(np.isfinite(day), False, None)
    t["conflict_span_days"] = np.where(np.isfinite(day), 0.0, np.nan)
    t["rejected_links"] = (np.isfinite(day) & ~plausible).astype("int64")
    t["demoted"] = np.where(demoted, "outside its class window", "")
    t["contradictory_event"] = False
    if not (np.isfinite(t[["es", "lf", "obs"]].to_numpy(dtype=float)).all() and (t["lf"] >= t["es"]).all()):
        raise AssertionError("every new match needs a finite window that does not end before it starts")
    return t.drop(columns=["phase", "era"])


def frozen_round_windows(ref_timing: pd.DataFrame) -> pd.DataFrame:
    """The frozen timeline's window of each (tournament, round): the earliest start and the latest finish of its rows."""
    return ref_timing.groupby(["tournament_id", "round"]).agg(f_es=("es", "min"), f_lf=("lf", "max"))


def round_union(timing: pd.DataFrame, ref_timing: pd.DataFrame, ref_ids: set) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A new match whose window is disjoint from the frozen timeline's windows of the same tournament and round (its
    source's day contradicts Stage 0's days for that round) takes the union of both: the earlier start and the later
    finish, so that the true days lie inside whichever record is right (role E, CP1b: a TennisLive semifinal dated six
    days before Stage 0's semifinals could count four days early). It is no longer exact; nothing else changes.
    Returns the timeline and the rows widened (before and after)."""
    fr = frozen_round_windows(ref_timing)
    t = timing.copy()
    key = pd.MultiIndex.from_arrays([t["tournament_id"].astype(str), t["round"].astype(str)])
    f_es = fr["f_es"].reindex(key).to_numpy(dtype=float)
    f_lf = fr["f_lf"].reindex(key).to_numpy(dtype=float)
    es, lf = t["es"].to_numpy(dtype=float), t["lf"].to_numpy(dtype=float)
    hit = (~t["match_id"].isin(ref_ids).to_numpy() & np.isfinite(f_es) & np.isfinite(f_lf)
           & ((lf < f_es) | (es > f_lf)))
    log_rows = t.loc[hit, ["match_id", "es", "lf", "obs", "exact", "window_basis"]].copy()
    if hit.any():
        t.loc[hit, "es"] = np.fmin(es[hit], f_es[hit])
        t.loc[hit, "lf"] = np.fmax(lf[hit], f_lf[hit])
        t.loc[hit, "obs"] = np.clip(t.loc[hit, "obs"].to_numpy(dtype=float), t.loc[hit, "es"].to_numpy(dtype=float),
                                    t.loc[hit, "lf"].to_numpy(dtype=float))
        t.loc[hit, "width_days"] = t.loc[hit, "lf"] - t.loc[hit, "es"] + 1
        t.loc[hit, "exact"] = False
        t.loc[hit, "demoted"] = "its day contradicts Stage 0's days for the same round"
        t.loc[hit, "window_basis"] = t.loc[hit, "window_basis"].astype(str) + "+frozen_round_union"
    log_rows = log_rows.rename(columns={c: f"{c}_before" for c in ("es", "lf", "obs", "exact", "window_basis")})
    log_rows["es_after"], log_rows["lf_after"] = t.loc[hit, "es"].to_numpy(), t.loc[hit, "lf"].to_numpy()
    log_rows["frozen_round_es"], log_rows["frozen_round_lf"] = f_es[hit], f_lf[hit]
    return t, log_rows.reset_index(drop=True)


def apply_round_union(label: str, out: Path) -> int:
    """round_union on a built candidate's timeline (for a candidate built before the rule): only the conflicting new
    rows change. The candidate's READY.txt and manifest.json are kept under a 'superseded' name (the folder is not
    READY while it changes); run --checks and --ready again afterwards."""
    t = pd.read_parquet(out / "timing.parquet")
    m_ids = set(pd.read_parquet(REF_TABLES / "stage0_matches.parquet", columns=["match_id"])["match_id"])
    t2, widened = round_union(t, pd.read_parquet(REF_TIMING), m_ids)
    if widened.empty:
        log("round union: no conflicting row; nothing changed")
        return 0
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
    for f in ("READY.txt", "manifest.json"):
        if (out / f).exists():
            (out / f).rename(out / f"{Path(f).stem}_superseded_{stamp}{Path(f).suffix}")
    other = t.drop(index=t.index[t["match_id"].isin(set(widened["match_id"]))])
    same = t2.loc[other.index]
    if not other.equals(same):
        raise AssertionError("round union changed a row it should not have")
    t2.to_parquet(out / "timing.parquet", index=False, compression="zstd")
    rec = json.loads((out / "build_record.json").read_text(encoding="utf-8"))
    rec.setdefault("patches", []).append({
        "patch": "round_union", "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "builder_sha256": sha256(Path(__file__)), "rows": widened.astype(object).where(widened.notna(), None)
        .to_dict("records")})
    jdump(rec, out / "build_record.json")
    status(f"{label}: round union applied to {len(widened)} new rows whose windows were disjoint from Stage 0's windows "
           f"for the same round ({', '.join(widened['match_id'])}); every other row unchanged; READY withdrawn until "
           f"the checks run again")
    return 0


# ------------------------------------------------------------------------------------------------ the build
def input_hashes(sources: list[str]) -> dict:
    files = {"wta_api": sorted((WTA / "matches").glob("*.parquet")) + sorted((WTA / "stats").glob("*.parquet"))
             + [WTA / "editions.parquet"],
             "itf_live": [ITF / f"{t}.parquet" for t in ("matches", "events", "statistics")],
             "wta_site": [WTA_SITE / "matches.csv", WTA_SITE / "tournaments.csv"]
             + (sorted(WTA_PLAYER_RESULTS.glob("*.parquet")) if WTA_SITE_API["on"] else []),
             "tennislive": [TL / "listed.parquet", TL / "events.parquet"],
             "tennislive_pages": [TL / "matches.parquet", TL / "statistics.parquet"],
             "tdi": [TDI / f"{t}.parquet" for t in ("matches", "statistics", "points")],
             "sofascore": [DUMP / "points" / c / f"{t}.parquet" for c in ("sofascore", "sofascore_editions",
                                                                         "sofascore_tournaments")
                           for t in ("events", "statistics")]}
    out = {}
    for s in sources:
        for f in files.get(s, []):
            if f.exists():
                st = f.stat()
                out[f.relative_to(ROOT).as_posix()] = {"sha256": sha256(f), "bytes": st.st_size,
                                                      "modified_utc": dt.datetime.fromtimestamp(
                                                          st.st_mtime, dt.timezone.utc).isoformat(timespec="seconds")}
    out[REF_TABLES.relative_to(ROOT).as_posix() + "/stage0_matches.parquet"] = {
        "sha256": sha256(REF_TABLES / "stage0_matches.parquet")}
    out[REF_TABLES.relative_to(ROOT).as_posix() + "/stage0_match_players.parquet"] = {
        "sha256": sha256(REF_TABLES / "stage0_match_players.parquet")}
    out[REF_TIMING.relative_to(ROOT).as_posix()] = {"sha256": sha256(REF_TIMING)}
    return out


def cross_tour_rows(m: pd.DataFrame, ref_ids: set) -> int:
    """Player ids of new matches whose tour is not the match's (an ATP match with a 'wta:' id): must be none."""
    new = m[~m["match_id"].isin(ref_ids)]
    bad = 0
    for side in ("player_a_id", "player_b_id"):
        pref = new[side].astype(str).str.split(":").str[0].replace({"atpcode": "atp"})
        bad += int((pref != new["tour"].astype(str)).sum())
    return bad


def repair_and_dedupe(m: pd.DataFrame, mp: pd.DataFrame, ref_ids: set) -> tuple[pd.DataFrame, pd.DataFrame, dict,
                                                                                   set]:
    """repair_tables on the candidate (it changes no reference row: they were repaired when Stage 0 was built), then
    the new matches its merges made duplicates: the same pair twice in one tournament (outside round robins), or a
    player twice in one round of one tournament. A reference match is never dropped; between new ones, the first
    (in the wiring order) stays for a pair, and none of them for a player twice in a round."""
    from src.eda.current_best_model import history as H
    from src.eda.feature_alpha_audit.repair_data import repair_tables
    before = mp[["match_id", "side", "player_id"]].copy()
    m2, mp2, meta = repair_tables(m, mp)
    changed = before["player_id"].to_numpy() != mp2["player_id"].to_numpy()
    ref_changed = int((changed & before["match_id"].isin(ref_ids).to_numpy()).sum())
    if ref_changed:
        raise AssertionError(f"the identity repair changed {ref_changed} reference player rows")
    # a reference match's facts stay the reference's (13 Oct 2026): repair_tables blanks a duration that the box score
    # makes implausible (under 15 or over 120 seconds a point), so a box score a layer completed can blank the minutes of
    # a match the reference holds (wta|2018-405|Q1, a one-set retirement of 83 minutes, in F20261013b). Completions
    # change no fact of the match, so the reference's values are put back
    facts = [c for c in H.MATCH_FACTS if c != "has_box" and c in m2.columns]
    ref_rows = m2["match_id"].isin(ref_ids).to_numpy()
    orig = m.drop_duplicates("match_id").set_index("match_id")
    restored = 0
    for c in facts:
        was = m2.loc[ref_rows, "match_id"].map(orig[c])
        cur = m2.loc[ref_rows, c]
        diff = ~((cur.astype(object) == was.astype(object)) | (cur.isna() & was.isna())).to_numpy()
        if diff.any():
            idx = m2.index[ref_rows][diff]
            m2.loc[idx, c] = was.to_numpy()[diff]
            restored += int(diff.sum())
    meta["reference_facts_restored"] = restored
    new = ~m2["match_id"].isin(ref_ids)
    lo = np.where(m2["player_a_id"] < m2["player_b_id"], m2["player_a_id"], m2["player_b_id"])
    hi = np.where(m2["player_a_id"] < m2["player_b_id"], m2["player_b_id"], m2["player_a_id"])
    ev = m2["tour"].astype(str) + "|" + m2["tournament_id"].astype(str) + "|" + m2["tournament_date"].astype(str)
    nrr = m2["round"].ne("RR").to_numpy()
    k = pd.Series(ev + "|" + lo + "|" + hi, index=m2.index)
    t = pd.DataFrame({"k": k, "new": new, "pos": np.arange(len(m2))})[nrr]
    grp = t.groupby("k")
    has_ref = grp["new"].transform(lambda s: (~s).any())
    first_new = t[t["new"]].sort_values("pos").drop_duplicates("k")["pos"]
    drop_pair = t["new"] & (has_ref | ~t["pos"].isin(first_new))
    gone = set(m2.loc[t.index[drop_pair.to_numpy()], "match_id"])
    # the same pair in two tournaments of the same week (tournament dates within NEW_EVENT_DAYS): one match filed twice
    # under two events; the new copy goes (a weekly venue's rematch is a week apart and stays)
    pr = pd.DataFrame({"pair": m2["tour"].astype(str) + "|" + lo + "|" + hi, "tid": m2["tournament_id"].astype(str),
                       "d": pd.to_datetime(m2["tournament_date"]), "new": new, "pos": np.arange(len(m2)),
                       "mid": m2["match_id"]})
    pr = pr[~pr["mid"].isin(gone) & pr["pair"].isin(set(pr.loc[pr["new"], "pair"]))].sort_values(["pair", "d", "pos"])
    same = pr["pair"].eq(pr["pair"].shift())
    near = same & ((pr["d"] - pr["d"].shift()).dt.days.abs() <= NEW_EVENT_DAYS) & pr["tid"].ne(pr["tid"].shift())
    prev_new = pr["new"].shift().fillna(False).astype(bool)
    week_dup = set(pr.loc[near & pr["new"], "mid"]) | set(pr["mid"].shift()[near & ~pr["new"] & prev_new].dropna())
    gone |= week_dup
    # one match filed under two events of consecutive weeks (same pair, same round, same score, within ten days):
    # the new copy goes; a real rematch the next week rarely repeats both the round and the score
    sc = pd.DataFrame({"pair": m2["tour"].astype(str) + "|" + lo + "|" + hi, "rnd": m2["round"].astype(str),
                       "score": m2["score"].astype(str), "tid": m2["tournament_id"].astype(str),
                       "d": pd.to_datetime(m2["tournament_date"]), "new": new, "pos": np.arange(len(m2)),
                       "mid": m2["match_id"]})
    sc = sc[~sc["mid"].isin(gone) & sc["pair"].isin(set(sc.loc[sc["new"], "pair"]))]
    sc = sc.sort_values(["pair", "rnd", "score", "d", "pos"])
    same = sc["pair"].eq(sc["pair"].shift()) & sc["rnd"].eq(sc["rnd"].shift()) & sc["score"].eq(sc["score"].shift())
    close = same & ((sc["d"] - sc["d"].shift()).dt.days.abs() <= 10) & sc["tid"].ne(sc["tid"].shift())
    prev_new2 = sc["new"].shift().fillna(False).astype(bool)
    copy_dup = set(sc.loc[close & sc["new"], "mid"]) | set(sc["mid"].shift()[close & ~sc["new"] & prev_new2].dropna())
    gone |= copy_dup
    pl = pd.concat([pd.DataFrame({"m": m2["match_id"], "pid": m2["player_a_id"], "ev": ev, "r": m2["round"],
                                  "new": new}),
                    pd.DataFrame({"m": m2["match_id"], "pid": m2["player_b_id"], "ev": ev, "r": m2["round"],
                                  "new": new})])
    pl = pl[pl["r"].ne("RR") & ~pl["m"].isin(gone)]
    key = pl["pid"].astype(str) + "|" + pl["ev"] + "|" + pl["r"].astype(str)
    multi = key.duplicated(keep=False)
    twice = set(pl.loc[multi.to_numpy() & pl["new"].to_numpy(), "m"])
    gone |= twice
    keep = ~m2["match_id"].isin(gone)
    m2 = m2[keep].reset_index(drop=True)
    mp2 = mp2[mp2["match_id"].isin(set(m2["match_id"]))].reset_index(drop=True)
    info = {"new_match_player_rows_merged": int(changed.sum()), "reference_player_rows_changed": ref_changed,
            "identity_aliases": len(meta.get("identity_aliases", [])),
            "identity_conflicts_left_unresolved": len(meta.get("identity_conflicts_left_unresolved", [])),
            "new_matches_dropped_same_pair_in_a_tournament": int(drop_pair.sum()),
            "new_matches_dropped_same_pair_in_two_tournaments_of_one_week": len(week_dup),
            "new_matches_dropped_same_pair_round_and_score_within_ten_days": len(copy_dup),
            "new_matches_dropped_player_twice_in_a_round": len(twice),
            "reference_facts_restored": meta.get("reference_facts_restored", 0)}
    log(f"identity repair: {info}")
    return m2, mp2, info, gone


ADDITION_COLUMNS = ["match_id", "sid", "source", "tour", "season", "ev_key", "ev_date", "event_tid", "event_date",
                    "level", "map_level", "rnd", "x1", "x2", "route1", "route2", "p1", "p2", "c1", "c2", "has_src_box",
                    "date_basis", "day"]
ADDITION_DERIVED = ["joins_stage0_event", "has_box", "player_a_id", "player_b_id"]


def empty_additions() -> pd.DataFrame:
    """additions.parquet of a candidate without new matches (a box-only source's: 14 Oct 2026, the TennisLive box-score
    package, docs/studies/tennislive_box_fill/): no rows, but the columns the checks read, with the types a written
    additions table reads back with (text as str, so that the checks' merges on player ids keep matching dtypes)."""
    other = {"season": "int64", "has_src_box": bool, "joins_stage0_event": bool, "has_box": bool,
             "ev_date": "datetime64[ns]", "event_date": "datetime64[ns]", "day": "datetime64[ns]"}
    return pd.DataFrame({c: pd.Series(dtype=other.get(c, "str")) for c in ADDITION_COLUMNS + ADDITION_DERIVED})


def build(label: str, sources: list[str], revisions: bool, out: Path) -> dict:
    QUIET["on"] = label.startswith("_")
    out.mkdir(parents=True, exist_ok=True)
    (out / "evidence").mkdir(exist_ok=True)
    status(f"build {label} started: sources {','.join(sources)}; box layer priority {','.join(BOX_PRIORITY)}; "
           f"revisions {'applied' if revisions else 'counted, not applied'}")
    record: dict = {"label": label, "started_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                    "sources": sources, "box_priority": BOX_PRIORITY, "box_sources": BOX_SOURCES["only"],
                    "revisions_applied": revisions,
                    "sofascore_skip": sorted(SOFA_SKIP["categories"]), "builder_sha256": sha256(Path(__file__)),
                    "inputs": input_hashes(sources), "per_source": {}}
    m_ref, mp_ref = load_reference()
    ref_ids = set(m_ref["match_id"])
    S = link_frame(m_ref, mp_ref)
    names = Names(m_ref, mp_ref)
    facts = event_facts(S, m_ref)
    ref_timing = pd.read_parquet(REF_TIMING)
    log(f"reference: {len(m_ref):,} matches; link frame ready")
    new_m, new_mp, new_rows, classes, box_inputs, clocks, xws = [], [], [], [], [], {}, {}
    for src in sources:
        R, st = LOADERS[src]()
        log(f"{src}: {len(R):,} played singles rows read ({st})")
        links, reason, amb = link_rows(R, S)
        evmap = event_map(R, links, S)
        links, dropped = weekly_venue_filter(R, links, evmap, S)
        xw, conflicting, contested = crosswalk(R, links, S)
        xws[src] = xw
        ids = resolve_ids(R, xw, conflicting, contested, names, TAGS[src], relax=src in MULTI_ID_SOURCES)
        cls = classify(R, links, amb, evmap, ids, S, facts)
        if src in BOX_ONLY:
            cls.loc[cls["why"].eq("new"), "why"] = "left_out: box-only source, its match is not in the candidate"
        clocks[src] = source_clock(R, links[links["match_id"].isin(ref_ids)], ref_timing)
        N = assemble_new(R, cls, facts)
        mn, mpn = build_rows(N)
        if len(mn):
            N["match_id"] = mn["match_id"].to_numpy()
            taken = set(S["match_id"])
            clash = mn["match_id"].isin(taken) | mn["match_id"].duplicated(keep="first")
            if clash.any():
                bad = set(N.loc[clash.to_numpy(), "sid"])
                cls.loc[cls["sid"].isin(bad), "why"] = "left_out: its Stage 0 match id is already taken"
                keep_ids = set(mn.loc[~clash, "match_id"])
                mn, N = mn[~clash].reset_index(drop=True), N[~clash.to_numpy()].reset_index(drop=True)
                mpn = mpn[mpn["match_id"].isin(keep_ids)].reset_index(drop=True)
            new_m.append(mn)
            new_mp.append(mpn)
            new_rows.append(N)
            S = pd.concat([S, link_frame(mn, mpn)], ignore_index=True)
            names.add(mn, mpn)
            nf = event_facts(None, mn)
            facts = pd.concat([facts, nf[~nf.index.isin(facts.index)]])
        if R["has_src_box"].any() and (BOX_SOURCES["only"] is None or src in BOX_SOURCES["only"]):
            keepc = ["sid", "source", "has_src_box"] + [f"p{k}_{c}" for k in (1, 2) for c in COUNTS]
            box_inputs.append((R.loc[R["has_src_box"], keepc].copy(), links[["sid", "match_id", "p1_side"]].copy()))
        cls = cls.merge(links[["sid", "pass", "sc", "rd"]].drop_duplicates("sid"), on="sid", how="left")
        classes.append(cls)
        links[["sid", "match_id", "pass", "sc", "rd", "p1_side", "q1", "q2"]].to_parquet(
            out / "evidence" / f"links_{src}.parquet", index=False)
        xw.to_csv(out / "evidence" / f"crosswalk_{src}.csv", index=False)
        dropped[["sid", "match_id", "ev_key", "tournament_id"]].to_csv(
            out / "evidence" / f"weekly_venue_unlinked_{src}.csv", index=False)
        why = cls["why"].value_counts().to_dict()
        nnew = int(len(mn)) if len(mn) else 0
        record["per_source"][src] = {
            "package": PACKAGES[src], "read": st, "rows": int(len(R)), "outcome": why,
            "links": int(len(links)), "links_by_pass": links["pass"].value_counts().to_dict(),
            "links_dropped_weekly_venue_rule": int(len(dropped)), "events_mapped": int(len(evmap)),
            "events": int(R["ev_key"].nunique()), "crosswalk_ids": int(len(xw)),
            "crosswalk_shared_claims_kept": int(xw["claim"].ne("sole").sum()) if "claim" in xw else 0,
            "conflicting_source_ids": len(conflicting), "contested_stage0_ids": len(contested), "new_matches": nnew,
            "id_routes_new_rows": pd.concat([N["route1"], N["route2"]]).value_counts().to_dict() if len(N) else {},
            "clock": clocks[src]}
        status(f"{src}: {len(R):,} rows; {why.get('in_stage0', 0):,} already in Stage 0; {nnew:,} new matches; "
               f"{sum(v for k, v in why.items() if k.startswith('left_out')):,} left out")
        log(f"{src}: {why}")
    # one player, one id, across the sources that share an id system (the WTA API and the WTA website: WTA ids)
    record["shared_ids"] = unify_shared_ids(new_m, new_mp, new_rows, shared_id_map(xws, set(mp_ref["player_id"])))
    log(f"shared id systems: {record['shared_ids']}")
    # box layers, on every lower-level match the candidate holds (reference or added): completions (a match held as a
    # result only) applied; revisions (a different box score) counted, applied only with --revisions; one source per
    # match, in BOX_PRIORITY's order, and only a box score that passes Stage 0's checks
    nm = pd.concat(new_m, ignore_index=True) if new_m else pd.DataFrame(columns=m_ref.columns)
    nm["order"] = -1                                  # set over the whole table below
    nmp = pd.concat(new_mp, ignore_index=True) if new_mp else pd.DataFrame(columns=mp_ref.columns)
    m = pd.concat([m_ref, conform(nm, m_ref)], ignore_index=True)
    mp = pd.concat([mp_ref, conform(nmp, mp_ref)], ignore_index=True)
    all_ids = set(m["match_id"])
    cands = [box_candidates(Rb, lb, m, mp, all_ids) for Rb, lb in box_inputs]
    cand = pd.concat([c for c in cands if len(c)], ignore_index=True) if any(len(c) for c in cands) else pd.DataFrame()
    if len(cand) and BOX_SOURCES["exclude"]:
        # --box-exclude: a source's box scores left out at the levels where it counts differently (by the matched
        # match's level)
        ml = cand["match_id"].map(m.drop_duplicates("match_id").set_index("match_id")["map_level"]).astype(str)
        out_ = pd.Series([(s, lv) in BOX_SOURCES["exclude"] for s, lv in zip(cand["source"], ml)], index=cand.index)
        record["box_candidates_excluded"] = {f"{s}:{lv}": int(n) for (s, lv), n in
                                             pd.DataFrame({"s": cand["source"], "lv": ml})[out_].value_counts().items()}
        cand = cand[~out_].reset_index(drop=True)
    layer = pd.DataFrame()
    if len(cand):
        cand["prio"] = cand["source"].map({s: i for i, s in enumerate(BOX_PRIORITY)}).fillna(len(BOX_PRIORITY))
        cand = cand.sort_values(["match_id", "prio"]).reset_index(drop=True)
        cand["reference_match"] = cand["match_id"].isin(ref_ids)
        work = cand[cand["kind"].isin(["completion", "revision"])].drop_duplicates(["match_id", "kind"])
        bm, bmp = box_rebuild(work, m, mp)
        work = work.merge(bm[["match_id", "has_box", "box_status"]].rename(columns={"has_box": "passes_checks",
                                                                                     "box_status": "new_box_status"}),
                          on="match_id", how="left")
        apply_ids = set(work.loc[work["kind"].eq("completion") & work["passes_checks"], "match_id"])
        if revisions:
            apply_ids |= set(work.loc[work["kind"].eq("revision") & work["passes_checks"], "match_id"])
        m, mp, done = apply_box(m, mp, bm, bmp, apply_ids)
        cand = cand.merge(work[["match_id", "source", "passes_checks", "new_box_status"]], on=["match_id", "source"],
                          how="left")
        cand["applied"] = cand["match_id"].isin(done).to_numpy() & cand.set_index(["match_id", "source"]).index.isin(
            list(zip(work["match_id"], work["source"])))
        layer = cand.drop(columns="prio")
    record["box_layers"] = (layer.groupby(["source", "reference_match", "kind"]).agg(
        matches=("match_id", "nunique"), pass_checks=("passes_checks", lambda s: int(s.fillna(False).sum())),
        applied=("applied", "sum")).reset_index().to_dict("records") if len(layer) else [])
    # the identity repair stage0_build applies to every Stage 0 (feature_alpha_audit.repair_data.repair_tables: a
    # non-Sackmann row's id merged into the one Sackmann id of the same exact name, no country or age conflict), so
    # that every builder sees the same ids (rebuild.py repairs again; Stage 1 does not); then the new matches it
    # made duplicates are left out
    m, mp, rmeta, gone = repair_and_dedupe(m, mp, ref_ids)
    record["repair"] = rmeta
    if gone:
        nm = nm[~nm["match_id"].isin(gone)].reset_index(drop=True)
        new_rows = [r[~r["match_id"].isin(gone)] for r in new_rows]
        if len(layer):
            layer = layer[~layer["match_id"].isin(gone)].reset_index(drop=True)
    # the candidate's tables
    allm = C.chrono_sort(m).reset_index(drop=True)
    allm["order"] = np.arange(len(allm), dtype="int64")
    allmp = mp.merge(allm[["match_id", "order"]], on="match_id", how="left", validate="many_to_one")
    allmp = allmp.sort_values(["order", "side"], kind="mergesort").drop(columns="order").reset_index(drop=True)
    if allm["match_id"].duplicated().any() or allmp.duplicated(["match_id", "side"]).any():
        raise AssertionError("duplicate match ids or sides in the candidate")
    cross = cross_tour_rows(allm, ref_ids)
    if cross:
        raise AssertionError(f"{cross} player ids of new matches belong to the other tour")
    NR = pd.concat(new_rows, ignore_index=True) if new_rows else pd.DataFrame()
    tl = timeline(nm, NR, clocks) if len(nm) else pd.DataFrame(columns=ref_timing.columns)
    if len(tl):     # a new row whose day contradicts Stage 0's days for the same round takes the union of both
        tl, widened = round_union(tl, ref_timing, ref_ids)
        record["round_union"] = widened.astype(object).where(widened.notna(), None).to_dict("records")
    timing = pd.concat([ref_timing, conform(tl, ref_timing)], ignore_index=True)
    allm.to_parquet(out / "stage0_matches.parquet", index=False)
    allmp.to_parquet(out / "stage0_match_players.parquet", index=False)
    timing.to_parquet(out / "timing.parquet", index=False, compression="zstd")
    adds = NR[ADDITION_COLUMNS].copy() if len(NR) else empty_additions()
    if len(adds):
        adds["joins_stage0_event"] = NR["tid"].notna().to_numpy()
        am = allm.set_index("match_id")
        adds["has_box"] = adds["match_id"].map(am["has_box"]).to_numpy()
        # the ids after the identity repair (x1 / x2 are the ids this builder resolved, before it)
        adds["player_a_id"] = adds["match_id"].map(am["player_a_id"]).to_numpy()
        adds["player_b_id"] = adds["match_id"].map(am["player_b_id"]).to_numpy()
    adds.to_parquet(out / "additions.parquet", index=False)
    if len(layer):
        layer.to_parquet(out / "box_layers.parquet", index=False)
    cl = pd.concat(classes, ignore_index=True)
    cl[~cl["why"].isin(["new"])][["sid", "source", "tour", "season", "ev_key", "ev_name", "qual", "rnd", "x1", "x2",
                                  "route1", "route2", "match_id", "map_level", "why", "pass", "sc", "rd"]].to_csv(
        out / "left_out.csv.gz", index=False, compression="gzip")
    record.update({"finished_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                   "reference_matches": int(len(m_ref)), "matches": int(len(allm)), "new_matches": int(len(nm)),
                   "player_rows": int(len(allmp)), "timing_rows": int(len(timing)), "clocks": clocks,
                   "new_by_source_level": nm.assign(source=nm["source"]).groupby(["source", "tour", "map_level"])
                   .size().rename("matches").reset_index().to_dict("records") if len(nm) else []})
    jdump(record, out / "build_record.json")
    status(f"build {label} written: {len(allm):,} matches ({len(nm):,} new), timeline {len(timing):,} rows -> "
           f"{rel(out)}")
    return record


# ------------------------------------------------------------------------------------------------ checks
MAIN_LEVELS = set(LC.MAIN_LEVELS)


def load_candidate(out: Path) -> dict:
    d = {"m": pd.read_parquet(out / "stage0_matches.parquet"), "mp": pd.read_parquet(out / "stage0_match_players.parquet"),
         "timing": pd.read_parquet(out / "timing.parquet"), "adds": pd.read_parquet(out / "additions.parquet")}
    d["layers"] = pd.read_parquet(out / "box_layers.parquet") if (out / "box_layers.parquet").exists() else pd.DataFrame()
    d["left_out"] = pd.read_csv(out / "left_out.csv.gz", low_memory=False)
    return d


def check_structure(d: dict, m_ref: pd.DataFrame, mp_ref: pd.DataFrame) -> dict:
    """The candidate's tables hold every reference match with its facts unchanged (box columns change only where a
    layer was applied), one A and one B row per match, ids consistent, and a chronological order."""
    from src.eda.current_best_model import history as H
    m, mp = d["m"], d["mp"]
    res = {"matches": int(len(m)), "reference_matches": int(len(m_ref)), "player_rows": int(len(mp))}
    res["match_ids_unique"] = bool(not m["match_id"].duplicated().any())
    sides = mp.groupby("match_id")["side"].agg(lambda s: "".join(sorted(s)))
    res["every_match_has_A_and_B"] = bool(sides.eq("AB").all() and set(sides.index) == set(m["match_id"]))
    res["reference_matches_all_present"] = bool(set(m_ref["match_id"]) <= set(m["match_id"]))
    ref = m[m["match_id"].isin(set(m_ref["match_id"]))]
    facts = [c for c in H.MATCH_FACTS if c != "has_box"]
    a = ref.set_index("match_id")[facts].sort_index().astype(str)
    b = m_ref.set_index("match_id")[facts].sort_index().astype(str)
    res["reference_facts_identical"] = bool(a.equals(b))
    layered = set(d["layers"].loc[d["layers"]["applied"].astype(bool), "match_id"]) if len(d["layers"]) else set()
    hb = ref.set_index("match_id")["has_box"].sort_index() != m_ref.set_index("match_id")["has_box"].sort_index()
    res["has_box_changed_only_where_a_layer_applied"] = bool(set(hb[hb].index) <= layered)
    keep = ["match_id", "player_id", "opponent_id", "side", "won", "player_name", "rank", "age", "country"]
    pa_ = mp[mp["match_id"].isin(set(m_ref["match_id"]))][keep].sort_values(["match_id", "side"]).reset_index(drop=True)
    pb_ = mp_ref[keep].sort_values(["match_id", "side"]).reset_index(drop=True)
    res["reference_player_rows_identical_outside_box"] = bool(pa_.astype(str).equals(pb_.astype(str)))
    a_of = m.set_index("match_id")["player_a_id"]
    b_of = m.set_index("match_id")["player_b_id"]
    side_id = np.where(mp["side"].eq("A"), mp["match_id"].map(a_of), mp["match_id"].map(b_of))
    res["player_ids_match_sides"] = bool((mp["player_id"].to_numpy() == side_id).all())
    aw = m.set_index("match_id")["a_won"]
    res["won_matches_a_won"] = bool((mp["won"].to_numpy() == np.where(mp["side"].eq("A"), mp["match_id"].map(aw),
                                                                      ~mp["match_id"].map(aw).astype(bool))).all())
    res["order_chronological"] = bool(m["order"].is_monotonic_increasing and
                                      pd.to_datetime(m["tournament_date"]).is_monotonic_increasing)
    new = m[~m["match_id"].isin(set(m_ref["match_id"]))]
    res["new_matches"] = int(len(new))
    res["new_matches_lower_levels_only"] = bool(new["map_level"].isin(LOWER_MAP).all())
    ref_players = set(mp_ref["player_id"])
    npl = pd.unique(np.r_[new["player_a_id"].to_numpy(), new["player_b_id"].to_numpy()])
    fresh = [p for p in npl if p not in ref_players]
    res["new_player_ids"] = len(fresh)
    res["new_player_ids_in_new_namespaces"] = bool(all(re.match(r"^(atp|wta):(tl|itf|wtaid|sofa)(name)?:", p) for p in fresh))
    res["new_match_player_ids_of_another_tour"] = cross_tour_rows(m, set(m_ref["match_id"]))
    res["new_match_player_ids_all_of_the_match_tour"] = res["new_match_player_ids_of_another_tour"] == 0
    # a new match's season and its holdout date agree (the holdout: events from 30 Dec 2024; seasons 2025-2026)
    hd = pd.to_datetime(new["tournament_date"]) >= LC.HOLDOUT_START
    res["new_matches_season_and_holdout_date_disagree"] = int((hd != new["year"].ge(2025)).sum())
    res["timing_rows_equal_matches"] = bool(set(d["timing"]["match_id"]) == set(m["match_id"])
                                            and not d["timing"]["match_id"].duplicated().any())
    t = d["timing"]
    res["timing_windows_valid"] = bool((t["lf"] >= t["es"]).all() and np.isfinite(t[["es", "lf"]].to_numpy(float)).all())
    tr = pd.read_parquet(REF_TIMING)
    tc = t[t["match_id"].isin(set(tr["match_id"]))].set_index("match_id").sort_index()[["es", "lf", "obs", "exact"]]
    res["reference_timing_identical"] = bool(tc.equals(tr.set_index("match_id").sort_index()[["es", "lf", "obs", "exact"]]))
    # a new row's window may not be disjoint from the frozen windows of its tournament's same round (E, CP1b)
    fr = frozen_round_windows(tr)
    tn = t[~t["match_id"].isin(set(m_ref["match_id"]))]
    key = pd.MultiIndex.from_arrays([tn["tournament_id"].astype(str), tn["round"].astype(str)])
    f_es, f_lf = fr["f_es"].reindex(key).to_numpy(dtype=float), fr["f_lf"].reindex(key).to_numpy(dtype=float)
    disjoint = np.isfinite(f_es) & ((tn["lf"].to_numpy(dtype=float) < f_es) | (tn["es"].to_numpy(dtype=float) > f_lf))
    res["new_windows_disjoint_from_the_frozen_round"] = int(disjoint.sum())
    res["new_windows_meet_the_frozen_round"] = bool(disjoint.sum() == 0)
    res["pass"] = all(v for k, v in res.items() if isinstance(v, bool))
    return res


def check_rules(d: dict, m_ref: pd.DataFrame) -> dict:
    """Stage 0's own rules on the additions: status, format, box checks (box_status after B0-B9), side A's share."""
    m = d["m"]
    new = m[~m["match_id"].isin(set(m_ref["match_id"]))].merge(d["adds"][["match_id", "source"]].rename(
        columns={"source": "src"}), on="match_id", how="left")
    out = {"status": new.groupby(["src", "status_detail"]).size().rename("matches").reset_index().to_dict("records"),
           "format": new.groupby(["src", "format"]).size().rename("matches").reset_index().to_dict("records"),
           "box_status": new.groupby(["src", "box_status"]).size().rename("matches").reset_index().to_dict("records"),
           "score_flag": new[new["score_flag"].ne("")].groupby(["src", "score_flag"]).size().rename("matches")
           .reset_index().to_dict("records")}
    k, n = int(new["a_won"].sum()), len(new)
    p = k / n if n else float("nan")
    half = 1.96 * np.sqrt(p * (1 - p) / n) if n else float("nan")
    out["side_a_won_new"] = {"n": n, "share": round(p, 4), "lo": round(p - half, 4), "hi": round(p + half, 4)}
    if len(d["layers"]):
        L = d["layers"]
        out["box_layers"] = L.groupby(["source", "kind"]).agg(
            matches=("match_id", "nunique"), pass_checks=("passes_checks", lambda s: int(s.fillna(False).sum())),
            failed_checks=("passes_checks", lambda s: int((s == False).sum())),  # noqa: E712
            applied=("applied", "sum")).reset_index().to_dict("records")
    return out


def check_duplicates(d: dict, m_ref: pd.DataFrame) -> dict:
    """Possible double counting: the same pair twice in one tournament (outside round robins), the same pair within
    three days in two tournaments, a player twice in one round of a tournament; each counted where a new match is
    involved. Weekly venues: real rematches a week apart are counted, not removed."""
    m = d["m"]
    ref = set(m_ref["match_id"])
    m = m.assign(new=~m["match_id"].isin(ref), lo=np.where(m["player_a_id"] < m["player_b_id"], m["player_a_id"],
                                                            m["player_b_id"]),
                 hi=np.where(m["player_a_id"] < m["player_b_id"], m["player_b_id"], m["player_a_id"]))
    m["pair"] = m["tour"] + "|" + m["lo"] + "|" + m["hi"]
    m["td"] = pd.to_datetime(m["tournament_date"])
    involved = m[m["pair"].isin(set(m.loc[m["new"], "pair"]))]
    nrr = involved[involved["round"].ne("RR")]
    g = nrr.groupby(["pair", "tournament_id", "td"])
    same_event = g.filter(lambda x: len(x) > 1 and x["new"].any())
    s = involved.sort_values(["pair", "td"])
    gap = s.groupby("pair")["td"].diff().dt.days
    prev_new = s.groupby("pair")["new"].shift(1)
    other_event = s.groupby("pair")["tournament_id"].shift(1) != s["tournament_id"]
    near = (gap <= NEW_EVENT_DAYS) & other_event & (s["new"] | prev_new.fillna(False).astype(bool))
    week = (gap.between(5, 9)) & other_event & (s["new"] | prev_new.fillna(False).astype(bool))
    pl = pd.concat([m[["match_id", "new", "tournament_id", "td", "round"]].assign(pid=m["player_a_id"]),
                    m[["match_id", "new", "tournament_id", "td", "round"]].assign(pid=m["player_b_id"])])
    pl = pl[pl["round"].ne("RR")]
    cnt = pl.groupby(["pid", "tournament_id", "td", "round"])["new"].agg(["size", "any"])
    twice = cnt[(cnt["size"] > 1) & cnt["any"]]
    # a player in two main draws of one week (two tournaments with the same Monday): an identity merge or a misdated
    # event; counted for the player-weeks that hold a new match and for the reference's own
    md = pl[~m.set_index("match_id").loc[pl["match_id"], "qualifying"].to_numpy(dtype=bool)]
    pw = md.groupby(["pid", "td"]).agg(events=("tournament_id", "nunique"), new=("new", "any"))
    two_main = {"player_weeks_with_a_new_match": int(pw["new"].sum()),
                "of_which_in_two_main_draws": int(((pw["events"] > 1) & pw["new"]).sum()),
                "reference_only_player_weeks": int((~pw["new"]).sum()),
                "of_which_in_two_main_draws_reference": int(((pw["events"] > 1) & ~pw["new"]).sum())}
    return {"same_pair_twice_in_one_tournament_with_a_new_match": int(same_event["match_id"].nunique()),
            "same_pair_within_3_days_in_two_tournaments_with_a_new_match": int(near.sum()),
            "same_pair_a_week_apart_in_two_tournaments_with_a_new_match (weekly venues: kept)": int(week.sum()),
            "player_twice_in_one_round_of_a_tournament_with_a_new_match": int(len(twice)),
            "player_in_two_main_draws_of_one_week": two_main,
            "examples_same_event": same_event[["match_id", "tournament_name", "round", "new"]].head(10).to_dict("records"),
            "examples_player_twice": [list(map(str, i)) for i in twice.index[:10]]}


def run_history(out: Path) -> dict:
    """history.py on the candidate: it should find new past (the additions) and revised (the box layers), never
    dropped."""
    from src.eda.current_best_model import history as H
    res = H.check(out, out / "timing.parquet")
    jdump(res, out / "history.json")
    return {k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items() if kk != "by"})
            for k, v in res.items() if k != "feeds"} | {"summary_line": H.summary_line(res)}


def repair_effect(d: dict, m_ref: pd.DataFrame) -> dict:
    """The chain's identity repair (feature_alpha_audit.repair_data.repair_tables, run by rebuild.py and Stage 4) on the
    candidate: player ids of new matches it would merge into an established id by exact name."""
    from src.eda.feature_alpha_audit.repair_data import repair_tables
    m, mp = d["m"], d["mp"]
    _, p2, meta = repair_tables(m, mp)
    newm = set(m.loc[~m["match_id"].isin(set(m_ref["match_id"])), "match_id"])
    sel = mp["match_id"].isin(newm).to_numpy()
    changed = (mp["player_id"].to_numpy() != p2["player_id"].to_numpy()) & sel
    ref_changed = (mp["player_id"].to_numpy() != p2["player_id"].to_numpy()) & ~sel
    by = pd.DataFrame({"from": mp.loc[changed, "player_id"].to_numpy(), "to": p2.loc[changed, "player_id"].to_numpy()})
    return {"new_match_player_rows_remapped": int(changed.sum()), "of_new_match_player_rows": int(sel.sum()),
            "reference_player_rows_remapped": int(ref_changed.sum()),
            "distinct_ids_remapped": int(by.drop_duplicates().shape[0]),
            "examples": by.drop_duplicates().head(15).to_dict("records"),
            "identity_aliases_total": len(meta.get("identity_aliases", [])),
            "identity_conflicts_total": len(meta.get("identity_conflicts_left_unresolved", []))}


def player_dates(m: pd.DataFrame) -> pd.DataFrame:
    p = pd.concat([m[["match_id", "tournament_date", "map_level"]].assign(pid=m["player_a_id"]),
                   m[["match_id", "tournament_date", "map_level"]].assign(pid=m["player_b_id"])], ignore_index=True)
    p["d"] = pd.to_datetime(p["tournament_date"]).astype("datetime64[ns]")
    return p


def relevance(rows: pd.DataFrame, m: pd.DataFrame) -> pd.Series:
    """Per (match_id, pid, d) row: a main-tour match (250 and up, main draw) of the player within 365 days either way."""
    p = player_dates(m)
    main = p[p["map_level"].isin(MAIN_LEVELS)][["pid", "d"]].rename(columns={"d": "d_main"}).sort_values("d_main")
    q = rows[["pid", "d"]].copy()
    q["_i"] = np.arange(len(q))
    q = q.dropna(subset=["d"]).sort_values("d")
    j = pd.merge_asof(q, main, left_on="d", right_on="d_main", by="pid", direction="nearest",
                      tolerance=pd.Timedelta(days=365))
    out = np.zeros(len(rows), dtype=bool)
    out[j["_i"].to_numpy()] = j["d_main"].notna().to_numpy()
    return pd.Series(out, index=rows.index)


def inventory(d: dict, m_ref: pd.DataFrame, out: Path) -> pd.DataFrame:
    """Source x kind x tour x level x year: new matches, box completions and revisions, and the rows left out (by
    why); how many touch the model's players (a player with a main-tour match within 365 days either way)."""
    m = d["m"]
    mm = m.set_index("match_id")
    adds = d["adds"].copy()
    adds["d"] = pd.to_datetime(adds["match_id"].map(mm["tournament_date"])).astype("datetime64[ns]")
    adds["year"] = adds["match_id"].map(mm["year"])
    r = pd.concat([adds[["match_id", "x1", "d"]].rename(columns={"x1": "pid"}),
                   adds[["match_id", "x2", "d"]].rename(columns={"x2": "pid"})], ignore_index=True)
    r["rel"] = relevance(r, m).to_numpy()
    rel = r.groupby("match_id")["rel"].any()
    adds["relevant"] = adds["match_id"].map(rel).fillna(False)
    adds["kind"] = np.where(adds["has_box"].astype(bool), "new match with box score", "new match, result only")
    parts = [adds.groupby(["source", "kind", "tour", "map_level", "year"]).agg(
        rows=("match_id", "size"), relevant_pm365=("relevant", "sum")).reset_index()]
    if len(d["layers"]):
        L = d["layers"].copy()
        L["tour"], L["map_level"], L["year"] = (L["match_id"].map(mm["tour"]), L["match_id"].map(mm["map_level"]),
                                                L["match_id"].map(mm["year"]))
        L["d"] = pd.to_datetime(L["match_id"].map(mm["tournament_date"])).astype("datetime64[ns]")
        rr = pd.concat([L[["match_id", "d"]].assign(pid=L["match_id"].map(mm["player_a_id"])),
                        L[["match_id", "d"]].assign(pid=L["match_id"].map(mm["player_b_id"]))], ignore_index=True)
        rr["rel"] = relevance(rr, m).to_numpy()
        L["relevant"] = L["match_id"].map(rr.groupby("match_id")["rel"].any())
        L["kind"] = "box " + L["kind"] + np.where(L["applied"].astype(bool), " (applied)", " (not applied)")
        parts.append(L.groupby(["source", "kind", "tour", "map_level", "year"]).agg(
            rows=("match_id", "nunique"), relevant_pm365=("relevant", "sum")).reset_index())
    lo = d["left_out"].copy()
    lo = lo[lo["why"].ne("in_stage0")]
    lo["kind"] = lo["why"]
    lo["year"] = lo["season"]
    lo["d"] = pd.NaT
    parts.append(lo.groupby(["source", "kind", "tour", "map_level", "year"], dropna=False).size().rename("rows")
                 .reset_index())
    inv = pd.concat(parts, ignore_index=True)
    inv["relevant_pm365"] = inv["relevant_pm365"].astype("Int64")
    inv["package"] = inv["source"].map(PACKAGES)
    inv = inv[["package", "source", "kind", "tour", "map_level", "year", "rows", "relevant_pm365"]]
    inv.sort_values(["source", "kind", "tour", "map_level", "year"]).to_csv(out / "inventory.csv", index=False)
    return inv


def dose(d: dict, m_ref: pd.DataFrame, out: Path) -> pd.DataFrame:
    """The model frame's matches by tour and season: how many have a player whose previous 365 (28) days gain new
    matches or new box scores, and the mean share those add to a player's previous-year history (matches, and box
    scores). Counts and dates only; no outcome."""
    m = d["m"]
    ref = set(m_ref["match_id"])
    layered = set(d["layers"].loc[d["layers"]["applied"].astype(bool), "match_id"]) if len(d["layers"]) else set()
    p = player_dates(m).merge(m[["match_id", "has_box"]], on="match_id")
    p["new"] = ~p["match_id"].isin(ref)
    p["new_box"] = (p["new"] & p["has_box"].astype(bool)) | p["match_id"].isin(layered)
    f = pd.read_parquet(LC.FRAME, columns=["match_id", "tour", "season", "tournament_date"])
    f = f.merge(m[["match_id", "player_a_id", "player_b_id"]], on="match_id", how="left")
    fr = pd.concat([f[["match_id", "tour", "season", "tournament_date"]].assign(pid=f["player_a_id"]),
                    f[["match_id", "tour", "season", "tournament_date"]].assign(pid=f["player_b_id"])], ignore_index=True)
    fr["d"] = pd.to_datetime(fr["tournament_date"]).astype("datetime64[ns]")
    codes, _ = pd.factorize(pd.concat([p["pid"], fr["pid"]], ignore_index=True))
    pc, fc = codes[:len(p)].astype(np.int64), codes[len(p):].astype(np.int64)
    pday = (p["d"] - EPOCH).dt.days.to_numpy().astype(np.int64)
    fday = (fr["d"] - EPOCH).dt.days.to_numpy().astype(np.int64)
    big = np.int64(100000)
    for name, mask in (("all", np.ones(len(p), dtype=bool)), ("box", p["has_box"].astype(bool).to_numpy()),
                       ("new", p["new"].to_numpy()), ("new_box", p["new_box"].to_numpy())):
        keys = np.sort(pc[mask] * big + pday[mask])
        for w in (365, 28):
            hi = np.searchsorted(keys, fc * big + fday, side="left")
            lo_ = np.searchsorted(keys, fc * big + (fday - w), side="left")
            fr[f"{name}_{w}"] = hi - lo_
    fr["share_new_365"] = fr["new_365"] / fr["all_365"].replace(0, np.nan)
    fr["share_new_box_365"] = fr["new_box_365"] / fr["box_365"].replace(0, np.nan)
    per = fr.groupby("match_id").agg(tour=("tour", "first"), season=("season", "first"),
                                     any_new_365=("new_365", lambda s: bool((s > 0).any())),
                                     any_new_28=("new_28", lambda s: bool((s > 0).any())),
                                     any_new_box_365=("new_box_365", lambda s: bool((s > 0).any())),
                                     any_new_box_28=("new_box_28", lambda s: bool((s > 0).any())))
    g = per.groupby(["tour", "season"])
    outd = g.agg(frame_matches=("any_new_365", "size"), with_new_365=("any_new_365", "sum"),
                 with_new_28=("any_new_28", "sum"), with_new_box_365=("any_new_box_365", "sum"),
                 with_new_box_28=("any_new_box_28", "sum"))
    pg = fr.groupby(["tour", "season"])
    outd["mean_share_new_of_prev_year_matches"] = pg["share_new_365"].mean().round(4)
    outd["mean_share_new_box_of_prev_year_box"] = pg["share_new_box_365"].mean().round(4)
    outd["mean_new_matches_prev_year"] = pg["new_365"].mean().round(3)
    outd["mean_new_box_prev_year"] = pg["new_box_365"].mean().round(3)
    outd = outd.reset_index()
    outd.to_csv(out / "dose.csv", index=False)
    return outd


def identity_samples(d: dict, m_ref: pd.DataFrame, out: Path, n: int = 20, seed: int = 20261009) -> dict:
    """Samples to check by hand, per source:
        links      source rows read as reference matches: the source's names, day, event and round beside Stage 0's
        players    new matches with a player resolved to an existing Stage 0 id: the source's name and event beside that
                   id's Stage 0 name and its nearest Stage 0 match (date, tournament, level)
    Written to identity_sample_<kind>.csv; the verdicts go to identity_verdicts.csv (by hand)."""
    m, mp = d["m"], d["mp"]
    mm = m.set_index("match_id")
    nm = mp.drop_duplicates("player_id").set_index("player_id")["player_name"]
    rng = np.random.default_rng(seed)
    rows_l, rows_p = [], []
    for lpath in sorted((out / "evidence").glob("links_*.parquet")):
        src = lpath.stem[len("links_"):]
        if src in LOADERS:
            lk = pd.read_parquet(lpath)
            take = lk.iloc[rng.choice(len(lk), size=min(n, len(lk)), replace=False)] if len(lk) else lk
            R, _ = LOADERS[src]()
            Ri = R.set_index("sid")
            for sid, mid in zip(take["sid"], take["match_id"]):
                r, s = Ri.loc[sid], mm.loc[mid]
                rows_l.append({"source": src, "sid": sid, "src_p1": r["p1"], "src_p2": r["p2"],
                               "src_day": str(r["day"])[:10] if pd.notna(r["day"]) else str(r["ev_date"])[:10],
                               "src_event": r["ev_name"], "src_round": r["rnd"], "match_id": mid,
                               "s0_a": nm.get(s["player_a_id"]), "s0_b": nm.get(s["player_b_id"]),
                               "s0_date": str(s["tournament_date"])[:10], "s0_event": s["tournament_name"],
                               "s0_round": s["round"], "name_grade": max(
                                   K.name_grade(r["p1"], nm.get(s["player_a_id"])) + K.name_grade(r["p2"], nm.get(s["player_b_id"])),
                                   K.name_grade(r["p1"], nm.get(s["player_b_id"])) + K.name_grade(r["p2"], nm.get(s["player_a_id"])))})
    p = player_dates(m)
    p = p.merge(m[["match_id", "tournament_name", "round"]], on="match_id")
    ref = set(m_ref["match_id"])
    pref = p[p["match_id"].isin(ref)].sort_values("d")
    adds = d["adds"]
    for src, g in adds.groupby("source"):
        routes = ["crosswalk", "name", "name_subset"]
        cand = pd.concat([g[g["route1"].isin(routes)].assign(k=1), g[g["route2"].isin(routes)].assign(k=2)])
        for route in routes:
            c = cand[np.where(cand["k"].eq(1), cand["route1"], cand["route2"]) == route]
            if c.empty:
                continue
            take = c.iloc[rng.choice(len(c), size=min(n, len(c)), replace=False)]
            for _, r in take.iterrows():
                pid = r["x1"] if r["k"] == 1 else r["x2"]
                name = r["p1"] if r["k"] == 1 else r["p2"]
                dd = mm.loc[r["match_id"], "tournament_date"]
                q = pref[pref["pid"].eq(pid)]
                near = q.iloc[(q["d"] - pd.Timestamp(dd)).abs().argsort()[:1]] if len(q) else q
                rows_p.append({"source": src, "route": route, "match_id": r["match_id"], "src_name": name,
                               "src_country": r["c1"] if r["k"] == 1 else r["c2"], "src_event": r["ev_key"],
                               "date": str(dd)[:10], "round": r["rnd"], "stage0_id": pid, "s0_name": nm.get(pid),
                               "s0_country": ";".join(sorted(set(mp.loc[mp["player_id"].eq(pid), "country"].dropna()
                                                                 .astype(str))))[:20],
                               "nearest_s0_date": str(near["d"].iloc[0])[:10] if len(near) else "",
                               "nearest_s0_event": near["tournament_name"].iloc[0] if len(near) else "",
                               "nearest_s0_level": near["map_level"].iloc[0] if len(near) else "",
                               "name_grade": K.name_grade(name, nm.get(pid))})
    # new ids: is the player perhaps one Stage 0 already holds (a split)? The reference players of the tour with the
    # same last name word, beside the source's name and country
    refp = mp_ref_players(m_ref, mp)
    rows_n = []
    split_exact = 0
    for src, g in adds.groupby("source"):
        nn = pd.concat([g.loc[g["route1"].eq("new"), ["match_id", "tour", "p1", "c1", "x1"]].set_axis(
                            ["match_id", "tour", "name", "c", "x"], axis=1),
                        g.loc[g["route2"].eq("new"), ["match_id", "tour", "p2", "c2", "x2"]].set_axis(
                            ["match_id", "tour", "name", "c", "x"], axis=1)]).drop_duplicates("x")
        nn["key"] = nn["name"].map(name_key)
        exact = nn.merge(refp[["tour", "key"]].drop_duplicates(), on=["tour", "key"])
        split_exact += int(len(exact))
        take = nn.iloc[rng.choice(len(nn), size=min(15, len(nn)), replace=False)] if len(nn) else nn
        for _, r in take.iterrows():
            last = r["key"].split()[-1] if r["key"] else ""
            same = refp[refp["tour"].eq(r["tour"]) & refp["last"].eq(last)].head(4)
            rows_n.append({"source": src, "new_id": r["x"], "src_name": r["name"], "src_country": r["c"],
                           "reference_same_last_name": "; ".join(f"{a} ({b})" for a, b in zip(same["player_name"],
                                                                                              same["country"]))})
    pd.DataFrame(rows_l).to_csv(out / "identity_sample_links.csv", index=False)
    pd.DataFrame(rows_p).to_csv(out / "identity_sample_players.csv", index=False)
    pd.DataFrame(rows_n).to_csv(out / "identity_sample_new_ids.csv", index=False)
    moves = repair_moves_sample(d, m_ref, out)
    return {"links_sampled": len(rows_l), "players_sampled": len(rows_p), "new_ids_sampled": len(rows_n),
            "new_ids_whose_exact_name_a_reference_player_has": split_exact, "seed": seed} | moves


def repair_moves_sample(d: dict, m_ref: pd.DataFrame, out: Path, n: int = 20, seed: int = 20261010) -> dict:
    """The identity repair's moves (a new match's player slot whose id the repair changed): per (id before, id after)
    pair the slots, the source name, and both ids' Stage 0 names, countries and spans; n pairs drawn with probability
    proportional to their slots, to check by hand (identity_sample_repair_moves.csv)."""
    adds, mp = d["adds"], d["mp"]
    fin = mp[mp["match_id"].isin(set(adds["match_id"]))].set_index(["match_id", "player_name"])["player_id"]
    fin = fin[~fin.index.duplicated()]
    cols = ["match_id", "source", "tour", "season", "name", "c", "x", "route"]
    s = pd.concat([adds[["match_id", "source", "tour", "season", "p1", "c1", "x1", "route1"]].set_axis(cols, axis=1),
                   adds[["match_id", "source", "tour", "season", "p2", "c2", "x2", "route2"]].set_axis(cols, axis=1)],
                  ignore_index=True)
    s["to"] = fin.reindex(pd.MultiIndex.from_arrays([s["match_id"], s["name"]])).to_numpy()
    mv = s[s["to"].notna() & s["x"].ne(s["to"])]
    if mv.empty:
        pd.DataFrame().to_csv(out / "identity_sample_repair_moves.csv", index=False)
        return {"repair_moved_slots": 0, "repair_moves_sampled": 0}
    ref = mp[mp["match_id"].isin(set(m_ref["match_id"]))]
    nm = ref.drop_duplicates("player_id").set_index("player_id")["player_name"]
    ct = ref.groupby("player_id")["country"].agg(lambda v: ";".join(sorted(set(v.dropna().astype(str))))[:12])
    p = player_dates(m_ref)
    span = p.groupby("pid").agg(n=("d", "size"), first=("d", "min"), last=("d", "max"))
    g = mv.groupby(["x", "to"]).agg(slots=("match_id", "size"), name=("name", "first"), c=("c", "first"),
                                    src=("source", "first"), route=("route", "first"), y0=("season", "min"),
                                    y1=("season", "max")).reset_index()
    for col, key in (("from", "x"), ("to", "to")):
        g[f"{col}_name"], g[f"{col}_c"], g[f"{col}_n"] = g[key].map(nm), g[key].map(ct), g[key].map(span["n"])
        g[f"{col}_span"] = g[key].map(span["first"].dt.year.astype("Int64").astype(str) + "-"
                                      + span["last"].dt.year.astype("Int64").astype(str))
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(g), size=min(n, len(g)), replace=False, p=(g["slots"] / g["slots"].sum()).to_numpy())
    g.iloc[sorted(idx)].to_csv(out / "identity_sample_repair_moves.csv", index=False)
    return {"repair_moved_slots": int(len(mv)), "repair_move_pairs": int(len(g)), "repair_moves_sampled": int(len(idx)),
            "repair_moves_seed": seed}


def mp_ref_players(m_ref: pd.DataFrame, mp: pd.DataFrame) -> pd.DataFrame:
    """The reference's players: tour, id, name, name key, last name word, countries."""
    ref = mp[mp["match_id"].isin(set(m_ref["match_id"]))][["match_id", "player_id", "player_name", "country"]]
    ref = ref.drop_duplicates("player_id").copy()
    ref["tour"] = ref["match_id"].str.split("|").str[0]
    ref["key"] = ref["player_name"].map(name_key)
    ref["last"] = ref["key"].str.split().str[-1]
    return ref


def run_checks(label: str, out: Path) -> int:
    QUIET["on"] = label.startswith("_")
    d = load_candidate(out)
    m_ref, mp_ref = load_reference()
    res = {"label": label, "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
    res["structure"] = check_structure(d, m_ref, mp_ref)
    log(f"structure: {res['structure']}")
    res["stage0_rules"] = check_rules(d, m_ref)
    res["duplicates"] = check_duplicates(d, m_ref)
    log(f"duplicates: { {k: v for k, v in res['duplicates'].items() if not k.startswith('examples')} }")
    res["history"] = run_history(out)
    log(res["history"]["summary_line"])
    res["repair_tables"] = repair_effect(d, m_ref)
    log(f"repair_tables: {res['repair_tables']}")
    inv = inventory(d, m_ref, out)
    res["inventory_rows"] = int(len(inv))
    ds = dose(d, m_ref, out)
    res["dose_rows"] = int(len(ds))
    rec = json.loads((out / "build_record.json").read_text(encoding="utf-8"))
    if rec.get("derived_from"):
        res["identity_samples"] = {"from_parent": rec["derived_from"],
                                   "note": "a dated subset of the parent: same ids, the parent's hand check"}
    else:
        res["identity_samples"] = identity_samples(d, m_ref, out)
    h = res["history"]
    res["history_ok"] = bool(h["dropped"]["matches"] == 0 and h["future"]["matches"] == 0)
    res["pass"] = bool(res["structure"]["pass"] and res["history_ok"])
    jdump(res, out / "checks.json")
    status(f"checks {label}: structure {'pass' if res['structure']['pass'] else 'FAIL'}; "
           f"{h['summary_line']}; repair_tables would remap "
           f"{res['repair_tables']['new_match_player_rows_remapped']:,} new-match player rows")
    return 0 if res["pass"] else 1


def identity_precision(out: Path) -> pd.DataFrame:
    """The hand check's verdicts (identity_verdicts.csv: kind, source, route, row, verdict, note; verdict 'right',
    'wrong' or 'unsure') per kind and source: the error rate and its exact 95% upper bound (Clopper-Pearson), with
    'unsure' counted once as right and once as wrong. Written to identity_precision.csv."""
    from scipy.stats import beta
    v = pd.read_csv(out / "identity_verdicts.csv")
    if not v["verdict"].isin(["right", "wrong", "unsure"]).all():
        raise SystemExit("identity_verdicts.csv: a verdict other than right / wrong / unsure")
    rows = []
    for (kind, src), g in v.groupby(["kind", "source"]):
        n, k, u = len(g), int(g["verdict"].eq("wrong").sum()), int(g["verdict"].eq("unsure").sum())
        hi = (lambda e: 1.0 if e >= n else float(beta.ppf(0.975, e + 1, n - e)))
        rows.append({"kind": kind, "source": src, "checked": n, "wrong": k, "unsure": u,
                     "error_rate": round(k / n, 4), "error_rate_unsure_as_wrong": round((k + u) / n, 4),
                     "upper95": round(hi(k), 4), "upper95_unsure_as_wrong": round(hi(k + u), 4)})
    p = pd.DataFrame(rows)
    p.to_csv(out / "identity_precision.csv", index=False)
    return p


def ready(label: str, out: Path) -> int:
    """The manifest (hashes and counts of the candidate's files and inputs) and READY.txt, after checks.json passes and
    the hand-checked identity verdicts exist."""
    chk = json.loads((out / "checks.json").read_text(encoding="utf-8"))
    if not chk.get("pass"):
        raise SystemExit("checks.json does not pass: no READY")
    if not (out / "identity_verdicts.csv").exists():
        raise SystemExit("identity_verdicts.csv (the hand check) is missing: no READY")
    precision = identity_precision(out)
    rec = json.loads((out / "build_record.json").read_text(encoding="utf-8"))
    files = {}
    for f in sorted(out.rglob("*")):
        if f.is_file() and f.name not in ("READY.txt", "manifest.json"):
            files[f.relative_to(out).as_posix()] = {"sha256": sha256(f), "bytes": f.stat().st_size}
    m = pd.read_parquet(out / "stage0_matches.parquet", columns=["match_id", "tour", "map_level", "year", "has_box"])
    manifest = {"label": label, "written_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "builder": "src/eda/lower_level_evidence/candidate_stage0.py",
                "builder_sha256_at_build": rec.get("builder_sha256"),
                "builder_sha256_at_ready": sha256(Path(__file__)), "reference": LC.REF.relative_to(ROOT).as_posix(),
                "inputs": rec["inputs"], "files": files,
                "counts": {"matches": int(len(m)), "new_matches": rec["new_matches"],
                           "reference_matches": rec["reference_matches"],
                           "by_tour_level": m.groupby(["tour", "map_level"]).size().rename("matches").reset_index()
                           .to_dict("records")},
                "history": chk["history"]["summary_line"], "checks_pass": chk["pass"],
                "identity_precision": precision.to_dict("records")}
    if rec.get("derived_from"):
        manifest.update({"derived_from": rec["derived_from"], "until": rec["until"], "keep": rec.get("keep"),
                         "builder_sha256_at_derive": rec.get("builder_sha256_at_derive"),
                         "parent_manifest_sha256": rec.get("parent_manifest_sha256")})
    jdump(manifest, out / "manifest.json")
    text = (f"{label}: ready for the chain ({manifest['written_at']}).\n"
            f"Folder: {rel(out)}/\n"
            f"Stage 0: stage0_matches.parquet ({len(m):,} matches, {rec['new_matches']:,} new), "
            f"stage0_match_players.parquet\n"
            f"Timeline: timing.parquet (the frozen reference's rows unchanged, windows for the new matches)\n"
            f"Manifest: manifest.json (sha256 of every file and input). Checks: checks.json. History: "
            f"{chk['history']['summary_line']}\n"
            f"Identity (hand check): identity_verdicts.csv, identity_precision.csv\n"
            f"Gate: role E re-audits a candidate before C1 builds an arm on it (the lead, 10 Oct 2026).\n"
            f"How the chain takes it: docs/studies/lower_level_evidence/system/F_rule_data.md, section 'Hand-over'.\n")
    (out / "READY.txt").write_text(text, encoding="utf-8")
    status(f"READY {label}: {rel(out)}/READY.txt")
    return 0


# ------------------------------------------------------------------------------------------------ a dated subset
def since_rules(rules: list[str]) -> list[tuple[str, str, pd.Timestamp, pd.Timestamp | None]]:
    """'tour:level:FROM[:UNTIL]' (dates inclusive, of the tournament date) -> (tour, level, from, until)."""
    out = []
    for r in rules:
        parts = r.split(":")
        if len(parts) not in (3, 4):
            raise SystemExit(f"--keep-since: '{r}' is not tour:level:YYYY-MM-DD[:YYYY-MM-DD]")
        out.append((parts[0], parts[1], pd.Timestamp(parts[2]), pd.Timestamp(parts[3]) if len(parts) == 4 else None))
    return out


def keep_mask(m: pd.DataFrame, keep: dict | None) -> pd.Series:
    """Whether each match is of the kept tours, levels (the study's buckets) and seasons; every match when keep is None.
    keep["since"] (13 Oct 2026, docs/studies/data_gaps_2026/): rules 'tour:level:FROM[:UNTIL]'; a match is kept only
    under a rule of its tour and level whose dates hold its tournament date (the levels a feed lost, from the week it
    was lost)."""
    if not keep:
        return pd.Series(True, index=m.index)
    ok = pd.Series(True, index=m.index)
    if keep.get("tours"):
        ok &= m["tour"].astype(str).isin(keep["tours"])
    if keep.get("levels"):
        ok &= LC.bucket(m["map_level"]).astype(str).isin(keep["levels"])
    if keep.get("years"):
        ok &= m["year"].astype(int).isin([int(y) for y in keep["years"]])
    if keep.get("since"):
        bk = LC.bucket(m["map_level"]).astype(str)
        td = pd.to_datetime(m["tournament_date"])
        tour = m["tour"].astype(str)
        hit = pd.Series(False, index=m.index)
        for t, lv, a, b in since_rules(keep["since"]):
            hit |= (tour == t) & (bk == lv) & (td >= a) & ((td <= b) if b is not None else True)
        ok &= hit
    return ok


def derive(label: str, parent: Path, until: str | None, out: Path, keep: dict | None = None) -> dict:
    """A candidate made of a built one's additions dated up to ``until`` (the lead's C0_pre: the frozen Stage 0 plus the
    additions of events dated up to 29 Dec 2024, which separates the historical backfill from the fill of the
    reference's 2026 publication lag), and of the kept tours, levels and seasons only (``keep``, since 10 Oct 2026: the
    owner's men's 2026 Challenger and Challenger-qualifying additions). Same ids, same windows, same box scores: the
    other new matches are dropped, and the box completions of the other matches are undone (the reference's own box
    columns put back). Nothing is re-linked, so the subset's identities are the parent's and its hand check is the
    parent's. until None: no date cut."""
    QUIET["on"] = label.startswith("_")
    import shutil
    cut = pd.Timestamp(until) if until is not None else None
    out.mkdir(parents=True, exist_ok=True)
    d = load_candidate(parent)
    m_ref, mp_ref = load_reference()
    ref_ids = set(m_ref["match_id"])
    m, mp = d["m"], d["mp"]
    late = (pd.to_datetime(m["tournament_date"]) > cut) if cut is not None else pd.Series(False, index=m.index)
    out_of_scope = late | ~keep_mask(m, keep)
    drop = ~m["match_id"].isin(ref_ids) & out_of_scope
    m2 = m[~drop].copy()
    mp2 = mp[mp["match_id"].isin(set(m2["match_id"]))].copy()
    L = d["layers"].copy()
    undo = set()
    # results only (13 Oct 2026, data_gaps_2026): at these tours and levels the kept matches carry no added box score,
    # because the history never held one (women's ITF qualifying) or the source counts differently (the WTA API's Slam
    # qualifying box scores equal Stage 0's on 4-37% of counts): added matches lose theirs, completions are undone
    ro = {tuple(x.split(":")) for x in (keep or {}).get("results_only", [])}
    ro_ids = set()
    if ro:
        bk = LC.bucket(m["map_level"]).astype(str)
        in_ro = pd.Series([(t, b) in ro for t, b in zip(m["tour"].astype(str), bk)], index=m.index)
        ro_ids = set(m.loc[in_ro & ~drop, "match_id"])
    if len(L):
        oos = L["match_id"].map(pd.Series(out_of_scope.to_numpy(), index=m["match_id"].to_numpy())).fillna(True)
        undo = set(L.loc[L["applied"].astype(bool) & L["match_id"].isin(ref_ids)
                         & (oos.astype(bool) | L["match_id"].isin(ro_ids)), "match_id"])
        L = L[~L["match_id"].isin(set(m.loc[drop, "match_id"]))].copy()
        L.loc[L["match_id"].isin(undo) | (L["match_id"].isin(ro_ids) & ~L["match_id"].isin(ref_ids)), "applied"] = False
    blank = set(m2.loc[m2["match_id"].isin(ro_ids) & ~m2["match_id"].isin(ref_ids) & m2["has_box"].astype(bool),
                       "match_id"])
    if blank:
        sel = m2["match_id"].isin(blank)
        m2.loc[sel, "has_box"] = False
        m2.loc[sel, "box_status"] = "blank"
        selp = mp2["match_id"].isin(blank)
        for c in COUNTS + BOX_RATES:
            mp2.loc[selp, c] = np.nan
        mp2.loc[selp, "has_box"] = False
    if undo:
        rm = m_ref.set_index("match_id")
        sel = m2["match_id"].isin(undo)
        for c in ("has_box", "box_status", "sv_gms_incl_tb"):
            m2.loc[sel, c] = m2.loc[sel, "match_id"].map(rm[c]).astype(m2[c].dtype).to_numpy()
        rp = mp_ref[mp_ref["match_id"].isin(undo)].set_index(["match_id", "player_id"])
        selp = mp2["match_id"].isin(undo)
        key = pd.MultiIndex.from_arrays([mp2.loc[selp, "match_id"], mp2.loc[selp, "player_id"]])
        for c in COUNTS + ["has_box"] + BOX_RATES:
            mp2.loc[selp, c] = rp[c].reindex(key).astype(mp2[c].dtype).to_numpy()
    m2 = m2.reset_index(drop=True)
    m2["order"] = np.arange(len(m2), dtype="int64")            # the parent's order, renumbered
    mp2 = mp2.reset_index(drop=True)
    t = d["timing"]
    t2 = t[t["match_id"].isin(set(m2["match_id"]))].reset_index(drop=True)
    adds = d["adds"][d["adds"]["match_id"].isin(set(m2["match_id"]))].reset_index(drop=True)
    m2.to_parquet(out / "stage0_matches.parquet", index=False)
    mp2.to_parquet(out / "stage0_match_players.parquet", index=False)
    t2.to_parquet(out / "timing.parquet", index=False, compression="zstd")
    adds.to_parquet(out / "additions.parquet", index=False)
    L.to_parquet(out / "box_layers.parquet", index=False)
    later = d["adds"][d["adds"]["match_id"].isin(set(m.loc[drop, "match_id"]))]
    lo_later = pd.DataFrame({c: (later[c].to_numpy() if c in later else np.nan) for c in d["left_out"].columns})
    scope = " and ".join(([f"dated after {cut.date()}"] if cut is not None else [])
                         + ([f"outside {json.dumps(keep, sort_keys=True)}"] if keep else []))
    lo_later["why"] = f"left_out: {scope} (the cut of {label})"
    lo = pd.concat([d["left_out"], lo_later], ignore_index=True)
    lo.to_csv(out / "left_out.csv.gz", index=False, compression="gzip")
    shutil.copytree(parent / "evidence", out / "evidence", dirs_exist_ok=True)
    # the identities are the parent's: its hand-check samples and verdicts stand for the subset
    for f in ("identity_sample_links.csv", "identity_sample_players.csv", "identity_sample_new_ids.csv",
              "identity_sample_repair_moves.csv", "identity_verdicts.csv", "expected_unevenness.txt",
              "expected_unevenness.sha256"):
        if (parent / f).exists():
            shutil.copy2(parent / f, out / f)
    rec = json.loads((parent / "build_record.json").read_text(encoding="utf-8"))
    rec.update({"label": label, "derived_from": rel(parent), "until": str(cut.date()) if cut is not None else None,
                "keep": keep or None,
                "derived_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "builder_sha256_at_derive": sha256(Path(__file__)),
                "parent_manifest_sha256": sha256(parent / "manifest.json"),
                "matches": int(len(m2)), "new_matches": int((~m2["match_id"].isin(ref_ids)).sum()),
                "new_matches_dropped_as_later": int(drop.sum()), "box_completions_undone_as_later": len(undo),
                "added_box_scores_blanked_results_only": len(blank),
                "player_rows": int(len(mp2)), "timing_rows": int(len(t2))})
    jdump(rec, out / "build_record.json")
    status(f"derived {label} from {rel(parent)}: additions {scope or 'all'} left out: {len(m2):,} matches "
           f"({rec['new_matches']:,} new; {int(drop.sum()):,} additions and {len(undo):,} completions left out)")
    return rec


# ------------------------------------------------------------------------------------------------ main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", required=True, help="the candidate's name (C0_now, C0_P7 ...)")
    ap.add_argument("--sources", default=",".join(SOURCE_ORDER), help="sources of new matches, in wiring order")
    ap.add_argument("--revisions", action="store_true", help="apply the revisions layer (off by default)")
    ap.add_argument("--sofascore-skip", default="", help="SofaScore categories to leave out, comma-separated "
                    "('ITF Men,ITF Women': the same day's candidate without P7's ITF box scores)")
    ap.add_argument("--out", default=None, help="output folder (default system/stage0/<label>)")
    ap.add_argument("--checks", action="store_true", help="run the checks on a built candidate")
    ap.add_argument("--ready", action="store_true", help="write the manifest and READY.txt after the checks pass")
    ap.add_argument("--derive-from", default=None, help="make the candidate from a built one's additions "
                    "dated up to --until (a label under system/stage0/, or a folder)")
    ap.add_argument("--until", default=None, help="the last tournament date --derive-from keeps (default 2024-12-29; "
                    "none with a --keep-* option)")
    ap.add_argument("--keep-tours", default="", help="--derive-from: keep only these tours' additions (atp,wta)")
    ap.add_argument("--keep-levels", default="", help="--derive-from: ... these levels' (the study's buckets: CH,CHQ)")
    ap.add_argument("--keep-years", default="", help="--derive-from: ... these seasons' (2026)")
    ap.add_argument("--keep-since", default="", help="--derive-from: rules tour:level:FROM[:UNTIL], comma-separated: "
                    "only additions of a rule's tour and level dated inside it (the 2026 gaps: data_gaps_2026)")
    ap.add_argument("--status-log", default=None, help="append status lines here instead of the team's status log")
    ap.add_argument("--round-union", action="store_true", help="apply the round-union rule to a built candidate's "
                    "timeline (withdraws READY; run --checks and --ready again)")
    ap.add_argument("--no-wta-player-matches", action="store_true", help="wta_site without the WTA API's player-matches "
                    "results (the source as built before 13 Oct 2026)")
    ap.add_argument("--box-sources", default="", help="the sources whose box scores may enter, in priority order "
                    "(default: every source, in BOX_PRIORITY's order)")
    ap.add_argument("--results-only", default="", help="--derive-from: tour:level pairs whose kept matches carry no "
                    "added box score (comma-separated)")
    ap.add_argument("--box-exclude", default="", help="source:level pairs whose box scores are left out (by the matched "
                    "match's level), comma-separated, e.g. tennislive_pages:ITF")
    a = ap.parse_args(argv)
    WTA_SITE_API["on"] = not a.no_wta_player_matches
    BOX_SOURCES["exclude"] = {tuple(x.strip().split(":", 1)) for x in a.box_exclude.split(",") if ":" in x}
    if a.box_sources.strip():
        order = [s.strip() for s in a.box_sources.split(",") if s.strip()]
        bad = set(order) - set(SOURCE_ORDER)
        if bad:
            raise SystemExit(f"--box-sources: unknown sources {sorted(bad)}")
        BOX_SOURCES["only"] = order
        BOX_PRIORITY[:] = order
    out = Path(a.out) if a.out else STAGE0_OUT / a.label
    if a.status_log:
        STATUS["log"] = Path(a.status_log)
    if a.round_union:
        QUIET["on"] = a.label.startswith("_")
        return apply_round_union(a.label, out)
    if a.checks:
        return run_checks(a.label, out)
    if a.ready:
        return ready(a.label, out)
    if a.derive_from:
        parent = Path(a.derive_from) if Path(a.derive_from).exists() else STAGE0_OUT / a.derive_from
        if not (parent / "READY.txt").exists():
            raise SystemExit(f"{parent}: not READY; derive from a checked candidate")
        keep = {k: [x.strip() for x in v.split(",") if x.strip()] for k, v in
                (("tours", a.keep_tours), ("levels", a.keep_levels), ("years", a.keep_years),
                 ("since", a.keep_since), ("results_only", a.results_only)) if v.strip()}
        if keep.get("since"):
            since_rules(keep["since"])                     # fails early on a malformed rule
        until = a.until if a.until is not None else (None if keep else "2024-12-29")
        if out.exists() and (out / "READY.txt").exists():
            raise SystemExit(f"{out} holds a candidate marked READY; derive under another label")
        derive(a.label, parent, until, out, keep or None)
        return 0
    sources = [s for s in a.sources.split(",") if s]
    unknown = set(sources) - set(SOURCE_ORDER)
    if unknown:
        raise SystemExit(f"unknown sources {sorted(unknown)}")
    if out.exists() and (out / "READY.txt").exists():
        raise SystemExit(f"{out} holds a candidate marked READY; build under another label")
    SOFA_SKIP["categories"] = {c.strip() for c in a.sofascore_skip.split(",") if c.strip()}
    build(a.label, sources, a.revisions, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())


