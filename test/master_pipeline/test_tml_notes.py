"""Tests of the bet sheet's run notes and the notebook's held-file list after the decision of 13 Oct 2026 (Tennis My
Life's own lower-level corrections enter by themselves; docs/decisions/2026-10-13-tml-lower-level-revisions.md):
no history note for them, a note for lower-level changes no decision covers, the held files named in the download
note, and an accepted held version no longer listed as held.

Run: ./python.sh -m pytest test/master_pipeline -q
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.pipeline import config as CFG  # noqa: E402
from src.pipeline import data as D  # noqa: E402
from src.pipeline import diagnostics as G  # noqa: E402


def gated(by: list[dict]) -> dict:
    return {"new_past": {"matches": sum(r["matches"] for r in by), "by": by}, "dropped": {"matches": 0, "by": []},
            "revised": {"matches": 0, "by": []}}


TML_ROWS = [{"source": "tml", "tour": "atp", "map_level": "TQ", "year": 2011, "matches": 24}]


def test_no_history_note_for_tennis_my_lifes_own_corrections(tmp_path):
    hist = {"template_ok": True, "gated": gated([]), "tml_lower": gated(TML_ROWS)}
    assert G._run_notes(tmp_path, hist, {}, None) == []


def test_a_record_written_before_the_decision_gets_no_note_for_them(tmp_path):
    hist = {"template_ok": False, "gated": gated(TML_ROWS)}             # no tml_lower: written before 13 Oct
    assert G._run_notes(tmp_path, hist, {}, None) == []


def test_a_lower_level_change_no_decision_covers_is_noted(tmp_path):
    other = [{"source": "tennislive", "tour": "atp", "map_level": "ITF", "year": 2022, "matches": 1}]
    for hist in ({"template_ok": False, "gated": gated(other), "tml_lower": gated(TML_ROWS)},
                 {"template_ok": False, "gated": gated(TML_ROWS + other)}):
        notes = G._run_notes(tmp_path, hist, {}, None)
        assert len(notes) == 1 and "no decision covers" in notes[0]["plain"]


def test_the_download_note_names_the_held_files(tmp_path):
    tail = ("[tennis_my_life] held 2022_challenger.csv: 38 rows of the current copy are gone (more than 5). To accept it "
            "after review: --accept-held 2022_challenger.csv@d95fa0a4bf8a\n[tennis_my_life] held 2025_challenger.csv: "
            "12 rows of the current copy are gone (more than 5).\n")
    (tmp_path / "refresh.json").write_text(json.dumps({"steps": [{"step": "tml", "exit": 1, "tail": tail}]}),
                                           encoding="utf-8")
    download = G._download_warning(tmp_path)
    notes = G._run_notes(tmp_path, {}, {}, download)
    assert len(notes) == 1 and "2022_challenger.csv, 2025_challenger.csv" in notes[0]["plain"]
    assert "held 2 changed files for review" in notes[0]["plain"]


def test_a_lock_or_failure_keeps_the_general_download_note(tmp_path):
    (tmp_path / "refresh.json").write_text(json.dumps({"steps": [{"step": "tml", "exit": 1, "tail": "lock"}]}),
                                           encoding="utf-8")
    notes = G._run_notes(tmp_path, {}, {}, G._download_warning(tmp_path))
    assert len(notes) == 1 and "did not finish cleanly" in notes[0]["plain"]


def test_an_accepted_held_version_is_not_listed(tmp_path, monkeypatch):
    raw = tmp_path / "tennis_my_life"
    (raw / "held").mkdir(parents=True)
    accepted, waiting = b"accepted bytes\n", b"new bytes\n"
    sha = lambda b: hashlib.sha256(b).hexdigest()[:12]                 # noqa: E731
    (raw / "2024_challenger.csv").write_bytes(accepted)                  # the current copy is the held version
    (raw / f"held/2024_challenger.{sha(accepted)}.csv").write_bytes(accepted)
    (raw / "2025_challenger.csv").write_bytes(b"old bytes\n")
    (raw / f"held/2025_challenger.{sha(waiting)}.csv").write_bytes(waiting)
    monkeypatch.setattr(CFG, "TML_RAW", raw)
    assert D.held_tml_files() == [f"2025_challenger.csv@{sha(waiting)}"]
