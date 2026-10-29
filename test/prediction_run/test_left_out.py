"""One match that cannot be placed is left out with its reason, and the others go on (28 Oct 2026, the owner: "while
you fix a single row it shouldnt hold up the whole pipeline"; docs/decisions/2026-10-28-one-bad-match-left-out.md;
master pipeline process log, Part 25), offline.

    the matchups step   live_from_matchups(leave_out=True): each row placed alone; its live row goes with it; the
                        earlier rounds the same, one by one and as a whole
    the live rows' check  inject.check(leave_out=True): each cause said apart (an id Stage 0 built otherwise, no row,
                        not built as live, no Stage 1 row to come, the sides)
Without leave_out each still stops the run, as before (the 8 Oct path and replays).

Run: ./python.sh -m pytest test/prediction_run/test_left_out.py -q
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.eda.prediction_run import earlier_rounds as ER  # noqa: E402
from src.eda.prediction_run import fills as FL  # noqa: E402
from src.eda.prediction_run import inject as INJ  # noqa: E402
from src.eda.prediction_run import live_rows as LR  # noqa: E402
from src.eda.prediction_run import run as RUN  # noqa: E402
from src.eda.predictability_diagnostic import common as C  # noqa: E402
from src.eda.predictability_diagnostic import stage0_build as B  # noqa: E402


def tml(tid, name, rnd, w, lo, row, date="20261026", src="t.csv"):
    """A staged TML row (as live_rows.staged_tml reads them); w and lo: (id, name)."""
    r = {c: "" for c in B.KEEP}
    r.update({"tourney_id": tid, "tourney_name": name, "surface": "Hard", "draw_size": "32", "tourney_level": "250",
              "indoor": "O", "tourney_date": date, "best_of": "3", "round": rnd, "match_num": str(row),
              "score": "6-3 6-4", "winner_id": w[0], "winner_name": w[1], "loser_id": lo[0], "loser_name": lo[1],
              "_source_file": src, "_row": row, "tour": "wta"})
    return r


def staged(rows) -> pd.DataFrame:
    raw = pd.DataFrame(rows)
    raw["_row"] = pd.to_numeric(raw["_row"]).astype("Int64")
    return raw


def s0(tid, rnd, w, lo, row, source="tml", src="t.csv", has_box=True):
    """A Stage 0 match and its two player rows; w and lo: (id, name). The sides follow the name, as the builder's do."""
    lo_h, hi_h = sorted([w[0], lo[0]])
    mid = f"wta|{tid}|{rnd}|{lo_h}|{hi_h}"
    a, b = (w, lo) if w[0] == (lo_h if C.side_is_low(mid) else hi_h) else (lo, w)
    match = {"match_id": mid, "tour": "wta", "tournament_id": tid, "round": rnd, "source": source, "source_file": src,
             "source_row": row, "tournament_date": pd.Timestamp("2026-10-26"), "player_a_id": a[0],
             "player_b_id": b[0], "a_won": a is w, "has_box": has_box}
    bio = {"rank": None, "rank_points": None, "age": 25.0, "height": None, "hand": "R", "country": None}
    return match, [{"match_id": mid, "player_id": a[0], "side": "A", "player_name": a[1], **bio},
                   {"match_id": mid, "player_id": b[0], "side": "B", "player_name": b[1], **bio}]


def stage0_folder(folder: Path, built) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([x[0] for x in built]).astype({"source_row": "Int64"}).to_parquet(folder / "stage0_matches.parquet")
    pd.DataFrame([r for x in built for r in x[1]]).to_parquet(folder / "stage0_match_players.parquet")


BONDAR, CHEN, ZHANG, QUEVEDO = ("214388", "Anna Bondar"), ("300001", "Ena Chen"), ("213550", "Shuai Zhang"), \
    ("259733", "Kaitlin Quevedo")
DELTA = ("999", "Dana Delta")                            # in Tennis My Life's rows, not in Stage 0's
RAW = [tml("2026-1023", "Guangzhou", "R32", QUEVEDO, ZHANG, 23), tml("2026-1023", "Guangzhou", "R32", BONDAR, CHEN, 24),
       tml("2026-1023", "Guangzhou", "R32", DELTA, ("888", "Fay Foxtrot"), 25)]
BUILT = [s0("2026-1023", "R32", ("wta:259733", "Kaitlin Quevedo"), ("wta:213550", "Shuai Zhang"), 23),
         s0("2026-1023", "R32", ("wta:214388", "Anna Bondar"), ("wta:300001", "Ena Chen"), 24)]


def matchups(*rows) -> pd.DataFrame:
    return pd.DataFrame([{"tour": "wta", "tourney_id": "2026-1023", "round": "R16", "player_a": a, "player_b": b,
                          "day": day, "p_a": p, "tourney_name": "Guangzhou"} for a, b, p, day in rows])


@pytest.fixture()
def world(tmp_path, monkeypatch):
    stage0_folder(tmp_path / "stage0", BUILT)
    monkeypatch.setattr(LR, "staged_tml", lambda seasons: staged(RAW))
    monkeypatch.setattr(RUN, "venue_for", lambda tour, tid, name: "Guangzhou")
    return tmp_path


GOOD = ("Anna Bondar", "Kaitlin Quevedo", 0.55, "2026-10-29")


def test_a_row_that_cannot_be_placed_is_left_out_and_the_others_written(world):
    mu = matchups(GOOD, ("Nobody Atall", "Shuai Zhang", 0.5, "2026-10-29"),     # no row names him: the live row fails
                  ("Dana Delta", "Ena Chen", 0.5, "2026-10-29"),                  # TML's, not Stage 0's: the meta fails
                  ("Shuai Zhang", "Ena Chen", "abc", "2026-10-29"),               # a price that is not a number
                  ("Ena Chen", "Shuai Zhang", 0.5, "not a day"))                  # a day that cannot be read
    res = RUN.live_from_matchups(mu, world / "stage0", world, leave_out=True)
    left = {r["csv_row"]: r for r in res["left_out"]}
    assert sorted(left) == [1, 2, 3, 4] and res["live_matches"] == 1
    assert "no TML row names the player" in left[1]["reason"]
    assert "'Dana Delta' names 0 Stage 0 players" in left[2]["reason"]
    assert left[3]["reason"].startswith("ValueError") and left[4]["reason"]
    assert (left[2]["player_a"], left[2]["round"], left[2]["tourney_name"]) == ("Dana Delta", "R16", "Guangzhou")
    meta = pd.read_parquet(world / "live_meta.parquet")
    assert meta["csv_row"].tolist() == [0] and meta["player_a"].tolist() == ["Anna Bondar"]
    rows = pd.read_parquet(world / "live_rows.parquet")
    assert rows["_row"].tolist() == [0] and rows["live_role"].tolist() == ["live"]   # their live rows went with them


def test_the_good_row_is_built_as_it_was_alone(world, tmp_path):
    """The match left standing gets the live row and meta a CSV of it alone gives (its csv_row aside)."""
    alone = tmp_path / "alone"
    alone.mkdir()
    RUN.live_from_matchups(matchups(GOOD), world / "stage0", alone, leave_out=True)
    RUN.live_from_matchups(matchups(("Nobody Atall", "Shuai Zhang", 0.5, "2026-10-29"), GOOD), world / "stage0", world,
                           leave_out=True)
    a, b = (pd.read_parquet(alone / "live_rows.parquet"), pd.read_parquet(world / "live_rows.parquet"))
    keep = [c for c in a.columns if c not in ("match_num", "_row")]       # its position in the CSV names those two
    pd.testing.assert_frame_equal(a[keep], b[keep])
    ma, mb = pd.read_parquet(alone / "live_meta.parquet"), pd.read_parquet(world / "live_meta.parquet")
    pd.testing.assert_frame_equal(ma.drop(columns="csv_row"), mb.drop(columns="csv_row"))
    assert mb["csv_row"].tolist() == [1]


def test_without_leave_out_a_bad_row_still_stops_the_run(world):
    with pytest.raises(SystemExit, match="no TML row names the player"):
        RUN.live_from_matchups(matchups(GOOD, ("Nobody Atall", "Shuai Zhang", 0.5, "2026-10-29")), world / "stage0",
                               world)
    with pytest.raises(SystemExit, match="names 0 Stage 0 players"):
        RUN.live_from_matchups(matchups(("Dana Delta", "Ena Chen", 0.5, "2026-10-29")), world / "stage0", world)


def test_a_csv_with_every_match_left_out_stops(world):
    with pytest.raises(SystemExit, match=r"every match was left out \(2\)"):
        RUN.live_from_matchups(matchups(("Nobody Atall", "Shuai Zhang", 0.5, "2026-10-29"),
                                        ("Dana Delta", "Ena Chen", 0.5, "2026-10-29")), world / "stage0", world,
                               leave_out=True)


def test_upcoming_rows_puts_each_failure_under_its_position():
    failed = {}
    rows = LR.upcoming_rows(matchups(GOOD, ("Nobody Atall", "Shuai Zhang", 0.5, "2026-10-29")), staged(RAW),
                            failed=failed)
    assert rows["_row"].tolist() == [0] and list(failed) == [1]
    assert LR.upcoming_rows(matchups(("Nobody Atall", "Shuai Zhang", 0.5, "2026-10-29")), staged(RAW),
                            failed={}).empty


# --- the earlier rounds from TennisLive ----------------------------------------------------------------------------------
def sidecar(*rows) -> pd.DataFrame:
    return pd.DataFrame([{"tour": "wta", "tourney_id": "2026-1023", "tourney_name": "Guangzhou", "round": rnd,
                          "winner_name": w, "loser_name": lo, "score": "6-3 6-4", "day": "2026-10-25", "best_of": "3",
                          "tl_url": url, "event_main_date": main} for rnd, w, lo, url, main in rows])


def test_an_earlier_round_that_fails_is_left_out_with_its_reason(world):
    keyed = pd.read_parquet(world / "stage0" / "stage0_match_players.parquet")
    keyed = keyed.assign(key=B.S.keys_for(keyed["player_name"]), tour="wta")
    e = sidecar(("Q2", "Kaitlin Quevedo", "Ena Chen", "/q2", ""), ("Q1", "Anna Bondar", "Shuai Zhang", "/q1", "garbage"))
    players = LR.stage0_players(world / "stage0")
    played, meta, left = ER.played_rows(e, staged(RAW), players, keyed, lambda r: "2026-1023", leave_out=True)
    assert len(played) == 1 and meta["tl_url"].tolist() == ["/q2"]
    assert left == [{"tl_url": "/q1", "reason": left[0]["reason"]}] and left[0]["reason"].startswith("ValueError")
    with pytest.raises(ValueError):
        ER.played_rows(e, staged(RAW), players, keyed, lambda r: "2026-1023")


def test_a_published_round_that_fails_is_noted_not_passed_on(world, monkeypatch):
    built = BUILT + [s0("2026-1023", "Q2", ("wta:259733", "Kaitlin Quevedo"), ("wta:300001", "Ena Chen"), 20,
                        has_box=False)]
    stage0_folder(world / "s2", built)
    keyed = pd.read_parquet(world / "s2" / "stage0_match_players.parquet")
    keyed = keyed.assign(key=B.S.keys_for(keyed["player_name"]), tour="wta")
    monkeypatch.setattr(FL, "tml_keys", lambda s, raw: (_ for _ in ()).throw(KeyError("no staged row")))
    e = sidecar(("Q2", "Kaitlin Quevedo", "Ena Chen", "/q2", ""))
    over, rest, notes = RUN.tml_box_fills(e, staged(RAW), world / "s2", keyed, lambda r: "2026-1023", leave_out=True)
    assert over.empty and rest.empty                      # neither filled nor made a played row
    assert notes[0]["error"].startswith("KeyError") and notes[0]["tl_url"] == "/q2"
    with pytest.raises(KeyError):
        RUN.tml_box_fills(e, staged(RAW), world / "s2", keyed, lambda r: "2026-1023")


def test_when_the_earlier_rounds_fail_as_a_whole_the_matches_still_go_on(world, monkeypatch):
    monkeypatch.setattr(RUN, "tml_box_fills", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("TennisLive broke")))
    e = sidecar(("Q2", "Kaitlin Quevedo", "Ena Chen", "/q2", ""))
    res = RUN.live_from_matchups(matchups(GOOD), world / "stage0", world, e, leave_out=True)
    assert res["live_matches"] == 1 and res["earlier_rounds"]["filled"] == 0
    assert res["earlier_left_out"][0]["winner"] == "Kaitlin Quevedo"
    assert "the earlier rounds could not be added: RuntimeError: TennisLive broke" in res["earlier_left_out"][0]["reason"]
    assert pd.read_parquet(world / "played_meta.parquet").empty
    with pytest.raises(RuntimeError):
        RUN.live_from_matchups(matchups(GOOD), world / "stage0", world, e)


# --- the live rows' check --------------------------------------------------------------------------------------------
def check_world(tmp_path, monkeypatch, rows, players):
    pd.DataFrame(rows).astype({"source_row": "Int64"}).to_parquet(tmp_path / "m.parquet")
    pd.DataFrame(players).to_parquet(tmp_path / "p.parquet")
    (tmp_path / "stage0_summary.json").write_text(json.dumps({"live_rows": {"rows": len(rows)}}), encoding="utf-8")
    monkeypatch.setattr(C, "MATCHES", tmp_path / "m.parquet")
    monkeypatch.setattr(C, "MATCH_PLAYERS", tmp_path / "p.parquet")
    monkeypatch.setattr(C, "OUT", tmp_path)
    monkeypatch.setattr(INJ, "PLAYED", tmp_path / "no_played_meta.parquet")


def m_row(mid, row, level="T250", qualifying=False, has_box=False, a="wta:1", b="wta:2", source_file="live_rows"):
    return {"match_id": mid, "status": "completed", "evaluation": True, "has_box": has_box, "level": level,
            "qualifying": qualifying, "source_file": source_file, "source_row": row, "player_a_id": a,
            "player_b_id": b}


def sides(mid, a="wta:1", b="wta:2"):
    return [{"match_id": mid, "player_id": a, "side": "A"}, {"match_id": mid, "player_id": b, "side": "B"}]


def test_the_check_names_each_cause_apart(tmp_path, monkeypatch):
    ok, other = "wta|e|R16|wta:1|wta:2", "wta|e|R16|wta:1|wta:77"
    rows = [m_row(ok, 0), m_row(other, 1),                                         # row 1 built under another id
            m_row("wta|e|R16|wta:5|wta:6", 3, has_box=True, a="wta:5", b="wta:6"),
            m_row("wta|e|R16|wta:7|wta:8", 4, level="CH", a="wta:7", b="wta:8"),
            m_row("wta|e|Q2|wta:9|wta:10", 5, level="CH", qualifying=True, a="wta:9", b="wta:10"),
            m_row("wta|e|R16|wta:11|wta:12", 6, a="wta:11", b="wta:12")]
    players = (sides(ok) + sides(other, b="wta:77") + sides("wta|e|R16|wta:5|wta:6", "wta:5", "wta:6")
               + sides("wta|e|R16|wta:7|wta:8", "wta:7", "wta:8") + sides("wta|e|Q2|wta:9|wta:10", "wta:9", "wta:10")
               + sides("wta|e|R16|wta:11|wta:12", "wta:12", "wta:11"))             # the last one's sides swapped
    check_world(tmp_path, monkeypatch, rows, players)
    meta = pd.DataFrame({"match_id": [ok, "wta|e|R16|wta:1|wta:3", "wta|e|R16|wta:1|wta:4", "wta|e|R16|wta:5|wta:6",
                                      "wta|e|R16|wta:7|wta:8", "wta|e|Q2|wta:9|wta:10", "wta|e|R16|wta:11|wta:12"],
                         "csv_row": [0, 1, 2, 3, 4, 5, 6]})
    out = INJ.check(meta, leave_out=True)
    why = {r["match_id"]: r["reason"] for r in out["left_out"]}
    assert ok not in why and "wta|e|Q2|wta:9|wta:10" not in why             # a qualifying match needs no Stage 1 row
    assert f"Stage 0 built its live row as {other}" in why["wta|e|R16|wta:1|wta:3"]
    assert "Stage 0's build kept no row of it" in why["wta|e|R16|wta:1|wta:4"]
    assert "not built as a live match" in why["wta|e|R16|wta:5|wta:6"] and "box score True" in why["wta|e|R16|wta:5|wta:6"]
    assert "level CH, which Stage 1 does not price" in why["wta|e|R16|wta:7|wta:8"]
    assert "do not give the match row's two sides" in why["wta|e|R16|wta:11|wta:12"]
    with pytest.raises(SystemExit, match="missing from Stage 0 or not built as expected"):
        INJ.check(meta)                                                      # without leave_out: as before


def test_the_check_stops_when_no_live_match_can_be_placed(tmp_path, monkeypatch):
    check_world(tmp_path, monkeypatch, [m_row("wta|e|R16|wta:1|wta:2", 0)], sides("wta|e|R16|wta:1|wta:2"))
    with pytest.raises(SystemExit, match="no live match can be placed"):
        INJ.check(pd.DataFrame({"match_id": ["wta|e|R16|wta:1|wta:9"], "csv_row": [0]}), leave_out=True)
    assert "left_out" not in INJ.check(pd.DataFrame({"match_id": ["wta|e|R16|wta:1|wta:2"], "csv_row": [0]}),
                                       leave_out=True)
