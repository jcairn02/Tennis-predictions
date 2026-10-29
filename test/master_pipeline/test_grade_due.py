"""The bet-day cells run top to bottom (27 Oct 2026; docs/studies/master_pipeline/process_log.md, Part 19): A7 grades
every live run again once the freshest Stage 0 holds more of its results, never before; the engine's grade reads the
Stage 0 it is given; and a day with nothing to predict passes A3 to A5b without an error."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import src.pipeline as tp  # noqa: E402
from src.pipeline import config as CFG  # noqa: E402
from src.pipeline import live as L  # noqa: E402
from src.pipeline import predict as PR  # noqa: E402
from src.pipeline import runner as R  # noqa: E402

needs_selection = pytest.mark.skipif(not CFG.SELECTED_INSTANCE.exists(), reason="no instance selected")


def _run(runs: Path, name: str, ids: list[str], graded: int | None = None) -> Path:
    run = runs / name
    run.mkdir(parents=True)
    pd.DataFrame({"match_id": ids, "q_a": [0.7] * len(ids), "p_market_a": [0.6] * len(ids)}).to_csv(
        run / "predictions.csv", index=False)
    if graded is not None:
        (run / "grade.json").write_text(json.dumps({"predictions": len(ids), "graded": graded}), encoding="utf-8")
    return run


@pytest.fixture()
def world(tmp_path):
    runs = tmp_path / "runs"
    _run(runs, "live_2026-10-20_090000", ["m1", "m2"])                 # both played since: graded now
    _run(runs, "live_2026-10-21_090000", ["m3", "m4"], graded=1)       # m3 graded before, m4 not played: up to date
    _run(runs, "live_2026-10-22_090000", ["m5", "m8"])                 # m5 not played, m8 a walkover: waiting
    _run(runs, "live_2026-10-23_090000", ["m6", "m7"], graded=1)       # one more result since its grade: graded again
    (runs / "live_2026-10-24_090000").mkdir()                           # a stopped run: no predictions, not listed
    s0 = tmp_path / "stage0_matches.parquet"
    pd.DataFrame({"match_id": ["m1", "m2", "m3", "m6", "m7", "m8", "x"],
                  "status": ["completed", "retired", "completed", "completed", "completed", "walkover", "completed"],
                  "a_won": [1, 0, 1, 1, 0, None, 1]}).to_parquet(s0)
    return runs, s0


def test_grade_due_grades_only_the_runs_with_new_results(world, monkeypatch, capsys):
    runs, s0 = world
    calls = []

    def engine(run, *, stage0=None, dry_run=False):              # what dp.py grade writes, by its own rule
        calls.append((Path(run).name, Path(stage0)))
        ids = pd.read_csv(Path(run) / "predictions.csv")["match_id"].astype(str)
        status = pd.read_parquet(stage0).set_index("match_id")["status"]
        n = int(ids.map(status).isin(["completed", "retired"]).sum())
        (Path(run) / "grade.json").write_text(json.dumps({"graded": n, "mean_ll_model": 0.5, "mean_ll_market": 0.6}),
                                              encoding="utf-8")
    monkeypatch.setattr(PR, "grade", engine)
    out = tp.grade_due(stage0=s0, runs=runs).set_index("run")
    assert calls == [("live_2026-10-20_090000", s0), ("live_2026-10-23_090000", s0)]
    assert out["state"].to_dict() == {"live_2026-10-20_090000": "graded now", "live_2026-10-21_090000": "up to date",
                                      "live_2026-10-22_090000": "waiting for results",
                                      "live_2026-10-23_090000": "graded now"}
    assert out.loc["live_2026-10-23_090000", ["results", "graded_before"]].tolist() == [2, 1]
    assert out.loc["live_2026-10-20_090000", "mean_ll_model"] == 0.5
    text = capsys.readouterr().out
    assert "2 run(s) graded now, 3 new result(s)" in text and "1 up to date, 1 waiting" in text
    assert "Tue 20 Oct 09:00" in text and "lower is better" in text
    again = tp.grade_due(stage0=s0, runs=runs)                    # nothing new since: nothing graded, one line
    assert len(calls) == 2 and set(again["state"]) == {"up to date", "waiting for results"}
    assert "Nothing new to grade" in capsys.readouterr().out


def test_the_run_just_made_is_never_graded(world, monkeypatch, capsys):
    """The run A4 made a minute ago: none of its matches has a result, so A7 leaves it alone (A7 as written before
    27 Oct, tp.grade(RUN), would have graded it on nothing)."""
    runs, s0 = world
    _run(runs, "live_2026-10-27_081500", ["new1", "new2"])
    monkeypatch.setattr(PR, "grade", lambda run, **k: pytest.fail(f"graded {Path(run).name}")
                        if Path(run).name.endswith("081500") else None)
    out = tp.grade_due(stage0=s0, runs=runs).set_index("run")
    assert out.loc["live_2026-10-27_081500", "state"] == "waiting for results"


@needs_selection
def test_the_engine_grades_from_the_stage0_it_is_given(world, monkeypatch, tmp_path):
    """dp.py grade --stage0, through tp.grade as A7 calls it: the counts, the log losses and the file named."""
    runs, s0 = world
    monkeypatch.setattr(CFG, "OUT", tmp_path / "out")             # the step's log and receipt
    monkeypatch.setattr(CFG, "LOGS", tmp_path / "out" / "logs")
    monkeypatch.setattr(CFG, "RECEIPTS", tmp_path / "out" / "runs.jsonl")
    monkeypatch.setattr(R, "RUNNING", tmp_path / "out" / "running")
    run = runs / "live_2026-10-20_090000"
    tp.grade(run, stage0=s0)
    g = json.loads((run / "grade.json").read_text(encoding="utf-8"))
    assert (g["predictions"], g["graded"], Path(g["stage0"])) == (2, 2, s0)
    assert g["mean_ll_model"] == pytest.approx((-math.log(0.7) - math.log(0.3)) / 2)     # m1 won, m2 lost (retired)
    assert g["mean_ll_market"] == pytest.approx((-math.log(0.6) - math.log(0.4)) / 2)
    assert pd.read_csv(run / "graded.csv")["status"].tolist() == ["completed", "retired"]


def test_a_day_with_nothing_to_predict_passes_the_cells(tmp_path, capsys):
    """A3 to A5b with nothing predictable: no error, no file, each later cell skips, and A4 skips before any check or
    paid call."""
    matches = pd.DataFrame({"status": ["left out", "left out"], "player_a": ["A", "C"], "player_b": ["B", "D"],
                            "reason": ["Challenger", "doubles"]})
    csv = tmp_path / "matchups.csv"
    assert L.build_matchups(matches, path=csv) is None and not csv.exists()
    assert "Nothing to predict now: none of the 2 listed matches" in capsys.readouterr().out
    assert L.check_matchups(None) is None                                # A3 then shows nothing, not an empty table
    assert tp.data_check(None) is None
    assert tp.predict_day(None, model="tabpfn35_thinking") is None       # without spend_tokens: no refusal either
    text = capsys.readouterr().out
    assert "Nothing to check (A3 wrote no matchups)" in text and "Nothing to predict (A3 wrote no matchups)" in text


def test_the_results_source_is_said_plainly(tmp_path, monkeypatch):
    runs = tmp_path / "runs"
    monkeypatch.setattr(CFG, "OUT", tmp_path / "out")
    monkeypatch.setattr(CFG, "STAGE0", tmp_path / "shared")
    own = runs / "live_2026-10-25_092143" / "stage0" / "stage0_matches.parquet"
    check = tmp_path / "out" / "data_check" / "stage0" / "stage0_matches.parquet"
    shared = tmp_path / "shared" / "stage0_matches.parquet"
    for p in (own, check, shared):
        p.parent.mkdir(parents=True)
        p.write_bytes(b"x")
    assert PR._results_source(own, runs) == "results as the prediction run of Sun 25 Oct 09:21 downloaded them"
    assert PR._results_source(check, runs).startswith("results as the data check (A3b) read them at ")
    assert PR._results_source(shared, runs).startswith("results from the shared tables, rebuilt ")
