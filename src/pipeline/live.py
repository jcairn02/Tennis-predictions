"""Section A's prediction-time inputs: the day's matches and their bet-time prices, as the daily pipeline's matchups CSV.

Agreed with the daily_prediction session (process log, 10:20): this layer writes prediction_run's MATCHUP_COLUMNS
(tour, tourney_id, round, player_a, player_b, day, p_a; optional tourney_name, best_of, start_utc; and quoted_at, the
quote's own time), and the daily pipeline turns p_a to Stage 0's side A itself.

    record_pinnacle()   one pull of Pinnacle's listed tennis matchups and moneylines (src/ingest/pinnacle.py)
    todays_matches()    the pull's pre-match main-tour singles, each linked to Tennis My Life's event and to the names
                        and ids Stage 0 knows, with a status and a reason for every row left out
    build_matchups()    the linked rows as the matchups CSV (player_a = Pinnacle's home player, p_a = his margin-free
                        chance, both from the same participant record; the resolved Stage 0 ids ride along)
    check_matchups()    the daily pipeline's own refusals, checked before the expensive run
    manual_matchups()   the fallback: a CSV from rows typed in the notebook (prices as odds of both players, or p_a)
    live_prices()       a fresh Pinnacle price for a run's matches, oriented to side A (for reprice)

What can be priced (the model's population and the daily pipeline's limits):
    * ATP/WTA main-tour singles (Slams, Finals, 1000s, 500s, 250s): Challengers, WTA 125s, ITF, team events, qualifying,
      doubles and in-play markets are left out;
    * the event must already have Tennis My Life rows (a played match), so first rounds wait until the event has begun;
    * each name must name exactly one Stage 0 player of the tour (by prediction_run's name key: accents, case and
      punctuation removed, words sorted). An ambiguous name would stop the whole run, so its match is left out. Names
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
from .runner import Step, run_step

if str(CFG.ROOT) not in sys.path:
    sys.path.insert(0, str(CFG.ROOT))
from src.eda.merge_feasibility.scan import name_key, norm  # noqa: E402  (prediction_run's key, imported, not copied)

MATCHUP_COLUMNS = ["tour", "tourney_id", "round", "player_a", "player_b", "day", "p_a"]
MAIN_TML_LEVELS = {"G", "M", "A", "F", "P", "PM", "I", "1000", "500", "250"}
NAMED_ROUNDS = {"QF": "QF", "SF": "SF", "F": "F", "FINAL": "F", "SEMIFINAL": "SF", "SEMIFINALS": "SF",
                "QUARTERFINAL": "QF", "QUARTERFINALS": "QF"}
ROUND_ORDER = ["R128", "R64", "R32", "R16", "QF", "SF", "F"]
EVENT_STOPWORDS = {"open", "masters", "master", "championships", "championship", "tennis", "international",
                   "internationals", "classic", "atp", "wta", "presented", "by", "the", "de", "of", "s"}


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
    found in Tennis My Life's rows instead, and the run's refreshed Stage 0 holds them)."""
    p = pd.read_parquet(CFG.STAGE0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "player_name"])
    p = p[p["match_id"].astype(str).str.startswith(f"{tour}|")]
    u = p.drop_duplicates(["player_id", "player_name"])
    return u.assign(key=u["player_name"].map(name_key))


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
        return None, None, f"{name!r} names {len(ids)} Stage 0 players ({', '.join(map(str, ids))}): the run would stop"
    for side, k in (("winner_name", "_wk"), ("loser_name", "_lk")):
        hit = tml_tour.loc[tml_tour[k].eq(key), side]
        if len(hit):
            return str(hit.iloc[0]), None, f"{hit.iloc[0]} is new since the shared Stage 0 (found in Tennis My Life)"
    return None, None, f"{name!r} is unknown to Stage 0 and Tennis My Life (add an alias in {CFG.rel(CFG.ALIASES)}?)"


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


def todays_matches(*, hours_ahead: float = 36, pull: pd.DataFrame | None = None, now: dt.datetime | None = None,
                   tours: tuple[str, ...] = ("atp", "wta")) -> pd.DataFrame:
    """Every pre-match moneyline of the latest Pinnacle pull starting within `hours_ahead`, linked to Tennis My Life's
    event and to Stage 0's names and ids; `status` is "ok" or "left out", with the reason. Run record_pinnacle() first."""
    rows = latest_pull() if pull is None else pull
    if rows.empty:
        raise RuntimeError("no Pinnacle pull yet: run record_pinnacle() first")
    now = now or dt.datetime.now(dt.timezone.utc)
    start = pd.to_datetime(rows["start_utc"], utc=True)
    window = (start > pd.Timestamp(now)) & (start <= pd.Timestamp(now) + pd.Timedelta(hours=hours_ahead))
    rows = rows[window].copy()
    if rows.empty:
        print(f"no listed match starts in the next {hours_ahead} h")
        return rows.assign(status=pd.Series(dtype=str), reason=pd.Series(dtype=str))
    years = sorted({d.year for d in start[window]} | {now.year - 1})
    tml = _tml(years)
    aliases = _aliases()
    stage0 = {t: _stage0_keys(t) for t in tours}
    out = []
    for _, r in rows.iterrows():
        rec = r.to_dict()
        uk = pd.Timestamp(r["start_utc"]).tz_convert("Europe/London")
        rec.update({"status": "left out", "reason": None, "tourney_id": None, "tourney_name": None, "round": None,
                    "player_a": None, "player_b": None, "stage0_id_a": None, "stage0_id_b": None,
                    "day": uk.date().isoformat(), "notes": ""})
        if not r["usable"]:
            rec["reason"] = r["reason"]
        elif r["tour"] not in tours:
            rec["reason"] = f"tour {r['tour']} (ITF or other)"
        elif r["level"] != "tour":
            rec["reason"] = f"{r['level']} level (outside the model's main-tour population)"
        elif r.get("qualifying"):
            rec["reason"] = "qualifying"
        elif re.search(r"\bcup\b", str(r["league"]), flags=re.I):
            rec["reason"] = "a team event (outside the model's population)"
        else:
            ev, why = _match_event(str(r["event"]), _events(tml, r["tour"], pd.Timestamp(uk.date())))
            if ev is None:
                rec["reason"] = why
            else:
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
                    else:
                        notes = [n for n in (note_a, note_b) if n != "stage0"]
                        tml_bo = pd.to_numeric(pd.Series([ev["best_of"]]), errors="coerce").iloc[0]
                        if pd.notna(r.get("best_of")) and pd.notna(tml_bo) and int(r["best_of"]) != int(tml_bo):
                            notes.append(f"Pinnacle says best of {int(r['best_of'])}, Tennis My Life {int(tml_bo)} "
                                         "(the model reads Tennis My Life's)")
                        rec.update(status="ok", player_a=a, player_b=b, stage0_id_a=ida, stage0_id_b=idb,
                                   notes="; ".join(notes))
        out.append(rec)
    res = pd.DataFrame(out)
    keep = ["status", "reason", "league", "start_utc", "day", "tour", "tourney_id", "tourney_name", "round",
            "home", "away", "player_a", "player_b", "stage0_id_a", "stage0_id_b", "price_home", "price_away",
            "p_home", "overround", "max_risk_stake", "best_of", "retrieved_at", "matchup_id", "notes"]
    res = res[[c for c in keep if c in res.columns]].sort_values(["status", "start_utc"], ascending=[False, True])
    pair = res.apply(lambda x: "|".join(sorted([str(x["player_a"]), str(x["player_b"])])), axis=1)
    dup = res["status"].eq("ok") & pair.duplicated(keep=False) & res["status"].eq("ok")
    res.loc[dup, ["status", "reason"]] = ["left out", "two listed matches of the same pair: ambiguous"]
    return res.reset_index(drop=True)


def show(matches: pd.DataFrame) -> pd.DataFrame:
    """A compact view: the matches to predict, then the ones left out with their reasons."""
    cols = ["status", "start_utc", "tourney_name", "round", "player_a", "player_b", "price_home", "price_away",
            "p_home", "reason"]
    return matches[[c for c in cols if c in matches.columns]]


# --- the CSV ---------------------------------------------------------------------------------------------------------------
def build_matchups(matches: pd.DataFrame | None = None, *, hours_ahead: float = 36, only: list[str] | None = None,
                   drop: list[str] | None = None, path: str | Path | None = None) -> Path:
    """Write the matchups CSV of the linked matches (status ok). `only` / `drop` keep or remove matches by a player's
    name (any part, case-insensitive). player_a is Pinnacle's home player and p_a his margin-free chance."""
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
        raise RuntimeError("no match left to write (see todays_matches() for the reasons)")
    utc = lambda s: pd.to_datetime(s, utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")  # noqa: E731
    # best_of is NOT written: the daily pipeline would take it over Tennis My Life's event value, and it is a model
    # input; Pinnacle's value rides along for reference (review V1, item 4)
    csv = pd.DataFrame({"tour": m["tour"], "tourney_id": m["tourney_id"], "round": m["round"],
                        "player_a": m["player_a"], "player_b": m["player_b"], "day": m["day"],
                        "p_a": m["p_home"].astype(float), "tourney_name": m["tourney_name"],
                        "start_utc": utc(m["start_utc"]), "quoted_at": utc(m["retrieved_at"]),
                        "price_source": "pinnacle", "stage0_id_a": m["stage0_id_a"], "stage0_id_b": m["stage0_id_b"],
                        "pinnacle_matchup_id": m["matchup_id"], "pinnacle_home": m["home"], "pinnacle_away": m["away"],
                        "odds_a": m["price_home"], "odds_b": m["price_away"], "odds_format": "american",
                        "overround": m["overround"], "max_risk_stake": m["max_risk_stake"],
                        "pinnacle_best_of": m["best_of"], "notes": m["notes"]})
    CFG.MATCHUPS.mkdir(parents=True, exist_ok=True)
    out = Path(path) if path else CFG.MATCHUPS / f"matchups_{dt.datetime.now():%Y-%m-%d_%H%M%S}.csv"
    csv.to_csv(out, index=False)
    all_rows.to_csv(out.with_name(out.stem + "_linking.csv"), index=False)     # every listed match, with its reason
    print(f"{len(csv)} matches written to {CFG.rel(out)} ({int((~all_rows['status'].eq('ok')).sum())} listed matches "
          "left out: see the _linking file or show_matches)")
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


def check_matchups(csv: str | Path) -> pd.DataFrame:
    """The daily pipeline's refusals, before the run (prediction_run/run.py live_from_matchups): the columns; p_a
    strictly between 0 and 1; a time-zoned start; the event's Tennis My Life rows; each name naming exactly one player.
    Returns one row per match; raises if any match would stop the run."""
    df = pd.read_csv(csv)
    missing = set(MATCHUP_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{csv}: columns missing: {sorted(missing)}")
    years = sorted({pd.Timestamp(d).year for d in df["day"]} | {pd.Timestamp(d).year - 1 for d in df["day"]})
    tml = _tml(years)
    stage0 = {t: _stage0_keys(t) for t in sorted(df["tour"].unique())}
    out = []
    for i, r in df.iterrows():
        prob = None
        if not (0 < float(r["p_a"]) < 1):
            prob = "p_a must lie strictly between 0 and 1"
        elif isinstance(r.get("start_utc"), str) and r["start_utc"].strip() and pd.Timestamp(r["start_utc"]).tzinfo is None:
            prob = "start_utc carries no time zone"
        else:
            ev = tml[tml["tour"].eq(r["tour"]) & tml["_tid"].eq(str(r["tourney_id"]))]
            if isinstance(r.get("tourney_name"), str) and r["tourney_name"]:
                ev = ev[ev["tourney_name"].astype(str).eq(r["tourney_name"])]
            if ev.empty:
                prob = f"event {r['tourney_id']} has no Tennis My Life rows (a first round, or a wrong id)"
            else:
                tour_rows = tml[tml["tour"].eq(r["tour"])]
                for who in ("player_a", "player_b"):
                    s0 = stage0[r["tour"]]
                    n = s0.loc[s0["key"].eq(name_key(r[who])), "player_id"].nunique()
                    if n > 1:
                        prob = f"{r[who]!r} names {n} Stage 0 players: the run would stop"
                        break
                    if n == 0 and not (tour_rows["_wk"].eq(name_key(r[who])).any()
                                       or tour_rows["_lk"].eq(name_key(r[who])).any()):
                        prob = f"{r[who]!r} is unknown to Stage 0 and Tennis My Life: the run would stop"
                        break
        out.append({"row": i, "match": f"{r['player_a']} v {r['player_b']}", "round": r["round"],
                    "ok": prob is None, "problem": prob})
    res = pd.DataFrame(out)
    bad = res[~res["ok"]]
    if len(bad):
        print(bad.to_string(index=False))
        raise ValueError(f"{len(bad)} of {len(res)} matches would stop the run: fix or drop them (build_matchups(drop=...))")
    print(f"{len(res)} matches pass the daily pipeline's checks")
    return res


# --- a new price for a run's matches -----------------------------------------------------------------------------------------
def live_prices(run: str | Path, *, pull_now: bool = True, path: str | Path | None = None) -> Path:
    """A fresh Pinnacle price for each match of a prediction run, as side A's margin-free chance (the daily pipeline's
    reprice takes match_id, p_a of side A). Each match is found by its Pinnacle matchup id (from the run's matchups
    CSV), else by the pair of names; a match no longer listed pre-match (started, finished, withdrawn) is left out."""
    run = Path(run)
    pred = pd.read_csv(run / "predictions.csv")
    mu_csv = _run_matchups(run)
    if pull_now:
        record_pinnacle()
    rows = latest_pull()
    rows = rows[rows["usable"]]
    out, skipped = [], []
    for _, p in pred.iterrows():
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
            skipped.append(f"{p['player_a']} v {p['player_b']}")
            continue
        h = hit.iloc[0]
        out.append({"match_id": p["match_id"], "p_a": float(h["p_home"] if home_is_a else 1 - h["p_home"]),
                    "quoted_at": h["retrieved_at"], "player_a": p["player_a"], "player_b": p["player_b"],
                    "odds_a": h["price_home"] if home_is_a else h["price_away"],
                    "odds_b": h["price_away"] if home_is_a else h["price_home"], "odds_format": "american",
                    "overround": h["overround"], "max_risk_stake": h["max_risk_stake"]})
    df = pd.DataFrame(out)
    if skipped:
        print("not listed pre-match on Pinnacle now (started, finished or withdrawn):", "; ".join(skipped))
    if df.empty:
        raise RuntimeError("none of the run's matches is listed pre-match on Pinnacle now")
    out_path = Path(path) if path else run / f"prices_{dt.datetime.now():%Y%m%dT%H%M%S}.csv"
    df.to_csv(out_path, index=False)
    print(f"{len(df)} of {len(pred)} matches re-priced from Pinnacle: {CFG.rel(out_path)}")
    return out_path


def _run_matchups(run: Path) -> pd.DataFrame | None:
    """The matchups CSV a run was made from (copied into the run folder by predict_day)."""
    p = run / "matchups_input.csv"
    return pd.read_csv(p) if p.exists() else None
