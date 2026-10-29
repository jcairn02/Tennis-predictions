"""A live run leaves out a match it cannot place, says so, and predicts the others (28 Oct 2026, the owner: "while you
fix a single row it shouldnt hold up the whole pipeline"; docs/decisions/2026-10-28-one-bad-match-left-out.md; master
pipeline process log, Part 25), offline: the run's record (dp_leftout), the prices step, and the tables step's second
Stage 0 without the matches its check could not place (dp_tables.prep, with the work tree's scripts stood in for).

Run: ./python.sh -m pytest test/daily_prediction/test_dp_left_out.py -q
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

import dp_common as DC
import dp_leftout as LO
import dp_matchups as MU
import dp_tables as TB


def live_files(folder, n=4, p=None):
    """A run's live rows (n live, one earlier round), meta (csv_row 0 .. n-1) and prices."""
    folder.mkdir(parents=True, exist_ok=True)
    ids = [f"atp|2026-1|R16|atp:{2 * i}|atp:{2 * i + 1}" for i in range(n)]
    rows = pd.DataFrame({"tour": "atp", "round": "R16", "winner_name": [f"W{i}" for i in range(n)] + ["Q"],
                         "loser_name": [f"L{i}" for i in range(n)] + ["R"], "live_role": ["live"] * n + ["played"],
                         "_source_file": ["live_rows"] * n + ["earlier_rounds"], "_row": list(range(n)) + [0]})
    rows.to_parquet(folder / "live_rows.parquet", index=False)
    meta = pd.DataFrame({"match_id": ids, "day": pd.Timestamp("2026-10-29"), "p_a": p or [0.5] * n, "venue": "Basel",
                         "tour": "atp", "tournament_name": "Basel", "round": "R16",
                         "player_a": [f"W{i}" for i in range(n)], "player_b": [f"L{i}" for i in range(n)],
                         "csv_row": list(range(n))})
    meta.to_parquet(folder / "live_meta.parquet", index=False)
    pd.DataFrame({"match_id": ids, "p_a": 0.5}).to_parquet(folder / "prices.parquet", index=False)
    return ids


def test_the_record_adds_resets_and_describes(tmp_path, capsys):
    LO.add(tmp_path, "check", matches=[{"csv_row": None, "tour": "wta", "tourney_name": "Guangzhou", "round": "R16",
                                        "player_a": "Ann", "player_b": "Bea", "reason": "a check's"}])
    LO.add(tmp_path, "matchups", matches=[{"csv_row": pd.Series([3]).iloc[0], "tour": "atp", "tourney_id": "2026-1",
                                           "round": "R16", "player_a": "Cal", "player_b": "Dan",
                                           "day": pd.Timestamp("2026-10-29"), "reason": "no event"}],
           earlier=[{"tour": "atp", "tourney_name": "Basel", "round": "Q2", "winner": "Eve", "loser": "Fay",
                     "reason": "not placed"}])
    held = LO.read(tmp_path)
    assert [r["step"] for r in held["matches"]] == ["check", "matchups"]
    assert held["matches"][1]["csv_row"] == 3 and held["matches"][1]["day"] == "2026-10-29"   # plain JSON values
    assert LO.describe(held["matches"][1]) == "ATP 2026-1 R16: Cal v Dan"
    assert LO.describe_earlier(held["earlier_rounds"][0]) == "ATP Basel Q2: Eve beat Fay"
    out = capsys.readouterr().out
    assert "!!! LEFT OUT at the matchups step, an error in its row: ATP 2026-1 R16: Cal v Dan -- no event" in out
    assert "!!! EARLIER ROUND NOT ADDED" in out
    LO.reset(tmp_path)                                    # a matchups step run again: A4's own records stay
    assert [r["step"] for r in LO.read(tmp_path)["matches"]] == ["check"] and not LO.read(tmp_path)["earlier_rounds"]
    assert LO.read(tmp_path / "nowhere") == {"matches": [], "earlier_rounds": []}


def test_drop_takes_a_match_out_of_every_table_and_keeps_its_earlier_rounds(tmp_path):
    ids = live_files(tmp_path)
    before = pd.read_parquet(tmp_path / "live_rows.parquet")
    assert LO.drop(tmp_path, [1, 3]) == {"live_meta": 2, "live_rows": 2, "prices": 2}
    assert pd.read_parquet(tmp_path / "live_meta.parquet")["csv_row"].tolist() == [0, 2]
    assert pd.read_parquet(tmp_path / "prices.parquet")["match_id"].tolist() == [ids[0], ids[2]]
    after = pd.read_parquet(tmp_path / "live_rows.parquet")
    pd.testing.assert_frame_equal(after, before.iloc[[0, 2, 4]].reset_index(drop=True))   # the rest as they were


def test_quote_times_follow_the_meta_rows_of_the_csv():
    meta = pd.DataFrame({"match_id": ["m0", "m2"], "tour": ["atp", "atp"], "round": ["R16", "QF"], "csv_row": [0, 2]})
    csv = pd.DataFrame({"tour": ["atp", "atp", "atp"], "round": ["R16", "R32", "QF"],
                        "quoted_at": ["2026-10-28T10:00:00Z", "2026-10-28T10:01:00Z", "2026-10-28T10:02:00Z"]})
    assert MU.quote_times(meta, csv).tolist() == ["2026-10-28T10:00:00Z", "2026-10-28T10:02:00Z"]
    with pytest.raises(SystemExit, match="names no row"):
        MU.quote_times(meta.assign(csv_row=[0, 5]), csv)


def test_the_prices_step_leaves_out_a_price_outside_0_1(tmp_path):
    ids = live_files(tmp_path, n=3, p=[0.4, 1.0, 0.6])
    pd.DataFrame({"tour": "atp", "round": "R16", "p_a": [0.4, 1.0, 0.6],
                  "quoted_at": "2026-10-28T10:00:00Z"}).to_csv(tmp_path / "matchups.csv", index=False)
    res = MU.prices(tmp_path, None, tmp_path / "matchups.csv")
    assert res["priced"] == 2
    assert pd.read_parquet(tmp_path / "prices.parquet")["match_id"].tolist() == [ids[0], ids[2]]
    assert pd.read_parquet(tmp_path / "live_meta.parquet")["csv_row"].tolist() == [0, 2]
    rows = pd.read_parquet(tmp_path / "live_rows.parquet")
    assert rows.loc[rows["live_role"].eq("live"), "_row"].tolist() == [0, 2]
    rec = LO.read(tmp_path)["matches"]
    assert [(r["step"], r["csv_row"], r["match_id"]) for r in rec] == [("prices", 1, ids[1])]
    assert "not strictly between 0 and 1" in rec[0]["reason"]


def test_a_replays_price_outside_0_1_still_stops(tmp_path):
    live_files(tmp_path, n=2)
    frame = tmp_path / "frame.parquet"
    meta = pd.read_parquet(tmp_path / "live_meta.parquet")
    pd.DataFrame({"match_id": meta["match_id"], "p_mkt": [0.5, 1.0], "odds_input": "x"}).to_parquet(frame)
    with pytest.raises(SystemExit, match="every match needs a price"):
        MU.prices(tmp_path, frame)


# --- the tables step ---------------------------------------------------------------------------------------------------
@pytest.fixture()
def tree(tmp_path):
    """A work tree (its marker, Stage 0, the timeline) and a run folder of five live matches."""
    import dp_worktree as WT
    box, run = tmp_path / "tree", tmp_path / "run"
    (box / DC.PD).mkdir(parents=True)
    (box / DC.MT).mkdir(parents=True)
    (box / WT.MARKER).write_text("{}", encoding="utf-8")
    for f in ("stage0_matches.parquet", "stage0_match_players.parquet"):
        pd.DataFrame({"match_id": ["old"]}).to_parquet(box / DC.PD / f)
    pd.DataFrame({"match_id": ["history"]}).to_parquet(box / DC.MT / "timing.parquet")
    ids = live_files(run, n=5)
    return box, run, ids


def stand_in(box, calls, unplaced, after_additions=()):
    """The work tree's scripts: additions appends a timeline row as the real one does (refusing to meet it twice); the
    checks leave out, while one is left in the meta, the first match of `unplaced` (the precheck and the check alike),
    or of `after_additions` (the check after the additions step only: an additions step that changed a live row)."""
    timeline = box / DC.MT / "timing.parquet"

    def run(b, name, script, args, env=None, record=None):
        calls.append((name, list(args)))
        record.append({"step": name, "exit": 0, "seconds": 0.0})
        if name == "additions":
            t = pd.read_parquet(timeline)
            assert "added" not in set(t["match_id"]), "the timeline was not put back before the second Stage 0"
            pd.concat([t, pd.DataFrame({"match_id": ["added"]})]).to_parquet(timeline)
        if name in ("precheck", "check"):
            meta = pd.read_parquet(box / "run" / "live_meta.parquet")
            pool = list(unplaced) + (list(after_additions) if name == "check" else [])
            left = [m for m in pool if m in set(meta["match_id"])][:1]
            done = {"check": {"live_matches": len(meta), **({"left_out": [{"match_id": m, "reason": "a test's reason"}
                                                                          for m in left]} if left else {}),
                              "earlier_rounds": {"not_in_stage0": []}}}
            (box / "run" / "inject.json").write_text(json.dumps(done), encoding="utf-8")
            return TB.LEFT_OUT_EXIT if left else 0
        return 0
    return run


def test_the_tables_step_builds_stage0_again_without_a_match_its_check_cannot_place(tree, monkeypatch):
    box, run, ids = tree
    calls = []
    monkeypatch.setattr(TB.WT, "run", stand_in(box, calls, [ids[1], ids[3]]))
    monkeypatch.setattr(TB, "layer_env", lambda b: {"LLE_LAYER": "layer.json"})
    rec = TB.prep(run, box, False, history=False)
    names = [n for n, _ in calls]
    # the precheck finds each one before the additions step: one Stage 0 build each, the additions merged once
    assert names[:8] == ["stage0", "precheck"] * 3 + ["additions", "check"]
    assert names[8:] == [n for n, _, _ in TB.steps(False, False)][3:]          # then every later step, once
    assert "--leave-out" in dict(calls)["check"] and rec["stage0_rebuilt"] == 2 and "failed" not in rec
    for folder in (run, box / "run"):
        assert pd.read_parquet(folder / "live_meta.parquet")["match_id"].tolist() == [ids[0], ids[2], ids[4]]
        rows = pd.read_parquet(folder / "live_rows.parquet")
        assert rows.loc[rows["live_role"].eq("live"), "_row"].tolist() == [0, 2, 4]
        assert rows["live_role"].tolist().count("played") == 1                 # its earlier rounds stay: history
    assert pd.read_parquet(run / "prices.parquet")["match_id"].tolist() == [ids[0], ids[2], ids[4]]
    left = LO.read(run)["matches"]
    assert [(r["step"], r["csv_row"], r["match_id"], r["reason"]) for r in left] == [
        ("tables", 1, ids[1], "a test's reason"), ("tables", 3, ids[3], "a test's reason")]
    assert pd.read_parquet(box / DC.MT / "timing.parquet")["match_id"].tolist() == ["history", "added"]


def test_a_match_only_the_check_after_the_additions_finds_puts_the_timeline_back(tree, monkeypatch):
    """The additions step changed a live row (a package's completion giving it a box score): the check after it leaves
    the match out, and the timeline the additions step appended to is put back before Stage 0 is built again (the
    stand-in's additions refuses to meet its own row twice)."""
    box, run, ids = tree
    calls = []
    monkeypatch.setattr(TB.WT, "run", stand_in(box, calls, [], after_additions=[ids[2]]))
    monkeypatch.setattr(TB, "layer_env", lambda b: {"LLE_LAYER": "layer.json"})
    rec = TB.prep(run, box, False, history=False)
    names = [n for n, _ in calls]
    assert names[:8] == ["stage0", "precheck", "additions", "check"] * 2 and "failed" not in rec
    assert rec["stage0_rebuilt"] == 1 and [r["match_id"] for r in LO.read(run)["matches"]] == [ids[2]]
    assert pd.read_parquet(box / DC.MT / "timing.parquet")["match_id"].tolist() == ["history", "added"]


def test_a_check_that_keeps_failing_stops_after_its_rebuilds(tree, monkeypatch):
    box, run, ids = tree
    calls = []
    monkeypatch.setattr(TB.WT, "run", stand_in(box, calls, ids[:4]))
    monkeypatch.setattr(TB, "layer_env", lambda b: {"LLE_LAYER": "layer.json"})
    rec = TB.prep(run, box, False, history=False)
    assert rec["failed"] == "precheck" and rec["stage0_rebuilt"] == TB.REBUILDS
    assert [n for n, _ in calls].count("stage0") == TB.REBUILDS + 1


def test_a_replays_check_never_leaves_out():
    replay = TB.steps(False, True)
    assert all("--leave-out" not in a for n, _, a in replay) and "precheck" not in [n for n, _, _ in replay]
    live = TB.steps(False, False, leave_out=True)
    assert [n for n, _, _ in live][:4] == ["stage0", "precheck", "additions", "check"]
    assert [a for n, _, a in live if "--leave-out" in a] == [
        ["--meta", "run/live_meta.parquet", "--step", "check", "--leave-out"]] * 2
