"""Women's matches switched off for the bet day (the owner, 28 Oct 2026; docs/decisions/2026-10-28-women-switched-off.md;
master pipeline process log, Part 24): config.BET_TOURS, read by A2 (the linker), A3 (the matchups check), A5 (the
sheet), A5b (the reprice), A7 (the grades shown), A8 (the closing-line reading) and STATUS. Each test sets the switch
itself, so the tests hold whichever way it is set."""
from __future__ import annotations

import datetime as dt
import json
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.pipeline as tp  # noqa: E402
from src.pipeline import closing_line as CL  # noqa: E402
from src.pipeline import config as CFG  # noqa: E402
from src.pipeline import diagnostics as D  # noqa: E402
from src.pipeline import live as L  # noqa: E402
from src.pipeline import overview as O  # noqa: E402
from src.pipeline import predict as PR  # noqa: E402

MEN, BOTH = ("atp",), ("atp", "wta")
NOW = pd.Timestamp("2026-10-28T12:00:00Z")
REPLAY = ROOT / "data" / "studies" / "daily_prediction" / "runs" / "replay_2026-07-13_R16_speed"
needs_replay = pytest.mark.skipif(not (REPLAY / "predictions.csv").exists(), reason="no replay run")


@pytest.fixture()
def women_off(monkeypatch):
    monkeypatch.setattr(CFG, "BET_TOURS", MEN)


@pytest.fixture()
def women_on(monkeypatch):
    monkeypatch.setattr(CFG, "BET_TOURS", BOTH)


def test_the_switch(monkeypatch):
    monkeypatch.setattr(CFG, "BET_TOURS", MEN)
    assert CFG.tour_off("wta").startswith("women's matches are switched off")
    assert CFG.tour_off("atp") is None and CFG.tour_off("itf") is None        # ITF keeps its own reason
    assert CFG.off_names() == "women's" and "women's switched off" in CFG.bet_tours_line()
    assert CFG.off_mask(pd.DataFrame({"tour": ["atp", "wta", "itf"]})).tolist() == [False, True, False]
    ids = pd.DataFrame({"match_id": ["atp|2026-1|R16|atp:1|atp:2", "wta|2026-2|R16|wta:3|wta:4", "m1"]})
    assert CFG.off_mask(ids).tolist() == [False, True, False]                 # by the match id without a tour column
    assert not CFG.off_mask(pd.DataFrame({"x": [1, 2]})).any()
    monkeypatch.setattr(CFG, "BET_TOURS", BOTH)
    assert CFG.tour_off("wta") is None and CFG.off_names() == ""
    assert not CFG.off_mask(ids).any() and CFG.bet_tours_line() == "men's and women's matches"


# --- A2 and A3 ------------------------------------------------------------------------------------------------------
def _pull(leagues: list[str]) -> pd.DataFrame:
    """A staged Pinnacle pull: one pre-match moneyline per league name, two hours ahead."""
    from src.ingest import pinnacle as P
    t = (NOW + pd.Timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    matchups = [{"id": i, "parentId": None, "isLive": False, "status": "pending", "startTime": t,
                 "league": {"name": name, "id": i, "bestOfX": 3},
                 "participants": [{"alignment": "home", "name": f"Home Player{i}"},
                                  {"alignment": "away", "name": f"Away Player{i}"}]}
                for i, name in enumerate(leagues, start=1)]
    straight = [{"type": "moneyline", "period": 0, "matchupId": i, "status": "open", "isAlternate": False,
                 "cutoffAt": t, "prices": [{"designation": "home", "price": -150}, {"designation": "away", "price": 130}],
                 "limits": [{"type": "maxRiskStake", "amount": 500}], "version": 1}
                for i in range(1, len(leagues) + 1)]
    return P.stage_pull({"retrieved_at": NOW.isoformat(), "matchups": matchups, "straight": straight})


class _NoTennisLive:
    """TennisLive must not be asked."""
    stopped = None

    def event(self, *a):
        raise AssertionError("TennisLive asked")

    results = page = event


def test_a2_leaves_womens_listings_out_before_any_linking(women_off, monkeypatch, capsys):
    pull = _pull(["ATP Challenger Testville - R16", "WTA Testcity - R16", "WTA Testcity - Doubles",
                  "WTA 125k Testtown - R16"])
    read = []
    monkeypatch.setattr(L, "_tml", lambda years: pd.DataFrame())               # any linking would fail on it
    monkeypatch.setattr(L, "_stage0_keys", lambda tour: read.append(tour) or pd.DataFrame())
    m = L.todays_matches(pull=pull, hours_ahead=36, now=NOW.to_pydatetime(), tennislive=_NoTennisLive())
    reason = dict(zip(m["league"], m["reason"]))
    assert read == ["atp"]                                                       # no women's Stage 0 names read
    assert reason["ATP Challenger Testville - R16"].startswith("challenger level")
    assert {r for k, r in reason.items() if k.startswith("WTA")} == {CFG.tour_off("wta")}
    shown = L.show(m)
    assert shown["reason"].tolist() == [reason["ATP Challenger Testville - R16"]]
    assert "3 women's listings left out, not shown" in capsys.readouterr().out
    assert len(m) == 4                                                           # the frame (and _linking file) keeps them


def test_a2_links_womens_listings_again_when_switched_on(women_on, monkeypatch):
    pull = _pull(["WTA 125k Testtown - R16", "WTA Testcity - Doubles"])
    read = []
    monkeypatch.setattr(L, "_tml", lambda years: pd.DataFrame())
    monkeypatch.setattr(L, "_stage0_keys", lambda tour: read.append(tour) or pd.DataFrame())
    m = L.todays_matches(pull=pull, hours_ahead=36, now=NOW.to_pydatetime())
    assert read == ["atp", "wta"]
    assert sorted(m["reason"].str[:9]) == ["125 level", "doubles"]              # their own reasons, as before


def test_a2_tours_asked_for_by_name_are_linked(women_off, monkeypatch):
    """The tests of the linker's women's code pass tours=("atp", "wta"): it links them while the switch is off."""
    read = []
    monkeypatch.setattr(L, "_tml", lambda years: pd.DataFrame())
    monkeypatch.setattr(L, "_stage0_keys", lambda tour: read.append(tour) or pd.DataFrame())
    m = L.todays_matches(pull=_pull(["WTA 125k Testtown - R16"]), hours_ahead=36, now=NOW.to_pydatetime(), tours=BOTH)
    assert read == ["atp", "wta"] and m["reason"].iloc[0].startswith("125 level")


def test_a3_leaves_out_a_womens_row_typed_by_hand(women_off, monkeypatch, tmp_path, capsys):
    """Since Part 25 (28 Oct 2026) the check flags the row, loudly, and A4 leaves it out: nothing raises."""
    csv = tmp_path / "matchups.csv"
    pd.DataFrame([{"tour": "wta", "tourney_id": "2026-1023", "round": "R16", "player_a": "Ann Alpha",
                   "player_b": "Bea Beta", "day": "2026-10-29", "p_a": 0.55}]).to_csv(csv, index=False)
    monkeypatch.setattr(L, "_tml", lambda years: pd.DataFrame())
    monkeypatch.setattr(L, "_stage0_keys", lambda tour: pytest.fail(f"Stage 0 read for {tour}"))
    res = L.check_matchups(csv)
    assert not res["ok"].iloc[0] and res["switched_off"].iloc[0]
    assert res["problem"].iloc[0].startswith("women's matches are switched off")
    out = capsys.readouterr().out
    assert "!!! 1 OF 1 MATCHES WILL BE LEFT OUT OF THE RUN" in out and "women's matches are switched off" in out


def test_a3_says_how_many_listings_the_switch_left_out(women_off, capsys):
    matches = pd.DataFrame({"status": ["left out", "left out"], "tour": ["atp", "wta"], "player_a": ["A", "C"],
                            "player_b": ["B", "D"], "reason": ["Challenger", CFG.tour_off("wta")]})
    assert L.build_matchups(matches) is None
    assert "1 of them women's, switched off" in capsys.readouterr().out


# --- A5 and A5b -------------------------------------------------------------------------------------------------------
def _live_copy(tmp_path) -> Path:
    """The replay (15 men's and 8 women's matches) as a live run made before the switch, with A3's linking file: one
    men's and one women's main-tour listing left out."""
    run = tmp_path / "live_2026-07-15_055500"
    run.mkdir()
    for f in ("predictions.csv", "curves.parquet", "live_frame.parquet", "gate.csv"):
        shutil.copy2(REPLAY / f, run / f)
    shutil.copytree(REPLAY / "fit", run / "fit")
    pd.DataFrame([{"status": "left out", "reason": "no event yet", "league": "ATP Testville - R16", "tour": "atp",
                   "day": "2026-07-15", "home": "Ann Men", "away": "Bob Men", "price_home": -150, "price_away": 130},
                  {"status": "left out", "reason": "no event yet", "league": "WTA Testcity - R16", "tour": "wta",
                   "day": "2026-07-15", "home": "Cat Women", "away": "Dee Women", "price_home": -150,
                   "price_away": 130}]).to_csv(run / "matchups_linking.csv", index=False)
    return run


SHEET_NOW = dt.datetime(2026, 7, 15, 6, 0, tzinfo=dt.timezone.utc)


@needs_replay
def test_a5_leaves_a_runs_womens_matches_off_the_sheet_and_says_so(women_off, monkeypatch, tmp_path):
    run = _live_copy(tmp_path)
    monkeypatch.setattr(CFG, "PREDICTIONS", tmp_path / "predictions")
    rec = D.bet_diagnostics(run, write=True, show=False, now=SHEET_NOW)
    pred = rec[rec["status"].eq("predicted")]
    assert len(pred) == 15 and set(pred["tour"]) == {"atp"}
    assert rec.loc[rec["status"].eq("not predicted"), "player_a"].tolist() == ["Ann Men"]
    prov = json.loads(next((tmp_path / "predictions").rglob("*.provenance.json")).read_text(encoding="utf-8"))
    assert any("this run's 8 women's predictions and the 1 women's listings it did not predict are not on this "
               "sheet" in n["plain"] for n in prov["run_notes"])
    assert len(pd.read_csv(run / "predictions.csv")) == 23                       # the run's own files keep them


@needs_replay
def test_a5_keeps_both_tours_when_switched_on_and_on_a_replay(monkeypatch, tmp_path):
    monkeypatch.setattr(CFG, "BET_TOURS", BOTH)
    rec = D.bet_diagnostics(_live_copy(tmp_path), write=False, show=False, now=SHEET_NOW)
    assert rec["status"].value_counts().to_dict() == {"predicted": 23, "not predicted": 2}
    monkeypatch.setattr(CFG, "BET_TOURS", MEN)                                    # a replay (C8) keeps both tours
    rec = D.bet_diagnostics(REPLAY, write=False, show=False, now=SHEET_NOW)
    assert rec["status"].eq("predicted").sum() == 23


def test_a5b_reprices_only_the_mens_matches_of_a_run_made_before_the_switch(women_off, monkeypatch, tmp_path, capsys):
    run = tmp_path / "live_2026-10-28_153009"
    run.mkdir()
    pd.DataFrame([{"match_id": "atp|x|R16|atp:1|atp:2", "tour": "atp", "player_a": "Home Player1",
                   "player_b": "Away Player1", "player_a_id": "atp:1", "player_b_id": "atp:2"},
                  {"match_id": "wta|x|R16|wta:3|wta:4", "tour": "wta", "player_a": "Home Player2",
                   "player_b": "Away Player2", "player_a_id": "wta:3", "player_b_id": "wta:4"}]
                 ).to_csv(run / "predictions.csv", index=False)
    pull = _pull(["ATP Testville - R16", "WTA Testcity - R16"])
    monkeypatch.setattr(L, "latest_pull", lambda: pull)
    out = pd.read_csv(L.live_prices(run, pull_now=False, path=tmp_path / "prices.csv"))
    assert out["match_id"].tolist() == ["atp|x|R16|atp:1|atp:2"]
    assert "1 of the run's 2 matches are women's" in capsys.readouterr().out


# --- A7 ----------------------------------------------------------------------------------------------------------------
@pytest.fixture()
def graded_world(tmp_path):
    """A run graded before the switch (a man and a woman, both played), a run with a man and a woman (only the woman
    played since), and a women's run; the engine's stand-in writes grade.json and graded.csv by its own rule."""
    runs = tmp_path / "runs"
    for name, ids in (("live_2026-10-27_090000", ["atp|a|R16|atp:1|atp:2", "wta|b|R16|wta:1|wta:2"]),
                      ("live_2026-10-28_090000", ["atp|c|R16|atp:3|atp:4", "wta|d|R16|wta:3|wta:4"]),
                      ("live_2026-10-28_100000", ["wta|e|R16|wta:5|wta:6"])):
        (runs / name).mkdir(parents=True)
        pd.DataFrame({"match_id": ids, "tour": [i[:3] for i in ids], "q_a": 0.7, "p_market_a": 0.6}).to_csv(
            runs / name / "predictions.csv", index=False)
    first = runs / "live_2026-10-27_090000"
    pd.DataFrame({"match_id": ["atp|a|R16|atp:1|atp:2", "wta|b|R16|wta:1|wta:2"], "tour": ["atp", "wta"],
                  "status": "completed", "ll_model": [0.5, 0.9], "ll_market": [0.6, 0.7]}).to_csv(
        first / "graded.csv", index=False)
    (first / "grade.json").write_text(json.dumps({"graded": 2, "mean_ll_model": 0.7, "mean_ll_market": 0.65}),
                                      encoding="utf-8")
    s0 = tmp_path / "stage0_matches.parquet"
    pd.DataFrame({"match_id": ["atp|a|R16|atp:1|atp:2", "wta|b|R16|wta:1|wta:2", "wta|d|R16|wta:3|wta:4",
                               "wta|e|R16|wta:5|wta:6"], "status": "completed"}).to_parquet(s0)
    return runs, s0


def _engine(calls: list):
    def grade(run, *, stage0=None, dry_run=False):
        calls.append(Path(run).name)
        p = pd.read_csv(Path(run) / "predictions.csv")
        done = p["match_id"].isin(pd.read_parquet(stage0)["match_id"])
        p.loc[done, "ll_model"], p.loc[done, "ll_market"] = 0.4, 0.5
        p.to_csv(Path(run) / "graded.csv", index=False)
        (Path(run) / "grade.json").write_text(json.dumps({"graded": int(done.sum()), "mean_ll_model": 0.4,
                                                          "mean_ll_market": 0.5}), encoding="utf-8")
    return grade


def test_a7_reads_the_mens_matches_and_grades_a_run_only_for_a_mens_result(women_off, graded_world, monkeypatch,
                                                                           capsys):
    runs, s0 = graded_world
    calls = []
    monkeypatch.setattr(PR, "grade", _engine(calls))
    out = tp.grade_due(stage0=s0, runs=runs).set_index("run")
    assert calls == []                                       # a woman's result alone grades nothing
    assert list(out.index) == ["live_2026-10-27_090000", "live_2026-10-28_090000"]       # the women's run not listed
    first = out.loc["live_2026-10-27_090000"]
    assert (first["state"], first["predicted"], first["results"], first["graded_before"]) == ("up to date", 1, 1, 1)
    assert first["mean_ll_model"] == 0.5 and first["switched_off"] == 1                 # the man's figures alone
    assert out.loc["live_2026-10-28_090000", "state"] == "waiting for results"
    assert "Nothing new to grade" in capsys.readouterr().out


def test_a7_grades_every_tour_when_switched_on(women_on, graded_world, monkeypatch, capsys):
    runs, s0 = graded_world
    calls = []
    monkeypatch.setattr(PR, "grade", _engine(calls))
    out = tp.grade_due(stage0=s0, runs=runs).set_index("run")
    assert calls == ["live_2026-10-28_090000", "live_2026-10-28_100000"]
    assert out.loc["live_2026-10-27_090000", ["state", "graded_before", "mean_ll_model"]].tolist() == [
        "up to date", 2, 0.7]                                # grade.json, every tour, as before the switch
    assert set(out["switched_off"]) == {0} and "Left out of these figures" not in capsys.readouterr().out


def test_a7_says_what_it_leaves_out_of_a_run_graded_now(women_off, graded_world, monkeypatch, capsys):
    runs, s0 = graded_world
    s = pd.read_parquet(s0)
    pd.concat([s, pd.DataFrame({"match_id": ["atp|c|R16|atp:3|atp:4"], "status": ["completed"]})]).to_parquet(s0)
    calls = []
    monkeypatch.setattr(PR, "grade", _engine(calls))
    out = tp.grade_due(stage0=s0, runs=runs).set_index("run")
    assert calls == ["live_2026-10-28_090000"]               # the man's result: the run graded in full (the record)
    assert len(pd.read_csv(runs / "live_2026-10-28_090000" / "graded.csv")) == 2
    assert out.loc["live_2026-10-28_090000", ["state", "results", "mean_ll_model"]].tolist() == ["graded now", 1, 0.4]
    assert "Left out of these figures: 1 women's predictions of these runs" in capsys.readouterr().out


# --- A8 and STATUS --------------------------------------------------------------------------------------------------
def _ledger() -> pd.DataFrame:
    rows = []
    for mid, tour, a, decision in (("atp|a|R16|atp:1|atp:2", "atp", "Alpha Men", "BET"),
                                   ("atp|b|R16|atp:3|atp:4", "atp", "Beta Men", "PASS"),
                                   ("wta|c|R16|wta:1|wta:2", "wta", "Gamma Women", "BET")):
        rows.append({"sheet_file": "predictions/2026-10-28/records/bet_sheet_2026-10-28_1553.csv",
                     "made_at": pd.Timestamp("2026-10-28T22:53:00Z"), "match_id": mid, "tour": tour,
                     "tournament": "Test", "round": "R16", "player_a": a, "player_b": "Other", "pick": "A",
                     "pick_player": a if decision == "BET" else None, "decision": decision, "close_kind": "pending",
                     "start_final": pd.Timestamp("2026-10-29T10:00:00Z"), "last_before_start": True,
                     "first_sheet": True, "made_after_start": False})
    return pd.DataFrame(rows).reindex(columns=CL.COLUMNS)


def test_a8_reads_the_mens_matches_and_the_ledger_keeps_every_one(women_off, monkeypatch, tmp_path, capsys):
    led = _ledger()
    monkeypatch.setattr(CL, "build", lambda now=None: (led, {"sheets": 1}))
    monkeypatch.setattr(CL, "OUT", tmp_path / "clv")
    out = CL.clv_ledger()
    assert len(out) == 3 and len(pd.read_csv(tmp_path / "clv" / "ledger.csv")) == 3
    summary = json.loads((tmp_path / "clv" / "summary.json").read_text(encoding="utf-8"))
    assert summary["switched_off"] == {"bet_tours": ["atp"], "predictions": 1, "matches": 1}
    assert summary["lines"][0].startswith("Women's matches are switched off") and "made 2 predictions" in summary["lines"][1]
    text = capsys.readouterr().out
    assert "Alpha Men" in text and "Gamma Women" not in text


def test_a8_reads_every_tour_when_switched_on(women_on, monkeypatch, tmp_path):
    monkeypatch.setattr(CL, "build", lambda now=None: (_ledger(), {"sheets": 1}))
    monkeypatch.setattr(CL, "OUT", tmp_path / "clv")
    CL.clv_ledger(show=False)
    summary = json.loads((tmp_path / "clv" / "summary.json").read_text(encoding="utf-8"))
    assert "switched_off" not in summary and "made 3 predictions" in summary["lines"][0]


def test_status_names_the_switch(women_off, monkeypatch, capsys):
    out = {"downloads": "x", "sources": {}, "model": "x", "live_model": "template_test", "paused": {},
           "prediction_runs": [], "running": [], "env_not_inherited": [], "disk": "x",
           "bet_tours": CFG.bet_tours_line()}
    O._print(out)
    assert "BET DAY (A1-A8): men's matches; women's switched off since 28 Oct 2026" in capsys.readouterr().out
