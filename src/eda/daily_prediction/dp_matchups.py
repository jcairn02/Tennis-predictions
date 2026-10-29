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
    """The CSV's matches as live rows; its sidecar's earlier qualifying rounds (prediction_run/earlier_rounds.py, since
    24 Oct 2026) as live rows with their results, when the linker wrote one. A match whose row cannot be placed is left
    out with its reason and the others written (since 28 Oct 2026; dp_leftout), as is an earlier round."""
    import dp_leftout as LO
    from src.eda.prediction_run import earlier_rounds as ER
    from src.eda.prediction_run import run as RUN
    from src.eda.predictability_diagnostic import common as C
    s0 = stage0 or ((run_dir / "stage0") if (run_dir / "stage0" / "stage0_matches.parquet").exists() else C.OUT)
    side = ER.sidecar(csv)
    earlier = pd.read_csv(side, dtype=str, keep_default_na=False) if side.exists() else None
    LO.reset(run_dir)                                   # every live row is built anew: no earlier attempt's records
    res = RUN.live_from_matchups(pd.read_csv(csv), Path(s0), run_dir, earlier, leave_out=True)
    LO.add(run_dir, "matchups", matches=res.get("left_out") or [], earlier=res.get("earlier_left_out") or [])
    return {"stage0": str(s0), **res}


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


def _tl_section(tour: str, name: str, year: int) -> pd.DataFrame:
    """TennisLive's results rows of an event, from the repository's raw copy (the work tree holds none): the one
    section file of the year whose slug holds every word of the event's name (Stage 0's "Shanghai Masters" is
    TennisLive's shanghai-rolex-masters-shanghai)."""
    from src.ingest.point_sources import common as PS
    from src.ingest.point_sources import tennislive_events as TLE
    folder = DC.REPO / "data" / "raw" / "point_sources" / "tennislive" / "tournaments" / TLE.SECTION_DIRS[tour]
    words = str(name).lower().split()
    hits = [f for f in folder.glob(f"*-{year}__results.json.gz") if "challenger" not in f.name
            and all(w in f.name.split("__")[0].split("-") for w in words)
            and not f.name.startswith(("m15", "m25", "w15", "w35", "w50", "w75", "w100"))]
    if len(hits) != 1:
        raise SystemExit(f"replay earlier rounds: {len(hits)} TennisLive sections for {tour} {name} {year}: "
                         f"{[h.name for h in hits]}")
    slug = hits[0].name.split("__")[0]
    ev = {"key": slug, "tour": tour, "url": f"/{TLE.SECTION_DIRS[tour]}/{slug}/", "name": name}
    return pd.DataFrame(TLE.section_rows(PS.read_json(hits[0]), ev, {"retrieved_at": None}))


def replay_earlier(targets: pd.DataFrame, base_tree: Path, raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame,
                                                                                         dict]:
    """--replay-earlier tennislive (24 Oct 2026): each target's players' earlier qualifying rounds at the event, their
    TML rows left out ("drop") and given again as a live run gives them (src/pipeline/live._earlier, then
    prediction_run/earlier_rounds.played_rows): TennisLive's score and its match page's box score, from the
    repository's raw copies. (drop rows, played rows, record).
    Since 25 Oct 2026 also a main-draw round's targets (their qualifiers' and lucky losers' every qualifying round), and
    a round a package or feed holds (women's qualifying): it needs no drop row, as the tables step's merge skips the
    package's copy once Stage 0 holds the same meeting (current_best_model/additions.merge), as in a live run; its fill
    takes the target's event id and name, as the live linker gives it. TennisLive's names are matched as the linker
    matches them (earlier_rounds.same_player: "Chak Lam Coleman Wong" for "Coleman Wong")."""
    from src.eda.prediction_run import earlier_rounds as ER
    from src.eda.prediction_run import live_rows as LR
    from src.eda.predictability_diagnostic import stage0_build as B
    from src.ingest.point_sources import common as PS
    from src.ingest.point_sources import tennislive as TL
    m = pd.read_parquet(Path(base_tree) / DC.PD / "stage0_matches.parquet")
    m["match_id"] = m["match_id"].astype(str)
    p = pd.read_parquet(Path(base_tree) / DC.PD / "stage0_match_players.parquet",
                        columns=["match_id", "player_id", "side", "player_name"]).astype({"match_id": str})
    names = p.drop_duplicates("player_id").set_index("player_id")["player_name"]
    base = m["tournament_id"].astype(str).str.split("-").str[:2].str.join("-")
    picked = []
    for _, t in targets.iterrows():
        tb = "-".join(str(t["tournament_id"]).split("-")[:2])
        prev = m[m["tour"].eq(t["tour"]) & m["qualifying"].astype(bool) & base.eq(tb)
                 & (m["round_order"] < t["round_order"])
                 & (m["player_a_id"].isin([t["player_a_id"], t["player_b_id"]])
                    | m["player_b_id"].isin([t["player_a_id"], t["player_b_id"]]))]
        picked.append(prev.assign(_target=t["match_id"]))
    prev = pd.concat(picked).drop_duplicates("match_id").reset_index(drop=True)
    tml = prev["source"].astype(str).eq("tml").to_numpy()
    own = LR.raw_of(prev[tml], raw)
    drops = own.assign(tour=prev.loc[tml, "tour"].to_numpy(), live_role="drop")
    target_raw = LR.raw_of(targets, raw).set_axis(targets["match_id"].to_numpy())
    sections, side_rows, missing = {}, [], []
    for i, pm in prev.iterrows():
        key = (pm["tour"], pm["tournament_name"], int(str(pm["tournament_date"])[:4]))
        if key not in sections:
            sections[key] = _tl_section(*key)
        q = sections[key]
        q = q[q["draw"].astype(str).eq("qualifying") & q["discipline"].astype(str).eq("singles")
              & q["round"].astype(str).eq(pm["round"])]
        wid = pm["player_a_id"] if bool(pm["a_won"]) else pm["player_b_id"]
        lid = pm["player_b_id"] if bool(pm["a_won"]) else pm["player_a_id"]
        wn, ln = str(names[wid]), str(names[lid])
        s1w, s2l = q["player1_name"].map(lambda n: ER.same_player(n, wn)), q["player2_name"].map(lambda n: ER.same_player(n, ln))
        s1l, s2w = q["player1_name"].map(lambda n: ER.same_player(n, ln)), q["player2_name"].map(lambda n: ER.same_player(n, wn))
        hit = q[(s1w & s2l) | (s1l & s2w)]
        if len(hit) != 1:
            missing.append({"match_id": pm["match_id"], "reason": f"{len(hit)} TennisLive rows"})
            continue
        w = hit.iloc[0]
        side = 1 if ER.same_player(w["player1_name"], wn) else 2
        if int(w["winner_side"]) != side:
            missing.append({"match_id": pm["match_id"], "reason": "TennisLive names the other winner"})
            continue
        box, note = None, "no match page on disk"
        score = ER.tl_score(w["player1_sets"], w["player2_sets"], side, w.get("end_reason"))
        parts = TL.match_path_parts(str(w["url"]))
        page = (DC.REPO / "data" / "raw" / "point_sources" / "tennislive" / "matches" / parts[0] / parts[1]
                / f"{parts[2]}.html.gz") if parts else None
        if page is not None and page.exists():
            parsed = TL.parse_match_page(PS.read_bytes(page).decode("utf-8", errors="replace"))
            pmeta = parsed["meta"]
            pw = 2 if str(pmeta.get("winner_id")) == str(pmeta.get("player2_id")) else 1
            box, note = ER.tl_box(parsed["statistics"], pw, pmeta.get("first_server_index"), score)
        fin = ER.finish_utc(w)
        # the event's id and name: a TML row's own; a package's round, its target's (the live linker's choice)
        r_own = own.iloc[int(tml[:i].sum())] if tml[i] else target_raw.loc[pm["_target"]]
        side_rows.append({"tour": pm["tour"], "tourney_id": str(r_own["tourney_id"]), "tourney_name": r_own["tourney_name"],
                          "round": pm["round"], "winner_name": wn, "loser_name": ln, "score": score,
                          "day": ER.uk_day(pd.to_datetime(w.get("start_utc"), utc=True, errors="coerce")) or ER.uk_day(fin),
                          "tl_url": w["url"], "box_note": note, "_tid": pm["tournament_id"], "_mid": pm["match_id"],
                          "best_of": 3, "venue": None, **(box or {})})
    side = pd.DataFrame(side_rows)
    keyed = p.assign(key=B.S.keys_for(p["player_name"])).merge(m[["match_id", "tour"]], on="match_id")
    played, pmeta, left = ER.played_rows(side, raw, LR.stage0_players(Path(base_tree) / DC.PD), keyed,
                                         lambda e: e["_tid"], LR.id_handles(m, p, raw))   # ids as Stage 0 names them
    mid_of = side.set_index("tl_url")["_mid"] if len(side) else pd.Series(dtype=str)
    same_id = int((pmeta["match_id"] == pmeta["tl_url"].map(mid_of)).sum()) if len(pmeta) else 0
    src_score = pd.Series(own["score"].astype(str).to_numpy(), index=prev.loc[tml, "match_id"].to_numpy())
    rec = {"earlier_rounds": int(len(prev)), "dropped_tml_rows": int(len(drops)),
           "package_rows_kept_for_the_merge": int((~tml).sum()), "filled": int(len(played)),
           "with_box": int(pmeta["has_box"].sum()) if len(pmeta) else 0, "same_match_id_as_stage0": same_id,
           "score_equal_tml": int((side["score"].astype(str) == side["_mid"].map(src_score)).sum()) if len(side) else 0,
           "not_found": missing, "left_out": left}
    return drops, played, rec


def replay(run_dir: Path, week: str, rnd: str, winner: str = "A", base_tree: Path = DC.BASE_TREE,
           frame_path: Path = DC.INSTANCE / "model_frame.parquet", dating: str = "training",
           main_date: str | None = None, earlier: str | None = None) -> dict:
    """Runs inside the work tree (its staged TML is the freeze's view). main_date (a qualifying round, YYYY-MM-DD): the
    main-draw start every live row names instead of the instance's own (a live run's estimate, to measure its error).
    earlier ("tennislive", a qualifying round after round 1): the targets' earlier rounds as a live run fills them
    (replay_earlier)."""
    from src.eda.match_timing import srcc_tennis_data as TD
    from src.eda.prediction_run import live_rows as LR
    targets, later = replay_select(base_tree, frame_path, week, rnd)
    players = pd.read_parquet(Path(base_tree) / DC.PD / "stage0_match_players.parquet",
                              columns=["match_id", "player_id", "player_name"]).astype({"match_id": str})
    raw = LR.staged_tml([int(week[:4])])
    rows = LR.replay_rows(targets, later, raw, players, placeholder_winner=winner)
    earlier_rec = None
    if earlier == "tennislive":
        drops, played, earlier_rec = replay_earlier(targets, base_tree, raw)
        rows = pd.concat([rows, drops, played], ignore_index=True)
    elif earlier:
        raise SystemExit(f"replay: earlier rounds {earlier!r} unknown (tennislive)")
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
            **({"main_date": main_date} if main_date else {}), **({"earlier": earlier_rec} if earlier_rec else {}),
            "targets": int(len(targets)), "left_out_later": int(len(later)),
            "placeholder_reverses_result": int((~meta["placeholder_is_real_result"]).sum()),
            "by_event": targets.groupby(["tour", "tournament_name"]).size().rename("matches").reset_index()
            .to_dict("records"), "base_tree": str(base_tree), "frame": str(frame_path)}


def quote_times(meta: pd.DataFrame, matchups: pd.DataFrame | None) -> np.ndarray:
    """Each live match's quote time from the matchups CSV's optional quoted_at column (UTC, written
    YYYY-MM-DDTHH:MM:SSZ), None where absent. prediction_run's live_from_matchups writes one live match per CSV row in
    the CSV's order, so rows are matched by position, after checking that each row's tour and round agree (11 Oct 2026,
    agreed with the master-notebook session). Since 28 Oct 2026 a live meta names each match's CSV row (csv_row: a row
    left out has no match) and the rows are taken by it; a meta without it is matched by position, as before."""
    out = np.full(len(meta), None, dtype=object)
    if matchups is None or "quoted_at" not in matchups.columns:
        return out
    if "csv_row" in meta.columns:
        pos = pd.to_numeric(meta["csv_row"], errors="coerce")
        if pos.isna().any() or (pos < 0).any() or (pos >= len(matchups)).any():
            raise SystemExit("prices: a live match names no row of the matchups CSV; quoted_at cannot be placed")
        matchups = matchups.iloc[pos.astype(int).to_numpy()].reset_index(drop=True)
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
    instance frame's Pinnacle-first price (its p_mkt, side A's). A live match whose price is not strictly between 0 and
    1 is left out, its live row with it (since 28 Oct 2026; dp_leftout); a replay's stops the run."""
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
    bad = ~((p > 0) & (p < 1))
    if bad.any() and replay_frame is None and "csv_row" in meta.columns:     # a live run: those matches left out
        import dp_leftout as LO
        gone = meta[bad]
        LO.drop(run_dir, gone["csv_row"])
        LO.add(run_dir, "prices", matches=LO.from_meta(gone, "its price is not strictly between 0 and 1 (side A's "
                                                             "chance: " + ", ".join(f"{x:g}" for x in p[bad]) + ")"))
        keep = ~bad
        meta, p, quoted, source = meta[keep].reset_index(drop=True), p[keep], quoted[keep], source[keep]
        if meta.empty:
            raise SystemExit("prices: every match was left out: no price strictly between 0 and 1")
    if not ((p > 0) & (p < 1)).all():
        raise SystemExit("prices: every match needs a price strictly between 0 and 1")
    meta.to_parquet(run_dir / "live_meta.parquet", index=False)
    t = pd.DataFrame({"match_id": meta["match_id"], "p_a": p, "source": source, "recorded_at": DC.stamp(),
                      "quoted_at": pd.Series(quoted, dtype="object")})
    t.to_parquet(run_dir / "prices.parquet", index=False)
    return {"priced": int(len(t)), "sources": pd.Series(source).value_counts().to_dict(),
            "quoted_at_given": int(pd.notna(t["quoted_at"]).sum())}
