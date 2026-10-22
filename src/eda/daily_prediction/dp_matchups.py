"""Steps 2 and 3: the day's matches as live rows, and each one's price.

Live: prediction_run/run.live_from_matchups, unchanged (a CSV of tour, tourney_id, round, player_a, player_b, day, p_a;
optional tourney_name, best_of, start_utc; the players linked to Stage 0 by an exact name key, refusing ambiguity; the
event's columns from its Tennis My Life rows, so an event's first round cannot get live rows yet: PLAN.md section 5).
The price p_a is the margin-free chance of player_a; live_from_matchups turns it to side A's.

Replay (prediction_run/replay.py's design, on the instance's own tables): the first day's matches of one round of a
week's main-tour events (Tennis My Life's era, not the two Slams whose box scores the feeds override), each a live row
from its own TML row with the outcome removed and a placeholder result won by Stage 0's player A; the round's later days
and the events' later rounds left out (they had not been played that morning). The targets, their players and days are
read from the instance's build tree (its Stage 0, timeline and Stage 1), the TML rows from the work tree's frozen dump.
Dated as played ("training"), priced at the instance's own Pinnacle-first price (prices step).

A replay of a qualifying round (Q1, Q2, Q3: tour-level qualifying, bet since 22 Oct 2026, docs/decisions/
2026-10-22-qualifying-bets.md) takes the first day's matches of that round at the week's T1000, T500 and T250 events;
the later qualifying rounds and the events' whole main draws are left out (none of them was played that morning). Their
inputs and prices are not in the instance frame (it holds main draws only): the run names a frame that holds them
(run.json's replay "frame", e.g. the qualifying-targets study's rows with a price), used for the targets, the prices and
the comparison.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import dp_common as DC

OVERRIDDEN = ("Wimbledon", "US Open")              # their 2026 box scores come from the feeds (decision 2026-10-06)
LEVELS = ("T1000", "T500", "T250")


def live(run_dir: Path, csv: Path, stage0: Path | None = None) -> dict:
    from src.eda.prediction_run import run as RUN
    from src.eda.predictability_diagnostic import common as C
    s0 = stage0 or ((run_dir / "stage0") if (run_dir / "stage0" / "stage0_matches.parquet").exists() else C.OUT)
    return {"stage0": str(s0), **RUN.live_from_matchups(pd.read_csv(csv), Path(s0), run_dir)}


def replay_select(base_tree: Path, frame_path: Path, week: str, rnd: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """replay.select on the instance's tables. A qualifying round (Q1-Q3): its first day's matches, with the later
    qualifying rounds and the events' main draws (their Stage 0 ids start with the event's year and code: TML files
    some events' qualifying apart, e.g. Shanghai 2026) left out."""
    from src.eda.predictability_diagnostic import common as C
    m = pd.read_parquet(Path(base_tree) / DC.PD / "stage0_matches.parquet")
    m["match_id"] = m["match_id"].astype(str)
    frame = set(pd.read_parquet(frame_path, columns=["match_id"])["match_id"].astype(str))
    obs = pd.read_parquet(Path(base_tree) / DC.MT / "timing.parquet", columns=["match_id", "obs"]).astype({"match_id": str})
    start = pd.Timestamp(week)
    qualifying = str(rnd).startswith("Q") and str(rnd) != "QF"
    week_tml = (m["tournament_date"].between(start, start + pd.Timedelta(days=6)) & m["source"].eq("tml")
                & m["level"].isin(LEVELS) & ~m["tournament_name"].isin(OVERRIDDEN))
    ev = m[week_tml & (m["qualifying"] if qualifying else ~m["qualifying"])]
    ev = ev.merge(obs, on="match_id", how="left")
    in_round = ev[ev["round"].eq(rnd)]
    first = in_round["obs"].min()
    targets = in_round[in_round["obs"].eq(first) & in_round["match_id"].isin(frame) & in_round["has_box"].astype(bool)]
    later = ev[(ev["round_order"] > C.ROUND_ORDER[rnd]) | (ev["round"].eq(rnd) & ~ev["match_id"].isin(set(targets["match_id"])))]
    if qualifying:                                   # the events' main draws: played after their qualifying
        base = targets["tournament_id"].astype(str).str.split("-").str[:2].str.join("-")
        main = m[week_tml & ~m["qualifying"] & m["tour"].isin(set(targets["tour"]))
                 & m["tournament_id"].astype(str).str.split("-").str[:2].str.join("-").isin(set(base))]
        later = pd.concat([later, main.merge(obs, on="match_id", how="left")], ignore_index=True)
    return targets.drop(columns="obs"), later.drop(columns="obs")


def replay(run_dir: Path, week: str, rnd: str, winner: str = "A", base_tree: Path = DC.BASE_TREE,
           frame_path: Path = DC.INSTANCE / "model_frame.parquet", dating: str = "training",
           main_date: str | None = None) -> dict:
    """Runs inside the work tree (its staged TML is the freeze's view). main_date (a qualifying round, YYYY-MM-DD): the
    main-draw start every live row names instead of the instance's own (a live run's estimate, to measure its error)."""
    from src.eda.match_timing import srcc_tennis_data as TD
    from src.eda.prediction_run import live_rows as LR
    targets, later = replay_select(base_tree, frame_path, week, rnd)
    players = pd.read_parquet(Path(base_tree) / DC.PD / "stage0_match_players.parquet",
                              columns=["match_id", "player_id", "player_name"]).astype({"match_id": str})
    raw = LR.staged_tml([int(week[:4])])
    rows = LR.replay_rows(targets, later, raw, players, placeholder_winner=winner)
    if str(rnd).startswith("Q") and str(rnd) != "QF":
        # the main draws are left out, so each live row names its event's main-draw start, as a live run's do
        # (live_rows' event_main_date, Stage 0's C05): here the instance's own date of the event, the exact test of
        # the code path; a live run's is the linker's estimate (src/pipeline/qualifying.main_draw_start)
        live = rows["live_role"].eq("live").to_numpy()
        rows.loc[live, "event_main_date"] = (pd.Timestamp(main_date).strftime("%Y%m%d") if main_date else
                                             pd.to_datetime(targets["tournament_date"]).dt.strftime("%Y%m%d").to_numpy())
        # qualifying: tennis-data holds none, so the day is the timeline's observed one, and the venue the event's
        # city as a live run finds it (prediction_run/run.venue_for)
        from src.eda.prediction_run import run as RUN
        obs = pd.read_parquet(Path(base_tree) / DC.MT / "timing.parquet", columns=["match_id", "obs"])
        obs = obs.astype({"match_id": str}).set_index("match_id")["obs"].reindex(targets["match_id"])
        if obs.isna().any():
            raise SystemExit("replay: a qualifying target has no observed day in the instance's timeline")
        days = pd.to_datetime(obs.to_numpy(dtype="float64"), unit="D").normalize()
        venue = pd.Series([RUN.venue_for(t, tid, n) for t, tid, n in
                           zip(targets["tour"], targets["tournament_id"], targets["tournament_name"])])
    else:
        o = pd.read_parquet(Path(base_tree) / DC.PD / "stage1_odds.parquet",
                            columns=["match_id", "td_date", "td_file", "td_row"]).astype({"match_id": str})
        o = o.set_index("match_id").reindex(targets["match_id"])
        if o["td_date"].isna().any():
            raise SystemExit("replay: a target lacks tennis-data's day")
        days = pd.to_datetime(o["td_date"]).dt.normalize().to_numpy()
        venue = TD.locations(o.reset_index().rename(columns={"index": "match_id"}))
    meta = pd.DataFrame({"match_id": targets["match_id"].to_numpy(),
                         "day": days, "p_a": np.nan,
                         "venue": venue.to_numpy(), "tour": targets["tour"].to_numpy(),
                         "tournament_name": targets["tournament_name"].to_numpy(), "round": targets["round"].to_numpy(),
                         "dating": dating})
    real_a_won = targets["a_won"].astype(bool).to_numpy()
    meta["placeholder_is_real_result"] = real_a_won if winner == "A" else ~real_a_won
    rows.to_parquet(run_dir / "live_rows.parquet", index=False)
    meta.to_parquet(run_dir / "live_meta.parquet", index=False)
    return {"kind": "replay", "week": week, "round": rnd, "placeholder_winner": winner, "dating": dating,
            **({"main_date": main_date} if main_date else {}),
            "targets": int(len(targets)), "left_out_later": int(len(later)),
            "placeholder_reverses_result": int((~meta["placeholder_is_real_result"]).sum()),
            "by_event": targets.groupby(["tour", "tournament_name"]).size().rename("matches").reset_index()
            .to_dict("records"), "base_tree": str(base_tree), "frame": str(frame_path)}


def quote_times(meta: pd.DataFrame, matchups: pd.DataFrame | None) -> np.ndarray:
    """Each live match's quote time from the matchups CSV's optional quoted_at column (UTC, written
    YYYY-MM-DDTHH:MM:SSZ), None where absent. prediction_run's live_from_matchups writes one live match per CSV row in
    the CSV's order, so rows are matched by position, after checking that each row's tour and round agree (11 Oct 2026,
    agreed with the master-notebook session)."""
    out = np.full(len(meta), None, dtype=object)
    if matchups is None or "quoted_at" not in matchups.columns:
        return out
    same = (len(matchups) == len(meta)
            and (matchups["tour"].astype(str).to_numpy() == meta["tour"].astype(str).to_numpy()).all()
            and (matchups["round"].astype(str).str.upper().to_numpy() == meta["round"].astype(str).to_numpy()).all())
    if not same:
        raise SystemExit("prices: the matchups CSV's rows do not line up with the live matches; quoted_at cannot be placed")
    t = pd.to_datetime(matchups["quoted_at"], utc=True, format="ISO8601")
    out[:] = [None if pd.isna(x) else x.strftime("%Y-%m-%dT%H:%M:%SZ") for x in t]
    return out


def prices(run_dir: Path, replay_frame: Path | None = None, matchups_csv: Path | None = None) -> dict:
    """prices.parquet (match_id, p_a, source, recorded_at: when this step ran, quoted_at: the quote's own time when
    the matchups CSV gives it) and live_meta's p_a: live, the CSV's (already side A's in live_meta); a replay, the
    instance frame's Pinnacle-first price (its p_mkt, side A's)."""
    meta = pd.read_parquet(run_dir / "live_meta.parquet")
    meta["match_id"] = meta["match_id"].astype(str)
    given = replay_frame is None and matchups_csv is not None and Path(matchups_csv).exists()
    quoted = quote_times(meta, pd.read_csv(matchups_csv) if given else None)
    if replay_frame is not None:
        f = pd.read_parquet(replay_frame, columns=["match_id", "p_mkt", "odds_input"]).astype({"match_id": str})
        f = f.set_index("match_id").reindex(meta["match_id"])
        if f["p_mkt"].isna().any():
            raise SystemExit("prices: a replayed match is not in the instance frame")
        meta["p_a"] = f["p_mkt"].to_numpy(dtype="float64")
        source = ("instance frame p_mkt (" + f["odds_input"].astype(str) + ")").to_numpy()
    else:
        source = np.full(len(meta), "matchups csv (margin-free, side A)", dtype=object)
    p = meta["p_a"].to_numpy(dtype="float64")
    if not ((p > 0) & (p < 1)).all():
        raise SystemExit("prices: every match needs a price strictly between 0 and 1")
    meta.to_parquet(run_dir / "live_meta.parquet", index=False)
    t = pd.DataFrame({"match_id": meta["match_id"], "p_a": p, "source": source, "recorded_at": DC.stamp(),
                      "quoted_at": pd.Series(quoted, dtype="object")})
    t.to_parquet(run_dir / "prices.parquet", index=False)
    return {"priced": int(len(t)), "sources": pd.Series(source).value_counts().to_dict(),
            "quoted_at_given": int(pd.notna(t["quoted_at"]).sum())}
