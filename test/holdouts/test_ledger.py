"""The holdout register and the look ledger (src/eda/holdouts/ledger.py). Temporary files only, except one read-only
check of the repository's register."""
import csv
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.holdouts import ledger as L  # noqa: E402

NOW = datetime(2026, 10, 29, 9, 30, tzinfo=timezone(timedelta(hours=-7)))


def register_file(tmp_path: Path) -> Path:
    path = tmp_path / "register.csv"
    rows = [
        {"id": "H1", "name": "the model's edge", "protects": "the model.", "tours": "both", "levels": "tour",
         "first_day": "2026-10-19", "last_day": "", "status": "open"},
        {"id": "H2", "name": "a men's lead", "protects": "a statistic.", "tours": "atp", "levels": "tour",
         "first_day": "2026-07-29", "last_day": "", "status": "open"},
        {"id": "H3", "name": "an ITF model", "protects": "the ITF model.", "tours": "both", "levels": "lower",
         "first_day": "2026-11-01", "last_day": "2027-01-31", "status": "open"},
        {"id": "H4", "name": "an old period", "protects": "nothing now.", "tours": "both", "levels": "all",
         "first_day": "2025-01-01", "last_day": "", "status": "released"},
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=L.REGISTER_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in L.REGISTER_COLUMNS})
    return path


def ids(rows):
    return [r["id"] for r in rows]


def test_touched_by_days_tours_and_levels(tmp_path):
    reg = register_file(tmp_path)
    assert ids(L.touched("2026-01-01", "2026-10-18", "both", "all", reg)) == ["H2"]       # the day before H1
    assert ids(L.touched("2026-01-01", "2026-10-19", "both", "all", reg)) == ["H1", "H2"]
    assert ids(L.touched("2026-10-19", "2026-10-28", "wta", "tour", reg)) == ["H1"]       # H2 is men's
    assert ids(L.touched("2026-10-19", "2026-12-01", "atp", "lower", reg)) == ["H3"]      # H1 and H2 are tour level
    assert ids(L.touched("2027-02-01", "2027-03-01", "both", "lower", reg)) == []         # after H3 ends
    assert "H4" not in ids(L.touched("2025-01-01", "2027-01-01", "both", "all", reg))     # released


def test_touched_refuses_a_backwards_window_and_unknown_choices(tmp_path):
    reg = register_file(tmp_path)
    with pytest.raises(ValueError):
        L.touched("2026-10-20", "2026-10-19", register_path=reg)
    with pytest.raises(ValueError):
        L.touched("2026-10-19", "2026-10-20", tours="men", register_path=reg)


def test_touched_takes_timestamps(tmp_path):
    import numpy as np
    import pandas as pd
    reg = register_file(tmp_path)
    assert ids(L.touched(pd.Timestamp("2026-10-01"), np.datetime64("2026-10-19"), "both", "tour", reg)) == ["H1", "H2"]


def test_add_look_numbers_rows_and_records_the_periods(tmp_path):
    reg, looks = register_file(tmp_path), tmp_path / "looks.csv"
    r1 = L.add_look("Claude", "2026-01-01", "2026-10-20", "both", "tour", "main", "a, comparison", "docs/x.md",
                    options=2, se_mll=0.17, path=looks, register_path=reg, now=NOW)
    r2 = L.add_look("Claude", "2026-01-01", "2026-10-20", "both", "tour", "main", "the same, narrower", "docs/x.md",
                    periods="H1", path=looks, register_path=reg, now=NOW)
    r3 = L.add_look("Claude", "2025-01-01", "2025-12-31", "both", "all", "props", "totals", "docs/y.md",
                    market="total games", done_on="2026-10-22", path=looks, register_path=reg, now=NOW)
    assert (r1["id"], r2["id"], r3["id"]) == ("L0001", "L0002", "L0003")
    assert (r1["periods"], r2["periods"], r3["periods"]) == ("H1;H2", "H1", "none")
    assert r3["done_on"] == "2026-10-22" and r1["done_on"] == "2026-10-29"
    back = L.looks(looks)
    assert ids(back) == ["L0001", "L0002", "L0003"] and back[0]["what"] == "a, comparison"
    assert back[0]["options"] == "2" and back[0]["se_mll"] == "0.17" and back[2]["market"] == "total games"
    assert looks.read_text(encoding="utf-8").count("id,kind,") == 1                      # one header


def test_add_look_refuses_missing_fields_and_unknown_periods(tmp_path):
    reg, looks = register_file(tmp_path), tmp_path / "looks.csv"
    with pytest.raises(ValueError):
        L.add_look("Claude", "2026-01-01", "2026-02-01", "both", "tour", "main", " ", "docs/x.md",
                   path=looks, register_path=reg)
    with pytest.raises(ValueError):
        L.add_look("Claude", "2026-01-01", "2026-02-01", "both", "tour", "main", "x", "docs/x.md", periods="H9",
                   path=looks, register_path=reg)
    with pytest.raises(ValueError):
        L.add_look("Claude", "2026-01-01", "2026-02-01", "both", "tour", "main", "x", "docs/x.md", options=0,
                   path=looks, register_path=reg)
    assert not looks.exists()


def test_a_hand_edit_without_a_final_newline_is_repaired(tmp_path):
    reg, looks = register_file(tmp_path), tmp_path / "looks.csv"
    L.add_look("Claude", "2026-01-01", "2026-02-01", "both", "tour", "main", "x", "docs/x.md",
               path=looks, register_path=reg, now=NOW)
    looks.write_bytes(looks.read_bytes().rstrip(b"\r\n"))
    L.add_look("Claude", "2026-01-01", "2026-02-01", "both", "tour", "main", "y", "docs/x.md",
               path=looks, register_path=reg, now=NOW)
    assert [r["what"] for r in L.looks(looks)] == ["x", "y"]


def test_decisions_rest_on_logged_reads(tmp_path):
    reg, looks = register_file(tmp_path), tmp_path / "looks.csv"
    L.add_look("Claude", "2026-08-01", "2026-10-20", "atp", "tour", "main", "x", "docs/x.md",
               options=3, se_mll=0.2, path=looks, register_path=reg, now=NOW)
    with pytest.raises(ValueError):
        L.add_decision("owner", "L0001,L0009", "adopt x", "reading", "docs/d.md", path=looks, now=NOW)
    with pytest.raises(ValueError):
        L.add_decision("owner", "L0001", "adopt x", "gut feeling", "docs/d.md", path=looks, now=NOW)
    d = L.add_decision("owner", "L0001", "adopt x", "reading", "docs/d.md", path=looks, now=NOW)
    assert d["id"] == "D0001" and d["periods"] == "H1;H2" and d["uses"] == "L0001"
    assert L.add_look("Claude", "2026-01-01", "2026-02-01", "both", "tour", "main", "z", "docs/x.md",
                      path=looks, register_path=reg, now=NOW)["id"] == "L0002"     # reads and decisions count apart


def test_expected_max_matches_the_rebuild_table():
    table = {1: 0.0, 2: 0.56, 3: 0.85, 4: 1.03, 6: 1.27, 10: 1.54}       # 02_contamination_and_forecast.md, section 1
    for k, m in table.items():
        assert L.expected_max(k) == pytest.approx(m, abs=0.005)


def test_status_reports_reads_decisions_and_optimism(tmp_path):
    reg, looks = register_file(tmp_path), tmp_path / "looks.csv"
    L.add_look("Claude", "2026-08-01", "2026-10-20", "atp", "tour", "main", "the pick", "docs/x.md",
               options=3, se_mll=0.2, path=looks, register_path=reg, now=NOW)
    L.add_look("Claude", "2026-08-01", "2026-10-20", "both", "tour", "main", "a harm check", "docs/x.md",
               path=looks, register_path=reg, now=NOW)
    L.add_decision("owner", "L0001", "adopt x", "reading", "docs/d.md", path=looks, now=NOW)
    L.add_decision("Claude", "L0002", "keep y", "harm-check", "docs/d.md", path=looks, now=NOW)
    text = L.status(looks, reg)
    h1 = text.split("H2  ")[0]
    assert "reads: 2" in h1 and "decisions resting on them: 2" in h1
    assert f"{0.2 * L.expected_max(3):.3f} mLL" in h1                 # se x m_3
    assert "about 0 (the reading could only veto)" in h1
    assert "H4  an old period" in text and "warning" not in text


def test_status_flags_an_id_written_twice(tmp_path):
    reg, looks = register_file(tmp_path), tmp_path / "looks.csv"
    L.add_look("Claude", "2026-08-01", "2026-08-02", "atp", "tour", "main", "x", "docs/x.md",
               path=looks, register_path=reg, now=NOW)
    looks.write_text(looks.read_text(encoding="utf-8") + looks.read_text(encoding="utf-8").splitlines()[1] + "\n",
                     encoding="utf-8")
    assert "ids written twice" in L.status(looks, reg)


def test_warn_says_the_rule_on_stderr(tmp_path, capsys):
    reg = register_file(tmp_path)
    hits = L.warn("2026-10-01", "2026-10-25", "atp", "all", "harness.py", reg)
    err = capsys.readouterr().err
    assert ids(hits) == ["H1", "H2"] and "reaches H1" in err and "Soft rule" in err


def test_the_repository_register_reads(tmp_path):
    reg = L.register()
    assert reg and set(L.REGISTER_COLUMNS) <= set(reg[0])
    h1 = next(r for r in reg if r["id"] == "H1")
    assert h1["first_day"] == "2026-10-19" and h1["tours"] == "both" and h1["levels"] == "tour"
    assert all(r["tours"] in L.TOURS and r["levels"] in L.LEVELS for r in reg)
    for r in L.looks():                                                 # every logged row names known periods
        assert all(p in {x["id"] for x in reg} for p in r["periods"].split(";") if p != "none")
