"""A prediction run: box scores refreshed first, then live inputs built by the training code, in a sandbox
(docs/decisions/2026-10-08-prediction-run-box-scores.md).

The steps, each with its own command (a run's records go to its folder, default data/studies/prediction_run/<stamp>/):
    --refresh   box scores first. Tennis My Life is downloaded; Stage 0 is built from it into the run's folder; the
                main-tour matches of the last weeks with a result but no box score are listed (fills.py); those the
                frozen reference does not hold are filled from the official feed that serves them (the WTA API), as an
                override table for the sandbox's Stage 0 only. --matchups <csv> then writes the upcoming matches' live
                rows and meta (live_rows.py; the price p_a and day of each come with the matchups), and fetches again the
                WTA's calendar pages of the women's live seasons: the women's indoor input reads the edition there
                (src/eda/indoor_fill/status.py; since 9 Oct 2026)
    --setup     create the sandbox (sandbox.py)
    --build     in the sandbox: Stage 0 with the decided overrides, the fills and the live rows, its checks, the level
                layer resolved on that Stage 0 (since 10 Oct 2026: current_best_model/layer_config.py --resolve, the
                opponent strength of every match, live rows included; every later step runs with LLE_LAYER = it, as
                the template is built; --no-layer builds without it), Stage 1's odds with the live prices, the match
                timeline with the live days, the leak-proof features (as data_continuity/rebuild_stage0.py builds them,
                without TrueSkill, which no input reads; with the layer, its IOS part is the layer's), then the model's
                chain (model_rebuild/run_chain.py's lanes: 1 and 2 side by side, then 3). The live matches' rows of the
                model frame are collected into the run's folder (live_frame.parquet), with the model's input list (the
                chain's, less the inputs the owner dropped: current_best_model/template_inputs.py), the history check
                of the sandbox's Stage 0 against the frozen reference (current_best_model/history.py), each live
                match's indoor value and its source (live_indoor.csv) and the layer's build config and strength check
                (level_layer/)
    --gate      the training standard (gate.py): every finished match of either player at the event and in the last 14
                days has a box score, and the match's indoor input is known; a live match that fails is marked not to
                bet, with what is missing
    --cleanup   delete the sandbox (its links first)
A replay (replay.py) prepares a folder of played matches as live rows and is built with --build like a run.

Run: ./python.sh src/eda/prediction_run/run.py --refresh [--matchups <csv>] [--out <folder>]
     ./python.sh src/eda/prediction_run/run.py --setup
     ./python.sh src/eda/prediction_run/run.py --build <folder> [--from <step>]
     ./python.sh src/eda/prediction_run/run.py --gate <folder>
     ./python.sh src/eda/prediction_run/run.py --cleanup
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import threading
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import common as P  # noqa: E402
from src.eda.prediction_run import sandbox as SB  # noqa: E402

INJECT = "src/eda/prediction_run/inject.py"
UPDATING = "tennis_data,wta_api,sofascore,slam_feeds,tdi"     # match_timing/refresh.py's updating sources
TML_ARGS = ["-m", "src.ingest.public_dump.tennis_my_life", "--start-year", "2000"]   # as the daily job downloads it
MATCHUP_COLUMNS = ["tour", "tourney_id", "round", "player_a", "player_b", "day", "p_a"]


def subprocess_step(name: str, args: list[str], record: list) -> int:
    import subprocess
    import time

    t0 = time.time()
    P.log(f"--> {name}: {' '.join(args)}")
    done = subprocess.run([str(P.PY), *args], cwd=P.ROOT, capture_output=True, text=True, encoding="utf-8",
                          errors="replace")
    record.append({"step": name, "args": args, "exit": done.returncode, "seconds": round(time.time() - t0, 1),
                   "tail": (done.stdout + done.stderr)[-1500:]})
    P.log(f"    exit {done.returncode} in {time.time() - t0:.0f} s")
    return done.returncode


def venue_for(tour: str, tid: str, name: str) -> str:
    """The event's city: its last edition's tennis-data Location (Stage 1's links), else TML's event name."""
    from src.eda.match_timing import srcc_tennis_data as TD

    code = str(tid).split("-")[1] if "-" in str(tid) else str(tid)
    o = pd.read_parquet(P.ROOT / P.PD / "stage1_odds.parquet", columns=["match_id", "tour", "td_file", "td_row",
                                                                       "tournament_date"])
    o = o[o["tour"].eq(tour) & o["td_file"].notna() & o["match_id"].astype(str).str.split("|").str[1]
          .str.split("-").str[1].eq(code)]
    if len(o):
        last = o.sort_values("tournament_date").tail(1).reset_index(drop=True)
        city = TD.locations(last).iloc[0]
        if isinstance(city, str) and city:
            return city
    return name


def uk_day(day, start_utc) -> pd.Timestamp:
    """tennis-data dates a match by the UK calendar day of its start: from the start time when known."""
    if isinstance(start_utc, str) and start_utc.strip():
        return pd.Timestamp(start_utc).tz_convert("Europe/London").tz_localize(None).normalize()
    return pd.Timestamp(day).normalize()


def tml_box_fills(earlier: pd.DataFrame, raw: pd.DataFrame, stage0: Path, keyed: pd.DataFrame, event_tid,
                  leave_out: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """The sidecar's rounds the run's fresh Stage 0 already holds (their source published them, possibly as results
    only: Tennis My Life posted Vienna's and Basel's round 1 at about 21:00 PDT on 24 Oct 2026 without box scores).
    Their rows stand; one without a box score takes TennisLive's as an override row (run/overrides.csv, as the WTA
    API's and the ATP's fills: live only, rebuilt at every run), when the two agree on the winner and every set's games
    and the row is the only one of its key in the staged files (apply_box_overrides stops a build otherwise).
    (the override rows, the sidecar rows Stage 0 lacks, notes). leave_out (the daily engine's live runs, since 28 Oct
    2026): a round that fails here is neither filled nor passed on, its note carrying the error (and its tl_url)."""
    from src.eda.predictability_diagnostic import common as C
    from src.eda.predictability_diagnostic import stage0_build as B
    from src.eda.prediction_run import fills as FL
    m = pd.read_parquet(stage0 / "stage0_matches.parquet",
                        columns=["match_id", "tour", "tournament_id", "round", "source", "has_box", "player_a_id",
                                 "player_b_id", "a_won", "source_file", "source_row"])
    m["match_id"] = m["match_id"].astype(str)
    m = m.set_index("match_id", drop=False)
    # each match found by its event, round and players, never by an id rebuilt from the players' ids: a source's second
    # id can name the match (live_rows.id_handles; 28 Oct 2026)
    tid_of = {i: str(event_tid(e)) for i, e in earlier.iterrows()}
    ev = m[m["tournament_id"].astype(str).isin(set(tid_of.values()))]
    by_players = {(t, str(tid), str(r), frozenset((str(a), str(b)))): mid for mid, t, tid, r, a, b in
                  zip(*(ev[c] for c in ("match_id", "tour", "tournament_id", "round", "player_a_id", "player_b_id")))}
    rkey = (raw["tour"].astype(str) + "|" + raw["tourney_id"].astype(str).str.replace(r"-0+(\d)", r"-\1", regex=True)
            + "|" + raw["round"].astype(str).str.upper() + "|" + B.S.keys_for(raw["winner_name"]) + "|"
            + B.S.keys_for(raw["loser_name"])).value_counts()
    cols = [f"{p}_{c}" for p in ("w", "l") for c in C.BOX_SOURCE_NAMES.values()]
    over, rest, notes = [], [], []
    for i, e in earlier.iterrows():
        try:
            ids = [keyed.loc[keyed["tour"].eq(e["tour"]) & keyed["key"].eq(B.S.name_key(str(e[w]))),
                             "player_id"].unique() for w in ("winner_name", "loser_name")]
            if any(len(x) != 1 for x in ids):
                rest.append(i)                          # played_rows says why it cannot be placed
                continue
            mid = by_players.get((e["tour"], tid_of[i], str(e["round"]).upper(),
                                  frozenset((str(ids[0][0]), str(ids[1][0])))))
            if mid is None:
                rest.append(i)                          # not published: a played row
                continue
            s = m.loc[[mid]]
            r = s.iloc[0]
            what = f"{e['winner_name']} v {e['loser_name']} ({e['round']})"
            if bool(r["has_box"]):
                notes.append({"match": what, "outcome": "its source holds it with a box score"})
                continue
            winner = r["player_a_id"] if bool(r["a_won"]) else r["player_b_id"]
            if str(r["source"]) != "tml" or str(winner) != str(ids[0][0]):
                notes.append({"match": what, "outcome": "held without a box score, not as TennisLive reads it (its "
                                                        "source or winner): left without one"})
                continue
            k = FL.tml_keys(s, raw).iloc[0]
            counts = {c: str(e.get(c, "") or "").strip() for c in cols}
            key = f"{k['tour']}|{k['tid']}|{k['round']}|{k['winner_key']}|{k['loser_key']}"
            if FL.games(k["tml_score"]) != FL.games(e["score"]) or rkey.get(key, 0) != 1 or not counts["w_svpt"]:
                notes.append({"match": what, "outcome": "held without a box score; TennisLive's not used (the games, "
                                                        "the row's key or the counts)"})
                continue
            over.append({"box_source": "tennislive_live", "feed_key": f"tennislive:{e.get('tl_url')}", **k.to_dict(),
                         "score": "", "minutes": "", "source": "tml", **counts})
            notes.append({"match": what, "outcome": "held without a box score: TennisLive's box score as a live fill"})
        except (SystemExit, Exception) as exc:  # noqa: BLE001 - one earlier round's failure, kept with its reason
            if not leave_out:
                raise
            notes.append({"match": f"{e.get('winner_name')} v {e.get('loser_name')} ({e.get('round')})",
                          "outcome": "left out because of an error", "error": P.reason_of(exc),
                          "tl_url": e.get("tl_url")})
    return pd.DataFrame(over), earlier.loc[rest], notes


def live_from_matchups(matchups: pd.DataFrame, stage0: Path, folder: Path, earlier: pd.DataFrame | None = None,
                       leave_out: bool = False) -> dict:
    """Live rows and meta for upcoming matches (columns MATCHUP_COLUMNS, optional tourney_name, best_of, start_utc).
    p_a is the margin-free price that player_a wins at bet time; the match id is predicted as Stage 0 builds it (each
    player's id as Stage 0's match ids give the one the live row carries, live_rows.id_handles: since 28 Oct 2026, when
    TML's second ids for two players stopped the run) and checked in the sandbox. An event TML holds no row of yet (a
    qualifying round 1; women's qualifying) comes with its
    columns in the CSV (live_rows.CSV_EVENT): its Stage 0 id is predicted as Stage 0 normalises TML's, and the check
    after the build leaves the match out (the daily engine) or refuses the run (the 8 Oct path) if Stage 0 gave it
    another. earlier (the CSV's sidecar, since 24 Oct 2026): the
    qualifying rounds the matches' players won at the event that TML or the feed has not published yet, from
    TennisLive, added as live rows with their results (earlier_rounds.played_rows) and dated by played_meta.parquet.
    Each meta row names its row of the CSV (csv_row).
    leave_out (the daily engine's live runs, since 28 Oct 2026: docs/decisions/2026-10-28-one-bad-match-left-out.md;
    the owner: "a single row shouldnt hold up the whole pipeline"): a match whose row cannot be placed (its event, a
    player, its live row, its day, its price's number) is left out, with the reason, in the result's "left_out", and the
    others are written; an earlier round that cannot be added is listed in "earlier_left_out" and its match still
    written. A CSV with every match left out still stops. Without it (the 8 Oct path) any of them stops the run."""
    import re

    from src.eda.prediction_run import live_rows as LR
    from src.eda.predictability_diagnostic import common as C
    from src.eda.predictability_diagnostic import stage0_build as B

    missing = set(MATCHUP_COLUMNS) - set(matchups.columns)
    if missing:
        raise SystemExit(f"matchups: columns missing: {sorted(missing)}")
    matchups = matchups.reset_index(drop=True)
    if leave_out:                                    # a day that cannot be read leaves out its own row (below)
        years = sorted({d.year for d in pd.to_datetime(matchups["day"], errors="coerce").dropna()})
        if not years:
            raise SystemExit("matchups: no row's day can be read")
    else:
        years = sorted({pd.Timestamp(d).year for d in matchups["day"]})
    raw = LR.staged_tml(sorted(set(years) | {y - 1 for y in years}))
    failed: dict = {}                                # CSV row -> why it is left out (leave_out only)
    rows = LR.upcoming_rows(matchups, raw, LR.stage0_players(stage0), failed=failed if leave_out else None)
    at = {int(r): k for k, r in enumerate(rows["_row"])} if len(rows) else {}
    m = pd.read_parquet(stage0 / "stage0_matches.parquet", columns=["match_id", "tour", "tournament_id", "source",
                                                                    "source_file", "source_row"])
    p = pd.read_parquet(stage0 / "stage0_match_players.parquet", columns=["match_id", "player_id", "side",
                                                                          "player_name"])
    keyed = p.assign(key=B.S.keys_for(p["player_name"])).merge(m[["match_id", "tour"]], on="match_id")
    handles = LR.id_handles(m, p, raw)
    meta = []
    for i, mu in matchups.iterrows():
        if i in failed:
            continue
        try:
            event = LR.event_rows(raw, mu["tour"], mu["tourney_id"], mu.get("tourney_name") or None)
            own = m[m["source_file"].astype(str).isin(set(event["_source_file"].astype(str)))
                    & pd.to_numeric(m["source_row"]).isin(pd.to_numeric(event["_row"]))]
            tids = own.loc[own["tour"].eq(mu["tour"]), "tournament_id"].value_counts()
            if tids.empty and event.empty and LR.csv_event(mu) is not None:  # a new event: its id as Stage 0 makes it
                tids = pd.Series([1], index=[re.sub(r"-0+(\d)", r"-\1", str(mu["tourney_id"]))])
            if tids.empty:
                raise SystemExit(f"matchups: the event {mu['tourney_id']} has no Stage 0 match")
            event_name = str(event["tourney_name"].iloc[0]) if len(event) else str(mu["tourney_name"])
            ids = []
            for who, col in (("player_a", "winner_id"), ("player_b", "loser_id")):
                hit = keyed[keyed["tour"].eq(mu["tour"]) & keyed["key"].eq(B.S.name_key(str(mu[who])))]["player_id"]
                if hit.nunique() != 1:
                    raise SystemExit(f"matchups: {mu[who]!r} names {hit.nunique()} Stage 0 players")
                ids.append(LR.handle_of(handles, mu["tour"], rows.at[at[i], col], hit.iloc[0]))  # the live row's own id
            lo, hi = sorted(ids)
            mid = f"{mu['tour']}|{tids.index[0]}|{str(mu['round']).upper()}|{lo}|{hi}"
            a_is_a = (lo if C.side_is_low(mid) else hi) == ids[0]
            p_a = float(mu["p_a"])
            meta.append({"match_id": mid, "day": uk_day(mu["day"], mu.get("start_utc")),
                         "p_a": p_a if a_is_a else 1 - p_a, "venue": venue_for(mu["tour"], tids.index[0], event_name),
                         "tour": mu["tour"], "tournament_name": event_name,
                         "round": str(mu["round"]).upper(), "player_a": mu["player_a"], "player_b": mu["player_b"],
                         "csv_row": int(i)})
        except (SystemExit, Exception) as exc:  # noqa: BLE001 - one match's failure, kept with its reason
            if not leave_out:
                raise
            failed[i] = P.reason_of(exc)
    left_out = [{"csv_row": int(i), "tour": mu["tour"], "tourney_id": str(mu["tourney_id"]),
                 "tourney_name": mu.get("tourney_name"), "round": str(mu["round"]).upper(), "player_a": mu["player_a"],
                 "player_b": mu["player_b"], "day": mu["day"], "reason": failed[i]}
                for i, mu in matchups.iterrows() if i in failed]
    if failed and len(rows):                         # their live rows go with them, before anything reads them
        rows = rows[~pd.to_numeric(rows["_row"]).isin(list(failed))].reset_index(drop=True)
    meta = pd.DataFrame(meta)
    if left_out and meta.empty:
        raise SystemExit(f"matchups: every match was left out ({len(left_out)}): "
                         + "; ".join(f"{r['player_a']} v {r['player_b']}: {r['reason']}" for r in left_out))
    filled, earlier_left = {}, []
    played_path = folder / "played_meta.parquet"
    if earlier is not None and len(earlier):
        from src.eda.prediction_run import earlier_rounds as ER

        def event_tid(e) -> str:
            event = LR.event_rows(raw, e["tour"], e["tourney_id"], e.get("tourney_name") or None)
            own = m[m["source_file"].astype(str).isin(set(event["_source_file"].astype(str)))
                    & pd.to_numeric(m["source_row"]).isin(pd.to_numeric(event["_row"]))]
            tids = own.loc[own["tour"].eq(e["tour"]), "tournament_id"].value_counts()
            return str(tids.index[0]) if len(tids) else re.sub(r"-0+(\d)", r"-\1", str(e["tourney_id"]))
        given = earlier.reset_index(drop=True)
        try:
            earlier = given.assign(venue=[venue_for(e["tour"], event_tid(e), e.get("tourney_name") or "")
                                          for _, e in given.iterrows()])
            boxed, earlier, held = tml_box_fills(earlier, raw, stage0, keyed, event_tid, leave_out=leave_out)
            if len(boxed):                              # the run's overrides: the decided table, the refresh's fills
                path = folder / "overrides.csv"
                base = pd.read_csv(path if path.exists() else B.DECIDED_OVERRIDES, dtype=str, keep_default_na=False)
                both = pd.concat([base, boxed.reindex(columns=base.columns).fillna("").astype(str)], ignore_index=True)
                dup = both[["tour", "tid", "round", "winner_key", "loser_key"]].astype(str).agg("|".join,
                                                                                                 axis=1).duplicated()
                both[~dup].to_csv(path, index=False)    # an official fill of the same row, listed first, wins
            played, pmeta, left = ER.played_rows(earlier, raw, LR.stage0_players(stage0), keyed, event_tid, handles,
                                                 leave_out=leave_out)
        except (SystemExit, Exception) as exc:  # noqa: BLE001 - the earlier rounds as a whole: the matches go on
            if not leave_out:
                raise
            why = f"the earlier rounds could not be added: {P.reason_of(exc)}"
            boxed, held, played = pd.DataFrame(), [], pd.DataFrame()
            pmeta = pd.DataFrame(columns=["match_id", "day", "venue", "tour"])
            left = [{"tl_url": e.get("tl_url"), "reason": why} for _, e in given.iterrows()]
        if len(played):
            rows = pd.concat([rows, played], ignore_index=True)
        pmeta.to_parquet(played_path, index=False)
        filled = {"earlier_rounds": {"filled": int(len(played)), "with_box": int(pmeta["has_box"].sum()) if len(pmeta)
                                     else 0, "left_out": left, "source_holds": held,
                                     "box_scores_given_to_source_rows": int(len(boxed))}}
        if leave_out:                                # each round not added, named (its match is still predicted)
            by_url = {str(e.get("tl_url")): e for _, e in given.iterrows()}

            def named(x: dict) -> dict:
                e = by_url.get(str(x.get("tl_url")))
                return {**({} if e is None else {"tour": e.get("tour"), "tourney_id": e.get("tourney_id"),
                                                 "tourney_name": e.get("tourney_name"), "round": e.get("round"),
                                                 "winner": e.get("winner_name"), "loser": e.get("loser_name")}), **x}
            earlier_left = [named(x) for x in left] + [named({"tl_url": n.get("tl_url"), "reason": n["error"]})
                                                       for n in held if n.get("error")]
    elif played_path.exists():                       # a folder reused: no stale earlier rounds
        pd.DataFrame(columns=["match_id", "day", "venue", "tour"]).to_parquet(played_path, index=False)
    rows.to_parquet(folder / "live_rows.parquet", index=False)
    meta.to_parquet(folder / "live_meta.parquet", index=False)
    return {"live_matches": int(len(meta)), "match_ids": meta["match_id"].tolist(), **filled,
            **({"left_out": left_out, "earlier_left_out": earlier_left} if leave_out else {})}


def wta_calendar(matchups: pd.DataFrame, max_requests: int) -> dict:
    """The WTA's calendar pages of the women's live seasons, fetched again through the WTA adapter's own client (about
    2 s between requests, a receipt for every answer, a stop on any block). The women's indoor input reads the edition's
    inOutdoor there (src/eda/indoor_fill/status.py), and only a fresh page lists a new edition."""
    from src.ingest.point_sources import common as PS
    from src.ingest.point_sources import feeds as F
    from src.ingest.point_sources import wta as W

    years = sorted({pd.Timestamp(d).year for d, t in zip(matchups["day"], matchups["tour"]) if str(t) == "wta"})
    if not years:
        return {"years": []}
    client = W.make_client(min_interval=2.0, jitter=1.0, max_requests=max_requests)
    receipts = PS.receipts_for(W.SOURCE)
    try:
        pages = [W.fetch_calendar(client, receipts, y, refresh=True) for y in years]
    except (PS.Blocked, PS.BudgetExhausted, F.Stopped) as stop:   # a block stops the fetch, as the decision asks
        return {"years": years, "stopped": f"{type(stop).__name__}: {stop}"}
    return {"years": years, "pages": pages}


def refresh(folder: Path, matchups: Path | None, download: bool, max_requests: int) -> int:
    """Box scores first: the download, Stage 0 on it, the gaps, the WTA fills; then the upcoming matches' live rows."""
    from src.eda.prediction_run import fills as FL
    from src.eda.prediction_run import live_rows as LR

    folder.mkdir(parents=True, exist_ok=True)
    record: dict = {"started_at": P.stamp(), "steps": []}
    try:
        if download and subprocess_step("tml", TML_ARGS, record["steps"]) not in (0, 1):
            return 2                                   # 1: a file held or a download error, reported in the record
        if subprocess_step("stage0", ["src/eda/predictability_diagnostic/stage0_build.py", "--out-dir",
                                      str(folder / "stage0")], record["steps"]):
            return 2
        today = pd.Timestamp.now().normalize()
        g = FL.gaps(folder / "stage0", today, FL.reference_ids())
        record["gaps"] = g.groupby(["class", "tour", "level"]).size().rename("matches").reset_index().to_dict("records")
        fillable = g[g["class"].eq("fillable")]
        keys = FL.tml_keys(fillable, LR.staged_tml(sorted({int(y) for y in fillable["year"]}))) if len(fillable) else None
        # the women's from the WTA API, the men's from the ATP Stats Centre (since 14 Oct 2026)
        fills, notes = FL.fill_all(fillable, keys, max_requests) if len(fillable) else (pd.DataFrame(), [])
        g = g.merge(pd.DataFrame(notes, columns=["match_id", "outcome"]), on="match_id", how="left") if notes else g
        g[["match_id", "tour", "level", "tournament_name", "round", "tournament_date", "class"]
          + (["outcome"] if "outcome" in g else [])].to_csv(folder / "gaps.csv", index=False)
        record["fills"] = {"filled": int(len(fills)), "notes": notes[:50]}
        if len(fills):
            fills.to_csv(folder / "fills.csv", index=False)
            FL.override_table(fills).to_csv(folder / "overrides.csv", index=False)
        if matchups is not None:
            record["live"] = live_from_matchups(pd.read_csv(matchups), folder / "stage0", folder)
            record["wta_calendar"] = wta_calendar(pd.read_csv(matchups), max_requests)
        return 0
    finally:
        record["finished_at"] = P.stamp()
        P.write_json(folder / "refresh.json", record)


LAYER_STEP = "lle_layer"


def stage0_steps(has_overrides: bool, layer: bool = True) -> list[tuple[str, str, list[str]]]:
    """Stage 0 to the leak-proof features, with the live rows' injections between the builders, and the level layer
    resolved on the sandbox's Stage 0 (every step after it runs with LLE_LAYER: build())."""
    from src.eda.current_best_model import layer_config as LCF
    over = ["--box-overrides", "run/overrides.csv", "--confirm-live-overrides"] if has_overrides else []
    lle = [(LAYER_STEP, "src/eda/current_best_model/layer_config.py", ["--resolve", "--official", str(LCF.OFFICIAL)])]
    # the lower-level additions the owner accepted (current_best_model/additions.py): merged into the sandbox's Stage 0
    # as a template build merges them, their timeline rows pinned back after the timeline is rebuilt (nothing when no
    # package is accepted)
    return [
        ("stage0", "src/eda/predictability_diagnostic/stage0_build.py", ["--live-rows", "run/live_rows.parquet", *over]),
        ("additions", "src/eda/current_best_model/additions.py", ["--apply"]),
        ("check", INJECT, ["--meta", "run/live_meta.parquet", "--step", "check"]),
        ("stage0_checks", "src/eda/predictability_diagnostic/stage0_checks.py", []),
        *(lle if layer else []),
        ("odds", "src/eda/predictability_diagnostic/stage1_odds.py", []),
        ("live_odds", INJECT, ["--meta", "run/live_meta.parquet", "--step", "odds"]),
        ("remap", INJECT, ["--meta", "run/live_meta.parquet", "--step", "remap"]),
        ("links", "src/eda/match_timing/link_sources_c.py", ["--sources", UPDATING]),
        ("live_links", INJECT, ["--meta", "run/live_meta.parquet", "--step", "links"]),
        ("timing", "src/eda/match_timing/timing.py", []),
        ("timing_check", "src/eda/match_timing/timing_check.py", []),
        ("live_window", INJECT, ["--meta", "run/live_meta.parquet", "--step", "pin"]),
        ("additions_window", "src/eda/current_best_model/additions.py", ["--pin-timing"]),
        ("timing_features", "src/eda/match_timing/rebuild.py", []),
    ]


def chain_lanes() -> dict[str, list[tuple[str, str, list[str]]]]:
    from src.eda.model_rebuild import run_chain as RC

    return {lane: [(name, script.split()[0], script.split()[1:]) for name, script in RC.LANES[lane]]
            for lane in ("1", "2", "3")}


def run_steps(steps, record: list, start: str | None = None, after=None) -> int:
    names = [s[0] for s in steps]
    for name, script, args in steps[names.index(start):] if start in names else steps:
        code = SB.run(name, script, *args, record=record)
        if code != 0:
            return code
        if after is not None:
            after(name)
    return 0


def use_layer(box: Path, record: dict) -> None:
    """Every later step runs with LLE_LAYER = the sandbox's resolved layer config (refused if it was resolved on another
    Stage 0 than the sandbox's)."""
    import os
    from src.eda.current_best_model import layer_config as LCF
    p = LCF.build_config(box)
    LCF.require_resolved(p, box)
    os.environ["LLE_LAYER"] = str(p)
    record["lle_layer"] = {"on": True, "build_config": str(p), "sha256": LCF.sha256(p)}
    P.log(f"the level layer: LLE_LAYER={p}")


def build(folder: Path, start: str | None = None, layer: bool = True) -> int:
    import os
    box = P.SANDBOX
    if not (box / P.MARKER).exists():
        raise SystemExit(f"no sandbox at {box}: run.py --setup")
    if os.environ.get("LLE_LAYER", "").strip():
        raise SystemExit("LLE_LAYER is set in the environment: a prediction run sets it itself (or --no-layer)")
    run_dir = box / "run"
    SB.refresh_code()                                  # the sandbox runs the repository's current code
    first = start is None
    if first:
        if run_dir.exists():
            raise SystemExit(f"{run_dir} exists: this sandbox has built a run already (--cleanup, --setup)")
        (run_dir / "stage0_before").mkdir(parents=True)
        for f in ("live_rows.parquet", "live_meta.parquet", "overrides.csv"):
            if (folder / f).exists():
                shutil.copy2(folder / f, run_dir / f)
        for f in ("stage0_matches.parquet", "stage0_match_players.parquet"):
            shutil.copy2(box / P.PD / f, run_dir / "stage0_before" / f)
    record_path = folder / "build.json"
    record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() and not first else {"steps": []}
    record.update({"sandbox": str(box), "folder": str(folder)})
    record.setdefault("lle_layer", {"on": False})
    steps = record["steps"]
    lanes = chain_lanes()
    order = ["prep"] + ["lane1_2", "lane3", "collect"]
    begin = "prep"
    prep = stage0_steps((run_dir / "overrides.csv").exists(), layer)
    if start:
        for phase, names in (("prep", [s[0] for s in prep]), ("lane1_2", [s[0] for s in lanes["1"]]
                             + [s[0] for s in lanes["2"]]), ("lane3", [s[0] for s in lanes["3"]]),
                             ("collect", ["collect"])):
            if start in names:
                begin = phase
                break
    prep_names = [s[0] for s in prep]
    resumed_after_layer = layer and start is not None and (
        begin != "prep" or prep_names.index(start) > prep_names.index(LAYER_STEP))
    try:
        if resumed_after_layer:
            use_layer(box, record)                     # resolved by the run being resumed
        if order.index(begin) <= order.index("prep"):
            code = run_steps(prep, steps, start if begin == "prep" else None,
                             after=lambda name: use_layer(box, record) if name == LAYER_STEP else None)
            if code:
                return code
        if order.index(begin) <= order.index("lane1_2"):
            codes = {}

            def lane(n: str) -> None:
                codes[n] = run_steps(lanes[n], steps, start if begin == "lane1_2" else None)

            threads = [threading.Thread(target=lane, args=(n,)) for n in ("1", "2")]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            if any(codes.values()):
                return max(codes.values())
        if order.index(begin) <= order.index("lane3"):
            code = run_steps(lanes["3"], steps, start if begin == "lane3" else None)
            if code:
                return code
        collect(folder, record)
        return 0
    finally:
        os.environ.pop("LLE_LAYER", None)
        P.write_json(record_path, record)


def collect(folder: Path, record: dict) -> None:
    """The live matches' rows of the sandbox's model frame, its input list, the history check and the logs."""
    box = P.SANDBOX
    meta = pd.read_parquet(folder / "live_meta.parquet").astype({"match_id": str})
    frame = pd.read_parquet(box / P.FRAME)
    frame["match_id"] = frame["match_id"].astype(str)
    live = frame[frame["match_id"].isin(set(meta["match_id"]))]
    live.to_parquet(folder / "live_frame.parquet", index=False)
    shutil.copy2(box / P.INPUTS, folder / "model_inputs.json")
    from src.eda.current_best_model import template_inputs as TI

    record["inputs"] = TI.apply(folder)          # the model's list: the chain's 58 less the dropped (9 Oct 2026)
    from src.eda.current_best_model import history as H

    res = H.check(box / P.PD, box / P.MT / "timing.parquet")
    record["history"] = {k: v for k, v in res.items() if k != "feeds"}
    record["indoor"] = live_indoor(box, meta, folder)
    from src.eda.prediction_run import gate as G

    record["gate"] = G.run(folder, box / P.PD, box / P.MT / "timing.parquet")
    record["collected"] = {"live_matches": int(len(meta)), "in_frame": int(len(live)),
                           "missing_from_frame": sorted(set(meta["match_id"]) - set(live["match_id"]))[:20]}
    logs = folder / "logs"
    logs.mkdir(exist_ok=True)
    for f in (box / "logs").glob("*.log"):
        shutil.copy2(f, logs / f.name)
    for f in (box / "run").glob("*.json"):
        shutil.copy2(f, folder / f"sandbox_{f.name}")
    from src.eda.current_best_model import layer_config as LCF
    lb = box / LCF.REL_BUILD
    if lb.is_dir():                                    # the level layer's build config and strength check
        (folder / "level_layer").mkdir(exist_ok=True)
        for f in ("build_config.json", "build_config.sha256", "strength_check.json", "strength_elo.parquet.sha256"):
            if (lb / f).exists():
                shutil.copy2(lb / f, folder / "level_layer" / f)
    P.log(f"collected {len(live)} of {len(meta)} live matches into {folder}; {H.summary_line(res)}")


def live_indoor(box: Path, meta: pd.DataFrame, folder: Path) -> dict:
    """Each live match's indoor value and the step of src/eda/indoor_fill/status.py it came from, as the sandbox's
    frame builder recorded them (live_indoor.csv)."""
    import pyarrow.parquet as pq

    path = box / P.THINKING_FRAME
    cols = ["match_id", "x_indoor", "indoor_source"]
    if not path.exists() or "indoor_source" not in pq.read_schema(path).names:
        return {"recorded": False, "why": f"{path} holds no indoor_source column"}
    t = pd.read_parquet(path, columns=cols).astype({"match_id": str})
    ind = meta[["match_id", "tour", "tournament_name"]].merge(t, on="match_id", how="left")
    ind.to_csv(folder / "live_indoor.csv", index=False)
    return {"recorded": True, "unknown": int(ind["x_indoor"].isna().sum()),
            "by_source": ind.groupby(["tour", "indoor_source"], dropna=False).size().rename("matches").reset_index()
                           .astype({"indoor_source": str}).to_dict("records")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    which = ap.add_mutually_exclusive_group(required=True)
    which.add_argument("--refresh", action="store_true")
    which.add_argument("--setup", action="store_true")
    which.add_argument("--build", metavar="FOLDER")
    which.add_argument("--gate", metavar="FOLDER")
    which.add_argument("--cleanup", action="store_true")
    ap.add_argument("--from", dest="start", default=None, help="--build: resume at this step")
    ap.add_argument("--out", default=None, help="--refresh: the run's folder (default data/studies/prediction_run/<stamp>)")
    ap.add_argument("--matchups", default=None, help="--refresh: CSV of upcoming matches (" + ", ".join(MATCHUP_COLUMNS)
                    + "; optional tourney_name, best_of, start_utc)")
    ap.add_argument("--no-download", action="store_true", help="--refresh: use the Tennis My Life files held")
    ap.add_argument("--max-requests", type=int, default=300, help="--refresh: the WTA API's request budget")
    ap.add_argument("--no-layer", action="store_true",
                    help="--build: without the level layer (the template before 10 Oct 2026); default: with it, as the "
                         "current best model is built")
    a = ap.parse_args()
    if a.setup:
        SB.setup()
        return 0
    if a.cleanup:
        SB.cleanup()
        return 0
    if a.refresh:
        out = Path(a.out) if a.out else P.OUT / P.stamp()
        out = out if out.is_absolute() else ROOT / out
        return refresh(out, Path(a.matchups) if a.matchups else None, not a.no_download, a.max_requests)
    if a.gate:
        from src.eda.prediction_run import gate as G

        folder = Path(a.gate) if Path(a.gate).is_absolute() else ROOT / a.gate
        print(json.dumps(G.run(folder, P.SANDBOX / P.PD, P.SANDBOX / P.MT / "timing.parquet"), indent=1, default=str))
        return 0
    folder = Path(a.build) if Path(a.build).is_absolute() else ROOT / a.build
    return build(folder, a.start, layer=not a.no_layer)


if __name__ == "__main__":
    sys.exit(main())
