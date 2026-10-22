"""Upcoming matches as Tennis My Life rows (Stage 0's --live-rows), and each one's price, day and venue.

A live row is the row TML will publish once the match is played, less what only playing it gives: the result (a
placeholder: one fixed player wins in straight sets), the games, the minutes and the box score. Every other column comes
from TML itself, so Stage 0 and every builder after it treat the row as one of the event's own:
    the event's columns (id, name, surface, draw size, level, indoor, date) from the event's own TML rows;
    each player's columns (id, seed, entry, name, hand, height, country, age, rank, points) from the player's latest row
    at the event (TML repeats them in every round), else from the player's latest row anywhere, aged to the event's date.
The placeholder never reaches the match's own inputs: every builder reads only earlier matches (the replay checks it).

What Stage 0 does not hold and the sandbox's tables need goes in the run's meta table (inject.py): the match id Stage 0
gives the row, the day it is dated by, the price, and the event's city.

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
"""
from __future__ import annotations

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


def upcoming_rows(matchups: pd.DataFrame, raw: pd.DataFrame, players: pd.DataFrame | None = None) -> pd.DataFrame:
    """Upcoming matches as live rows. ``matchups`` holds, per match: tour, tourney_id (TML's, zero padding removed, e.g.
    2026-5014), tourney_name (needed when TML reuses the id), round, player_a, player_b (names as TML writes them), and
    optionally best_of; for an event TML holds no row of, the event's columns (CSV_EVENT). players (stage0_players):
    the fallback of a player no TML row names. The placeholder is won by player_a."""
    out = []
    for i, m in matchups.reset_index(drop=True).iterrows():
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
        for side, who in (("winner", "player_a"), ("loser", "player_b")):
            cols = player_columns(raw, m["tour"], B.S.name_key(str(m[who])), event, event_date, players)
            row.update({f"{side}_{b}": v for b, v in cols.items()})
        main = m.get("event_main_date")             # a qualifying match: its main draw's start (Stage 0's C05)
        if main is not None and not (not isinstance(main, str) and pd.isna(main)) and str(main).strip():
            row["event_main_date"] = str(int(float(main)))
        row.update({"round": str(m["round"]).upper(), "match_num": str(LIVE_MATCH_NUM + i), "tour": m["tour"],
                    "live_role": "live", "_source_file": "live_rows", "_row": i})
        out.append(row)
    return outcome_removed(pd.DataFrame(out))
