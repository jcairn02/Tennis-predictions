"""Indoor or outdoor for every Stage 0 match at tennis-data's levels: the model input `indoor`, both tours.

Until 9 Oct 2026 the input was Stage 0's flag, which Tennis My Life gives for men's main-tour events only. The frame
builder (tabpfn_thinking/build_frame.py) left it missing for every women's match, 32,507 of the model's, and it was
missing too for the men's 2026 US Open (127 matches), which TML left blank (docs/studies/indoor_fill/README.md).

The rule: per tour, the first of these that exists.
    men     stage0     Stage 0's flag (TML's event field), as the model has always read it
            own        tennis-data.co.uk's Court of the match's own row: Stage 1's link (td_file, and td_row, the row's
                       position in its staged partition), checked against the row's two names
            event      the Court the event's other linked rows share (the same tour and Stage 0 tournament id)
            previous   the latest earlier edition's value (the same tour, and the tournament id without its year)
    women   calendar   the WTA's own calendar: its inOutdoor for the edition (api.wtatennis.com; the calendar pages
                       src/ingest/point_sources/wta.py keeps on disk)
            own, event, previous   as for the men
            stage0     Stage 0's flag
Why this order. tennis-data's Court is wrong on whole events, 26 of the model's 1,594 (crosscheck.py; each checked against
the venue). Where it disagrees with TML on a men's event (10 events), TML is right; where it disagrees with the WTA's
calendar on a women's event (16), the WTA is right. So each tour reads its better source first, and tennis-data's Court
fills what that source lacks: the men's 2026 US Open, and the women's events missing from the WTA's calendar (Eastbourne
2013-2025).

Every played model match has a value before `previous`. The `previous` step, and for the women the calendar, serve live
matches (prediction runs): a live match's Stage 1 row has no tennis-data link (prediction_run/inject.py), as tennis-data
publishes a match only after it is played, while the WTA's calendar lists the edition in advance.

A WTA edition is matched to a Stage 0 event when the event's date (Stage 0's tournament date) falls between 3 days before
the edition's start and 2 days after its end, and either the event's id is TML's form of the edition's id (<year>-<the
WTA's id>, as prediction_run/fills.py reads it) or the event's name, or tennis-data's Location of its rows, reads like the
edition's city or title (similarity 0.6 or more; the closest when several do, Stage 0's name breaking ties).

Reads Stage 0 and Stage 1 where predictability_diagnostic.common puts them, the tennis-data partitions Stage 1 names, and
the WTA calendar pages. No result is read.
"""
from __future__ import annotations

import difflib
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.eda.predictability_diagnostic import common as C  # noqa: E402

STAGE1 = C.OUT / "stage1_odds.parquet"
MATCH_COLS = ["match_id", "tour", "year", "level", "tournament_id", "tournament_name", "tournament_date", "indoor"]
LEVELS = ("GS", "FIN", "T1000", "T500", "T250", "TEAM")      # Stage 1's link levels (stage1_odds.LINK_LEVELS)
STEPS = {"atp": ("stage0", "own", "event", "previous"), "wta": ("calendar", "own", "event", "previous", "stage0")}
COURT = {"indoor": 1.0, "outdoor": 0.0}
WTA_ID = re.compile(r"^(\d{4})-(\d+)$")                       # TML's women's ids: <year>-<the WTA's tournament id>
WINDOW = (-3, 2)                                              # days before an edition's start, after its end
MIN_SIMILARITY = 0.6
OUT_COLUMNS = ["match_id", "tour", "year", "tournament_id", "indoor", "source", "stage0", "own", "event", "calendar",
               "previous", "wta_id", "wta_title", "wta_how"]


def court_flag(values) -> pd.Series:
    """tennis-data's Court as 1.0 (Indoor), 0.0 (Outdoor), NaN (anything else)."""
    s = pd.Series(values)
    return s.astype("string").str.strip().str.lower().map(COURT).astype("float64")


def stage0_rows(ids=None, levels=LEVELS) -> pd.DataFrame:
    """Stage 0's facts the rule reads, at tennis-data's levels (all levels with levels=None)."""
    m = pd.read_parquet(C.MATCHES, columns=MATCH_COLS)
    m["match_id"] = m["match_id"].astype(str)
    if levels is not None:
        m = m[m["level"].isin(levels)]
    if ids is not None:
        m = m[m["match_id"].isin(set(map(str, ids)))]
    return m.reset_index(drop=True)


def td_fields(ids, cols: list[str]) -> pd.DataFrame:
    """The linked tennis-data row's columns (text, as staged), indexed by match id; unlinked matches are absent.

    A row is read by its position in its partition (td_row). Its two names must be the two Stage 1 recorded when it
    linked, so a dump restaged since Stage 1 was built, with rows moved, stops here instead of reading other rows."""
    o = pd.read_parquet(STAGE1, columns=["match_id", "td_file", "td_row", "td_winner", "td_loser"])
    o = o[o["td_file"].notna() & o["td_row"].notna()]
    o["match_id"] = o["match_id"].astype(str)
    o = o[o["match_id"].isin(set(map(str, ids)))]
    parts = []
    for f, g in o.groupby("td_file"):
        raw = pd.read_parquet(ROOT / str(f), columns=sorted(set(cols) | {"Winner", "Loser"}))
        pos = g["td_row"].astype("int64").to_numpy()
        if len(pos) and (pos.max() >= len(raw) or pos.min() < 0):
            raise RuntimeError(f"{f}: Stage 1 names row {int(pos.max())} of {len(raw)}: rebuild Stage 1 on this dump")
        rows = raw.iloc[pos]
        same = np.array([{a, b} == {c, d} for a, b, c, d in
                         zip(rows["Winner"], rows["Loser"], g["td_winner"], g["td_loser"])], dtype=bool)
        if not same.all():
            bad = g["match_id"].to_numpy()[~same][:3].tolist()
            raise RuntimeError(f"{f}: {int((~same).sum())} linked rows name other players than Stage 1 recorded "
                               f"(first {bad}): rebuild Stage 1 on this dump")
        parts.append(rows[cols].set_axis(g["match_id"].to_numpy()))
    if not parts:
        return pd.DataFrame(columns=cols)
    out = pd.concat(parts)
    return out[~out.index.duplicated()]


def edition_series(tour: pd.Series, tournament_id: pd.Series) -> pd.Series:
    """An event across its editions: the tour, and the tournament id without its year (a leading "YYYY-", and the
    trailing "-YYYY" of the older WTA ids)."""
    tid = tournament_id.astype(str).str.replace(r"^\d{4}-", "", regex=True).str.replace(r"-\d{4}$", "", regex=True)
    return tour.astype(str) + "|" + tid


# ------------------------------------------------------------------------------------------------
# The WTA's calendar

def norm(text) -> str:
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]", "", text)


def similarity(a, b) -> float:
    """1 when one normalised name holds the other (four letters or more), else difflib's ratio."""
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    if min(len(a), len(b)) >= 4 and (a in b or b in a):
        return 1.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def wta_editions(years) -> pd.DataFrame:
    """The WTA calendar's editions of these years, from the pages on disk, with dates and the flag."""
    from src.ingest.point_sources import wta as W
    e = pd.DataFrame(W.load_editions(sorted({int(y) for y in years})), columns=W.EDITION_COLUMNS)
    e["tournament_id"] = e["tournament_id"].astype(str)
    e["start"] = pd.to_datetime(e["start_date"].astype(str).str[:10], errors="coerce")
    e["end"] = pd.to_datetime(e["end_date"].astype(str).str[:10], errors="coerce")
    e["flag"] = e["in_outdoor"].astype(str).str.strip().str.upper().map({"I": 1.0, "O": 0.0})
    return e


def match_editions(events: pd.DataFrame, e: pd.DataFrame) -> pd.DataFrame:
    """Per event (columns tournament_id, date, name, location): the WTA edition it is (wta_id, wta_title, the flag
    calendar, wta_how "id" or "name", wta_similarity), or NaN when none matches."""
    out = []
    for tid, date, name, loc in zip(events["tournament_id"].astype(str), events["date"], events["name"],
                                    events["location"]):
        cand = e[(e["start"] + pd.Timedelta(days=WINDOW[0]) <= date) & (date <= e["end"] + pd.Timedelta(days=WINDOW[1]))]
        hit, how, score = None, None, 0.0
        mt = WTA_ID.match(tid)
        same = cand[cand["tournament_id"].eq(mt.group(2))] if mt else cand.iloc[0:0]
        if len(same):
            hit, how, score = same.iloc[0], "id", 1.0
        elif len(cand):
            by_name = [max(similarity(name, c), similarity(name, t)) for c, t in zip(cand["city"], cand["title"])]
            by_loc = [max(similarity(loc, c), similarity(loc, t)) for c, t in zip(cand["city"], cand["title"])]
            key = [(max(n, l_), n, -abs((s - date).days)) for n, l_, s in zip(by_name, by_loc, cand["start"])]
            best = max(range(len(key)), key=key.__getitem__)
            if key[best][0] >= MIN_SIMILARITY:
                hit, how, score = cand.iloc[best], "name", key[best][0]
        out.append({"wta_id": hit["tournament_id"] if hit is not None else None,
                    "wta_title": hit["title"] if hit is not None else None,
                    "calendar": float(hit["flag"]) if hit is not None else np.nan,
                    "wta_how": how, "wta_similarity": round(float(score), 3)})
    return pd.DataFrame(out, index=events.index)


# ------------------------------------------------------------------------------------------------
# The rule

def first_known(values: pd.DataFrame, order: tuple[str, ...]) -> tuple[pd.Series, pd.Series]:
    v = pd.Series(np.nan, index=values.index)
    src = pd.Series("none", index=values.index, dtype=object)
    for step in order:
        take = v.isna() & values[step].notna()
        v[take], src[take] = values.loc[take, step], step
    return v, src


def table(ids=None, calendar: bool = True, unlinked=None) -> pd.DataFrame:
    """Per Stage 0 match at tennis-data's levels (or the given ids among them): indoor (1.0, 0.0 or NaN), its source
    (a step's name, or "none"), every step's value, and the WTA edition matched (women). ``unlinked``: match ids whose
    tennis-data link is ignored, as a live match has none (live_check.py)."""
    m = stage0_rows()
    td = td_fields(m["match_id"], ["Court", "Location"])
    if unlinked is not None:
        td = td[~td.index.isin(set(map(str, unlinked)))]
    out = rule(m, court_flag(td["Court"]), td["Location"], wta_editions if calendar else None)
    if ids is not None:
        out = out[out["match_id"].isin(set(map(str, ids)))]
    return out.reset_index(drop=True)


def rule(m: pd.DataFrame, court: pd.Series, location: pd.Series, editions=None) -> pd.DataFrame:
    """The rule on given tables: m, Stage 0 rows (MATCH_COLS); court and location, tennis-data's Court flag and Location
    by match id (linked matches only); editions, a function of years returning the WTA calendar's editions (None: no
    calendar step). Returns OUT_COLUMNS, in m's order."""
    m = m.reset_index(drop=True)
    s = pd.DataFrame(index=m.index)
    s["stage0"] = m["indoor"].map({True: 1.0, False: 0.0}).astype("float64")
    s["own"] = m["match_id"].map(court).astype("float64")
    ev = m["tour"].astype(str) + "|" + m["tournament_id"].astype(str)
    lo, hi = s["own"].groupby(ev).transform("min"), s["own"].groupby(ev).transform("max")
    s["event"] = np.where(lo == hi, lo, np.nan)                      # none when no row links, or when rows disagree
    s["calendar"] = np.nan
    for c in ("wta_id", "wta_title", "wta_how"):
        s[c] = None
    women = m["tour"].eq("wta")
    if editions is not None and women.any():
        w = pd.DataFrame({"ev": ev, "tournament_id": m["tournament_id"].astype(str),
                          "date": pd.to_datetime(m["tournament_date"]), "name": m["tournament_name"],
                          "location": m["match_id"].map(location)})[women]
        events = w.groupby("ev").agg(tournament_id=("tournament_id", "first"), date=("date", "min"),
                                     name=("name", "first"),
                                     location=("location", lambda x: x.mode().iloc[0] if x.notna().any() else None))
        years = set(events["date"].dt.year.dropna().astype(int))
        cal = match_editions(events, editions(years | {y - 1 for y in years} | {y + 1 for y in years}))
        for c in ("calendar", "wta_id", "wta_title", "wta_how"):
            s.loc[women, c] = ev[women].map(cal[c]).to_numpy()
    s["calendar"] = s["calendar"].astype("float64")
    # previous edition: the latest earlier edition's value, from the steps before it
    base = pd.Series(np.nan, index=m.index)
    for tour, order in STEPS.items():
        t = m["tour"].eq(tour)
        base[t] = first_known(s[t], tuple(x for x in order if x != "previous"))[0]
    series = edition_series(m["tour"], m["tournament_id"])
    ed = pd.DataFrame({"series": series, "year": m["year"].astype(int), "v": base})
    ed = ed.groupby(["series", "year"])["v"].agg(["min", "max"]).reset_index().sort_values(["series", "year"])
    ed["v"] = np.where(ed["min"] == ed["max"], ed["min"], np.nan)    # an edition whose rows disagree gives none
    ed["prev"] = ed.groupby("series")["v"].transform(lambda x: x.shift().ffill())
    prev = ed.set_index(["series", "year"])["prev"]
    s["previous"] = pd.MultiIndex.from_arrays([series, m["year"].astype(int)]).map(prev).to_numpy(dtype="float64")
    value = pd.Series(np.nan, index=m.index)
    source = pd.Series("none", index=m.index, dtype=object)
    for tour, order in STEPS.items():
        t = m["tour"].eq(tour)
        value[t], source[t] = first_known(s[t], order)
    return pd.concat([m[["match_id", "tour", "year", "tournament_id"]],
                      pd.DataFrame({"indoor": value, "source": source}), s], axis=1)[OUT_COLUMNS]


def for_matches(ids, calendar: bool = True) -> tuple[np.ndarray, pd.Series]:
    """(indoor value, source) aligned to ids (NaN and "none" for an id outside Stage 0's tennis-data levels)."""
    ids = pd.Index(pd.Series(list(ids)).astype(str))
    t = table(ids, calendar).set_index("match_id")
    return t["indoor"].reindex(ids).to_numpy(dtype="float64"), t["source"].reindex(ids).fillna("none")
