"""Section A's prediction-time inputs: the day's matches and their bet-time prices, as the daily pipeline's matchups CSV.

Agreed with the daily_prediction session (process log, 10:20): this layer writes prediction_run's MATCHUP_COLUMNS
(tour, tourney_id, round, player_a, player_b, day, p_a; optional tourney_name, best_of, start_utc; and quoted_at, the
quote's own time), and the daily pipeline turns p_a to Stage 0's side A itself.

    record_pinnacle()   one pull of Pinnacle's listed tennis matchups and moneylines (src/ingest/pinnacle.py)
    todays_matches()    the pull's pre-match main-tour singles, each linked to Tennis My Life's event and to the names
                        and ids Stage 0 knows, with a status and a reason for every row left out
    build_matchups()    the linked rows as the matchups CSV (player_a = Pinnacle's home player, p_a = his margin-free
                        chance, both from the same participant record; the resolved Stage 0 ids ride along)
    check_matchups()    the daily pipeline's own refusals, checked before the expensive run: since 28 Oct 2026 a match
                        that fails one stops nothing; it is said loudly and A4 leaves it out (docs/decisions/
                        2026-10-28-one-bad-match-left-out.md), as an error while linking one listing leaves it out
    manual_matchups()   the fallback: a CSV from rows typed in the notebook (prices as odds of both players, or p_a)
    live_prices()       a fresh Pinnacle price for a run's matches, oriented to side A (for reprice)

What can be priced (the model's population and the daily pipeline's limits):
    * the tours of config.BET_TOURS: since 28 Oct 2026 the men's only (the owner: women's matches switched off for the
      bet day, docs/decisions/2026-10-28-women-switched-off.md). A women's listing is left out before any linking;
    * ATP/WTA main-tour singles (Slams, Finals, 1000s, 500s, 250s): Challengers, WTA 125s, ITF, team events, doubles and
      in-play markets are left out;
    * since 22 Oct 2026 the qualifying of those events too (the owner's decision: docs/decisions/2026-10-22-qualifying-
      bets.md), its event and round found as qualifying.py describes: the event from Tennis My Life's rows of the
      edition, else built from its previous edition (round 1, women's qualifying); the round from TennisLive's results
      of the event, checked against Tennis My Life's. The qualifying of Challengers, WTA 125s and ITF events stays out;
    * a main-draw match's event must already have Tennis My Life rows (a played match), so first rounds wait until the
      event has begun;
    * each name must name exactly one Stage 0 player of the tour (by prediction_run's name key: accents, case and
      punctuation removed, words sorted). The run could not place an ambiguous name, so its match is left out. Names
      Pinnacle spells differently go in config/player_aliases.csv (columns pinnacle_name, tour, tml_name). No fuzzy
      matching: near-namesakes are real (Xinyu Wang / Xiyu Wang).
"""
from __future__ import annotations

import datetime as dt
import math
import re
import sys
from pathlib import Path

import pandas as pd

from . import config as CFG
from . import qualifying as Q
from .runner import Step, run_step

if str(CFG.ROOT) not in sys.path:
    sys.path.insert(0, str(CFG.ROOT))
from src.eda.merge_feasibility.scan import name_key, norm  # noqa: E402  (prediction_run's key, imported, not copied)

MATCHUP_COLUMNS = ["tour", "tourney_id", "round", "player_a", "player_b", "day", "p_a"]
# a qualifying match's event built from its previous edition (prediction_run/live_rows.CSV_EVENT reads the first five),
# where it came from, and a men's Slam qualifying round's best-of when its previous edition played 5
EVENT_COLUMNS = ["event_surface", "event_draw_size", "event_level", "event_indoor", "event_date", "event_main_date",
                 "event_from", "event_best_of"]
MAIN_TML_LEVELS = {"G", "M", "A", "F", "P", "PM", "I", "1000", "500", "250"}
NAMED_ROUNDS = {"QF": "QF", "SF": "SF", "F": "F", "FINAL": "F", "SEMIFINAL": "SF", "SEMIFINALS": "SF",
                "QUARTERFINAL": "QF", "QUARTERFINALS": "QF"}
ROUND_ORDER = ["R128", "R64", "R32", "R16", "QF", "SF", "F"]
EVENT_STOPWORDS = {"open", "masters", "master", "championships", "championship", "tennis", "international",
                   "internationals", "classic", "atp", "wta", "presented", "by", "the", "de", "of", "s"}
# Pinnacle's staging reasons (src/ingest/pinnacle.py) for a pre-match price still listed after its listed start or its
# market's cutoff, the match not in play. Since 24 Oct 2026 such a match is linked and repriced like any other (the
# owner: a start time never withholds a prediction; Pinnacle often pushes a tennis start back and reopens the market).
# In-play markets stay out: a live price is never the model's input.
PAST_LISTED_START = {"start not after the pull", "market cutoff not after the pull"}


def event_tokens(name) -> frozenset:
    return frozenset(t for t in norm(name).split() if t not in EVENT_STOPWORDS and not t.isdigit())


# --- the Pinnacle pull ---------------------------------------------------------------------------------------------------
def record_pinnacle(*, force: bool = False, dry_run: bool = False) -> pd.DataFrame:
    """One pull of Pinnacle's listing (three paced GETs; raw copies and receipts kept; a pull under a minute after the
    last reuses it). Returns the pull's rows: every match moneyline, usable or not, with the reason."""
    run_step(Step("pinnacle_pull", ["-m", "src.ingest.pinnacle"] + (["--force"] if force else [])), dry_run=dry_run)
    return pd.DataFrame() if dry_run else latest_pull()


def latest_pull() -> pd.DataFrame:
    from src.ingest import pinnacle as PN
    return PN.latest_pull()


# --- the reference tables: Tennis My Life's staged rows and Stage 0's players --------------------------------------------
def _tml(seasons: list[int]) -> pd.DataFrame:
    """Tennis My Life's staged rows, read as prediction_run reads them (prediction_run/live_rows.staged_tml)."""
    from src.eda.prediction_run import live_rows as LR
    raw = LR.staged_tml(seasons)
    raw["_tid"] = raw["tourney_id"].astype(str).str.replace(r"-0+(\d)", r"-\1", regex=True)
    raw["_date"] = pd.to_datetime(raw["tourney_date"].astype(str), format="%Y%m%d", errors="coerce")
    raw["_wk"] = raw["winner_name"].map(name_key)
    raw["_lk"] = raw["loser_name"].map(name_key)
    return raw


def _stage0_keys(tour: str) -> pd.DataFrame:
    """Stage 0's players of a tour with their name keys (the repository's Stage 0; players new since its build are
    found in Tennis My Life's rows instead, and the run's refreshed Stage 0 holds them). The decided id aliases apply
    as in every Stage 0 build, so a second id merged since the repository's build names its player once (Jakub
    Mensik's, 28 Oct 2026)."""
    p = pd.read_parquet(CFG.STAGE0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name"])
    p = p[p["match_id"].astype(str).str.startswith(f"{tour}|")]
    p = p.assign(player_id=p["player_id"].replace(_id_aliases(tour)))
    u = p.drop_duplicates(["player_id", "player_name"])
    return u.assign(key=u["player_name"].map(name_key))


def _id_aliases(tour: str) -> dict:
    """The decided id aliases of a tour (stage0_build's id_aliases.csv): a player's second id -> his established id."""
    from src.eda.input_data_audit import corrections as X
    if not X.ID_ALIASES.exists():
        return {}
    a = pd.read_csv(X.ID_ALIASES, dtype=str)
    a = a[a["tour"].eq(tour)]
    return dict(zip(a["from_id"], a["to_id"]))


def _aliases() -> dict:
    if not CFG.ALIASES.exists():
        return {}
    a = pd.read_csv(CFG.ALIASES)
    return {(str(r["tour"]).lower(), name_key(r["pinnacle_name"])): str(r["tml_name"]) for _, r in a.iterrows()}


# --- linking ---------------------------------------------------------------------------------------------------------------
def _round(phase: str | None, draw_size) -> str | None:
    """Pinnacle's phase as Tennis My Life's round: named rounds as they are; R1, R2, ... counted from the event's
    bracket (its draw size rounded up to a power of two: Shanghai's 96 draw has R1 = R128, R2 = R64, R3 = R32)."""
    if not phase:
        return None
    ph = phase.strip().upper().replace(" ", "")
    if ph in NAMED_ROUNDS:
        return NAMED_ROUNDS[ph]
    if ph in ("R16", "R32", "R64", "R128"):              # Pinnacle also names a round by its draw ("ATP Shanghai - R16")
        return ph
    m = re.match(r"^R(\d)$", ph)                         # else by its number (R1, R2, ...)
    if m and draw_size is not None and not pd.isna(draw_size) and str(draw_size).strip():
        bracket = 2 ** math.ceil(math.log2(max(2, int(float(draw_size)))))
        size = bracket // (2 ** (int(m.group(1)) - 1))
        if size < 2:
            return None
        return {2: "F", 4: "SF", 8: "QF"}.get(size, f"R{size}")
    return None


def _events(tml: pd.DataFrame, tour: str, day: pd.Timestamp) -> pd.DataFrame:
    """Tennis My Life's MAIN-TOUR events of a tour with a row dated in the 16 days to the match day."""
    recent = tml[tml["tour"].eq(tour) & tml["_date"].between(day - pd.Timedelta(days=16), day + pd.Timedelta(days=1))
                 & tml["tourney_level"].astype(str).isin(MAIN_TML_LEVELS)]
    if recent.empty:
        return pd.DataFrame(columns=["_tid", "tourney_name", "tourney_level", "draw_size", "best_of", "last", "tokens"])
    g = recent.groupby(["_tid", "tourney_name"], as_index=False).agg(
        tourney_level=("tourney_level", "last"), draw_size=("draw_size", "last"), best_of=("best_of", "last"),
        last=("_date", "max"))
    g["tokens"] = g["tourney_name"].map(event_tokens)
    return g


def _match_event(event: str, cands: pd.DataFrame) -> tuple[pd.Series | None, str | None]:
    """Exact name tokens first; else one event whose tokens contain Pinnacle's or are contained in them."""
    want = event_tokens(event)
    if not want or cands.empty:
        return None, "no main-tour Tennis My Life event in the last 16 days (first rounds wait for a played match)"
    for rule in (lambda t: t == want, lambda t: bool(t) and (t <= want or want <= t)):
        hit = cands[cands["tokens"].map(rule)]
        if hit["_tid"].nunique() == 1:
            return hit.sort_values("last").iloc[-1], None
        if hit["_tid"].nunique() > 1:
            return None, f"{event!r} matches several events: {sorted(hit['tourney_name'].unique())}"
    return None, (f"no main-tour Tennis My Life event named like {event!r} in the last 16 days "
                  "(a first round waits for the event's first played match)")


def _player(name: str, tour: str, stage0: pd.DataFrame, tml_tour: pd.DataFrame, aliases: dict
            ) -> tuple[str | None, str | None, str]:
    """(the name Stage 0 knows, its Stage 0 id, a note). (None, None, reason) when not exactly one player."""
    key = name_key(aliases.get((tour, name_key(name)), name))
    hits = stage0[stage0["key"].eq(key)]
    ids = hits["player_id"].unique()
    if len(ids) == 1:
        return str(hits["player_name"].iloc[0]), str(ids[0]), "stage0"
    if len(ids) > 1:
        return None, None, (f"{name!r} names {len(ids)} Stage 0 players ({', '.join(map(str, ids))}): the run could not "
                            "place it")
    for side, k in (("winner_name", "_wk"), ("loser_name", "_lk")):
        hit = tml_tour.loc[tml_tour[k].eq(key), side]
        if len(hit):
            return str(hit.iloc[0]), None, f"{hit.iloc[0]} is new since the shared Stage 0 (found in Tennis My Life)"
    return None, None, f"{name!r} is unknown to Stage 0 and Tennis My Life (add an alias in {CFG.rel(CFG.ALIASES)}?)"


def _tl_player(name: str, tour: str, stage0: pd.DataFrame, tml_tour: pd.DataFrame, aliases: dict
               ) -> tuple[str | None, str | None, str]:
    """A TennisLive name as _player reads it; one unknown there, as the one Stage 0 player whose name is another
    spelling of it (earlier_rounds.same_player: TennisLive adds given names, "Chak Lam Coleman Wong" for "Coleman
    Wong"). Two or more such players: unknown, as before."""
    from src.eda.prediction_run import earlier_rounds as ER
    got = _player(name, tour, stage0, tml_tour, aliases)
    if got[0] is not None or re.search(r" names \d+ Stage 0 players", got[2]):     # found, or ambiguous already
        return got
    words = norm(name).split()
    if not words:
        return got
    near = stage0[stage0["key"].map(lambda k: words[-1] in k.split() or words[0] in k.split())]
    hits = near[near["player_name"].map(lambda n: ER.same_player(name, n))].drop_duplicates("player_id")
    if len(hits) == 1:
        h = hits.iloc[0]
        return str(h["player_name"]), str(h["player_id"]), f"TennisLive's {name!r} read as {h['player_name']!r}"
    return got


def _event_current(event_rows: pd.DataFrame, rnd: str, day: pd.Timestamp) -> str | None:
    """A reason the Tennis My Life event cannot be the listed match's: its final is played (the event is over: the
    listing is a new event of the same name, e.g. Adelaide 1 then Adelaide 2), or its latest match is more than a week
    before the listed day (review V1, item 6). A later round played elsewhere in the draw is not a reason: after rain,
    one half of a draw can be a round behind the other."""
    if event_rows["round"].astype(str).eq("F").any():
        return f"the Tennis My Life event's final is played: the listing ({rnd}) is a new event of the same name?"
    last = event_rows["_date"].max()
    if pd.notna(last) and (day - last).days > 7:
        return f"the Tennis My Life event's latest match is {last:%Y-%m-%d}, over a week before the listed day"
    return None


def _evidence(event_rows: pd.DataFrame, rnd: str, a: str, b: str) -> str | None:
    """A reason to leave the match out, from the players' Tennis My Life rows at the event: the match already
    played, a player already out, or a player whose last win there is not the round before (a wrong round)."""
    ka, kb = name_key(a), name_key(b)
    same = event_rows["round"].astype(str).eq(rnd) & (((event_rows["_wk"] == ka) & (event_rows["_lk"] == kb))
                                                       | ((event_rows["_wk"] == kb) & (event_rows["_lk"] == ka)))
    if same.any():
        return "already played (Tennis My Life holds the result)"
    if rnd not in ROUND_ORDER:
        return None
    before = ROUND_ORDER[ROUND_ORDER.index(rnd) - 1] if ROUND_ORDER.index(rnd) > 0 else None
    for k, n in ((ka, a), (kb, b)):
        if (event_rows["_lk"] == k).any():
            return f"{n} already lost at this event"
        won = event_rows.loc[event_rows["_wk"] == k, "round"].astype(str)
        won = [r for r in won if r in ROUND_ORDER]
        if won:
            last = max(won, key=ROUND_ORDER.index)
            if last != before:
                return f"round check: {n}'s last win here is {last}, not {before} (Pinnacle's round read as {rnd})"
    return None


class _Qualifying:
    """What linking a listing's qualifying matches reads once: TennisLive (one session, each event's results once) and
    the shared Stage 0's round-1 counts of past editions (the round check's "round 1 looks complete")."""

    def __init__(self, tennislive: "Q.TennisLive | None" = None):
        self._tl = tennislive
        self._rounds = None
        self._dates = None
        self.editions: dict = {}

    def edition_date(self, tour: str, tid: str) -> pd.Timestamp | None:
        """A past edition's date in the shared Stage 0 (its main draw's rows; else its qualifying's): the weekday the
        main draw's start is estimated on (qualifying.main_draw_start)."""
        if self._dates is None:
            self._dates = pd.read_parquet(CFG.STAGE0 / "stage0_matches.parquet",
                                          columns=["tour", "tournament_id", "tournament_date", "qualifying"])
        d = self._dates
        hit = d[d["tour"].eq(tour) & (d["tournament_id"].astype(str).eq(tid)
                                      | d["tournament_id"].astype(str).str.startswith(tid + "-"))]
        main = hit[~hit["qualifying"].astype(bool)]
        dates = (main if len(main) else hit)["tournament_date"]
        return pd.Timestamp(dates.mode().iloc[0]) if len(dates) else None

    def tennislive(self) -> "Q.TennisLive":
        if self._tl is None:
            self._tl = Q.TennisLive()
        return self._tl

    def round1_size(self, tour: str, prev: dict | None) -> int | None:
        if prev is None:
            return None
        if self._rounds is None:
            m = pd.read_parquet(CFG.STAGE0 / "stage0_matches.parquet", columns=["tour", "tournament_id", "round"])
            self._rounds = m[m["round"].astype(str).eq("Q1")]
        tid = str(prev["tid"])
        hit = self._rounds[self._rounds["tour"].eq(tour) & (self._rounds["tournament_id"].astype(str).eq(tid)
                                                           | self._rounds["tournament_id"].astype(str).str.startswith(tid + "-"))]
        return int(len(hit)) or None

    def previous(self, tml: pd.DataFrame, tour: str, event: str, day: pd.Timestamp) -> tuple[dict | None, str]:
        key = (tour, event, day.year)
        if key not in self.editions:
            self.editions[key] = Q.previous_edition(tml, tour, event, day, MAIN_TML_LEVELS)
        return self.editions[key]


def _earlier(rows: pd.DataFrame, rnd: str, players: list[tuple[str, set]], event_rows: pd.DataFrame, tour: str,
             tid: str, name: str, stage0: pd.DataFrame, tour_rows: pd.DataFrame, aliases: dict, ctx: _Qualifying,
             level, prev: dict | None, built: dict | None, main: str | None, losses: bool = False
             ) -> tuple[list[dict], list[str]]:
    """The players' earlier rounds at the event that Tennis My Life does not hold yet with a box score (qualifying.py's
    "earlier rounds"): one sidecar row each, with its score and its TennisLive match page's box score; and notes on any
    left out. A round Tennis My Life holds as a result only (Vienna's and Basel's round 1, about 21:00 PDT on 24 Oct
    2026) is kept: the run gives its row TennisLive's box score (prediction_run/run.tml_box_fills). event_rows: Tennis My
    Life's qualifying rows of the edition. losses (a main-draw match): a lucky loser's lost round too. Best of: 3, or a
    men's Slam qualifying round's 5 (qualifying.best_of), never the event's main-draw value."""
    from src.eda.prediction_run import earlier_rounds as ER
    out, notes = [], []
    for player, keys in players:
        for _, w in Q.earlier_matches(rows, keys, rnd, losses).iterrows():
            r, side, won = str(w["round"]), int(w["_side"]), bool(w["_won"])
            wside = side if won else 3 - side              # the winner's side in TennisLive's row
            held = event_rows[(event_rows["round"].astype(str).str.upper() == r)
                              & (event_rows["_wk" if won else "_lk"] == name_key(player))]
            if len(held) and held.get("w_svpt", pd.Series(dtype=str)).astype(str).str.strip().replace(
                    {"nan": "", "None": ""}).ne("").any():
                continue                                   # Tennis My Life holds it with its box score: its row alone
            opp_tl = str(w[f"player{3 - side}_name"])
            opp, _, note = _tl_player(opp_tl, tour, stage0, tour_rows, aliases)
            if opp is None:
                notes.append(f"{player}'s {r} (v {opp_tl}) not filled: {note}")
                continue
            winner, loser = (player, opp) if won else (opp, player)
            walkover = str(w["state"]) in ("walkover", "awarded") or str(w.get("end_reason")) == "walkover"
            score = "W/O" if walkover else ER.tl_score(w["player1_sets"], w["player2_sets"], wside, w.get("end_reason"))
            box, box_note = None, "a walkover: no box score"
            if not walkover:
                page = ctx.tennislive().page(str(w["url"]))
                if page is None:
                    box_note = f"no match page ({ctx.tennislive().stopped or 'not served'})"
                else:
                    pm = page["meta"]
                    pw = 2 if str(pm.get("winner_id")) == str(pm.get("player2_id")) else 1
                    # the player is the page's winner, or its loser in a lost round
                    if not (Q.player_keys(pm.get(f"player{pw if won else 3 - pw}_name")) & keys):
                        box_note = "the match page's winner is not the listing's: its statistics not used"
                    else:
                        box, box_note = ER.tl_box(page["statistics"], pw, pm.get("first_server_index"), score)
            fin = ER.finish_utc(w)
            # dated as the live matches are (prediction_run/run.uk_day): the UK day of its start
            day = ER.uk_day(pd.to_datetime(w.get("start_utc"), utc=True, errors="coerce")) or ER.uk_day(fin)
            row = {"tour": tour, "tourney_id": tid, "tourney_name": name, "round": r, "winner_name": winner,
                   "loser_name": loser, "winner_tl": w[f"player{wside}_name"], "loser_tl": w[f"player{3 - wside}_name"],
                   "score": score, "start_utc": w.get("start_utc"),
                   "finished_utc": None if fin is None else fin.isoformat(), "day": day, "tl_url": w["url"],
                   "tl_match_id": w["match_id"], "box_note": box_note, "event_main_date": main,
                   **({k: v for k, v in built.items() if k.startswith("event_")} if built else {}), **(box or {})}
            row["best_of"] = Q.best_of(tour, level, r, prev) or 3
            out.append(row)
    return out, notes


def _qualifiers(rec: dict, r: pd.Series, ev: pd.Series, a: str, b: str, tml: pd.DataFrame, stage0: pd.DataFrame,
                aliases: dict, uk: pd.Timestamp, ctx: _Qualifying) -> list[str]:
    """A main-draw match's qualifiers and lucky losers (since 25 Oct 2026): every qualifying match either player
    played at the event, from TennisLive's results, unless Tennis My Life holds it with its box score (_earlier), into
    rec["earlier"]; notes. Tennis My Life's qualifying rows of the edition are found under the main draw's id, else by
    the event's name in the three weeks before its latest row (Shanghai 2026 filed its qualifying under an id of its
    own). A player with no qualifying match at the event gives none. Since 27 Oct 2026, also the main draw's first day
    as TennisLive and the listing tell, in the venue's zone, into rec["event_main_date"] (qualifying.main_draw_first_day;
    prediction_run/live_rows.main_draw_date)."""
    tour, day = r["tour"], pd.Timestamp(uk.date())
    tl_event, tl_note = ctx.tennislive().event(tour, str(r["event"]), uk.date())
    rows = None if tl_event is None else ctx.tennislive().results(tl_event)
    if rows is None:
        why = tl_note or f"TennisLive's results did not come ({ctx.tennislive().stopped or 'no answer'})"
        return [f"qualifiers' rounds not checked: {why}"]
    first = Q.main_draw_first_day(rows, tl_event, str(ev["tourney_name"]), r.get("start_utc"))
    if first:                                            # Tennis My Life's file of events under way can date it late
        rec["event_main_date"] = first
    tour_rows = tml[tml["tour"].eq(tour)]
    qual = tour_rows["round"].astype(str).str.upper().str.fullmatch(r"Q\d")
    named = tour_rows["tourney_name"].astype(str).eq(str(ev["tourney_name"])) & tour_rows["_date"].between(
        ev["last"] - pd.Timedelta(days=21), ev["last"])
    held = tour_rows[qual & (tour_rows["_tid"].eq(ev["_tid"]) | named)]
    prev, _ = ctx.previous(tml, tour, str(r["event"]), day)
    earlier, notes = _earlier(rows, rec["round"], [(a, Q.player_keys(a, r["home"])), (b, Q.player_keys(b, r["away"]))],
                              held, tour, ev["_tid"], ev["tourney_name"], stage0, tour_rows, aliases, ctx,
                              ev["tourney_level"], prev, None, None, losses=True)
    rec["earlier"] = earlier
    if earlier:
        notes.insert(0, f"{len(earlier)} qualifying round(s) of its qualifiers from TennisLive (live only, until Tennis "
                        f"My Life or the feed publishes them; {sum(bool(e.get('w_svpt')) for e in earlier)} with a box "
                        "score)")
    return notes


def _link_qualifying(rec: dict, r: pd.Series, tml: pd.DataFrame, stage0: pd.DataFrame, aliases: dict,
                     uk: pd.Timestamp, ctx: _Qualifying) -> None:
    """A listed tour-level qualifying match (qualifying.py): its event (Tennis My Life's edition, else built from the
    previous edition), its players, its round (TennisLive's results, else Tennis My Life's), into rec."""
    tour, event, day = r["tour"], str(r["event"]), pd.Timestamp(uk.date())
    qual_rows = tml[tml["round"].astype(str).str.upper().str.fullmatch(r"Q\d")]
    ev, why = _match_event(event, _events(qual_rows, tour, day))      # the edition's qualifying rows first
    if ev is None:
        ev, why = _match_event(event, _events(tml, tour, day))       # then its main draw (begun)
    prev, prev_note = ctx.previous(tml, tour, event, day)
    built = None
    if ev is None:
        if prev is None:
            rec["reason"] = (f"qualifying: no Tennis My Life rows of the event, and its previous edition is not found "
                             f"({prev_note})")
            return
        try:
            built = Q.built_event(prev, day)
        except ValueError as exc:
            rec["reason"] = f"qualifying: {exc}"
            return
        tid, name, level, draw = built["tourney_id"], built["tourney_name"], prev["level"], prev["draw_size"]
        event_rows = tml.iloc[0:0]
    else:
        tid, name, level, draw = ev["_tid"], ev["tourney_name"], ev["tourney_level"], ev["draw_size"]
        event_rows = tml[tml["tour"].eq(tour) & tml["_tid"].eq(tid)]
        stale = _event_current(event_rows, "Q", day)
        if stale:
            rec["reason"] = f"qualifying: {stale}"
            return
    rec.update(tourney_id=tid, tourney_name=name)
    tour_rows = tml[tml["tour"].eq(tour)]
    a, ida, note_a = _player(r["home"], tour, stage0, tour_rows, aliases)
    b, idb, note_b = _player(r["away"], tour, stage0, tour_rows, aliases)
    if a is None or b is None:
        rec["reason"] = note_a if a is None else note_b
        return
    rnd, how, tl_note, rows = None, "", "", None
    tl_event, tl_note = ctx.tennislive().event(tour, event, uk.date())
    if tl_event is not None:
        rows = ctx.tennislive().results(tl_event)
        if rows is None:
            tl_note = f"TennisLive's results did not come ({ctx.tennislive().stopped or 'no answer'})"
        else:
            rnd, how = Q.round_from_results(rows, Q.player_keys(a, r["home"]), Q.player_keys(b, r["away"]), (a, b),
                                            ctx.round1_size(tour, prev))
            if rnd is None:
                rec["reason"] = f"qualifying: {how}"
                return
            bad = Q.tml_agrees(event_rows, a, b, rnd)
            if bad:
                rec["reason"] = f"qualifying round check: {bad}, while TennisLive reads {rnd}"
                return
    if rnd is None:                                    # TennisLive gave nothing: Tennis My Life's rows alone
        rnd, how = Q.round_from_tml(event_rows, a, b)
        if rnd is None:
            rec["reason"] = f"qualifying: {how}" + (f" ({tl_note})" if tl_note else "")
            return
    played = _evidence(event_rows, rnd, a, b)
    if played:
        rec["reason"] = played
        return
    notes = [n for n in (note_a, note_b) if n != "stage0"] + [f"qualifying {rnd}: {how}"]
    if built:
        notes.append(f"event built from its {built['event_from']}")
        rec.update({k: v for k, v in built.items() if k.startswith("event_")})
    # the main draw's start, the date Stage 0 gives a played event's qualifying (C05), for an event whose main draw
    # is not played yet; where it is, Stage 0 takes the main draw's own first date and this is not read
    main = Q.main_draw_start(day, str(level) == "G", ctx.edition_date(tour, prev["tid"]) if prev else None)
    rec["event_main_date"] = main.strftime("%Y%m%d")
    bo = Q.best_of(tour, level, rnd, prev)
    if bo:
        rec["event_best_of"] = bo
        notes.append(f"best of {bo}, as at its previous edition's {rnd}")
    if rnd != "Q1" and rows is not None:              # the earlier rounds Tennis My Life has not published yet
        earlier, left = _earlier(rows, rnd, [(a, Q.player_keys(a, r["home"])), (b, Q.player_keys(b, r["away"]))],
                                 event_rows, tour, tid, name, stage0, tour_rows, aliases, ctx, level, prev, built,
                                 rec["event_main_date"])
        rec["earlier"] = earlier
        if earlier:
            notes.append(f"{len(earlier)} earlier round(s) from TennisLive (live only, until Tennis My Life or the feed "
                         f"publishes them; {sum(bool(e.get('w_svpt')) for e in earlier)} with a box score)")
        notes += left
    rec.update(status="ok", round=rnd, player_a=a, player_b=b, stage0_id_a=ida, stage0_id_b=idb,
               notes="; ".join(notes), qualifying=True, draw_size=draw)


LINK_ERROR = "ERROR while linking this listing"          # an error in one listing's row (28 Oct 2026): it alone is left out


def _link(rec: dict, r: pd.Series, tours: tuple, tml: pd.DataFrame, stage0: dict, aliases: dict,
          qual: _Qualifying) -> None:
    """One listing linked into rec: "ok" with its event, round and players, or "left out" with the reason."""
    uk = pd.Timestamp(r["start_utc"]).tz_convert("Europe/London")
    rec["day"] = uk.date().isoformat()
    off = CFG.tour_off(r["tour"]) if r["tour"] not in tours else None
    if off:                                         # switched off (config.BET_TOURS): every listing says so
        rec["reason"] = off
    elif not r["usable"] and r["reason"] not in PAST_LISTED_START:
        rec["reason"] = r["reason"]
    elif r["tour"] not in tours:
        rec["reason"] = f"tour {r['tour']} (ITF or other)"
    elif r["level"] != "tour":
        rec["reason"] = f"{r['level']} level (outside the model's main-tour population)"
    elif r.get("qualifying"):                       # tour-level qualifying, bet since 22 Oct 2026
        _link_qualifying(rec, r, tml, stage0[r["tour"]], aliases, uk, qual)
    elif re.search(r"\bcup\b", str(r["league"]), flags=re.I):
        rec["reason"] = "a team event (outside the model's population)"
    else:
        ev, why = _match_event(str(r["event"]), _events(tml, r["tour"], pd.Timestamp(uk.date())))
        if ev is None:
            rec["reason"] = why
            return
        rnd = _round(r["phase"], ev["draw_size"])
        rec.update(tourney_id=ev["_tid"], tourney_name=ev["tourney_name"], round=rnd)
        tour_rows = tml[tml["tour"].eq(r["tour"])]
        event_rows = tour_rows[tour_rows["_tid"].eq(ev["_tid"])]
        a, ida, note_a = _player(r["home"], r["tour"], stage0[r["tour"]], tour_rows, aliases)
        b, idb, note_b = _player(r["away"], r["tour"], stage0[r["tour"]], tour_rows, aliases)
        if rnd is None:
            rec["reason"] = f"round {r['phase']!r} not understood"
        elif a is None or b is None:
            rec["reason"] = note_a if a is None else note_b
        else:
            why = _event_current(event_rows, rnd, pd.Timestamp(uk.date())) or _evidence(event_rows, rnd, a, b)
            if why:
                rec["reason"] = why
                return
            notes = [n for n in (note_a, note_b) if n != "stage0"]
            tml_bo = pd.to_numeric(pd.Series([ev["best_of"]]), errors="coerce").iloc[0]
            if pd.notna(r.get("best_of")) and pd.notna(tml_bo) and int(r["best_of"]) != int(tml_bo):
                notes.append(f"Pinnacle says best of {int(r['best_of'])}, Tennis My Life {int(tml_bo)} "
                             "(the model reads Tennis My Life's)")
            notes += _qualifiers(rec, r, ev, a, b, tml, stage0[r["tour"]], aliases, uk, qual)
            rec.update(status="ok", player_a=a, player_b=b, stage0_id_a=ida, stage0_id_b=idb, notes="; ".join(notes))


def todays_matches(*, hours_ahead: float = 36, pull: pd.DataFrame | None = None, now: dt.datetime | None = None,
                   tours: tuple[str, ...] | None = None, tennislive: "Q.TennisLive | None" = None) -> pd.DataFrame:
    """Every pre-match moneyline of the latest Pinnacle pull starting within `hours_ahead` (or still listed pre-match
    after its listed start: PAST_LISTED_START), linked to Tennis My Life's event and to Stage 0's names and ids; `status`
    is "ok" or "left out", with the reason. tours: the tours linked (default config.BET_TOURS; a switched-off tour's
    listings are left out first, with the switch as their reason). Run record_pinnacle() first. An error while linking
    one listing leaves that listing out, its reason starting LINK_ERROR, and the others are linked; one "!!!" line says
    which (since 28 Oct 2026: docs/decisions/2026-10-28-one-bad-match-left-out.md)."""
    tours = CFG.BET_TOURS if tours is None else tuple(tours)
    rows = latest_pull() if pull is None else pull
    if rows.empty:
        raise RuntimeError("no Pinnacle pull yet: run record_pinnacle() first")
    now = now or dt.datetime.now(dt.timezone.utc)
    start = pd.to_datetime(rows["start_utc"], utc=True)
    pre_match = rows["usable"] | rows["reason"].isin(PAST_LISTED_START)
    window = ((start > pd.Timestamp(now)) | pre_match) & (start <= pd.Timestamp(now) + pd.Timedelta(hours=hours_ahead))
    rows = rows[window].copy()
    if rows.empty:
        print(f"no listed match starts in the next {hours_ahead} h")
        return rows.assign(status=pd.Series(dtype=str), reason=pd.Series(dtype=str))
    years = sorted({d.year for d in start[window]} | {now.year - 1})
    tml = _tml(years)
    aliases = _aliases()
    stage0 = {t: _stage0_keys(t) for t in tours}
    qual = _Qualifying(tennislive)                      # TennisLive is asked only when a qualifying match is listed
    out, errors = [], []
    for _, r in rows.iterrows():
        rec = r.to_dict()
        rec.update({"status": "left out", "reason": None, "tourney_id": None, "tourney_name": None, "round": None,
                    "player_a": None, "player_b": None, "stage0_id_a": None, "stage0_id_b": None, "day": None,
                    "notes": ""})
        try:
            _link(rec, r, tours, tml, stage0, aliases, qual)
        except Exception as exc:  # noqa: BLE001 - one listing's error leaves that listing out, never the others
            rec.update(status="left out", reason=f"{LINK_ERROR} ({type(exc).__name__}: {exc})")
            errors.append(rec)
        out.append(rec)
    if errors:                                          # said loudly (the owner, 28 Oct 2026); show_matches lists them
        print(f"!!! ERROR while linking {len(errors)} listing{'s' * (len(errors) != 1)}: left out, no prediction; the "
              f"other {len(out) - len(errors)} listings were linked as usual:")
        for e in errors:
            print(f"!!!   {str(e.get('tour') or '').upper()} {e.get('event')}: {e.get('home')} v {e.get('away')} -- "
                  f"{e['reason']}")
    res = pd.DataFrame(out)
    keep = ["status", "reason", "league", "start_utc", "day", "tour", "tourney_id", "tourney_name", "round",
            "home", "away", "player_a", "player_b", "stage0_id_a", "stage0_id_b", "price_home", "price_away",
            "p_home", "overround", "max_risk_stake", "best_of", "retrieved_at", "matchup_id", "notes", "qualifying",
            *EVENT_COLUMNS, "earlier"]
    res = res[[c for c in keep if c in res.columns]].sort_values(["status", "start_utc"], ascending=[False, True])
    if qual._tl is not None and qual._tl.stopped:
        print(f"TennisLive stopped answering ({qual._tl.stopped}): qualifying rounds were read from Tennis My Life "
              "only, where it gives them")
    pair = res.apply(lambda x: "|".join(sorted([str(x["player_a"]), str(x["player_b"])])), axis=1)
    dup = res["status"].eq("ok") & pair.duplicated(keep=False) & res["status"].eq("ok")
    res.loc[dup, ["status", "reason"]] = ["left out", "two listed matches of the same pair: ambiguous"]
    return res.reset_index(drop=True)


def show(matches: pd.DataFrame) -> pd.DataFrame:
    """A compact view: the matches to predict, then the ones left out with their reasons. The listings of a switched-
    off tour (config.BET_TOURS) are counted in one line, not shown a row each (the _linking file keeps them)."""
    off = CFG.off_mask(matches) & ~matches["status"].eq("ok") if "status" in matches.columns else CFG.off_mask(matches)
    if off.any():
        print(f"{int(off.sum())} {CFG.off_names()} listings left out, not shown: {CFG.off_names()} matches are "
              "switched off (the owner, 28 Oct 2026; config.BET_TOURS)")
    cols = ["status", "start_utc", "tourney_name", "round", "player_a", "player_b", "price_home", "price_away",
            "p_home", "reason"]
    return matches.loc[~off, [c for c in cols if c in matches.columns]]


def _off_note(rows: pd.DataFrame) -> str:
    """"; 12 of them women's, switched off" for the listings a switched-off tour left out, else "", and "; 1 of them
    because of an ERROR while linking it" for the listings an error left out (28 Oct 2026)."""
    n = int((CFG.off_mask(rows) & ~rows["status"].eq("ok")).sum()) if len(rows) else 0
    err = int(rows["reason"].astype(str).str.startswith(LINK_ERROR).sum()) if len(rows) and "reason" in rows else 0
    return ((f"; {n} of them {CFG.off_names()}, switched off (config.BET_TOURS)" if n else "")
            + (f"; !!! {err} of them because of an ERROR while linking (A2 said which)" if err else ""))


# --- the CSV ---------------------------------------------------------------------------------------------------------------
def build_matchups(matches: pd.DataFrame | None = None, *, hours_ahead: float = 36, only: list[str] | None = None,
                   drop: list[str] | None = None, path: str | Path | None = None) -> Path | None:
    """Write the matchups CSV of the linked matches (status ok). `only` / `drop` keep or remove matches by a player's
    name (any part, case-insensitive). player_a is Pinnacle's home player and p_a his margin-free chance. None, said
    plainly, when no match is left: the cells up to A5b then skip, so the bet-day cells run top to bottom on any day
    (27 Oct 2026, an agent's choice; before, this raised)."""
    all_rows = (todays_matches(hours_ahead=hours_ahead) if matches is None else matches).copy()

    def has(row, names):
        text = f"{row['player_a']} {row['player_b']} {row.get('home', '')} {row.get('away', '')}".lower()
        return any(n.lower() in text for n in names)
    keep = all_rows["status"].eq("ok")
    if only:
        out_only = keep & ~all_rows.apply(lambda r: has(r, only), axis=1)
        all_rows.loc[out_only, ["status", "reason"]] = ["left out", "not chosen (build_matchups only=)"]
    if drop:
        out_drop = all_rows["status"].eq("ok") & all_rows.apply(lambda r: has(r, drop), axis=1)
        all_rows.loc[out_drop, ["status", "reason"]] = ["left out", "dropped (build_matchups drop=)"]
    m = all_rows[all_rows["status"].eq("ok")].copy()
    if m.empty:
        print(f"Nothing to predict now: none of the {len(all_rows)} listed matches can be predicted (each one's reason "
              f"is in A2's list{_off_note(all_rows)}). A3b to A5b skip; A7 and A8 still run.")
        return None
    utc = lambda s: pd.to_datetime(s, utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    # best_of is NOT written: the daily pipeline would take it over Tennis My Life's event value, and it is a model
    # input; Pinnacle's value rides along for reference (review V1, item 4). The one exception: a men's Slam
    # qualifying round its previous edition played at best of 5 (qualifying.best_of: Wimbledon's last round)
    csv = pd.DataFrame({"tour": m["tour"], "tourney_id": m["tourney_id"], "round": m["round"],
                        "player_a": m["player_a"], "player_b": m["player_b"], "day": m["day"],
                        "p_a": m["p_home"].astype(float), "tourney_name": m["tourney_name"],
                        "start_utc": utc(m["start_utc"]), "quoted_at": utc(m["retrieved_at"]),
                        "price_source": "pinnacle", "stage0_id_a": m["stage0_id_a"], "stage0_id_b": m["stage0_id_b"],
                        "pinnacle_matchup_id": m["matchup_id"], "pinnacle_home": m["home"], "pinnacle_away": m["away"],
                        "odds_a": m["price_home"], "odds_b": m["price_away"], "odds_format": "american",
                        "overround": m["overround"], "max_risk_stake": m["max_risk_stake"],
                        "pinnacle_best_of": m["best_of"], "notes": m["notes"]})
    if "event_best_of" in m.columns and m["event_best_of"].notna().any():
        csv["best_of"] = m["event_best_of"]
    for c in EVENT_COLUMNS[:-1]:                        # a qualifying event built from its previous edition
        if c in m.columns and m[c].notna().any():
            csv[c] = m[c]
    CFG.MATCHUPS.mkdir(parents=True, exist_ok=True)
    out = Path(path) if path else CFG.MATCHUPS / f"matchups_{dt.datetime.now():%Y-%m-%d_%H%M%S}.csv"
    csv.to_csv(out, index=False)
    # the earlier qualifying rounds of the matches written (qualifying.py's "earlier rounds"), one row per match, for
    # the run's live rows (prediction_run/earlier_rounds.py)
    from src.eda.prediction_run import earlier_rounds as ER
    earlier = [e for lst in (m["earlier"] if "earlier" in m.columns else []) if isinstance(lst, list) for e in lst]
    if earlier:
        er = pd.DataFrame(earlier).drop_duplicates("tl_url")
        er.to_csv(ER.sidecar(out), index=False)
    elif ER.sidecar(out).exists():                     # a CSV written again to the same path: no stale earlier rounds
        pd.DataFrame(columns=["tour", "tourney_id", "round", "winner_name", "loser_name"]).to_csv(ER.sidecar(out),
                                                                                                 index=False)
    all_rows.drop(columns=["earlier"], errors="ignore").to_csv(out.with_name(out.stem + "_linking.csv"), index=False)
    print(f"{len(csv)} matches written to {CFG.rel(out)} ({int((~all_rows['status'].eq('ok')).sum())} listed matches "
          f"left out{_off_note(all_rows)}: see the _linking file or show_matches)"
          + (f"; {len(er)} earlier qualifying round(s) from TennisLive in {CFG.rel(ER.sidecar(out))}" if earlier else ""))
    return out


def _decimal(odds) -> float:
    """Decimal odds from American (|x| >= 100) or decimal (1 < x < 100) odds."""
    x = float(odds)
    if x >= 100:
        return 1 + x / 100
    if x <= -100:
        return 1 + 100 / -x
    if 1 < x < 100:
        return x
    raise ValueError(f"odds {odds!r}: neither American nor decimal")


def manual_matchups(rows: list[dict], *, path: str | Path | None = None, source: str = "manual") -> Path:
    """The fallback: a CSV from rows typed in the notebook, each with tour, tourney_id, round, player_a, player_b,
    day, and the price as odds_a and odds_b (American or decimal; the margin is removed proportionally) or as p_a
    (player_a's margin-free chance). Optional: tourney_name, best_of, start_utc, quoted_at. The price source is
    recorded as `source` (e.g. "pinnacle (read by hand)" or "betonline": BetOnline's line stands in only while
    Pinnacle has none)."""
    df = pd.DataFrame(rows)
    if {"odds_a", "odds_b"} <= set(df.columns):
        da, db = df["odds_a"].map(_decimal), df["odds_b"].map(_decimal)
        if "p_a" not in df.columns:
            df["p_a"] = (1 / da) / (1 / da + 1 / db)
        df["overround"] = 1 / da + 1 / db
        df["odds_format"] = "as typed (American if |x| >= 100, else decimal)"
    elif "p_a" not in df.columns:
        raise ValueError("each row needs odds_a and odds_b (the bookmaker's, with its margin), or p_a")
    missing = set(MATCHUP_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"columns missing: {sorted(missing)}")
    df["price_source"] = source
    if "quoted_at" not in df.columns:
        df["quoted_at"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for col in ("quoted_at", "start_utc"):
        if col in df.columns and df[col].map(lambda x: isinstance(x, str) and pd.Timestamp(x).tzinfo is None).any():
            raise ValueError(f"{col} must carry a time zone, e.g. 2026-10-12T08:00:00Z")
    CFG.MATCHUPS.mkdir(parents=True, exist_ok=True)
    out = Path(path) if path else CFG.MATCHUPS / f"matchups_manual_{dt.datetime.now():%Y-%m-%d_%H%M%S}.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} matches written to {CFG.rel(out)}")
    return out


def _built_event(row) -> bool | str | None:
    """True when a matchups row carries a whole built event (prediction_run/live_rows.csv_event accepts it), its
    refusal as text when it carries part of one, None when it carries none."""
    from src.eda.prediction_run import live_rows as LR
    try:
        return LR.csv_event(row) is not None or None
    except SystemExit as exc:
        return str(exc)


def _matchup_problem(r: pd.Series, day, tml: pd.DataFrame | None, stage0: dict) -> str | None:
    """Why one matchups row cannot go into the run (None: it can)."""
    if CFG.tour_off(r["tour"]):
        return f"{CFG.tour_off(r['tour'])}: drop the row, or switch them back on there"
    if pd.isna(day):
        return f"its day {r['day']!r} cannot be read"
    if not (0 < float(r["p_a"]) < 1):
        return "p_a must lie strictly between 0 and 1"
    if isinstance(r.get("start_utc"), str) and r["start_utc"].strip() and pd.Timestamp(r["start_utc"]).tzinfo is None:
        return "start_utc carries no time zone"
    ev = tml[tml["tour"].eq(r["tour"]) & tml["_tid"].eq(str(r["tourney_id"]))]
    if isinstance(r.get("tourney_name"), str) and r["tourney_name"]:
        ev = ev[ev["tourney_name"].astype(str).eq(r["tourney_name"])]
    built = _built_event(r)                             # a qualifying event built from its previous edition
    if ev.empty and built is not True:
        return built if isinstance(built, str) else (f"event {r['tourney_id']} has no Tennis My Life rows (a first "
                                                     "round, or a wrong id)")
    tour_rows = tml[tml["tour"].eq(r["tour"])]
    s0 = stage0.get(r["tour"])
    if s0 is None:
        return f"tour {r['tour']!r} is not one the model predicts"
    for who in ("player_a", "player_b"):
        n = s0.loc[s0["key"].eq(name_key(r[who])), "player_id"].nunique()
        if n > 1:
            return f"{r[who]!r} names {n} Stage 0 players"
        if n == 0 and not (tour_rows["_wk"].eq(name_key(r[who])).any() or tour_rows["_lk"].eq(name_key(r[who])).any()):
            return f"{r[who]!r} is unknown to Stage 0 and Tennis My Life"
    return None


def check_matchups(csv: str | Path | None) -> pd.DataFrame | None:
    """The daily pipeline's refusals, before the run (prediction_run/run.py live_from_matchups): the columns; a day it
    can read; p_a strictly between 0 and 1; a time-zoned start; the event's Tennis My Life rows; each name naming
    exactly one player. And a match of a tour switched off for the bet day (config.BET_TOURS: women's since 28 Oct
    2026), which only a CSV made by hand or before the switch can hold. Returns one row per match (None without a CSV:
    nothing to predict), with ok False and the problem for a match that cannot go into the run.
    Since 28 Oct 2026 such a match stops nothing (the owner: "a single row shouldnt hold up the whole pipeline";
    docs/decisions/2026-10-28-one-bad-match-left-out.md): it is said here with "!!!", and A4 (predict.predict_day)
    leaves it out of the run, which predicts the others. An error while checking a row is that row's problem. Only a
    CSV without the required columns raises."""
    if csv is None:
        return None
    df = pd.read_csv(csv)
    missing = set(MATCHUP_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{csv}: columns missing: {sorted(missing)}")
    days = pd.to_datetime(df["day"], errors="coerce")
    years = sorted({d.year for d in days.dropna()} | {d.year - 1 for d in days.dropna()})
    tml = _tml(years) if years else None
    stage0 = {t: _stage0_keys(t) for t in sorted(df["tour"].astype(str).unique()) if not CFG.tour_off(t)}
    out = []
    for i, r in df.iterrows():
        try:
            prob = _matchup_problem(r, days[i], tml, stage0)
        except Exception as exc:  # noqa: BLE001 - an error checking one row is that row's problem, not the others'
            prob = f"ERROR while checking this row ({type(exc).__name__}: {exc})"
        name = r.get("tourney_name")
        out.append({"row": i, "tour": r["tour"], "event": name if isinstance(name, str) and name else r["tourney_id"],
                    "match": f"{r['player_a']} v {r['player_b']}", "round": r["round"], "ok": prob is None,
                    "problem": prob, "switched_off": bool(CFG.tour_off(r["tour"]))})
    res = pd.DataFrame(out)
    bad = res[~res["ok"]]
    if len(bad):
        print(f"!!! {len(bad)} OF {len(res)} MATCHES WILL BE LEFT OUT OF THE RUN, NO PREDICTION (a problem in their own "
              f"row); A4 predicts the other {len(res) - len(bad)}:")
        for _, b in bad.iterrows():
            print(f"!!!   {str(b['tour']).upper()} {b['event']} {b['round']}: {b['match']} -- {b['problem']}")
        print("!!! A4 and the bet sheet say them again. To keep one: fix its row (or add an alias), then A3 again.")
    else:
        print(f"{len(res)} matches pass the daily pipeline's checks")
    return res


# --- a new price for a run's matches -----------------------------------------------------------------------------------------
def live_prices(run: str | Path, *, pull_now: bool = True, path: str | Path | None = None) -> Path:
    """A fresh Pinnacle price for each match of a prediction run, as side A's margin-free chance (the daily pipeline's
    reprice takes match_id, p_a of side A). Each match is found by its Pinnacle matchup id (from the run's matchups
    CSV), else by the pair of names; a match no longer listed pre-match (in play, finished, withdrawn) is left out, and
    one still listed pre-match after its listed start is repriced (PAST_LISTED_START, 24 Oct 2026). A match of a tour
    switched off since the run (config.BET_TOURS) is not repriced: the bet sheet leaves it out."""
    run = Path(run)
    pred = pd.read_csv(run / "predictions.csv")
    off = CFG.off_mask(pred)
    if off.any():
        print(f"{int(off.sum())} of the run's {len(pred)} matches are {CFG.off_names()}, switched off since the run "
              "(config.BET_TOURS): not repriced")
        if off.all():
            raise RuntimeError(f"every match of {run.name} is {CFG.off_names()}, and they are switched off: nothing to "
                               "reprice")
        pred = pred[~off]
    mu_csv = _run_matchups(run)
    if pull_now:
        record_pinnacle()
    rows = latest_pull()
    rows = rows[rows["usable"] | rows["reason"].isin(PAST_LISTED_START)]
    out, skipped, errors = [], [], []
    for _, p in pred.iterrows():
        try:
            row = _fresh_price(p, mu_csv, rows)
        except Exception as exc:  # noqa: BLE001 - one match's error leaves it at its earlier price, never the others
            errors.append(f"{p['player_a']} v {p['player_b']} -- {type(exc).__name__}: {exc}")
            continue
        if row is None:
            skipped.append(f"{p['player_a']} v {p['player_b']}")
        else:
            out.append(row)
    df = pd.DataFrame(out)
    if skipped:
        print("not listed pre-match on Pinnacle now (in play, finished or withdrawn):", "; ".join(skipped))
    if errors:                                      # said loudly (the owner, 28 Oct 2026)
        print(f"!!! ERROR repricing {len(errors)} match{'es' * (len(errors) != 1)}: NOT repriced (the bet sheet keeps "
              "its earlier price and quote time, and blocks it once that is stale); the others are repriced:")
        for e in errors:
            print(f"!!!   {e}")
    if df.empty:
        raise RuntimeError("none of the run's matches is listed pre-match on Pinnacle now")
    out_path = Path(path) if path else run / f"prices_{dt.datetime.now():%Y%m%dT%H%M%S}.csv"
    df.to_csv(out_path, index=False)
    print(f"{len(df)} of {len(pred)} matches re-priced from Pinnacle: {CFG.rel(out_path)}")
    return out_path


def _fresh_price(p: pd.Series, mu_csv: pd.DataFrame | None, rows: pd.DataFrame) -> dict | None:
    """One prediction's fresh Pinnacle price, oriented to side A (None: not listed pre-match now)."""
    ka, kb = name_key(p["player_a"]), name_key(p["player_b"])
    hit, home_is_a = pd.DataFrame(), None
    if mu_csv is not None and "pinnacle_matchup_id" in mu_csv.columns:
        mrow = mu_csv[mu_csv["player_a"].map(name_key).isin([ka, kb]) & mu_csv["player_b"].map(name_key).isin([ka, kb])]
        if len(mrow) == 1:
            mr = mrow.iloc[0]
            hit = rows[rows["matchup_id"] == int(mr["pinnacle_matchup_id"])]
            # the side of Pinnacle's home player, from what the run was given (resolved id, else Stage 0 name),
            # never from Pinnacle's raw spelling (which an alias may have changed)
            if isinstance(mr.get("stage0_id_a"), str) and mr["stage0_id_a"]:
                home_is_a = str(mr["stage0_id_a"]) == str(p["player_a_id"])
            else:
                home_is_a = name_key(mr["player_a"]) == ka
    if hit.empty:
        hk, ak = rows["home"].map(name_key), rows["away"].map(name_key)
        hit = rows[((hk == ka) & (ak == kb)) | ((hk == kb) & (ak == ka))]
        if len(hit) == 1:
            home_is_a = name_key(hit.iloc[0]["home"]) == ka
    if len(hit) != 1 or home_is_a is None:
        return None
    h = hit.iloc[0]
    return {"match_id": p["match_id"], "p_a": float(h["p_home"] if home_is_a else 1 - h["p_home"]),
            "quoted_at": h["retrieved_at"], "player_a": p["player_a"], "player_b": p["player_b"],
            "odds_a": h["price_home"] if home_is_a else h["price_away"],
            "odds_b": h["price_away"] if home_is_a else h["price_home"], "odds_format": "american",
            "overround": h["overround"], "max_risk_stake": h["max_risk_stake"]}


def _run_matchups(run: Path) -> pd.DataFrame | None:
    """The matchups CSV a run was made from (copied into the run folder by predict_day)."""
    p = run / "matchups_input.csv"
    return pd.read_csv(p) if p.exists() else None
