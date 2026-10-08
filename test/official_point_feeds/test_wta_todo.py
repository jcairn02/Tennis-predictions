"""The WTA to-do list's classification and estimates (offline)."""
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src" / "eda" / "official_point_feeds"))

from src.ingest.point_sources import common as P  # noqa: E402
from src.ingest.point_sources import wta as W  # noqa: E402
import wta_todo as T  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_item_states(tmp_path):
    doc = tmp_path / "events.json.gz"
    assert T.item_state(None, doc, "events") == "pending"
    assert T.item_state({"error": "HTTP 500"}, doc, "events") == "error"
    assert T.item_state({"status": 404}, doc, "events") == "absent"
    assert T.item_state({"status": 200, "bytes": 9000}, doc, "events") == "pending"  # the file is missing: fetch again
    doc.write_bytes(__import__("gzip").compress(b'{"Events": [], "Players": {}}'))
    assert T.item_state({"status": 200, "bytes": 30}, doc, "events") == "empty"
    full = (FIXTURES / "wta_events_1045_2024_LS001.json").read_bytes()
    doc.write_bytes(__import__("gzip").compress(full))
    assert T.item_state({"status": 200, "bytes": 3000}, doc, "events") == "fetched"  # small enough to be opened
    assert T.item_state({"status": 200, "bytes": 50000}, doc, "events") == "fetched"
    box = tmp_path / "stats.json.gz"
    box.write_bytes(__import__("gzip").compress(b"[]"))
    assert T.item_state({"status": 200, "bytes": 2}, box, "stats") == "empty"  # opened: "[]"
    assert T.item_state({"status": 200, "bytes": 534}, box, "stats") == "fetched"  # the smallest with a row: not opened


def test_data_by_endpoint():
    assert T.has_data("stats", [{"setnum": 0}]) and not T.has_data("stats", [])
    assert T.has_data("advanced-stats", {"teamA": {}, "teamB": {"x": 1}}) and not T.has_data("advanced-stats", {})
    assert T.has_data("win-probability-momentum", [{"pointInMatch": 0}])
    assert T.has_data("point-by-point", json.loads((FIXTURES / "wta_pbp_1045_2024_LD001.json").read_text("utf-8")))


def test_scope_and_estimates():
    b1 = next(b for b in W.BATCHES if b["id"] == "B1")
    edition = {"year": 2021, "tier": "250", "start_date": "2021-03-01", "tournament_id": "1", "status": "past",
               "singles_draw_size": 32}
    assert T.in_scope(b1, edition) and not T.in_scope(b1, {**edition, "tier": "slam"})
    assert not T.in_scope(b1, {**edition, "year": 2019})
    b8 = next(b for b in W.BATCHES if b["id"] == "B8")
    assert not T.in_scope(b8, {**edition, "year": 2022, "start_date": "2022-03-09"})  # before point-by-point began
    editions = [{**edition, "tournament_id": str(n)} for n in range(5)]
    held = {("0", 2021): Counter(main_singles=31, main_doubles=15), ("1", 2021): Counter(main_singles=27),
            ("2", 2021): Counter()}  # a cancelled edition: listed, nothing played
    guess = T.size_estimator(held, editions)({**edition, "tournament_id": "4"})
    assert round(guess["main_singles"], 3) == round(29 * 2 / 3, 3) and round(guess["main_doubles"], 3) == 5.0
