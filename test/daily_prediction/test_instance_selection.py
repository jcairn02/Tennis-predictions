"""Which instance the daily pipeline predicts with (22 Oct 2026; docs/studies/master_pipeline/process_log.md, Part 9).

One place names the live model: the master notebook's selection (data/studies/master_pipeline/selected_instance.json),
written by use_instance() and by a retrain's switch. DP_INSTANCE with DP_BASE_TREE names another instance explicitly
(a retrain's or a candidate's checkpoints and replays). With neither, every dp.py command refuses. Before 22 Oct 2026
dp_common fell back to the 10 Oct instance and its build tree, so a run started without the notebook predicted with a
model two retrains old, and nothing flagged it.

Fast: a fake repository in tmp_path (DP_REPO), no data, no GPU. The real selection is never read or written.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "src" / "eda" / "daily_prediction"
OLD_DEFAULT = "template_2026-10-10"


def _repo(tmp_path: Path, selection: dict | str | None, instances=(OLD_DEFAULT,)) -> Path:
    """A fake repository: instance folders holding an (empty) model frame, and the selection as given (a dict, raw
    text, or None for no selection file)."""
    repo = tmp_path / "repo"
    for name in instances:
        inst = repo / "data" / "studies" / "current_best_model" / name
        inst.mkdir(parents=True, exist_ok=True)
        (inst / "model_frame.parquet").write_bytes(b"")        # init checks only that the frame exists
    sel = repo / "data" / "studies" / "master_pipeline" / "selected_instance.json"
    sel.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(selection, dict):
        sel.write_text(json.dumps(selection), encoding="utf-8")
    elif isinstance(selection, str):
        sel.write_text(selection, encoding="utf-8")
    return repo


def _env(repo: Path, **extra) -> dict:
    # the package's conftest sets DP_* from the real selection: none of them reaches these processes
    env = {k: v for k, v in os.environ.items() if not k.startswith("DP_")}
    env.update({"DP_REPO": str(repo), "PYTHONIOENCODING": "utf-8", **extra})
    return env


def _resolved(repo: Path, **extra) -> dict:
    """What dp_common resolves, read in a fresh process (it resolves at import)."""
    code = ("import json, sys; sys.path.insert(0, sys.argv[1]); import dp_common as DC; "
            "print(json.dumps({'id': DC.INSTANCE_ID, 'tree': str(DC.BASE_TREE), "
            "'ok': getattr(DC, 'INSTANCE_OK', None), 'source': getattr(DC, 'INSTANCE_SOURCE', None)}))")
    done = subprocess.run([sys.executable, "-c", code, str(PKG)], capture_output=True, text=True, encoding="utf-8",
                          env=_env(repo, **extra), cwd=repo, timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout.strip().splitlines()[-1])


def _init(repo: Path, run: Path, **extra) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(PKG / "dp.py"), "init", "--run", str(run), "--replay-week", "2026-07-13"],
                          capture_output=True, text=True, encoding="utf-8", env=_env(repo, **extra), cwd=repo,
                          timeout=300)


def test_no_selection_refuses_instead_of_the_10_oct_default(tmp_path):
    """The bug of 22 Oct 2026: with no selection and no DP_INSTANCE, a run started on the 10 Oct instance."""
    repo = _repo(tmp_path, selection=None)
    run = tmp_path / "run"
    done = _init(repo, run)
    assert done.returncode != 0, done.stdout
    assert "no instance is selected" in done.stderr
    assert not (run / "run.json").exists()
    assert _resolved(repo)["id"] != OLD_DEFAULT


def test_the_selection_names_the_instance_and_its_tree(tmp_path):
    repo = _repo(tmp_path, {"instance": "template_x", "tree": str(tmp_path / "tnr_x")}, instances=("template_x",))
    r = _resolved(repo)
    assert r["id"] == "template_x" and Path(r["tree"]) == tmp_path / "tnr_x" and r["ok"] is True
    assert "selection" in r["source"]
    run = tmp_path / "run"
    done = _init(repo, run)
    assert done.returncode == 0, done.stderr
    assert "template_x" in done.stderr                         # the run says which instance, and from where
    cfg = json.loads((run / "run.json").read_text(encoding="utf-8"))
    assert Path(cfg["instance"]).name == "template_x" and Path(cfg["base_tree"]) == tmp_path / "tnr_x"
    assert "selection" in cfg["instance_source"]


def test_dp_instance_with_its_tree_names_another_instance(tmp_path):
    """A retrain's or a candidate's checkpoints and replays; the source says the selection names another."""
    repo = _repo(tmp_path, {"instance": "template_x", "tree": "C:/tnr_x"}, instances=("template_x", "template_y"))
    r = _resolved(repo, DP_INSTANCE="template_y", DP_BASE_TREE=str(tmp_path / "tnr_y"))
    assert r["id"] == "template_y" and Path(r["tree"]) == tmp_path / "tnr_y" and r["ok"] is True
    assert "DP_INSTANCE" in r["source"] and "template_x" in r["source"]


def test_dp_instance_of_the_selection_takes_its_tree(tmp_path):
    repo = _repo(tmp_path, {"instance": "template_x", "tree": str(tmp_path / "tnr_x")}, instances=("template_x",))
    r = _resolved(repo, DP_INSTANCE="template_x")
    assert r["id"] == "template_x" and Path(r["tree"]) == tmp_path / "tnr_x" and r["ok"] is True


def test_another_instance_without_its_tree_refuses(tmp_path):
    """DP_INSTANCE alone would pair another instance with the selection's build tree: refused."""
    repo = _repo(tmp_path, {"instance": "template_x", "tree": "C:/tnr_x"}, instances=("template_x", "template_y"))
    assert _resolved(repo, DP_INSTANCE="template_y")["ok"] is False
    done = _init(repo, tmp_path / "run", DP_INSTANCE="template_y")
    assert done.returncode != 0 and "DP_BASE_TREE" in done.stderr
    assert not (tmp_path / "run" / "run.json").exists()


def test_a_tree_alone_must_be_the_selections(tmp_path):
    repo = _repo(tmp_path, {"instance": "template_x", "tree": str(tmp_path / "tnr_x")}, instances=("template_x",))
    assert _resolved(repo, DP_BASE_TREE=str(tmp_path / "tnr_other"))["ok"] is False
    assert _resolved(repo, DP_BASE_TREE=str(tmp_path / "tnr_x"))["ok"] is True


def test_an_unreadable_selection_refuses(tmp_path):
    repo = _repo(tmp_path, '{"instance": "template_x", "tr', instances=("template_x",))      # cut short
    r = _resolved(repo)
    assert r["ok"] is False and "cannot be read" in r["source"]


def test_the_resolved_instance_is_handed_to_the_steps_it_starts(tmp_path):
    """require_instance pins DP_INSTANCE and DP_BASE_TREE, so a step started later in the run reads the same instance
    even if the selection changes meanwhile (a retrain switching it)."""
    repo = _repo(tmp_path, {"instance": "template_x", "tree": str(tmp_path / "tnr_x")}, instances=("template_x",))
    code = ("import os, sys; sys.path.insert(0, sys.argv[1]); import dp_common as DC; DC.require_instance(); "
            "print(os.environ['DP_INSTANCE']); print(os.environ['DP_BASE_TREE'])")
    done = subprocess.run([sys.executable, "-c", code, str(PKG)], capture_output=True, text=True, encoding="utf-8",
                          env=_env(repo), cwd=repo, timeout=120)
    assert done.returncode == 0, done.stderr
    inst, tree = done.stdout.strip().splitlines()[-2:]
    assert inst == "template_x" and Path(tree) == tmp_path / "tnr_x"
