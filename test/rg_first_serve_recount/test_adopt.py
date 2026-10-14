"""The adoption swap: the check, the apply with kept copies, and the restore (src/eda/rg_first_serve_recount/adopt.py)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.eda.rg_first_serve_recount import adopt as AD  # noqa: E402

DECIDED = pd.DataFrame({"tour": ["atp", "wta"], "tid": ["520", "520"], "w_svpt": ["80", "60"]})


def write(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def test_compare_accepts_a_superset_with_a_blank_or_tml_source():
    cand = pd.concat([DECIDED.assign(source=["", "tml"]),
                      pd.DataFrame({"tour": ["atp"], "tid": ["520"], "w_svpt": ["91"], "source": ["sackmann"]})],
                     ignore_index=True)
    res = AD.compare(DECIDED, cand)
    assert res["ok"] and res["rows_added"] == 1 and res["columns_added"] == ["source"]


@pytest.mark.parametrize("cand, reason", [
    (DECIDED.iloc[:1], "not in the candidate"),                                  # a decided row dropped
    (DECIDED.assign(w_svpt=["80", "61"]), "not in the candidate"),               # a decided row changed
    (DECIDED.drop(columns="w_svpt"), "lacks the decided columns"),               # a decided column dropped
    (DECIDED.assign(source=["sackmann", ""]), "carry the source"),               # a decided row re-pointed
])
def test_compare_refuses_anything_but_added_rows(cand, reason):
    res = AD.compare(DECIDED, cand)
    assert not res["ok"] and reason in res["reason"]


def test_apply_keeps_copies_and_restore_puts_them_back(tmp_path, monkeypatch):
    monkeypatch.setattr(AD, "ROOT", tmp_path)
    decided = write(DECIDED, tmp_path / "live" / "overrides.csv")
    cand = write(pd.concat([DECIDED, DECIDED.iloc[:1].assign(w_svpt="99")], ignore_index=True),
                 tmp_path / "cand" / "overrides.csv")
    same_live = write(DECIDED, tmp_path / "live" / "aliases.csv")
    same_cand = write(DECIDED, tmp_path / "cand" / "aliases.csv")
    before = AD.sha(decided)
    folder = AD.apply({decided: cand, same_live: same_cand}, out_dir=tmp_path / "adoption")
    assert AD.sha(decided) == AD.sha(cand)
    assert (folder / "replaced" / "live" / "overrides.csv").exists()
    assert not (folder / "replaced" / "live" / "aliases.csv").exists()        # identical tables are not kept
    AD.restore(folder.name, out_dir=tmp_path / "adoption", root=tmp_path)
    assert AD.sha(decided) == before


def test_apply_refuses_when_a_decided_row_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(AD, "ROOT", tmp_path)
    decided = write(DECIDED, tmp_path / "live" / "overrides.csv")
    cand = write(DECIDED.iloc[:1], tmp_path / "cand" / "overrides.csv")
    with pytest.raises(SystemExit, match="not applied"):
        AD.apply({decided: cand}, out_dir=tmp_path / "adoption")
    assert AD.sha(decided) != AD.sha(cand)
