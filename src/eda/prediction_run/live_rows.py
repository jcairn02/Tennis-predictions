"""Upcoming matches as Tennis My Life rows (Stage 0's --live-rows), and each one's price, day and venue.

A live row is the row TML will publish once the match is played, less what only playing it gives: the result (a
placeholder: one fixed player wins in straight sets), the games, the minutes and the box score. Every other column comes
from TML itself, so Stage 0 and every builder after it treat the row as one of the event's own:
    the event's columns (id, name, surface, draw size, level, indoor, date) from the event's own TML rows;
    each player's columns (id, seed, entry, name, hand, height, country, age, rank, points) from the player's latest row
    at the event (TML repeats them in every round), else from the player's latest row anywhere, aged to the event's date.
The placeholder never reaches the match's own inputs: every builder reads only earlier matches (the replay checks it).

What Stage 0 does not hold and the sandbox's tables need goes in the run's meta table (inject.py): the match id Stage 0
gives the row, the day it is dated by, the price, and the event's city. The match id is predicted as Stage 0 builds it,
from the ids the row carries (id_handles, since 28 Oct 2026): a player's Stage 0 id can differ from the one her matches
are named with.

A replay builds the same rows from played matches (replay.py): each match's own TML row less its outcome, with the
event's later rounds left out ("drop" rows).

An event TML holds no row of yet (a qualifying round 1, or any women's qualifying: TML carries none) takes its columns
from the matchups CSV instead (the owner's decision of 22 Oct 2026 to bet tour-level qualifying, docs/decisions/
2026-10-22-qualifying-bets.md): event_surface, event_draw_size, event_level, event_indoor and event_date, in TML's own
codes, which the notebook's linker reads off the event's previous edition (src/pipeline/live.py). A player without a TML
row (some women qualifiers' matches are all from Sackmann's files or the lower-level feed) takes their latest Stage 0
player row, aged the same way, with a blank id: Stage 0 resolves a blank id by the player's unambiguous name (C60).
A qualifying match's row also carries event_main_date, its main draw's start, when the CSV gives it: Stage 0 dates an
event by its main draw's first date (C05), and before the main draw is played it would otherwise take the qualifying's
first day, which moves every input read over a window of days (the 22 Oct replay: sets_14d, points_52w, the forms).

A main-draw row's date (25 Oct 2026, an agent's finding; on since 27 Oct 2026, the owner: "switch the date fix on";
master pipeline process log, Part 17): the event's columns come from its earliest-dated TML row, and in 2026 TML dates
each match by its day, the qualifying's before the main draw's. That row's date then becomes the live row's, and Stage
0's main-draw date for the whole event (C05 takes the earliest main-draw row, live rows included): 129 of the 148 men's
main-draw matches of the live runs of 18-24 Oct were dated 1 or 2 days before training's date of their event. A
main-draw row takes the main draw's first date instead (main_draw_date): the earliest day known of the event's main
draw, from TML's main-draw rows and the CSV's main-draw matches (each by the linker's event_main_date, the main draw's
first day as TennisLive and the listing tell in the venue's zone, else by its own day). TML's file of events under way
can date that day late, so its rows alone do not settle it. LIVE_MAIN_DRAW_DATE=0 reproduces the runs before 27 Oct
2026.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.eda.prediction_run import common as P  # noqa: F401  (puts the repository on sys.path)
from src.eda.predictability_diagnostic import common as C
from src.eda.predictability_diagnostic import stage0_build as B

TML_STAGED = C.DUMP / "matches" / "tennis_my_life"
SUBDIR_TOUR = {"atp_main": "atp", "atp_challenger": "atp", "atp_qualifying": "atp", "wta_main": "wta"}
BOX = [f"{side}_{c}" for side in ("w", "l") for c in C.BOX_SOURCE_NAMES.values()]
EVENT = ["tourney_id", "tourney_name", "surface", "draw_size", "tourney_level", "indoor", "tourney_date", "best_of"]
# the matchups CSV's columns for an event TML holds no row of yet, as the TML columns they stand for
CSV_EVENT = {"event_surface": "surface", "event_draw_size": "draw_size", "event_level": "tourney_level",
             "event_indoor": "indoor", "event_date": "tourney_date"}
PLACEHOLDER = {3: "6-4 6-4", 5: "6-4 6-4 6-4"}     # a straight-sets win: a completed match in the standard format
LIVE_MATCH_NUM = 900                               # after any real match of the event (the order within a round)
MAIN_DATE_SWITCH = "LIVE_MAIN_DRAW_DATE"           # "0": the rule before 27 Oct 2026 (the event's earliest TML row)
QUALIFYING_ROUND = re.compile(r"^Q\d$")


def staged_tml(seasons: list[int]) -> pd.DataFrame:
    """The staged TML rows of the given seasons and the three in-progress files, with their tour, as Stage 0 reads them
    (all columns text). _source_file and _row name each row as Stage 0's source_file and source_row do."""
    frames = []
    for sub, tour in SUBDIR_TOUR.items():
        for f in sorted((TML_STAGED / sub).glob("*.parquet")):
            if B.file_season(f) in seasons:
                frames.append(pd.read_parquet(f).assign(tour=tour))
    for f in sorted((TML_STAGED / "ongoing").glob("*.parquet")):
        frames.append(pd.read_parquet(f).assign(tour="wta" if f.name.startswith("wta") else "atp"))
    raw = pd.concat(frames, ignore_index=True)
    raw["_row"] = pd.to_numeric(raw["_row"], errors="coerce").astype("Int64")
    return raw


def raw_of(matches: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    """Each Stage 0 match's own TML row (matched on source_file and source_row), indexed like ``matches``."""
    key = raw["_source_file"].astype(str) + "#" + raw["_row"].astype(str)
    by = raw.assign(_key=key).drop_duplicates("_key").set_index("_key")
    want = matches["source_file"].astype(str) + "#" + pd.to_numeric(matches["source_row"]).astype("Int64").astype(str)
    out = by.reindex(want.to_numpy())
    out.index = matches.index
    missing = out["tourney_id"].isna()
    if missing.any():
        raise SystemExit(f"live rows: {int(missing.sum())} matches have no staged TML row "
                         f"(first: {matches.loc[missing, 'match_id'].head(3).tolist()})")
    return out.drop(columns=["tour"], errors="ignore")


def swap(rows: pd.DataFrame, mask: np.ndarray) -> pd.DataFrame:
    """Exchange the winner's and loser's columns where ``mask`` holds."""
    rows = rows.copy()
    pairs = [(f"winner_{b}", f"loser_{b}") for b in B.BIO] + [(f"w_{c}", f"l_{c}")
                                                             for c in C.BOX_SOURCE_NAMES.values()]
    for w, lo in pairs:
        rows.loc[mask, [w, lo]] = rows.loc[mask, [lo, w]].to_numpy()
    return rows


def outcome_removed(rows: pd.DataFrame) -> pd.DataFrame:
    """Blank what only playing the match gives, and give the placeholder result's score."""
    rows = rows.copy()
    bo = pd.to_numeric(rows["best_of"], errors="coerce").fillna(3).astype(int)
    rows["score"] = bo.map(PLACEHOLDER).fillna(PLACEHOLDER[3]).to_numpy()
    rows["minutes"] = ""
    rows[BOX] = ""
    return rows


def replay_rows(targets: pd.DataFrame, later: pd.DataFrame, raw: pd.DataFrame, players: pd.DataFrame,
                placeholder_winner: str = "A") -> pd.DataFrame:
    """Played matches as live rows: each target's own TML row, its outcome removed and the placeholder won by Stage 0's
    player A (or B), plus a "drop" row for each match of ``later`` (the events' rounds after the targets')."""
    own = raw_of(targets, raw)
    names = players.set_index(["match_id", "player_id"])["player_name"]
    winner = targets["player_a_id"] if placeholder_winner == "A" else targets["player_b_id"]
    want = B.S.keys_for(pd.Series([names.get((m, p), "") for m, p in zip(targets["match_id"], winner)],
                                  index=targets.index))
    wkey, lkey = B.S.keys_for(own["winner_name"]), B.S.keys_for(own["loser_name"])
    if not (wkey.eq(want) | lkey.eq(want)).all():
        bad = targets.loc[~(wkey.eq(want) | lkey.eq(want)), "match_id"].head(3).tolist()
        raise SystemExit(f"replay: the TML row does not name Stage 0's player (first: {bad})")
    rows = outcome_removed(swap(own, lkey.eq(want).to_numpy()))
    rows["tour"], rows["live_role"] = targets["tour"].to_numpy(), "live"
    rows["match_num"] = [str(LIVE_MATCH_NUM + i) for i in range(len(rows))]
    parts = [rows]
    if len(later):
        parts.append(raw_of(later, raw).assign(tour=later["tour"].to_numpy(), live_role="drop"))
    return pd.concat(parts, ignore_index=True)


def event_rows(raw: pd.DataFrame, tour: str, tourney_id: str, tourney_name: str | None) -> pd.DataFrame:
    """The event's TML rows (its id normalised as Stage 0 does; the name too when TML reuses the id)."""
    tid = raw["tourney_id"].astype(str).str.replace(r"-0+(\d)", r"-\1", regex=True)
    rows = raw[raw["tour"].eq(tour) & tid.eq(str(tourney_id))]
    if tourney_name:
        rows = rows[rows["tourney_name"].astype(str).eq(str(tourney_name))]
    return rows


def latest(rows: pd.DataFrame) -> pd.DataFrame:
    return rows.assign(_n=pd.to_numeric(rows["match_num"], errors="coerce")).sort_values(["tourney_date", "_n"])


def _aged(age, days: int) -> str:
    age = pd.to_numeric(age, errors="coerce")
    return "" if pd.isna(age) else f"{age + days / 365.25:.3f}"


def _days(event_date: str, last: str) -> int:
    return (pd.to_datetime(str(event_date), format="%Y%m%d") - pd.to_datetime(str(last), format="%Y%m%d")).days


def stage0_players(stage0: Path) -> pd.DataFrame:
    """Every Stage 0 player row with its match's tour and date, and the player's name key: the columns a player
    without a TML row takes (player_columns' fallback)."""
    m = pd.read_parquet(Path(stage0) / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_date"])
    p = pd.read_parquet(Path(stage0) / "stage0_match_players.parquet",
                        columns=["match_id", "player_name", "rank", "rank_points", "age", "height", "hand", "country"])
    p = p.merge(m, on="match_id", how="inner")
    return p.assign(key=B.S.keys_for(p["player_name"]), d=pd.to_datetime(p["tournament_date"]).dt.strftime("%Y%m%d"))


def id_handles(matches: pd.DataFrame, players: pd.DataFrame, raw: pd.DataFrame) -> dict:
    """(tour, a player id as TML writes it) -> the id Stage 0's match ids give it: the id a live row's match id is
    predicted with (28 Oct 2026, an agent's choice; master pipeline process log, Part 23).

    Stage 0 names a match by its players' ids as the source row resolves them (stage0_build.resolve_ids: the Sackmann
    id the crosswalk learned from linked matches, else TML's own) and only then maps a player's second id to the
    established one (repair_data.repair_tables by the exact name, apply_id_aliases), keeping the match id and the sides.
    An id TML first wrote after Sackmann's files ended is learned from no link, so the player's rows carry the
    established id and her matches' ids TML's: Kaitlin Quevedo is wta:259733 in every row, and her matches from Osaka
    (19 Oct 2026) on are named with wta:269267, TML's new id for her (the live run of 28 Oct 2026 stopped on two such
    matches). Read off Stage 0's own matches from TML rows: each paired with its staged row (source file and row), each
    side with the row's player by name. matches: Stage 0's match rows (match_id, tour, source, source_file,
    source_row); players: its player rows (match_id, side, player_name); raw: staged_tml. An id read two ways is left
    out: the caller keeps the player's Stage 0 id, and the check after the sandbox's build decides."""
    m = matches.loc[matches["source"].astype(str).eq("tml"), ["match_id", "tour", "source_file", "source_row"]]
    row = pd.to_numeric(m["source_row"], errors="coerce").astype("Int64").astype(str)
    key = m["source_file"].astype(str) + "#" + row
    r = raw.assign(_key=raw["_source_file"].astype(str) + "#" + raw["_row"].astype(str)).drop_duplicates("_key")
    j = m.assign(_key=key.to_numpy()).merge(r[["_key", "winner_id", "winner_name", "loser_id", "loser_name"]],
                                           on="_key")
    p = players[players["match_id"].isin(set(j["match_id"]))]
    side_key = dict(zip(zip(p["match_id"].astype(str), p["side"].astype(str)), B.S.keys_for(p["player_name"])))
    seen: dict = {}
    for mid, tour, wid, wn, lid, ln in zip(*(j[c].tolist() for c in ("match_id", "tour", "winner_id", "winner_name",
                                                                       "loser_id", "loser_name"))):
        mid = str(mid)
        lo, hi = mid.rsplit("|", 2)[1:]
        by_key = {side_key.get((mid, s)): h for s, h in zip("AB", (lo, hi) if C.side_is_low(mid) else (hi, lo))}
        if len(by_key) != 2:                         # one name on both sides: nothing to pair
            continue
        for pid, name in ((wid, wn), (lid, ln)):
            pid, h = _text(pid).strip(), by_key.get(B.S.name_key(str(name)))
            if pid and h is not None:
                seen.setdefault((str(tour), pid), set()).add(h)
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}


def handle_of(handles: dict, tour: str, row_id, stage0_id) -> str:
    """A player's id in a live row's match id: the one Stage 0 gives the id the row carries (id_handles), else the
    player's Stage 0 id (a row without an id, or an id no Stage 0 match from a TML row carries)."""
    return handles.get((str(tour), _text(row_id).strip()), str(stage0_id))


def _text(v) -> str:
    """A Stage 0 value as TML writes it: blank for a missing one, integers without a decimal point."""
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def player_columns(raw: pd.DataFrame, tour: str, name_key: str, event: pd.DataFrame, event_date: str | None = None,
                   fallback: pd.DataFrame | None = None) -> dict:
    """A player's TML columns (B.BIO): from their row at the event, else their latest row, aged to the event's date
    (event_date, YYYYMMDD, for an event TML holds no row of; else its rows' first date). fallback (stage0_players): a
    player no TML row names takes their latest Stage 0 row, aged likewise, with a blank id (Stage 0's C60 resolves it
    by the unambiguous name)."""
    when = event_date if event_date else str(event["tourney_date"].min())
    for rows, at_event in ((event, True), (raw[raw["tour"].eq(tour)], False)):
        hits = []
        for side in ("winner", "loser"):
            hit = rows[B.S.keys_for(rows[f"{side}_name"]).eq(name_key)]
            if len(hit):
                last = latest(hit).iloc[-1]
                hits.append((str(last["tourney_date"]), {b: last[f"{side}_{b}"] for b in B.BIO}))
        if hits:
            cols = max(hits, key=lambda h: h[0])[1]
            if not at_event:
                cols["age"] = _aged(cols["age"], _days(when, max(hits, key=lambda h: h[0])[0]))
                cols["seed"], cols["entry"] = "", ""
            return cols
    if fallback is not None:
        hit = fallback[fallback["tour"].eq(tour) & fallback["key"].eq(name_key)]
        if len(hit):
            last = hit.sort_values(["d", "match_id"]).iloc[-1]
            return {"id": "", "seed": "", "entry": "", "name": str(last["player_name"]), "hand": _text(last["hand"]),
                    "ht": _text(last["height"]), "ioc": _text(last["country"]),
                    "age": _aged(last["age"], _days(when, last["d"])), "rank": _text(last["rank"]),
                    "rank_points": _text(last["rank_points"])}
    raise SystemExit(f"live rows: no TML row names the player {name_key!r} ({tour})")


def csv_event(m) -> dict | None:
    """The event's columns from a matchups row that carries them (CSV_EVENT, with its tourney_id, tourney_name and
    best_of), as TML would write them; None when the row carries none. The indoor flag may be blank, as TML leaves it
    in every women's row (their indoor input comes from the WTA's calendar)."""
    given = {k: m.get(k) for k in CSV_EVENT}

    def blank(v) -> bool:
        return v is None or (not isinstance(v, str) and pd.isna(v)) or not str(v).strip()
    if all(blank(v) for v in given.values()):
        return None
    missing = [k for k, v in given.items() if blank(v) and k != "event_indoor"]
    name = m.get("tourney_name")
    if missing or not (isinstance(name, str) and name.strip()):
        raise SystemExit(f"live rows: {m['tour']} event {m['tourney_id']}: the event's columns are incomplete "
                         f"(missing: {missing + ([] if isinstance(name, str) and name.strip() else ['tourney_name'])})")
    row = {"tourney_id": str(m["tourney_id"]), "tourney_name": name.strip(),
           "best_of": str(int(float(m["best_of"]))) if pd.notna(m.get("best_of")) and str(m.get("best_of")).strip()
           else "3"}
    for k, col in CSV_EVENT.items():
        v = given[k]
        if blank(v):                                 # the indoor flag only (the others are required above)
            row[col] = ""
        elif col in ("draw_size", "tourney_date"):
            row[col] = str(int(float(v)))
        else:                                        # a CSV reads TML's level "250" back as 250.0 beside blank rows
            text = str(v).strip()
            row[col] = text[:-2] if col == "tourney_level" and text.endswith(".0") and text[:-2].isdigit() else text
    return row


def main_draw_date(event: pd.DataFrame, m, matchups: pd.DataFrame) -> str | None:
    """A live main-draw row's event date (YYYYMMDD) as Stage 0 dates a played event (C05: its earliest main-draw row):
    the earliest of the days known of the event's main draw, none of which can precede its first day: the earliest
    main-draw row TML holds of the event, and each of the CSV's main-draw matches of the event, by the linker's day
    where it gives one (event_main_date: the main draw's first day as TennisLive and the listing tell, in the venue's
    zone), else by its own day. TML's file of events under way can date the first day late (Almaty's and Brussels' 19
    Oct 2026 read 20 Oct there until 23 Oct), and the CSV's own day is the UK one (Auckland's 11:00 start is the day
    before). None for a qualifying round."""
    if QUALIFYING_ROUND.match(str(m["round"]).strip().upper()):
        return None
    known = []
    main = event[~event["round"].astype(str).str.strip().str.upper().str.match(r"^Q\d$")]
    if len(main):
        known.append(str(latest(main).iloc[0]["tourney_date"]))
    same = matchups[matchups["tour"].eq(m["tour"]) & matchups["tourney_id"].astype(str).eq(str(m["tourney_id"]))
                    & ~matchups["round"].astype(str).str.strip().str.upper().str.match(r"^Q\d$")]
    for _, s in same.iterrows():
        given = s.get("event_main_date")
        if given is not None and not (not isinstance(given, str) and pd.isna(given)) and str(given).strip():
            known.append(str(int(float(given))))
        elif pd.notna(day := pd.to_datetime(s["day"], errors="coerce")):
            known.append(day.strftime("%Y%m%d"))
    return min(known) if known else None


def upcoming_rows(matchups: pd.DataFrame, raw: pd.DataFrame, players: pd.DataFrame | None = None,
                  failed: dict | None = None) -> pd.DataFrame:
    """Upcoming matches as live rows. ``matchups`` holds, per match: tour, tourney_id (TML's, zero padding removed, e.g.
    2026-5014), tourney_name (needed when TML reuses the id), round, player_a, player_b (names as TML writes them), and
    optionally best_of; for an event TML holds no row of, the event's columns (CSV_EVENT). players (stage0_players):
    the fallback of a player no TML row names. The placeholder is won by player_a. Each row's _row is its position in
    ``matchups``. failed (a dict; the daily engine's live runs since 28 Oct 2026: docs/decisions/2026-10-28-one-bad-
    match-left-out.md): a row that cannot be built is left out, its reason put in failed under its position, and the
    others are built (an empty frame when none is); without it, any such row stops the run, as before."""
    out = []
    for i, m in matchups.reset_index(drop=True).iterrows():
        try:
            out.append(_upcoming_row(i, m, matchups, raw, players))
        except (SystemExit, Exception) as exc:  # noqa: BLE001 - one row's failure, kept with its reason
            if failed is None:
                raise
            failed[i] = P.reason_of(exc)
    if failed is not None and not out:
        return pd.DataFrame()
    return outcome_removed(pd.DataFrame(out))


def _upcoming_row(i: int, m: pd.Series, matchups: pd.DataFrame, raw: pd.DataFrame,
                  players: pd.DataFrame | None) -> dict:
    """One matchups row (position i) as its live row, before outcome_removed."""
    name = m.get("tourney_name") if isinstance(m.get("tourney_name"), str) and m.get("tourney_name") else None
    event = event_rows(raw, m["tour"], m["tourney_id"], name)
    event_date = None
    if event.empty:
        row = csv_event(m)
        if row is None:
            raise SystemExit(f"live rows: no TML row of {m['tour']} event {m['tourney_id']} {name or ''}")
        event_date = row["tourney_date"]
    else:
        first = latest(event).iloc[0]
        row = {c: first[c] for c in EVENT}
        if pd.notna(m.get("best_of")) and str(m.get("best_of")).strip():
            row["best_of"] = str(int(float(m["best_of"])))
        if os.environ.get(MAIN_DATE_SWITCH) != "0":       # the main draw's first date (module docstring)
            main = main_draw_date(event, m, matchups)
            if main:
                row["tourney_date"] = event_date = main
    for side, who in (("winner", "player_a"), ("loser", "player_b")):
        cols = player_columns(raw, m["tour"], B.S.name_key(str(m[who])), event, event_date, players)
        row.update({f"{side}_{b}": v for b, v in cols.items()})
    main = m.get("event_main_date")             # a qualifying match: its main draw's start (Stage 0's C05)
    if (QUALIFYING_ROUND.match(str(m["round"]).strip().upper()) and main is not None
            and not (not isinstance(main, str) and pd.isna(main)) and str(main).strip()):
        row["event_main_date"] = str(int(float(main)))
    row.update({"round": str(m["round"]).upper(), "match_num": str(LIVE_MATCH_NUM + i), "tour": m["tour"],
                "live_role": "live", "_source_file": "live_rows", "_row": i})
    return row
