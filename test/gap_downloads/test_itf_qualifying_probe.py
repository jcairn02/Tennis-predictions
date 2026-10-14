"""The ITF qualifying probe's selection: played singles qualifying events only, and a seeded, capped sample
(offline, synthetic)."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.eda.gap_downloads import itf_qualifying_probe as Q  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_sofascore_editions import event  # noqa: E402


def qual(eid, rnd="Qualification Round 1", **kw):
    return event(eid, f"Ann Bee{eid}", f"Cid Dee{eid}", "2024-11-24", tname="M15 Monastir, Qualifying", rnd=rnd, **kw)


def test_only_played_singles_qualifying_events_are_probed():
    walkover = qual(4)
    walkover["status"] = {"code": 100, "type": "finished", "description": "Walkover"}
    cancelled = qual(5)
    cancelled["status"] = {"code": 70, "type": "canceled", "description": "Canceled"}
    main = event(6, "Eve Fox", "Gus Hil", "2024-11-26", tname="M15 Monastir", rnd="Round of 32")
    doubles = qual(7, doubles=True)
    named_by_round_only = event(8, "Ivy Jo", "Kay Lu", "2024-11-24", tname="M15 Monastir", rnd="Qualification Final")
    events = [qual(1), qual(2), walkover, cancelled, main, doubles, named_by_round_only]
    assert [e["id"] for e in Q.qualifying_events(events)] == [1, 2, 8]


def test_the_sample_is_capped_seeded_and_ordered():
    events = [qual(i) for i in range(40, 0, -1)]
    picked = Q.sample(events, 10, seed=7)
    assert len(picked) == 10 and [e["id"] for e in picked] == sorted(e["id"] for e in picked)
    assert [e["id"] for e in Q.sample(events, 10, seed=7)] == [e["id"] for e in picked]   # the same seed, the same sample
    assert [e["id"] for e in Q.sample(events[:5], 10, seed=7)] == [36, 37, 38, 39, 40]   # fewer than the cap: all
